"""Generate three short MIST fixtures and preserve their streaming mouth cues."""
import asyncio
import base64
import json
from pathlib import Path
import sys
import time
import wave

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN))
from duplex.tts import StreamingTTS
from pi_client import load_env

OUT = BRAIN / 'art_direction/artist_studio_20260916/reuse/drawn/audio'
CASES = [
    ('aligned_soft', "Maybe. No rush. I'm here, and I'm listening."),
    ('aligned_bright', 'Blue balloons! Wow, that worked. Shall we try again?'),
    ('aligned_pause', 'Let me think. One moment... Yes. We can do that.'),
]


async def main():
    reports = []
    packets, notices = [], []
    finished = asyncio.Event()

    async def emit(event):
        if event['type'] == 'audio':
            packets.append(event)
        elif event['type'] == 'latency':
            notices.append(event)
            finished.set()
        elif event['type'] in ('voice_warning', 'error'):
            notices.append(event)
            finished.set()

    key = load_env().get('ELEVENLABS_API_KEY', '').strip('"\'')
    if not key:
        raise RuntimeError('Configured ElevenLabs key is missing')
    tts = StreamingTTS(key, emit)
    provider_errors = []
    output = tts.output
    async def observed_output(message):
        if message.get('error'):
            provider_errors.append(json.dumps({k: message[k] for k in ('error', 'code', 'message') if k in message}).replace(key, '[redacted]')[:500])
        await output(message)
    tts.output = observed_output
    try:
        await tts.start()
        for name, phrase in CASES:
            packets.clear(); notices.clear(); finished.clear()
            began = time.monotonic()
            await tts.begin(name)
            await tts.text(phrase)
            await tts.finish()
            await asyncio.wait_for(finished.wait(), 35)
            # The completion metric precedes the final drain within the provider callback.
            for _ in range(100):
                if not tts.pending:
                    break
                await asyncio.sleep(.01)
            if not packets:
                print(json.dumps({'failed': name, 'provider_errors': provider_errors, 'notices': notices}), flush=True)
                raise SystemExit(2)
            raw = bytearray()
            cues, sources = [], {}
            for packet in packets:
                offset = len(raw) / 48000
                chunk = base64.b64decode(packet['pcm'], validate=True)
                sources[packet.get('alignment_source', 'unknown')] = sources.get(packet.get('alignment_source', 'unknown'), 0) + len(chunk)
                cues.extend({**cue, 'time': round(offset + cue['time'], 6)} for cue in packet['mouth_cues'])
                raw.extend(chunk)
            OUT.mkdir(parents=True, exist_ok=True)
            with wave.open(str(OUT / (name + '.wav')), 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000); wav.writeframes(raw)
            source = 'elevenlabs_characters_audio_gated' if sources.get('elevenlabs_characters_audio_gated') else 'audio_energy'
            cue_payload = {'text': phrase, 'sample_rate': 24000, 'duration': len(raw)/48000,
                           'alignment_source': source, 'mouth_cues': cues}
            (OUT / (name + '.json')).write_text(json.dumps(cue_payload, indent=2) + '\n', encoding='utf-8')
            report = {'id': name, 'text': phrase, 'file': name + '.wav', 'cues': name + '.json',
                      'duration': len(raw)/48000, 'alignment': source, 'packetCount': len(packets),
                      'cueCount': len(cues), 'shapes': sorted(set(c['viseme'] for c in cues)),
                      'sourceBytes': sources, 'elapsed': round(time.monotonic()-began, 3),
                      'metrics': tts.metrics[-1] if tts.metrics else {},
                      'source': 'Live MIST ElevenLabs Flash v2.5 streaming test, 2026-09-22'}
            assert all(a['time'] <= b['time'] for a, b in zip(cues, cues[1:])), 'Non-monotonic cues'
            reports.append(report)
            print(json.dumps({k: report[k] for k in ('id', 'duration', 'packetCount', 'cueCount', 'shapes', 'alignment', 'metrics')}), flush=True)
    finally:
        await tts.close()
    (OUT / 'live_sync_results.json').write_text(json.dumps(reports, indent=2) + '\n', encoding='utf-8')
    existing = json.loads((OUT/'samples.json').read_text(encoding='utf-8-sig'))
    ids = {r['id'] for r in reports}
    (OUT/'samples.json').write_text(json.dumps(reports+[s for s in existing if s['id'] not in ids], indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    asyncio.run(main())
