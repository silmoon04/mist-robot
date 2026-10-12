"""Start a real analyst while the real conversation is already producing speech."""
import asyncio,json,time
from pathlib import Path
import aiohttp

async def main():
    out=Path('brain/results/layered_brain_20260914');events=[];started=None;finished=None;sent=None;overlap=0;asked=False
    base='http://127.0.0.1:8791'
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as http:
        async with http.post(base+'/pair',headers={'Origin':base},json={'code':'quality-local-test'}) as r:assert r.status==200
        async with http.ws_connect(base+'/voice',headers={'Origin':base}) as ws:
            deadline=time.monotonic()+65
            while time.monotonic()<deadline:
                try:m=await asyncio.wait_for(ws.receive(),1)
                except asyncio.TimeoutError:continue
                if m.type!=aiohttp.WSMsgType.TEXT:break
                e=json.loads(m.data);now=time.perf_counter()
                if e['type']=='ready':await ws.send_json({'type':'fixture','text':'Tell me a fairly long story about a tiny robot learning to recognize rain. Take about twenty seconds.'})
                if e['type']=='audio':
                    if sent is None:
                        sent=now
                        await ws.send_json({'type':'start_background','question':'Use your sensor and preference tools, then compare three approaches to validating a quadruped before a first physical test. State missing evidence and recommend one practical next step.'})
                    elif started is not None and finished is None:overlap+=1
                else:events.append({**e,'at':now})
                if e['type']=='brain_job' and e['status']=='running':started=now
                if e['type']=='brain_job' and e['status']=='complete':finished=now
                if finished is not None and overlap>0:
                    await ws.send_json({'type':'barge_in'});break
                if e['type']=='error':break
    result={'audio_packets_during_real_analysis':overlap,'submission_receipt_ms':None if started is None else (started-sent)*1000,
            'analysis_s':None if finished is None else finished-started,'passed':overlap>0 and finished is not None,
            'limits':'Client-observed speech packets overlap a real read-only model job. This is not a room-acoustics test.'}
    (out/'parallel_audio.json').write_text(json.dumps({**result,'events':events},indent=2),encoding='utf-8');print(json.dumps(result));assert result['passed']

asyncio.run(main())
