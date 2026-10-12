import asyncio,json,re,sys,wave
from pathlib import Path
import aiohttp
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pi_client import load_env

async def main():
    out=Path('brain/results/layered_brain_20260914/phrases');rows=[]
    cases={'clause':'I can keep the beginning quite short, and explain the rest while you listen. This should stay one connected thought.',
           'sentences':'That worked! We can try the next step. No rush, though. I am still listening.'}
    async with aiohttp.ClientSession() as http:
        for name,expected in cases.items():
            with wave.open(str(out/f'{name}_phrases.wav'),'rb') as w:raw=w.readframes(w.getnframes())
            async with http.post('https://api.deepgram.com/v1/listen?model=nova-3&encoding=linear16&sample_rate=24000&channels=1',headers={'Authorization':'Token '+load_env()['DEEPGRAM_API_KEY'],'Content-Type':'application/octet-stream'},data=raw) as r:
                assert r.status==200;d=await r.json();heard=d['results']['channels'][0]['alternatives'][0]['transcript']
            clean=lambda s:re.sub('[^a-z]','',s.lower())
            rows.append({'case':name,'recognized':heard,'passed':clean(heard)==clean(expected)})
    (out/'recognition.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(rows));assert all(r['passed'] for r in rows)

asyncio.run(main())
