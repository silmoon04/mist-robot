import json
import shutil
from pathlib import Path

base = Path(__file__).resolve().parent
entries = json.loads((base / 'generated_blinks.json').read_text(encoding='utf-8'))
for entry in entries:
    destination = Path(entry['saved_path'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != Path(entry['generated_path']).read_bytes():
            raise RuntimeError(f'Destination already contains another asset: {destination}')
    else:
        shutil.copy2(entry['generated_path'], destination)
    print(f"{entry['id']}: {destination.stat().st_size} bytes {destination}")
