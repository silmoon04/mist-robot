"""bench.py — repeatable benchmark runner, built on run_suite internals.

Usage:
  python harness/bench.py --models gemini-flash-lite-latest:off[,more]
                          [--souls butter-nihilist-v2,butter-nihilist]
                          [--only <substring>] [--pace 5] [--timeout 90]
                          [--repeat 1] [--run-id NAME] [--plan]

Writes results/<run-id>/{manifest.json, results.jsonl, summary.json, report.md}
and prints the same summary to stdout. On Ctrl-C, writes a partial summary
marked "aborted": true.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from pi_client import BRAIN_DIR
from metrics import percentile as pct
from run_suite import run_config
from scenarios import SCENARIOS


def filter_scenarios(only: str | None) -> list[dict]:
    if not only:
        return SCENARIOS
    return [s for s in SCENARIOS if only in s["id"] or only in s["category"]]


def _canon(obj):
    """Recursively tag tuples so json.dumps can't silently collapse them to
    lists (which would make pack_hash blind to tuple<->list DSL changes)."""
    if isinstance(obj, tuple):
        return {"__tuple__": [_canon(x) for x in obj]}
    if isinstance(obj, list):
        return [_canon(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _canon(v) for k, v in obj.items()}
    return obj


def pack_hash(scenarios: list[dict]) -> str:
    """Stable sha256 of the scenario pack structure, so two runs are only
    comparable if the pack matched."""
    blob = json.dumps(_canon(scenarios), sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def parse_model_specs(models: str) -> list[tuple[str, str]]:
    specs = []
    for spec in models.split(","):
        spec = spec.strip()
        if not spec:
            continue
        model, _, thinking = spec.partition(":")
        specs.append((model, thinking or "off"))
    return specs


def plan_matrix(model_specs: list[tuple[str, str]], souls: list[str],
                 scenarios: list[dict], repeat: int) -> list[dict]:
    n_turns = sum(len(s["turns"]) for s in scenarios)
    matrix = []
    for model, thinking in model_specs:
        for soul in souls:
            matrix.append({
                "model": model, "thinking": thinking, "soul": soul,
                "n_scenarios": len(scenarios), "n_turns": n_turns,
                "repeat": repeat, "total_turns": n_turns * repeat,
            })
    return matrix


def summarize_config(rows: list[dict], model: str, thinking: str, soul: str, repeat: int) -> dict:
    """Build one summary.json entry for a (model, thinking, soul) config,
    aggregated across all repeats of that config."""
    turn_rows = [r for r in rows if "checks" in r]
    # run_suite/run_config emits harness-failure rows like
    # {"scenario": id, "error": "new_session timeout"} that never got a
    # "checks" list. Count them as failed turns instead of dropping them,
    # else n_turns/pass_rate silently exclude harness errors.
    error_rows = [r for r in rows if "checks" not in r and "error" in r]
    n_turns = len(turn_rows) + len(error_rows)
    n_pass = sum(1 for r in turn_rows if r["passed"])

    by_category: dict[str, dict] = {}
    for r in turn_rows:
        cat = r.get("category", "?")
        c = by_category.setdefault(cat, {"turns": 0, "passed": 0, "rate": 0.0})
        c["turns"] += 1
        c["passed"] += 1 if r["passed"] else 0
    if error_rows:
        c = by_category.setdefault("harness_error", {"turns": 0, "passed": 0, "rate": 0.0})
        c["turns"] += len(error_rows)
    for c in by_category.values():
        c["rate"] = round(c["passed"] / c["turns"], 4) if c["turns"] else 0.0

    persona_checked = 0
    persona_passed = 0
    for r in turn_rows:
        for chk in r.get("checks", []):
            if chk["name"].startswith("persona:"):
                persona_checked += 1
                persona_passed += 1 if chk["pass"] else 0

    reacts = [r.get("ttf_any_s") for r in turn_rows if r.get("ttf_any_s") is not None]
    totals = [r.get("total_s") for r in turn_rows]

    failures = []
    for r in turn_rows:
        if not r["passed"]:
            failures.append({
                "scenario": r["scenario"], "turn": r["turn"],
                "failed_checks": [c["name"] for c in r["checks"] if not c["pass"]],
            })
    for r in error_rows:
        failures.append({
            "scenario": r["scenario"], "turn": None,
            "failed_checks": [f"harness_error: {r['error']}"],
        })

    return {
        "model": model, "thinking": thinking, "soul": soul, "repeat": repeat,
        "n_turns": n_turns, "n_pass": n_pass,
        "pass_rate": round(n_pass / n_turns, 4) if n_turns else 0.0,
        "by_category": by_category,
        "persona": {
            "checked": persona_checked, "passed": persona_passed,
            "rate": round(persona_passed / persona_checked, 4) if persona_checked else 0.0,
        },
        "latency": {
            "ttf_any_p50": pct(reacts, .5), "ttf_any_p90": pct(reacts, .9),
            "total_p50": pct(totals, .5), "total_p90": pct(totals, .9),
            "total_max": max(totals) if totals else None,
        },
        "tokens": {
            "input": sum(r.get("input_tokens", 0) for r in turn_rows),
            "output": sum(r.get("output_tokens", 0) for r in turn_rows),
        },
        "cost_usd": round(sum(r.get("cost_usd", 0.0) for r in turn_rows), 6),
        "failures": failures,
    }


def write_report_md(summaries: list[dict], manifest: dict, out_path: Path):
    lines = [f"# HEX-1 brain — bench report `{manifest['run_id']}`", ""]
    lines.append(f"- scenarios: {manifest['n_scenarios']}  "
                 f"pack_hash: `{manifest['pack_hash'][:12]}`  "
                 f"repeat: {manifest['repeat']}")
    if manifest.get("aborted"):
        lines.append("- **ABORTED (KeyboardInterrupt) — partial results**")
    lines.append("")
    lines.append("| config | turn pass | react p50 | react p90 | total p50 | total p90 | cost |")
    lines.append("|---|---|---|---|---|---|---|")
    for s in summaries:
        cfg = f"{s['model']}:{s['thinking']}:{s['soul']}"
        lat = s["latency"]

        def fmt(v):
            return f"{v:.2f}s" if isinstance(v, (int, float)) else "—"
        lines.append(
            f"| {cfg} | {s['n_pass']}/{s['n_turns']} ({100 * s['pass_rate']:.0f}%) "
            f"| {fmt(lat['ttf_any_p50'])} | {fmt(lat['ttf_any_p90'])} "
            f"| {fmt(lat['total_p50'])} | {fmt(lat['total_p90'])} "
            f"| ${s['cost_usd']:.4f} |")

    lines += ["", "## By category", ""]
    cats = sorted({cat for s in summaries for cat in s["by_category"]})
    cfg_keys = [f"{s['model']}:{s['thinking']}:{s['soul']}" for s in summaries]
    lines.append("| category | " + " | ".join(cfg_keys) + " |")
    lines.append("|---" * (len(cfg_keys) + 1) + "|")
    for cat in cats:
        cells = []
        for s in summaries:
            c = s["by_category"].get(cat)
            cells.append(f"{c['passed']}/{c['turns']}" if c else "—")
        lines.append(f"| {cat} | " + " | ".join(cells) + " |")

    lines += ["", "## Failures", ""]
    for s in summaries:
        if not s["failures"]:
            continue
        cfg = f"{s['model']}:{s['thinking']}:{s['soul']}"
        lines.append(f"### {cfg}")
        for f in s["failures"]:
            turn_label = f"#t{f['turn']}" if f["turn"] is not None else ""
            lines.append(f"- **{f['scenario']}{turn_label}** — failed: {', '.join(f['failed_checks'])}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="gemini-flash-lite-latest:off",
                    help="comma list of model:thinking")
    ap.add_argument("--souls", default="butter-nihilist-v2",
                    help="comma list of soul names")
    ap.add_argument("--only", default=None, help="substring filter on scenario id or category")
    ap.add_argument("--pace", type=float, default=5.0)
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--plan", action="store_true", help="print the run matrix and exit, no network")
    args = ap.parse_args()

    model_specs = parse_model_specs(args.models)
    souls = [s.strip() for s in args.souls.split(",") if s.strip()]
    scenarios = filter_scenarios(args.only)

    if args.plan:
        matrix = plan_matrix(model_specs, souls, scenarios, args.repeat)
        total_turns = sum(m["total_turns"] for m in matrix)
        print(f"=== PLAN: {len(matrix)} configs x {len(scenarios)} scenarios "
              f"({sum(len(s['turns']) for s in scenarios)} turns/pass) x repeat={args.repeat} ===")
        for m in matrix:
            print(f"  {m['model']}:{m['thinking']}:{m['soul']}  "
                  f"scenarios={m['n_scenarios']} turns/pass={m['n_turns']} "
                  f"repeat={m['repeat']} total_turns={m['total_turns']}")
        print(f"grand total turns: {total_turns}")
        return

    run_id = args.run_id or time.strftime("bench-%Y%m%d-%H%M%S")
    out_dir = BRAIN_DIR / "results" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": run_id, "started_wall": time.time(),
        "models": [f"{m}:{t}" for m, t in model_specs], "souls": souls,
        "only": args.only, "pace_s": args.pace, "timeout_s": args.timeout,
        "repeat": args.repeat, "n_scenarios": len(scenarios),
        "scenario_ids": [s["id"] for s in scenarios],
        "pack_hash": pack_hash(scenarios),
    }

    all_rows: list[dict] = []
    results_path = out_dir / "results.jsonl"
    summaries: list[dict] = []
    aborted = False
    try:
        for model, thinking in model_specs:
            for soul in souls:
                # cfg_rows is filled incrementally by _flush (below) as each
                # scenario completes, so a KeyboardInterrupt raised mid-way
                # through run_config still leaves this config's completed
                # rows available for a partial per-config summary — rows are
                # no longer lost just because run_config never returned.
                cfg_rows: list[dict] = []
                try:
                    for rep in range(args.repeat):
                        print(f"\n### {model}:{thinking} soul={soul} repeat={rep + 1}/{args.repeat} "
                              f"({len(scenarios)} scenarios)")
                        rep_dir = out_dir if args.repeat == 1 else out_dir / f"rep{rep}"
                        rep_dir.mkdir(parents=True, exist_ok=True)

                        def _flush(sc_rows, rep=rep):
                            for r in sc_rows:
                                r["repeat"] = rep
                            cfg_rows.extend(sc_rows)
                            all_rows.extend(sc_rows)
                            with open(results_path, "a", encoding="utf-8") as f:
                                for r in sc_rows:
                                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

                        run_config(model, thinking, soul, scenarios, rep_dir,
                                   args.timeout, args.pace, on_scenario_done=_flush)
                    summaries.append(summarize_config(cfg_rows, model, thinking, soul, args.repeat))
                except KeyboardInterrupt:
                    aborted = True
                    print("\n[bench] KeyboardInterrupt — writing partial results")
                    if cfg_rows:
                        partial = summarize_config(cfg_rows, model, thinking, soul, args.repeat)
                        partial["partial_config"] = True
                        summaries.append(partial)
                    raise
    except KeyboardInterrupt:
        pass

    manifest["aborted"] = aborted
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    write_report_md(summaries, manifest, out_dir / "report.md")

    print("\n=== SUMMARY ===")
    for s in summaries:
        cfg = f"{s['model']}:{s['thinking']}:{s['soul']}"
        lat = s["latency"]
        print(f"{cfg}")
        print(f"  turn pass rate : {s['n_pass']}/{s['n_turns']} ({100 * s['pass_rate']:.0f}%)")
        p50 = lat["ttf_any_p50"] if lat["ttf_any_p50"] is not None else float("nan")
        p90 = lat["ttf_any_p90"] if lat["ttf_any_p90"] is not None else float("nan")
        t50 = lat["total_p50"] if lat["total_p50"] is not None else float("nan")
        t90 = lat["total_p90"] if lat["total_p90"] is not None else float("nan")
        print(f"  reaction  p50={p50:.2f}s p90={p90:.2f}s")
        print(f"  total     p50={t50:.2f}s p90={t90:.2f}s")
        print(f"  cost: ${s['cost_usd']:.4f}")
        if s["failures"]:
            print("  failures:")
            for f in s["failures"]:
                turn_label = f"#t{f['turn']}" if f["turn"] is not None else ""
                print(f"    {f['scenario']}{turn_label}: {', '.join(f['failed_checks'])}")
    if aborted:
        print("\n[bench] ABORTED — partial results written")
    print(f"\nresults: {out_dir}")


if __name__ == "__main__":
    main()
