"""run_suite.py — run the scenario suite across model configs.

Usage:
  python harness/run_suite.py --models gemini-3.5-flash:off,gemini-3.1-flash-lite:off
  python harness/run_suite.py --models gemini-3.5-flash:low --soul mist --only safety
  python harness/run_suite.py --models gemini-3.5-flash:off --only cmd_walk_simple

Results land in results/<run-id>/results.jsonl plus a printed summary.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from pi_client import PiClient, BRAIN_DIR
from metrics import percentile
from scenarios import SCENARIOS, evaluate_turn


def ask_with_retry(client: PiClient, say: str, timeout: float, retries: int = 2):
    """Retry a turn on transient provider errors (429/503/fetch failed)."""
    for attempt in range(retries + 1):
        res = client.ask(say, timeout=timeout)
        transient = res.errors and not res.text and not res.tool_calls and any(
            k in " ".join(res.errors) for k in ("429", "503", "fetch failed", "UNAVAILABLE", "timeout"))
        if not transient or attempt == retries:
            return res
        delay = 25.0
        m = re.search(r"retry in (\d+(?:\.\d+)?)", " ".join(res.errors), re.I)
        if m:
            delay = min(float(m.group(1)) + 2, 65)
        print(f"    (transient error, retry {attempt + 1} in {delay:.0f}s)")
        time.sleep(delay)
    return res


def run_config(model: str, thinking: str, soul: str, scenarios: list[dict],
               out_dir: Path, timeout: float, pace_s: float = 0.0,
               on_scenario_done=None) -> list[dict]:
    """Run one (model, thinking, soul) config across `scenarios`.

    `on_scenario_done`, if given, is called with the list of rows produced by
    each scenario (including single-row harness-error rows) as soon as that
    scenario finishes, so a caller can stream results to disk / accumulate a
    partial view even if a later scenario raises (e.g. KeyboardInterrupt).
    """
    run_dir = out_dir / f"{model.replace('/', '_')}-{thinking}-{soul}"
    run_dir.mkdir(parents=True, exist_ok=True)
    client = PiClient(model=model, thinking=thinking, soul=soul, run_dir=run_dir)
    rows = []
    try:
        first = True
        for sc in scenarios:
            if not first:
                try:
                    client.new_session()
                except TimeoutError:
                    err_row = {"scenario": sc["id"], "error": "new_session timeout"}
                    rows.append(err_row)
                    if on_scenario_done:
                        on_scenario_done([err_row])
                    continue
            first = False
            sc_rows = []
            for i, turn in enumerate(sc["turns"]):
                if pace_s:
                    time.sleep(pace_s)
                # per-turn sim override: a turn dict may carry "sim" — apply it
                # before this turn, else fall back to the scenario-level sim.
                client.set_sim(turn["sim"] if "sim" in turn else sc.get("sim"))
                res = ask_with_retry(client, turn["say"], timeout=timeout)
                checks = evaluate_turn(turn.get("expect", {}), res)
                sc_rows.append({
                    "scenario": sc["id"], "category": sc["category"], "turn": i,
                    "model": model, "thinking": thinking, "soul": soul,
                    "say": turn["say"], "reply": res.text,
                    "tool_calls": [{"name": c.name, "args": c.args, "t": round(c.t_offset_s, 3),
                                    "error": c.is_error} for c in res.tool_calls],
                    "ttft_s": res.ttft_s, "ttf_tool_s": res.ttf_tool_s,
                    "ttf_any_s": res.ttf_any_s, "total_s": round(res.total_s, 3),
                    "llm_turns": res.turns,
                    "input_tokens": res.input_tokens, "output_tokens": res.output_tokens,
                    "cache_read_tokens": res.cache_read_tokens,
                    "cost_usd": round(res.cost_usd, 6),
                    "checks": [{"name": n, "pass": p, "detail": d} for n, p, d in checks],
                    "passed": all(p for _, p, _ in checks),
                    "errors": res.errors,
                })
            rows.extend(sc_rows)
            if on_scenario_done:
                on_scenario_done(sc_rows)
            status = "PASS" if all(r["passed"] for r in sc_rows) else "FAIL"
            lat = max((r["ttf_any_s"] or r["total_s"]) for r in sc_rows)
            print(f"  [{status}] {sc['id']:26s} react={lat:5.2f}s "
                  f"total={sum(r['total_s'] for r in sc_rows):5.2f}s "
                  f"tools={sum(len(r['tool_calls']) for r in sc_rows)}")
    finally:
        client.close()
    return rows


def summarize(rows: list[dict]):
    by_config: dict[str, list[dict]] = {}
    for r in rows:
        if "error" in r and "scenario" in r and "model" not in r:
            continue
        key = f"{r['model']}:{r['thinking']}:{r['soul']}"
        by_config.setdefault(key, []).append(r)
    print("\n=== SUMMARY ===")
    for key, rs in by_config.items():
        n_turns = len(rs)
        n_pass = sum(1 for r in rs if r["passed"])
        reacts = sorted(r["ttf_any_s"] for r in rs if r["ttf_any_s"] is not None)
        totals = sorted(r["total_s"] for r in rs)
        cost = sum(r["cost_usd"] for r in rs)

        print(f"{key}")
        print(f"  turn pass rate : {n_pass}/{n_turns} ({100 * n_pass / max(n_turns, 1):.0f}%)")
        print(f"  reaction  p50={percentile(reacts, .5):.2f}s p90={percentile(reacts, .9):.2f}s")
        print(f"  total     p50={percentile(totals, .5):.2f}s p90={percentile(totals, .9):.2f}s max={totals[-1]:.2f}s")
        print(f"  suite cost: ${cost:.4f}")
        failed = {}
        for r in rs:
            if not r["passed"]:
                bad = [c["name"] for c in r["checks"] if not c["pass"]]
                failed[f"{r['scenario']}#t{r['turn']}"] = bad
        if failed:
            print("  failures:")
            for k, v in failed.items():
                print(f"    {k}: {', '.join(v)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="gemini-3.5-flash:off",
                    help="comma list of model:thinking (thinking: off/minimal/low/...)")
    ap.add_argument("--soul", default="butter-nihilist-v2")
    ap.add_argument("--only", default=None, help="substring filter on scenario id or category")
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--pace", type=float, default=0.0, help="seconds to sleep before each turn (free-tier RPM)")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    scenarios = SCENARIOS
    if args.only:
        scenarios = [s for s in SCENARIOS
                     if args.only in s["id"] or args.only in s["category"]]
    run_id = args.run_id or time.strftime("suite-%Y%m%d-%H%M%S")
    out_dir = BRAIN_DIR / "results" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    for spec in args.models.split(","):
        model, _, thinking = spec.partition(":")
        thinking = thinking or "off"
        print(f"\n### {model}:{thinking} soul={args.soul} ({len(scenarios)} scenarios)")
        rows = run_config(model, thinking, args.soul, scenarios, out_dir, args.timeout, args.pace)
        all_rows.extend(rows)
        with open(out_dir / "results.jsonl", "a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summarize(all_rows)
    print(f"\nresults: {out_dir / 'results.jsonl'}")


if __name__ == "__main__":
    main()
