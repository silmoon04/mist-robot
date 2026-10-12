"""Read surviving face assets and build audit-only contact sheets and metrics."""
from pathlib import Path
import collections
import hashlib
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cairosvg

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[4]
SRC = REPO / 'brain' / 'face_assets'
OUT.mkdir(parents=True, exist_ok=True)
FONT = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 16)
SMALL = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 13)

inventory = []
for path in sorted(SRC.rglob('*')):
    if not path.is_file():
        continue
    item = {'path': path.relative_to(SRC).as_posix(), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if path.suffix.lower() in {'.png', '.jpg', '.gif', '.webp'}:
        with Image.open(path) as im:
            item.update(width=im.width, height=im.height, frames=getattr(im, 'n_frames', 1))
    inventory.append(item)

def paste_fit(canvas, path_or_image, box):
    im = Image.open(path_or_image).convert('RGB') if isinstance(path_or_image, Path) else path_or_image.convert('RGB')
    im.thumbnail((box[2], box[3]), Image.Resampling.LANCZOS)
    canvas.paste(im, (box[0] + (box[2] - im.width)//2, box[1] + (box[3] - im.height)//2))

names = sorted(p.stem for p in (SRC/'svg').glob('*.svg'))
renders = OUT/'fitted_svg_renders'
renders.mkdir(exist_ok=True)
for name in names:
    cairosvg.svg2png(url=str(SRC/'svg'/f'{name}.svg'), write_to=str(renders/f'{name}.png'), output_width=800, output_height=512)

stages = ['Original preview', 'Extracted core', 'Normalized core', 'Cleaned raster', 'Fitted SVG', 'Canonical raster']
sheets = []
for page in range(8):
    sheet = Image.new('RGB', (1680, 1080), '#192027')
    d = ImageDraw.Draw(sheet)
    d.text((12,8), f'MIST surviving stages | faces {page*5+1:02d}-{page*5+5:02d} | original = left third of compare PNG', fill='white', font=FONT)
    for col, label in enumerate(stages):
        d.text((col*280+10,35),label,fill='#a2c2cd',font=FONT)
    for row,name in enumerate(names[page*5:page*5+5]):
        y=64+row*200
        d.text((10,y), name, fill='white', font=FONT)
        cmp = Image.open(SRC/'compare'/f'{name}.png')
        original = cmp.crop((0,0,cmp.width//3,cmp.height))
        sources=[original,SRC/'masks'/f'{name}_core.png',SRC/'normalized'/f'{name}_core.png',SRC/'cleaned'/f'{name}.png',renders/f'{name}.png',SRC/'canonical_renders'/f'{name}.png']
        for col, source in enumerate(sources):
            paste_fit(sheet,source,(col*280+5,y+24,270,173))
    path=OUT/f'stages_{page+1:02d}.png'
    sheet.save(path)
    sheets.append(path.name)

def simple_sheets(paths, prefix, cols, per_page, cell_width, cell_height):
    generated=[]
    for page, start in enumerate(range(0,len(paths),per_page)):
        subset=paths[start:start+per_page]
        rows=math.ceil(len(subset)/cols)
        sheet=Image.new('RGB',(cols*cell_width,45+rows*cell_height),'#192027')
        d=ImageDraw.Draw(sheet)
        d.text((10,10),f'MIST {prefix} | {start+1}-{start+len(subset)} of {len(paths)}',fill='white',font=FONT)
        for i,p in enumerate(subset):
            x=(i%cols)*cell_width; y=45+(i//cols)*cell_height
            label=p.stem.replace('_manual','').replace('_glow','')
            d.text((x+7,y+4),label,fill='white',font=SMALL)
            paste_fit(sheet,p,(x+5,y+28,cell_width-10,cell_height-34))
        path=OUT/f'{prefix}_{page+1:02d}.png'; sheet.save(path); generated.append(path.name)
    return generated

sheets+=simple_sheets(sorted((SRC/'masks').glob('*_glow.png')),'extracted_glow',5,20,300,225)
sheets+=simple_sheets(sorted((SRC/'part_crops').glob('*.png')),'part_crops',5,30,280,190)

faces=json.loads((SRC/'faces_canonical.json').read_text())
library=json.loads((SRC/'parts_library.json').read_text())
metrics=[]
for face in faces:
    item={'face':face['face'],'canonical_iou':face.get('canonical_iou'),'slots':{}}
    for role,entries in face['slots'].items():
        entries=entries if isinstance(entries,list) else [entries]
        for n,e in enumerate(entries):
            part=library[e['part']]
            p=np.array(part['points'],float)
            if e.get('mirror'): p[:,0]*=-1
            r=math.radians(e.get('rot',0)); c=math.cos(r); s=math.sin(r)
            p=p@np.array([[c,s],[-s,c]])+np.array([e['x'],e['y']])
            margin=part.get('width',0)/2 if part['kind']=='stroke' else 0
            bbox=[float(p[:,0].min()-margin),float(p[:,1].min()-margin),float(p[:,0].max()+margin),float(p[:,1].max()+margin)]
            label=role if len(entries)==1 else f'{role}_{n}'
            item['slots'][label]={'part':e['part'],'bbox':bbox,'outside_screen':bbox[0]<0 or bbox[1]<0 or bbox[2]>100 or bbox[3]>64,'bottom_margin':64-bbox[3]}
    item['outside_roles']=[r for r,v in item['slots'].items() if v['outside_screen']]
    metrics.append(item)

summary={'total_files':len(inventory),'files_by_extension':dict(collections.Counter(Path(i['path']).suffix for i in inventory)),
         'files_by_directory':dict(collections.Counter(Path(i['path']).parts[0] if len(Path(i['path']).parts)>1 else '.' for i in inventory)),
         'face_count':len(names),'canonical_part_count':len(library),'sheets':sheets,
         'original_source_directory_exists':(SRC.parent/'isolated_screens_highres').exists(),
         'metric_note':'Canonical bboxes include half stroke width, excluding glow. Coordinates use 100 x 64 screen. CairoSVG fitted renders verify geometry; its filter support may differ from a browser.'}
(OUT/'inventory.json').write_text(json.dumps({'summary':summary,'files':inventory},indent=2)+'\n')
(OUT/'canonical_geometry_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
print(json.dumps(summary,indent=2))
print('Outside screen:',[(m['face'],m['outside_roles']) for m in metrics if m['outside_roles']])
