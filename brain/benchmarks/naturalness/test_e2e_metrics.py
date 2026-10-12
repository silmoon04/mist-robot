"""Protect browser measurements from teardown, seed and clock attribution errors."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e2e_metrics import analyze_browser, analyze_case, build_report, summarize_captures


def event(event_type, time, **fields):
    return {"type": event_type, "t_ms": time, **fields}


def capture():
    return {
        "case_id": "simple", "status": "complete", "timing_kind": "software_output_estimate_not_acoustic",
        "fixture": {"id": "simple", "steps": [{"type": "audio", "role": "user"}], "speech_fixture": "synthetic"},
        "inputs": [{"step": 0, "start_ms": 100, "end_ms": 500, "playback_active_at_start": False,
                    "packets": [[100, 640, 0], [120, 640, 2]]}],
        "events": [
            event("input_started", 100), event("input_ended", 500),
            event("transcript_done", 600, role="user", text="Hello"),
            event("transcript_delta", 700, role="assistant", text="Hi"),
            event("audio", 800, pcm_bytes=4800), event("playback_started", 900),
            event("capture_boundary", 2000),
        ],
        "frames": [{"t_ms": 100 + index*66.667, "sample_late_ms": 0, "audio_active": False,
                    "queue_ms": 0, "face": {"drawnError": None}} for index in range(20)],
        "observation_end_ms": 2000, "remaining": {"queue_ms": 0, "playback_active": False},
        "environment": {"face_fps": 15}, "recording": [], "errors": [],
    }


class BrowserLatencyTests(unittest.TestCase):
    def test_first_response_uses_input_end_and_one_clock(self):
        result = analyze_browser(capture())
        self.assertTrue(result["first_response"]["eligible"])
        self.assertEqual(result["first_response"]["latency_ms"], {
            "user_final_transcript_ms": 100, "assistant_first_text_ms": 200,
            "first_audio_received_ms": 300, "first_playback_ms": 400,
        })
        self.assertIsNone(result["first_response"]["first_useful_audio_ms"])
        self.assertIsNone(result["human_quality_rating"])

    def test_seeded_case_cannot_use_next_audio_packet_as_new_reply(self):
        data = capture()
        data["fixture"]["steps"].insert(0, {"type": "seed_text", "text": "Read a long sentence"})
        result = analyze_browser(data)
        self.assertFalse(result["first_response"]["eligible"])
        self.assertIn("seeded_assistant_output", result["first_response"]["exclusion_reasons"])
        self.assertTrue(all(value is None for value in result["first_response"]["latency_ms"].values()))

    def test_context_setup_event_also_excludes_seeded_case(self):
        data = capture()
        data["events"].append(event("context_setup", 50, kind="seed_text"))
        self.assertFalse(analyze_browser(data)["first_response"]["eligible"])

    def test_input_overlap_and_missing_overlap_are_explicit(self):
        for overlap in (True, None):
            data = capture()
            data["inputs"][0]["playback_active_at_start"] = overlap
            data["frames"] = []
            result = analyze_browser(data)
            self.assertFalse(result["first_response"]["eligible"])
            self.assertIs(result["inputs"][0]["observed_overlap"], overlap)

    def test_overlap_during_input_caught_by_frame(self):
        data = capture()
        data["frames"][2]["audio_active"] = True
        result = analyze_browser(data)
        self.assertFalse(result["first_response"]["eligible"])
        self.assertTrue(result["inputs"][0]["observed_overlap"])

    def test_multi_input_case_is_not_assigned_nearest_packet(self):
        data = capture()
        data["inputs"].append({"step": 1, "start_ms": 1200, "end_ms": 1500, "playback_active_at_start": False})
        self.assertFalse(analyze_browser(data)["first_response"]["eligible"])

    def test_output_before_input_is_not_reused(self):
        data = capture()
        data["events"].append(event("audio", 50, pcm_bytes=4800))
        result = analyze_browser(data)
        self.assertIn("assistant_output_predates_input", result["first_response"]["exclusion_reasons"])

    def test_different_clock_cannot_supply_latency_endpoint(self):
        data = capture()
        data["events"][4]["clock_id"] = "server"
        result = analyze_browser(data)
        self.assertIsNone(result["first_response"]["latency_ms"]["first_audio_received_ms"])
        self.assertTrue(any(issue.startswith("event_clock_mismatch") for issue in result["issues"]))

    def test_input_clock_mismatch_excludes_case(self):
        data = capture()
        data["inputs"][0]["clock_id"] = "server"
        self.assertFalse(analyze_browser(data)["first_response"]["eligible"])

    def test_final_transcript_before_input_end_remains_signed(self):
        data = capture()
        data["events"][2]["t_ms"] = 450
        result = analyze_browser(data)
        self.assertEqual(result["first_response"]["latency_ms"]["user_final_transcript_ms"], -50)

    def test_no_audio_data_does_not_measure_empty_audio_event(self):
        data = capture()
        data["events"][4]["pcm_bytes"] = 0
        self.assertIsNone(analyze_browser(data)["first_response"]["latency_ms"]["first_audio_received_ms"])

    def test_capture_boundary_prevents_late_response_becoming_measurement(self):
        data = capture()
        data["events"][4]["t_ms"] = 2100
        self.assertIsNone(analyze_browser(data)["first_response"]["latency_ms"]["first_audio_received_ms"])

    def test_startup_is_separate_from_reply_and_retains_server_source(self):
        data = capture()
        data["events"] += [event("socket_open", 10), event("ready", 90, startup={"server_ms": 40}),
                           event("face_ready", 20, ready=True)]
        result = analyze_browser(data)
        self.assertEqual(result["startup"]["ready_after_capture_start_ms"], 90)
        self.assertEqual(result["startup"]["ready_after_socket_open_ms"], 80)
        self.assertEqual(result["startup"]["server_reported_breakdown"], {"server_ms": 40})
        self.assertEqual(result["first_response"]["latency_ms"]["first_playback_ms"], 400)
        summary = summarize_captures([result])
        self.assertEqual(summary["startup_ms"]["ready_after_capture_start_ms"]["median"], 90)

    def test_split_input_cannot_join_early_text_to_later_response_audio(self):
        data = capture()
        data["events"] += [
            event("transcript_done", 250, role="user", text="The green bracket"),
            event("transcript_delta", 260, role="assistant", text="Did you mean"),
            event("transcript_done", 350, role="assistant", text="Did you mean the green bracket?"),
            event("audio_reset", 360),
            event("transcript_done", 1100, role="assistant", text="Got it."),
        ]
        result = analyze_browser(data)
        self.assertFalse(result["first_response"]["eligible"])
        self.assertTrue(all(value is None for value in result["first_response"]["latency_ms"].values()))
        self.assertEqual(set(result["first_response"]["exclusion_reasons"]), {
            "multiple_user_final_transcripts", "multiple_assistant_reply_segments",
            "response_cancelled_or_reset", "assistant_text_before_input_end",
        })
        observed = result["inputs"][0]["turn_observations"]
        self.assertEqual(observed["distinct_nonempty_user_final_count"], 2)
        self.assertEqual(observed["assistant_reply_segments"], 2)
        self.assertEqual(observed["mid_input_reset_count"], 1)
        self.assertEqual(observed["first_assistant_text_timestamp_ms"], 260)
        self.assertEqual(observed["premature_first_text_before_input_end_ms"], 240)
        summary = summarize_captures([result, analyze_browser(capture())])
        self.assertEqual(summary["latency_ms"]["first_playback_ms"]["eligible_captures"], 1)
        self.assertEqual(summary["turn_observations"]["single_input_multiple_user_final_windows"], 1)
        self.assertEqual(summary["turn_observations"]["single_input_multiple_reply_windows"], 1)
        self.assertEqual(summary["turn_observations"]["single_input_mid_input_reset_windows"], 1)
        self.assertEqual(summary["turn_observations"]["single_input_premature_text_windows"], 1)

    def test_multiple_user_finals_exclude_even_without_early_reply(self):
        data = capture()
        data["events"].append(event("transcript_done", 550, role="user", text="An earlier segment"))
        result = analyze_browser(data)
        self.assertIn("multiple_user_final_transcripts", result["first_response"]["exclusion_reasons"])
        self.assertIsNone(result["first_response"]["latency_ms"]["first_playback_ms"])

    def test_repeated_identical_user_final_is_counted_but_not_distinct(self):
        data = capture()
        data["events"].append(event("transcript_done", 650, role="user", text="  hello  "))
        result = analyze_browser(data)
        self.assertTrue(result["first_response"]["eligible"])
        self.assertEqual(result["inputs"][0]["turn_observations"]["user_final_transcript_count"], 2)
        self.assertEqual(result["inputs"][0]["turn_observations"]["distinct_nonempty_user_final_count"], 1)

    def test_reset_after_input_end_also_excludes_cancelled_response(self):
        data = capture()
        data["events"].append(event("audio_reset", 1000))
        result = analyze_browser(data)
        self.assertIn("response_cancelled_or_reset", result["first_response"]["exclusion_reasons"])
        self.assertEqual(result["inputs"][0]["turn_observations"]["mid_input_reset_count"], 0)

    def test_stop_command_without_reset_excludes_cancelled_response(self):
        data = capture()
        data["events"].append(event("source_stop_called", 1000, source_id=7))
        result = analyze_browser(data)
        self.assertIn("response_source_stopped", result["first_response"]["exclusion_reasons"])
        self.assertIsNone(result["first_response"]["latency_ms"]["first_playback_ms"])

    def test_early_text_excludes_without_audio_overlap(self):
        data = capture()
        data["events"][3]["t_ms"] = 450
        result = analyze_browser(data)
        self.assertIn("assistant_text_before_input_end", result["first_response"]["exclusion_reasons"])
        self.assertFalse(result["inputs"][0]["observed_overlap"])

    def test_ordinary_one_input_answer_with_many_chunks_remains_eligible(self):
        data = capture()
        data["events"] += [event("transcript_delta", 750, role="assistant", text=" there."),
                           event("transcript_done", 1200, role="assistant", text="Hi there."),
                           event("audio", 1000, pcm_bytes=4800), event("audio", 1100, pcm_bytes=4800)]
        result = analyze_browser(data)
        self.assertTrue(result["first_response"]["eligible"])
        self.assertEqual(result["inputs"][0]["turn_observations"]["assistant_reply_segments"], 1)
        self.assertEqual(result["first_response"]["latency_ms"]["first_playback_ms"], 400)


class InterruptionAndCaptureTests(unittest.TestCase):
    def test_cleanup_stops_do_not_count_as_interruptions(self):
        data = capture()
        data["events"] += [event("source_stop_called", 2001, source_id=1), event("audio_reset", 2001.1)]
        result = analyze_browser(data)
        self.assertEqual(result["inputs"][0]["audio_resets_in_window"], 0)
        self.assertEqual(result["inputs"][0]["source_stop_commands_in_window"], 0)
        self.assertEqual(result["cleanup_event_counts"]["source_stop_called"], 1)

    def test_reset_and_stop_are_commands_not_acoustic_or_correctness_rating(self):
        data = capture()
        data["inputs"][0]["playback_active_at_start"] = True
        data["events"] += [
            event("source_scheduled", 50, source_id=7, estimated_output_start_ms=90, estimated_output_end_ms=1000),
            event("audio_reset", 250), event("source_stop_called", 251, source_id=7),
        ]
        data["frames"] = [{"t_ms": 200, "queue_ms": 800, "audio_active": True, "face": {}}]
        result = analyze_browser(data)
        row = result["inputs"][0]
        self.assertEqual(row["first_reset_after_start_ms"], 150)
        self.assertEqual(row["first_reset_after_end_ms"], -250)
        self.assertEqual(row["first_stop_command_after_start_ms"], 151)
        self.assertEqual(row["resets"][0]["queue_snapshot_age_ms"], 50)
        self.assertTrue(row["resets"][0]["interrupted_queue_observed"])
        self.assertIsNone(row["interruption_correctness"])

    def test_two_inputs_have_disjoint_reset_windows(self):
        data = capture()
        data["inputs"].append({"step": 1, "start_ms": 1000, "end_ms": 1500, "playback_active_at_start": True})
        data["events"] += [event("audio_reset", 1100), event("source_stop_called", 1101, source_id=1)]
        result = analyze_browser(data)
        self.assertEqual(result["inputs"][0]["audio_resets_in_window"], 0)
        self.assertEqual(result["inputs"][1]["audio_resets_in_window"], 1)

    def test_complete_status_does_not_hide_truncated_playback(self):
        data = capture()
        data["remaining"] = {"queue_ms": 500, "playback_active": True}
        result = analyze_browser(data)
        self.assertTrue(result["capture"]["truncated"])
        self.assertEqual(result["status"], "complete")
        summary = summarize_captures([result])
        self.assertEqual(summary["truncated_captures"], 1)
        self.assertEqual(summary["latency_ms"]["first_playback_ms"]["truncated_captures_with_metric"], 1)

    def test_frame_gaps_are_sampling_intervals_not_verified_fps(self):
        data = capture()
        data["frames"] = [{"t_ms": t, "audio_active": False, "face": {}} for t in (100, 166.667, 400)]
        face = analyze_browser(data)["face"]
        self.assertEqual(face["sample_gaps_over_1_5_frames"], 1)
        self.assertAlmostEqual(face["sample_interval_ms"]["max"], 233.333)
        self.assertIn("not proof", face["note"])

    def test_missing_frames_and_recording_errors_visible(self):
        data = capture()
        data["frames"] = []
        data["recording"] = [{"kind": "audio", "unavailable": "No MediaRecorder"}]
        summary = summarize_captures([analyze_browser(data)])
        self.assertEqual(summary["captures_missing_frame_samples"], 1)
        self.assertEqual(summary["captures_with_recording_errors"], 1)

    def test_failed_fast_case_not_in_latency_distribution(self):
        data = capture()
        data["status"] = "failed"
        data["errors"] = [{"message": "transport failed"}]
        summary = summarize_captures([analyze_browser(data), analyze_browser(capture())])
        self.assertEqual(summary["capture_count"], 2)
        self.assertEqual(summary["complete_status_rate"], .5)
        self.assertEqual(summary["latency_ms"]["first_playback_ms"]["count"], 1)
        self.assertEqual(summary["latency_ms"]["first_playback_ms"]["excluded_captures"], 1)


class FilesAndGroupsTests(unittest.TestCase):
    def test_missing_browser_file_stays_in_denominator(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)
            (path / "fixture.json").write_text(json.dumps({"id": "missing"}))
            report = build_report({"native": path})
            summary = report["groups"]["native"]["summary"]
            self.assertEqual(summary["capture_count"], 1)
            self.assertEqual(summary["missing_or_invalid_captures"], 1)
            self.assertEqual(summary["complete_status_rate"], 0)

    def test_config_grouping_ignores_server_start_origin_only(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)
            for index, (floor, start) in enumerate((("hold", 100), ("hold", 200), ("cancel_all", 300))):
                case = path / str(index)
                case.mkdir()
                (case / "browser.json").write_text(json.dumps(capture()))
                (case / "configuration.json").write_text(json.dumps({"backend": "cascade", "floor": floor, "started_unix": start}))
            group = build_report({"cascade": path})["groups"]["cascade"]
            self.assertEqual(group["summary"]["capture_count"], 3)
            self.assertEqual(len(group["configurations"]), 2)

    def test_empty_group_no_zero_latency_or_pass(self):
        with tempfile.TemporaryDirectory() as name:
            summary = build_report({"empty": name})["groups"]["empty"]["summary"]
            self.assertEqual(summary["capture_count"], 0)
            self.assertIsNone(summary["complete_status_rate"])
            self.assertIsNone(summary["latency_ms"]["first_playback_ms"]["median"])
            self.assertIsNone(summary["overall_quality_pass"])


if __name__ == "__main__":
    unittest.main()
