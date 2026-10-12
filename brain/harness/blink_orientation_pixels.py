"""Read actual closed-lid ink direction without changing source images."""
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DRAWN = ROOT / 'brain/art_direction/artist_studio_20260916/reuse/drawn'
atlas = json.loads((DRAWN / 'atlas.json').read_text(encoding='utf-8'))
result = {}
for family in ('round', 'hook', 'arc', 'loop', 'slot', 'chevron', 'bar'):
    asset = atlas['assets'][family]
    index, frame = next((i, frame) for i, frame in enumerate(asset['frames']) if frame['pose'] == 'closed')
    path = DRAWN / frame.get('file', asset['file'])
    image = Image.open(path).convert('RGBA')
    points = []
    for y in range(frame['y'], frame['y'] + frame['h']):
        for x in range(frame['x'], frame['x'] + frame['w']):
            r, g, b, a = image.getpixel((x, y))
            # Match the runtime's cyan-on-white inclusion boundary.
            if a > 64 and max(r, g, b) - min(r, g, b) >= 22 and min(r, g, b) < 210:
                points.append((x, y))
    cx = sum(x for x, y in points) / len(points)
    cy = sum(y for x, y in points) / len(points)
    xx = sum((x - cx) ** 2 for x, y in points) / len(points)
    yy = sum((y - cy) ** 2 for x, y in points) / len(points)
    xy = sum((x - cx) * (y - cy) for x, y in points) / len(points)
    angle = .5 * math.atan2(2 * xy, xx - yy)
    eigsum = xx + yy
    eigdiff = math.hypot(xx - yy, 2 * xy)
    result[family] = {'frame': index, 'pose': 'closed', 'file': path.relative_to(ROOT).as_posix(),
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'inkPixels': len(points), 'principalAngleDegrees': math.degrees(angle),
                      'principalVector': [math.cos(angle), math.sin(angle)],
                      'axisRatio': math.sqrt((eigsum + eigdiff) / max(.000001, eigsum - eigdiff))}
print(json.dumps(result))
