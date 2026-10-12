import json
import shutil
from pathlib import Path
base = Path(__file__).resolve().parent
entry = json.loads((base / 'blink_detail_v2_provenance.json').read_text(encoding='utf-8'))
source = Path(entry['generated_path'])
destination = Path(entry['saved_path'])
destination.parent.mkdir(parents=True, exist_ok=True)
if destination.exists() and destination.read_bytes() != source.read_bytes():
    raise RuntimeError('Destination exists with different bytes')
shutil.copy2(source, destination)
print(destination)
print(destination.stat().st_size)
