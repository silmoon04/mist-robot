import concurrent.futures,hashlib,html,json,pathlib,subprocess,urllib.parse
ROOT=pathlib.Path(__file__).resolve().parent.parent;OUT=ROOT/'audit'/'media-sources';OUT.mkdir(exist_ok=True)
groups={}
for f in (ROOT/'branches').glob('*.json'):
 for e in json.loads(f.read_text(encoding='utf-8-sig')):
  for i,m in enumerate(e.get('media',[])):
   groups.setdefault(m['sourceUrl'],[]).append({'id':e['id'],'index':i,'url':m['url']})
def get(pair):
 source,media=pair;p=OUT/(hashlib.sha256(source.encode()).hexdigest()[:16]+'.html')
 r=subprocess.run(['curl.exe','-sS','-L','--max-time','25','-o',str(p),'-w','%{http_code}',source],capture_output=True,text=True)
 content=html.unescape(p.read_text(encoding='utf8',errors='replace')).replace('\\/','/') if p.exists() else ''
 for m in media:
  path=urllib.parse.urlsplit(m['url']).path;filename=path.rsplit('/',1)[-1]
  m['exactUrlPresent']=m['url'] in content
  m['pathPresent']=bool(path and path in content)
  m['filenamePresent']=bool(filename and filename in content)
 return {'sourceUrl':source,'httpStatus':r.stdout,'media':media}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(get,groups.items()))
(OUT.parent/'media-source-validation.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print(json.dumps({'sources':len(results),'exactOrPath':sum(m['exactUrlPresent'] or m['pathPresent'] for s in results for m in s['media']),'total':sum(len(s['media']) for s in results)},indent=2))
