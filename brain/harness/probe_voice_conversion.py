"""Measure the owned MIST Voice Changer on captured synthetic Codex speech."""
import asyncio,io,json,time,wave
from pathlib import Path
import aiohttp,numpy as np
from pi_client import load_env

async def main():
    out=Path(__file__).resolve().parents[1]/'results/voice_refinement_20260914'
    with wave.open(str(out/'codex_voice_response.wav'),'rb') as w:pcm=w.readframes(w.getnframes())
    a=np.frombuffer(pcm,dtype='<i2');idx=np.flatnonzero(np.abs(a)>300)
    pcm=pcm[max(0,idx[0]-1600)*2:min(len(a),idx[-1]+3200)*2]
    key=load_env()['ELEVENLABS_API_KEY'];results=[]
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as client:
        for duration in (.8,1.4,2.4):
            form=aiohttp.FormData();form.add_field('audio',pcm[:int(duration*32000)],filename='voice.pcm',content_type='application/octet-stream')
            form.add_field('model_id','eleven_multilingual_sts_v2');form.add_field('file_format','pcm_s16le_16')
            start=time.monotonic();first=None;data=bytearray()
            async with client.post('https://api.elevenlabs.io/v1/speech-to-speech/24AMj4dc02cYAwoUnqzN/stream?output_format=pcm_24000',data=form,headers={'xi-api-key':key}) as r:
                if r.status!=200:print('STS HTTP',r.status,(await r.text())[:200]);break
                async for chunk in r.content.iter_chunked(4096):
                    if first is None:first=time.monotonic()-start
                    data.extend(chunk)
            with wave.open(str(out/f'converted_{duration}.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(data)
            row={'input_seconds':duration,'first_byte_s':first,'total_s':time.monotonic()-start,'output_seconds':len(data)/48000}
            results.append(row);print(row,flush=True)
    (out/'conversion_probe.json').write_text(json.dumps(results,indent=2),encoding='utf-8')

if __name__=='__main__':asyncio.run(main())
