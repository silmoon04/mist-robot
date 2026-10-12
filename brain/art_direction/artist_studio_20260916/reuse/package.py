from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import csv,hashlib,json,zipfile
import cairosvg
from PIL import Image,ImageDraw,ImageFont

OUT=Path(__file__).resolve().parent
def render(p):
 target=p.with_suffix('.png');cairosvg.svg2png(url=str(p),write_to=str(target),output_width=800,output_height=512)
 with Image.open(target) as im:
  assert im.mode=='RGBA' and im.size==(800,512)
 return target
def sheet(paths,name,cols=6):
 w,h=220,166;im=Image.new('RGB',(cols*w,((len(paths)+cols-1)//cols)*h),'#f6f6f2');draw=ImageDraw.Draw(im)
 font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',12)
 for i,p in enumerate(paths):
  x,y=i%cols*w,i//cols*h
  tile=Image.new('RGBA',(208,134),'#0c1411');src=Image.open(p).convert('RGBA');src.thumbnail((208,134));tile.alpha_composite(src,((208-src.width)//2,(134-src.height)//2));im.paste(tile.convert('RGB'),(x+6,y+4));draw.text((x+8,y+142),p.stem,fill='#252923',font=font)
 im.save(OUT/name)
def main():
 paths=sorted(OUT.rglob('*.svg'))
 with ThreadPoolExecutor(max_workers=4) as pool:
  for i,_ in enumerate(pool.map(render,paths)):
   if i%250==0:print('Raster frames',i,flush=True)
 audit=json.loads((OUT/'audit.json').read_text());clips=json.loads((OUT/'clips.json').read_text())
 for kind in ['eyes','mouths']:
  sheet([OUT/'parts'/(g['id']+'.png') for g in audit['groups'] if g['kind']==kind],kind+'_sheet.png')
 sheet(sorted((OUT/'faces').glob('*.png')),'faces_sheet.png',5)
 for c in clips:
  with (OUT/'clips'/c['id']/'timing.csv').open('w',newline='') as f:
   w=csv.writer(f);w.writerow(['frame','duration_ms','png','svg'])
   for i in range(c['frames']):w.writerow([i,125,f'{i:03d}.png',f'{i:03d}.svg'])
 # The pack contains sources, reports, the offline viewer and all split layers.
 files=[p for p in OUT.rglob('*') if p.is_file() and p.suffix not in {'.zip','.py','.cjs'} and p.name!='validation.json']
 target=OUT/'MIST_reuse_pack.zip'
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for p in files:z.write(p,p.relative_to(OUT))
 with zipfile.ZipFile(target) as z:assert z.testzip() is None
 result={'passed':True,'svg_files':len(paths),'png_files':len(list(OUT.rglob('*.png'))),'base_parts':len(audit['groups']),'faces':len(audit['faces']),'isolated_face_layers':len(list((OUT/'instances').rglob('*.png'))),'archived_composite_frames':len(list((OUT/'archive').glob('*.png'))),'archived_split_layers':len(list((OUT/'archive_layers').rglob('*.png'))),'clips_8fps':len(clips),'frames_8fps':sum(c['frames'] for c in clips),'zip_bytes':target.stat().st_size,'zip_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
 assert result['base_parts']==53 and result['isolated_face_layers']==120 and result['archived_composite_frames']==450
 (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
