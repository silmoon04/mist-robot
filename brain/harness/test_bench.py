"""test_bench.py — offline tests for bench.py and compare_runs.py.

Fabricates two tiny fake run dirs, runs compare_runs on them (asserts flips
and by-category deltas are detected), and asserts `bench.py --plan` runs
without any network access. Plain script, no pytest. Exit 0/1.
"""
from __future__ import annotations

import json
import queue
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
BRAIN_DIR = HARNESS_DIR.parent

sys.path.insert(0, str(HARNESS_DIR))

import compare_runs  # noqa: E402


FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    status = "ok" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def _summary_entry(model, thinking, soul, n_pass, n_turns, by_category, cost=0.01):
    return {
        "model": model, "thinking": thinking, "soul": soul, "repeat": 1,
        "n_turns": n_turns, "n_pass": n_pass,
        "pass_rate": round(n_pass / n_turns, 4) if n_turns else 0.0,
        "by_category": by_category,
        "persona": {"checked": n_turns, "passed": n_pass,
                    "rate": round(n_pass / n_turns, 4) if n_turns else 0.0},
        "latency": {"ttf_any_p50": 1.1, "ttf_any_p90": 2.2,
                    "total_p50": 2.0, "total_p90": 3.5, "total_max": 4.0},
        "tokens": {"input": 100, "output": 50},
        "cost_usd": cost,
        "failures": [],
    }


def _row(scenario, turn, category, model, thinking, soul, passed):
    return {
        "scenario": scenario, "category": category, "turn": turn,
        "model": model, "thinking": thinking, "soul": soul,
        "say": "hi", "reply": "ok",
        "tool_calls": [], "ttft_s": 0.5, "ttf_tool_s": None, "ttf_any_s": 0.5,
        "total_s": 1.0, "llm_turns": 1, "input_tokens": 10, "output_tokens": 5,
        "cache_read_tokens": 0, "cost_usd": 0.001,
        "checks": [{"name": "tool:x", "pass": passed, "detail": ""}],
        "passed": passed, "errors": [], "repeat": 0,
    }


def make_fake_run(root: Path, run_id: str, pack_hash: str, s1_pass: bool, s2_pass: bool) -> Path:
    """s1 exercises regression detection (A passes, B may fail);
    s2 exercises fix detection (A fails, B may pass)."""
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id, "started_wall": 0, "models": ["dummy:off"],
        "souls": ["butter-nihilist"], "only": None, "pace_s": 0, "timeout_s": 5,
        "repeat": 1, "n_scenarios": 2, "scenario_ids": ["s1", "s2"],
        "pack_hash": pack_hash, "aborted": False,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    rows = [
        _row("s1", 0, "cat1", "dummy", "off", "butter-nihilist", s1_pass),
        _row("s2", 0, "cat2", "dummy", "off", "butter-nihilist", s2_pass),
    ]
    with open(run_dir / "results.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    n_pass = sum(1 for r in rows if r["passed"])
    by_category = {
        "cat1": {"turns": 1, "passed": 1 if s1_pass else 0,
                 "rate": 1.0 if s1_pass else 0.0},
        "cat2": {"turns": 1, "passed": 1 if s2_pass else 0,
                 "rate": 1.0 if s2_pass else 0.0},
    }
    summary = [_summary_entry("dummy", "off", "butter-nihilist", n_pass, 2, by_category)]
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return run_dir


def test_compare_runs_flips_and_deltas():
    tmp = Path(tempfile.mkdtemp(prefix="bench_test_"))
    try:
        # base run: s1 passes, s2 fails
        run_a = make_fake_run(tmp, "runA", "hashXYZ", s1_pass=True, s2_pass=False)
        # later run: s1 fails (regression), s2 passes (fix) -- same pack hash
        run_b = make_fake_run(tmp, "runB", "hashXYZ", s1_pass=False, s2_pass=True)

        out_md = tmp / "compare.md"
        rc = compare_runs.main([str(run_a), str(run_b), "--out", str(out_md)])
        check("compare_runs.main exits 0", rc == 0, f"rc={rc}")
        check("compare.md written", out_md.exists())

        text = out_md.read_text(encoding="utf-8")
        check("report has flips section", "## Flips" in text)
        check("regression s1 detected", "s1#t0" in text and "Regressions" in text)
        check("fix s2 detected", "s2#t0" in text and "Fixes" in text)
        check("no pack_hash warning when hashes match", "pack_hash differs" not in text)
        check("category delta table present", "## By-category delta" in text)
        check("cat1 delta negative (regression)", "-100.0pp" in text or "-100pp" in text)
        check("cat2 delta positive (fix)", "+100.0pp" in text or "+100pp" in text)
        check("pass rate table present", "## Overall pass rate" in text)
        check("latency table present", "## Latency" in text)
        check("cost table present", "## Cost" in text)

        # Also directly exercise the internal flips() detector.
        runs = [compare_runs.load_run(run_a), compare_runs.load_run(run_b)]
        fl = compare_runs.flips(runs)
        check("flips() returns one entry (2 runs)", len(fl) == 1, str(fl))
        reg_ids = {sc for _, sc, _, _ in fl[0]["regressions"]}
        fix_ids = {sc for _, sc, _, _ in fl[0]["fixes"]}
        check("flips() finds s1 regression", "s1" in reg_ids, str(fl))
        check("flips() finds s2 fix", "s2" in fix_ids, str(fl))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_compare_runs_mismatched_pack_hash_warns():
    tmp = Path(tempfile.mkdtemp(prefix="bench_test2_"))
    try:
        run_a = make_fake_run(tmp, "runA", "hash1", s1_pass=True, s2_pass=False)
        run_b = make_fake_run(tmp, "runB", "hash2-different", s1_pass=False, s2_pass=True)
        out_md = tmp / "compare.md"
        rc = compare_runs.main([str(run_a), str(run_b), "--out", str(out_md)])
        check("mismatched-hash compare exits 0", rc == 0, f"rc={rc}")
        text = out_md.read_text(encoding="utf-8")
        check("warns on pack_hash mismatch", "pack_hash differs" in text)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_compare_runs_stdout_print_survives_narrow_console_encoding():
    """compare_runs prints straight to stdout when --out is omitted. On
    Windows, sys.stdout.encoding defaults to the cp1252 code page even when
    redirected/piped (no PYTHONIOENCODING set) -- a non-cp1252-encodable
    character in the mismatched-pack_hash warning line crashed this path
    with UnicodeEncodeError (exit 1), violating the "works offline, exit 0"
    contract on exactly the mandated warning path. Run as a real subprocess
    with captured (piped) stdout and an env with no encoding overrides to
    faithfully reproduce that default."""
    tmp = Path(tempfile.mkdtemp(prefix="bench_test4_"))
    try:
        run_a = make_fake_run(tmp, "runA", "hash1", s1_pass=True, s2_pass=False)
        run_b = make_fake_run(tmp, "runB", "hash2-different", s1_pass=False, s2_pass=True)
        import os
        env = {k: v for k, v in os.environ.items()
               if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
        proc = subprocess.run(
            [sys.executable, str(HARNESS_DIR / "compare_runs.py"), str(run_a), str(run_b)],
            capture_output=True, text=True, timeout=30, env=env,
        )
        check("compare_runs stdout-print (mismatched hash) exits 0",
              proc.returncode == 0,
              f"rc={proc.returncode} stderr={proc.stderr[:400]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_compare_runs_missing_dir_errors():
    tmp = Path(tempfile.mkdtemp(prefix="bench_test3_"))
    try:
        rc = compare_runs.main([str(tmp / "does-not-exist")])
        check("missing run dir returns exit 1", rc == 1, f"rc={rc}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_bench_plan_offline():
    """bench.py --plan must run fully offline (no pi/node spawn, no network)
    and print the run matrix."""
    proc = subprocess.run(
        [sys.executable, str(HARNESS_DIR / "bench.py"), "--plan",
         "--models", "dummy:off", "--souls", "butter-nihilist"],
        cwd=str(HARNESS_DIR), capture_output=True, text=True, timeout=30,
    )
    check("bench.py --plan exits 0", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr[:400]}")
    check("plan output mentions PLAN", "PLAN" in proc.stdout, proc.stdout[:200])
    check("plan output mentions dummy:off", "dummy:off" in proc.stdout, proc.stdout[:200])


def test_bench_plan_with_only_and_repeat():
    proc = subprocess.run(
        [sys.executable, str(HARNESS_DIR / "bench.py"), "--plan",
         "--models", "dummy:off,dummy2:low", "--souls", "butter-nihilist,mist",
         "--only", "safety", "--repeat", "3"],
        cwd=str(HARNESS_DIR), capture_output=True, text=True, timeout=30,
    )
    check("bench.py --plan (multi config) exits 0", proc.returncode == 0,
          f"rc={proc.returncode} stderr={proc.stderr[:400]}")
    check("plan lists 4 configs (2 models x 2 souls)",
          proc.stdout.count("total_turns=") == 4, proc.stdout)
    check("repeat=3 reflected", "repeat=3" in proc.stdout, proc.stdout)


def test_pack_hash_stable_and_sensitive():
    import bench
    a = bench.pack_hash([{"id": "x", "turns": [{"say": "hi", "expect": {}}]}])
    b = bench.pack_hash([{"id": "x", "turns": [{"say": "hi", "expect": {}}]}])
    c = bench.pack_hash([{"id": "x", "turns": [{"say": "bye", "expect": {}}]}])
    check("pack_hash deterministic for identical structure", a == b)
    check("pack_hash changes when scenario content changes", a != c)


def test_summarize_config_shape():
    import bench
    rows = [
        _row("s1", 0, "cat1", "m", "off", "soul", True),
        _row("s1", 1, "cat1", "m", "off", "soul", False),
        _row("s2", 0, "cat2", "m", "off", "soul", True),
    ]
    s = bench.summarize_config(rows, "m", "off", "soul", 1)
    check("summarize_config n_turns", s["n_turns"] == 3, str(s["n_turns"]))
    check("summarize_config n_pass", s["n_pass"] == 2, str(s["n_pass"]))
    check("summarize_config by_category has cat1/cat2",
          set(s["by_category"]) == {"cat1", "cat2"}, str(s["by_category"]))
    check("summarize_config failures lists s1#t1",
          any(f["scenario"] == "s1" and f["turn"] == 1 for f in s["failures"]),
          str(s["failures"]))
    check("summarize_config has all required top-level keys",
          {"model", "thinking", "soul", "repeat", "n_turns", "n_pass", "pass_rate",
           "by_category", "persona", "latency", "tokens", "cost_usd", "failures"} <= set(s),
          str(sorted(s)))


def test_summarize_config_counts_harness_errors():
    """run_config/run_suite emit rows like {"scenario": id, "error": "..."}
    (no "checks" key) when e.g. new_session() times out. These must count as
    failed turns, not be silently dropped from n_turns/pass_rate."""
    import bench
    rows = [
        _row("s1", 0, "cat1", "m", "off", "soul", True),
        {"scenario": "s2", "error": "new_session timeout"},
    ]
    s = bench.summarize_config(rows, "m", "off", "soul", 1)
    check("harness-error row counted in n_turns", s["n_turns"] == 2, str(s["n_turns"]))
    check("harness-error row not counted as a pass", s["n_pass"] == 1, str(s["n_pass"]))
    check("harness-error row surfaced in failures",
          any(f["scenario"] == "s2" for f in s["failures"]), str(s["failures"]))


def test_pct_nearest_rank():
    import bench
    check("pct p50 of [1,2] is the lower value, not the max",
          bench.pct([1, 2], 0.5) == 1, str(bench.pct([1, 2], 0.5)))
    check("pct p90 of 10 samples is not always the max",
          bench.pct(list(range(1, 11)), 0.9) != 10,
          str(bench.pct(list(range(1, 11)), 0.9)))
    check("pct p100 (p=1.0) is the max",
          bench.pct([1, 2, 3], 1.0) == 3, str(bench.pct([1, 2, 3], 1.0)))
    check("pct of single sample is that sample",
          bench.pct([5.0], 0.5) == 5.0, str(bench.pct([5.0], 0.5)))
    check("pct of empty list is None", bench.pct([], 0.5) is None)


def test_report_accepts_long_convo_checks():
    """long_convo writes {want, ok}; report must not assume {name, pass}."""
    with tempfile.TemporaryDirectory(prefix="report-longconvo-") as tmp:
        root = Path(tmp)
        row = {
            "turn": 0, "say": "remember this", "reply": "missed it",
            "model": "dummy", "thinking": "off", "soul": "v2",
            "ttf_any_s": 0.2, "total_s": 0.4, "cost_usd": 0,
            "checks": [{"want": "blue cube", "ok": False}],
            "passed": False, "tools": [],
        }
        (root / "longconvo.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
        out = root / "report.md"
        proc = subprocess.run(
            [sys.executable, str(HARNESS_DIR / "report.py"), str(root), "-o", str(out)],
            capture_output=True, text=True, timeout=20,
        )
        check("report.py accepts longconvo {want,ok}", proc.returncode == 0,
              proc.stderr[-500:])
        check("longconvo failure name appears in report",
              out.exists() and "blue cube" in out.read_text(encoding="utf-8"))


def test_rpc_abort_is_correlated_and_drained():
    from pi_client import PiClient
    client = object.__new__(PiClient)
    client._q = queue.Queue()

    def fake_send(command):
        client._q.put({"type": "agent_end", "messages": []})
        client._q.put({"id": command["id"], "type": "response",
                       "command": "abort", "success": True})

    client._send = fake_send
    check("RPC abort waits for correlated acknowledgement",
          client._abort_and_drain(timeout=0.2))
    check("RPC abort drains old turn events", client._q.empty())


def test_flips_respects_repeat():
    """Two rows sharing (config, scenario, turn) but different repeat values
    must both be tracked, not silently overwritten by key collision."""
    import compare_runs
    run = {
        "run_id": "r", "manifest": {"pack_hash": "h"},
        "rows": [
            {"model": "m", "thinking": "off", "soul": "s", "scenario": "s1",
             "turn": 0, "repeat": 0, "passed": True, "checks": []},
            {"model": "m", "thinking": "off", "soul": "s", "scenario": "s1",
             "turn": 0, "repeat": 1, "passed": False, "checks": []},
        ],
    }
    m = compare_runs._turn_map(run)
    check("both repeats of the same (config,scenario,turn) are kept",
          len(m) == 2, str(m))


def main():
    print("test_bench.py — offline bench/compare_runs tests")
    test_compare_runs_flips_and_deltas()
    test_compare_runs_mismatched_pack_hash_warns()
    test_compare_runs_stdout_print_survives_narrow_console_encoding()
    test_compare_runs_missing_dir_errors()
    test_pack_hash_stable_and_sensitive()
    test_summarize_config_shape()
    test_summarize_config_counts_harness_errors()
    test_pct_nearest_rank()
    test_report_accepts_long_convo_checks()
    test_rpc_abort_is_correlated_and_drained()
    test_flips_respects_repeat()
    test_bench_plan_offline()
    test_bench_plan_with_only_and_repeat()

    if FAILS:
        print(f"\n{len(FAILS)} FAILURE(S): {', '.join(FAILS)}")
        return 1
    print("\nall tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
