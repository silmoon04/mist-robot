"""Repeat real conversion requests and preserve metadata without credentials."""
import asyncio,importlib.util,json,logging,sys,time,wave
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from duplex.conversion import VoiceMask
from pi_client import load_env

async def main():
    out=Path(__file__).resolve().parents[1]/'results/voice_fix_20260914';out.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=out/'baseline_diagnostics.log',level=logging.ERROR)
    source=out.parent/'voice_refinement_20260914/codex_voice_response.wav'
    with wave.open(str(source),'rb') as wav:raw=wav.readframes(wav.getnframes())
    a=np.frombuffer(raw,dtype='<i2');start=max(0,int(np.flatnonzero(np.abs(a)>300)[0])-1000);raw=raw[start*2:]
    events=[]
    async def emit(e):
        if e['type']!='audio':events.append(e);print(json.dumps(e),flush=True)
    mask=VoiceMask(load_env()['ELEVENLABS_API_KEY'],emit);await mask.start()
    try:
        for group in range(4):
            if mask.muted:break
            jobs=[]
            for duration in [.8,.14,1.2]:
                seq=mask.sequence;mask.sequence+=1
                t=asyncio.create_task(mask.convert(raw[:int(duration*32000)],seq,mask.epoch));mask.tasks.add(t);t.add_done_callback(mask.tasks.discard);jobs.append(t)
            await asyncio.gather(*jobs,return_exceptions=True)
            if mask.muted:break
            await asyncio.sleep(1)
    finally:await mask.close()
    (out/'baseline_stress_events.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
    errors=[e for e in events if e['type']=='error']
    print('conversion failures',len(errors),flush=True)
    if errors:raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
