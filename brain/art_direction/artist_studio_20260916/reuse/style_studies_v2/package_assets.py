from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


manifest = json.loads((ROOT / 'manifest.json').read_text())
review = json.loads((ROOT / 'asset_review.json').read_text())
assert review['passed'] and review['manifestSha256'] == sha((ROOT / 'manifest.json').read_bytes())
visual = json.loads((ROOT / 'visual_review.json').read_text())
assert visual['passed'] and visual['manifestSha256'] == sha((ROOT / 'manifest.json').read_bytes())
assert len(manifest['faces']) == 10 and len(manifest['styles']) == 4
for variants in manifest['assets'].values():
    for asset in variants.values():
        assert sha((ROOT / asset['file']).read_bytes()) == asset['sha256']
payload = {}
for file in ROOT.rglob('*'):
    if file.is_file() and file.suffix in {'.html', '.css', '.js', '.json', '.png', '.jpg', '.txt', '.md', '.cjs', '.py'} and file.name != 'package_report.json':
        payload[file.relative_to(ROOT).as_posix()] = file.read_bytes()
# Prior previews stay linked to the repository server in the standalone pack.
html = payload['index.html'].decode()
for name in ['thinking_v8', 'drawn', 'style_studies_v1']:
    html = html.replace(f'href="../{name}/', f'href="http://127.0.0.1:9041/reuse/{name}/')
html = html.replace('<a class="pack" href="MIST_style_studies_v2.zip" download>Download pack</a>', '<a class="pack" href="comparison.png">Comparison sheet</a>')
payload['index.html'] = html.encode()
payload['pack_manifest.json'] = (json.dumps({name: sha(data) for name, data in sorted(payload.items())}, indent=2) + '\n').encode()
output = ROOT / 'MIST_style_studies_v2.zip'
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, data in sorted(payload.items()):
        archive.writestr(name, data)
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert all(archive.read(name) == data for name, data in payload.items())
report = {'verified': True, 'originalFaces': 10, 'generatedVariants': 30, 'files': len(payload), 'bytes': output.stat().st_size, 'sha256': sha(output.read_bytes())}
(ROOT / 'package_report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
