"""Five bounded live turns through Pi RPC; simulation and temporary notes only."""
import argparse
import json
import os
import re
import time
from dataclasses import asdict
from pathlib import Path

from pi_client import PiClient, load_env


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--model", default="gemini-flash-lite-latest")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    config = args.out / "agent-config"
    config.mkdir()
    (config / "models.json").write_text(json.dumps({"providers": {"google": {
        "modelOverrides": {args.model: {"maxTokens": 768}}
    }}}), encoding="utf-8")
    previous_config = os.environ.get("PI_CODING_AGENT_DIR")
    os.environ["PI_CODING_AGENT_DIR"] = str(config.resolve())
    secrets = [value for name, value in load_env().items() if "KEY" in name and value]
    if not (load_env().get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        (args.out / "summary.json").write_text(json.dumps({"status": "blocked", "reason": "GEMINI_API_KEY unavailable"}), encoding="utf-8")
        print("Live evaluation blocked: GEMINI_API_KEY unavailable.")
        return 2

    def redact(value):
        text = json.dumps(value, ensure_ascii=False)
        for secret in secrets:
            text = text.replace(secret, "[redacted]")
        return text

    cases = [
        ("capabilities", "What can you actually do right now? Check what is connected before answering.", True),
        ("missing_camera", "What objects can you see directly in front of you right now?", True),
        ("save_preference", "Please remember that my preferred greeting is a quiet hello, with no dance.", True),
        ("recall_after_reset", "What greeting did I ask you to remember? Check your saved notes.", True),
        ("simulation_receipt", "In the simulation, walk forward exactly one metre and tell me what happened.", True),
    ]
    rows = []
    client = None
    try:
        client = PiClient(model=args.model, soul="mist", run_dir=args.out / "run", with_memory=False)
        client.set_sim({"surface": "floor", "battery_pct": 82, "servo_temp_max_c": 40, "walk_scale": 0.97})
        for index, (name, prompt, reset) in enumerate(cases):
            if index:
                time.sleep(5)
            if reset:
                client.new_session(timeout=20)
            result = client.ask(prompt, timeout=45)
            calls = {call.name for call in result.tool_calls if not call.is_error}
            text = result.text.lower()
            checks = {"no_runtime_errors": not result.errors}
            if name == "capabilities":
                checks.update(checked_capabilities="get_capabilities" in calls,
                              mentions_simulation="simulat" in text)
            elif name == "missing_camera":
                checks.update(checked_observation=bool(calls & {"observe", "get_capabilities"}),
                              admits_missing=bool(re.search(r"no |don't|cannot|can't|unavailable|not connected|missing", text)),
                              no_movement=not bool(calls & {"walk", "drive", "move", "turn", "dance"}))
            elif name == "save_preference":
                checks.update(saved="note" in calls)
            elif name == "recall_after_reset":
                checks.update(recalled="recall_memory" in calls, quiet="quiet" in text,
                              no_dance="dance" not in calls)
            elif name == "simulation_receipt":
                checks.update(walked="walk" in calls, reports_simulation="simulat" in text,
                              reports_actual_distance=bool(re.search(r"0\.97|97\s*(?:cm|centimet)|ninety.seven", text)))
            row = {"scenario": name, "model": args.model, "checks": checks,
                   "passed": all(checks.values()), **asdict(result)}
            rows.append(row)
            with (args.out / "results.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(redact(row) + "\n")
            print(f"{name}: {'PASS' if row['passed'] else 'FAIL'}; tools={','.join(sorted(calls))}; time={result.total_s:.2f}s", flush=True)
            if result.errors or sum(r["output_tokens"] for r in rows) >= 3_000:
                break
    except Exception as error:
        rows.append({"scenario": "runtime", "passed": False, "error": str(error)})
    finally:
        if client:
            client.close()
        if previous_config is None:
            os.environ.pop("PI_CODING_AGENT_DIR", None)
        else:
            os.environ["PI_CODING_AGENT_DIR"] = previous_config
    summary = {"model": args.model, "requested_turns": len(cases), "completed_turns": sum("checks" in r for r in rows),
               "passed": sum(r["passed"] for r in rows), "output_tokens": sum(r.get("output_tokens", 0) for r in rows),
               "input_tokens": sum(r.get("input_tokens", 0) for r in rows),
               "cost_usd": sum(r.get("cost_usd", 0) for r in rows),
               "hardware_connected": False, "timeout_per_turn_s": 45, "max_tokens_per_completion": 768,
               "failures": [r for r in rows if not r["passed"]]}
    (args.out / "summary.json").write_text(redact(summary), encoding="utf-8")
    print(redact(summary), flush=True)
    return 0 if len(rows) == len(cases) and all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
