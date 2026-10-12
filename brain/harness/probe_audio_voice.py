"""Speak a synthetic fixture into native voice; never open a real microphone."""
import asyncio,json,queue,time,wave
from pathlib import Path
from fractions import Fraction
import requests,av,numpy as np
from aiortc import RTCPeerConnection,RTCConfiguration,RTCSessionDescription,AudioStreamTrack
from codex_client import CodexClient
from pi_client import load_env

class FixtureTrack(AudioStreamTrack):
    def __init__(self):
        super().__init__();self.q=asyncio.Queue();self.ts=0;self.started=None
    async def recv(self):
        if self.started is None:self.started=time.monotonic()
        await asyncio.sleep(max(0,self.started+self.ts/48000-time.monotonic()))
        try:pcm=self.q.get_nowait()
        except asyncio.QueueEmpty:pcm=b'\0'*1920
        frame=av.AudioFrame.from_ndarray(np.frombuffer(pcm,dtype='<i2').reshape(1,-1),format='s16',layout='mono')
        frame.sample_rate=48000;frame.pts=self.ts;frame.time_base=Fraction(1,48000);self.ts+=960
        return frame
    def feed(self,pcm):
        from scipy.signal import resample_poly
        a=resample_poly(np.frombuffer(pcm,dtype='<i2').astype(float),3,1).clip(-32768,32767).astype('<i2').tobytes()
        for i in range(0,len(a),1920):self.q.put_nowait(a[i:i+1920].ljust(1920,b'\0'))

async def main():
    out=Path(__file__).resolve().parents[1]/'results/voice_refinement_20260914'
    env=load_env();r=requests.post('https://api.deepgram.com/v1/speak?model=aura-2-thalia-en&encoding=linear16&sample_rate=16000&container=none',headers={'Authorization':'Token '+env['DEEPGRAM_API_KEY']},json={'text':'Hello MIST. I finally finished building your legs. What do you think?'},timeout=20);r.raise_for_status()
    fixture=r.content;(out/'fixture_user.pcm').write_bytes(fixture)
    track=FixtureTrack();pc=RTCPeerConnection(RTCConfiguration(iceServers=[]));pc.addTrack(track);dc=pc.createDataChannel('oai-events');frames=[];logs=[]
    @pc.on('track')
    async def receive(t):
        while True:
            try:frames.append(await t.recv())
            except Exception:break
    @dc.on('message')
    def message(msg):
        logs.append({'source':'dc','event':json.loads(msg)});print('DC',str(msg)[:1600],flush=True)
    opened=asyncio.Event()
    dc.on('open',opened.set)
    await pc.setLocalDescription(await pc.createOffer())
    c=await asyncio.to_thread(CodexClient,model='gpt-5.3-codex-spark',tools=[],with_memory=False,run_dir=out/'audio_probe',service_tier='default',system_prompt='You are MIST, a concise robot companion. No physical hardware is connected. No tools.')
    try:
        await asyncio.to_thread(c._rpc.request,'thread/realtime/start',{'threadId':c.thread_id,'outputModality':'audio','transport':{'type':'webrtc','sdp':pc.localDescription.sdp},'version':'v3','includeStartupContext':False,'delegationAckFiller':False,'prompt':'You are MIST. Warm and slightly dry, never gushy. Reply in one short sentence unless asked for detail. You have four legs and a phone face, but physical movement is not connected.'})
        end=time.monotonic()+28;sent=False
        while time.monotonic()<end:
            if opened.is_set() and not sent:sent=True;track.feed(fixture);print('FIXTURE START',flush=True)
            try:e=await asyncio.to_thread(c._rpc.events.get,True,.2)
            except queue.Empty:continue
            if not e:break
            method=e.get('method','');p=e.get('params',{})
            if method.startswith('thread/realtime/'):
                if method=='thread/realtime/sdp':await pc.setRemoteDescription(RTCSessionDescription(p['sdp'],'answer'))
                else:logs.append({'source':'rpc','method':method,'params':p});print(method,json.dumps(p)[:1300],flush=True)
                if method=='thread/realtime/error':break
        await asyncio.to_thread(c._rpc.request,'thread/realtime/stop',{'threadId':c.thread_id})
    finally:
        await pc.close();await asyncio.to_thread(c.close)
        resample=av.AudioResampler(format='s16',layout='mono',rate=16000)
        raw=b''.join(f.to_ndarray().tobytes() for frame in frames for f in resample.resample(frame))
        with wave.open(str(out/'codex_voice_response.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(raw)
        (out/'audio_probe_events.json').write_text(json.dumps(logs,indent=2),encoding='utf-8')
        print('Captured seconds',len(raw)/32000,'nonzero',np.max(np.abs(np.frombuffer(raw,dtype='<i2'))) if raw else 0,flush=True)

if __name__=='__main__':asyncio.run(main())
