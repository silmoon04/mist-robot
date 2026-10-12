"""Offline leg sizing; SI units, no robot/device interfaces.

This is a quasi-static engineering screen. It does not prove stair traversal,
thermal duty cycle, fatigue, traction, or safe hardware operation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

MODES = ("absolute_tibia", "unequal_remote_pulleys", "joint_relative_ideal")


def transmission(mode, ratios):
    """u=Aq, where u is STS output-shaft angle before external reduction."""
    ry, rh, rk = ratios
    A = np.diag([ry, rh, rk]).astype(float)
    if mode == "absolute_tibia":
        A[2, 1] = rk
    elif mode == "unequal_remote_pulleys":
        A[2, 1] = 1.0
    elif mode != "joint_relative_ideal":
        raise ValueError(mode)
    return A


def fk(q, lengths, offsets=(0.0, 0.0), mount=(0.0, 0.0, 0.0), azimuth=0.0):
    y, h, k = q
    l1, l2 = lengths
    phi = y + azimuth
    x = offsets[0] + l1 * np.sin(h) + l2 * np.sin(h + k)
    yy = offsets[1]
    z = -l1 * np.cos(h) - l2 * np.cos(h + k)
    c, s = np.cos(phi), np.sin(phi)
    return np.array([c * x - s * yy, s * x + c * yy, z]) + mount


def jacobian(q, lengths, offsets=(0.0, 0.0), azimuth=0.0):
    y, h, k = q
    l1, l2 = lengths
    phi = y + azimuth
    er = np.array([np.cos(phi), np.sin(phi), 0.0])
    et = np.array([-np.sin(phi), np.cos(phi), 0.0])
    ez = np.array([0.0, 0.0, 1.0])
    reach = l1 * np.sin(h) + l2 * np.sin(h + k)
    a = l1 * np.cos(h) + l2 * np.cos(h + k)
    b = l2 * np.cos(h + k)
    c = l2 * np.sin(h + k)
    return np.column_stack([
        (offsets[0] + reach) * et - offsets[1] * er,
        a * er + reach * ez,
        b * er + c * ez,
    ])


def ik_planar(radial, down, lengths, limits=None):
    """Negative-knee branch; radial measured from the pitch axis, not yaw axis."""
    l1, l2 = lengths
    ck = (radial * radial + down * down - l1 * l1 - l2 * l2) / (2 * l1 * l2)
    if abs(ck) > 1 + 1e-10:
        return None
    k = -math.acos(float(np.clip(ck, -1, 1)))
    h = math.atan2(radial, down) - math.atan2(l2 * math.sin(k), l1 + l2 * math.cos(k))
    q = np.array([0.0, h, k])
    if limits is not None and (np.any(q < limits[:, 0] - 1e-10) or np.any(q > limits[:, 1] + 1e-10)):
        return None
    return q


def motor_torque(joint_torque, A, efficiency):
    """Sizing convention divides each channel by eta, including backdrive loads."""
    return np.linalg.solve(A.T, joint_torque) / np.asarray(efficiency)


def total_mass(p):
    m = p["mass"]
    body = sum(m[k] for k in ("shell_kg", "battery_kg", "brain_phone_kg", "face_phone_with_frame_kg", "electronics_kg", "harness_kg"))
    leg = 3 * m["proximal_servo_kg"] + sum(m[k] for k in ("yaw_carriage_without_servos_kg", "femur_with_pulleys_kg", "tibia_with_carrier_kg", "wheel_motor_with_mount_kg", "wheel_hub_and_tire_kg"))
    return body + 4 * leg


def leg_gravity(q, lengths, offsets, p):
    """Generalized gravity loads of the moving leg, with uniform link COMs."""
    m, g = p["mass"], p["environment"]["gravity_m_s2"]
    l1, l2 = lengths
    femur_j = jacobian(q, (l1 / 2, 0), offsets)
    tibia_j = jacobian(q, (l1, l2 / 2), offsets)
    wheel_j = jacobian(q, lengths, offsets)
    # A zero second length ensures femur COM has zero knee derivative.
    down = np.array([0.0, 0.0, -g])
    return femur_j.T @ (m["femur_with_pulleys_kg"] * down) + tibia_j.T @ (m["tibia_with_carrier_kg"] * down) + wheel_j.T @ ((m["wheel_motor_with_mount_kg"] + m["wheel_hub_and_tire_kg"]) * down)


def servo_limits(voltage, p):
    s = p["servo"]
    scale = voltage / s["nominal_voltage_v"]
    stall = s["stall_torque_nm"] * scale
    omega = s["no_load_speed_rpm"] * 2 * np.pi / 60 * scale
    return stall, omega, stall * s["continuous_fraction_of_stall"], stall * s["peak_fraction_of_stall"]


def mass_limit(affine_slope, affine_offset, motor_allowance):
    """Largest nonnegative mass satisfying every |a*m+b| <= allowance."""
    lower, upper = 0.0, math.inf
    for a, b in zip(affine_slope, affine_offset):
        if abs(a) < 1e-12:
            if abs(b) > motor_allowance: return 0.0
            continue
        ends = sorted(((-motor_allowance - b) / a, (motor_allowance - b) / a))
        lower, upper = max(lower, ends[0]), min(upper, ends[1])
    return float(max(0.0, upper)) if upper >= lower else 0.0


def directional_speed(J, A, demand, voltage, p, direction=(1, 0, 0)):
    """Local Cartesian speed under approximate linear DC torque-speed envelope."""
    if np.linalg.cond(J) > 1e8:
        return 0.0
    qdot = np.linalg.solve(J, np.asarray(direction, dtype=float))
    unit_motor_speed = np.abs(A @ qdot)
    stall, omega, _, _ = servo_limits(voltage, p)
    # A loaded stationary channel still has to hold the requested force.
    if np.any(np.abs(demand) >= stall):
        return 0.0
    available = omega * np.maximum(0.0, 1 - np.abs(demand) / stall)
    moving = unit_motor_speed > 1e-10
    return float(np.min(available[moving] / unit_motor_speed[moving])) if np.any(moving) else 0.0


def position_uncertainty(q, lengths, offsets, A, ratios, joint_load, p):
    """Full backlash travel in inputs is converted to a +/- half-width bound."""
    r = np.asarray(ratios)
    C = np.diag(1 / r) @ A
    invC = np.linalg.inv(C)
    halfwidth = np.deg2rad(0.5 * (p["servo"]["gearbox_backlash_full_width_deg"] / r + np.asarray(p["transmission"]["output_backlash_full_width_deg"])))
    J = jacobian(q, lengths, offsets)
    p0 = fk(q, lengths, offsets)
    worst_linear, worst_exact = 0.0, 0.0
    for signs in itertools.product((-1, 1), repeat=3):
        dq = invC @ (halfwidth * signs)
        worst_linear = max(worst_linear, float(np.linalg.norm(J @ dq)))
        worst_exact = max(worst_exact, float(np.linalg.norm(fk(q + dq, lengths, offsets) - p0)))
    output_load = np.linalg.solve(C.T, joint_load)
    output_deflection = output_load / np.asarray(p["transmission"]["output_stiffness_nm_per_rad"])
    dq_elastic = invC @ output_deflection
    elastic = float(np.linalg.norm(fk(q + dq_elastic, lengths, offsets) - p0))
    return worst_linear, worst_exact, elastic


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate_pose(q, lengths, offsets, ratios, mode, force, mass, voltage, p):
    A = transmission(mode, ratios)
    J = jacobian(q, lengths, offsets)
    endpoint_load = J.T @ force
    gravity = leg_gravity(q, lengths, offsets, p)
    joint_load = endpoint_load + gravity
    demand = motor_torque(joint_load, A, p["transmission"]["efficiency"])
    stall, _, continuous, peak = servo_limits(voltage, p)
    linear, exact, elastic = position_uncertainty(q, lengths, offsets, A, ratios, joint_load, p)
    return {
        "yaw_motor_nm": abs(float(demand[0])), "hip_motor_nm": abs(float(demand[1])), "knee_motor_nm": abs(float(demand[2])),
        "continuous_utilization": float(np.max(np.abs(demand)) / continuous),
        "peak_utilization": float(np.max(np.abs(demand)) / peak),
        "stall_utilization": float(np.max(np.abs(demand)) / stall),
        "loaded_radial_speed_m_s": directional_speed(J, A, demand, voltage, p),
        "loaded_vertical_speed_m_s": directional_speed(J, A, demand, voltage, p, (0, 0, 1)),
        "backlash_linear_bound_mm": linear * 1000,
        "backlash_corner_bound_mm": exact * 1000,
        "assumed_elastic_error_mm": elastic * 1000,
        "condition_number": float(np.linalg.cond(J)),
        "force_radial_n": float(force[0]), "force_tangent_n": float(force[1]), "force_vertical_n": float(force[2]),
        "endpoint_hip_load_nm": float(endpoint_load[1]), "net_joint_hip_load_nm": float(joint_load[1]),
        "net_joint_knee_load_nm": float(joint_load[2]),
    }


def workspace(p, lengths, offsets, qhome):
    limits = np.deg2rad(p["geometry"]["joint_limits_deg"])
    ratios = p["transmission"]["ratios"]
    A = transmission("absolute_tibia", ratios)
    motor_limits = np.deg2rad(p["transmission"]["motor_travel_limits_deg"])
    pts, qs = [], []
    for y, h, k in itertools.product(np.linspace(*limits[0], 41), np.linspace(*limits[1], 100), np.linspace(*limits[2], 90)):
        q = np.array([y, h, k])
        u = A @ (q - qhome)
        if np.any(u < motor_limits[:, 0]) or np.any(u > motor_limits[:, 1]):
            continue
        pts.append(fk(q, lengths, offsets)); qs.append(q)
    pts = np.asarray(pts)
    rows = [{"yaw_deg": np.rad2deg(q[0]), "hip_deg": np.rad2deg(q[1]), "knee_deg": np.rad2deg(q[2]), "x_m": v[0], "y_m": v[1], "z_m": v[2]} for q, v in zip(qs[::100], pts[::100])]
    return {"samples_accepted": len(pts), "axis_min_m": pts.min(axis=0).tolist(), "axis_max_m": pts.max(axis=0).tolist(), "motor_neutral_joint_deg": np.rad2deg(qhome).tolist(), "collision_checked": False, "mount_translation_included": False}, rows


def stair_screen(p, lengths, offsets, qhome):
    """Can the same hip elevation reach ground and stair top? No path/contact proof."""
    e, g = p["environment"], p["geometry"]
    limits = np.deg2rad(g["joint_limits_deg"])
    A = transmission("absolute_tibia", p["transmission"]["ratios"])
    ml = np.deg2rad(p["transmission"]["motor_travel_limits_deg"])
    wheel_r = g["wheel_diameter_m"] / 2
    rows = []
    for height in np.arange(0.12, 0.321, 0.005):
        for reach in (0.04, 0.06, 0.08, 0.10, 0.12, 0.15):
            low = ik_planar(reach, height - wheel_r, lengths, limits)
            high = ik_planar(reach, height - wheel_r - e["step_rise_m"], lengths, limits)
            clearance = ik_planar(reach, height - wheel_r - e["step_rise_m"] - e["toe_clearance_m"], lengths, limits)
            def travel_ok(q):
                if q is None: return False
                u = A @ (q - qhome)
                return bool(np.all(u >= ml[:, 0]) and np.all(u <= ml[:, 1]))
            rows.append({"femur_mm": lengths[0] * 1000, "tibia_mm": lengths[1] * 1000, "hip_above_lower_floor_mm": height * 1000, "reach_from_pitch_mm": reach * 1000,
                "both_joint_reachable": low is not None and high is not None,
                "both_with_motor_travel": travel_ok(low) and travel_ok(high),
                "clearance_with_motor_travel": travel_ok(low) and travel_ok(clearance),
                "upper_hip_deg": None if high is None else np.rad2deg(high[1]), "upper_knee_deg": None if high is None else np.rad2deg(high[2])})
    return rows


def run(p, out, parameter_path):
    out.mkdir(parents=True, exist_ok=True)
    source_bytes = parameter_path.read_bytes()
    if json.loads(source_bytes.decode("utf-8-sig")) != p:
        raise RuntimeError("Shared parameters changed during intake; rerun for a consistent snapshot")
    (out / "parameters_snapshot.json").write_bytes(source_bytes)
    parameter_hash = hashlib.sha256(source_bytes).hexdigest()
    mass0 = total_mass(p)
    g = p["geometry"]
    nominal_lengths = (g["femur_m"], g["tibia_m"])
    offsets = (g["hip_radial_offset_m"], g["hip_transverse_offset_m"])
    limits = np.deg2rad(g["joint_limits_deg"])
    qhome = ik_planar(g["drive_radial_reach_from_pitch_m"], g["hip_to_wheel_axle_height_m"], nominal_lengths, limits)
    if qhome is None:
        raise ValueError("Shared nominal geometry is outside the chosen physical joint limits")
    gravity = p["environment"]["gravity_m_s2"]
    cases = (("four_static", 4, 1.0), ("crawl_three_static", 3, 1.0), ("pair_static", 2, 1.0), ("pair_dynamic_1p5", 2, 1.5), ("single_dynamic_1p5", 1, 1.5))
    nominal_rows = []
    for mode, voltage, (name, contacts, factor) in itertools.product(MODES, (9.9, 12.0), cases):
        force = np.array([0., 0., mass0 * gravity * factor / contacts])
        for friction in (0.0, 0.25):
            force[0], force[1] = force[2] * friction, force[2] * friction
            row = {"mode": mode, "case": name, "horizontal_force_each_fraction": friction, "mass_kg": mass0, "voltage_v": voltage}
            row.update(evaluate_pose(qhome, nominal_lengths, offsets, p["transmission"]["ratios"], mode, force, mass0, voltage, p))
            nominal_rows.append(row)
    write_csv(out / "nominal_load_cases.csv", nominal_rows)
    # All three reductions are swept; normalized poses prevent pretending short
    # legs can achieve the same absolute home clearance as long legs.
    sweep_rows = []
    length_pairs = ((0.11, 0.07), (0.14, 0.13), (0.16, 0.15))
    poses = (("normalized_home", .35, .65), ("long_reach", .60, .55), ("crouch", .65, .35))
    ratio_values = (1.0, 1.5, 2.0, 2.5, 3.0)
    for lengths, mass, voltage, mode in itertools.product(length_pairs, (3.0, 3.4, round(mass0, 3), 4.5), (9.9, 12.0), MODES):
        for ratios in itertools.product(ratio_values, repeat=3):
            demands, speeds, max_mass_peak, max_mass_crawl = [], [], [], []
            limit_stall, _, continuous, peak = servo_limits(voltage, p)
            A = transmission(mode, ratios)
            per_pose = []
            for name, rfrac, dfrac in poses:
                q = ik_planar(sum(lengths) * rfrac, sum(lengths) * dfrac, lengths, limits)
                if q is None:
                    continue
                load_cases = [(3, 1.0, 0.0, 0.0)] + [(2, 1.5, fr, ft) for fr, ft in itertools.product((-.25, .25), repeat=2)]
                for contacts, factor, fr, ft in load_cases:
                    fz = mass * gravity * factor / contacts
                    F = np.array([fr * fz, ft * fz, fz])
                    J = jacobian(q, lengths, offsets)
                    gravity_load = leg_gravity(q, lengths, offsets, p)
                    tq = J.T @ F + gravity_load
                    tm = motor_torque(tq, A, p["transmission"]["efficiency"])
                    demands.append(np.abs(tm))
                    speeds.append(directional_speed(J, A, tm, voltage, p))
                    slope = motor_torque(J.T @ (F / mass), A, p["transmission"]["efficiency"])
                    intercept = motor_torque(gravity_load, A, p["transmission"]["efficiency"])
                    max_mass_peak.append(mass_limit(slope, intercept, peak))
                    if contacts == 3:
                        per_pose.append(float(np.max(np.abs(tm)) / continuous))
                        max_mass_crawl.append(mass_limit(slope, intercept, continuous))
            maximum = np.max(demands, axis=0)
            # Travel span applies to the complete physical joint box; it is a
            # separate constraint from a local pose passing a torque test.
            span = np.abs(A) @ (limits[:, 1] - limits[:, 0])
            available_span = np.diff(np.deg2rad(p["transmission"]["motor_travel_limits_deg"]), axis=1).ravel()
            sweep_rows.append({"mode": mode, "femur_mm": lengths[0]*1000, "tibia_mm": lengths[1]*1000, "mass_kg": mass, "voltage_v": voltage,
                "ratio_yaw": ratios[0], "ratio_hip": ratios[1], "ratio_knee": ratios[2],
                "worst_yaw_motor_nm": maximum[0], "worst_hip_motor_nm": maximum[1], "worst_knee_motor_nm": maximum[2],
                "worst_peak_utilization": float(np.max(maximum) / peak), "worst_continuous_utilization": float(np.max(maximum) / continuous),
                "crawl_continuous_utilization": max(per_pose), "minimum_loaded_radial_speed_m_s": min(speeds),
                "maximum_mass_peak_kg": min(max_mass_peak), "maximum_mass_crawl_continuous_kg": min(max_mass_crawl),
                "complete_joint_box_within_servo_span": bool(np.all(span <= available_span)), "evaluated_pose_count": len(demands)})
    write_csv(out / "ratio_mass_length_sweep.csv", sweep_rows)
    stair_rows = []
    for lengths in length_pairs:
        home = ik_planar(g["drive_radial_reach_from_pitch_m"], min(g["hip_to_wheel_axle_height_m"], .70 * sum(lengths)), lengths, limits)
        if lengths == nominal_lengths: home = qhome
        stair_rows.extend(stair_screen(p, lengths, offsets, home))
    write_csv(out / "stair_reach_screen.csv", stair_rows)
    ws, wsrows = workspace(p, nominal_lengths, offsets, qhome)
    write_csv(out / "workspace_sample.csv", wsrows)
    best = []
    for lengths, voltage in itertools.product(length_pairs, (9.9, 12.0)):
        candidates = [r for r in sweep_rows if r["mode"] == "absolute_tibia" and r["mass_kg"] == round(mass0, 3) and r["voltage_v"] == voltage and r["femur_mm"] == lengths[0]*1000 and r["tibia_mm"] == lengths[1]*1000]
        feasible = [r for r in candidates if r["worst_peak_utilization"] <= 1 and r["crawl_continuous_utilization"] <= 1]
        winner = max(feasible, key=lambda r: r["minimum_loaded_radial_speed_m_s"]) if feasible else min(candidates, key=lambda r: r["worst_peak_utilization"])
        best.append({"passes_sampled_peak_and_crawl_loads": bool(feasible), **winner})
    stair_counts = []
    for lengths in length_pairs:
        sr = [r for r in stair_rows if r["femur_mm"] == lengths[0]*1000 and r["tibia_mm"] == lengths[1]*1000]
        passing = [r for r in sr if r["clearance_with_motor_travel"]]
        stair_counts.append({"femur_mm": lengths[0]*1000,"tibia_mm":lengths[1]*1000,"tested_configurations":len(sr),"both_reachable_with_motor_travel":sum(r["both_with_motor_travel"] for r in sr),"with_toe_clearance":len(passing),"first_passing_example":passing[0] if passing else None})
    summary = {"model_status": "quasi_static_sizing_not_hardware_validation", "parameters_file": str(parameter_path.resolve()),
        "parameters_sha256": parameter_hash, "estimated_total_mass_kg": mass0,
        "nominal_joint_deg": np.rad2deg(qhome).tolist(), "nominal_wheel_center_relative_yaw_m": fk(qhome, nominal_lengths, offsets).tolist(),
        "backlash_convention": "shared full-width backlash converted to +/- half-width; downstream backlash is not divided by preceding reduction",
        "sweep_rows": len(sweep_rows), "sampled_design_candidates": best, "stair_reach": stair_counts, "workspace": ws,
        "assumptions": ["Total mass includes both phones and all four complete leg mass estimates.", "Sweep masses change body payload while moving-link masses stay fixed; no CAD mass prediction.", "Foot support uses equal load sharing then stated dynamic multiplier. Link gravity is subtracted once because total mass already includes it.", "Sweep checks all four sign combinations of radial and tangential force, each 25% normal. Nominal CSV shows positive forces only. Unequal COM sharing requires contact dynamics.", "Linear voltage and torque-speed scaling, efficiency, backlash, stiffness, continuous/peak ratings and controller response are unmeasured.", "The speed estimate is a local kinematic upper bound at a fixed force. It omits acceleration, reflected servo inertia, control lag, drive/brake reaction moments and impact.", "Stair screen only checks paired endpoint inverse kinematics and motor travel. It does not check a continuous collision-free path, body clearance, tread placement, tipping, stair edge contact, or actuator loads during traversal.", "Workspace extrema contain geometrically reachable samples which may collide with body or another leg.", "Motor span is centered at a calibrated home, per shared parameters; whole joint box cannot be obtained at arbitrary high ratios in single-turn position mode."]}
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(out, summary, nominal_rows)
    return summary


def write_report(out, summary, rows):
    text = ["# MIST leg engineering screen", "", "These results size a candidate mechanism. They do not establish that a robot can climb stairs or sustain the calculated loads.", "",
        f"The shared mass estimate totals **{summary['estimated_total_mass_kg']:.3f} kg**, including both phones and four wheel motors. The selected 140/130 mm leg has nominal hip and knee angles {summary['nominal_joint_deg'][1]:.2f} and {summary['nominal_joint_deg'][2]:.2f} degrees.", "",
        "For the preferred proximal reduction and 1:1 remote belt, motor angles are `u = [ry*yaw, rh*hip, rk*(hip+knee)]`. Virtual work gives `tau_motor = [tau_yaw/ry, (tau_hip-tau_knee)/rh, tau_knee/rk]` before losses. An unequal remote pulley instead gives `u_k=hip+rk*knee`, and changes the proximal torque subtraction to `tau_hip-tau_knee/rk`. These equations must match the actual belt routing.", "",
        "## Shared nominal posture at 2:1", "", "The following rows include moving-leg gravity and vertical support force. Utilization greater than 1 exceeds the stated sizing allowance. Speed is a local upper estimate, even where the continuous limit fails.", "",
        "| Supply | Load case | Hip motor Nm | Knee motor Nm | Continuous utilization | Peak utilization | Radial speed m/s |", "|---|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        if row["mode"] == "absolute_tibia" and row["horizontal_force_each_fraction"] == 0:
            text.append(f"| {row['voltage_v']:.1f} V | {row['case']} | {row['hip_motor_nm']:.3f} | {row['knee_motor_nm']:.3f} | {row['continuous_utilization']:.2f} | {row['peak_utilization']:.2f} | {row['loaded_radial_speed_m_s']:.3f} |")
    text += ["", "## Ratio and length trade", "", "The sweep checks three normalized postures, three-contact static support, and two-contact support with a 1.5 normal-force multiplier and off-axis loading. Reductions span 1:1 to 3:1 independently on all three channels. A passing row covers those samples only. Shorter links in this comparison have lower body clearance.", "", "| Links mm | Supply | Ratios yaw/hip/knee | Sampled load pass | Peak utilization | Crawl continuous utilization | Minimum radial speed m/s |", "|---|---|---|---|---:|---:|---:|"]
    for row in summary["sampled_design_candidates"]:
        text.append(f"| {row['femur_mm']:.0f}/{row['tibia_mm']:.0f} | {row['voltage_v']:.1f} V | {row['ratio_yaw']:g}/{row['ratio_hip']:g}/{row['ratio_knee']:g} | {row['passes_sampled_peak_and_crawl_loads']} | {row['worst_peak_utilization']:.2f} | {row['crawl_continuous_utilization']:.2f} | {row['minimum_loaded_radial_speed_m_s']:.3f} |")
    mass_row = next(r for r in summary["sampled_design_candidates"] if r["femur_mm"] == 140 and r["voltage_v"] == 9.9)
    text += ["", f"For 140/130 mm links at 9.9 V, the selected best torque case within this sweep reaches its modeled peak allowance at {mass_row['maximum_mass_peak_kg']:.3f} kg. That is a boundary with no extra margin. Reducing body mass changes this limit while the model holds moving-link masses fixed. The current estimated mass exceeds it. The CSV includes each ratio's exact mass envelope.", "", "## Stair geometry and error budget", "", "The stair screen assumes 180 mm rise, 270 mm tread, and the shared wheel radius. It searches hip heights from 120 to 320 mm above the lower floor and pitch-axis reaches from 40 to 150 mm. A pair of reachable endpoints says nothing about tread placement or stability.", ""]
    for row in summary["stair_reach"]:
        text.append(f"- {row['femur_mm']:.0f}/{row['tibia_mm']:.0f} mm: {row['both_reachable_with_motor_travel']} of {row['tested_configurations']} sampled pairs reach both heights within joint and servo travel, and {row['with_toe_clearance']} also allow the requested toe clearance at the same radial coordinate.")
    nom = next(r for r in rows if r["mode"] == "absolute_tibia" and r["voltage_v"] == 9.9 and r["case"] == "pair_dynamic_1p5" and r["horizontal_force_each_fraction"] == 0)
    text += ["", f"At the nominal pose, the backlash-only corner bound is {nom['backlash_corner_bound_mm']:.2f} mm. Shared full-width servo backlash is divided by the external reduction, then combined with downstream backlash at its own output. The assumed stiffness adds {nom['assumed_elastic_error_mm']:.2f} mm of load-dependent endpoint deflection in the two-contact dynamic load case. These are separate terms; fabrication error, bearing clearance, belt tension, printed part flex, deadband and tracking error are not included in the backlash number.", "", "A yaw axis about vertical has zero torque from a purely vertical endpoint force. Tangential contact force, steering scrub, drive reaction and inertia create yaw demand. The nominal CSV includes an off-axis load case so yaw is not sized from gravity alone.", "", "## Limits and next measurements", ""]
    text += ["- " + item for item in summary["assumptions"]]
    text += ["", "Measure loaded servo speed, temperature and current over the intended duty cycle; full reversal backlash; force-versus-deflection of the complete leg; actual component masses; wheel traction and motor current; physical travel and body interference. Re-run the shared parameter file after the coupon and bench measurements.", "", "Reproduce with `python analytic.py`; run `python -m unittest discover -s . -p 'test_*.py'` from this directory. The CSV files preserve every load case and sweep row. `summary.json` records the exact shared parameter SHA-256.", ""]
    (out / "REPORT.md").write_text("\n".join(text), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters", type=Path, default=Path(__file__).resolve().parent.parent / "parameters.json")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "results")
    args = parser.parse_args()
    result = run(json.loads(args.parameters.read_text(encoding="utf-8-sig")), args.output, args.parameters)
    print(json.dumps({k: result[k] for k in ("estimated_total_mass_kg", "nominal_joint_deg", "sweep_rows", "sampled_design_candidates", "stair_reach")}, indent=2))
