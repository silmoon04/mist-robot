"""Experimental one-variable test of the planned horizontal recovery window.

Compare shift005 with velocity-matched recovery over .80--1.00 against the
same controller recovering over .84--.96. Original acceptance and all earlier
probe/trajectory files remain unchanged. This runner uses zero residuals and
never loads a policy or reads untouched final-policy receipts.
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

EXPECTED_PRIOR = {
    "dev_tracking_probe.py":"54915f674b74392cf24102b16c21562dbecff041167845a39644b171dbfbbc0e",
    "experimental_recovery.py":"de08ca7bb29aff0fb12d33d4c23b74f9d28f97726065415a6092d19a4b63b89c",
    "dev_recovery_probe.py":"39556a2584c7912354aba2e2693ecacca5adead101ef2b5c1bb2664510566907",
}
FILES = (Path(__file__),HERE/"experimental_clearance_recovery.py",*(HERE/name for name in EXPECTED_PRIOR))
VARIANTS = {"shift005_matched":{"shift_m":.005},"shift005_clearance":{"shift_m":.005}}


def experiment_hashes():
    return {str(path.relative_to(REPO)):hashlib.sha256(path.read_bytes()).hexdigest() for path in FILES}


def run_case(case):
    import locomotion.mist_env as env_module
    from experimental_recovery import VelocityMatchedCrawl
    from experimental_clearance_recovery import ClearanceWindowCrawl,RECOVERY_START,RECOVERY_END
    original_probe.VARIANTS = VARIANTS
    frozen_env_class = env_module.MistEnv
    gait_class = ClearanceWindowCrawl if case["variant"] == "shift005_clearance" else VelocityMatchedCrawl
    class ExperimentalEnv(frozen_env_class):
        def __init__(self,**kwargs):
            super().__init__(**kwargs)
            self.gait = gait_class(config=self.cfg)
    env_module.MistEnv = ExperimentalEnv
    try:
        result = original_probe.run_case(case)
        result["recovery_window_phase"] = [RECOVERY_START,RECOVERY_END] if case["variant"] == "shift005_clearance" else [.8,1.]
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
    for name,expected in EXPECTED_PRIOR.items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=expected:
            parser.error(f"Prior experiment bytes changed: {name}")
    args.variants = list(VARIANTS)
    cases = original_probe.make_cases(args)
    from locomotion.provenance import check_sources,source_hashes
    hashes,sources = experiment_hashes(),source_hashes()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as output:
        record = {"schema":1,"suite_role":"experimental_development_clearance_not_policy_selection",
                  "experiment_hashes":hashes,"source_hashes":sources,"ordered_cases":cases,"variants":VARIANTS,
                  "changed_variable":"horizontal recovery window .80--1.00 to .84--.96; endpoint velocity stays matched",
                  "prediction":"Less conflicting horizontal motion during loaded release/touchdown; smaller negative steady velocity bias. Faster airborne recovery may increase servo lag.",
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
                          "SCREEN_PASS" if result["tracking_screen_passed"] else "SCREEN_FAIL",result["steady"],flush=True)
                else:
                    print(case["variant"],case["command_name"],result["status"],result["execution_error"],flush=True)
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
