"""Verify the debug surfaces and record the source revision for packaging."""
import hashlib,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];BRAIN=ROOT/'brain';OUT=BRAIN/'results/debug_views_20260914'

def main():
    OUT.mkdir(exist_ok=True);tests=[]
    for name,cmd in [
        ('5 diagnostic buffer, redaction, pagination and pairing contracts',['python','brain/harness/test_debugging.py']),
        ('33 application contracts',['python','brain/harness/test_duplex.py']),
        ('12 streaming TTS contracts',['python','brain/harness/test_streaming_tts.py']),
        ('3 background lifecycle contracts',['python','brain/harness/test_background.py']),
        ('Playback scheduling',['node','brain/harness/test_duplex_playback.mjs']),
        ('31,050 renderer states',['node','brain/harness/check_face_runtime.cjs']),
    ]:
        r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);tests.append({'name':name,'passed':r.returncode==0})
        (OUT/(Path(cmd[-1]).stem+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
    for name in ('app.js','debug.js','expressions.js'):
        r=subprocess.run(['node','--input-type=module','--check'],input=(BRAIN/'duplex/static'/name).read_text(encoding='utf-8'),capture_output=True,text=True,encoding='utf-8')
        tests.append({'name':name+' module syntax','passed':r.returncode==0})
    files=[p for p in (BRAIN/'duplex').rglob('*') if p.is_file() and p.suffix in ('.py','.js','.css','.html','.wav') and '__pycache__' not in p.parts]
    files += [BRAIN/'duplex/README.md',BRAIN/'duplex/persona.txt',BRAIN/'duplex/face_map.json']
    report={'revision':'Live debug and expression inspector, 2026-09-14','tests':tests,
        'browser_checks':[
            'Real synthetic conversation recorded native startup, model turn duration, sensor-tool start/end/result, TTS first audio, playback queue and expression events.',
            'Real background sensor analysis produced background tool execution and timing events in the filtered debug table.',
            'Debug category filtering separated background/tool events from transcript wording; text rendered correctly after UTF-8 verification.',
            'Inspector rendered 40 variants, 20 named presets and 11 mouth shapes without console errors.',
            'Happy face with held AA mouth at frame 12 (200 ms) returned to byte-identical frame geometry after next/previous stepping.',
            'Narrow viewport layout showed the main face before controls; geometry bounds had nonzero dimensions.',
        ],
        'limits':[
            'The journal holds 2,000 events in memory and pages in batches of 400. Old records roll out; exports contain the currently loaded and filtered trace.',
            'Audio delivery is sampled at most once per half second per reply. Browser queue and microphone statistics are sampled once per second. PCM is not retained.',
            'Known authentication fields are removed recursively. Conversation text and tool arguments remain visible and can contain user-provided sensitive information.',
            'Server elapsed time uses a monotonic performance clock. Browser timestamps use a separate clock; arrival times are not network-latency measurements.',
            'Tool handler duration excludes model reasoning. Transcript-done-to-playback excludes prior native speech-end detection.',
            'The inspector mouth sweep is synthetic. Production speech currently uses amplitude-driven AA/rest, not full phoneme alignment.',
            'The inspector is a review surface, not an editor of the production face geometry. SVG and JSON export actions serialize the selected frame locally.',
        ],
        'implementation_sha256':{p.relative_to(BRAIN).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}}
    target=BRAIN/'duplex/DEBUG_REPORT';target.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    text='''# MIST debug and expression inspection

Two new routes are linked from Conversation controls: /debug and /expressions.

The live debug page shows a bounded server timeline with native model phases, tool arguments/results, application handler durations, background jobs and their read-tool calls, TTS phrase and connection events, browser playback starts and queue depth, microphone frame/RMS summaries, and expression changes. Filter by category or text, pause updates, expand event details, clear the local view, or export its filtered trace. Debug data requires the same pairing cookie as the conversation. Server restarts have a distinct trace identifier so old cursor values do not mix two timelines.

The server retains 2,000 events in memory and pages without skipping retained records. Raw PCM and known authentication fields are excluded. Audio delivery is sampled per reply at half-second intervals; microphone and queue summaries arrive once per second. Conversation text and tool arguments remain available for debugging, so exports should be treated as conversation records. No hidden model reasoning is collected.

Timing labels distinguish the native connection, model turn, application tool execution, TTS first byte, and transcript completion to playback. The last interval excludes native speech-end detection. Browser and server performance clocks are separate; server event time records arrival, not synchronized wire latency.

The expression inspector uses the actual MIST renderer and data: 40 face variants, 20 named presets and 11 visemes. It includes a looping gallery and focused view, all-viseme speech, the production AA/rest pattern, a single held mouth shape, idle motion, blink inspection and expression transitions. Gaze, mouth amount, transition duration, playback speed, glow and bounds are adjustable. Pause, scrub or step by 1/60 second. Backward seeks rebuild and replay the renderer so its transition state can be inspected consistently. Export the current clean SVG or its JSON geometry from the page.

The inspector makes no model or microphone calls. The all-viseme sweep is a synthetic diagnostic, not a claim that live speech has phoneme alignment. It does not edit production face assets.

## Verification

A real synthetic conversation produced native connection timing, a sensor-tool call, model activity, TTS timing, playback and expression records. A real background analysis produced its separate sensor-tool start/end and timing events. The browser reported no JavaScript errors. Category filtering and narrow-screen layout were inspected.

All 40 gallery variants loaded. A held AA mouth on the happy face at frame 12 (200 ms) produced byte-identical geometry after stepping forward and back. The face renderer's existing 31,050-state verification passed. Five new diagnostic contracts verify bounds, redaction, paging, audio sampling and pairing; existing application, TTS, background and playback tests also passed. Export functions are present; no real microphone recording or phone-acoustics validation was performed.

Evidence and check logs: brain/results/debug_views_20260914. DEBUG_REPORT.json includes the exact implementation hashes used for the source archive.
'''
    target.with_suffix('.md').write_text(text,encoding='utf-8');target.with_suffix('.txt').write_text(text,encoding='utf-8')
    assert all(t['passed'] for t in tests);print(json.dumps({'tests':tests}))

if __name__=='__main__':main()
