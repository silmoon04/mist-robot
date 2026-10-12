"""Probe provider message boundaries using synthetic, non-personal text."""
import asyncio, base64, json, sys, time
from pathlib import Path
import aiohttp
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pi_client import load_env
from duplex.conversion import VOICE

async def main():
    start=time.monotonic()
    async with aiohttp.ClientSession() as http:
        async with http.ws_connect(f'wss://api.elevenlabs.io/v1/text-to-speech/{VOICE}/multi-stream-input?model_id=eleven_flash_v2_5&output_format=pcm_24000&inactivity_timeout=180',headers={'xi-api-key':load_env()['ELEVENLABS_API_KEY']}) as ws:
            print('connected',round(time.monotonic()-start,3),flush=True)
            await ws.send_json({'context_id':'test','text':' ','voice_settings':{'stability':.5,'similarity_boost':.8,'use_speaker_boost':False},'generation_config':{'chunk_length_schedule':[50,120,160,250]}})
            await ws.send_json({'context_id':'test','text':'Blue teacup. ','flush':True})
            for _ in range(5):
                try:m=await asyncio.wait_for(ws.receive_json(),2)
                except asyncio.TimeoutError:break
                print({k:v for k,v in m.items() if k not in ('audio','alignment','normalizedAlignment','normalized_alignment')},'bytes',len(base64.b64decode(m.get('audio') or '')),'ms',round((time.monotonic()-start)*1000),flush=True)
            await ws.send_json({'context_id':'test','text':' The tiny robot is listening. ','flush':True})
            await ws.send_json({'context_id':'test','close_context':True})
            for _ in range(10):
                try:m=await asyncio.wait_for(ws.receive_json(),2)
                except asyncio.TimeoutError:break
                print({k:v for k,v in m.items() if k not in ('audio','alignment','normalizedAlignment','normalized_alignment')},'bytes',len(base64.b64decode(m.get('audio') or '')),flush=True)
                if m.get('isFinal') or m.get('is_final'):break
asyncio.run(main())
