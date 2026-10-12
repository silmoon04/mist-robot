"""Exercise speech request ownership and retries through the real HTTP handler.

Every test binds a temporary loopback port and replaces speech generation with
a fixed WAV fixture. It never starts a model, contacts a provider or uses 8776.
"""
from __future__ import annotations

import base64
import copy
import http.client
import json
import sys
import tempfile
import threading
import unittest
from concurrent.futures import Future, InvalidStateError, ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui import server


# A fixed mono PCM16 WAV with four samples at 24 kHz.
SAMPLE_WAV = (
    b"RIFF\x2c\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    b"\x01\x00\x01\x00\xc0\x5d\x00\x00\x80\xbb\x00\x00"
    b"\x02\x00\x10\x00data\x08\x00\x00\x00"
    b"\x00\x00\x10\x00\xf0\xff\x00\x00"
)
SAMPLE = {
    "audio_base64": base64.b64encode(SAMPLE_WAV).decode("ascii"),
    "mime_type": "audio/wav",
    "duration_s": 4 / 24000,
    "events": [{"time": 0, "shape": "rest"}],
    "provider": "elevenlabs",
    "voice_id": "fixture_voice",
    "model_id": "eleven_flash_v2_5",
    "alignment_source": "fixed_fixture",
    "usage": {"characters": 0, "audio_seconds": 4 / 24000, "fixture": True},
}


class SpeechHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mist-speech-http-")
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(patch.stopall)
        patch.object(server, "load_env", return_value={}).start()
        patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected provider request")).start()
        self.duplicate_wait_entered = threading.Event()
        self.fixture_threads = []
        self.fixture_futures = []
        self.fixture_lock = threading.Lock()
        fixture = self

        class ObservedFuture(Future):
            def __init__(self):
                super().__init__()
                with fixture.fixture_lock:
                    fixture.fixture_futures.append(self)

            def result(self, timeout=None):
                if not self.done():
                    fixture.duplicate_wait_entered.set()
                return super().result(timeout=timeout)

        patch.object(server, "Future", ObservedFuture, create=True).start()
        args = server.parse_args(["--stub", "--no-executive", "--run-dir", self.temporary.name])
        client = server.StubClient(args.model, args.thinking, args.soul, args.run_dir)
        self.app = server.App(args, "chat", client, None)
        self.calls = []
        self.calls_lock = threading.Lock()
        self.provider_entered = threading.Event()
        self.provider_release = threading.Event()
        self.provider_release.set()
        self.request_barrier = None
        self.barrier_request_id = None
        self.request_count = 0
        self.requests_seen = threading.Condition()
        self.provider = patch("ui.voice.generate_speech", side_effect=self.generate_speech).start()
        class FixtureHandler(server.Handler):
            app = fixture.app

            def setup(self):
                with fixture.fixture_lock:
                    fixture.fixture_threads.append(threading.current_thread())
                super().setup()

            def _read_json_body(self):
                body = super()._read_json_body()
                if (fixture.request_barrier is not None and isinstance(body, dict)
                        and body.get("request_id") == fixture.barrier_request_id):
                    fixture.request_barrier.wait(timeout=3)
                    with fixture.requests_seen:
                        fixture.request_count += 1
                        fixture.requests_seen.notify_all()
                return body

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.httpd.daemon_threads = True
        self.http_thread = threading.Thread(
            target=lambda: self.httpd.serve_forever(poll_interval=0.01), daemon=True)
        self.http_thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.provider_release.set()
        if self.request_barrier is not None:
            self.request_barrier.abort()
        self.httpd.shutdown()
        self.httpd.server_close()
        with self.fixture_lock:
            futures = list(self.fixture_futures)
            threads = list(self.fixture_threads)
        for future in futures:
            if not future.done():
                try:
                    future.set_exception(RuntimeError("Speech HTTP fixture stopped"))
                except InvalidStateError:
                    pass
        for thread in threads:
            thread.join(timeout=3)
        self.assertFalse(any(thread.is_alive() for thread in threads), "Fixture HTTP handlers did not stop")
        self.http_thread.join(timeout=3)
        self.assertFalse(self.http_thread.is_alive(), "Fixture HTTP server did not stop")

    def generate_speech(self, text, provider, voice, env, model=None):
        with self.calls_lock:
            self.calls.append({"text": text, "provider": provider, "voice": voice, "model": model})
        self.provider_entered.set()
        if not self.provider_release.wait(timeout=10):
            raise AssertionError("Fixture provider was not released")
        return copy.deepcopy(SAMPLE)

    def request(self, body):
        connection = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=5)
        try:
            connection.request("POST", "/api/speech", json.dumps(body).encode("utf-8"),
                               {"Content-Type": "application/json", "Connection": "close"})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    @staticmethod
    def payload(request_id="reply-1", **changes):
        return {"client_protocol": 2, "purpose": "reply", "request_id": request_id,
                "text": "A saved fixture reply.", "provider": "elevenlabs",
                "voice": "fixture_voice", "model": "eleven_flash_v2_5", **changes}

    def assert_audio(self, response):
        status, body = response
        self.assertEqual(status, 200, body)
        self.assertEqual(base64.b64decode(body["audio_base64"], validate=True), SAMPLE_WAV)
        self.assertEqual(body["events"], SAMPLE["events"])

    def test_obsolete_tab_and_current_tab_generate_one_clip(self):
        obsolete = {key: value for key, value in self.payload().items()
                    if key not in {"client_protocol", "purpose", "request_id"}}
        old_response = self.request(obsolete)
        current_response = self.request(self.payload())
        observed = {"obsolete_status": old_response[0], "current_status": current_response[0],
                    "provider_calls": len(self.calls)}
        print("obsolete_and_current: " + json.dumps(observed), flush=True)
        self.assertEqual(observed, {"obsolete_status": 409, "current_status": 200,
                                    "provider_calls": 1})
        self.assertEqual(old_response[1].get("code"), "client_reload_required")
        self.assert_audio(current_response)

    def test_protocol_and_request_identity_are_required_before_generation(self):
        invalid = [
            {"client_protocol": 1}, {"client_protocol": "2"}, {"client_protocol": None},
            {"client_protocol": []}, {"purpose": "unknown"}, {"purpose": ""},
            {"purpose": None}, {"purpose": []}, {"purpose": {}},
            {"request_id": ""}, {"request_id": " "}, {"request_id": "x" * 101},
            {"request_id": None}, {"request_id": []}, {"request_id": 2},
        ]
        expected = {"client_protocol": (409, "client_reload_required"),
                    "purpose": (400, "invalid_purpose"), "request_id": (400, "invalid_request_id")}
        for change in invalid:
            with self.subTest(change=change):
                status, body = self.request(self.payload(**change))
                expected_status, expected_code = expected[next(iter(change))]
                self.assertEqual(status, expected_status, body)
                self.assertEqual(body.get("code"), expected_code)
        self.assertEqual(len(self.calls), 0)

    def test_concurrent_retry_and_later_retry_reuse_the_same_clip(self):
        payload = self.payload("concurrent-reply")
        self.barrier_request_id = payload["request_id"]
        self.request_barrier = threading.Barrier(2)
        self.provider_release.clear()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.request, payload) for _ in range(2)]
            try:
                self.assertTrue(self.provider_entered.wait(timeout=3), "Provider did not start")
                with self.requests_seen:
                    self.assertTrue(self.requests_seen.wait_for(lambda: self.request_count == 2, timeout=3),
                                    "Both HTTP requests must arrive while generation is blocked")
                self.assertTrue(self.duplicate_wait_entered.wait(timeout=3),
                                "Retry did not wait for the active generation")
                self.assertEqual(len(self.calls), 1, "Retry reached the provider while generation was active")
                self.assertFalse(any(future.done() for future in futures))
            finally:
                self.provider_release.set()
            responses = [future.result(timeout=5) for future in futures]
        self.request_barrier = None
        responses.append(self.request(payload))
        for response in responses:
            self.assert_audio(response)
        self.assertEqual(len(self.calls), 1, "Concurrent or later retry generated another clip")
        for _, body in responses[1:]:
            self.assertEqual(body["audio_base64"], responses[0][1]["audio_base64"])
            self.assertEqual(body["events"], responses[0][1]["events"])
        metrics = Path(self.temporary.name, "speech_metrics.jsonl")
        rows = [json.loads(line) for line in metrics.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1, "Cached requests duplicated the provider usage record")

    def test_completed_request_id_rejects_changed_generation_inputs(self):
        original = self.payload("immutable-reply")
        self.assert_audio(self.request(original))
        for change in [{"text": "A different reply."}, {"provider": "deepgram"},
                       {"voice": "another_voice"}, {"model": "eleven_multilingual_v2"}]:
            with self.subTest(change=change):
                status, body = self.request({**original, **change})
                self.assertEqual(status, 409, body)
                self.assertEqual(body.get("code"), "request_id_conflict")
                self.assertEqual(len(self.calls), 1, "Conflicting payload reached the provider")

    def test_pending_request_id_rejects_conflicting_payload(self):
        original = self.payload("pending-reply")
        self.provider_release.clear()
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.request, original)
            try:
                self.assertTrue(self.provider_entered.wait(timeout=3), "Provider did not start")
                status, body = self.request({**original, "text": "A different pending reply."})
                self.assertEqual(status, 409, body)
                self.assertEqual(body.get("code"), "request_id_conflict")
                self.assertEqual(len(self.calls), 1)
            finally:
                self.provider_release.set()
            self.assert_audio(pending.result(timeout=5))

    def test_new_manual_request_and_preview_are_allowed(self):
        self.assert_audio(self.request(self.payload("reply-source")))
        self.assert_audio(self.request(self.payload("manual-replay", purpose="manual")))
        self.assertEqual(len(self.calls), 2, "A deliberate replay with a new ID must generate")
        self.assert_audio(self.request(self.payload("voice-preview", purpose="preview")))
        self.assertEqual(len(self.calls), 3)

    def test_entry_eviction_rejects_old_id_without_generating_again(self):
        self.app.speech_cache = server.SpeechCache(max_entries=1)
        first = self.payload("evicted-reply")
        latest = self.payload("retained-reply")
        self.assert_audio(self.request(first))
        self.assert_audio(self.request(latest))
        status, body = self.request(first)
        self.assertEqual(status, 410, body)
        self.assert_audio(self.request(latest))
        self.assertEqual(len(self.calls), 2, "An evicted reply ID regenerated paid speech")

    def test_expired_audio_rejects_old_id_without_generating_again(self):
        self.app.speech_cache = server.SpeechCache(ttl_s=0)
        payload = self.payload("expired-reply")
        self.assert_audio(self.request(payload))
        status, body = self.request(payload)
        self.assertEqual(status, 410, body)
        self.assertEqual(len(self.calls), 1, "An expired reply ID regenerated paid speech")

    def test_audio_over_cache_byte_limit_is_not_generated_twice(self):
        self.app.speech_cache = server.SpeechCache(max_bytes=1)
        payload = self.payload("uncached-large-reply")
        self.assert_audio(self.request(payload))
        status, body = self.request(payload)
        self.assertEqual(status, 410, body)
        self.assertEqual(len(self.calls), 1, "An uncached reply ID regenerated paid speech")

    def test_restart_remembers_generated_ids_without_retaining_audio(self):
        payload = self.payload("reply-before-restart")
        self.assert_audio(self.request(payload))
        args = self.app.args
        client = server.StubClient(args.model, args.thinking, args.soul, args.run_dir)
        restarted = server.App(args, "chat", client, None)
        self.httpd.RequestHandlerClass.app = restarted
        status, body = self.request(payload)
        self.assertEqual(status, 410, body)
        self.assertEqual(len(self.calls), 1, "Restart replay generated the same reply again")
        self.assert_audio(self.request(self.payload("manual-after-restart", purpose="manual")))
        self.assertEqual(len(self.calls), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
