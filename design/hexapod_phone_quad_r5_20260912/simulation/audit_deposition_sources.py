"""Independently audit frozen production deposition properties and their sources."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import struct

import numpy as np


MODEL = {"WALL-INNER", "WALL-OUTER", "SKIN", "FILL", "IRONING", "BRIDGE",
         "TOP-SKIN", "BOTTOM-SKIN", "WALL-OVERHANG"}
ADHESION = {"SKIRT", "BRIM", "RAFT", "PRIME-TOWER", "PRIME-BLOB"}
FIELDS = re.compile(r"([A-Z])([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
TOL = {"mass_kg": 1e-11, "com_mm": 1e-6, "inertia_kg_m2": 1e-14,
       "transform": 1e-10, "volume_mm3": 1e-6, "mesh_vertex_mm": 1e-5}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def group(feature):
    if feature in MODEL:
        return "model"
    if feature.startswith("SUPPORT"):
        return "support"
    if feature in ADHESION or feature.startswith("RAFT"):
        return "adhesion"
    return "unclassified"


def independent_segments(text):
    """Replay the frozen absolute-coordinate, single-extruder linear profile."""
    position = np.zeros(3)
    previous_e, debt, feed = 0., 0., 0.
    feature = "UNCLASSIFIED"
    segments = defaultdict(list)
    retracted, repaid, nonmoving = 0., 0., 0.
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith(";TYPE:"):
            feature = line[6:].strip()
        command = line.partition(";")[0].strip()
        if not command:
            continue
        match = re.match(r"([GMT]\d+(?:\.\d+)?)", command)
        if not match:
            raise ValueError(f"Unrecognized command at line {number}")
        verb = match.group(1)
        values = {name: float(value) for name, value in FIELDS.findall(command[match.end():])}
        if verb in {"G20", "G91", "M83", "G2", "G3", "G5", "G28", "G53", "G54", "G55", "G56", "G57", "G58", "G59", "G92.1", "G10", "G11"}:
            raise ValueError(f"Command {verb} is outside this frozen-profile audit")
        if verb.startswith("T") and verb != "T0":
            raise ValueError("Multiple extruders are outside this audit")
        if verb == "M200" and values.get("D", 0) != 0:
            raise ValueError("Volumetric extrusion is outside this audit")
        if verb == "M221" and values.get("S", 100) != 100:
            raise ValueError("Firmware flow override changes the material accounting")
        if verb == "G92":
            if any(axis in values for axis in "XYZ"):
                raise ValueError("Spatial G92 resets are outside this frozen profile")
            previous_e = values.get("E", previous_e)
            continue
        if verb not in {"G0", "G1"}:
            continue
        feed = values.get("F", feed*60)/60
        destination = np.array([values.get(axis, position[index]) for index, axis in enumerate("XYZ")])
        next_e = values.get("E", previous_e)
        change = next_e-previous_e
        previous_e = next_e
        fresh, paid = 0., 0.
        if change < 0:
            debt -= change
            retracted -= change
        elif change > 0:
            paid = min(change, debt)
            debt -= paid
            repaid += paid
            fresh = change-paid
        distance = float(np.linalg.norm(destination-position))
        if fresh > 1e-10 and distance > 1e-7:
            if abs(destination[2]-position[2]) > 1e-6:
                raise ValueError("An extruding move changes layer height")
            start = position+(destination-position)*(paid/change)
            segments[group(feature)].append([*start, *destination, fresh, feed])
        elif fresh > 1e-10:
            nonmoving += fresh
        position = destination
    return segments, {"retracted_filament_mm": retracted,
        "repaid_retraction_filament_mm": repaid, "outstanding_retraction_filament_mm": debt,
        "nonmoving_fresh_prime_filament_mm": nonmoving}


def quadrature_properties(rows, transform, density, diameter, height):
    """Use endpoint/midpoint Simpson quadrature, exact for line second moments."""
    if not rows:
        return {"mass_kg": 0., "deposited_volume_mm3": 0., "segment_count": 0}
    rows = np.asarray(rows)
    start, end = rows[:, :3].copy(), rows[:, 3:6].copy()
    start[:, 2] -= height/2
    end[:, 2] -= height/2
    rotation, translation = transform[:3, :3], transform[:3, 3]
    start, end = start @ rotation.T+translation, end @ rotation.T+translation
    middle = (start+end)/2
    volume = rows[:, 6]*math.pi*diameter**2/4
    mass = volume*density*1e-6
    total = float(mass.sum())
    center = np.average(middle, axis=0, weights=mass)
    second = np.zeros((3, 3))
    for points, weight in ((start, 1/6), (middle, 4/6), (end, 1/6)):
        delta = points-center
        second += np.einsum("n,ni,nj->ij", mass*weight, delta, delta)
    inertia = (np.trace(second)*np.eye(3)-second)*1e-6
    lengths = np.linalg.norm(end-start, axis=1)
    width = volume/(lengths*height)
    normal = rotation @ np.array([0., 0., 1.])
    side = np.cross(normal, (end-start)/lengths[:, None])
    side /= np.linalg.norm(side, axis=1)[:, None]
    correction = (np.eye(3)*float(np.sum(mass*width**2))
                  - np.einsum("n,ni,nj->ij", mass*width**2, side, side))/12
    correction += total*height**2/12*(np.eye(3)-np.outer(normal, normal))
    times = np.divide(lengths, rows[:, 7], out=np.zeros_like(lengths), where=rows[:, 7] > 0)
    return {"mass_kg": total, "deposited_volume_mm3": float(volume.sum()),
            "segment_count": len(rows), "com_mm": center,
            "inertia_line_about_com_kg_m2": inertia,
            "inertia_rectangular_bead_about_com_kg_m2": inertia+correction*1e-6,
            "deposited_path_time_without_acceleration_s": float(times.sum())}


def stl_triangles(path):
    payload = Path(path).read_bytes()
    count = struct.unpack_from("<I", payload, 80)[0]
    if len(payload) != 84+50*count:
        raise ValueError("Expected the frozen binary STL format")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    return np.frombuffer(payload, dtype=dtype, offset=84)["vertices"].astype(float)


def solid_properties(triangles, density):
    """Integrate signed tetrahedra relative to one mesh vertex."""
    reference = triangles[0, 0]
    vertices = triangles-reference
    a, b, c = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    volume = np.einsum("ni,ni->n", a, np.cross(b, c))/6
    masses = volume*density*1e-6
    total = float(masses.sum())
    if total <= 0:
        raise ValueError("The STL has nonpositive signed volume")
    summed = vertices.sum(axis=1)
    center = np.einsum("n,ni->i", masses/4, summed)/total
    second = np.einsum("n,ni,nj->ij", masses/20, summed, summed)
    for i in range(3):
        second += np.einsum("n,ni,nj->ij", masses/20, vertices[:, i], vertices[:, i])
    second -= total*np.outer(center, center)
    return {"mass_kg": total, "volume_mm3": float(volume.sum()),
            "com_mm": center+reference,
            "inertia_kg_m2": (np.trace(second)*np.eye(3)-second)*1e-6}


def compare_properties(check, prefix, actual, expected, inertia_keys):
    check(prefix+":mass", abs(actual["mass_kg"]-expected["mass_kg"]) <= TOL["mass_kg"])
    if actual["mass_kg"] == 0:
        return
    check(prefix+":com", np.max(np.abs(actual["com_mm"]-np.asarray(expected["com_mm"]))) <= TOL["com_mm"])
    for key in inertia_keys:
        matrix = np.asarray(expected[key], dtype=float)
        check(prefix+":"+key, matrix.shape == (3, 3) and np.all(np.isfinite(matrix))
              and np.max(np.abs(actual[key]-matrix)) <= TOL["inertia_kg_m2"])
        check(prefix+":"+key+":physical", np.max(np.abs(matrix-matrix.T)) < 1e-12
              and np.linalg.eigvalsh(matrix).min() >= -1e-12
              and np.trace(matrix)-2*np.linalg.eigvalsh(matrix).max() >= -1e-12)


def audit_case(row, entry, source_dir, record_file):
    result = {"sku": row["sku"], "quantity": row["quantity"], "checks": {}, "errors": []}
    def check(name, passed):
        result["checks"][name] = bool(passed)
    try:
        engine, deposition, evidence = row["engine"], row["deposition"], row["gcode_evidence"]
        check("quantity", row["quantity"] == entry["quantity"])
        check("row_status", row["status"] == "pass" and engine["return_code"] == 0)
        for label, path_key, hash_key in [
            ("source", "source_stl_path", "source_sha256"),
            ("original_snapshot", "original_snapshot_path", "original_snapshot_sha256"),
            ("normalized_snapshot", "normalized_snapshot_path", "normalized_snapshot_sha256"),
            ("profile", "profile_path", "profile_sha256"),
            ("resolved_settings", "resolved_settings_path", "resolved_settings_sha256"),
            ("engine", "engine_path", "engine_sha256"), ("log", "log_path", "log_sha256")]:
            check("hash:"+label, record_file(engine[path_key]) == engine[hash_key])
        check("hash:manifest_print_stl", record_file(source_dir/entry["stl"]) == row["source_stl_hash"])
        check("source_hash_aliases", row["source_stl_hash"] == engine["source_sha256"] == engine["original_snapshot_sha256"])
        check("source_rotation", row["source_print_rotation_deg"] == entry.get("print_rotation"))
        check("hash:compressed_gcode", record_file(evidence["path"]) == evidence["sha256"])
        lines = gzip.decompress(Path(evidence["path"]).read_bytes()).decode("utf-8").splitlines()
        check("archive_commands_disabled", all(not line.strip() or line.lstrip().startswith(";") for line in lines))
        check("archive_header", bool(lines) and lines[0].startswith("; ANALYSIS EVIDENCE ONLY."))
        prefix = "; DISABLED| "
        restored = "\n".join(line[len(prefix):] if line.startswith(prefix) else line for line in lines[1:])+"\n"
        text_hash = hashlib.sha256(restored.encode()).hexdigest()
        crlf_hash = hashlib.sha256(restored.replace("\n", "\r\n").encode()).hexdigest()
        check("hash:restored_raw_text", text_hash == evidence["raw_text_sha256"])
        check("hash:restored_raw_bytes", engine["raw_temporary_sha256"] in {text_hash, crlf_hash})
        check("temporary_gcode_removed", not Path(engine["raw_temporary_path"]).exists())
        matrices = {key: np.asarray(engine[key], dtype=float) for key in (
            "source_to_normalized_snapshot_transform", "normalized_snapshot_to_gcode_transform",
            "source_to_gcode_transform", "gcode_to_source_transform")}
        for key, transform in matrices.items():
            check("rigid_transform:"+key, transform.shape == (4, 4) and np.all(np.isfinite(transform))
                  and np.allclose(transform[3], [0, 0, 0, 1], rtol=0, atol=TOL["transform"])
                  and np.allclose(transform[:3, :3].T @ transform[:3, :3], np.eye(3), rtol=0, atol=TOL["transform"])
                  and abs(np.linalg.det(transform[:3, :3])-1) <= TOL["transform"])
        transform = matrices["gcode_to_source_transform"]
        check("transform_inverse", np.allclose(transform @ matrices["source_to_gcode_transform"], np.eye(4), rtol=0, atol=TOL["transform"]))
        check("transform_composition", np.allclose(matrices["normalized_snapshot_to_gcode_transform"] @ matrices["source_to_normalized_snapshot_transform"], matrices["source_to_gcode_transform"], rtol=0, atol=TOL["transform"]))
        check("parser_transform_alias", np.allclose(transform, deposition["gcode_to_source_transform"], rtol=0, atol=TOL["transform"]))
        settings = json.loads(Path(engine["resolved_settings_path"]).read_text())
        check("frozen_profile_assumptions", settings["machine_extruder_count"] == 1
              and settings["relative_extrusion"] is False and settings["machine_start_gcode"] == ""
              and settings["machine_end_gcode"] == "" and settings["material_flow"] == 100
              and settings["layer_height"] == settings["layer_height_0"] == deposition["layer_height_mm"]
              and settings["material_diameter"] == deposition["filament_diameter_mm"])
        profile = json.loads(Path(engine["profile_path"]).read_text())
        check("resolved_profile_alias", settings == {key: value["default_value"] for key, value in profile["settings"].items()})
        segments, accounting = independent_segments(restored)
        calculated = {}
        for name in ("model", "support", "adhesion", "unclassified"):
            calculated[name] = quadrature_properties(segments[name], transform, deposition["density_g_cm3"],
                                                    deposition["filament_diameter_mm"], deposition["layer_height_mm"])
            expected = deposition["properties"][name]
            compare_properties(check, "quadrature:"+name, calculated[name], expected,
                ("inertia_line_about_com_kg_m2", "inertia_rectangular_bead_about_com_kg_m2"))
            check("segments:"+name, calculated[name]["segment_count"] == expected["segment_count"])
            check("volume:"+name, abs(calculated[name]["deposited_volume_mm3"]-expected["deposited_volume_mm3"]) <= TOL["volume_mm3"])
        model = calculated["model"]
        compare_properties(check, "production_row", {"mass_kg": model["mass_kg"], "com_mm": model["com_mm"],
                           "inertia_kg_m2": model["inertia_line_about_com_kg_m2"]}, row, ("inertia_kg_m2",))
        check("unclassified_zero", calculated["unclassified"]["mass_kg"] == 0)
        check("removable_material_excluded", abs(row["support_mass_g"]-calculated["support"]["mass_kg"]*1000) <= 1e-8
              and abs(row["adhesion_mass_g"]-calculated["adhesion"]["mass_kg"]*1000) <= 1e-8)
        check("reported_total_material", abs(sum(v["mass_kg"] for v in calculated.values())*1000-row["total_deposited_mass_g"]) <= 1e-8)
        check("retraction_accounting", all(abs(value-deposition["extrusion_accounting"][key]) <= 1e-6 for key, value in accounting.items()))
        parsed_volume = sum(v["deposited_volume_mm3"] for v in calculated.values())
        denominator = max(1., engine["engine_filament_volume_mm3"])
        discrepancy = abs(parsed_volume-engine["engine_filament_volume_mm3"])/denominator
        tolerance = max(.001, 1.1/denominator)
        check("engine_rounded_volume", discrepancy <= tolerance and abs(tolerance-row["extrusion_accounting_tolerance"]) <= 1e-12
              and abs(discrepancy-row["extrusion_accounting_relative_difference"]) <= 1e-9)
        source_triangles = stl_triangles(engine["original_snapshot_path"])
        normalized_triangles = stl_triangles(engine["normalized_snapshot_path"])
        source_to_normal = matrices["source_to_normalized_snapshot_transform"]
        expected_normal = source_triangles @ source_to_normal[:3, :3].T + source_to_normal[:3, 3]
        check("normalized_mesh_transform", normalized_triangles.shape == expected_normal.shape
              and np.max(np.abs(normalized_triangles-expected_normal)) <= TOL["mesh_vertex_mm"])
        actual_solid = solid_properties(source_triangles, deposition["density_g_cm3"])
        compare_properties(check, "stl_solid_tetrahedra", actual_solid, row["solid_scenario"], ("inertia_kg_m2",))
        result["independent_model_properties"] = {"mass_kg": model["mass_kg"], "com_mm": model["com_mm"].tolist(),
            "inertia_kg_m2": model["inertia_line_about_com_kg_m2"].tolist(), "segment_count": model["segment_count"]}
        result["engine_volume_relative_difference"] = discrepancy
        result["engine_volume_relative_tolerance"] = tolerance
    except Exception as error:
        result["errors"].append(f"{type(error).__name__}: {error}")
    result["failed_checks"] = [name for name, passed in result["checks"].items() if not passed]
    result["passed"] = bool(result["checks"]) and not result["failed_checks"] and not result["errors"]
    return result


def audit(production, expected_hash=None):
    report = {"created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "audit_fail",
        "inputs": {}, "checks": {}, "cases": [], "errors": [], "tolerances": TOL,
        "method": "Independent absolute-mode extrusion replay, endpoint/midpoint Simpson quadrature for deposited line moments, rectangular-section correction, and signed tetrahedral STL mass integration.",
        "scope": "Checks commanded deposition estimates and source identity. Does not establish measured mass, printed strength, printer calibration, assembled transforms or walking."}
    def record_file(path):
        path = str(Path(path).resolve())
        if path not in report["inputs"]:
            report["inputs"][path] = digest(path)
        return report["inputs"][path]
    def check(name, passed):
        report["checks"][name] = bool(passed)
    try:
        source_hash = record_file(production)
        if expected_hash and source_hash != expected_hash:
            raise ValueError("The production properties file differs from the requested frozen hash")
        record_file(__file__)
        data = json.loads(production.read_text())
        report["production_properties_sha256"] = source_hash
        report["source_manifest_sha256"] = data["source_manifest_hash"]
        source = Path(data["source_manifest_path"])
        check("source_manifest_hash", record_file(source) == data["source_manifest_hash"])
        check("source_snapshot_hash", record_file(production.parent/"source_assembly_manifest.json") == data["source_manifest_hash"])
        manifest = json.loads(source.read_text())
        check("production_status_revision", data["status"] == "pass" and data["source_revision"] == manifest["revision"])
        for name, expected in data["source_script_hashes"].items():
            check("producer_hash:"+name, record_file(production.parent.parent/name) == expected)
        entries = {entry["sku"]: entry for entry in manifest["print_parts"]}
        by_sku = {row["sku"]: row for row in data["parts"]}
        check("unique_sku_coverage", len(entries) == len(manifest["print_parts"]) == len(by_sku) == len(data["parts"])
              and set(entries) == set(by_sku))
        counts = Counter(part["sku"] for part in manifest["parts"] if part["printable"])
        check("manifest_piece_coverage", counts == Counter({name: entry["quantity"] for name, entry in entries.items()}))
        base_profile = production.parent.parent.parent/"orientation/slicer/resolved_analysis.def.json"
        base_hash = record_file(base_profile)
        for row in data["parts"]:
            check("base_profile_hash:"+row["sku"], row["engine"]["base_profile_sha256"] == base_hash)
            check("nominal_density:"+row["sku"], abs(row["deposition"]["density_g_cm3"]-manifest["parameters"]["pla_density_kg_m3"]/1000) < 1e-12)
            result = audit_case(row, entries[row["sku"]], source.parent, record_file)
            report["cases"].append(result)
            print(json.dumps({"sku": row["sku"], "passed": result["passed"], "failed_checks": result["failed_checks"], "errors": result["errors"]}), flush=True)
        totals = {
            "piece_count": sum(row["quantity"] for row in data["parts"]),
            "model_mass_g": sum(row["quantity"]*row["mass_kg"]*1000 for row in data["parts"]),
            "support_mass_g": sum(row["quantity"]*row["support_mass_g"] for row in data["parts"]),
            "adhesion_mass_g": sum(row["quantity"]*row["adhesion_mass_g"] for row in data["parts"]),
            "total_deposited_mass_g": sum(row["quantity"]*row["total_deposited_mass_g"] for row in data["parts"]),
            "estimated_individual_print_time_hours": sum(row["quantity"]*row["estimated_print_time_s"] for row in data["parts"])/3600,
            "full_solid_model_mass_g": sum(row["quantity"]*row["solid_scenario"]["mass_g"] for row in data["parts"]),
        }
        check("quantity_weighted_totals", all(abs(value-data["quantity_weighted_totals"][name]) < 1e-7 for name, value in totals.items()))
        report["quantity_weighted_totals"] = totals
        check("all_inputs_unchanged", all(digest(path) == value for path, value in report["inputs"].items()))
    except Exception as error:
        report["errors"].append(f"{type(error).__name__}: {error}")
    report["failed_checks"] = [name for name, passed in report["checks"].items() if not passed]
    report["passed"] = bool(report["cases"]) and not report["errors"] and not report["failed_checks"] and all(case["passed"] for case in report["cases"])
    report["status"] = "audit_pass" if report["passed"] else "audit_fail"
    report["check_count"] = len(report["checks"])+sum(len(case["checks"]) for case in report["cases"])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production", required=True, type=Path)
    parser.add_argument("--expected-production-sha256")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    production, output = args.production.resolve(), args.output.resolve()
    if output in {production, Path(__file__).resolve()}:
        parser.error("The audit output cannot overwrite its inputs")
    report = audit(production, args.expected_production_sha256)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    totals = report.get("quantity_weighted_totals", {})
    lines = [f"Production deposition audit: {report['status']}", "",
             f"Audited SKUs: {len(report['cases'])}", f"Checks: {report['check_count']}",
             f"Printed pieces: {totals.get('piece_count', 'unavailable')}",
             f"Production properties SHA256: {report.get('production_properties_sha256', 'unavailable')}",
             f"Source manifest SHA256: {report.get('source_manifest_sha256', 'unavailable')}", "",
             report["method"], "", report["scope"], ""]
    for case in report["cases"]:
        if not case["passed"]:
            lines.append(f"FAILED {case['sku']}: {case['failed_checks']} {case['errors']}")
    lines.extend([f"Top-level failed checks: {report['failed_checks']}", f"Errors: {report['errors']}", ""])
    output.with_suffix(".txt").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["check_count"], "output_path": str(output)}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
