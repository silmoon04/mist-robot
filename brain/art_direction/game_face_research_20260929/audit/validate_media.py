"""Read-only branch media validation; writes audit evidence only. No video downloads."""
import concurrent.futures, datetime, hashlib, json, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'audit'
def check(item):
    url, refs = item
    p = subprocess.run(['curl.exe','-sS','-L','-I','--max-time','25','-w','\n%{http_code}\t%{content_type}\t%{url_effective}',url],capture_output=True,text=True)
    lines=p.stdout.strip().splitlines()
    fields=lines[-1].split('\t') if lines else []
    return {'url':url,'references':refs,'httpStatus':fields[0] if fields else None,'contentType':fields[1] if len(fields)>1 else None,'effectiveUrl':fields[2] if len(fields)>2 else None,'curlExit':p.returncode,'error':p.stderr.strip(),'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def main():
    urls={}; files=[]
    for f in sorted((ROOT/'branches').glob('*.json')):
        data=f.read_bytes(); files.append({'path':str(f.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest()})
        entries=json.loads(data.decode('utf-8-sig'))
        if isinstance(entries,dict): entries=entries.get('entries',[])
        for e in entries:
            for i,m in enumerate(e.get('media',[])):
                urls.setdefault(m['url'],[]).append({'entry':e['id'],'index':i,'kind':m.get('kind'),'claimedVerified':m.get('verified'),'claimedMotionVerified':m.get('motionVerified')})
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(check,urls.items()))
    (OUT/'http-validation.json').write_text(json.dumps({'branchFiles':files,'results':results},indent=2),encoding='utf-8')
    print(json.dumps({'files':len(files),'urls':len(results),'non200':[{ 'url':r['url'],'status':r['httpStatus'],'error':r['error']} for r in results if r['httpStatus']!='200']},indent=2))
if __name__=='__main__': main()
