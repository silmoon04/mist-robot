"""Isolated, serial, cached-audio end-to-end streaming speech comparison.

Planning and validation make no provider calls. Only --serve starts a local
studio and only --run sends audio to it. The existing 9053 service is untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sys
import time
import wave

BRAIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BRAIN))
from duplex import live_studio
from benchmarks.naturalness import architecture_speech_20260928 as cached
from benchmarks.naturalness import speech_cases_20260930 as spec
from benchmarks.naturalness.streaming_voice_20260930 import StreamingComparisonVoice

PORT = 9066
OUTPUT_ROOT = BRAIN / 'results' / 'flux-scribe-jev-20260930'
FIXTURE_ROOT = BRAIN / spec.FIXTURE_ROOT.removeprefix('brain/')
DEFAULT_ENV = Path.home() / 'Downloads/03_Programming_Projects/misc/.env'
MAIN_ARMS = tuple(arm.lower() for arm in spec.ARMS)
SHADOW_ARMS = ('flux-scribe-shadow-jev-off', 'flux-scribe-shadow-jev-on')
SHADOW_CASES = ('unfinished_pause_resume', 'correction')
LEGACY_ARM = 'legacy-qwen-affect'
LEGACY_CASES = ('normal_end', 'unfinished_pause_resume', 'yeah_backchannel', 'explicit_stop')
HASH_SOURCES = (
    'benchmarks/naturalness/streaming_benchmark_20260930.py',
    'benchmarks/naturalness/speech_cases_20260930.py',
    'benchmarks/naturalness/streaming_voice_20260930.py',
    'benchmarks/naturalness/streaming_asr_20260930.py',
    'benchmarks/naturalness/jev_turn_policy_20260930.py',
    'benchmarks/naturalness/jev_async_client_20260930.py',
    'benchmarks/naturalness/jev_comparison_20260929.py',
    'benchmarks/naturalness/architecture_speech_20260928.py',
    'benchmarks/naturalness/cascade_voice.py',
    'benchmarks/naturalness/cerebras_client.py',
    'duplex/live_studio.py', 'duplex/server.py', 'duplex/tts.py',
    'duplex/runtime.py', 'duplex/persona.txt', 'duplex/conversation_policy.py',
    'duplex/listener_feedback.py', 'duplex/listener_backchannels.py',
    'duplex/listener_voice.py', 'duplex/affect_director.py',
    'duplex/affect_controller.py',
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def _selection(names: str | None, allowed: tuple[str, ...]) -> tuple[str, ...]:
    if names is None:
        return allowed
    picked = tuple(part.strip() for part in names.split(',') if part.strip())
    if not picked or len(picked) != len(set(picked)) or set(picked) - set(allowed):
        raise ValueError(f'Invalid selection; allowed: {", ".join(allowed)}')
    return picked


def make_plan(*, cases: tuple[str, ...] | None = None, arms: tuple[str, ...] | None = None,
              repetitions: int = 2, include_legacy: bool = True,
              include_shadow: bool = False, seed: int = 20260930) -> dict:
    selected_cases = cases or tuple(case.id for case in spec.CASES)
    selected_arms = arms or MAIN_ARMS
    if repetitions < 1 or repetitions > 2 or len(set(selected_cases)) != len(selected_cases) \
            or set(selected_cases) - {case.id for case in spec.CASES} \
            or len(set(selected_arms)) != len(selected_arms) \
            or set(selected_arms) - set(MAIN_ARMS):
        raise ValueError('Invalid cases, arms, or repetitions')
    if include_legacy and (set(selected_cases) != {case.id for case in spec.CASES}
                           or set(selected_arms) != set(MAIN_ARMS) or repetitions != 2):
        raise ValueError('Legacy control is part of the complete two-repetition main design only')
    rng = random.Random(seed)
    trials = []
    order = 0
    for repetition in range(1, repetitions + 1):
        blocks = list(selected_cases)
        rng.shuffle(blocks)
        for case_id in blocks:
            block_arms = list(selected_arms)
            if include_legacy and case_id in LEGACY_CASES:
                block_arms.append(LEGACY_ARM)
            rng.shuffle(block_arms)
            for arm in block_arms:
                order += 1
                trials.append({'order': order, 'case_id': case_id, 'arm': arm,
                               'repetition': repetition,
                               'kind': 'legacy_control' if arm == LEGACY_ARM else 'core'})
    if include_shadow:
        if not include_legacy:
            raise ValueError('Shadow control is an addition to the complete main design')
        for repetition in range(1, repetitions + 1):
            for case_id in SHADOW_CASES:
                for arm in SHADOW_ARMS:
                    order += 1
                    trials.append({'order': order, 'case_id': case_id, 'arm': arm,
                                   'repetition': repetition, 'kind': 'passive_shadow_control'})
    if include_legacy and len(trials) != (112 if include_shadow else 104):
        raise AssertionError('Complete design must contain 96 core and 8 legacy trials')
    fixtures = {case.id: {'path': str(FIXTURE_ROOT / case.fixture),
                          'sha256': _hash(FIXTURE_ROOT / case.fixture)}
                for case in spec.CASES if case.id in selected_cases}
    sources = {name: _hash(BRAIN / name) for name in HASH_SOURCES}
    manifest_path = BRAIN / spec.SOURCE_MANIFEST.removeprefix('brain/')
    return {'schema_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
            'working_id': '2026-09-30', 'protocol_date_utc': '2026-09-29',
            'seed': seed, 'repetitions': repetitions, 'cases': selected_cases,
            'arms': selected_arms, 'legacy_control': include_legacy,
            'shadow_control': include_shadow, 'planned_trial_count': len(trials), 'trials': trials,
            'fixture_hashes': fixtures, 'source_hashes': sources,
            'fixture_manifest_sha256': _hash(manifest_path),
            'model': 'qwen-3.8-27b', 'reasoning_effort': 'low',
            'conversation_policy': 'responsive', 'parallel_tool_calls': True,
            'playback_buffer_ms': 120,
            'measurement_scope': 'cached PCM and software queue; no acoustic or browser playback'}


def verify_plan(plan: dict) -> None:
    for name, expected in plan['source_hashes'].items():
        if _hash(BRAIN / name) != expected:
            raise ValueError(f'Source changed since plan: {name}')
    for item in plan['fixture_hashes'].values():
        if _hash(Path(item['path'])) != item['sha256']:
            raise ValueError('Fixture changed since plan')
    manifest_path = BRAIN / spec.SOURCE_MANIFEST.removeprefix('brain/')
    if _hash(manifest_path) != plan['fixture_manifest_sha256']:
        raise ValueError('Fixture manifest changed since plan')


def _safe_error(exc: BaseException) -> dict:
    # Provider exception strings sometimes contain URL query keys or request data.
    return {'type': type(exc).__name__, 'message': 'Trial failed; inspect redacted trace and event records'}


def _non_silent_last_sample_ms(pcm: bytes, threshold: int = 256) -> float | None:
    for offset in range(len(pcm) - 2, -1, -2):
        if abs(int.from_bytes(pcm[offset:offset + 2], 'little', signed=True)) >= threshold:
            return round(offset / 2 / cached.SAMPLE_RATE * 1000, 3)
    return None


def _post_input_events(events: list[dict], input_start_ms: float, seed_turn_id: str | None) -> list[dict]:
    return [event for event in events if event.get('t_ms', -1) >= input_start_ms
            and (seed_turn_id is None or (event.get('benchmark_turn_id') != seed_turn_id
                 and event.get('benchmark_parent_user_turn_id') != seed_turn_id))]


def terminal_state(events: list[dict], *, input_start_ms: float,
                   input_last_sample_ms: float, expected_reply: bool,
                   expected_stop: bool, preserve_backchannel: bool,
                   playback_active: bool, playback_queue_end: float,
                   now: float, seed_turn_id: str | None = None,
                   settled_ms: int = 1200) -> tuple[bool, str]:
    """Require all observed user epochs and TTS sequences to finish and settle."""
    observed = _post_input_events(events, input_start_ms, seed_turn_id)
    if now * 1000 < input_last_sample_ms + settled_ms or playback_active \
            or now < playback_queue_end + settled_ms / 1000:
        return False, 'waiting_for_input_or_software_queue'
    finals = [e for e in observed if e.get('type') == 'transcript_done' and e.get('role') == 'user']
    floor = [e for e in observed if e.get('type') == 'debug_model'
             and e.get('phase') in ('floor_preserved', 'floor_backchannel_kept', 'user_committed')]
    if not finals and not floor:
        return False, 'waiting_for_floor_decision'
    audio = [e for e in observed if e.get('type') == 'audio']
    complete = {(e.get('tts', {}).get('epoch'), e.get('tts', {}).get('sequence'))
                for e in observed if e.get('type') == 'latency' and isinstance(e.get('tts'), dict)}
    resets = [e for e in observed if e.get('type') == 'audio_reset']
    def cancelled(packet):
        return any(reset.get('t_ms', -1) >= packet.get('t_ms', float('inf'))
                   and (reset.get('epoch') is None or packet.get('epoch') is None
                        or reset['epoch'] > packet['epoch']) for reset in resets)
    if any((e.get('epoch'), e.get('seq')) not in complete and not cancelled(e) for e in audio):
        return False, 'waiting_for_tts_sequences'
    latest_user_ms = max([e.get('t_ms', 0) for e in finals] + [input_last_sample_ms])
    if now * 1000 < latest_user_ms + settled_ms:
        return False, 'waiting_for_resumed_input'
    latest_speech_start = max((e.get('t_ms', -1) for e in observed
        if e.get('type') == 'debug_model' and e.get('phase') in ('speech_started', 'turn_resumed')),
        default=-1)
    if latest_speech_start > max((e.get('t_ms', -1) for e in finals), default=-1):
        return False, 'waiting_for_active_user_epoch'
    reply_done = any(e.get('type') == 'transcript_done' and e.get('role') == 'assistant'
                     and e.get('t_ms', -1) >= latest_user_ms for e in observed)
    if expected_stop:
        stopped = any(e.get('type') == 'audio_reset' for e in observed)
        return (stopped, 'stop_and_queue_drained' if stopped else 'waiting_for_stop')
    if preserve_backchannel:
        preserved = any(e.get('backchannel') or e.get('floor_preserved') for e in finals) \
            or any(e.get('phase') == 'floor_preserved' for e in floor)
        return (preserved, 'floor_preserved_and_queue_drained' if preserved else 'waiting_for_floor_preservation')
    if not expected_reply:
        return True, 'non_reply_case_queue_drained'
    return (reply_done and bool(audio), 'assistant_and_tts_complete' if reply_done and audio else 'waiting_for_reply')


def _transcript_rows(events: list[dict]) -> list[dict]:
    return [{'role': e.get('role'), 'text': e.get('text', ''), 'final': True,
             't_ms': e.get('t_ms'), 'turn_id': e.get('benchmark_turn_id')}
            for e in events if e.get('type') == 'transcript_done']


def _input_turn_ids(events: list[dict]) -> list[str]:
    return list(dict.fromkeys(e['benchmark_turn_id'] for e in events
        if e.get('type') == 'transcript_done' and e.get('role') == 'user'
        and e.get('benchmark_turn_id')))


def _client_delivery_metrics(events: list[dict]) -> dict:
    audio = [e for e in events if e.get('type') == 'audio']
    stamps = [e['t_ms'] for e in audio if isinstance(e.get('t_ms'), (int, float))]
    gaps = [later-earlier for earlier, later in zip(stamps, stamps[1:])]
    return {'audio_packets': len(audio),
            'pcm_bytes': sum(e.get('pcm_bytes') or 0 for e in audio),
            'first_audio_received_ms': stamps[0] if stamps else None,
            'last_audio_received_ms': stamps[-1] if stamps else None,
            'max_interpacket_gap_ms': round(max(gaps), 3) if gaps else None,
            'audio_resets': sum(e.get('type') == 'audio_reset' for e in events),
            'receive_basis': 'client perf_counter at WebSocket packet receipt'}


def _runtime_receipts(trace: dict) -> list[dict]:
    return [{'elapsed_ms': row.get('elapsed_ms'), 'source': row.get('source'),
             'event': row.get('event')}
            for row in trace.get('events', []) if isinstance(row.get('event'), dict)
            and row['event'].get('type') in ('tool', 'debug_tool', 'tool_call', 'tool_result',
                                             'runtime_call', 'runtime_result', 'runtime_state')]


def _usage(trace: dict) -> dict:
    records = []
    tts = []
    tts_diagnostics = []
    model_failures = 0
    asr_streams = []
    for row in trace.get('events', []):
        event = row.get('event', {})
        if not isinstance(event, dict):
            continue
        if event.get('type') == 'debug_model' and event.get('phase') == 'thinking_finished':
            timings = event.get('timings', {})
            for request in timings.get('http_requests', []) if isinstance(timings, dict) else []:
                if isinstance(request, dict):
                    records.append({'provider': 'cerebras', 'usage': request.get('usage'),
                                    'usage_known': isinstance(request.get('usage'), dict)})
        if event.get('type') == 'debug_model' and event.get('phase') == 'model_failed':
            model_failures += 1
        if event.get('type') == 'latency' and isinstance(event.get('tts'), dict):
            metric = event['tts']
            tts.append({'epoch': metric.get('epoch'), 'sequence': metric.get('sequence'),
                        'characters': metric.get('characters'),
                        'output_s': metric.get('output_s')})
        if event.get('event') == 'tts_phrase':
            tts_diagnostics.append({'sequence': event.get('sequence'),
                                    'characters': event.get('characters')})
        if event.get('type') == 'jev_policy_outcomes':
            for outcome in event.get('outcomes', []):
                result = outcome.get('result', {})
                response = result.get('response') if isinstance(result, dict) else None
                usage = response.get('usage') if isinstance(response, dict) else None
                records.append({'provider': 'jev', 'usage': usage,
                                'usage_known': isinstance(usage, dict),
                                'endpoint_id': outcome.get('endpoint_id')})
        if event.get('type') == 'asr_accounting':
            asr_streams.append({'streams': event.get('streams'),
                                'timing_summary': event.get('timing_summary')})
    return {'known': bool(records) and all(r['usage_known'] for r in records)
            and model_failures == 0,
            'request_records': records, 'model_failures_without_usage': model_failures,
            'tts_completed_sequences': tts, 'tts_phrase_diagnostics': tts_diagnostics,
            'asr_streams': asr_streams,
            'billing_note': 'PCM seconds include sent silence and tail; a proxy, not an invoice',
            'unknown_components': [name for name, missing in (
                ('provider_requests', not records),
                ('request_usage', any(not r['usage_known'] for r in records)),
                ('failed_model_request_usage', bool(model_failures)),
                ('tts_cancelled_phrase_usage', len(tts_diagnostics) > len(tts))) if missing]}


async def _receive(ws, events, audio_chunks, playback, started, stop):
    while not stop.is_set():
        message = await ws.receive()
        if message.type.name in ('CLOSED', 'CLOSE', 'ERROR'):
            return
        if message.type.name != 'TEXT':
            continue
        try:
            packet = json.loads(message.data)
        except (ValueError, TypeError):
            events.append({'type': 'receive_decode_error', 't_ms': round((time.perf_counter()-started)*1000, 3)})
            continue
        if not isinstance(packet, dict):
            continue
        packet['t_ms'] = round((time.perf_counter()-started)*1000, 3)
        if packet.get('type') == 'error':
            packet.pop('message', None)
            packet['message_redacted'] = True
        if packet.get('type') == 'audio':
            try:
                chunk = base64.b64decode(packet.pop('pcm'), validate=True)
                if len(chunk) % 2:
                    raise ValueError('unaligned audio')
                audio_chunks.setdefault((packet.get('benchmark_turn_id'), packet.get('epoch')),
                                        []).append((packet.get('seq'), packet.get('sample_rate'), chunk))
                packet['pcm_bytes'] = len(chunk)
            except (KeyError, ValueError, TypeError):
                packet['audio_capture_error'] = 'invalid_pcm_payload'
                packet['pcm_bytes'] = 0
        if packet.get('type') == 'audio_reset':
            packet['was_playing'] = playback.active
        events.append(packet)
        await playback.observe(packet, time.perf_counter())


async def _wait_until(predicate, deadline: float, error: str) -> None:
    while time.perf_counter() < deadline:
        if predicate():
            return
        await asyncio.sleep(.025)
    raise TimeoutError(error)


def _save_audio(output: Path, stem: str, chunks: dict) -> list[dict]:
    files = []
    for index, ((turn_id, epoch), packets) in enumerate(chunks.items(), 1):
        rates = {rate for _, rate, _ in packets}
        if len(rates) != 1 or None in rates:
            files.append({'turn_id': turn_id, 'epoch': epoch, 'error': 'inconsistent_sample_rate'})
            continue
        path = output / f'{stem}__audio-{index}.wav'
        with wave.open(str(path), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(next(iter(rates)))
            wav.writeframes(b''.join(block for _, _, block in sorted(packets, key=lambda p: p[0] or 0)))
        files.append({'file': path.name, 'sha256': _hash(path), 'turn_id': turn_id,
                      'epoch': epoch, 'sample_rate': next(iter(rates)),
                      'pcm_bytes': sum(len(block) for _, _, block in packets)})
    return files


async def run_one(http, base: str, trial: dict, output: Path, *, timeout_s: float = 45) -> dict:
    case = next(c for c in spec.CASES if c.id == trial['case_id'])
    pcm, input_info = cached.load_cached_wav(FIXTURE_ROOT / case.fixture)
    started = time.perf_counter()
    events: list[dict] = []
    chunks: dict = {}
    stop = asyncio.Event()
    reader = None
    playback = None
    trace_id = None
    stem = f"{trial['order']:03d}__{case.id}__{trial['arm']}__r{trial['repetition']}"
    row = {**trial, 'status': 'running', 'input': input_info, 'events': events,
           'clock_id': 'client_perf_counter', 'trace_id': None,
           'playback_clock': {'kind': 'software_PCM_duration_simulation',
                              'buffer_ms': 120, 'acoustic_playback_measured': False},
           'usage': {'known': False, 'reason': 'provider_usage_not_yet_observed'}}
    try:
        async with http.ws_connect(base + '/trial/voice', params={'architecture': trial['arm']},
                                   headers={'Origin': base}, heartbeat=20,
                                   max_msg_size=4*1024*1024) as ws:
            playback = cached.SoftwarePlaybackClock(ws, events, 120)
            reader = asyncio.create_task(_receive(ws, events, chunks, playback, started, stop))
            await _wait_until(lambda: any(e.get('type') == 'ready' or e.get('fatal') for e in events),
                              started + 35, 'startup_timeout')
            if any(e.get('fatal') for e in events):
                raise RuntimeError('fatal_startup_event')
            await _wait_until(lambda: any(e.get('type') == 'studio_session' for e in events),
                              started + 35, 'missing_trace_identity')
            trace_id = next(e['trace_id'] for e in events if e.get('type') == 'studio_session')
            row['trace_id'] = trace_id
            row['ready_ms'] = round((time.perf_counter()-started)*1000, 3)
            seed = (case.seed_text, case.seed_delay_after_playback_ms) if case.seed_text else None
            seed_turn_id = None
            if seed:
                await ws.send_json({'type': 'bench_context', 'text': seed[0]})
                await _wait_until(lambda: reader.done() or any(e.get('fatal') for e in events)
                                  or any(e.get('type') == 'audio' for e in events),
                                  time.perf_counter() + timeout_s, 'seed_audio_timeout')
                if reader.done() or any(e.get('fatal') for e in events):
                    raise RuntimeError('seed_stream_failed')
                first_seed = next(e for e in events if e.get('type') == 'audio')
                seed_turn_id = first_seed.get('benchmark_turn_id')
                row['seed_first_returned_audio_ms'] = first_seed['t_ms']
                await asyncio.sleep(seed[1] / 1000)
            row['seed_turn_id'] = seed_turn_id
            row['input_start_ms'] = round((time.perf_counter()-started)*1000, 3)
            row['seed_playing_at_input'] = (playback.active if seed else None)
            row['condition_valid'] = not seed or (playback.active and seed_turn_id is not None)
            row['input_last_nonsilent_sample_ms'] = (None if _non_silent_last_sample_ms(pcm) is None else
                round(row['input_start_ms'] + _non_silent_last_sample_ms(pcm), 3))
            timing = await cached.send_cached_pcm(ws, pcm)
            row['input_timing'] = timing
            row['input_last_sample_ms'] = round(row['input_start_ms'] + timing['input_last_sample_ms'], 3)
            deadline = time.perf_counter() + timeout_s
            outcome = 'bounded_timeout'
            while time.perf_counter() < deadline:
                if reader.done():
                    raise RuntimeError('receive_stream_closed')
                if any(e.get('fatal') for e in events):
                    raise RuntimeError('fatal_runtime_event')
                done, reason = terminal_state(events, input_start_ms=row['input_start_ms'],
                    input_last_sample_ms=row['input_last_sample_ms'],
                    expected_reply=case.expected_reply, expected_stop=case.expected_stop,
                    preserve_backchannel=case.preserve_backchannel,
                    playback_active=playback.active,
                    playback_queue_end=max(0.0, playback.queue_end-started),
                    now=time.perf_counter()-started, seed_turn_id=seed_turn_id)
                if done:
                    outcome = reason
                    break
                await asyncio.sleep(.025)
            row['outcome'] = outcome
            row['status'] = 'complete' if outcome != 'bounded_timeout' else 'timeout'
    except Exception as exc:
        row['status'] = 'failed'
        row['error'] = _safe_error(exc)
    finally:
        stop.set()
        if reader:
            reader.cancel()
            await asyncio.gather(reader, return_exceptions=True)
        if playback:
            await playback.close()
        row['duration_ms'] = round((time.perf_counter()-started)*1000, 3)
        row['client_delivery'] = _client_delivery_metrics(events)
        row['output_audio'] = _save_audio(output, stem, chunks)
        post = ([] if row.get('seed_playing_at_input') is not None and row.get('seed_turn_id') is None
                else _post_input_events(events, row.get('input_start_ms', float('inf')),
                                        row.get('seed_turn_id')))
        row['scored_events'] = post
        row['transcript'] = _transcript_rows(post)
        row['audio_clock'] = {'clip_start_ms': row.get('input_start_ms'),
                              'input_start_ms': row.get('input_start_ms'),
                              'input_last_sample_ms': row.get('input_last_sample_ms'),
                              'input_last_nonsilent_sample_ms': row.get('input_last_nonsilent_sample_ms'),
                              'seed_playback_active_at_input': row.get('seed_playing_at_input'),
                              'capture_complete': row['status'] in ('complete', 'timeout'),
                              'acoustic_playback_measured': False}
        row['input_user_turn_ids'] = _input_turn_ids(post)
        row['active_user_turn_id'] = (row['input_user_turn_ids'][-1]
                                       if row['input_user_turn_ids'] else None)
        row['score'] = spec.score_trial(case, events=post, transcript=row['transcript'],
            audio_clock=row['audio_clock'], active_user_turn_id=row['active_user_turn_id'],
            input_user_turn_ids=row['input_user_turn_ids'],
            input_start_ms=row.get('input_start_ms'), seed_turn_id=row.get('seed_turn_id'))
        _write_json(output / f'{stem}.json', row)
    return row


class IsolatedBenchTrialConversation(cached.CachedBenchTrialConversation):
    def __init__(self, app, ws, architecture, journal):
        super().__init__(app, ws, architecture, journal)
        self._bench_mic_packets = 0
        self._bench_mic_bytes = 0
        self._bench_mic_first = None
        self._bench_mic_last = None
        self._bench_mic_max_gap_ms = 0.0

    async def handle(self, packet):
        if packet.get('type') == 'mic':
            now = time.perf_counter()
            if self._bench_mic_first is None:
                self._bench_mic_first = now
                self.journal.record({'type': 'bench_mic_first_received'}, 'benchmark_adapter')
            if self._bench_mic_last is not None:
                self._bench_mic_max_gap_ms = max(self._bench_mic_max_gap_ms,
                    (now-self._bench_mic_last)*1000)
            self._bench_mic_last = now
            self._bench_mic_packets += 1
            payload = packet.get('pcm')
            if isinstance(payload, str):
                self._bench_mic_bytes += len(payload) * 3 // 4 - payload.count('=')
        await super().handle(packet)

    async def close(self):
        await super().close()
        self.journal.record({'type': 'bench_mic_summary',
            'packets': self._bench_mic_packets, 'decoded_bytes': self._bench_mic_bytes,
            'receive_span_ms': (round((self._bench_mic_last-self._bench_mic_first)*1000, 3)
                if self._bench_mic_first is not None and self._bench_mic_last is not None else None),
            'max_interpacket_gap_ms': round(self._bench_mic_max_gap_ms, 3)}, 'benchmark_adapter')
        voice = getattr(self, 'voice', None)
        policy = getattr(voice, 'jev_policy', None)
        if policy is not None:
            self.journal.record({'type': 'jev_policy_outcomes',
                'drained': getattr(voice, 'jev_drained', None),
                'outcomes': [{'epoch': key[0], 'endpoint_id': key[1], 'result': result}
                             for key, result in policy.outcomes.items()]}, 'benchmark_adapter')
        adapter = getattr(voice, 'asr_adapter', None)
        if adapter is not None:
            timing_summary = getattr(adapter, 'timing_summary', None)
            if callable(timing_summary):
                timing_summary = timing_summary()
            streams = {'primary': {'pcm_bytes': getattr(adapter, 'sent_pcm_bytes', None),
                        'pcm_seconds': getattr(adapter, 'sent_pcm_seconds', None),
                        'connected_duration_s': getattr(adapter, 'connected_duration_s', None)}}
            if hasattr(adapter, 'shadow_sent_pcm_bytes'):
                streams['shadow'] = {
                    'pcm_bytes': getattr(adapter, 'shadow_sent_pcm_bytes', None),
                    'pcm_seconds': getattr(adapter, 'shadow_sent_pcm_seconds', None),
                    'connected_duration_s': getattr(adapter, 'shadow_connected_duration_s', None),
                    'dropped_pcm_bytes': getattr(adapter, 'shadow_dropped_pcm_bytes', None)}
            self.journal.record({'type': 'asr_accounting', 'streams': streams,
                'timing_summary': timing_summary,
                'note': 'Sent PCM and connected duration are billing proxies, not invoices'},
                'benchmark_adapter')
        if getattr(voice, 'jev_drained', True) is False:
            self.app['trial_health']['quarantined'] = True
            self.journal.record({'type': 'jev_retirement', 'drained': False}, 'benchmark_adapter')


def configure_isolated_studio() -> None:
    live_studio.TrialConversation = IsolatedBenchTrialConversation
    source = next(a for a in live_studio.ARCHITECTURES if a['id'] == 'qwen-affect')
    for arm in MAIN_ARMS:
        if any(a['id'] == arm for a in live_studio.ARCHITECTURES):
            continue
        provider, _, jev = arm.partition('-jev-')
        item = dict(source, id=arm, label=f'{provider.title()} / JEV {jev}',
                    model='qwen-3.8-27b', reasoning_effort='low', floor='selective',
                    endpoint_ms=500, incomplete_hold_ms=900,
                    conversation_policy='responsive', parallel_tool_calls=True,
                    playback_buffer_ms=120, asr_provider=provider,
                    jev_enabled=jev == 'on', affect_model=None, affect_reasoning=None,
                    description='Isolated streaming ASR and turn policy comparison.')
        live_studio.ARCHITECTURES.append(item)
    for arm in SHADOW_ARMS:
        if any(a['id'] == arm for a in live_studio.ARCHITECTURES):
            continue
        source_arm = next(a for a in live_studio.ARCHITECTURES if a['id'] == arm.replace('-scribe-shadow', ''))
        live_studio.ARCHITECTURES.append(dict(source_arm, id=arm,
            label=f"Flux + passive Scribe / JEV {arm.rsplit('-', 1)[-1]}",
            shadow_provider='scribe',
            description='Flux controls the floor; Scribe is a passive transcript shadow.'))
    if not any(a['id'] == LEGACY_ARM for a in live_studio.ARCHITECTURES):
        live_studio.ARCHITECTURES.append(dict(source, id=LEGACY_ARM,
                                             label='Legacy Qwen affect control'))


def create_benchmark_studio(port: int, run_dir: Path, *, env_path: Path = DEFAULT_ENV):
    if port in (9053, 9054) or not 1 <= port <= 65535:
        raise ValueError('Choose an isolated local port other than 9053 or 9054')
    configure_isolated_studio()
    app = live_studio.create_studio(argparse.Namespace(port=port, run_dir=str(run_dir)))
    from benchmarks.naturalness.jev_comparison_20260929 import load_key
    from benchmarks.naturalness.jev_async_client_20260930 import AsyncJevClient
    from benchmarks.naturalness.jev_turn_policy_20260930 import JEVTurnPolicy
    jev_client = None

    def factory(runtime, voice_dir, emit, feed, dc_event, **kwargs):
        nonlocal jev_client
        architecture = dc_event.__self__.architecture
        if architecture['id'] == LEGACY_ARM:
            from benchmarks.naturalness.cascade_voice import CascadeVoice
            return CascadeVoice(runtime, voice_dir, emit, feed, dc_event, **kwargs)
        if architecture['jev_enabled']:
            if jev_client is None:
                jev_client = AsyncJevClient(load_key(env_path), timeout_s=2)
            kwargs['jev_policy'] = JEVTurnPolicy(jev_client, deadline_ms=500,
                                                 total_deadline_ms=2000)
        if architecture.get('shadow_provider'):
            from benchmarks.naturalness.streaming_asr_20260930 import FluxScribeShadowASR
            environment = dc_event.__self__.app['env']
            kwargs['asr_adapter'] = FluxScribeShadowASR(
                environment['DEEPGRAM_API_KEY'], environment['ELEVENLABS_API_KEY'],
                sample_rate=16000)
        return StreamingComparisonVoice(runtime, voice_dir, emit, feed, dc_event,
            asr_provider=architecture['asr_provider'],
            jev_enabled=architecture['jev_enabled'], **kwargs)

    app['trial_voice_factory'] = factory
    app['trial_source_hashes'].update({name: _hash(BRAIN / name) for name in HASH_SOURCES})

    async def close_jev(app):
        yield
        if jev_client is not None:
            await jev_client.aclose()
    app.cleanup_ctx.append(close_jev)
    return app


async def _bootstrap_and_check(http, base: str, plan: dict) -> dict:
    async with http.post(base + '/trial/bootstrap', headers={'Origin': base}) as response:
        response.raise_for_status()
    async with http.get(base + '/trial/catalog') as response:
        response.raise_for_status()
        catalog = {row['id']: row for row in (await response.json())['architectures']}
    needed = set(plan['arms']) | ({LEGACY_ARM} if plan['legacy_control'] else set()) \
        | (set(SHADOW_ARMS) if plan['shadow_control'] else set())
    missing = needed - set(catalog)
    unavailable = [arm for arm in needed if arm in catalog and not catalog[arm]['available']]
    if missing or unavailable:
        raise RuntimeError(f'Catalog preflight failed: missing={sorted(missing)}, unavailable={sorted(unavailable)}')
    for arm in needed:
        config = catalog[arm]
        for source_name, digest in plan['source_hashes'].items():
            if config.get('source_hashes', {}).get(source_name) != digest:
                raise ValueError(f'Server source differs from plan: {source_name}')
        if arm != LEGACY_ARM and (config.get('model') != 'qwen-3.8-27b'
                or config.get('reasoning_effort') != 'low'
                or config.get('conversation_policy') != 'responsive'
                or config.get('parallel_tool_calls') is not True
                or config.get('playback_buffer_ms') != 120
                or config.get('affect_model')):
            raise ValueError(f'Unmatched architecture settings: {arm}')
    return {arm: catalog[arm] for arm in sorted(needed)}


async def run_batch(base: str, output: Path, plan: dict) -> dict:
    import aiohttp
    if output.exists():
        raise FileExistsError('Choose a fresh output directory; previous data is immutable')
    verify_plan(plan)
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / 'plan.frozen.json', plan)  # Before bootstrap or provider calls.
    rows = []
    halted_reason = None
    timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_connect=10)
    async with aiohttp.ClientSession(timeout=timeout, cookie_jar=aiohttp.CookieJar(unsafe=True)) as http:
        catalog = await _bootstrap_and_check(http, base, plan)
        _write_json(output / 'catalog.json', catalog)
        for trial in plan['trials']:
            try:
                verify_plan(plan)
            except (ValueError, OSError):
                halted_reason = 'source_or_fixture_changed'
                break
            try:
                row = await run_one(http, base, trial, output)
            finally:
                try:
                    async with http.post(base + '/trial/disconnect', headers={'Origin': base}) as response:
                        if response.status != 200:
                            halted_reason = f'disconnect_http_{response.status}'
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    halted_reason = 'disconnect_unavailable'
            if row.get('trace_id'):
                try:
                    async with http.get(base + '/trial/export', params={'session': row['trace_id']}) as response:
                        response.raise_for_status()
                        trace = await response.json()
                    stem = f"{trial['order']:03d}__{trial['case_id']}__{trial['arm']}__r{trial['repetition']}"
                    _write_json(output / f'{stem}__trace.json', trace)
                    row['trace_file'] = f'{stem}__trace.json'
                    row['trace_sha256'] = _hash(output / row['trace_file'])
                    row['runtime_receipts'] = _runtime_receipts(trace)
                    row['usage'] = _usage(trace)
                    row['score'] = spec.score_trial(next(c for c in spec.CASES if c.id == trial['case_id']),
                        events=row['scored_events'], transcript=row['transcript'],
                        audio_clock=row['audio_clock'], task_receipts=row['runtime_receipts'],
                        active_user_turn_id=row['active_user_turn_id'],
                        input_user_turn_ids=row['input_user_turn_ids'],
                        input_start_ms=row.get('input_start_ms'),
                        seed_turn_id=row.get('seed_turn_id'))
                    _write_json(output / f'{stem}.json', row)
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                    row['trace_export_error'] = _safe_error(exc)
            rows.append(row)
            _write_json(output / 'attempts.json', rows)
            if halted_reason:
                break
    report = {'planned_trial_count': len(plan['trials']), 'completed_trial_count': len(rows),
              'halted_reason': halted_reason,
              'status_counts': {status: sum(r['status'] == status for r in rows)
                                for status in ('complete', 'timeout', 'failed')},
              'by_arm': {arm: {'trials': sum(r['arm'] == arm for r in rows),
                               'complete': sum(r['arm'] == arm and r['status'] == 'complete' for r in rows),
                               'timeouts': sum(r['arm'] == arm and r['status'] == 'timeout' for r in rows),
                               'failed': sum(r['arm'] == arm and r['status'] == 'failed' for r in rows)}
                         for arm in sorted({r['arm'] for r in rows})},
              'condition_invalid_count': sum(r.get('condition_valid') is False for r in rows),
              'score_aggregate': spec.aggregate([r['score'] for r in rows]),
              'unknown_usage_count': sum(not r['usage']['known'] for r in rows),
              'no_acoustic_playback_measurement': True}
    _write_json(output / 'report.json', report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', action='store_true')
    mode.add_argument('--serve', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--port', type=int, default=PORT)
    parser.add_argument('--base-url', default=f'http://127.0.0.1:{PORT}')
    parser.add_argument('--run-dir', type=Path, default=OUTPUT_ROOT / 'server-state')
    parser.add_argument('--output', type=Path, default=OUTPUT_ROOT / 'main')
    parser.add_argument('--env', type=Path, default=DEFAULT_ENV)
    parser.add_argument('--cases', help='Comma-separated subset for an isolated smoke run')
    parser.add_argument('--arms', help='Comma-separated subset for an isolated smoke run')
    parser.add_argument('--repetitions', type=int, default=2)
    parser.add_argument('--include-shadow', action='store_true')
    args = parser.parse_args()
    if args.serve:
        from aiohttp import web
        app = create_benchmark_studio(args.port, args.run_dir, env_path=args.env)
        web.run_app(app, host='127.0.0.1', port=args.port)
        return
    cases = _selection(args.cases, tuple(case.id for case in spec.CASES))
    arms = _selection(args.arms, MAIN_ARMS)
    full = args.cases is None and args.arms is None and args.repetitions == 2
    plan = make_plan(cases=cases, arms=arms, repetitions=args.repetitions,
                     include_legacy=full, include_shadow=args.include_shadow)
    if args.plan:
        print(json.dumps(plan, indent=2))
    else:
        if not full and args.output.resolve() == (OUTPUT_ROOT / 'main').resolve():
            parser.error('Smoke selections require --output pointing to a dedicated fresh directory')
        print(json.dumps(asyncio.run(run_batch(args.base_url, args.output, plan)), indent=2))


if __name__ == '__main__':
    main()
