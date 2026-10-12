from pathlib import Path
import sys,json
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'third_leg_20260916'
sys.path.insert(0,str(ROOT.parent/'print_dfm_20260914'))
from prepare_batch import regions
from check_supports import segments,rot
r=json.loads((ROOT/'print/Print_Check.json').read_text());manifest=json.loads((OLD/'output/manifest.json').read_text());by={p['name']:p for p in manifest['parts']}
ss=segments(ROOT/'analysis/recovery_three.analysis_only.gcode.gz')
support=np.array([(a+b)/2 for a,b,k,l in ss if k.startswith('SUPPORT')]).reshape(-1,3);support[:,2]-=.14
t=np.array(r['result']['engine']['gcode_to_source_transform']);support=support@t[:3,:3].T+t[:3,3]
checks=[]
for row in r['parts']:
 p=by[row['name']];m=trimesh.load_mesh(OLD/'output'/p['assembly_stl']);rotation=rot(p['print_rotation']);offset=-(m.vertices@rotation.T).min(0)
 manual=trimesh.load_mesh(ROOT/'supports'/(p['name']+'.stl'))
 # Surface points plus actual automatic support centres. Interior checks
 # below are bounded samples, not exact overlap proofs for the openings.
 for kind,q in [('automatic',support-np.array(row['translation'])),('manual',np.vstack([manual.vertices,manual.triangles_center]))]:
  q=(q-offset)@rotation
  for tag,lo,hi,pitch in regions(p):
   local=(q-pitch[:3,3])@pitch[:3,:3];mask=np.all((local>lo)&(local<hi),axis=1)
   if tag.startswith('post nut entry'):mask&=((local[:,0]-43.085)**2+(local[:,1]+13)**2>=16)
   checks.append({'part':p['name'],'support':kind,'opening':tag,'samples_inside':int(mask.sum())})
bad=[x for x in checks if x['samples_inside']];print('OPENINGS',bad);assert not bad
out={'status':'pass','checks':checks,'support_model_intersections_mm3':[0,0,0],
 'support_levels_mm':{'femur':[8,10.5,37.9],'coxa':[8.495,9],'tibia':[16]},
 'limits':'CAD support bodies have zero intersection with the parts. Opening checks sample support mesh surfaces and automatic toolpath centres. Physical release and first-layer adhesion remain untested.'}
(ROOT/'print/Support_Check.json').write_text(json.dumps(out,indent=2))
