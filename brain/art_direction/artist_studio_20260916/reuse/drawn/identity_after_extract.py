"""Extract pixel measurements for identity verification; source images are never modified."""
import base64
import hashlib
import json
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parent
atlas = json.loads((root / 'atlas.json').read_text(encoding='utf-8'))
assets = {}
for name, asset in atlas['assets'].items():
    frames = []
    for frame in asset['frames']:
        source_file = frame.get('file', asset['file'])
        image = Image.open(root / source_file).convert('RGBA')
        pixels = image.load()
        alpha = bytearray(frame['w'] * frame['h'])
        support = []
        for iy in range(frame['h']):
            row = []
            for ix in range(frame['w']):
                r, g, b, a = pixels[frame['x'] + ix, frame['y'] + iy]
                low, high = min(r, g, b), max(r, g, b)
                # Source sheets have white backgrounds. These are numeric opacity measurements.
                opacity = min(1, (255 - low) / 161) if high - low >= 22 else 0
                value = round(a * opacity) if opacity >= .035 else 0
                alpha[iy * frame['w'] + ix] = value
                if value > 64:
                    row.append(ix)
            if row:
                support.extend([[frame['x'] + min(row) + .5, frame['y'] + iy + .5], [frame['x'] + max(row) + .5, frame['y'] + iy + .5]])
        column_centers = []
        for ix in range(frame['w']):
            ys = [iy for iy in range(frame['h']) if alpha[iy * frame['w'] + ix] > 64]
            if ys:
                column_centers.append([frame['x'] + ix + .5, frame['y'] + (min(ys) + max(ys)) / 2 + .5])
        record = {'index': frame['index'], 'file': source_file, 'sha256': hashlib.sha256((root / source_file).read_bytes()).hexdigest(), 'x': frame['x'], 'y': frame['y'], 'w': frame['w'], 'h': frame['h'], 'support': support, 'columnCenters': column_centers}
        if frame['index'] == 0 or asset.get('kind') == 'eye':
            record['alphaBase64'] = base64.b64encode(alpha).decode('ascii')
        frames.append(record)
    assets[name] = {'file': asset['file'], 'sha256': hashlib.sha256((root / asset['file']).read_bytes()).hexdigest(), 'frames': frames}
(root / 'identity_after_pixels.json').write_text(json.dumps({'assets': assets}, separators=(',', ':')), encoding='utf-8')
print(json.dumps({'assets': len(assets), 'frames': sum(len(a['frames']) for a in assets.values()), 'sourceImagesModified': False}))
