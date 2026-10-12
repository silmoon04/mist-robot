"""Record the playback revision, including unsuccessful live observations."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRAIN = ROOT / 'brain'
OUT = BRAIN / 'results/voice_quality_20260914'


def main():
    tests = []
    for name, command in [
        ('33 offline contracts', ['python', 'brain/harness/test_duplex.py']),
        ('6 converter recovery contracts', ['python', 'brain/harness/test_voice_recovery.py']),
        ('Browser audio scheduler contracts', ['node', 'brain/harness/test_duplex_playback.mjs']),
        ('40 faces and 31,050 renderer states', ['node', 'brain/harness/check_face_runtime.cjs']),
    ]:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        (OUT / (Path(command[-1]).stem + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
        tests.append({'name': name, 'passed': result.returncode == 0})
    conversations = json.loads((OUT / 'conversations/conversations.json').read_text())
    observations = []
    for folder in ['interruption', 'native_interruption_diagnostic', 'manual_interruption_diagnostic']:
        result = json.loads((OUT / folder / 'interruption.json').read_text())
        observations.append({'name': folder, **{k: v for k, v in result.items() if k != 'events'}})
    paths = [p for p in (BRAIN / 'duplex').rglob('*') if p.is_file() and
             p.suffix in ('.py', '.js', '.html', '.css') and '__pycache__' not in p.parts]
    paths.extend([BRAIN / 'duplex/face_map.json', BRAIN / 'duplex/persona.txt'])
    report = {
        'revision': 'Playback continuity and thinking expression, 2026-09-14',
        'status': 'Ready for another listening trial; subjective quality and room echo are not verified.',
        'tests': tests,
        'live_conversations': [{
            'case': row['case'], 'errors': row['errors'], 'warnings': row['warnings'],
            'last_fixture_frame_to_first_converted_audio_s': row['last_fixture_frame_to_first_converted_audio_s'],
            'conversion_requests': len(row['conversion']),
        } for row in conversations],
        'interruption_observations': observations,
        'limits': [
            'One initial explicit-interruption trial produced a corrected native transcript but no converted correction audio within the test window. Subsequent native and explicit interruption trials returned new audio. This intermittent observation is not resolved by the passing repeats.',
            'Live tests use synthetic input. No claim is made about loudspeaker echo or recognition of a real user speaking over playback.',
            'The 200 ms startup reserve is additional to server-measured first-packet timings.',
            'A native-interruption acknowledgement measurement includes synthetic speech generation and delivery; it is not a microphone-to-stop latency measurement.',
            'Acoustic pause detection is not sentence segmentation. Long voiced passages can still be cut at the 1.8-second cap.',
            'Independent Voice Changer requests can still introduce seams. No listening-panel quality score is available.',
        ],
        'sources': [
            'https://elevenlabs.io/docs/api-reference/speech-to-speech/stream',
            'https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/realtime-tts',
        ],
        'implementation_sha256': {p.relative_to(BRAIN).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)},
    }
    target = BRAIN / 'duplex/QUALITY_REPORT'
    target.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    text = '''# MIST playback revision

The 400 ms first upload was too short to preserve context and could finish playing before the next passage arrived. The current bridge uses a consistent 1.8-second cap, preferring pauses after 800 ms of context. A completed short phrase can still flush earlier after silence. The browser adds a 200 ms startup reserve and schedules subsequent audio packets contiguously. A three-second audio burst no longer triggers the old backlog reset.

Microphone capture continues during playback. Volume alone no longer cancels speech: native user-turn events clear the old playback generation, including audio already delivered to the browser. Stop speaking remains immediate. Browser echo cancellation is requested, but this does not establish reliable room echo handling.

Thinking uses a closed line mouth and a slight upward, sideways gaze. Listening and speaking remain distinct. Thinking is explicitly selected while preparing a response or checking a tool, and speech animation follows the playback clock. Updated asset URLs prevent stale cached mappings from concealing the revision. The thinking pose was visually checked in the app browser.

The backing Spark model, native Codex voice path and MIST voice ID are unchanged. Voice Changer accepts finite audio uploads and streams their converted output. ElevenLabs' incremental text WebSocket is a possible alternative for a later comparison, but would synthesize a new performance from text.

## Checks and remaining uncertainty

All 33 offline application contracts, six conversion recovery tests, browser scheduler checks and 31,050 renderer states passed. Three live synthetic conversations returned converted audio without error or warning. First converted packets arrived 2.56, 3.91 and 2.67 seconds after the final synthetic microphone frame. The browser reserve adds another 200 ms when playback starts.

The latest native-turn interruption and explicit-stop trials cleared old audio generations, followed the correction and produced new audio. One initial explicit-stop trial produced the corrected transcript but no converted correction audio within the observation window. That failure remains in the evidence; passing repeats do not establish that it is fixed.

These tests do not establish human-perceived voice quality, seamless conversational overlap, loudspeaker echo rejection or Mi 9 SE performance. Independent conversion requests still have a latency and prosody tradeoff. The current build is ready for another listening trial, not a claim of production voice reliability.

Evidence: brain/results/voice_quality_20260914. The JSON companion records exact implementation hashes, tests and observations. Earlier FIX_REPORT files describe the superseded 400 ms first-segment policy and remain historical records.

API references:
https://elevenlabs.io/docs/api-reference/speech-to-speech/stream
https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/realtime-tts
'''
    target.with_suffix('.md').write_text(text, encoding='utf-8')
    target.with_suffix('.txt').write_text(text, encoding='utf-8')
    print(json.dumps({'tests': tests, 'report': str(target.with_suffix('.md'))}))
    assert all(t['passed'] for t in tests)


if __name__ == '__main__':
    main()
