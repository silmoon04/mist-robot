"""Copy selected ImageGen artwork byte for byte and audit its cells without editing pixels."""
from pathlib import Path
from collections import deque
import hashlib
import json
import shutil
from PIL import Image

root = Path(__file__).resolve().parent
meta = json.loads((root / 'generated_mouths_v2.json').read_text(encoding='utf-8'))
source = Path(meta['source'])
dest = root / meta['destination']
shutil.copyfile(source, dest)
im = Image.open(dest).convert('RGBA')
w, h = im.size
frames = []
failures = []
for index in range(32):
    col, row = index % 4, index // 4
    x0, y0, x1, y1 = round(col * w / 4), round(row * h / 8), round((col + 1) * w / 4), round((row + 1) * h / 8)
    pixels = im.load()
    ink = set()
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b, a = pixels[x, y]
            if a > 64 and g > 110 and b > 110 and g - r > 30 and b - r > 25:
                ink.add((x, y))
    unseen = set(ink)
    components = []
    while unseen:
        seed = unseen.pop()
        q = deque([seed])
        component = [seed]
        while q:
            x, y = q.popleft()
            for p in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if p in unseen:
                    unseen.remove(p)
                    q.append(p)
                    component.append(p)
        components.append(component)
    components.sort(key=len, reverse=True)
    if not components:
        failures.append(f'Empty cell {index}')
        continue
    dominant = components[0]
    bx0, by0 = min(p[0] for p in dominant), min(p[1] for p in dominant)
    bx1, by1 = max(p[0] for p in dominant) + 1, max(p[1] for p in dominant) + 1
    margin = min(bx0 - x0, by0 - y0, x1 - bx1, y1 - by1)
    speckles = sum(len(c) for c in components[1:])
    if margin < 8:
        failures.append(f'Cell {index} too close to cell boundary')
    if speckles > 8:
        failures.append(f'Cell {index} has {speckles} detached pixels')
    frames.append({
        'index': index % 16, 'sheetIndex': index,
        'family': 'mouth_neutral' if index < 16 else 'mouth_smile',
        'pose': meta['order'][index % 16],
        'cell': {'x': x0, 'y': y0, 'w': x1 - x0, 'h': y1 - y0},
        'inkBounds': {'x': bx0, 'y': by0, 'w': bx1 - bx0, 'h': by1 - by0},
        'cropBounds': {'x': bx0 - 3, 'y': by0 - 3, 'w': bx1 - bx0 + 6, 'h': by1 - by0 + 6},
        'cx': (bx0 + bx1) / 2,
        'cy': by0,
        'anchor': 'upper-mouth',
        'minCellMargin': margin,
        'inkPixels': len(dominant),
        'detachedPixelCount': speckles,
        'components': len(components)
    })
report = {
    'source': str(dest.relative_to(root)).replace('\\', '/'),
    'imageWidth': w, 'imageHeight': h, 'columns': 4, 'rows': 8,
    'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'copySha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
    'pixelsUnmodified': source.read_bytes() == dest.read_bytes(),
    'alphaExtrema': im.getchannel('A').getextrema(),
    'frames': frames,
    'failures': failures,
    'passed': not failures and len(frames) == 32,
    'limitations': ['Pixel analysis checks placement and stray pixels; natural motion and audio sync need playback review.']
}
(root / 'mouth_v2_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'frames'}, indent=2))
