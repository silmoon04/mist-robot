"""Inspect expression coverage in synchronized browser snapshots, without rendering.

python expression_capture_audit.py CASE_DIRECTORY [CASE_DIRECTORY ...]
Counts are sampled frames, not exact durations or a subjective quality score.
"""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path


def analyze(browser):
    boundary = browser.get("observation_end_ms", float("inf"))
    frames = [frame for frame in browser.get("frames", []) if frame.get("t_ms", float("inf")) < boundary]
    commands = [{key: event.get(key) for key in ("t_ms", "expression", "variant", "duration_ms", "source", "epoch")}
                for event in browser.get("events", []) if event.get("type") == "face" and event.get("t_ms", float("inf")) < boundary]
    transitions, spans, counts = [], [], Counter()
    previous = None
    for frame in frames:
        policy = frame.get("policy", {})
        face = frame.get("face", {})
        mouth = face.get("drawnMouthFamily", {})
        active = frame.get("audio_active") is True
        key = (active, policy.get("expression"), face.get("expression"), mouth.get("active"))
        if key != previous:
            spans.append({"start_ms": frame["t_ms"], "last_sample_ms": frame["t_ms"], "sample_count": 0,
                          "audio_active": active, "policy_expression": key[1], "face_id": key[2], "mouth_family": key[3]})
        spans[-1]["last_sample_ms"] = frame["t_ms"]
        spans[-1]["sample_count"] += 1
        if previous is None or key[1] != previous[1]:
            transitions.append({"t_ms": frame["t_ms"], "audio_active": active, "policy": policy,
                                "face_id": key[2], "mouth_family": key[3]})
        if active:
            counts[key[1:]] += 1
        previous = key
    rows = [{"policy_expression": key[0], "face_id": key[1], "mouth_family": key[2], "sample_count": count}
            for key, count in counts.items()]
    observations = []
    for index, command in enumerate(commands):
        next_command = commands[index + 1]["t_ms"] if index + 1 < len(commands) else boundary
        following = [f for f in frames if command["t_ms"] <= f["t_ms"] < next_command and f.get("audio_active") is True]
        matches = [f for f in following if f.get("policy", {}).get("expression") == command["expression"]]
        differing = [f for f in following if f.get("policy", {}).get("expression") != command["expression"]]
        observations.append({"command": command, "active_samples_before_next_command": len(following),
                             "matching_active_samples": len(matches), "different_active_samples": len(differing),
                             "first_different_active_sample_ms": differing[0]["t_ms"] if differing else None,
                             "caution": "Later samples can belong to another utterance; inspect transcript and playback spans before assigning fault."})
    return {"case_id": browser.get("case_id"), "scope": "Same browser-frame snapshots of audio_active, expression policy, renderer face and mouth family",
            "human_quality": "unrated", "sample_count": len(frames), "active_sample_count": sum(counts.values()),
            "active_frame_counts": rows, "expression_commands": commands,
            "policy_transitions": transitions, "sample_spans": spans, "command_coverage_observations": observations,
            "limitations": ["Sampling can miss short transitions; counts are not exact durations.",
                            "Internal expiresAt/appliedAt values remain in their original policy clock; only frame t_ms uses the capture clock.",
                            "Emotion suitability and pronunciation still require human review."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path)
    args = parser.parse_args()
    for directory in args.directories:
        source = directory / "browser.json"
        raw = source.read_bytes()
        report = analyze(json.loads(raw))
        report["source_browser_sha256"] = hashlib.sha256(raw).hexdigest()
        report["source_code_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        output = directory / "audio_capture_audit"
        output.mkdir(exist_ok=True)
        (output / "expression-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"case_id": report["case_id"], "active_frame_counts": report["active_frame_counts"]}))


if __name__ == "__main__":
    main()
