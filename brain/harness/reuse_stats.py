exec(open('brain/harness/inspect_reuse.py',encoding='utf-8').read().split('for name in')[0])
from collections import Counter,defaultdict
s=(root/'brain/face_assets/app/app_data.js').read_text();d=json.loads(s[s.index('{'):].rstrip(';\n '))
roles=defaultdict(Counter)
for f in d['faces']:
 for role,slot in f['slots'].items():
  for e in slot if isinstance(slot,list) else [slot]:roles[role][e['part']]+=1
for role,ids in roles.items():print(role,len(ids),sum(ids.values()),dict(ids))
print('families',dict(Counter(p['family'] for k,p in d['parts'].items() if '__blink' not in k)))
print('blinks',d['blinks'])
for f in d['faces']:print(f['id'],[(r,s.get('part'),s.get('open')) for r,s in f['slots'].items() if isinstance(s,dict)])
