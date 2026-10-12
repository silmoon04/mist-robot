"""Stage the public acting-review page using an explicit asset list."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / 'brain/art_direction/artist_studio_20260916/reuse/acting_studies_v1'
DEST = PROJECT / 'output/mist-acting-pages/docs/acting-review'
PUBLIC_URL = 'https://silmoon04.github.io/mist/acting-review/'
UI = ('index.html', 'style.css', 'app.js', 'review-state.js')
sha = lambda data: hashlib.sha256(data).hexdigest()


def public_bytes(name):
    path = (SOURCE / name).resolve()
    if not path.is_relative_to(SOURCE.resolve()) or not path.is_file():
        raise ValueError(f'Invalid source asset: {name}')
    data = path.read_bytes()
    if path.suffix in {'.html', '.css', '.js', '.json', '.txt', '.md'}:
        data = (data.decode('utf-8-sig').replace('\r\n', '\n').rstrip() + '\n').encode()
    return data


def main():
    payload = {name: public_bytes(name) for name in UI}
    manifest = json.loads(public_bytes('manifest.json'))
    assert len(manifest['groups']) == 6
    poses = 0
    for group in manifest['groups']:
        sheet = group['sheet']
        assert sheet == f"source/{group['id']}.png"
        payload[sheet] = public_bytes(sheet)
        assert sha(payload[sheet]) == group['sourceSha256']
        prompt = group.get('prompt')
        if prompt:
            payload[prompt] = public_bytes(prompt)
        for example in group['examples']:
            for pose in example['poses']:
                name = pose['file']
                assert name.startswith(f"poses/{group['id']}/") and name.endswith('.png')
                payload[name] = public_bytes(name)
                assert sha(payload[name]) == pose['sha256']
                poses += 1
    assert poses == 54
    payload['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode()
    for name in ['overview.png', 'user_reference.png']:
        payload[name] = public_bytes(name)
    html = payload['index.html'].decode()
    html = html.replace('href="../thinking_v8/"', 'href="../"')
    html = re.sub(r'<nav\b[^>]*aria-label="Other previews"[^>]*>.*?</nav>', '<nav aria-label="Other previews"><a href="../acting-animations/">Animated gallery</a><a href="../">MIST voice</a></nav>', html, flags=re.S)
    payload['index.html'] = html.encode()
    payload['README.md'] = f'''# MIST acting review

Open {PUBLIC_URL}

Select examples with Animate this, choose individual poses, and add notes about
what to keep or change. Drafts save in the current browser. Export JSON to keep
a copy or import it on another device; Markdown is readable without this page.
A review link carries the selected content in its URL fragment.

The gallery contains 18 original MIST examples inspired by six animation
references, with three key poses each. Play timing shows proposed holds; these
are not finished animations or voice-synchronised assets. The PNG sources were
made with built-in ImageGen. Prompts, source sheets and the 54 pose crops are
included. The live voice application is separate.

The site has no review database or automatic cross-device sync. Reviews are
only included in exports or links when you use those controls.

To view an extracted pack, serve this folder with a local static HTTP server.
'''.encode()
    forbidden = re.compile(r'(?i)(?:[A-Z]:[\\/]Users[\\/]|127\.0\.0\.1|localhost|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,})')
    for name, data in payload.items():
        if Path(name).suffix in {'.html', '.css', '.js', '.json', '.txt', '.md'} and forbidden.search(data.decode()):
            raise ValueError(f'Private path, local endpoint or credential pattern in public file: {name}')
    archive_payload = dict(payload)
    archive_payload['index.html'] = payload['index.html'].replace(b'href="MIST_acting_studies_v1.zip" download>Download pack', b'href="overview.png">All source sheets').replace(b'href="../"', f'href="{PUBLIC_URL.rsplit("acting-review/",1)[0]}"'.encode())
    archive_payload['pack_manifest.json'] = (json.dumps({name:sha(data) for name,data in sorted(archive_payload.items())},indent=2)+'\n').encode()
    DEST.mkdir(parents=True, exist_ok=True)
    for name, data in payload.items():
        target = DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    archive_path = DEST / 'MIST_acting_studies_v1.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(archive_payload.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert all(archive.read(name) == data for name,data in archive_payload.items())
    expected = set(payload) | {archive_path.name, 'publication.json'}
    extra = [f.relative_to(DEST).as_posix() for f in DEST.rglob('*') if f.is_file() and f.relative_to(DEST).as_posix() not in expected]
    if extra:
        raise ValueError(f'Unexpected deployment files require review: {extra}')
    receipt = {'url': PUBLIC_URL, 'groups':6, 'examples':18, 'poses':poses,
               'files': {name:{'bytes':len(data),'sha256':sha(data)} for name,data in sorted(payload.items())},
               'archive': {'file':archive_path.name,'sha256':sha(archive_path.read_bytes()),'bytes':archive_path.stat().st_size}}
    (DEST / 'publication.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'url':PUBLIC_URL,'files':len(payload)+2,'poses':poses,'bytes':sum(f.stat().st_size for f in DEST.rglob('*') if f.is_file())}))


if __name__ == '__main__':
    main()
