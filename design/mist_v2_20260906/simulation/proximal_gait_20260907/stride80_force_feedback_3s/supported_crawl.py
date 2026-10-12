"""Free-base supported crawl experiment. All actuation uses existing torque limits."""
import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import numpy as np
import pybullet as pb

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
RUNTIME = Path(sys.argv[sys.argv.index("--runtime") + 1]).resolve() if "--runtime" in sys.argv else HERE / "runtime_snapshot"
sys.path.insert(0, str(RUNTIME if RUNTIME.is_dir() else SIM))
import model as model_module
import run_sim as run_sim_module
import geometry_study.geometry_study as geometry_module
from model import build_urdf, fk, ik, load_parameters, total_mass
from run_sim import ActuatorBank, base_link_pose, load_world, scene_geometry, smooth, support_margin, world_com
from geometry_study.geometry_study import body_for_com, closest_inset, com as kinematic_com


def json_write(path, value):
    path.write_text(json.dumps(value, indent=2, default=lambda item: item.item() if isinstance(item, np.generic) else item.tolist()), encoding="utf-8")


def run(config, parameters, destination):
    destination.mkdir(parents=True, exist_ok=True)
    json_write(destination / "parameters_used.json", parameters)
    json_write(destination / "controller.json", config)
    sources = {}
    for path in [Path(__file__), Path(model_module.__file__), Path(run_sim_module.__file__), Path(geometry_module.__file__)]:
        content = path.read_bytes()
        sources[path.name] = hashlib.sha256(content).hexdigest()
        (destination / path.name).write_bytes(content)
    build_urdf(parameters, destination / "candidate.urdf")
    cid, robot, legids, wheelids, names, q0, dt, base0, terrain = load_world(parameters, "crawl")
    bank = ActuatorBank(parameters, q0, dt)
    allids = list(range(pb.getNumJoints(robot)))
    wheelradius = parameters["geometry"]["wheel_diameter_m"] / 2
    wheelwidth = parameters["geometry"]["wheel_width_m"] / 2
    anchors = np.array([base0 + fk(parameters, i, q0[i])["axle"] for i in range(4)])
    anchors[:, 2] = wheelradius
    nominal_anchors = anchors.copy()
    knots = []
    last_body = base0 + [0, 0, config["raise_m"]]
    planfeet = anchors.copy()
    if config["com_inset_m"] > 0:
        for k in range(4 * config["cycles"]):
            active_leg = config["order"][k % 4]
            stance = [i for i in range(4) if i != active_leg]
            nominal_com = np.array([config["stride_m"] * k / 4, 0]) + kinematic_com(parameters, q0)[:2]
            desired_com = closest_inset(planfeet[stance], nominal_com, config["com_inset_m"])
            bodies = []
            for u in np.linspace(0, 1, 41):
                feet = planfeet.copy()
                feet[active_leg] += [config["stride_m"] * smooth(u), 0, config["swing_m"] * math.sin(math.pi * u) ** 2]
                body, qs, valid = body_for_com(parameters, feet, last_body[:2], base0[2] + config["raise_m"], desired_com)
                if not valid:
                    raise ValueError(f"COM plan unreachable at step{k}, phase{u}")
                bodies.append(body)
            knots.append((last_body.copy(), np.array(bodies)))
            last_body = bodies[-1].copy()
            planfeet[active_leg, 0] += config["stride_m"]
    nominal_duration = config["settle_s"] + config["leg_period_s"] * 4 * config["cycles"] + config["final_settle_s"]
    duration = nominal_duration + (8 * config["cycles"] if config["support_gate"] else 0)
    motor = parameters["wheel_motor"]
    voltage = parameters["servo"]["simulation_voltage_v"] / motor["nominal_voltage_v"]
    wspeed = motor["no_load_speed_rpm"] * 2 * math.pi / 60 * voltage
    wstall = motor["stall_torque_nm"] * voltage
    current_limit = wstall * max(0, motor["current_limit_a"] - motor["no_load_current_a"]) / max(.01, motor["stall_current_a"] * voltage - motor["no_load_current_a"])
    sample_stride = max(1, round(1 / (parameters["simulation"]["record_hz"] * dt)))
    control_stride = max(1, round(.01 / dt))
    target = q0.copy()
    integral = np.zeros(3)
    frames, milestones, collisions = [], [], []
    last_leg_step = -1
    invalid_count = clamped_count = body_contacts = 0
    elapsed = 0.
    freeze_time = 0.
    completed = 0
    desired_body = base0.copy()
    desired_feet = anchors.copy()
    active = -1
    stage = "settle"
    phase = 0.
    prev_phase = 0.
    wheel_peak = 0.
    wheel_energy = 0.
    max_force = 0.
    max_clearance = np.zeros(4)
    supports = []
    pose_error = np.zeros(3)
    euler = np.zeros(3)
    control_period = control_stride * dt
    grf = np.zeros(4)
    completion_time = None
    abort_reason = None
    force_offsets = np.zeros(4)
    command_feet = anchors.copy()
    for step in range(round(duration / dt)):
        t = step * dt
        states = pb.getJointStates(robot, allids)
        q = np.array([[states[j][0] for j in row] for row in legids])
        qd = np.array([[states[j][1] for j in row] for row in legids])
        if step % control_stride == 0:
            bpos, quat = base_link_pose(robot)
            bpos = np.array(bpos)
            euler = np.array(pb.getEulerFromQuaternion(quat))
            rot = np.array(pb.getMatrixFromQuaternion(quat)).reshape(3, 3)
            com = world_com(robot)
            actual_feet = np.array([bpos + rot @ fk(parameters, i, q[i])["axle"] for i in range(4)])
            grf[:] = 0
            supports = []
            for contact in pb.getContactPoints(bodyA=robot):
                if contact[2] != robot and contact[3] in wheelids:
                    i = wheelids.index(contact[3])
                    grf[i] += contact[9]
                    if contact[9] > .25 and contact[7][2] > .5:
                        supports.append(contact[5])
            if t >= config["settle_s"] and elapsed < 4 * config["cycles"] * config["leg_period_s"]:
                leg_step = int(elapsed / config["leg_period_s"])
                active = config["order"][leg_step % 4]
                phase = (elapsed % config["leg_period_s"]) / config["leg_period_s"]
                if leg_step != last_leg_step:
                    if last_leg_step >= 0:
                        oldactive = config["order"][last_leg_step % 4]
                        anchors[oldactive, 0] += config["stride_m"]
                        completed += 1
                        milestones.append({"t": t, "completed_legs": completed, "base_position": bpos.tolist(), "contacts_n": grf.tolist()})
                    last_leg_step = leg_step
                lift = float(np.clip((phase - .25) / .50, 0, 1))
                shift_weight = min(smooth(phase / .22), smooth((1 - phase) / .22))
                direction = np.sign(nominal_anchors[active, :2])
                shift = -direction * np.array([config["shift_x_m"], config["shift_y_m"]]) * shift_weight
                forward = config["stride_m"] * elapsed / (4 * config["leg_period_s"])
                desired_body = base0 + np.array([forward + shift[0], shift[1], config["raise_m"]])
                desired_feet = anchors.copy()
                desired_feet[active, 0] += config["stride_m"] * smooth(lift)
                desired_feet[active, 2] += config["swing_m"] * math.sin(math.pi * lift) ** 2
                if knots:
                    previous_body, swing_bodies = knots[leg_step]
                    if phase < .25:
                        weight = smooth(phase / .25)
                        desired_body = previous_body * (1 - weight) + swing_bodies[0] * weight
                    else:
                        desired_body = np.array([np.interp(lift, np.linspace(0, 1, 41), swing_bodies[:, j]) for j in range(3)])
                stage = "shift" if phase < .25 else "swing" if phase < .75 else "recover"
                triangle = actual_feet[[i for i in range(4) if i != active]]
                margin = support_margin(triangle, com)
                # Pause before unloading until the measured COM is inside support.
                freeze = bool(config["support_gate"] and .245 <= phase < .26 and (margin is None or margin < config["gate_margin_m"] or max(abs(euler[:2])) > math.radians(6)))
                # Touchdown is also confirmed through measured normal force.
                freeze |= bool(config["support_gate"] and phase >= .94 and grf[active] < 1.)
                if freeze:
                    freeze_time += control_period
                else:
                    elapsed += control_period
            elif elapsed >= 4 * config["cycles"] * config["leg_period_s"]:
                if completed < 4 * config["cycles"]:
                    anchors[active, 0] += config["stride_m"]
                    completed += 1
                    milestones.append({"t": t, "completed_legs": completed, "base_position": bpos.tolist(), "contacts_n": grf.tolist()})
                    completion_time = t
                active = -1
                stage = "final_settle"
                desired_body = base0 + np.array([config["stride_m"] * config["cycles"], 0, config["raise_m"]])
                if knots:
                    blend = smooth((t - completion_time) / config["final_settle_s"])
                    desired_body = knots[-1][1][-1] * (1 - blend) + desired_body * blend
                desired_feet = anchors.copy()
            if stage == "settle":
                desired_body[2] = base0[2] + config["raise_m"] * smooth(t / config["settle_s"])
            pose_error = desired_body - bpos
            if t > .5:
                integral += np.clip(pose_error, -.03, .03) * control_period * config["integral_gain"]
                integral = np.clip(integral, -config["integral_limit_m"], config["integral_limit_m"])
            body_command = desired_body + np.clip(config["position_gain"] * pose_error, -.020, .020) + integral
            attitude_command = np.clip(-config["attitude_gain"] * euler, -.075, .075)
            command_rot = np.array(pb.getMatrixFromQuaternion(pb.getQuaternionFromEuler(attitude_command))).reshape(3, 3)
            requested_offsets = np.zeros(4)
            if config["contact_gain_m_per_n"] and active >= 0 and stage == "swing":
                stance = [i for i in range(4) if i != active]
                reference_q = np.array([ik(parameters, i, desired_feet[i] - desired_body)[0] for i in range(4)])
                reference_com = desired_body + kinematic_com(parameters, reference_q)
                vertical_loads = np.linalg.solve(np.vstack([np.ones(3), anchors[stance, :2].T]), total_mass(parameters) * parameters["environment"]["gravity_m_s2"] * np.array([1, reference_com[0], reference_com[1]]))
                requested_offsets[stance] = np.clip(config["contact_gain_m_per_n"] * (grf[stance] - vertical_loads), -.006, .006)
            force_offsets += control_period / (.1 + control_period) * (requested_offsets - force_offsets)
            command_feet = desired_feet.copy()
            command_feet[:, 2] += force_offsets
            for i in range(4):
                raw, valid = ik(parameters, i, command_rot.T @ (command_feet[i] - body_command))
                if valid:
                    target[i] = raw
                else:
                    invalid_count += 1
                    # Hold the last reachable target; retain invalid requests as failures.
                    clamped_count += 1
        torque, shaft = bank.update(q, qd, target)
        for i, row in enumerate(legids):
            for k, jid in enumerate(row):
                pb.setJointMotorControl2(robot, jid, pb.TORQUE_CONTROL, force=float(torque[i, k]))
        wheel_torques = []
        for i, jid in enumerate(wheelids):
            heading = fk(parameters, i, q[i])["heading"]
            # Holding joint angle alone rolls the wheel as the tibia pitches.
            # Compensate tibia and body pitch to hold wheel orientation in world.
            angle_target = -(q[i, 1] + q[i, 2] - q0[i, 1] - q0[i, 2])
            angle_target += euler[1] * math.cos(heading) - euler[0] * math.sin(heading)
            if not config["world_wheel_hold"]:
                angle_target = 0.
            speed = states[jid][1]
            wanted = config["wheel_kp"] * (angle_target - states[jid][0]) - .03 * speed
            limit = min(current_limit, wstall * np.clip(1 - np.sign(wanted) * speed / wspeed, 0, 1))
            wt = float(np.clip(wanted, -limit, limit))
            wheel_torques.append(wt)
            wheel_peak = max(wheel_peak, abs(wt))
            wheel_energy += abs(wt * speed) * dt
            pb.setJointMotorControl2(robot, jid, pb.TORQUE_CONTROL, force=wt)
        pb.stepSimulation()
        if step % sample_stride == 0:
            states = pb.getJointStates(robot, allids)
            q = np.array([[states[j][0] for j in row] for row in legids])
            bpos, quat = base_link_pose(robot)
            rot = np.array(pb.getMatrixFromQuaternion(quat)).reshape(3, 3)
            tilt = math.degrees(math.acos(np.clip(rot[2, 2], -1, 1)))
            clearance = []
            actual_axles = []
            for i in range(4):
                foot = fk(parameters, i, q[i])
                axis = rot @ foot["wheel_axis"]
                axle = np.array(bpos) + rot @ foot["axle"]
                actual_axles.append(axle.tolist())
                low = wheelradius * math.sqrt(max(0, 1 - axis[2] ** 2)) + wheelwidth * abs(axis[2])
                clearance.append(float(axle[2] - low))
            max_clearance = np.maximum(max_clearance, clearance)
            grf[:] = 0
            supports = []
            for c in pb.getContactPoints(bodyA=robot):
                if c[2] == robot and c[8] < -.001:
                    collisions.append([t, c[3], c[4], c[8]])
                elif c[2] != robot and c[3] not in wheelids and c[9] > .25:
                    body_contacts += 1
                if c[2] != robot and c[3] in wheelids:
                    grf[wheelids.index(c[3])] += c[9]
                    if c[9] > .25 and c[7][2] > .5:
                        supports.append(c[5])
            com = world_com(robot)
            margin = support_margin(supports, com)
            max_force = max(max_force, max(grf))
            frames.append({"t": round(t, 4), "base_position": list(bpos), "base_quaternion_xyzw": list(quat),
                           "q": [float(s[0]) for s in states], "target_q": target.flatten().tolist(),
                           "desired_base_position": desired_body.tolist(), "desired_axles_world": desired_feet.tolist(),
                           "command_axles_world": command_feet.tolist(), "force_feedback_offsets_m": force_offsets.tolist(),
                           "actual_axles_world": actual_axles,
                           "contact_normal_n": grf.tolist(), "com_world": com.tolist(), "tilt_deg": tilt,
                           "support_margin_m": margin, "wheel_clearance_m": clearance, "wheel_torque_nm": wheel_torques,
                           "servo_torque_nm": shaft.tolist(), "active_leg": active, "phase": phase, "stage": stage,
                           "gait_elapsed_s": elapsed, "pose_error_m": pose_error.tolist(), "leg_step": last_leg_step})
            if tilt > 30 or body_contacts > 10:
                abort_reason = "tilt_above_30deg" if tilt > 30 else "sustained_nonwheel_ground_support"
                break
            if completion_time is not None and t >= completion_time + config["final_settle_s"]:
                break
    duration = (step + 1) * dt
    final = np.array(base_link_pose(robot)[0])
    mt = np.array(bank.motor_torque)
    torque_rms = np.sqrt(np.mean(mt ** 2, axis=0))
    late = [f for f in frames if f["t"] >= config["settle_s"]]
    rms = float(np.sqrt(np.mean([(np.array(f["q"]).reshape(4, 4)[:, :3] - np.array(f["target_q"]).reshape(4, 3)) ** 2 for f in late])) * 180 / math.pi)
    peak_tilt = max(f["tilt_deg"] for f in frames)
    contacts_missing = sum(sum(np.array(f["contact_normal_n"]) > 1) < 3 for f in late) / max(1, len(late))
    body_xy = np.array([f["base_position"][:2] for f in frames])
    peak_drift = float(np.max(np.abs(body_xy[:, 1])))
    planned = config["stride_m"] * config["cycles"]
    cycle_positions = [np.array(m["base_position"]) for m in milestones if m["completed_legs"] % 4 == 0]
    cycle_advances = [float((b - a)[0]) for a, b in zip(cycle_positions, cycle_positions[1:])]
    swing_audits = []
    for k in range(4 * config["cycles"]):
        samples = [f for f in frames if f["leg_step"] == k and f["active_leg"] >= 0]
        active_leg = config["order"][k % 4]
        swing = [f for f in samples if f["stage"] == "swing"]
        landing = [f for f in samples if f["phase"] >= .75]
        swing_audits.append({"leg_step": k, "leg": active_leg,
                             "max_swing_clearance_m": max([f["wheel_clearance_m"][active_leg] for f in swing], default=0.),
                             "unloaded_during_swing": any(f["contact_normal_n"][active_leg] < .25 for f in swing),
                             "touchdown_confirmed": any(f["contact_normal_n"][active_leg] > 1 for f in landing)})
    criteria = {"all_leg_steps_completed": completed == 4 * config["cycles"], "continuous_motor_rms": bool(np.max(torque_rms) < bank.continuous),
                "reachable_targets": invalid_count == 0, "motor_travel_limits": bank.travel_violations == 0,
                "tilt_below_10deg": peak_tilt < 10, "joint_tracking_rms_below_8deg": rms < 8,
                "no_nonwheel_ground_support": body_contacts == 0, "coarse_self_collision": len(collisions) == 0,
                "forward_at_least_80pct_planned": final[0] - base0[0] >= .8 * planned,
                "final_lateral_drift_below_10mm": abs(final[1] - base0[1]) < .01,
                "all_feet_clear_15mm": all(s["max_swing_clearance_m"] >= .015 for s in swing_audits),
                "all_swings_unload_and_touch_down": all(s["unloaded_during_swing"] and s["touchdown_confirmed"] for s in swing_audits),
                "no_early_abort": abort_reason is None,
                "three_contact_samples_at_least_95pct": contacts_missing <= .05}
    if config["cycles"] > 1:
        criteria["each_full_cycle_advances_at_least_60pct_stride"] = len(cycle_advances) == config["cycles"] - 1 and min(cycle_advances) >= .6 * config["stride_m"]
    report = {"status": "PASS_IN_MODEL" if all(criteria.values()) else "FAIL_IN_MODEL", "criteria": criteria,
              "mass_kg": total_mass(parameters), "duration_s": duration, "dt_s": dt, "completed_leg_steps": completed,
              "planned_forward_m": planned, "base_displacement_m": (final - base0).tolist(), "mean_forward_speed_m_s": float((final[0] - base0[0]) / duration),
              "max_tilt_deg": peak_tilt, "max_lateral_excursion_m": peak_drift, "joint_tracking_rms_deg": rms,
              "motor_rms_nm": torque_rms.tolist(), "max_servo_rms_nm": float(np.max(torque_rms)),
              "servo_continuous_limit_nm": bank.continuous, "servo_peak_limit_nm": bank.peak,
              "motor_saturation_fraction": bank.saturated_steps / bank.step, "motor_travel_violation_fraction": bank.travel_violations / bank.step,
              "invalid_ik_commands": invalid_count, "wheel_current_torque_limit_nm": current_limit, "max_wheel_torque_nm": wheel_peak,
              "wheel_abs_mechanical_work_j": wheel_energy, "max_contact_force_n": max_force,
              "all_foot_max_clearance_m": max_clearance.tolist(), "fewer_than_three_contact_sample_fraction": contacts_missing,
              "support_gate_wait_s": freeze_time, "coarse_collision_count": len(collisions), "nonwheel_contact_samples": body_contacts,
              "full_cycle_advances_m": cycle_advances, "trajectory_record_hz": parameters["simulation"]["record_hz"],
              "nominal_duration_s": nominal_duration, "abort_reason": abort_reason, "swing_audits": swing_audits,
              "min_sampled_support_margin_m": min((f["support_margin_m"] for f in frames if f["support_margin_m"] is not None), default=None),
              "negative_support_margin_fraction": sum(f["support_margin_m"] is not None and f["support_margin_m"] < 0 for f in late) / len(late),
              "source_sha256": sources, "parameters_sha256": hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest(),
              "controller_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
              "pybullet_api": pb.getAPIVersion(), "python": platform.python_version(), "milestones": milestones,
              "limitations": ["This is a coarse collision model with ideal state feedback. IMU, contact estimation and localization are not implemented.",
                              "Use parameters_used.json for mass provenance. The initial sensitivity moves the same 55 g servo to 40 mm down the femur; fitted geometry is a separate input.",
                              "Servo delay, command hysteresis, stiffness, thermal limits and friction are assumed. No separate force-side backlash gap, rotor inertia or belt vibration.",
                              "Wheel orientation compensation uses small body roll/pitch angles and is only evaluated for the stated tilt envelope.",
                              "No base reset, external forces, raised torque limits or contact constraints are used after initial placement.",
                              "Not a stair controller or a physical build release."]}
    json_write(destination / "report.json", report)
    json_write(destination / "trajectory.json", {"schema_version": 1, "case": "supported_crawl", "joint_names": names, "frames": frames})
    json_write(destination / "scene.json", scene_geometry(parameters, "crawl"))
    np.savez_compressed(destination / "servo_torques_1000hz.npz", torque_nm=mt, dt_s=dt)
    pb.disconnect(cid)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--stride", type=float, default=.04)
    parser.add_argument("--period", type=float, default=3.)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--position-gain", type=float, default=.5)
    parser.add_argument("--integral-gain", type=float, default=.3)
    parser.add_argument("--attitude-gain", type=float, default=.5)
    parser.add_argument("--world-wheel-hold", type=int, default=1)
    parser.add_argument("--support-gate", type=int, default=1)
    parser.add_argument("--swing", type=float, default=.04)
    parser.add_argument("--shift-x", type=float, default=.03)
    parser.add_argument("--shift-y", type=float, default=.022)
    parser.add_argument("--raise-body", type=float, default=0.)
    parser.add_argument("--order", default="0,3,1,2")
    parser.add_argument("--com-inset", type=float, default=0.)
    parser.add_argument("--contact-gain", type=float, default=0.)
    parser.add_argument("--parameters", type=Path, default=SIM / "proximal_knee_20260907/parameters_same_mass.json")
    parser.add_argument("--runtime", type=Path)
    args = parser.parse_args()
    config = {"stride_m": args.stride, "leg_period_s": args.period, "cycles": args.cycles, "settle_s": 1.5, "final_settle_s": 2.,
              "position_gain": args.position_gain, "integral_gain": args.integral_gain, "integral_limit_m": .015, "attitude_gain": args.attitude_gain,
              "world_wheel_hold": bool(args.world_wheel_hold), "support_gate": bool(args.support_gate), "gate_margin_m": .01,
              "swing_m": args.swing, "shift_x_m": args.shift_x, "shift_y_m": args.shift_y, "wheel_kp": .7,
              "raise_m": args.raise_body, "order": [int(i) for i in args.order.split(",")], "com_inset_m": args.com_inset,
              "contact_gain_m_per_n": args.contact_gain}
    report = run(config, load_parameters(args.parameters), HERE / args.name)
    print(json.dumps({key: report[key] for key in ["status", "criteria", "base_displacement_m", "mean_forward_speed_m_s", "max_tilt_deg", "max_servo_rms_nm", "completed_leg_steps"]}, default=lambda item: item.item()), flush=True)


if __name__ == "__main__":
    main()
