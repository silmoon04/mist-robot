"""Sequential, paired A/B text experiments; neither arm wins automatically."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import random
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import runner
from metrics import compare_runs
from review import build_review


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def durable_save(path, value):
    """Replace a checkpoint only after its complete JSON was written."""
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".pending")
    runner.save(temp, value)
    temp.replace(path)


def schedule_pairs(cases, repeats, seed):
    if repeats < 1:
        raise ValueError("Repeats must be positive")
    rng = random.Random(seed)
    pairs = [(case["id"], repeat) for case in cases for repeat in range(1, repeats + 1)]
    rng.shuffle(pairs)
    firsts = ["baseline", "candidate"] * (len(pairs) // 2)
    if len(pairs) % 2:
        firsts.append(rng.choice(["baseline", "candidate"]))
    rng.shuffle(firsts)
    return [{"block": index + 1, "case_id": cid, "repeat": repeat,
             "order": [first, "candidate" if first == "baseline" else "baseline"],
             "status": "pending", "samples": []}
            for index, ((cid, repeat), first) in enumerate(zip(pairs, firsts))]


def initialize_arm(args, arm, output, suite_bytes, suite_hash, cases):
    """Use runner's manifest schema and its exact production prompt adaptation."""
    persona_path = getattr(args, arm + "_persona").resolve()
    raw = persona_path.read_bytes()
    persona = raw.decode("utf-8").replace(
        "Your voice is being converted to the owner's MIST voice.",
        "Your replies are spoken using the owner's MIST voice through streaming text to speech.")
    provider = getattr(args, arm + '_provider', 'codex')
    reasoning = getattr(args, arm + '_reasoning', None) or args.reasoning
    config = {"model": getattr(args, arm + "_model"), "reasoning": reasoning, "provider": provider,
              "service_tier": args.service_tier if provider == 'codex' else 'provider_default', "max_output_tokens": args.max_output_tokens,
              "timeout_s": args.timeout, "concurrency": 1, "seed": args.seed,
              "persona_sha256": runner.sha(persona.encode()), "persona_raw_sha256": runner.sha(raw),
              "condition": "new_session_per_case_warm_within_case"}
    source_files = [runner.BRAIN / "duplex" / f for f in (
        "runtime.py", "persona.txt", "background.py", "expression_policy.py",
        "expression_requests.py", "memory_requests.py", "motion_requests.py", "phrasing.py", "face_map.json")]
    source_files += [runner.BRAIN / "harness" / f for f in (
        "codex_client.py", "eval_luna_conversations.py", "response_format.py")]
    source_files += list(HERE.glob("*.py"))
    hashes = {}
    output.mkdir()
    for source in source_files:
        relative = source.relative_to(runner.ROOT)
        data = source.read_bytes()
        hashes[relative.as_posix()] = runner.sha(data)
        target = output / "sources" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    rubric = HERE / "RUBRIC.md"
    run = {"manifest": {"schema_version": 1, "run_id": output.parent.name + "/" + arm,
           "suite_sha256": suite_hash, "adapter": "mist-bounded-text-v2", "created_utc": utc_now(),
           "config": config, "selected_case_ids": [c["id"] for c in cases], "repeats": args.repeats,
           "source_hashes": hashes, "rubric_sha256": runner.sha(rubric.read_bytes()) if rubric.exists() else None,
           "evidence_mode": "text_only", "human_quality": "unrated", "audio_quality": "unmeasured",
           "experiment_arm": arm, "persona_source_path": str(persona_path)}, "samples": []}
    (output / "cases.frozen.json").write_bytes(suite_bytes)
    (output / "persona.raw.txt").write_bytes(raw)
    (output / "persona.frozen.txt").write_text(persona, encoding="utf-8")
    if rubric.exists():
        (output / "RUBRIC.frozen.md").write_bytes(rubric.read_bytes())
    durable_save(output / "run.json", run)
    return run, config, persona


def run_experiment(args):
    suite, suite_hash = runner.checked_suite(args.suite)
    suite_bytes = args.suite.read_bytes()
    if runner.sha(suite_bytes) != suite_hash:
        raise ValueError("Suite changed while being read")
    cases = runner.select(suite, args.split, args.ids, args.limit)
    schedule = schedule_pairs(cases, args.repeats, args.seed)
    if args.timeout <= 0 or args.max_output_tokens < 1:
        raise ValueError("Timeout and output limit must be positive")
    for path in (args.baseline_persona, args.candidate_persona):
        path.read_text(encoding="utf-8")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    arms = {arm: initialize_arm(args, arm, output / arm, suite_bytes, suite_hash, cases)
            for arm in ("baseline", "candidate")}
    start = time.perf_counter()
    experiment = {"schema_version": 1, "experiment_id": output.name,
                  "started_utc": utc_now(), "status": "running", "seed": args.seed,
                  "concurrency": 1, "schedule": schedule, "subjective_winner": None,
                  "limits": ["Live text and bounded tools only; no audible latency or naturalness rating.",
                             "AB/BA order is balanced within one experiment; repeats are independent sessions.",
                             "Production preferences and actuator transports are not used.",
                             "Provider comparison includes model, transport, prompt wrappers and runtime overhead, not isolated model inference.",
                             "Same effective persona and application schema; Codex adds its native harness instructions. Completion-cap semantics and reasoning effort differ by provider."],
                  "arms": {arm: arm + "/run.json" for arm in arms}}
    lookup = {c["id"]: c for c in cases}
    durable_save(output / "run.json", experiment)
    try:
        for block in schedule:
            block.update(status="running", started_utc=utc_now(), started_ms=(time.perf_counter()-start)*1000)
            durable_save(output / "run.json", experiment)
            case = lookup[block["case_id"]]
            for arm in block["order"]:
                run, config, persona = arms[arm]
                sample_dir = output / arm / (case["id"] + "-r" + str(block["repeat"]))
                sample_dir.mkdir()
                record = {"arm": arm, "started_utc": utc_now(), "started_ms": (time.perf_counter()-start)*1000,
                          "status": "running", "sample_path": sample_dir.relative_to(output).as_posix()+"/sample.json"}
                block["samples"].append(record)
                durable_save(output / "run.json", experiment)
                if case["mode"] == "text":
                    try:
                        row = runner.luna_case(case, block["repeat"], sample_dir, config, persona)
                    except Exception as exc:
                        row = {"case_id": case["id"], "repeat": block["repeat"], "category": case["category"],
                               "split": case["split"], "status": "failed", "turns": [], "events": [],
                               "checks": [], "outcomes": {}, "errors": [type(exc).__name__ + ": " + str(exc)[:700]]}
                else:
                    row = {"case_id": case["id"], "repeat": block["repeat"], "category": case["category"],
                           "split": case["split"], "status": "unsupported", "turns": [], "events": [],
                           "checks": [], "outcomes": {}, "errors": ["Requires " + case["mode"] + " evidence; text cannot establish this behavior."]}
                record.update(status=row["status"], stopped_utc=utc_now(), stopped_ms=(time.perf_counter()-start)*1000)
                row["experiment_block"] = block["block"]
                row["experiment_position"] = len(block["samples"])
                run["samples"].append(row)
                durable_save(sample_dir / "sample.json", row)
                durable_save(output / arm / "run.json", run)
                durable_save(output / "run.json", experiment)
                print(f"{block['block']}/{len(schedule)} {arm} {case['id']} r{block['repeat']}: {row['status']}", flush=True)
            block.update(status="finished", stopped_utc=utc_now(), stopped_ms=(time.perf_counter()-start)*1000)
            durable_save(output / "run.json", experiment)
    except BaseException as exc:
        experiment.update(status="interrupted", error=type(exc).__name__, stopped_utc=utc_now())
        durable_save(output / "run.json", experiment)
        raise
    for arm, (run, _, _) in arms.items():
        runner.write_report(run, output / arm)
    baseline, candidate = arms["baseline"][0], arms["candidate"][0]
    durable_save(output / "comparison.json", compare_runs(baseline, candidate, seed=args.seed))
    counts = {arm: dict(Counter(s["status"] for s in run["samples"])) for arm, (run, _, _) in arms.items()}
    if all(s["status"] == "completed" for run, _, _ in arms.values() for s in run["samples"]):
        experiment["review"] = build_review(baseline, candidate, output / "review", seed=args.seed)
    else:
        experiment["review"] = {"status": "not_built", "reason": "All selected pairs must complete before a full blinded review; inspect failures and unsupported modes in both reports."}
    experiment.update(status="finished", stopped_utc=utc_now(), status_counts=counts,
                      elapsed_ms=(time.perf_counter()-start)*1000)
    durable_save(output / "run.json", experiment)
    return 0 if all(s["status"] in ("completed", "unsupported") and all(c.get("passed") is not False for c in s.get("checks", []))
                    for run, _, _ in arms.values() for s in run["samples"]) else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--suite", type=Path, default=HERE / "cases.json")
    p.add_argument("--baseline-persona", type=Path, default=runner.BRAIN / "duplex/persona.txt")
    p.add_argument("--candidate-persona", type=Path, required=True)
    p.add_argument("--baseline-model", default="gpt-6-luna")
    p.add_argument("--candidate-model", default="gpt-6-luna")
    p.add_argument("--baseline-provider", default="codex", choices=['codex', 'cerebras'])
    p.add_argument("--candidate-provider", default="codex", choices=['codex', 'cerebras'])
    p.add_argument("--split", default="dev", choices=["dev", "validation", "holdout", "all"])
    p.add_argument("--ids"); p.add_argument("--limit", type=int)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20260923)
    p.add_argument("--timeout", type=float, default=45)
    p.add_argument("--reasoning", choices=["low", "medium", "high"], default="low")
    p.add_argument("--baseline-reasoning", choices=["low", "medium", "high"], help="Override the shared effort for the baseline only")
    p.add_argument("--candidate-reasoning", choices=["low", "medium", "high"], help="Override the shared effort for the candidate only")
    p.add_argument("--service-tier", choices=["default", "priority"], default="default")
    p.add_argument("--max-output-tokens", type=int, default=180)
    return run_experiment(p.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
