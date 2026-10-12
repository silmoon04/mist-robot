"""Bounded live ElevenLabs delivery-profile and v3 compatibility probe.

Runs at most six current Flash multi-context TTS utterances and one documented
v3 Text-to-Dialogue utterance. Writes only public-safe provider outcomes/audio.
"""
from __future__ import annotations

import asyncio
import base64
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid
import wave

import aiohttp

ROOT = Path(__file__).resolve().parents[2]
BRAIN = ROOT / 'brain'
OUT = BRAIN / 'results' / 'dual-model-harness-20260924' / 'prosody'
TEXT = 'I found a small blue light near the doorway, and I wanted to tell you before it disappears.'
VOICE_ID = '24AMj4dc02cYAwoUnqzN'
FLASH_ORDER = [
    ('neutral', 1), ('gentle', 1), ('bright', 1),
    ('bright', 2), ('gentle', 2), ('neutral', 2),
]


def load_key() -> str | None:
    value = os.environ.get('ELEVENLABS_API_KEY')
    if value:
        return value.strip()
    env_file = ROOT / '.env'
    if not env_file.exists():
        return None
    for line in env_file.read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('ELEVENLABS_API_KEY='):
            value = line.split('=', 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            return value or None
    return None


def write_wav(path: Path, pcm: bytes, sample_rate: int = 24000) -> None:
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)


def compact_error(stage: str, kind: str, status: int | None = None) -> dict:
    result = {'stage': stage, 'kind': kind}
    if status is not None:
        result['status'] = status
    return result


async def flash_probe(key: str) -> tuple[list[dict], dict | None]:
    sys.path.insert(0, str(BRAIN))
    from duplex.tts import StreamingTTS

    events: list[dict] = []

    async def emit(event):
        events.append(event)

    tts = StreamingTTS(key, emit)
    records: list[dict] = []
    failure = None
    try:
        try:
            await tts.start()
        except Exception as error:
            return [], compact_error('flash_connect', type(error).__name__)

        for delivery, repeat in FLASH_ORDER:
            if tts.muted or tts.closed:
                failure = compact_error('flash', 'session_muted')
                break
            event_start = len(events)
            turn_id = f'{delivery}-{repeat}'
            started = time.monotonic()
            try:
                await tts.begin(turn_id, delivery=delivery)
                if tts.muted:
                    failure = compact_error('flash_begin', 'provider_failure')
                    break
                await tts.text(TEXT)
                await tts.finish(TEXT)
            except Exception as error:
                failure = compact_error('flash_turn', type(error).__name__)
                break

            deadline = time.monotonic() + 9.0
            while time.monotonic() < deadline:
                turn_events = events[event_start:]
                if any(e.get('type') == 'latency' and e.get('tts', {}).get('sequence') == tts.sequence - 1
                       for e in turn_events):
                    break
                if any(e.get('type') == 'voice_warning' for e in turn_events) or tts.muted:
                    warning = next((e for e in turn_events if e.get('type') == 'voice_warning'), {})
                    failure = compact_error('flash_generation', str(warning.get('code') or 'provider_failure'))
                    break
                await asyncio.sleep(.04)
            turn_events = events[event_start:]
            latency_event = next((e.get('tts') for e in turn_events
                                  if e.get('type') == 'latency' and e.get('tts', {}).get('sequence') == tts.sequence - 1), None)
            if latency_event is None:
                if failure is None:
                    failure = compact_error('flash_generation', 'no_final_within_probe_deadline')
                    failure.update({
                        'wait_deadline_s': 9.0,
                        'event_type_counts': {kind: sum(1 for event in turn_events if event.get('type') == kind)
                                              for kind in sorted({str(event.get('type', 'unknown')) for event in turn_events})},
                        'audio_packet_count': sum(1 for event in turn_events if event.get('type') == 'audio'),
                        'warning_codes': [str(event.get('code')) for event in turn_events
                                          if event.get('type') == 'voice_warning' and event.get('code')],
                        'connection_was_open_at_deadline': bool(tts.socket is not None and not tts.socket.closed),
                    })
                break
            seq = latency_event['sequence']
            audio = b''.join(base64.b64decode(e['pcm'], validate=True)
                             for e in turn_events if e.get('type') == 'audio' and e.get('seq') == seq)
            source_counts: dict[str, int] = {}
            aligned_bytes = 0
            for event in turn_events:
                if event.get('type') != 'audio' or event.get('seq') != seq:
                    continue
                source = str(event.get('alignment_source') or 'unavailable')
                source_counts[source] = source_counts.get(source, 0) + 1
                if source.startswith('elevenlabs_'):
                    aligned_bytes += len(base64.b64decode(event['pcm'], validate=True))
            filename = f'flash-{delivery}-{repeat}.wav'
            write_wav(OUT / filename, audio)
            duration = len(audio) / 48000
            records.append({
                'model': 'eleven_flash_v2_5', 'delivery': delivery, 'repeat': repeat,
                'stability': {'neutral': .5, 'gentle': .65, 'bright': .3}[delivery],
                'similarity_boost': .8, 'use_speaker_boost': False,
                'first_provider_byte_s': latency_event.get('first_byte_s'),
                'output_duration_s': duration,
                'alignment_coverage': (aligned_bytes / len(audio)) if audio else 0.0,
                'audio_file': filename, 'alignment_source_packets': source_counts,
                'status': 'ok' if audio else 'empty_audio',
                'probe_elapsed_s': round(time.monotonic() - started, 3),
            })
            if not audio:
                failure = compact_error('flash_generation', 'empty_audio')
                break
    finally:
        try:
            await tts.close()
        except Exception:
            pass
    return records, failure


async def v3_probe(key: str, tag: str | None = None,
                   output_name: str = 'v3-conversational-once.wav') -> tuple[dict, dict | None]:
    """One-shot v3 multi-context request; no retry and no response text in report."""
    url = ('wss://api.elevenlabs.io/v1/text-to-dialogue/multi-stream-input'
           '?model_id=eleven_v3_conversational&output_format=pcm_24000&sync_alignment=true')
    input_text = f'[{tag}] {TEXT}' if tag else TEXT
    record = {'model': 'eleven_v3_conversational', 'status': 'not_run',
              'tag': tag, 'input_text': input_text}
    audio = bytearray()
    aligned_bytes = 0
    alignment_packets = 0
    started = time.monotonic()
    first_text_sent = None
    first_audio_at = None
    status = None
    error = None
    context = f'mist-affect-probe-{uuid.uuid4().hex}'

    timeout = aiohttp.ClientTimeout(total=14, connect=5, sock_read=9)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as client:
            try:
                socket = await client.ws_connect(url, headers={'xi-api-key': key}, max_msg_size=4 * 1024 * 1024)
            except aiohttp.WSServerHandshakeError as exc:
                status = exc.status
                error = compact_error('v3_connect', 'handshake_rejected', status)
                return record | {'status': 'error', 'error': error}, error
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                error = compact_error('v3_connect', type(exc).__name__)
                return record | {'status': 'error', 'error': error}, error

            try:
                await socket.send_json({'context_id': context, 'voices': [VOICE_ID]})
                first_text_sent = time.monotonic()
                await socket.send_json({'context_id': context, 'inputs': [{'text': input_text, 'voice_id': VOICE_ID}]})
                await socket.send_json({'context_id': context, 'close_context': True})
                deadline = time.monotonic() + 9.0
                final_seen = False
                while time.monotonic() < deadline:
                    try:
                        message = await asyncio.wait_for(socket.receive(), timeout=max(.1, deadline - time.monotonic()))
                    except asyncio.TimeoutError:
                        break
                    if message.type == aiohttp.WSMsgType.TEXT:
                        try:
                            payload = json.loads(message.data)
                        except (ValueError, TypeError):
                            continue
                        msg_context = payload.get('context_id', payload.get('contextId'))
                        if msg_context not in (None, context):
                            continue
                        if payload.get('error'):
                            error = compact_error('v3_generation', 'provider_error')
                            break
                        encoded = payload.get('audio')
                        if encoded:
                            chunk = base64.b64decode(encoded, validate=True)
                            audio.extend(chunk)
                            if first_audio_at is None:
                                first_audio_at = time.monotonic()
                            alignment = payload.get('alignment') or payload.get('normalizedAlignment') or {}
                            chars = alignment.get('chars') or []
                            durations = alignment.get('char_durations_ms', alignment.get('charDurationsMs', [])) or []
                            if chars and len(chars) == len(durations):
                                alignment_packets += 1
                                aligned_bytes += len(chunk)
                        if payload.get('is_final') or payload.get('isFinal'):
                            final_seen = True
                            break
                    elif message.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE):
                        error = compact_error('v3_generation', 'socket_closed')
                        break
                if not final_seen and error is None:
                    error = compact_error('v3_generation', 'final_timeout')
            finally:
                await socket.close()
    except Exception as exc:
        error = compact_error('v3_client', type(exc).__name__)

    if audio:
        filename = output_name
        write_wav(OUT / filename, bytes(audio))
        record.update({
            'status': 'ok' if error is None else 'partial_audio',
            'first_provider_byte_s': None if first_audio_at is None or first_text_sent is None else first_audio_at - first_text_sent,
            'output_duration_s': len(audio) / 48000,
            'alignment_coverage': aligned_bytes / len(audio),
            'alignment_packets': alignment_packets,
            'audio_file': filename,
            'probe_elapsed_s': round(time.monotonic() - started, 3),
        })
    else:
        record.update({'status': 'error', 'probe_elapsed_s': round(time.monotonic() - started, 3)})
    if error:
        record['error'] = error
    return record, error


def write_report(flash: list[dict], v3: dict | None, error: dict | None,
                 flash_error: dict | None = None, v3_error: dict | None = None,
                 v3_attempts: list[dict] | None = None,
                 v3_tag_samples: list[dict] | None = None) -> None:
    payload = {
        'date': '2026-09-24', 'voice_id': VOICE_ID,
        'utterance': TEXT,
        'method': 'Same one-sentence plain text; Flash order neutral, gentle, bright, bright, gentle, neutral. Two Flash samples completed. A third timed out at the 9-second probe deadline. The first v3 attempt failed locally before sending context/text; one corrected v3 synthesis request completed. No generation request was repeated.',
        'flash': flash, 'v3_conversational': v3,
        'flash_probe_error': flash_error, 'v3_probe_error': v3_error,
        'v3_attempts': v3_attempts or [],
        'v3_tag_samples': v3_tag_samples or [],
        'v3_probe_scope': 'The baseline v3 sample uses plain text and checks model/voice/output-format compatibility. Separate tagged samples use documented [curious] and [excited] audio tags. Audio tags are tested as provider controls, not as proof of human-perceived quality.',
        'probe_error': error,
        'quality_claim': 'Audio was not machine-scored. No human listening judgment is recorded by this probe.',
        'timing_note': 'Flash first_provider_byte_s is the existing implementation metric (first non-whitespace text to first provider audio byte); it is not browser playback onset. V3 timing is measured from sending the text input to first provider audio byte.',
        'alignment_note': 'Coverage is the share of returned PCM bytes in chunks carrying usable provider character timing; it is not phoneme accuracy or mouth-shape quality.',
    }
    (OUT / 'results.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    rows = []
    for item in flash + ([v3] if v3 else []) + (v3_tag_samples or []):
        name = item.get('audio_file')
        player = f'<audio controls preload="none" src="{name}"></audio>' if name else ''
        latency = item.get('first_provider_byte_s')
        rows.append('<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
            item.get('model', ''), item.get('tag', item.get('delivery', 'v3 baseline')), item.get('repeat', '1'),
            '' if latency is None else f'{latency * 1000:.0f} ms',
            '' if item.get('output_duration_s') is None else f"{item['output_duration_s']:.2f} s",
            '' if item.get('alignment_coverage') is None else f"{item['alignment_coverage']:.0%}", player))
    notices = []
    if flash_error:
        notices.append(f'Flash stopped: {flash_error.get("kind")} (see results JSON for trace availability).')
    if v3_error:
        notices.append(f'V3 stopped: {v3_error.get("stage")} / {v3_error.get("kind")} .')
    error_html = ''.join(f'<p>{notice}</p>' for notice in notices)
    html = ('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>MIST prosody probe</title><style>body{font:15px/1.5 system-ui;max-width:1100px;margin:30px auto;padding:0 18px;color:#263832;background:#f5f5ef}table{border-collapse:collapse;width:100%;background:#fff}th,td{text-align:left;padding:10px;border-bottom:1px solid #d9e0d8}audio{width:190px}small{color:#59655f}</style>'
            '<h1>MIST prosody probe</h1><p>One fixed sentence and voice ID. Flash profiles change stability; v3 baseline is plain text and the added v3 rows use documented tags. The audio files support listening comparison, but no claim of improved human quality is made.</p>'
            '<p><strong>Text:</strong> ' + TEXT + '</p>' + error_html +
            '<table><thead><tr><th>Model</th><th>Delivery</th><th>Repeat</th><th>First provider byte</th><th>Audio duration</th><th>Timing coverage</th><th>Listen</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
            '<p><small>Flash latency uses the bridge’s text-to-provider-byte metric, not browser playback onset. V3 latency is from text-input send to first provider byte. Alignment coverage only means returned PCM chunks carried character timing. Listen and judge voice quality separately.</small></p>')
    (OUT / 'index.html').write_text(html, encoding='utf-8')


async def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v3-only', action='store_true', help='run the single v3 check without repeating Flash samples')
    parser.add_argument('--corrected-v3-once', action='store_true', help='one corrected v3 request after the recorded pre-send aiohttp bug')
    parser.add_argument('--v3-tags-once', action='store_true', help='at most one request each for documented curious and excited tags')
    args = parser.parse_args()
    if sum((args.v3_only, args.corrected_v3_once, args.v3_tags_once)) > 1:
        parser.error('choose only one v3 mode')
    key = load_key()
    if not key:
        error = compact_error('credentials', 'ELEVENLABS_API_KEY_unavailable')
        write_report([], None, error)
        return 2

    prior = None
    flash_error = None
    v3_error = None
    v3_attempts: list[dict] = []
    v3_tag_samples: list[dict] = []
    if args.v3_only:
        prior_path = OUT / 'results.json'
        if not prior_path.exists():
            error = compact_error('v3_only', 'prior_flash_results_missing')
            write_report([], None, error)
            return 2
        prior = json.loads(prior_path.read_text(encoding='utf-8'))
        if prior.get('v3_conversational') is not None:
            print(json.dumps({'v3_status': 'already_attempted', 'result_file': str(prior_path)}))
            return 2
        flash = prior.get('flash', [])
        flash_error = prior.get('flash_probe_error', prior.get('probe_error'))
        v3_attempts = prior.get('v3_attempts', [])
        v3, error = await v3_probe(key)
        v3_error = error
    elif args.corrected_v3_once:
        prior_path = OUT / 'results.json'
        if not prior_path.exists():
            error = compact_error('v3_corrected', 'prior_results_missing')
            write_report([], None, error)
            return 2
        prior = json.loads(prior_path.read_text(encoding='utf-8'))
        previous = prior.get('v3_conversational') or {}
        previous_error = previous.get('error') or {}
        if not (previous_error.get('stage') == 'v3_client' and previous_error.get('kind') == 'TypeError'
                and previous.get('status') == 'error'):
            print(json.dumps({'v3_status': 'corrected_request_refused', 'reason': 'prior_error_not_the_recorded_pre_send_client_bug'}))
            return 2
        v3_attempts = prior.get('v3_attempts', [])
        if any(attempt.get('kind') == 'corrected_request' for attempt in v3_attempts):
            print(json.dumps({'v3_status': 'corrected_request_already_attempted', 'result_file': str(prior_path)}))
            return 2
        v3_attempts.append({
            'kind': 'original_request', 'status': 'client_error_before_context_or_text_send',
            'client_error': 'TypeError',
            'local_cause': 'aiohttp ClientWebSocketResponse is not an async context manager',
            'provider_synthesis_request_sent': False,
        })
        flash = prior.get('flash', [])
        flash_error = prior.get('flash_probe_error')
        v3, error = await v3_probe(key)
        v3_error = error
        v3_attempts.append({
            'kind': 'corrected_request', 'status': v3.get('status'),
            'error': error, 'provider_synthesis_request_sent': True,
        })
    elif args.v3_tags_once:
        prior_path = OUT / 'results.json'
        if not prior_path.exists():
            error = compact_error('v3_tagged', 'prior_results_missing')
            write_report([], None, error)
            return 2
        prior = json.loads(prior_path.read_text(encoding='utf-8'))
        baseline = prior.get('v3_conversational') or {}
        if baseline.get('status') != 'ok':
            print(json.dumps({'v3_status': 'tagged_request_refused', 'reason': 'plain_text_v3_baseline_not_successful'}))
            return 2
        v3_tag_samples = prior.get('v3_tag_samples', [])
        v3_attempts = prior.get('v3_attempts', [])
        completed_tags = {item.get('tag') for item in v3_tag_samples}
        tags = [tag for tag in ('curious', 'excited') if tag not in completed_tags]
        if not tags:
            print(json.dumps({'v3_status': 'tagged_requests_already_attempted', 'result_file': str(prior_path)}))
            return 2
        flash = prior.get('flash', [])
        flash_error = prior.get('flash_probe_error')
        v3 = baseline
        for tag in tags[:2]:
            sample, error = await v3_probe(key, tag=tag, output_name=f'v3-{tag}.wav')
            v3_tag_samples.append(sample)
            v3_error = error
            v3_attempts.append({'kind': 'tagged_request', 'tag': tag,
                                'status': sample.get('status'), 'error': error,
                                'provider_synthesis_request_sent': True})
            if error:
                break
    else:
        flash, error = await flash_probe(key)
        flash_error = error
        v3 = None
        if error is None and len(flash) == 6:
            v3, error = await v3_probe(key)
            v3_error = error
    if prior is not None:
        prior['v3_conversational'] = v3
        prior['v3_attempts'] = v3_attempts
        prior['v3_tag_samples'] = v3_tag_samples
        prior['probe_error'] = error
        (OUT / 'results.json').write_text(json.dumps(prior, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        # Reuse the renderer with the preserved Flash records and v3 result.
        write_report(flash, v3, error, flash_error=flash_error, v3_error=v3_error,
                     v3_attempts=v3_attempts, v3_tag_samples=v3_tag_samples)
    print(json.dumps({'flash_samples': len(flash), 'flash_statuses': [r['status'] for r in flash],
                      'v3_status': None if v3 is None else v3['status'],
                      'stopped_on_error': error is not None,
                      'result_file': str(OUT / 'results.json'), 'listen_page': str(OUT / 'index.html')}))
    return 0 if len(flash) == 6 else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
