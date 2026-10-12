"""Read-only analysis of the isolated 2026-09-30 streaming speech trials.

Writes exclusively to a caller-selected analysis directory outside the frozen
attempt directory. No provider calls and no edits to attempts, traces or audio.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import sys

BRAIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BRAIN))
from benchmarks.naturalness import speech_cases_20260930 as spec

CASES = {case.id: case for case in spec.CASES}
ASR_RATES_PER_HOUR = {
    "nova": {"promo": .29, "regular": .462},
    "flux": {"regular": .39},
    "scribe": {"regular": .39},
}
JEV_USD_PER_M = .042
SHADOW_CASES = {"unfinished_pause_resume", "correction"}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def delta(at, anchor):
    return round(at - anchor, 3) if number(at) and number(anchor) else None


def normal(text):
    return spec._wer_tokens(str(text or ""))


def percentile(values, fraction):
    ordered = sorted(v for v in values if number(v))
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    low = int(position)
    return round(ordered[low] + (ordered[min(low + 1, len(ordered)-1)] - ordered[low]) * (position-low), 3)


def events_after_input(row):
    start = row.get("input_start_ms")
    if not number(start):
        return []
    seed = row.get("seed_turn_id")
    return [e for e in row.get("events", []) if isinstance(e, dict) and number(e.get("t_ms"))
            and e["t_ms"] >= start and (not seed or
            (e.get("benchmark_turn_id") != seed and e.get("benchmark_parent_user_turn_id") != seed))]


def timing_and_transcript(row):
    events = events_after_input(row)
    user = [e for e in events if e.get("type") == "transcript_done" and e.get("role") == "user"]
    # Every accepted user epoch matters for early output; the last one is the
    # final task epoch for completion. Output is linked by parent, not arrival.
    user_ids = {e.get("benchmark_turn_id") for e in user if e.get("benchmark_turn_id")}
    final_id = user[-1].get("benchmark_turn_id") if user else None
    output = [e for e in events if e.get("benchmark_parent_user_turn_id") in user_ids
              and e.get("benchmark_parent_user_turn_id") is not None]
    text = [e["t_ms"] for e in output if e.get("type") == "transcript_delta"
            and e.get("role") == "assistant"]
    pcm = [e["t_ms"] for e in output if e.get("type") == "audio" and e.get("pcm_bytes", 0) > 0]
    anchors = {"last_nonsilent": row.get("input_last_nonsilent_sample_ms"),
               "last_sample": row.get("input_last_sample_ms")}
    first_text = min(text) if text else None
    first_pcm = min(pcm) if pcm else None
    accepted_at = user[-1]["t_ms"] if user else None
    return {
        "accepted_transcript": " ".join(str(e.get("text") or "") for e in user).strip(),
        "accepted_user_turn_ids": sorted(user_ids), "final_user_turn_id": final_id,
        "first_text_ms": first_text, "first_pcm_ms": first_pcm,
        "accepted_transcript_ms": accepted_at,
        "from_last_nonsilent_ms": {"first_text": delta(first_text, anchors["last_nonsilent"]),
                                   "first_pcm": delta(first_pcm, anchors["last_nonsilent"]),
                                   "accepted_transcript": delta(accepted_at, anchors["last_nonsilent"])},
        "from_last_sample_ms": {"first_text": delta(first_text, anchors["last_sample"]),
                                "first_pcm": delta(first_pcm, anchors["last_sample"]),
                                "accepted_transcript": delta(accepted_at, anchors["last_sample"])},
        "seed_exclusion": "parent user turn lineage; every accepted input epoch",
    }


def trace_events(trace):
    for row in trace.get("events", []) if isinstance(trace, dict) else []:
        event = row.get("event")
        if isinstance(event, dict):
            yield {**event, "trace_elapsed_ms": row.get("elapsed_ms")}


def raw_asr(trace):
    rows = [e for e in trace_events(trace) if e.get("type") == "debug_model"
            and e.get("phase") == "asr_event"]
    # Provider EOT is a diagnostic point, distinct from local accepted user
    # transcript. Provider text is revision prone; final segments only.
    primary = [e for e in rows if not e.get("shadow")]
    finals = [e for e in primary if e.get("event_type") == "final"]
    eots = [e for e in primary if e.get("event_type") == "turn_end"]
    return {"final_segments": [e.get("segment") or e.get("text") for e in finals],
            "provider_eot_trace_elapsed_ms": [e.get("trace_elapsed_ms") for e in eots],
            "provider_eot_count": len(eots),
            "provider_eot_note": "server trace clock; not subtracted from client input anchors"}


def usage_cost(row, trace, pricing):
    usage = row.get("usage") or {}
    records = usage.get("request_records") or []
    # Recover from trace if a partial row has not yet been enriched by export.
    if not records and trace:
        for e in trace_events(trace):
            if e.get("type") == "debug_model" and e.get("phase") == "thinking_finished":
                for request in (e.get("timings") or {}).get("http_requests", []):
                    records.append({"provider": "cerebras", "usage": request.get("usage")})
            if e.get("type") == "jev_policy_outcomes":
                for outcome in e.get("outcomes", []):
                    result = outcome.get("result") or {}
                    records.append({"provider": "jev", "usage": (result.get("response") or {}).get("usage")})
    qwen = pricing["cerebras"]["models"]["qwen-3.8-27b"]
    unknown = []
    by_component = defaultdict(float)
    token_counts = defaultdict(int)
    for rec in records:
        tokens = rec.get("usage") or {}
        provider = rec.get("provider")
        prompt = tokens.get("prompt_tokens", tokens.get("input_tokens"))
        completion = tokens.get("completion_tokens", tokens.get("output_tokens"))
        if not number(prompt) or (provider == "cerebras" and not number(completion)):
            unknown.append(f"{provider}_request_usage")
            continue
        if provider == "cerebras":
            by_component["qwen_model"] += (prompt*qwen["input_usd_per_million_tokens"] +
                                            completion*qwen["output_usd_per_million_tokens"])/1e6
        elif provider == "jev":
            # Public JEV rate is input-only; response tokens are free.
            by_component["jev"] += prompt*JEV_USD_PER_M/1e6
        else:
            unknown.append("unknown_provider_rate")
        token_counts[f"{provider}_input"] += prompt
        if number(completion):
            token_counts[f"{provider}_output"] += completion
    if usage.get("model_failures_without_usage"):
        unknown.append("failed_model_requests")
    tts = usage.get("tts_completed_sequences") or []
    diagnostic = usage.get("tts_phrase_diagnostics") or []
    chars = sum(x["characters"] for x in tts if number(x.get("characters")))
    # A phrase can incur charges without a latency completion event.
    if len(diagnostic) > len(tts):
        unknown.append("cancelled_or_unfinished_tts_phrases")
    if any(not number(x.get("characters")) for x in tts):
        unknown.append("tts_characters")
    by_component["tts_completed"] = chars * pricing["elevenlabs"]["usd_per_1000_characters"] / 1000
    accounting = next((x for x in reversed(usage.get("asr_streams") or []) if isinstance(x, dict)), {})
    # New traces nest streams alongside the provider timing summary. Older
    # smoke traces stored the streams dictionary directly.
    streams = accounting.get("streams", accounting)
    timing_summary = accounting.get("timing_summary")
    asr = {}
    arm = row.get("arm", "")
    provider = arm.split("-")[0]
    for name, stream in streams.items():
        if not isinstance(stream, dict):
            continue
        seconds = stream.get("pcm_seconds")
        stream_provider = "scribe" if name == "shadow" else (
            stream.get("provider") or (provider if provider in ASR_RATES_PER_HOUR else None))
        if not number(seconds) or stream_provider not in ASR_RATES_PER_HOUR:
            unknown.append(f"{name}_asr_pcm_seconds_or_rate")
            continue
        rates = ASR_RATES_PER_HOUR[stream_provider]
        rate = rates["regular"]
        by_component[f"asr_{name}_regular_proxy"] += seconds / 3600 * rate
        asr[name] = {"sent_pcm_seconds": seconds,
                     "connected_duration_s": stream.get("connected_duration_s"),
                     "regular_rate_usd_per_hour": rate,
                     "promo_rate_usd_per_hour": rates.get("promo"),
                     "promo_proxy_usd": round(seconds/3600*rates["promo"], 9) if "promo" in rates else None,
                     "dropped_pcm_bytes": stream.get("dropped_pcm_bytes")}
    if not streams:
        unknown.append("asr_accounting")
    if not records:
        unknown.append("model_or_jev_request_accounting")
    # ASR duration is a billed-seconds proxy and excluded from the captured
    # usage subtotal; it can include startup and trailing silence.
    measured = sum(value for key, value in by_component.items() if not key.startswith("asr_"))
    return {"captured_usage_listed_rate_subtotal_usd": round(measured, 9),
            "regular_asr_duration_proxy_usd": round(sum(v for k,v in by_component.items() if k.startswith("asr_")), 9),
            "components_usd": {k: round(v, 9) for k,v in by_component.items()},
            "tokens": dict(token_counts), "tts_completed_characters": chars,
            "asr_streams": asr, "asr_timing_summary": timing_summary,
            "unknown_components": sorted(set(unknown)),
            "cost_basis": "captured usage at listed rates, excluding unreported costs; account discounts and invoice unknown",
            "invoice_total_known": False}


def jev_diagnostics(trace):
    events = list(trace_events(trace))
    phase = Counter(e.get("phase") for e in events if e.get("type") == "debug_model"
                    and str(e.get("phase", "")).startswith("jev_"))
    results = [e for e in events if e.get("type") == "debug_model" and e.get("phase") == "jev_result"]
    application_phases = {"jev_turn_applied", "jev_wait_applied"}
    applications = []
    latest_result_by_turn = {}
    for event in events:
        if event.get("type") != "debug_model":
            continue
        turn = event.get("provider_turn_id")
        if event.get("phase") == "jev_result" and turn is not None:
            latest_result_by_turn[turn] = event
        elif event.get("phase") in application_phases:
            result = latest_result_by_turn.get(turn)
            # A matching provider turn and event order are needed. In older
            # traces source is absent, so the origin remains unknown.
            origin = result.get("source") if result is not None else None
            applications.append({"phase": event["phase"], "provider_turn_id": turn,
                                 "decision": event.get("decision"),
                                 "decision_origin": origin if isinstance(origin, str) else None,
                                 "result_matched": result is not None})
    app_sources = Counter(a["decision_origin"] for a in applications if a["decision_origin"])
    sources = [e.get("source") for e in results]
    source_counts = Counter(source for source in sources if isinstance(source, str) and source)
    drained = [e for e in events if e.get("type") == "jev_policy_outcomes"]
    outcomes = [x for e in drained for x in e.get("outcomes", [])]
    provider_answers = []
    for item in outcomes:
        response = (item.get("result") or {}).get("response") or {}
        answer = (response.get("answers") or {}).get("turn_intent") or {}
        if answer:
            provider_answers.append({"endpoint_id": item.get("endpoint_id"),
                                     "choice": answer.get("choice"),
                                     "probabilities": answer.get("probabilities"),
                                     "confidence": answer.get("confidence"),
                                     "wall_latency_ms": (item.get("result") or {}).get("wall_latency_ms")})
    return {"requests": phase["jev_request"],
            "resolved_decision_events": len(applications),
            "resolved_decisions_by_origin": dict(app_sources),
            "provider_advice_returned": source_counts["jev"],
            "provider_advice_applied": app_sources["jev"],
            "local_or_other_decisions_applied": sum(count for source,count in app_sources.items() if source != "jev"),
            "applied_decision_origin_unknown": len(applications)-sum(app_sources.values()),
            "decision_application_receipts": applications,
            "late": phase["jev_late"], "stale_local_state": phase["jev_local_state_changed"],
            "failed": phase["jev_failed"],
            "application_source_recorded": bool(results) and sum(source_counts.values()) == len(results),
            "application_sources": dict(source_counts),
            "application_source_unknown_results": len(results) - sum(source_counts.values()),
            "decision_counts": dict(Counter(e.get("decision", "unknown") for e in results)),
            "latency_ms": [e.get("latency_ms") for e in results if number(e.get("latency_ms"))],
            "deadline_fallbacks": source_counts["deadline_fallback"] if sum(source_counts.values()) == len(results) else None,
            "busy_fallbacks": source_counts["busy_fallback"] if sum(source_counts.values()) == len(results) else None,
            "fallback_note": "Unknown when a jev_result trace omits TurnAdvice.source",
            "drained": drained[-1].get("drained") if drained else None,
            "drained_outcomes": len(outcomes),
            "raw_provider_answers_unrated": provider_answers,
            "drained_result_status": dict(Counter((x.get("result") or {}).get("status", "unknown") for x in outcomes)),
            "drained_error_types": dict(Counter((x.get("result") or {}).get("error_type") for x in outcomes
                                               if (x.get("result") or {}).get("error_type"))),
            "drained_usage_outcomes": sum(isinstance(((x.get("result") or {}).get("response") or {}).get("usage"), dict)
                                          for x in outcomes)}


def error_categories(row, trace):
    categories = set()
    if row.get("status") == "timeout": categories.add("trial_timeout")
    if row.get("status") == "failed":
        categories.add("trial_failed")
        kind = (row.get("error") or {}).get("type")
        if kind: categories.add("exception_" + kind)
    if row.get("trace_export_error"): categories.add("trace_export")
    if row.get("condition_valid") is False: categories.add("invalid_condition")
    if any(e.get("type") == "error" for e in row.get("events", [])): categories.add("client_error_event")
    for e in trace_events(trace):
        if e.get("type") == "debug_model" and e.get("phase") in ("model_failed", "transport_failure"):
            categories.add(e["phase"])
        if e.get("type") == "debug_model" and e.get("phase") == "asr_event" and e.get("event_type") == "error":
            categories.add("asr_error")
        if e.get("type") == "debug_model" and e.get("phase") == "asr_event" and e.get("shadow") and (
                (e.get("metadata") or {}).get("original_event_type") == "error"):
            categories.add("shadow_asr_error")
    return sorted(categories)


def analyze_row(row, trace, pricing):
    timing = timing_and_transcript(row)
    case = CASES[row["case_id"]]
    transcript = timing["accepted_transcript"]
    condition_valid = row.get("status") in ("complete", "timeout") and row.get("condition_valid") is not False
    if case.seed_text and row.get("condition_valid") is not True:
        condition_valid = False
    completed_valid = condition_valid and row.get("status") == "complete"
    score = spec.score_trial(case, events=events_after_input(row),
        transcript=[{"role": "user", "text": transcript}], audio_clock=row.get("audio_clock") or {},
        accepted_transcript=transcript, active_user_turn_id=timing["final_user_turn_id"],
        input_user_turn_ids=timing["accepted_user_turn_ids"], input_start_ms=row.get("input_start_ms"),
        seed_turn_id=row.get("seed_turn_id"), task_receipts=row.get("runtime_receipts"))
    return {"order": row["order"], "case_id": case.id, "arm": row["arm"],
            "kind": row.get("kind"), "repetition": row["repetition"],
            "status": row.get("status"), "terminal_outcome": row.get("outcome"),
            "condition_valid": row.get("condition_valid"),
            "experimental_condition_valid": condition_valid,
            "comparable_valid": completed_valid,
            "capture_completed": row.get("status") == "complete",
            "error_categories": error_categories(row, trace),
            "timing": timing, "raw_asr": raw_asr(trace),
            "wer": spec.word_error_rate(" ".join(case.expected_transcript), transcript) if transcript else None,
            "wer_normalization": "casefold, punctuation removed, apostrophes internal; no synonym/entity aliases",
            "gates": score["hard_gates"], "metrics": score["metrics"],
            "mechanical_checks": {key: value.get("pass") if value.get("available") is True else None
                                  for key,value in score["metrics"].items()
                                  if isinstance(value, dict) and "pass" in value},
            "jev": jev_diagnostics(trace), "model": model_diagnostics(trace),
            "cost": usage_cost(row, trace, pricing),
            "output_audio": row.get("output_audio") or [],
            "seed_turn_id": row.get("seed_turn_id"),
            "trace_available": bool(trace)}


def model_diagnostics(trace):
    events = list(trace_events(trace))
    commits = [e for e in events if e.get("type") == "debug_model" and e.get("phase") == "user_committed"]
    finished = [e for e in events if e.get("type") == "debug_model" and e.get("phase") == "thinking_finished"]
    requests = [request for e in finished for request in (e.get("timings") or {}).get("http_requests", [])]
    pairs = []
    for finish in finished:
        revision, end = finish.get("revision"), finish.get("trace_elapsed_ms")
        matching = [commit for commit in commits if revision is not None
                    and commit.get("revision") == revision and number(commit.get("trace_elapsed_ms"))
                    and number(end) and commit["trace_elapsed_ms"] <= end]
        # A revision plus a unique preceding commit is required. Seed and
        # resumed turns can otherwise be accidentally crossed.
        pairs.append(delta(end, matching[0]["trace_elapsed_ms"]) if len(matching) == 1 else None)
    return {"user_commit_trace_elapsed_ms": [e.get("trace_elapsed_ms") for e in commits],
            "thinking_finished_trace_elapsed_ms": [e.get("trace_elapsed_ms") for e in finished],
            "commit_to_thinking_finished_ms_by_revision": pairs,
            "commit_to_thinking_finished_ms": pairs[0] if len(pairs) == 1 else None,
            "http_requests": [{"status": q.get("status"), "headers_ms": q.get("headers_ms"),
                               "total_ms": q.get("total_ms"), "reasoning_tokens":
                               ((q.get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens")}
                              for q in requests]}


def aggregate(rows):
    result = {}
    for arm in sorted({r["arm"] for r in rows}):
        group = [r for r in rows if r["arm"] == arm]
        valid = [r for r in group if r["experimental_condition_valid"]]
        complete_valid = [r for r in valid if r["comparable_valid"]]
        result[arm] = {"attempted": len(group), "status": dict(Counter(r["status"] for r in group)),
                       "condition_invalid": sum(r["condition_valid"] is False for r in group),
                       "experimental_condition_valid": len(valid),
                       "condition_valid_timeout": sum(r["status"] == "timeout" for r in valid),
                       "comparable_valid": len(complete_valid),
                       "error_categories": dict(Counter(c for r in group for c in r["error_categories"])),
                       "wer_median_valid_only": percentile([r["wer"] for r in valid if r["wer"] is not None], .5),
                       "wer_n": sum(r["wer"] is not None for r in valid),
                       "timing_condition_valid_all_statuses": {key: {"n": len(values := [r["timing"]["from_last_nonsilent_ms"][key]
                                                for r in valid if number(r["timing"]["from_last_nonsilent_ms"][key])]),
                                              "median_ms": percentile(values, .5), "p90_ms": percentile(values, .9)}
                                             for key in ("accepted_transcript", "first_text", "first_pcm")},
                       "cost_captured_usage_listed_rate_subtotal_usd_all_attempts": round(sum(r["cost"]["captured_usage_listed_rate_subtotal_usd"] for r in group), 8),
                       "asr_regular_proxy_usd_all_attempts": round(sum(r["cost"]["regular_asr_duration_proxy_usd"] for r in group), 8),
                       "unknown_cost_attempts": sum(bool(r["cost"]["unknown_components"]) for r in group)}
    return result


def per_case_checks(rows):
    """Gate counts only within the case to which each check applies."""
    result = {}
    for case, arm in sorted({(r["case_id"], r["arm"]) for r in rows}):
        group = [r for r in rows if r["case_id"] == case and r["arm"] == arm]
        valid = [r for r in group if r["experimental_condition_valid"]]
        def tally(field):
            return {name: {"pass": sum(r[field].get(name) is True for r in valid),
                           "fail": sum(r[field].get(name) is False for r in valid),
                           "unmeasured_or_not_applicable": sum(r[field].get(name) is None for r in valid)}
                    for name in sorted({name for r in valid for name in r[field]})
                    if any(r[field].get(name) is not None for r in valid)}
        result[f"{case}::{arm}"] = {"case_id": case, "arm": arm, "attempted": len(group),
                                     "condition_valid": len(valid),
                                     "gates": tally("gates"), "mechanical_checks": tally("mechanical_checks")}
    return result


def per_case_arm_timing(rows):
    """Observed timings by fixture and arm, with explicit sample counts."""
    result = {}
    for case, arm in sorted({(r["case_id"], r["arm"]) for r in rows}):
        group = [r for r in rows if r["case_id"] == case and r["arm"] == arm]
        eligible = [r for r in group if r["experimental_condition_valid"]]
        def measure(field):
            values = [r["timing"]["from_last_nonsilent_ms"][field] for r in eligible
                      if number(r["timing"]["from_last_nonsilent_ms"][field])]
            return {"n": len(values), "median_ms": percentile(values, .5),
                    "p90_ms": percentile(values, .9)}
        result[f"{case}::{arm}"] = {
            "case_id": case, "arm": arm, "attempted": len(group),
            "status": dict(Counter(r["status"] for r in group)),
            "condition_valid": len(eligible),
            "completed_comparable": sum(r["comparable_valid"] for r in group),
            "expected_reply": CASES[case].expected_reply,
            "wer_n": sum(r["wer"] is not None for r in eligible),
            "wer_median": percentile([r["wer"] for r in eligible if number(r["wer"])], .5),
            "accepted_transcript": measure("accepted_transcript"),
            "first_text": measure("first_text") if CASES[case].expected_reply else None,
            "first_pcm": measure("first_pcm") if CASES[case].expected_reply else None,
        }
    return result


def jev_by_arm(rows):
    result = {}
    for arm in sorted({r["arm"] for r in rows if "jev-on" in r["arm"]}):
        group = [r["jev"] for r in rows if r["arm"] == arm]
        result[arm] = {"attempted": len(group),
                       "requests": sum(x["requests"] for x in group),
                       "resolved_decision_events": sum(x["resolved_decision_events"] for x in group),
                       "provider_advice_returned": sum(x["provider_advice_returned"] for x in group),
                       "provider_advice_applied": sum(x["provider_advice_applied"] for x in group),
                       "local_or_other_decisions_applied": sum(x["local_or_other_decisions_applied"] for x in group),
                       "application_origin_unknown": sum(x["applied_decision_origin_unknown"] for x in group),
                       "decision_sources": dict(sum((Counter(x["application_sources"]) for x in group), Counter())),
                       "late_event_count": sum(x["late"] for x in group),
                       "drained_outcomes": sum(x["drained_outcomes"] for x in group),
                       "drained_usage_outcomes": sum(x["drained_usage_outcomes"] for x in group),
                       "drained_result_status": dict(sum((Counter(x["drained_result_status"]) for x in group), Counter()))}
    return result


def paired(rows):
    by = {(r["case_id"], r["repetition"], r["arm"]): r for r in rows}
    result = {}
    for provider in ("nova", "flux", "scribe"):
        arm_off, arm_on = provider+"-jev-off", provider+"-jev-on"
        keys = {(r["case_id"], r["repetition"]) for r in rows if r["arm"] in (arm_off, arm_on)}
        pairs = [(by.get((case, rep, arm_off)), by.get((case, rep, arm_on))) for case,rep in sorted(keys)]
        comparable = [(a,b) for a,b in pairs if a and b and a["comparable_valid"] and b["comparable_valid"]]
        def differences(path):
            values = [(path(b)-path(a)) for a,b in comparable if number(path(a)) and number(path(b))]
            return {"n": len(values), "median_on_minus_off": percentile(values, .5),
                    "values": [round(v,3) for v in values]}
        result[provider] = {"possible_pairs": len(keys), "both_attempted": sum(bool(a and b) for a,b in pairs),
                            "comparable_valid_pairs": len(comparable),
                            "excluded_pairs": [{"case_id": (a or b)["case_id"], "repetition": (a or b)["repetition"],
                                                "off_status": a["status"] if a else "not_attempted",
                                                "on_status": b["status"] if b else "not_attempted"}
                                               for a,b in pairs if (a,b) not in comparable],
                            "wer": differences(lambda r:r["wer"]),
                            "first_pcm_from_last_nonsilent_ms": differences(lambda r:r["timing"]["from_last_nonsilent_ms"]["first_pcm"]),
                            "accepted_from_last_nonsilent_ms": differences(lambda r:r["timing"]["from_last_nonsilent_ms"]["accepted_transcript"])}
    return result


def paired_asr(rows):
    """Pair providers by the same fixture, repetition and JEV setting."""
    by = {(r["case_id"], r["repetition"], r["arm"]): r for r in rows}
    result = {}
    for jev in ("off", "on"):
        for left, right in (("nova", "flux"), ("nova", "scribe"), ("flux", "scribe")):
            left_arm, right_arm = f"{left}-jev-{jev}", f"{right}-jev-{jev}"
            keys = {(r["case_id"], r["repetition"]) for r in rows if r["arm"] in (left_arm, right_arm)}
            pairs = [(by.get((case,rep,left_arm)), by.get((case,rep,right_arm))) for case,rep in sorted(keys)]
            valid = [(a,b) for a,b in pairs if a and b and a["comparable_valid"] and b["comparable_valid"]]
            def difference(field):
                values = [field(b)-field(a) for a,b in valid if number(field(a)) and number(field(b))]
                return {"n": len(values), "median_right_minus_left": percentile(values,.5)}
            result[f"{left}_vs_{right}_jev_{jev}"] = {
                "left": left_arm, "right": right_arm, "possible_pairs": len(keys),
                "both_attempted": sum(bool(a and b) for a,b in pairs), "comparable_valid_pairs": len(valid),
                "wer": difference(lambda r:r["wer"]),
                "accepted_transcript_ms": difference(lambda r:r["timing"]["from_last_nonsilent_ms"]["accepted_transcript"]),
                "first_pcm_ms": difference(lambda r:r["timing"]["from_last_nonsilent_ms"]["first_pcm"]),
            }
    return result


def shadow_overlap(trace):
    rows = [e for e in trace_events(trace) if e.get("type") == "debug_model" and e.get("phase") == "asr_event"
            and (e.get("event_type") == "final" or
                 (e.get("shadow") and (e.get("metadata") or {}).get("original_event_type") in ("final", "alignment")))]
    def words(e):
        result = []
        for w in e.get("words") or []:
            token = normal(w.get("word") or w.get("text"))
            start, end = w.get("start", w.get("start_time")), w.get("end", w.get("end_time"))
            if token and number(start) and number(end) and end > start:
                result.append((token[0], float(start), float(end)))
        return result
    primary_finals = [e for e in rows if not e.get("shadow") and e.get("event_type") == "final"]
    shadow_finals = [e for e in rows if e.get("shadow") and
                     (e.get("metadata") or {}).get("original_event_type") == "final"]
    shadow_alignments = [e for e in rows if e.get("shadow") and
                         (e.get("metadata") or {}).get("original_event_type") == "alignment"]
    primary = [w for e in primary_finals for w in words(e)]
    shadow = [w for e in shadow_alignments for w in words(e)]
    matched = []
    used = set()
    for token, start, end in primary:
        choices = [(j, other) for j, other in enumerate(shadow) if j not in used
                   and max(start,other[1]) < min(end,other[2])]
        if choices:
            j, other = max(choices, key=lambda x:min(end,x[1][2])-max(start,x[1][1]))
            used.add(j)
            matched.append({"audio_interval_s": [round(max(start,other[1]),3), round(min(end,other[2]),3)],
                            "flux": token, "scribe": other[0], "agree": token == other[0]})
    return {"flux_final_transcript": " ".join(str(e.get("segment") or "") for e in primary_finals).strip(),
            "scribe_final_transcript": " ".join(str(e.get("segment") or "") for e in shadow_finals).strip(),
            "flux_timed_words": len(primary), "scribe_timed_words": len(shadow),
            "same_audio_overlap_words": len(matched), "matches": sum(x["agree"] for x in matched),
            "aligned_words": matched,
            "disagreements": [x for x in matched if not x["agree"]],
            "coverage_note": "Timestamp overlap only; missing timestamps or partial audio cannot establish agreement. No transcript fusion was tested."}


def shadow_comparison(shadow_trials, shadow_diagnostics, main_trials):
    """Compare passive shadow rows only to matching main Flux rows."""
    main_by_key = {(x["case_id"], x["repetition"], x["arm"]): x for x in main_trials
                   if x["arm"] in ("flux-jev-off", "flux-jev-on")}
    result = []
    for row in shadow_trials:
        suffix = row["arm"].rsplit("-jev-", 1)[-1]
        key = (row["case_id"], row["repetition"], "flux-jev-"+suffix)
        main = main_by_key.get(key)
        diag = shadow_diagnostics.get(str(row["order"])) or {}
        reference = " ".join(CASES[row["case_id"]].expected_transcript)
        flux_raw = diag.get("flux_final_transcript", "")
        scribe_raw = diag.get("scribe_final_transcript", "")
        streams = row["cost"]["asr_streams"]
        shadow_stream = streams.get("shadow") or {}
        result.append({"shadow_order": row["order"], "case_id": row["case_id"],
                       "repetition": row["repetition"], "jev": suffix,
                       "shadow_status": row["status"],
                       "matched_main_order": main["order"] if main else None,
                       "matched_main_status": main["status"] if main else None,
                       "gold_user_transcript": reference,
                       "main_flux_accepted_transcript": main["timing"]["accepted_transcript"] if main else None,
                       "shadow_flux_accepted_transcript": row["timing"]["accepted_transcript"],
                       "shadow_flux_provider_final": flux_raw,
                       "shadow_scribe_provider_final": scribe_raw,
                       "flux_raw_wer_vs_gold": spec.word_error_rate(reference, flux_raw) if flux_raw else None,
                       "scribe_raw_wer_vs_gold": spec.word_error_rate(reference, scribe_raw) if scribe_raw else None,
                       "same_audio_alignment": {k: diag.get(k) for k in
                          ("flux_timed_words", "scribe_timed_words", "same_audio_overlap_words",
                           "matches", "disagreements", "aligned_words", "coverage_note")},
                       "shadow_sent_pcm_seconds": shadow_stream.get("sent_pcm_seconds"),
                       "shadow_dropped_pcm_bytes": shadow_stream.get("dropped_pcm_bytes"),
                       "shadow_regular_duration_proxy_usd": row["cost"]["components_usd"].get("asr_shadow_regular_proxy"),
                       "interpretation": "Passive transcript diagnostic; no active fusion or causal quality claim"})
    return result


def blind_packet(rows, run, out, *, seed=20260930):
    eligible = [r for r in rows if r["comparable_valid"] and r["output_audio"]]
    rng = random.Random(seed)
    rng.shuffle(eligible)
    key, packet = {}, []
    media = out / "review_audio"
    media.mkdir(exist_ok=True)
    for index, row in enumerate(eligible, 1):
        code = f"clip-{index:03d}"
        copied = []
        for part, item in enumerate(row["output_audio"], 1):
            if row.get("seed_turn_id") and item.get("turn_id") == row["seed_turn_id"]:
                continue
            filename = item.get("file")
            if not filename or Path(filename).name != filename:
                continue
            source = run / filename
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != item.get("sha256"):
                continue
            target = media / f"{code}-{part}.wav"
            shutil.copyfile(source, target)
            copied.append(str(target.relative_to(out)).replace("\\", "/"))
        if copied:
            key[code] = {"arm": row["arm"], "case_id": row["case_id"], "repetition": row["repetition"],
                         "order": row["order"]}
            packet.append({"blind_id": code, "case_id": row["case_id"],
                           "prompt": " ".join(CASES[row["case_id"]].expected_transcript),
                           "audio": copied, "questions": ["Is the speech in this saved audio intelligible?",
                           "How natural is the prosody and pacing of the captured speech?",
                           "Is the audible answer content appropriate to the stated request, where present?"],
                           "ratings": None})
    write(out / "blind_review_packet.json", {"schema_version": 1, "human_ratings": "pending",
          "instructions": "Rate without opening secret_arm_key.json. WAVs concatenate returned PCM and omit transport gaps, reset truncation and user overlap. They may contain speech later cancelled by the software queue. Judge only captured speech content, intelligibility and prosody; these files do not reconstruct an audible conversation or establish floor behavior. Browser, acoustic and physical playback are unmeasured.",
          "items": packet})
    write(out / "secret_arm_key.json", key)
    return len(packet)


def semantic_packet(attempts, out: Path, *, seed=20260930):
    """Anonymous textual packet for independent case-oracle review.

    Every attempted trial is included, even a transport failure. The key is
    saved separately and the grader packet uses a strict event allowlist.
    """
    rng = random.Random(seed + 1)
    shuffled = list(attempts)
    rng.shuffle(shuffled)
    items, key = [], {}
    floor_phases = {"floor_preserved", "floor_backchannel_kept", "user_committed",
                    "speech_started", "turn_resumed"}
    for index, row in enumerate(shuffled, 1):
        case = CASES[row["case_id"]]
        code = f"review-{index:03d}"
        input_start = row.get("input_start_ms")
        events = events_after_input(row)
        seed = row.get("seed_turn_id")
        seed_speech = [str(e.get("text") or "") for e in row.get("events", [])
                       if isinstance(e, dict) and e.get("type") == "transcript_done"
                       and e.get("role") == "assistant" and seed
                       and e.get("benchmark_turn_id") == seed]
        chronology = []
        for event in events:
            kind = event.get("type")
            if kind in ("transcript_done", "transcript_delta"):
                if event.get("role") not in ("user", "assistant"):
                    continue
                chronology.append({"relative_ms": delta(event.get("t_ms"), input_start),
                                   "event": kind, "role": event.get("role"),
                                   "text": str(event.get("text") or "")})
            elif kind == "audio_reset":
                chronology.append({"relative_ms": delta(event.get("t_ms"), input_start),
                                   "event": "audio_reset", "was_playing": event.get("was_playing"),
                                   "queue_active_before_reset": event.get("software_queue_was_active_before_reset")})
            elif kind == "face":
                chronology.append({"relative_ms": delta(event.get("t_ms"), input_start),
                                   "event": "face_state", "expression": event.get("expression"),
                                   "variant": event.get("variant"), "visible_frame_measured": False})
            elif kind == "debug_model" and event.get("phase") in floor_phases:
                chronology.append({"relative_ms": delta(event.get("t_ms"), input_start),
                                   "event": "floor_state", "phase": event["phase"],
                                   "text": str(event.get("text") or "")})
        receipts = []
        for receipt in row.get("runtime_receipts") or []:
            event = receipt.get("event") or {}
            if isinstance(event, dict):
                receipts.append({"event_type": event.get("type"),
                                 "tool": event.get("name", event.get("tool")),
                                 "state": event.get("state", event.get("status")),
                                 "success": event.get("success"),
                                 "visible_delivery_measured": False})
        key[code] = {"arm": row["arm"], "case_id": case.id,
                     "repetition": row["repetition"], "order": row["order"]}
        items.append({"blind_id": code, "case_id": case.id,
                      "case_class": case.class_name,
                      "gold_user_transcript": list(case.expected_transcript),
                      "semantic_constraints": list(case.semantic_constraints),
                      "seed_assistant_context_from_case_spec": case.seed_text,
                      "seed_assistant_response_recorded": seed_speech,
                      "expected_reply": case.expected_reply,
                      "expected_stop": case.expected_stop,
                      "preserve_backchannel": case.preserve_backchannel,
                      "status": row.get("status"),
                      "condition_valid": row.get("condition_valid"),
                      "input_started": number(input_start),
                      "accepted_user_transcript": timing_and_transcript(row)["accepted_transcript"],
                      "response_audio_captured": any(not row.get("seed_turn_id") or a.get("turn_id") != row.get("seed_turn_id")
                                                     for a in row.get("output_audio") or []),
                      "post_input_chronology": chronology,
                      "sanitized_runtime_receipts": receipts,
                      "judgments": None})
    quality = out / "quality"
    write(quality / "semantic_review_packet.json", {
        "schema_version": 1, "items": items,
        "instructions": "Grade case semantics using the frozen rubric. Every attempted trial is present. Do not consult the secret arm key. Floor, reset and tool records are event receipts; face events are state receipts and visible delivery is unmeasured. Audio naturalness needs separate listening."})
    write(quality / "secret_semantic_key.json", key)
    return len(items)


def markdown(summary):
    lines = ["# Streaming speech comparison", "", f"Generated {summary['generated_utc']}. Trials are synthetic cached audio, two repetitions per case. Human/audio naturalness is unrated; browser, acoustic and physical playback are unmeasured.", "",
             "## Attempt accounting", "", "| Arm | Attempted | Complete | Timeout | Failed | Valid condition | Completed comparable | Median WER | First PCM median ms | Captured usage at listed rates USD |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for arm, a in summary["by_arm"].items():
        lines.append(f"| {arm} | {a['attempted']} | {a['status'].get('complete',0)} | {a['status'].get('timeout',0)} | {a['status'].get('failed',0)} | {a['experimental_condition_valid']} | {a['comparable_valid']} | {a['wer_median_valid_only']} | {a['timing_condition_valid_all_statuses']['first_pcm']['median_ms']} | {a['cost_captured_usage_listed_rate_subtotal_usd_all_attempts']:.6f} |")
    lines += ["", "WER, gates and observed timing include condition-valid timeouts; statuses and captured cost retain every attempt. Paired deltas require completed trials on both sides. WER is a diagnostic against synthetic gold words. Provider end-of-turn timestamps and local accepted transcript timestamps have different clocks and meanings. Across-case first-PCM medians mix different case compositions and must not be used to rank providers.", "", "## Paired Nova, Flux and Scribe", "", "Right minus left on the same case, repetition and JEV setting. Only completed valid pairs enter deltas.", "", "| Pair | Valid pairs | WER delta | Accepted transcript delta ms | First PCM n | First PCM delta ms |", "|---|---:|---:|---:|---:|---:|"]
    for name,p in summary["paired_asr"].items():
        lines.append(f"| {p['left']} → {p['right']} | {p['comparable_valid_pairs']}/{p['possible_pairs']} | {p['wer']['median_right_minus_left']} | {p['accepted_transcript_ms']['median_right_minus_left']} | {p['first_pcm_ms']['n']} | {p['first_pcm_ms']['median_right_minus_left']} |")
    lines += ["", "## Paired JEV on minus off", "", "These are configuration pairs, not credited JEV effects. Provider segmentation can differ between trials. `trials.json` separates a resolved endpoint decision from advice actually returned by JEV and applied to that same provider turn; later drained responses are diagnostic only.", "", "| ASR | Valid pairs | WER median delta | First PCM n | First PCM median delta ms | Accepted transcript median delta ms |", "|---|---:|---:|---:|---:|---:|"]
    for provider,p in summary["paired_jev"].items():
        lines.append(f"| {provider} | {p['comparable_valid_pairs']}/{p['possible_pairs']} | {p['wer']['median_on_minus_off']} | {p['first_pcm_from_last_nonsilent_ms']['n']} | {p['first_pcm_from_last_nonsilent_ms']['median_on_minus_off']} | {p['accepted_from_last_nonsilent_ms']['median_on_minus_off']} |")
    lines += ["", "## JEV decision provenance", "", "A resolved turn after a local fallback is counted under the fallback source. Drained provider outcomes and usage do not establish that advice affected the turn.", "", "| JEV-on arm | Requests | Provider advice applied | Local/other decisions applied | Source unknown | Deadline fallback results | Drained outcomes | Drained usage |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for arm, row in summary["jev_by_arm"].items():
        lines.append(f"| {arm} | {row['requests']} | {row['provider_advice_applied']} | {row['local_or_other_decisions_applied']} | {row['application_origin_unknown']} | {row['decision_sources'].get('deadline_fallback',0)} | {row['drained_outcomes']} | {row['drained_usage_outcomes']} |")
    lines += ["", "## Normal turn first returned PCM", "", "Two repetitions were planned. Sample counts below include only condition-valid attempts with returned PCM; timing is relative to the last nonsilent input sample.", "", "| Arm | Attempted | Complete | First PCM n | Median ms | Accepted transcript n | Median ms |", "|---|---:|---:|---:|---:|---:|---:|"]
    for arm in summary["by_arm"]:
        row = summary["per_case_arm_timing"].get(f"normal_end::{arm}")
        if row:
            lines.append(f"| {arm} | {row['attempted']} | {row['status'].get('complete',0)} | {row['first_pcm']['n']} | {row['first_pcm']['median_ms']} | {row['accepted_transcript']['n']} | {row['accepted_transcript']['median_ms']} |")
    lines += ["", "## Case gates", "", "Each cell is pass/fail/unmeasured among condition-valid attempts, including timeouts. Attempt and error counts stay in the arm table and summary.json.", "", "| Case | Arm | Condition-valid | Gate outcomes |", "|---|---|---:|---|"]
    for case_id in CASES:
        for arm in summary["by_arm"]:
            group = [r for r in summary["trials_for_report"] if r["case_id"] == case_id and r["arm"] == arm and r["experimental_condition_valid"]]
            if not group:
                continue
            gates = "; ".join(f"{name}: {sum(r['gates'].get(name) is True for r in group)}/{sum(r['gates'].get(name) is False for r in group)}/{sum(r['gates'].get(name) is None for r in group)}" for name in group[0]["gates"] if any(r["gates"].get(name) is not None for r in group))
            checks = "; ".join(f"{name}: {sum(r['mechanical_checks'].get(name) is True for r in group)}/{sum(r['mechanical_checks'].get(name) is False for r in group)}/{sum(r['mechanical_checks'].get(name) is None for r in group)}" for name in group[0]["mechanical_checks"] if any(r["mechanical_checks"].get(name) is not None for r in group))
            lines.append(f"| {case_id} | {arm} | {len(group)} | {gates or 'no measured gate'}; {checks or 'no measured check'} |")
    lines += ["", "## Evidence limits", "", "Per-case gates, invalid conditions, errors, raw event diagnostics, both input anchors, pricing assumptions and missing usage are in trials.json and summary.json. The configured 120 ms software queue hold affects state and drain timing; it is not a measured audio startup buffer. Saved WAVs concatenate returned PCM without transport gaps, reset truncation or user overlap and may include speech later cancelled. They cannot establish what was audible or whether the floor was preserved. Tool and face events establish receipt/state only; face delivery requires rendered frames. Raw JEV responses have no gold labels, so their semantic accuracy is unrated. ASR charges use sent PCM seconds as a proxy including silence. Captured usage is priced at listed rates and excludes unreported costs; account discounts and invoice totals are unknown.", "", "Blind audio packet: `blind_review_packet.json`; keep `secret_arm_key.json` hidden from the reviewer. No overall naturalness score is computed."]
    return "\n".join(lines)+"\n"


def analyze(run: Path, out: Path):
    run, out = run.resolve(), out.resolve()
    if run == out or run in out.parents or out in run.parents:
        raise ValueError("Analysis output must be separate from frozen run directory")
    if out.exists():
        raise FileExistsError("Choose a fresh analysis output directory")
    plan = read(run / "plan.frozen.json")
    attempts = read(run / "attempts.json")
    if not isinstance(attempts, list): raise ValueError("Missing attempts list")
    planned = {(t["order"], t["case_id"], t["arm"], t["repetition"]) for t in plan["trials"]}
    seen = set()
    pricing_path = Path(__file__).resolve().parents[2] / "results/architecture-cost-20260928/pricing.json"
    pricing = read(pricing_path)
    rows, shadow = [], {}
    for attempt in attempts:
        identity = (attempt["order"], attempt["case_id"], attempt["arm"], attempt["repetition"])
        if identity not in planned or identity in seen: raise ValueError(f"Unplanned or duplicate attempt: {identity}")
        seen.add(identity)
        trace_name = attempt.get("trace_file")
        trace = read(run / trace_name) if trace_name and Path(trace_name).name == trace_name and (run / trace_name).is_file() else {}
        if trace_name and trace and attempt.get("trace_sha256") and hashlib.sha256((run / trace_name).read_bytes()).hexdigest() != attempt["trace_sha256"]:
            raise ValueError("Trace hash changed")
        result = analyze_row(attempt, trace, pricing)
        rows.append(result)
        if "shadow" in attempt["arm"]:
            shadow[str(attempt["order"])] = shadow_overlap(trace)
    out.mkdir(parents=True)
    write(out / "trials.json", rows)
    summary = {"schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
               "source_run": str(run), "planned": len(planned), "attempted": len(rows),
               "not_attempted": len(planned)-len(rows), "attempt_status": dict(Counter(r["status"] for r in rows)),
               "by_arm": aggregate(rows), "per_case_arm_checks": per_case_checks(rows),
               "per_case_arm_timing": per_case_arm_timing(rows),
               "jev_by_arm": jev_by_arm(rows),
               "paired_asr": paired_asr(rows), "paired_jev": paired(rows),
               "shadow_same_audio_diagnostic": shadow,
               "software_queue_clock": {"configured_hold_ms": plan.get("playback_buffer_ms"),
                                        "meaning": "software state and tail queue drain hold; not an observed startup audio buffer",
                                        "acoustic_playback_measured": False},
               "pricing": {"captured": pricing.get("retrieved_on"),
                           "sources": ["brain/results/architecture-cost-20260928/pricing.json", "brain/results/architecture-cost-20260928/PRICING.md"],
                           "asr_usd_per_hour": ASR_RATES_PER_HOUR,
                           "jev_usd_per_m_tokens": JEV_USD_PER_M,
                           "tts_flash_usd_per_1000_chars": pricing["elevenlabs"]["usd_per_1000_characters"]},
               "unmeasured": ["human prosody and answer quality", "acoustic and browser playback", "visible face delivery", "invoice total", "JEV semantic accuracy"]}
    summary["blind_review_items"] = blind_packet(rows, run, out)
    summary["semantic_review_items"] = semantic_packet(attempts, out)
    write(out / "summary.json", summary)
    (out / "REPORT.md").write_text(markdown({**summary, "trials_for_report": rows}), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run, args.out)
    print(json.dumps({"attempted": result["attempted"], "planned": result["planned"],
                      "output": str(args.out.resolve())}, indent=2))


if __name__ == "__main__": main()
