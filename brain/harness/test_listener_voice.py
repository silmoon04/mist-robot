"""Bounded cache tests for the nonblocking listening acknowledgement path."""
import base64
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from duplex.listener_voice import MODEL, SAMPLE_RATE, TEXTS, VoiceCache, _trim_silence


def pcm(seconds, value=0):
    return struct.pack('<h', value) * round(seconds * SAMPLE_RATE)


class FakeResponse:
    def __init__(self, status, body):
        self.status, self.body = status, body
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    async def read(self): return self.body


class FakeSession:
    closed = False
    def __init__(self, response_factory):
        self.response_factory = response_factory
        self.calls = []
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response_factory(url, kwargs)
    async def close(self): self.closed = True


class ListenerVoiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_warm_synthesizes_only_two_soft_cues_and_event_is_energy_gated(self):
        # 250 ms of quiet before and after a gentle voiced middle.
        raw = pcm(.25) + pcm(.35, 900) + pcm(.25)
        session = FakeSession(lambda _url, _kwargs: FakeResponse(200, raw))
        with tempfile.TemporaryDirectory() as folder:
            cache = VoiceCache('runtime-key-fixture', folder, session=session)
            self.assertTrue(await cache.warm())
            self.assertEqual(len(session.calls), 2)
            for _url, request in session.calls:
                self.assertIn('/24AMj4dc02cYAwoUnqzN/stream?', _url)
                self.assertEqual(request['json']['model_id'], MODEL)
                self.assertEqual(request['headers']['xi-api-key'], 'runtime-key-fixture')
            mhm = cache.event_for('mhm')
            self.assertEqual(mhm['text'], TEXTS['mhm'])
            self.assertEqual(mhm['sample_rate'], SAMPLE_RATE)
            self.assertLessEqual(mhm['duration_s'], 1.5)
            self.assertEqual(base64.b64decode(mhm['pcm']), _trim_silence(raw))
            active = [cue for cue in mhm['mouth_cues'] if cue['viseme'] != 'rest']
            self.assertTrue(active)
            self.assertTrue(all(cue['viseme'] == 'MBP' for cue in active))
            self.assertTrue(all(cue['amount'] <= .35 for cue in active))
            self.assertIsNone(cache.event_for('unrecognized'))

    async def test_existing_cache_serves_without_a_runtime_key_or_provider(self):
        raw = pcm(.4, 700)
        with tempfile.TemporaryDirectory() as folder:
            first = VoiceCache('fixture', folder, session=FakeSession(
                lambda _url, _kwargs: FakeResponse(200, raw)))
            await first.warm()
            second = VoiceCache('', folder)
            event = second.event_for('uh_huh')
            self.assertEqual(event['text'], TEXTS['uh_huh'])
            self.assertEqual(base64.b64decode(event['pcm']), raw)
            self.assertIsNotNone(second.event_for('mhm'))

    async def test_invalid_cache_and_provider_failure_are_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            audio = Path(folder) / 'mhm-invalid.pcm'
            metadata = Path(folder) / 'mhm-invalid.json'
            audio.write_bytes(b'bad')
            metadata.write_text('{broken', encoding='utf-8')
            session = FakeSession(lambda _url, _kwargs: FakeResponse(401, b'private provider detail'))
            cache = VoiceCache('fixture', folder, session=session)
            self.assertFalse(await cache.warm())
            self.assertIsNone(cache.event_for('mhm'))
            self.assertEqual(len(session.calls), 2)
            for path in Path(folder).glob('*.json'):
                if path.name != metadata.name:
                    parsed = json.loads(path.read_text(encoding='utf-8'))
                    self.assertNotIn('fixture', json.dumps(parsed))

    async def test_rejects_malformed_silent_and_overlong_pcm(self):
        for raw in (b'', b'\x00', pcm(.3), pcm(1.6, 900)):
            with self.assertRaises(ValueError):
                _trim_silence(raw)
        with self.assertRaises(ValueError):
            _trim_silence(pcm(10.1, 900))


if __name__ == '__main__':
    unittest.main()
