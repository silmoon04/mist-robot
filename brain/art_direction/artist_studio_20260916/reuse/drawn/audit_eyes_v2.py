from pathlib import Path
from PIL import Image
import json
import hashlib
import shutil
import statistics

BASE = Path(__file__).resolve().parent
SOURCE = Path(r'<LOCAL_HOME>\.codex\generated_images\01a0ca9b-b015-7d00-9159-3200088125f4\exec-f6c8a887-131c-4277-b390-fd2c358e3272.png')
DEST = BASE / 'sheets' / 'v2' / 'eyes_round_loop_arc_v2.png'
DEST.parent.mkdir(exist_ok=True)
shutil.copy2(SOURCE, DEST)
img = Image.open(DEST).convert('RGB')
width, height = img.size
poses = ['rest', 'anticipation', 'closing', 'near_closed', 'closed', 'opening_low', 'opening', 'settled']
atlas = json.loads((BASE / 'atlas.json').read_text(encoding='utf-8'))
result = {'status': 'accepted', 'source': str(SOURCE), 'file': DEST.relative_to(BASE).as_posix(), 'sha256': hashlib.sha256(DEST.read_bytes()).hexdigest(), 'dimensions': [width, height], 'grid': {'columns': 4, 'rows': 6}, 'poses': poses, 'sourceUnmodified': SOURCE.read_bytes() == DEST.read_bytes(), 'assets': {}, 'limits': ['Static cel audit does not establish perceptual naturalness during playback.', 'Frame 7 differs from frame 0; use frame 0 to finish the loop.', 'Generated cel placement is imperfect; use measured lower-lid bounds for runtime registration without stretching.']}
pixels = img.load()
row_ink = [sum(1 for x in range(width) if pixels[x,y][1]-pixels[x,y][0] > 30 and pixels[x,y][2]-pixels[x,y][0] > 20) for y in range(height)]
bands = []
start = None
for y, count in enumerate(row_ink + [0]):
    if count and start is None:
        start = y
    elif not count and start is not None:
        bands.append([start,y])
        start = None
assert len(bands) == 6, bands
row_bounds = [0] + [round((bands[i-1][1] + bands[i][0])/2) for i in range(1,6)] + [height]
result['grid']['rowBoundaries'] = row_bounds
result['grid']['note'] = 'The generated row spacing is not uniform. Use these measured row boundaries, not height/6.'
print('ROW_BOUNDARIES', row_bounds)
for family_index, family in enumerate(['round', 'loop', 'arc']):
    frames = []
    for pose_index, pose in enumerate(poses):
        index = family_index * 8 + pose_index
        col, row = index % 4, index // 4
        x0, x1 = round(col * width / 4), round((col+1) * width / 4)
        y0, y1 = row_bounds[row], row_bounds[row+1]
        ink = {(x,y) for y in range(y0,y1) for x in range(x0,x1) if pixels[x,y][1]-pixels[x,y][0] > 30 and pixels[x,y][2]-pixels[x,y][0] > 20}
        minx, maxx = min(x for x,y in ink), max(x for x,y in ink)
        miny, maxy = min(y for x,y in ink), max(y for x,y in ink)
        pending = set(ink)
        comps = []
        while pending:
            stack = [pending.pop()]
            count = 0
            while stack:
                x,y = stack.pop()
                count += 1
                for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if (nx,ny) in pending:
                        pending.remove((nx,ny))
                        stack.append((nx,ny))
            if count >= 4:
                comps.append(count)
        frames.append({'index': pose_index, 'sheetIndex': index, 'pose': pose, 'cell': {'x':x0,'y':y0,'w':x1-x0,'h':y1-y0}, 'inkBounds': {'x':minx,'y':miny,'w':maxx-minx+1,'h':maxy-miny+1}, 'localLowerLidAnchor': [(minx+maxx+1)/2-x0,maxy+1-y0], 'components': len(comps), 'inkPixels': len(ink), 'minMarginPx': min(minx-x0,miny-y0,x1-maxx-1,y1-maxy-1)})
    widths = [f['inkBounds']['w'] for f in frames]
    previous = atlas['assets'][family]
    old_widths = [f['inkBounds']['w'] for f in previous['frames']]
    result['assets'][family] = {'file':result['file'],'columns':4,'rows':6,'rowBoundaries':row_bounds,'frameOffset':family_index*8,'frameCount':8,'poses':poses,'frames':frames,'widthRangePx':[min(widths),max(widths)],'widthVariationPercentOfRest':round((max(widths)-min(widths))*100/widths[0],2),'oldWidthVariationPercentOfRest':round((max(old_widths)-min(old_widths))*100/old_widths[0],2)}
result['allCelsOneConnectedComponent'] = all(f['components'] == 1 for a in result['assets'].values() for f in a['frames'])
result['allCelsHave16pxMargin'] = all(f['minMarginPx'] >= 16 for a in result['assets'].values() for f in a['frames'])
result['sampleCornerColors'] = [pixels[0,0],pixels[width-1,0],pixels[0,height-1],pixels[width-1,height-1]]
(BASE / 'eye_v2_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:result[key] for key in ['status','file','dimensions','sourceUnmodified','allCelsOneConnectedComponent','allCelsHave16pxMargin','sampleCornerColors']}))
for family, asset in result['assets'].items():
    print(family,asset['widthRangePx'],asset['widthVariationPercentOfRest'],asset['oldWidthVariationPercentOfRest'])
