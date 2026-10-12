"""Package the selected drawings, player, and its local dependencies."""
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
    checks = json.loads((ROOT / 'asset_checks.json').read_text())
    qa = json.loads((ROOT / 'qa_runtime_report.json').read_text())
    async_qa = json.loads((ROOT / 'qa_async_report.json').read_text())
    original_qa = json.loads((ROOT / 'qa_original_eyes_report.json').read_text())
    assert manifest['complete'] and checks['passed'] and qa['passed'] and async_qa['passed'] and original_qa['passed']
    assert qa['runtimeSha256'] == sha((ROOT / 'runtime.js').read_bytes()), 'Stale runtime review'
    assert async_qa['runtimeSha256'] == qa['runtimeSha256'], 'Stale async review'
    assert qa['manifestSha256'] == sha((ROOT / 'manifest.json').read_bytes()), 'Stale asset review'
    assert qa['rendererSha256'] == sha((REUSE / 'runtime/drawn_face_renderer.js').read_bytes()), 'Stale renderer review'
    payload = {}

    def add(file, name):
        payload[name] = file.read_bytes()

    for name in ['index.html', 'style.css', 'preview.js', 'runtime.js', 'manifest.json',
                 'reference.png', 'contact_sheet.png', 'CONTRACT.md', 'AGENT_API.md',
                 'asset_checks.json', 'qa_runtime_report.json', 'qa_async_report.json', 'qa_findings.md',
                 'check_assets.cjs', 'qa_runtime.cjs', 'qa_async.cjs', 'build_assets.cjs',
                 'qa_original_eyes.cjs', 'qa_original_eyes_report.json', 'qa_v5_reference_renderer.cjs']:
        add(ROOT / name, 'handdrawn_v6/' + name)
    for asset in manifest['assets'].values():
        source = ROOT / asset['source']
        assert sha(source.read_bytes()) == asset['sourceSha256']
        add(source, 'handdrawn_v6/' + asset['source'])
        add(source.with_suffix('.json'), 'handdrawn_v6/' + source.with_suffix('.json').relative_to(ROOT).as_posix())
        for frame in asset['frames']:
            source = ROOT / frame['file']
            assert sha(source.read_bytes()) == frame['sha256']
            add(source, 'handdrawn_v6/' + frame['file'])
    for file in (ROOT / 'prompts').glob('*.txt'):
        if not file.name.startswith('eye_'):
            add(file, 'handdrawn_v6/prompts/' + file.name)
    for name in ['app_data.js', 'face_runtime.js', 'drawn_face_renderer.js', 'playback.js']:
        add(REUSE / 'runtime' / name, 'runtime/' + name)
    for name in ['transitions.html', 'transitions.css', 'transitions.js', 'index.html', 'preview.css', 'preview.js', 'MIST_drawn_animation_pack.zip']:
        add(REUSE / 'drawn' / name, 'drawn/' + name)
    add(REUSE / 'audit.js', 'audit.js')
    atlas_path = REUSE / 'drawn/atlas.json'
    add(atlas_path, 'drawn/atlas.json')
    atlas = json.loads(atlas_path.read_text())
    for asset in atlas['assets'].values():
        for name in {asset['file'], *(frame['file'] for frame in asset['frames'] if frame.get('file'))}:
            add(REUSE / 'drawn' / name, 'drawn/' + name)
    for file in (REUSE / 'drawn/audio').iterdir():
        if file.suffix in ('.json', '.wav'):
            add(file, 'drawn/audio/' + file.name)
    readme = '''# MIST activity motion

Original MIST faces with nine new activities, 108 separate transparent symbol cels.
The player keeps the original eyes, blinks, expression transitions and speech mouths.
Only the task symbols use the new hand-drawn style.

From this extracted directory run:

    python -m http.server 9042 --bind 127.0.0.1

Then open http://127.0.0.1:9042/handdrawn_v6/ in a browser.
Use Pause and Step to inspect frames. Select a card to inspect individual layers.
Play recording uses saved audio; it does not connect a microphone or voice provider.

Source sheets and exact ImageGen prompts are in handdrawn_v6/source and prompts.
The individual transparent PNGs are in handdrawn_v6/frames.
Animation playback is 15 fps with held drawn cels.
AGENT_API.md explains activity start, finish, cancellation and ownership.
The browser player is self-contained. Repository test scripts may need the full
project and the dependency paths named in their source.
'''
    payload['README.md'] = readme.encode()
    listing = {name: {'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(payload.items())}
    payload['pack_manifest.json'] = (json.dumps(listing, indent=2) + '\n').encode()
    output = ROOT / 'MIST_handdrawn_v6.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name, data in payload.items():
            assert archive.read(name) == data
    report = {'entries': len(payload), 'frames': checks['frames'], 'sourceSheets': checks['sourceSheets'],
              'bytes': output.stat().st_size, 'sha256': sha(output.read_bytes()), 'zipVerified': True}
    (ROOT / 'package_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
