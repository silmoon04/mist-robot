"""Bounded typed-turn comparison through the live trial conversation adapter.

Audio and recognition are replaced by local sinks; model, application tools,
history, persona, and optional expression reader use the production trial path.
Each planned sample is recorded once, including failures. Never retry samples.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import sys
import time
from datetime import datetime, timezone

BRAIN = Path(__file__).resolve().parents[2]
ROOT = BRAIN.parent
sys.path.insert(0, str(BRAIN))
from duplex.live_studio import ARCHITECTURES, TrialConversation
from duplex.runtime import RobotRuntime
from benchmarks.naturalness.cascade_voice import CascadeVoice
from benchmarks.naturalness.cerebras_client import CerebrasClient
from harness.pi_client import load_env

DEFAULT_CASES = BRAIN / 'results/architecture-cost-20260928/cases.json'
DEFAULT_OUT = BRAIN / 'results/architecture-cost-20260928/model'
ARMS = ('cerebras-balanced', 'qwen-none', 'qwen-low', 'qwen-assist', 'qwen-affect')
CALIBRATION_CASES = ('ac29.constraint_reasoning', 'ac29.clarify_only_when_needed')
SOURCE_FILES = (
    'benchmarks/naturalness/architecture_comparison_20260928.py',
    'benchmarks/naturalness/cascade_voice.py',
    'benchmarks/naturalness/cerebras_client.py',
    'duplex/live_studio.py', 'duplex/server.py', 'duplex/background.py',
    'duplex/affect_director.py', 'duplex/affect_controller.py',
    'duplex/conversation_policy.py', 'duplex/persona.txt',
    'duplex/runtime.py', 'duplex/expression_requests.py',
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    os.replace(temporary, path)


class Sink:
    epoch = 0
    muted = False
    pending = {}
    async def start(self): pass
    async def warm(self): pass
    async def close(self): pass
    async def begin(self, *args, **kwargs): pass
    async def release(self): pass
    async def text(self, text): pass
    async def finish(self, text): pass
    async def interrupt(self):
        self.epoch += 1
    async def feed(self, *args, **kwargs): pass
    def diagnostic(self, *args, **kwargs): pass


class Journal:
    def __init__(self, trace_id): self.trace_id = trace_id
    def record(self, *args, **kwargs): pass


class Wire:
    closed = False
    def __init__(self):
        self.events = []
        self.zero = time.perf_counter()
    async def send_json(self, event):
        self.events.append({'at_ms': round((time.perf_counter()-self.zero)*1000, 2), 'event': event})


def event_slice(wire, begin):
    base = wire.events[begin]['at_ms'] if begin < len(wire.events) else (time.perf_counter()-wire.zero)*1000
    return [{'at_ms': round(row['at_ms']-base, 2), 'event': row['event']}
            for row in wire.events[begin:]]


def summarize_turn(events, user, index):
    def first(predicate):
        return next((row['at_ms'] for row in events if predicate(row['event'])), None)
    finish = next((row for row in reversed(events) if row['event'].get('type') == 'debug_model'
                   and row['event'].get('phase') in ('thinking_finished', 'model_failed')), None)
    completed = [row for row in events if row['event'].get('type') == 'debug_tool'
                 and row['event'].get('phase') == 'finished' and row['event'].get('success')]
    text_done = [row['event'].get('text', '') for row in events if row['event'].get('type') == 'transcript_done'
                 and row['event'].get('role') == 'assistant']
    reader = [row for row in events if row['event'].get('type') == 'affect_decision']
    timing = (finish or {}).get('event', {}).get('timings', {})
    rounds = timing.get('http_requests', []) if isinstance(timing, dict) else []
    usage = {'input_tokens': 0, 'output_tokens': 0, 'reasoning_tokens': 0,
             'rounds_with_usage': 0, 'rounds_missing_usage': 0}
    for item in rounds:
        u = item.get('usage') or {}
        if u:
            usage['rounds_with_usage'] += 1
        else:
            usage['rounds_missing_usage'] += 1
        usage['input_tokens'] += u.get('prompt_tokens', 0) or 0
        usage['output_tokens'] += u.get('completion_tokens', 0) or 0
        usage['reasoning_tokens'] += (u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) or 0
    return {
        'turn_index': index, 'user': user,
        'text': text_done[-1] if text_done else '',
        'first_nonempty_text_ms': first(lambda e: e.get('type') == 'transcript_delta' and e.get('role') == 'assistant' and bool(e.get('text', '').strip())),
        'first_tool_start_ms': first(lambda e: e.get('type') == 'debug_tool' and e.get('phase') == 'started'),
        'first_completed_tool_ms': completed[0]['at_ms'] if completed else None,
        'model_complete_ms': finish['at_ms'] if finish else None,
        'status': ((finish or {}).get('event', {}).get('phase') or 'timeout'),
        'model_errors': (finish or {}).get('event', {}).get('errors'),
        'tool_calls': [{'name': row['event'].get('name'), 'success': row['event'].get('success'),
                        'result': row['event'].get('result'), 'at_ms': row['at_ms']}
                       for row in events if row['event'].get('type') == 'debug_tool' and row['event'].get('phase') == 'finished'],
        'reader': [{'phase': row['event'].get('phase'), 'at_ms': row['at_ms'],
                    'outcome': row['event'].get('outcome'), 'trace': row['event'].get('trace'),
                    'decision': row['event'].get('decision')} for row in reader],
        'rounds': rounds, 'usage': usage,
        'usage_complete': bool(rounds) and usage['rounds_missing_usage'] == 0,
        'stop_reasons': [r.get('finish_reason') for r in rounds],
    }


def instrument_reader(session):
    """Retain expression-reader provider rounds without changing its decision."""
    if not session.affect:
        return
    reader = session.affect.reader
    holder = {}
    class CapturingClient(CerebrasClient):
        def ask(self, *args, **kwargs):
            result = super().ask(*args, **kwargs)
            holder['result'] = result
            return result
    original = reader.decide_with_trace
    reader.client_factory = CapturingClient
    def traced(snapshot):
        holder.clear()
        decision, trace = original(snapshot)
        result = holder.get('result')
        if result is not None:
            timing = getattr(result, 'timings', {})
            trace['http_requests'] = timing.get('http_requests', [])
            trace['reasoning_tokens'] = timing.get('reasoning_output_tokens')
            trace['usage_complete'] = all(bool(r.get('usage')) for r in trace['http_requests'])
        else:
            trace['usage_complete'] = False
        return decision, trace
    reader.decide_with_trace = traced


def check_assertions(case, turns):
    output = []
    for assertion in case.get('assertions', []):
        idx = assertion.get('turn_index', len(turns)-1)
        if idx >= len(turns):
            output.append({'assertion': assertion, 'pass': None, 'reason': 'turn_unavailable'})
            continue
        t = turns[idx]
        names = [call['name'] for call in t['tool_calls']]
        kind = assertion.get('kind')
        name = assertion.get('name')
        if kind == 'tool_called': good = name in names
        elif kind == 'tool_not_called': good = not names if name == '*' else name not in names
        elif kind == 'text_contains': good = any(s.casefold() in t['text'].casefold() for s in assertion.get('any_of', []))
        else:
            output.append({'assertion': assertion, 'pass': None, 'reason': 'human_or_unknown_kind'})
            continue
        output.append({'assertion': assertion, 'pass': good})
    return output


async def sample(sample_id, architecture, case, run_dir):
    wire = Wire()
    run_dir.mkdir(parents=True, exist_ok=True)
    app = {'run_dir': run_dir, 'runtime': RobotRuntime(run_dir / 'state'),
           'env': {**load_env(), **os.environ}, 'speech_backend': 'streaming-tts',
           'enable_fixtures': False}
    session = TrialConversation(app, wire, architecture, Journal(sample_id))
    instrument_reader(session)
    session.mask = Sink()
    voice = CascadeVoice(session.runtime, run_dir / 'voice', session.emit, session.mask.feed,
                         session.realtime_event, speech_backend='streaming-tts', background=session.brain,
                         expression_revision=lambda: session.expression_revision,
                         request_text=lambda: session.user_request_text,
                         provider=architecture['provider'], model=architecture['model'],
                         floor=architecture['floor'], endpoint_ms=architecture['endpoint_ms'],
                         incomplete_hold_ms=architecture['incomplete_hold_ms'],
                         reasoning_effort=architecture['reasoning_effort'],
                         max_output_tokens=architecture['max_output_tokens'],
                         conversation_policy=architecture['conversation_policy'],
                         parallel_tool_calls=architecture['parallel_tool_calls'])
    session.voice = voice
    voice.loop = asyncio.get_running_loop()
    turns = []
    try:
        voice.client = await asyncio.to_thread(voice.make_client)
        ask_results = []
        original_ask = voice.client.ask
        def captured_ask(*args, **kwargs):
            result = original_ask(*args, **kwargs)
            ask_results.append(result)
            return result
        voice.client.ask = captured_ask
        voice.task(voice.model_worker())
        for index, turn in enumerate(case['turns']):
            begin = len(wire.events)
            await session.handle({'type': 'text', 'text': turn['user']})
            deadline = time.perf_counter() + 49
            while time.perf_counter() < deadline:
                if any(row['event'].get('type') == 'debug_model' and row['event'].get('phase') in ('thinking_finished', 'model_failed')
                       for row in wire.events[begin:]):
                    break
                await asyncio.sleep(.04)
            if session.affect and session.affect.task:
                try: await asyncio.wait_for(asyncio.shield(session.affect.task), timeout=10)
                except asyncio.TimeoutError: pass
            captured = event_slice(wire, begin)
            turns.append(summarize_turn(captured, turn['user'], index))
            if len(ask_results) > index:
                result = ask_results[index]
                turns[-1]['provider_result'] = {
                    'input_tokens': result.input_tokens, 'output_tokens': result.output_tokens,
                    'errors': result.errors, 'timings': getattr(result, 'timings', {}),
                    'total_s': result.total_s}
            if turns[-1]['status'] != 'thinking_finished':
                break
        return {'sample_id': sample_id, 'case_id': case['id'], 'arm': architecture['id'],
                'turns': turns, 'assertions': check_assertions(case, turns),
                'events': wire.events, 'status': 'complete' if len(turns) == len(case['turns']) and
                all(t['status'] == 'thinking_finished' for t in turns) else 'failed'}
    finally:
        await session.close()


def make_schedule(cases, arms, repeats, seed):
    rng = random.Random(seed)
    schedule = []
    for repeat in range(repeats):
        case_order = list(cases)
        rng.shuffle(case_order)
        for case in case_order:
            arm_order = list(arms)
            rng.shuffle(arm_order)
            for arm in arm_order:
                schedule.append({'id': f'{repeat:02d}-{case["id"]}-{arm}',
                                 'repeat': repeat, 'case_id': case['id'], 'arm': arm})
    return schedule


def calibration_architectures(catalog):
    high = dict(catalog['cerebras-balanced'])
    high.update(id='oss-high-calibration', reasoning_effort='high', label='OSS high diagnostic')
    medium = dict(catalog['qwen-low'])
    medium.update(id='qwen-medium-calibration', reasoning_effort='medium', label='Qwen medium diagnostic')
    return {high['id']: high, medium['id']: medium}


def report(out, manifest, rows):
    lines = ['# Architecture comparison: typed production trial path', '',
             f'Generated {datetime.now(timezone.utc).isoformat()}. Planned {len(manifest["schedule"])} samples; completed {len(rows)}.',
             'Timing starts at typed submission. Speech recognition, TTS, and playback are excluded. A model text event is not audible speech.', '',
             '| Arm | Samples | Completed | Median first text ms | Median model complete ms | Tool starts | Reader accepted/applied/late | Input / output / reasoning tokens |',
             '|---|---:|---:|---:|---:|---:|---|---:|']
    for arm in manifest['arms']:
        subset = [r for r in rows if r.get('arm') == arm]
        turns = [t for r in subset for t in r.get('turns', [])]
        def med(key):
            values = [t[key] for t in turns if isinstance(t.get(key), (float,int)) and t.get('status') == 'thinking_finished']
            return f'{statistics.median(values):.0f}' if values else '—'
        reader = [d for t in turns for d in t.get('reader', []) if d.get('phase') == 'finished']
        accepted = sum(d.get('trace', {}).get('status') == 'accepted' for d in reader)
        applied = sum(d.get('outcome') == 'applied_before_speech' for d in reader)
        late = sum(d.get('outcome') == 'speech_already_started' for d in reader)
        usage = [sum(t.get('usage', {}).get(k, 0) for t in turns) for k in ('input_tokens','output_tokens','reasoning_tokens')]
        for t in turns:
            for d in t.get('reader', []):
                trace = d.get('trace') or {}
                if d.get('phase') == 'finished':
                    usage[0] += trace.get('input_tokens', 0) or 0
                    usage[1] += trace.get('output_tokens', 0) or 0
                    usage[2] += trace.get('reasoning_tokens', 0) or 0
        unknown = sum(not t.get('usage_complete') for t in turns) + sum(
            d.get('phase') == 'finished' and not (d.get('trace') or {}).get('usage_complete')
            for t in turns for d in t.get('reader', []))
        usage_label = f'{usage[0]} / {usage[1]} / {usage[2]}' + (f' (≥; {unknown} unknown)' if unknown else '')
        lines.append(f'| {arm} | {len(subset)} | {sum(r.get("status") == "complete" for r in subset)} | {med("first_nonempty_text_ms")} | {med("model_complete_ms")} | {sum(t.get("first_tool_start_ms") is not None for t in turns)} | {accepted}/{applied}/{late} | {usage_label} |')
    lines.extend(['', 'Objective assertions are saved per sample. They do not grade conversational quality; inspect the raw replies and human rubric separately.',
                  'Provider round usage and stop reasons are retained in results.json. Null usage means unavailable, not zero cost.',
                  'First text is a local event receipt. Successful tool completion means the application returned a receipt, not that a physical device acted.', ''])
    (out / 'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def blind_export(out, cases, rows, seed):
    """Create judgement packets without provider, latency, or token metadata."""
    rng = random.Random(seed ^ 0xB11D)
    by_id = {case['id']: case for case in cases}
    groups = {}
    for row in rows:
        sample_id = row['sample_id']
        if sample_id.startswith(('cal-', 'smoke-')):
            continue
        repeat = int(sample_id.split('-', 1)[0])
        groups.setdefault((row['case_id'], repeat), []).append(row)
    packets, key = [], {}
    for (case_id, repeat), group in sorted(groups.items()):
        shuffled = list(group)
        rng.shuffle(shuffled)
        for label, row in zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ', shuffled):
            events = row.get('events', [])
            face = [e['event'] for e in events if e['event'].get('type') == 'face']
            case = by_id[case_id]
            packet_id = f'{case_id}.r{repeat}.{label}'
            key[packet_id] = row['sample_id']
            packets.append({
                'packet_id': packet_id, 'case_id': case_id, 'repeat': repeat,
                'anonymous_label': label, 'family': case.get('family'),
                'case_goal': case.get('case_goal'),
                'review_focus': case.get('review_focus', []),
                'critical_failures': case.get('critical_failures', []),
                'assertions': case.get('assertions', []),
                'status': row.get('status'),
                'dialogue': [{'turn_ref': f'{packet_id}.t{t.get("turn_index", i)}',
                              'user': t.get('user', ''), 'assistant': t.get('text', ''),
                              'status': t.get('status'),
                              'tool_calls': [{'name': call.get('name'), 'success': call.get('success'),
                                              'result': call.get('result')}
                                             for call in t.get('tool_calls', [])],
                              'expression_decisions': [
                                  {'decision': d.get('decision'), 'outcome': d.get('outcome'),
                                   'validation_status': (d.get('trace') or {}).get('status')}
                                  for d in t.get('reader', []) if d.get('phase') == 'finished']}
                             for i, t in enumerate(row.get('turns', []))],
                'face_events': face,
                'evidence_limit': 'Generated text and server receipts only; audio/playback and renderer visibility unverified.',
            })
    write_json(out / 'blind_quality.json', packets)
    write_json(out / 'anonymization_key.json', key)


async def main_async(args):
    cases_path, out = Path(args.cases), Path(args.output_dir)
    suite = json.loads(cases_path.read_text(encoding='utf-8'))
    cases = suite['cases']
    by_id = {case['id']: case for case in cases}
    catalog = {a['id']: a for a in ARCHITECTURES}
    catalog.update(calibration_architectures(catalog))
    arms = [a for a in ARMS if a in catalog]
    schedule = make_schedule(cases, arms, args.repeats, args.seed)
    if args.calibration:
        for case_id in CALIBRATION_CASES:
            if case_id not in by_id: raise ValueError('Missing predeclared calibration case ' + case_id)
            for arm in ('oss-high-calibration', 'qwen-medium-calibration'):
                schedule.append({'id': f'cal-{case_id}-{arm}', 'repeat': 0,
                                 'case_id': case_id, 'arm': arm, 'calibration': True})
    if args.smoke:
        case_id = 'ac29.social_backchannel'
        schedule = [{'id': 'smoke-' + case_id + '-qwen-none', 'repeat': 0,
                     'case_id': case_id, 'arm': 'qwen-none', 'smoke': True}]
    if sum(len(by_id[item['case_id']]['turns']) * (2 if item['arm'] == 'qwen-affect' else 1) for item in schedule) > args.max_provider_turns:
        raise ValueError('Schedule exceeds provider-turn budget')
    out.mkdir(parents=True, exist_ok=True)
    rubric_path = cases_path.with_name('RUBRIC.md')
    manifest = {'suite_sha256': digest(cases_path), 'suite_path': str(cases_path.resolve()),
                'rubric_sha256': digest(rubric_path) if rubric_path.exists() else None,
                'source_sha256': {p: digest(BRAIN / p) for p in SOURCE_FILES},
                'architectures': {a: catalog[a] for a in arms + (['oss-high-calibration', 'qwen-medium-calibration'] if args.calibration else [])},
                'arms': arms + (['oss-high-calibration', 'qwen-medium-calibration'] if args.calibration else []),
                'calibration_arms': ['oss-high-calibration', 'qwen-medium-calibration'] if args.calibration else [],
                'seed': args.seed, 'repeats': args.repeats, 'schedule': schedule,
                'max_provider_turns': args.max_provider_turns,
                'method': 'TrialConversation.handle(text) + CascadeVoice.model_worker; local TTS and WebSocket sinks; no STT or audio calls',
                'started_utc': datetime.now(timezone.utc).isoformat()}
    manifest_path = out / 'manifest.json'
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding='utf-8'))
        for key in ('suite_sha256', 'rubric_sha256', 'source_sha256', 'architectures', 'seed', 'repeats', 'schedule'):
            if old[key] != manifest[key]: raise ValueError('Frozen manifest mismatch: ' + key)
    else: write_json(manifest_path, manifest)
    rows = []
    path = out / 'results.jsonl'
    seen = set()
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            rows.append(row)
            seen.add(row['sample_id'])
    for number, item in enumerate(schedule, 1):
        if item['id'] in seen: continue
        print(f'[{number}/{len(schedule)}] {item["id"]}', flush=True)
        try:
            row = await sample(item['id'], catalog[item['arm']], by_id[item['case_id']], out / 'runs' / item['id'])
        except Exception as exc:
            row = {'sample_id': item['id'], 'case_id': item['case_id'], 'arm': item['arm'],
                   'status': 'harness_error', 'error_type': type(exc).__name__, 'error': str(exc)[:500], 'turns': []}
        with path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
            handle.flush(); os.fsync(handle.fileno())
        rows.append(row)
        write_json(out / 'results.json', rows)
        report(out, manifest, rows)
        blind_export(out, cases, rows, args.seed)
    print(f'Finished {len(rows)}/{len(schedule)} samples at {out}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', default=str(DEFAULT_CASES))
    parser.add_argument('--output-dir', default=str(DEFAULT_OUT))
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--seed', type=int, default=290928)
    parser.add_argument('--max-provider-turns', type=int, default=140)
    parser.add_argument('--no-calibration', action='store_false', dest='calibration')
    parser.add_argument('--smoke', action='store_true', help='One fixed two-turn integration sample in a separate output directory')
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == '__main__': main()
