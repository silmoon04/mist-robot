import asyncio,base64,json,sys,time,wave,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pi_client import load_env
from duplex.tts import StreamingTTS

async def main():
    out=Path('brain/results/layered_brain_20260914/phrases');out.mkdir(parents=True,exist_ok=True)
    baseline=out/'previous_tts.py'
    if baseline.exists():source=baseline.read_text(encoding='utf-8')
    else:
        with zipfile.ZipFile('brain/duplex/MIST_Native_Voice_20260914.zip') as z:source=z.read('MIST_Native_Voice/brain/duplex/tts.py').decode()
        baseline.write_text(source,encoding='utf-8')
    namespace={'__name__':'previous_tts'};exec(compile(source,'previous_tts.py','exec'),namespace)
    rows=[]
    cases=[('clause','I can keep the beginning quite short, and explain the rest while you listen. This should stay one connected thought.'),
           ('sentences','That worked! We can try the next step. No rush, though. I am still listening.')]
    for name,text in cases:
        for label,cls in [('previous',namespace['StreamingTTS']),('phrases',StreamingTTS)]:
            events=[]
            async def emit(e):events.append({**e,'at':time.monotonic()})
            t=cls(load_env()['ELEVENLABS_API_KEY'],emit);await t.start();start=time.monotonic();await t.begin('probe')
            for i in range(0,len(text),7):await t.text(text[i:i+7]);await asyncio.sleep(.08)
            await t.finish(text)
            deadline=time.monotonic()+10
            while t.pending and time.monotonic()<deadline:await asyncio.sleep(.02)
            audio=[e for e in events if e['type']=='audio'];raw=b''.join(base64.b64decode(e['pcm']) for e in audio)
            with wave.open(str(out/f'{name}_{label}.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(raw)
            rows.append({'case':name,'version':label,'first_audio_s':audio[0]['at']-start if audio else None,'audio_s':len(raw)/48000,'warnings':[e.get('code') for e in events if e['type']=='voice_warning']})
            await t.close()
    (out/'comparison.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(rows))

asyncio.run(main())
