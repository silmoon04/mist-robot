"""Isolated Scribe language-hint diagnostic; default invocation makes no API calls.

Run `--execute` only after the main benchmark and other live probes finish.
Eight fresh, serial VAD connections compare auto language with explicit English.
No LLM, TTS, floor controller, manual commit, or retry is used.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import time
from urllib.parse import urlencode
import wave

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parents[1]
ROOT = BRAIN.parent
sys.path.insert(0, str(BRAIN))
from harness.pi_client import load_env
try:
    from .speech_cases_20260930 import CASES, FIXTURE_ROOT
    from .streaming_asr_20260930 import ScribeRealtimeASR
except ImportError:
    from speech_cases_20260930 import CASES, FIXTURE_ROOT
    from streaming_asr_20260930 import ScribeRealtimeASR

OUT_BASE = BRAIN / 'results/flux-scribe-jev-20260930'
CASE_IDS = ('yeah_backchannel', 'normal_end')
SEED = 20260930
LEAD_S = 1
TAIL_S = 5
DRAIN_S = 3
FRAME_BYTES = 640  # 20 ms mono PCM16; adapter sends 100 ms packets.


class EnglishScribe(ScribeRealtimeASR):
    @property
    def url(self):
        # Keep every inherited query setting; change only language_code.
        return super().url + '&' + urlencode({'language_code': 'en'})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases():
    return {case.id: case for case in CASES if case.id in CASE_IDS}


def plan():
    """Two counterbalanced randomized pairs per case, serially executed."""
    rng = random.Random(SEED)
    blocks = [(case_id, repetition) for case_id in CASE_IDS for repetition in (1, 2)]
    rng.shuffle(blocks)
    result = []
    for case_id, repetition in blocks:
        languages = ['auto', 'en']
        rng.shuffle(languages)
        result.extend({'case_id': case_id, 'repetition': repetition,
                       'language': language} for language in languages)
    return result


def pcm_for(case):
    path = ROOT / FIXTURE_ROOT / case.fixture
    with wave.open(str(path), 'rb') as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
            raise ValueError(f'Expected mono 16 kHz PCM16 fixture: {case.fixture}')
        pcm = audio.readframes(audio.getnframes())
    return path, pcm


def tokens(text):
    return re.findall(r"[\w']+", text.lower())


def wer(reference, hypothesis):
    left, right = tokens(reference), tokens(hypothesis)
    if not left:
        return None
    previous = list(range(len(right) + 1))
    for i, word in enumerate(left, 1):
        current = [i]
        for j, candidate in enumerate(right, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (word != candidate)))
        previous = current
    return round(previous[-1] / len(left), 6)


def summarize(rows):
    """Descriptive ASR results only; no floor or response-quality inference."""
    groups = {}
    for row in rows:
        key = (row['case_id'], row['language'])
        group = groups.setdefault(key, {'case_id': key[0], 'language': key[1],
                                        'trials': 0, 'committed': 0, 'wer_values': [],
                                        'transcripts': []})
        group['trials'] += 1
        group['committed'] += row['status'] == 'complete'
        if row['wer'] is not None:
            group['wer_values'].append(row['wer'])
        group['transcripts'].append(row['final_transcript'])
    return [{**group,
             'mean_wer_on_committed': (round(sum(group['wer_values']) / len(group['wer_values']), 6)
                                       if group['wer_values'] else None)}
            for _, group in sorted(groups.items())]


async def trial(spec, case, key, *, adapter_factory=None, sleep=asyncio.sleep):
    fixture_path, pcm = pcm_for(case)
    factory = adapter_factory or (lambda: EnglishScribe(key) if spec['language'] == 'en'
                                  else ScribeRealtimeASR(key))
    adapter = factory()
    events = []
    began = time.monotonic()
    event_signal = asyncio.Event()
    sent_bytes = 0
    failure_type = None

    def record(event):
        events.append({'at_s': round(time.monotonic() - began, 4), **event})
        if event['type'] in ('turn_end', 'error'):
            event_signal.set()

    try:
        await adapter.start(record)
        audio = b'\0' * (16000 * 2 * LEAD_S) + pcm + b'\0' * (16000 * 2 * TAIL_S)
        audio_epoch = time.monotonic()
        for offset in range(0, len(audio), FRAME_BYTES):
            if time.monotonic() - audio_epoch > len(audio) / 32000 + 2:
                raise TimeoutError('paced_audio_deadline')
            await sleep(max(0, audio_epoch + offset / 32000 - time.monotonic()))
            chunk = audio[offset:offset + FRAME_BYTES]
            await adapter.send_pcm16k(chunk)
            sent_bytes += len(chunk)
        if not event_signal.is_set():
            try:
                await asyncio.wait_for(event_signal.wait(), timeout=DRAIN_S)
            except asyncio.TimeoutError:
                pass
    except Exception as error:
        failure_type = type(error).__name__
    finally:
        try:
            await adapter.close()
        except Exception as error:
            failure_type = failure_type or 'close_' + type(error).__name__

    finals = [event['segment'] for event in events if event['type'] == 'final' and event['segment']]
    transcript = ' '.join(finals)
    expected = ' '.join(case.expected_transcript)
    raw_ack = next((raw for raw in adapter.raw_events if raw.get('message_type') == 'session_started'), None)
    first = {}
    for event in events:
        first.setdefault(event['type'], event['at_s'])
    return {
        **spec, 'status': ('complete' if finals and any(e['type'] == 'turn_end' for e in events)
                            else 'incomplete'),
        'failure_type': failure_type,
        'fixture': str(fixture_path.relative_to(ROOT)).replace('\\', '/'),
        'fixture_sha256': sha256(fixture_path),
        'fixture_s': round(len(pcm) / 32000, 4),
        'lead_s': LEAD_S, 'tail_s': TAIL_S, 'drain_s': DRAIN_S,
        'sent_pcm_bytes': sent_bytes, 'sent_pcm_s': round(sent_bytes / 32000, 4),
        'expected_transcript': expected, 'final_transcript': transcript,
        'wer': wer(expected, transcript) if finals else None,
        'provider_session_started': raw_ack is not None,
        'provider_language_config': (raw_ack or {}).get('config', {}).get('language_code'),
        'first_event_s': first,
        'timing_summary': adapter.timing_summary,
        'events': events, 'raw_events': adapter.raw_events,
        'elapsed_s': round(time.monotonic() - began, 4),
    }


async def execute(out_name):
    selected = cases()
    if set(selected) != set(CASE_IDS):
        raise ValueError('Required cases are unavailable')
    if not re.fullmatch(r'scribe-language-probe-[0-9]{2}', out_name):
        raise ValueError('Output must be a new scribe-language-probe-NN directory')
    out = OUT_BASE / out_name
    out.mkdir(parents=True, exist_ok=False)
    # Load only the existing repository key; never serialize or print its value.
    key = load_env().get('ELEVENLABS_API_KEY', '').strip('"\'')
    if not key:
        raise RuntimeError('Existing ElevenLabs key unavailable')
    order = plan()
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(),
                'purpose': 'ASR-only language hint diagnostic, not core benchmark',
                'credential_source': 'brain.harness.pi_client.load_env:ELEVENLABS_API_KEY',
                'source_sha256': sha256(Path(__file__)),
                'adapter_sha256': sha256(HERE / 'streaming_asr_20260930.py'),
                'case_spec_sha256': sha256(HERE / 'speech_cases_20260930.py'),
                'seed': SEED, 'lead_s': LEAD_S, 'tail_s': TAIL_S,
                'drain_s': DRAIN_S, 'manual_commit': False, 'order': order}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    rows = []
    for index, spec in enumerate(order, 1):
        row = await trial(spec, selected[spec['case_id']], key)
        rows.append(row)
        (out / f'{index:02d}__{spec["case_id"]}__r{spec["repetition"]}__{spec["language"]}.json').write_text(
            json.dumps(row, indent=2), encoding='utf-8')
        print(f'{index}/8 {spec["case_id"]} r{spec["repetition"]} {spec["language"]}: '
              f'{row["status"]}, WER={row["wer"]}', flush=True)
    (out / 'summary.json').write_text(json.dumps({
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'ASR-only descriptive language diagnostic',
        'groups': summarize(rows)}, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true',
                        help='Run eight paid Scribe connections after the main benchmark')
    parser.add_argument('--out', default='scribe-language-probe-01')
    args = parser.parse_args()
    if args.execute:
        asyncio.run(execute(args.out))
    else:
        print(json.dumps({'dry_run': True, 'connections': 8,
                          'order': plan(), 'output_if_executed': args.out}, indent=2))


if __name__ == '__main__':
    main()
