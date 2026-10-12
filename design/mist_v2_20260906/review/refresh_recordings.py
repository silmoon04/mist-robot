"""Index completed four-leg solver recordings for the read-only viewer."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
items = []
paths = list((root/'simulation'/'outputs').glob('*/trajectory.json'))
paths += list((root/'simulation'/'variants').glob('*/*/trajectory.json'))
for path in sorted(paths):
    report_path = path.with_name('report.json')
    if not report_path.exists():
        continue
    trajectory = json.loads(path.read_text(encoding='utf-8'))
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if len(trajectory.get('joint_names', [])) != 16:
        continue
    prefix = path.parent.parent.name.replace('_',' ')+' / ' if 'variants' in path.parts else ''
    items.append({'label':prefix+report.get('case',path.parent.name).replace('_',' ')+' / '+report.get('status','unclassified'),
                  'path':'../'+path.relative_to(root).as_posix()})
(root/'review'/'recordings.json').write_text(json.dumps(items,indent=2),encoding='utf-8')
print(f'Indexed {len(items)} recordings')
