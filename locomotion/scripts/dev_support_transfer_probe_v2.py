"""Version 2 paired support probe: known payload is available before env.reset.

Version 1 and its initialization-failure receipt remain preserved. This does not qualify a policy.

The first development pair is backward, .155 kg, 480 steps, saved contact and
planned-load traces. A separate static audit and review must precede physics.
Only the support-shift reference changes; scoring and sensor/motor contracts
remain inherited. The actor receives no simulator contact or velocity truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
import dev_tracking_probe as original_probe

EXPECTED_PRIOR = {
    "dev_tracking_probe.py": "54915f674b74392cf24102b16c21562dbecff041167845a39644b171dbfbbc0e",
    "experimental_recovery.py": "de08ca7bb29aff0fb12d33d4c23b74f9d28f97726065415a6092d19a4b63b89c",
    "dev_recovery_probe.py": "39556a2584c7912354aba2e2693ecacca5adead101ef2b5c1bb2664510566907",
    "experimental_clearance_recovery.py": "c659fad8ce96064adfa3a6b79d1068a9a582d51646054f645bcac0ec6d79ad34",
    "dev_clearance_probe.py": "8b3053abcf8de175b4a1b5d95188820441e1c3977a7538a5fe21316347053a1f",
    "experimental_stride_gain.py": "afff4bfd2ccaac61ad08542955d4d142102dab8ab8014c9b022e18a9b1f1a744",
    "dev_stride_factorial_probe.py": "aebf71749d5cbf02da6706da396fc7e071daaa585c7d5a1b3193cc1faf5de4a3",
}
COMMANDS = ("forward", "backward", "left", "right", "clockwise", "counterclockwise")
VARIANTS = {"clearance_shift005_gain115": {}, "planned_support_gain115": {}}
EXPECTED_PRIOR.update({
    name: expected for name, expected in {
        "dev_support_transfer_probe.py": "33be584d7c748d4abc4f0a5ccf6b193b3c58c33eda479c9008c729cdcdc08b03",
        "experimental_support_transfer.py": "07ddb9a22d81ddf2901625f9b7d78a5ca4383029d54591321235db94e3c7c09b",
        "audit_support_transfer.py": "ecd51a70df5a4e70c16b84d4e39b30505713c07807f0d4aafaef8a06060569c2",
        "test_support_transfer.py": "55aa22aa93b4907a988822618cd00fc2f02e131d93b6910e85146b02a2ab1cc6",
    }.items()
})
FILES = (Path(__file__), HERE/"test_support_transfer_v2.py", HERE/"experimental_support_transfer.py",
         HERE/"audit_support_transfer.py", HERE/"test_support_transfer.py",
         *(HERE/name for name in EXPECTED_PRIOR))


def experiment_hashes():
    return {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in FILES}


def check_prior():
    for name, expected in EXPECTED_PRIOR.items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Prior experiment bytes changed: {name}")
    frozen = json.loads((REPO/"locomotion/handoff/frozen_sources.json").read_text())
    for name, expected in frozen.items():
        if hashlib.sha256((REPO/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Frozen source bytes changed: {name}")


def run_case(case):
    import numpy as np
    import locomotion.mist_env as env_module
    from experimental_stride_gain import TranslationGainClearanceCrawl
    from experimental_support_transfer import (PlannedSupportTransferCrawl, PlanningError,
        load_diagnostics, inherited_shift_reference, attitude_correction)
    if case["randomize"]:
        raise PlanningError("Version 2 is a deterministic nominal pair; randomized cases are not admitted")
    original_probe.VARIANTS = VARIANTS
    frozen_env_class = env_module.MistEnv
    planned = case["variant"] == "planned_support_gain115"
    controller_class = PlannedSupportTransferCrawl if planned else TranslationGainClearanceCrawl
    traces = []
    holder = {}

    class DiagnosticController(controller_class):
        def position_targets(self, time_s, command, attitude=None, phone_mass_kg=.155):
            try:
                target = super().position_targets(time_s, command, attitude, phone_mass_kg)
                geometric = self.targets(time_s, command, attitude)
            except ValueError as error:
                raise PlanningError(f"Paired desired geometry failed: {error}") from error
            if case["save_trace"]:
                reference = self.reference(time_s, command) if planned else inherited_shift_reference(self, time_s)
                diagnostics = load_diagnostics(self, time_s, command, geometric, phone_mass_kg)
                correction = attitude_correction(attitude)
                # Undo only the original attitude compensation and common
                # body shift, for frame-explicit planned triangle telemetry.
                unshifted = (correction.T@diagnostics["geometric_body_feet_m"].T).T
                unshifted += np.r_[reference["shift_m"], 0.]
                row = {"command_time_s": time_s, "requested_command": np.asarray(command).copy(),
                       "effective_geometric_command": self.effective_geometric_command(command),
                       "attitude_input_rad": np.zeros(2) if attitude is None else np.asarray(attitude).copy(),
                       "commanded_phase": [(time_s/self.cycle_s-self.offset[leg]) % 1. for leg in self.nominal],
                       "unshifted_pre_attitude_feet_m": unshifted, "geometric_joint_target_rad": geometric,
                       "position_target_before_env_clip_rad": target,
                       "position_bias_rad": self.last_position_bias.copy(), **reference, **diagnostics}
                traces.append(row)
            return target

    class ExperimentalEnv(frozen_env_class):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            options = {"config": self.cfg}
            if planned:
                options["phone_mass_kg"] = case["payload"]
            else:
                options.update(shift_m=.005, translational_stride_gain=1.15)
            self.gait = DiagnosticController(**options)
            holder["gait"] = self.gait

        def reset(self, **kwargs):
            result = super().reset(**kwargs)
            if self.phone_mass != float(case["payload"]):
                raise PlanningError("Realized known payload differs from declared case payload")
            if planned and self.gait.phone_mass_kg != self.phone_mass:
                raise PlanningError("Support-plan payload differs from realized known payload")
            return result

    env_module.MistEnv = ExperimentalEnv
    try:
        result = original_probe.run_case(case)
        result["planned_support_trace"] = traces if case["save_trace"] else None
        result["support_reference"] = "periodic C2 nominal support-feasible spline" if planned else "inherited .005 m sin-squared shift"
        if planned:
            result["support_plan"] = holder["gait"].plan(result["initial_info"]["command"])
        result["geometry_note"] = "Only support reference changes. Requested/scored command stays original; geometric vx/vy gain 1.15, original yaw, clearance timing, centred-COM solver and sensor/motor settings are inherited. Nominal zero-attitude feasibility is not a dynamic guarantee."
        return result
    finally:
        env_module.MistEnv = frozen_env_class


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", nargs="+", choices=COMMANDS, default=["backward"])
    parser.add_argument("--payloads", nargs="+", type=float, default=[.155])
    parser.add_argument("--terrains", nargs="+", choices=("flat",), default=["flat"])
    parser.add_argument("--steps", type=int, default=480)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--contact-stride", type=int, default=5)
    parser.set_defaults(randomize=False)
    parser.add_argument("--save-trace", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if min(args.steps, args.workers, args.repeats, args.contact_stride) < 1 or any(not 0 <= mass <= .4 for mass in args.payloads):
        parser.error("Positive counts and payloads within [0,.4] are required")
    check_prior()
    args.variants = list(VARIANTS)
    cases = original_probe.make_cases(args)
    from locomotion.provenance import check_sources, source_hashes
    hashes, sources = experiment_hashes(), source_hashes()
    static_path = REPO/"locomotion/runs/msi_20261012/dev_support_static_01.json"
    static = json.loads(static_path.read_text())
    for name in ("experimental_support_transfer.py", "audit_support_transfer.py"):
        if static["experiment_hashes"]["locomotion/scripts/"+name] != EXPECTED_PRIOR[name]:
            raise RuntimeError("Static geometry evidence has different experiment bytes")
    if static["status"] != "complete" or len(static["results"]) != 12:
        raise RuntimeError("The completed twelve-case nominal static gate is required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        record = {"schema": 1, "suite_role": "experimental_development_support_transfer",
                  "experiment_hashes": hashes, "source_hashes": sources, "ordered_cases": cases,
                  "static_geometry_evidence": {"receipt": str(static_path.relative_to(REPO)),
                                               "sha256": hashlib.sha256(static_path.read_bytes()).hexdigest(),
                                               "controller_sha256": EXPECTED_PRIOR["experimental_support_transfer.py"],
                                               "audit_sha256": EXPECTED_PRIOR["audit_support_transfer.py"],
                                               "note": "Unchanged geometry from completed static audit; v2 repairs pre-reset payload construction and verifies realized known mass at reset."},
                  "changed_variable": "common body-shift reference only",
                  "solver_contract": {"dependency": "NumPy 2.2.6", "input": "requested command, planned phase/feet, nominal centred-COM mass and known payload only",
                                      "basis": "32-knot periodic cubic B-spline; C2 steady cycle",
                                      "constraints": "three planned stance loads >=.1 N during .80--1 swing; raw scheduled loads >=0 all phases; coefficients within +/-15 mm",
                                      "limitations": "Constraints are at zero attitude after startup. Existing half-angle attitude compensation and linear startup ramp remain unchanged; no true COM or dynamic feasibility claim."},
                  "predictions": ["Backward negative nominal stance loads disappear before clipping.",
                                  "Unexpected loaded-stance contact losses and velocity ripple decrease without higher slew/saturation demand.",
                                  "Forward may lose useful stabilizing motion; this is an outcome to test with the same reference definition."],
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
            for result in results:
                key = original_probe.stable_hash(result["case"])
                if key in printed:
                    continue
                printed.add(key)
                if result["status"] == "completed":
                    print(result["case"]["variant"], result["case"]["command_name"],
                          "SCREEN_PASS" if result["tracking_screen_passed"] else "SCREEN_FAIL", result["steady"], flush=True)
                else:
                    print(result["case"]["variant"], result["status"], result["execution_error"], flush=True)
        try:
            original_probe.collect_cases(cases, args.workers, publish, runner=run_case)
            check_prior()
            check_sources(sources)
            if experiment_hashes() != hashes:
                raise RuntimeError("Experimental source changed during execution")
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
