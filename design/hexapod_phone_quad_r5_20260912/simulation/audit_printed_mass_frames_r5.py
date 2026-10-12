"""Audit frozen R5 deposition assembly, distributed hardware, and URDF frames."""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial import cKDTree

import audit_mass_frames as baseline


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/"simulation/output_r5_printed_nominal/printed_mass_frame_audit.json"
EXPECTED_REVISION = "hex_quad_r5_inward_hip_straight_tibia"
REQUIRED_HASH_LABELS = ("printed_manifest", "solid_manifest", "production_properties", "urdf", "fastener_properties")
TOLERANCES = {
    "mass_kg": 1e-10,
    "com_mm": 1e-8,
    "inertia_kg_m2": 1e-12,
    "rigid_transform": 1e-10,
    "stl_vertex_position_mm": 2e-5,
    "urdf_origin_m": 1e-10,
    "joint_angle_rad": 1e-10,
}
PROPERTY_KEYS = ("mass_kg", "com_mm", "inertia_kg_m2")
check = baseline.check


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bind(report, label, path):
    path = Path(path).resolve()
    value = sha256(path)
    report["inputs"]["bound_files"][label] = {"path": str(path), "sha256": value}
    return value


def matrix(record):
    value = record["inertia_kg_m2"]
    return np.asarray(value, dtype=float) if isinstance(value, list) else baseline.tensor(record)


def properties(mass, center, inertia):
    return {"mass_kg": float(mass), "com_mm": np.asarray(center).tolist(),
            "inertia_kg_m2": np.asarray(inertia).tolist()}


def physical(report, label, record):
    mass, center, inertia = record["mass_kg"], np.asarray(record["com_mm"]), matrix(record)
    valid = (math.isfinite(mass) and mass > 0 and center.shape == (3,)
             and np.all(np.isfinite(center)) and inertia.shape == (3, 3)
             and np.all(np.isfinite(inertia)))
    if not valid:
        raise ValueError(f"Invalid mass properties: {label}")
    symmetry = float(np.max(np.abs(inertia-inertia.T)))
    eigenvalues = np.linalg.eigvalsh((inertia+inertia.T)/2)
    triangle_margin = float(eigenvalues.sum()-2*eigenvalues.max())
    check(report, f"physical_tensor:{label}", symmetry <= 1e-12
          and eigenvalues.min() > 0 and triangle_margin >= -1e-12,
          symmetry_error_kg_m2=symmetry, principal_moments_kg_m2=eigenvalues.tolist(),
          triangle_margin_kg_m2=triangle_margin)


def compare(report, label, actual, expected):
    errors = {
        "mass_error_kg": abs(actual["mass_kg"]-expected["mass_kg"]),
        "com_error_mm": float(np.max(np.abs(np.asarray(actual["com_mm"])-expected["com_mm"]))),
        "inertia_error_kg_m2": float(np.max(np.abs(matrix(actual)-matrix(expected)))),
    }
    limits = [TOLERANCES[k] for k in ("mass_kg", "com_mm", "inertia_kg_m2")]
    check(report, label, all(error <= limit for error, limit in zip(errors.values(), limits)), **errors)


def aggregate(records):
    """Sum tensors at the link origin, then translate once to the aggregate COM."""
    mass = math.fsum(record["mass_kg"] for record in records)
    centers_m = np.asarray([record["com_mm"] for record in records], float)*.001
    masses = np.asarray([record["mass_kg"] for record in records], float)
    center_m = np.array([math.fsum(masses*centers_m[:, axis])/mass for axis in range(3)])
    tensor_origin = np.zeros((3, 3))
    for record, center in zip(records, centers_m):
        tensor_origin += matrix(record) + record["mass_kg"]*(center@center*np.eye(3)-np.outer(center, center))
    inertia = tensor_origin - mass*(center_m@center_m*np.eye(3)-np.outer(center_m, center_m))
    return properties(mass, center_m*1000, inertia)


def vertices(path):
    raw = Path(path).read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84+50*count:
        raise ValueError(f"Expected a binary STL with its recorded triangle count: {path}")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    return np.frombuffer(raw, dtype=dtype, count=count, offset=84)["vertices"].reshape(-1, 3).astype(float)


def point_to_surface_distances(points, triangle_vertices):
    """Measure distance to triangle interiors and edges, including degenerate faces."""
    triangles = triangle_vertices.reshape(-1, 3, 3)
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    ab, ac = b-a, c-a
    normal = np.cross(ab, ac)
    normal_squared = np.einsum("ij,ij->i", normal, normal)
    ab_squared = np.einsum("ij,ij->i", ab, ab)
    ac_squared = np.einsum("ij,ij->i", ac, ac)
    ab_ac = np.einsum("ij,ij->i", ab, ac)
    denominator = ab_squared*ac_squared-ab_ac**2
    result = []
    for start in range(0, len(points), 64):
        offset = points[start:start+64, None, :]-a
        ab_offset = np.einsum("bij,ij->bi", offset, ab)
        ac_offset = np.einsum("bij,ij->bi", offset, ac)
        safe_denominator = np.where(denominator > 0, denominator, 1)
        u = (ac_squared*ab_offset-ab_ac*ac_offset)/safe_denominator
        v = (ab_squared*ac_offset-ab_ac*ab_offset)/safe_denominator
        inside = (denominator > 0) & (u >= 0) & (v >= 0) & (u+v <= 1)
        signed = np.einsum("bij,ij->bi", offset, normal)
        distance_squared = np.where(inside, signed**2/np.where(normal_squared > 0, normal_squared, 1), np.inf)
        for origin, edge in ((a, ab), (a, ac), (b, c-b)):
            offset = points[start:start+64, None, :]-origin
            edge_squared = np.einsum("ij,ij->i", edge, edge)
            t = np.clip(np.einsum("bij,ij->bi", offset, edge)/np.where(edge_squared > 0, edge_squared, 1), 0, 1)
            remaining = offset-t[:, :, None]*edge
            distance_squared = np.minimum(distance_squared, np.einsum("bij,bij->bi", remaining, remaining))
        result.extend(np.sqrt(distance_squared.min(axis=1)))
    return np.asarray(result)


def mesh_surface_check(report, name, expected_vertices, actual_vertices):
    forward = cKDTree(actual_vertices).query(expected_vertices, k=1)[0]
    backward = cKDTree(expected_vertices).query(actual_vertices, k=1)[0]
    vertex_error = float(max(forward.max(), backward.max()))
    tolerance = TOLERANCES["stl_vertex_position_mm"]
    alternate_vertices = int(np.sum(forward > tolerance)+np.sum(backward > tolerance))
    surface_error = vertex_error
    if alternate_vertices:
        # Rigidly transformed CAD exports can retessellate a planar face.
        # Verify those vertices against triangle surfaces instead of vertex IDs.
        forward[forward > tolerance] = point_to_surface_distances(expected_vertices[forward > tolerance], actual_vertices)
        backward[backward > tolerance] = point_to_surface_distances(actual_vertices[backward > tolerance], expected_vertices)
        surface_error = float(max(forward.max(), backward.max()))
    check(report, f"print_to_instance_mesh_frame:{name}", len(actual_vertices) == len(expected_vertices)
          and surface_error <= tolerance, maximum_bidirectional_surface_distance_bound_mm=surface_error,
          maximum_bidirectional_nearest_vertex_error_mm=vertex_error,
          vertices_requiring_triangle_surface_distance=alternate_vertices,
          source_vertex_count=len(expected_vertices), instance_vertex_count=len(actual_vertices))


def printed_checks(report, data, solid, production, manifest):
    parts, original = data["parts"], {part["name"]: part for part in solid["parts"]}
    printed = [part for part in parts if part["printable"]]
    rows = {row["sku"]: row for row in production["parts"]}
    print_files = {row["sku"]: row for row in solid["print_parts"]}
    quantities = Counter(part["sku"] for part in printed)
    expected_pieces = sum(row["quantity"] for row in solid["print_parts"])
    check(report, "source_rows_and_instance_coverage", len(rows) == len(production["parts"])
          and len(print_files) == len(solid["print_parts"]) > 0
          and len(printed) == expected_pieces == production["quantity_weighted_totals"]["piece_count"]
          and set(rows) == set(print_files) == set(quantities),
          source_sku_count=len(rows), printed_instance_count=len(printed),
          solid_manifest_printed_instance_count=expected_pieces)
    check(report, "part_identity_and_ownership", len({part["name"] for part in parts}) == len(parts)
          and {part["name"] for part in parts} == set(original)
          and all(part["link"] in data["links"] for part in parts),
          all_part_count=len(parts), link_count=len(data["links"]))
    for key in ("units", "parameters", "source_hashes", "print_parts", "assembly_bounds_mm", "coupons"):
        check(report, f"solid_metadata_retained:{key}", data[key] == solid[key])
    properties_hash = report["inputs"]["bound_files"]["production_properties"]["sha256"]
    source_vertices = {}
    for sku, row in rows.items():
        source_path = manifest.parent/print_files[sku]["stl"]
        source_hash = bind(report, f"print_stl:{sku}", source_path)
        source_vertices[sku] = vertices(source_path)
        check(report, f"sku_source_and_quantity:{sku}", row["quantity"] == quantities[sku]
              and row["quantity"] == print_files[sku]["quantity"]
              and source_hash == row["source_stl_hash"]
              and source_path.resolve() == Path(row["source_stl_path"]).resolve()
              and row["source_print_rotation_deg"] == print_files[sku]["print_rotation"]
              and row["status"] == "pass", quantity=quantities[sku], source_stl_sha256=source_hash)
        physical(report, f"source:{sku}", row)
        model = row["deposition"]["properties"]["model"]
        compare(report, f"source_model_only:{sku}", row, {
            "mass_kg": model["mass_kg"], "com_mm": model["com_mm"],
            "inertia_kg_m2": model["inertia_line_about_com_kg_m2"]})
    reconstructed = []
    for part in parts:
        name = part["name"]
        physical(report, f"assembled_part:{name}", part)
        if not part["printable"]:
            check(report, f"nonprinted_part_retained:{name}", part == original[name])
            reconstructed.append(part)
            continue
        row = rows[part["sku"]]
        transform = np.asarray(part["print_to_link_transform"], float)
        if transform.shape != (4, 4) or not np.all(np.isfinite(transform)):
            raise ValueError(f"Invalid print transform for {name}")
        rotation, offset = transform[:3, :3], transform[:3, 3]
        orthogonality_error = float(np.max(np.abs(rotation.T@rotation-np.eye(3))))
        check(report, f"print_transform_rigid:{name}", orthogonality_error <= TOLERANCES["rigid_transform"]
              and abs(np.linalg.det(rotation)-1) <= TOLERANCES["rigid_transform"]
              and np.array_equal(transform[3], [0, 0, 0, 1]),
              orthogonality_error=orthogonality_error, determinant=float(np.linalg.det(rotation)))
        retained = {key: value for key, value in part.items()
                    if key not in (*PROPERTY_KEYS, "mass_source", "solid_CAD_properties", "deposition_source")}
        expected_retained = {key: value for key, value in original[name].items()
                             if key not in (*PROPERTY_KEYS, "mass_source")}
        check(report, f"printed_source_geometry_retained:{name}", retained == expected_retained
              and part["solid_CAD_properties"] == {key: original[name][key] for key in PROPERTY_KEYS})
        expected = properties(row["mass_kg"], rotation@np.asarray(row["com_mm"])+offset,
                              rotation@matrix(row)@rotation.T)
        compare(report, f"print_mass_com_tensor_transform:{name}", part, expected)
        reconstructed.append({**expected, "name": name, "link": part["link"]})
        source = part["deposition_source"]
        check(report, f"deposition_binding:{name}", source["sku"] == part["sku"]
              and source["source_stl_sha256"] == row["source_stl_hash"]
              and source["properties_json_sha256"] == properties_hash
              and abs(source["support_mass_excluded_g"]-row["support_mass_g"]) <= 1e-10)
        mesh_path = manifest.parent/part["stl"]
        bind(report, f"part_mesh:{name}", mesh_path)
        actual_vertices = vertices(mesh_path)
        expected_vertices = source_vertices[part["sku"]]@rotation.T+offset
        mesh_surface_check(report, name, expected_vertices, actual_vertices)
    for link_name, link in data["links"].items():
        records = [part for part in reconstructed if part["link"] == link_name]
        rebuilt = aggregate(records)
        compare(report, f"independent_link_aggregation:{link_name}", link, rebuilt)
        physical(report, f"link:{link_name}", link)
        check(report, f"solid_link_geometry_retained:{link_name}",
              {k: v for k, v in link.items() if k not in PROPERTY_KEYS}
              == {k: v for k, v in solid["links"][link_name].items() if k not in PROPERTY_KEYS})
    model_mass = math.fsum(row["mass_kg"]*row["quantity"] for row in rows.values())
    parts_mass = math.fsum(part["mass_kg"] for part in parts)
    links_mass = math.fsum(link["mass_kg"] for link in data["links"].values())
    support_mass = math.fsum(row["support_mass_g"]*row["quantity"]/1000 for row in rows.values())
    adhesion_mass = math.fsum(row["adhesion_mass_g"]*row["quantity"]/1000 for row in rows.values())
    check(report, "mass_totals_and_model_only_selection",
          abs(parts_mass-data["total_mass_kg"]) <= TOLERANCES["mass_kg"]
          and abs(links_mass-parts_mass) <= TOLERANCES["mass_kg"]
          and abs(model_mass-data["printable_mass_deposited_kg"]) <= TOLERANCES["mass_kg"]
          and abs(model_mass-production["quantity_weighted_totals"]["model_mass_g"]/1000) <= TOLERANCES["mass_kg"]
          and abs(parts_mass-(solid["total_mass_kg"]-solid["printable_mass_solid_kg"]+model_mass)) <= TOLERANCES["mass_kg"],
          assembled_mass_kg=parts_mass, links_mass_kg=links_mass, model_deposition_mass_kg=model_mass,
          excluded_support_mass_kg=support_mass, excluded_adhesion_mass_kg=adhesion_mass)
    report["summary"] = {"part_count": len(parts), "printed_instance_count": len(printed),
                         "source_sku_count": len(rows), "link_count": len(data["links"]),
                         "assembled_mass_kg": parts_mass, "model_deposition_mass_kg": model_mass}


def hardware_checks(report, data, fasteners, fastener_path):
    counts = Counter(piece["category"] for piece in fasteners["pieces"])
    check(report, "fastener_piece_counts", counts == fasteners["counts"]
          and len({piece["id"] for piece in fasteners["pieces"]}) == len(fasteners["pieces"]) > 0
          and all(piece["link"] in data["links"] for piece in fasteners["pieces"]),
          piece_count=len(fasteners["pieces"]), counts=dict(counts))
    for path, expected_hash in fasteners["source_hashes"].items():
        actual_hash = bind(report, f"fastener_source:{path}", fastener_path.parent.parent/path)
        check(report, f"fastener_source_current:{path}", actual_hash == expected_hash)
    check(report, "fastener_generator_manifest_binding",
          data["source_hashes"]["../printing/fastener_mass.py"]
          == fasteners["source_hashes"]["printing/fastener_mass.py"])
    for leg in data["parameters"]["leg_azimuth_deg"]:
        for kind, owner in (("hip", f"coxa_{leg}"), ("knee", f"femur_{leg}")):
            screws = [piece for piece in fasteners["pieces"]
                      if piece["group"] == f"{leg}_{kind}_clamp" and piece["category"] == "screw"]
            check(report, f"r5_inward_clamp_frame:{kind}_{leg}", bool(screws)
                  and all(piece["link"] == owner
                          and np.allclose(piece["axis_local"], [0, 0, 1], rtol=0, atol=1e-10)
                          for piece in screws), screw_count=len(screws),
                  expected_owning_link=owner, expected_axis_local=[0, 0, 1])
    lumps = [part for part in data["parts"] if part["material"] == "analytical_fasteners"]
    check(report, "distributed_fastener_coverage", len(lumps) == 14
          and {part["link"] for part in lumps} == set(data["links"])
          and all(part["allowance_only"] and part["stl"] is None for part in lumps))
    for part in lumps:
        owned = [piece["estimates"]["high"] for piece in fasteners["pieces"] if piece["link"] == part["link"]]
        compare(report, f"high_fastener_piece_aggregation:{part['link']}", part, aggregate(owned))
        compare(report, f"high_fastener_export_match:{part['link']}", part, fasteners["links"][part["link"]]["high"])
    mass = math.fsum(part["mass_kg"] for part in lumps)
    piece_mass = math.fsum(piece["estimates"]["high"]["mass_kg"] for piece in fasteners["pieces"])
    wire = [part for part in data["parts"] if part["material"] == "allowance"]
    check(report, "high_fastener_mass_and_single_wiring_allowance",
          abs(mass-piece_mass) <= TOLERANCES["mass_kg"]
          and abs(mass-fasteners["totals_g"]["high"]/1000) <= TOLERANCES["mass_kg"]
          and len(wire) == 1 and wire[0]["name"] == "wiring_allowance"
          and wire[0]["link"] == "base" and abs(wire[0]["mass_kg"]-.150) <= TOLERANCES["mass_kg"]
          and {part["name"] for part in data["parts"] if part["allowance_only"]}
              == {"wiring_allowance", *(part["name"] for part in lumps)},
          fastener_mass_kg=mass, wiring_mass_kg=math.fsum(part["mass_kg"] for part in wire),
          old_fastener_allowance_present=any(part["name"] == "fastener_allowance" for part in data["parts"]))
    servos = [part for part in data["parts"] if part["material"] == "servo"]
    check(report, "servo_count_mass_and_ownership", len(servos) == 13
          and all(abs(part["mass_kg"]-.055) <= TOLERANCES["mass_kg"] for part in servos)
          and Counter(part["link"] for part in servos)
              == Counter({"base": 5, **{f"{kind}_{leg}": 1 for kind in ("coxa", "femur")
                                        for leg in data["parameters"]["leg_azimuth_deg"]}}),
          servo_count=len(servos), servo_mass_kg=math.fsum(part["mass_kg"] for part in servos))
    report["summary"].update(fastener_piece_count=len(fasteners["pieces"]), fastener_mass_kg=mass,
                             wiring_mass_kg=.150, servo_count=len(servos))


def urdf_checks(report, data, urdf, operating_pose_deg, pitch_limits_deg):
    xml = ET.parse(urdf).getroot()
    nodes = {node.attrib["name"]: node for node in xml.findall("link")}
    check(report, "urdf_unique_links", len(nodes) == len(xml.findall("link")) == 14)
    for name, record in data["links"].items():
        inertial = nodes[name].find("inertial")
        origin = inertial.find("origin")
        center = np.fromstring(origin.attrib.get("xyz", "0 0 0"), sep=" ")
        rotation = baseline.rpy_matrix(np.fromstring(origin.attrib.get("rpy", "0 0 0"), sep=" "))
        tensor = baseline.tensor({"inertia_kg_m2": {key: float(value)
                                                  for key, value in inertial.find("inertia").attrib.items()}})
        compare(report, f"urdf_xml_inertial:{name}", record,
                properties(float(inertial.find("mass").attrib["value"]), center*1000, rotation@tensor@rotation.T))
    joints = {joint.attrib["name"]: joint for joint in xml.findall("joint")}
    parameters = data["parameters"]
    expected_names = {"phone_pan", *(f"{kind}_{leg}" for kind in ("yaw", "hip", "knee")
                                     for leg in parameters["leg_azimuth_deg"])}
    check(report, "urdf_joint_names", set(joints) == expected_names and len(joints) == len(xml.findall("joint")) == 13)
    yaw_limit = parameters["yaw_operating_limit_deg"]
    check(report, "configured_yaw_operating_limit", math.isfinite(yaw_limit) and 0 < yaw_limit <= 180,
          yaw_operating_limit_deg=yaw_limit)
    limits_by_kind = {"yaw": [-yaw_limit, yaw_limit], **pitch_limits_deg}
    check(report, "r5_segment_dimensions", math.isfinite(parameters["coxa_mm"]) and parameters["coxa_mm"] > 0
          and abs(parameters["femur_mm"]-90) <= 1e-10 and abs(parameters["tibia_mm"]-105) <= 1e-10,
          coxa_mm=parameters["coxa_mm"], femur_mm=parameters["femur_mm"], tibia_mm=parameters["tibia_mm"])
    report["joint_contract"] = {"limits_deg": limits_by_kind, "operating_pose_deg": list(operating_pose_deg),
                               "joint_origins_source": "Frozen manifest dimensions and leg azimuths"}
    check(report, "operating_pose_within_joint_limits", all(limits_by_kind[kind][0] <= angle <= limits_by_kind[kind][1]
          for kind, angle in zip(("yaw", "hip", "knee"), operating_pose_deg)))
    for name, joint in joints.items():
        limit = joint.find("limit").attrib
        if name == "phone_pan":
            expected_type, parent, child, axis, limits = "continuous", "base", "phone_pan", [0, 0, 1], None
            expected_origin = np.asarray(parameters["phone_pan_origin_mm"])*.001
            expected_rotation = np.eye(3)
        else:
            kind, leg = name.split("_")
            parent, child = {"yaw": ("base", f"coxa_{leg}"), "hip": (f"coxa_{leg}", f"femur_{leg}"),
                             "knee": (f"femur_{leg}", f"tibia_{leg}")}[kind]
            expected_type, axis = "revolute", [0, 0, 1] if kind == "yaw" else [0, 1, 0]
            limits = np.radians(limits_by_kind[kind])
            if kind == "yaw":
                azimuth = math.radians(parameters["leg_azimuth_deg"][leg])
                expected_origin = np.array([parameters["yaw_radius_mm"]*math.cos(azimuth),
                                            parameters["yaw_radius_mm"]*math.sin(azimuth),
                                            parameters["yaw_height_mm"]])*.001
                expected_rotation = baseline.rpy_matrix([0, 0, azimuth])
            else:
                dimension = parameters["coxa_mm"] if kind == "hip" else parameters["femur_mm"]
                expected_origin, expected_rotation = np.array([dimension*.001, 0, 0]), np.eye(3)
        origin = joint.find("origin")
        actual_origin = np.fromstring(origin.attrib.get("xyz", "0 0 0"), sep=" ")
        actual_rotation = baseline.rpy_matrix(np.fromstring(origin.attrib.get("rpy", "0 0 0"), sep=" "))
        origin_error = float(np.max(np.abs(actual_origin-expected_origin)))
        rotation_error = float(np.max(np.abs(actual_rotation-expected_rotation)))
        check(report, f"urdf_joint_origin:{name}", origin_error <= TOLERANCES["urdf_origin_m"]
              and rotation_error <= TOLERANCES["joint_angle_rad"], origin_error_m=origin_error,
              rotation_matrix_error=rotation_error, expected_origin_m=expected_origin.tolist(),
              actual_origin_m=actual_origin.tolist())
        valid = (joint.attrib["type"] == expected_type and joint.find("parent").attrib["link"] == parent
                 and joint.find("child").attrib["link"] == child
                 and np.array_equal(np.fromstring(joint.find("axis").attrib["xyz"], sep=" "), axis)
                 and abs(float(limit["effort"])-.588) <= 1e-12 and abs(float(limit["velocity"])-1) <= 1e-12)
        measured_limits = None if limits is None else [float(limit["lower"]), float(limit["upper"])]
        if limits is not None:
            valid = valid and np.max(np.abs(limits-measured_limits)) <= TOLERANCES["joint_angle_rad"]
        check(report, f"urdf_joint_contract:{name}", valid, limit_rad=measured_limits,
              joint_type=joint.attrib["type"], effort_nm=float(limit["effort"]), velocity_rad_s=float(limit["velocity"]))


def operating_pose_checks(report, data, urdf, operating_pose_deg):
    """Probe the specified operating pose separately from the CAD assembly pose."""
    bullet = baseline.p
    parameters = data["parameters"]
    angles_deg = list(operating_pose_deg)
    angles = {leg: np.radians(angles_deg) for leg in parameters["leg_azimuth_deg"]}
    position, rotation = np.array([0, 0, .3]), np.eye(3)
    frames = baseline.independent_frames(parameters, position, rotation, angles, 0)
    report["operating_pose_probe"] = {
        "base_position_m": position.tolist(), "base_rpy_deg": [0, 0, 0],
        "leg_angles_deg": {leg: angles_deg for leg in angles}, "phone_pan_deg": 0,
        "cad_neutral_angles_deg": parameters["neutral_deg"],
        "scope": "Read-only kinematics at the requested operating pose. The dynamic run must record its own initial joint angles.",
    }
    client = bullet.connect(bullet.DIRECT)
    try:
        robot = bullet.loadURDF(str(urdf), basePosition=position.tolist(),
                               flags=bullet.URDF_USE_INERTIA_FROM_FILE, physicsClientId=client)
        names, joints = {"base": -1}, {}
        for index in range(bullet.getNumJoints(robot, physicsClientId=client)):
            info = bullet.getJointInfo(robot, index, physicsClientId=client)
            names[info[12].decode()] = index
            joints[info[1].decode()] = index
        for leg, values in angles.items():
            for kind, angle in zip(("yaw", "hip", "knee"), values):
                bullet.resetJointState(robot, joints[f"{kind}_{leg}"], float(angle), physicsClientId=client)
        bullet.resetJointState(robot, joints["phone_pan"], 0, physicsClientId=client)
        for name, index in names.items():
            if index == -1:
                dynamics = bullet.getDynamicsInfo(robot, index, physicsClientId=client)
                com, quaternion = bullet.getBasePositionAndOrientation(robot, physicsClientId=client)
                actual_rotation = baseline.quaternion_matrix(quaternion)@baseline.quaternion_matrix(dynamics[4]).T
                actual_position = np.asarray(com)-actual_rotation@np.asarray(dynamics[3])
            else:
                state = bullet.getLinkState(robot, index, computeForwardKinematics=True, physicsClientId=client)
                actual_position, actual_rotation = np.asarray(state[4]), baseline.quaternion_matrix(state[5])
            expected_position, expected_rotation = frames[name]
            position_error = float(np.max(np.abs(actual_position-expected_position)))
            rotation_error = float(np.max(np.abs(actual_rotation-expected_rotation)))
            check(report, f"r5_operating_pose_frame:{name}", position_error <= baseline.TOLERANCES["frame_position_m"]
                  and rotation_error <= baseline.TOLERANCES["frame_rotation_matrix"],
                  position_error_m=position_error, rotation_matrix_error=rotation_error)
    finally:
        bullet.disconnect(client)


def audit(manifest, urdf, solid_path, production_path, fastener_path, expected_hashes,
          operating_pose_deg, pitch_limits_deg=None):
    report = {"created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "audit_fail",
              "inputs": {"bound_files": {}, "meshes": {}, "expected_sha256": expected_hashes}, "tolerances": TOLERANCES,
              "reused_frame_probe_tolerances": baseline.TOLERANCES, "checks": [], "errors": [],
              "scope": "Checks frozen deposition properties through print-STL to link transforms, assembled tensors, distributed high fastener mass, URDF values, CAD visual frames, landscape phone collision and Bullet kinematic probes without stepping. GCode integration is covered by a separate source audit. Physical mass, fit and walking are not measured here.",
              "method": "Source COM tensors receive only R I R^T and COM receives R c + t. Link tensors are summed at the origin and translated to the combined COM. No deposition density, uniform box inertia, GCode inverse transform or additional layer-height correction is applied."}
    try:
        if set(expected_hashes) != set(REQUIRED_HASH_LABELS):
            raise ValueError("Expected hashes are required for all five frozen assembly inputs")
        if len(operating_pose_deg) != 3 or not all(math.isfinite(value) for value in operating_pose_deg):
            raise ValueError("Supply the frozen run's finite yaw, hip and knee operating angles")
        paths = {"printed_manifest": manifest, "urdf": urdf, "solid_manifest": solid_path,
                 "production_properties": production_path, "fastener_properties": fastener_path,
                 "audit_source": Path(__file__), "reused_frame_probe_source": Path(baseline.__file__)}
        for label, path in paths.items():
            digest = bind(report, label, path)
            if label in expected_hashes:
                check(report, f"frozen_input:{label}", digest == expected_hashes[label], actual_sha256=digest)
        if any(not item["passed"] for item in report["checks"]):
            raise ValueError("Frozen input identity check failed; no assembly or Bullet probe was run")
        load = lambda path: json.loads(path.read_text(encoding="utf-8-sig"))
        data, solid, production, fasteners = map(load, (manifest, solid_path, production_path, fastener_path))
        check(report, "r5_revision_identity", data["revision"] == solid["revision"]
              == production["source_revision"] == EXPECTED_REVISION
              and data["parameters"]["revision"] == EXPECTED_REVISION
              and data["parameters"]["knee_servo_orientation"] == "tail inward toward hip"
              and data["parameters"]["hip_servo_orientation"] == "tail inward toward yaw joint"
              and data["parameters"]["tibia_form"] == "straight knee-to-toe beam with detachable auxiliary support")
        if not report["checks"][-1]["passed"]:
            raise ValueError("The selected inputs do not describe the expected R5 inward-hip assembly")
        selected_limits = pitch_limits_deg or {kind: data["parameters"].get("joint_limits_deg", {}).get(kind, default)
                                              for kind, default in (("hip", [3, 35]), ("knee", [30, 100]))}
        if (set(selected_limits) != {"hip", "knee"}
                or any(len(values) != 2 or not all(math.isfinite(value) for value in values) or values[0] >= values[1]
                       for values in selected_limits.values())):
            raise ValueError("Each pitch joint requires finite increasing lower and upper angle limits")
        for relative_path, expected_hash in solid["source_hashes"].items():
            actual_hash = bind(report, f"cad_source:{relative_path}", solid_path.parent.parent/relative_path)
            check(report, f"cad_source_current:{relative_path}", actual_hash == expected_hash)
        settings_path = ROOT/"settings.json"
        bind(report, "design_settings", settings_path)
        check(report, "manifest_parameters_match_settings", data["parameters"] == load(settings_path))
        model = data["mass_model"]
        check(report, "printed_mass_model_and_source_bindings", data["units"] == "mm"
              and model["kind"] == "Cura_model_deposition_high_fasteners"
              and model["as_sliced"] is True and model["physical_measurement"] is False
              and model["fasteners"] == "high" and abs(model["wire_allowance_kg"]-.150) <= 1e-12
              and model["source_solid_manifest_sha256"] == sha256(solid_path)
              and model["source_production_properties_sha256"] == sha256(production_path)
              and production["source_manifest_hash"] == sha256(solid_path)
              and production["status"] == "pass")
        integrator_hash = bind(report, "printed_manifest_integrator", ROOT/"printing/build_printed_mass.py")
        check(report, "printed_manifest_integrator_binding", integrator_hash == model["integrator_sha256"])
        if any(not item["passed"] for item in report["checks"]):
            raise ValueError("Source provenance or mass-model checks failed; no assembly or Bullet probe was run")
        printed_checks(report, data, solid, production, manifest)
        baseline.servo_case_checks(report, data)
        hardware_checks(report, data, fasteners, fastener_path)
        urdf_checks(report, data, urdf, operating_pose_deg, selected_limits)
        baseline.mesh_checks(report, data, manifest, urdf)
        baseline.bullet_checks(report, data, urdf)
        operating_pose_checks(report, data, urdf, operating_pose_deg)
        unchanged = all(sha256(entry["path"]) == entry["sha256"] for entry in report["inputs"]["bound_files"].values())
        unchanged = unchanged and all(sha256(entry[f"{kind}_mesh_path"]) == entry[f"{kind}_mesh_sha256"]
                                    for entry in report["inputs"]["meshes"].values() for kind in ("manifest", "urdf"))
        check(report, "inputs_unchanged_during_audit", unchanged,
              bound_file_count=len(report["inputs"]["bound_files"]), cad_visual_link_count=len(report["inputs"]["meshes"]))
    except Exception as error:
        report["errors"].append(f"{type(error).__name__}: {error}")
    report["failed_checks"] = [item["name"] for item in report["checks"] if not item["passed"]]
    report["passed"] = bool(report["checks"]) and not report["failed_checks"] and not report["errors"]
    report["status"] = "audit_pass" if report["passed"] else "audit_fail"
    report["check_count"] = len(report["checks"])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT/"cad/output/assembly_manifest_as_printed.json")
    parser.add_argument("--solid-manifest", type=Path, default=ROOT/"cad/output/assembly_manifest.json")
    parser.add_argument("--production-properties", type=Path, default=ROOT/"manufacturing/slicing_r5/output/production_mass_properties.json")
    parser.add_argument("--fastener-properties", type=Path, default=ROOT/"printing/fastener_mass.json")
    parser.add_argument("--urdf", type=Path, default=ROOT/"simulation/output_r5_printed_nominal/quadruped.urdf")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--operating-pose-deg", nargs=3, type=float, required=True, metavar=("YAW", "HIP", "KNEE"))
    parser.add_argument("--hip-limits-deg", nargs=2, type=float, metavar=("LOWER", "UPPER"))
    parser.add_argument("--knee-limits-deg", nargs=2, type=float, metavar=("LOWER", "UPPER"))
    for label in REQUIRED_HASH_LABELS:
        parser.add_argument(f"--expected-{label.replace('_', '-')}-sha256", required=True)
    args = parser.parse_args()
    inputs = [path.resolve() for path in (args.manifest, args.urdf, args.solid_manifest,
                                         args.production_properties, args.fastener_properties)]
    output = args.output.resolve()
    expected_hashes = {label: getattr(args, f"expected_{label}_sha256").lower() for label in REQUIRED_HASH_LABELS}
    if any(len(value) != 64 or any(character not in "0123456789abcdef" for character in value)
           for value in expected_hashes.values()):
        parser.error("Each expected SHA256 must contain exactly 64 hexadecimal characters")
    if output in {*inputs, Path(__file__).resolve(), Path(baseline.__file__).resolve()}:
        parser.error("The audit output must not overwrite its source or inputs")
    if output != OUTPUT.resolve():
        parser.error("This entry point writes only output_r5_printed_nominal/printed_mass_frame_audit.json")
    if (args.hip_limits_deg is None) != (args.knee_limits_deg is None):
        parser.error("Supply both hip and knee limit overrides together")
    pitch_limits = None if args.hip_limits_deg is None else {"hip": args.hip_limits_deg, "knee": args.knee_limits_deg}
    report = audit(*inputs, expected_hashes, args.operating_pose_deg, pitch_limits)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["check_count"],
                      "failed_checks": report["failed_checks"], "errors": report["errors"],
                      "summary": report.get("summary", {}), "output_path": str(output)}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
