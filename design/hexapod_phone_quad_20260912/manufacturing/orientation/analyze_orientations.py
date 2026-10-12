"""Read-only print orientation screening of the released STL geometry.

Projected overhang area is an exact triangle sum. Vertical support intervals
are sampled on a deterministic XY grid and are geometric estimates, not slicing.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAD = ROOT / "cad" / "output"
PITCH = 0.5
ORIENTATIONS = {
    "current": (0, 0, 0),
    "flip_x180": (180, 0, 0),
    "side_x90": (90, 0, 0),
    "side_xminus90": (-90, 0, 0),
    "side_y90": (0, 90, 0),
    "side_yminus90": (0, -90, 0),
    "tilt_x45": (45, 0, 0),
    "tilt_xminus45": (-45, 0, 0),
    "tilt_y45": (0, 45, 0),
    "tilt_yminus45": (0, -45, 0),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rotation(angles):
    x, y, z = np.radians(angles)
    rx = np.array([[1, 0, 0], [0, np.cos(x), -np.sin(x)], [0, np.sin(x), np.cos(x)]])
    ry = np.array([[np.cos(y), 0, np.sin(y)], [0, 1, 0], [-np.sin(y), 0, np.cos(y)]])
    rz = np.array([[np.cos(z), -np.sin(z), 0], [np.sin(z), np.cos(z), 0], [0, 0, 1]])
    return rz @ ry @ rx


def oriented(mesh, angles):
    result = mesh.copy()
    transform = np.eye(4)
    transform[:3, :3] = rotation(angles)
    result.apply_transform(transform)
    result.apply_translation(-result.bounds[0])
    return result


def raster_intervals(mesh, pitch=PITCH):
    """Rasterize exact triangle planes, then pair downward faces to solids below.

    Each raster cell has one ray. All nonvertical triangle intersections are
    sorted by height. A downward overhang uses the last upward crossing or bed
    as its lower endpoint. Overlapping support segments in a column remain
    separate because solid material interrupts them.
    """
    width = int(math.ceil(mesh.extents[0] / pitch)) + 1
    hits = []
    for triangle, normal in zip(mesh.triangles, mesh.face_normals):
        if abs(normal[2]) < 1e-7:
            continue
        low = np.maximum(0, np.floor(triangle[:, :2].min(axis=0) / pitch).astype(int))
        high = np.ceil(triangle[:, :2].max(axis=0) / pitch).astype(int)
        # Unequal noncentral offsets avoid rays exactly on many shared edges.
        xx, yy = np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1))
        xx, yy = xx.ravel(), yy.ravel()
        p = np.column_stack(((xx + .371) * pitch, (yy + .619) * pitch))
        a, b, c = triangle
        v0, v1 = b[:2] - a[:2], c[:2] - a[:2]
        denom = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(denom) < 1e-10:
            continue
        d = p - a[:2]
        u = (d[:, 0] * v1[1] - v1[0] * d[:, 1]) / denom
        v = (v0[0] * d[:, 1] - d[:, 0] * v0[1]) / denom
        inside = (u >= 0) & (v >= 0) & (u + v < 1)
        if not inside.any():
            continue
        z = a[2] + u[inside] * (b[2] - a[2]) + v[inside] * (c[2] - a[2])
        hits.append(np.column_stack((xx[inside] + width * yy[inside], z, np.full(len(z), normal[2]))))
    if not hits:
        return dict(sampled_overhang_mm2=0, support_envelope_mm3=0,
                    bed_support_contact_mm2=0, model_support_contact_mm2=0,
                    short_internal_gap_mm2=0, gap_p95_mm=0, max_gap_mm=0,
                    raster_pitch_mm=pitch)
    hits = np.concatenate(hits)
    hits = hits[np.lexsort((-hits[:, 2], hits[:, 1], hits[:, 0]))]
    # Column offsets exceed any part height, so accumulation resets at each ray.
    column_base = hits[:, 0] * 10000
    upward = hits[:, 2] > 1e-7
    last_surface = np.maximum.accumulate(column_base + np.where(upward, hits[:, 1], 0)) - column_base
    overhang = (hits[:, 2] <= -math.cos(math.radians(45)) + 1e-7) & (hits[:, 1] > .21)
    gap = hits[overhang, 1] - last_surface[overhang]
    below = last_surface[overhang]
    valid = gap > .21
    gap, below = gap[valid], below[valid]
    area = pitch ** 2
    answer = dict(sampled_overhang_mm2=float(len(gap) * area),
                support_envelope_mm3=float(np.sum(np.maximum(0, gap - .2)) * area),
                bed_support_contact_mm2=float(np.sum(below <= .2) * area),
                model_support_contact_mm2=float(np.sum(below > .2) * area),
                short_internal_gap_mm2=float(np.sum((below > .2) & (gap < 6)) * area),
                gap_p95_mm=float(np.percentile(gap, 95)) if len(gap) else 0,
                max_gap_mm=float(np.max(gap)) if len(gap) else 0,
                raster_pitch_mm=pitch)
    strict50 = (hits[:, 2] < -math.cos(math.radians(40)) - 1e-7) & (hits[:, 1] > .21)
    gap50 = hits[strict50, 1] - last_surface[strict50]
    answer["sampled_overhang_50_mm2"] = float(np.sum(gap50 > .21) * area)
    answer["support_envelope_50_mm3"] = float(np.maximum(0, gap50 - .2).sum() * area)
    return answer


def metrics(mesh, angles, original_rotation, sku, raster=True):
    m = oriented(mesh, angles)
    z = m.triangles[:, :, 2]
    nz = m.face_normals[:, 2]
    projected = m.area_faces * np.maximum(0, -nz)
    offbed = z.max(axis=1) > .21
    mask45 = (nz <= -math.cos(math.radians(45)) + 1e-7) & offbed
    mask50 = (nz < -math.cos(math.radians(40)) - 1e-7) & offbed
    bed = z.max(axis=1) < 1e-5
    layer_axis = None
    if sku.startswith(("femur", "tibia", "coxa")):
        layer_axis = np.array([1, 0, 0])
    elif sku == "phone_cradle_rear_frame":
        layer_axis = np.array([0, 0, 1])
    q = dict(dim_x_mm=float(m.extents[0]), dim_y_mm=float(m.extents[1]), height_mm=float(m.extents[2]),
             footprint_box_mm2=float(np.prod(m.extents[:2])),
             fits_225_bed_4mm_brim=bool(np.all(m.extents[:2] + 8 <= 225)),
             exact_bed_contact_mm2=float(projected[bed].sum()),
             projected_overhang_45_inclusive_mm2=float(projected[mask45].sum()),
             projected_overhang_50_strict_mm2=float(projected[mask50].sum()),
             boundary_45_mm2=float(projected[(np.abs(nz + math.cos(math.radians(45))) < 1e-6) & offbed].sum()))
    if layer_axis is not None:
        print_axis = rotation(angles) @ rotation(original_rotation) @ layer_axis
        c = abs(float(print_axis[2]))
        q.update(nominal_axial_layer_normal_fraction=c*c,
                 nominal_axial_layer_shear_fraction=c*math.sqrt(max(0, 1-c*c)))
    else:
        q.update(nominal_axial_layer_normal_fraction=None, nominal_axial_layer_shear_fraction=None)
    if raster:
        q.update(raster_intervals(m))
    return q


def self_test():
    flat = trimesh.creation.box([20, 20, 4])
    flat.apply_translation([10, 10, 2])
    q = raster_intervals(flat)
    assert q["sampled_overhang_mm2"] == 0, q
    # A 10 by 10 roof at Z10 has a 2 by 2 centre post. Analytic unsupported
    # area is 96 mm2, all to bed, and 960 mm3 before the 0.2 mm support gap.
    roof = trimesh.creation.box([10, 10, 2])
    roof.apply_translation([5, 5, 11])
    post = trimesh.creation.box([2, 2, 10])
    post.apply_translation([5, 5, 5])
    q = raster_intervals(trimesh.util.concatenate([roof, post]))
    assert q["sampled_overhang_mm2"] == 96, q
    assert abs(q["support_envelope_mm3"] - 940.8) < 1e-6, q
    assert q["bed_support_contact_mm2"] == 96, q
    return {"flat_plate": "passed", "elevated_roof_on_post": "passed"}


def run():
    tests = self_test()
    manifest_path = CAD / "assembly_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    before = sha(manifest_path)
    rows, sources = [], []
    for entry in manifest["print_parts"]:
        path = CAD / entry["stl"]
        mesh = trimesh.load_mesh(path, process=True)
        assert mesh.is_watertight, entry["sku"]
        source_hash = sha(path)
        sources.append(dict(sku=entry["sku"], path=str(path), hash=source_hash))
        for name, angles in ORIENTATIONS.items():
            result = metrics(mesh, angles, entry["print_rotation"], entry["sku"])
            row = dict(sku=entry["sku"], quantity=entry["quantity"], orientation=name,
                       additional_rotation_deg=list(angles), source_stl_hash=source_hash, **result)
            rows.append(row)
        current = next(r for r in rows if r["sku"] == entry["sku"] and r["orientation"] == "current")
        print(entry["sku"], "current overhang", round(current["projected_overhang_45_inclusive_mm2"]),
              "support envelope", round(current["support_envelope_mm3"]), flush=True)
    assert before == sha(manifest_path), "Source manifest changed during analysis; rerun against a fixed revision."
    for source in sources:
        assert sha(source["path"]) == source["hash"], source
    data = dict(status="Geometric support screening; actual slicer cases are reported separately",
                source_manifest_hash=before, source_revision=manifest["revision"],
                script_hash=sha(__file__), source_stls=sources, self_tests=tests,
                orientation_reference="Additional rotations of the already print-oriented supplied STL",
                method={"raster_pitch_mm": PITCH,
                        "support_angle_from_vertical_deg": 45,
                        "top_gap_mm": .2,
                        "bed_exclusion_mm": .21,
                        "short_internal_gap_threshold_mm": 6,
                        "support_volume_meaning": "Air column envelope under sampled overhangs, before support density, interface, XY expansion, branches or bridge treatment",
                        "short_gap_meaning": "Support landing on the part in a gap below 6 mm; limited tool access flag, not proof of trapped support",
                        "stress_meaning": "Nominal uniaxial traction fractions on the layer plane: normal=cos(theta)^2, shear=abs(cos(theta)*sin(theta)); no material strength or safety factor implied"},
                results=rows)
    (HERE / "orientation_results.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    with (HERE / "orientation_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("COMPLETE", len(rows), "orientation cases", flush=True)


if __name__ == "__main__":
    run()
