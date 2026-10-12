"""Assemble labeled audit views of the exported Aseprite sheet without edits."""
from pathlib import Path
import json, math, hashlib, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE=Path(__file__).resolve().parent
FACE=BASE.parent
OUT=BASE if len(sys.argv)<2 else BASE/sys.argv[1]
assert OUT.resolve().is_relative_to(BASE.resolve())
SOURCE=FACE.parents[3]/'brain'/'face_assets'
OUT.mkdir(exist_ok=True)
frame_path=FACE/'animation_frames.json'
sheet_path=FACE/'aseprite_check'/'aseprite_frames.png'
meta_path=FACE/'aseprite_check'/'aseprite_frames.json'
animation=json.loads(frame_path.read_text(encoding='utf-8'))
frames=animation['frames']
meta=json.loads(meta_path.read_text(encoding='utf-8'))
sheet=Image.open(sheet_path).convert('RGBA')
assert len(frames)==len(meta['frames'])==450
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',13)
def frame_image(i):
    r=meta['frames'][i]['frame']
    crop=sheet.crop((r['x'],r['y'],r['x']+r['w'],r['y']+r['h']))
    bg=Image.new('RGBA',crop.size,'#07090c'); bg.alpha_composite(crop)
    return bg.convert('RGB')

pages=[]
for page in range(9):
    ids=range(page*50,min(page*50+50,len(frames)))
    out=Image.new('RGB',(2000,975),'#20282f')
    d=ImageDraw.Draw(out)
    d.text((12,10),f'MIST Aseprite export | frames {page*50:03d}-{page*50+49:03d} (zero-based) | native pixels, labeled audit layout',font=font,fill='white')
    for j,i in enumerate(ids):
        x=(j%10)*200; y=45+(j//10)*184
        label=frames[i]['label']; parts=label.split(' ')
        d.text((x+5,y),f'{i:03d} '+parts[0].replace('_manual',''),font=small,fill='white')
        d.text((x+5,y+18),' '.join(parts[1:]),font=small,fill='#b7c9d2')
        out.paste(frame_image(i),(x,y+40))
    name=f'frames_{page+1:02d}.png'; out.save(OUT/name); pages.append(name)

metrics=[]
for i,f in enumerate(frames):
    a=np.asarray(frame_image(i))
    cyan=(a[:,:,1]>35)&(a[:,:,1]>a[:,:,0]*1.3)
    ys,xs=np.where(cyan)
    bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None
    visible=[l for l in f['layers'] if l.get('opacity',1)>0.001]
    layer_bounds=[]
    for n,l in enumerate(visible):
        p=np.asarray(l['points'],float)
        if not len(p): continue
        pad=l.get('width',0)/2 if l['mode']=='stroke' else 0
        b=[float(p[:,0].min()-pad),float(p[:,1].min()-pad),float(p[:,0].max()+pad),float(p[:,1].max()+pad)]
        layer_bounds.append({'layer':n,'role':l['role'],'opacity':l.get('opacity',1),'bbox':b,'outside':b[0]<0 or b[1]<0 or b[2]>100 or b[3]>64})
    metrics.append({'index':i,'label':f['label'],'raster_cyan_bbox':bbox,
                    'minimum_raster_padding':min(bbox[0],bbox[1],200-bbox[2],128-bbox[3]) if bbox else None,
                    'visible_layer_count':len(visible),'layer_bounds':layer_bounds})
(OUT/'frame_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')

selected=[13,28,32,15,18,27,39]
comparison=Image.new('RGB',(1600,len(selected)*230+70),'#20282f')
d=ImageDraw.Draw(comparison)
d.text((10,10),'MIST settled pose comparison | original preview / source canonical / new Aseprite settled / new settled enlarged',fill='white',font=font)
for row,num in enumerate(selected):
    index=(num-1)*10+9; name=frames[index]['expression']; y=row*230+50
    d.text((10,y),f'{name} | export frame {index:03d}',fill='white',font=font)
    orig=Image.open(SOURCE/'compare'/f'{name}.png').convert('RGB'); orig=orig.crop((0,0,orig.width//3,orig.height))
    canon=Image.open(SOURCE/'canonical_renders'/f'{name}.png').convert('RGB')
    for col,im in enumerate([orig,canon,frame_image(index)]):
        im.thumbnail((310,198),Image.Resampling.LANCZOS); comparison.paste(im,(col*320+5,y+24))
    large=frame_image(index).resize((600,384),Image.Resampling.NEAREST)
    large.thumbnail((620,198),Image.Resampling.NEAREST); comparison.paste(large,(980,y+24))
comparison.save(OUT/'settled_comparison.png')
snapshot={'frame_count':len(frames),'sheet_size':sheet.size,'pages':pages,'sources':{str(p.relative_to(FACE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [frame_path,sheet_path,meta_path,FACE/'settled_frames.json']},
          'outside_vector_frames':[m['index'] for m in metrics if any(l['outside'] for l in m['layer_bounds'])],
          'raster_edge_frames':[m['index'] for m in metrics if m['minimum_raster_padding']==0],
          'minimum_raster_padding':min(m['minimum_raster_padding'] for m in metrics if m['minimum_raster_padding'] is not None)}
(OUT/'snapshot.json').write_text(json.dumps(snapshot,indent=2)+'\n')
print(json.dumps(snapshot,indent=2))
