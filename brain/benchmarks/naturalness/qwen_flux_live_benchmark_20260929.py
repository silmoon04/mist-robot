"""Frozen, serial 32-attempt Qwen-affect versus Qwen-Flux live pilot.

The service uses the production live_studio architecture catalog and voice
factory. Only a benchmark conversation subclass adds context seeding and turn
lineage. Planning and --serve do not send cached audio to providers.
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

BRAIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BRAIN))
from duplex import live_studio
from benchmarks.naturalness import architecture_speech_20260928 as cached
from benchmarks.naturalness import speech_cases_20260930 as spec
from benchmarks.naturalness import streaming_benchmark_20260930 as prior

PORT = 9068
ARMS = ('qwen-affect', 'qwen-flux')
ROOT = BRAIN / 'results/qwen-flux-live-20260929'
FIXTURES = BRAIN / spec.FIXTURE_ROOT.removeprefix('brain/')
SOURCE_FILES = tuple(dict.fromkeys((
    'benchmarks/naturalness/qwen_flux_live_benchmark_20260929.py',
    'benchmarks/naturalness/architecture_speech_20260928.py',
    'benchmarks/naturalness/streaming_benchmark_20260930.py',
    'benchmarks/naturalness/speech_cases_20260930.py',
    'benchmarks/naturalness/streaming_voice_20260930.py',
    'benchmarks/naturalness/streaming_asr_20260930.py',
    'benchmarks/naturalness/cascade_voice.py',
    'benchmarks/naturalness/cerebras_client.py',
    'duplex/live_studio.py', 'duplex/server.py', 'duplex/tts.py',
    'duplex/runtime.py', 'duplex/persona.txt', 'duplex/conversation_policy.py',
    'duplex/listener_feedback.py', 'duplex/listener_backchannels.py',
    'duplex/listener_voice.py', 'duplex/affect_director.py',
    'duplex/affect_controller.py', 'duplex/expression_requests.py',
    'duplex/expression_policy.py',
)))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, obj: object) -> None:
    prior._write_json(path, obj)


def seed_for(case: spec.Case) -> str | None:
    if not case.seed_text:
        return None
    # Context speech must still be playing when the cached interruption begins.
    # Append identical, case-neutral material in both arms; never alter the WAV.
    return (case.seed_text + ' ' +
            'Next, check the clearance around the screw and the fit of the bracket. ' +
            'Then inspect the cable path carefully before making any adjustment. ' +
            'Finally, go back through those checks in order so we can discuss each one.')


def plan() -> dict:
    check = spec.preflight_fixtures(FIXTURES, BRAIN / spec.SOURCE_MANIFEST.removeprefix('brain/'))
    if not check['ready_to_freeze']:
        raise ValueError(f'Cached fixture preflight failed: {check["flags"]}')
    fixture_info = {case.id: cached.load_cached_wav(FIXTURES / case.fixture)[1]
                    for case in spec.CASES}
    rng = random.Random(20260929)
    trials = []
    for repetition in (1, 2):
        case_ids = [case.id for case in spec.CASES]
        rng.shuffle(case_ids)
        for case_id in case_ids:
            block_arms = list(ARMS)
            rng.shuffle(block_arms)
            for arm in block_arms:
                trials.append(dict(order=len(trials) + 1, repetition=repetition,
                                   case_id=case_id, arm=arm))
    fixture_manifest = BRAIN / spec.SOURCE_MANIFEST.removeprefix('brain/')
    return dict(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
                seed=20260929, planned_trial_count=32, trials=trials,
                arms=list(ARMS), repetitions=2,
                fixture_manifest_sha256=digest(fixture_manifest),
                fixture_suite_sha256=check['source_manifest_sha256'],
                fixtures={case.id: dict(path=str(FIXTURES / case.fixture),
                    sha256=digest(FIXTURES / case.fixture),
                    wav=fixture_info[case.id],
                    expected_transcript=list(case.expected_transcript),
                    timing=case.timing, wait_windows_ms=case.wait_windows_ms,
                    seed_text=seed_for(case),
                    seed_delay_after_playback_ms=case.seed_delay_after_playback_ms)
                    for case in spec.CASES},
                source_hashes={name: digest(BRAIN / name) for name in SOURCE_FILES},
                measurement=dict(input='cached PCM16 mono 16 kHz, 20 ms pacing',
                    playback='120 ms software PCM queue simulation, not acoustic delivery',
                    provider_calls='serial, no failed-trial retries'))


def verify_frozen(p: dict) -> None:
    for name, expected in p['source_hashes'].items():
        if digest(BRAIN / name) != expected:
            raise ValueError(f'Source changed after freeze: {name}')
    for row in p['fixtures'].values():
        if digest(Path(row['path'])) != row['sha256']:
            raise ValueError('Fixture changed after freeze')
    if digest(BRAIN / spec.SOURCE_MANIFEST.removeprefix('brain/')) != p['fixture_manifest_sha256']:
        raise ValueError('Fixture manifest changed after freeze')


def install_tts_drain_receipts(mask, emit):
    """Observe actual completed TTS drain without modifying production TTS."""
    original_drain = mask.drain
    reported = set()

    async def observed_drain():
        before = dict(mask.pending)
        epoch = mask.epoch
        await original_drain()
        if mask.epoch != epoch:
            return
        for context, entry in before.items():
            key = (entry['epoch'], entry['seq'])
            if context not in mask.pending and entry.get('done') and key not in reported:
                reported.add(key)
                await emit({'type': 'bench_tts_sequence_drained',
                            'epoch': entry['epoch'], 'seq': entry['seq'],
                            'pending_count': len(mask.pending)})

    mask.drain = observed_drain


class BenchConversation(cached.CachedBenchTrialConversation):
    """Test-only context and lineage instrumentation; production start path."""

    async def start(self):
        await super().start()
        # The ordinary TTS latency event precedes its final buffered PCM.
        install_tts_drain_receipts(self.mask, self.emit)

    async def emit(self, event):
        if isinstance(event, dict) and event.get('type') == 'bench_tts_sequence_drained':
            event = dict(event, benchmark_turn_id=getattr(self, '_bench_output_turn_id', None),
                         benchmark_parent_user_turn_id=getattr(self, '_bench_parent_user_turn_id', None))
        await super().emit(event)


def create_service(port: int, run_dir: Path):
    if port != PORT:
        raise ValueError(f'This pilot uses isolated port {PORT}')
    live_studio.TrialConversation = BenchConversation
    app = live_studio.create_studio(argparse.Namespace(port=port, run_dir=str(run_dir)))
    app['trial_source_hashes'].update({name: digest(BRAIN / name) for name in SOURCE_FILES})
    return app


class Playback(cached.SoftwarePlaybackClock):
    def __init__(self, ws, events, started):
        super().__init__(ws, events, 120)
        self.started = started
        self.drains = []

    async def observe(self, packet, received_at):
        was_active = self.active
        await super().observe(packet, received_at)
        if self.active != was_active and self.events and self.events[-1].get('type') == 'software_playback_state':
            self.events[-1]['t_ms'] = round((time.perf_counter()-self.started)*1000, 3)
        if packet.get('type') == 'audio_reset' and was_active:
            self.drains.append(dict(reason='reset', t_ms=round((time.perf_counter()-self.started)*1000, 3)))

    async def _finish_after_queue(self):
        await super()._finish_after_queue()
        if self.events and self.events[-1].get('type') == 'software_playback_state' and \
           self.events[-1].get('reason') == 'PCM_duration_queue_drained':
            self.drains.append(dict(reason='PCM_duration_queue_drained',
                t_ms=round((time.perf_counter()-self.started)*1000, 3)))


async def receive(ws, events, chunks, playback, started):
    while True:
        msg = await ws.receive()
        if msg.type.name in ('CLOSED', 'CLOSE', 'ERROR'):
            return
        if msg.type.name != 'TEXT':
            continue
        try:
            event = json.loads(msg.data)
        except (ValueError, TypeError):
            events.append(dict(type='receive_decode_error', t_ms=round((time.perf_counter()-started)*1000, 3)))
            continue
        if not isinstance(event, dict):
            continue
        event['t_ms'] = round((time.perf_counter()-started)*1000, 3)
        if event.get('type') == 'error':
            event.pop('message', None)
            event['message_redacted'] = True
        if event.get('type') == 'audio':
            try:
                pcm = base64.b64decode(event.pop('pcm'), validate=True)
                if len(pcm) % 2:
                    raise ValueError('Unaligned PCM')
                chunks.setdefault((event.get('benchmark_turn_id'), event.get('epoch')), []).append(
                    (event.get('seq'), event.get('sample_rate'), pcm))
                event['pcm_bytes'] = len(pcm)
            except (KeyError, ValueError, TypeError):
                event['audio_capture_error'] = 'invalid_pcm_payload'
                event['pcm_bytes'] = 0
        if event.get('type') == 'audio_reset':
            event['was_playing'] = playback.active
        events.append(event)
        await playback.observe(event, time.perf_counter())


def evidence(events: list[dict], input_start_ms: float | None, seed_turn_id: str | None,
             last_nonsilent_ms: float | None, drains: list[dict]) -> dict:
    post = prior._post_input_events(events, input_start_ms if input_start_ms is not None else float('inf'), seed_turn_id)
    ids = prior._input_turn_ids(post)
    lineage = [e for e in post if e.get('benchmark_parent_user_turn_id') in ids] if ids else []
    def first(rows, kind, role=None):
        return next((e['t_ms'] for e in rows if e.get('type') == kind and
                     (role is None or e.get('role') == role) and
                     (kind != 'transcript_delta' or str(e.get('text', '')).strip())), None)
    asr = first(post, 'transcript_done', 'user')
    delta = first(lineage, 'transcript_delta', 'assistant')
    pcm = first(lineage, 'audio')
    final_text = first(lineage, 'transcript_done', 'assistant')
    final_pcm = max((e['t_ms'] for e in lineage if e.get('type') == 'audio'), default=None)
    tts_drains = [e for e in lineage if e.get('type') == 'bench_tts_sequence_drained']
    queue_drain = next((d['t_ms'] for d in drains if d['reason'] == 'PCM_duration_queue_drained'
                        and final_pcm is not None and d['t_ms'] >= final_pcm), None)
    playback_start = next((e['t_ms'] for e in events if e.get('type') == 'software_playback_state'
                           and e.get('playing') is True and pcm is not None
                           and e.get('t_ms', -1) >= pcm), None)
    return dict(input_user_turn_ids=ids, active_user_turn_id=ids[-1] if ids else None,
        asr_commit_ms=asr, first_correlated_text_ms=delta, first_correlated_pcm_ms=pcm,
        final_correlated_text_ms=final_text, final_correlated_pcm_ms=final_pcm,
        tts_drain_receipts=[dict(epoch=e.get('epoch'), seq=e.get('seq'),
                                 pending_count=e.get('pending_count'), t_ms=e['t_ms'])
                            for e in tts_drains],
        simulated_playback_start_ms=playback_start,
        software_queue_drain_ms=queue_drain,
        asr_from_last_nonsilent_ms=prior._delta(asr, last_nonsilent_ms) if hasattr(prior, '_delta') else cached._delta(asr, last_nonsilent_ms),
        text_from_last_nonsilent_ms=cached._delta(delta, last_nonsilent_ms),
        pcm_from_last_nonsilent_ms=cached._delta(pcm, last_nonsilent_ms),
        simulated_playback_start_from_last_nonsilent_ms=cached._delta(playback_start, last_nonsilent_ms),
        simulated_playback_completion_from_last_nonsilent_ms=cached._delta(queue_drain, last_nonsilent_ms),
        acoustic_delivery_available=False)


def terminal_with_tts_drain(events: list[dict], **kwargs) -> tuple[bool, str]:
    done, reason = prior.terminal_state(events, **kwargs)
    if not done or kwargs['expected_stop'] or kwargs['preserve_backchannel'] or not kwargs['expected_reply']:
        return done, reason
    post = prior._post_input_events(events, kwargs['input_start_ms'], kwargs.get('seed_turn_id'))
    completed = {(e.get('epoch'), e.get('seq')) for e in post if e.get('type') == 'audio'}
    receipts = [e for e in post if e.get('type') == 'bench_tts_sequence_drained']
    drained = {(e.get('epoch'), e.get('seq')) for e in receipts}
    if not completed or not completed <= drained or not receipts or receipts[-1].get('pending_count') != 0:
        return False, 'waiting_for_actual_tts_drain'
    return True, 'assistant_tts_and_software_queue_drained'


async def run_one(http, base: str, trial: dict, out: Path, timeout_s: float = 55) -> dict:
    case = next(c for c in spec.CASES if c.id == trial['case_id'])
    pcm, input_info = cached.load_cached_wav(FIXTURES / case.fixture)
    started = time.perf_counter()
    events, chunks, playback, reader = [], {}, None, None
    stem = f"{trial['order']:03d}__{case.id}__{trial['arm']}__r{trial['repetition']}"
    row = dict(trial, status='running', started_utc=datetime.now(timezone.utc).isoformat(),
               input=input_info, clock_id='client_perf_counter', events=events,
               playback_basis='120 ms software PCM queue, not acoustic playback')
    try:
        async with http.ws_connect(base + '/trial/voice', params={'architecture': trial['arm']},
                                   headers={'Origin': base}, heartbeat=20,
                                   max_msg_size=4*1024*1024) as ws:
            playback = Playback(ws, events, started)
            reader = asyncio.create_task(receive(ws, events, chunks, playback, started))
            await prior._wait_until(lambda: reader.done() or any(e.get('type') == 'ready' or e.get('fatal') for e in events),
                                    started + 35, 'startup_timeout')
            if reader.done() or any(e.get('fatal') for e in events):
                raise RuntimeError('startup_failed')
            await prior._wait_until(lambda: any(e.get('type') == 'studio_session' for e in events),
                                    started + 35, 'missing_trace_identity')
            row['trace_id'] = next(e['trace_id'] for e in events if e.get('type') == 'studio_session')
            row['ready_ms'] = round((time.perf_counter()-started)*1000, 3)
            seed_text = seed_for(case)
            if seed_text:
                await ws.send_json({'type': 'bench_context', 'text': seed_text})
                await prior._wait_until(lambda: reader.done() or any(e.get('fatal') for e in events) or
                                        any(e.get('type') == 'audio' and playback.active for e in events),
                                        time.perf_counter() + timeout_s, 'seed_audio_timeout')
                if reader.done() or any(e.get('fatal') for e in events):
                    raise RuntimeError('seed_stream_failed')
                seed_audio = next(e for e in events if e.get('type') == 'audio')
                row['seed_turn_id'] = seed_audio.get('benchmark_turn_id')
                row['seed_first_pcm_ms'] = seed_audio['t_ms']
                await asyncio.sleep(case.seed_delay_after_playback_ms / 1000)
            row['input_start_ms'] = round((time.perf_counter()-started)*1000, 3)
            row['seed_playing_at_input'] = playback.active if seed_text else None
            row['condition_valid'] = not seed_text or (playback.active and bool(row.get('seed_turn_id')))
            nonsilent = prior._non_silent_last_sample_ms(pcm)
            row['last_nonsilent_sample_offset'] = (round(nonsilent * cached.SAMPLE_RATE / 1000)
                                                  if nonsilent is not None else None)
            row['input_last_nonsilent_sample_ms'] = (round(row['input_start_ms'] + nonsilent, 3)
                                                      if nonsilent is not None else None)
            row['input_timing'] = await cached.send_cached_pcm(ws, pcm)
            row['input_last_sample_ms'] = round(row['input_start_ms'] + row['input_timing']['input_last_sample_ms'], 3)
            deadline = time.perf_counter() + timeout_s
            row['outcome'] = 'bounded_timeout'
            while time.perf_counter() < deadline:
                if reader.done() or any(e.get('fatal') for e in events):
                    raise RuntimeError('receive_or_provider_failed')
                done, reason = terminal_with_tts_drain(events, input_start_ms=row['input_start_ms'],
                    input_last_sample_ms=row['input_last_sample_ms'], expected_reply=case.expected_reply,
                    expected_stop=case.expected_stop, preserve_backchannel=case.preserve_backchannel,
                    playback_active=playback.active,
                    playback_queue_end=max(0, playback.queue_end-started),
                    now=time.perf_counter()-started, seed_turn_id=row.get('seed_turn_id'))
                if done:
                    row['outcome'] = reason
                    break
                await asyncio.sleep(.025)
            row['status'] = 'timeout' if row['outcome'] == 'bounded_timeout' else 'complete'
    except Exception as exc:
        row['status'] = 'failed'
        row['error'] = prior._safe_error(exc)
    finally:
        if reader:
            reader.cancel()
            await asyncio.gather(reader, return_exceptions=True)
        if playback:
            await playback.close()
        row['ended_utc'] = datetime.now(timezone.utc).isoformat()
        row['duration_ms'] = round((time.perf_counter()-started)*1000, 3)
        row['playback_events'] = playback.drains if playback else []
        row['output_audio'] = prior._save_audio(out, stem, chunks)
        post = prior._post_input_events(events, row.get('input_start_ms', float('inf')),
                                        row.get('seed_turn_id'))
        row['scored_events'] = post
        row['transcript'] = prior._transcript_rows(post)
        row['stage'] = evidence(events, row.get('input_start_ms'), row.get('seed_turn_id'),
                                row.get('input_last_nonsilent_sample_ms'), row['playback_events'])
        row['score'] = spec.score_trial(case, events=post, transcript=row['transcript'],
            audio_clock=dict(clip_start_ms=row.get('input_start_ms'),
                             input_last_nonsilent_sample_ms=row.get('input_last_nonsilent_sample_ms'),
                             seed_playback_active_at_input=row.get('seed_playing_at_input'),
                             capture_complete=row['status'] in ('complete', 'timeout')),
            active_user_turn_id=row['stage']['active_user_turn_id'],
            input_user_turn_ids=row['stage']['input_user_turn_ids'],
            input_start_ms=row.get('input_start_ms'), seed_turn_id=row.get('seed_turn_id'))
        save(out / f'{stem}.json', row)
    return row


async def run(base: str, out: Path, frozen: dict) -> dict:
    import aiohttp
    if out.exists():
        raise FileExistsError(f'Output exists: {out}')
    verify_frozen(frozen)
    out.mkdir(parents=True)
    save(out / 'manifest.frozen.json', frozen)
    rows = []
    halted = None
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None, connect=10),
                                     cookie_jar=aiohttp.CookieJar(unsafe=True)) as http:
        async with http.post(base + '/trial/bootstrap', headers={'Origin': base}) as response:
            response.raise_for_status()
        async with http.get(base + '/trial/catalog') as response:
            response.raise_for_status()
            catalog = {a['id']: a for a in (await response.json())['architectures']}
        for arm in ARMS:
            a = catalog[arm]
            if not a['available'] or a['model'] != 'qwen-3.8-27b' or a['reasoning_effort'] != 'low' or \
               a['conversation_policy'] != 'responsive' or a['playback_buffer_ms'] != 120 or \
               a['affect_model'] != 'qwen-3.8-27b' or a['affect_reasoning'] != 'none' or \
               a['voice_id'] != catalog[ARMS[0]]['voice_id'] or a.get('jev_enabled', False):
                raise ValueError(f'Architecture preflight failed: {arm}')
            for name, expected in frozen['source_hashes'].items():
                if a['source_hashes'].get(name) != expected:
                    raise ValueError(f'Server source differs: {name}')
        if catalog['qwen-affect'].get('asr_provider') or catalog['qwen-flux'].get('asr_provider') != 'flux' or \
           catalog['qwen-flux'].get('turn_policy') != 'flux_end_of_turn':
            raise ValueError('Listener path preflight failed')
        save(out / 'catalog.json', {a: catalog[a] for a in ARMS})
        for trial in frozen['trials']:
            try:
                verify_frozen(frozen)
            except (ValueError, OSError):
                halted = 'source_or_fixture_changed_after_freeze'
                break
            row = await run_one(http, base, trial, out)
            try:
                async with http.post(base + '/trial/disconnect', headers={'Origin': base}) as response:
                    if response.status != 200:
                        halted = f'disconnect_http_{response.status}'
            except (aiohttp.ClientError, asyncio.TimeoutError):
                halted = 'disconnect_unavailable'
            if row.get('trace_id'):
                try:
                    async with http.get(base + '/trial/export', params={'session': row['trace_id']}) as response:
                        response.raise_for_status()
                        trace = await response.json()
                    stem = f"{trial['order']:03d}__{trial['case_id']}__{trial['arm']}__r{trial['repetition']}"
                    save(out / f'{stem}__trace.json', trace)
                    row['trace_file'] = f'{stem}__trace.json'
                    row['trace_sha256'] = digest(out / row['trace_file'])
                    row['runtime_receipts'] = prior._runtime_receipts(trace)
                    row['usage'] = prior._usage(trace)
                    save(out / f'{stem}.json', row)
                except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                    row['trace_export_error'] = prior._safe_error(exc)
            rows.append(row)
            save(out / 'attempts.json', rows)
            if halted:
                break
    report = dict(planned=32, attempted=len(rows), halted_reason=halted,
        ended_utc=datetime.now(timezone.utc).isoformat(),
        by_arm={arm: dict(attempted=sum(r['arm'] == arm for r in rows),
            complete=sum(r['arm'] == arm and r['status'] == 'complete' for r in rows),
            timeout=sum(r['arm'] == arm and r['status'] == 'timeout' for r in rows),
            failed=sum(r['arm'] == arm and r['status'] == 'failed' for r in rows)) for arm in ARMS},
        invalid_seed_conditions=sum(r.get('condition_valid') is False for r in rows),
        measurement_limit='Software PCM queue simulation; no acoustic or human naturalness claim')
    save(out / 'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', action='store_true')
    mode.add_argument('--serve', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--port', type=int, default=PORT)
    parser.add_argument('--base-url', default=f'http://127.0.0.1:{PORT}')
    parser.add_argument('--run-dir', type=Path, default=ROOT / 'server-state')
    parser.add_argument('--output', type=Path, default=ROOT / 'run-01')
    parser.add_argument('--manifest', type=Path, default=ROOT / 'manifest.frozen.json')
    args = parser.parse_args()
    if args.plan:
        if args.manifest.exists():
            raise FileExistsError(args.manifest)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        save(args.manifest, plan())
        print(json.dumps({'manifest': str(args.manifest), 'trials': 32}))
    elif args.serve:
        from aiohttp import web
        web.run_app(create_service(args.port, args.run_dir), host='127.0.0.1', port=args.port)
    else:
        print(json.dumps(asyncio.run(run(args.base_url, args.output,
            json.loads(args.manifest.read_text(encoding='utf-8'))))))


if __name__ == '__main__':
    main()
