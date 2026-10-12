"""Static geometry audit for support transfer; this executes no physics.

The hard gate covers nominal steady geometry, numerical optimizer residuals,
periodic C2 support-reference continuity and IK validity. Startup/attitude
stress and servo demand are reported separately, with the paired reference.
This audit does not alter acceptance or predict measured saturation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO), str(HERE)]
import numpy as np
from dev_support_transfer_probe import check_prior, experiment_hashes, COMMANDS
from dev_tracking_probe import json_scalar
from experimental_stride_gain import TranslationGainClearanceCrawl
from experimental_support_transfer import (PlannedSupportTransferCrawl, periodic_basis,
    load_diagnostics, attitude_correction, feet_from_angles)
from locomotion.acceptance import COMMANDS as COMMAND_VALUES
from locomotion.kinematics import LIMITS, inverse
from locomotion.gait import rz
from locomotion.model import LEGS, MOUNTS, load_config
from locomotion.provenance import source_hashes, check_sources


def triangle_loads(points, phases, weight):
    moving = np.flatnonzero(np.asarray(phases) >= .8)
    if not len(moving):
        return []
    stance = [index for index in range(4) if index != moving[0]]
    matrix = np.vstack([np.ones(3), points[stance, 0], points[stance, 1]])
    return np.linalg.solve(matrix, [weight, 0., 0.])


def continuity_error(gait, command):
    coefficients = gait.plan(command)["coefficients_mm"]*.001
    errors = np.zeros(3)
    for knot in np.arange(32)/32.:
        for derivative in range(3):
            left = coefficients@periodic_basis(knot-1e-10, derivative)/gait.cycle_s**derivative
            right = coefficients@periodic_basis(knot+1e-10, derivative)/gait.cycle_s**derivative
            errors[derivative] = max(errors[derivative], np.max(np.abs(right-left)))
    return errors


def demand(gait, command, payload):
    times = np.arange(481)*.02
    geometric = np.array([gait.targets(t, command, [0., 0.]) for t in times])
    biased = np.array([gait.position_targets(t, command, [0., 0.], payload) for t in times])
    geometric_rate = np.abs(np.diff(geometric, axis=0))/.02
    biased_rate = np.abs(np.diff(biased, axis=0))/.02
    speed = load_config()["actuator"]["command_speed_rad_s"]
    return {"control_hz": 50, "window_s": [0., 9.6],
            "max_geometric_increment_rad": float(np.max(geometric_rate)*.02),
            "max_biased_increment_rad": float(np.max(biased_rate)*.02),
            "max_geometric_rate_rad_s": float(np.max(geometric_rate)),
            "max_biased_rate_rad_s": float(np.max(biased_rate)),
            "biased_increment_above_nominal_slew_fraction": float(np.mean(biased_rate > speed)),
            "nominal_command_slew_rad_s": speed,
            "max_geometric_rate_by_joint_rad_s": np.max(geometric_rate.reshape(-1, 4, 3), axis=(0, 1)),
            "max_biased_rate_by_joint_rad_s": np.max(biased_rate.reshape(-1, 4, 3), axis=(0, 1))}


def audit_case(name, payload, samples):
    command = COMMAND_VALUES[name]
    gait = PlannedSupportTransferCrawl(phone_mass_kg=payload)
    reference = TranslationGainClearanceCrawl(shift_m=.005, translational_stride_gain=1.15)
    phase_grid = (np.arange(samples)+.1732050807568877)/samples
    weight = (gait.model_mass_without_phone+payload)*9.81
    min_triangle = np.inf
    min_raw = np.inf
    max_raw_moment = 0.
    max_clipped_moment = 0.
    min_joint_margin = np.inf
    shift, velocity, acceleration = [], [], []
    for phase in phase_grid:
        time_s = 6.4+phase*gait.cycle_s
        q = gait.targets(time_s, command, [0., 0.])
        diagnostics = load_diagnostics(gait, time_s, command, q, payload)
        points = diagnostics["geometric_body_feet_m"]
        phases = [(phase-gait.offset[leg]) % 1. for leg in LEGS]
        forces = triangle_loads(points, phases, weight)
        if len(forces):
            min_triangle = min(min_triangle, float(np.min(forces)))
        min_raw = min(min_raw, float(np.min(diagnostics["raw_support_force_n"])))
        max_raw_moment = max(max_raw_moment, float(np.max(np.abs(diagnostics["raw_moment_nm"]))))
        max_clipped_moment = max(max_clipped_moment, float(np.max(np.abs(diagnostics["clipped_moment_nm"]))))
        q4 = q.reshape(4, 3)
        min_joint_margin = min(min_joint_margin, float(np.min(np.minimum(q4-LIMITS[:, 0], LIMITS[:, 1]-q4))))
        planned = gait.reference(time_s, command)
        shift.append(planned["shift_m"])
        velocity.append(planned["shift_velocity_m_s"])
        acceleration.append(planned["shift_acceleration_m_s2"])
    continuous = continuity_error(gait, command)
    stress = []
    # This smaller independent grid is a sensitivity check, not a guarantee
    # over the inherited +/- .25 rad attitude-compensation range.
    for roll, pitch in ((0., 0.), (.05, 0.), (-.05, 0.), (0., .05), (0., -.05),
                        (.05, .05), (.05, -.05), (-.05, .05), (-.05, -.05)):
        minima = {"planned": np.inf, "reference": np.inf}
        for phase in (np.arange(128)+.6180339887498949)/128.:
            t = 6.4+phase*gait.cycle_s
            for label, controller in (("planned", gait), ("reference", reference)):
                q = controller.targets(t, command, [roll, pitch])
                raw = load_diagnostics(controller, t, command, q, payload)["raw_support_force_n"]
                minima[label] = min(minima[label], float(np.min(raw)))
        stress.append({"attitude_rad": [roll, pitch], "minimum_raw_force_n": minima})
    ramp_stress = []
    for ramp in (0., .25, .5, .75, 1.):
        min_force = np.inf
        for phase in (np.arange(128)+.6180339887498949)/128.:
            unshifted = gait.unshifted_points(phase, command, ramp)
            shift_r = ramp*gait.plan(command)["coefficients_mm"]@periodic_basis(phase)*.001
            points = unshifted-np.r_[shift_r, 0.]
            phases = [(phase-gait.offset[leg]) % 1. for leg in LEGS]
            forces = triangle_loads(points, phases, weight)
            if len(forces):
                min_force = min(min_force, float(np.min(forces)))
            # Validate startup workspace without modifying controller time.
            for leg, point in zip(LEGS, points):
                inverse(rz(MOUNTS[leg]["yaw"]).T@(point-np.asarray(MOUNTS[leg]["xyz"])))
        ramp_stress.append({"ramp": ramp, "minimum_three_stance_load_n": min_force})
    planned_demand = demand(gait, command, payload)
    reference_demand = demand(reference, command, payload)
    gates = {"independent_triangle_margin": min_triangle >= .1-2e-6,
             "independent_raw_load_nonnegative": min_raw >= -2e-6,
             "raw_moment_balance": max_raw_moment < 1e-9,
             "clipped_moment_balance": max_clipped_moment < 1e-9,
             "IK_inside_original_limits": min_joint_margin > .002,
             "periodic_reference_C2": bool(np.all(continuous < [1e-9, 1e-8, 1e-6]))}
    return {"command": name, "payload_kg": payload, "nominal_gate_passed": all(gates.values()), "gates": gates,
            "independent_phase_samples": samples, "solver": gait.plan(command)["solver"],
            "coefficients_mm": gait.plan(command)["coefficients_mm"],
            "minimum_three_stance_load_n": min_triangle, "minimum_raw_scheduled_force_n": min_raw,
            "maximum_raw_moment_nm": max_raw_moment, "maximum_clipped_moment_nm": max_clipped_moment,
            "minimum_geometric_joint_limit_margin_rad": min_joint_margin,
            "maximum_C2_two_sided_difference": continuous,
            "peak_shift_m": float(np.max(np.linalg.norm(shift, axis=1))),
            "rms_shift_velocity_m_s": float(np.sqrt(np.mean(np.sum(np.asarray(velocity)**2, axis=1)))),
            "peak_shift_velocity_m_s": float(np.max(np.linalg.norm(velocity, axis=1))),
            "peak_shift_acceleration_m_s2": float(np.max(np.linalg.norm(acceleration, axis=1))),
            "attitude_sensitivity_not_a_gate": stress,
            "ramp_sensitivity_not_a_gate": ramp_stress,
            "50hz_demand": {"planned": planned_demand, "reference": reference_demand},
            "limitations": ["Nominal centred COM, no measured load/velocity input.",
                            "Existing attitude compensation can invalidate nominal support feasibility.",
                            "Inherited linear startup ramp has a derivative corner at 1.5 s; C2 applies to the periodic reference.",
                            "Foot recovery remains inherited C1; the full joint path is not claimed C2.",
                            "Servo saturation and actual contact require the paired physics receipt."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", nargs="+", choices=COMMANDS, default=list(COMMANDS))
    parser.add_argument("--payloads", nargs="+", type=float, default=[0., .155])
    parser.add_argument("--samples", type=int, default=2048)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 1024 or any(not 0. <= mass <= .4 for mass in args.payloads):
        parser.error("Audit requires >=1024 phases and payloads within [0,.4]")
    check_prior()
    hashes, sources = experiment_hashes(), source_hashes()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        record = {"schema": 1, "suite_role": "static_support_transfer_audit_no_physics",
                  "experiment_hashes": hashes, "source_hashes": sources, "status": "running", "results": []}
        def save():
            output.seek(0)
            output.write(json.dumps(record, indent=2, allow_nan=False, default=json_scalar)+"\n")
            output.truncate()
            output.flush()
        save()
        try:
            for payload in args.payloads:
                for name in args.commands:
                    row = audit_case(name, payload, args.samples)
                    record["results"].append(row)
                    save()
                    print(name, payload, "NOMINAL_STATIC_PASS" if row["nominal_gate_passed"] else "NOMINAL_STATIC_FAIL",
                          "shift", row["peak_shift_m"], "stance_min", row["minimum_three_stance_load_n"],
                          "50Hz_biased_rate", row["50hz_demand"]["planned"]["max_biased_rate_rad_s"], flush=True)
            check_prior()
            check_sources(sources)
            if experiment_hashes() != hashes:
                raise RuntimeError("Experimental files changed during static audit")
            record["status"] = "complete" if all(row["nominal_gate_passed"] for row in record["results"]) else "static_gate_failed"
            save()
        except BaseException as error:
            record["status"], record["error"] = "interrupted_or_failed", f"{type(error).__name__}: {error}"
            save()
            raise
    if record["status"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
