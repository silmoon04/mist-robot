"""Dense hinge sweeps through sampled transverse sections of actual meshes."""
from pathlib import Path
import json,math,hashlib
import numpy as np
import trimesh
from shapely.geometry import Polygon,GeometryCollection
from shapely.ops import unary_union
from shapely.affinity import affine_transform
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
PLANES=[-26.75,-24.5,-22.25,-21.8,-20,-18,-17.75,-15,-12,-6,0,.6,6,12,15.2,17.8,19.25,22.75]

def cut(mesh,y):
    sec=mesh.section(plane_origin=[0,y,0],plane_normal=[0,1,0])
    result=GeometryCollection()
    if sec is None:return result
    for path in sec.discrete:
        if len(path)<4 or np.linalg.norm(path[0]-path[-1])>1e-5:continue
        polygon=Polygon(path[:,[0,2]])
        if not polygon.is_valid:polygon=polygon.buffer(0)
        result=result.symmetric_difference(polygon)
    return result

def main():
    manifest=json.loads((OUT/'manifest.json').read_text());meshes=[]
    for p in manifest['parts']:
        if p['material']=='metal':continue
        meshes.append((p,trimesh.load_mesh(OUT/p['assembly_stl'])))
    results=[]
    for joint,angles,origin in [('hip',range(-35,71),82),('knee',range(0,121),90)]:
        parents=[];children=[]
        for p,m in meshes:
            if joint=='hip':
                if p['link'] in ('base_mount','coxa'):parents.append(m)
                else:
                    child=m.copy()
                    if p['link']=='tibia':
                        a=math.radians(81);t=np.eye(4);t[:3,:3]=[[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]];t[0,3]=90;child.apply_transform(t)
                    children.append(child)
            else:
                if p['link']=='femur':parents.append(m)
                if p['link']=='tibia':children.append(m)
        for y in PLANES:
            fixed=unary_union([cut(m,y) for m in parents]);moving=unary_union([cut(m,y) for m in children]);hits=[];maximum=0
            for deg in angles:
                a=math.radians(deg);c,s=math.cos(a),math.sin(a)
                area=fixed.intersection(affine_transform(moving,[c,s,-s,c,origin,0])).area
                maximum=max(maximum,area)
                if area>.05:hits.append({'angle_deg':deg,'overlap_mm2':area})
            results.append({'joint':joint,'y_plane_mm':y,'angle_samples':len(angles),'maximum_overlap_mm2':maximum,'failures':hits})
            print(joint,y,'hits',len(hits),'max',round(maximum,6),flush=True)
    report={'status':'pass' if not any(r['failures'] for r in results) else 'fail',
        'manifest_sha256':hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest(),'rows':results,
        'scope':'One-degree hinge sweeps at 18 transverse section planes, using actual printed-part and servo-envelope meshes. Hip sweep keeps knee at 81 degrees; knee sweep uses its parent frame. Metal sliding interfaces are excluded from this mesh approximation and included in the separate exact solid check. This supplements the 3D checks; it is not a continuous 3D collision proof.'}
    (OUT/'pitch_section_sweep.json').write_text(json.dumps(report,indent=2));print(report['status'])

if __name__=='__main__':main()
