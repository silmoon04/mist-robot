import concurrent.futures,hashlib,json,pathlib
from validate_media import check
ROOT=pathlib.Path(__file__).resolve().parent.parent
p=ROOT/'board'/'catalog.json';data=p.read_bytes();entries=json.loads(data)
urls={}
for e in entries:
 for i,m in enumerate(e['media']):urls.setdefault(m['url'],[]).append({'entry':e['id'],'index':i,'kind':m['kind'],'verified':m.get('verified'),'motionVerified':m.get('motionVerified')})
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(check,urls.items()))
out={'catalogPath':str(p),'sha256':hashlib.sha256(data).hexdigest(),'studies':len(entries),'mediaCount':sum(len(e['media']) for e in entries),'uniqueUrls':len(urls),'results':results}
(ROOT/'audit'/'final-catalog-validation.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in out.items() if k!='results'},indent=2));print(json.dumps([r for r in results if r['httpStatus']!='200'],indent=2))
