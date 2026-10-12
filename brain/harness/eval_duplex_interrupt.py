"""Interrupt audible converted speech and verify generation replacement."""
import argparse,asyncio,base64,json,time,wave
from pathlib import Path
import aiohttp

async def main():
    p=argparse.ArgumentParser();p.add_argument('--native-turn-only',action='store_true');p.add_argument('--port',type=int,default=8790);p.add_argument('--code',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    base=f'http://127.0.0.1:{a.port}';headers={'Origin':base};events=[];samples=bytearray();reset_time=None;sent_time=None;reset_epoch=None;stale=0;new_audio=0;interrupted=False;ready=False;finished=False
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as http:
        async with http.post(base+'/pair',headers=headers,json={'code':a.code}) as r:assert r.status==200
        async with http.ws_connect(base+'/voice',headers=headers,heartbeat=15) as ws:
            deadline=time.monotonic()+70
            while time.monotonic()<deadline:
                try:msg=await asyncio.wait_for(ws.receive(),1)
                except asyncio.TimeoutError:continue
                if msg.type!=aiohttp.WSMsgType.TEXT:break
                e=json.loads(msg.data);kind=e['type']
                if kind=='ready' and not ready:
                    ready=True;await ws.send_json({'type':'fixture','text':'Tell me a fairly long story about your first day as a tiny robot.'})
                if kind=='audio':
                    samples.extend(base64.b64decode(e['pcm']))
                    if not interrupted:
                        interrupted=True;sent_time=time.monotonic()
                        if not a.native_turn_only:await ws.send_json({'type':'barge_in'})
                        await ws.send_json({'type':'fixture','text':'Actually stop the story. Please just say blue teacup, then wait.'})
                    elif reset_epoch is not None:
                        if e['epoch']<reset_epoch:stale+=1
                        else:new_audio+=1
                else:
                    events.append({**e,'at':time.monotonic()})
                    if kind=='audio_reset' and interrupted and reset_epoch is None:reset_time=time.monotonic();reset_epoch=e['epoch']
                    if kind=='transcript_done' and e.get('role')=='assistant' and 'teacup' in e.get('text','').lower():finished=True;deadline=min(deadline,time.monotonic()+4)
                    if kind=='error':break
            await ws.close()
    report={'interrupted':interrupted,'reset_ack_ms':None if reset_time is None else (reset_time-sent_time)*1000,
        'stale_generation_packets_after_reset':stale,'new_generation_audio_packets':new_audio,'correction_followed':finished,
        'passed':interrupted and reset_time is not None and stale==0 and new_audio>0 and finished,
        'limits':['Synthetic audio input and client-observed packets; not a measurement of room echo or human perception.','The browser playback stop is independently tested with fake audio sources.'],
        'events':events}
    (a.out/'interruption.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with wave.open(str(a.out/'interruption.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(samples)
    print(json.dumps({k:v for k,v in report.items() if k!='events'}),flush=True)

if __name__=='__main__':asyncio.run(main())
