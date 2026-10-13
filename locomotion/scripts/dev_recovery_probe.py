"""Experimental paired recovery test; keeps the original tracking probe unchanged.

Compare shift005 legacy with shift005 plus Hermite horizontal recovery only.
This wrapper uses zero actions and does not load checkpoints or inspect final
policy receipts. Original acceptance thresholds are inherited unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0,str(REPO))
sys.path.insert(0,str(HERE))
import dev_tracking_probe as original_probe

EXPECTED_ORIGINAL_HASH = "54915f674b74392cf24102b16c21562dbecff041167845a39644b171dbfbbc0e"
FILES = (Path(__file__),HERE/"experimental_recovery.py",HERE/"dev_tracking_probe.py")
VARIANTS = {"shift005": {"shift_m":.005}, "shift005_matched": {"shift_m":.005}}


def experiment_hashes():
    return {str(path.relative_to(REPO)):hashlib.sha256(path.read_bytes()).hexdigest() for path in FILES}


def run_case(case):
    import locomotion.mist_env as env_module
    from experimental_recovery import VelocityMatchedCrawl
    original_probe.VARIANTS = VARIANTS
    frozen_env_class = env_module.MistEnv
    class ExperimentalEnv(frozen_env_class):
        def __init__(self,**kwargs):
            super().__init__(**kwargs)
            self.gait = VelocityMatchedCrawl(config=self.cfg)
    if case["variant"] == "shift005_matched":
        # This process-local binding leaves every source file unchanged.
        env_module.MistEnv = ExperimentalEnv
    try:
        result = original_probe.run_case(case)
        result["experimental_recovery"] = "hermite_endpoint_velocity" if case["variant"] == "shift005_matched" else "legacy_smoothstep"
        return result
    finally:
        env_module.MistEnv = frozen_env_class


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands",nargs="+",choices=original_probe.COMMAND_NAMES,default=["forward"])
    parser.add_argument("--payloads",nargs="+",type=float,default=[.155])
    parser.add_argument("--terrains",nargs="+",choices=("flat","low_friction","slope","rough"),default=["flat"])
    parser.add_argument("--steps",type=int,default=480)
    parser.add_argument("--workers",type=int,default=2)
    parser.add_argument("--repeats",type=int,default=1)
    parser.add_argument("--contact-stride",type=int,default=5)
    parser.add_argument("--randomize",action="store_true")
    parser.add_argument("--save-trace",action="store_true")
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    if min(args.steps,args.workers,args.repeats,args.contact_stride)<1 or any(not 0<=mass<=.4 for mass in args.payloads):
        parser.error("Positive counts and payloads within [0,.4] are required")
    if hashlib.sha256((HERE/"dev_tracking_probe.py").read_bytes()).hexdigest() != EXPECTED_ORIGINAL_HASH:
        parser.error("Original probe bytes changed; preserve the development receipt contract")
    args.variants = list(VARIANTS)
    cases = original_probe.make_cases(args)
    from locomotion.provenance import check_sources,source_hashes
    hashes,sources = experiment_hashes(),source_hashes()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as output:
        record = {"schema":1,"suite_role":"experimental_development_recovery_not_policy_selection",
                  "experiment_hashes":hashes,"source_hashes":sources,"ordered_cases":cases,
                  "variants":VARIANTS,"changed_variable":"horizontal swing interpolation only; endpoint velocity matches stance",
                  "status":"running","results":[]}
        def save():
            output.seek(0)
            output.write(json.dumps(record,indent=2,allow_nan=False,default=original_probe.json_scalar)+"\n")
            output.truncate()
            output.flush()
        save()
        printed = set()
        def publish(results):
            record["results"] = results
            save()
            for result in results:
                case = result["case"]
                case_key = original_probe.stable_hash(case)
                if case_key in printed:
                    continue
                printed.add(case_key)
                if result["status"] == "completed":
                    print(case["variant"],case["command_name"],
                          "SCREEN_PASS" if result["tracking_screen_passed"] else "SCREEN_FAIL",
                          result["steady"],flush=True)
                else:
                    print(case["variant"],case["command_name"],result["status"],
                          result["execution_error"],flush=True)
        try:
            original_probe.collect_cases(cases,args.workers,publish,runner=run_case)
            check_sources(sources)
            if experiment_hashes()!=hashes:
                raise RuntimeError("Experimental source changed during execution")
            record["status"] = "failed" if any("execution_error" in row for row in record["results"]) else "complete"
            save()
        except BaseException as error:
            record["status"],record["error"] = "interrupted_or_failed",f"{type(error).__name__}: {error}"
            save()
            raise
    if record["status"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
