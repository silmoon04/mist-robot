"""Reconcile actual candidate CAD volumes with nominal/assumed hardware mass."""
from collections import defaultdict
from pathlib import Path
import argparse
import copy
import hashlib
import json

ROOT=Path(__file__).resolve().parent

def audit(report_path, output):
    raw=report_path.read_bytes(); report=json.loads(raw)
    parameter_path=Path(report.get('parameters_path',ROOT/'simulation/parameters.json'))
    p=json.loads(parameter_path.read_text())
    recipes={group:{x['name']:x for x in spec['parts']} for group,spec in report['specifications'].items()}
    expected_groups=set(p['geometry']['leg_names'])|{'body'}
    if set(recipes)!=expected_groups:
        raise ValueError('Mass audit requires the complete four-leg plus body export; found '+', '.join(recipes))
    totals=defaultdict(float); group_links=defaultdict(float); moment=defaultdict(lambda:[0.,0.,0.])
    rows=[]; missing=[]; rotating_wheel=defaultdict(float)
    body_hardware={'H01_battery_HOOVO_3S_REFERENCE':174.,'H02_brain_phone_ENVELOPE':155.,'H03_face_phone_Mi9SE_REFERENCE':155.}
    for item in report['parts']:
        group=item['group']; part=recipes[group][item['name']]; name=part['name']; v=item.get('mass_volume_cm3',item['volume_cm3'])
        source=''; mass=None; bucket='other'
        if part['category']=='visual_reference': mass=0.;source='Display guide, not additional physical mass';bucket='visual'
        elif group=='body' and name in body_hardware:mass=body_hardware[name];source='Prior nominal battery/phone assumption';bucket='hardware'
        elif 'mass_g' in part:mass=float(part['mass_g']);source=part.get('mass_provenance','Nominal part mass');bucket='hardware'
        elif 'density_g_cm3' in part:
            mass=v*part['density_g_cm3'];source=part.get('mass_provenance',part.get('material','')+' solid CAD volume')
            bucket='print' if part['category']=='print' else 'hardware_estimate'
        elif part['category']=='print':mass=v*1.27;source='Solid PETG CAD at1.27g/cm3';bucket='print'
        elif 'belt_ENVELOPE' in name:mass=10.;source='Explicit10g belt allowance, actual belt unselected';bucket='hardware_estimate'
        if mass is None:
            missing.append(group+'__'+name);continue
        if mass<0:raise ValueError('Negative part mass')
        key=group+'|'+part.get('link','body'); totals[bucket]+=mass;group_links[key]+=mass
        for i in range(3):moment[key][i]+=mass*item['center_hipplane_mm'][i]
        if name in ['W02_6mm_wheel_axle','W03_wheel_hub','W04_tire_ENVELOPE']:rotating_wheel[group]+=mass
        rows.append(dict(name=group+'__'+name,group=group,link=part.get('link','body'),mass_g=mass,
                         source=source,bucket=bucket,center_hipplane_mm=item['center_hipplane_mm']))
    allowance=(p['mass']['electronics_kg']+p['mass']['harness_kg'])*1000+50
    total=sum(totals.values())+allowance
    output.mkdir(parents=True,exist_ok=True)
    result=dict(status='CAD_mass_sensitivity_not_weighed_or_slicer_confirmed',
                source_report_sha256=hashlib.sha256(raw).hexdigest(),source_report=str(report_path),
                accounted_mass_g=total,part_mass_by_category_g=dict(totals),mass_by_group_link_g=dict(group_links),
                extra_allowance_g=allowance,extra_allowance_note='Existing250g electronics+150g harness, plus explicit50g unmatched nuts/washers/couplers. Not a finished BOM.',
                missing_mass_items=missing,rows=rows,
                caveats=['Printed masses are solid model volumes; actual slicing and scales remain necessary.',
                         'Bearing annuli are upper-bound solid steel envelopes, not actual bearing weights.',
                         'The extra allowances and current motor/phone assignments are unmeasured.',
                         'Missing parts, future brackets, covers, couplings or wiring can increase mass. This is not a final upper bound.'])
    (output/'mass_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    names=p['geometry']['leg_names']
    if set(names).issubset(recipes) and 'body' in recipes and not missing:
        q=copy.deepcopy(p); m=q['mass']; fixed_extra=[]
        for row in rows:
            if row['group'] in names and row['link']=='body' and 'C018' not in row['name']:
                fixed_extra.append(row)
        shell_rows=[x for x in rows if x['group']=='body' and x['bucket']=='print' and not x['name'].endswith(('B13_face_phone_cassette','B14_square_face_bezel'))]
        shell_rows+=fixed_extra
        m['shell_kg']=sum(x['mass_g'] for x in shell_rows)/1000+.05
        m['shell_com_m']=[sum(x['mass_g']*x['center_hipplane_mm'][i]/1e6 for x in shell_rows)/m['shell_kg'] for i in range(3)]
        face_rows=[x for x in rows if x['group']=='body' and x['name'].endswith(('B13_face_phone_cassette','B14_square_face_bezel','H03_face_phone_Mi9SE_REFERENCE'))]
        m['face_phone_with_frame_kg']=sum(x['mass_g'] for x in face_rows)/1000
        m['face_phone_com_m']=[sum(x['mass_g']*x['center_hipplane_mm'][i]/1e6 for x in face_rows)/m['face_phone_with_frame_kg'] for i in range(3)]
        def avg(*links):return sum(group_links[n+'|'+link] for n in names for link in links)/4000
        m['yaw_carriage_without_servos_kg']=avg('yaw','pod')-2*m['proximal_servo_kg']
        m['femur_with_pulleys_kg']=avg('femur');m['tibia_with_carrier_kg']=avg('tibia')
        m['wheel_hub_and_tire_kg']=sum(rotating_wheel.values())/4000
        m['wheel_motor_with_mount_kg']=avg('wheel')-m['wheel_hub_and_tire_kg']
        m['provenance']='Mass-only reconciliation to actual candidate CAD, solid-print/bearing-envelope assumptions plus stated allowances. Link COM/inertias and collision shapes remain coarse.'
        q['status']='heavier_CAD_mass_only_sensitivity_not_selected_design'
        q['cad_mass_report_sha256']=result['source_report_sha256']
        expected=sum(m[k] for k in ['shell_kg','battery_kg','brain_phone_kg','face_phone_with_frame_kg','electronics_kg','harness_kg'])
        expected+=4*(3*m['proximal_servo_kg']+sum(m[k] for k in ['yaw_carriage_without_servos_kg','femur_with_pulleys_kg','tibia_with_carrier_kg','wheel_motor_with_mount_kg','wheel_hub_and_tire_kg']))
        result['coarse_sim_mass_kg']=expected
        result['accounting_delta_g']=expected*1000-total
        if abs(result['accounting_delta_g'])>.1:
            result['parameters_created']=False
        else:
            (output/'parameters_mass_only.json').write_text(json.dumps(q,indent=2),encoding='utf-8');result['parameters_created']=True
        (output/'mass_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# Candidate CAD mass reconciliation','',f"Accounted mass: **{total/1000:.3f} kg**. This uses the actual exported candidate volumes and nominal/assumed hardware values. It is neither a scale measurement nor a slicer estimate.",'',
           '| Group | Accounted mass |','|---|---:|']
    for group in recipes:lines.append(f"| {group} | {sum(r['mass_g'] for r in rows if r['group']==group):.1f} g |")
    lines += [f'| Electronics, harness and unmatched hardware allowance | {allowance:.1f} g |','',
              'The per-part JSON keeps every mass source. Bearings are deliberately represented by a solid steel annulus estimate, which can exceed actual ball-bearing mass. Fully solid PETG volumes also exceed many sliced parts. Unmodeled couplings, nuts, wires and covers can add mass. These opposing uncertainties cannot be collapsed into a claimed finished weight.','',
              'A mass-only parameter snapshot is produced only when its accounting agrees with the CAD grouping. It retains simple link COM/inertia and collision geometry, so it is a sensitivity experiment rather than a reconstructed dynamic CAD model. Earlier3.95376kg simulation results remain attached to their original parameters.','',
              'Missing mass assignments: '+(', '.join(missing) if missing else 'none among exported parts; unfinished physical parts still require a BOM')+'.']
    (output/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','caveats','mass_by_group_link_g')},indent=2))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path,default=ROOT/'cad/leg_output/leg_geometry_report.json');parser.add_argument('--out',type=Path,default=ROOT/'simulation/cad_mass_20260907')
    args=parser.parse_args();audit(args.report,args.out)
