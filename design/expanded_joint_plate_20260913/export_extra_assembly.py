"""Check and export the extra lower-yaw support stack in assembly coordinates."""
from pathlib import Path
import json
import sys
HERE=Path(__file__).resolve().parent
CAD=HERE.parent/'hexapod_phone_quad_r5_20260912/cad'
sys.path.insert(0,str(CAD))
import geom as g
import leg


def ring(outer,inner,height,base=(0,0,0)):
    return g.translate(g.cut(g.cylinder(outer,height),g.cylinder(inner,height+2,(0,0,-1))),base)


def main():
    assets=HERE/'diagram_assets';assets.mkdir(exist_ok=True)
    arm=g.import_step(CAD/'output/parts_step/coxa_lower_auxiliary_arm.step')
    yaw_spacer=ring(2.9,1.7,11.6)
    pan_spacer=g.import_step(CAD/'output/parts_step/pan_cover_spacer_1.step')
    lo,hi=g.bounds(pan_spacer);pan_spacer=g.translate(pan_spacer,(-(lo[0]+hi[0])/2,-(lo[1]+hi[1])/2,-lo[2]))
    screw20=g.cut(g.fuse(g.cylinder(1.5,20,(0,0,-20)),g.cylinder(2.75,3)),leg._hex_z(0,0,.8,3,2.5))
    shapes={'lower_arm':arm,'yaw_spacer':yaw_spacer,'pan_spacer':pan_spacer,'screw20':screw20}
    for name,shape in shapes.items():g.export_stl(shape,assets/(name+'.stl'),.04)
    previous=HERE.parent/'second_fit_supportfree_20260913'
    items=[('existing_saddle',g.import_step(previous/'second_fit_saddle_45deg_roofs.step')),
           ('existing_cap',leg.case_clamp(True,.3)[1]),('servo',leg.servo_envelope()),
           ('aux_disc',leg.auxiliary_disc()),('lower_arm',arm)]
    for i,(x,y) in enumerate(((7,0),(-7,0),(0,7),(0,-7)),1):
        items.append((f'11p6_spacer_{i}',g.translate(yaw_spacer,(x,y,-44))))
    rows=[]
    for i,(name,shape) in enumerate(items):
        for other,second in items[i+1:]:
            v=g.common_volume(shape,second)
            rows.append({'a':name,'b':other,'intersection_mm3':v})
            assert v<.01,(name,other,v)
    path=HERE/'expanded_plate_validation.json';d=json.loads(path.read_text())
    d['extra_lower_stack_check']={'passed':True,'pairs':rows,
        'scope':'Existing clamp, nominal servo exterior, supplied auxiliary disc, four nominal spacers and lower arm at the shown assembly position. Threads and physical fit remain unverified.'}
    path.write_text(json.dumps(d,indent=2),encoding='utf-8')
    print('Checked '+str(len(rows))+' lower-stack part pairs without positive intersections.')


if __name__=='__main__':main()
