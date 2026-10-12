"""Second full-size clamp trial: keep fitted case surfaces, remove hole supports."""
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
import servo_contract as sc


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def screw_roof(x,z,r=1.7):
    """A circular clearance with a tangent 45-degree pointed upper roof."""
    q=r/math.sqrt(2)
    return g.prism_xz([(x-q,z+q),(x,z+r*math.sqrt(2)),(x+q,z+q)],-18,38)


def nut_roof(x,z):
    """Keep the 5.7 mm nut flats and lower locating faces; open a 45-degree roof."""
    half_flat=5.7/2
    shoulder=half_flat/math.sqrt(3)
    return g.prism_xz([(x-half_flat,z+shoulder),
        (x,z+shoulder+half_flat),(x+half_flat,z+shoulder)],-16.5,2.8)


def actual_nut(x,z,angle=0):
    nut=leg._hex_z(x,-z,0,2.4,5.5)
    nut=g.translate(g.rotate(nut,(1,0,0),-90),(0,-16.1,0))
    if angle:nut=g.rotate(nut,(0,1,0),angle,(x,0,z))
    return g.cut(nut,leg._hole_y(x,z,-18,8,radius=1.5))


def solid_count(shape):
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SOLID
    e=TopExp_Explorer(shape,TopAbs_SOLID);n=0
    while e.More():n+=1;e.Next()
    return n


def main():
    HERE.mkdir(parents=True,exist_ok=True)
    original_saddle,cap=leg.case_clamp(True,.3)
    saddle=original_saddle
    roofs=[]
    for x,z in sc.CLAMP_BOLT_XZ:
        apex=z+5.7/2/math.sqrt(3)+5.7/2
        top=max(-2,apex+2.0)
        if top>-2:
            # Extra material is on the OUTSIDE fixed rail. The fitted servo
            # pocket, case lands, cap gap and every screw axis stay unchanged.
            saddle=g.fuse(saddle,leg._b(x-3.7,x+3.7,-16.365,-12.365,-2,top))
        saddle=g.cut(saddle,screw_roof(x,z),nut_roof(x,z))
        roofs.append({'x_mm':x,'z_mm':z,'screw_circle_diameter_mm':3.4,
            'screw_roof_apex_z_mm':z+1.7*math.sqrt(2),
            'nut_pocket_across_flats_mm':5.7,'nut_roof_apex_z_mm':apex,
            'outer_roof_top_z_mm':top,'minimum_vertical_roof_material_mm':top-apex})
    case=g.box(sc.CASE_LENGTH,sc.CASE_WIDTH,29,(-12.5,0,-14.5))
    # Changes may not reach the fitted case or the joint datum fixtures.
    guard=g.box(sc.CASE_LENGTH+.6,sc.CASE_WIDTH,36,(-12.5,0,-14))
    added=g.cut(saddle,original_saddle)
    removed=g.cut(original_saddle,saddle)
    guard_added=g.common_volume(added,guard)
    guard_removed=g.common_volume(removed,guard)
    supplier=leg.servo_envelope()
    checks=[]
    for index,(x,z) in enumerate(sc.CLAMP_BOLT_XZ,1):
        screw=leg._hole_y(x,z,-18.135,35,radius=1.5)
        nut=actual_nut(x,z)
        checks.append({'bolt':index,'screw_saddle_intersection_mm3':g.common_volume(screw,saddle),
            'screw_cap_intersection_mm3':g.common_volume(screw,cap),
            'seated_nut_intersection_mm3':g.common_volume(nut,saddle),
            'nut_turned_10deg_intersection_mm3':g.common_volume(actual_nut(x,z,10),saddle)})
    interface=dict(case_added_mm3=guard_added,case_removed_mm3=guard_removed,
        nominal_case_intersection_mm3=g.common_volume(saddle,case),
        supplier_case_intersection_mm3=g.common_volume(saddle,supplier),
        saddle_cap_intersection_mm3=g.common_volume(saddle,cap),
        cap_changed_mm3=0.0)
    assert all(v<.001 for v in interface.values()),interface
    assert all(all(row[k]<.001 for k in ('screw_saddle_intersection_mm3',
        'screw_cap_intersection_mm3','seated_nut_intersection_mm3')) and
        row['nut_turned_10deg_intersection_mm3']>.01 for row in checks),checks
    entries=[]
    for name,shape,rotation in [('second_fit_saddle_45deg_roofs',saddle,(0,0,0)),
                               ('second_fit_matching_cap',cap,(90,0,0))]:
        assert g.valid(shape) and solid_count(shape)==1
        printed=g.transform(shape,rpy_deg=rotation)
        lo,hi=g.bounds(printed);printed=g.translate(printed,tuple(-v for v in lo))
        g.export_stl(printed,HERE/(name+'.stl'),deflection=.025)
        g.export_step(shape,HERE/(name+'.step'))
        entries.append({'name':name,'stl':name+'.stl','stl_sha256':sha(HERE/(name+'.stl')),
            'print_rotation_deg':rotation,'dimensions_mm':[hi[k]-lo[k] for k in range(3)],
            'volume_mm3':g.volume(shape),'single_valid_solid':True})
    g.export_step([saddle,cap],HERE/'second_fit_clamp_assembly.step')
    report={'status':'CAD checks pass; physical screw/nut fit pending',
        'source_manifest_sha256':sha(CAD/'output/assembly_manifest.json'),
        'source_files_sha256':{str(p):sha(p) for p in [CAD/'leg.py',CAD/'servo_contract.py',CAD/'geom.py',Path(__file__)]},
        'parts':entries,'bolt_roofs':roofs,'interface_checks':interface,'fastener_checks':checks,
        'screw_axes_unchanged':True,'case_contact_geometry_unchanged':True,
        'roof_angle_degrees_above_bed':45,'intended_saddle_orientation':'Original Z axis upright; added roofs point upward',
        'cap_orientation':'Flat with its screw bores vertical',
        'minimum_screw_circle_diameter_mm':3.4,'nut_pocket_across_flats_mm':5.7,
        'scope':'Full-size second fit trial. The released robot CAD is not modified.',
        'limits':['Nominal screw and nut clearances do not establish as-printed fit.',
            'The enlarged outer roof tabs require integration clearance checks before use on all robot joints.',
            'The case fit is operator-confirmed qualitatively; no caliper measurement or screw-fit pass was reported.',
            'Support-free intent must be checked by a fresh slice and this physical print.']}
    (HERE/'cad_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'parts':entries,'interface_checks':interface,'fastener_checks':checks}),flush=True)


if __name__=='__main__':main()
