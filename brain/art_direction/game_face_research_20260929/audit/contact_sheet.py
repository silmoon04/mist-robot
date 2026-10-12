import concurrent.futures,json,pathlib,subprocess
from PIL import Image,ImageOps,ImageDraw
ROOT=pathlib.Path(__file__).resolve().parent.parent; OUT=ROOT/'audit'; (OUT/'images').mkdir(exist_ok=True)
items=[]
for f in sorted((ROOT/'branches').glob('*.json')):
 for e in json.loads(f.read_text(encoding='utf-8-sig')):
  for i,m in enumerate(e.get('media',[])):
   if m.get('kind') in ['image','gif']: items.append({'id':e['id'],'index':i,**m})
def get(pair):
 n,m=pair;p=OUT/'images'/f'{n:02d}.asset';r=subprocess.run(['curl.exe','-sS','-L','--max-time','30','-o',str(p),m['url']],capture_output=True)
 try:
  im=Image.open(p);m.update({'auditNumber':n,'width':im.width,'height':im.height,'frames':getattr(im,'n_frames',1),'localPath':str(p)})
 except Exception as ex:m['error']=str(ex)
 return m
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:items=list(pool.map(get,enumerate(items)))
(OUT/'image-metadata.json').write_text(json.dumps(items,indent=2),encoding='utf-8')
for batch in range(0,len(items),12):
 subset=items[batch:batch+12];sheet=Image.new('RGB',(1200,330*((len(subset)+2)//3)), '#dddddd');draw=ImageDraw.Draw(sheet)
 for j,m in enumerate(subset):
  x=(j%3)*400;y=(j//3)*330
  if 'localPath' in m:
   im=Image.open(m['localPath']).convert('RGBA');base=Image.new('RGBA',im.size,'white');base.alpha_composite(im);im=ImageOps.contain(base.convert('RGB'),(390,290));sheet.paste(im,(x+(400-im.width)//2,y))
  draw.text((x+4,y+294),f"{m.get('auditNumber','?')} {m['id'][:42]}\nmedia {m['index']}",fill='black')
 sheet.save(OUT/f'contact-{batch//12}.jpg')
print(len(items))
