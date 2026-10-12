"""Offline measurements of browser E2E captures, without packet-to-turn guesses.

CLI: python e2e_metrics.py --group native=PATH --group cascade=PATH --output report.json
All event/input timestamps must use this capture's browser performance clock.
Software playback estimates are not measurements at a listener's ear.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping


LATENCY_NAMES = ("user_final_transcript_ms", "assistant_first_text_ms", "first_audio_received_ms", "first_playback_ms")
TIMING_KIND = "software_output_estimate_not_acoustic"


def numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def stats(values) -> dict:
    values = sorted(float(value) for value in values if numeric(value))
    def quantile(q):
        if not values:
            return None
        index = (len(values) - 1) * q
        low, high = math.floor(index), math.ceil(index)
        return values[low] + (values[high] - values[low]) * (index-low)
    return {"count": len(values), "median": statistics.median(values) if values else None,
            "p90": quantile(.9), "p95": quantile(.95), "min": values[0] if values else None,
            "max": values[-1] if values else None,
            "small_n_warning": "Fewer than 20 captures; tail estimates are unstable." if 0 < len(values) < 20 else None}


def _read(path: Path) -> tuple[dict | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return (value, None) if isinstance(value, dict) else (None, "Expected a JSON object")
    except (OSError, ValueError) as error:
        return None, str(error)


def _config_identity(configuration: dict) -> tuple[dict, str]:
    config = {key: value for key, value in configuration.items()
              if key not in {"started_unix", "server_origin_perf", "started_at", "ended_at", "run_id"}}
    raw = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return config, hashlib.sha256(raw).hexdigest()


def _clock_matches(item: dict, clock_id: str) -> bool:
    return item.get("clock_id", clock_id) == clock_id


def _nonempty_text(event: dict) -> bool:
    return isinstance(event.get("text"), str) and bool(event["text"].strip())


def _turn_observations(events: list[dict], start: float, end: float) -> dict:
    """Describe segmentation without joining different response generations."""
    user_finals = [event for event in events if event.get("type") == "transcript_done"
                   and event.get("role") == "user" and _nonempty_text(event)]
    assistant_text = [event for event in events if event.get("type") in ("transcript_delta", "transcript_done")
                      and event.get("role") == "assistant" and _nonempty_text(event)]
    assistant_finals = [event for event in assistant_text if event["type"] == "transcript_done"]
    reset_events = [event for event in events if event.get("type") == "audio_reset"]
    reply_segments, reply_open = 0, False
    for event in events:
        if event.get("type") == "audio_reset":
            reply_open = False
        elif event.get("role") == "assistant" and event.get("type") in ("transcript_delta", "transcript_done") and _nonempty_text(event):
            if not reply_open:
                reply_segments += 1
                reply_open = True
            if event["type"] == "transcript_done":
                reply_open = False
    early_text = [event for event in assistant_text if event["t_ms"] < end]
    early_audio = [event for event in events if event.get("type") == "audio" and event["t_ms"] < end
                   and numeric(event.get("pcm_bytes")) and event["pcm_bytes"] > 0]
    early_playback = [event for event in events if event.get("type") == "playback_started" and event["t_ms"] < end]
    return {
        "user_final_transcript_count": len(user_finals),
        "distinct_nonempty_user_final_count": len({" ".join(event["text"].split()).casefold() for event in user_finals}),
        "user_final_timestamps_ms": [event["t_ms"] for event in user_finals],
        "assistant_final_transcript_count": len(assistant_finals),
        "assistant_reply_segments": reply_segments,
        "assistant_final_timestamps_ms": [event["t_ms"] for event in assistant_finals],
        "premature_assistant_text_event_count": len(early_text),
        "premature_first_text_before_input_end_ms": end-early_text[0]["t_ms"] if early_text else None,
        "first_assistant_text_timestamp_ms": assistant_text[0]["t_ms"] if assistant_text else None,
        "audio_received_before_input_end_count": len(early_audio),
        "playback_started_before_input_end_count": len(early_playback),
        "audio_reset_count": len(reset_events),
        "mid_input_reset_count": sum(start <= event["t_ms"] < end for event in reset_events),
        "reset_timestamps_ms": [event["t_ms"] for event in reset_events],
        "note": "Observed events within this input window. Counts do not establish which utterance caused an event or whether an interruption was appropriate.",
    }


def analyze_browser(data: dict, fixture: dict | None = None, configuration: dict | None = None,
                    *, label: str = "unlabelled", capture_id: str | None = None) -> dict:
    """Analyze one browser.json. Report observations separately from judgments."""
    fixture = fixture if fixture is not None else data.get("fixture", {})
    configuration, config_hash = _config_identity(configuration or {})
    issues = []
    clock_id = data.get("clock_id", "browser_performance")
    raw_events = data.get("events", [])
    if not isinstance(raw_events, list):
        issues.append("events_not_a_list")
        raw_events = []
    valid_events = []
    for index, item in enumerate(raw_events):
        if not isinstance(item, dict) or not numeric(item.get("t_ms")) or item["t_ms"] < 0:
            issues.append(f"invalid_event_timestamp:{index}")
        elif not _clock_matches(item, clock_id):
            issues.append(f"event_clock_mismatch:{index}")
        else:
            valid_events.append(item)
    valid_events.sort(key=lambda item: item["t_ms"])
    boundaries = [item["t_ms"] for item in valid_events if item.get("type") == "capture_boundary"]
    boundary = data.get("observation_end_ms")
    if not numeric(boundary):
        boundary = min(boundaries) if boundaries else None
    elif boundaries:
        boundary = min(boundary, min(boundaries))
    if boundary is None:
        issues.append("missing_observation_boundary")
    # Cleanup resets/stops after the capture boundary are never conversational stops.
    events = [item for item in valid_events if boundary is None or item["t_ms"] < boundary]
    event_counts = Counter(item.get("type", "unknown") for item in events)
    cleanup_counts = Counter(item.get("type", "unknown") for item in valid_events
                             if boundary is not None and item["t_ms"] >= boundary)
    ready = next((item for item in events if item.get("type") == "ready"), None)
    socket_open = next((item for item in events if item.get("type") == "socket_open"), None)
    face_ready = next((item for item in events if item.get("type") == "face_ready" and item.get("ready") is True), None)
    startup = {
        "ready_after_capture_start_ms": ready["t_ms"] if ready else None,
        "ready_after_socket_open_ms": ready["t_ms"]-socket_open["t_ms"] if ready and socket_open and ready["t_ms"] >= socket_open["t_ms"] else None,
        "face_ready_after_capture_start_ms": face_ready["t_ms"] if face_ready else None,
        "server_reported_breakdown": ready.get("startup") if ready else None,
        "note": "Browser startup is separate from response latency. Server-reported breakdown retains its source and is not subtracted from browser timestamps.",
    }
    raw_frames = data.get("frames", [])
    if not isinstance(raw_frames, list):
        raw_frames = []
        issues.append("frames_not_a_list")
    frames = [frame for frame in raw_frames if isinstance(frame, dict) and numeric(frame.get("t_ms"))
              and frame["t_ms"] >= 0 and _clock_matches(frame, clock_id)
              and (boundary is None or frame["t_ms"] < boundary)]
    invalid_frames = len(raw_frames) - len(frames)
    input_rows = data.get("inputs", [])
    if not isinstance(input_rows, list):
        input_rows = []
        issues.append("inputs_not_a_list")
    steps = fixture.get("steps", []) if isinstance(fixture, dict) else []
    seeded = any(isinstance(step, dict) and step.get("type") == "seed_text" for step in steps)
    seeded |= any(item.get("type") == "context_setup" and item.get("kind") == "seed_text" for item in events)
    background = any(isinstance(step, dict) and step.get("type") == "background" for step in steps)
    input_reports = []
    for index, item in enumerate(input_rows):
        if not isinstance(item, dict):
            issues.append(f"invalid_input:{index}")
            continue
        start, end = item.get("start_ms"), item.get("end_ms")
        valid = numeric(start) and numeric(end) and 0 <= start <= end and _clock_matches(item, clock_id)
        if not valid:
            issues.append(f"invalid_input_timing:{index}")
        later = [other.get("start_ms") for other in input_rows[index+1:] if isinstance(other, dict)
                 and numeric(other.get("start_ms")) and numeric(start) and other["start_ms"] > start]
        window_end = min(later + ([boundary] if boundary is not None else [])) if later or boundary is not None else None
        observed_overlap = item.get("playback_active_at_start") if isinstance(item.get("playback_active_at_start"), bool) else None
        during_frames = [frame for frame in frames if valid and start <= frame["t_ms"] <= end]
        if any(frame.get("audio_active") is True for frame in during_frames):
            observed_overlap = True
        elif observed_overlap is None and during_frames and all(isinstance(frame.get("audio_active"), bool) for frame in during_frames):
            observed_overlap = False
        # These are associations within an input's observation window, not causal attribution.
        window = [event for event in events if valid and window_end is not None and start <= event["t_ms"] < window_end]
        resets = [event for event in window if event.get("type") == "audio_reset"]
        stops = [event for event in window if event.get("type") == "source_stop_called"]
        reset_details = []
        scheduled = [event for event in events if event.get("type") == "source_scheduled"]
        for reset in resets:
            before = [frame for frame in frames if frame["t_ms"] <= reset["t_ms"]]
            snapshot = max(before, key=lambda frame: frame["t_ms"]) if before else None
            stopped = [stop for stop in stops if reset["t_ms"] <= stop["t_ms"] < reset["t_ms"] + 100]
            source_ids = {stop.get("source_id") for stop in stopped if stop.get("source_id") is not None}
            remaining_sources = [source for source in scheduled if source.get("source_id") in source_ids
                                 and numeric(source.get("estimated_output_end_ms"))
                                 and source["estimated_output_end_ms"] > reset["t_ms"]]
            reset_details.append({
                "t_ms": reset["t_ms"], "after_input_start_ms": reset["t_ms"] - start,
                "after_input_end_ms": reset["t_ms"] - end,
                "queue_snapshot_ms": snapshot.get("queue_ms") if snapshot else None,
                "queue_snapshot_age_ms": reset["t_ms"] - snapshot["t_ms"] if snapshot else None,
                "stop_commands_within_100ms": len(stopped),
                "stopped_source_ids": sorted(source_ids, key=str),
                "scheduled_remaining_source_count": len(remaining_sources),
                "interrupted_queue_observed": bool(remaining_sources) if stopped else None,
                "note": "Queue is the preceding sampled estimate. Stop commands are not acoustic cutoff measurements.",
            })
        packets = item.get("packets", [])
        packet_lateness = [packet[2] for packet in packets if isinstance(packet, list) and len(packet) >= 3 and numeric(packet[2])]
        input_reports.append({
            "step": item.get("step", index), "file": item.get("file"), "start_ms": start, "end_ms": end,
            "valid_timing": valid, "playback_active_at_start": item.get("playback_active_at_start"),
            "observed_overlap": observed_overlap, "observation_window_end_ms": window_end,
            "audio_resets_in_window": len(resets) if valid and window_end is not None else None,
            "source_stop_commands_in_window": len(stops) if valid and window_end is not None else None,
            "first_reset_after_start_ms": resets[0]["t_ms"]-start if resets else None,
            "first_reset_after_end_ms": resets[0]["t_ms"]-end if resets else None,
            "first_stop_command_after_start_ms": stops[0]["t_ms"]-start if stops else None,
            "first_stop_command_after_end_ms": stops[0]["t_ms"]-end if stops else None,
            "resets": reset_details, "packet_lateness_ms": stats(packet_lateness),
            "turn_observations": _turn_observations(window, start, end) if valid and window_end is not None else None,
            "interruption_correctness": None,
        })
    exclusion = []
    if len(input_rows) != 1 or len(input_reports) != 1:
        exclusion.append("requires_exactly_one_user_audio_input")
    if seeded:
        exclusion.append("seeded_assistant_output")
    if background:
        exclusion.append("background_output_may_overlap")
    if boundary is None:
        exclusion.append("missing_observation_boundary")
    if len(input_reports) == 1:
        one = input_reports[0]
        if not one["valid_timing"]:
            exclusion.append("invalid_input_clock_or_timing")
        if one["observed_overlap"] is not False:
            exclusion.append("overlapping_or_unknown_playback")
        turn_observations = one["turn_observations"]
        if turn_observations:
            if turn_observations["distinct_nonempty_user_final_count"] > 1:
                exclusion.append("multiple_user_final_transcripts")
            if turn_observations["assistant_reply_segments"] > 1:
                exclusion.append("multiple_assistant_reply_segments")
            if turn_observations["audio_reset_count"]:
                exclusion.append("response_cancelled_or_reset")
            if one["source_stop_commands_in_window"]:
                exclusion.append("response_source_stopped")
            if turn_observations["premature_assistant_text_event_count"]:
                exclusion.append("assistant_text_before_input_end")
        if one["valid_timing"] and any(
            event["t_ms"] < one["start_ms"] and (event.get("type") in ("audio", "playback_started")
            or event.get("role") == "assistant" and event.get("type") in ("transcript_delta", "transcript_done"))
            for event in events
        ):
            exclusion.append("assistant_output_predates_input")
    latency = {name: None for name in LATENCY_NAMES}
    event_times = {name: None for name in LATENCY_NAMES}
    if not exclusion:
        one = input_reports[0]
        filters = {
            "user_final_transcript_ms": lambda e: e.get("type") == "transcript_done" and e.get("role") == "user" and _nonempty_text(e),
            "assistant_first_text_ms": lambda e: e.get("type") in ("transcript_delta", "transcript_done") and e.get("role") == "assistant" and _nonempty_text(e),
            "first_audio_received_ms": lambda e: e.get("type") == "audio" and numeric(e.get("pcm_bytes")) and e["pcm_bytes"] > 0,
            "first_playback_ms": lambda e: e.get("type") == "playback_started",
        }
        for name, predicate in filters.items():
            matches = [event for event in events if event["t_ms"] >= one["start_ms"] and predicate(event)]
            if matches:
                event_times[name] = matches[0]["t_ms"]
                latency[name] = round(matches[0]["t_ms"] - one["end_ms"], 3)
    gaps = [after["t_ms"] - before["t_ms"] for before, after in zip(frames, frames[1:])
            if after["t_ms"] > before["t_ms"]]
    nonmonotonic_frames = sum(after["t_ms"] <= before["t_ms"] for before, after in zip(frames, frames[1:]))
    expected_fps = data.get("environment", {}).get("face_fps")
    expected_interval = 1000 / expected_fps if numeric(expected_fps) and expected_fps > 0 else None
    frame_errors = [frame["face"].get("drawnError") for frame in frames if isinstance(frame.get("face"), dict) and frame["face"].get("drawnError")]
    missing_face = sum(not isinstance(frame.get("face"), dict) for frame in frames)
    transcripts = [dict(t_ms=event["t_ms"], type=event["type"], role=event.get("role"), text=event.get("text", ""))
                   for event in events if event.get("type") in ("transcript_delta", "transcript_done")]
    errors = data.get("errors", [])
    errors = errors if isinstance(errors, list) else [{"message": str(errors)}]
    remaining = data.get("remaining", {})
    remaining = remaining if isinstance(remaining, dict) else {}
    truncated = (data.get("capture_truncated") is True or remaining.get("playback_active") is True
                 or numeric(remaining.get("queue_ms")) and remaining["queue_ms"] > 20)
    recording = data.get("recording", [])
    recording = recording if isinstance(recording, list) else []
    recording_errors = [item for item in recording if isinstance(item, dict) and (item.get("error") or item.get("unavailable") or item.get("upload", {}).get("saved") is False)]
    return {
        "schema_version": 1, "capture_id": capture_id, "case_id": data.get("case_id", fixture.get("id")),
        "label": label, "status": data.get("status", "unknown"), "configuration": configuration,
        "configuration_sha256": config_hash, "timing_kind": data.get("timing_kind", TIMING_KIND),
        "clock_id": clock_id, "observation_end_ms": boundary,
        "startup": startup,
        "first_response": {"eligible": not exclusion, "exclusion_reasons": exclusion,
                           "relative_to": "single_input.end_ms", "latency_ms": latency, "event_times_ms": event_times,
                           "missing_metrics": [name for name, value in latency.items() if value is None],
                           "negative_latency_note": "Negative values mean the event occurred before the audio input ended; values are not clamped.",
                           "first_useful_audio_ms": None},
        "inputs": input_reports, "seeded_assistant": seeded,
        "event_counts": dict(event_counts), "cleanup_event_counts": dict(cleanup_counts),
        "face": {"sample_count": len(frames), "invalid_or_outside_frames": invalid_frames,
                 "missing_face_snapshots": missing_face, "nonmonotonic_samples": nonmonotonic_frames,
                 "configured_fps": expected_fps, "sample_interval_ms": stats(gaps),
                 "late_samples_ms": stats(frame.get("sample_late_ms") for frame in frames),
                 "sample_gaps_over_1_5_frames": sum(gap > expected_interval * 1.5 for gap in gaps) if expected_interval else None,
                 "renderer_errors": frame_errors,
                 "note": "These are snapshot sampling intervals, not proof of rendered video cadence or perceptual lip sync."},
        "capture": {"truncated": bool(truncated), "explicit_truncated": data.get("capture_truncated"),
                    "remaining": remaining, "recording_count": len(recording), "recording_errors": recording_errors,
                    "error_count": len(errors), "errors": errors,
                    "complete_status_does_not_imply_complete_playback": True},
        "transcript_events": transcripts, "human_quality_rating": None, "overall_quality_pass": None,
        "issues": issues, "conditions_uncontrolled": fixture.get("conditions_uncontrolled", []),
        "speech_fixture": fixture.get("speech_fixture"),
    }


def analyze_case(path: str | Path, *, label: str = "unlabelled") -> dict:
    directory = Path(path)
    if directory.name == "browser.json":
        directory = directory.parent
    browser, error = _read(directory / "browser.json")
    fixture, fixture_error = _read(directory / "fixture.json")
    configuration, config_error = _read(directory / "configuration.json")
    if browser is None:
        return {"capture_id": directory.name, "path": str(directory.resolve()), "label": label,
                "case_id": (fixture or {}).get("id"), "status": "missing_or_invalid_browser",
                "configuration": configuration, "error": error, "first_response": None,
                "human_quality_rating": None, "overall_quality_pass": None}
    result = analyze_browser(browser, fixture=fixture, configuration=configuration, label=label, capture_id=directory.name)
    result["path"] = str(directory.resolve())
    result["file_issues"] = {key: value for key, value in {"fixture": fixture_error, "configuration": config_error}.items() if value}
    result["evidence_files"] = sorted(item.name for item in directory.iterdir() if item.is_file() and item.suffix in (".webm", ".mp4", ".ogg", ".pcm", ".jsonl"))
    return result


def summarize_captures(captures: list[dict]) -> dict:
    valid = [item for item in captures if item.get("first_response") is not None]
    completed = [item for item in valid if item["status"] == "complete"]
    latency_eligible = [item for item in completed if item["first_response"]["eligible"] and not item["capture"]["error_count"]]
    observed_turns = [inp["turn_observations"] for item in valid for inp in item["inputs"] if inp.get("turn_observations") is not None]
    observed_single_turns = [item["inputs"][0]["turn_observations"] for item in valid
                             if len(item["inputs"]) == 1 and not item["seeded_assistant"]
                             and item["inputs"][0].get("turn_observations") is not None]
    latencies = {}
    for name in LATENCY_NAMES:
        values = [item["first_response"]["latency_ms"][name] for item in latency_eligible]
        metric = stats(values)
        metric.update({"total_capture_denominator": len(captures), "eligible_captures": len(latency_eligible),
                       "missing_in_eligible": sum(value is None for value in values),
                       "excluded_captures": len(captures)-len(latency_eligible),
                       "truncated_captures_with_metric": sum(item["capture"]["truncated"] and item["first_response"]["latency_ms"][name] is not None for item in latency_eligible)})
        latencies[name] = metric
    return {
        "capture_count": len(captures), "valid_browser_captures": len(valid),
        "missing_or_invalid_captures": len(captures)-len(valid),
        "complete_status_count": len(completed), "status_counts": dict(Counter(item["status"] for item in captures)),
        "complete_status_rate": len(completed)/len(captures) if captures else None,
        "truncated_captures": sum(item["capture"]["truncated"] for item in valid),
        "captures_with_errors": sum(bool(item["capture"]["error_count"]) for item in valid),
        "captures_missing_frame_samples": sum(item["face"]["sample_count"] == 0 for item in valid),
        "captures_with_recording_errors": sum(bool(item["capture"]["recording_errors"]) for item in valid),
        "latency_ms": latencies,
        "first_response_exclusion_counts": dict(Counter(
            reason for item in valid for reason in item["first_response"]["exclusion_reasons"])),
        "turn_observations": {
            "input_windows_with_data": len(observed_turns),
            "single_unseeded_input_windows_with_data": len(observed_single_turns),
            "single_input_multiple_user_final_windows": sum(row["distinct_nonempty_user_final_count"] > 1 for row in observed_single_turns),
            "single_input_multiple_reply_windows": sum(row["assistant_reply_segments"] > 1 for row in observed_single_turns),
            "single_input_premature_text_windows": sum(row["premature_assistant_text_event_count"] > 0 for row in observed_single_turns),
            "single_input_mid_input_reset_windows": sum(row["mid_input_reset_count"] > 0 for row in observed_single_turns),
            "single_input_mid_input_reset_count": sum(row["mid_input_reset_count"] for row in observed_single_turns),
            "all_windows_user_final_transcript_count": sum(row["user_final_transcript_count"] for row in observed_turns),
            "all_windows_assistant_reply_segments": sum(row["assistant_reply_segments"] for row in observed_turns),
            "note": "Segmentation and early-output counts are observations, separate from clean single-turn response latency and human ratings.",
        },
        "startup_ms": {
            key: {**stats(item["startup"].get(key) for item in valid), "total_capture_denominator": len(captures),
                  "missing_captures": len(captures)-sum(numeric(item["startup"].get(key)) for item in valid)}
            for key in ("ready_after_capture_start_ms", "ready_after_socket_open_ms", "face_ready_after_capture_start_ms")
        },
        "input_count": sum(len(item["inputs"]) for item in valid),
        "overlapping_inputs": sum(inp["observed_overlap"] is True for item in valid for inp in item["inputs"]),
        "unknown_overlap_inputs": sum(inp["observed_overlap"] is None for item in valid for inp in item["inputs"]),
        "audio_reset_count": sum(item["event_counts"].get("audio_reset", 0) for item in valid),
        "source_stop_command_count": sum(item["event_counts"].get("source_stop_called", 0) for item in valid),
        "human_rated_captures": 0, "human_unrated_captures": len(captures), "overall_quality_pass": None,
        "limits": ["Input fixtures use synthetic speech unless recorded otherwise.",
                   "No acoustic mouth-to-ear, microphone echo, semantic usefulness or human naturalness score is inferred.",
                   "Seeded/overlapping output is excluded from first-response latency instead of assigning the nearest packet.",
                   "Multiple user finals, multiple assistant replies, resets or early assistant text exclude a single-input capture from the combined latency pipeline.",
                   "A truncated capture can retain a valid first-response timestamp; truncation is counted separately.",
                   "Reset/stop timing is observed association, not a judgment that the interruption was appropriate."],
    }


def build_report(groups: Mapping[str, str | Path]) -> dict:
    reports = {}
    for label, raw_path in groups.items():
        path = Path(raw_path)
        if path.is_file():
            directories = [path.parent]
        elif (path / "browser.json").exists() or (path / "fixture.json").exists():
            directories = [path]
        else:
            directories = sorted({item.parent for filename in ("browser.json", "fixture.json", "configuration.json") for item in path.rglob(filename)})
        captures = [analyze_case(directory, label=label) for directory in directories]
        configurations = defaultdict(list)
        for capture in captures:
            configurations[capture.get("configuration_sha256", "missing")].append(capture)
        reports[label] = {"root": str(path.resolve()), "exists": path.exists(),
                          "summary": summarize_captures(captures),
                          "configurations": {key: {"configuration": rows[0].get("configuration"), "summary": summarize_captures(rows)} for key, rows in configurations.items()},
                          "captures": captures}
    return {"schema_version": 1, "kind": "offline_browser_e2e_analysis", "groups": reports,
            "timing_kind": TIMING_KIND, "overall_quality_pass": None,
            "note": "Groups are descriptive. Different case mixes or configurations are not a controlled paired comparison. Planned but uncreated case directories are unknown."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", action="append", required=True, help="LABEL=directory; repeat for native/cascade conditions")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    groups = {}
    for value in args.group:
        if "=" not in value:
            parser.error("--group requires LABEL=directory")
        label, path = value.split("=", 1)
        if not label or not path or label in groups:
            parser.error("Each group needs a unique nonempty label and path")
        groups[label] = path
    report = build_report(groups)
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(json.dumps({"output": str(args.output.resolve()), "groups": {key: value["summary"]["capture_count"] for key, value in report["groups"].items()}}))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
