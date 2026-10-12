"""Publish selected, public-safe experiment outputs in the local voice studio."""
from pathlib import Path
import json
import shutil
from html import escape

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'brain/results/dual-model-harness-20260924'
PUBLIC = ROOT / 'brain/duplex/static/affect'


def publish():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    # Copy only explicit reports and generated test audio, never run state or credentials.
    for folder, names in {
        'comparison-rerun': ['index.html', 'comparison.json', 'COMPARISON.md', 'SEMANTIC-REVIEW.md'],
        'comparison': ['index.html', 'comparison.json', 'COMPARISON.md'],
        'prosody': ['index.html', 'results.json', 'v3-attempt-01-original-client-error.json', 'flash-timeout-evidence.json'],
    }.items():
        source = RESULTS / folder
        target = PUBLIC / folder
        target.mkdir(exist_ok=True)
        for name in names:
            path = source / name
            if path.is_file():
                shutil.copyfile(path, target / name)
        if folder == 'prosody':
            for path in source.glob('*.wav'):
                shutil.copyfile(path, target / path.name)
    probes = sorted((RESULTS / 'live-smoke').glob('probe-*/probe-summary.json'))
    if probes:
        source = probes[-1].parent
        target = PUBLIC / 'live-smoke'
        target.mkdir(exist_ok=True)
        for name in ['probe-summary.json', 'public-trace.json', 'timeline.json', 'LIVE-SMOKE.md']:
            shutil.copyfile(source / name, target / name)
        report = json.loads((source / 'probe-summary.json').read_text(encoding='utf-8'))
        turns = report['turns']
        timely = sum(t.get('affect_outcome') == 'applied_before_speech' for t in turns)
        late = sum(t.get('affect_outcome') == 'speech_already_started' for t in turns)
        voiced = sum(t.get('audio_bytes', 0) > 0 for t in turns)
        live_summary = (f'{len(turns)} typed turns through the real conversation server, Qwen speaker, '
                        f'Qwen expression reader and ElevenLabs. {voiced} returned audio. '
                        f'{timely} reader results arrived before speech generation; {late} were discarded as late.')
        rows = ''.join('<tr>'+''.join('<td>'+escape(str(value))+'</td>' for value in [
            turn['number'], turn['prompt'], turn.get('affect_outcome'),
            turn.get('affect_elapsed_ms'), turn.get('audio_seconds'), turn.get('assistant_text')])+'</tr>'
            for turn in report['turns'])
        (target / 'index.html').write_text('''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>MIST · Live integration check</title><style>body{font:15px/1.5 system-ui;margin:30px;color:#25332e;background:#f4f3ee}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #ccd1c8}a{color:#205f4e}</style>
<a href="../index.html">Face and voice</a><h1>Live integration check</h1>
<p>'''+escape(live_summary)+'''</p>
<p>This tests provider integration. It does not measure microphone recognition, browser playback or human quality.</p>
<table><thead><tr><th>Turn</th><th>Input</th><th>Reader outcome</th><th>Reader ms</th><th>Audio seconds</th><th>Reply</th></tr></thead><tbody>'''+rows+'''</tbody></table>
<p><a href="public-trace.json" download>Public trace</a> · <a href="probe-summary.json" download>Measurements</a></p>''',encoding='utf-8')
    body = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MIST · Face and voice</title><link rel="icon" href="data:,"><style>
*{box-sizing:border-box}body{font:16px/1.55 system-ui,sans-serif;background:#f4f3ee;color:#25332e;margin:0}
main{max-width:940px;padding:32px 24px 64px;margin:auto}nav{display:flex;gap:24px;border-bottom:1px solid #ccd1c8;padding-bottom:16px}
a{color:#205f4e;text-underline-offset:4px}h1{font-size:27px;font-weight:600;margin:32px 0 14px}h2{font-size:18px;font-weight:600}
p{max-width:76ch}section{padding:16px 0;border-bottom:1px solid #ccd1c8}.row{display:grid;grid-template-columns:1fr 1fr;gap:28px}
small{color:#5e685f}code{font:14px ui-monospace,monospace}li{margin:8px 0}details{margin:18px 0}summary{cursor:pointer}
@media(max-width:650px){.row{grid-template-columns:1fr;gap:0}main{padding:20px 18px}}
</style></head><body><main>
<nav><a href="/try">Try a conversation</a><a href="/duplex/expectations/index.html">Earlier conversation review</a></nav>
<h1>Face and voice</h1>
<p>A selected face now stays through listening, thinking and speaking. A timed flash returns to the previous face. Blinks and mouth timing still follow the existing animation and audio code.</p>
<section class="row"><div><h2>Try the separate reader</h2>
<p>In Voice trials, choose <b>Qwen · separate expression reader</b> or <b>Qwen · GPT-OSS expression reader</b>. The original default remains available.</p>
<p>Qwen writes the reply and calls tools. The second model proposes a face and voice setting from the conversation. It cannot speak or move the robot.</p></div>
<div><h2>Timing and ownership</h2><p>Speech does not wait for the reader. A late proposal is discarded, as is a proposal overtaken by a new user turn or a face replacement. Explicit face requests take priority.</p>
<p>Look for <code>affect_decision</code> and <code>speech_style</code> in the saved trace. They show the proposal, evidence, elapsed time, rejection reason and setting actually sent to ElevenLabs.</p></div></section>
<section><h2>Measurements</h2><ul>
<li><a href="comparison-rerun/index.html">Speaker and reader comparison</a> · authored conversation cases, real model calls, no microphone or playback measurement.</li>
<li><a href="comparison-rerun/SEMANTIC-REVIEW.md">Independent review of the choices</a> · wording, face selection and missed timing.</li>
<li><a href="prosody/index.html">Listen to the voice samples</a> · fixed sentence, existing MIST voice, provider timing and failures.</li>
<li><a href="live-smoke/index.html">Live integration check</a> · three typed turns through the real speaker, expression reader and voice stream.</li>
</ul><p>These tests can show whether a proposal arrives in time and follows the contract. They do not establish that a conversation feels more human.</p>
<details><summary>Retained failed comparison</summary><p>The first runner lost its combined-arm results after a local aggregation error. Its results are retained separately: <a href="comparison/index.html">failed run</a>. They cannot be used for a model ranking.</p></details></section>
<section><h2>What ElevenLabs can change</h2>
<p>The current Flash stream can vary stability per reply. The experimental profiles named warm, gentle, bright and serious are setting choices, not guaranteed emotions. All phrases in one reply use the same setting.</p>
<p>Eleven v3 supports expressive tags through a different dialogue streaming API. It produced audio with your MIST voice for plain text, <code>[curious]</code> and <code>[excited]</code>. Listen to the samples above. It is not the live studio's voice backend.</p>
<p><a href="https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/tts-vs-ttd-websockets">Streaming APIs</a> · <a href="https://elevenlabs.io/docs/api-reference/voices/settings/get">Voice settings</a></p></section>
<section><h2>Listen for</h2><p>Does the voice fit what MIST is saying? Does the face remain appropriate after a correction? Does a brief interruption stop the old response without leaving an old tone on the next reply? Compare those moments across architectures, then export the session trace.</p></section>
<p><small>Local experiments · 24 September 2026. Robot tools remain previews.</small></p>
</main></body></html>'''
    (PUBLIC / 'index.html').write_text(body, encoding='utf-8')
    return PUBLIC


if __name__ == '__main__':
    print(publish())
