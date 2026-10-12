"""Check measured latency, evidence gaps, and paired comparison failure modes."""

import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import compare_runs, distribution, extract_metrics, score_sample, summarize_run


def event(name, t_ms, turn_id="turn-1", **kwargs):
    return {"name": name, "t_ms": t_ms, "turn_id": turn_id, **kwargs}


def sample(case_id="case-1", latency=100, *, status="completed", repeat=0, **kwargs):
    return {
        "case_id": case_id, "repeat": repeat, "category": "conversation",
        "split": "dev", "status": status,
        "events": [event("turn_committed", 20), event("first_text", 20 + latency)],
        "outcomes": {}, "checks": [], **kwargs,
    }


def run(samples, **manifest):
    return {
        "manifest": {"suite_sha256": "suite-sha", "adapter": "text", "run_id": "run-1",
                     "config": {"model": "luna"}, "source_hashes": {}, **manifest},
        "samples": samples,
    }


class ExtractMetricsTests(unittest.TestCase):
    def test_distinct_stages_do_not_claim_audio_for_text(self):
        result = extract_metrics(sample(events=[
            event("turn_committed", 100), event("first_text", 250),
            event("first_phrase", 300), event("turn_completed", 420),
        ]))
        self.assertEqual(result["model_ttft_ms"], 150)
        self.assertEqual(result["first_phrase_ms"], 200)
        self.assertEqual(result["turn_duration_ms"], 320)
        for metric in ("first_audio_ms", "first_useful_audio_ms", "asr_final_delay_ms",
                       "endpoint_delay_ms", "text_response_ms", "interrupt_cutoff_ms"):
            self.assertIsNone(result[metric], metric)

    def test_audio_stage_measurements_are_distinct(self):
        measured = extract_metrics(sample(events=[
            event("user_audio_end", 100), event("asr_final", 180),
            event("turn_committed", 200), event("first_text", 300),
            event("playback_started", 460), event("first_useful_audio", 700,
                metadata={"annotation_source": "human", "note": "First word of the requested answer."}),
        ]))
        self.assertEqual(measured["endpoint_delay_ms"], 100)
        self.assertEqual(measured["asr_final_delay_ms"], 80)
        self.assertEqual(measured["model_ttft_ms"], 100)
        self.assertEqual(measured["text_response_ms"], 200)
        self.assertEqual(measured["first_audio_ms"], 360)
        self.assertEqual(measured["first_useful_audio_ms"], 600)

    def test_clock_domains_never_subtracted(self):
        scored = score_sample(sample(events=[
            event("user_audio_end", 100, clock_id="phone"),
            event("playback_started", 200, clock_id="server"),
        ]))
        self.assertIsNone(scored["metrics"]["first_audio_ms"])
        self.assertTrue(any(issue["reason"] == "clock_mismatch" for issue in scored["issues"]))

    def test_turns_never_cross_paired(self):
        scored = score_sample(sample(events=[
            event("turn_committed", 100, turn_id="a"),
            event("first_text", 200, turn_id="b"),
        ]))
        self.assertIsNone(scored["metrics"]["model_ttft_ms"])
        self.assertTrue(any(issue["reason"] == "turn_mismatch" for issue in scored["issues"]))

    def test_multiple_turns_have_independent_spans(self):
        scored = score_sample(sample(events=[
            event("turn_committed", 100, turn_id="a"),
            event("first_text", 180, turn_id="a"),
            event("turn_committed", 2000, turn_id="b"),
            event("first_text", 2320, turn_id="b"),
        ]))
        self.assertEqual(scored["metric_observations"]["model_ttft_ms"], [80, 320])
        self.assertEqual(scored["metrics"]["model_ttft_ms"], 200)

    def test_out_of_order_records_are_sorted_by_identity_not_input_order(self):
        self.assertEqual(extract_metrics(sample(events=[
            event("first_text", 200), event("turn_committed", 100),
        ]))["model_ttft_ms"], 100)

    def test_negative_span_is_missing_not_zero(self):
        scored = score_sample(sample(events=[
            event("first_text", 50), event("turn_committed", 100),
        ]))
        self.assertIsNone(scored["metrics"]["model_ttft_ms"])
        self.assertTrue(any(issue["reason"] == "negative_latency" for issue in scored["issues"]))

    def test_duplicate_endpoints_are_ambiguous(self):
        scored = score_sample(sample(events=[
            event("turn_committed", 100), event("first_text", 200), event("first_text", 220),
        ]))
        self.assertIsNone(scored["metrics"]["model_ttft_ms"])
        self.assertTrue(any(issue["reason"] == "ambiguous_endpoints" for issue in scored["issues"]))

    def test_invalid_timestamps_not_coerced(self):
        for value in (True, "200", float("inf"), float("nan"), -1, None):
            with self.subTest(value=value):
                self.assertIsNone(extract_metrics(sample(events=[
                    event("turn_committed", 10), event("first_text", value),
                ]))["model_ttft_ms"])

    def test_missing_turn_and_other_case_cannot_supply_endpoint(self):
        for bad in (event("first_text", 200, turn_id=None),
                    event("first_text", 200, case_id="other-case")):
            with self.subTest(event=bad):
                self.assertIsNone(extract_metrics(sample(events=[event("turn_committed", 100), bad]))["model_ttft_ms"])

    def test_default_runner_clock_matches_explicit_runner(self):
        self.assertEqual(extract_metrics(sample(events=[
            event("turn_committed", 100), event("first_text", 175, clock_id="runner"),
        ]))["model_ttft_ms"], 75)

    def test_interleaved_tools_pair_by_id(self):
        scored = score_sample(sample(events=[
            event("tool_started", 10, tool_call_id="a"),
            event("tool_started", 50, tool_call_id="b"),
            event("tool_finished", 150, tool_call_id="b"),
            event("tool_finished", 410, tool_call_id="a"),
        ]))
        self.assertEqual(sorted(scored["metric_observations"]["tool_duration_ms"]), [100, 400])
        self.assertEqual(scored["metrics"]["tool_duration_ms"], 250)

    def test_tools_without_ids_not_guessed(self):
        self.assertIsNone(extract_metrics(sample(events=[
            event("tool_started", 10), event("tool_finished", 200),
        ]))["tool_duration_ms"])

    def test_metadata_ids_and_event_name_alias(self):
        self.assertEqual(extract_metrics(sample(events=[
            {"event": "tool_requested", "t_ms": 20, "turn_id": "a", "metadata": {"tool_call_id": "t"}},
            event("tool_started", 90, turn_id="a", metadata={"tool_call_id": "t"}),
        ]))["tool_dispatch_ms"], 70)

    def test_silence_does_not_imply_interruption_outcome(self):
        scored = score_sample(sample(events=[]))
        self.assertIsNone(scored["outcomes"]["false_interruption"])
        self.assertIsNone(scored["outcomes"]["missed_interruption"])
        explicit = score_sample(sample(outcomes={"false_interruption": False, "missed_interruption": True}))
        self.assertIs(explicit["outcomes"]["false_interruption"], False)
        self.assertIs(explicit["outcomes"]["missed_interruption"], True)

    def test_false_outcome_string_not_truthy_boolean(self):
        self.assertIsNone(score_sample(sample(outcomes={"task_success": "false"}))["outcomes"]["task_success"])

    def test_cutoff_measures_real_stop_not_text(self):
        result = extract_metrics(sample(events=[
            event("user_interrupt_onset", 50), event("first_text", 70),
            event("playback_stopped", 140),
        ]))
        self.assertEqual(result["interrupt_cutoff_ms"], 90)

    def test_first_useful_audio_requires_annotation(self):
        for metadata in ({}, {"annotation_source": "synth", "note": "guessed"}, {"annotation_source": "human"}):
            with self.subTest(metadata=metadata):
                result = extract_metrics(sample(events=[
                    event("user_audio_end", 50), event("first_useful_audio", 200, metadata=metadata),
                ]))
                self.assertIsNone(result["first_useful_audio_ms"])

    def test_first_tool_is_selection_latency_not_handler_time(self):
        result = extract_metrics(sample(events=[
            event("turn_committed", 20), event("first_tool", 100),
            event("tool_started", 105, tool_call_id="a"),
            event("tool_finished", 150, tool_call_id="a"),
        ]))
        self.assertEqual(result["first_tool_ms"], 80)
        self.assertEqual(result["tool_duration_ms"], 45)
        self.assertIsNone(result["tool_dispatch_ms"])


class SummaryTests(unittest.TestCase):
    def test_empty_distribution_not_zero(self):
        result = distribution([])
        self.assertEqual(result["count"], 0)
        self.assertIsNone(result["median"])
        self.assertIsNone(result["p95"])

    def test_percentiles_warn_for_small_n(self):
        result = distribution([100, 200, 300, float("nan"), True])
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["median"], 200)
        self.assertAlmostEqual(result["p90"], 280)
        self.assertAlmostEqual(result["p95"], 290)
        self.assertIsNotNone(result["small_n_warning"])
        self.assertIsNone(distribution(range(20))["small_n_warning"])

    def test_failed_and_unsupported_stay_in_denominator(self):
        report = summarize_run(run([
            sample(latency=100), sample("b", 1, status="failed"),
            sample("c", 1, status="unsupported"), sample("d", 1, status="timeout"),
        ]))
        self.assertEqual(report["sample_count"], 4)
        self.assertEqual(report["completion_rate"], .25)
        self.assertEqual(report["metrics"]["model_ttft_ms"]["median"], 100)
        self.assertEqual(report["metrics"]["model_ttft_ms"]["excluded_noncompleted_samples"], 3)

    def test_quality_failures_not_a_fast_success(self):
        report = summarize_run(run([
            sample("good", 100),
            sample("wrong", 1, checks=[{"name": "correct tool", "critical": True, "passed": False}]),
            sample("failed-task", 1, outcomes={"task_success": False}),
        ]))
        self.assertEqual(report["completed_samples"], 3)
        self.assertEqual(report["quality_failed_samples"], 2)
        self.assertEqual(report["metrics"]["model_ttft_ms"]["median"], 100)
        self.assertEqual(report["checks"]["correct tool"]["critical_failures"], 1)

    def test_missing_outcomes_and_audio_are_visible(self):
        report = summarize_run(run([
            sample("a", outcomes={"false_interruption": False}),
            sample("b", outcomes={"false_interruption": True}), sample("c"),
        ]))
        self.assertEqual(report["outcomes"]["false_interruption"], {
            "true": 1, "false": 1, "known": 2, "missing": 1, "true_rate": .5,
            "total_sample_denominator": 3,
        })
        self.assertEqual(report["metrics"]["first_audio_ms"]["missing_samples"], 3)
        self.assertIsNone(report["metrics"]["first_audio_ms"]["median"])

    def test_partial_run_planned_samples_remain_in_denominator(self):
        report = summarize_run(run([sample("a", repeat=1)], selected_case_ids=["a", "b"], repeats=2))
        self.assertEqual(report["sample_count"], 4)
        self.assertEqual(report["planned_sample_count"], 4)
        self.assertEqual(report["observed_sample_count"], 1)
        self.assertEqual(report["missing_sample_count"], 3)
        self.assertEqual(report["completion_rate"], .25)
        self.assertEqual(report["outcomes"]["task_success"]["missing"], 4)
        self.assertEqual(report["metrics"]["model_ttft_ms"]["missing_planned_samples"], 3)
        self.assertEqual(report["attempted_sample_count"], 1)
        self.assertEqual(report["attempted_completion_rate"], 1)
        self.assertEqual(report["planned_completion_rate"], .25)

    def test_empty_planned_run_has_no_attempted_completion_rate(self):
        report = summarize_run(run([], selected_case_ids=["a", "b"], repeats=2))
        self.assertEqual(report["planned_sample_count"], 4)
        self.assertEqual(report["missing_sample_count"], 4)
        self.assertEqual(report["attempted_sample_count"], 0)
        self.assertIsNone(report["attempted_completion_rate"])
        self.assertEqual(report["planned_completion_rate"], 0)

    def test_duplicate_rows_cannot_raise_completion_rate(self):
        report = summarize_run(run([sample(), sample()]))
        self.assertEqual(report["sample_count"], 2)
        self.assertEqual(report["invalid_sample_count"], 2)
        self.assertEqual(report["completion_rate"], 0)

    def test_text_audio_metrics_are_unmeasured_not_failed(self):
        report = summarize_run(run([sample()], evidence_mode="text_only", human_quality="unrated"))
        self.assertEqual(report["metrics"]["first_audio_ms"]["applicability"], "not_measured_by_text_adapter")
        self.assertIsNone(report["overall_quality_verdict"])


class CompareTests(unittest.TestCase):
    def test_pair_by_case_repeat_not_input_order(self):
        before = run([sample("a", 100), sample("b", 300), sample("a", 400, repeat=1)])
        after = run([sample("a", 350, repeat=1), sample("b", 200), sample("a", 90)])
        result = compare_runs(before, after, resamples=100)
        metric = result["metrics"]["model_ttft_ms"]
        self.assertEqual(metric["pairs"], 3)
        self.assertEqual(metric["delta_ms"]["median"], -50)
        self.assertEqual(result["coverage"]["usable_pairs"], 3)

    def test_suite_and_adapter_must_match(self):
        for change in ({"suite_sha256": "different"}, {"adapter": "audio"}):
            with self.subTest(change=change):
                result = compare_runs(run([sample()]), run([sample()], **change))
                self.assertFalse(result["comparable"])
                self.assertEqual(result["metrics"], {})

    def test_configuration_change_is_surfaced_and_allowed(self):
        result = compare_runs(run([sample()]), run([sample()], config={"model": "other"}))
        self.assertTrue(result["comparable"])
        self.assertTrue(result["config_changed"])

    def test_missing_manifest_identity_is_not_comparable(self):
        result = compare_runs({"samples": [sample()]}, run([sample()]))
        self.assertFalse(result["comparable"])

    def test_duplicate_identity_excluded_not_last_write_wins(self):
        result = compare_runs(run([sample(), sample(latency=1)]), run([sample()]))
        self.assertEqual(result["coverage"]["usable_pairs"], 0)
        self.assertEqual(result["coverage"]["invalid_baseline_samples"], 2)
        self.assertTrue(any(issue["reason"] == "duplicate_sample_identity" for issue in result["issues"]))

    def test_unpaired_failed_and_quality_failed_are_disclosed(self):
        before = run([sample("a"), sample("b"), sample("c"), sample("left")])
        after = run([sample("a", 1, status="failed"), sample("b", 90),
                     sample("c", 1, outcomes={"task_success": False}), sample("right")])
        result = compare_runs(before, after)
        self.assertEqual(result["metrics"]["model_ttft_ms"]["pairs"], 1)
        self.assertEqual(result["coverage"]["baseline_only"], [{"case_id": "left", "repeat": 0}])
        self.assertEqual(result["coverage"]["candidate_only"], [{"case_id": "right", "repeat": 0}])
        self.assertEqual({pair["reason"] for pair in result["excluded_pairs"]}, {"noncompleted_pair", "quality_failed_pair"})

    def test_missing_metric_pair_has_no_zero_delta(self):
        result = compare_runs(run([sample()]), run([sample(events=[])]))
        self.assertEqual(result["metrics"]["model_ttft_ms"]["missing_pairs"], 1)
        self.assertIsNone(result["metrics"]["model_ttft_ms"]["delta_ms"]["median"])

    def test_bootstrap_is_deterministic_and_does_not_split_turns(self):
        before = run([sample("a", 100), sample("b", 200)])
        after = run([sample("a", 110), sample("b", 220, events=[
            event("turn_committed", 0, turn_id="a"), event("first_text", 200, turn_id="a"),
            event("turn_committed", 1000, turn_id="b"), event("first_text", 1240, turn_id="b"),
        ])])
        first = compare_runs(before, after, seed=12, resamples=100)
        second = compare_runs(before, after, seed=12, resamples=100)
        self.assertEqual(first, second)
        self.assertEqual(first["metrics"]["model_ttft_ms"]["pairs"], 2)
        self.assertEqual(first["metrics"]["model_ttft_ms"]["median_delta_ci95_ms"], [10, 20])

    def test_single_pair_does_not_claim_confidence_interval(self):
        result = compare_runs(run([sample()]), run([sample(latency=90)]))
        self.assertIsNone(result["metrics"]["model_ttft_ms"]["median_delta_ci95_ms"])

    def test_category_and_split_mismatch_rejected(self):
        for kwargs in ({"category": "interrupts"}, {"split": "holdout"}, {"scenario_hash": "other"}):
            with self.subTest(kwargs=kwargs):
                result = compare_runs(run([sample()]), run([sample(**kwargs)]))
                self.assertEqual(result["coverage"]["usable_pairs"], 0)

    def test_category_strata_keep_different_workloads_separate(self):
        before = run([sample("a", 100), sample("b", 900, category="tools")])
        after = run([sample("a", 90), sample("b", 1200, category="tools")])
        result = compare_runs(before, after)
        self.assertEqual(result["categories"]["conversation"]["metrics"]["model_ttft_ms"]["delta_ms"]["median"], -10)
        self.assertEqual(result["categories"]["tools"]["metrics"]["model_ttft_ms"]["delta_ms"]["median"], 300)

    def test_repeats_of_one_case_do_not_create_independent_clusters(self):
        result = compare_runs(run([sample("a", 100, repeat=i) for i in range(5)]),
                              run([sample("a", 90, repeat=i) for i in range(5)]))
        metric = result["metrics"]["model_ttft_ms"]
        self.assertEqual(metric["pairs"], 5)
        self.assertEqual(metric["independent_case_clusters"], 1)
        self.assertIsNone(metric["median_delta_ci95_ms"])

    def test_planned_missing_pairs_survive_partial_runs(self):
        before = run([sample("a", repeat=1)], selected_case_ids=["a", "b"], repeats=2)
        after = run([sample("a", repeat=1), sample("b", repeat=1)], selected_case_ids=["a", "b"], repeats=2)
        result = compare_runs(before, after)
        self.assertEqual(result["coverage"]["planned_pair_union"], 4)
        self.assertEqual(len(result["coverage"]["missing_planned_pairs"]), 3)
        both_missing = [pair for pair in result["coverage"]["missing_planned_pairs"]
                        if pair["missing_baseline"] and pair["missing_candidate"]]
        self.assertEqual(len(both_missing), 2)
        self.assertEqual(len(result["coverage"]["missing_baseline_planned_samples"]), 3)
        self.assertEqual(len(result["coverage"]["missing_candidate_planned_samples"]), 2)

    def test_known_arm_plan_is_reported_when_other_plan_is_unknown(self):
        before = run([sample("a", repeat=1)], selected_case_ids=["a", "b"], repeats=2)
        after = run([sample("a", repeat=1)])
        result = compare_runs(before, after)
        self.assertEqual(result["coverage"]["planned_baseline_samples"], 4)
        self.assertEqual(len(result["coverage"]["missing_baseline_planned_samples"]), 3)
        self.assertIsNone(result["coverage"]["planned_candidate_samples"])
        self.assertIsNone(result["coverage"]["missing_candidate_planned_samples"])

    def test_same_config_is_repeatability_not_an_improvement_verdict(self):
        result = compare_runs(run([sample()]), run([sample(latency=50)]))
        self.assertEqual(result["comparison_kind"], "repeatability")
        self.assertIsNone(result["overall_quality_verdict"])
        self.assertEqual(result["human_quality_status"]["candidate"], "unrated")


if __name__ == "__main__":
    unittest.main()
