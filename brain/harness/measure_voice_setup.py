"""Measure native handshake without microphone, speech or conversion calls."""
import asyncio,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from duplex.native import NativeVoice
from duplex.runtime import RobotRuntime

async def main():
    out=Path(__file__).resolve().parents[1]/'results/voice_fix_20260914/setup';out.mkdir(parents=True,exist_ok=True)
    rows=[]
    async def emit(e):
        if e['type'] in ('ready','error'):print(json.dumps(e),flush=True)
    async def discard(e):pass
    for index,include in enumerate((False,False)):
        voice=NativeVoice(RobotRuntime(out/str(index)),out/str(index),emit,discard,discard,include_startup_context=include)
        try:
            await voice.start();rows.append({'include_startup_context':include,**voice.startup})
        except Exception as e:rows.append({'include_startup_context':include,'error':type(e).__name__})
        finally:await voice.close()
    (out/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(rows),flush=True)

if __name__=='__main__':asyncio.run(main())
