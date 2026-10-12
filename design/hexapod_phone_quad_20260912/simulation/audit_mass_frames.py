"""Audit CAD mass aggregation and URDF frames without importing the simulator."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pybullet as p


TOLERANCES = {
    "mass_kg": 1e-10,
    "aggregate_com_mm": 1e-8,
    "aggregate_inertia_kg_m2": 1e-12,
    "box_inertia_kg_m2": 1e-12,
    "bullet_com_local_m": 1e-10,
    "bullet_inertia_kg_m2": 1e-10,
    "frame_position_m": 2e-6,
    "frame_rotation_matrix": 2e-6,
    "whole_com_m": 1e-9,
    "phone_collision_m": 1e-9,
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tensor(record):
    a = record["inertia_kg_m2"]
    result = np.array([[a["ixx"], a["ixy"], a["ixz"]],
                       [a["ixy"], a["iyy"], a["iyz"]],
                       [a["ixz"], a["iyz"], a["izz"]]], dtype=float)
    if not np.all(np.isfinite(result)):
        raise ValueError("An inertia tensor contains nonfinite terms")
    return result


def ry(angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rpy_matrix(angles):
    x, y, z = angles
    c, s = math.cos(x), math.sin(x)
    return rz(z) @ ry(y) @ np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def quaternion_matrix(q):
    x, y, z, w = np.asarray(q, dtype=float) / np.linalg.norm(q)
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)],
    ])


def independent_frames(parameters, body, rotation, angles, pan):
    """Compose joint frames directly from the mechanism dimensions."""
    radius = parameters["yaw_radius_mm"] / 1000
    height = parameters["yaw_height_mm"] / 1000
    coxa = parameters["coxa_mm"] / 1000
    femur = parameters["femur_mm"] / 1000
    phone = np.array(parameters["phone_pan_origin_mm"]) / 1000
    frames = {"base": (body, rotation),
              "phone_pan": (body + rotation @ phone, rotation @ rz(pan))}
    for leg, azimuth in parameters["leg_azimuth_deg"].items():
        az = math.radians(azimuth)
        yaw, hip, knee = angles[leg]
        co = body + rotation @ np.array([radius*math.cos(az), radius*math.sin(az), height])
        cr = rotation @ rz(az + yaw)
        fo, fr = co + cr @ np.array([coxa, 0, 0]), cr @ ry(hip)
        to, tr = fo + fr @ np.array([femur, 0, 0]), fr @ ry(knee)
        frames.update({f"coxa_{leg}": (co, cr), f"femur_{leg}": (fo, fr),
                       f"tibia_{leg}": (to, tr)})
    return frames


def check(report, name, passed, **measurements):
    report["checks"].append({"name": name, "passed": bool(passed), **measurements})


def source_file_checks(report, data, source_root):
    auxiliary = report["inputs"].setdefault("auxiliary_files", {})
    for name, expected in data["source_hashes"].items():
        path = (source_root/"cad"/name).resolve()
        actual = sha256(path)
        auxiliary[str(path)] = actual
        check(report, "cad_source:"+name, actual == expected)


def r4_case_checks(report, data):
    """Check exported knee-case placement against the corrected drawing datum."""
    if not data["revision"].startswith("hex_quad_r4"):
        return
    parameters = data["parameters"]
    offset = parameters.get("servo_case_center_offset_mm")
    check(report, "r4_case_center_datum", offset is not None and abs(offset-12.5) <= 1e-9,
          expected_case_center_to_shaft_mm=12.5, declared_case_center_to_shaft_mm=offset)
    check(report, "r4_knee_orientation", parameters.get("knee_servo_orientation") == "tail inward toward hip")
    knee_x = parameters["femur_mm"]
    expected_bounds = np.array([knee_x-35.115, knee_x+10.115])
    # The supplier exterior differs slightly from the drawing's rounded dimensions.
    tolerance = .02
    for leg in parameters["leg_azimuth_deg"]:
        parts = [part for part in data["parts"] if part["name"] == f"{leg}_servo_knee"]
        if len(parts) != 1:
            check(report, "r4_knee_case:"+leg, False, reason="Expected one knee servo case")
            continue
        part = parts[0]
        bounds = np.asarray(part["bounds_mm"], dtype=float)
        center = np.asarray(part["com_mm"], dtype=float)
        if bounds.shape != (2, 3) or center.shape != (3,) or not np.all(np.isfinite(bounds)) or not np.all(np.isfinite(center)):
            check(report, "r4_knee_case:"+leg, False, reason="Invalid case bounds or COM")
            continue
        valid = part["link"] == f"femur_{leg}" and part["material"] == "servo" and not part["printable"]
        valid = valid and np.max(np.abs(bounds[:, 0]-expected_bounds)) <= tolerance
        valid = valid and bounds[0, 0] <= center[0] < knee_x and abs(part["mass_kg"]-.055) <= TOLERANCES["mass_kg"]
        check(report, "r4_knee_case:"+leg, valid,
              expected_case_x_bounds_mm=expected_bounds.tolist(), actual_case_x_bounds_mm=bounds[:, 0].tolist(),
              case_com_x_mm=float(center[0]), knee_axis_x_mm=knee_x, drawing_comparison_tolerance_mm=tolerance)


def analytical_fastener_checks(report, data, source_root=None):
    """Check distributed hardware properties; placeholder boxes have no inertia role."""
    declared = [part for part in data["parts"] if part["material"] == "analytical_fasteners"]
    if not declared:
        return set()
    design = Path(source_root).resolve() if source_root is not None else Path(__file__).resolve().parent.parent
    source_path = design/"printing/fastener_mass.json"
    source_hash = sha256(source_path)
    source = json.loads(source_path.read_text(encoding="utf-8-sig"))
    auxiliary = report["inputs"].setdefault("auxiliary_files", {})
    auxiliary[str(source_path)] = source_hash
    report["inputs"]["fastener_properties_sha256"] = source_hash
    scenario = data["mass_model"]["fasteners"]
    scenario_valid = scenario in {"low", "nominal", "high"}
    scenario_valid = scenario_valid and data["parameters"].get("fastener_mass_scenario", scenario) == scenario
    check(report, "analytical_fastener_scenario", scenario_valid, scenario=scenario)
    if not scenario_valid:
        raise ValueError("The analytical fastener scenario is missing or inconsistent")
    provenance_valid = True
    for name, expected in source["source_hashes"].items():
        path = (design/name).resolve()
        actual = sha256(path)
        auxiliary[str(path)] = actual
        matches = actual == expected
        provenance_valid = provenance_valid and matches
        check(report, "analytical_fastener_source:"+name, matches)
    manifest_generator_hash = data["source_hashes"]["../printing/fastener_mass.py"]
    generator_matches = source["source_hashes"]["printing/fastener_mass.py"] == manifest_generator_hash
    provenance_valid = provenance_valid and generator_matches
    check(report, "analytical_fastener_manifest_source", generator_matches)
    pieces = source["pieces"]
    links = {part["link"] for part in declared}
    coverage = len(links) == len(declared) and links == set(source["links"])
    coverage = coverage and {piece["link"] for piece in pieces} == links
    coverage = coverage and len({piece["id"] for piece in pieces}) == len(pieces)
    check(report, "analytical_fastener_coverage", coverage,
          analytical_record_count=len(declared), hardware_piece_count=len(pieces))
    source_total = sum(piece["estimates"][scenario]["mass_kg"] for piece in pieces)
    total_matches = abs(source_total-source["totals_g"][scenario]/1000) <= TOLERANCES["mass_kg"]
    check(report, "analytical_fastener_total", total_matches, total_mass_kg=source_total)
    validated = set()
    for part in declared:
        values = [piece["estimates"][scenario] for piece in pieces if piece["link"] == part["link"]]
        mass = sum(value["mass_kg"] for value in values)
        if not math.isfinite(mass) or mass <= 0:
            raise ValueError("An analytical fastener group has invalid mass")
        center = sum(value["mass_kg"]*np.asarray(value["com_mm"]) for value in values)/mass
        inertia = np.zeros((3, 3))
        for value in values:
            delta = (np.asarray(value["com_mm"])-center)/1000
            inertia += tensor(value)+value["mass_kg"]*(np.dot(delta, delta)*np.eye(3)-np.outer(delta, delta))
        recorded = source["links"][part["link"]][scenario]
        mass_error = max(abs(mass-part["mass_kg"]), abs(mass-recorded["mass_kg"]))
        com_error = float(max(np.max(np.abs(center-part["com_mm"])), np.max(np.abs(center-recorded["com_mm"]))))
        inertia_error = float(max(np.max(np.abs(inertia-tensor(part))), np.max(np.abs(inertia-tensor(recorded)))))
        valid = part.get("allowance_only") is True and part.get("stl", "missing") is None and not part["printable"]
        valid = valid and mass_error <= TOLERANCES["mass_kg"] and com_error <= TOLERANCES["aggregate_com_mm"]
        valid = valid and inertia_error <= TOLERANCES["aggregate_inertia_kg_m2"]
        valid = valid and provenance_valid and coverage and total_matches
        check(report, "analytical_fasteners:"+part["name"], valid,
              hardware_piece_count=len(values), mass_error_kg=mass_error,
              com_error_mm=com_error, inertia_error_kg_m2=inertia_error)
        if valid:
            validated.add(part["name"])
    return validated


def aggregate_checks(report, data, validated_fasteners=None):
    validated_fasteners = set() if validated_fasteners is None else set(validated_fasteners)
    parts, links = data["parts"], data["links"]
    for record in [*parts, *links.values()]:
        if not math.isfinite(record["mass_kg"]) or record["mass_kg"] <= 0:
            raise ValueError("Every part and link must have finite positive mass")
        if np.asarray(record["com_mm"]).shape != (3,) or not np.all(np.isfinite(record["com_mm"])):
            raise ValueError("Every part and link must have a finite three component COM")
        tensor(record)
    if not math.isfinite(data["total_mass_kg"]) or data["total_mass_kg"] <= 0:
        raise ValueError("The total mass must be finite and positive")
    check(report, "part_ownership", all(part["link"] in links for part in parts),
          part_count=len(parts), link_count=len(links))
    check(report, "unique_part_names", len({part["name"] for part in parts}) == len(parts))
    part_mass = sum(part["mass_kg"] for part in parts)
    link_mass = sum(link["mass_kg"] for link in links.values())
    check(report, "total_mass", abs(part_mass-link_mass) <= TOLERANCES["mass_kg"]
          and abs(part_mass-data["total_mass_kg"]) <= TOLERANCES["mass_kg"],
          parts_mass_kg=part_mass, links_mass_kg=link_mass)
    boxes = 0
    for part in parts:
        eig = np.linalg.eigvalsh(tensor(part))
        valid = part["mass_kg"] > 0 and np.all(np.isfinite(part["com_mm"]))
        valid = valid and eig.min() > 0 and eig.sum()-2*eig.max() >= -1e-12
        check(report, f"part_physical_properties:{part['name']}", valid)
        if part["material"] == "pla":
            expected_mass = part["volume_mm3"] * data["parameters"]["pla_density_kg_m3"] * 1e-9
            check(report, f"pla_density:{part['name']}",
                  abs(part["mass_kg"]-expected_mass) <= TOLERANCES["mass_kg"])
        low, high = np.asarray(part["bounds_mm"], dtype=float)
        dimensions = (high-low)/1000
        volume = part["volume_mm3"]
        analytical_placeholder = part["material"] == "analytical_fasteners" and part["name"] in validated_fasteners
        if not analytical_placeholder and volume > 0 and abs(np.prod(dimensions)*1e9-volume)/volume < 1e-8:
            boxes += 1
            x, y, z = dimensions
            expected = part["mass_kg"]/12 * np.diag([y*y+z*z, x*x+z*z, x*x+y*y])
            error = float(np.max(np.abs(expected-tensor(part))))
            check(report, f"analytical_box:{part['name']}",
                  error <= TOLERANCES["box_inertia_kg_m2"], inertia_error_kg_m2=error)
    check(report, "analytical_box_coverage", boxes > 0, box_count=boxes)
    for name, link in links.items():
        owned = [part for part in parts if part["link"] == name]
        mass = sum(part["mass_kg"] for part in owned)
        if mass <= 0:
            raise ValueError(f"Link {name} has no positive part mass")
        center = sum(part["mass_kg"]*np.asarray(part["com_mm"]) for part in owned)/mass
        inertia = np.zeros((3, 3))
        for part in owned:
            delta = (np.asarray(part["com_mm"])-center)/1000
            inertia += tensor(part) + part["mass_kg"]*(np.dot(delta, delta)*np.eye(3)-np.outer(delta, delta))
        mass_error = abs(mass-link["mass_kg"])
        com_error = float(np.max(np.abs(center-link["com_mm"])))
        inertia_error = float(np.max(np.abs(inertia-tensor(link))))
        eig = np.linalg.eigvalsh(tensor(link))
        valid = mass_error <= TOLERANCES["mass_kg"] and com_error <= TOLERANCES["aggregate_com_mm"]
        valid = valid and inertia_error <= TOLERANCES["aggregate_inertia_kg_m2"]
        valid = valid and eig.min() > 0 and eig.sum()-2*eig.max() >= -1e-12
        check(report, f"link_aggregation:{name}", valid, part_count=len(owned),
              mass_error_kg=mass_error, com_error_mm=com_error,
              inertia_error_kg_m2=inertia_error, principal_moments_kg_m2=eig.tolist())


def phone_collision_check(report, data, phone_node):
    """Require the phone floor proxy to follow the CAD phone envelope."""
    phone_parts = [part for part in data["parts"]
                   if part["link"] == "phone_pan" and part["name"] == "Xiaomi_Mi9SE_bare_phone_envelope"]
    collisions = [] if phone_node is None else phone_node.findall("collision")
    if len(phone_parts) != 1 or len(collisions) != 1:
        check(report, "phone_collision_box", False,
              reason="Exactly one phone envelope and one phone collision are required",
              envelope_count=len(phone_parts), collision_count=len(collisions))
        return
    box = collisions[0].find("geometry/box")
    if box is None:
        check(report, "phone_collision_box", False, reason="The phone collision must be a box")
        return
    bounds = np.asarray(phone_parts[0]["bounds_mm"], dtype=float)/1000
    if bounds.shape != (2, 3) or not np.all(np.isfinite(bounds)) or np.any(bounds[1] <= bounds[0]):
        check(report, "phone_collision_box", False, reason="The phone envelope bounds are invalid")
        return
    expected_size = bounds[1]-bounds[0]
    expected_origin = (bounds[0]+bounds[1])/2
    size = np.fromstring(box.attrib.get("size", ""), sep=" ")
    origin = collisions[0].find("origin")
    xyz = np.fromstring(origin.attrib.get("xyz", "0 0 0"), sep=" ") if origin is not None else np.zeros(3)
    rpy = np.fromstring(origin.attrib.get("rpy", "0 0 0"), sep=" ") if origin is not None else np.zeros(3)
    valid = all(value.shape == (3,) and np.all(np.isfinite(value)) for value in (size, xyz, rpy))
    if not valid:
        check(report, "phone_collision_box", False, reason="The phone collision dimensions or pose are invalid")
        return
    valid = valid and np.allclose(size, expected_size, rtol=0, atol=TOLERANCES["phone_collision_m"])
    valid = valid and np.allclose(xyz, expected_origin, rtol=0, atol=TOLERANCES["phone_collision_m"])
    valid = valid and np.allclose(rpy, 0, rtol=0, atol=1e-12)
    check(report, "phone_collision_box", valid,
          expected_size_m=expected_size.tolist(), actual_size_m=size.tolist(),
          expected_origin_m=expected_origin.tolist(), actual_origin_m=xyz.tolist(),
          actual_rpy_rad=rpy.tolist())


def mesh_checks(report, data, manifest, urdf):
    xml = ET.parse(urdf).getroot()
    nodes = {node.attrib["name"]: node for node in xml.findall("link")}
    check(report, "urdf_link_names", set(nodes) == set(data["links"]))
    phone_collision_check(report, data, nodes.get("phone_pan"))
    for name, link in data["links"].items():
        expected = (manifest.parent/link["stl"]).resolve()
        visuals = nodes[name].findall("visual")
        if len(visuals) != 1:
            raise ValueError(f"Expected one CAD visual for {name}")
        mesh = visuals[0].find("geometry/mesh")
        if mesh is None:
            raise ValueError(f"No CAD visual mesh for {name}")
        actual = (urdf.parent/mesh.attrib["filename"]).resolve()
        scale = np.fromstring(mesh.attrib.get("scale", "1 1 1"), sep=" ")
        origin = visuals[0].find("origin")
        xyz = np.fromstring(origin.attrib.get("xyz", "0 0 0"), sep=" ") if origin is not None else np.zeros(3)
        rpy = np.fromstring(origin.attrib.get("rpy", "0 0 0"), sep=" ") if origin is not None else np.zeros(3)
        expected_hash, actual_hash = sha256(expected), sha256(actual)
        valid = expected_hash == actual_hash and scale.shape == (3,) and np.allclose(scale, .001, rtol=0, atol=1e-15)
        valid = valid and np.allclose(xyz, 0, rtol=0, atol=1e-15) and np.allclose(rpy, 0, rtol=0, atol=1e-15)
        check(report, f"cad_visual:{name}", valid)
        report["inputs"]["meshes"][name] = {"manifest_mesh_path": str(expected),
            "urdf_mesh_path": str(actual), "manifest_mesh_sha256": expected_hash,
            "urdf_mesh_sha256": actual_hash}


def bullet_checks(report, data, urdf):
    parameters = data["parameters"]
    legs = parameters["leg_azimuth_deg"]
    if set(legs) != {"FL", "FR", "RL", "RR"}:
        raise ValueError("The independent pose probe requires FL, FR, RL and RR")
    neutral = np.radians([parameters["neutral_deg"][key] for key in ("yaw", "hip", "knee")])
    neutral_frames = independent_frames(parameters, np.zeros(3), np.eye(3),
                                       {leg: neutral for leg in legs}, 0)
    for name, (position, rotation) in neutral_frames.items():
        stored = np.asarray(data["links"][name]["assembly_transform"])
        position_error = float(np.max(np.abs(stored[:3, 3]/1000-position)))
        rotation_error = float(np.max(np.abs(stored[:3, :3]-rotation)))
        check(report, f"manifest_assembly_frame:{name}", position_error < 1e-10 and rotation_error < 1e-10,
              position_error_m=position_error, rotation_matrix_error=rotation_error)
    body = np.array([-.2, .1, .3])
    body_rpy = np.radians([5, -7, 12])
    body_rotation = rpy_matrix(body_rpy)
    body_quaternion = p.getQuaternionFromEuler(body_rpy.tolist())
    angles_deg = {"FL": [10, 30, 75], "FR": [-5, 20, 60],
                  "RL": [20, 15, 90], "RR": [-15, 25, 80]}
    angles = {leg: np.radians(values) for leg, values in angles_deg.items()}
    pan = math.radians(60)
    frames = independent_frames(parameters, body, body_rotation, angles, pan)
    report["pose_probe"] = {"base_position_m": body.tolist(), "base_rpy_deg": [5, -7, 12],
                            "leg_angles_deg": angles_deg, "phone_pan_deg": 60}
    client = p.connect(p.DIRECT)
    try:
        robot = p.loadURDF(str(urdf), basePosition=body.tolist(), baseOrientation=body_quaternion,
                           useFixedBase=False, flags=p.URDF_USE_INERTIA_FROM_FILE, physicsClientId=client)
        names, joints = {"base": -1}, {}
        for index in range(p.getNumJoints(robot, physicsClientId=client)):
            info = p.getJointInfo(robot, index, physicsClientId=client)
            names[info[12].decode()] = index
            joints[info[1].decode()] = index
        if set(names) != set(data["links"]):
            raise ValueError("Bullet loaded a different link set")
        for leg in legs:
            for kind, angle in zip(("yaw", "hip", "knee"), angles[leg]):
                p.resetJointState(robot, joints[f"{kind}_{leg}"], float(angle), physicsClientId=client)
        p.resetJointState(robot, joints["phone_pan"], pan, physicsClientId=client)
        actual_com, expected_com = np.zeros(3), np.zeros(3)
        for name, index in names.items():
            source = data["links"][name]
            info = p.getDynamicsInfo(robot, index, physicsClientId=client)
            inertial_rotation = quaternion_matrix(info[4])
            restored_tensor = inertial_rotation @ np.diag(info[2]) @ inertial_rotation.T
            if index == -1:
                com, quaternion = p.getBasePositionAndOrientation(robot, physicsClientId=client)
                world_inertial_rotation = quaternion_matrix(quaternion)
                link_rotation = world_inertial_rotation @ inertial_rotation.T
                link_position = np.asarray(com)-link_rotation @ np.asarray(info[3])
            else:
                state = p.getLinkState(robot, index, computeForwardKinematics=True, physicsClientId=client)
                com, link_position, link_rotation = state[0], np.asarray(state[4]), quaternion_matrix(state[5])
            expected_position, expected_rotation = frames[name]
            errors = {
                "mass_error_kg": abs(info[0]-source["mass_kg"]),
                "com_local_error_m": float(np.max(np.abs(np.asarray(info[3])-np.asarray(source["com_mm"])/1000))),
                "inertia_error_kg_m2": float(np.max(np.abs(restored_tensor-tensor(source)))),
                "position_error_m": float(np.max(np.abs(link_position-expected_position))),
                "rotation_matrix_error": float(np.max(np.abs(link_rotation-expected_rotation))),
            }
            thresholds = [TOLERANCES[key] for key in ("mass_kg", "bullet_com_local_m", "bullet_inertia_kg_m2",
                                                     "frame_position_m", "frame_rotation_matrix")]
            check(report, f"bullet_mass_inertia_frame:{name}",
                  all(value <= limit for value, limit in zip(errors.values(), thresholds)), **errors)
            actual_com += info[0]*np.asarray(com)
            expected_com += source["mass_kg"]*(expected_position+expected_rotation @ (np.asarray(source["com_mm"])/1000))
        error = float(np.max(np.abs(actual_com-expected_com))/data["total_mass_kg"])
        check(report, "whole_robot_world_com", error <= TOLERANCES["whole_com_m"], maximum_error_m=error)
    finally:
        p.disconnect(client)


def audit(manifest, urdf, expected_manifest_hash=None, expected_urdf_hash=None, source_root=None):
    source_root = Path(source_root).resolve() if source_root is not None else Path(__file__).resolve().parent.parent
    report = {"created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "audit_fail",
              "inputs": {"manifest_path": str(manifest), "urdf_path": str(urdf),
                         "source_root_path": str(source_root),
                         "expected_manifest_sha256": expected_manifest_hash,
                         "expected_urdf_sha256": expected_urdf_hash,
                         "audit_source_sha256": sha256(__file__), "meshes": {}},
              "tolerances": TOLERANCES, "checks": [], "errors": [],
              "scope": "Mass aggregation, analytical box inertia, CAD mesh identity, phone collision dimensions, and kinematic frames. This audit does not test walking, contact dynamics, print fit, or physical material properties."}
    try:
        report["inputs"]["manifest_sha256"] = sha256(manifest)
        report["inputs"]["urdf_sha256"] = sha256(urdf)
        if expected_manifest_hash is not None and report["inputs"]["manifest_sha256"] != expected_manifest_hash:
            raise ValueError("The manifest differs from the requested frozen hash")
        if expected_urdf_hash is not None and report["inputs"]["urdf_sha256"] != expected_urdf_hash:
            raise ValueError("The URDF differs from the requested frozen hash")
        data = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if data["units"] != "mm":
            raise ValueError("The manifest must use millimeters for geometry")
        source_file_checks(report, data, source_root)
        r4_case_checks(report, data)
        validated_fasteners = analytical_fastener_checks(report, data, source_root)
        aggregate_checks(report, data, validated_fasteners)
        mesh_checks(report, data, manifest, urdf)
        bullet_checks(report, data, urdf)
        unchanged = sha256(manifest) == report["inputs"]["manifest_sha256"] and sha256(urdf) == report["inputs"]["urdf_sha256"]
        unchanged = unchanged and sha256(__file__) == report["inputs"]["audit_source_sha256"]
        for entry in report["inputs"]["meshes"].values():
            unchanged = unchanged and sha256(entry["manifest_mesh_path"]) == entry["manifest_mesh_sha256"]
            unchanged = unchanged and sha256(entry["urdf_mesh_path"]) == entry["urdf_mesh_sha256"]
        unchanged = unchanged and all(sha256(path) == expected for path, expected in report["inputs"].get("auxiliary_files", {}).items())
        check(report, "inputs_unchanged_during_audit", unchanged)
    except Exception as error:
        report["errors"].append(f"{type(error).__name__}: {error}")
    report["failed_checks"] = [item["name"] for item in report["checks"] if not item["passed"]]
    report["passed"] = bool(report["checks"]) and not report["failed_checks"] and not report["errors"]
    report["status"] = "audit_pass" if report["passed"] else "audit_fail"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--urdf", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--expected-urdf-sha256")
    parser.add_argument("--source-root", type=Path, help="Root containing the CAD, settings and fastener sources")
    args = parser.parse_args()
    manifest, urdf, output = [path.resolve() for path in (args.manifest, args.urdf, args.output)]
    if output in {manifest, urdf, Path(__file__).resolve()}:
        parser.error("The output must not overwrite an input or the audit source")
    report = audit(manifest, urdf, args.expected_manifest_sha256, args.expected_urdf_sha256, args.source_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]),
                      "failed_checks": report["failed_checks"], "errors": report["errors"],
                      "output_path": str(output)}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
