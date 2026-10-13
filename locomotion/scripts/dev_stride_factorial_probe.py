"""Bounded development 2x2: body shift .005/.003 and translation gain 1/1.15.

Uses the existing clearance recovery, zero residual actions and unchanged
acceptance. The scored command and its yaw component stay unchanged. Only six
cardinal/pure-yaw commands are admitted; mixed translation/yaw would need a
separate review of the existing combined-vector stride cap.
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
    "experimental_clearance_recovery.py":"c659fad8ce96064adfa3a6b79d1068a9a582d51646054f645bcac0ec6d79ad34",
    "dev_clearance_probe.py":"8b3053abcf8de175b4a1b5d95188820441e1c3977a7538a5fe21316347053a1f",
}
FILES = (Path(__file__),HERE/"experimental_stride_gain.py",*(HERE/name for name in EXPECTED_PRIOR))
COMMANDS = ("forward","backward","left","right","clockwise","counterclockwise")
FACTORS = {
    "shift005_gain100":{"shift_m":.005,"translational_stride_gain":1.},
    "shift003_gain100":{"shift_m":.003,"translational_stride_gain":1.},
    "shift005_gain115":{"shift_m":.005,"translational_stride_gain":1.15},
    "shift003_gain115":{"shift_m":.003,"translational_stride_gain":1.15},
}
VARIANTS = {name:{"shift_m":factor["shift_m"]} for name,factor in FACTORS.items()}


def experiment_hashes():
    return {str(path.relative_to(REPO)):hashlib.sha256(path.read_bytes()).hexdigest() for path in FILES}


def run_case(case):
    import locomotion.mist_env as env_module
    from experimental_stride_gain import TranslationGainClearanceCrawl
    original_probe.VARIANTS = VARIANTS
    frozen_env_class = env_module.MistEnv
    factor = FACTORS[case["variant"]]
    class ExperimentalEnv(frozen_env_class):
        def __init__(self,**kwargs):
            super().__init__(**kwargs)
            self.gait = TranslationGainClearanceCrawl(config=self.cfg,translational_stride_gain=factor["translational_stride_gain"])
    env_module.MistEnv = ExperimentalEnv
    try:
        result = original_probe.run_case(case)
        result["factor_levels"] = factor
        result["geometry_note"] = "vx/vy geometric stride gain only; requested/scored command and yaw unchanged. Load bias uses changed geometry."
        return result
    finally:
        env_module.MistEnv = frozen_env_class


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands",nargs="+",choices=COMMANDS,default=list(COMMANDS))
    parser.add_argument("--payloads",nargs="+",type=float,default=[0.,.155])
    parser.add_argument("--terrains",nargs="+",choices=("flat","low_friction","slope","rough"),default=["flat"])
    parser.add_argument("--steps",type=int,default=960)
    parser.add_argument("--workers",type=int,default=4)
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
    args.variants = list(FACTORS)
    cases = original_probe.make_cases(args)
    from locomotion.provenance import check_sources,source_hashes
    hashes,sources = experiment_hashes(),source_hashes()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf-8") as output:
        record = {"schema":1,"suite_role":"experimental_development_factorial_not_policy_selection",
                  "experiment_hashes":hashes,"source_hashes":sources,"ordered_cases":cases,"factor_levels":FACTORS,
                  "changed_variables":["body shift .005 vs .003 m","translational geometric stride gain 1.0 vs 1.15"],
                  "geometry_definition":"Only internal geometric vx/vy are scaled; internal yaw, requested/env/scored command and sensor/servo settings are unchanged. The existing support-load estimate uses modified geometric q. Selected commands do not activate the stride cap.",
                  "predictions":["Smaller shift reduces velocity ripple unless support contact loss creates instability.","Translation gain makes negative command-direction velocity bias smaller; pure-yaw gain pairs must be identical.","The 2x2 comparison separates main effects and their interaction; no candidate is a qualified policy."],
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
                    print(case["variant"],case["command_name"],case["payload"],
                          "PASS" if result["acceptance"]["passed"] else "FAIL",result["steady"],flush=True)
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
