"""Two isolated Spark probes; no voice calls or live console changes."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from codex_client import CodexClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []
    client = None
    try:
        client = CodexClient(model="gpt-5.3-codex-spark", thinking="low", service_tier="default",
                             soul="mist-v2", with_memory=False, run_dir=args.out / "run", max_output_tokens=50)
        cases = [
            ("greeting", "Give Moon a warm, one-sentence hello, with a happy display cue alongside your words."),
            ("fresh_observation", "What objects can you see directly in front of you right now?"),
        ]
        for index, (name, prompt) in enumerate(cases):
            expressions = []
            result = client.ask(prompt, timeout=30, on_event=lambda event: expressions.append(event["expression"])
                                if event.get("type") == "face_expression" else None)
            tools = {call.name for call in result.tool_calls}
            checks = {"no_runtime_errors": not result.errors, "spoken_text_has_no_marker": "[[face:" not in result.text,
                      "within_output_target": result.output_tokens <= 50}
            if name == "greeting":
                checks.update(no_tool_round_trip=not tools, expression_delivered="happy" in expressions)
            else:
                checks.update(fresh_observe_retained="observe" in tools,
                              no_motion=not bool(tools & {"walk", "drive", "move", "turn", "dance"}),
                              admits_missing=any(word in result.text.lower() for word in ("no ", "can't", "cannot", "don't", "unavailable", "missing")))
            row = {"scenario": name, "process_state": "cold_first_turn" if index == 0 else "warm",
                   "backend_info": client.backend_info, "expressions": expressions, "checks": checks,
                   "passed": all(checks.values()), **asdict(result)}
            rows.append(row)
            with (args.out / "results.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(json.dumps({key: row[key] for key in ("scenario", "passed", "checks", "ttft_s", "total_s", "output_tokens", "timings", "expressions")}), flush=True)
            if result.errors:
                break
    except Exception as error:
        rows.append({"scenario": "startup", "passed": False, "error": str(error)})
    finally:
        if client:
            client.close()
    summary = {"completed": sum("checks" in row for row in rows), "passed": sum(row["passed"] for row in rows),
               "output_tokens": sum(row.get("output_tokens", 0) for row in rows),
               "input_tokens": sum(row.get("input_tokens", 0) for row in rows),
               "cached_input_tokens": sum(row.get("cache_read_tokens", 0) for row in rows),
               "voice_calls": 0, "model": "gpt-5.3-codex-spark", "effort": "low", "service_tier": "default",
               "failures": [row for row in rows if not row["passed"]]}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary), flush=True)
    return 0 if len(rows) == 2 and all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
