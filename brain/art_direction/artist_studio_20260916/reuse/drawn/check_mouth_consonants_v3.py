"""Copy the selected sheet unchanged; inspect ink bounds and connected shapes."""
from pathlib import Path
from collections import deque
import hashlib
import json
import shutil
from PIL import Image

root = Path(__file__).resolve().parent
meta = json.loads((root / 'generated_mouth_consonants_v3.json').read_text(encoding='utf-8'))
source = Path(meta['source'])
dest = root / meta['destination']
shutil.copyfile(source, dest)
im = Image.open(dest).convert('RGBA')
w, h = im.size
pixels = im.load()
frames, failures = [], []
scale = meta['logicalCellSize'] / (w / 3)
for index, pose in enumerate(meta['order']):
    col, row = index % 3, index // 3
    x0, y0, x1, y1 = round(col*w/3), round(row*h/2), round((col+1)*w/3), round((row+1)*h/2)
    ink = set()
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b, a = pixels[x, y]
            if a > 64 and g > 110 and b > 110 and g-r > 30 and b-r > 25:
                ink.add((x,y))
    unseen, components = set(ink), []
    while unseen:
        seed = unseen.pop()
        q, component = deque([seed]), [seed]
        while q:
            x, y = q.popleft()
            for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if p in unseen:
                    unseen.remove(p)
                    q.append(p)
                    component.append(p)
        components.append(component)
    components.sort(key=len, reverse=True)
    if not components:
        failures.append(f'Empty cell {index}')
        continue
    shape = set(components[0])
    bx0, by0 = min(p[0] for p in shape), min(p[1] for p in shape)
    bx1, by1 = max(p[0] for p in shape)+1, max(p[1] for p in shape)+1
    speckles = sum(len(c) for c in components[1:])
    column_gaps = 0
    for x in range(bx0, bx1):
        ys = [y for xx, y in shape if xx == x]
        if ys:
            column_gaps += max(ys)-min(ys)+1-len(ys)
    margin = min(bx0-x0, by0-y0, x1-bx1, y1-by1)
    if margin < 8 or speckles > 8 or column_gaps > 8:
        failures.append(f'Cell {index}: margin={margin}, detached={speckles}, column gaps={column_gaps}')
    replacement = meta['replaces'][index]
    frames.append({
        'sheetIndex': index, 'family': replacement['family'], 'pose': replacement['pose'],
        'frameIndex': replacement['frameIndex'],
        'file': meta['destination'],
        'cell': {'x':x0,'y':y0,'w':x1-x0,'h':y1-y0},
        'inkBounds': {'x':bx0,'y':by0,'w':bx1-bx0,'h':by1-by0},
        'cropBounds': {'x':bx0-3,'y':by0-3,'w':bx1-bx0+6,'h':by1-by0+6},
        'cx':(bx0+bx1)/2, 'cy':by0, 'anchor':'upper-mouth',
        'sourceScale':scale,
        'logicalInkWidth':(bx1-bx0)*scale,'logicalInkHeight':(by1-by0)*scale,
        'components':len(components),'detachedPixelCount':speckles,'internalColumnGapPixels':column_gaps,
        'minCellMargin':margin,'inkPixels':len(shape)
    })
report = {
    'source':meta['destination'],'imageWidth':w,'imageHeight':h,'columns':3,'rows':2,
    'logicalCellSize':meta['logicalCellSize'],'sourceScale':scale,
    'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'copySha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
    'pixelsUnmodified':source.read_bytes()==dest.read_bytes(),
    'alphaExtrema':im.getchannel('A').getextrema(),
    'frames':frames,'failures':failures,'passed':not failures and len(frames)==6,
    'limitations':['Read-only pixel audit checks bounds, detached pixels and internal gaps. Visual review separately checked smooth silhouettes.']
}
(root/'mouth_consonants_v3_validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
