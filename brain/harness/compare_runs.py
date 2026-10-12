"""compare_runs.py — markdown comparison across two or more bench.py runs.

Usage:
  python harness/compare_runs.py results/runA results/runB [more...] [--out compare.md]

Works entirely offline against existing results/<run-id>/ directories
(manifest.json, summary.json, results.jsonl). Exits 0 on success, 1 if a run
directory is missing required files.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def config_key(s: dict) -> str:
    return f"{s['model']}:{s['thinking']}:{s['soul']}"


def load_run(path: Path) -> dict:
    manifest_f = path / "manifest.json"
    summary_f = path / "summary.json"
    if not manifest_f.exists() or not summary_f.exists():
        raise FileNotFoundError(f"{path} is missing manifest.json/summary.json (not a bench run dir)")
    manifest = json.loads(manifest_f.read_text(encoding="utf-8"))
    summary = json.loads(summary_f.read_text(encoding="utf-8"))
    rows = []
    rp = path / "results.jsonl"
    if rp.exists():
        for line in rp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return {
        "path": path,
        "run_id": manifest.get("run_id", path.name),
        "manifest": manifest,
        "summary": summary,
        "rows": rows,
    }


def pass_rate_table(runs: list[dict]) -> list[str]:
    configs = sorted({config_key(s) for r in runs for s in r["summary"]})
    if not configs:
        return ["_no configs found_", ""]
    lines = ["| run | " + " | ".join(configs) + " |",
             "|---" * (len(configs) + 1) + "|"]
    for r in runs:
        by_cfg = {config_key(s): s for s in r["summary"]}
        cells = []
        for c in configs:
            s = by_cfg.get(c)
            if s:
                cells.append(f"{s['n_pass']}/{s['n_turns']} ({100 * s['pass_rate']:.0f}%)")
            else:
                cells.append("—")
        lines.append(f"| {r['run_id']} | " + " | ".join(cells) + " |")
    return lines


def category_rates(run: dict) -> dict[str, float]:
    agg: dict[str, list[int]] = {}
    for s in run["summary"]:
        for cat, c in s.get("by_category", {}).items():
            a = agg.setdefault(cat, [0, 0])
            a[0] += c.get("passed", 0)
            a[1] += c.get("turns", 0)
    return {cat: (p / n if n else 0.0) for cat, (p, n) in agg.items()}


def category_delta_table(runs: list[dict]) -> list[str]:
    if len(runs) < 2:
        return ["_need >=2 runs for category deltas_", ""]
    first = runs[0]
    later = runs[1:]
    first_rates = category_rates(first)
    later_rates = [category_rates(r) for r in later]
    cats = sorted(set(first_rates) | {c for lr in later_rates for c in lr})
    lines = ["| category | " + f"{first['run_id']} (base)" + " | " +
             " | ".join(f"{r['run_id']} (delta)" for r in later) + " |",
             "|---" * (len(later) + 2) + "|"]
    for cat in cats:
        base = first_rates.get(cat)
        cells = [f"{100 * base:.0f}%" if base is not None else "—"]
        for lr in later_rates:
            cur = lr.get(cat)
            if base is None or cur is None:
                cells.append("—")
            else:
                delta = (cur - base) * 100
                sign = "+" if delta >= 0 else ""
                cells.append(f"{sign}{delta:.1f}pp")
        lines.append(f"| {cat} | " + " | ".join(cells) + " |")
    return lines


def _fmt(v):
    return f"{v:.2f}s" if isinstance(v, (int, float)) else "—"


def latency_table(runs: list[dict]) -> list[str]:
    lines = ["| run | config | react p50 | react p90 | total p50 | total p90 |",
             "|---|---|---|---|---|---|"]
    for r in runs:
        for s in r["summary"]:
            lat = s.get("latency", {})
            lines.append(
                f"| {r['run_id']} | {config_key(s)} "
                f"| {_fmt(lat.get('ttf_any_p50'))} | {_fmt(lat.get('ttf_any_p90'))} "
                f"| {_fmt(lat.get('total_p50'))} | {_fmt(lat.get('total_p90'))} |")
    return lines


def cost_table(runs: list[dict]) -> list[str]:
    lines = ["| run | config | cost |", "|---|---|---|"]
    for r in runs:
        for s in r["summary"]:
            lines.append(f"| {r['run_id']} | {config_key(s)} | ${s.get('cost_usd', 0):.4f} |")
    return lines


def _turn_map(run: dict, scenario_ids: set[str] | None = None) -> dict[tuple, bool]:
    m = {}
    for row in run["rows"]:
        if "checks" not in row or "scenario" not in row:
            continue
        if scenario_ids is not None and row["scenario"] not in scenario_ids:
            continue
        # Include "repeat" in the key — bench.py's --repeat > 1 produces
        # multiple rows sharing (config, scenario, turn); without repeat in
        # the key they'd overwrite each other and flips would reflect only
        # the last repeat encountered in file order.
        key = (f"{row.get('model')}:{row.get('thinking')}:{row.get('soul')}",
               row["scenario"], row["turn"], row.get("repeat", 0))
        m[key] = row["passed"]
    return m


def flips(runs: list[dict]) -> list[dict]:
    """For each run after the first, find scenario+turn flips vs the first run."""
    first = runs[0]
    first_hash = first["manifest"].get("pack_hash")
    out = []
    for r in runs[1:]:
        same_hash = bool(first_hash) and first_hash == r["manifest"].get("pack_hash")
        warn = None
        scenario_filter = None
        if not same_hash:
            first_ids = {row["scenario"] for row in first["rows"] if "scenario" in row}
            other_ids = {row["scenario"] for row in r["rows"] if "scenario" in row}
            scenario_filter = first_ids & other_ids
            warn = (f"pack_hash differs between {first['run_id']} and {r['run_id']} "
                    f"— comparing only {len(scenario_filter)} shared scenario id(s)")
        fm = _turn_map(first, scenario_filter)
        om = _turn_map(r, scenario_filter)
        regressions = []
        fixes = []
        for key in sorted(set(fm) & set(om)):
            fp, op = fm[key], om[key]
            if fp and not op:
                regressions.append(key)
            elif not fp and op:
                fixes.append(key)
        out.append({"run_id": r["run_id"], "warn": warn,
                    "regressions": regressions, "fixes": fixes})
    return out


def flips_section(runs: list[dict]) -> list[str]:
    if len(runs) < 2:
        return ["_need >=2 runs for flips_", ""]
    lines = []
    for f in flips(runs):
        lines.append(f"### {runs[0]['run_id']} -> {f['run_id']}")
        if f["warn"]:
            # Plain ASCII only: on Windows, stdout defaults to the cp1252
            # code page even when piped/redirected, and a literal warning
            # emoji here raised UnicodeEncodeError on the print(report) path
            # (exit 1) -- exactly the "works offline, exit 0" contract this
            # warning is supposed to satisfy.
            lines.append(f"> **WARNING:** {f['warn']}")
        if f["regressions"]:
            lines.append("**Regressions (pass -> fail):**")
            for cfg, sc, turn, repeat in f["regressions"]:
                lines.append(f"- `{cfg}` {sc}#t{turn} (repeat {repeat})")
        else:
            lines.append("_no regressions_")
        if f["fixes"]:
            lines.append("")
            lines.append("**Fixes (fail -> pass):**")
            for cfg, sc, turn, repeat in f["fixes"]:
                lines.append(f"- `{cfg}` {sc}#t{turn} (repeat {repeat})")
        else:
            lines.append("")
            lines.append("_no fixes_")
        lines.append("")
    return lines


def build_report(runs: list[dict]) -> str:
    lines = ["# HEX-1 brain — run comparison", ""]
    lines.append("Runs: " + ", ".join(r["run_id"] for r in runs))
    lines += ["", "## Overall pass rate", ""]
    lines += pass_rate_table(runs)
    lines += ["", "## By-category delta vs base run", ""]
    lines += category_delta_table(runs)
    lines += ["", "## Latency", ""]
    lines += latency_table(runs)
    lines += ["", "## Cost", ""]
    lines += cost_table(runs)
    lines += ["", "## Flips", ""]
    lines += flips_section(runs)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="results/<run-id> directories")
    ap.add_argument("--out", default=None, help="write markdown to this path (default: stdout)")
    args = ap.parse_args(argv)

    try:
        runs = [load_run(Path(p)) for p in args.runs]
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    report = build_report(runs)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
