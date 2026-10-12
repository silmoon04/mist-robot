"""One authorized, bounded ASR-only connection per provider; no LLM or TTS."""
from __future__ import annotations

import asyncio
import argparse
import json
import os
from pathlib import Path
import sys
import time
import wave

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parents[1]
sys.path.insert(0, str(BRAIN))
from harness.pi_client import load_env
try:
    from .streaming_asr_20260930 import Nova3ASR, FluxASR, ScribeRealtimeASR, FluxScribeShadowASR
except ImportError:
    from streaming_asr_20260930 import Nova3ASR, FluxASR, ScribeRealtimeASR, FluxScribeShadowASR

SOURCE = BRAIN / 'results/e2e_20260924/fixtures_v2/audio/audio_phrase_seam-1.wav'
OUT_BASE = BRAIN / 'results/flux-scribe-jev-20260930'
SILENCE_S = 10
MAX_STREAM_S = 18


def fixture():
    with wave.open(str(SOURCE), 'rb') as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
            raise ValueError('Expected fixture in 16 kHz mono PCM16')
        data = audio.readframes(audio.getnframes())
    return data


async def trial(label, adapter, pcm, out, drain_seconds):
    started = time.monotonic()
    normalized = []
    first_event = {}
    sent = 0
    completed = asyncio.Event()

    def record(event):
        elapsed = round(time.monotonic() - started, 4)
        normalized.append({'at_s': elapsed, **event})
        first_event.setdefault(event['type'], elapsed)
        if event['type'] in ('turn_end', 'error'):
            completed.set()

    status, failure = 'error', None
    try:
        await adapter.start(record)
        audio = pcm + b'\0' * (16000 * 2 * SILENCE_S)
        frame = 640  # 20 ms at 16 kHz, regrouped to 80 ms by Flux.
        clock = time.monotonic()
        for offset in range(0, len(audio), frame):
            if time.monotonic() - clock >= MAX_STREAM_S:
                raise TimeoutError('stream_duration_limit')
            await asyncio.sleep(max(0, clock + offset / 32000 - time.monotonic()))
            chunk = audio[offset:offset + frame]
            await adapter.send_pcm16k(chunk)
            sent += len(chunk)
        if not completed.is_set():
            try:
                await asyncio.wait_for(completed.wait(), timeout=drain_seconds)
            except asyncio.TimeoutError:
                pass
        status = 'pass' if any(e['type'] == 'final' and e['text'] for e in normalized) and any(
            e['type'] == 'turn_end' for e in normalized) else 'incomplete'
        if label == 'dual':
            shadow_kinds = {e['metadata'].get('original_event_type') for e in normalized
                            if e['type'] == 'shadow'}
            if not {'final', 'turn_end'} <= shadow_kinds:
                status = 'incomplete'
    except Exception as error:
        failure = type(error).__name__
    finally:
        try:
            await adapter.close()
        except Exception as error:
            failure = failure or ('close_' + type(error).__name__)
    payload = {'provider': label, 'status': status, 'failure_type': failure,
               'source': str(SOURCE.relative_to(BRAIN)), 'source_pcm_seconds': len(pcm) / 32000,
               'silence_seconds_requested': SILENCE_S, 'sent_pcm_seconds': sent / 32000,
               'adapter_sent_pcm_bytes': adapter.sent_pcm_bytes,
               'adapter_sent_pcm_seconds_billing_proxy': adapter.sent_pcm_seconds,
               'connected_duration_s': round(adapter.connected_duration_s, 4),
               'shadow_sent_pcm_seconds_billing_proxy': getattr(adapter, 'shadow_sent_pcm_seconds', None),
               'shadow_connected_duration_s': getattr(adapter, 'shadow_connected_duration_s', None),
               'shadow_dropped_pcm_bytes': getattr(adapter, 'shadow_dropped_pcm_bytes', None),
               'billing_note': 'Submitted audio seconds include silence; not a provider invoice.',
               'elapsed_s': round(time.monotonic() - started, 4), 'first_event_at_s': first_event,
               'settings': {'sample_rate': 16000, 'packet_ms': getattr(adapter, 'packet_ms', 20),
                            'model': adapter.model, 'url_without_credentials': adapter.url},
               'events': normalized, 'raw_events': adapter.raw_events}
    (out / f'{label}.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'{label}: {status}; final={sum(e["type"] == "final" for e in normalized)}; '
          f'turn_end={sum(e["type"] == "turn_end" for e in normalized)}; '
          f'error={failure or "none"}', flush=True)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='asr-smoke-01')
    parser.add_argument('--providers', nargs='+', choices=('nova3', 'flux', 'scribe', 'dual'),
                        default=['nova3', 'flux', 'scribe'])
    parser.add_argument('--drain-seconds', type=int, default=5, choices=range(1, 11))
    args = parser.parse_args()
    if '/' in args.out or '\\' in args.out or not args.out.startswith('asr-smoke-'):
        raise ValueError('Output must be a new asr-smoke-* directory name')
    out = OUT_BASE / args.out
    out.mkdir(parents=True, exist_ok=False)
    pcm = fixture()
    env = {**load_env(), **os.environ}
    dg = env.get('DEEPGRAM_API_KEY', '').strip('"\'')
    el = env.get('ELEVENLABS_API_KEY', '').strip('"\'')
    if not dg or not el:
        raise RuntimeError('Required existing ASR credentials are unavailable')
    adapters = {'nova3': Nova3ASR(dg), 'flux': FluxASR(dg),
                'scribe': ScribeRealtimeASR(el),
                'dual': FluxScribeShadowASR(dg, el)}
    for label in args.providers:
        await trial(label, adapters[label], pcm, out, args.drain_seconds)


if __name__ == '__main__':
    asyncio.run(main())
