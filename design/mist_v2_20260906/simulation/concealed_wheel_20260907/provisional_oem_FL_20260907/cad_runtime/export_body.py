"""Replay body_native's dimensional recipe through OpenCascade via CadQuery.

This independent solid-model replay supplies STEP, GLB, part STLs and a mass /
interference report when Fusion cannot run. It is not a native Fusion document.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh

from body_native import COLORS, _radial_points, body_spec


def tool_shape(op):
    kind = op["kind"]
    if kind == "box":
        return cq.Workplane("XY").box(*op["size"]).translate(op["center"]).val()
    if kind in ("cylinder", "annulus"):
        a = np.array(op["start"], dtype=float)
        b = np.array(op["end"], dtype=float)
        delta = b - a
        height = np.linalg.norm(delta)
        normal = tuple(delta / height)
        plane = cq.Plane(origin=tuple(a), normal=normal)
        wire = cq.Workplane(plane).circle(op["radius"])
        if kind == "annulus":
            wire = wire.circle(op["inner"])
        return wire.extrude(height).val()
    if kind == "radial_box":
        plane = cq.Plane(origin=(0, 0, op["z"] - op["height"] / 2))
        return cq.Workplane(plane).polyline(_radial_points(op)).close().extrude(op["height"]).val()
    if kind == "polygon":
        plane = cq.Plane(origin=op["origin"], xDir=op["x_axis"], normal=op["normal"])
        return cq.Workplane(plane).polyline(op["points"]).close().extrude(op["thickness"]).val()
    if kind == "revolve":
        return cq.Workplane("XZ").polyline(op["points"]).close().revolve(360, (0, 0), (0, 1)).val()
    raise ValueError(kind)


def build_solids(spec):
    solids, checks = {}, []
    for p in spec["parts"]:
        shape = None
        for i, op in enumerate(p["ops"]):
            tool = tool_shape(op)
            if shape is None:
                shape = tool
            else:
                old_volume = shape.Volume()
                shape = (shape.cut(tool) if op["mode"] == "cut" else shape.fuse(tool)).clean()
                if op["mode"] == "cut" and old_volume - shape.Volume() < 0.0001:
                    checks.append(dict(part=p["name"], operation=i + 1, issue="cut_removes_no_material"))
            if not shape.isValid():
                raise RuntimeError(f"Invalid OpenCascade shape: {p['name']} operation{i + 1}")
        if len(shape.Solids()) != 1:
            checks.append(dict(part=p["name"], issue="disconnected_solids", count=len(shape.Solids())))
        solids[p["name"]] = shape
        print(f"built {p['name']}: {shape.Volume()/1000:.2f}cm3", flush=True)
    return solids, checks


def export(parameters, output):
    params = json.loads(parameters.read_text(encoding="utf-8"))
    spec = body_spec(params)
    output.mkdir(parents=True, exist_ok=True)
    solids, checks = build_solids(spec)
    assembly = cq.Assembly(name="MIST_body_engineering_candidate")
    scene = trimesh.Scene()
    part_rows = []
    for p in spec["parts"]:
        shape = solids[p["name"]]
        rgba = COLORS[p["color"]]
        placed = shape.translate((0, 0, spec["assembly_z_offset"]))
        assembly.add(placed, name=p["name"], color=cq.Color(*(n / 255 for n in rgba)))
        vertices, triangles = placed.tessellate(0.22, 0.12)
        mesh = trimesh.Trimesh(vertices=[v.toTuple() for v in vertices], faces=triangles,
                               process=False, metadata=dict(name=p["name"], category=p["category"]))
        mesh.visual.vertex_colors = rgba
        scene.add_geometry(mesh, node_name=p["name"], geom_name=p["name"])
        bbox = shape.BoundingBox()
        center = shape.Center()
        row = dict(name=p["name"], category=p["category"], valid=shape.isValid(),
                   solid_count=len(shape.Solids()), volume_cm3=shape.Volume() / 1000,
                   solid_petg_mass_g=shape.Volume() / 1000 * 1.27 if p["category"] == "print" else None,
                   center_bodybottom_mm=center.toTuple(),
                   bounds_bodybottom_mm=[[bbox.xmin, bbox.ymin, bbox.zmin], [bbox.xmax, bbox.ymax, bbox.zmax]],
                   note=p["note"])
        part_rows.append(row)
        if p["category"] == "print":
            # These STL files retain assembly orientation and are not a print bed.
            stl_dir = output / "candidate_parts_not_print_release"
            stl_dir.mkdir(exist_ok=True)
            cq.exporters.export(shape, str(stl_dir / (p["name"] + ".stl")), tolerance=0.1, angularTolerance=0.15)
    assembly.export(str(output / "MIST_body_candidate.step"))
    (output / "MIST_body_candidate.glb").write_bytes(scene.export(file_type="glb"))
    # Pairwise checks separate positive-volume collisions from intended touching.
    overlaps = []
    print("Checking body component interference", flush=True)
    keys = list(solids)
    for i, an in enumerate(keys):
        a = solids[an]
        ba = a.BoundingBox()
        for bn in keys[i + 1:]:
            b = solids[bn]
            bb = b.BoundingBox()
            if (ba.xmin >= bb.xmax or bb.xmin >= ba.xmax or
                ba.ymin >= bb.ymax or bb.ymin >= ba.ymax or
                ba.zmin >= bb.zmax or bb.zmin >= ba.zmax):
                continue
            overlap = a.intersect(b).Volume()
            if overlap > 0.01:
                overlaps.append(dict(part_a=an, part_b=bn, overlap_mm3=round(overlap, 3)))
    prints = [p for p in part_rows if p["category"] == "print"]
    total_mass = sum(p["solid_petg_mass_g"] for p in prints)
    com = [sum(p["solid_petg_mass_g"] * p["center_bodybottom_mm"][j] for p in prints) / total_mass for j in range(3)]
    report = dict(status="offline_CAD_engineering_candidate_not_Fusion_execution_or_print_release",
                  kernel="CadQuery/OpenCascade", origin="hip mount plane", specification=spec,
                  printed_solid_mass_g=total_mass, printed_solid_com_bodybottom_mm=com,
                  printed_solid_com_hipplane_mm=[com[0], com[1], com[2] + spec["assembly_z_offset"]],
                  mass_note="1.27g/cm3 applied to fully solid CAD; slicer walls/infill and hardware weights must replace this estimate",
                  shape_checks=checks, positive_volume_interferences=overlaps, parts=part_rows)
    (output / "body_geometry_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "body_recipe.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(json.dumps(dict(printed_solid_mass_g=total_mass, shape_checks=checks, overlaps=overlaps), indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters", type=Path, default=Path(__file__).parents[1] / "simulation" / "parameters.json")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output")
    args = parser.parse_args()
    export(args.parameters, args.output)
