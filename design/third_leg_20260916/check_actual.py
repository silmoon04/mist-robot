"""Inspect sliced support in the fastener openings and the saddle support gap."""
from pathlib import Path
import json,sys
import numpy as np
import trimesh
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'print_dfm_20260914'))
from prepare_batch import regions
from check_supports import segments,rot
manifest=json.loads((ROOT/'output/manifest.json').read_text());by={p['name']:p for p in manifest['parts']}
report=json.loads((ROOT/'print/Print_Check.json').read_text());checks=[]
for name in ['third_leg_fast','third_leg_familiar']:
    result=json.loads((ROOT/'analysis'/(name+'.json')).read_text());ss=segments(ROOT/'analysis'/(name+'.analysis_only.gcode.gz'))
    a=np.array([(a+b)/2 for a,b,kind,layer in ss if kind.startswith('SUPPORT')]).reshape(-1,3)
    a[:,2]-=result['settings']['layer_height']/2
    inv=np.array(result['engine']['gcode_to_source_transform']);a=a@inv[:3,:3].T+inv[:3,3]
    opening_checks=[]
    for row in report['parts']:
        p=by[row['name']];inv=np.linalg.inv(np.array(row['source_print_to_plate']));q=a@inv[:3,:3].T+inv[:3,3]
        asm=trimesh.load_mesh(ROOT/'output'/p['assembly_stl']);r=rot(p['print_rotation']);pr=trimesh.load_mesh(ROOT/'output'/p['print_stl'])
        offset=pr.bounds[0]-(asm.vertices@r.T).min(0);q=(q-offset)@r
        for tag,lo,hi,pitch in regions(p):
            local=(q-pitch[:3,3])@pitch[:3,:3];mask=np.all((local>lo)&(local<hi),axis=1)
            if tag.startswith('post nut entry'):mask&=((local[:,0]-43.085)**2+(local[:,1]+13)**2>=16)
            opening_checks.append({'part':p['name'],'opening':tag,'support_midpoints_inside':int(mask.sum())})
        bridges=[(65,20.5)] if p['name']=='femur_main_and_knee_saddle' else [(36,0),(44,0)] if p['name']=='tibia_curved_main_and_foot' else []
        for x,z in bridges:
            mask=((q[:,0]-x)**2+(q[:,2]-z)**2<1.5**2)&(q[:,1]>-22)&(q[:,1]<-16.4)
            opening_checks.append({'part':p['name'],'opening':'insert '+str(x),'support_midpoints_inside':int(mask.sum())})
    checks.append({'slice':name,'openings':opening_checks})
    bad=[c for c in opening_checks if c['support_midpoints_inside']]
    print(name,'intrusions',bad,flush=True)
    assert not bad,bad
plan=json.loads((ROOT/'support_plan.json').read_text());coverage=[]
model=trimesh.load_mesh(ROOT/'output/print_stl'/(plan['part']+'.stl'))
lower=model.slice_plane([0,0,plan['support_top_z_mm']+.2],[0,0,-1])
existing=unary_union([Polygon(t[:,:2]) for t in lower.triangles if Polygon(t[:,:2]).area>1e-6])
for row in plan['combs']:
    base=Polygon(row['base'],row['base_holes']);fins=unary_union([existing,*[Polygon(x) for x in row['fins']]]);distances=[]
    lo=base.bounds
    for x in np.arange(lo[0],lo[2],.3):
        for y in np.arange(lo[1],lo[3],.3):
            point=Point(x,y)
            if base.contains(point):distances.append(point.distance(fins))
    maximum=max(distances);assert maximum<3
    coverage.append({'maximum_sampled_horizontal_distance_to_comb_or_model_below_mm':maximum,'sampling_pitch_mm':.3})
out={'status':'pass','support_opening_checks':checks,'comb_coverage':coverage,
     'limits':'Support centreline midpoint sampling and geometric comb spacing do not prove breakaway force or actual bridge quality. No physical insert pullout test has been completed.'}
(ROOT/'print/Support_Check.json').write_text(json.dumps(out,indent=2));print('CHECK_OK',flush=True)
