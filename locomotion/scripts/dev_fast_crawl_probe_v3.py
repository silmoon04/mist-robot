"""Final bounded recovery-start comparison and brief selected-direction preview.

First run exactly two forward cases (payload0/.155) with wider recovery. Then
use --brief --controller wide or scaled for the selected profile's six-command
phone-payload check. These 480-step screens retain original acceptance.
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
import dev_tracking_probe as original_probe
import dev_fast_crawl_probe as fast_probe
import dev_fast_crawl_probe_v2 as previous_probe

EXPECTED_PRIOR = {**previous_probe.EXPECTED_PRIOR,
    "experimental_fast_crawl_v2.py": "d7914ea6b49edf8452eccdfc4c355ae8215cd68e4e4f5c7e6b2b4af0364dd483",
    "dev_fast_crawl_probe_v2.py": "98f138335d929d79c666f0974029ccb9b53515f8987f3db955ff6414d9d8a332",
    "test_fast_crawl_v2.py": "349df9ce4b250d8f3111af2d7a140c64ce5fff4011546268d55c2608f0e8d68e"}
FILES = (Path(__file__), HERE/"experimental_fast_crawl_v3.py", HERE/"test_fast_crawl_v3.py",
         *(HERE/name for name in EXPECTED_PRIOR))
BASE_PROFILE = {**fast_probe.PROFILES["fast120_v025_s180"], "shift_m": .001875}
PROFILES = {"wide82_fast120_v025_s180_shift1875": {**BASE_PROFILE, "recovery_start": .82},
            "scaled_fast120_v025_s180_shift1875": {**BASE_PROFILE, "recovery_start": .84}}
REFERENCE_PATH = REPO/"locomotion/runs/msi_20261012/dev_fast_shift_forward480_01.json"
REFERENCE_SHA256 = "451f45b9c9f01df046584bd8c0d1a864c4bce55c34633f7d83098e6aab3a8ee0"
COMMANDS = ("forward", "backward", "left", "right", "clockwise", "counterclockwise")


def check_prior():
    previous_probe.check_prior()
    for name, expected in EXPECTED_PRIOR.items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Previous experiment changed: {name}")
    if hashlib.sha256(REFERENCE_PATH.read_bytes()).hexdigest() != REFERENCE_SHA256:
        raise RuntimeError("Cadence-shift reference receipt changed")


def experiment_hashes():
    return {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in FILES}


def saved_forward_reference(case):
    if case["command_name"] != "forward":
        return None
    rows = json.loads(REFERENCE_PATH.read_text())["results"]
    row = next(x for x in rows if x["case"]["payload"] == case["payload"]
               and x["case"]["variant"] == "fast120_v025_s180_shift1875")
    for key in ("seed", "steps", "terrain", "randomize", "contact_stride", "save_trace"):
        if row["case"][key] != case[key]:
            raise RuntimeError(f"Saved reference mismatch: {key}")
    return {"receipt": str(REFERENCE_PATH.relative_to(REPO)), "receipt_sha256": REFERENCE_SHA256,
            "case": row["case"], "acceptance": row["acceptance"], "steady": row["steady"],
            "average_progress_speed_m_s": row["average_progress_speed_m_s"]}


def run_case(case):
    import experimental_fast_crawl as fast_module
    from experimental_fast_crawl_v3 import WideRecoveryFastCrawl
    profile = PROFILES[case["variant"]]
    original_class, original_profiles = fast_module.FastClearanceCrawl, fast_probe.PROFILES
    class SelectedController(WideRecoveryFastCrawl):
        def __init__(self, **kwargs):
            super().__init__(shift_m=profile["shift_m"], recovery_start=profile["recovery_start"], **kwargs)
    fast_module.FastClearanceCrawl = SelectedController
    fast_probe.PROFILES = PROFILES
    try:
        result = fast_probe.run_case(case)
        result["matched_saved_forward_reference"] = saved_forward_reference(case)
        result["recovery_window"] = [profile["recovery_start"], .96]
        result["preview_scope"] = "480-step development only. No qualification or physical bridge commands."
        return result
    finally:
        fast_module.FastClearanceCrawl = original_class
        fast_probe.PROFILES = original_profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief", action="store_true")
    parser.add_argument("--controller", choices=("wide", "scaled"), default="wide")
    parser.add_argument("--commands", nargs="+", choices=COMMANDS)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.commands = args.commands or (list(COMMANDS[1:]) if args.brief else ["forward"])
    if not args.brief and args.commands != ["forward"]:
        parser.error("The bounded two-payload comparison is forward only")
    args.payloads = [.155] if args.brief else [0., .155]
    args.terrains, args.repeats, args.randomize = ["flat"], 1, False
    args.steps, args.contact_stride, args.save_trace = 480, 5, True
    args.variants = [next(name for name in PROFILES if name.startswith("wide82_" if args.controller == "wide" else "scaled_"))]
    check_prior()
    cases = original_probe.make_cases(args)
    from locomotion.provenance import source_hashes, check_sources
    hashes, sources = experiment_hashes(), source_hashes()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        record = {"schema": 1, "suite_role": "brief_fast_preview_directions" if args.brief else "bounded_fast_recovery_start_comparison",
                  "experiment_hashes": hashes, "source_hashes": sources, "profile": PROFILES[args.variants[0]],
                  "ordered_cases": cases,
                  "changed_variable": "selected preview profile; no paired cause claim for other directions" if args.brief else "horizontal recovery start.84->.82 only; end.96 unchanged",
                  "original_acceptance_unchanged": True, "status": "running", "results": []}
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
                    print(row["case"]["command_name"], row["case"]["payload"],
                          "SCREEN_PASS" if row["tracking_screen_passed"] else "SCREEN_FAIL",
                          "speed", row["average_progress_speed_m_s"], row["acceptance"]["metrics"], flush=True)
                else:
                    print(row["case"], row["status"], row["execution_error"], flush=True)
        try:
            original_probe.collect_cases(cases, args.workers, publish, runner=run_case)
            check_prior()
            check_sources(sources)
            if experiment_hashes() != hashes:
                raise RuntimeError("Final bounded variant changed during execution")
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
