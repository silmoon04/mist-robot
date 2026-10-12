"""Compare old and new first-audio timing using identical PCM and HTTP fixtures."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from duplex.conversion import VoiceMask

OUT=Path(__file__).resolve().parents[1]/'results/voice_fix_20260914'

class Content:
    async def iter_chunked(self,n):
        yield b'\1\0'*2400

class Response:
    status=200
    content=Content()
    async def __aenter__(self):await asyncio.sleep(.15);return self
    async def __aexit__(self,*a):pass

class Session:
    def post(self,*a,**kw):return Response()

async def trial(cls):
    start=asyncio.get_running_loop().time();first=None
    async def emit(e):
        nonlocal first
        if e['type']=='audio' and first is None:first=asyncio.get_running_loop().time()-start
    mask=cls('fake',emit);mask.client=Session();frame=np.full(320,800,dtype='<i2').tobytes()
    for i in range(50):
        await asyncio.sleep(max(0,start+i*.02-asyncio.get_running_loop().time()))
        await mask.feed(frame)
    await asyncio.gather(*list(mask.tasks))
    return first

async def main():
    path=OUT/'baseline/conversion.py';spec=importlib.util.spec_from_file_location('old_voice',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    before=await trial(old.VoiceMask);after=await trial(VoiceMask)
    result={'old_first_audio_s':before,'new_first_audio_s':after,'improvement_s':before-after,
        'same_input':'50 voiced PCM frames at20 ms each','provider_fixture':'150 ms before first output; identical in both trials',
        'scope':'Isolates buffering and scheduling; not an internet latency claim.'}
    assert .3<before-after<.5,result
    (OUT/'buffer_comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':asyncio.run(main())
