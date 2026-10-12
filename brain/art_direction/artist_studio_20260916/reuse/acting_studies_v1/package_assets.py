from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()
manifest_bytes = (ROOT / 'manifest.json').read_bytes()
manifest = json.loads(manifest_bytes)
for name in ['asset_review.json', 'visual_review.json']:
    review = json.loads((ROOT / name).read_text())
    assert review['passed'] and review['manifestSha256'] == sha(manifest_bytes), name
assert len(manifest['groups']) == 6
count = 0
for group in manifest['groups']:
    assert sha((ROOT / group['sheet']).read_bytes()) == group['sourceSha256']
    for example in group['examples']:
        for pose in example['poses']:
            assert sha((ROOT / pose['file']).read_bytes()) == pose['sha256']
            count += 1
assert count == 54
payload = {}
for file in ROOT.rglob('*'):
    if file.is_file() and file.suffix in {'.html', '.css', '.js', '.json', '.png', '.jpg', '.txt', '.md', '.cjs', '.py'} and file.name != 'package_report.json':
        payload[file.relative_to(ROOT).as_posix()] = file.read_bytes()
html = payload['index.html'].decode()
for name in ['thinking_v8', 'style_studies_v3']:
    html = html.replace(f'href="../{name}/', f'href="http://127.0.0.1:9041/reuse/{name}/')
html = html.replace('href="MIST_acting_studies_v1.zip" download>Download pack', 'href="overview.png">All source sheets')
payload['index.html'] = html.encode()
payload['pack_manifest.json'] = (json.dumps({name: sha(data) for name, data in sorted(payload.items())}, indent=2) + '\n').encode()
output = ROOT / 'MIST_acting_studies_v1.zip'
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, data in sorted(payload.items()):
        archive.writestr(name, data)
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert all(archive.read(name) == data for name, data in payload.items())
report = {'verified': True, 'groups': 6, 'examples': 18, 'poses': 54, 'files': len(payload), 'bytes': output.stat().st_size, 'sha256': sha(output.read_bytes())}
(ROOT / 'package_report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
