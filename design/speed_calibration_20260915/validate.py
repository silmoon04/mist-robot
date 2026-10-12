"""Independently parse emitted G-code, check schedules and extrusion accounting."""
from pathlib import Path
import re,json,math,hashlib,collections
import numpy as np
ROOT=Path(__file__).resolve().parent
FIELDS=re.compile(r'([XYZEFS])([-+]?\d*\.?\d+)')
AREA=math.pi*1.75**2/4

def seconds_stop_to_stop(distance,speed,accel):
    if distance<=0:return 0.
    ramp=speed*speed/accel
    return distance/speed+speed/accel if distance>=ramp else 2*math.sqrt(distance/accel)

def main():
    design=json.loads((ROOT/'test_design.json').read_text());file=ROOT/design['gcode_file'];code=file.read_text();expected=json.loads((ROOT/'expected_paths.json').read_text())
    xyz=np.zeros(3);e_relative=False;absolute=False;homed=False;heated=False;temp=None;bed=None;fan=0;accel=0;speed=0;stage='startup';band=0
    rows=[];retract=0;retraction_time=0;netE=0;front_complete=False;min_clearance=1e9;allowed={'G1','G90','G28','M220','M221','M107','M104','M140','M190','M109','M83','G92','M204','M106','M117','M400','M84','SET_VELOCITY_LIMIT'}
    for line_no,raw in enumerate(code.splitlines(),1):
        if raw==';FRONT_FLOW_TOWER_COMPLETE':front_complete=True
        if raw.startswith(';TEST:'):
            match=re.fullmatch(r';TEST:(\w+) BAND:(\d+)',raw);assert match
            stage=match[1];band=int(match[2])
        text=raw.split(';')[0].strip()
        if not text:continue
        verb=text.split()[0];assert verb in allowed,(line_no,verb)
        fields={k:float(v) for k,v in FIELDS.findall(text.split(' ',1)[1] if ' ' in text else '')}
        if verb=='G90':absolute=True
        elif verb=='G28':homed=True
        elif verb=='M83':e_relative=True
        elif verb=='M104':temp=fields['S'];assert temp in (0,140,210)
        elif verb=='M109':heated=True;temp=fields['S'];assert temp==210
        elif verb in ('M140','M190'):bed=fields['S'];assert bed in (0,60)
        elif verb=='M204':accel=fields['S'];assert 0<accel<=10000
        elif verb=='M106':fan=fields['S'];assert 0<=fan<=255
        elif verb=='M107':fan=0
        elif verb=='SET_VELOCITY_LIMIT':assert text=='SET_VELOCITY_LIMIT VELOCITY=300'
        elif verb=='G1':
            assert absolute and homed
            start=xyz.copy()
            for i,k in enumerate('XYZ'):
                if k in fields:xyz[i]=fields[k]
            speed=fields.get('F',speed*60)/60
            assert 0<speed<=300 and np.isfinite(xyz).all()
            assert -1e-6<=xyz[0]<=225 and -1e-6<=xyz[1]<=225 and 0<=xyz[2]<=45,(line_no,xyz)
            d=float(np.linalg.norm(xyz-start));extr=fields.get('E',0)
            if extr:
                assert e_relative and heated and temp==210 and bed==60
                netE+=extr
                if d<.001:
                    assert abs(extr)<=1 and speed==35
                    retract-=extr;retraction_time+=abs(extr)/speed
                    assert -.0001<=retract<=1.0001,(line_no,retract)
                else:
                    assert extr>0 and retract<.0001
                    assert abs(xyz[2]-start[2])<.0001
                    assert xyz[0]>=17 and xyz[0]<=203 and xyz[1]>=7 and xyz[1]<=207
            if front_complete and min(xyz[2],start[2])<design['height_mm']+.5:
                if stage!='F_RECOVERY':
                    clearance=min(xyz[1],start[1])-50-42.14
                    assert clearance>10,(line_no,clearance)
                    min_clearance=min(min_clearance,clearance)
            if d>.001:
                rows.append({'line_number':line_no,'start':start.tolist(),'end':xyz.tolist(),'distance_mm':d,'speed':speed,'accel':accel,'e':extr,'stage':stage,'band':band,'fan':fan})
    assert temp==0 and bed==0 and fan==0 and accel==2500
    expected_by={r['line_number']:r for r in expected}
    tests=collections.defaultdict(list);volume=collections.defaultdict(float)
    for row in rows:
        if row['line_number'] not in expected_by:continue
        ref=expected_by[row['line_number']]
        assert np.allclose(row['end'],ref['end'],atol=6e-5)
        assert abs(row['e']-ref['e_mm'])<6e-7
        if row['e']<=0:continue
        cross=row['e']*AREA/row['distance_mm'];q=cross*row['speed'];row['flow_mm3_s']=q;row['bead_cross_section_mm2']=cross
        wanted=ref['layer_height']*ref['width'];assert abs(cross-wanted)<.00015,(row['line_number'],cross,wanted)
        assert q<=28.03
        if row['stage'] in ('F','A','R','C','S','T'):
            assert row['fan']==255
            schedule=design['schedule'][row['band']-1];stage=row['stage']
            target_q=schedule['F_flow_mm3_s'] if stage=='F' else schedule['A_flow_mm3_s'] if stage=='A' else schedule['R_flow_mm3_s'] if stage=='R' else 40*.42*.28
            target_a=schedule['A_acceleration_mm_s2'] if stage=='A' else 3000 if stage=='F' else 2000 if stage in ('R','C') else 1500
            assert abs(q-target_q)<.04,(stage,row['band'],q,target_q)
            assert row['accel']==target_a
            assert schedule['z_bottom_mm']<row['end'][2]<=schedule['z_top_mm']+.0001
            tests[(stage,row['band'])].append(row)
        volume[row['stage']]+=row['e']*AREA
    assert set(tests)=={(s,b) for s in ('F','A','R','C','S','T') for b in range(1,7)}
    # Scan retractions separately: no accidental cross-zone parameter bleed.
    stage='startup';band=0
    for raw in code.splitlines():
        if raw.startswith(';TEST:'):m=re.fullmatch(r';TEST:(\w+) BAND:(\d+)',raw);stage=m[1];band=int(m[2])
        if raw.startswith('G1 E-') and stage in ('F','A','R','C','S','T'):
            amount=-float(raw.split()[1][1:]);wanted=design['schedule'][band-1]['S_retraction_mm'] if stage=='S' else .5
            assert abs(amount-wanted)<1e-5
    reach=[]
    for (stage,band),segments in tests.items():
        if stage not in ('F','A','R'):continue
        long=[r for r in segments if r['distance_mm']>=40]
        if stage in ('F','A'):assert long,(stage,band)
        r=max(segments,key=lambda r:r['distance_mm']);distance=r['distance_mm'];speed=r['speed'];acc=r['accel']
        cruise=max(0,distance-speed*speed/acc)
        reach.append({'zone':stage,'band':band,'longest_straight_mm':distance,'requested_speed_mm_s':speed,'accel_mm_s2':acc,'conservative_stop_to_stop_cruise_mm':cruise,
            'note':'Simple trapezoidal calculation. Klipper lookahead, minimum cruise ratio or accel_to_decel, input shaping and pressure advance can alter realized speed.'})
    nominal=sum(r['distance_mm']/r['speed'] for r in rows)+retraction_time
    upper=sum(seconds_stop_to_stop(r['distance_mm'],r['speed'],r['accel'] or 500) for r in rows)+retraction_time
    totalvol=sum(volume.values());mass=totalvol*.00124
    report={'status':'pass','gcode_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'parsed_move_count':len(rows),'tested_zone_bands':len(tests),
        'nominal_motion_lower_bound_minutes':nominal/60,'stop_to_stop_motion_estimate_minutes':upper/60,'heating_and_homing_included':False,
        'estimated_deposited_mass_g':mass,'deposited_volume_by_zone_mm3':dict(volume),'filament_metres':totalvol/AREA/1000,
        'max_flow_mm3_s':max(r.get('flow_mm3_s',0) for r in rows),'max_requested_feed_mm_s':max(r['speed'] for r in rows),'max_acceleration_mm_s2':max(r['accel'] for r in rows),
        'finished_front_tower_minimum_clearance_mm_with_50mm_head_envelope':min_clearance,
        'straight_run_reach_checks':reach,'checks':['ASCII command allowlist','XY and Z bounds','Homing and heating before extrusion','Explicit relative extrusion mode','Retraction recovery accounting','Independent per-zone feed, flow, acceleration and fan checks','Layer band and commanded bead-area checks','No saved-config, shaping, pressure-advance, motor-current or thermal-protection changes','End heaters and fan off, runtime acceleration reset to2500'],
        'limits':['Validation is static, not a physical print or an exact Klipper planner simulation.','Times are bounded motion estimates, not a slicer or firmware ETA.','Subtle overlap, real shrinkage, thermals and maximum usable material flow need the physical result.']}
    (ROOT/'VALIDATION.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('straight_run_reach_checks','checks','limits','deposited_volume_by_zone_mm3')},indent=2))

if __name__=='__main__':main()
