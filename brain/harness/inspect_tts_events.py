import json
from pathlib import Path
p=Path('brain/results/tts_websocket_20260914/live/events.json')
for e in json.loads(p.read_text()):
    if e['type'] in ('state','transcript_delta','transcript_done','latency','audio_reset'):
        print({k:v for k,v in e.items() if k!='received_at'})
