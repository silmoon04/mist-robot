"""Signal tests use generated local arrays; no network or live playback."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio_capture_audit import TIMING_KIND, align_browser, decode_audio, media_clock_audit, packet_gaps, recording_anchor, waveform_metrics


class CaptureAuditTests(unittest.TestCase):
    def browser(self):
        return {"timing_kind": TIMING_KIND, "performance_origin_ms": 500, "performance_time_origin_ms": 1000,
                "observation_end_ms": 2000, "recording": [{"kind": "audio", "start_ms": 100, "end_ms": 1100}],
                "events": [{"type": "recording_started", "kind": "audio", "t_ms": 100.1}]}

    def test_quiet_gaps_exclude_edges_and_strict_thresholds(self):
        signal = np.r_[np.zeros(200), np.ones(200)*.1, np.zeros(300), np.ones(200)*.1,
                       np.zeros(710), np.ones(200)*.1, np.zeros(400)]
        report = waveform_metrics(signal, 1000)
        self.assertEqual(report["non_silent_duration_ms"], 600)
        self.assertEqual(report["leading_quiet_ms"], 200)
        self.assertEqual(report["trailing_quiet_ms"], 400)
        self.assertEqual([g["duration_ms"] for g in report["internal_quiet_gaps"]], [300, 710])
        self.assertEqual(len(report["internal_quiet_over_300_ms"]), 1)
        self.assertEqual(len(report["internal_quiet_over_700_ms"]), 1)

    def test_silence_is_not_a_failure_or_internal_gap(self):
        report = waveform_metrics(np.zeros(100), 1000)
        self.assertEqual(report["non_silent_duration_ms"], 0)
        self.assertEqual(report["internal_quiet_gaps"], [])
        self.assertIsNone(report["rms_dbfs"])

    def test_partial_last_window_and_clip_indicators(self):
        report = waveform_metrics(np.array([0]*10 + [1, -1, 1.05, .2, .3]), 1000)
        self.assertEqual(report["duration_ms"], 15)
        self.assertEqual(report["non_silent_duration_ms"], 5)
        self.assertEqual(report["near_full_scale_sample_count"], 3)
        self.assertEqual(report["over_full_scale_sample_count"], 1)
        self.assertEqual(report["longest_near_full_scale_run_ms"], 3)

    def test_no_alignment_without_clock_contract(self):
        data = self.browser()
        data.pop("performance_time_origin_ms")
        self.assertEqual(recording_anchor(data), (None, "missing_browser_performance_origin"))
        result = align_browser(data, waveform_metrics(np.ones(1000)*.1, 1000), {"decoded_first_pts_ms": 0})
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["events"], [])

    def test_alignment_uses_recorder_start_and_excludes_cleanup(self):
        data = self.browser()
        data["events"] += [{"type": "input_started", "t_ms": 600}, {"type": "audio_reset", "t_ms": 2100}]
        result = align_browser(data, waveform_metrics(np.ones(1000)*.1, 1000), {"decoded_first_pts_ms": 5, "media_duration_ms": 1000})
        self.assertEqual(result["status"], "software_estimate_uncalibrated")
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["recording_offset_ms"], 495)
        self.assertEqual(result["events"][0]["active_ms_in_next_250_ms"], 250)

    def test_inconsistent_or_duplicate_start_is_not_aligned(self):
        data = self.browser()
        data["events"][0]["t_ms"] = 150
        self.assertEqual(recording_anchor(data)[1], "inconsistent_recorder_start")
        data["events"] *= 2
        self.assertEqual(recording_anchor(data)[1], "missing_or_ambiguous_recorder_start")

    def test_packet_gaps_are_separate_by_epoch(self):
        data = self.browser()
        data["events"] += [{"type": "audio", "t_ms": 200, "epoch": 1},
                           {"type": "audio", "t_ms": 600, "epoch": 1},
                           {"type": "audio", "t_ms": 1500, "epoch": 2},
                           {"type": "audio", "t_ms": 2100, "epoch": 2}]
        report = packet_gaps(data)
        self.assertEqual(report["packet_count"], 3)
        self.assertEqual(report["max_interarrival_ms"], 400)
        self.assertEqual(len(report["over_300_ms"]), 1)
        self.assertEqual(report["over_700_ms"], [])

    def test_decode_pcm_fixture_preserves_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp)/"source.wav", Path(temp)/"decoded.wav"
            with wave.open(str(source), "wb") as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(np.full(16000*2, 16384, dtype="<i2").tobytes())
            samples, rate, details = decode_audio(source, output)
            self.assertEqual(rate, 16000)
            self.assertEqual(len(samples), 16000)
            self.assertAlmostEqual(float(samples.max()), .5, places=5)
            self.assertEqual(details["timestamp_gaps"], [])
            with wave.open(str(output)) as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getnframes(), 16000)

    def test_omitted_leading_silence_must_not_create_false_alignment(self):
        data = self.browser()
        data["recording"][0]["end_ms"] = 11100
        data["events"].append({"type": "audio_reset", "t_ms": 600})
        result = align_browser(data, waveform_metrics(np.ones(1000)*.1, 1000),
                               {"decoded_first_pts_ms": 0, "media_duration_ms": 1000})
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "media_duration_does_not_cover_recorder_interval")
        self.assertEqual(result["events"], [])
        self.assertEqual(result["unaccounted_recording_time_ms"], 10000)

    def test_stream_clock_audit_rejects_duration_mismatch_without_av_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "browser-output.webm"
            # PyAV detects the container bytes; a local WAV suffices to test the
            # stream timestamp checks without invoking a WebM encoder.
            with wave.open(str(source), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(np.zeros(16000, dtype="<i2").tobytes())
            data = self.browser()
            report = media_clock_audit(Path(temp), data)
            self.assertEqual(report["streams"][0]["browser_clock_alignment"], "approximately_consistent")
            self.assertEqual(report["av_sync_status"], "unverified")
            self.assertFalse(report["default_auto_av_sync_claim"])
            data["recording"][0]["end_ms"] = 11100
            report = media_clock_audit(Path(temp), data)
            self.assertEqual(report["streams"][0]["browser_clock_alignment"], "unverified")
            self.assertIn("media_end_differs_from_recorder_interval", report["streams"][0]["clock_cautions"])


if __name__ == "__main__":
    unittest.main()
