"""Fake-engine loopback tests; no provider connection or microphone access."""
import json
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path

from websockets.exceptions import ConnectionClosed, InvalidStatus
from websockets.sync.client import connect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui.stt_proxy import create_proxy_server

ORIGIN = "http://127.0.0.1:8779"
SECRET = "private-fixture-provider-key"


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.callbacks = []
        self.active = None
        self.closed = False
        self.cancel_count = 0
        self.hold_final = False
        self.final_entered = threading.Event()
        self.release_final = threading.Event()
        self.fail_begin = False
        self.final_workers = 0
        self.max_final_workers = 0

    def begin_utterance(self, sample_rate, *, on_event=None):
        if self.fail_begin:
            raise RuntimeError(SECRET)
        self.calls.append(("begin", sample_rate))
        self.callbacks.append(on_event)
        self.active = {"rate": sample_rate, "pcm": [], "index": len(self.callbacks)}
        return str(uuid.uuid4())

    def send_pcm(self, pcm):
        self.calls.append(("pcm", pcm))
        self.active["pcm"].append(pcm)
        self.callbacks[-1]({"type": "stt_partial", "text": "Partial words", "utterance_id": "provider-only-id"})

    def finalize(self, timeout=8):
        active = self.active
        self.final_workers += 1
        self.max_final_workers = max(self.max_final_workers, self.final_workers)
        self.final_entered.set()
        if self.hold_final:
            self.release_final.wait(timeout=2)
        self.final_workers -= 1
        seconds = sum(map(len, active["pcm"])) / (2 * active["rate"])
        return {"final": True, "transcript": f"Final utterance {active['index']}", "confidence": 0.9,
                "audio_seconds": seconds, "provider_processed_audio_seconds": seconds,
                "timings": {"connection_reused": active["index"] > 1, "recognition_total_s": 0.01, "headers": SECRET},
                "headers": SECRET, "provider_events": [{"secret": SECRET}]}

    def cancel(self):
        self.cancel_count += 1
        self.active = None

    def close(self):
        self.closed = True
        self.cancel()
        self.release_final.set()


class STTProxyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mist-stt-proxy-test-")
        self.addCleanup(self.temp.cleanup)
        self.metrics = Path(self.temp.name) / "metrics.jsonl"
        self.engines = []
        self.proxies = []

    def proxy(self, **limits):
        def factory():
            engine = FakeEngine()
            self.engines.append(engine)
            return engine
        proxy = create_proxy_server(port=0, origins=(ORIGIN,), engine_factory=factory,
                                    metrics_path=self.metrics, **limits)
        thread = threading.Thread(target=proxy.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(proxy.shutdown)
        self.proxies.append(proxy)
        return proxy

    def browser(self, proxy, origin=ORIGIN):
        browser = connect(f"ws://127.0.0.1:{proxy.port}/stt", origin=origin, compression=None, close_timeout=0.2)
        self.addCleanup(browser.close)
        return browser

    def start(self, browser, utterance_id=None):
        utterance_id = utterance_id or str(uuid.uuid4())
        browser.send(json.dumps({"type": "start", "utterance_id": utterance_id, "sample_rate": 16000}))
        started = json.loads(browser.recv(timeout=2))
        self.assertEqual(started["type"], "started")
        self.assertEqual(started["utterance_id"], utterance_id)
        return utterance_id

    def test_invalid_or_missing_origin_is_rejected_before_engine_creation(self):
        proxy = self.proxy()
        for origin in ("http://127.0.0.1:8776", "https://untrusted.invalid", None):
            with self.assertRaises(InvalidStatus):
                self.browser(proxy, origin)
        self.assertEqual(self.engines, [])

    def test_one_browser_limit_and_reconnect_after_disconnect(self):
        proxy = self.proxy()
        browser = self.browser(proxy)
        self.start(browser)
        with self.assertRaises(InvalidStatus):
            self.browser(proxy)
        browser.close()
        deadline = time.monotonic() + 2
        while proxy.gate.locked() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(self.engines[0].closed)
        self.start(self.browser(proxy))
        self.assertEqual(len(self.engines), 2)

    def test_pcm_order_final_fields_and_warm_engine_reuse(self):
        browser = self.browser(self.proxy())
        all_events = []
        for turn in range(2):
            utterance_id = self.start(browser)
            for pcm in (b"\x01\0" * 20, b"\x02\0" * 30):
                browser.send(pcm)
                partial = json.loads(browser.recv(timeout=2))
                self.assertEqual(partial["type"], "partial")
                self.assertEqual(partial["utterance_id"], utterance_id)
                all_events.append(partial)
            browser.send(json.dumps({"type": "end", "utterance_id": utterance_id}))
            final = json.loads(browser.recv(timeout=2))
            self.assertEqual(final["type"], "final")
            self.assertEqual(final["utterance_id"], utterance_id)
            self.assertEqual(final["audio_seconds"], 50 / 16000)
            self.assertEqual(final["provider_processed_audio_seconds"], 50 / 16000)
            self.assertEqual(final["timings"]["connection_reused"], turn > 0)
            all_events.append(final)
        self.assertEqual(len(self.engines), 1)
        self.assertEqual([value for name, value in self.engines[0].calls if name == "pcm"],
                         [b"\x01\0" * 20, b"\x02\0" * 30] * 2)
        self.assertNotIn(SECRET, json.dumps(all_events))
        deadline = time.monotonic() + 1
        while (not self.metrics.exists() or len(self.metrics.read_text().splitlines()) < 2) and time.monotonic() < deadline:
            time.sleep(0.01)
        metrics = self.metrics.read_text()
        self.assertNotIn(SECRET, metrics)
        self.assertNotIn("Final utterance", metrics)
        self.assertNotIn("Partial words", metrics)

    def test_cancel_suppresses_late_callback_and_final_before_queued_start(self):
        browser = self.browser(self.proxy())
        old_id = self.start(browser)
        engine = self.engines[0]
        engine.hold_final = True
        browser.send(b"\0\0" * 10)
        browser.recv(timeout=2)
        browser.send(json.dumps({"type": "end", "utterance_id": old_id}))
        self.assertTrue(engine.final_entered.wait(1))
        browser.send(json.dumps({"type": "cancel", "utterance_id": old_id}))
        self.assertEqual(json.loads(browser.recv(timeout=1))["type"], "cancelled")
        new_id = str(uuid.uuid4())
        browser.send(json.dumps({"type": "start", "utterance_id": new_id, "sample_rate": 16000}))
        engine.callbacks[0]({"text": "stale private words"})
        engine.release_final.set()
        started = json.loads(browser.recv(timeout=2))
        self.assertEqual(started["type"], "started")
        self.assertEqual(started["utterance_id"], new_id)
        engine.callbacks[0]({"text": "stale private words again"})
        browser.send(b"\0\0" * 15)
        self.assertEqual(json.loads(browser.recv(timeout=2))["utterance_id"], new_id)
        browser.send(json.dumps({"type": "end", "utterance_id": new_id}))
        final = json.loads(browser.recv(timeout=2))
        self.assertEqual(final["type"], "final")
        self.assertEqual(final["utterance_id"], new_id)
        self.assertEqual(engine.max_final_workers, 1)

    def test_errors_never_return_provider_exception_or_key(self):
        browser = self.browser(self.proxy())
        self.start(browser)
        engine = self.engines[0]
        active_id = self.proxies[-1].session.active["id"]
        browser.send(json.dumps({"type": "cancel", "utterance_id": active_id}))
        browser.recv(timeout=2)
        engine.fail_begin = True
        browser.send(json.dumps({"type": "start", "utterance_id": str(uuid.uuid4()), "sample_rate": 16000}))
        event = browser.recv(timeout=2)
        self.assertEqual(json.loads(event)["type"], "error")
        self.assertNotIn(SECRET, event)
        self.assertNotIn(SECRET, self.metrics.read_text())

    def test_idle_utterance_and_session_have_wall_clock_limits(self):
        browser = self.browser(self.proxy(max_utterance_seconds=0.15, max_session_seconds=0.4))
        self.start(browser)
        self.assertIn("utterance", json.loads(browser.recv(timeout=1))["message"])
        self.assertGreater(self.engines[0].cancel_count, 0)
        self.assertIn("session", json.loads(browser.recv(timeout=1))["message"])
        with self.assertRaises(ConnectionClosed):
            browser.recv(timeout=1)

    def test_invalid_controls_pcm_and_oversized_messages_do_not_reach_engine(self):
        proxy = self.proxy()
        browser = self.browser(proxy)
        for request in ({"type": [], "utterance_id": str(uuid.uuid4())},
                        {"type": "start", "utterance_id": "not-a-uuid", "sample_rate": 16000},
                        {"type": "start", "utterance_id": str(uuid.uuid4()), "sample_rate": True}):
            browser.send(json.dumps(request))
            self.assertEqual(json.loads(browser.recv(timeout=1))["type"], "error")
        self.assertEqual(self.engines[0].calls, [])
        self.start(browser)
        browser.send(b"\0")
        self.assertEqual(json.loads(browser.recv(timeout=1))["type"], "error")
        self.assertFalse(any(name == "pcm" for name, value in self.engines[0].calls))
        self.start(browser)
        browser.send(b"\0" * 192_002)
        with self.assertRaises(ConnectionClosed) as caught:
            browser.recv(timeout=1)
        self.assertEqual(caught.exception.rcvd.code, 1009)
        self.assertFalse(any(name == "pcm" for name, value in self.engines[0].calls))


if __name__ == "__main__":
    unittest.main()
