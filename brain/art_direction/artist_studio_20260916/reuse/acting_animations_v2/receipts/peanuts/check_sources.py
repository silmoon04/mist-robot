from PIL import Image
from pathlib import Path
import numpy as np,hashlib,json
root=Path('brain/art_direction/artist_studio_20260916/reuse/acting_animations_v2')
sources={
'company':'exec-ea427dc1-b21e-4772-9dc1-2fecda918652.png',
'wry':'exec-88144150-0967-401b-a430-0048acbdb80e.png',
'pride':'exec-08ce5279-4ddc-47a1-8153-a1819e1780f7.png'}
for name,source in sources.items():
 p=root/'source'/'peanuts'/(name+'.png')
 im=Image.open(p).convert('RGBA')
 a=np.array(im)[:,:,3]
 frames=[]
 for i in range(12):
  c=i%4;r=i//4
  box=(c*384,round(r*1024/3),(c+1)*384,round((r+1)*1024/3))
  f=im.crop(box); fa=np.array(f)[:,:,3]
  yy,xx=np.where(fa>16)
  edges=np.r_[fa[0],fa[-1],fa[:,0],fa[:,-1]]
  frames.append({'frame':i,'sourceRect':[box[0],box[1],box[2]-box[0],box[3]-box[1]],'visibleAlphaBounds':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],'rgbaSha256':hashlib.sha256(f.tobytes()).hexdigest(),'edgeAlphaMax':int(edges.max()),'occupiedFraction':round(float(np.count_nonzero(fa)/fa.size),6)})
 receipt={'exampleId':name,'groupId':'peanuts','generator':'built-in image_gen.imagegen','sourceFile':'source/peanuts/'+name+'.png','generatedFileName':source,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':list(im.size),'mode':im.mode,'frameCount':12,'uniqueRgbaCrops':len(set(f['rgbaSha256'] for f in frames)),'alphaExtrema':[int(a.min()),int(a.max())],'occupiedFraction':round(float(np.count_nonzero(a)/a.size),6),'frames':frames,'review':['Composited onto #101c20 to inspect actual RGBA. Tool RGB thumbnail falsely suggests glow; delivered alpha excludes it.','Fixed grid 4x3; crop edge alpha at most 1/255; no visible clipping; independent eye and mouth crops possible.','Raw generated row registration drifts vertically by several dozen pixels. Compiler should normalize feature anchors using crop metadata, without redrawing artwork.','Blink closes as curved lid strokes at frame3. Pride regenerated to replace premature frame2 full closure with partial closure.'],'promptFiles':['prompts/peanuts/'+name+'.txt']+(['prompts/peanuts/pride-blink-correction.txt'] if name=='pride' else [])}
 (root/'receipts'/'peanuts'/(name+'.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 print(name,receipt['sha256'],receipt['uniqueRgbaCrops'],receipt['occupiedFraction'],[f['edgeAlphaMax'] for f in frames])


