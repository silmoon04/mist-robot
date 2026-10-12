"""Build a portable, read-only view of recorded Luna test reports.

Only report and review files are read. Runtime stores, credentials, raw event
logs and model catalogs are deliberately outside this input contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "brain/results"
OUT = ROOT / "brain/duplex/static/luna-tests.json"
OMIT = re.compile(r"(?:thread.?id|session.?id|job.?id|tool.?call.?id|api.?key|authorization|access.?token|refresh.?token|secret|password|credential|backend_info|model_children)", re.I)


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items() if not OMIT.search(str(k))}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"[A-Za-z]:[\\/][^\n\r\"<>]*", "[local path omitted]", value)
        value = re.sub(r"/(?:Users|home)/[^\s\"<>]+", "[local path omitted]", value)
        value = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]+)", "[credential omitted]", value)
        value = re.sub(r"\b(?:thread|job|session)[_-][A-Za-z0-9_-]{12,}\b", "[runtime identifier omitted]", value)
        return value
    return value


def picked(data, names):
    return clean({name: data[name] for name in names if name in data})


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def status(value):
    return "pass" if value is True else "fail" if value is False else "ungraded"


def record(raw, index, kind):
    checks = raw.get("checks", {})
    verdict = checks.get("passed", raw.get("passed"))
    if "automated_failures" in raw:
        verdict = not raw["automated_failures"]
    r = {
        "id": str(raw.get("id", raw.get("index", index))),
        "input": clean(raw.get("input", raw.get("prompt", ""))),
        "text": clean(raw.get("text", raw.get("job", {}).get("summary", ""))),
        "status": status(verdict),
        "failures": clean(checks.get("failures", raw.get("failures", raw.get("automated_failures", [])))),
        "errors": clean(raw.get("errors", [])),
        "tools": clean(raw.get("tools", raw.get("calls", []))),
        "receipts": clean(raw.get("receipts", raw.get("actual_tool_receipts", []))),
        "transcripts": clean(raw.get("transcripts", [])),
        "timings": picked(raw, ["first_text_s", "first_tool_s", "total_s", "elapsed_s", "first_text_after_tool_s", "first_speakable_phrase_s", "fixture_end_to_first_delta_s", "fixture_end_to_first_tool_s", "fixture_end_to_face_s", "start_handle_s", "result_from_start_s"]),
        "detail": picked(raw, ["timings", "first_phrase", "phrases", "expected_calls", "expected_face_ids", "selected_face_ids", "faces", "checks", "application_invariants", "display_invariant", "display_invariants", "display_invariant_passed", "state_before", "state_after", "guard_refusals", "manual_review", "manual_criteria", "foreground", "cancellation", "explicit_interruption", "session_continuation"]),
    }
    if isinstance(raw.get("first_phrase"), dict):
        r["timings"]["first_speakable_phrase_s"] = raw["first_phrase"].get("at_s")
    if kind == "native":
        r["timings"].pop("elapsed_s", None)
    invariant = raw.get("application_invariants", {})
    r["state_protected"] = invariant.get("state_protected") if isinstance(invariant, dict) else None
    if isinstance(raw.get("display_invariant_passed"), bool):
        r["display_protected"] = raw["display_invariant_passed"]
    for key in ("display_invariant", "display_invariants"):
        inv = raw.get(key)
        if isinstance(inv, dict):
            r["display_protected"] = inv.get("passed", inv.get("protected"))
        elif isinstance(inv, bool):
            r["display_protected"] = inv
    return r


def build():
    data = {"generated_at": datetime.now(timezone.utc).isoformat(), "sessions": [], "runs": [], "reviews": [], "deterministic": [], "sources": [], "gaps": []}

    def load(path):
        try:
            raw = path.read_bytes()
            result = json.loads(raw.decode("utf-8-sig"))
            data["sources"].append({"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()})
            return result
        except (OSError, ValueError) as exc:
            data["gaps"].append(f"Could not read {path.relative_to(ROOT).as_posix()}: {type(exc).__name__}")
            return None

    def run(path, suite, name, kind, groups):
        report = load(path)
        if not isinstance(report, dict):
            return
        run_id = f"{suite}/{name}"
        known_limits = report.get("limits", [])
        if isinstance(known_limits, str):
            known_limits = [known_limits]
        if report.get("raw_case_correlation_valid") is False:
            known_limits = [*known_limits, "Historical native run: case correlation is invalid. These automatic verdicts are not reliable; consult the corrected trace review."]
        meta = {"id": run_id, "suite": suite, "name": name, "kind": kind, "source": path.relative_to(ROOT).as_posix(), "model": report.get("model", "Native realtime front; Luna backing tools"), "limits": clean(known_limits), "metadata": picked(report, ["reasoning", "service_tier", "architecture", "scope", "runtime", "startup", "startup_s", "cold_constructor_s", "configure_tool_session_s", "latency_note", "post_review", "expected_turns", "expected_cases", "completed", "unique_faces_selected", "display_invariants_passed", "guard_refusals", "request_text_guard_enabled", "state_checks", "expression_request_guard", "raw_case_correlation_valid"])}
        sessions = []
        for group, style, rows in groups(report):
            if not isinstance(rows, list):
                continue
            turns = [record(row, n + 1, kind) for n, row in enumerate(rows) if isinstance(row, dict)]
            if not turns:
                continue
            session = {"id": f"{run_id}/{group}", "run_id": run_id, "suite": suite, "run": name, "style": style, "group": group, "kind": kind, "turns": turns, "source": meta["source"]}
            if report.get("raw_case_correlation_valid") is False:
                session["correlation_invalid"] = True
            data["sessions"].append(session)
            sessions.append(session)
        rows = [turn for s in sessions for turn in s["turns"]]
        meta["counts"] = dict(Counter(t["status"] for t in rows))
        meta["count"] = len(rows)
        meta["state_protected"] = sum(t.get("state_protected") is True for t in rows)
        metrics = {}
        for key in {k for t in rows for k in t["timings"]}:
            values = [t["timings"].get(key) for t in rows]
            values = [x for x in values if isinstance(x, (int, float)) and math.isfinite(x)]
            if values:
                metrics[key] = {"n": len(values), "median_s": statistics.median(values), "p90_s": percentile(values, .9)}
        meta["metrics"] = metrics
        data["runs"].append(meta)

    for path in sorted((RESULTS / "luna_conversations_20260922").glob("*/report.json")):
        run(path, "Conversations", path.parent.name, "luna", lambda d: [(a["id"], a.get("style", a["id"]), a.get("turns", [])) for a in d.get("arcs", [])])
    for path in sorted((RESULTS / "luna_faces_20260922").glob("*/report.json")):
        def face_groups(d):
            groups = {}
            for case in d.get("cases", []):
                groups.setdefault(case.get("group", "Face selection"), []).append(case)
            return [(key, key.replace("_", " "), rows) for key, rows in groups.items()]
        run(path, "Faces", path.parent.name, "luna", face_groups)
    path = RESULTS / "luna_latency_20260922/report.json"
    if path.exists():
        run(path, "Latency", "continuous baseline", "luna", lambda d: [("continuous", "Continuous session", d.get("baseline", []))])
        for tier in ("default", "priority"):
            run(path, "Latency", f"matched {tier}", "luna", lambda d, tier=tier: [(tier, f"Matched {tier} tier", [r for r in d.get("matched_tier_trials", []) if r.get("tier") == tier])])
    for pattern in ("luna_native_20260922*/report.json", "luna_handoff_*/report.json"):
        for path in sorted(RESULTS.glob(pattern)):
            name = path.parent.name.replace("luna_", "").replace("_20260922", "").replace("_", " ")
            run(path, "Native voice", name, "native", lambda d: [("session", "Synthetic microphone session", d.get("cases", []))])
    for path in sorted(RESULTS.glob("luna_background_20260922*/report.json")):
        name = path.parent.name.replace("luna_background_20260922", "").strip("_") or "baseline"
        run(path, "Background", name, "luna", lambda d: [("jobs", "Background analysis with a test audio sink", d.get("cases", []))])

    review_paths = [
        "luna_review_20260922/baseline_review.md", "luna_review_20260922/refined_adjudication.md", "luna_review_20260922/final_review.md",
        "luna_faces_20260922/REVISED_REVIEW.md", "luna_native_20260922_refined/REVIEW.md", "luna_latency_20260922/REVIEW.md",
        "luna_faces_20260922/GUARD_REVIEW.md", "luna_review_20260922/guard_addendum.md",
        "luna_conversations_20260922/FINAL_MEMORY_CHECK.md", "luna_latency_20260922/HANDOFF_REVIEW.md",
        "luna_native_20260922_refined/PREDICTIVE_TEXT_REVIEW.md",
    ]
    for path in sorted(RESULTS.glob("luna_background_20260922*/*REVIEW*.md")):
        review_paths.append(path.relative_to(RESULTS).as_posix())
    for name in review_paths:
        path = RESULTS / name
        if path.exists():
            text = path.read_text(encoding="utf-8-sig")
            data["reviews"].append({"source": path.relative_to(ROOT).as_posix(), "text": clean(text)})
    control_path = RESULTS / "luna_review_20260922/control_results.json"
    if control_path.exists():
        report = load(control_path)
        if report:
            data["deterministic"].append({"source": control_path.relative_to(ROOT).as_posix(), "report": picked(report, ["command", "result", "tests", "additional_subcases", "initial_reproduced_failures", "scope"])})
    for name in ("luna_native_20260922/wire_review.json", "luna_native_20260922_refined/review.json", "luna_latency_20260922/handoff_comparison.json", "luna_conversations_20260922/conversation_summary.json", "luna_background_20260922_capabilities/review.json"):
        path = RESULTS / name
        if path.exists():
            report = load(path)
            data["reviews"].append({"source": path.relative_to(ROOT).as_posix(), "report": clean(report)})

    data["sources"] = list({s["path"]: s for s in data["sources"]}.values())
    data["counts"] = {"records": sum(len(s["turns"]) for s in data["sessions"]), "sessions": len(data["sessions"]), "runs": len(data["runs"])}
    data["notes"] = [
        "Counts are recorded model turns or native fixture cases, with repeated fixtures retained across runs. Deterministic assertions are separate.",
        "Pass and fail mean the recorded automatic contract check. They do not grade whether a conversation feels natural. Manual reviews retain their original scope and date.",
        "A guard can prevent a state change while the model's tool choice still fails. These are separate outcomes.",
        "Native sessions use the Codex realtime front voice with Luna handling delegated tools. They are not Luna speech-to-speech sessions.",
        "ElevenLabs was replaced with a text recorder in native tests because billing blocked synthesis. Audible latency, room echo, voice quality and physical phone lip sync are not verified here.",
        "Text timing starts when a backend turn is submitted. Native fixture-end timing starts when paced microphone audio ends; delayed transcript completion is not a useful latency origin.",
        "P90 uses nearest rank, calculated from available numeric records within each run. Case mixes and concurrency differ; cross-run medians are not a controlled speedup claim.",
    ]
    return clean(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    data = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output.relative_to(ROOT).as_posix(), **data["counts"], "gaps": data["gaps"]}))
