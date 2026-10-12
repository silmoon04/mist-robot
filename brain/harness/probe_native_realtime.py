"""Bounded native Codex voice probe; no microphone or hardware capture."""
import os
import queue
import json
import time
from pathlib import Path
from codex_client import CodexClient
from pi_client import load_env
import requests

OUT=Path(__file__).resolve().parents[1]/'results/voice_refinement_20260914'

def main():
    env=load_env()
    response=requests.get('https://api.elevenlabs.io/v1/voices/24AMj4dc02cYAwoUnqzN',
        headers={'xi-api-key':env['ELEVENLABS_API_KEY']},timeout=20)
    voice=response.json() if response.ok else {}
    print('Voice metadata',response.status_code,voice.get('name'),voice.get('category'),flush=True)
    (OUT/'voice_access.json').write_text(json.dumps({'status':response.status_code,
        'voice_id':voice.get('voice_id'),'name':voice.get('name'),'category':voice.get('category')}),encoding='utf-8')
    client=CodexClient(model='gpt-5.3-codex-spark',thinking='low',service_tier='default',
        tools=[],with_memory=False,run_dir=OUT/'native_probe',system_prompt='You are MIST. Be brief. No tools or hardware are connected.')
    records=[]
    try:
        print('Codex ready',client.backend_info,flush=True)
        value=client._rpc.request('thread/realtime/start',{'threadId':client.thread_id,
            'outputModality':'audio','transport':{'type':'websocket'},'version':'v3',
            'includeStartupContext':False,'prompt':'You are MIST, a warm concise robot companion. Answer naturally in one short sentence. Do not claim hardware actions.',
            'delegationAckFiller':False})
        print('Realtime start',value,flush=True)
        client._rpc.request('thread/realtime/appendText',{'threadId':client.thread_id,
            'text':'Hello MIST. Give me a short playful greeting.'})
        end=time.monotonic()+22
        while time.monotonic()<end:
            try:event=client._rpc.events.get(timeout=1)
            except queue.Empty:continue
            if not event:break
            method=event.get('method','');params=event.get('params',{})
            if 'audio' in params:
                audio=params['audio'];audio={**audio,'data_bytes':len(audio.get('data',''))}
                audio.pop('data',None);safe={**params,'audio':audio}
            else:safe=params
            records.append({'method':method,'params':safe})
            print(method,json.dumps(safe,ensure_ascii=True)[:2000],flush=True)
            if method=='thread/realtime/error':break
        client._rpc.request('thread/realtime/stop',{'threadId':client.thread_id})
    finally:
        client.close()
        (OUT/'native_probe_events.json').write_text(json.dumps(records,indent=2),encoding='utf-8')

if __name__=='__main__':main()
