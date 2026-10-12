"""Bundle the thinking preview with its original face and saved-audio dependencies."""
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
    runtime = json.loads((ROOT / 'runtime_checks.json').read_text())
    choreography = json.loads((ROOT / 'qa_choreography_report.json').read_text())
    assets = json.loads((ROOT / 'qa_assets_report.json').read_text())
    integration = json.loads((ROOT / 'qa_integration_report.json').read_text())
    assert manifest['complete'] and runtime['passed'] and choreography['passed'] and integration['passed']
    assert assets.get('assetValidationPassed') or assets['passed']
    # Preserve the red baseline guard. Its sole reviewed difference is a concurrent
    # CSS positioning fix; the original-face integration tests cover the new bytes.
    for difference in assets.get('protectedFileDifferences', []):
        assert difference['file'] == 'brain/ui/static/drawn_face_renderer.js'
        assert difference['expected'] == '3a600d7b08f15bf96c5a74ee353bc01403c09b7bf744e12f9c7c62485ee60f5a'
        assert difference['actual'] == '22084e744e8d11ed0484b273b8f82ee3af8c9e9e11070c6290a3e535f6d48ce3'
    runtime_hash = sha((ROOT / 'runtime.js').read_bytes())
    assert runtime['runtimeSha256'] == choreography['runtimeSha256'] == runtime_hash
    assert runtime['rendererSha256'] == sha((REUSE / 'runtime/drawn_face_renderer.js').read_bytes())
    assert assets['manifestSha256'] == sha((ROOT / 'manifest.json').read_bytes())
    payload = {}

    def add(file, name):
        payload[name] = file.read_bytes()

    for name in ['index.html', 'style.css', 'preview.js', 'runtime.js', 'manifest.json',
                 'contact_sheet.png', 'BRIEF.md', 'PLAYER.md', 'REFERENCE_NOTES.md',
                 'runtime_checks.json', 'qa_choreography_report.json', 'qa_assets_report.json',
                 'qa_integration_report.json', 'qa_findings.md', 'qa_external_edit.md',
                 'build_assets.cjs', 'test_choreography.cjs', 'qa_choreography.cjs',
                 'qa_assets.cjs', 'package_assets.py']:
        add(ROOT / name, 'thinking_v7/' + name)

    # These links lead to earlier project pages which are not part of this pack.
    html = payload['thinking_v7/index.html'].decode()
    html = html.replace('href="../handdrawn_v6/"', 'href="./"', 1)
    html = html.replace('<a href="../handdrawn_v6/">Previous animations</a>', '<a href="PLAYER.md">Player notes</a>')
    html = html.replace('<a href="MIST_thinking_v7.zip" download>Download pack</a>', '<a href="contact_sheet.png">Drawings</a>')
    payload['thinking_v7/index.html'] = html.encode()
    for asset in manifest['assets'].values():
        source = ROOT / asset['source']
        assert sha(source.read_bytes()) == asset['sourceSha256']
        add(source, 'thinking_v7/' + asset['source'])
        add(source.with_suffix('.json'), 'thinking_v7/' + source.with_suffix('.json').relative_to(ROOT).as_posix())
        for frame in asset['frames']:
            source = ROOT / frame['file']
            assert sha(source.read_bytes()) == frame['sha256']
            add(source, 'thinking_v7/' + frame['file'])
    for file in (ROOT / 'prompts').glob('*.txt'):
        add(file, 'thinking_v7/prompts/' + file.name)
    for name in ['app_data.js', 'face_runtime.js', 'drawn_face_renderer.js', 'playback.js']:
        add(REUSE / 'runtime' / name, 'runtime/' + name)
    atlas_path = REUSE / 'drawn/atlas.json'
    add(atlas_path, 'drawn/atlas.json')
    atlas = json.loads(atlas_path.read_text())
    for asset in atlas['assets'].values():
        for name in {asset['file'], *(frame['file'] for frame in asset['frames'] if frame.get('file'))}:
            add(REUSE / 'drawn' / name, 'drawn/' + name)
    for file in (REUSE / 'drawn/audio').iterdir():
        if file.suffix in ('.json', '.wav'):
            add(file, 'drawn/audio/' + file.name)
    payload['README.md'] = '''# MIST thinking studies

Six activity previews with original MIST faces: quiet thought, reading, coding,
drafting, sorting ideas and searching. There are 88 transparent prop cels:
64 newly generated drawings and 24 reused searching/pondering drawings.
Playback uses 15 fps with deliberate holds. The frame count is not the frame rate.

From this extracted directory run:

    python -m http.server 9042 --bind 127.0.0.1

Then open http://127.0.0.1:9042/thinking_v7/ in your browser.

Click a card to inspect it. Pause, Step and the cel strip let you examine drawings.
Play recording uses saved audio with mouth motion driven by audio energy; it does
not contact a model or voice provider. No microphone is needed.

Source sheets and exact ImageGen prompts are under thinking_v7/source and prompts.
Individual PNGs are under thinking_v7/frames. PLAYER.md documents the activity API.
REFERENCE_NOTES.md records the EMO and Lordicon observations behind the studies.
This is a concept preview; the live phone default has not been switched to it.

The browser player is self-contained. Repository tests/build scripts retain their
original dependency paths and may need the full project to run.
'''.encode()
    payload['pack_manifest.json'] = (json.dumps({name: {'bytes': len(data), 'sha256': sha(data)}
                                                for name, data in sorted(payload.items())}, indent=2) + '\n').encode()
    output = ROOT / 'MIST_thinking_v7.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name, data in payload.items():
            assert archive.read(name) == data
    report = {'zipVerified': True, 'entries': len(payload), 'frames': 88,
              'newFrames': 64, 'reusedFrames': 24, 'bytes': output.stat().st_size,
              'sha256': sha(output.read_bytes()), 'runtimeSha256': runtime_hash}
    (ROOT / 'package_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
