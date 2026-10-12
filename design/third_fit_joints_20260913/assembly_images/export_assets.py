"""Export actual assembly-coordinate parts for the instruction images."""
from pathlib import Path
import hashlib
import sys
HERE=Path(__file__).resolve().parent
THIRD=HERE.parent
CAD=THIRD.parent/'hexapod_phone_quad_r5_20260912/cad'
sys.path.insert(0,str(CAD));sys.path.insert(0,str(THIRD))
import geom as g
import leg
import build_joint_plate as trial


def ring(outer,inner,height):
    return g.cut(g.cylinder(outer,height),g.cylinder(inner,height+2,(0,0,-1)))


def screw(length):
    return g.cut(g.fuse(g.cylinder(1.5,length,(0,0,-length)),g.cylinder(2.75,3)),
                 leg._hex_z(0,0,.8,3,2.5))


def main():
    out=HERE/'assets';out.mkdir(parents=True,exist_ok=True)
    _,gauge,parts=trial.parts()
    assets={'saddle':g.import_step(THIRD.parent/'second_fit_supportfree_20260913/second_fit_saddle_45deg_roofs.step'),
        'cap':leg.case_clamp(True,.3)[1],'servo':leg.servo_envelope(),
        'main_horn':leg.main_horn(),'aux_disc':leg.auxiliary_disc(),'gauge':gauge,
        'gauge_spacer':ring(4,1.7,5),'washer6':ring(3,1.6,.5),'washer7':ring(3.5,1.6,.5),
        'nut':g.cut(leg._hex_z(0,0,0,2.4,5.5),g.cylinder(1.6,4,(0,0,-.5)))}
    for key,name in [('main_cheek','02_main_horn_cheek'),('aux_cheek','03_auxiliary_horn_cheek'),('bridge','04_horn_bridge_38_roofed')]:
        assets[key]=next(p['shape'] for p in parts if p['name']==name)
    for length in (5,6,8,50):assets['screw'+str(length)]=screw(length)
    lines=[]
    for name,shape in assets.items():
        path=out/(name+'.stl');g.export_stl(shape,path,.04)
        lines.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  assets/'+path.name)
    for path in [THIRD/'build_joint_plate.py',THIRD/'PRINT_NEXT.txt',CAD/'leg.py',CAD/'servo_contract.py']:
        lines.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  SOURCE '+str(path))
    (HERE/'SOURCE_HASHES.sha256').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Exported '+str(len(assets))+' assembly-coordinate assets. Fasteners are schematic unthreaded envelopes.')


if __name__=='__main__':main()
