"""Replay leg_native recipes as offline OpenCascade solids and visual assemblies.

Run with the coupon/body CadQuery environment. STEP and candidate part STLs use
millimetres; GLB uses metres. This does not create a native Fusion document or
release a print bed. Local part axes are retained in individual STLs, and their
print orientation still needs review.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import itertools
import json
import re
import time
import uuid
from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh
from cadquery.occ_impl.exporters.assembly import exportAssembly
from OCP.gp import gp_Trsf
from OCP.BOPAlgo import BOPAlgo_BOP, BOPAlgo_Operation
from OCP.TopTools import TopTools_ListOfShape

from body_native import COLORS, body_spec
from export_body import build_solids


_DENSITY_PETG_G_CM3 = 1.27
_VOLUME_THRESHOLD_MM3 = 0.01


def _safe_name(name):
    result = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name)).strip("._")
    if not result:
        raise ValueError("Part name must contain a filename-safe character")
    return result


def _matrix(rows):
    matrix = np.asarray(rows, dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError("Part transform must be a finite 4x4 row-major matrix")
    if not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-9, rtol=0):
        raise ValueError("Part transform has an invalid homogeneous bottom row")
    rotation = matrix[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-8, rtol=0):
        raise ValueError("Part transform must contain an orthogonal rotation")
    if not np.isclose(np.linalg.det(rotation), 1, atol=1e-8, rtol=0):
        raise ValueError("Mirrored or scaled transforms are unsupported; encode handedness in part geometry")
    return matrix


def place_shape(shape, rows):
    """Apply one rigid component-local-to-world transform without spline conversion."""
    matrix = _matrix(rows)
    transform = gp_Trsf()
    transform.SetValues(*(float(value) for value in matrix[:3].ravel()))
    placed = shape.moved(cq.Location(transform))
    if not placed.isValid():
        raise RuntimeError("Rigid placement produced an invalid OpenCascade shape")
    if not np.isclose(shape.Volume(), placed.Volume(), atol=1e-5, rtol=1e-8):
        raise RuntimeError("Rigid placement changed part volume")
    return placed


def _bounds(shape):
    box = shape.BoundingBox()
    return [[box.xmin, box.ymin, box.zmin], [box.xmax, box.ymax, box.zmax]]


def _rgba(value, palette):
    if isinstance(value, str):
        value = palette.get(value, COLORS["grey"])
    color = np.asarray(value, dtype=float)
    if color.shape not in ((3,), (4,)) or not np.isfinite(color).all():
        raise ValueError("Color must contain three or four finite channels")
    if np.any(color < 0) or np.any(color > 255):
        raise ValueError("Color channels must be in 0..1 or 0..255")
    if np.max(color) <= 1:
        color = color * 255
    if len(color) == 3:
        color = np.append(color, 255)
    return tuple(int(round(channel)) for channel in color)


def _specifications(params, leg_name, all_legs, include_body, pose):
    # Keeping this import here allows syntax/API review before leg_native is ready.
    import leg_native

    leg_names = list(params["geometry"].get("leg_names", ["FL", "FR", "RL", "RR"]))
    if leg_name not in leg_names or len(set(leg_names)) != len(leg_names):
        raise ValueError("Choose a leg from the unique geometry.leg_names list")
    names = leg_names if all_legs or include_body else [leg_name]
    specifications = {
        name: leg_native.leg_spec(params, leg_name=name, **pose) for name in names
    }
    if include_body:
        specifications["body"] = body_spec(params)
    palette = dict(COLORS)
    palette.update(getattr(leg_native, "COLORS", {}))
    entries = []
    used_names = set()
    for group, spec in specifications.items():
        for part in spec["parts"]:
            assembly_name = _safe_name(group) + "__" + _safe_name(part["name"])
            if assembly_name in used_names:
                raise ValueError("Duplicate assembly part name: " + assembly_name)
            used_names.add(assembly_name)
            if group == "body":
                transform = np.eye(4)
                transform[2, 3] = spec["assembly_z_offset"]
            else:
                if "transform" not in part:
                    raise ValueError("Missing world transform: " + assembly_name)
                transform = _matrix(part["transform"])
            if not part.get("ops"):
                raise ValueError("Part contains no shape operations: " + assembly_name)
            if part["ops"][0].get("mode") == "cut":
                raise ValueError("The first part operation cannot be a cut: " + assembly_name)
            for op in part["ops"]:
                if op.get("mode") not in ("union", "add", "cut"):
                    raise ValueError("Unsupported Boolean mode: " + str(op.get("mode")))
            entries.append(dict(assembly_name=assembly_name, group=group, part=part,
                                transform=transform.tolist(),
                                color_rgba=_rgba(part.get("color", "grey"), palette)))
    return specifications, entries


def _build(entries):
    local_shapes, world_shapes, rows, checks = {}, {}, [], []
    cache = {}
    for index, entry in enumerate(entries):
        part, name = entry["part"], entry["assembly_name"]
        recipe_bytes = json.dumps(part["ops"], sort_keys=True, separators=(",", ":"),
                                  allow_nan=False).encode("utf-8")
        digest = hashlib.sha256(recipe_bytes).hexdigest()
        reused = digest in cache
        try:
            if reused:
                shape, source_checks = cache[digest]
            else:
                result, source_checks = build_solids({"parts": [part]})
                shape = result[part["name"]]
                cache[digest] = shape, source_checks
            if not shape.isValid() or shape.Volume() <= 0:
                raise RuntimeError("Part is not a valid non-empty shape")
            placed = place_shape(shape, entry["transform"])
        except Exception as error:
            raise RuntimeError("{}: {}: {}".format(name, type(error).__name__, error)) from error
        for check in source_checks:
            check = dict(check)
            check.update(part=part["name"], assembly_name=name, group=entry["group"])
            checks.append(check)
        local_shapes[name], world_shapes[name] = shape, placed
        printed = part["category"] == "print"
        volume_cm3 = shape.Volume() / 1000
        density = float(part.get('density_g_cm3', _DENSITY_PETG_G_CM3))
        free_volume_cm3 = volume_cm3
        if part.get('free_shape_ops'):
            free_part = dict(part, ops=part['free_shape_ops'])
            free_result, free_checks = build_solids({'parts':[free_part]})
            if free_checks or len(free_result[part['name']].Solids()) != 1:
                raise RuntimeError('Invalid free-state print shape: '+name)
            free_volume_cm3 = free_result[part['name']].Volume()/1000
        rows.append(dict(
            assembly_name=name, name=part["name"], group=entry["group"],
            category=part["category"], link=part.get("link", "body"),
            note=part.get("note", ""), valid=placed.isValid(),
            solid_count=len(placed.Solids()), volume_cm3=volume_cm3,
            solid_petg_mass_g=volume_cm3 * _DENSITY_PETG_G_CM3 if printed else None,
            solid_material_mass_g=free_volume_cm3*density if printed else None,
            material=part.get('material','PETG' if printed else 'reference'),
            mass_volume_cm3=free_volume_cm3, assumed_density_g_cm3=density if printed else None,
            center_partlocal_mm=shape.Center().toTuple(),
            center_hipplane_mm=placed.Center().toTuple(),
            bounds_partlocal_mm=_bounds(shape), bounds_hipplane_mm=_bounds(placed),
            transform_partlocal_to_hipplane_mm=entry["transform"],
            geometry_recipe_sha256=digest, reused_exact_geometry_recipe=reused))
        print("placed {}/{} {}".format(index + 1, len(entries), name), flush=True)
    return local_shapes, world_shapes, rows, checks


def checked_overlap(a, b):
    """Return solid overlap in mm3 and kernel warnings after checking completion."""
    if not a.isValid() or not b.isValid():
        raise RuntimeError("Intersection input contains invalid geometry")
    arguments, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    arguments.Append(a.wrapped)
    tools.Append(b.wrapped)
    operation = BOPAlgo_BOP()
    operation.SetArguments(arguments)
    operation.SetTools(tools)
    operation.SetOperation(BOPAlgo_Operation.BOPAlgo_COMMON)
    operation.SetNonDestructive(True)
    operation.SetRunParallel(False)
    operation.Perform()
    if operation.HasErrors():
        diagnostic = io.BytesIO()
        operation.DumpErrors(diagnostic)
        message = diagnostic.getvalue().decode("utf-8", errors="replace")
        raise RuntimeError(message or "OpenCascade intersection failed")
    warning = ""
    if operation.HasWarnings():
        diagnostic = io.BytesIO()
        operation.DumpWarnings(diagnostic)
        warning = diagnostic.getvalue().decode("utf-8", errors="replace")
    native_result = operation.Shape()
    if native_result.IsNull():
        raise RuntimeError("OpenCascade intersection returned a null shape")
    intersection = cq.Shape.cast(native_result)
    if not intersection.isValid():
        raise RuntimeError("OpenCascade returned an invalid intersection shape")
    # Shape.Volume() can calculate area for a face-only result. Count solids only.
    volume = sum(float(solid.Volume()) for solid in intersection.Solids())
    if not np.isfinite(volume) or volume < 0:
        raise RuntimeError("OpenCascade returned an invalid solid intersection volume")
    return volume, warning


def pairwise_interference(shapes, rows, volume_threshold_mm3=_VOLUME_THRESHOLD_MM3):
    """Check every pair with conservative AABB culling and explicit Boolean failures."""
    if volume_threshold_mm3 < 0:
        raise ValueError("Intersection reporting threshold cannot be negative")
    overlaps, subthreshold, failures, warnings = [], [], [], []
    by_name = {row["assembly_name"]: row for row in rows}
    statistics = {}
    last_update = time.monotonic()
    completed = 0
    total = len(shapes) * (len(shapes) - 1) // 2
    print("Checking {} assembly part pairs".format(total), flush=True)
    for an, bn in itertools.combinations(shapes, 2):
        arow, brow = by_name[an], by_name[bn]
        key = "|".join(sorted((arow["group"], brow["group"])))
        stats = statistics.setdefault(key, dict(pairs=0, aabb_disjoint=0,
                                                 boolean_checks=0, zero_volume=0,
                                                 subthreshold=0, positive=0, failures=0))
        stats["pairs"] += 1
        completed += 1
        amin, amax = arow["bounds_hipplane_mm"]
        bmin, bmax = brow["bounds_hipplane_mm"]
        if any(amin[i] >= bmax[i] or bmin[i] >= amax[i] for i in range(3)):
            stats["aabb_disjoint"] += 1
            continue
        record = dict(part_a=an, part_b=bn, group_a=arow["group"], group_b=brow["group"],
                      category_a=arow["category"], category_b=brow["category"],
                      link_a=arow["link"], link_b=brow["link"])
        stats["boolean_checks"] += 1
        try:
            volume, warning = checked_overlap(shapes[an], shapes[bn])
        except Exception as error:
            record.update(overlap_mm3=None, error_type=type(error).__name__, error=str(error))
            failures.append(record)
            stats["failures"] += 1
            print("INTERSECTION FAILED {} / {}: {}".format(an, bn, error), flush=True)
            continue
        if warning:
            warnings.append(dict(record, overlap_mm3=volume, warning=warning))
        if volume > volume_threshold_mm3:
            record["overlap_mm3"] = volume
            overlaps.append(record)
            stats["positive"] += 1
            print("INTERFERENCE {} / {}: {:.6f} mm3".format(an, bn, volume), flush=True)
        elif volume > 0:
            record["overlap_mm3"] = volume
            subthreshold.append(record)
            stats["subthreshold"] += 1
        else:
            stats["zero_volume"] += 1
        if time.monotonic() - last_update > 25:
            print("Checked {}/{} part pairs".format(completed, total), flush=True)
            last_update = time.monotonic()
    return dict(complete=not failures, tested_pose_only=True,
                positive_volume_threshold_mm3=volume_threshold_mm3,
                positive_volume_interferences=overlaps,
                subthreshold_positive_intersections=subthreshold,
                boolean_failures=failures, boolean_warnings=warnings,
                pair_statistics_by_group=statistics,
                interpretation="All part pairs are considered. Positive overlaps are reported without exemptions for links, hardware or reference envelopes. AABB-disjoint pairs need no Boolean. Zero volume does not establish running clearance, swept-motion clearance or correct gear phase.")


def _mass_summary(rows):
    printed = [row for row in rows if row["category"] == "print"]
    mass = sum(row.get("solid_material_mass_g",row["solid_petg_mass_g"]) for row in printed)
    com = ([sum(row.get("solid_material_mass_g",row["solid_petg_mass_g"]) * row["center_hipplane_mm"][i]
                for row in printed) / mass for i in range(3)] if mass else None)
    return dict(printed_solid_mass_g=mass, printed_solid_com_hipplane_mm=com,
                mass_note="Fully solid printed CAD using each part's declared density (PETG default1.27g/cm3). Captured pads use free-state material volume and assembled COM. Legacy per-row solid_petg_mass_g remains a PETG-only comparison. Hardware and non-print categories excluded. Slicer settings and measured weights must replace estimates.")


def _export_assembly(output, label, entries, shapes):
    assembly = cq.Assembly(name=label)
    scene = trimesh.Scene()
    for entry in entries:
        name, part = entry["assembly_name"], entry["part"]
        shape, rgba = shapes[name], entry["color_rgba"]
        assembly.add(shape, name=name, color=cq.Color(*(channel / 255 for channel in rgba)))
        vertices, faces = shape.tessellate(0.22, 0.12)
        if not vertices or not faces:
            raise RuntimeError("Part tessellation is empty: " + name)
        mesh = trimesh.Trimesh(
            vertices=np.array([vertex.toTuple() for vertex in vertices]) / 1000,
            faces=faces, process=False,
            metadata=dict(name=name, category=part["category"], link=part.get("link"), units="m"))
        mesh.visual.vertex_colors = rgba
        scene.add_geometry(mesh, node_name=name, geom_name=name)
    step_path, glb_path = output / (label + ".step"), output / (label + ".glb")
    token = uuid.uuid4().hex
    temporary_step = output / (label + "." + token + ".step")
    if not exportAssembly(assembly, str(temporary_step)):
        raise RuntimeError("OpenCascade STEP writer failed: " + str(temporary_step))
    size = temporary_step.stat().st_size
    with temporary_step.open("rb") as source:
        opening = source.read(64)
        source.seek(max(0, size - 256))
        closing = source.read()
    if not opening.lstrip().startswith(b"ISO-10303-21;") or b"END-ISO-10303-21;" not in closing:
        raise RuntimeError("STEP file is empty or incomplete: " + str(temporary_step))
    temporary_step.replace(step_path)
    glb_bytes = scene.export(file_type="glb")
    if len(glb_bytes) < 20 or glb_bytes[:4] != b"glTF":
        raise RuntimeError("GLB exporter returned an invalid container header")
    temporary_glb = output / (label + "." + token + ".glb")
    temporary_glb.write_bytes(glb_bytes)
    temporary_glb.replace(glb_path)
    return dict(step=str(step_path), glb=str(glb_path),
                step_length_unit="mm", glb_length_unit="m",
                step_writer_reported_success=True, step_roundtrip_checked=False)


def _export_candidate_parts(output, entries, shapes):
    manifest = []
    for entry in entries:
        part = entry["part"]
        if part["category"] != "print":
            continue
        directory = output / "candidate_parts_not_print_release" / _safe_name(entry["group"])
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (_safe_name(part["name"]) + ".stl")
        print_shape = shapes[entry["assembly_name"]]
        state = 'assembled_part_local'
        if part.get('free_shape_ops'):
            free_part = dict(part, ops=part['free_shape_ops'])
            free_result, checks = build_solids({'parts':[free_part]})
            if checks:
                raise RuntimeError('Free-state print recipe failed checks: '+part['name'])
            print_shape = free_result[part['name']]
            state = 'uncompressed_free_state_print_recipe'
        cq.exporters.export(print_shape, str(path),
                            tolerance=0.1, angularTolerance=0.15)
        if path.stat().st_size == 0:
            raise RuntimeError("Part STL is empty: " + str(path))
        manifest.append(dict(assembly_name=entry["assembly_name"], path=str(path),
                             units="mm", coordinate_frame="part_local",
                             shape_state=state, material=part.get('material','PETG'),
                             print_orientation_reviewed=False))
    return manifest


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def export(parameters, output, leg_name="FL", all_legs=False, include_body=False,
           yaw_deg=None, hip_deg=None, knee_deg=None):
    """Write a selected leg, optionally all legs and body, then return the report."""
    parameters, output = Path(parameters), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    params = json.loads(parameters.read_text(encoding="utf-8"))
    pose = dict(yaw_deg=yaw_deg, hip_deg=hip_deg, knee_deg=knee_deg)
    report = dict(
        status="offline_CAD_engineering_candidate_not_Fusion_execution_or_print_release",
        kernel="CadQuery/OpenCascade", coordinate_origin="body hip yaw mount plane",
        report_length_unit="mm", selected_leg=leg_name, pose_overrides_deg=pose,
        generated_utc=datetime.now(timezone.utc).isoformat(),
        parameters_path=str(parameters.resolve()),
        parameters_sha256=hashlib.sha256(parameters.read_bytes()).hexdigest(),
        native_Fusion_executed=False, print_release=False)
    try:
        specs, entries = _specifications(params, leg_name, all_legs, include_body, pose)
        _write_json(output / "leg_recipes.json", specs)
        local_shapes, world_shapes, rows, checks = _build(entries)
        report.update(specifications=specs, shape_checks=checks, parts=rows)
        report.update(_mass_summary(rows))
        report["interference"] = pairwise_interference(world_shapes, rows)
        # Save geometric evidence before any presentation export can fail.
        _write_json(output / "leg_geometry_report.json", report)
        selected_entries = [entry for entry in entries if entry["group"] == leg_name]
        selected_label = "MIST_leg_{}_candidate".format(_safe_name(leg_name))
        files = {"selected_leg": _export_assembly(output, selected_label, selected_entries, world_shapes)}
        if all_legs or include_body:
            leg_entries = [entry for entry in entries if entry["group"] != "body"]
            files["four_legs"] = _export_assembly(output, "MIST_four_legs_candidate", leg_entries, world_shapes)
        if include_body:
            files["whole_robot"] = _export_assembly(output, "MIST_robot_candidate", entries, world_shapes)
        report["candidate_part_stls"] = _export_candidate_parts(output, entries, local_shapes)
        report["assembly_exports"] = files
        report["exports_complete"] = True
        report["process_exit_note"] = "Written before normal interpreter shutdown. The invoking process must record its actual exit status separately; artifact creation does not prove a clean process exit."
        _write_json(output / "leg_geometry_report.json", report)
        selected_rows = [row for row in rows if row["group"] == leg_name]
        selected_report = dict(report)
        selected_report.update(specifications={leg_name: specs[leg_name]}, parts=selected_rows,
                               shape_checks=[check for check in checks if check["group"] == leg_name],
                               assembly_exports={"selected_leg": files["selected_leg"]})
        selected_report.update(_mass_summary(selected_rows))
        selected_report["candidate_part_stls"] = [row for row in report["candidate_part_stls"]
                                                    if row["assembly_name"].startswith(_safe_name(leg_name) + "__")]
        selected_interference = dict(report["interference"])
        for field in ("positive_volume_interferences", "subthreshold_positive_intersections", "boolean_failures", "boolean_warnings"):
            selected_interference[field] = [row for row in selected_interference[field]
                                             if row["group_a"] == leg_name and row["group_b"] == leg_name]
        group_key = leg_name + "|" + leg_name
        selected_interference["pair_statistics_by_group"] = {
            group_key: report["interference"]["pair_statistics_by_group"].get(group_key, {})}
        selected_interference["complete"] = not selected_interference["boolean_failures"]
        selected_report["interference"] = selected_interference
        _write_json(output / ("leg_{}_geometry_report.json".format(_safe_name(leg_name))), selected_report)
    except Exception as error:
        report.update(status="offline_CAD_export_incomplete", exports_complete=False,
                      failure=dict(type=type(error).__name__, message=str(error)))
        _write_json(output / "leg_export_failure.json", report)
        raise
    summary = dict(parts=len(rows), printed_solid_mass_g=report["printed_solid_mass_g"],
                   shape_checks=len(checks),
                   positive_volume_interferences=len(report["interference"]["positive_volume_interferences"]),
                   boolean_failures=len(report["interference"]["boolean_failures"]),
                   assembly_exports=files)
    print(json.dumps(summary, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", type=Path,
                        default=Path(__file__).parents[1] / "simulation" / "design_parameters_20260907.json")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output")
    parser.add_argument("--leg", default="FL")
    parser.add_argument("--all-legs", action="store_true")
    parser.add_argument("--include-body", action="store_true", help="Export body and all four legs together")
    parser.add_argument("--yaw-deg", type=float)
    parser.add_argument("--hip-deg", type=float)
    parser.add_argument("--knee-deg", type=float)
    arguments = parser.parse_args()
    export(arguments.parameters, arguments.output, arguments.leg,
           arguments.all_legs, arguments.include_body,
           arguments.yaw_deg, arguments.hip_deg, arguments.knee_deg)
