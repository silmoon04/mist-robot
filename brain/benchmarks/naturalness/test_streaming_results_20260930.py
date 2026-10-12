from __future__ import annotations

from pathlib import Path
import json
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarks.naturalness import streaming_results_20260930 as report


def test_timing_uses_every_user_epoch_and_parent_lineage():
    row = {"input_start_ms": 100, "input_last_nonsilent_sample_ms": 1000,
           "input_last_sample_ms": 1100, "seed_turn_id": "seed",
           "events": [
               {"t_ms": 150, "type": "audio", "benchmark_turn_id": "seed",
                "benchmark_parent_user_turn_id": "seed", "pcm_bytes": 200},
               {"t_ms": 400, "type": "transcript_done", "role": "user", "text": "the green bracket",
                "benchmark_turn_id": "user-1"},
               {"t_ms": 900, "type": "transcript_delta", "role": "assistant", "text": "early",
                "benchmark_parent_user_turn_id": "user-1"},
               {"t_ms": 1200, "type": "transcript_done", "role": "user", "text": "needs sanding",
                "benchmark_turn_id": "user-2"},
               {"t_ms": 1400, "type": "audio", "pcm_bytes": 320,
                "benchmark_parent_user_turn_id": "user-2"},
           ]}
    timing = report.timing_and_transcript(row)
    assert timing["accepted_user_turn_ids"] == ["user-1", "user-2"]
    assert timing["first_text_ms"] == 900
    assert timing["first_pcm_ms"] == 1400
    assert timing["from_last_nonsilent_ms"]["first_text"] == -100
    assert timing["from_last_sample_ms"]["accepted_transcript"] == 100


def test_failed_attempt_stays_in_denominator_and_pair_is_excluded():
    def one(arm, status, valid):
        return {"arm": arm, "case_id": "normal_end", "repetition": 1,
                "status": status, "condition_valid": True,
                "experimental_condition_valid": valid, "comparable_valid": valid,
                "error_categories": ["trial_failed"] if status == "failed" else [],
                "gates": {"no_early_assistant_output": True}, "mechanical_checks": {}, "wer": 0,
                "timing": {"from_last_nonsilent_ms": {"first_pcm": 200,
                           "first_text": 100, "accepted_transcript": 50}},
                "cost": {"captured_usage_listed_rate_subtotal_usd": .01,
                         "regular_asr_duration_proxy_usd": .001, "unknown_components": []}}
    rows = [one("nova-jev-off", "complete", True), one("nova-jev-on", "failed", False)]
    arm = report.aggregate(rows)
    assert arm["nova-jev-on"]["attempted"] == 1
    assert arm["nova-jev-on"]["comparable_valid"] == 0
    assert report.paired(rows)["nova"]["comparable_valid_pairs"] == 0
    assert report.paired_asr(rows)["nova_vs_flux_jev_off"]["comparable_valid_pairs"] == 0


def test_timeout_with_valid_condition_counts_in_gates_and_observed_timing():
    row = {"arm": "nova-jev-off", "case_id": "normal_end", "repetition": 1,
           "status": "timeout", "condition_valid": True,
           "experimental_condition_valid": True, "comparable_valid": False,
           "error_categories": ["trial_timeout"], "gates": {"no_early_assistant_output": False},
           "mechanical_checks": {"missed_reply": False},
           "wer": .1, "timing": {"from_last_nonsilent_ms": {"first_pcm": 230,
                    "first_text": 200, "accepted_transcript": 100}},
           "cost": {"captured_usage_listed_rate_subtotal_usd": .01,
                    "regular_asr_duration_proxy_usd": .001, "unknown_components": []}}
    aggregate = report.aggregate([row])["nova-jev-off"]
    assert aggregate["attempted"] == 1 and aggregate["comparable_valid"] == 0
    checks = report.per_case_checks([row])["normal_end::nova-jev-off"]
    assert checks["gates"]["no_early_assistant_output"]["fail"] == 1
    assert aggregate["timing_condition_valid_all_statuses"]["first_pcm"]["median_ms"] == 230
    timing = report.per_case_arm_timing([row])["normal_end::nova-jev-off"]
    assert timing["first_pcm"] == {"n": 1, "median_ms": 230, "p90_ms": 230}


def test_non_face_case_does_not_fail_face_check():
    pricing = report.read(report.BRAIN / "results/architecture-cost-20260928/pricing.json")
    row = {"order": 1, "case_id": "normal_end", "arm": "nova-jev-off",
           "repetition": 1, "status": "complete", "condition_valid": True,
           "input_start_ms": 0, "input_last_sample_ms": 1000,
           "input_last_nonsilent_sample_ms": 900,
           "events": [{"t_ms": 1200, "type": "transcript_done", "role": "user",
                       "text": "Explain how a screw washer and bracket fit together in four short sentences",
                       "benchmark_turn_id": "user"}],
           "audio_clock": {"clip_start_ms": 0, "input_last_nonsilent_sample_ms": 900,
                           "capture_complete": True}, "usage": {}}
    result = report.analyze_row(row, {}, pricing)
    assert result["metrics"]["applied_requested_face"]["available"] is False
    assert result["metrics"]["applied_requested_face"]["pass"] is False
    assert result["mechanical_checks"]["applied_requested_face"] is None
    case_checks = report.per_case_checks([result])["normal_end::nova-jev-off"]
    assert "applied_requested_face" not in case_checks["mechanical_checks"]


def test_jev_cost_uses_input_tokens_only():
    pricing = report.read(report.BRAIN / "results/architecture-cost-20260928/pricing.json")
    row = {"arm": "nova-jev-on", "usage": {"request_records": [{"provider": "jev",
           "usage": {"input_tokens": 1_000_000, "output_tokens": 500_000}}]}}
    cost = report.usage_cost(row, {}, pricing)
    assert cost["components_usd"]["jev"] == .042
    assert cost["tokens"]["jev_output"] == 500_000


def test_late_jev_outcome_is_counted_without_inventing_fallback_source():
    trace = {"events": [{"event": {"type": "debug_model", "phase": "jev_request"}},
                        {"event": {"type": "debug_model", "phase": "jev_result",
                                   "decision": "take_turn", "latency_ms": 500, "raw": None}},
                        {"event": {"type": "jev_policy_outcomes", "drained": True,
                                   "outcomes": [{"result": {"status": "error", "error_type": "timeout",
                                                           "response": None}}]}}]}
    result = report.jev_diagnostics(trace)
    assert result["requests"] == 1
    assert result["drained_error_types"] == {"timeout": 1}
    assert result["deadline_fallbacks"] is None


def test_jev_application_source_is_counted_when_recorded():
    trace = {"events": [{"event": {"type": "debug_model", "phase": "jev_result",
                                  "source": "deadline_fallback", "decision": "take_turn"}}]}
    result = report.jev_diagnostics(trace)
    assert result["application_source_recorded"] is True
    assert result["deadline_fallbacks"] == 1
    assert result["busy_fallbacks"] == 0


def test_fallback_turn_applied_does_not_credit_provider_advice():
    trace = {"events": [
        {"event": {"type": "debug_model", "phase": "jev_result", "provider_turn_id": "turn-1",
                   "source": "deadline_fallback", "decision": "take_turn"}},
        {"event": {"type": "debug_model", "phase": "jev_turn_applied", "provider_turn_id": "turn-1",
                   "decision": "take_turn"}},
    ]}
    result = report.jev_diagnostics(trace)
    assert result["resolved_decision_events"] == 1
    assert result["resolved_decisions_by_origin"] == {"deadline_fallback": 1}
    assert result["provider_advice_applied"] == 0
    assert result["local_or_other_decisions_applied"] == 1
    summary = report.jev_by_arm([{"arm": "flux-jev-on", "jev": result}])["flux-jev-on"]
    assert summary["provider_advice_applied"] == 0
    assert summary["decision_sources"] == {"deadline_fallback": 1}


def test_provider_advice_application_requires_matching_turn():
    trace = {"events": [
        {"event": {"type": "debug_model", "phase": "jev_result", "provider_turn_id": "turn-1",
                   "source": "jev", "decision": "take_turn"}},
        {"event": {"type": "debug_model", "phase": "jev_turn_applied", "provider_turn_id": "turn-2",
                   "decision": "take_turn"}},
    ]}
    result = report.jev_diagnostics(trace)
    assert result["provider_advice_returned"] == 1
    assert result["provider_advice_applied"] == 0
    assert result["applied_decision_origin_unknown"] == 1


def test_nested_asr_accounting_preserves_timing_summary_and_unknown_legacy_rate():
    pricing = report.read(report.BRAIN / "results/architecture-cost-20260928/pricing.json")
    timing = {"first_text_receive_after_open_s": 7.4}
    row = {"arm": "flux-jev-off", "usage": {"asr_streams": [{"streams": {"primary":
           {"pcm_seconds": 36, "connected_duration_s": 38}}, "timing_summary": timing}]}}
    result = report.usage_cost(row, {}, pricing)
    assert result["regular_asr_duration_proxy_usd"] == .0039
    assert result["asr_timing_summary"] == timing
    row["arm"] = "legacy-qwen-affect"
    unknown = report.usage_cost(row, {}, pricing)
    assert unknown["regular_asr_duration_proxy_usd"] == 0
    assert "primary_asr_pcm_seconds_or_rate" in unknown["unknown_components"]


def test_shadow_only_compares_words_with_overlapping_audio():
    def event(shadow, word, start, end):
        return {"event": {"type": "debug_model", "phase": "asr_event", "event_type": "final",
                          "shadow": shadow,
                          "metadata": {"original_event_type": "alignment"} if shadow else {},
                          "words": [{"word": word, "start": start, "end": end}]}}
    trace = {"events": [event(False, "landscape", 1, 1.5),
                        event(True, "portrait", 1.1, 1.4), event(True, "landscape", 2, 2.5)]}
    overlap = report.shadow_overlap(trace)
    assert overlap["same_audio_overlap_words"] == 1
    assert len(overlap["disagreements"]) == 1


def test_shadow_comparison_requires_matching_flux_case_rep_and_jev():
    shadow = {"order": 1, "case_id": "correction", "repetition": 2,
              "arm": "flux-scribe-shadow-jev-on", "status": "complete",
              "timing": {"accepted_transcript": "Wait I said landscape"},
              "cost": {"asr_streams": {"shadow": {"sent_pcm_seconds": 5, "dropped_pcm_bytes": 0}},
                       "components_usd": {"asr_shadow_regular_proxy": .0005}}}
    main = [{"order": 50, "case_id": "correction", "repetition": 2,
             "arm": "flux-jev-on", "status": "complete",
             "timing": {"accepted_transcript": "Wait I said landscape"}},
            {"order": 51, "case_id": "correction", "repetition": 1,
             "arm": "flux-jev-off", "status": "complete",
             "timing": {"accepted_transcript": "other"}}]
    diagnostics = {"1": {"flux_final_transcript": "Wait I said landscape",
                         "scribe_final_transcript": "Wait I said landscape",
                         "same_audio_overlap_words": 4}}
    row = report.shadow_comparison([shadow], diagnostics, main)[0]
    assert row["matched_main_order"] == 50
    assert row["scribe_raw_wer_vs_gold"] == 0
    assert row["shadow_dropped_pcm_bytes"] == 0


def test_shadow_wrapped_error_is_categorized():
    trace = {"events": [{"event": {"type": "debug_model", "phase": "asr_event",
                                   "shadow": True, "event_type": "shadow",
                                   "metadata": {"original_event_type": "error"}}}]}
    assert "shadow_asr_error" in report.error_categories({"status": "complete", "events": []}, trace)


def test_model_latency_requires_unique_revision_match():
    def event(phase, t, revision):
        return {"elapsed_ms": t, "event": {"type": "debug_model", "phase": phase,
                                             "revision": revision}}
    trace = {"events": [event("user_committed", 100, 1),
                        event("thinking_finished", 200, 1),
                        event("user_committed", 300, 2),
                        event("thinking_finished", 450, 2)]}
    model = report.model_diagnostics(trace)
    assert model["commit_to_thinking_finished_ms_by_revision"] == [100, 150]
    assert model["commit_to_thinking_finished_ms"] is None
    ambiguous = {"events": [event("user_committed", 100, 1),
                            event("user_committed", 120, 1),
                            event("thinking_finished", 200, 1)]}
    assert report.model_diagnostics(ambiguous)["commit_to_thinking_finished_ms"] is None


def test_semantic_packet_includes_failure_without_arm_identity(tmp_path: Path):
    attempt = {"order": 1, "case_id": "normal_end", "arm": "nova-jev-off",
               "repetition": 1, "status": "timeout", "condition_valid": True,
               "input_start_ms": 0, "events": [{"t_ms": 100, "type": "transcript_done",
                   "role": "user", "text": "Explain the bracket", "benchmark_turn_id": "u"}],
               "output_audio": []}
    assert report.semantic_packet([attempt], tmp_path) == 1
    packet = json.loads((tmp_path / "quality/semantic_review_packet.json").read_text())
    assert packet["items"][0]["status"] == "timeout"
    assert "nova" not in json.dumps(packet)
    key = json.loads((tmp_path / "quality/secret_semantic_key.json").read_text())
    assert key["review-001"]["arm"] == "nova-jev-off"


def test_audio_packet_only_asks_about_captured_speech(tmp_path: Path):
    run, out = tmp_path / "run", tmp_path / "analysis"
    run.mkdir()
    out.mkdir()
    audio = run / "response.wav"
    audio.write_bytes(b"captured-pcm")
    row = {"arm": "flux-jev-on", "case_id": "normal_end", "repetition": 1,
           "order": 1, "comparable_valid": True, "seed_turn_id": None,
           "output_audio": [{"file": audio.name,
                             "sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
                             "turn_id": "user"}]}
    assert report.blind_packet([row], run, out) == 1
    packet = json.loads((out / "blind_review_packet.json").read_text())
    questions = " ".join(packet["items"][0]["questions"]).casefold()
    assert "floor" not in questions and "interrupt" not in questions
    assert "transport gaps" in packet["instructions"]


def test_output_must_be_outside_frozen_run(tmp_path: Path):
    run = tmp_path / "run"
    run.mkdir()
    try:
        report.analyze(run, run / "analysis")
    except ValueError as exc:
        assert "separate" in str(exc)
    else:
        raise AssertionError("Analyzer accepted output under frozen run")
