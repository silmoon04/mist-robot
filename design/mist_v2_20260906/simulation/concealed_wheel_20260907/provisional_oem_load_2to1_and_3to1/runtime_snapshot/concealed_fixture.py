"""Suspended single-leg load fixture; this applies a virtual load, not a gait."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pybullet as pb

import model
import run_sim
from model import fk, total_mass
from run_sim import ActuatorBank, load_world, smooth


def trial(parameters, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    cid, robot, legs, wheels, names, q0, dt, base0, terrain = load_world(parameters, "single_leg_swing")
    position, quaternion = pb.getBasePositionAndOrientation(robot)
    # The supported fixture starts above the floor and stays fixed throughout.
    pb.resetBasePositionAndOrientation(robot, [position[0], position[1], position[2] + .4], quaternion)
    bank = ActuatorBank(parameters, q0, dt)
    force = total_mass(parameters) * parameters["environment"]["gravity_m_s2"] / 3
    ids = list(range(pb.getNumJoints(robot)))
    stride = max(1, round(.02 / dt))
    times, torques, errors, saturations, travels, history = [], [], [], [], [], []
    for step in range(round(6 / dt)):
        t = step * dt
        load = force * smooth((t - 1) / 1.5) * (1 - smooth((t - 4.5) / .5))
        states = pb.getJointStates(robot, ids)
        q = np.array([[states[j][0] for j in leg] for leg in legs])
        qd = np.array([[states[j][1] for j in leg] for leg in legs])
        joint_torque, shaft_torque = bank.update(q, qd, q0)
        for i, leg in enumerate(legs):
            for k, joint in enumerate(leg):
                pb.setJointMotorControl2(robot, joint, pb.TORQUE_CONTROL, force=float(joint_torque[i, k]))
        wheel = pb.getLinkState(robot, wheels[0], computeForwardKinematics=True)
        axle = wheel[4]
        # The vertical contact line passes through the axle, not an eccentric COM.
        pb.applyExternalForce(robot, wheels[0], [0, 0, load], axle, pb.WORLD_FRAME)
        shaft_speed = bank.A @ qd[0]
        directional_speed = np.sign(bank.filtered[0]) * shaft_speed
        available = np.minimum(bank.peak, bank.stall * np.clip(1 - directional_speed / bank.speed, 0, 1))
        saturated = bool(np.any(np.abs(bank.filtered[0]) > available + 1e-10))
        travel_reference = getattr(bank, "travel_reference", bank.s0)
        delta = np.degrees(bank.A @ q[0] - travel_reference[0])
        limits = np.array(parameters["transmission"]["motor_travel_limits_deg"])
        violated = bool(np.any((delta < limits[:, 0]) | (delta > limits[:, 1])))
        pb.stepSimulation()
        states = pb.getJointStates(robot, ids)
        actual_q = np.array([[states[j][0] for j in leg] for leg in legs])
        error = float(np.linalg.norm(fk(parameters, 0, actual_q[0])["axle"] - fk(parameters, 0, q0[0])["axle"]))
        times.append(t)
        torques.append(shaft_torque[0].copy())
        errors.append(error)
        saturations.append(saturated)
        travels.append(violated)
        if step % stride == 0:
            history.append({"t": round(t + dt, 6), "force_interval_start_s": t,
                            "applied_vertical_force_n": float(load), "applied_world_point_m": list(axle),
                            "joint_angles_rad": actual_q[0].tolist(), "all_joint_angles_rad": actual_q.tolist(), "servo_torque_nm": shaft_torque[0].tolist(),
                            "foot_error_m": error, "active_servo_saturated": saturated,
                            "active_shaft_travel_violation": violated})
    time_array = np.array(times)
    torque_array = np.array(torques)
    hold = (time_array >= 3) & (time_array <= 4.4)
    rms = np.sqrt(np.mean(torque_array[hold] ** 2, axis=0))
    max_error = float(np.max(np.array(errors)[hold]))
    hold_saturations = int(np.count_nonzero(np.array(saturations)[hold]))
    hold_travels = int(np.count_nonzero(np.array(travels)[hold]))
    criteria = {"foot_error_below_15mm": max_error < .015,
                "motor_rms_below_continuous": float(max(rms)) < bank.continuous,
                "no_active_hold_saturation": hold_saturations == 0,
                "no_active_shaft_travel_violation": not any(travels)}
    paths = [Path(model.__file__), Path(run_sim.__file__), Path(__file__)]
    report = {"status": "PASS_IN_MODEL" if all(criteria.values()) else "FAIL_IN_MODEL", "criteria": criteria,
              "fixed_base": True, "mass_kg": total_mass(parameters), "contacts_equivalent": 3, "load_multiplier": 1,
              "force_n": force, "applied_point": "wheel link-frame axle origin; vertical tire contact line",
              "hold_window_s": [3, 4.4], "physics_dt_s": dt, "hold_samples": int(np.count_nonzero(hold)),
              "hold_max_foot_error_m": max_error, "hold_servo_rms_nm": rms.tolist(),
              "servo_continuous_limit_nm": bank.continuous, "servo_peak_limit_nm": bank.peak,
              "continuous_torque_reserve_fraction": 1 - float(max(rms)) / bank.continuous,
              "active_hold_saturated_steps": hold_saturations, "active_hold_travel_violations": hold_travels,
              "active_all_run_travel_violations": int(np.count_nonzero(travels)),
              "all_servo_saturation_fraction": bank.saturated_steps / bank.step,
              "history": history, "parameters_used": parameters,
              "parameters_sha256": hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest(),
              "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              "limitations": ["An ideal vertical force acts on one suspended wheel with the body fixed. This is a load fixture, not locomotion.",
                              "The wheel-axis load point and full-rate hold RMS differ from the older load_test.py COM-force/50Hz metrics.",
                              "Backlash, compliance, bandwidth, friction and continuous limits remain unmeasured assumptions."]}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    np.savez_compressed(output / "fixture_1000hz.npz", time_s=time_array, torque_nm=torque_array,
                        foot_error_m=errors, saturated=saturations, travel_violation=travels)
    pb.disconnect(cid)
    return report
