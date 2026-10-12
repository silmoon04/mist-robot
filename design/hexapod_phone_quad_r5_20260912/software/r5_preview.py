"""Validate R5 joint requests locally. This module has no hardware transport."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent
DEFAULT_MANIFEST = DESIGN / "cad/output/assembly_manifest.json"
REVISION = "hex_quad_r5_inward_hip_straight_tibia"
LEGS = ("FL", "FR", "RL", "RR")
KINDS = (("yaw", "coxa"), ("hip", "femur"), ("knee", "tibia"))


class ContractError(ValueError):
    pass


def finite_number(value, label):
    if type(value) not in (int, float):
        raise ContractError(f"{label} must be a finite number, not a boolean or string")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ContractError(f"{label} is outside the supported numeric range") from exc
    if not math.isfinite(number):
        raise ContractError(f"{label} must be finite")
    return number


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ContractError(f"Nonfinite JSON constant: {value}")


def read_json(path, max_bytes=4_000_000):
    raw = Path(path).read_bytes()
    if len(raw) > max_bytes:
        raise ContractError("Input exceeds its size limit")
    return decode_json(raw)


def decode_json(raw):
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=strict_object,
                          parse_constant=reject_constant)
    except ValueError as exc:
        raise ContractError(f"Invalid JSON input: {exc}") from exc


def exact_fields(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ContractError(f"{label} requires exactly these fields: {', '.join(fields)}")


def build_profile(manifest_path=DEFAULT_MANIFEST):
    path = Path(manifest_path).resolve()
    raw = path.read_bytes()
    if len(raw) > 4_000_000:
        raise ContractError("CAD manifest exceeds its size limit")
    manifest = decode_json(raw)
    if not isinstance(manifest, dict):
        raise ContractError("CAD manifest must be an object")
    if manifest.get("revision") != REVISION or manifest.get("units") != "mm":
        raise ContractError("Only the R5 inward-hip and straight-tibia manifest in mm is supported")
    parameters = manifest.get("parameters", {})
    if not isinstance(parameters, dict) or type(parameters.get("servo_count")) is not int or parameters["servo_count"] != 13:
        raise ContractError("R5 requires exactly thirteen servos")
    dimensions = {name: finite_number(parameters.get(name), name)
                  for name in ("coxa_mm", "femur_mm", "tibia_mm")}
    if any(value <= 0 for value in dimensions.values()):
        raise ContractError("CAD link dimensions must be positive")
    links = manifest.get("links")
    expected = {"base", "phone_pan"} | {f"{kind}_{leg}" for leg in LEGS
                                              for _, kind in KINDS}
    if not isinstance(links, dict) or set(links) != expected:
        raise ContractError("Manifest must contain the fourteen R5 links exactly")
    rows = []
    for leg_index, leg in enumerate(LEGS):
        for joint_index, (joint_kind, link_kind) in enumerate(KINDS):
            parent = "base" if joint_index == 0 else f"{KINDS[joint_index - 1][1]}_{leg}"
            rows.append((f"{joint_kind}_{leg}", f"{link_kind}_{leg}", parent,
                         3 * leg_index + joint_index + 1, "revolute"))
    rows.append(("phone_pan", "phone_pan", "base", 13, "continuous"))
    joints = []
    for name, child, parent, servo_id, joint_type in rows:
        if not isinstance(links[child], dict):
            raise ContractError(f"CAD link must be an object: {child}")
        joint = links[child].get("joint")
        if not isinstance(joint, dict) or joint.get("parent") != parent or joint.get("type") != joint_type:
            raise ContractError(f"Unexpected CAD joint relationship for {name}")
        axis = joint.get("axis")
        expected_axis = [0, 0, 1] if name.startswith("yaw_") or name == "phone_pan" else [0, 1, 0]
        if axis != expected_axis:
            raise ContractError(f"Unexpected CAD axis for {name}")
        origin = joint.get("origin_mm")
        if not isinstance(origin, list) or len(origin) != 3:
            raise ContractError(f"Missing CAD origin for {name}")
        origin = [finite_number(value, f"{name} origin") for value in origin]
        if name.startswith("hip_") or name.startswith("knee_"):
            length = dimensions["coxa_mm" if name.startswith("hip_") else "femur_mm"]
            if any(abs(actual - expected) > 1e-9 for actual, expected in zip(origin, (length, 0, 0))):
                raise ContractError(f"CAD origin for {name} disagrees with link dimensions")
        limits = joint.get("limits_rad")
        if not isinstance(limits, list) or len(limits) != 2:
            raise ContractError(f"Missing CAD limits for {name}")
        lower, upper = [finite_number(value, f"{name} limit") for value in limits]
        neutral = finite_number(joint.get("neutral_angle_rad"), f"{name} neutral")
        if not lower < upper or not lower <= neutral <= upper:
            raise ContractError(f"Invalid limits or neutral angle for {name}")
        if name == "phone_pan" and (abs(lower + math.pi) > 1e-9 or abs(upper - math.pi) > 1e-9):
            raise ContractError("Phone pan preview requires the CAD principal-angle interval")
        joints.append({
            "joint_name": name, "child_link": child, "parent_link": parent,
            "proposed_servo_id": servo_id, "axis": axis, "joint_type": joint_type,
            "origin_mm": origin,
            "preview_limits_rad": [lower, upper], "neutral_angle_rad": neutral,
            "calibration": {"status": "not_commissioned", "delivered_servo_identity": None,
                            "reference_tick": None, "direction_sign": None,
                            "minimum_tick": None, "maximum_tick": None,
                            "mode_and_startup_position_verified": False},
        })
    try:
        source_path = path.relative_to(DESIGN).as_posix()
    except ValueError:
        source_path = path.as_posix()
    return {
        "schema_version": 1, "design_revision": REVISION,
        "manifest_path": source_path,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "link_dimensions_mm": dimensions,
        "execution": "dry_run", "hardware_connected": False, "actuation_supported": False,
        "body": "four legs with three direct joints each and one phone pan; no wheels",
        "id_status": "Proposal from printing/WIRING.md; no IDs were read or assigned",
        "angle_units": "radians in the new CAD and URDF joint frames",
        "limit_status": "Geometric preview ranges only; physical servo limits are unmeasured",
        "pan_status": "Principal-angle preview only; no wrap counting or startup recovery",
        "joints": joints,
    }


def neutral_request(profile):
    return {"schema_version": 1, "action": "joint_pose",
            "args": {"positions_rad": {row["joint_name"]: row["neutral_angle_rad"]
                                       for row in profile["joints"]}, "usb_connected": False}}


def preview(request, profile=None, manifest_path=DEFAULT_MANIFEST, mode="dry_run"):
    if mode != "dry_run":
        raise ContractError("Actuation disabled: R5 calibration is missing and this package has no hardware transport")
    current = build_profile(manifest_path)
    if profile is not None and profile != current:
        raise ContractError("Profile differs from the current CAD or uncommissioned ID proposal; regenerate it")
    exact_fields(request, ("schema_version", "action", "args"), "Request")
    if type(request["schema_version"]) is not int or request["schema_version"] != 1:
        raise ContractError("Unsupported request schema")
    action, args = request["action"], request["args"]
    if not isinstance(action, str) or not isinstance(args, dict):
        raise ContractError("Action must be a string and args must be an object")
    result = {"schema_version": 1, "design_revision": REVISION,
              "manifest_sha256": current["manifest_sha256"], "action": action,
              "execution": "dry_run", "hardware_connected": False,
              "actuated": False, "raw_servo_counts": None, "transport_packets": None}
    if action == "get_capabilities":
        exact_fields(args, (), "Capability arguments")
        return {**result, "profile": current}
    if action == "stop":
        exact_fields(args, (), "Stop arguments")
        return {**result, "physical_stop_confirmed": False,
                "message": "Preview stop only. No motor connection exists."}
    if action not in {"joint_pose", "phone_pan"}:
        raise ContractError("Unsupported preview action. Wheel drive, gait, pose IK and gaze-to-pan conversion are not implemented")
    exact_fields(args, ("positions_rad", "usb_connected") if action == "joint_pose"
                 else ("angle_rad", "usb_connected"), "Motion preview arguments")
    if type(args["usb_connected"]) is not bool:
        raise ContractError("usb_connected must be an explicit boolean")
    if action == "joint_pose":
        positions = args["positions_rad"]
        exact_fields(positions, tuple(row["joint_name"] for row in current["joints"]), "Joint pose")
    else:
        positions = {"phone_pan": args["angle_rad"]}
    if args["usb_connected"]:
        raise ContractError("Pan preview is disabled while USB is attached; park and service separately")
    targets = []
    for row in current["joints"]:
        name = row["joint_name"]
        if name not in positions:
            continue
        angle = finite_number(positions[name], name)
        lower, upper = row["preview_limits_rad"]
        if not lower <= angle <= upper:
            raise ContractError(f"{name} is outside the CAD preview interval [{lower}, {upper}] radians")
        targets.append({"joint_name": name, "proposed_servo_id": row["proposed_servo_id"],
                        "angle_rad": angle, "angle_deg": math.degrees(angle)})
    return {**result, "geometry_preview_valid": True, "targets": targets,
            "message": "Angles passed geometric range checks only. No gait, collision, load or hardware validation occurred."}


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("profile", "neutral", "preview"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--mode", choices=("dry_run", "hardware"), default="dry_run")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.mode != "dry_run":
            raise ContractError("Actuation disabled: R5 calibration is missing and this package has no hardware transport")
        if args.operation == "profile":
            result = build_profile(args.manifest)
        elif args.operation == "neutral":
            result = neutral_request(build_profile(args.manifest))
        else:
            if args.request is None:
                raise ContractError("preview requires --request")
            profile = read_json(args.profile, 262_144) if args.profile else None
            result = preview(read_json(args.request, 65_536), profile, args.manifest)
        if args.output:
            write_json(args.output, result)
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ContractError, OSError, json.JSONDecodeError, UnicodeError) as exc:
        print(json.dumps({"error": str(exc), "execution": "dry_run", "actuated": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
