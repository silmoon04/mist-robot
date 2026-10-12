"""Local leg solid and contact checks; excludes unmeasured wiring geometry."""
import math
from pathlib import Path
import tempfile
import itertools
import trimesh
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from leg import build_leg
from geom import bounds, common_volume, rotate, translate, export_stl


def transformed(parts, hip=25, knee=60, yaw=0):
    result=[]
    a=math.radians(hip)
    for p in parts:
        s=p['shape']
        if p['link']=='femur':
            s=translate(rotate(s,(0,1,0),hip),(50,0,0))
        elif p['link']=='tibia':
            s=translate(rotate(s,(0,1,0),hip+knee),(50+90*math.cos(a),0,-90*math.sin(a)))
        if p['link']!='base_mount': s=rotate(s,(0,0,1),yaw)
        result.append({**p,'shape':s,'bbox':bounds(s)})
    return result


def overlaps(parts, min_volume=0.01, different_link_only=False):
    hits=[]
    for a,b in itertools.combinations(parts,2):
        if different_link_only and a['link']==b['link']: continue
        if any(a['bbox'][0][k]>=b['bbox'][1][k]-1e-7 or b['bbox'][0][k]>=a['bbox'][1][k]-1e-7 for k in range(3)): continue
        v=common_volume(a['shape'],b['shape'])
        if v>min_volume: hits.append((a['name'],b['name'],round(v,3)))
    return hits


if __name__=='__main__':
    parts=build_leg()
    failures=[]
    with tempfile.TemporaryDirectory(prefix='leg_mesh_check_') as tmp:
        for p in parts:
            if not p['printable']:continue
            ex=TopExp_Explorer(p['shape'],TopAbs_SOLID); n=0
            while ex.More():n+=1;ex.Next()
            path=Path(tmp)/(p['name']+'.stl')
            export_stl(p['shape'],path)
            mesh=trimesh.load_mesh(path)
            parent=list(range(len(mesh.faces)))
            def find(v):
                while parent[v]!=v:
                    parent[v]=parent[parent[v]];v=parent[v]
                return v
            for i,j in mesh.face_adjacency:parent[find(int(i))]=find(int(j))
            components=len({find(i) for i in range(len(parent))})
            print('MESH',p['name'],'solids',n,'components',components,'watertight',mesh.is_watertight,flush=True)
            if n!=1 or components!=1 or not mesh.is_watertight:
                failures.append(('mesh',p['name']))
    hits=overlaps(transformed(parts))
    print('NEUTRAL',hits,flush=True)
    failures.extend(hits)
    for hip,knee in ((3.35,30.46),(8.55,51.83),(25,76),(30,75),(29.01,87.69),(35,100),(10,45)):
        hits=overlaps(transformed(parts,hip,knee),different_link_only=True)
        print('POSE',hip,knee,hits,flush=True)
        failures.extend(hits)
    for yaw in (-25,25):
        hits=overlaps(transformed(parts,yaw=yaw),different_link_only=True)
        print('YAW',yaw,hits,flush=True)
        failures.extend(hits)
    if failures: raise SystemExit(1)
