from PIL import Image, ImageDraw
from pathlib import Path
import json, hashlib

ROOT = Path(__file__).resolve().parent
INK = (94,234,221)
SIZE = (128,112)
ANCHOR = (64,92)
WIDTH = 86

def shape_bounds(im):
    return im.getchannel('A').point(lambda a: 255 if a >= 32 else 0).getbbox()

def tint(im):
    rgba = Image.new('RGBA', im.size, (*INK,0))
    rgba.putalpha(im.getchannel('A'))
    return rgba

def align(im, scale):
    # One common uniform scale per family; translation alone registers each attachment.
    resized = im.resize((round(im.width*scale),round(im.height*scale)), Image.Resampling.LANCZOS)
    box = shape_bounds(resized)
    out = Image.new('RGBA',SIZE)
    left = round(ANCHOR[0] - (box[0]+box[2])/2)
    top = ANCHOR[1] - box[3]
    out.alpha_composite(tint(resized), (left,top))
    return out

manifest = {'version':1,'dimensions':list(SIZE),'attachment':list(ANCHOR),'openWidthPx':WIDTH,
    'ink':'#5eeadd','normalization':'Fixed uniform scale per family; translation aligns bottom attachment. Generated alpha retained; RGB replaced with common MIST ink as explicitly requested by lead agent. Cell 0 is canonical source; cell 5 is shared closure.',
    'families':{}}
for name,version in [('round',4),('hook',3)]:
    src = ROOT/name/f'source_v{version}.png'
    sheet = Image.open(src).convert('RGBA')
    crops = [sheet.crop(((i%3)*512,(i//3)*512,(i%3+1)*512,(i//3+1)*512)) for i in range(6)]
    first = shape_bounds(crops[0])
    scale = WIDTH/(first[2]-first[0])
    cells = [align(c,scale) for c in crops]
    native=Image.open(ROOT/f'{name}_reference.png').convert('RGBA')
    native_bounds=shape_bounds(native)
    cells[0]=align(native,WIDTH/(native_bounds[2]-native_bounds[0]))
    if name == 'hook': cells[5]=Image.open(ROOT/'round'/'cell_5.png').convert('RGBA')
    contact=Image.new('RGBA',(128*6,144),(15,29,32,255))
    draw=ImageDraw.Draw(contact)
    frames=[]
    for i,im in enumerate(cells):
        p=ROOT/name/f'cell_{i}.png'; im.save(p)
        contact.alpha_composite(im,(128*i,0)); draw.text((128*i+10,121),f'{i+1} '+('canonical' if i==0 else 'closed' if i==5 else 'drawn'),fill=(190,205,204))
        frames.append({'file':f'{name}/cell_{i}.png','bounds':list(shape_bounds(im)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
            'source':f'{name}_reference.png' if i==0 else 'round/source_v4.png#cell5' if i==5 else f'{name}/source_v{version}.png#cell{i}'})
    contact.save(ROOT/name/'contact_final.png')
    manifest['families'][name]={'selectedSource':str(src.relative_to(ROOT)).replace('\\','/'),'sourceSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'uniformScale':scale,'cells':frames}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
combined=Image.new('RGBA',(768,288),(15,29,32,255))
for row,name in enumerate(['round','hook']): combined.alpha_composite(Image.open(ROOT/name/'contact_final.png'),(0,row*144))
combined.save(ROOT/'contact_final.png')
print(json.dumps({n: [c['bounds'] for c in v['cells']] for n,v in manifest['families'].items()}))
