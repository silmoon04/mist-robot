"""Measured turn-taking metrics. No clock, outcome, or missing value is invented.

Public API: extract_metrics(sample), summarize_run(run), compare_runs(before, after).
A run has a manifest (suite_sha256, adapter, config, run_id) and samples. A sample
has case_id, repeat (default 0), category, status, events, checks, and outcomes.
Events use event (name is accepted), t_ms, turn_id, clock_id (default runner),
optional case_id, and metadata. Tool spans need tool_call_id when
there is more than one call in a turn; repeated interrupts similarly need
metadata.interruption_id. All timestamps are monotonic, run-relative ms.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import math
import random
import statistics
from typing import Any, Iterable


METRIC_PAIRS = {
    "endpoint_delay_ms": ("user_audio_end", "turn_committed", None),
    "asr_final_delay_ms": ("user_audio_end", "asr_final", None),
    "model_ttft_ms": ("turn_committed", "first_text", None),
    "first_tool_ms": ("turn_committed", "first_tool", None),
    "text_response_ms": ("user_audio_end", "first_text", None),
    "first_audio_ms": ("user_audio_end", "playback_started", None),
    "first_useful_audio_ms": ("user_audio_end", "first_useful_audio", None),
    "tool_dispatch_ms": ("tool_requested", "tool_started", "tool_call_id"),
    "tool_duration_ms": ("tool_started", "tool_finished", "tool_call_id"),
    "first_phrase_ms": ("turn_committed", "first_phrase", None),
    "turn_duration_ms": ("turn_committed", "turn_completed", None),
    "interrupt_cutoff_ms": (
        "user_interrupt_onset", "playback_stopped", "interruption_id"
    ),
    "expression_delay_ms": (
        "expression_requested", "expression_applied", "expression_id"
    ),
}
SUCCESS_STATUSES = frozenset({"ok", "passed", "success", "completed", "complete"})
OUTCOME_FIELDS = (
    "false_interruption", "missed_interruption", "task_success",
    "appropriate_expression", "history_correct", "tool_correct",
)
AUDIO_METRICS = frozenset({
    "endpoint_delay_ms", "asr_final_delay_ms", "text_response_ms", "first_audio_ms",
    "first_useful_audio_ms", "interrupt_cutoff_ms",
})


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    index = (len(values) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def distribution(values: Iterable[float]) -> dict[str, Any]:
    """Descriptive interpolated quantiles; a small run does not estimate tails well."""
    clean = sorted(float(value) for value in values if _number(value))
    return {
        "count": len(clean),
        "median": statistics.median(clean) if clean else None,
        "p90": _percentile(clean, .90),
        "p95": _percentile(clean, .95),
        "min": clean[0] if clean else None,
        "max": clean[-1] if clean else None,
        "small_n_warning": (
            "Fewer than 20 observations; tail estimates are unstable."
            if 0 < len(clean) < 20 else None
        ),
    }


def _events(sample: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events, issues = [], []
    raw_events = sample.get("events", [])
    if not isinstance(raw_events, list):
        return [], [{"reason": "invalid_events"}]
    for index, event in enumerate(raw_events):
        reason = None
        if not isinstance(event, dict):
            reason = "invalid_event"
        elif not isinstance(event.get("event", event.get("name")), str):
            reason = "missing_event_name"
        elif not _number(event.get("t_ms")) or event["t_ms"] < 0:
            reason = "invalid_timestamp"
        elif not isinstance(event.get("turn_id"), str) or not event["turn_id"]:
            reason = "missing_turn_id"
        elif not isinstance(event.get("clock_id", "runner"), str) or not event.get("clock_id", "runner"):
            reason = "invalid_clock_id"
        elif event.get("case_id", sample.get("case_id")) != sample.get("case_id"):
            reason = "case_mismatch"
        elif not isinstance(event.get("metadata", {}), dict):
            reason = "invalid_metadata"
        elif event.get("event", event.get("name")) == "first_useful_audio":
            metadata = event.get("metadata", {})
            note = metadata.get("note", metadata.get("annotation_note"))
            if metadata.get("annotation_source") not in ("human", "scenario_rule") or not isinstance(note, str) or not note.strip():
                reason = "missing_useful_audio_annotation"
        if reason is None and isinstance(event, dict):
            for field in ("tool_call_id", "interruption_id", "expression_id"):
                if field in event and field in event.get("metadata", {}) and event[field] != event["metadata"][field]:
                    reason = "conflicting_correlation_id"
        if reason:
            issues.append({"event_index": index, "reason": reason})
            continue
        metadata = dict(event.get("metadata", {}))
        for field in ("tool_call_id", "interruption_id", "expression_id"):
            if field in event:
                metadata[field] = event[field]
        events.append({
            **event,
            "event": event.get("event", event.get("name")),
            "clock_id": event.get("clock_id", "runner"),
            "metadata": metadata,
        })
    return events, issues


def _measure(events: list[dict[str, Any]], start_name: str, end_name: str,
             correlation: str | None) -> tuple[list[float], list[dict[str, Any]]]:
    relevant = [event for event in events if event["event"] in (start_name, end_name)]
    groups: dict[tuple[Any, ...], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for event in relevant:
        correlation_id = event["metadata"].get(correlation) if correlation else None
        if correlation == "tool_call_id" and correlation_id is None:
            return [], [{"reason": "missing_tool_call_id"}]
        if correlation_id is not None and not isinstance(correlation_id, (str, int)):
            return [], [{"reason": "invalid_correlation_id"}]
        groups[(event["turn_id"], event["clock_id"], correlation_id)][event["event"]].append(event["t_ms"])
    values, issues = [], []
    for (turn_id, clock_id, correlation_id), group in groups.items():
        context = {"turn_id": turn_id, "clock_id": clock_id}
        if correlation:
            context[correlation] = correlation_id
        starts, ends = group[start_name], group[end_name]
        if not starts or not ends:
            issues.append({**context, "reason": "missing_endpoint"})
        elif len(starts) != 1 or len(ends) != 1:
            issues.append({**context, "reason": "ambiguous_endpoints"})
        elif ends[0] < starts[0]:
            issues.append({**context, "reason": "negative_latency"})
        else:
            values.append(float(ends[0] - starts[0]))
    if not groups:
        issues.append({"reason": "missing_events"})
    if relevant and not values:
        starts = [event for event in relevant if event["event"] == start_name]
        ends = [event for event in relevant if event["event"] == end_name]
        if starts and ends:
            start_turns = {event["turn_id"] for event in starts}
            end_turns = {event["turn_id"] for event in ends}
            if start_turns.isdisjoint(end_turns):
                issues.append({"reason": "turn_mismatch"})
            elif not any(a["turn_id"] == b["turn_id"] and a["clock_id"] == b["clock_id"]
                         for a in starts for b in ends):
                issues.append({"reason": "clock_mismatch"})
    return values, issues


def score_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Return per-sample medians plus every valid observed span and its issues."""
    events, issues = _events(sample)
    observations, metrics = {}, {}
    for metric, (start, end, correlation) in METRIC_PAIRS.items():
        values, metric_issues = _measure(events, start, end, correlation)
        observations[metric] = values
        metrics[metric] = statistics.median(values) if values else None
        issues.extend({"metric": metric, **issue} for issue in metric_issues)
    raw_outcomes = sample.get("outcomes", {})
    if not isinstance(raw_outcomes, dict):
        issues.append({"reason": "invalid_outcomes"})
        raw_outcomes = {}
    outcomes = {}
    for name in OUTCOME_FIELDS:
        value = raw_outcomes.get(name)
        outcomes[name] = value if isinstance(value, bool) else None
        if value is not None and not isinstance(value, bool):
            issues.append({"outcome": name, "reason": "outcome_must_be_boolean"})
    return {
        "case_id": sample.get("case_id"),
        "repeat": sample.get("repeat", 0),
        "category": sample.get("category", "uncategorized"),
        "status": sample.get("status", "unknown"),
        "checks": sample.get("checks", []),
        "metrics": metrics,
        "metric_observations": observations,
        "outcomes": outcomes,
        "issues": issues,
    }


def extract_metrics(sample: dict[str, Any]) -> dict[str, float | None]:
    """Return latency medians, keeping unobserved audio and invalid spans null."""
    return score_sample(sample)["metrics"]


def _quality_failed(sample: dict[str, Any]) -> bool:
    outcomes = sample.get("outcomes", {})
    if isinstance(outcomes, dict) and outcomes.get("task_success") is False:
        return True
    checks = sample.get("checks", [])
    return isinstance(checks, list) and any(
        isinstance(check, dict) and check.get("critical") is True and check.get("passed") is False
        for check in checks
    )


def _summarize_scores(scores: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [sample for sample in scores if sample["status"] in SUCCESS_STATUSES]
    eligible = [sample for sample in completed if not _quality_failed(sample)]
    metrics = {}
    for name in METRIC_PAIRS:
        values = [value for sample in eligible for value in sample["metric_observations"][name]]
        measured_samples = sum(sample["metrics"][name] is not None for sample in eligible)
        metrics[name] = {
            **distribution(values),
            "measured_samples": measured_samples,
            "eligible_samples": len(eligible),
            "missing_samples": len(eligible) - measured_samples,
            "excluded_noncompleted_samples": len(scores) - len(completed),
            "excluded_quality_failed_samples": len(completed) - len(eligible),
            "independent_case_count": len({sample["case_id"] for sample in eligible if sample["metrics"][name] is not None}),
        }
    outcomes = {}
    for name in OUTCOME_FIELDS:
        known = [sample["outcomes"][name] for sample in scores if sample["outcomes"][name] is not None]
        outcomes[name] = {
            "true": sum(known), "false": len(known) - sum(known),
            "known": len(known), "missing": len(scores) - len(known),
            "true_rate": sum(known) / len(known) if known else None,
        }
    checks = defaultdict(list)
    for sample in scores:
        for check in sample["checks"] if isinstance(sample["checks"], list) else []:
            if isinstance(check, dict) and isinstance(check.get("name"), str):
                checks[check["name"]].append(check)
    check_summary = {}
    for name, entries in checks.items():
        known = [entry["passed"] for entry in entries if isinstance(entry.get("passed"), bool)]
        check_summary[name] = {
            "observations": len(entries), "passed": sum(known), "failed": len(known) - sum(known),
            "unknown": len(entries) - len(known), "known": len(known),
            "pass_rate": sum(known) / len(known) if known else None,
            "critical_failures": sum(entry.get("critical") is True and entry.get("passed") is False for entry in entries),
        }
    return {
        "sample_count": len(scores),
        "completed_samples": len(completed),
        "quality_failed_samples": sum(_quality_failed(sample) for sample in scores),
        "latency_eligible_samples": len(eligible),
        "status_counts": dict(Counter(sample["status"] for sample in scores)),
        "completion_rate": len(completed) / len(scores) if scores else None,
        "metrics": metrics, "outcomes": outcomes, "checks": check_summary,
    }


def _planned_keys(run: dict[str, Any]) -> set[tuple[str, int]] | None:
    manifest = run.get("manifest", {})
    ids, repeats = manifest.get("selected_case_ids"), manifest.get("repeats")
    if (not isinstance(ids, list) or any(not isinstance(case_id, str) or not case_id for case_id in ids)
            or not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1):
        return None
    return {(case_id, repeat) for case_id in ids for repeat in range(1, repeats + 1)}


def summarize_run(run: dict[str, Any]) -> dict[str, Any]:
    manifest = run.get("manifest", {})
    index, identity_issues = _sample_index(run)
    scores = [score_sample(sample) for sample in index.values()]
    planned = _planned_keys(run)
    missing = planned - index.keys() if planned is not None else set()
    observed_count = len(run.get("samples", []))
    denominator = max(observed_count, len(planned)) if planned is not None else observed_count
    summary = _summarize_scores(scores)
    summary["sample_count"] = denominator
    summary["observed_sample_count"] = observed_count
    summary["attempted_sample_count"] = len(index)
    summary["planned_sample_count"] = len(planned) if planned is not None else None
    summary["missing_sample_count"] = len(missing) if planned is not None else None
    summary["missing_samples"] = [{"case_id": key[0], "repeat": key[1]} for key in sorted(missing)]
    summary["invalid_sample_count"] = observed_count - len(index)
    summary["completion_rate"] = summary["completed_samples"] / denominator if denominator else None
    summary["attempted_completion_rate"] = summary["completed_samples"] / len(index) if index else None
    summary["planned_completion_rate"] = (
        summary["completed_samples"] / len(planned) if planned else None
    )
    summary["coverage_rate"] = len(index) / denominator if denominator else None
    text_only = manifest.get("evidence_mode") == "text_only" or manifest.get("adapter") in ("text", "luna-text")
    for name, metric in summary["metrics"].items():
        metric["applicability"] = "not_measured_by_text_adapter" if text_only and name in AUDIO_METRICS else "event_dependent"
        metric["missing_planned_samples"] = len(missing) if planned is not None else None
        metric["total_sample_denominator"] = denominator
    unscored_count = denominator - len(scores)
    for outcome in summary["outcomes"].values():
        outcome["missing"] += unscored_count
        outcome["total_sample_denominator"] = denominator
    by_category = defaultdict(list)
    for sample in scores:
        by_category[sample["category"]].append(sample)
    return {
        "manifest": manifest,
        **summary,
        "categories": {key: _summarize_scores(value) for key, value in sorted(by_category.items())},
        "samples": scores,
        "identity_issues": identity_issues,
        "human_quality": manifest.get("human_quality", "unrated"),
        "overall_quality_verdict": None,
        "interpretation": "Latency describes completed samples without known critical or task failures. Unknown quality is not a pass. Quality outcomes are reported separately.",
    }


def _paired_distribution(pairs: list[tuple[float, float, str]], seed: int, resamples: int) -> dict[str, Any]:
    deltas = [after - before for before, after, _ in pairs]
    clusters = defaultdict(list)
    for before, after, case_id in pairs:
        clusters[case_id].append(after - before)
    ci = None
    if len(clusters) >= 2 and resamples > 0:
        rng = random.Random(seed)
        cluster_values = list(clusters.values())
        bootstrap = sorted(statistics.median([
            delta for group in rng.choices(cluster_values, k=len(cluster_values)) for delta in group
        ]) for _ in range(resamples))
        ci = [_percentile(bootstrap, .025), _percentile(bootstrap, .975)]
    return {
        "pairs": len(pairs),
        "independent_case_clusters": len(clusters),
        "small_cluster_warning": (
            "Fewer than 20 independent cases; the confidence interval is exploratory."
            if 0 < len(clusters) < 20 else None
        ),
        "baseline": distribution(before for before, _, _ in pairs),
        "candidate": distribution(after for _, after, _ in pairs),
        "delta_ms": distribution(deltas),
        "median_delta_ci95_ms": ci,
        "ci_method": "paired case-cluster bootstrap of median case-repeat deltas; all repeats move together" if ci else None,
        "resamples": resamples if ci else 0,
        "direction": "Negative latency deltas are faster; they do not establish better conversation quality.",
    }


def _sample_index(run: dict[str, Any]) -> tuple[dict[tuple[str, int], dict[str, Any]], list[dict[str, Any]]]:
    index, issues, duplicates = {}, [], set()
    planned = _planned_keys(run)
    for sample in run.get("samples", []):
        case_id, repeat = sample.get("case_id"), sample.get("repeat", 0)
        if not isinstance(case_id, str) or not case_id or not isinstance(repeat, int) or isinstance(repeat, bool) or repeat < 0:
            issues.append({"reason": "invalid_sample_identity", "case_id": case_id, "repeat": repeat})
            continue
        key = (case_id, repeat)
        if planned is not None and key not in planned:
            issues.append({"reason": "sample_outside_plan", "case_id": case_id, "repeat": repeat})
            continue
        if any(field in sample and sample[field] != run.get("manifest", {}).get(field)
               for field in ("suite_sha256", "adapter")):
            issues.append({"reason": "sample_run_identity_mismatch", "case_id": case_id, "repeat": repeat})
            continue
        if key in index or key in duplicates:
            duplicates.add(key)
            index.pop(key, None)
            issues.append({"reason": "duplicate_sample_identity", "case_id": case_id, "repeat": repeat})
            continue
        index[key] = sample
    return index, issues


def compare_runs(baseline: dict[str, Any], candidate: dict[str, Any], *,
                 seed: int = 1729, resamples: int = 2000) -> dict[str, Any]:
    """Pair exact case/repeat IDs, keeping the suite and adapter fixed."""
    if not isinstance(resamples, int) or isinstance(resamples, bool) or resamples < 0:
        raise ValueError("resamples must be a nonnegative integer")
    identity_issues = []
    before_manifest = baseline.get("manifest", {})
    after_manifest = candidate.get("manifest", {})
    for field in ("suite_sha256", "adapter"):
        for label, manifest in (("baseline", before_manifest), ("candidate", after_manifest)):
            if not isinstance(manifest.get(field), str) or not manifest[field]:
                identity_issues.append({"reason": "missing_run_identity", "run": label, "field": field})
        if before_manifest.get(field) != after_manifest.get(field):
            identity_issues.append({"reason": "run_identity_mismatch", "field": field})
    result = {
        "comparable": not identity_issues,
        "baseline_manifest": before_manifest,
        "candidate_manifest": after_manifest,
        "config_changed": before_manifest.get("config") != after_manifest.get("config"),
        "source_changed": before_manifest.get("source_hashes") != after_manifest.get("source_hashes"),
        "comparison_kind": (
            "repeatability" if before_manifest.get("config") == after_manifest.get("config")
            and before_manifest.get("source_hashes") == after_manifest.get("source_hashes")
            else "configuration_comparison"
        ),
        "baseline_summary": summarize_run(baseline),
        "candidate_summary": summarize_run(candidate),
        "issues": identity_issues,
        "metrics": {}, "categories": {},
    }
    if identity_issues:
        return result
    left, left_issues = _sample_index(baseline)
    right, right_issues = _sample_index(candidate)
    result["issues"].extend({"run": "baseline", **issue} for issue in left_issues)
    result["issues"].extend({"run": "candidate", **issue} for issue in right_issues)
    common = sorted(left.keys() & right.keys())
    before_planned, after_planned = _planned_keys(baseline), _planned_keys(candidate)
    planned_union = (before_planned | after_planned) if before_planned is not None and after_planned is not None else None
    result["coverage"] = {
        "baseline_samples": len(baseline.get("samples", [])),
        "candidate_samples": len(candidate.get("samples", [])),
        "matched_identity_pairs": len(common),
        "planned_pair_union": len(planned_union) if planned_union is not None else None,
        "planned_shared_pairs": len(before_planned & after_planned) if planned_union is not None else None,
        "planned_baseline_samples": len(before_planned) if before_planned is not None else None,
        "planned_candidate_samples": len(after_planned) if after_planned is not None else None,
        "missing_baseline_planned_samples": [
            {"case_id": key[0], "repeat": key[1]} for key in sorted(before_planned - left.keys())
        ] if before_planned is not None else None,
        "missing_candidate_planned_samples": [
            {"case_id": key[0], "repeat": key[1]} for key in sorted(after_planned - right.keys())
        ] if after_planned is not None else None,
        "missing_planned_pairs": [
            {"case_id": key[0], "repeat": key[1], "missing_baseline": key not in left,
             "missing_candidate": key not in right} for key in sorted(planned_union - set(common))
        ] if planned_union is not None else None,
        "baseline_only": [{"case_id": key[0], "repeat": key[1]} for key in sorted(left.keys() - right.keys())],
        "candidate_only": [{"case_id": key[0], "repeat": key[1]} for key in sorted(right.keys() - left.keys())],
        "invalid_baseline_samples": len(baseline.get("samples", [])) - len(left),
        "invalid_candidate_samples": len(candidate.get("samples", [])) - len(right),
        "usable_pairs": 0,
    }
    scored_pairs, excluded = [], []
    for key in common:
        before, after = left[key], right[key]
        reason = None
        if before.get("category", "uncategorized") != after.get("category", "uncategorized"):
            reason = "category_mismatch"
        elif ("scenario_hash" in before or "scenario_hash" in after) and before.get("scenario_hash") != after.get("scenario_hash"):
            reason = "scenario_hash_mismatch"
        elif before.get("split") != after.get("split"):
            reason = "split_mismatch"
        elif before.get("status") not in SUCCESS_STATUSES or after.get("status") not in SUCCESS_STATUSES:
            reason = "noncompleted_pair"
        elif _quality_failed(before) or _quality_failed(after):
            reason = "quality_failed_pair"
        if reason:
            excluded.append({"case_id": key[0], "repeat": key[1], "reason": reason,
                             "baseline_status": before.get("status"), "candidate_status": after.get("status")})
        else:
            scored_pairs.append((score_sample(before), score_sample(after)))
    result["coverage"]["usable_pairs"] = len(scored_pairs)
    result["excluded_pairs"] = excluded
    grouped = defaultdict(list)
    for pair in scored_pairs:
        grouped[pair[0]["category"]].append(pair)

    def paired_metrics(pairs: list[tuple[dict[str, Any], dict[str, Any]]], category: str) -> dict[str, Any]:
        output = {}
        for name in METRIC_PAIRS:
            values = [(before["metrics"][name], after["metrics"][name], before["case_id"]) for before, after in pairs
                      if before["metrics"][name] is not None and after["metrics"][name] is not None]
            digest = hashlib.sha256(f"{seed}:{category}:{name}".encode()).digest()
            metric_seed = int.from_bytes(digest[:8], "big")
            output[name] = {
                **_paired_distribution(values, metric_seed, resamples),
                "eligible_pairs": len(pairs), "missing_pairs": len(pairs) - len(values),
            }
        return output

    result["metrics"] = paired_metrics(scored_pairs, "all")
    result["categories"] = {key: {"pairs": len(value), "metrics": paired_metrics(value, key)}
                            for key, value in sorted(grouped.items())}
    result["interpretation"] = (
        "Review completion rate, coverage, explicit quality outcomes and human ratings alongside latency. "
        "Bootstrap samples whole cases with their repeats; small case counts and multiple comparisons limit confidence."
    )
    result["overall_quality_verdict"] = None
    result["human_quality_status"] = {
        "baseline": before_manifest.get("human_quality", "unrated"),
        "candidate": after_manifest.get("human_quality", "unrated"),
        "note": "No overall winner is inferred from latency or automatic checks.",
    }
    return result
