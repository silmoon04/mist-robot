"""Audit surviving MIST sources; never rewrite the source geometry."""
from pathlib import Path
import csv, hashlib, json, math
from collections import Counter, defaultdict
import numpy as np
from scipy.spatial.distance import cdist

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
SOURCE=ROOT/'brain/face_assets'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data): (OUT/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def csvwrite(name,rows):
 if not rows:return
 with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def slots(face):
 for role,entry in face['slots'].items():
  for i,s in enumerate(entry if isinstance(entry,list) else [entry]):
   yield role+str(i) if isinstance(entry,list) else role,s

def align(a,b):
 # Dense arclength sampling avoids confusing different point spacing with different contours.
 def sample(p):
  q=np.array(p['points'],float)
  if p['kind']=='fill':q=np.vstack([q,q[:1]])
  t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
  keep=np.r_[True,np.diff(t)>1e-10];q=q[keep];t=t[keep]
  tnew=np.linspace(0,t[-1],96,endpoint=p['kind']!='fill')
  return np.stack([np.interp(tnew,t,q[:,i]) for i in range(2)],axis=1)
 x,y=sample(a),sample(b);x-=x.mean(0);y-=y.mean(0)
 best=None
 for mirror in (False,True):
  xm=x*np.array([-1 if mirror else 1,1])
  for reverse in (False,True):
   z=y[::-1] if reverse else y
   for shift in range(0,96,4) if a['kind']=='fill' else [0]:
    z1=np.roll(z,shift,axis=0)
    u,_,vt=np.linalg.svd(xm.T@z1);fix=np.diag([1,np.linalg.det(u@vt)]);r=u@fix@vt
    xx=xm@r;dist=cdist(xx,y);error=max(dist.min(0).max(),dist.min(1).max())
    if best is None or error<best['max_distance']:
     best={'max_distance':float(error),'rms':float(np.sqrt(np.mean((xx-z1)**2))), 'mirror':mirror,'rotation':float(math.degrees(math.atan2(r[0,1],r[0,0])))}
 return {k:round(v,5) if isinstance(v,float) else v for k,v in best.items()}

def main():
 OUT.mkdir(exist_ok=True)
 raw=(SOURCE/'app/app_data.js').read_text(encoding='utf-8');data=json.loads(raw[raw.index('{'):].rstrip(';\n '))
 base=read(SOURCE/'parts_library.json');uses=defaultdict(list);instances=[]
 for f in data['faces']:
  for role,s in slots(f):
   row={'face':f['id'],'role':role,**s};uses[s['part']].append(row);instances.append(row)
 groups=[]
 for pid,p in base.items():
  roles={u['role'] for u in uses[pid]};kind='eyes' if any(r.startswith('eye') for r in roles) else 'mouths' if 'mouth' in roles else 'accents'
  groups.append({'id':pid,'kind':kind,'family':p['family'],'uses':uses[pid],'face_count':len({u['face'] for u in uses[pid]}),'instance_count':len(uses[pid]),'blink':data['blinks'].get(pid),'width':p['width'],'mode':p['kind'],'geometry_sha256':hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()})
 candidates=[];extra_exact=[]
 for i,a in enumerate(groups):
  for b in groups[i+1:]:
   if a['kind']!=b['kind'] or a['mode']!=b['mode']:continue
   metric=align(base[a['id']],base[b['id']])
   width_diff=abs(a['width']-b['width']);exact=metric['max_distance']<=.000001 and width_diff<=.000001
   if exact:extra_exact.append([a['id'],b['id']])
   if a['family']==b['family'] or metric['max_distance']<.35:
    candidates.append({'a':a['id'],'b':b['id'],**metric,'stroke_difference':round(width_diff,4),'exact':exact,'same_family':a['family']==b['family']})
 candidates.sort(key=lambda c:c['max_distance']+c['stroke_difference']/2)
 archive=ROOT/'design/mist_v2_20260906/brain_v2_20260907/faces'
 anim=read(archive/'animation_frames.json');layer_rows=[];frame_hashes=[]
 for i,f in enumerate(anim['frames']):
  frame_hashes.append(hashlib.sha256(json.dumps(f['layers'],sort_keys=True).encode()).hexdigest())
  for j,l in enumerate(f['layers']):
   xy=np.array(l['points']);role=l['role']
   side=('left' if xy[:,0].mean()<50 else 'right') if role=='eyes' else role
   layer_rows.append({'frame':i,'label':f['label'],'expression':f['expression'],'duration_ms':f['durationMs'],'layer':j,'role':role,'side_by_centroid':side,'part':l['part'],'geometry_sha256':hashlib.sha256(json.dumps(l,sort_keys=True).encode()).hexdigest()})
 plan=read(OUT.parent/'plan.json');active={c['id'] for c in plan['clips']};dirs=[p for p in (OUT.parent/'frame_assets').iterdir() if p.is_dir()]
 studio_clips=[]
 for folder in sorted(dirs):
  svgs=sorted(folder.glob('*.svg'));pngs=sorted(folder.glob('*.png'))
  studio_clips.append({'clip':folder.name,'status':'active existing-source export' if folder.name in active else 'retired concept; excluded from reusable source','svg_frames':len(svgs),'png_frames':len(pngs)})
 inventory=[]
 for parent in [SOURCE,ROOT/'brain/art_direction',archive,ROOT/'brain/duplex/static',ROOT/'brain/ui/static']:
  for p in sorted(parent.rglob('*')):
   if not p.is_file() or OUT in p.parents or '__pycache__' in p.parts or p.suffix.lower() not in {'.json','.js','.cjs','.svg','.png','.gif','.aseprite','.zip','.html'}:continue
   inventory.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)})
 eye=[g for g in groups if g['kind']=='eyes'];mouth=[g for g in groups if g['kind']=='mouths'];nb=len(data['blinks']);nonblink=len(eye)-nb
 counts={'faces':len(data['faces']),'placed_parts':len(instances),'base_parts':len(groups),'eye_parts':len(eye),'mouth_parts':len(mouth),'accent_parts':len(groups)-len(eye)-len(mouth),'eye_families':len({g['family'] for g in eye}),'mouth_families':len({g['family'] for g in mouth}),'blink_variants':nb,'speech_shapes':len(data['visemes']),'additional_exact_pairs':len(extra_exact),'core_painted_drawings':len(groups)+2*nb+len(data['visemes']),'full_painted_drawings':len(groups)+2*nb+len(data['visemes'])+2*nonblink+len(mouth),'existing_archive_frames':len(anim['frames']),'existing_archive_tags':len(anim['tags']),'existing_archive_seconds':sum(f['durationMs'] for f in anim['frames'])/1000,'archive_exact_unique_frame_layers':len(set(frame_hashes)),'active_studio_frames':sum(c['svg_frames'] for c in studio_clips if c['clip'] in active),'retired_studio_frames':sum(c['svg_frames'] for c in studio_clips if c['clip'] not in active)}
 runtime_extra=sorted({s['part'] for f in data['faces'] for r,s in slots(f) if r.startswith('eye') and not s.get('open') and base[s['part']]['family'].startswith(('open_C','e_shape'))})
 audit={'counts':counts,'groups':groups,'faces':data['faces'],'candidates':candidates,'additional_exact_pairs':extra_exact,'archive_tags':anim['tags'],'studio_clips':studio_clips,'runtime_blink_override_parts':runtime_extra,'method':{'source':'Surviving canonical vector geometry. Original capture screenshots are missing.','exact':'Same canonical part ID, independent of role, translation, rotation and mirroring. Separate IDs only merge at 0.000001 logical units with equal stroke widths. No extra IDs are merged automatically.','similar':'Rigid alignment with reflection, no scaling; sampled symmetric contour distance and stroke-width difference. Candidate metrics support visual review; family labels do not prove identity.','units':'100 x 64 logical face coordinates. At 800 x 512, multiply distances by 8.','scope':'All 40 canonical faces, 450 archived geometry frames, every studio frame directory, and surviving face-source derivatives. Robot CAD videos excluded.'}}
 audit['archive_durations']=[f['durationMs'] for f in anim['frames']]
 write('audit.json',audit);write('source_inventory.json',inventory)
 (OUT/'audit.js').write_text('window.REUSE_AUDIT='+json.dumps(audit)+';\n',encoding='utf-8')
 csvwrite('face_instances.csv',[{k:r.get(k,'') for k in ['face','role','part','x','y','rot','mirror','open']} for r in instances]);csvwrite('archive_layers.csv',layer_rows);csvwrite('similarity_review.csv',candidates)
 csvwrite('drawing_plan.csv',[{'scope':'base','count':len(groups),'instruction':'Existing base parts; redraw only if changing to painted artwork.'},{'scope':'speech','count':len(data['visemes']),'instruction':'One shared set across speaking faces, not per expression.'},{'scope':'blink','count':2*nb,'instruction':'Half-closed and closed drawings for each of 14 open source eye parts. Reuse on left and right.'},{'scope':'transition eyes','count':2*nonblink,'instruction':'Half-closed and closed exit drawings for the other 16 eye parts. Skip on static-only reactions.'},{'scope':'transition mouths','count':len(mouth),'instruction':'One compressed breakdown per expression mouth; shared rest is the hub.'}])
 print(json.dumps(counts,indent=2));print('Closest candidates',candidates[:8]);print('Runtime open-flag overrides',runtime_extra)

if __name__=='__main__':main()
