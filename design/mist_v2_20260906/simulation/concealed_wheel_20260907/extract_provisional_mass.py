"""Rebuild frozen OEM FL shapes for load-only mass projection, allowing clashes."""
from pathlib import Path
import copy
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
CAD = SIM.parent / "cad"


def main():
    output = HERE / "provisional_oem_FL_20260907"
    output.mkdir(exist_ok=False)
    source = CAD / "concealed_wheel_drive_20260907/output_oem_checkpoint"
    paths = {"leg_geometry_report.json": source / "leg_geometry_report.json",
             "leg_recipes.json": source / "leg_recipes.json", "parameters_used.json": source / "parameters_used.json",
             "old_full_report.json": CAD / "leg_proximal_20260907/output_candidate/leg_geometry_report.json"}
    hashes = {}
    for name, path in paths.items():
        raw = path.read_bytes()
        (output / name).write_bytes(raw)
        hashes[name] = {"source": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
    runtime = output / "cad_runtime"
    runtime.mkdir()
    runtime_paths = {name: CAD / name for name in ["export_leg.py", "export_body.py", "body_native.py"]}
    runtime_paths["reference_shapes.py"] = CAD / "concealed_wheel_drive_20260907/reference_shapes.py"
    runtime_paths["inertia_report.py"] = CAD / "leg_proximal_20260907/inertia_report.py"
    for name, path in runtime_paths.items():
        raw = path.read_bytes()
        (runtime / name).write_bytes(raw)
        hashes["cad_runtime/" + name] = {"source": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
    (output / "source_hashes.json").write_text(json.dumps(hashes, indent=2))
    sys.path.insert(0, str(runtime))
    import numpy as np
    import export_leg as replay
    from reference_shapes import enable_step_references
    from inertia_report import enrich_report
    enable_step_references()
    report = json.loads((output / "leg_geometry_report.json").read_text())
    specs = json.loads((output / "leg_recipes.json").read_text())
    params = json.loads((output / "parameters_used.json").read_text())
    old = json.loads((output / "old_full_report.json").read_text())
    if set(specs) != {"FL"} or not report["exports_complete"]:
        raise ValueError("Expected the completed OEM FL checkpoint")
    fixed = {row["name"]: row for row in report["parts"] if row["link"] in ["body", "base", "base_link"]}
    old_fixed = {row["name"]: row for row in old["parts"] if row["group"] == "FL" and row["link"] in ["body", "base", "base_link"]}
    if set(fixed) != set(old_fixed) or any(fixed[name][key] != old_fixed[name][key] for name in fixed for key in ["geometry_recipe_sha256", "transform_partlocal_to_hipplane_mm"]):
        raise ValueError("Base-fixed leg recipes changed; previous full base cannot be used")
    entries = [dict(assembly_name="FL__" + part["name"], group="FL", part=part,
                    transform=part["transform"], color_rgba=[235, 234, 225, 255]) for part in specs["FL"]["parts"]]
    local, world, rows, checks = replay._build(entries)
    if checks:
        raise ValueError("Reconstructed individual solids have shape issues")
    original_rows = {row["assembly_name"]: row for row in report["parts"]}
    volume_errors = {row["assembly_name"]: abs(row["volume_cm3"] - original_rows[row["assembly_name"]]["volume_cm3"]) for row in rows}
    if max(volume_errors.values()) > 1e-6:
        raise ValueError("Reconstructed shape volumes do not match the saved checkpoint")
    enriched = copy.deepcopy(report)
    enriched["parts"] = rows
    enrich_report(enriched, local, world, entries, params)
    (output / "FL_enriched_mass_report.json").write_text(json.dumps(enriched, indent=2))
    base = old["link_mass_properties"]["base_link"]
    link_properties = {"base_link": {"mass_kg": base["mass_kg"], "com_m": base["com_local_m"], "inertia_kg_m2": base["inertia_com_local_kg_m2"]}}
    for leg, hand in zip(["FL", "FR", "RL", "RR"], [1, -1, -1, 1]):
        mirror = np.diag([1, hand, 1])
        for link in ["yaw", "femur", "tibia", "wheel"]:
            prop = enriched["link_mass_properties"]["FL_" + link]
            if not prop["has_geometry"]:
                raise ValueError("FL moving-link mass allocation is incomplete")
            link_properties[leg + "_" + link] = {"mass_kg": prop["mass_kg"],
                "com_m": (mirror @ np.array(prop["com_local_m"])).tolist(),
                "inertia_kg_m2": (mirror @ np.array(prop["inertia_com_local_kg_m2"]) @ mirror.T).tolist()}
    params["link_mass_properties"] = link_properties
    params["mass"]["knee_servo_com_m"] = (np.array(specs["FL"]["knee_servo_com_femur_mm"]) / 1000).tolist()
    params["mass"]["provenance"] = "PROVISIONAL: latest OEM FL moving-link solids mirrored into four proper local leg frames; previous unchanged base allocation. Not a full collision-safe CAD export."
    params["transmission"]["knee_motor_mount"] = "femur"
    params["status"] = "PROVISIONAL_OEM_FL_MIRRORED_LOAD_ONLY_COLLISIONS_UNRESOLVED"
    params["provisional_load_only"] = {"sources": hashes, "FL_part_count": len(rows), "base_fixed_FL_parts_identical": len(fixed),
        "mirror": "Local Y reflection for FR/RL; COM M*c and full tensor M*I*M^T. Proper world leg frames are supplied by URDF kinematics.",
        "old_base_mass_kg": base["mass_kg"], "base_assumption": "Body and base-fixed leg inventory unchanged from previous full export.",
        "FL_collision_count": len(report["interference"]["positive_volume_interferences"]),
        "new_mount_mass_included": False, "estimated_mount_mass_delta_not_applied_kg": .12,
        "all_four_legs_exported": False, "collision_safe_model": False, "physical_release": False,
        "max_reconstructed_volume_error_cm3": max(volume_errors.values())}
    (output / "parameters_provisional.json").write_text(json.dumps(params, indent=2))
    print(json.dumps({"status": params["status"], "projected_mass_kg": sum(item["mass_kg"] for item in link_properties.values()),
                      "FL_collision_count": params["provisional_load_only"]["FL_collision_count"]}), flush=True)


if __name__ == "__main__":
    main()
