"""Exercise production native WebRTC with a Luna tool thread and synthetic mic.

The ElevenLabs sink alone is replaced with a recorder. No output audio is played,
no actuator is connected, and preference files are isolated in this run folder.
"""
import argparse
import asyncio
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN))
sys.path.insert(0, str(BRAIN / 'harness'))
from pi_client import load_env
from duplex.runtime import RobotRuntime
from duplex import server


CASES = [
    ('greeting', 'Hi MIST. The printed legs finally fit together. That made my morning.'),
    ('happy_variant', 'Show me your happy face, variation one, for seventeen hundred milliseconds.'),
    ('uncertain', 'Now show your uncertain face for a second, please.'),
    ('sensors', 'Use your sensor tool and tell me which readings are actually available right now.'),
    ('correction', 'Actually, I meant only the printed parts fit. You cannot walk yet. Please keep that distinction clear.'),
    ('tired', 'I am tired today. No advice or cheerful pep talk please. Just keep me company for a moment.'),
    ('long_interrupt', 'Tell me a detailed story about a tiny robot exploring a kitchen, with several surprising turns.'),
    ('quiet', 'Please be quiet now. I will tell you when I am ready to talk again.'),
    ('return', 'I am back. Give me one short, dry joke about your unfinished legs.'),
]
REVISED_CASES = [
    ('greeting', 'Hi MIST. The printed legs finally fit together. That made my morning.'),
    ('happy_variant', 'Show me your happy face, variation one, for seventeen hundred milliseconds.'),
    ('invalid_keep', 'Show your ultraviolet dragon expression, variation ninety nine. If that is not available, leave the face unchanged.'),
    ('correction', 'Actually, I meant only the printed parts fit. You cannot walk yet. Please keep that distinction clear, no joke.'),
    ('uncertain', 'Now show your uncertain face for a second, please.'),
    ('sensors', 'Use your sensor tool and tell me which readings are actually available right now.'),
    ('long_interrupt', 'Tell me a detailed story about a tiny robot exploring a kitchen, with several surprising turns.'),
    ('quiet', 'Please be quiet now. I will tell you when I am ready to talk again.'),
    ('return', 'I am back. Give me one short, dry joke about your unfinished legs.'),
]


class Sink:
    closed = False
    def __init__(self):
        self.events = []
        self.started = time.monotonic()
    async def send_json(self, value):
        self.events.append({**value, 't_s': round(time.monotonic() - self.started, 5)})


class TextRecorder:
    """Same interface as streaming TTS; no synthesis or audible native fallback."""
    def __init__(self, key, emit):
        self.emit = emit
        self.epoch = 0
        self.pending = False
        self.muted = False
        self.events = []
        self.native_audio_bytes = 0
        self.native_first_audio = None
    def diagnostic(self, name, **fields):
        self.events.append({'name': name, **fields, 'at': time.monotonic()})
    async def start(self): pass
    async def warm(self): pass
    async def begin(self, turn_id, audible=True):
        self.pending = True
        self.diagnostic('tts_begin', turn_id=turn_id, audible=audible, epoch=self.epoch)
    async def release(self): self.diagnostic('tts_release', epoch=self.epoch)
    async def text(self, delta): self.diagnostic('tts_text', text=delta, epoch=self.epoch, muted=self.muted)
    async def finish(self, text):
        self.pending = False
        self.diagnostic('tts_finish', text=text, epoch=self.epoch, muted=self.muted)
    async def feed(self, pcm):
        # Native transport audio is counted and discarded, never replayed or saved.
        self.native_audio_bytes += len(pcm)
        if self.native_first_audio is None: self.native_first_audio = time.monotonic()
    async def interrupt(self):
        self.epoch += 1
        self.pending = False
        await self.emit({'type': 'playback_reset', 'epoch': self.epoch})
        self.diagnostic('tts_interrupt', epoch=self.epoch)
    async def close(self): self.pending = False


def summary_case(name, text, events, start, elapsed, interrupted):
    def first(kind, **attrs):
        return next((e['t_s'] - start for e in events if e.get('type') == kind and all(e.get(k) == v for k, v in attrs.items())), None)
    transcripts = [dict(role=e.get('role'), text=e.get('text'), at_s=round(e['t_s']-start, 4)) for e in events if e.get('type') == 'transcript_done']
    user_end = first('transcript_done', role='user')
    first_user_delta = first('transcript_delta', role='user')
    first_reply = next((e['t_s']-start for e in events if e.get('type') == 'transcript_delta' and e.get('role') == 'assistant' and
        first_user_delta is not None and e['t_s']-start >= first_user_delta), None)
    mic_end = first('fixture_finished')
    tools = [e for e in events if e.get('type') == 'tool']
    faces = [e for e in events if e.get('type') == 'face']
    errors = [e for e in events if e.get('type') == 'error']
    reasons = []
    if errors: reasons.append('pipeline_error')
    if not any(t['role'] == 'user' for t in transcripts): reasons.append('no_microphone_transcript')
    if name != 'quiet' and first_reply is None: reasons.append('no_assistant_response')
    if name == 'happy_variant' and not any(e.get('expression') == 'happy' and e.get('variant') == 1 and e.get('duration_ms') == 1700 for e in faces): reasons.append('requested_face_variant_not_emitted')
    if name == 'uncertain' and not any(e.get('expression') == 'uncertain' for e in faces): reasons.append('requested_face_not_emitted')
    if name == 'sensors' and not any(e.get('name') == 'get_sensor_snapshot' for e in tools): reasons.append('sensor_tool_not_called')
    if name == 'invalid_keep' and any(e.get('name') == 'set_expression' for e in tools): reasons.append('unavailable_request_changed_face')
    return {'id': name, 'input': text, 'case_started_t_s': round(start, 5), 'passed': not reasons, 'failures': reasons,
        'transcripts': transcripts, 'tools': tools, 'faces': faces, 'errors': errors,
        'first_assistant_delta_s': first_reply,
        'fixture_end_to_first_delta_s': None if mic_end is None or first_reply is None else round(first_reply-mic_end, 4),
        'user_transcript_end_to_first_delta_s': None if user_end is None or first_reply is None else round(first_reply-user_end, 4),
        'first_tool_s': first('debug_tool', phase='started'),
        'elapsed_s': round(elapsed, 3), 'explicit_interruption': interrupted}


async def run(args):
    os.environ['MIST_BRAIN_MODEL'] = 'gpt-6-luna'
    args.output.mkdir(parents=True, exist_ok=True)
    for name in ('persona.txt', 'native.py', 'server.py'):
        (args.output/('source_' + name)).write_bytes((BRAIN/'duplex'/name).read_bytes())
    sink = Sink()
    env = load_env()
    if not env.get('DEEPGRAM_API_KEY'): raise RuntimeError('Synthetic microphone input provider key unavailable')
    app = {'runtime': RobotRuntime(args.output / 'isolated_runtime'), 'run_dir': args.output / 'native',
        'env': env, 'speech_backend': 'streaming-tts', 'enable_fixtures': True}
    original_sink = server.StreamingTTS
    server.StreamingTTS = TextRecorder
    conversation = server.Conversation(app, sink)
    raw_events = []
    original_handler = conversation.realtime_event
    async def record_event(value):
        raw_events.append({**value, 't_s': round(time.monotonic()-sink.started, 5)})
        await original_handler(value)
    conversation.realtime_event = record_event
    rows = []
    cases = REVISED_CASES if args.suite == 'revised' else CASES
    report = {'architecture': {'front': 'Codex native realtime V3 voice model (identity not exposed by API)',
        'backing_tools': 'gpt-6-luna / low / default service tier', 'mic': 'Deepgram synthetic speech, paced 16 kHz PCM through production MicrophoneTrack',
        'tts': 'Recorder replacing ElevenLabs only; no final MIST audio or speaker latency measured',
        'hardware': 'Isolated production RobotRuntime preview boundary; no actuator transport'},
        'source_sha256': {p.relative_to(BRAIN).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in [BRAIN/'duplex/native.py', BRAIN/'duplex/server.py', BRAIN/'duplex/persona.txt']},
        'cases': rows}
    def save():
        (args.output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        (args.output/'events.json').write_text(json.dumps(sink.events, indent=2), encoding='utf-8')
        (args.output/'native_events.json').write_text(json.dumps(raw_events, indent=2), encoding='utf-8')
        if conversation.mask:
            (args.output/'tts_recorder.json').write_text(json.dumps(conversation.mask.events, indent=2), encoding='utf-8')
    try:
        await asyncio.wait_for(conversation.start(), 55)
        report['startup'] = conversation.voice.startup
        report['ready'] = next((e for e in sink.events if e.get('type') == 'ready'), None)
        print(json.dumps({'phase': 'connected', 'startup': report['startup']}), flush=True)
        save()
        await asyncio.sleep(.7)
        for name, text in cases[:args.limit]:
            begin = time.monotonic()
            relative = begin-sink.started
            offset = len(sink.events)
            fixture = asyncio.create_task(conversation.handle({'type': 'fixture', 'text': text}))
            last_done = None
            interrupted = False
            while time.monotonic()-begin < 35:
                events = sink.events[offset:]
                if fixture.done():
                    fixture.result()
                replies = [e for e in events if e.get('type') == 'transcript_delta' and e.get('role') == 'assistant']
                if name == 'long_interrupt' and replies and not interrupted:
                    await conversation.handle({'type': 'barge_in'})
                    interrupted = True
                    report['interruption_at_s'] = round(time.monotonic()-sink.started, 5)
                # An interrupted assistant can finish while the next fixture is
                # still being recognized. Correlate this input before ending it.
                normalized = lambda value: ''.join(c.lower() for c in value if c.isalnum())
                matched_users = [e for e in events if e.get('type') == 'transcript_done' and e.get('role') == 'user' and
                    SequenceMatcher(None, normalized(text), normalized(e.get('text', ''))).ratio() > .7]
                user_done_at = matched_users[-1]['t_s'] if matched_users else float('inf')
                completed = [e for e in events if e.get('type') == 'transcript_done' and e.get('role') == 'assistant' and e['t_s'] >= user_done_at]
                if completed: last_done = completed[-1]['t_s'] + sink.started
                if name == 'long_interrupt' and interrupted and fixture.done() and time.monotonic()-begin > replies[0]['t_s']-relative+2: break
                if last_done and fixture.done() and time.monotonic()-last_done > (8 if name == 'quiet' else 2): break
                if name == 'quiet' and matched_users and not replies and fixture.done() and time.monotonic()-begin > 15: break
                await asyncio.sleep(.05)
            if not fixture.done():
                fixture.cancel()
                await asyncio.gather(fixture, return_exceptions=True)
            rows.append(summary_case(name, text, sink.events[offset:], relative, time.monotonic()-begin, interrupted))
            print(json.dumps({'case': name, 'passed': rows[-1]['passed'], 'failures': rows[-1]['failures'], 'transcripts': rows[-1]['transcripts'], 'tools': [e['name'] for e in rows[-1]['tools']]}), flush=True)
            save()
            if rows[-1]['errors'] or (len(rows) == 2 and not any(r['transcripts'] for r in rows)): break
            await asyncio.sleep(.35)
        await asyncio.sleep(2)
        report['native_audio_discarded_bytes'] = conversation.mask.native_audio_bytes
        report['passed'] = all(r['passed'] for r in rows) and len(rows) == min(args.limit, len(cases))
        report['case_count'] = len(rows)
        samples = [r['user_transcript_end_to_first_delta_s'] for r in rows if r['user_transcript_end_to_first_delta_s'] is not None and r['user_transcript_end_to_first_delta_s'] >= 0]
        report['latency_median_user_transcript_end_to_delta_s'] = statistics.median(samples) if samples else None
    except Exception as error:
        report['passed'] = False
        report['fatal'] = {'type': type(error).__name__, 'message': str(error)[:600]}
        print(json.dumps({'fatal': report['fatal']}), flush=True)
    finally:
        await conversation.close()
        server.StreamingTTS = original_sink
        report['closed'] = True
        save()
    print(json.dumps({'complete': True, 'passed': report.get('passed'), 'cases': len(rows)}), flush=True)
    return 0 if report.get('passed') else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=9)
    parser.add_argument('--suite', choices=['baseline', 'revised'], default='baseline')
    parser.add_argument('--output', type=Path, default=BRAIN/'results/luna_native_20260922')
    raise SystemExit(asyncio.run(run(parser.parse_args())))
