"""Paired development probes for crawl tracking, contacts and servo limits.

This script changes only per-instance development settings. It does not load
policies, edit frozen files, or read final policy receipts. Contact telemetry
is diagnostic ground truth and is never fed into the controller.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
SEED_BASE = 1 << 50
COMMAND_NAMES = ("forward", "backward", "left", "right", "clockwise", "counterclockwise", "combined", "stop", "transient")
VARIANTS = {
    "nominal": {},
    "shift010": {"shift_m": .010},
    "shift005": {"shift_m": .005},
    "shift000": {"shift_m": 0.},
    "cycle256": {"cycle_s": 2.56},
    "cycle400": {"cycle_s": 4.0},
    "friction160": {"scenario": {"friction": 1.6}},
    "delay000": {"scenario": {"motor_delay_s": 0.}},
    "cap0981": {"torque_cap": .981},
}


def stable_hash(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode()).hexdigest()


def json_scalar(value):
    """Keep NumPy booleans and scalars from the original scorer serializable."""
    import numpy as np
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def make_cases(args):
    cases = []
    for terrain in args.terrains:
        for payload in args.payloads:
            for command in args.commands:
                for repeat in range(args.repeats):
                    case = {"terrain": terrain, "payload": payload, "command_name": command,
                            "repeat": repeat, "randomize": args.randomize}
                    # All variants share the same case seed. Existing sensitivity
                    # seeds are <2**33 and final-matrix seeds are <2**49.
                    seed = SEED_BASE + int(stable_hash(case)[:12], 16)
                    for variant in args.variants:
                        cases.append({**case, "variant": variant, "seed": seed,
                                      "steps": args.steps, "contact_stride": args.contact_stride,
                                      "save_trace": args.save_trace})
    return cases


class Telemetry:
    """Sample contacts at 200 Hz by default; count saturation at physics rate."""

    def __init__(self, env, stride):
        import numpy as np
        from locomotion.model import LEGS
        self.env, self.stride, self.ticks = env, stride, 0
        self.physics_start_s = env.physics_time_s
        self.legs = LEGS
        self.by_link = {env.links[f"{leg}_toe"]: i for i, leg in enumerate(LEGS)}
        self.saturated = np.zeros(12)
        self.samples = []
        self.original_physics = env._physics
        env._physics = self.advance

    def advance(self, target):
        import numpy as np
        import pybullet as p
        env = self.env
        self.original_physics(target)
        self.ticks += 1
        self.saturated += env.servos.saturation
        if self.ticks % self.stride:
            return
        q, qdot = env._joint_state()
        forces = np.zeros(4)
        weighted_speed = np.zeros(4)
        weighted_tangent = np.zeros((4,3))
        _, rotation, _ = env._orientation()
        for contact in env._call(p.getContactPoints, bodyA=env.robot, bodyB=env.floor):
            index = self.by_link.get(contact[3])
            if index is None or contact[9] <= .1:
                continue
            state = env._call(p.getLinkState, env.robot, contact[3], computeLinkVelocity=1)
            point_velocity = np.asarray(state[6]) + np.cross(state[7], np.asarray(contact[5])-state[0])
            normal = np.asarray(contact[7])
            tangent = point_velocity - normal * np.dot(point_velocity, normal)
            forces[index] += contact[9]
            weighted_speed[index] += contact[9] * np.linalg.norm(tangent)
            weighted_tangent[index] += contact[9] * (rotation.T @ tangent)
        body_tangent = weighted_tangent/np.maximum(forces[:,None],1e-12)
        command_vectors = np.asarray([np.r_[env.command[:2],0.] + env.command[2]*np.cross([0.,0.,1.],env.gait.nominal[leg]) for leg in self.legs])
        command_units = command_vectors/np.maximum(np.linalg.norm(command_vectors,axis=1)[:,None],1e-12)
        phase_time = env.step_count * env.substeps * env.dt
        phases = np.asarray([(phase_time/env.gait.cycle_s-env.gait.offset[leg]) % 1. for leg in self.legs])
        self.samples.append({"time_s": env.physics_time_s-self.physics_start_s,
                             "command_time_s": phase_time, "commanded_phase": phases,
                             "normal_force_n": forces,
                             "slip_m_s": weighted_speed/np.maximum(forces, 1e-12),
                             "body_contact_tangent_m_s": body_tangent,
                             "slip_along_command_m_s": np.sum(body_tangent*command_units,axis=1),
                             "joint_error_rad": np.abs(q-target),
                             "servo_target_lag_rad": np.abs(env.servos.target-target),
                             "joint_speed_rad_s": np.abs(qdot),
                             "saturation": env.servos.saturation.copy()})

    def summary(self, start_time, end_time=None):
        import numpy as np
        samples = [row for row in self.samples if row["time_s"] > start_time+1e-9 and (end_time is None or row["time_s"] <= end_time+1e-9)]
        if not samples:
            return {"sample_count": 0}
        arrays = {key: np.asarray([row[key] for row in samples]) for key in samples[0] if key not in ("time_s", "command_time_s")}
        loaded = arrays["normal_force_n"] > .1
        phase = arrays["commanded_phase"]
        per_leg = {}
        for index, leg in enumerate(self.legs):
            bins = []
            for lo, hi in zip((0., .73, .76, .80, .82, .97), (.73, .76, .80, .82, .97, 1.)):
                mask = (phase[:, index] >= lo) & (phase[:, index] < hi)
                contact_mask = mask & loaded[:, index]
                bins.append({"phase": [lo, hi], "sample_count": int(mask.sum()),
                             "loaded_fraction": float(loaded[mask, index].mean()) if mask.any() else None,
                             "mean_normal_force_n": float(arrays["normal_force_n"][mask, index].mean()) if mask.any() else None,
                             "mean_contact_slip_m_s": float(arrays["slip_m_s"][contact_mask, index].mean()) if contact_mask.any() else None,
                             "mean_slip_along_command_m_s": float(arrays["slip_along_command_m_s"][contact_mask,index].mean()) if contact_mask.any() else None,
                             "mean_body_contact_tangent_m_s": arrays["body_contact_tangent_m_s"][contact_mask,index].mean(axis=0).tolist() if contact_mask.any() else None})
            selected = arrays["slip_m_s"][loaded[:, index], index]
            per_leg[leg] = {"phase_bins": bins, "loaded_fraction": float(loaded[:, index].mean()),
                            "mean_contact_slip_m_s": float(selected.mean()) if len(selected) else None,
                            "p95_contact_slip_m_s": float(np.percentile(selected, 95)) if len(selected) else None}
        return {"sample_count": len(samples), "start_time_s": start_time, "end_time_s": end_time,
                "contact_sampling_hz": 1/(self.stride*self.env.dt),
                "phase_note": "Phase bins use the held command phase; contact sample times use actual physics time since reset settling.",
                "saturation_by_joint_all_physics": (self.saturated/max(1, self.ticks)).tolist(),
                "mean_joint_error_rad": arrays["joint_error_rad"].mean(axis=0).tolist(),
                "p95_joint_error_rad": np.percentile(arrays["joint_error_rad"],95,axis=0).tolist(),
                "p95_servo_target_lag_rad": np.percentile(arrays["servo_target_lag_rad"],95,axis=0).tolist(),
                "p95_joint_speed_rad_s": np.percentile(arrays["joint_speed_rad_s"],95,axis=0).tolist(),
                "per_leg": per_leg}


def run_case(case):
    import numpy as np
    from locomotion.acceptance import COMMANDS, command_at, score
    from locomotion.mist_env import MistEnv
    from locomotion.provenance import check_sources, source_hashes
    sources = source_hashes()
    override = deepcopy(VARIANTS[case["variant"]])
    gait_settings = {key: override.pop(key) for key in ("shift_m", "cycle_s") if key in override}
    env = MistEnv(command=COMMANDS[case["command_name"]], terrain=case["terrain"], payload=case["payload"],
                  randomize=case["randomize"], pushes=False, sensor_mode="mpu6050", max_steps=case["steps"], **override)
    started = time.perf_counter()
    try:
        for key, value in gait_settings.items():
            setattr(env.gait, key, value)
        _, initial = env.reset(seed=case["seed"])
        telemetry = Telemetry(env, case["contact_stride"])
        rows, trace = [], []
        for step in range(case["steps"]):
            env.command = np.asarray(command_at(case["command_name"], COMMANDS[case["command_name"]], step, case["steps"]))
            _, _, terminated, truncated, info = env.step(np.zeros(12))
            rows.append(info)
            if case["save_trace"]:
                trace_row = {key: info[key] for key in ("time_s", "position", "rpy", "body_velocity", "body_angular_velocity", "tracking_error_rad", "torque_saturation_fraction", "command")}
                trace_row["contact_sample"] = telemetry.samples[-1] if telemetry.samples else None
                from locomotion.gait import rz
                from locomotion.kinematics import forward
                from locomotion.model import LEGS, MOUNTS
                q, _ = env._joint_state()
                def feet(angles):
                    return [(np.asarray(MOUNTS[leg]["xyz"])+rz(MOUNTS[leg]["yaw"])@forward(angles[3*i:3*i+3])).tolist() for i,leg in enumerate(LEGS)]
                trace_row["actual_body_feet_m"] = feet(q)
                trace_row["target_body_feet_m"] = feet(env.last_target)
                trace_row["geometric_body_feet_after_final_clip_m"] = feet(env.last_target-env.gait.last_position_bias)
                trace_row["position_bias_rad"] = env.gait.last_position_bias.tolist()
                trace.append(trace_row)
            if terminated or truncated:
                break
        result = score(initial, rows, COMMANDS[case["command_name"]], case["steps"])
        steady_start = math.ceil((1.5+env.gait.cycle_s)/env.gait.cycle_s)*env.gait.cycle_s
        steady_end = math.floor(rows[-1]["time_s"]/env.gait.cycle_s+1e-9)*env.gait.cycle_s
        steady = [row for row in rows if row["time_s"] > steady_start+1e-9 and row["time_s"] <= steady_end+1e-9]
        velocity = np.asarray([row["body_velocity"][:2] for row in steady])
        command = np.asarray([row["command"][:2] for row in steady])
        omega = np.asarray([row["body_angular_velocity"][2] for row in steady])
        yaw_command = np.asarray([row["command"][2] for row in steady])
        steady_metrics = {"sample_count": len(steady), "start_time_s": steady_start, "end_time_s": steady_end,
                          "whole_cycles": max(0,round((steady_end-steady_start)/env.gait.cycle_s))}
        if steady:
            error = velocity-command
            bias = error.mean(axis=0)
            yaw_error = omega-yaw_command
            steady_metrics.update({"mean_velocity_bias_m_s": bias.tolist(),
                                   "velocity_error_ripple_rms_m_s": float(np.sqrt(np.mean(np.sum((error-bias)**2, axis=1)))),
                                   "body_velocity_rmse_m_s": float(np.sqrt(np.mean(np.sum(error**2, axis=1)))),
                                   "mean_yaw_rate_bias_rad_s": float(yaw_error.mean()),
                                   "yaw_rate_error_ripple_rms_rad_s": float(yaw_error.std())})
        speed_ratios = {}
        for leg, nominal in env.gait.nominal.items():
            foot_velocity = np.r_[env.command[:2],0.] + env.command[2]*np.cross([0.,0.,1.],nominal)
            stride = np.linalg.norm(foot_velocity[:2])*env.gait.cycle_s*.8
            speed_ratios[leg] = min(1., .035/stride) if stride else 1.
        symptom_keys = ("complete", "finite", "no_falls", "no_sensor_fault", "no_body_ground_contact", "no_nonfoot_ground_contact", "progress", "path", "velocity", "yaw_rate", "yaw", "tilt", "tracking", "saturation")
        check_sources(sources)
        return {"case": case, "acceptance": result,
                "tracking_screen_passed": all(result["checks"][key] for key in symptom_keys),
                "screen_note": "The screen excludes only duration; full qualification still requires all original checks.",
                "steady": steady_metrics, "telemetry_all": telemetry.summary(0.),
                "telemetry_steady": telemetry.summary(steady_start,steady_end),
                "gait": {"cycle_s": env.gait.cycle_s, "shift_m": env.gait.shift_m, "lift_m": env.gait.lift_m,
                         "stride_cap_speed_ratio_at_last_command": speed_ratios},
                "initial_info": initial, "ik_rejections": rows[-1]["ik_rejections"],
                "trace": trace if case["save_trace"] else None, "wall_s": time.perf_counter()-started}
    finally:
        env.close()


def collect_cases(cases, workers, publish, runner=run_case):
    """Persist individual outcomes in declared order, including worker errors."""
    outcomes, futures = {}, {}
    pool = ProcessPoolExecutor(max_workers=workers)
    interrupted = False

    def collect(future, index):
        try:
            outcomes[index] = {**future.result(), "status": "completed"}
        except Exception as error:
            outcomes[index] = {"case": cases[index], "status": "execution_error",
                               "execution_error": f"{type(error).__name__}: {error}"}

    def save():
        publish([outcomes[index] for index in sorted(outcomes)])

    try:
        for index, case in enumerate(cases):
            futures[pool.submit(runner, case)] = index
        for future in as_completed(futures):
            collect(future, futures[future])
            save()
    except BaseException:
        interrupted = True
        for future, index in futures.items():
            if index in outcomes:
                continue
            if future.done() and not future.cancelled():
                collect(future, index)
            else:
                cancelled = future.cancel()
                outcomes[index] = {"case": cases[index],
                                   "status": "cancelled" if cancelled else "uncollected",
                                   "execution_error": "Collection interrupted; no result recorded."}
        for index, case in enumerate(cases):
            if index not in outcomes:
                outcomes[index] = {"case": case, "status": "not_submitted",
                                   "execution_error": "Submission interrupted; case was not started."}
        save()
        raise
    finally:
        # Already-running workers may finish after interruption. Their outcome
        # remains explicitly uncollected; queued work is cancelled where possible.
        pool.shutdown(wait=not interrupted, cancel_futures=interrupted)
    return [outcomes[index] for index in range(len(cases))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variants", nargs="+", choices=tuple(VARIANTS), default=["nominal", "shift010"])
    parser.add_argument("--commands", nargs="+", choices=COMMAND_NAMES, default=["forward", "clockwise"])
    parser.add_argument("--payloads", nargs="+", type=float, default=[.155])
    parser.add_argument("--terrains", nargs="+", choices=("flat", "low_friction", "slope", "rough"), default=["flat"])
    parser.add_argument("--steps", type=int, default=960)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--contact-stride", type=int, default=5)
    parser.add_argument("--randomize", action="store_true")
    parser.add_argument("--save-trace", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--require-tracking", action="store_true", help="Exit 1 when the development tracking screen fails.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if min(args.steps,args.repeats,args.workers,args.contact_stride) < 1 or any(not 0<=mass<=.4 for mass in args.payloads):
        parser.error("Positive counts and payloads within [0,.4] are required")
    cases = make_cases(args)
    if args.plan:
        print(json.dumps({"seed_ownership": "development seeds >=2**50; paired across variants", "cases": cases},indent=2))
        return
    if args.output is None:
        parser.error("--output is required for execution")
    # Preserve every previous result and reserve the path before starting work.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        from locomotion.provenance import check_sources, source_hashes
        sources = source_hashes()
        record = {"schema": 1, "suite_role": "development_tracking_not_final_selection",
                  "source_hashes": sources, "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "seed_base": SEED_BASE, "ordered_cases": cases, "variants": VARIANTS,
                  "contact_note": "Loaded contact speed is sampled ground truth; it is never controller input. Impulses faster than the sample interval may be missed.",
                  "cap_variant_note": "cap0981 raises only the simulation torque cap to the inventory rated value. It does not establish a measured continuous hardware limit.",
                  "status": "running", "results": []}
        output.write(json.dumps(record, indent=2, allow_nan=False, default=json_scalar)+"\n")
        output.flush()
        def save():
            output.seek(0)
            output.write(json.dumps(record, indent=2, allow_nan=False, default=json_scalar)+"\n")
            output.truncate()
            output.flush()
        printed = set()
        def publish(results):
            record["results"] = results
            save()
            for result in results:
                case = result["case"]
                case_key = stable_hash(case)
                if case_key in printed:
                    continue
                printed.add(case_key)
                if result["status"] == "completed":
                    metrics = result["acceptance"]["metrics"]
                    print(case["variant"], case["command_name"], case["payload"],
                          "SCREEN_PASS" if result["tracking_screen_passed"] else "SCREEN_FAIL",
                          "velocity", round(metrics["body_velocity_rmse_m_s"],6),
                          "path", round(metrics["peak_path_error_m"],6), flush=True)
                else:
                    print(case["variant"], case["command_name"], case["payload"],
                          result["status"], result["execution_error"], flush=True)
        try:
            collect_cases(cases, args.workers, publish)
            check_sources(sources)
            record["status"] = "failed" if any("execution_error" in row for row in record["results"]) else "complete"
            save()
        except BaseException as error:
            record["status"] = "interrupted_or_failed"
            record["error"] = f"{type(error).__name__}: {error}"
            save()
            raise
    if record["status"] != "complete" or (args.require_tracking and not all(row["tracking_screen_passed"] for row in record["results"])):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
