"""Replay a previously generated WAV through the real player without provider calls."""
import argparse
import base64
import json
import sys
import tempfile
import time
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BRAIN = Path(__file__).resolve().parents[1]
VOICE = BRAIN.parent / "design/mist_v2_20260906/brain_v2_20260907/voice"
HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><title>MIST saved audio check</title>
<style>body{font:18px system-ui;background:#111;color:#eee;padding:30px}#face{width:420px;height:270px}button{font:inherit;padding:12px;margin:6px}audio{display:block}output{display:block}</style>
<h1>MIST saved audio check</h1><p>Local replay of an existing synthetic clip. No model or speech API calls.</p>
<div id="face"></div><p id="status" role="status">Loading saved clip</p>
<button id="resume" hidden>Play reply</button><button id="delay">Play after six seconds</button><button id="stop">Stop</button>
<output id="requests">Audio requests: 0</output><output id="result"></output>
<script src="/data.js"></script><script src="/face.js"></script><script src="/player.js"></script><script>
const face=MistFaceRuntime.create(document.querySelector('#face'),{data:MIST_DATA});
const audio=new Audio();audio.controls=true;document.body.appendChild(audio);let requests=0;
const player=MistSpeechPlayer.create({face,audio,fetch:(...args)=>{document.querySelector('#requests').textContent='Audio requests: '+(++requests);return fetch(...args);},
 onState:state=>{document.querySelector('#status').textContent=state==='blocked'?'Reply ready. Press Play reply.':state;
  document.querySelector('#resume').hidden=state!=='blocked';
  if(state==='playing') document.querySelector('#result').textContent='Playback started from the saved clip. Audio requests: '+requests;},
 onError:error=>{document.querySelector('#status').textContent=error;}});
document.querySelector('#resume').onclick=()=>player.resume();
document.querySelector('#delay').onclick=()=>{document.querySelector('#status').textContent='Waiting six seconds after this click';setTimeout(()=>player.resume(),6000);};
document.querySelector('#stop').onclick=()=>player.stop();
player.play('Saved clip');
</script></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, content_type, data):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        files = {"/data.js": BRAIN/"face_assets/app/app_data.js",
                 "/face.js": BRAIN/"ui/static/face_runtime.js",
                 "/player.js": BRAIN/"ui/static/speech_player.js"}
        if self.path == "/":
            return self.reply("text/html; charset=utf-8", HTML.encode())
        if self.path in files:
            return self.reply("text/javascript; charset=utf-8", files[self.path].read_bytes())
        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/speech":
            return self.send_error(404)
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        sample=json.loads((VOICE/"voice_check.json").read_text(encoding="utf-8"))["samples"][0]
        sample["audio_base64"]=base64.b64encode((VOICE/"mist_refined_01.wav").read_bytes()).decode()
        sample["provider"]="saved_elevenlabs_clip"
        sample["alignment_source"]="saved_character_timestamps"
        self.reply("application/json", json.dumps(sample).encode())


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8778)
    parser.add_argument("--console", action="store_true", help="Serve the complete console with offline model and saved speech.")
    args=parser.parse_args()
    app=None
    temporary=None
    if args.console:
        sys.path.insert(0, str(BRAIN))
        from ui import server as console, voice
        temporary=tempfile.TemporaryDirectory(prefix="mist-console-fixture-")
        options=console.parse_args(["--stub", "--no-executive", "--run-dir", temporary.name])
        app=console.build_app(options, use_stub=True)
        sample=json.loads((VOICE/"voice_check.json").read_text(encoding="utf-8"))["samples"][0]
        def fixture_ask(prompt, timeout=120, on_event=None):
            if on_event:
                on_event({"type":"message_update","assistantMessageEvent":{"type":"text_delta","delta":sample["text"]}})
            return SimpleNamespace(text=sample["text"],tool_calls=[],ttft_s=0,ttf_tool_s=None,ttf_any_s=0,total_s=0,
                                   input_tokens=0,output_tokens=0,cost_usd=0,errors=[],timings={"fixture":True})
        app.client.ask=fixture_ask
        def saved_speech(text, provider, selected_voice, env, model=None):
            return {**sample,"audio_base64":base64.b64encode((VOICE/"mist_refined_01.wav").read_bytes()).decode(),
                    "provider":"saved_clip","voice_id":"fixture","model_id":"saved_clip","alignment_source":"saved_character_timestamps",
                    "usage":{"characters":0,"audio_seconds":sample["duration_s"],"api_latency_s":0,"fixture":True}}
        voice.generate_speech=saved_speech
        original_config=app.config
        def fixture_config():
            config=original_config()
            config["deepgram_available"]=False
            config["speech"]={"elevenlabs_available":True,"elevenlabs_voice_label":"Saved clip fixture","elevenlabs_models":[]}
            return config
        app.config=fixture_config
        console.start_background(app)
        server=console.make_server(app,args.port)
    else:
        server=ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Saved audio fixture on http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if app:
            app._stop_background=True
        server.server_close()
        if temporary:
            temporary.cleanup()
