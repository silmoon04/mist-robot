"""One short live phrase, reporting protocol fields without credentials or audio data."""
import asyncio
import base64
import json
from pathlib import Path
import sys
import time
import aiohttp

BRAIN=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BRAIN))
from pi_client import load_env
from duplex.conversion import VOICE


async def main():
    key=load_env()['ELEVENLABS_API_KEY'].strip('"\'')
    url=f'wss://api.elevenlabs.io/v1/text-to-speech/{VOICE}/multi-stream-input?model_id=eleven_flash_v2_5&output_format=pcm_24000&inactivity_timeout=180'
    started=time.monotonic();total=0;closed=False
    async with aiohttp.ClientSession() as client:
        async with client.ws_connect(url,headers={'xi-api-key':key}) as socket:
            await socket.send_json({'context_id':'finish-probe','text':"Maybe. No rush. I'm here, and I'm listening. ",'flush':True,
                'voice_settings':{'stability':.5,'similarity_boost':.8,'use_speaker_boost':False},
                'generation_config':{'chunk_length_schedule':[120,160,250,290]}})
            for _ in range(20):
                try:
                    msg=await asyncio.wait_for(socket.receive(),3)
                except asyncio.TimeoutError:
                    if closed:break
                    await socket.send_json({'context_id':'finish-probe','close_context':True});closed=True
                    print(json.dumps({'sent':'close_context_after_3s_idle','elapsed':round(time.monotonic()-started,3)}),flush=True)
                    continue
                if msg.type!=aiohttp.WSMsgType.TEXT:
                    print(json.dumps({'type':str(msg.type)}),flush=True);break
                value=json.loads(msg.data);raw=base64.b64decode(value.get('audio') or '')
                total+=len(raw);alignment=value.get('normalizedAlignment') or value.get('normalized_alignment') or value.get('alignment') or {}
                print(json.dumps({'elapsed':round(time.monotonic()-started,3),'keys':list(value),'audio_bytes':len(raw),'total_bytes':total,
                    'isFinal':value.get('isFinal',value.get('is_final')),'contextId':value.get('contextId',value.get('context_id')),'alignmentKeys':list(alignment),
                    'text':''.join(alignment.get('chars',[])),'error':str(value.get('error','')).replace(key,'[redacted]')[:200]}),flush=True)
                if value.get('isFinal') or value.get('is_final'):break

if __name__=='__main__':asyncio.run(main())
