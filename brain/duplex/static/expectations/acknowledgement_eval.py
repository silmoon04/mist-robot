"""Offline acknowledgement contracts; synthetic fixtures are not MIST results."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

try:
    from .metrics import extract_metrics
except ImportError:
    from metrics import extract_metrics


CHECKS = (
    "after_user_yield", "pending_work_only", "no_ack_for_ready_fast",
    "quiet_preference", "invalidation", "repetition", "useful_content_evidence",
)
NAMES = {
    "user_audio_start", "user_audio_end", "turn_committed", "response_started",
    "answer_ready", "ack_queued", "ack_started", "ack_stopped", "ack_cancelled",
    "user_resumed", "revision_changed", "answer_started", "answer_stopped",
    "first_useful_audio", "response_closed",
}


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def identifier(value):
    return isinstance(value, str) and bool(value.strip())


def evaluate_sample(sample):
    """Score one response revision. Missing/ambiguous evidence cannot pass."""
    if not isinstance(sample, dict):
        sample = {}
    result = {
        "case_id": sample.get("case_id"), "evidence_mode": sample.get("evidence_mode"),
        "status": "unknown", "checks": {}, "issues": [],
        "timings_ms": {"first_reaction": None, "first_acknowledgement": None,
                       "first_useful_content": None, "acknowledgement_cutoffs": []},
        "human_naturalness": "unmeasured", "prosody": "unmeasured",
    }
    issues = result["issues"]

    def unknown(reason):
        issues.append(reason)

    def check(name, passed, reason):
        result["checks"][name] = {"status": "unknown" if passed is None else
                                 ("pass" if passed else "fail"), "reason": reason}

    def finish_unknown():
        for name in CHECKS:
            check(name, None, "Incomplete or invalid evidence; see issues.")
        return result

    scope = ("case_id", "turn_id", "revision_id", "response_id", "user_span_id")
    if any(not identifier(sample.get(key)) for key in scope):
        unknown("missing_sample_correlation")
    capture = sample.get("capture", {})
    if not isinstance(capture, dict):
        capture = {}
    start, end = capture.get("start_ms"), capture.get("end_ms")
    if (capture.get("complete") is not True or not identifier(capture.get("clock_id"))
            or not identifier(capture.get("note")) or not number(start) or not number(end)
            or (number(start) and number(end) and end <= start)
            or capture.get("basis") not in ("synthetic", "software_events", "annotated_recording")):
        unknown("missing_complete_common_clock_capture")
    if sample.get("evidence_mode") not in ("synthetic_fixture", "observed_events"):
        unknown("missing_evidence_mode")
    if (sample.get("evidence_mode") == "synthetic_fixture") != (capture.get("basis") == "synthetic"):
        unknown("evidence_mode_basis_mismatch")
    policy = sample.get("policy", {})
    if not isinstance(policy, dict):
        policy = {}
    if (type(policy.get("quiet")) is not bool or not identifier(policy.get("note"))
            or not number(policy.get("ready_fast_ms"))
            or not number(policy.get("cancel_deadline_ms"))):
        unknown("missing_frozen_policy")
    events = sample.get("events")
    if not isinstance(events, list) or not events:
        unknown("missing_events")
        return finish_unknown()
    for event in events:
        if not isinstance(event, dict):
            unknown("invalid_event")
            continue
        name, t = event.get("event"), event.get("t_ms")
        if not isinstance(name, str) or name not in NAMES or not number(t):
            unknown("invalid_event_name_or_time")
        if not isinstance(name, str):
            continue
        if not identifier(event.get("clock_id")) or event.get("clock_id") != capture.get("clock_id"):
            unknown("missing_or_mixed_clock")
        if any(event.get(key) != sample.get(key) or not identifier(event.get(key))
               for key in scope[:-1]):
            unknown("event_scope_mismatch")
        if number(t) and number(start) and number(end) and not start <= t <= end:
            unknown("event_outside_capture")
        fields = []
        if name in ("user_audio_start", "user_audio_end"):
            fields.append("user_span_id")
        if name.startswith("ack_"):
            fields.append("ack_id")
        if name in ("ack_started", "ack_stopped", "answer_started", "answer_stopped", "first_useful_audio"):
            fields.append("playback_id")
        if name in ("user_resumed", "revision_changed", "ack_cancelled"):
            fields.append("interruption_id")
        if name == "revision_changed":
            fields.append("next_revision_id")
        if any(not identifier(event.get(key)) for key in fields):
            unknown("missing_event_correlation")
    if issues:
        return finish_unknown()
    events = sorted(events, key=lambda row: row["t_ms"])

    def named(name):
        return [row for row in events if row["event"] == name]

    def one(name):
        rows = named(name)
        if len(rows) != 1:
            unknown("missing_or_ambiguous_" + name)
            return None
        return rows[0]

    user_start, user_end = one("user_audio_start"), one("user_audio_end")
    commit, work, closed = one("turn_committed"), one("response_started"), one("response_closed")
    if any(row is None for row in (user_start, user_end, commit, work, closed)):
        return finish_unknown()
    if (user_start["user_span_id"] != sample["user_span_id"]
            or user_end["user_span_id"] != sample["user_span_id"]
            or not user_start["t_ms"] <= user_end["t_ms"] <= commit["t_ms"] <= work["t_ms"] <= closed["t_ms"]
            or closed["t_ms"] != end or closed.get("outcome") not in ("completed", "cancelled")):
        unknown("invalid_response_or_user_span")
    invalidations = named("user_resumed") + named("revision_changed")
    if (len({row["interruption_id"] for row in invalidations}) != len(invalidations)
            or any(row["t_ms"] < user_end["t_ms"] for row in invalidations)
            or any(row.get("next_revision_id") == sample["revision_id"] for row in named("revision_changed"))):
        unknown("invalid_invalidation_correlation")
    ready = named("answer_ready")
    if len(ready) > 1 or (closed.get("outcome") == "completed" and len(ready) != 1):
        unknown("missing_or_ambiguous_answer_ready")
    if ready and ready[0]["t_ms"] < work["t_ms"]:
        unknown("answer_ready_before_work")
    answer_starts = named("answer_started")
    if answer_starts and len(ready) != 1:
        unknown("answer_playback_without_ready")
    elif answer_starts and any(row["t_ms"] < max(ready[0]["t_ms"], work["t_ms"])
                               for row in answer_starts):
        unknown("answer_playback_before_ready_or_work")
    if closed.get("outcome") == "cancelled" and not invalidations:
        unknown("cancelled_without_invalidation")
    if closed.get("outcome") == "completed" and invalidations:
        unknown("completed_response_contains_invalidation")

    queues = named("ack_queued")
    if len({row["ack_id"] for row in queues}) != len(queues):
        unknown("ambiguous_ack_id")
    queue_by_id = {row["ack_id"]: row for row in queues}
    for row in events:
        if row["event"].startswith("ack_") and row["event"] != "ack_queued":
            queue = queue_by_id.get(row["ack_id"])
            if queue is None or row["t_ms"] < queue["t_ms"]:
                unknown("ack_without_prior_matching_queue")
    for queue in queues:
        own = [row for row in events if row.get("ack_id") == queue["ack_id"]]
        if any(sum(row["event"] == name for row in own) > 1
               for name in ("ack_started", "ack_stopped", "ack_cancelled")):
            unknown("ambiguous_ack_lifecycle")
        if not any(row["event"] in ("ack_started", "ack_cancelled") for row in own):
            unknown("unsettled_ack_queue")

    starts = named("ack_started") + named("answer_started")
    stops = named("ack_stopped") + named("answer_stopped")
    if len({row["playback_id"] for row in starts}) != len(starts):
        unknown("ambiguous_playback_id")
    spans = {}
    for opening in starts:
        endings = [row for row in stops if row["playback_id"] == opening["playback_id"]]
        if (len(endings) != 1 or endings[0]["t_ms"] < opening["t_ms"]
                or endings[0]["event"] != opening["event"].replace("started", "stopped")
                or endings[0].get("ack_id") != opening.get("ack_id")):
            unknown("incomplete_or_mismatched_playback_span")
        else:
            spans[opening["playback_id"]] = (opening, endings[0])
    if any(row["playback_id"] not in spans for row in stops):
        unknown("unmatched_playback_stop")
    if any(opening["event"] == "answer_started" and
           opening["t_ms"] < trigger["t_ms"] < ending["t_ms"]
           for opening, ending in spans.values() for trigger in invalidations):
        # This evaluator times acknowledgement cancellation, not full answers.
        unknown("answer_crosses_invalidation_out_of_scope")
    if issues:
        return finish_unknown()

    acknowledgements = named("ack_started")
    check("after_user_yield", all(row["t_ms"] >= commit["t_ms"] for row in acknowledgements),
          "Audible acknowledgements must follow the correlated user end and committed turn.")
    ready_time = ready[0]["t_ms"] if ready else float("inf")
    check("pending_work_only", all(work["t_ms"] <= row["t_ms"] < ready_time for row in acknowledgements),
          "Substantive work must already be running and its answer not yet ready.")
    fast = bool(ready and ready_time - user_end["t_ms"] <= policy["ready_fast_ms"])
    check("no_ack_for_ready_fast", not (fast and acknowledgements),
          "A response ready within the declared fast window should have no audible filler.")
    check("quiet_preference", not (policy["quiet"] and acknowledgements),
          "The explicit quiet preference forbids audible acknowledgements.")
    check("repetition", len(acknowledgements) <= 1,
          "At most one audible acknowledgement in this response revision; wording is not judged.")

    cancelled_ok = True
    cutoffs = []
    for trigger in invalidations:
        t, iid = trigger["t_ms"], trigger["interruption_id"]
        if any(row["t_ms"] >= t for row in starts + queues + named("first_useful_audio")):
            cancelled_ok = False
        for queue in queues:
            own = [row for row in events if row.get("ack_id") == queue["ack_id"]]
            settled_before = any(row["event"] in ("ack_cancelled", "ack_stopped") and row["t_ms"] < t for row in own)
            if queue["t_ms"] > t or settled_before:
                continue
            cancels = [row for row in own if row["event"] == "ack_cancelled" and row["interruption_id"] == iid
                       and t <= row["t_ms"] <= t + policy["cancel_deadline_ms"]]
            cancelled_ok &= len(cancels) == 1
            for opening, ending in spans.values():
                if opening.get("ack_id") == queue["ack_id"] and opening["t_ms"] < t <= ending["t_ms"]:
                    if not identifier(ending.get("interruption_id")):
                        unknown("missing_cutoff_correlation")
                    correlated = ending.get("interruption_id") == iid
                    cancelled_ok &= correlated and ending["t_ms"] - t <= policy["cancel_deadline_ms"]
                    if correlated:
                        cutoffs.append(ending["t_ms"] - t)
    for cancelled in named("ack_cancelled"):
        if not any(row["interruption_id"] == cancelled["interruption_id"] and row["t_ms"] <= cancelled["t_ms"]
                   for row in invalidations):
            unknown("orphan_ack_cancellation")
    for stopped in named("ack_stopped"):
        if "interruption_id" in stopped and not any(
                row["interruption_id"] == stopped["interruption_id"] and row["t_ms"] <= stopped["t_ms"]
                for row in invalidations):
            unknown("orphan_cutoff_correlation")
    if issues:
        return finish_unknown()
    check("invalidation", cancelled_ok,
          "Resume/revision must cancel pending or active cues by the declared deadline; no superseded output starts later.")

    useful = named("first_useful_audio")
    useful_valid = len(useful) == 1
    if useful_valid:
        annotation = useful[0].get("metadata", {})
        span = spans.get(useful[0]["playback_id"])
        useful_valid = (isinstance(annotation, dict) and annotation.get("annotation_source") in ("human", "scenario_rule")
                        and identifier(annotation.get("note")) and span is not None
                        and span[0]["event"] == "answer_started"
                        and span[0]["t_ms"] <= useful[0]["t_ms"] <= span[1]["t_ms"]
                        and useful[0]["t_ms"] >= user_end["t_ms"])
    if closed["outcome"] == "cancelled" and not useful:
        check("useful_content_evidence", True, "Cancelled response has no useful-content measurement; none inferred.")
    else:
        check("useful_content_evidence", True if useful_valid else None,
              "Useful content needs an explicit human/scenario annotation within a correlated answer playback span.")

    # Reuse the existing scorer only after stricter clock/scope/span validation.
    measure_events = [user_end]
    if starts:
        measure_events.append({**min(starts, key=lambda row: row["t_ms"]), "event": "playback_started"})
    if useful_valid:
        measure_events.extend(useful)
    measured = extract_metrics({"case_id": sample["case_id"], "events": measure_events})
    result["timings_ms"] = {
        "first_reaction": measured["first_audio_ms"],
        "first_acknowledgement": (min(row["t_ms"] for row in acknowledgements) - user_end["t_ms"]
                                  if acknowledgements else None),
        "first_useful_content": measured["first_useful_audio_ms"],
        "acknowledgement_cutoffs": cutoffs,
    }
    statuses = [row["status"] for row in result["checks"].values()]
    result["status"] = "fail" if "fail" in statuses else ("unknown" if "unknown" in statuses else "pass")
    result["timing_basis"] = capture["basis"]
    return result


def validate_contracts(document):
    """Compare synthetic fixture outcomes with their declared expectations."""
    results = []
    for contract in document["contracts"]:
        for label in ("good", "bad"):
            fixture = contract[label]
            result = evaluate_sample(fixture["sample"])
            expected = fixture["expected_status"]
            expected_check = fixture.get("expected_failed_check")
            matched = result["status"] == expected and (not expected_check or
                      result["checks"][expected_check]["status"] == "fail")
            results.append({"contract_id": contract["id"], "fixture": label,
                            "expected_status": expected, "matched": matched, "evaluation": result})
    return {"kind": "synthetic_evaluator_validation", "mist_performance_measured": False,
            "human_naturalness": "unmeasured", "fixtures": len(results),
            "matched": sum(row["matched"] for row in results),
            "status_counts": dict(Counter(row["evaluation"]["status"] for row in results)), "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path,
                        default=Path(__file__).with_name("acknowledgement_contracts.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    document = json.loads(args.input.read_text(encoding="utf-8"))
    report = validate_contracts(document) if "contracts" in document else evaluate_sample(document)
    rendered = json.dumps(report, indent=2, allow_nan=False)
    if args.output:
        if args.output.resolve() == args.input.resolve():
            parser.error("Output must not overwrite input evidence.")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    if "contracts" in document:
        return 0 if report["fixtures"] and report["matched"] == report["fixtures"] else 1
    return {"pass": 0, "fail": 1, "unknown": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
