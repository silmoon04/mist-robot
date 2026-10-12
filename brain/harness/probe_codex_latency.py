"""Three short live probes of the conversation latency changes. No speech calls."""
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
    client = CodexClient(model="gpt-6-astra", thinking="low", service_tier="priority",
                         soul="mist-v2", with_memory=False, run_dir=args.out / "run", max_output_tokens=100)
    cases = [
        ("ordinary_chat", "I finally finished my project today."),
        ("capabilities", "What can you actually do right now? Check what is connected before answering."),
        ("fresh_observation", "What objects can you see directly in front of you right now?"),
    ]
    try:
        for index, (name, prompt) in enumerate(cases):
            expressions = []
            def event(value):
                if value.get("type") == "face_expression":
                    expressions.append(value["expression"])
            result = client.ask(prompt, timeout=45, on_event=event)
            tools = {call.name for call in result.tool_calls}
            checks = {"no_runtime_errors": not result.errors, "spoken_text_has_no_marker": "[[face:" not in result.text,
                      "within_output_target": result.output_tokens <= 100}
            if name in ("ordinary_chat", "capabilities"):
                checks["no_tool_round_trip"] = not tools
            if name == "capabilities":
                checks["accurate_simulation_limit"] = "simulat" in result.text.lower()
            if name == "fresh_observation":
                checks["fresh_observe_retained"] = "observe" in tools
            row = {"scenario": name, "process_state": "cold_first_turn" if index == 0 else "warm",
                   "backend_info": client.backend_info, "expressions": expressions, "checks": checks,
                   "passed": all(checks.values()), **asdict(result)}
            rows.append(row)
            with (args.out / "results.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(json.dumps({"scenario": name, "passed": row["passed"], "first_text_s": result.ttft_s,
                              "total_s": result.total_s, "tools": sorted(tools), "expressions": expressions,
                              "output_tokens": result.output_tokens, "timings": result.timings}), flush=True)
            if result.errors or sum(row["output_tokens"] for row in rows) >= 300:
                break
    finally:
        client.close()
    summary = {"completed": len(rows), "passed": sum(row["passed"] for row in rows),
               "output_tokens": sum(row["output_tokens"] for row in rows),
               "input_tokens": sum(row["input_tokens"] for row in rows),
               "cached_input_tokens": sum(row["cache_read_tokens"] for row in rows),
               "voice_calls": 0, "model": "gpt-6-astra", "effort": "low", "service_tier": "priority"}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary), flush=True)
    return 0 if len(rows) == 3 and all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
