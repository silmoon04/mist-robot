"""Offline fixtures and fake sockets only. No network or speech provider calls."""
import asyncio
import base64
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio_replay import Capture, ReplayFailure, frames, load_annotations, load_fixture, paced_upload, preflight, redact, run


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def wav(self, rate=16000, channels=1, width=2, count=640):
        path = self.root / "fixture.wav"
        with wave.open(str(path), "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(width)
            out.setframerate(rate)
            out.writeframes(bytes(count * channels * width))
        return path

    def test_format_rejection(self):
        self.assertEqual(len(load_fixture(self.wav())), 1280)
        for kwargs in ({"rate": 24000}, {"channels": 2}, {"width": 1}, {"count": 0}):
            with self.assertRaises(ReplayFailure):
                load_fixture(self.wav(**kwargs))

    def test_annotations(self):
        path = self.root / "annotations.json"
        good = [{"turn_id": "u1", "start_ms": 0, "end_ms": 30}]
        path.write_text(json.dumps(good))
        self.assertEqual(load_annotations(path, 40), good)
        for rows in ([dict(good[0], end_ms=41)], good * 2, [dict(good[0], start_ms=True)], []):
            path.write_text(json.dumps(rows))
            with self.assertRaises(ReplayFailure):
                load_annotations(path, 40)

    def test_pacing_and_padding(self):
        schedule = list(frames(bytes(642)))
        self.assertEqual([item[1] for item in schedule], [.02, .04])
        self.assertEqual([item[3] for item in schedule], [320, 1])
        self.assertTrue(all(len(item[2]) == 640 for item in schedule))

    def test_concurrent_compatible_upload(self):
        now, sent = [10.0], []
        cap = Capture(self.root, "case", [{"turn_id": "u1", "start_ms": 0, "end_ms": 25}], clock=lambda: now[0])
        class Socket:
            async def send_json(self, packet):
                sent.append(packet)
        async def sleep(delay):
            now[0] += delay
        asyncio.run(paced_upload(Socket(), bytes(1280), cap, sleep=sleep))
        self.assertEqual([p["type"] for p in sent], ["mic", "mic"])
        self.assertEqual(len(base64.b64decode(sent[0]["pcm"])), 640)
        self.assertAlmostEqual(cap.sent[-1]["sent_t_ms"], 40)
        names = [e["event"] for e in cap.events]
        self.assertEqual(names, ["fixture_started", "user_audio_start", "user_audio_end", "fixture_finished"])
        self.assertTrue(all(abs(p["schedule_lateness_ms"]) < 1e-6 for p in cap.sent))

    def test_unknown_correlation_and_no_false_playback(self):
        cap = Capture(self.root, "case", [])
        cap.server_event({"type": "audio", "epoch": 4, "sample_rate": 24000, "pcm": "AAAAAA=="})
        cap.server_event({"type": "transcript_done", "role": "user", "text": "hello"})
        self.assertTrue(all(e["turn_id"] == "uncorrelated_server" for e in cap.events))
        self.assertNotIn("pcm", cap.raw[0]["payload"])
        self.assertEqual(cap.events[0]["event"], "server_audio_packet_received")
        files = cap.write_audio()
        with wave.open(str(self.root / files[0]["path"])) as wav:
            self.assertEqual(wav.getframerate(), 24000)
            self.assertEqual(wav.getnframes(), 2)
        self.assertFalse(any(e["event"] == "playback_started" for e in cap.events))

    def test_output_epoch_format_and_secret(self):
        cap = Capture(self.root, "case", [])
        for event in ({"type": "audio", "pcm": "AAAA"}, {"type": "audio", "epoch": 0, "sample_rate": 24000, "pcm": "not-base64!"}):
            with self.assertRaises(ReplayFailure):
                cap.server_event(event)
        self.assertEqual(redact({"message": ["token ABC"]}, "ABC"), {"message": ["token [REDACTED]"]})

    def test_missing_credentials_saves_failed_envelope_without_network(self):
        annotations = self.root / "annotations.json"
        annotations.write_text(json.dumps([{"turn_id": "u1", "start_ms": 0, "end_ms": 20}]))
        suite = self.root / "cases.json"
        suite.write_text(json.dumps({"cases": [{"id": "case", "category": "audio", "split": "dev"}]}))
        args = SimpleNamespace(fixture=self.wav(), annotations=annotations, suite=suite,
                               case_id="case", base_url="http://127.0.0.1:8790", output=self.root / "run",
                               pair_code_env="MIST_PAIR_CODE", repeat=1, tail_seconds=1)
        with patch.dict("os.environ", {}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(asyncio.run(run(args)), 1)
        result = json.loads((args.output / "run.json").read_text())
        self.assertEqual(result["samples"][0]["errors"], [{"code": "pair_code_env_missing"}])
        self.assertEqual(result["manifest"]["measurement_scope"], "server_transport_only")
        from metrics import summarize_run
        self.assertIsInstance(summarize_run(result), dict)

    def test_preflight_rejects_production_before_pairing(self):
        calls = []
        class Response:
            status = 200
            config = {}
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def json(self):
                return self.config
        response = Response()
        class Session:
            def get(self, url, headers):
                calls.append(url)
                return response
            def post(self, *args, **kwargs):
                raise AssertionError("Pairing must not happen during preflight")
        for config in ({}, {"fixtures_enabled": False}, {"fixtures_enabled": 1}):
            response.config = config
            with self.assertRaisesRegex(ReplayFailure, "fixtures_not_enabled"):
                asyncio.run(preflight(Session(), "http://127.0.0.1:8796", {}))
        response.config = {"fixtures_enabled": True}
        asyncio.run(preflight(Session(), "http://127.0.0.1:8796", {}))
        self.assertTrue(all(url.endswith("/config") for url in calls))


if __name__ == "__main__":
    unittest.main()
