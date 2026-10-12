"""Assign physical masses and aggregate CAD inertias for the 17 simulation links.

CAD dimensions are mm. Output inertia tensors are kg m^2 about the named COM,
with ordinary tensor off-diagonals (not negated products of inertia). Purchased
parts use their supplied nominal mass distributed uniformly over the envelope.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import math

import cadquery as cq
import numpy as np


LEG_NAMES = ("FL", "FR", "RL", "RR")
LINK_NAMES = ("base_link",) + tuple(
    f"{leg}_{link}" for leg in LEG_NAMES for link in ("yaw", "femur", "tibia", "wheel")
)
BODY_NOMINAL_MASS_G = {
    "H01_battery_HOOVO_3S_REFERENCE": 174.0,
    "H02_brain_phone_ENVELOPE": 155.0,
    "H03_face_phone_Mi9SE_REFERENCE": 155.0,
}
SUPPLEMENTAL_MASSES_KG = {"electronics": 0.250, "harness": 0.150, "extras": 0.050}


def _rigid_matrix(value, label):
    result = np.asarray(value, dtype=float)
    if result.shape != (4, 4) or not np.isfinite(result).all():
        raise ValueError(f"{label}: expected a finite 4x4 transform")
    rotation = result[:3, :3]
    if (not np.allclose(result[3], [0, 0, 0, 1], atol=1e-9, rtol=0)
            or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-8, rtol=0)
            or not np.isclose(np.linalg.det(rotation), 1.0, atol=1e-8, rtol=0)):
        raise ValueError(f"{label}: transform must contain a proper rigid rotation")
    return result


def _tensor(value, label):
    result = np.asarray(value, dtype=float)
    if result.shape != (3, 3) or not np.isfinite(result).all():
        raise ValueError(f"{label}: expected a finite 3x3 inertia tensor")
    if not np.allclose(result, result.T, atol=1e-12, rtol=1e-9):
        raise ValueError(f"{label}: inertia tensor is not symmetric")
    result = (result + result.T) / 2.0
    eigenvalues = np.linalg.eigvalsh(result)
    tolerance = max(1e-13, float(np.max(np.abs(eigenvalues))) * 1e-9)
    if eigenvalues[0] < -tolerance or eigenvalues[2] > sum(eigenvalues[:2]) + tolerance:
        raise ValueError(f"{label}: inertia eigenvalues violate rigid-body constraints")
    return result


def _shape_map(shapes, entries):
    if isinstance(shapes, Mapping):
        return shapes
    if len(shapes) != len(entries):
        raise ValueError("Shape list and entry list have different lengths")
    return {entry["assembly_name"]: shape for entry, shape in zip(entries, shapes)}


def _assigned_mass(entry, row, volume_mm3):
    part = entry["part"]
    category = part.get("category", row.get("category", "print"))
    if category == "visual_reference":
        return 0.0, dict(method="excluded_visual_reference", provenance="Visual reference has no physical mass.")
    if "mass_g" in part:
        mass_g = float(part["mass_g"])
        basis = dict(method="nominal_mass", provenance=part.get(
            "mass_provenance", "Nominal mass specified by the part recipe; not independently weighed."))
    elif entry["group"] == "body" and part["name"] in BODY_NOMINAL_MASS_G:
        mass_g = BODY_NOMINAL_MASS_G[part["name"]]
        basis = dict(method="body_nominal_mass", provenance=(
            "Body allocation: battery 174 g, brain phone 155 g, face phone 155 g. "
            "The printed phone frame is counted through its own solid."))
    else:
        density_default = 1.27 if category == "print" else 7.85
        density = float(part.get("density_g_cm3", row.get("assumed_density_g_cm3") or density_default))
        if part.get("free_shape_ops") and "mass_volume_cm3" not in row:
            raise ValueError(f"{entry['assembly_name']}: free-state mass volume was not supplied")
        volume_cm3 = float(row.get("mass_volume_cm3", volume_mm3 / 1000.0))
        if not math.isfinite(density) or density <= 0 or not math.isfinite(volume_cm3) or volume_cm3 <= 0:
            raise ValueError(f"{entry['assembly_name']}: invalid density or mass volume")
        mass_g = density * volume_cm3
        basis = dict(method="density_times_mass_volume", density_g_cm3=density,
                     mass_volume_cm3=volume_cm3, provenance=part.get("mass_provenance", (
                         "Solid PETG estimate at 1.27 g/cm^3; slicer infill is not applied."
                         if category == "print" and "density_g_cm3" not in part else
                         "Uniform material density over CAD geometry; hardware is not independently weighed.")))
        if category != "print" and "density_g_cm3" not in part and not row.get("assumed_density_g_cm3"):
            basis["fallback_assumption"] = "Unspecified hardware is treated as solid steel at 7.85 g/cm^3."
    if not math.isfinite(mass_g) or mass_g < 0:
        raise ValueError(f"{entry['assembly_name']}: assigned mass must be finite and nonnegative")
    return mass_g / 1000.0, basis


def _simulation_link(entry):
    group = entry["group"]
    link = entry["part"].get("link", "body")
    if group == "body" or link in ("body", "base", "base_link"):
        return "base_link"
    link = "yaw" if link == "pod" else link
    name = f"{group}_{link}"
    if name not in LINK_NAMES:
        raise ValueError(f"{entry['assembly_name']}: unsupported simulation link {name}")
    return name


def _sum_properties(items):
    mass = sum(item["mass_kg"] for item in items)
    center = (sum((item["mass_kg"] * item["com_world_m"] for item in items), np.zeros(3)) / mass
              if mass else np.zeros(3))
    inertia = np.zeros((3, 3))
    for item in items:
        offset = item["com_world_m"] - center
        inertia += item["inertia_com_world_kg_m2"] + item["mass_kg"] * (
            np.dot(offset, offset) * np.eye(3) - np.outer(offset, offset))
    return mass, center, _tensor(inertia, "Aggregate inertia")


def enrich_report(report, local_shapes, world_shapes, entries, params):
    """Mutate and return a report containing parts and specifications.

    Shape mappings use assembly_name keys; sequences may follow entries order.
    Per-leg specifications must provide frames_world_mm for yaw/femur/tibia/wheel.
    Part links body/pod map to base_link/yaw. Internal transmission rotors remain
    assigned to their recipe link, with that missing internal DOF recorded.
    """
    entries = list(entries)
    local_shapes = _shape_map(local_shapes, entries)
    world_shapes = _shape_map(world_shapes, entries)
    rows = report.setdefault("parts", [])
    by_name = {row["assembly_name"]: row for row in rows}
    if len(by_name) != len(rows):
        raise ValueError("Report contains duplicate assembly names")
    if len({entry["assembly_name"] for entry in entries}) != len(entries):
        raise ValueError("Entries contain duplicate assembly names")
    frames = {"base_link": np.eye(4)}
    present_legs = {entry["group"] for entry in entries if entry["group"] in LEG_NAMES}
    specifications = report.get("specifications", {})
    for leg in LEG_NAMES:
        frame_values = specifications.get(leg, {}).get("frames_world_mm", {})
        for link in ("yaw", "femur", "tibia", "wheel"):
            if leg in present_legs and link not in frame_values:
                raise ValueError(f"Missing specifications.{leg}.frames_world_mm.{link}")
            frames[f"{leg}_{link}"] = _rigid_matrix(frame_values.get(link, np.eye(4)), f"{leg}_{link}")

    grouped = {name: [] for name in LINK_NAMES}
    all_items = []
    for entry in entries:
        name, part = entry["assembly_name"], entry["part"]
        row = by_name.get(name)
        if row is None:
            row = dict(assembly_name=name, name=part["name"], group=entry["group"],
                       category=part.get("category", "print"), link=part.get("link", "body"))
            rows.append(row)
            by_name[name] = row
        shape, placed = local_shapes[name], world_shapes[name]
        volume = float(shape.Volume())
        if not shape.isValid() or not placed.isValid() or not math.isfinite(volume) or volume <= 0:
            raise ValueError(f"{name}: mass properties require valid positive-volume solids")
        transform = _rigid_matrix(entry.get("transform", part.get("transform", np.eye(4))), name)
        rotation = transform[:3, :3]
        center_local_mm = np.asarray(shape.Center().toTuple(), dtype=float)
        center_world_mm = np.asarray(placed.Center().toTuple(), dtype=float)
        predicted_center = rotation @ center_local_mm + transform[:3, 3]
        if not np.allclose(predicted_center, center_world_mm, atol=1e-5, rtol=0):
            raise ValueError(f"{name}: local/world COM does not match its rigid transform")
        mass, basis = _assigned_mass(entry, row, volume)
        # OCC's solid-volume tensor is about COM, in mm^5. Dividing by volume
        # gives mm^2; multiplying by kg and 1e-6 gives the physical kg m^2.
        geometric_tensor = np.asarray(cq.Shape.matrixOfInertia(shape), dtype=float)
        local_inertia = _tensor(geometric_tensor * (mass / volume / 1e6), name)
        world_inertia = _tensor(rotation @ local_inertia @ rotation.T, name)
        link = _simulation_link(entry)
        rigid_group = part.get("rigid_group", part.get("link", "body"))
        internal_dof = ("rotor" in str(rigid_group).lower())
        row.update(assigned_mass_g=mass * 1000.0, assigned_mass_kg=mass,
                   mass_basis=basis, simulation_link=link, rigid_group=rigid_group,
                   center_partlocal_mm=center_local_mm.tolist(), center_hipplane_mm=center_world_mm.tolist(),
                   inertia_com_partlocal_kg_m2=local_inertia.tolist(),
                   inertia_com_world_kg_m2=world_inertia.tolist(),
                   inertia_distribution="Assigned mass uniformly distributed over assembled CAD solid.")
        if internal_dof:
            row["internal_dof_approximation"] = (
                f"{rigid_group} rotates within {link}; its mass and pose tensor are lumped into that "
                "simulation link. Independent rotor kinetic energy and gyroscopic coupling are omitted.")
        item = dict(name=name, mass_kg=mass, com_world_m=center_world_mm / 1000.0,
                    inertia_com_world_kg_m2=world_inertia, supplemental=False,
                    internal_dof_approximation=row.get("internal_dof_approximation"))
        grouped[link].append(item)
        all_items.append(item)

    supplemental = []
    for name, mass in SUPPLEMENTAL_MASSES_KG.items():
        center = np.asarray(params.get("mass", {}).get(f"{name}_com_m", [0.0, 0.0, 0.0]), dtype=float)
        if center.shape != (3,) or not np.isfinite(center).all():
            raise ValueError(f"mass.{name}_com_m must contain three finite metre coordinates")
        inertia = np.eye(3) * mass * 0.1 ** 2 / 6.0
        item = dict(name=f"supplemental_{name}", mass_kg=mass, com_world_m=center,
                    inertia_com_world_kg_m2=inertia, supplemental=True, internal_dof_approximation=None)
        grouped["base_link"].append(item)
        all_items.append(item)
        supplemental.append(dict(name=item["name"], assigned_mass_g=mass * 1000.0,
                                 simulation_link="base_link", com_world_m=center.tolist(),
                                 inertia_com_world_kg_m2=inertia.tolist(), box_size_m=[0.1, 0.1, 0.1],
                                 provenance=("One body allocation, uniformly distributed in a 100 mm cube. "
                                             "COM uses mass." + name + "_com_m when supplied, otherwise the "
                                             "hip-plane origin. Position and distribution are unmeasured.")))

    links = {}
    for name in LINK_NAMES:
        mass, center, world_inertia = _sum_properties(grouped[name])
        frame = frames[name]
        rotation = frame[:3, :3]
        local_center = rotation.T @ (center - frame[:3, 3] / 1000.0)
        local_inertia = _tensor(rotation.T @ world_inertia @ rotation, name)
        links[name] = dict(mass_kg=mass, com_local_m=local_center.tolist(),
                           inertia_com_local_kg_m2=local_inertia.tolist(), com_world_m=center.tolist(),
                           inertia_com_world_kg_m2=world_inertia.tolist(), frame_local_to_world_mm=frame.tolist(),
                           principal_inertia_kg_m2=np.linalg.eigvalsh(local_inertia).tolist(),
                           parts=[item["name"] for item in grouped[name] if not item["supplemental"]],
                           supplemental_items=[item["name"] for item in grouped[name] if item["supplemental"]],
                           internal_dof_approximations=[item["internal_dof_approximation"] for item in grouped[name]
                                                       if item["internal_dof_approximation"]],
                           has_geometry=any(not item["supplemental"] for item in grouped[name]))
    total_mass, total_com, total_inertia = _sum_properties(all_items)
    if not np.isclose(total_mass, sum(link["mass_kg"] for link in links.values()), atol=1e-12, rtol=1e-12):
        raise RuntimeError("Part and link total masses disagree")
    report["link_mass_properties"] = links
    report["supplemental_mass_properties"] = supplemental
    report["physical_mass_properties"] = dict(
        units=dict(mass="kg", com="m", inertia="kg m^2", cad_transforms="mm"),
        assigned_mass_kg=total_mass, assigned_mass_g=total_mass * 1000.0,
        geometry_assigned_mass_kg=sum(row["assigned_mass_kg"] for row in rows),
        supplemental_mass_kg=sum(SUPPLEMENTAL_MASSES_KG.values()),
        com_world_m=total_com.tolist(), inertia_com_world_kg_m2=total_inertia.tolist(),
        tensor_convention="Symmetric inertia tensor about COM; off-diagonal entries retain the tensor signs.",
        method="OCC COM tensor / volume * assigned_mass_kg * 1e-6, rigid rotation, then parallel-axis aggregation.",
        completeness="Complete 17-link allocation" if all(link["has_geometry"] for link in links.values()) else
                     "Partial geometry; absent links are retained with zero geometric mass.",
        assumptions=["Purchased-part nominal mass is distributed uniformly over its simplified envelope.",
                     "Printed mass uses solid material volume, including free-state pad volume; no infill reduction.",
                     "Compressed pads retain their free-state mass in the assembled shape distribution.",
                     "Electronics 250 g, harness 150 g and extras 50 g are each added once to base_link.",
                     "Internal transmission rotors remain lumped into their declared simulation link."])
    return report


def _self_test():
    """Check analytical box inertia, rotation, translation and parallel axes."""
    shape = cq.Workplane("XY").box(10, 20, 30).val()
    mass = 2.0
    expected = np.diag([mass * (0.02 ** 2 + 0.03 ** 2) / 12,
                        mass * (0.01 ** 2 + 0.03 ** 2) / 12,
                        mass * (0.01 ** 2 + 0.02 ** 2) / 12])
    actual = np.asarray(cq.Shape.matrixOfInertia(shape)) * mass / shape.Volume() / 1e6
    assert np.allclose(actual, expected, atol=1e-14, rtol=1e-12)
    entries, local, world = [], {}, {}
    angle = math.radians(37)
    rotation = np.array([[math.cos(angle), -math.sin(angle), 0],
                         [math.sin(angle), math.cos(angle), 0], [0, 0, 1]])
    for index, offset in enumerate(([-50, 20, 30], [50, 20, 30])):
        name = f"body__box{index}"
        transform = np.eye(4)
        transform[:3, :3], transform[:3, 3] = rotation, offset
        entries.append(dict(assembly_name=name, group="body", transform=transform.tolist(),
                            part=dict(name=f"box{index}", category="hardware_reference", mass_g=2000)))
        local[name] = shape
        world[name] = shape.rotate((0, 0, 0), (0, 0, 1), 37).translate(offset)
    report = enrich_report(dict(parts=[], specifications={}), local, world, entries, {})
    first = report["parts"][0]
    assert np.allclose(first["inertia_com_world_kg_m2"], rotation @ expected @ rotation.T, atol=1e-14)
    translated_occ = np.asarray(cq.Shape.matrixOfInertia(world[entries[0]["assembly_name"]]))
    assert np.allclose(translated_occ * mass / shape.Volume() / 1e6,
                       first["inertia_com_world_kg_m2"], atol=1e-14)
    base = report["link_mass_properties"]["base_link"]
    assert tuple(report["link_mass_properties"]) == LINK_NAMES
    assert np.isclose(base["mass_kg"], 4.45)
    center = np.array([0, 4 * 0.02 / 4.45, 4 * 0.03 / 4.45])
    expected_sum = 2 * rotation @ expected @ rotation.T
    for offset in (np.array([-0.05, 0.02, 0.03]), np.array([0.05, 0.02, 0.03])):
        displacement = offset - center
        expected_sum += 2 * (displacement @ displacement * np.eye(3) - np.outer(displacement, displacement))
    expected_sum += np.eye(3) * 0.45 * 0.1 ** 2 / 6
    expected_sum += 0.45 * (center @ center * np.eye(3) - np.outer(center, center))
    assert np.allclose(base["com_local_m"], center, atol=1e-14)
    assert np.allclose(base["inertia_com_local_kg_m2"], expected_sum, atol=1e-14)
    assert len(report["supplemental_mass_properties"]) == 3
    json.dumps(report, allow_nan=False)
    frame = np.eye(4)
    frame[:3, :3], frame[:3, 3] = rotation, [100, -30, 80]
    local_offset = np.array([5.0, 7.0, -11.0])
    leg_shape = shape.translate(local_offset.tolist())
    leg_world = leg_shape.rotate((0, 0, 0), (0, 0, 1), 37).translate(frame[:3, 3].tolist())
    leg_entry = dict(assembly_name="FL__rotor", group="FL", transform=frame.tolist(),
                     part=dict(name="rotor", category="hardware_reference", mass_g=2000,
                               link="femur", rigid_group="knee_input_rotor"))
    leg_report = enrich_report(dict(parts=[], specifications={"FL": {"frames_world_mm": {
        link: frame.tolist() for link in ("yaw", "femur", "tibia", "wheel")}}}),
        [leg_shape], [leg_world], [leg_entry], {})
    femur = leg_report["link_mass_properties"]["FL_femur"]
    assert np.allclose(femur["com_local_m"], local_offset / 1000, atol=1e-14)
    assert np.allclose(femur["inertia_com_local_kg_m2"], expected, atol=1e-14)
    assert len(femur["internal_dof_approximations"]) == 1
    visual = dict(leg_entry, part=dict(name="visual", category="visual_reference", mass_g=2000))
    assert _assigned_mass(visual, {}, shape.Volume())[0] == 0
    battery = dict(assembly_name="body__battery", group="body",
                   part=dict(name="H01_battery_HOOVO_3S_REFERENCE", category="hardware_reference"))
    assert _assigned_mass(battery, {}, shape.Volume())[0] == 0.174
    pad = dict(leg_entry, part=dict(name="pad", category="print", density_g_cm3=1.2, free_shape_ops=[{}]))
    assert np.isclose(_assigned_mass(pad, dict(mass_volume_cm3=12), shape.Volume())[0], 0.0144)
    return dict(passed=True, checks=["analytical_box", "rotation", "translation_invariance",
                                    "parallel_axis_aggregation", "supplemental_mass_once", "17_links", "finite_json",
                                    "link_frame_COM_and_inertia", "internal_rotor_note", "visual_mass_zero",
                                    "body_nominal_mass", "free_state_pad_mass"],
                box_mass_kg=mass, box_inertia_com_kg_m2=actual.tolist())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()
    if arguments.self_test:
        print(json.dumps(_self_test(), indent=2, allow_nan=False), flush=True)
