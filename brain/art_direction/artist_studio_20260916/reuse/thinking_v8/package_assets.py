"""Export the reviewed sprite assets and a self-contained local player."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent
REUSE = ROOT.parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    assert manifest['complete'] and manifest['version'] == 8
    assert len(manifest['assets']) == 8
    assert sum(len(a['frames']) for a in manifest['assets'].values()) == 192
    for filename in ['qa_assets_report.json', 'qa_runtime_report.json']:
        report = json.loads((ROOT / filename).read_text())
        assert report['passed'], filename
        if report.get('manifestSha256'):
            assert report['manifestSha256'] == sha((ROOT / 'manifest.json').read_bytes())
        if report.get('runtimeSha256'):
            assert report['runtimeSha256'] == sha((ROOT / 'runtime.js').read_bytes())
    payload = {}
    draft_reports = {'package_report.json', 'qa_runtime_contract_report.json', 'qa_semantic_probe.json'}

    def add(file, name):
        payload[name] = file.read_bytes()

    for file in ROOT.iterdir():
        if file.is_file() and file.suffix in {'.html', '.css', '.js', '.cjs', '.json', '.md', '.py', '.png'} and file.name not in draft_reports:
            add(file, 'thinking_v8/' + file.name)
    # A downloaded player has no previous-version pages or copy of its own zip.
    html = payload['thinking_v8/index.html'].decode()
    import re
    html = re.sub(r'href="\.\./(?:thinking_v7|handdrawn_v6)/"', 'href="PLAYER.md"', html)
    html = re.sub(r'<a\b[^>]*href="MIST_thinking_v8\.zip"[^>]*>.*?</a>', '<a href="contact_sheet.png">Drawings</a>', html)
    payload['thinking_v8/index.html'] = html.encode()
    for asset in manifest['assets'].values():
        source = ROOT / asset['source']
        assert sha(source.read_bytes()) == asset['sourceSha256']
        add(source, 'thinking_v8/' + asset['source'])
        add(source.with_suffix('.json'), 'thinking_v8/' + source.with_suffix('.json').relative_to(ROOT).as_posix())
        for frame in asset['frames']:
            file = ROOT / frame['file']
            assert sha(file.read_bytes()) == frame['sha256']
            add(file, 'thinking_v8/' + frame['file'])
    for file in (ROOT / 'prompts').glob('*.txt'):
        add(file, 'thinking_v8/prompts/' + file.name)
    for folder in ['components', 'source']:
        for file in (ROOT / folder).iterdir():
            if file.suffix in {'.png', '.json'}:
                add(file, 'thinking_v8/' + folder + '/' + file.name)
    for name in ['app_data.js', 'face_runtime.js', 'drawn_face_renderer.js', 'playback.js']:
        add(REUSE / 'runtime' / name, 'runtime/' + name)
    atlas_path = REUSE / 'drawn/atlas.json'
    add(atlas_path, 'drawn/atlas.json')
    for asset in json.loads(atlas_path.read_text())['assets'].values():
        for name in {asset['file'], *(f['file'] for f in asset['frames'] if f.get('file'))}:
            add(REUSE / 'drawn' / name, 'drawn/' + name)
    for file in (REUSE / 'drawn/audio').iterdir():
        if file.suffix in {'.json', '.wav'}:
            add(file, 'drawn/audio/' + file.name)
    payload['README.md'] = '''# MIST thinking animations

Eight sequences, each with 24 transparent frames: four entrance, sixteen active,
four exit. The player runs at 15 fps with short deliberate holds. Original MIST
face shapes, blinks and speech mouths are included. Automatic thinking varies
between three faces; the expression selector can hold a specific face instead.

From this extracted folder run:

    python -m http.server 9042 --bind 127.0.0.1

Open http://127.0.0.1:9042/thinking_v8/ in your browser.

Click a card to inspect individual frames and layers. The saved voice test uses
audio energy to move the mouth; it does not call a model or voice provider.

Original ImageGen sheets and exact prompts are in thinking_v8/source and prompts.
Sorting, drafting, connecting and checking reuse generated components with
controlled placement and ink reveal. These frames are assembled poses, not
separately generated drawings; drafting retains the generated page-turn cels.
The 192 individual transparent PNGs are in thinking_v8/frames. PLAYER.md describes
activity selection, face variation and speech handling. QA reports state what was
tested. Tests and asset scripts may need the original repository dependencies.
Use the exported frames for playback; source sheets are retained as references.
'''.encode()
    payload['pack_manifest.json'] = (json.dumps({name: {'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(payload.items())}, indent=2) + '\n').encode()
    output = ROOT / 'MIST_thinking_v8.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name, data in payload.items():
            assert archive.read(name) == data
    report = {'zipVerified': True, 'entries': len(payload), 'frames': 192, 'bytes': output.stat().st_size, 'sha256': sha(output.read_bytes())}
    (ROOT / 'package_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
