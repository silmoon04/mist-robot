"""Validate a frozen full concealed-wheel CAD inventory before any optional gait."""
import argparse
import copy
import hashlib
import importlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
POLICY = {"minimum_fixture_continuous_reserve_fraction": .20, "fixture_max_foot_error_m": .010,
          "require_zero_hold_saturation": True, "require_zero_travel_violation": True,
          "require_stand_and_drive_pass": True,
          "meaning": "Predeclared conservative simulation dispatch screen, not a measured thermal or reliability guarantee."}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def verify_actuator_contract(parameters):
    contract = json.loads((HERE / "protected_actuator_contract.json").read_text(encoding="utf-8"))
    for section, fields in contract["protected"].items():
        for field, expected in fields.items():
            if parameters.get(section, {}).get(field) != expected:
                raise ValueError(f"Protected actuator/control assumption changed: {section}.{field}")
    if "motor_travel_reference_joint_deg" in parameters["transmission"] or "joint_limits_by_leg_deg" in parameters["geometry"]:
        raise ValueError("Hypothesis-only commissioning fields cannot replace the actual2:1 baseline contract")


def basic_preflight(report_path):
    raw = report_path.read_bytes()
    report = json.loads(raw)
    names = {"FL", "FR", "RL", "RR"}
    if set(report.get("specifications", {})) != names | {"body"}:
        raise ValueError("Need the completed four-leg plus body report; a single-leg export is insufficient")
    if not report.get("exports_complete") or report.get("shape_checks"):
        raise ValueError("The full export must complete and have no shape failures")
    interference = report["interference"]
    if interference["positive_volume_interferences"] or interference["boolean_failures"]:
        raise ValueError("The frozen CAD report still has positive-volume interference or failed Boolean checks")
    expected_units = {"mass": "kg", "com": "m", "inertia": "kg m^2", "cad_transforms": "mm"}
    if report["physical_mass_properties"]["units"] != expected_units:
        raise ValueError("Unexpected mass, COM, inertia or CAD-transform units")
    source_path = Path(report["parameters_path"])
    parameter_bytes = source_path.read_bytes()
    if hashlib.sha256(parameter_bytes).hexdigest() != report.get("parameters_sha256"):
        raise ValueError("Frozen report parameter bytes changed or their recorded SHA does not match")
    parameters = json.loads(parameter_bytes)
    verify_actuator_contract(parameters)
    geometry = parameters["geometry"]
    if not math.isclose(geometry["femur_m"], .1395, abs_tol=1e-12) or not math.isclose(geometry["tibia_m"], .140, abs_tol=1e-12):
        raise ValueError("This check requires the new 139.5mm femur and 140mm tibia geometry")
    if parameters["transmission"]["ratios"] != [2, 2, 2]:
        raise ValueError("CAD and simulation must retain the actual 2:1 joint reductions")
    if parameters["simulation"]["physics_hz"] != 1000:
        raise ValueError("The bounded validation contract is frozen at 1000Hz")
    transmission = parameters["wheel_transmission"]
    if transmission["topology"] != "longitudinal_upper_tibia_shaft_miter_1to1" or transmission["ratio"] != 1:
        raise ValueError("Unexpected concealed wheel transmission")
    for name in names:
        if report["specifications"][name]["topology"] != "proximal_femur_relative_knee":
            raise ValueError("The motor housing reaction frame differs from the modeled femur-relative knee")
        drive = report["specifications"][name]["wheel_drive"]
        if drive["topology"] != transmission["topology"] or drive["tibia_mm"] != 140 or drive["declared_ratio"] != 1:
            raise ValueError("Per-leg wheel-drive contract differs from parameter geometry")
        if drive["motor_case_u_mm"] != [20, 81]:
            raise ValueError("Expected the declared upper-tibia motor case from20 to81mm")
    return report, parameters, {"report_sha256": hashlib.sha256(raw).hexdigest(),
                                "source_parameters_sha256": hashlib.sha256(parameter_bytes).hexdigest(),
                                "report_path": str(report_path.resolve()), "source_parameters_path": str(source_path.resolve())}, raw, parameter_bytes


def freeze_runtime(destination):
    runtime = destination / "runtime_snapshot"
    runtime.mkdir(parents=True)
    files = {name: SIM / name for name in ["model.py", "run_sim.py", "load_test.py", "reconcile_proximal_cad.py"]}
    files["concealed_fixture.py"] = HERE / "concealed_fixture.py"
    files["supported_crawl.py"] = SIM / "proximal_gait_20260907/supported_crawl.py"
    files["validate_concealed.py"] = Path(__file__)
    files["commissioning_offsets.py"] = HERE / "commissioning_offsets.py"
    hashes = {}
    for name, source in files.items():
        raw = source.read_bytes()
        (runtime / name).write_bytes(raw)
        hashes[name] = {"source_path": str(source), "original_sha256": hashlib.sha256(raw).hexdigest()}
    geometry = runtime / "geometry_study"
    geometry.mkdir()
    source = SIM / "proximal_gait_20260907/geometry_study/geometry_study.py"
    geometry_raw = source.read_bytes()
    (geometry / "geometry_study.py").write_bytes(geometry_raw)
    (geometry / "__init__.py").write_text("", encoding="utf-8")
    hashes["geometry_study/geometry_study.py"] = {"source_path": str(source), "original_sha256": hashlib.sha256(geometry_raw).hexdigest()}
    hashes["geometry_study/__init__.py"] = {"source_path": "generated empty package initializer", "original_sha256": hashlib.sha256(b"").hexdigest()}
    contract = HERE / "protected_actuator_contract.json"
    (destination / contract.name).write_bytes(contract.read_bytes())
    controller_path = SIM / "proximal_gait_20260907/matched_cad_60mm_4s_3cycles/controller.json"
    controller_raw = controller_path.read_bytes()
    (destination / "slow_controller_snapshot.json").write_bytes(controller_raw)
    write_json(destination / "controller_source.json", {"path": str(controller_path), "sha256": hashlib.sha256(controller_raw).hexdigest()})
    references = destination / "reference_snapshots"
    references.mkdir()
    reference_hashes = {}
    for name in ["first_leg_candidate.json", "first_rear_pitch_5.0deg.json", "parameters_snapshot.json", "pitch_search.py"]:
        source = SIM / "stair_feasibility_20260907" / name
        raw = source.read_bytes()
        (references / name).write_bytes(raw)
        reference_hashes[name] = {"source": str(source), "sha256": hashlib.sha256(raw).hexdigest()}
    write_json(destination / "reference_sources.json", reference_hashes)
    # Correct only the copied diagnostic: inertia principal axes are not link axes.
    path = runtime / "run_sim.py"
    code = path.read_text(encoding="utf-8")
    old = 'axis=np.array(pb.getMatrixFromQuaternion(state[1])).reshape(3,3) @ axis_local\n                lateral.append(float(np.dot(state[6],axis)))'
    new = 'axis=np.array(pb.getMatrixFromQuaternion(state[5])).reshape(3,3) @ axis_local\n                axle_velocity=np.array(state[6])+np.cross(np.array(state[7]),np.array(state[4])-np.array(state[0]))\n                lateral.append(float(np.dot(axle_velocity,axis)))'
    if old not in code:
        raise ValueError("Shared wheel diagnostic changed; review this narrow frozen-runtime patch")
    code = code.replace(old, new)
    old = 'self.s0=(self.A @ q0.T).T'
    new = '''self.s0=(self.A @ q0.T).T
        self.travel_reference=self.s0.copy()
        if "motor_travel_reference_joint_deg" in p["transmission"]:
            reference=np.radians(p["transmission"]["motor_travel_reference_joint_deg"])
            if reference.shape!=(4,3) or not np.all(np.isfinite(reference)):
                raise ValueError("Need four explicit three-axis commissioning references")
            self.travel_reference=(self.A @ reference.T).T'''
    if old not in code or 'delta=np.degrees(s-self.s0)' not in code:
        raise ValueError("Servo travel implementation changed; review commissioning-reference support")
    code = code.replace(old, new).replace('delta=np.degrees(s-self.s0)', 'delta=np.degrees(s-self.travel_reference)')
    path.write_text(code, encoding="utf-8")
    path = runtime / "model.py"
    code = path.read_text(encoding="utf-8")
    old_ik = 'limits = np.radians(g["joint_limits_deg"])'
    old_urdf = 'limits=np.radians(g["joint_limits_deg"])'
    if code.count(old_ik) != 1 or code.count(old_urdf) != 1:
        raise ValueError("Joint-limit implementation changed; review per-leg output corridors")
    code = code.replace(old_ik, 'limits = np.radians(g.get("joint_limits_by_leg_deg",{}).get(g["leg_names"][leg],g["joint_limits_deg"]))')
    code = code.replace(old_urdf, 'limits=np.radians(g.get("joint_limits_by_leg_deg",{}).get(name,g["joint_limits_deg"]))')
    path.write_text(code, encoding="utf-8")
    for name, value in hashes.items():
        value["executed_sha256"] = hashlib.sha256((runtime / name).read_bytes()).hexdigest()
    write_json(destination / "frozen_extra_inputs.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [destination / contract.name, destination / "slow_controller_snapshot.json"]})
    write_json(destination / "runtime_sources.json", {"sources": hashes, "local_patches": [
        "Wheel slip diagnostics use link orientation and axle velocity; no solver/control change.",
        "Optional explicit per-joint commissioning travel references and per-leg output limits; absent in the actual2:1 baseline."]})
    (destination / "validate_concealed.py").write_bytes(Path(__file__).read_bytes())
    return runtime, hashes


def verify_frames(report, parameters, model):
    import numpy as np
    maximum = 0.
    if not np.allclose(report["link_mass_properties"]["base_link"]["frame_local_to_world_mm"], np.eye(4), atol=1e-9):
        raise ValueError("Base inertial allocation must use the body hip-plane frame")
    for index, name in enumerate(parameters["geometry"]["leg_names"]):
        spec = report["specifications"][name]
        pose = spec["pose_deg"]
        q = np.radians([pose["yaw"], pose["hip"], pose["knee"]])
        f = model.fk(parameters, index, q)
        centers = dict(yaw=f["hip"], hip=f["pitch"], knee=f["knee"], wheel=f["axle"])
        for label, expected in centers.items():
            error = float(np.linalg.norm(np.array(spec["joint_centers_world_mm"][label]) / 1000 - expected))
            maximum = max(maximum, error)
            if error > 1e-8:
                raise ValueError(f"CAD/URDF joint centre differs for{name}/{label}: {error}m")
        for label in ["yaw", "femur", "tibia", "wheel"]:
            frame = np.array(spec["frames_world_mm"][label])
            origins = {"yaw": f["hip"], "femur": f["pitch"], "tibia": f["knee"], "wheel": f["axle"]}
            if not np.allclose(frame[:3, 3] / 1000, origins[label], atol=1e-9):
                raise ValueError(f"CAD/URDF frame origin differs for {name}/{label}")
            if not np.allclose(frame[3], [0, 0, 0, 1], atol=1e-12):
                raise ValueError("Invalid homogeneous CAD frame")
            angle = 0 if label == "yaw" else q[1] if label == "femur" else q[1] + q[2]
            c, s = np.cos(angle), np.sin(angle)
            ry = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])
            expected_rotation = model.rotation_z(f["heading"]) @ ry
            if not np.allclose(frame[:3, :3], expected_rotation, atol=1e-9):
                raise ValueError(f"CAD/URDF rotation differs for{name}/{label}")
            inertial_frame = np.array(report["link_mass_properties"][name + "_" + label]["frame_local_to_world_mm"])
            if not np.allclose(frame, inertial_frame, atol=1e-8):
                raise ValueError("Allocated inertia frame differs from the exported rigid-link frame")
    return {"max_joint_centre_difference_m": maximum, "link_rotations_and_inertial_frames_match": True}


def effective_wheel_parameters(parameters):
    p = copy.deepcopy(parameters)
    if "wheel_axis_envelope_derivation" in p:
        raise ValueError("Refusing to apply wheel transmission efficiency twice")
    original = copy.deepcopy(p["wheel_motor"])
    ratio = p["wheel_transmission"]["ratio"]
    efficiency = p["wheel_transmission"]["efficiency_assumption"]
    if not 0 < efficiency <= 1 or ratio <= 0:
        raise ValueError("Invalid wheel transmission assumptions")
    p["wheel_motor"]["stall_torque_nm"] *= ratio * efficiency
    p["wheel_motor"]["no_load_speed_rpm"] /= ratio
    p["wheel_motor"]["provenance"] += " Simulation fields converted to wheel-axis torque/speed through the declared transmission; original motor fields preserved in wheel_axis_envelope_derivation."
    p["wheel_axis_envelope_derivation"] = {"original_motor_parameters": original, "ratio": ratio, "efficiency_assumption": efficiency,
        "mapping": "wheel torque=eta*ratio*motor torque; wheel speed=motor speed/ratio; electrical current fields unchanged",
        "limitations": "Assumed efficiency and four-quadrant loss approximation. Shaft/input-gear spin inertia and gyroscopic coupling omitted; housing/link pose inertia retained."}
    return p


def gait_gate(stand, drive, fixture):
    checks = {"stand_pass": stand["status"] == "PASS_IN_MODEL", "drive_pass": drive["status"] == "PASS_IN_MODEL",
              "fixture_pass": fixture["status"] == "PASS_IN_MODEL",
              "fixture_torque_reserve_at_least_20pct": fixture["continuous_torque_reserve_fraction"] >= POLICY["minimum_fixture_continuous_reserve_fraction"],
              "fixture_error_at_most_10mm": fixture["hold_max_foot_error_m"] <= POLICY["fixture_max_foot_error_m"],
              "no_fixture_hold_saturation": fixture["active_hold_saturated_steps"] == 0,
              "no_fixture_travel_violation": fixture["active_all_run_travel_violations"] == 0}
    return {"allowed": all(checks.values()), "checks": checks, "policy": POLICY}


def frozen_import(name, runtime):
    module = importlib.import_module(name)
    expected = runtime / (name.replace(".", "/") + ".py")
    if Path(module.__file__).resolve() != expected.resolve():
        raise RuntimeError("Import did not use the frozen runtime: " + name)
    if name == "model" and module.ROOT.resolve() != runtime.resolve():
        raise RuntimeError("Frozen model ROOT mismatch")
    return module


def verify_frozen_inputs(runtime, source_hashes, report_path, provenance):
    for name, hashes in source_hashes.items():
        if hashlib.sha256((runtime / name).read_bytes()).hexdigest() != hashes["executed_sha256"]:
            raise RuntimeError("Frozen runtime changed during execution: " + name)
    if hashlib.sha256(report_path.read_bytes()).hexdigest() != provenance["report_sha256"]:
        raise RuntimeError("CAD report changed during execution")
    if hashlib.sha256(Path(provenance["source_parameters_path"]).read_bytes()).hexdigest() != provenance["source_parameters_sha256"]:
        raise RuntimeError("CAD parameter source changed during execution")
    extra = json.loads((runtime.parent / "frozen_extra_inputs.json").read_text(encoding="utf-8"))
    for name, expected in extra.items():
        if hashlib.sha256((runtime.parent / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Frozen controller/contract changed during execution: " + name)
    references = json.loads((runtime.parent / "reference_sources.json").read_text(encoding="utf-8"))
    for name, metadata in references.items():
        if hashlib.sha256((runtime.parent / "reference_snapshots" / name).read_bytes()).hexdigest() != metadata["sha256"]:
            raise RuntimeError("Frozen commissioning reference changed during execution: " + name)


def hypothetical_gearing(parameters, model, geometry_helper, fixture_module, output, baseline_fixture, commissioning_module):
    import numpy as np
    output.mkdir()
    p = copy.deepcopy(parameters)
    q0 = model.neutral(p)
    original_limits = np.array(p["geometry"]["joint_limits_deg"], float)
    motor_limits = np.array(p["transmission"]["motor_travel_limits_deg"], float)
    ratios = np.array([2., 3., 3.])
    p["transmission"]["ratios"] = ratios.tolist()
    p["transmission"]["motor_coordinate_equation"] = "s=[2*yaw,3*hip,3*knee]; hypothetical gearing only"
    p["status"] = "hypothetical_3to1_hip_knee_with_original_shaft_span_not_fitted_CAD"
    radius = p["geometry"]["wheel_diameter_m"] / 2
    feet = np.array([model.fk(p, i, q0[i])["axle"] for i in range(4)])
    feet[:, 2] = radius
    body_height = p["geometry"]["hip_to_wheel_axle_height_m"] + radius + .001 + .01
    prior_body = np.array([0, 0, body_height])
    samples = []
    for step, active in enumerate([2, 0, 3, 1]):
        stance = [i for i in range(4) if i != active]
        nominal_com = np.array([.06 * step / 4, 0]) + geometry_helper.com(p, q0)[:2]
        desired_com = geometry_helper.closest_inset(feet[stance], nominal_com, .03)
        start_body, start_q, start_ok = geometry_helper.body_for_com(p, feet, prior_body[:2], body_height, desired_com)
        for u in np.linspace(0, 1, 21):
            body = prior_body * (1 - u) + start_body * u
            q, ok = geometry_helper.joint_pose(p, feet, body)
            samples.append((step, "shift", u, q, ok))
        for u in np.linspace(0, 1, 41):
            local_feet = feet.copy()
            local_feet[active] += [.06 * u * u * (3 - 2 * u), 0, .04 * np.sin(np.pi * u) ** 2]
            body, q, ok = geometry_helper.body_for_com(p, local_feet, start_body[:2], body_height, desired_com)
            samples.append((step, "swing", u, q, ok))
        prior_body = body.copy()
        feet[active, 0] += .06
    reference_dir = output.parent / "reference_snapshots"
    fixture_q = np.array([item["all_joint_angles_rad"] for item in baseline_fixture["history"]])
    flat_q = np.array([sample[3] for sample in samples])
    commissioning = commissioning_module.analyze_commissioning(
        p, model, reference_dir / "first_leg_candidate.json", reference_dir / "first_rear_pitch_5.0deg.json",
        reference_dir / "parameters_snapshot.json", fixture_q_rad=fixture_q, flat_q_rad=flat_q,
        reproject_old_targets=True, ratios=(2, 3, 3))
    write_json(output / "commissioning_offsets.json", commissioning)
    selected = commissioning["reprojected_world_target_assessment"]
    reference = np.array(selected["travel_reference_q_rad"])
    restricted = np.array(selected["per_leg_output_limits_deg"])
    p["transmission"]["motor_travel_reference_joint_deg"] = np.degrees(reference).tolist()
    p["geometry"]["joint_limits_by_leg_deg"] = {name: restricted[i].tolist() for i, name in enumerate(p["geometry"]["leg_names"])}
    p["hypothetical_gearing"] = {"actual_CAD_ratios": parameters["transmission"]["ratios"],
        "hypothetical_ratios": ratios.tolist(), "motor_travel_limits_deg_unchanged": motor_limits.tolist(),
        "original_geometry_limits_deg": original_limits.tolist(), "restricted_output_limits_by_leg_deg": restricted.tolist(),
        "commissioning_reference_joint_deg": np.degrees(reference).tolist(),
        "commissioning_choice": "One proposed static center per physical joint across oldworld targets reprojected to current geometry, currentfixture, neutral and flat reference. Old exact-angle assessment is preserved separately.",
        "commissioning_validated": False,
        "mass_and_tensor_assumption": "Existing2:1 CAD inertials retained; new3:1 gear mass and clearance have not been designed.",
        "efficiency_assumption": "Existing efficiency/stiffness/backlash retained solely for sensitivity; extra stages or larger gears are not validated."}
    write_json(output / "parameters_hypothetical.json", p)
    model.build_urdf(p, output / "hypothetical_candidate.urdf")
    travel = np.array([np.degrees((ratios * (q - reference))) for _, _, _, q, _ in samples])
    within = np.all((travel >= motor_limits[:, 0]) & (travel <= motor_limits[:, 1]), axis=(1, 2))
    output_within = np.all((np.degrees(flat_q) >= restricted[:, :, 0]) & (np.degrees(flat_q) <= restricted[:, :, 1]), axis=(1, 2))
    motor_speed = p["servo"]["no_load_speed_rpm"] * p["servo"]["simulation_voltage_v"] / p["servo"]["nominal_voltage_v"]
    rom = {"status": "KINEMATIC_CORRIDOR_FOUND" if all(s[4] for s in samples) and bool(np.all(within)) and bool(np.all(output_within)) else "NO_CORRIDOR_FOR_SAMPLED_REFERENCE",
           "reference": "One ideal60mm/40mmlift cycle with30mm COM inset; no dynamic feedback, collision or stair validation",
           "sample_count": len(samples), "all_ik_reachable": all(s[4] for s in samples),
           "all_shaft_targets_inside_original_span": bool(np.all(within)),
           "all_targets_inside_per_leg_physical_corridor": bool(np.all(output_within)),
           "shaft_travel_min_deg": travel.min(axis=(0, 1)).tolist(), "shaft_travel_max_deg": travel.max(axis=(0, 1)).tolist(),
           "minimum_shaft_span_margin_deg": np.minimum(travel.min(axis=(0, 1)) - motor_limits[:, 0], motor_limits[:, 1] - travel.max(axis=(0, 1))).tolist(),
           "restricted_output_limits_by_leg_deg": restricted.tolist(), "no_load_output_speed_rpm": (motor_speed / ratios).tolist(),
           "samples": [{"step": step, "stage": stage, "phase": float(u), "q_rad": q.tolist(), "reachable": bool(ok)} for step, stage, u, q, ok in samples]}
    write_json(output / "rom_screen.json", rom)
    fixture = fixture_module.trial(p, output / "fixture")
    result = {"status": "hypothetical_gearing_screen_complete_not_CAD_release", "rom": {k: v for k, v in rom.items() if k != "samples"},
              "fixture": {k: v for k, v in fixture.items() if k not in ["history", "parameters_used"]},
              "torque_reserve_gate_pass": fixture["continuous_torque_reserve_fraction"] >= POLICY["minimum_fixture_continuous_reserve_fraction"],
              "actual_2to1_CAD_unchanged": True, "new_gears_manufactured_or_packaged": False}
    write_json(output / "summary.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--hypothetical-gearing-on-failure", action="store_true")
    args = parser.parse_args()
    output = HERE / args.name
    if output.exists():
        raise ValueError("Choose a new output name; existing evidence is not overwritten")
    report, original, provenance, report_raw, parameter_raw = basic_preflight(args.report.resolve())
    output.mkdir()
    write_json(output / "dispatch_policy.json", POLICY)
    (output / "cad_report_snapshot.json").write_bytes(report_raw)
    parameter_snapshot = output / "cad_parameters_snapshot.json"
    parameter_snapshot.write_bytes(parameter_raw)
    reconciliation_report = copy.deepcopy(report)
    reconciliation_report["parameters_path"] = str(parameter_snapshot.resolve())
    reconciliation_report_path = output / "cad_report_for_reconciliation.json"
    write_json(reconciliation_report_path, reconciliation_report)
    runtime, source_hashes = freeze_runtime(output)
    sys.path.insert(0, str(runtime))
    model = frozen_import("model", runtime)
    reconcile = frozen_import("reconcile_proximal_cad", runtime)
    frame_check = verify_frames(report, original, model)
    reconciled_path = reconcile.reconcile(reconciliation_report_path, output / "reconciled")
    parameters = effective_wheel_parameters(json.loads(reconciled_path.read_text(encoding="utf-8")))
    parameters["status"] = "concealed_wheel_CAD_inertials_and_derived_wheel_envelope_not_physical_release"
    parameters["cad_evidence"]["original_frozen_source"] = provenance
    write_json(output / "parameters_used.json", parameters)
    model.build_urdf(parameters, output / "MIST_concealed_inertials.urdf")
    write_json(output / "input_verification.json", {**provenance, **frame_check, "mass_kg": model.total_mass(parameters),
        "wheel_axis_envelope_derivation": parameters["wheel_axis_envelope_derivation"], "no_previous_mass_reused": True})
    if args.preflight_only:
        verify_frozen_inputs(runtime, source_hashes, args.report, provenance)
        print(json.dumps({"status": "preflight_passed", "mass_kg": model.total_mass(parameters)}))
        return
    run_sim = frozen_import("run_sim", runtime)
    fixture_module = frozen_import("concealed_fixture", runtime)
    reports = []
    errors = []
    try:
        for case in ["stand", "drive"]:
            result = run_sim.run_case(copy.deepcopy(parameters), case, output_root=output / "outputs")
            reports.append(result)
            print(json.dumps({k: result[k] for k in ["case", "status", "mass_kg", "max_servo_rms_nm", "base_displacement_m"]}), flush=True)
        fixture = fixture_module.trial(copy.deepcopy(parameters), output / "fixture")
    except Exception as exc:
        error = {"status": "PREREQUISITE_RUNTIME_ERROR", "error_type": type(exc).__name__, "message": str(exc), "completed_cases": [r["case"] for r in reports]}
        try:
            verify_frozen_inputs(runtime, source_hashes, args.report, provenance)
        except Exception as verification_error:
            error["evidence_verification_error"] = str(verification_error)
        write_json(output / "validation_summary.json", {"status": "prerequisite_runtime_error", "error": error, "stand_and_drive": reports, "gait_dispatch": {"allowed": False}, "input": provenance, "sources": source_hashes})
        raise
    decision = gait_gate(reports[0], reports[1], fixture)
    write_json(output / "gait_dispatch.json", decision)
    print(json.dumps({"fixture_status": fixture["status"], "hold_servo_rms_nm": fixture["hold_servo_rms_nm"], "hold_max_foot_error_m": fixture["hold_max_foot_error_m"], "gait_dispatch": decision}), flush=True)
    gait = None
    if decision["allowed"]:
        controller = json.loads((output / "slow_controller_snapshot.json").read_text())
        try:
            gait_module = frozen_import("supported_crawl", runtime)
            frozen_import("geometry_study.geometry_study", runtime)
            gait = gait_module.run(controller, copy.deepcopy(parameters), output / "slow_crawl")
            print(json.dumps({k: gait[k] for k in ["status", "mass_kg", "max_servo_rms_nm", "base_displacement_m"]}), flush=True)
        except Exception as exc:
            gait = {"status": "FAIL_BEFORE_OR_DURING_GAIT", "error_type": type(exc).__name__, "message": str(exc)}
            write_json(output / "gait_attempt_error.json", gait)
    hypothetical = None
    try:
        if args.hypothetical_gearing_on_failure and not decision["allowed"]:
            geometry_helper = frozen_import("geometry_study.geometry_study", runtime)
            commissioning_module = frozen_import("commissioning_offsets", runtime)
            hypothetical = hypothetical_gearing(parameters, model, geometry_helper, fixture_module, output / "hypothetical_3to1", fixture, commissioning_module)
    except Exception as exc:
        hypothetical = {"status": "HYPOTHETICAL_SCREEN_ERROR", "error_type": type(exc).__name__, "message": str(exc)}
        errors.append(hypothetical)
    finally:
        try:
            verify_frozen_inputs(runtime, source_hashes, args.report, provenance)
        except Exception as exc:
            errors.append({"status": "EVIDENCE_VERIFICATION_FAILED", "error_type": type(exc).__name__, "message": str(exc)})
    summary = {"status": "completed_bounded_checks_with_errors" if errors else "completed_bounded_checks_not_hardware_release", "mass_kg": model.total_mass(parameters),
               "stand_and_drive": reports, "fixture": {k: v for k, v in fixture.items() if k not in ["history", "parameters_used"]},
               "gait_dispatch": decision, "gait": gait, "hypothetical_gearing": hypothetical, "errors": errors,
               "sources": source_hashes, "input": provenance,
               "collision_geometry": "Coarse primitives, not the full concealed-wheel CAD meshes"}
    write_json(output / "validation_summary.json", summary)


if __name__ == "__main__":
    main()
