"""Summarize existing conversation timings without reading prompt or reply text."""
import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


def analyze(path: Path) -> dict:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for record in records:
        text, any_event = record.get("ttft_s"), record.get("ttf_any_s")
        if text is None or any_event is None:
            continue
        rows.append({"at": datetime.fromtimestamp(record["at"], timezone.utc).isoformat(),
                     "backend": record.get("backend"), "model": record.get("model"),
                     "first_text_s": text, "first_action_s": any_event,
                     "action_to_text_gap_s": max(0, text - any_event),
                     "total_s": record.get("total_s"), "input_tokens": record.get("input_tokens"),
                     "output_tokens": record.get("output_tokens"), "runtime_errors": len(record.get("errors", []))})
    return {"turns": rows, "count": len(rows),
            "first_text_median_s": statistics.median(row["first_text_s"] for row in rows) if rows else None,
            "first_text_max_s": max((row["first_text_s"] for row in rows), default=None)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--max-first-text", type=float)
    args = parser.parse_args()
    summary = analyze(args.metrics)
    if args.max_first_text is not None:
        summary["first_text_budget_s"] = args.max_first_text
        summary["within_budget"] = bool(summary["count"]) and summary["first_text_max_s"] <= args.max_first_text
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("within_budget", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
