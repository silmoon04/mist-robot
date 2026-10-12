"""Four-case cadence-scaled-shift screen against hash-bound saved fast cases.

Only shift amplitude changes to .001875m at T1.2. Both target-slew levels and
payloads match the previous development receipt. Scored speeds, sensors and
motors remain exact; this is not a physical robot or qualification run.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO), str(HERE)]
import dev_fast_crawl_probe as previous_probe
import dev_tracking_probe as original_probe

EXPECTED_PRIOR = {**previous_probe.EXPECTED_PRIOR,
    "experimental_fast_crawl.py": "e142f150760199299363115dc0deb0c6895afc2c895df4f05b6ff7ac9b8e15ff",
    "dev_fast_crawl_probe.py": "6ef63da68d8499f21b7afa2df0f947d4cc7ab6e11b4cdf0a836a1654cbaeda38",
    "test_fast_crawl.py": "aa6f96f33f1917214f315c2b9913ad1158d372b9e6dab4290c96ef708f1f8713"}
FILES = (Path(__file__), HERE/"experimental_fast_crawl_v2.py", HERE/"test_fast_crawl_v2.py",
         *(HERE/name for name in EXPECTED_PRIOR))
PROFILES = {name+"_shift1875": {**previous_probe.PROFILES[name], "shift_m": .005*1.2/3.2}
            for name in ("fast120_v025_s180", "fast120_v025_s300")}
REFERENCE_PATH = REPO/"locomotion/runs/msi_20261012/dev_fast_forward480_01.json"
REFERENCE_SHA256 = "e634ddf2c56645b8bca99d61ec1b4ecac3fb037ca749c0119c48a885d6759605"


def check_prior():
    previous_probe.check_prior()
    for name, expected in EXPECTED_PRIOR.items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Prior fast/source bytes changed: {name}")
    if hashlib.sha256(REFERENCE_PATH.read_bytes()).hexdigest() != REFERENCE_SHA256:
        raise RuntimeError("Saved fast-reference receipt changed")


def experiment_hashes():
    return {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in FILES}


def reference_for_case(case):
    receipt = json.loads(REFERENCE_PATH.read_text())
    previous_variant = case["variant"].removesuffix("_shift1875")
    matching = [row for row in receipt["results"] if row["case"]["variant"] == previous_variant
                and row["case"]["payload"] == case["payload"] and row["case"]["command_name"] == case["command_name"]]
    if len(matching) != 1:
        raise RuntimeError("Exactly one saved matched fast reference is required")
    reference = matching[0]
    for key in ("seed", "steps", "terrain", "randomize", "contact_stride", "save_trace"):
        if case[key] != reference["case"][key]:
            raise RuntimeError(f"Saved reference case mismatch: {key}")
    return {"receipt": str(REFERENCE_PATH.relative_to(REPO)), "receipt_sha256": REFERENCE_SHA256,
            "case": reference["case"], "acceptance": reference["acceptance"], "steady": reference["steady"],
            "average_progress_speed_m_s": reference["average_progress_speed_m_s"],
            "motor_diagnostics": reference["motor_diagnostics"]}


def run_case(case):
    import experimental_fast_crawl as fast_module
    from experimental_fast_crawl_v2 import CadenceShiftFastCrawl
    reference = reference_for_case(case)
    original_class = fast_module.FastClearanceCrawl
    original_profiles = previous_probe.PROFILES
    # The previous runner still owns scoring, DIRECT construction and motor
    # telemetry. Its process-local controller import receives this subclass.
    fast_module.FastClearanceCrawl = CadenceShiftFastCrawl
    previous_probe.PROFILES = PROFILES
    try:
        result = previous_probe.run_case(case)
        result["matched_saved_reference"] = reference
        result["changed_parameter"] = "shift_m .005 -> .001875; cadence-scaled amplitude only"
        return result
    finally:
        fast_module.FastClearanceCrawl = original_class
        previous_probe.PROFILES = original_profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", nargs="+", choices=PROFILES, default=list(PROFILES))
    parser.add_argument("--payloads", nargs="+", type=float, choices=(0., .155), default=[0., .155])
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.commands, args.terrains, args.repeats, args.randomize = ["forward"], ["flat"], 1, False
    args.steps, args.contact_stride, args.save_trace, args.variants = 480, 5, True, args.profiles
    check_prior()
    cases = original_probe.make_cases(args)
    references = [reference_for_case(case) for case in cases]
    from locomotion.provenance import source_hashes, check_sources
    hashes, sources = experiment_hashes(), source_hashes()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        record = {"schema": 1, "suite_role": "experimental_cadence_shift_preview_screen",
                  "experiment_hashes": hashes, "source_hashes": sources, "profiles": {name: PROFILES[name] for name in args.profiles},
                  "ordered_cases": cases, "saved_matched_references": references,
                  "changed_variable": "body shift amplitude .005 -> .001875m only; sameT1.2 requested.025m/s gain1.15 clearance and motor levels",
                  "predictions": ["Shift velocity ripple decreases at unchanged cadence.",
                                  "Forward support stays adequate; this does not predict backward/lateral feasibility.",
                                  "If progress remains lagged, faster clearance recovery is a separate later cause."],
                  "status": "running", "results": []}
        def save():
            output.seek(0)
            output.write(json.dumps(record, indent=2, allow_nan=False, default=original_probe.json_scalar)+"\n")
            output.truncate()
            output.flush()
        save()
        printed = set()
        def publish(results):
            record["results"] = results
            save()
            for row in results:
                key = original_probe.stable_hash(row["case"])
                if key in printed:
                    continue
                printed.add(key)
                if row["status"] == "completed":
                    print(row["case"]["variant"], row["case"]["payload"],
                          "SCREEN_PASS" if row["tracking_screen_passed"] else "SCREEN_FAIL",
                          "speed", row["average_progress_speed_m_s"], row["acceptance"]["metrics"], flush=True)
                else:
                    print(row["case"], row["status"], row["execution_error"], flush=True)
        try:
            original_probe.collect_cases(cases, args.workers, publish, runner=run_case)
            check_prior()
            check_sources(sources)
            if experiment_hashes() != hashes:
                raise RuntimeError("Cadence-shift source changed during execution")
            record["status"] = "failed" if any("execution_error" in row for row in record["results"]) else "complete"
            save()
        except BaseException as error:
            record["status"], record["error"] = "interrupted_or_failed", f"{type(error).__name__}: {error}"
            save()
            raise
    if record["status"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
