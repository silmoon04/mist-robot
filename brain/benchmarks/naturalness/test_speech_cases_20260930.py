"""Local checks for the editable preflight speech case/scorer contract."""
import unittest

from brain.benchmarks.naturalness.speech_cases_20260930 import (
    ARMS, CASES, CORE_TRIALS, aggregate, preflight_fixtures, score_trial,
    word_error_rate, FIXTURE_ROOT, SOURCE_MANIFEST,
)


class SpeechCaseSpecTests(unittest.TestCase):
    def test_suite_is_bounded_and_uses_unique_cached_assets(self):
        self.assertEqual(len(CASES), 8)
        self.assertEqual(len({case.id for case in CASES}), 8)
        self.assertEqual(len(ARMS), 6)
        self.assertEqual(CORE_TRIALS, 96)
        self.assertEqual({case.id for case in CASES}, {
            "normal_end", "unfinished_pause_resume", "yeah_backchannel", "explicit_stop",
            "correction", "negated_stop", "quoted_stop", "face_request",
        })
        self.assertTrue(all(case.fixture.startswith("audio_") and case.fixture.endswith(".wav")
                            for case in CASES))

    def test_waits_are_allowed_and_semantics_are_explicit_oracle_inputs(self):
        case = next(c for c in CASES if c.id == "unfinished_pause_resume")
        self.assertEqual(case.wait_windows_ms, ((1240, 2540), (3260, 4360)))
        result = score_trial(case, events=[], transcript=[], audio_clock={},
                             semantic_judgments={})
        self.assertIsNone(result["metrics"]["semantic_constraints"]["pass"])
        self.assertFalse(result["metrics"]["semantic_constraints"]["available"])

    def test_separate_metric_rates_and_no_combined_ordinal_score(self):
        case = next(c for c in CASES if c.id == "yeah_backchannel")
        result = score_trial(case, events=[{"type": "debug_model", "phase": "floor_preserved",
                                            "t_ms": 110}],
                             transcript=[{"role": "user", "text": "yeah", "final": True}],
                             audio_clock={"capture_complete": True}, semantic_judgments={}, active_user_turn_id="u1",
                             input_start_ms=100, seed_turn_id="s1")
        self.assertTrue(result["metrics"]["preserved_backchannel"]["pass"])
        self.assertTrue(result["metrics"]["preserved_backchannel"]["transcript_preserved"])
        summary = aggregate([result])
        self.assertEqual(summary["metrics"]["preserved_backchannel"],
                         {"n": 1, "passed": 1, "failed": 0})
        self.assertNotIn("score", summary)
        self.assertNotIn("overall", summary)

    def test_last_nonsilent_sample_is_latency_anchor_and_missing_is_unavailable(self):
        case = next(c for c in CASES if c.id == "normal_end")
        result = score_trial(case,
                             events=[{"type": "audio", "role": "assistant", "t_ms": 9000,
                                      "benchmark_parent_user_turn_id": "u1"},
                                     # Seed audio has no parent user turn and is excluded.
                                     {"type": "audio", "role": "assistant", "t_ms": 2000,
                                      "benchmark_turn_id": "seed"}],
                             transcript=[],
                             audio_clock={"input_last_nonsilent_sample_ms": 8000},
                             semantic_judgments={}, active_user_turn_id="u1", input_start_ms=1000)
        self.assertEqual(result["metrics"]["false_premature_response"]
                         ["latency_from_last_nonsilent_sample_ms"], 1000)
        missing = score_trial(case, events=[], transcript=[], audio_clock={}, semantic_judgments={})
        self.assertIsNone(missing["metrics"]["false_premature_response"]
                          ["latency_from_last_nonsilent_sample_ms"])

    def test_long_pause_reply_during_fragment_gap_is_early(self):
        case = next(c for c in CASES if c.id == "unfinished_pause_resume")
        # Clip starts at t=10000; 1240-2540 ms is a legitimate silence, but
        # the utterance is still unfinished, so output in that window fails.
        result = score_trial(case,
                             events=[{"type": "audio", "role": "assistant", "t_ms": 12000,
                                      "benchmark_parent_user_turn_id": "u1"}],
                             transcript=[],
                             audio_clock={"clip_start_ms": 10000,
                                          "input_last_nonsilent_sample_ms": 15560},
                             semantic_judgments={}, active_user_turn_id="u1", input_start_ms=10000)
        self.assertTrue(result["metrics"]["false_premature_response"]
                        ["reply_before_final_segment_end"])
        self.assertFalse(result["hard_gates"]["no_early_assistant_output"])

    def test_stop_gate_uses_cancel_event_without_making_missing_evidence_a_failure(self):
        case = next(c for c in CASES if c.id == "explicit_stop")
        present = score_trial(case, events=[{"type": "audio_reset", "t_ms": 1200}], transcript=[],
                              audio_clock={"seed_playback_active_at_input": True,
                                           "capture_complete": True}, semantic_judgments={},
                              input_start_ms=1000, seed_turn_id="s1")
        absent = score_trial(case, events=[], transcript=[],
                             audio_clock={"seed_playback_active_at_input": True,
                                          "capture_complete": True}, semantic_judgments={},
                             input_start_ms=1000, seed_turn_id="s1")
        self.assertTrue(present["hard_gates"]["stop_command_honored"])
        self.assertFalse(absent["hard_gates"]["stop_command_honored"])
        self.assertIsNone(absent["metrics"]["missed_reply"]["pass"])

    def test_backchannel_needs_floor_kept_and_no_seed_reset_or_new_reply(self):
        case = next(c for c in CASES if c.id == "yeah_backchannel")
        events = [
            {"type": "debug_model", "phase": "floor_preserved", "t_ms": 1100,
             "benchmark_parent_user_turn_id": "u1"},
            {"type": "audio", "role": "assistant", "t_ms": 1200,
             "benchmark_turn_id": "seed"},
        ]
        good = score_trial(case, events=events,
                           transcript=[{"role": "user", "text": "yeah", "final": True}],
                           audio_clock={"capture_complete": True}, semantic_judgments={}, active_user_turn_id="u1",
                           input_start_ms=1000, seed_turn_id="seed")
        self.assertTrue(good["metrics"]["preserved_backchannel"]["pass"])
        reset = score_trial(case, events=events + [{"type": "audio_reset", "t_ms": 1300,
                                                   "was_playing": True}],
                            transcript=[{"role": "user", "text": "yeah", "final": True}],
                            audio_clock={"capture_complete": True}, semantic_judgments={}, active_user_turn_id="u1",
                            input_start_ms=1000, seed_turn_id="seed")
        self.assertFalse(reset["metrics"]["preserved_backchannel"]["pass"])
        partial = score_trial(case, events=events,
                              transcript=[{"role": "user", "text": "yeah", "final": True}],
                              audio_clock={}, semantic_judgments={}, active_user_turn_id="u1",
                              input_start_ms=1000, seed_turn_id="seed")
        self.assertIsNone(partial["metrics"]["preserved_backchannel"]["pass"])

    def test_negated_stop_checks_unwanted_cancel_and_face_receipt(self):
        negated = next(c for c in CASES if c.id == "negated_stop")
        cancelled = score_trial(negated, events=[{"type": "audio_reset", "t_ms": 1200,
                                                  "was_playing": True}],
                                transcript=[], audio_clock={"seed_playback_active_at_input": True,
                                                           "capture_complete": True},
                                semantic_judgments={}, input_start_ms=1000, seed_turn_id="s1")
        self.assertFalse(cancelled["metrics"]["unwanted_stop"]["pass"])
        face = next(c for c in CASES if c.id == "face_request")
        result = score_trial(face, events=[{"type": "face", "source": "model",
                                           "expression": "sad", "variant": 2}],
                             transcript=[], audio_clock={}, semantic_judgments={})
        self.assertTrue(result["hard_gates"]["requested_face_applied"])
        wrong_variant = score_trial(face, events=[{"type": "face", "source": "model",
                                                   "expression": "sad", "variant": 1}],
                                    transcript=[], audio_clock={}, semantic_judgments={})
        self.assertFalse(wrong_variant["hard_gates"]["requested_face_applied"])

    def test_wer_only_normalizes_case_and_punctuation(self):
        self.assertEqual(word_error_rate("Claude, please.", "claude please"), 0.0)
        self.assertEqual(word_error_rate("Claude", "cloud"), 1.0)

    def test_early_reply_correlation_includes_all_input_turns_not_seed(self):
        case = next(c for c in CASES if c.id == "unfinished_pause_resume")
        result = score_trial(case,
                             events=[{"type": "audio", "t_ms": 12000,
                                      "benchmark_parent_user_turn_id": "first"},
                                     {"type": "audio", "t_ms": 9000,
                                      "benchmark_turn_id": "seed"}],
                             transcript=[],
                             audio_clock={"clip_start_ms": 10000,
                                          "input_last_nonsilent_sample_ms": 15560},
                             semantic_judgments={}, active_user_turn_id="final",
                             input_user_turn_ids={"first", "final"}, input_start_ms=10000)
        self.assertEqual(result["metrics"]["false_premature_response"]
                         ["latency_from_last_nonsilent_sample_ms"], -3560)

    def test_cached_fixture_hash_and_declared_durations_match(self):
        result = preflight_fixtures(FIXTURE_ROOT, SOURCE_MANIFEST)
        self.assertTrue(result["ready_to_freeze"], result["flags"])
        self.assertEqual(len(result["checks"]), len(CASES))


if __name__ == "__main__":
    unittest.main()
