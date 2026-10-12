"""Package the complete fourth leg, reusing verified recovery geometry."""
from pathlib import Path
import sys,json,shutil,hashlib
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'third_leg_20260916';REC=ROOT.parent/'recovery_three_parts_20260916';OUT=ROOT/'print';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(OLD));import compare_speed as c,prepare_plate as pt
sys.path.insert(0,str(ROOT.parent/'print_dfm_20260914'));import prepare_batch as pack
from check_supports import segments,rot
c.ROOT=ROOT
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads((OLD/'output/manifest.json').read_text());by={p['name']:p for p in m['parts']}
main=['coxa_upper_and_hip_saddle','femur_main_and_knee_saddle','tibia_curved_main_and_foot']
names=[n for n in by if n not in main and not n.startswith('yaw_auxiliary_spacer')];assert len(names)==7
for ext in ['stl','3mf']:shutil.copy2(REC/'print'/('Recovery_Three_Parts_With_Supports.'+ext),OUT/('01_Main_Parts_With_Supports.'+ext))
profile='Neptune4Pro_Recovery_Balanced_028.curaprofile';shutil.copy2(REC/'balanced_profile'/profile,OUT/profile)
baseline=json.loads((REC/'balanced_profile/Profile_Check.json').read_text());assert sha(OUT/'01_Main_Parts_With_Supports.stl')==baseline['plate_sha256'];assert sha(OUT/profile)==baseline['profile_sha256']
meshes={n:trimesh.load_mesh(OLD/'output'/by[n]['print_stl']) for n in names}
for n,mesh in meshes.items():assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,n
pack.GAP=16;pack.BIN=200
layout=pack.pack({n:v.extents[:2] for n,v in meshes.items()});placed=[];rows=[]
for n,mesh in meshes.items():
 x,y,w,h,turn=layout[n];t=np.eye(4);t[:3,:3]=rot([0,0,90 if turn else 0]);v=mesh.vertices@t[:3,:3].T;t[:3,3]=[x,y,0]-v.min(0);mesh.apply_transform(t);placed.append((n,mesh));rows.append({'name':n,'source_print_to_plate':t.tolist(),'source_sha256':sha(OLD/'output'/by[n]['print_stl'])})
whole=trimesh.util.concatenate([v for n,v in placed]);shift=np.r_[112.5-whole.bounds[:,:2].mean(0),0]
for (n,mesh),r in zip(placed,rows):
 mesh.apply_translation(shift);t=np.array(r['source_print_to_plate']);t[:3,3]+=shift;r['source_print_to_plate']=t.tolist()
for i,(n,a) in enumerate(placed):
 for nn,b in placed[i+1:]:assert any(a.bounds[1,k]+15.999<=b.bounds[0,k] or b.bounds[1,k]+15.999<=a.bounds[0,k] for k in (0,1))
whole=trimesh.util.concatenate([v for n,v in placed]);stl=OUT/'02_Brackets_And_Caps.stl';whole.export(stl);c.p.three_mf(stl.with_suffix('.3mf'),placed)
result=c.run('fourth_leg_brackets',stl,baseline['result']['settings'])
assert result['engine']['motion_inside_build_envelope'] and result['deposition']['unclassified_deposition_is_zero']
lo,hi=np.array(result['engine']['motion_bounds_mm']);assert min(lo[:2].min(),(225-hi[:2]).min())>2
ss=segments(ROOT/'analysis/fourth_leg_brackets.analysis_only.gcode.gz');a=np.array([(a+b)/2 for a,b,k,l in ss if k.startswith('SUPPORT')]).reshape(-1,3);a[:,2]-=.14
t=np.array(result['engine']['gcode_to_source_transform']);a=a@t[:3,:3].T+t[:3,3];checks=[]
for row in rows:
 p=by[row['name']];t=np.linalg.inv(row['source_print_to_plate']);q=a@t[:3,:3].T+t[:3,3];asm=trimesh.load_mesh(OLD/'output'/p['assembly_stl']);rotation=rot(p['print_rotation']);offset=-(asm.vertices@rotation.T).min(0);q=(q-offset)@rotation
 for tag,lo,hi,pitch in pack.regions(p):
  v=(q-pitch[:3,3])@pitch[:3,:3];count=int(np.all((v>lo)&(v<hi),axis=1).sum());checks.append({'part':p['name'],'opening':tag,'support_midpoints_inside':count});assert count==0,(p['name'],tag,count)
fig,ax=plt.subplots(figsize=(8,9));legend=[]
for i,(n,mesh) in enumerate(placed,1):
 ax.add_collection(PolyCollection(mesh.triangles[:,:,:2],facecolors=['#63a9c6','#96b96b','#dca466'][i%3],edgecolors='none',alpha=.35));ax.text(*mesh.bounds[:,:2].mean(0),str(i),ha='center',va='center',bbox={'facecolor':'white','edgecolor':'none'});legend.append(str(i)+'. '+n.replace('_',' '))
ax.set_xlim(0,225);ax.set_ylim(0,225);ax.set_aspect('equal');ax.set_title('Plate 2: seven brackets and caps');ax.set_xlabel('Bed X, mm');ax.set_ylabel('Bed Y, mm');fig.text(.14,.02,'\n'.join(legend),fontsize=10);fig.subplots_adjust(bottom=.23);fig.savefig(OUT/'Plate_2_Map.png',dpi=140);plt.close(fig)
for name in ['Support_Map.png','Femur_Upper_Lip_Support.png']:shutil.copy2(REC/'print'/name,OUT/name)
report={'printed_parts':10,'reuse':'Four existing 13 mm tall, 5.5 mm OD spacers; user has sufficient quantity.',
 'plate_1':{'parts':main,'sha256':sha(OUT/'01_Main_Parts_With_Supports.stl'),'estimate_seconds':baseline['after_seconds'],'mass_g':baseline['result']['deposition']['total_deposited_mass_g'],'evidence':'Exact recovery plate and balanced profile bytes reused. No repeat slicing needed.'},
 'plate_2':{'parts':rows,'sha256':sha(stl),'result':result,'support_opening_checks':checks},
 'profile_sha256':sha(OUT/profile),'limits':'Physical outcome of the latest balanced recovery print has not been reported. No new load or adhesion qualification.'}
(OUT/'Fourth_Leg_Check.json').write_text(json.dumps(report,indent=2));print('COMPLETE',flush=True)
