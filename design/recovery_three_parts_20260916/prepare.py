from pathlib import Path
import sys,json,hashlib,concurrent.futures
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'third_leg_20260916';OUT=ROOT/'print';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(OLD));import compare_speed as c,prepare_plate as p
c.ROOT=ROOT;p.OUT=OUT
names=['coxa_upper_and_hip_saddle','femur_main_and_knee_saddle','tibia_curved_main_and_foot']
manifest=json.loads((OLD/'output/manifest.json').read_text());by={p['name']:p for p in manifest['parts']}
placed=[];rows=[];y=0
for name in names:
 model=trimesh.load_mesh(OLD/'output/print_stl'/(name+'.stl'));support=trimesh.load_mesh(ROOT/'supports'/(name+'.stl'))
 both=trimesh.util.concatenate([model,support]);shift=np.array([0,y,0])-both.bounds[0];shift[2]=0
 for m in (model,support):m.apply_translation(shift)
 placed.extend([(name,model),('REMOVE_support_'+name,support)])
 rows.append({'name':name,'translation':shift.tolist(),'source_sha256':p.sha(OLD/'output/print_stl'/(name+'.stl'))})
 y=max(model.bounds[1,1],support.bounds[1,1])+20
whole=trimesh.util.concatenate([m for n,m in placed]);shift=np.r_[112.5-whole.bounds[:,:2].mean(0),0]
for n,m in placed:m.apply_translation(shift)
for r in rows:r['translation']=(np.array(r['translation'])+shift).tolist()
whole=trimesh.util.concatenate([m for n,m in placed]);stl=OUT/'Recovery_Three_Parts_With_Supports.stl';whole.export(stl);c.p.three_mf(stl.with_suffix('.3mf'),placed)
s=c.settings(False);s.update(adhesion_type='brim',brim_width=6,brim_line_count=15,brim_gap=.1,brim_location='outside',
 support_brim_enable=True,support_brim_width=4,support_brim_line_count=10,
 speed_print=60,speed_wall=45,speed_wall_0=35,speed_wall_x=60,speed_infill=60,speed_topbottom=35,
 speed_travel=120,speed_layer_0=20,speed_print_layer_0=20,speed_travel_layer_0=40,skirt_brim_speed=20,
 acceleration_print=1500,acceleration_wall=1000,acceleration_wall_0=800,acceleration_wall_x=1200,
 acceleration_infill=1500,acceleration_support=1000,acceleration_support_infill=1000,acceleration_travel=1800,
 acceleration_layer_0=300,acceleration_print_layer_0=300,acceleration_travel_layer_0=500,acceleration_skirt_brim=300,
 cool_fan_full_layer=6,cool_fan_full_at_height=1.68,cool_min_layer_time=15)
profile=p.profile(s,'Neptune4Pro_Recovery_Three_Parts_028')
limits=dict(machine_max_acceleration_x=20000,machine_max_acceleration_y=20000,machine_max_acceleration_e=5000,machine_acceleration=5000)
result=c.run('recovery_three',stl,dict(s,**limits))
assert result['engine']['motion_inside_build_envelope'] and result['deposition']['unclassified_deposition_is_zero']
lo,hi=np.array(result['engine']['motion_bounds_mm']);assert min(lo[:2].min(),(225-hi[:2]).min())>2
fig=plt.figure(figsize=(13,6),facecolor='#fafaf7')
for i,name in enumerate(names):
 ax=fig.add_subplot(1,3,i+1,projection='3d');ax.set_facecolor('#fafaf7')
 a=trimesh.load_mesh(OLD/'output/print_stl'/(name+'.stl'));b=trimesh.load_mesh(ROOT/'supports'/(name+'.stl'))
 for m,col in [(a,'#76bed2'),(b,'#f4a044')]:
  ax.add_collection3d(Poly3DCollection(m.triangles,facecolors=col,edgecolors='#527078',linewidths=.05,shade=True))
 total=trimesh.util.concatenate([a,b]);lo,hi=total.bounds;ax.set_xlim(lo[0]-2,hi[0]+2);ax.set_ylim(lo[1]-2,hi[1]+2);ax.set_zlim(0,hi[2]+3);ax.set_box_aspect(hi-lo+[4,4,3]);ax.view_init(20,-60);ax.set_axis_off()
 ax.set_title(['Coxa and hip saddle','Femur and knee saddle','Tibia and foot'][i],fontsize=12)
fig.suptitle('Recovery print: blue stays, orange supports are removed',fontsize=16)
fig.text(.5,.12,'Femur support now reaches the upper lip as well as the lower saddle.\nCura adds the outer brim and any remaining tree support.',ha='center',fontsize=12)
fig.subplots_adjust(left=0,right=1,bottom=.15,top=.85,wspace=0);fig.savefig(OUT/'Support_Map.png',dpi=150);plt.close(fig)
report={'status':'sliced; physical recovery print pending','part_count':3,'parts':rows,'plate_sha256':p.sha(stl),'profile_file':profile,'profile_sha256':p.sha(OUT/profile),'result':result,
 'scope':'Only the three failed parts. All main part STL hashes match the previous insert-compatible revision. Added support geometry is removable.',
 'limits':'Adhesion and support release require physical confirmation. Earlier no-brim fast process failed for these parts.'}
(OUT/'Print_Check.json').write_text(json.dumps(report,indent=2));print('DONE',flush=True)
