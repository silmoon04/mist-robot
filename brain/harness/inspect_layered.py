import json
from pathlib import Path
d=json.loads(Path('brain/results/layered_brain_20260914/conversation/result.json').read_text())
events=d['events'];start=next(e['at'] for e in events if e['type']=='brain_job' and e['status']=='running')
for e in events:
    if e['type'] in ('brain_job','transcript_done','tool','latency'):
        print(round(e['at']-start,3),{k:v for k,v in e.items() if k not in ('at','received_at','startup','result','summary')})
