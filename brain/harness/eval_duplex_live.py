"""Scripted real speech-to-speech conversations using synthetic microphone input."""
import argparse,asyncio,base64,json,time,wave
from pathlib import Path
import aiohttp

CASES=[
 ('greeting','Hello MIST. I finally finished your legs. What do you think?'),
 ('correction','Actually, they are only printed parts so far. Please do not pretend you can walk yet.'),
 ('tired','I have had a long day. I do not want advice, just a bit of company.'),
 ('humor','Okay, one tiny joke about being a robot with unfinished legs.'),
 ('sensors','Use your tools and tell me which sensor readings you actually have right now.'),
 ('pan','Use the phone pan preview tool to look thirty degrees left. The USB cable is disconnected.'),
 ('stop','Stop moving.'),
 ('remember','Remember that I prefer short replies and no jokes when I am tired.'),
 ('recall','What did I ask you to remember about how to talk to me?'),
 ('quiet','Be quiet for a moment. I will speak when I am ready.'),
 ('return','I am back. In one sentence, what should we test first on your new body?'),
]

async def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8790);p.add_argument('--code',required=True);p.add_argument('--limit',type=int,default=4);p.add_argument('--offset',type=int,default=0);p.add_argument('--out',type=Path,required=True);args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    base=f'http://127.0.0.1:{args.port}';origin={'Origin':base};rows=[];queue=asyncio.Queue();audio=bytearray();events=[]
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True),timeout=aiohttp.ClientTimeout(total=90)) as http:
        async with http.post(base+'/pair',headers=origin,json={'code':args.code}) as response:assert response.status==200
        async with http.ws_connect(base+'/voice',headers=origin,heartbeat=15) as ws:
            async def reader():
                async for msg in ws:
                    if msg.type!=aiohttp.WSMsgType.TEXT:continue
                    event=json.loads(msg.data);event['received_at']=time.monotonic()
                    if event['type']=='audio':audio.extend(base64.b64decode(event['pcm']))
                    else:events.append(event)
                    await queue.put(event)
            task=asyncio.create_task(reader())
            while True:
                event=await asyncio.wait_for(queue.get(),30)
                if event['type']=='error':raise RuntimeError(event['message'])
                if event['type']=='ready':break
            await asyncio.sleep(.4)
            await ws.send_json({'type':'sensors','packet':{'kind':'phone_motion','seq':1,'captured_at':time.time(),'values':{'ax':0,'ay':9.81,'az':0}}})
            for name,text in CASES[args.offset:args.offset+args.limit]:
                start=time.monotonic();first_audio=None;transcripts=[];tools=[];errors=[];warnings=[];metrics=[];user_done=None;mic_end=None
                await ws.send_json({'type':'fixture','text':text})
                deadline=start+36;done_at=None;fixture_done=False;matched_user=False
                while time.monotonic()<deadline:
                    if done_at and fixture_done and matched_user and time.monotonic()-done_at>3:break
                    try:event=await asyncio.wait_for(queue.get(),.2)
                    except asyncio.TimeoutError:continue
                    kind=event['type']
                    if kind=='fixture_finished':fixture_done=True;mic_end=time.monotonic()
                    if kind=='audio' and first_audio is None:first_audio=time.monotonic()
                    if kind=='transcript_done':
                        transcripts.append({'role':event['role'],'text':event['text']})
                        if event['role']=='user':user_done=time.monotonic();matched_user=True
                        if event['role']=='assistant':done_at=time.monotonic()
                    if kind=='tool':tools.append(event)
                    if kind=='latency':metrics.append(event.get('tts',event.get('conversion')))
                    if kind=='error':errors.append({'message':event['message'],'code':event.get('code')})
                    if kind=='voice_warning':warnings.append({'message':event['message'],'code':event.get('code')})
                row={'case':name,'input':text,'transcripts':transcripts,'tools':tools,'errors':errors,'warnings':warnings,
                    'first_converted_audio_from_request_s':None if first_audio is None else first_audio-start,
                    'first_converted_audio_from_user_transcript_done_s':None if first_audio is None or user_done is None else first_audio-user_done,
                    'last_fixture_frame_to_first_converted_audio_s':None if first_audio is None or mic_end is None else first_audio-mic_end,
                    'conversion':metrics,'elapsed_s':time.monotonic()-start}
                rows.append(row);print(json.dumps(row,ensure_ascii=True),flush=True)
                (args.out/'conversations.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
                if errors:break
            await ws.close();await task
    with wave.open(str(args.out/'converted_conversation.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(audio)
    (args.out/'events.json').write_text(json.dumps(events,indent=2),encoding='utf-8')

if __name__=='__main__':asyncio.run(main())
