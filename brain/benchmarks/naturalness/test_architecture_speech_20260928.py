import asyncio
import base64
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from benchmarks.naturalness import architecture_speech_20260928 as bench


class FakeSocket:
    def __init__(self):
        self.sent = []

    async def send_json(self, value):
        self.sent.append(value)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.now += max(0.0, seconds)


class ArchitectureSpeechBenchTests(unittest.TestCase):
    def test_cached_pcm_replays_all_bytes_at_twenty_ms(self):
        pcm, manifest = bench.load_cached_wav(
            bench.FIXTURE_DIR / "audio" / "audio_backchannel_yes-1.wav")
        socket, clock = FakeSocket(), FakeClock()
        result = asyncio.run(bench.send_cached_pcm(socket, pcm, clock=clock, sleep=clock.sleep))
        self.assertEqual(manifest["duration_ms"], 520.0)
        self.assertEqual(result["packet_count"], 26)
        self.assertEqual(result["packet_ms"], 20)
        self.assertEqual(sum(len(base64.b64decode(item["pcm"])) for item in socket.sent), len(pcm))
        self.assertLess(result["schedule_lateness_ms_max"], 0.1)

    def test_transcript_done_without_audio_does_not_satisfy_drain(self):
        assistant_done = {"type": "transcript_done", "role": "assistant"}
        self.assertFalse(bench._normal_turn_drained(assistant_done, [], [], False))
        audio = [{"type": "audio", "epoch": 0, "seq": 2}]
        self.assertFalse(bench._normal_turn_drained(assistant_done, audio, [], False))
        self.assertFalse(bench._normal_turn_drained(
            assistant_done, audio, [{"epoch": 0, "sequence": 2}], True))
        self.assertTrue(bench._normal_turn_drained(
            assistant_done, audio, [{"epoch": 0, "sequence": 2}], False))
        self.assertFalse(bench._tts_sequences_finished(
            audio + [{"type": "audio", "epoch": 1, "seq": 3}],
            [{"epoch": 0, "sequence": 2}]))

    def test_audio_reset_clears_simulated_playback_state(self):
        async def run():
            socket, events = FakeSocket(), []
            playback = bench.SoftwarePlaybackClock(socket, events, 200)
            await playback.observe({"type": "audio", "sample_rate": 24000,
                                    "pcm_bytes": 480, "epoch": 0}, time.perf_counter())
            self.assertTrue(playback.active)
            self.assertEqual(socket.sent[-1], {"type": "playback_state", "playing": True})
            await playback.observe({"type": "audio_reset", "epoch": 1}, time.perf_counter())
            self.assertFalse(playback.active)
            self.assertEqual(socket.sent[-1], {"type": "playback_state", "playing": False})
            await playback.close()
        asyncio.run(run())

    def test_correlated_metrics_exclude_seed_and_keep_early_signed_latency(self):
        events = [
            {"type": "transcript_delta", "role": "assistant", "text": "seed",
             "benchmark_turn_id": "seed", "benchmark_parent_user_turn_id": None, "t_ms": 50},
            {"type": "transcript_done", "role": "user", "benchmark_turn_id": "u1", "t_ms": 100},
            {"type": "transcript_delta", "role": "assistant", "text": "answer",
             "benchmark_turn_id": "a1", "benchmark_parent_user_turn_id": "u1", "t_ms": 80},
            {"type": "audio", "benchmark_turn_id": "a1", "benchmark_parent_user_turn_id": "u1",
             "epoch": 0, "seq": 3, "t_ms": 90},
            {"type": "latency", "tts": {"epoch": 0, "sequence": 3}, "t_ms": 110},
        ]
        metrics = bench._correlated_metrics(events, "u1", 0, 100)
        self.assertEqual(metrics["events_ms"]["first_assistant_text"], 80)
        self.assertEqual(metrics["signed_durations_from_input_last_sample_ms"]["first_assistant_text"], -20)
        self.assertEqual(metrics["events_ms"]["first_tts_audio_packet"], 90)
        self.assertEqual(metrics["events_ms"]["tts_complete"], 110)


if __name__ == "__main__":
    unittest.main()
