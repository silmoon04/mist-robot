"""Stage the layered animation gallery without copying local working metadata."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / 'brain/art_direction/artist_studio_20260916/reuse/acting_animations_v2'
DEST = PROJECT / 'output/mist-acting-pages/docs/acting-animations'
PUBLIC_URL = 'https://silmoon04.github.io/mist/acting-animations/'
TEXT_EXTENSIONS = {'.html', '.css', '.js', '.json', '.txt', '.md'}
sha = lambda value: hashlib.sha256(value).hexdigest()


def main():
    manifest = json.loads((SOURCE / 'manifest.json').read_text(encoding='utf-8-sig'))
    checks = json.loads((SOURCE / 'asset_checks.json').read_text(encoding='utf-8-sig'))
    assert manifest.get('complete') and checks.get('passed') and checks.get('complete')
    examples = [example for group in manifest['groups'] for example in group['examples']]
    assert len(examples) == 18 and all(len(example['frames']) == 12 for example in examples)
    names = {'index.html', 'style.css', 'app.js', 'runtime.js', 'review-state.js', 'manifest.json'}
    for example in examples:
        names.add(example['sheet'])
        assert sha((SOURCE / example['sheet']).read_bytes()) == example['sourceSha256']
        for frame in example['frames']:
            names.add(frame['file'])
            assert sha((SOURCE / frame['file']).read_bytes()) == frame['sha256']
            names.update(layer['file'] for layer in frame['layers'].values())
            for layer in frame['layers'].values():
                assert sha((SOURCE / layer['file']).read_bytes()) == layer['sha256']
    for directory in ['prompts', 'contact', 'previews']:
        names.update(file.relative_to(SOURCE).as_posix() for file in (SOURCE / directory).rglob('*') if file.is_file() and file.suffix in {'.png', '.jpg', '.gif', '.webp', '.txt', '.json', '.md'})
    for optional in ['README.md', 'transition_plans.json', 'animation_catalog.json']:
        if (SOURCE / optional).is_file():
            names.add(optional)
    payload = {}
    forbidden = re.compile(r'(?i)(?:[A-Z]:[\\/]Users[\\/]|127\.0\.0\.1|localhost|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,})')
    for name in sorted(names):
        path = (SOURCE / name).resolve()
        if not path.is_relative_to(SOURCE.resolve()) or not path.is_file():
            raise ValueError(f'Invalid asset: {name}')
        data = path.read_bytes()
        if path.suffix in TEXT_EXTENSIONS:
            text = data.decode('utf-8-sig').replace('\r\n', '\n').rstrip() + '\n'
            if forbidden.search(text):
                raise ValueError(f'Local endpoint, path or credential pattern: {name}')
            data = text.encode()
        payload[name] = data
    DEST.mkdir(parents=True, exist_ok=True)
    for name, data in payload.items():
        target = DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    archive_payload = dict(payload)
    archive_payload['index.html'] = archive_payload['index.html'].replace(b'href="../acting-review/"', b'href="https://silmoon04.github.io/mist/acting-review/"')
    archive_payload['index.html'] = archive_payload['index.html'].replace(b'href="../"', b'href="https://silmoon04.github.io/mist/"')
    archive_payload['index.html'] = archive_payload['index.html'].replace(b'href="MIST_acting_animations_v2.zip" download>Download pack', b'href="previews/all-animations.gif" download>Download GIF')
    archive_payload['pack_manifest.json'] = (json.dumps({name: sha(data) for name, data in sorted(archive_payload.items())}, indent=2) + '\n').encode()
    archive_path = DEST / 'MIST_acting_animations_v2.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(archive_payload.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert all(archive.read(name) == data for name, data in archive_payload.items())
    receipt = {
        'url': PUBLIC_URL, 'examples': len(examples), 'frames': sum(len(example['frames']) for example in examples),
        'layerFiles': sum(len(frame['layers']) for example in examples for frame in example['frames']),
        'files': {name: {'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(payload.items())},
        'archive': {'file': archive_path.name, 'bytes': archive_path.stat().st_size, 'sha256': sha(archive_path.read_bytes())}
    }
    (DEST / 'publication.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
    extra = [file.relative_to(DEST).as_posix() for file in DEST.rglob('*') if file.is_file() and file.relative_to(DEST).as_posix() not in set(payload) | {archive_path.name, 'publication.json'}]
    if extra:
        raise ValueError(f'Unexpected staged files: {extra}')
    print(json.dumps({'url': PUBLIC_URL, 'files': len(payload), 'frames': receipt['frames'], 'layers': receipt['layerFiles'], 'archiveBytes': archive_path.stat().st_size}))


if __name__ == '__main__':
    main()
