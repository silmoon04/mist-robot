"""Live TTS continuity/intelligibility probes with synthetic text only."""
import asyncio, base64, json, sys, time, wave
from pathlib import Path
import aiohttp
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pi_client import load_env
from duplex.tts import StreamingTTS

CASES=[
 ('short','Blue teacup.'),
 ('gentle',"No rush. I'm listening. Take your time."),
 ('excited','Wait, really? That worked! The tiny robot has a voice!'),
 ('question','Was that your idea, or mine? I have a slight suspicion.'),
 ('precision','Thirty degrees left. Then return to the center and wait.'),
 ('long','The little robot waited beside the window. Outside, the rain tapped on the glass. It could not walk yet, but it had become exceptionally good at supervising the weather.'),
]

def acoustics(raw):
    a=np.frombuffer(raw,dtype='<i2').astype(float)/32768
    f=[]
    # Basic autocorrelation estimates voiced pitch only; not a perceptual score.
    for i in range(0,len(a)-1440,720):
        x=a[i:i+1440];x=x-x.mean()
        if np.sqrt(np.mean(x*x))<.015:continue
        r=np.correlate(x,x,'full')[len(x)-1:]
        lag=np.argmax(r[48:343])+48
        if r[lag]/max(r[0],1e-12)>.6:f.append(24000/lag)
    return {'duration_s':len(a)/24000,'peak':float(np.max(np.abs(a))) if len(a) else 0,
      'clipped_samples':int(np.sum(np.abs(a)>=.999)),
      'estimated_voiced_pitch_hz_p10_p50_p90':np.percentile(f,[10,50,90]).round(1).tolist() if f else []}

async def main():
    out=Path('brain/results/tts_websocket_20260914/voice_samples');out.mkdir(parents=True,exist_ok=True)
    env=load_env();rows=[];events=[]
    async def emit(e):events.append({**e,'at':time.monotonic()})
    t=StreamingTTS(env['ELEVENLABS_API_KEY'],emit)
    await t.start()
    try:
        for name,text in CASES:
            events.clear();start=time.monotonic();await t.begin(name)
            # Exercise fragments inside words, as a streaming transcript may do.
            for i in range(0,len(text),7):
                await t.text(text[i:i+7]);await asyncio.sleep(.025)
            await t.finish(text)
            deadline=time.monotonic()+15
            while t.pending and time.monotonic()<deadline:await asyncio.sleep(.02)
            packets=[e for e in events if e['type']=='audio'];raw=b''.join(base64.b64decode(e['pcm']) for e in packets)
            with wave.open(str(out/(name+'.wav')),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(raw)
            recognized=''
            async with aiohttp.ClientSession() as http:
                async with http.post('https://api.deepgram.com/v1/listen?model=nova-3&encoding=linear16&sample_rate=24000&channels=1',headers={'Authorization':'Token '+env['DEEPGRAM_API_KEY'],'Content-Type':'application/octet-stream'},data=raw) as response:
                    if response.status==200:
                        d=await response.json();recognized=d['results']['channels'][0]['alternatives'][0]['transcript']
            row={'case':name,'input':text,'recognized':recognized,
                 'first_audio_from_first_text_s':packets[0]['at']-start if packets else None,
                 'warnings':[e.get('code') for e in events if e['type'] in ('error','voice_warning')],
                 'metrics':acoustics(raw),'synthesis':[e['tts'] for e in events if e['type']=='latency'],
                 'packets':[{'at':round(e['at']-start,4),'bytes':len(base64.b64decode(e['pcm']))} for e in packets]}
            rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='packets'}),flush=True)
            (out/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    finally:await t.close()

asyncio.run(main())
