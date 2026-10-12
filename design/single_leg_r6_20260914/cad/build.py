"""Build one complete R6 leg with actual part frames and a bench mounting plate."""
from pathlib import Path
import hashlib,json,math,csv
import numpy as np
import geom as g
import leg

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'output'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pose(xyz=(0,0,0),rpy=(0,0,0)):
    x,y,z=np.radians(rpy);cx,sx=np.cos(x),np.sin(x);cy,sy=np.cos(y),np.sin(y);cz,sz=np.cos(z),np.sin(z)
    rx=np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]]);ry=np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]]);rz=np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
    t=np.eye(4);t[:3,:3]=rz@ry@rx;t[:3,3]=xyz;return t


def shape_at(shape,m):
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    t=gp_Trsf();t.SetValues(*[float(m[i,j]) for i in range(3) for j in range(4)])
    return BRepBuilderAPI_Transform(shape,t,True).Shape()


def mounting_plate():
    p=g.prism_xy([(-110,-39),(-105,-44),(13,-44),(18,-39),(18,39),(13,44),(-105,44),(-110,39)],-39,7)
    p=g.cut(p,g.box(60,29,12,(-15,0,-35)),g.cylinder(15,12,(0,0,-41)))
    p=g.cut(p,g.prism_xy([(-83,-22),(-47,-22),(-45,-20),(-45,20),(-47,22),(-83,22),(-85,20),(-85,-20)],-41,12))
    for x,y in leg.CONSTANTS['mount_holes_xy']:p=g.cut(p,g.cylinder(1.8,12,(x,y,-41)))
    for x in (-95,-65):
        for y in (-34,34):p=g.cut(p,g.cylinder(3.2,12,(x,y,-41)))
    outside=g.cut(g.box(120,130,20,(60,0,-35)),g.cylinder(30,30,(0,0,-50)))
    p=g.cut(p,outside)
    return p


def load_assembly(yaw=0,hip=30,knee=81):
    parts=leg.build_leg()
    parts.append({'name':'bench_mounting_plate','shape':mounting_plate(),'link':'base_mount','material':'pla','printable':True,'print_rotation':(0,0,0)})
    frames={'base_mount':np.eye(4),'coxa':pose(rpy=(0,0,yaw))}
    frames['femur']=frames['coxa']@pose((82,0,0),(0,hip,0))
    frames['tibia']=frames['femur']@pose((90,0,0),(0,knee,0))
    return parts,frames


def intersections(parts,frames):
    shapes=[shape_at(p['shape'],frames[p['link']]) for p in parts];boxes=[g.bounds(s) for s in shapes]
    pairs=0;hits=[]
    for i,p in enumerate(parts):
        for j in range(i+1,len(parts)):
            a,b=boxes[i],boxes[j]
            if any(a[1][k]<=b[0][k]+1e-5 or b[1][k]<=a[0][k]+1e-5 for k in range(3)):continue
            pairs+=1;v=g.common_volume(shapes[i],shapes[j])
            if v>.01:hits.append({'a':p['name'],'b':parts[j]['name'],'mm3':v})
    return {'boolean_pairs':pairs,'intersections':hits}


def main():
    OUT.mkdir(exist_ok=True)
    for name in ['print_stl','parts_step','assembly_mesh','links']:(OUT/name).mkdir(exist_ok=True)
    parts,frames=load_assembly();static=intersections(parts,frames)
    print(json.dumps(static),flush=True)
    if static['intersections']:
        (OUT/'static_check.json').write_text(json.dumps(static,indent=2));raise RuntimeError('Resolve static intersections before exporting')
    records=[]
    for p in parts:
        assert g.valid(p['shape'])
        name=p['name'];shape=p['shape']
        g.export_stl(shape,OUT/'assembly_mesh'/(name+'.stl'),.04)
        mass=p.get('mass_kg',.055 if p['material']=='servo' else g.volume(shape)*(.0000027 if p['material']=='metal' else .00000124))
        entry={'name':name,'link':p['link'],'printable':p['printable'],'material':p['material'],
            'solid_mass_kg':mass,'volume_mm3':g.volume(shape),'com_mm':g.centroid(shape),
            'assembly_stl':'assembly_mesh/'+name+'.stl','transform':frames[p['link']].tolist()}
        if p['printable']:
            rot=p.get('print_rotation',(0,0,0))
            if name=='coxa_lower_auxiliary_arm':rot=(180,0,0)
            oriented=g.transform(shape,rpy_deg=rot);lo,hi=g.bounds(oriented)
            oriented=g.translate(oriented,tuple(-v for v in lo))
            stl=OUT/'print_stl'/(name+'.stl');g.export_stl(oriented,stl,.04)
            g.export_step(shape,OUT/'parts_step'/(name+'.step'))
            entry.update(print_rotation=rot,dimensions_mm=[hi[k]-lo[k] for k in range(3)],
                print_stl='print_stl/'+name+'.stl',stl_sha256=sha(stl))
        records.append(entry)
    for link in frames:
        shapes=[p['shape'] for p in parts if p['link']==link]
        g.export_step(shapes,OUT/'links'/(link+'.step'))
    g.export_step([shape_at(p['shape'],frames[p['link']]) for p in parts],OUT/'Single_Leg_R6_Assembly.step')
    sources={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')}
    manifest={'revision':'single_leg_r6_20260914','units':'mm','parts':records,
        'frames':{k:v.tolist() for k,v in frames.items()},'source_hashes':sources,
        'static_check':static,'lengths_mm':[82,90,105],'neutral_deg':[0,30,81],
        'nut_pocket_AF_mm':5.6,'nut_entry_thickness_mm':2.7,
        'scope':'One complete three-servo leg and bench mounting plate, physical qualification pending.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    with (OUT/'print_bom.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['part','quantity','file','dimensions_mm'])
        w.writerows((p['name'],1,p['print_stl'],p['dimensions_mm']) for p in records if p['printable'])
    print(json.dumps({'parts':len(parts),'print_parts':sum(p['printable'] for p in parts),'manifest_sha256':sha(OUT/'manifest.json')}),flush=True)


if __name__=='__main__':main()
