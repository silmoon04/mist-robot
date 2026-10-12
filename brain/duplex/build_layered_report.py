"""Record layered execution, phrase timing and the final source revision."""
import hashlib,json,subprocess,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];BRAIN=ROOT/'brain';OUT=BRAIN/'results/layered_brain_20260914'

def main():
    baseline=OUT/'phrases/previous_tts.py'
    if not baseline.exists():
        with zipfile.ZipFile(BRAIN/'duplex/MIST_Native_Voice_20260914.zip') as z:
            baseline.write_bytes(z.read('MIST_Native_Voice/brain/duplex/tts.py'))
    tests=[]
    for name,cmd in [
        ('33 application contracts',['python','brain/harness/test_duplex.py']),
        ('12 streaming TTS contracts',['python','brain/harness/test_streaming_tts.py']),
        ('7 phrase boundary contracts',['python','brain/harness/test_phrasing.py']),
        ('3 background lifecycle contracts',['python','brain/harness/test_background.py']),
        ('6 legacy recovery contracts',['python','brain/harness/test_voice_recovery.py']),
        ('Playback scheduling',['node','brain/harness/test_duplex_playback.mjs']),
        ('Expression wording cues',['node','brain/harness/test_delivery.mjs']),
        ('31,050 face renderer states',['node','brain/harness/check_face_runtime.cjs']),
    ]:
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        (OUT/(Path(cmd[-1]).stem+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
        tests.append({'name':name,'passed':r.returncode==0})
    read=lambda p:json.loads((OUT/p).read_text(encoding='utf-8'))
    worker=read('worker_result.json');parallel=read('parallel_audio.json');conversation=read('conversation/result.json')
    phrases=read('phrases/comparison.json');recognition=read('phrases/recognition.json');social=read('social/conversations.json')
    assert worker['passed'] and parallel['passed'] and conversation['passed'] and all(r['passed'] for r in recognition)
    assert all(not r['errors'] and not r['warnings'] for r in social)
    files=[p for p in (BRAIN/'duplex').rglob('*') if p.is_file() and p.suffix in ('.py','.js','.css','.html','.wav') and '__pycache__' not in p.parts]
    files += [BRAIN/'duplex/README.md',BRAIN/'duplex/persona.txt',BRAIN/'duplex/face_map.json']
    report={'revision':'Independent background reasoning and phrase streaming, 2026-09-14','tests':tests,
        'layers':[
            {'role':'Conversation','implementation':'Native Codex V3 voice, with its existing Spark application-tool bridge'},
            {'role':'Background analysis','implementation':'Separate ephemeral Spark model session with read-only sensor and preference tools'},
            {'role':'Speech','implementation':'ElevenLabs Flash v2.5, one context per reply, MIST voice unchanged'},
            {'role':'Coordination','implementation':'Bounded job mailbox, cancellation, revision checks, and playback/user-speech idle checks'},
        ],
        'background_submission_ack_ms':parallel['submission_receipt_ms'],
        'background_analysis_s':parallel['analysis_s'],
        'speech_packets_during_analysis':parallel['audio_packets_during_real_analysis'],
        'standalone_worker':{k:worker[k] for k in ('submit_ack_ms','event_loop_ticks','max_tick_ms','elapsed_s','passed')},
        'private_handoff':{k:v for k,v in conversation.items() if k!='events'},
        'phrase_comparison':phrases,'phrase_audio_recognition':recognition,
        'ordinary_reply_first_packet_s':[r['last_fixture_frame_to_first_converted_audio_s'] for r in social],
        'browser_playback_reserve_s':.2,
        'limits':[
            'Sub-millisecond submission acknowledgement starts after the request reaches the application. Native model routing before that point can still take seconds.',
            'Phrase comparisons use two controlled text examples and a fixed input cadence, not a population latency benchmark. Same-context synthesis reduces but cannot guarantee elimination of prosody seams.',
            'The first conversational background probe merged the extra spoken input into the existing native user turn. A separate live probe then verified speech packets continuing during a real background model job.',
            'Background completions are auto-delivered only when the original user turn is still current and speech/tool activity is idle. Other results remain in the mailbox for explicit retrieval.',
            'The background worker cannot actuate hardware or change preferences. Existing movement commands remain bounded previews.',
            'Speech recognition and waveform checks do not establish subjective naturalness or real phone echo handling.',
        ],
        'baseline_tts_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),
        'implementation_sha256':{p.relative_to(BRAIN).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}}
    target=BRAIN/'duplex/LAYERED_REPORT';target.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    text='''# MIST layered conversation and phrase streaming

The conversation and background reasoning now run independently. Native Codex V3 retains the live microphone and conversation. Its existing Spark tool bridge can start a separate Spark analyst, receiving a job receipt without waiting for the answer. ElevenLabs Flash v2.5 produces speech from phrase chunks using the same MIST voice and one synthesis context per reply.

```mermaid
flowchart LR
  Mic[Microphone] --> Voice[Native conversation]
  Voice --> Phrases[Phrase grouping]
  Phrases --> TTS[Streaming TTS]
  TTS --> Speaker[Speaker and face]
  Voice <--> Bridge[Application tool bridge]
  Bridge --> Analyst[Independent analyst]
  Analyst --> ReadTools[Read sensors and preferences]
  Analyst --> Mailbox[Private result mailbox]
  Mailbox --> Voice
```

## Coordination

The new tools are start_background_task, background_task_status and cancel_background_task. Controls also offer a typed background question and Cancel analysis. A single analyst runs at a time, with bounded output and a 45-second reasoning limit. Duplicate requests in the same user turn reuse the existing job. The analyst has no motion, filesystem, shell or preference-write tools.

Results are summaries and tool receipts, not inner reasoning traces. A completed result can be supplied privately to the conversation when the original user turn is still current and user speech, playback and tool delegation are idle. Otherwise it remains available for an explicit follow-up. Cancellation prevents late results from publishing. Ending the conversation closes the independent model process, including cancellation during startup.

## Speech and expression

Text is grouped at full sentences or substantial comma/semicolon clauses, keeping short prefaces and decimal values intact. An unpunctuated stream has a 140-character whole-word fallback. The same TTS context remains open across all phrases, preserving continuity. The prompt favors a short useful opening, natural clause punctuation and varied rhythm. Automatic happy or curious expressions use conservative opening-word cues once per reply at playback start; manual selections take priority. No voice identity change, pitch shift or spoken emotion tags were introduced.

## Evidence and latency

A live test started real background reasoning during an ongoing spoken story. The application acknowledged the request in 0.65 ms; the analyst completed in 5.54 seconds, using its tools while 39 speech packets continued to reach the client. This acknowledgement excludes the model-routing delay before an application request arrives.

A separate conversational test started work through the model, accepted more spoken input, answered a greeting, and retrieved the completed result through background_task_status. Native voice combined that additional input with the current user turn, so the separate story probe supplies the stronger evidence for simultaneous speech and reasoning.

The standalone analyst used a real sensor tool. After moving startup imports off the event loop, its longest observed 20 ms heartbeat interval was about 35.7 ms. This is one desktop measurement, not a real-time scheduling guarantee.

In controlled phrase tests, first audio improved from 766 to 594 ms for a longer clause and from 765 to 204 ms for short sentences. Independent speech recognition recovered all words in both new recordings. These are two examples at a fixed text-input cadence, not a guarantee for every response.

Two ordinary spoken conversations returned first audio packets about 1.80 seconds after the final synthetic input frame. The browser adds its existing 200 ms reserve, keeping total ordinary response near two seconds. Native turn detection still sets that floor; background task routing and tool-dependent answers can take longer.

All 33 application, 12 TTS, seven phrasing, three background lifecycle and six legacy recovery contracts passed, along with playback checks, expression cues and 31,050 renderer states. Cancellation, stale result suppression, microphone forwarding and private idle delivery have deterministic coverage. Human-perceived prosody and real handset echo remain listening tests.

Evidence: brain/results/layered_brain_20260914. LAYERED_REPORT.json contains measurements and implementation hashes. Earlier reports remain historical. The default service is still python brain/duplex/server.py on port 8790. Background Spark can be selected through MIST_BACKGROUND_MODEL without changing the conversation model.
'''
    target.with_suffix('.md').write_text(text,encoding='utf-8');target.with_suffix('.txt').write_text(text,encoding='utf-8')
    assert all(t['passed'] for t in tests)
    print(json.dumps({'tests':tests,'speech_packets_during_analysis':report['speech_packets_during_analysis'],'ordinary_reply_first_packet_s':report['ordinary_reply_first_packet_s']}))

if __name__=='__main__':main()
