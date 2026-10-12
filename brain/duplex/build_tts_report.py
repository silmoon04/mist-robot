"""Build the current streaming TTS evidence summary and verified source bundle inputs."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BRAIN=ROOT/'brain'
OUT=BRAIN/'results/tts_websocket_20260914'


def main():
    tests=[]
    for name,cmd in [
        ('33 application contracts',['python','brain/harness/test_duplex.py']),
        ('11 streaming TTS contracts',['python','brain/harness/test_streaming_tts.py']),
        ('6 legacy converter recovery contracts',['python','brain/harness/test_voice_recovery.py']),
        ('Browser playback scheduling and cancellation',['node','brain/harness/test_duplex_playback.mjs']),
        ('40 faces and 31,050 renderer states',['node','brain/harness/check_face_runtime.cjs']),
    ]:
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        (OUT/(Path(cmd[-1]).stem+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
        tests.append({'name':name,'passed':r.returncode==0})
    samples=json.loads((OUT/'voice_samples/results.json').read_text())
    social=json.loads((OUT/'prefix_fixed/conversations.json').read_text())
    tool_rows=json.loads((OUT/'tools/conversations.json').read_text())
    verification=json.loads((OUT/'prefix_fixed/audio_verification.json').read_text())
    interruptions=[]
    for folder in ['native_interrupt','manual_interrupt']:
        r=json.loads((OUT/folder/'interruption.json').read_text())
        audio=json.loads((OUT/folder/'audio_verification.json').read_text())
        interruptions.append({'mode':folder,'passed':r['passed'] and audio['passed'],
            'stale_packets':r['stale_generation_packets_after_reset'],
            'new_audio_packets':r['new_generation_audio_packets'],
            'spoken_correction_verified':audio['checks']['correction_audible']})
    assert verification['passed'] and all(r['passed'] for r in interruptions)
    assert all(not r['errors'] and not r['warnings'] for r in social+tool_rows)
    assert all(not r['warnings'] and r['metrics']['clipped_samples']==0 for r in samples)
    shutil.copyfile(OUT/'voice_samples/gentle.wav',BRAIN/'duplex/static/sample.wav')
    implementation=[p for p in (BRAIN/'duplex').rglob('*') if p.is_file() and p.suffix in ('.py','.js','.css','.html','.wav') and '__pycache__' not in p.parts]
    implementation += [BRAIN/'duplex/face_map.json',BRAIN/'duplex/persona.txt']
    report={
        'revision':'Streaming TTS WebSocket, 2026-09-14',
        'default_speech_backend':'streaming-tts',
        'voice_id':'24AMj4dc02cYAwoUnqzN',
        'tts_model':'eleven_flash_v2_5',
        'backing_model':'gpt-5.3-codex-spark, low reasoning, unchanged',
        'tests':tests,
        'social_latency_seconds':[r['last_fixture_frame_to_first_converted_audio_s'] for r in social],
        'tool_latency_seconds':[r['last_fixture_frame_to_first_converted_audio_s'] for r in tool_rows],
        'browser_startup_buffer_seconds':.2,
        'social_audio_first_and_last_words_verified':verification['checks'],
        'interruption_tests':interruptions,
        'voice_samples':[{k:v for k,v in r.items() if k not in ('packets','synthesis')} for r in samples],
        'browser_check':{'passed':True,'observation':'Synthetic Blue teacup reply appeared at playback start; screen returned to Listening; no browser console errors; microphone was not opened.'},
        'findings':[
            'Native predictive transcript fragments arrive before the assistant-turn boundary. Preparing TTS from them fixes missing first words; audio remains gated until that boundary.',
            'One persistent provider WebSocket manages a synthesis context per reply. Interrupted contexts are closed, and late audio and errors from them are ignored.',
            'Word fragments are assembled before provider transmission; sentence and final flushing preserve short replies.',
            'Native data-channel callbacks are serialized to preserve event order.',
            'The native microphone uplink continues throughout TTS generation and playback.',
        ],
        'limits':[
            'The initial TTS implementation lost predictive prefixes. The prefix_fixed recordings and regression tests verify the correction; earlier live and order_probe results are retained as failed-development evidence.',
            'Social timings are three synthetic trials, not a percentile benchmark. The native end-of-turn wait remains; total audible response is approximately two seconds in these trials.',
            'Tool delegation remains much slower, about 7.4 and 8.4 seconds in the two recorded cases. Both tools were invoked twice by the native/backing path.',
            'ASR and clipping checks verify intelligibility and signal bounds, not human-perceived naturalness. Pitch values are basic autocorrelation estimates and may contain octave errors.',
            'No real microphone, room echo, phone speaker or Mi 9 SE acceptance test was performed.',
            'This is a duplex application with separate native input/turn detection and TTS output, not one end-to-end speech model.',
        ],
        'sources':[
            'https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-multi-stream-input',
            'https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/multi-context-web-socket',
        ],
        'implementation_sha256':{p.relative_to(BRAIN).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(implementation)},
    }
    target=BRAIN/'duplex/STREAMING_TTS_REPORT'
    target.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    text='''# MIST streaming TTS trial

Streaming TTS is now the default. Native Codex V3 still receives the microphone and handles conversation and tool delegation. Its response text is synthesized by ElevenLabs Flash v2.5 using MIST (refined), voice ID 24AMj4dc02cYAwoUnqzN. Native audio is discarded. The backing Spark model is unchanged.

One provider WebSocket stays open for the conversation. Each reply uses one synthesis context, preserving state across text fragments. Complete sentences and final turns flush pending text. The microphone remains active during playback. A new native user turn closes the old speech context, invalidates queued audio, and lets the correction use a fresh context. Manual Stop speaking clears playback immediately.

The first implementation revealed a specific missing-speech bug: native transcript fragments can precede the assistant-turn event. The bridge now prepares those fragments immediately and holds their audio until the native boundary. This keeps the first words without speaking prematurely over the user. Native event handlers are serialized, split words are reassembled, and late audio or errors from canceled contexts cannot affect the next reply.

The browser buffers 200 ms at startup, then schedules PCM packets contiguously. A ten-second sentence generated in a burst passes the playback regression test; it does not trigger the old backlog reset. The 30-second maximum queue is a resource bound, not an intentional playback delay. No pitch shifting or gain boost is applied.

## Measured results

Six direct TTS probes covered a two-word reply, gentle reassurance, excitement, a question, a precise instruction, and a longer story. Their first audio arrived 140-265 ms after input began on an already connected socket. All six were recovered correctly by independent speech recognition and had zero clipped samples. Basic pitch estimates varied across the samples, but these are not a listening-quality score.

Three complete native conversations returned their first playable audio 1.75-1.84 seconds after the final synthetic microphone frame. Browser buffering adds 200 ms, giving roughly two seconds to audible speech. Independent recognition of the recorded audio confirmed the first and last words of all three replies. Earlier attempts lost prefixes; those results remain in the evidence alongside the fixed run.

Both native-turn interruption and explicit-stop tests discarded all old-generation audio and produced the new blue teacup reply. Independent recognition confirmed the correction was present in the audio. The interruption harness includes synthetic-input generation time, so its dispatch-to-reset interval is not a real microphone interruption latency measurement.

Sensor and phone-pan tools returned real application receipts and spoken replies without speech errors. They remained slow: first audio arrived about 7.4 and 8.4 seconds after input ended. Both were called twice by the native/backing path. This trial does not claim that tool latency is solved.

The browser test played a short synthetic reply, showed its caption at playback start, returned to Listening, and reported no console errors. All 33 application contracts, 11 streaming TTS contracts, six legacy recovery contracts, playback checks and 31,050 renderer states passed.

## Limits and reproduction

This is a duplex application with separate native input and TTS output, not a single end-to-end speech model. Native turn detection remains the main ordinary-conversation delay. Real room echo, phone loudspeaker interaction and subjective quality still need the owner's listening trial. No real microphone was opened by these tests, and no physical robot commands were enabled.

Start normally with python brain/duplex/server.py. The default backend is streaming-tts. The previous audio-to-audio experiment remains selectable with --speech-backend voice-changer. Evidence and recordings are under brain/results/tts_websocket_20260914. The JSON companion records timings, checks and implementation hashes.

API references:
https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-multi-stream-input
https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/multi-context-web-socket
'''
    target.with_suffix('.md').write_text(text,encoding='utf-8')
    target.with_suffix('.txt').write_text(text,encoding='utf-8')
    assert all(t['passed'] for t in tests)
    print(json.dumps({'tests':tests,'social_latency_seconds':report['social_latency_seconds'],'interruptions':interruptions}))

if __name__=='__main__':main()
