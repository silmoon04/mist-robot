"""Write the connection-recovery and latency-fix evidence index."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys

BRAIN=Path(__file__).resolve().parents[1]
OUT=BRAIN/'results/voice_fix_20260914'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))

def main():
    tests=[]
    for command in [[sys.executable,BRAIN/'harness/test_duplex.py'],
                    [sys.executable,BRAIN/'harness/test_voice_recovery.py'],
                    ['node',BRAIN/'harness/test_duplex_playback.mjs']]:
        run=subprocess.run(list(map(str,command)),capture_output=True,text=True,encoding='utf-8')
        tests.append({'test':Path(command[-1]).name,'passed':run.returncode==0})
        (OUT/(Path(command[-1]).stem+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
        assert run.returncode==0,command
    baseline=read(OUT/'baseline_conversation/conversations.json')
    fixed=read(OUT/'fixed_conversation/conversations.json')
    fast=read(OUT/'fast_conversation/conversations.json')
    fixed_events=read(OUT/'fixed_conversation/events.json')
    fast_events=read(OUT/'fast_conversation/events.json')
    setup=read(OUT/'setup/results.json')
    buffer=read(OUT/'buffer_comparison.json')
    interruption=read(OUT/'interruption/interruption.json')
    diagnostics=[json.loads(line) for line in (OUT/'fixed_runtime/voice_diagnostics.jsonl').read_text(encoding='utf-8').splitlines()]
    retries=[d for d in diagnostics if d['event']=='conversion_attempt_failed' and d.get('retry')]
    errors=[e for e in fixed_events+fast_events if e['type'] in ('error','voice_warning')]
    assert len(fixed)==9 and len(fast)==3 and not errors
    assert interruption['passed']
    assert any(e['code']=='ClientConnectorError' for row in baseline for e in row['errors'])
    assert any(e['error_type']=='ClientConnectorError' for e in retries)
    assert any(t['name']=='set_expression' for row in fast for t in row['tools'])
    inputs=[OUT/'baseline_conversation/conversations.json',OUT/'baseline_server.log',OUT/'recovery_red.log',
        OUT/'fixed_conversation/conversations.json',OUT/'fast_conversation/conversations.json',
        OUT/'fixed_runtime/voice_diagnostics.jsonl',OUT/'fast_runtime/voice_diagnostics.jsonl',
        OUT/'setup/results.json',OUT/'buffer_comparison.json',OUT/'interruption/interruption.json']
    implementation=[p for p in (BRAIN/'duplex').rglob('*') if p.is_file() and '__pycache__' not in p.parts
        and (p.suffix in ('.py','.js','.html','.css') or p.name in ('persona.txt','face_map.json'))]
    implementation.extend(BRAIN/'harness'/name for name in ('test_voice_recovery.py','test_duplex.py','test_duplex_playback.mjs','repro_voice_conversation.py'))
    report={'status':'Fixed and verified; provider/network variability remains',
        'cause':'A live replay reproduced ClientConnectorError before audio. The old converter treated a single connection failure as fatal and muted the entire conversation.',
        'unchanged_model':'gpt-5.3-codex-spark, low reasoning',
        'voice_id':'24AMj4dc02cYAwoUnqzN',
        'tests':tests,'full_conversation_turns_without_converter_shutdown':len(fixed),
        'fast_start_conversation_turns_without_warnings':len(fast),
        'real_transport_retries_recovered':len(retries),
        'observed_original_error':'ClientConnectorError',
        'startup_before_ms':next(d['media_ready_ms'] for d in diagnostics if d['event']=='native_startup'),
        'startup_after_ms':[r['media_ready_ms'] for r in setup],
        'buffer_comparison':buffer,
        'live_short_reply_latency_s':[r['last_fixture_frame_to_first_converted_audio_s'] for r in fixed+fast if r['case']!='expressions'],
        'live_expression_reply_latency_s':[r['last_fixture_frame_to_first_converted_audio_s'] for r in fixed+fast if r['case']=='expressions'],
        'interruption':{k:v for k,v in interruption.items() if k not in ('events','reset_ack_ms')},
        'changes':['Retry transient connection, timeout and5xx failures only before audio from that segment has been emitted.',
            'Discard an unrecoverable reply without closing the native conversation. Keep account/access failures explicit.',
            'Disable duplicate automatic startup context while retaining the explicit MIST prompt and backing tools.',
            'Reduce initial PCM accumulation from800 to400 ms and browser lead-in from45 to25 ms.',
            'Warm the provider connection and retain metadata-only rotating diagnostics.',
            'Begin overlay captions with playback; detailed transcripts remain immediate.'],
        'limits':['The exact underlying internet connection failure is not determined. The failure boundary and incorrect fatal handling were reproduced.',
            'A retry or slow provider can still delay a reply. A persistent outage can still interrupt audio.',
            'Live response timings vary with generated phrasing and tool execution; the controlled400 ms buffer comparison isolates the code improvement.',
            'Expression requests still wait for backing-tool work; they are not guaranteed to speak immediately.',
            'Captions are gated to audio start, not word-aligned forced transcription.',
            'Tests used synthetic microphone input, not a physical handset or room-echo measurement.'],
        'evidence_sha256':{str(p.relative_to(BRAIN)):sha(p) for p in inputs},
        'implementation_sha256':{str(p.relative_to(BRAIN)):sha(p) for p in implementation}}
    for a,b in [('and5xx','and 5xx'),('from800 to400','from 800 to 400'),('from45 to25','from 45 to 25'),('controlled400','controlled 400')]:
        report['changes']=[v.replace(a,b) for v in report['changes']]
        report['limits']=[v.replace(a,b) for v in report['limits']]
    (BRAIN/'duplex/FIX_REPORT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    text=f'''# Voice connection and latency fix

The user's failure was reproduced on the native voice path: ClientConnectorError occurred while opening an ElevenLabs connection, before any audio was received for that segment. The previous implementation converted that brief transport error into a fatal mute for the whole conversation. The exact same user-visible failure also appeared in the new regression test before the fix.

The fixed path retries before any segment audio has been emitted, using a fresh multipart request body each time. It never retries already played audio. Retries, queueing and transfer share a bounded deadline. If recovery fails, that reply is cleared while native conversation remains available; account and voice-access errors are reported explicitly.

## Verified results

- Nine turns of the user's greeting/today/expression sequence completed without converter shutdowns.
- {len(retries)} real connection failures during that replay recovered on retry.
- Three additional turns with the faster startup completed without warnings, and the expression tool still worked.
- Six recovery regressions and the existing twenty-nine Python contracts passed. Browser playback/cancellation/caption-start checks passed.
- Interruption followed the corrected request with no stale-generation audio packets.
- Native connection readiness changed from {report['startup_before_ms']/1000:.2f} seconds with automatic startup context to {setup[0]['media_ready_ms']/1000:.2f} and {setup[1]['media_ready_ms']/1000:.2f} seconds without it. MIST already provides its own prompt and tool setup; the backing model is unchanged.
- An identical-input, identical-provider-fixture comparison measured {buffer['improvement_s']*1000:.0f} ms earlier first audio, from {buffer['old_first_audio_s']:.3f} to {buffer['new_first_audio_s']:.3f} seconds. This isolates the buffer change and is not an internet latency guarantee.

The first native-audio segment is now 400 ms instead of 800 ms. Following segments remain up to 1.2 seconds. Browser playout lead-in is 25 ms instead of 45 ms. The overlay waits for playback; the detailed transcript still appears immediately. Caption gating is separate from the actual buffering improvement.

Metadata-only diagnostics are saved in the running server's run directory as voice_diagnostics.jsonl. They contain phases, retry counts, exception classes and timing, without microphone audio, transcript text or credentials.

## Practical limits

'''+''.join('- '+x+'\n' for x in report['limits'])+'''
The normal interface remains at http://127.0.0.1:8790/. The existing pairing code was retained. This fix does not change the backing model, servo calibration or hardware connection state. The initial EVALUATION report is historical; FIX_REPORT.json binds the corrected implementation to its regression and live replay evidence.
'''
    for ext in ('md','txt'):(BRAIN/f'duplex/FIX_REPORT.{ext}').write_text(text,encoding='utf-8')
    print(json.dumps({'tests':tests,'replay_turns':len(fixed)+len(fast),'recovered_retries':len(retries),
        'startup_ms':report['startup_after_ms'],'buffer_saved_ms':buffer['improvement_s']*1000}))

if __name__=='__main__':main()
