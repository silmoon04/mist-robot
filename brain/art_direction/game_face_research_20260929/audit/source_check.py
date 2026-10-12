import concurrent.futures,hashlib,json,pathlib,subprocess
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).resolve().parent.parent;OUT=ROOT/'audit'/'sources';OUT.mkdir(exist_ok=True)
urls={}
for f in (ROOT/'branches').glob('*.json'):
 for e in json.loads(f.read_text(encoding='utf-8-sig')):
  for p in e.get('people',[]):urls.setdefault(p['sourceUrl'],[]).append({'id':e['id'],**p})
def get(pair):
 url,people=pair;stem=hashlib.sha256(url.encode()).hexdigest()[:16];p=OUT/(stem+'.html')
 r=subprocess.run(['curl.exe','-sS','-L','--max-time','25','-o',str(p),'-w','%{http_code}',url],capture_output=True,text=True)
 text=BeautifulSoup(p.read_text(encoding='utf-8',errors='replace'),'html.parser').get_text(' ',strip=True) if p.exists() else ''
 (OUT/(stem+'.txt')).write_text(text,encoding='utf-8')
 snippets=[]
 for person in people:
  name=person['name'];idx=text.lower().find(name.lower());snippets.append({'person':person,'found':idx>=0,'snippet':text[max(0,idx-200):idx+650] if idx>=0 else ''})
 return {'url':url,'httpStatus':r.stdout,'textPath':str(OUT/(stem+'.txt')),'people':snippets}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(get,urls.items()))
(OUT.parent/'source-validation.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(results,ensure_ascii=True,indent=2))
