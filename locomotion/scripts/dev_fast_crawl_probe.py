"""Bounded faster-walking development screen, using independent DIRECT cases.

Default ten cases pair both payloads and match seeds across profiles. Requested
speed is also the scored speed. Original acceptance thresholds stay intact;
480-step results are preview screens, never walking qualification.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO), str(HERE)]
import dev_tracking_probe as original_probe
from dev_support_transfer_probe_v2 import EXPECTED_PRIOR as SUPPORT_PRIOR

EXPECTED_PRIOR = {**SUPPORT_PRIOR,
    "dev_support_transfer_probe_v2.py": "8e003141426cd1d9575d07899ebd67588aeee8f19a3e1ae9281bf6c013a17219",
    "test_support_transfer_v2.py": "3e96451f9dd0c5ffd108a70c58e0c4bce857012687d7c371ab8283a8335d47d1"}
FILES = (Path(__file__), HERE/"experimental_fast_crawl.py", HERE/"test_fast_crawl.py",
         *(HERE/name for name in EXPECTED_PRIOR))
COMMANDS = ("forward", "backward", "left", "right", "clockwise", "counterclockwise")
PROFILES = {
    "reference320_v010_s180": {"cycle_s": 3.2, "travel_speed_m_s": .01, "yaw_speed_rad_s": .04, "command_speed_rad_s": 1.8},
    "fast160_v020_s180": {"cycle_s": 1.6, "travel_speed_m_s": .02, "yaw_speed_rad_s": .08, "command_speed_rad_s": 1.8},
    "fast160_v020_s300": {"cycle_s": 1.6, "travel_speed_m_s": .02, "yaw_speed_rad_s": .08, "command_speed_rad_s": 3.0},
    "fast120_v025_s180": {"cycle_s": 1.2, "travel_speed_m_s": .025, "yaw_speed_rad_s": .10666666666666667, "command_speed_rad_s": 1.8},
    "fast120_v025_s300": {"cycle_s": 1.2, "travel_speed_m_s": .025, "yaw_speed_rad_s": .10666666666666667, "command_speed_rad_s": 3.0},
    "fast120_v030_s300": {"cycle_s": 1.2, "travel_speed_m_s": .03, "yaw_speed_rad_s": .10666666666666667, "command_speed_rad_s": 3.0},
}
DEFAULT_PROFILES = tuple(PROFILES)[:5]


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


def requested_command(name, profile):
    speed, yaw = profile["travel_speed_m_s"], profile["yaw_speed_rad_s"]
    return {"forward": [speed, 0., 0.], "backward": [-speed, 0., 0.],
            "left": [0., speed, 0.], "right": [0., -speed, 0.],
            "clockwise": [0., 0., -yaw], "counterclockwise": [0., 0., yaw]}[name]


def run_case(case):
    import numpy as np
    import locomotion.mist_env as env_module
    import locomotion.acceptance as acceptance
    from experimental_fast_crawl import FastClearanceCrawl, preview_config
    from locomotion.provenance import identity
    profile = PROFILES[case["variant"]]
    config = preview_config(profile["command_speed_rad_s"])
    command = requested_command(case["command_name"], profile)
    frozen_env_class = env_module.MistEnv
    original_command = acceptance.COMMANDS[case["command_name"]]
    original_variants = original_probe.VARIANTS
    original_probe.VARIANTS = {name: {} for name in PROFILES}
    acceptance.COMMANDS[case["command_name"]] = tuple(command)
    holder = {}

    class ExperimentalEnv(frozen_env_class):
        def __init__(self, **kwargs):
            kwargs["config"] = deepcopy(config)
            super().__init__(**kwargs)
            self.gait = FastClearanceCrawl(config=self.cfg, cycle_s=profile["cycle_s"])
            self._collect_motor = False
            self._inside_physics = False
            self._actual_speed = []
            self._limited = np.zeros(12)
            self._filtered_speed_peak = np.zeros(12)
            self._motor_ticks = 0
            holder["env"] = self

        def reset(self, **kwargs):
            result = super().reset(**kwargs)
            if self.phone_mass != float(case["payload"]):
                raise RuntimeError("Realized known payload differs from declared case")
            self._collect_motor = True
            return result

        def _joint_state(self):
            q, qdot = super()._joint_state()
            if self._collect_motor and self._inside_physics:
                self._actual_speed.append(np.abs(qdot).copy())
            return q, qdot

        def _physics(self, target):
            before = self.servos.target.copy() if self._collect_motor else None
            self._inside_physics = True
            try:
                super()._physics(target)
            finally:
                self._inside_physics = False
            if self._collect_motor:
                slew = self.servos.speed*self.servos.voltage/self.servos.nominal_voltage*self.dt
                # Inspect the same delayed/quantized target that advance used.
                self._limited += np.abs(self.servos.queue[0]-before) > slew+1e-12
                self._filtered_speed_peak = np.maximum(self._filtered_speed_peak, np.abs(self.servos.target-before)/self.dt)
                self._motor_ticks += 1

    env_module.MistEnv = ExperimentalEnv
    try:
        result = original_probe.run_case(case)
        env = holder["env"]
        actual = np.asarray(env._actual_speed)
        duration = result["acceptance"]["metrics"]["duration_s"]
        result["effective_profile"] = profile
        result["requested_command"] = command
        result["effective_config"] = config
        result["effective_config_sha256"] = identity(config)
        result["effective_geometric_stride_cap_ratios"] = env.gait.stride_cap_ratios(command)
        result["average_progress_speed_m_s"] = result["acceptance"]["metrics"]["progress_m"]/duration
        result["motor_diagnostics"] = {"sampling_hz": 1./env.dt, "physics_ticks": env._motor_ticks,
            "actual_joint_speed_peak_rad_s": actual.max(axis=0),
            "actual_joint_speed_p95_rad_s": np.percentile(actual, 95, axis=0),
            "actual_joint_speed_rms_rad_s": np.sqrt(np.mean(actual*actual, axis=0)),
            "filtered_target_speed_peak_rad_s": env._filtered_speed_peak,
            "target_slew_limit_usage_fraction": env._limited/max(1, env._motor_ticks),
            "note": "Actual qdot sampled before each physics tick; target limit usage compares delayed quantized desired target with prior filtered target. Diagnostic truth never feeds actor."}
        result["scope"] = "Simulation preview screen only; source torque/no-load/gains/latency/inertials/timestep/sensor and acceptance are unchanged. Effective runtime command slew is recorded separately."
        return result
    finally:
        env_module.MistEnv = frozen_env_class
        acceptance.COMMANDS[case["command_name"]] = original_command
        original_probe.VARIANTS = original_variants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", nargs="+", choices=PROFILES, default=list(DEFAULT_PROFILES))
    parser.add_argument("--commands", nargs="+", choices=COMMANDS, default=["forward"])
    parser.add_argument("--payloads", nargs="+", type=float, default=[0., .155])
    parser.add_argument("--steps", type=int, default=480)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--contact-stride", type=int, default=5)
    parser.add_argument("--save-trace", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.workers <= 3 or min(args.steps, args.contact_stride) < 1 or any(not 0 <= mass <= .4 for mass in args.payloads):
        parser.error("Use 1--3 workers, positive counts and payloads within[0,.4]")
    check_prior()
    args.terrains, args.repeats, args.randomize, args.variants = ["flat"], 1, False, args.profiles
    cases = original_probe.make_cases(args)
    for case in cases:
        case["requested_command"] = requested_command(case["command_name"], PROFILES[case["variant"]])
    from locomotion.provenance import source_hashes, check_sources
    hashes, sources = experiment_hashes(), source_hashes()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        record = {"schema": 1, "suite_role": "experimental_faster_walk_preview_screen",
                  "experiment_hashes": hashes, "source_hashes": sources, "profiles": {name: PROFILES[name] for name in args.profiles},
                  "ordered_cases": cases, "status": "running", "results": [],
                  "seed_note": "Shared development seed across profile variants for each command/payload; seed>=2**50. No final-policy seeds.",
                  "changed_parameters": ["cycle3.2/1.6/1.2s", "requested translation.01/.02/.025/.03m/s; scored exactly", "runtime target slew1.8/3.0rad/s"],
                  "fixed_contract": "clearance,5mmshift,gain1.15; torque.588Nm,no-load4.717rad/s,gains,latency,inertials,step,sensor and acceptance source unchanged"}
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
                    print(row["case"]["variant"], row["case"]["command_name"], row["case"]["payload"],
                          "SCREEN_PASS" if row["tracking_screen_passed"] else "SCREEN_FAIL",
                          "speed", row["average_progress_speed_m_s"], row["acceptance"]["metrics"], flush=True)
                else:
                    print(row["case"], row["status"], row["execution_error"], flush=True)
        try:
            original_probe.collect_cases(cases, args.workers, publish, runner=run_case)
            check_prior()
            check_sources(sources)
            if experiment_hashes() != hashes:
                raise RuntimeError("Fast experiment source changed during execution")
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
