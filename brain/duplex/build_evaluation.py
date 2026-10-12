"""Summarize measured evidence without rewriting raw synthetic conversations."""
from pathlib import Path
import hashlib,json,statistics,subprocess,sys

BRAIN=Path(__file__).resolve().parents[1]
OUT=BRAIN/'results/voice_refinement_20260914'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def stats(values):
    values=sorted(x for x in values if x is not None)
    return {'n':len(values),'min':min(values),'median':statistics.median(values),'max':max(values)} if values else None

def main():
    commands=[[sys.executable,str(BRAIN/'harness/test_duplex.py')],['node',str(BRAIN/'harness/test_duplex_playback.mjs')],['node',str(BRAIN/'harness/check_face_runtime.cjs')]]
    tests=[]
    for cmd in commands:
        result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
        (OUT/(Path(cmd[-1]).stem+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        tests.append({'test':Path(cmd[-1]).name,'passed':result.returncode==0})
        if result.returncode:raise RuntimeError('Offline test failed: '+cmd[-1])
    final=read(OUT/'conversations_v5/conversations.json')
    tools=read(OUT/'conversations_v6_tools/conversations.json')
    social=[x for x in final if x['case'] in ('greeting','correction','tired','humor')]
    conversion=[v['first_byte_s'] for row in final+tools for v in row['conversion']]
    interrupt=read(OUT/'interrupt_v5/interruption.json')
    counts={}
    for p in OUT.glob('conversations_*/conversations.json'):counts[p.parent.name]=len(read(p))
    examples=[]
    for row in social+tools:
        # These are readable excerpts, not byte-for-byte evidence exports.
        text=' '.join(t['text'].strip() for t in row['transcripts'] if t['role']=='assistant')
        text=text.replace('\u2014',', ').replace('\u2013','-')
        examples.append({'case':row['case'],'reply':text,'tools':[x['name'] for x in row['tools']]})
    source_files=[OUT/'conversations_v5/conversations.json',OUT/'conversations_v6_tools/conversations.json',OUT/'interrupt_v5/interruption.json',OUT/'voice_access.json',OUT/'webrtc_probe_events.json',OUT/'native_probe_events.json']
    report={'status':'Live development harness verified; handset and physical controller untested',
        'native_voice':'Codex V3 WebRTC through installed signed-in app-server','backing_model':'gpt-5.3-codex-spark, low reasoning',
        'voice_id':'24AMj4dc02cYAwoUnqzN','voice_name':'MIST (refined)','native_cli':'0.154.0-alpha.6.2',
        'tests':tests,'synthetic_conversation_counts':counts,'final_social_mic_tail_to_audio_s':stats([x['last_fixture_frame_to_first_converted_audio_s'] for x in social]),
        'final_tool_mic_tail_to_audio_s':stats([x['last_fixture_frame_to_first_converted_audio_s'] for x in tools]),
        'converter_first_byte_s':stats(conversion),
        'interruption':{k:v for k,v in interrupt.items() if k not in ('events','reset_ack_ms')},
        'browser':{'landscape_viewport':[851,393],'named_expression_controls_checked':20,'physical_phone_connected':False,
            'synthetic_browser_call':'Native speech requested happy expression; the rendered happy face persisted after spoken confirmation and status returned to Listening.',
            'observed_browser_errors':[]},
        'examples':examples,'improvements':['Replaced full-reply TTS with native audio performance conversion.',
            'Removed sensor context pushes that triggered unsolicited speech; snapshots are pulled through tools.',
            'Reduced initial conversion segment from 1.2 seconds to 0.8 seconds, retaining 1.2-second follow-on chunks.',
            'Changed tool handoff channel to commentary and added a quiet checking expression.',
            'Preserved preview-versus-hardware wording and corrected the USB/controller distinction.',
            'Added generation cancellation, a live conversion deadline, bounded playback and early transcript stop latching.',
            'Kept explicitly requested expressions through delayed speech and returned the display to Listening when playback ends.'],
        'known_limits':['Observed social latency is seconds, not a claimed subsecond response.',
            'Tool-backed turns remain slower than ordinary voice conversation.',
            'Provider probes included one startup timeout and one early conversion failure; the latter failed silent with original audio muted.',
            'A later slow conversion motivated the 3-second live deadline and clearing pending old speech on a new user turn.',
            'Small audio chunks can introduce seams. Converted speech was checked with ASR, not certified by a human listening panel.',
            'Quiet waiting can keep the native transcript turn open until the next utterance.',
            'Saved preference wording can reflect model or recognition errors; exact stored text is shown in the transcript.',
            'Room echo cancellation, Mi 9 SE microphone/speaker behavior, wireless transport and live sensors need handset testing.',
            'No calibrated servo transport, camera producer or body-attitude fusion is enabled.'],
        'evidence_sha256':{str(p.relative_to(BRAIN)):sha(p) for p in source_files},
        'implementation_sha256':{str(p.relative_to(BRAIN)):sha(p) for p in (BRAIN/'duplex').rglob('*') if p.is_file() and (p.suffix in ('.py','.js','.html','.css') or p.name in ('persona.txt','face_map.json')) and '__pycache__' not in p.parts}}
    (BRAIN/'duplex/EVALUATION.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    social_stat=report['final_social_mic_tail_to_audio_s'];tool_stat=report['final_tool_mic_tail_to_audio_s'];c=report['converter_first_byte_s']
    text=f'''# MIST voice evaluation, 14 September 2026

The native voice and masking path works with the supplied MIST voice. This is a tested development harness; the handset and physical robot were not connected.

The final social cases measured {social_stat['min']:.2f} to {social_stat['max']:.2f} seconds from the last uploaded synthetic microphone frame to the first converted audio packet (median {social_stat['median']:.2f}). The final tool cases measured {tool_stat['min']:.2f} to {tool_stat['max']:.2f} seconds (median {tool_stat['median']:.2f}). These are client-side packet measurements, before the browser's small playback buffer; they are not physical microphone-to-speaker measurements. Earlier fixture runs used sleep-based pacing that stretched input, so those latency values are not mixed into the final summary.

Converter first-byte time across the final social/tool samples had median {c['median']:.2f} seconds and range {c['min']:.2f} to {c['max']:.2f}. This excludes native voice processing and input chunk accumulation. It must not be advertised as total conversation latency.

The interruption test cut off a story, requested blue teacup, and received that correction. Zero old-generation audio packets arrived after the reset acknowledgement. The local clock reported reset within one clock tick, which is not evidence of zero physical latency. Browser playback cancellation and stale-packet rejection passed separate tests.

All offline test commands passed. The existing face checker covers forty faces, 1,600 expression pairs and 31,050 states; twenty expression controls were exercised in an 851 by 393 landscape browser viewport. The mouth follows converted PCM playback. A synthetic converted recording was transcribed again to check broad intelligibility, with differences from the native transcript retained in the raw evidence.

The conversation passes covered greeting, correction, tired-user companionship, a requested joke, sensor availability, phone-pan preview, stop, memory, recall, quiet waiting and returning. Prompt changes reduced unnecessary questions and corrected the pan/USB explanation. The final prompt still cannot guarantee a particular style on every response. The owner should judge the recorded sample and actual conversation on the phone.

## Representative observed replies

'''+''.join(f"- {x['case']}: {x['reply']}\n" for x in examples)+'''
## Remaining work

'''+''.join('- '+x+'\n' for x in report['known_limits'])+'''
The original text/STT/TTS console is preserved. The new mode reuses its face assets and Codex transport but keeps physical robot actuation unavailable. See README.md for launch, pairing, phone routing and the optional SensorServer adapter. EVALUATION.json contains hashes of the exact evidence and current implementation.
'''
    for ext in ('md','txt'):(BRAIN/f'duplex/EVALUATION.{ext}').write_text(text,encoding='utf-8')
    print(json.dumps({'tests':tests,'social':social_stat,'tools':tool_stat,'conversion':c,'conversation_counts':counts}))

if __name__=='__main__':main()
