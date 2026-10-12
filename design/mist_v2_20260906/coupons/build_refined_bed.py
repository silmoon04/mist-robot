"""Build a second coupon bed from measured, verified feedback.

Run in the CAD environment: python build_refined_bed.py request.json --out bed2
The output directory must not exist. Use one to three interface groups printed
with one shared material/profile. These specimens do not release robot parts.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile

from build_coupon_bed import BEARINGS, Part, export_3mf, primitive
from refine_from_feedback import FIELDS, FeedbackError, make_request


class BuildError(ValueError):
    """A request cannot be used to build this coupon bed."""


def load_validated_request(path: Path | str) -> dict:
    path = Path(path)
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"Cannot read request: {exc}") from exc
    if not isinstance(request, dict):
        raise BuildError("Request must be a JSON object.")
    if type(request.get("schema_version")) is not int or request.get("schema_version") != 1 or request.get("purpose") != "second_coupon_parameter_request":
        raise BuildError("Request schema or purpose is unsupported.")
    if request.get("status") != "requires_review" or request.get("production_release") is not False:
        raise BuildError("Request must be a coupon request with production_release false.")
    source = request.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("path"), str):
        raise BuildError("Request has no source CSV path.")
    csv_path = Path(source["path"])
    if not csv_path.is_absolute():
        raise BuildError("Source CSV path must be absolute.")
    try:
        data = csv_path.read_bytes()
    except OSError as exc:
        raise BuildError(f"Cannot read source CSV: {exc}") from exc
    if source.get("sha256") != hashlib.sha256(data).hexdigest():
        raise BuildError("Source CSV hash changed; rebuild the request from the current measurements.")
    try:
        expected = make_request(data, str(csv_path.resolve()))
    except (FeedbackError, csv.Error) as exc:
        raise BuildError(f"Source feedback is invalid: {exc}") from exc
    submitted = copy.deepcopy(request)
    submitted.pop("generated_at_utc", None)
    expected.pop("generated_at_utc", None)
    try:
        matches = json.dumps(submitted, sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)
    except ValueError as exc:
        raise BuildError("Request contains nonfinite numeric values.") from exc
    if not matches:
        raise BuildError("Request differs from its measured source; regenerate it with refine_from_feedback.py.")
    return request


def _dimension(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BuildError(f"{name} must be numeric.")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise BuildError(f"{name} must be positive and finite.")
    return value


def _part_for_group(group: dict, number: int) -> tuple[Part, list[dict], float, float]:
    interface = group["interface"]
    nominal = _dimension(group["nominal_mm"], "nominal_mm")
    candidates = [_dimension(value, "candidate CAD dimension") for value in group["candidate_cad_mm"]]
    if len(candidates) != 3 or any(abs(candidates[i + 1] - candidates[i] - .05) > 1e-6 for i in range(2)):
        raise BuildError("Each group must have three ascending candidates spaced by 0.05 mm.")
    p = Part(f"{number:02}_refined_{interface}")
    features = []

    def feature(i, x, y, **extra):
        features.append(dict(
            feature_id=f"BED2_{number:02}_{interface}_{i + 1}", interface=interface,
            nominal_mm=nominal, cad_mm=candidates[i], x_mm=x, y_mm=y, part=p.name,
            source_feature_id=group["selected_feature_id"], source_row=group["selected_source_row"],
            source_fit_result=group["basis"]["fit_result"], print_axis="Z",
            selection_method=group["selection_method"], validation_pending=group["validation_pending"], **extra,
        ))

    bearing_map = {f"bearing_OD{od}": (code, od, width) for code, _, od, width in BEARINGS}
    if interface in bearing_map:
        code, od, width = bearing_map[interface]
        if nominal != od:
            raise BuildError(f"{interface} nominal must match the bearing OD {od} mm.")
        outer, height = od + 8, width + 1.4
        if min(candidates) <= od - 1.4 or max(candidates) > outer - 4:
            raise BuildError(f"{interface} candidates would remove the floor or leave less than 2 mm radial wall.")
        sx, sy = 3 * outer + 6, outer
        p.box(outer / 2, 1.5, 0, 2 * (outer + 3), 2.4, 1.2)
        for i, seat in enumerate(candidates):
            cx, cy = outer / 2 + i * (outer + 3), outer / 2
            p.cyl(cx, cy, 0, outer, height)
            p.cyl(cx, cy, -.1, od - 1.4, height + .2, True)
            p.cyl(cx, cy, 1.2, seat, width + .4, True)
            p.cone(cx, cy, height - .6, seat, seat + 1.2, .7, True)
            for angle in (30, 150, 270):
                radius = od / 2 - .3
                p.cyl(cx + radius * math.cos(math.radians(angle)),
                      cy + radius * math.sin(math.radians(angle)), -.1, 1.6, 1.5, True)
            p.label(str(i + 1), cx, 2.2, height, 2.2)
            feature(i, cx, cy, bearing_codes=code, bearing_width_mm=width, boss_outer_mm=outer,
                    floor_mm=1.2, seat_depth_mm=width + .2, lead_in_mm=.6,
                    underside_opening_mm=od - 1.4, purpose="Hand slip fit; retain bearing separately.")
    elif interface.startswith("shaft_clearance_ID") or interface.startswith("bolt_clearance_M"):
        shaft = interface.startswith("shaft_clearance_ID")
        allowed = {f"shaft_clearance_ID{n}": n for n in range(3, 9)} if shaft else {"bolt_clearance_M3": 3, "bolt_clearance_M4": 4}
        if interface not in allowed or nominal != allowed[interface]:
            raise BuildError(f"Unsupported shaft or bolt interface: {interface}.")
        if min(candidates) < nominal - .5 or max(candidates) > nominal + 2:
            raise BuildError(f"{interface} correction exceeds this clearance coupon's range.")
        thickness = 2 if shaft else 4
        pitch = max(12, max(candidates) + 6)
        sx, sy = 3 * pitch, 18
        p.box(0, 0, 0, sx, sy, thickness)
        for i, bore in enumerate(candidates):
            cx, cy = pitch * (i + .5), 7
            p.cyl(cx, cy, -.1, bore, thickness + .2, True)
            p.label(str(i + 1), cx, 14, thickness, 2.2)
            feature(i, cx, cy, wall_depth_mm=thickness, purpose="Metal shaft or bolt through-hole clearance.")
    elif interface in ("nut_trap_M3", "nut_trap_M4"):
        metric, af, depth = (3, 5.5, 2.8) if interface.endswith("M3") else (4, 7, 3.6)
        if nominal != af or min(candidates) < af - .5 or max(candidates) > af + 2:
            raise BuildError(f"{interface} dimensions do not match this nut coupon.")
        pitch = max(14, max(candidates) + 8)
        sx, sy = 3 * pitch, max(18, 2 * max(candidates) / math.sqrt(3) + 8)
        p.box(0, 0, 0, sx, sy, 6)
        for i, across_flats in enumerate(candidates):
            cx, cy = pitch * (i + .5), sy / 2
            radius = across_flats / math.sqrt(3)
            points = [[cx + radius * math.cos(math.pi / 6 + j * math.pi / 3),
                       cy + radius * math.sin(math.pi / 6 + j * math.pi / 3)] for j in range(6)]
            p.poly(points, 6 - depth, depth + .1, True)
            p.cyl(cx, cy, -.1, metric + .5, 6.2, True)
            p.label(str(i + 1), cx, 2, 6, 2)
            feature(i, cx, cy, pocket_depth_mm=depth, plate_height_mm=6,
                    purpose="Nut across-flats and height; check fit with the actual screw.")
    elif interface in ("heat_insert_M3", "heat_insert_M4"):
        height, depth = (8, 6) if interface.endswith("M3") else (10, 8)
        if min(candidates) < 2 or max(candidates) > 6:
            raise BuildError(f"{interface} candidates leave insufficient wall in the original 10 mm boss.")
        sx, sy = 42, 14
        p.box(0, 0, 0, sx, sy, 2)
        for i, bore in enumerate(candidates):
            cx, cy = 7 + i * 14, 7
            p.cyl(cx, cy, 0, 10, height)
            p.cyl(cx, cy, height - depth, bore, depth + .1, True)
            p.cone(cx, cy, height - .6, bore, bore + .8, .7, True)
            p.label(str(i + 1), cx, cy - 4, height, 2)
            feature(i, cx, cy, hole_depth_mm=depth, boss_height_mm=height, boss_outer_mm=10,
                    hardware_od_mm=group["basis"]["measured_hardware_mm"], hardware_length_mm=None,
                    purpose="Heat insertion trial. Measure insert length before heating; no joint-load claim.")
    elif interface == "servo_body_width":
        if min(candidates) < 5 or max(candidates) > 60:
            raise BuildError("Servo width falls outside this U-gauge's supported range.")
        sx, sy = sum(value + 6 for value in candidates) + 6, 24
        p.box(0, 0, 0, sx, 5, 8)
        left = 0
        for i, gap in enumerate(candidates):
            p.box(left, 4, 0, 3, 20, 8)
            p.box(left + 3 + gap, 4, 0, 3, 20, 8)
            p.label(str(i + 1), left + 3 + gap / 2, 2.5, 8, 2.2)
            feature(i, left + 3 + gap / 2, 14, gauge_height_mm=8, wall_mm=3,
                    purpose="Case width only; mounting ears, length and cable exit remain unvalidated.")
            left += gap + 9
    elif interface == "wire_slot":
        if max(candidates) > 50:
            raise BuildError("Wire slot exceeds the supported connector gauge width.")
        pitch = max(12, max(candidates) + 8)
        sx, sy = 3 * pitch, 17
        p.box(0, 0, 0, sx, sy, 2)
        for i, gap in enumerate(candidates):
            cx, cy = pitch * (i + .5), 7
            p.box(cx - gap / 2, cy - 3.5, -.1, gap, 7, 2.2, True)
            p.label(str(i + 1), cx, 14, 2, 2.2)
            feature(i, cx, cy, wall_depth_mm=2, slot_length_mm=7,
                    purpose="Pass the actual connector and sleeved loom; deburr before use.")
    elif interface.startswith("clamp"):
        raise BuildError("Clamp refinement needs engineering review of jaw stiffness, screw loading and face gap.")
    else:
        raise BuildError(f"Unsupported interface {interface}; no substitute geometry was generated.")
    return p, features, sx, sy


def make_refined_recipe(request: dict) -> dict:
    groups = request.get("interface_requests")
    if not isinstance(groups, list) or not 1 <= len(groups) <= 3:
        raise BuildError("Choose one to three measured interface groups for a refinement bed.")
    profile = groups[0].get("print_profile")
    if any(group.get("print_profile") != profile for group in groups):
        raise BuildError("A single bed requires one shared print profile; submit a CSV containing one profile.")
    unplaced = [_part_for_group(group, i + 1) for i, group in enumerate(groups)]
    parts, features, placements = [], [], []
    x, y, shelf_height = 2., 2., 0.
    for part, items, width, height in sorted(unplaced, key=lambda item: -item[2]):
        if width > 206 or height > 206:
            raise BuildError("A coupon group does not fit within the 210 mm bed with 2 mm edge clearance.")
        if x + width > 208:
            x, y, shelf_height = 2., y + shelf_height + 3, 0.
        if y + height > 208:
            raise BuildError("Refinement groups exceed the 210 mm bed; reduce the submitted interfaces.")
        for op in part.adds + part.cuts:
            if op["kind"] == "polygon":
                op["points"] = [[px + x, py + y] for px, py in op["points"]]
            else:
                op["x"] += x
                op["y"] += y
        for feature in items:
            feature["x_mm"] += x
            feature["y_mm"] += y
        parts.append(part.recipe())
        features.extend(items)
        placements.append(dict(part=part.name, x_mm=x, y_mm=y, width_mm=width, height_mm=height))
        x += width + 3
        shelf_height = max(shelf_height, height)
    return dict(
        schema_version=1, units="mm", purpose="second_fit_bed", production_release=False,
        source=copy.deepcopy(request["source"]), print_profile=copy.deepcopy(profile),
        bed_limit_mm=[210, 210], parts=parts, features=features, placements=placements,
        notes=["Numbers 1, 2, 3 on each object correspond to ascending candidate CAD dimensions in the manifest.",
               "Preserve axes Z and the measured print profile; this bed tests fit, not structural capacity.",
               "Insert hardware length and hot insertion remain unvalidated."],
    )


def _export(recipe: dict, request_path: Path, output: Path) -> dict:
    import cadquery as cq
    import trimesh

    solids, meshes, checks = [], {}, []
    for part in recipe["parts"]:
        adds = [primitive(cq, op) for op in part["ops"] if op["op"] == "add"]
        body = adds[0].fuse(*adds[1:]).clean() if len(adds) > 1 else adds[0]
        cuts = [primitive(cq, op) for op in part["ops"] if op["op"] == "cut"]
        if cuts:
            body = body.cut(*cuts).clean()
        if not body.isValid() or len(body.Solids()) != 1:
            raise BuildError(f"{part['name']} is not one valid solid.")
        stl = output / f"{part['name']}.stl"
        cq.exporters.export(body, str(stl), tolerance=.03, angularTolerance=.08)
        mesh = trimesh.load_mesh(stl, process=True)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
            raise BuildError(f"{part['name']} mesh failed volume or closed-surface checks.")
        solids.append(body)
        meshes[part["name"]] = mesh
        checks.append(dict(part=part["name"], brep_valid=True, solid_count=1,
                           watertight=True, winding_consistent=True, volume_mm3=body.Volume(),
                           bounds_mm=mesh.bounds.tolist(), triangles=len(mesh.faces)))
    all_mesh = trimesh.util.concatenate(list(meshes.values()))
    low, high = all_mesh.bounds
    if low[0] < 0 or low[1] < 0 or low[2] < -1e-5 or high[0] > 210 or high[1] > 210:
        raise BuildError(f"CAD exceeds bed coordinates: {all_mesh.bounds.tolist()}.")
    compound = cq.Compound.makeCompound(solids)
    cq.exporters.export(compound, str(output / "MIST_BED2_ALL_PARTS.step"))
    cq.exporters.export(compound, str(output / "MIST_BED2_ALL_PARTS.stl"), tolerance=.03, angularTolerance=.08)
    export_3mf(meshes, output / "MIST_BED2_ALL_PARTS.3mf")
    (output / "coupon_recipe.json").write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    (output / "feature_manifest.json").write_text(json.dumps(recipe["features"], indent=2) + "\n", encoding="utf-8")
    with (output / "feedback_BED2.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for feature in recipe["features"]:
            row = {field: feature.get(field, "") for field in FIELDS}
            row.update(recipe["print_profile"])
            row["fit_result"] = "not_tested"
            writer.writerow(row)
    validation = dict(
        schema_version=1, status="geometry_checks_passed_physical_fit_pending", production_release=False,
        request_path=str(request_path.resolve()), request_sha256=hashlib.sha256(request_path.read_bytes()).hexdigest(),
        source_csv=recipe["source"], part_count=len(solids), feature_count=len(recipe["features"]),
        bounds_mm=all_mesh.bounds.tolist(), extent_mm=all_mesh.extents.tolist(),
        print_profile=recipe["print_profile"], tessellation_mm=.03, checks=checks,
        unvalidated=["Printed fit", "Insert length and hot insertion", "Structural loads", "Printer setup"],
    )
    (output / "validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    return validation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_json", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise BuildError("Output directory already exists; choose a new directory to preserve its files.")
        if not args.out.parent.is_dir():
            raise BuildError("Output parent directory must already exist.")
        request = load_validated_request(args.request_json)
        recipe = make_refined_recipe(request)
        with tempfile.TemporaryDirectory(prefix=".mist_refinement_", dir=args.out.parent) as staging:
            stage = Path(staging)
            validation = _export(recipe, args.request_json, stage)
            # Check the evidence again before publishing files if CAD took a long time.
            if load_validated_request(args.request_json) != request:
                raise BuildError("Request changed during CAD generation; no output was published.")
            os.rename(stage, args.out)
        print(json.dumps(validation, indent=2))
        return 0
    except (BuildError, OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        print(f"No second bed was published: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
