"""Eight forward cases testing preview speed limits with exact saved physics.

Requested speeds remain the scored speeds. All cases last 480 control steps
and use nominal motors, no randomization, flat ground and slew 1.8 rad/s.
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
import dev_fast_crawl_probe_v3 as previous_probe

EXPECTED_PRIOR = {**previous_probe.EXPECTED_PRIOR,
    "experimental_fast_crawl_v3.py": "629f93ba11ff85b34287f4fe670645442e982838a40652347762c4e9181d7fe2",
    "dev_fast_crawl_probe_v3.py": "546dc5eb8bc5ac273dfbd5e3275293ec9818fb1c2f273152a01065a5ac6a4ef4",
    "test_fast_crawl_v3.py": "5f425b9dbe6c497cfc5458dc68aca35db9ccd75d50ad4ecd72d1fba100c154d6"}
FILES = (Path(__file__), HERE/"experimental_fast_crawl_v4.py", HERE/"test_fast_crawl_v4.py",
         *(HERE/name for name in EXPECTED_PRIOR))
REFERENCE_PATH = REPO/"locomotion/runs/msi_20261012/dev_fast_wide_forward480_01.json"
REFERENCE_SHA256 = "27c6a8c3142625b0043ddc3dcc252c4477f72da1b45cd8b5a4fa40056a47001b"
PROFILE_PARAMETERS = ((1.2, .04), (1., .025), (1., .04), (.8, .025), (.8, .04), (.8, .06))
PROFILES = {f"ceiling_T{round(cycle*100):03d}_v{round(speed*1000):03d}": {
    "cycle_s": cycle, "travel_speed_m_s": speed, "yaw_speed_rad_s": .06,
    "command_speed_rad_s": 1.8, "shift_m": .005*cycle/3.2, "recovery_start": .82}
    for cycle, speed in PROFILE_PARAMETERS}


def check_prior():
    previous_probe.check_prior()
    for name, expected in EXPECTED_PRIOR.items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Previous experiment changed: {name}")
    if hashlib.sha256(REFERENCE_PATH.read_bytes()).hexdigest() != REFERENCE_SHA256:
        raise RuntimeError("Selected fast-preview reference receipt changed")


def experiment_hashes():
    return {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in FILES}


def reference_for_case(case):
    row = next(x for x in json.loads(REFERENCE_PATH.read_text())["results"]
               if x["case"]["payload"] == case["payload"])
    for key in ("seed", "steps", "terrain", "randomize", "contact_stride", "save_trace"):
        if row["case"][key] != case[key]:
            raise RuntimeError(f"Saved reference mismatch: {key}")
    return {"receipt": str(REFERENCE_PATH.relative_to(REPO)), "receipt_sha256": REFERENCE_SHA256,
            **{key: row[key] for key in ("case", "acceptance", "steady", "motor_diagnostics",
                                        "average_progress_speed_m_s", "telemetry_steady")}}


def make_cases():
    rows = json.loads(REFERENCE_PATH.read_text())["results"]
    result = []
    for payload in (.155, 0.):
        reference = next(row["case"] for row in rows if row["case"]["payload"] == payload)
        for name, profile in PROFILES.items():
            if payload == 0. and (profile["cycle_s"], profile["travel_speed_m_s"]) not in ((1., .04), (.8, .04)):
                continue
            result.append({**reference, "variant": name,
                           "requested_command": [profile["travel_speed_m_s"], 0., 0.]})
    return result


def run_case(case):
    import experimental_fast_crawl as fast_module
    from experimental_fast_crawl_v4 import SpeedCeilingCrawl
    profile = PROFILES[case["variant"]]
    original_class, original_profiles = fast_module.FastClearanceCrawl, fast_probe.PROFILES
    fast_module.FastClearanceCrawl = SpeedCeilingCrawl
    fast_probe.PROFILES = PROFILES
    try:
        result = fast_probe.run_case(case)
        result["matched_saved_forward_reference"] = reference_for_case(case)
        result["recovery_window"] = [.82, .96]
        result["uncapped_requested_translation_m_s"] = .035/(.8*profile["cycle_s"]*1.15)
        result["preview_scope"] = "480-step forward development only; no qualification or physical bridge commands."
        return result
    finally:
        fast_module.FastClearanceCrawl, fast_probe.PROFILES = original_class, original_profiles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check_prior()
    from locomotion.provenance import source_hashes, check_sources
    hashes, sources, cases = experiment_hashes(), source_hashes(), make_cases()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        record = {"schema": 1, "suite_role": "bounded_preview_speed_ceiling_forward_comparison",
                  "experiment_hashes": hashes, "source_hashes": sources, "profiles": PROFILES,
                  "ordered_cases": cases, "case_budget": 8, "steps_per_case": 480,
                  "original_acceptance_unchanged": True,
                  "fixed_contract": "35mmstride,lift12mm,gain1.15,recovery.82-.96,torque.588Nm,no-load4.717rad/s,slew1.8rad/s,gains,latency,inertials,timestep,sensors",
                  "reference_receipt": str(REFERENCE_PATH.relative_to(REPO)),
                  "reference_sha256": REFERENCE_SHA256, "status": "running", "results": []}
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
                raise RuntimeError("Speed-ceiling helper changed during execution")
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
