"""Complete Talk UI with a saved WAV as virtual microphone; no ambient capture or cloud calls."""
import argparse
import base64
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import wave

BRAIN=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BRAIN))
from ui import server, voice

VOICE=BRAIN.parent/'design/mist_v2_20260906/brain_v2_20260907/voice'
OUT=BRAIN.parent/'design/mist_v2_20260906/brain_v2_20260907/talk_mode_20260907'
MIC_AUDIO=(VOICE/'mist_refined_01.wav').read_bytes()
SAMPLE=json.loads((VOICE/'voice_check.json').read_text(encoding='utf-8'))['samples'][0]

INJECTION="""<script>
// Fixture-only dependency: the Talk button opens a saved WAV stream, never getUserMedia.
const actualCapture=MistTalkCapture.create;
window.MistTalkCapture={...MistTalkCapture,create:()=>{throw new Error('Saved microphone fixture did not initialize.');}};
/* STT_FIXTURE */
let fixtureInput=null;
MistTalkCapture.create=options=>{
 let sourceContext=null;
 const capture=actualCapture({...options,getUserMedia:async()=>{
   sourceContext=new AudioContext();await sourceContext.resume();
   const destination=sourceContext.createMediaStreamDestination();
   const response=await fetch('/fixture/mic.wav');
   const buffer=await sourceContext.decodeAudioData(await response.arrayBuffer());
   fixtureInput=()=>{const source=sourceContext.createBufferSource();source.buffer=buffer;source.connect(destination);source.start(sourceContext.currentTime+.45);};
   fixtureInput();
   return destination.stream;
 }});
 const close=capture.stop;
 capture.stop=async()=>{fixtureInput=null;await close();if(sourceContext){await sourceContext.close();sourceContext=null;}};
 return capture;
};
const injectButton=document.createElement('button');injectButton.textContent='Test saved interruption';
injectButton.onclick=()=>{if(fixtureInput){document.querySelector('#btnPreview').click();fixtureInput();}};
document.body.appendChild(injectButton);
</script>"""


class FixtureHandler(server.Handler):
    lock=threading.Lock()
    counts={'stt':0,'chat':0,'speech':0,'interrupt':0}
    stream_port=None

    def do_GET(self):
        if self.path=='/fixture/mic.wav':
            return self._send_bytes(200,'audio/wav',MIC_AUDIO)
        if self.path=='/fixture/counts':
            return self._send_json(200,self.counts)
        if self.path=='/':
            html=(server.STATIC_DIR/'index.html').read_text(encoding='utf-8')
            marker='<script src="/static/talk_session.js?v=1"></script>'
            if marker not in html:
                raise RuntimeError('Fixture injection marker missing; refusing to expose the real microphone path.')
            if self.stream_port:
                stream_code="const savedStreamFactory=MistSTTStream.create;window.MistSTTStream={create:options=>savedStreamFactory({...options,url:'ws://127.0.0.1:%s/stt'})};" % self.stream_port
            else:
                stream_code="window.MistSTTStream={create:()=>({start:()=>false,push:()=>false,end:()=>false,cancel:()=>false,result:async()=>null,stop:()=>{}})};"
            html=html.replace(marker,marker+INJECTION.replace('/* STT_FIXTURE */',stream_code))
            html=html.replace('<header>','<p role="status" style="margin:0;padding:6px;background:#402500">OFFLINE TALK CHECK: saved audio input, no microphone permission or provider calls.</p><header>')
            return self._send_bytes(200,'text/html; charset=utf-8',html.encode())
        return super().do_GET()

    def do_POST(self):
        if self.path=='/api/interrupt':
            with self.lock: self.counts['interrupt']+=1
        return super().do_POST()

    def _api_stt(self):
        raw=self._read_body()
        with wave.open(io.BytesIO(raw),'rb') as wav:
            metadata={'sample_rate':wav.getframerate(),'channels':wav.getnchannels(),'duration_s':wav.getnframes()/wav.getframerate()}
        with self.lock:
            self.counts['stt']+=1
            (OUT/'captured_utterance.wav').write_bytes(raw)
            (OUT/'captured_utterance.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        return self._send_json(200,{'transcript':SAMPLE['text'],'confidence':1.0,'fixture':True,'audio_seconds':metadata['duration_s']})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8779)
    parser.add_argument('--streaming',action='store_true',help='Run a fake provider through the real local WebSocket proxy.')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mist-talk-fixture-') as temp:
        options=server.parse_args(['--stub','--no-executive','--run-dir',temp])
        app=server.build_app(options,use_stub=True)
        def ask(prompt,timeout=120,on_event=None):
            FixtureHandler.counts['chat']+=1
            text='I heard the saved greeting.'
            if on_event: on_event({'type':'message_update','assistantMessageEvent':{'type':'text_delta','delta':text}})
            return SimpleNamespace(text=text,tool_calls=[],ttft_s=0,ttf_tool_s=None,ttf_any_s=0,total_s=0,input_tokens=0,output_tokens=0,cost_usd=0,errors=[],timings={'fixture':True})
        app.client.ask=ask
        def saved_speech(text,provider,selected_voice,env,model=None):
            FixtureHandler.counts['speech']+=1
            return {**SAMPLE,'audio_base64':base64.b64encode(MIC_AUDIO).decode(),'provider':'saved_clip','voice_id':'fixture','model_id':'saved_clip','alignment_source':'saved_character_timestamps','usage':{'characters':0,'audio_seconds':SAMPLE['duration_s'],'fixture':True}}
        voice.generate_speech=saved_speech
        original=app.config
        def config():
            result=original();result['deepgram_available']=True
            result['speech']={'elevenlabs_available':True,'elevenlabs_voice_label':'Saved clip fixture','elevenlabs_models':[]}
            return result
        app.config=config
        proxy=None
        if args.streaming:
            from ui.stt_proxy import create_proxy_server
            class FakeStreamingEngine:
                def begin_utterance(self,sample_rate,*,on_event=None):
                    self.rate=sample_rate;self.pcm=bytearray();self.on_event=on_event
                    FixtureHandler.counts['stream_start']=FixtureHandler.counts.get('stream_start',0)+1
                def send_pcm(self,pcm):
                    self.pcm.extend(pcm)
                    if self.on_event:self.on_event({'type':'stt_partial','text':'Saved partial'})
                def finalize(self,timeout=8):
                    FixtureHandler.counts['stream_final']=FixtureHandler.counts.get('stream_final',0)+1
                    seconds=len(self.pcm)/(2*self.rate)
                    return {'final':True,'transcript':SAMPLE['text'],'confidence':1.0,'audio_seconds':seconds,
                            'provider_processed_audio_seconds':seconds,'timings':{'finalize_to_final_s':0,'recognition_total_s':seconds}}
                def cancel(self): pass
                def close(self): pass
            proxy=create_proxy_server(port=0,origins=(f'http://127.0.0.1:{args.port}',),engine_factory=FakeStreamingEngine)
            FixtureHandler.stream_port=proxy.port
            threading.Thread(target=proxy.serve_forever,daemon=True).start()
        server.start_background(app)
        httpd=server.ThreadingHTTPServer(('127.0.0.1',args.port),type('BoundFixture',(FixtureHandler,),{'app':app}))
        print(f'Offline Talk fixture on http://127.0.0.1:{httpd.server_port}/',flush=True)
        try: httpd.serve_forever()
        except KeyboardInterrupt: pass
        finally:
            app._stop_background=True
            httpd.server_close()
            if proxy:proxy.shutdown()

if __name__=='__main__': main()
