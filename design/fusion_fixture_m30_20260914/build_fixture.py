"""M3x30 bridge adaptation and exact parts for the Fusion teaching assembly."""
from pathlib import Path
import json,hashlib,sys,math
HERE=Path(__file__).resolve().parent
CAD=HERE.parent/'hexapod_phone_quad_r5_20260912/cad'
THIRD=HERE.parent/'third_fit_joints_20260913'
sys.path.insert(0,str(CAD));sys.path.insert(0,str(THIRD))
import geom as g
import leg
import build_joint_plate as previous

def nut(y):
    return g.cut(leg._hex_y(29,y,0,2.4),leg._hole_y(29,0,y-1,5,radius=1.5))

def main():
    assets=HERE/'assets';assets.mkdir(parents=True,exist_ok=True)
    _,gauge,parts=previous.parts()
    named={p['name']:p['shape'] for p in parts}
    bridge=named['04_horn_bridge_38_roofed']
    # Two side-loaded hex pockets; a central gap separates opposing screw tips.
    for ya,yb in [(-6.6,-4),(4,6.6)]:
        bridge=g.cut(bridge,leg._hex_y(29,ya,0,yb-ya),leg._b(26.15,31.85,ya,yb,0,8))
    spacer=g.cut(g.cylinder(4,8),g.cylinder(1.7,10,(0,0,-1)))
    fixed={'servo_case_FIXED':leg._pitch(leg.servo_envelope(),False)}
    moving={'main_horn_MOVES':leg._pitch(leg.main_horn(),False),
        'aux_disc_MOVES':leg._pitch(leg.auxiliary_disc(),False),
        'main_cheek_MOVES':named['02_main_horn_cheek'],
        'aux_cheek_MOVES':named['03_auxiliary_horn_cheek'],
        'bridge_M3x30_MOVES':bridge,
        'spacer_main_MOVES':g.translate(g.rotate(spacer,(1,0,0),-90),(29,23,0)),
        'spacer_aux_MOVES':g.translate(g.rotate(spacer,(1,0,0),-90),(29,-31,0))}
    checks=[]
    allparts={**fixed,**moving}
    for i,(a,sa) in enumerate(allparts.items()):
        for b,sb in list(allparts.items())[i+1:]:
            v=g.common_volume(sa,sb);assert v<.01,(a,b,v)
    for side in [-1,1]:
        start=-31.5 if side<0 else 1.5
        screw=leg._hole_y(29,0,start,30,radius=1.5)
        n=nut(-6.5 if side<0 else 4.1)
        for name,shape in allparts.items():
            v=g.common_volume(shape,screw);assert v<.01,(side,name,v)
        assert g.common_volume(n,bridge)<.01
        checks.append({'side':side,'under_head_y_mm':side*31.5,'tip_y_mm':side*1.5,
            'nut_seat_y_mm':[-6.5,-4.1] if side<0 else [4.1,6.5],
            'nominal_screw_tip_separation_mm':3.0})
    motions=[]
    for deg in [-10,-5,0,5,10]:
        hits=[]
        for name,shape in moving.items():
            v=g.common_volume(g.rotate(shape,(0,1,0),deg),fixed['servo_case_FIXED'])
            if v>.01:hits.append((name,v))
        assert not hits,(deg,hits)
        motions.append({'angle_deg':deg,'intersections':hits})
    records=[]
    explode={'main_horn_MOVES':[0,13,0],'aux_disc_MOVES':[0,-13,0],
        'main_cheek_MOVES':[0,35,0],'aux_cheek_MOVES':[0,-35,0],
        'bridge_M3x30_MOVES':[25,0,0],'spacer_main_MOVES':[0,45,0],
        'spacer_aux_MOVES':[0,-45,0],'servo_case_FIXED':[0,0,0]}
    for name,shape in allparts.items():
        g.export_step(shape,assets/(name+'.step'))
        records.append({'name':name,'step':str((assets/(name+'.step')).resolve()),'explode_mm':explode[name]})
    g.export_step(list(fixed.values()),assets/'base.step')
    g.export_step(list(moving.values()),assets/'output.step')
    saddle=g.import_step(HERE.parent/'second_fit_supportfree_20260913/second_fit_saddle_45deg_roofs.step')
    for name,shape in [('alignment_clamp',g.compound([saddle,leg.case_clamp(True,.3)[1],leg.servo_envelope(),leg.main_horn()])),('alignment_gauge',gauge)]:
        g.export_step(shape,assets/(name+'.step'))
    for name,shape in [('bridge_M3x30',bridge),('bridge_spacer_8mm',spacer)]:
        lo,_=g.bounds(shape);normalized=g.translate(shape,tuple(-v for v in lo))
        g.export_stl(normalized,HERE/(name+'.stl'),.025)
        g.export_step(shape,HERE/(name+'.step'))
    result={'parts':records,'bridge_screw_checks':checks,'sampled_motion':motions,
        'motion_axis':[0,1,0],'motion_origin_mm':[0,0,0],
        'scope':'Unpowered fit fixture and kinematic illustration, not a force or motor-control simulation.',
        'print_quantities':{'bridge_M3x30.stl':1,'bridge_spacer_8mm.stl':2},
        'gauge_workaround':'Use the existing gauge as a hand-seated datum check. Do not force feet down or power the servo while gauge is attached.',
        'hardware':'Two M3x30 bridge screws, two plain M3 nuts and two OD7 x0.5 mm head washers, plus two printed 8 mm spacers. Existing short horn screws remain required.'}
    (HERE/'fixture_manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Fixture exported;30mm screws clear and opposing tips remain3mm apart. Motion samples +/-10degrees clear.')

if __name__=='__main__':main()
