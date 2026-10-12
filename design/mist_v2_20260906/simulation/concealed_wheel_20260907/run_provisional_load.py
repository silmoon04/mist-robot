"""Explicitly provisional load-only 2:1/3:1 screen while CAD clashes remain."""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import validate_concealed as validation


def main():
    source = HERE / "provisional_oem_FL_20260907/parameters_provisional.json"
    raw = source.read_bytes()
    p = json.loads(raw)
    if p.get("status") != "PROVISIONAL_OEM_FL_MIRRORED_LOAD_ONLY_COLLISIONS_UNRESOLVED":
        raise ValueError("This entry point requires the explicit provisional mirrored-FL input")
    validation.verify_actuator_contract(p)
    output = HERE / "provisional_oem_load_2to1_and_3to1"
    output.mkdir(exist_ok=False)
    (output / "source_parameters.json").write_bytes(raw)
    runtime, hashes = validation.freeze_runtime(output)
    sys.path.insert(0, str(runtime))
    model = validation.frozen_import("model", runtime)
    model.validate_link_mass_properties(p)
    p = validation.effective_wheel_parameters(p)
    validation.write_json(output / "parameters_used.json", p)
    model.build_urdf(p, output / "provisional_candidate.urdf")
    run_sim = validation.frozen_import("run_sim", runtime)
    fixture_module = validation.frozen_import("concealed_fixture", runtime)
    geometry = validation.frozen_import("geometry_study.geometry_study", runtime)
    commissioning = validation.frozen_import("commissioning_offsets", runtime)
    scope = "PROVISIONAL LOAD ONLY: mirrored OEM FL shape inertials; known CAD clashes; no collision-safe acceptance or physical release"
    stand = run_sim.run_case(copy.deepcopy(p), "stand", output_root=output / "actual_2to1")
    stand["scope"] = scope
    validation.write_json(output / "actual_2to1/stand/report.json", stand)
    print(json.dumps({"variant": "actual_2to1_mass_projection", **{k: stand[k] for k in ["status", "mass_kg", "max_servo_rms_nm", "max_tilt_deg"]}}), flush=True)
    fixture = fixture_module.trial(copy.deepcopy(p), output / "actual_2to1/fixture")
    print(json.dumps({"variant": "actual_2to1_fixture", **{k: fixture[k] for k in ["status", "hold_servo_rms_nm", "hold_max_foot_error_m", "continuous_torque_reserve_fraction"]}}), flush=True)
    hypo = validation.hypothetical_gearing(p, model, geometry, fixture_module, output / "hypothetical_3to1", fixture, commissioning)
    hypothetical_p = json.loads((output / "hypothetical_3to1/parameters_hypothetical.json").read_text())
    hypothetical_stand = run_sim.run_case(hypothetical_p, "stand", output_root=output / "hypothetical_3to1")
    hypothetical_stand["scope"] = scope + "; 3:1 gear geometry and commissioning offsets are hypothetical"
    validation.write_json(output / "hypothetical_3to1/stand/report.json", hypothetical_stand)
    print(json.dumps({"variant": "hypothetical_3to1_stand", **{k: hypothetical_stand[k] for k in ["status", "mass_kg", "max_servo_rms_nm", "max_tilt_deg"]}}), flush=True)
    print(json.dumps({"variant": "hypothetical_3to1_fixture", **{k: hypo["fixture"][k] for k in ["status", "hold_servo_rms_nm", "hold_max_foot_error_m", "continuous_torque_reserve_fraction"]}}), flush=True)
    for name, metadata in hashes.items():
        if hashlib.sha256((runtime / name).read_bytes()).hexdigest() != metadata["executed_sha256"]:
            raise RuntimeError("Frozen runtime changed: " + name)
    if hashlib.sha256(source.read_bytes()).hexdigest() != hashlib.sha256(raw).hexdigest():
        raise RuntimeError("Provisional input changed during the screen")
    summary = {"status": "PROVISIONAL_LOAD_ONLY_SCREEN_COMPLETE", "scope": scope, "mass_kg": model.total_mass(p),
               "actual_2to1_stand": stand, "actual_2to1_fixture": {k: v for k, v in fixture.items() if k not in ["history", "parameters_used"]},
               "hypothetical_3to1_stand": hypothetical_stand, "hypothetical_3to1": hypo,
               "source_parameters_sha256": hashlib.sha256(raw).hexdigest(), "sources": hashes,
               "gait_dispatched": False, "clean_CAD_gate_bypassed": False,
               "separate_authorization": "Root explicitly requested a provisional load-only sensitivity while final CAD collision cleanup continues."}
    validation.write_json(output / "summary.json", summary)


if __name__ == "__main__":
    main()
