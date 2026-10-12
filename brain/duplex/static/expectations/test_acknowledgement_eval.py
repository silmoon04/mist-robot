"""Validate evidence discrimination with invented events, not voice performance."""

import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acknowledgement_eval import evaluate_sample, validate_contracts


DOCUMENT = json.loads(Path(__file__).with_name("acknowledgement_contracts.json").read_text(encoding="utf-8"))


def fixture(contract=0, label="good"):
    return copy.deepcopy(DOCUMENT["contracts"][contract][label]["sample"])


def event(sample, name):
    return next(row for row in sample["events"] if row["event"] == name)


class AcknowledgementEvidenceTests(unittest.TestCase):
    def assert_unknown(self, sample):
        result = evaluate_sample(sample)
        self.assertEqual(result["status"], "unknown", result)
        return result

    def test_all_seven_good_bad_pairs_discriminate(self):
        report = validate_contracts(DOCUMENT)
        self.assertEqual(report["fixtures"], 14)
        self.assertEqual(report["matched"], 14, report)
        self.assertEqual(report["status_counts"], {"pass": 7, "fail": 6, "unknown": 1})
        self.assertFalse(report["mist_performance_measured"])
        self.assertEqual(report["human_naturalness"], "unmeasured")

    def test_filler_does_not_improve_useful_content_timing(self):
        result = evaluate_sample(fixture())
        self.assertEqual(result["timings_ms"]["first_reaction"], 550)
        self.assertEqual(result["timings_ms"]["first_acknowledgement"], 550)
        self.assertEqual(result["timings_ms"]["first_useful_content"], 1680)
        self.assertEqual(result["prosody"], "unmeasured")

    def test_useful_marker_in_filler_span_stays_unknown(self):
        result = self.assert_unknown(fixture(6, "bad"))
        self.assertEqual(result["timings_ms"]["first_reaction"], 550)
        self.assertIsNone(result["timings_ms"]["first_useful_content"])

    def test_quiet_and_fast_success_do_not_require_a_cue(self):
        for index in (1, 2):
            with self.subTest(index=index):
                result = evaluate_sample(fixture(index))
                self.assertEqual(result["status"], "pass")
                self.assertIsNone(result["timings_ms"]["first_acknowledgement"])
                self.assertIsNotNone(result["timings_ms"]["first_useful_content"])

    def test_optional_slow_response_can_remain_silent(self):
        sample = fixture()
        sample["events"] = [row for row in sample["events"] if not row["event"].startswith("ack_")]
        self.assertEqual(evaluate_sample(sample)["status"], "pass")

    def test_active_cue_cutoff_has_its_own_correlated_measurement(self):
        result = evaluate_sample(fixture(4))
        self.assertEqual(result["timings_ms"]["acknowledgement_cutoffs"], [40])
        self.assertIsNone(result["timings_ms"]["first_useful_content"])
        self.assertEqual(evaluate_sample(fixture(4, "bad"))["timings_ms"]["acknowledgement_cutoffs"], [200])

    def test_missing_or_mixed_event_clock_is_unknown(self):
        for value in (None, "", "different-clock"):
            with self.subTest(value=value):
                sample = fixture()
                event(sample, "ack_started")["clock_id"] = value
                result = self.assert_unknown(sample)
                self.assertIsNone(result["timings_ms"]["first_reaction"])

    def test_no_implicit_default_clock(self):
        sample = fixture()
        for row in sample["events"]:
            del row["clock_id"]
        self.assert_unknown(sample)

    def test_missing_sample_or_event_scope_is_unknown(self):
        for field in ("case_id", "turn_id", "revision_id", "response_id"):
            with self.subTest(field=field):
                sample = fixture()
                del event(sample, "ack_started")[field]
                self.assert_unknown(sample)
                sample = fixture()
                sample[field] = ""
                self.assert_unknown(sample)

    def test_incomplete_capture_never_proves_absence_of_ack(self):
        sample = fixture(1)
        sample["capture"]["complete"] = False
        self.assert_unknown(sample)
        sample = fixture(1)
        sample["capture"]["end_ms"] += 1
        self.assert_unknown(sample)

    def test_missing_policy_is_not_an_inferred_quiet_preference(self):
        sample = fixture(2)
        del sample["policy"]["quiet"]
        self.assert_unknown(sample)

    def test_incomplete_user_or_playback_span_is_unknown(self):
        for missing in ("user_audio_start", "user_audio_end", "ack_stopped", "answer_stopped"):
            with self.subTest(missing=missing):
                sample = fixture()
                sample["events"] = [row for row in sample["events"] if row["event"] != missing]
                self.assert_unknown(sample)

    def test_missing_or_wrong_ack_and_playback_ids_are_unknown(self):
        for name, field in (("ack_started", "ack_id"), ("ack_stopped", "playback_id"),
                            ("user_audio_end", "user_span_id")):
            with self.subTest(name=name, field=field):
                sample = fixture()
                event(sample, name)[field] = "unmatched-id"
                self.assert_unknown(sample)

    def test_missing_cutoff_id_is_unknown_not_a_latency(self):
        sample = fixture(4)
        del event(sample, "ack_stopped")["interruption_id"]
        result = self.assert_unknown(sample)
        self.assertEqual(result["timings_ms"]["acknowledgement_cutoffs"], [])

    def test_wrong_cancellation_id_cannot_pass(self):
        sample = fixture(3)
        event(sample, "ack_cancelled")["interruption_id"] = "different-interruption"
        self.assert_unknown(sample)
        sample = fixture(4)
        event(sample, "ack_stopped")["interruption_id"] = "different-interruption"
        self.assert_unknown(sample)

    def test_duplicate_playback_and_ready_endpoints_are_unknown(self):
        for name in ("ack_started", "answer_ready", "response_closed"):
            with self.subTest(name=name):
                sample = fixture()
                sample["events"].append(copy.deepcopy(event(sample, name)))
                self.assert_unknown(sample)

    def test_useful_annotation_and_answer_span_are_both_required(self):
        for mutation in ("missing_marker", "missing_annotation", "outside_span", "unknown_playback"):
            with self.subTest(mutation=mutation):
                sample = fixture()
                useful = event(sample, "first_useful_audio")
                if mutation == "missing_marker":
                    sample["events"].remove(useful)
                elif mutation == "missing_annotation":
                    useful.pop("metadata")
                elif mutation == "outside_span":
                    useful["t_ms"] = 900
                else:
                    useful["playback_id"] = "unobserved-audio"
                result = self.assert_unknown(sample)
                self.assertIsNone(result["timings_ms"]["first_useful_content"])

    def test_invalid_times_and_names_do_not_crash_or_pass(self):
        for field, value in (("t_ms", True), ("t_ms", math.nan), ("t_ms", -1),
                             ("event", None), ("event", ["ack_started"])):
            with self.subTest(field=field, value=value):
                sample = fixture()
                event(sample, "ack_started")[field] = value
                self.assert_unknown(sample)
        self.assert_unknown(None)

    def test_events_can_arrive_in_another_order_on_the_same_clock(self):
        sample = fixture()
        sample["events"].reverse()
        self.assertEqual(evaluate_sample(sample)["status"], "pass")

    def test_answer_winning_before_cue_start_fails_pending_work_contract(self):
        sample = fixture()
        event(sample, "answer_ready")["t_ms"] = 600
        result = evaluate_sample(sample)
        self.assertEqual(result["checks"]["pending_work_only"]["status"], "fail")
        self.assertEqual(result["status"], "fail")

    def test_answer_cannot_play_before_ready_or_work_or_after_close(self):
        for name, timestamp, issue in (
            ("answer_started", 1699, "answer_playback_before_ready_or_work"),
            ("answer_started", 120, "answer_playback_before_ready_or_work"),
            ("answer_stopped", 2200, "event_outside_capture"),
        ):
            with self.subTest(name=name, timestamp=timestamp):
                sample = fixture()
                event(sample, name)["t_ms"] = timestamp
                result = self.assert_unknown(sample)
                self.assertIn(issue, result["issues"])
                self.assertIsNone(result["timings_ms"]["first_useful_content"])

    def test_completed_response_cannot_contain_invalidation(self):
        sample = fixture()
        sample["events"].append({**event(sample, "response_started"),
                                 "event": "user_resumed", "t_ms": 2050,
                                 "interruption_id": "late-resume"})
        result = self.assert_unknown(sample)
        self.assertIn("completed_response_contains_invalidation", result["issues"])

    def test_answer_crossing_invalidation_is_unscored_not_a_cancellation_pass(self):
        sample = fixture(1)
        sample["events"].append({**event(sample, "response_started"),
                                 "event": "user_resumed", "t_ms": 400,
                                 "interruption_id": "resume-during-answer"})
        event(sample, "response_closed")["outcome"] = "cancelled"
        result = self.assert_unknown(sample)
        self.assertIn("answer_crosses_invalidation_out_of_scope", result["issues"])
        self.assertEqual(result["timings_ms"]["acknowledgement_cutoffs"], [])

    def test_absolute_script_path_works_from_another_directory(self):
        script = Path(__file__).resolve().with_name("acknowledgement_eval.py")
        with tempfile.TemporaryDirectory(prefix="ack-eval-cli-") as directory:
            completed = subprocess.run([sys.executable, str(script)], cwd=directory,
                                       capture_output=True, text=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["matched"], 14)
        self.assertEqual(report["kind"], "synthetic_evaluator_validation")


if __name__ == "__main__":
    unittest.main()
