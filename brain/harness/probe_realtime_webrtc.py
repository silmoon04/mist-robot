"""Negotiate native Codex realtime without accessing the microphone."""
import asyncio,json,queue,time,wave
from pathlib import Path
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration
from codex_client import CodexClient

async def main():
    out=Path(__file__).resolve().parents[1]/'results/voice_refinement_20260914'
    pc=RTCPeerConnection(RTCConfiguration(iceServers=[]))
    pc.addTransceiver('audio',direction='sendrecv')
    dc=pc.createDataChannel('oai-events')
    received=[]
    @pc.on('track')
    async def track_in(track):
        print('TRACK',track.kind,flush=True)
        while True:
            try:
                frame=await track.recv();received.append(frame)
            except Exception:break
    dc.on('open',lambda:print('Data channel opened',flush=True))
    dc.on('message',lambda message:print('DC',str(message)[:1200],flush=True))
    await pc.setLocalDescription(await pc.createOffer())
    c=await asyncio.to_thread(CodexClient,model='gpt-5.3-codex-spark',tools=[],with_memory=False,
        run_dir=out/'webrtc_probe',service_tier='default',system_prompt='You are MIST, a concise companion. No hardware connected.')
    logs=[]
    try:
        await asyncio.to_thread(c._rpc.request,'thread/realtime/start',{'threadId':c.thread_id,
            'outputModality':'audio','transport':{'type':'webrtc','sdp':pc.localDescription.sdp},
            'version':'v3','includeStartupContext':False,'delegationAckFiller':False,
            'prompt':'You are MIST. Speak warmly and briefly. No hardware is connected.'})
        end=time.monotonic()+25
        sent=False
        while time.monotonic()<end:
            if dc.readyState=='open' and not sent:
                sent=True
                await asyncio.to_thread(c._rpc.request,'thread/realtime/appendText',{'threadId':c.thread_id,'text':'Hello MIST. Say one short playful greeting, then stop.'})
            try:e=await asyncio.to_thread(c._rpc.events.get,True,1)
            except queue.Empty:continue
            if not e:break
            method=e.get('method','');p=e.get('params',{})
            if method.startswith('thread/realtime/'):
                safe={k:v for k,v in p.items() if k not in ['sdp','audio']}
                print(method,json.dumps(safe)[:1800],flush=True);logs.append({'method':method,'params':safe})
                if method=='thread/realtime/sdp':
                    print('SDP keys',list(p),flush=True)
                    await pc.setRemoteDescription(RTCSessionDescription(p['sdp'],'answer'))
                if method=='thread/realtime/error':break
            if dc.readyState=='open' and not sent:
                sent=True
                await asyncio.to_thread(c._rpc.request,'thread/realtime/appendText',{'threadId':c.thread_id,'text':'Hello MIST. Say one short playful greeting, then stop.'})
        await asyncio.to_thread(c._rpc.request,'thread/realtime/stop',{'threadId':c.thread_id})
    finally:
        await pc.close();await asyncio.to_thread(c.close)
        (out/'webrtc_probe_events.json').write_text(json.dumps(logs,indent=2),encoding='utf-8')
        import av
        resampler=av.AudioResampler(format='s16',layout='mono',rate=16000)
        raw=b''.join(f.to_ndarray().tobytes() for frame in received for f in resampler.resample(frame))
        with wave.open(str(out/'native_voice.wav'),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(raw)
        print('received_audio_seconds',len(raw)/32000,flush=True)

if __name__=='__main__':asyncio.run(main())
