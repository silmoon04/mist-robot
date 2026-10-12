from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import json, hashlib

ROOT=Path(__file__).resolve().parent
PARTS=ROOT.parents[2]/'parts'
CANVAS=(128,64)
ANCHOR=(64,26)

def palette(im):
    # Production palette normalization preserves the complete generated alpha silhouette.
    ink=Image.new('RGBA',im.size,'#5eeadd')
    ink.putalpha(im.getchannel('A'))
    return ink

def bounds(im):
    a=np.array(im.getchannel('A'))
    yy,xx=np.where(a>16)
    return (int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))

def attach(im, family):
    a=np.array(im.getchannel('A'))
    x0,y0,x1,y1=bounds(im)
    cx=(x0+x1)/2
    width=x1-x0
    # Register the authored mouth corners, rather than the changing height.
    # The samples lie inside the rounded ends so anti-aliased cap tips do not drift.
    xs=[round(x0+width*.075),round(x1-width*.075)]
    centers=[]
    for x in xs:
        ys=np.where(a[:,x]>100)[0]
        centers.append(float((ys.min()+ys.max())/2))
    return cx,float(sum(centers)/2)

def place(im, scale, attachment):
    # One scale for an entire source sheet. Registration only translates pixels.
    width=round(im.width*scale); height=round(im.height*scale)
    scaled=im.resize((width,height),Image.Resampling.LANCZOS)
    target=Image.new('RGBA',CANVAS)
    at=(round(ANCHOR[0]-attachment[0]*scale),round(ANCHOR[1]-attachment[1]*scale))
    target.alpha_composite(scaled,at)
    return target,at

canonical=Image.open(PARTS/'mouth_line_30.png').convert('RGBA')
cb=bounds(canonical)
neutral,_=place(canonical,80/(cb[2]-cb[0]),((cb[0]+cb[2])/2,(cb[1]+cb[3])/2))
neutral=palette(neutral)
neutral.save(ROOT/'neutral.png')
aggregate=Image.new('RGB',(768,240),'#101f22')
draw=ImageDraw.Draw(aggregate)
for row,family in enumerate(['smile','bowl','concern']):
    folder=ROOT/family
    im=Image.open(folder/'source.png').convert('RGBA')
    w,h=im.size
    crops=[im.crop((i%3*w//3,i//3*h//2,(i%3+1)*w//3,(i//3+1)*h//2)) for i in range(6)]
    widths=[bounds(c)[2]-bounds(c)[0] for c in crops]
    scale=80/float(np.median(widths))
    frames=[]; records=[]
    for i,c in enumerate(crops):
        attachment=attach(c,family)
        cel,offset=place(c,scale,attachment)
        origin='ImageGen source sheet'
        if i==0:
            cel=neutral.copy()
            origin='Original MIST mouth_line_30; shared exact neutral'
        cel=palette(cel)
        path=folder/f'cell_{i}.png'
        cel.save(path)
        background=Image.new('RGBA',CANVAS,'#101f22'); background.alpha_composite(cel)
        aggregate.paste(background.convert('RGB'),(i*128,row*80))
        draw.text((i*128+5,row*80+64),f'{family} {i}',fill='#d6ece8')
        frames.append(background.convert('RGB'))
        records.append({'index':i,'file':path.name,'origin':origin,'sourceBounds':bounds(c),'sourceAttachment':attachment,'translationPx':offset,'outputBounds':bounds(cel),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    contact=Image.new('RGB',(768,80),'#101f22')
    contact.paste(aggregate.crop((0,row*80,768,row*80+80)),(0,0))
    contact.save(folder/'dark_contact.png')
    play=frames+frames[-2:0:-1]
    play[0].save(folder/'preview.gif',save_all=True,append_images=play[1:],duration=[400]+[100]*4+[350]+[100]*4,loop=0,disposal=2)
    (folder/'metadata.json').write_text(json.dumps({'family':family,'cellCanvas':CANVAS,'attachment':ANCHOR,'sheetScale':scale,'generatedCelCount':6,'usedGeneratedCelCount':5,'canonicalNeutral':True,'palette':'RGB#5eeadd; original alpha preserved after common-scale resampling','registration':'mouth corner centers at7.5%width; x centered; no vertical bbox centering','frames':records},indent=2))
aggregate.save(ROOT/'all_contacts.png')
print('Wrote18commoncanvas cels;15newdrawings plus3copiesofcanonicalneutral')
