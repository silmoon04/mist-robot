"""Export a fixed R7 test leg and a floating four-leg robot from source CAD.

Moving-link inertials and all joint transforms are copied from the R7 URDF.
The quadruped removes the bench fixture's mesh-derived mass and inertia.
Hub, battery, harness and phone assumptions are recorded in the export report.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CONFIG_PATH = HERE / "config.json"
LEGS = ("FL", "FR", "RL", "RR")
JOINTS = ("yaw", "hip", "knee")
JOINT_NAMES = tuple(f"{leg}_{joint}" for leg in LEGS for joint in JOINTS)
NEUTRAL = np.radians([0.0, 30.0, 81.0])
LIMITS = np.radians([[-55.0, 55.0], [-30.0, 65.0], [5.0, 115.0]])
MOUNTS = {
    leg: {
        "xyz": [0.075 * math.cos(math.radians(deg)), 0.075 * math.sin(math.radians(deg)), 0.038],
        "yaw": math.radians(deg),
    }
    for leg, deg in zip(LEGS, (45, -45, 135, -135))
}


def load_config(path=CONFIG_PATH):
    return validate_config(json.loads(Path(path).read_text()))


def validate_config(cfg):
    """Reject unsupported clocks and invalid physical inputs before allocation."""
    def finite_tree(value):
        if isinstance(value, dict):
            for v in value.values(): finite_tree(v)
        elif isinstance(value, list):
            for v in value: finite_tree(v)
        elif isinstance(value, (int, float)) and (isinstance(value, bool) or not math.isfinite(value)):
            raise ValueError("configuration numbers must be finite")
    finite_tree(cfg)
    a, sim, ranges = cfg['actuator'], cfg['simulation'], cfg['randomization']
    if sim['physics_hz'] != 1000 or sim['control_hz'] != 50 or a['command_period_s'] != 1/sim['control_hz']:
        raise ValueError('supported timing is 1000 Hz physics and 50 Hz commands')
    for k in ('torque_limit_nm','rated_torque_nm','stall_torque_nm','no_load_speed_rad_s','command_speed_rad_s','position_quantization_rad','nominal_voltage_v'):
        if a[k] <= 0: raise ValueError(f'{k} must be positive')
    for k in ('kp_nm_rad','kd_nm_s_rad'):
        if len(a[k]) != 3 or min(a[k]) <= 0: raise ValueError(f'{k} requires three positive gains')
    for k in ('latency_s','position_deadband_rad','viscous_damping_nm_s_rad','coulomb_friction_nm'):
        if a[k] < 0: raise ValueError(f'{k} must be nonnegative')
    for k,v in ranges.items():
        if isinstance(v,list) and (len(v)!=2 or v[0]>v[1]): raise ValueError(f'{k} requires ordered bounds')
    for k in ('torque_scale','link_mass_scale','body_mass_scale','voltage_v','kp_scale'):
        if ranges[k][0] <= 0: raise ValueError(f'{k} requires positive bounds')
    for k in ('motor_latency_s','deadband_deg','friction'):
        if ranges[k][0] < 0: raise ValueError(f'{k} requires nonnegative bounds')
    for k in ('encoder_noise_std_rad','encoder_velocity_noise_std_rad_s'):
        if ranges[k] < 0: raise ValueError(f'{k} must be nonnegative')
    if not 0 <= ranges['phone_presence_probability'] <= 1 or not 0 <= sim['contact_restitution'] <= 1 or sim['foot_friction'] < 0:
        raise ValueError('invalid probability, restitution or friction')
    t=a['thermal_proxy']
    if t['cooling_s_inv'] < 0 or t['heating_c_s_at_rated_torque'] < 0 or not t['ambient_c'] < t['derate_start_c'] < t['zero_torque_c']:
        raise ValueError('invalid thermal proxy')
    return cfg


def _fmt(values):
    return " ".join(f"{float(v):.16g}" for v in values)


def _inertia_matrix(element):
    a = element.attrib
    return np.array([[float(a["ixx"]), float(a["ixy"]), float(a["ixz"])],
                     [float(a["ixy"]), float(a["iyy"]), float(a["iyz"])],
                     [float(a["ixz"]), float(a["iyz"]), float(a["izz"])]])


def _read_inertial(link):
    el = link.find("inertial")
    return float(el.find("mass").get("value")), np.fromstring(el.find("origin").get("xyz"), sep=" "), _inertia_matrix(el.find("inertia"))


def _parallel_axis(mass, offset):
    return mass * (float(offset @ offset) * np.eye(3) - np.outer(offset, offset))


def _set_inertial(link, mass, com, inertia):
    previous = link.find("inertial")
    if previous is not None:
        link.remove(previous)
    item = ET.SubElement(link, "inertial")
    ET.SubElement(item, "origin", xyz=_fmt(com), rpy="0 0 0")
    ET.SubElement(item, "mass", value=f"{mass:.16g}")
    fields = (("ixx", 0, 0), ("ixy", 0, 1), ("ixz", 0, 2), ("iyy", 1, 1), ("iyz", 1, 2), ("izz", 2, 2))
    ET.SubElement(item, "inertia", **{key: f"{inertia[i, j]:.16g}" for key, i, j in fields})


def _box_inertial(mass, size, com):
    x, y, z = size
    inertia = mass / 12 * np.diag([y*y + z*z, x*x + z*z, x*x + y*y])
    return float(mass), np.asarray(com, dtype=float), inertia


def _aggregate(parts):
    mass = sum(p[0] for p in parts)
    if mass <= 0:
        raise ValueError("combined mass must be positive")
    com = sum(m * c for m, c, i in parts) / mass
    inertia = sum(i + _parallel_axis(m, c - com) for m, c, i in parts)
    if np.linalg.eigvalsh(inertia).min() <= 0:
        raise ValueError("combined inertia must be positive definite")
    return mass, com, inertia


@lru_cache(maxsize=16)
def _cached_mesh_inertial(path, modified_ns, size_bytes, mass):
    import trimesh
    mesh = trimesh.load_mesh(path, process=True)
    mesh.apply_scale(0.001)
    if not mesh.is_watertight or mesh.volume <= 0:
        raise ValueError(f"mass mesh is not a closed positive-volume solid: {path}")
    return float(mass), np.asarray(mesh.center_mass), np.asarray(mesh.moment_inertia) * mass / mesh.mass


def _mesh_inertial(path, mass):
    path = Path(path).resolve()
    stat = path.stat()
    value = _cached_mesh_inertial(str(path), stat.st_mtime_ns, stat.st_size, float(mass))
    return value[0], value[1].copy(), value[2].copy()


@lru_cache(maxsize=32)
def _cached_sha256(path, modified_ns, size_bytes):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _sha256(path):
    path = Path(path).resolve()
    stat = path.stat()
    return _cached_sha256(str(path), stat.st_mtime_ns, stat.st_size)


def _remove_bench(base_link, source_dir, manifest):
    bench = next(p for p in manifest["parts"] if p["name"] == "bench_mounting_plate")
    fixture = _mesh_inertial(source_dir / bench["assembly_stl"], bench["solid_mass_kg"])
    total_mass, total_com, total_i = _read_inertial(base_link)
    mass, com, inertia = fixture
    remaining_mass = total_mass - mass
    remaining_com = (total_mass * total_com - mass * com) / remaining_mass
    remaining_origin_i = total_i + _parallel_axis(total_mass, total_com) - inertia - _parallel_axis(mass, com)
    remaining_i = remaining_origin_i - _parallel_axis(remaining_mass, remaining_com)
    if remaining_mass <= 0 or np.linalg.eigvalsh(remaining_i).min() <= 0:
        raise ValueError("fixture subtraction produced an invalid base inertia")
    _set_inertial(base_link, remaining_mass, remaining_com, remaining_i)
    for visual in list(base_link.findall("visual")):
        if visual.get("name") == "bench_mounting_plate":
            base_link.remove(visual)
    return {"removed_mass_kg": mass, "remaining_base_mass_kg": remaining_mass,
            "remaining_base_com_m": remaining_com.tolist(), "remaining_base_inertia_kg_m2": remaining_i.tolist(),
            "method": "Subtract the fixture STL's uniform-density inertia and centre of mass from the source aggregate using the parallel-axis theorem."}


def _primitive(link, kind, name, xyz, size=None, radius=None, color=None):
    item = ET.SubElement(link, kind, name=name)
    ET.SubElement(item, "origin", xyz=_fmt(xyz), rpy="0 0 0")
    geometry = ET.SubElement(item, "geometry")
    if radius is not None:
        ET.SubElement(geometry, "sphere", radius=f"{radius:.16g}")
    else:
        ET.SubElement(geometry, "box", size=_fmt(size))
    if color is not None:
        mat = ET.SubElement(item, "material", name=name + "_material")
        ET.SubElement(mat, "color", rgba=_fmt(color))


def _simplify_collisions(link):
    original = link.get("name")
    for collision in list(link.findall("collision")):
        link.remove(collision)
    # These small proxy shapes support fast contact tests; CAD clearance remains
    # a separate check. Toe collision is on the fixed toe frame below.
    boxes = {
        "base_mount": [((-0.014, 0.0, -0.017), (0.059, 0.041, 0.032))],
        "coxa": [((0.039, 0.0, 0.0), (0.078, 0.024, 0.018)),
                 ((0.067, 0.0, -0.01), (0.055, 0.04, 0.027))],
        "femur": [((0.043, 0.0, 0.0), (0.086, 0.024, 0.018)),
                  ((0.075, 0.0, 0.01), (0.047, 0.041, 0.027))],
        "tibia": [((0.048, 0.0, 0.0), (0.092, 0.017, 0.014))],
    }
    for index, (xyz, size) in enumerate(boxes[original]):
        _primitive(link, "collision", f"{original}_proxy_{index}", xyz, size=size)


def _relative_meshes(robot, source_dir, output_dir):
    for mesh in robot.iter("mesh"):
        path = source_dir / mesh.get("filename")
        if not path.is_file():
            raise FileNotFoundError(f"required CAD mesh is missing: {path}")
        mesh.set("filename", Path(os.path.relpath(path, output_dir)).as_posix())


def _toe(robot, prefix, radius):
    name = prefix + "toe"
    link = ET.SubElement(robot, "link", name=name)
    # The foot's mass already belongs to the tibia's source inertial.
    _set_inertial(link, 0.0, np.zeros(3), np.zeros((3, 3)))
    _primitive(link, "collision", name + "_sphere", (0, 0, 0), radius=radius)
    _primitive(link, "visual", name + "_contact", (0, 0, 0), radius=radius, color=(0.15, 0.15, 0.15, 1))
    joint = ET.SubElement(robot, "joint", name=name + "_fixed", type="fixed")
    ET.SubElement(joint, "parent", link=prefix + "tibia")
    ET.SubElement(joint, "child", link=name)
    ET.SubElement(joint, "origin", xyz="0.105 0 0", rpy="0 0 0")


def _write(robot, path):
    ET.indent(robot)
    ET.ElementTree(robot).write(path, encoding="utf-8", xml_declaration=True)


def _link_report(robot):
    result = []
    for link in robot.findall("link"):
        mass, com, inertia = _read_inertial(link)
        result.append({"name": link.get("name"), "mass_kg": mass, "com_m": com.tolist(), "inertia_kg_m2": inertia.tolist()})
    return result


def export_models(output_dir=None, phone_mass_kg=None, body_mass_scale=1.0,
                  body_com_shift=None, phone_offset=None, link_mass_scale=1.0,
                  config=None):
    """Generate portable relative-mesh URDFs and a provenance report.

    The test leg must be loaded with useFixedBase=True. The quadruped must use
    a free base. Mass scaling also scales inertia, preserving physical units.
    Body shift changes the lumped centre without changing CAD mount frames.
    """
    cfg = load_config() if config is None else validate_config(deepcopy(config))
    try:
        from .design_profile import load_profile
    except ImportError:
        from design_profile import load_profile
    approved = load_profile()
    for key in ("leg_urdf", "leg_manifest"):
        name = "urdf" if key == "leg_urdf" else "manifest"
        if hashlib.sha256((REPO / cfg["sources"][key]).read_bytes()).hexdigest() != approved.report["sources"][name]["sha256"]:
            raise ValueError("source differs from pinned R7 profile")
    if cfg["geometry"] != load_config()["geometry"]:
        raise ValueError("configured geometry differ from the source CAD; exporter supports only fixed R7")
    if [cfg["geometry"][k] for k in ("coxa_m","femur_m","tibia_m")] != [.082,.09,.105]:
        raise ValueError("fixed R7 link lengths required")
    output_dir = HERE / "models" if output_dir is None else Path(output_dir)

    if not np.isfinite([body_mass_scale, link_mass_scale]).all() or min(body_mass_scale, link_mass_scale) <= 0:
        raise ValueError("mass scales must be positive and finite")
    phone_mass = cfg["body"]["phone_mass_kg"] if phone_mass_kg is None else float(phone_mass_kg)
    if not np.isfinite(phone_mass) or phone_mass < 0:
        raise ValueError("phone mass must be finite and nonnegative")
    body_shift = np.asarray(cfg["body"]["body_com_shift_m"] if body_com_shift is None else body_com_shift, dtype=float)
    phone_shift = np.zeros(3) if phone_offset is None else np.asarray(phone_offset, dtype=float)
    for name, shift in (("body_com_shift", body_shift), ("phone_offset", phone_shift)):
        if shift.shape != (3,) or not np.isfinite(shift).all():
            raise ValueError(f"{name} must contain three finite metres")
    source = REPO / cfg["sources"]["leg_urdf"]
    source_dir = source.parent
    manifest_path = REPO / cfg["sources"]["leg_manifest"]
    manifest = json.loads(manifest_path.read_text())
    template = ET.parse(source).getroot()
    configured_lengths = [cfg["geometry"][key] for key in ("coxa_m", "femur_m", "tibia_m")]
    if not np.allclose(configured_lengths, np.asarray(manifest["lengths_mm"]) / 1000, rtol=0, atol=1e-12):
        raise ValueError("configured leg lengths differ from the source CAD; rebuild CAD and kinematics together")
    if not np.allclose(np.radians(cfg["geometry"]["neutral_deg"]), NEUTRAL, rtol=0, atol=1e-12):
        raise ValueError("configured neutral angles differ from the R7 kinematics contract")
    if not np.allclose(np.radians(cfg["geometry"]["limits_deg"]), LIMITS, rtol=0, atol=1e-12):
        raise ValueError("configured joint limits differ from the R7 source limits")
    # Reject a changed CAD convention before silently exporting an incompatible
    # model. Geometry/config changes must be made together with kinematics.
    for joint, expected_xyz, expected_axis in zip(JOINTS, ((0, 0, 0), (.082, 0, 0), (.09, 0, 0)), ((0, 0, 1), (0, 1, 0), (0, 1, 0))):
        item = template.find(f"joint[@name='{joint}']")
        if not np.allclose(np.fromstring(item.find("origin").get("xyz"), sep=" "), expected_xyz):
            raise ValueError("source joint geometry changed; update kinematics")
        if not np.allclose(np.fromstring(item.find("axis").get("xyz"), sep=" "), expected_axis):
            raise ValueError("source joint axis changed; update kinematics")
        limit = item.find("limit")
        if not np.allclose([float(limit.get(key)) for key in ("lower", "upper")], LIMITS[JOINTS.index(joint)], rtol=0, atol=1e-12):
            raise ValueError("source joint limits changed; update kinematics")
    output_dir.mkdir(parents=True, exist_ok=True)
    _relative_meshes(template, source_dir, output_dir)
    for link in template.findall("link"):
        _simplify_collisions(link)
    for joint in template.findall("joint"):
        joint.find("limit").set("effort", str(cfg["actuator"]["torque_limit_nm"]))
        joint.find("limit").set("velocity", str(cfg["actuator"]["no_load_speed_rad_s"]))
        joint.find("dynamics").set("damping", str(cfg["actuator"]["viscous_damping_nm_s_rad"]))
    single = deepcopy(template)
    single.set("name", "mist_r7_fixed_test_leg")
    _toe(single, "", cfg["geometry"]["toe_radius_m"])
    # Fixed-leg visual still shows the original fixture, with its exact source
    # aggregate inertia. It has no ground collision because its base is fixed.
    single_path = output_dir / "single_leg.urdf"
    _write(single, single_path)

    free_template = deepcopy(template)
    bench_report = _remove_bench(free_template.find("link[@name='base_mount']"), source_dir, manifest)
    robot = ET.Element("robot", name="mist_r7_four_leg_provisional")
    body = ET.SubElement(robot, "link", name="body")
    b = cfg["body"]
    hub_path = REPO / cfg["sources"]["hub_cad"]
    hub = _mesh_inertial(hub_path, b["hub_solid_pla_mass_kg"])
    parts = [hub]
    for key in ("battery", "electronics_harness", "phone_mount", "phone_pan_servo", "phone_pan_horn"):
        parts.append(_box_inertial(b[key + "_mass_kg"], b[key + "_size_m"], b[key + "_com_m"]))
    body_mass, body_com, body_i = _aggregate(parts)
    _set_inertial(body, body_mass * body_mass_scale, body_com + body_shift, body_i * body_mass_scale)
    visual = ET.SubElement(body, "visual", name="source_hub")
    geometry = ET.SubElement(visual, "geometry")
    ET.SubElement(geometry, "mesh", filename=Path(os.path.relpath(hub_path, output_dir)).as_posix(), scale="0.001 0.001 0.001")
    material = ET.SubElement(visual, "material", name="hub_material")
    ET.SubElement(material, "color", rgba="0.3 0.6 0.65 1")
    _primitive(body, "collision", "hub_proxy", (0, 0, 0.006), size=b["hub_collision_box_m"])
    _primitive(body, "visual", "battery_estimate", b["battery_com_m"], size=b["battery_size_m"], color=(0.1, 0.12, 0.14, 1))
    _primitive(body, "visual", "electronics_estimate", b["electronics_harness_com_m"], size=b["electronics_harness_size_m"], color=(0.1, 0.45, 0.2, 0.25))
    _primitive(body, "visual", "phone_mount_estimate", b["phone_mount_com_m"], size=b["phone_mount_size_m"], color=(0.3, 0.3, 0.3, 0.4))
    _primitive(body, "visual", "phone_pan_servo_estimate", b["phone_pan_servo_com_m"], size=b["phone_pan_servo_size_m"], color=(0.18, 0.23, 0.25, 1))
    mounts = {}
    for leg in LEGS:
        deg = cfg["geometry"]["mount_yaw_deg"][leg]
        angle = math.radians(deg)
        radius = cfg["geometry"]["yaw_mount_radius_m"]
        mounts[leg] = {"xyz": [radius * math.cos(angle), radius * math.sin(angle), cfg["geometry"]["yaw_origin_z_m"]], "yaw": angle}
        prefix = leg + "_"
        for src_link in free_template.findall("link"):
            link = deepcopy(src_link)
            link.set("name", prefix + src_link.get("name"))
            mass, com, inertia = _read_inertial(link)
            _set_inertial(link, mass * link_mass_scale, com, inertia * link_mass_scale)
            robot.append(link)
        mount_joint = ET.SubElement(robot, "joint", name=prefix + "mount", type="fixed")
        ET.SubElement(mount_joint, "parent", link="body")
        ET.SubElement(mount_joint, "child", link=prefix + "base_mount")
        ET.SubElement(mount_joint, "origin", xyz=_fmt(mounts[leg]["xyz"]), rpy=_fmt((0, 0, angle)))
        for src_joint in free_template.findall("joint"):
            joint = deepcopy(src_joint)
            joint.set("name", prefix + src_joint.get("name"))
            for item in (joint.find("parent"), joint.find("child")):
                item.set("link", prefix + item.get("link"))
            robot.append(joint)
        _toe(robot, prefix, cfg["geometry"]["toe_radius_m"])
    if phone_mass > 0:
        phone = ET.SubElement(robot, "link", name="phone")
        _set_inertial(phone, *_box_inertial(phone_mass, b["phone_size_m"], (0, 0, 0)))
        _primitive(phone, "visual", "phone_estimate", (0, 0, 0), size=b["phone_size_m"], color=(0.05, 0.05, 0.07, 1))
        _primitive(phone, "collision", "phone_proxy", (0, 0, 0), size=b["phone_size_m"])
        joint = ET.SubElement(robot, "joint", name="phone_mount", type="fixed")
        ET.SubElement(joint, "parent", link="body")
        ET.SubElement(joint, "child", link="phone")
        ET.SubElement(joint, "origin", xyz=_fmt(np.asarray(b["phone_com_m"]) + phone_shift), rpy="0 0 0")
    quad_path = output_dir / "quadruped.urdf"
    _write(robot, quad_path)
    try:
        from .kinematics import forward
    except ImportError:
        from kinematics import forward
    stance_deck_height = -float(forward(NEUTRAL)[2]) - cfg["geometry"]["yaw_origin_z_m"] + cfg["geometry"]["toe_radius_m"]
    links = _link_report(robot)
    report = {
        "source_urdf_sha256": _sha256(source),
        "source_manifest_sha256": _sha256(manifest_path),
        "source_hub_sha256": _sha256(hub_path),
        "joint_order": list(JOINT_NAMES), "mounts": mounts, "neutral_rad": NEUTRAL.tolist(),
        "neutral_deck_height_m": stance_deck_height, "bench_removed": bench_report,
        "body_mass_scale": body_mass_scale, "link_mass_scale": link_mass_scale,
        "body_com_shift_m": body_shift.tolist(), "phone_offset_m": phone_shift.tolist(),
        "phone_mass_kg": phone_mass, "total_mass_kg": sum(row["mass_kg"] for row in links), "links": links,
        "source_mass_model": "R7 moving links retain the source uniform full-solid PLA mass, 55 g servos and aluminium horn geometry. Printed infill, density, fasteners and wiring on moving links are unmeasured.",
        "added_mass_model": b["mass_notes"], "assembly_scope": cfg["sources"]["assembly_scope"],
        "phone_pose": b["phone_pose_notes"],
        "collision_scope": cfg["simulation"]["collision_model"],
        "actuator_scope": cfg["actuator"]["calibration_status"],
        "test_leg_loading": "single_leg.urdf requires useFixedBase=True; quadruped.urdf requires useFixedBase=False. Both use SI units.",
    }
    report_path = output_dir / "model_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return {"single_leg": single_path, "quadruped": quad_path, "report": report_path}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "models")
    parser.add_argument("--without-phone", action="store_true")
    args = parser.parse_args()
    paths = export_models(args.output, phone_mass_kg=0 if args.without_phone else None)
    report = json.loads(paths["report"].read_text())
    print(json.dumps({"files": {k: str(v) for k, v in paths.items()}, "total_mass_kg": report["total_mass_kg"], "neutral_deck_height_m": report["neutral_deck_height_m"]}, indent=2))


if __name__ == "__main__":
    main()
