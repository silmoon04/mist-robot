"""report.py — aggregate one or more results.jsonl files into a markdown report.

Usage: python harness/report.py results/matrix-* [-o results/REPORT.md]
"""
from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path

from metrics import percentile


def load_rows(patterns: list[str]) -> list[dict]:
    rows = []
    for pat in patterns:
        for d in glob.glob(pat):
            p = Path(d)
            files = [p] if p.is_file() else list(p.glob("**/results.jsonl")) + list(p.glob("**/longconvo.jsonl"))
            for f in files:
                for line in open(f, encoding="utf-8"):
                    r = json.loads(line)
                    r.setdefault("model", "?")
                    rows.append(r)
    return rows


def check_passed(check: dict) -> bool:
    """Accept suite checks ({name, pass}) and long-convo checks ({want, ok})."""
    return bool(check.get("pass", check.get("ok", False)))


def check_name(check: dict) -> str:
    return str(check.get("name", check.get("want", "unnamed check")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    rows = [r for r in load_rows(args.paths) if "checks" in r]

    by_cfg = defaultdict(list)
    for r in rows:
        by_cfg[f"{r.get('model')}:{r.get('thinking', '?')}:{r.get('soul', '?')}"].append(r)

    lines = ["# HEX-1 brain — suite report", ""]
    lines.append("| config | turn pass | react p50 | react p90 | total p50 | total p90 | cost |")
    lines.append("|---|---|---|---|---|---|---|")
    for cfg, rs in by_cfg.items():
        reacts = [r["ttf_any_s"] for r in rs if r.get("ttf_any_s")]
        totals = [r["total_s"] for r in rs]
        n_pass = sum(1 for r in rs if r["passed"])
        lines.append(
            f"| {cfg} | {n_pass}/{len(rs)} ({100 * n_pass / len(rs):.0f}%) "
            f"| {percentile(reacts, .5):.2f}s | {percentile(reacts, .9):.2f}s "
            f"| {percentile(totals, .5):.2f}s | {percentile(totals, .9):.2f}s "
            f"| ${sum(r.get('cost_usd', 0) for r in rs):.4f} |")

    # per-category pass rates
    lines += ["", "## By category", ""]
    cats = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in rows:
        if "category" in r:
            cfg = f"{r.get('model')}:{r.get('thinking', '?')}"
            cats[r["category"]][cfg][0] += r["passed"]
            cats[r["category"]][cfg][1] += 1
    cfgs = sorted({c for v in cats.values() for c in v})
    lines.append("| category | " + " | ".join(cfgs) + " |")
    lines.append("|---" * (len(cfgs) + 1) + "|")
    for cat, per in sorted(cats.items()):
        cells = []
        for c in cfgs:
            p, n = per.get(c, [0, 0])
            cells.append(f"{p}/{n}" if n else "—")
        lines.append(f"| {cat} | " + " | ".join(cells) + " |")

    # failures with detail
    lines += ["", "## Failures", ""]
    for cfg, rs in by_cfg.items():
        bad = [r for r in rs if not r["passed"]]
        if not bad:
            continue
        lines.append(f"### {cfg}")
        for r in bad:
            fails = [check_name(c) for c in r["checks"] if not check_passed(c)]
            sid = r.get("scenario", f"turn{r.get('turn')}")
            lines.append(f"- **{sid}** — failed: {', '.join(fails)}")
            lines.append(f"  - said: `{r['say'][:90]}`")
            lines.append(f"  - reply: {(r.get('reply') or '(empty)')[:160]}")
            tc = r.get("tool_calls") or r.get("tools") or []
            if tc:
                lines.append(f"  - tools: {json.dumps(tc)[:200]}")
        lines.append("")

    out = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(out)


if __name__ == "__main__":
    main()
