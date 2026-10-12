from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
a=json.loads((OUT/'audit.json').read_text());clips=json.loads((OUT/'clips.json').read_text())
assert len(a['faces'])==40 and sum(g['instance_count'] for g in a['groups'])==120
assert len({p for ids in a['motion_families'].values() for p in ids})==30
max_error=0
for face in a['faces']:
 target=Image.open(OUT/'faces'/(face['id']+'.png')).convert('RGBA')
 merged=Image.new('RGBA',target.size)
 for role in ['eye_L','eye_R','mouth','tear0','tear1']:
  p=OUT/'instances'/face['id']/(role+'.png')
  if p.exists():merged=Image.alpha_composite(merged,Image.open(p).convert('RGBA'))
 # Transparent RGB has no visible meaning; compare premultiplied colour and alpha.
 def premul(im):
  v=np.array(im,dtype=float);v[:,:,:3]*=v[:,:,3:]/255;return v
 error=float(np.max(np.abs(premul(target)-premul(merged))));max_error=max(max_error,error)
 assert error<=2,(face['id'],error)
for clip in clips:
 assert clip['fps']==8
 for i in range(clip['frames']):assert (OUT/'clips'/clip['id']/f'{i:03d}.png').exists()
inventory=json.loads((OUT/'source_inventory.json').read_text())
protected=['brain/face_assets/app/app_data.js','brain/face_assets/parts_library.json','brain/face_assets/faces_canonical.json','brain/ui/static/face_runtime.js','design/mist_v2_20260906/brain_v2_20260907/faces/animation_frames.json']
for path in protected:
 entry=next(p for p in inventory if p['path']==path)
 assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==entry['sha256'],path
result={'passed':True,'faces_reassembled':40,'maximum_premultiplied_pixel_error':max_error,'preserved_source_files':protected,'eight_fps_clips':len(clips),'eight_fps_frames':sum(c['frames'] for c in clips),'studio_path_layers_audited':a['studio_path_layers_audited'],'imagegen_pilot':'Not approved: inconsistent half-lids, anchor drift, edge specks.'}
(OUT/'geometry_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
