import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for name in ['brain/face_assets/app/app_data.js','brain/face_assets/parts_library.json','brain/face_assets/faces_canonical.json','design/mist_v2_20260906/brain_v2_20260907/faces/animation_frames.json','brain/art_direction/artist_studio_20260916/plan.json']:
 p=root/name;s=p.read_text(encoding='utf-8'); d=json.loads(s[s.index('{'):].rstrip(';\n ')) if p.suffix=='.js' else json.loads(s)
 print('\nFILE',name)
 if isinstance(d,dict):
  for k,v in d.items():
   print(k,type(v).__name__,len(v) if isinstance(v,(dict,list)) else str(v)[:180])
   if isinstance(v,dict): print(str(list(v.items())[:1])[:1700])
   if isinstance(v,list): print(str(v[:1])[:1700])
 else:print(str(d[:1])[:1700])
