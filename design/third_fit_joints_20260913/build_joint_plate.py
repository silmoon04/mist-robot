"""Next joint-fit fixtures, with support-free geometry and the proven clamp reused."""
from pathlib import Path
import hashlib
import json
import math
import sys

HERE=Path(__file__).resolve().parent
CAD=HERE.parent/'hexapod_phone_quad_r5_20260912/cad'
sys.path.insert(0,str(CAD))
import geom as g
import leg
import fit_coupons as fit
import servo_contract as sc
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon
from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCP.gp import gp_Pnt


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def taper(rectangles):
    op=BRepOffsetAPI_ThruSections(True,True)
    for x0,x1,y0,y1,z in rectangles:
        w=BRepBuilderAPI_MakePolygon()
        for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1)):w.Add(gp_Pnt(x,y,z))
        w.Close();op.AddWire(w.Wire())
    op.Build();assert op.IsDone() and g.valid(op.Shape())
    return op.Shape()


def gauge():
    original=fit.datum_registration_plate()
    shape=original
    for sign in (-1,1):
        # Fasten from the top with an M3x50 tie bolt. A short bolt head under
        # this brace would be inaccessible. Fill the old driver-access hole
        # and retain a straight vertical 3.4 mm bore and flat washer seat.
        shape=g.fuse(shape,g.cylinder(3.5,4,(9,sign*20,4.5)))
        ya,yb=(23.5,29.5) if sign>0 else (-29.5,-23.5)
        yc,yd=(16.9,30) if sign>0 else (-30,-16.9)
        shape=g.fuse(shape,taper([(6,12,ya,yb,-17.4),(3,15,yc,yd,-25)]))
        shape=g.cut(shape,g.cylinder(1.7,44,(9,sign*20,-33)))
    return original,shape


def parts():
    original,registration=gauge()
    result=[dict(name='01_case_to_shaft_gauge_no_support',shape=registration,rotation=(180,0,0),
        purpose='Attach to the existing clamped servo with two M3x50 tie bolts, printed 5 mm underside spacers, nuts and washers. New tapered feet remove the former supports.')]
    for index in (1,2):
        spacer=g.cut(g.cylinder(4,5),g.cylinder(1.7,7,(0,0,-1)))
        result.append(dict(name=f'01_gauge_tie_bolt_spacer_5mm_{index}',shape=spacer,rotation=(0,0,0),
            purpose='Under the existing saddle foot, before its washer and nut, when using the M3x50 gauge tie bolt. This is not a yaw spacer.'))
    for p in fit.horn_fixture_cheeks():
        shape=p['shape'];rotation=p['print_rotation'];name=p['name']
        if name.endswith('bridge_38'):
            r=1.7;q=r/math.sqrt(2)
            roof=g.prism_xz([(29-q,q),(29,r*math.sqrt(2)),(29+q,q)],-20,40)
            shape=g.cut(shape,roof);rotation=(0,0,0)
            name='04_horn_bridge_38_roofed'
        elif name.endswith('main'):name='02_main_horn_cheek'
        else:
            name='03_auxiliary_horn_cheek'
            shape=g.cut(shape,leg._pitch(sc.plugged_profile_reserve(),False))
        result.append(dict(name=name,shape=shape,rotation=rotation,purpose=p['note']))
    for label,length,count in [('nominal',11.6,4),('short',11.3,1),('long',11.9,1)]:
        for index in range(count):
            shape=g.cut(g.cylinder(2.9,length),g.cylinder(1.7,length+2,(0,0,-1)))
            result.append(dict(name=f'05_yaw_spacer_{label}_{str(length).replace(".","p")}_{index+1}',
                shape=shape,rotation=(0,0,0),purpose='Four nominal spacers form a complete set. Short and long alternatives are comparison samples only.'))
    strip=g.cut(leg._b(-17,17,-7,7,0,4),*[g.cylinder(d/2,6,(x,0,-1)) for x,d in ((-10,3.2),(0,3.4),(10,3.6))])
    result.append(dict(name='06_M3_hole_strip_3p2_3p4_3p6',shape=strip,rotation=(0,0,0),
        purpose='Left to right from the notched end: 3.2, 3.4 and 3.6 mm bore diameter.'))
    # A notch identifies the start without putting small lettering on fit faces.
    result[-1]['shape']=g.cut(strip,leg._b(-18,-15,-8,-5,-1,5))
    depth=leg._b(-18,18,-6,6,0,5)
    for x,h in ((-11,2.6),(0,2.8),(11,3.0)):
        depth=g.cut(depth,leg._hex_z(x,0,5-h,h+1,5.7),g.cylinder(1.7,7,(x,0,-1)))
    depth=g.cut(depth,leg._b(-19,-16,-7,-4,-1,6))
    result.append(dict(name='07_M3_nut_depth_2p6_2p8_3p0',shape=depth,rotation=(0,0,0),
        purpose='Left to right from the notched end: 2.6, 2.8 and 3.0 mm pocket depth; all have 5.7 mm across flats. Measures nut seating without guessing what needed sanding.'))
    return original,registration,result


def main():
    HERE.mkdir(exist_ok=True)
    original,registration,items=parts()
    previous=HERE.parent/'second_fit_supportfree_20260913'
    saddle=g.import_step(previous/'second_fit_saddle_45deg_roofs.step')
    oldcap=leg.case_clamp(True,.3)[1]
    checks={name:g.common_volume(registration,shape) for name,shape in (
        ('gauge_to_printed_saddle',saddle),('gauge_to_reused_cap',oldcap),
        ('gauge_to_servo',leg.servo_envelope()),('gauge_to_main_horn',leg.main_horn()))}
    assert all(v<.01 for v in checks.values()),checks
    # Exact planar interface regions stay identical; only free-space braces are added.
    for name,region in [('horn_face',g.cylinder(14.1,4.02,(0,0,4.49))),
                        ('mount_feet',leg._b(2.9,15.1,-30.1,30.1,-29.01,-25.01))]:
        delta_added=g.common_volume(g.cut(registration,original),region)
        delta_removed=g.common_volume(g.cut(original,registration),region)
        checks[name+'_added_mm3']=delta_added;checks[name+'_removed_mm3']=delta_removed
        assert delta_added<.01 and delta_removed<.01,(name,delta_added,delta_removed)
    for sign in (-1,1):
        screw=g.cylinder(1.5,50,(9,sign*20,-41))
        washer=g.cut(g.cylinder(3,.5,(9,sign*20,8.5)),g.cylinder(1.6,2,(9,sign*20,8)))
        for name,part in [('gauge',registration),('existing_saddle',saddle),('servo',leg.servo_envelope()),('cap',oldcap)]:
            v=g.common_volume(screw,part);checks[f'tie_bolt_{sign}_to_{name}_mm3']=v;assert v<.01
        assert g.common_volume(washer,registration)<.01
    # Correct horn stack around the same fixed pitch servo, at a neutral fixture angle.
    main=next(p['shape'] for p in items if p['name']=='02_main_horn_cheek')
    aux=next(p['shape'] for p in items if p['name']=='03_auxiliary_horn_cheek')
    bridge=next(p['shape'] for p in items if p['name']=='04_horn_bridge_38_roofed')
    checks['auxiliary_cheek_to_provisional_plug_mm3']=g.common_volume(aux,leg._pitch(sc.plugged_profile_reserve(),False))
    assert checks['auxiliary_cheek_to_provisional_plug_mm3']<.01
    assembled=[('main',main),('auxiliary',aux),('bridge',bridge),
        ('case',leg._pitch(leg.servo_envelope(),False)),
        ('main_horn',leg._pitch(leg.main_horn(),False)),
        ('aux_disc',leg._pitch(leg.auxiliary_disc(),False))]
    for i,(a,sa) in enumerate(assembled):
        for b,sb in assembled[i+1:]:
            v=g.common_volume(sa,sb);checks[f'horn_fixture_{a}_to_{b}_mm3']=v;assert v<.01,(a,b,v)
    records=[]
    for item in items:
        shape=g.transform(item['shape'],rpy_deg=item['rotation'])
        lo,hi=g.bounds(shape);shape=g.translate(shape,tuple(-v for v in lo))
        g.export_stl(shape,HERE/(item['name']+'.stl'),deflection=.025)
        records.append({'name':item['name'],'stl':item['name']+'.stl',
            'sha256':sha(HERE/(item['name']+'.stl')),'dimensions_mm':[hi[k]-lo[k] for k in range(3)],
            'print_rotation_deg':item['rotation'],'purpose':item['purpose'],
            'volume_mm3':g.volume(item['shape'])})
    g.export_step(registration,HERE/'case_to_shaft_gauge_no_support.step')
    feedback={'date':'2026-09-13','operator_report':{
        'printed':'Revised upright saddle only; reused an earlier flat cap.',
        'sanding':'Some sanding was required around the reported 2.5 nut or height fit. Exact feature and cause not confirmed.',
        'nut_fit':'All three nuts fitted firmly.',
        'servo_retention':'Servo reported not moving within the completed clamp.',
        'nut_identifier':'2.5 wording awaiting clarification; no M2.5 substitution assumed.',
        'physical_load_or_torque_measurement':None},
        'disposition':'Proceed to shaft alignment and free horn/auxiliary rotation fixtures. Keep the case-contact dimensions.',
        'flat_cap_changed_between_trials':False}
    data={'status':'geometry_checks_pass','parts':records,'interface_checks':checks,
        'prior_printed_saddle_step_sha256':sha(previous/'second_fit_saddle_45deg_roofs.step'),
        'source_manifest_sha256':sha(CAD/'output/assembly_manifest.json'),
        'feedback':feedback,'units':'mm',
        'limits':['Assembled clamp retention is operator-reported and has no quantified load test.',
            'The registration gauge checks fixed alignment only; do not command the servo with it attached.',
            'No powered or loaded joint performance is established by the current feedback.']}
    (HERE/'cad_manifest.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps({'parts':len(records),'checks':checks}),flush=True)


if __name__=='__main__':main()
