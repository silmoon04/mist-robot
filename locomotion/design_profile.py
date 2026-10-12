"""Audit a direct-drive leg profile and record measurements without enabling it.

Only a serial +Z yaw / +Y hip / +Y knee chain is supported. A profile does
not replace the R7 model exporter, gait assumptions or hardware calibration.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

try:
    from .kinematics import LegGeometry, validate_angles, validate_limits
except ImportError:
    from kinematics import LegGeometry, validate_angles, validate_limits

HERE = Path(__file__).resolve().parent
DEFAULT_PROFILE = HERE / "profiles" / "r7_direct.json"
FAMILY = "direct_yaw_pitch_pitch"
LENGTH_KEYS = ("coxa_m", "femur_m", "tibia_m")
ADAPTATION_NOTE = "Profile audit only. Another design requires model export, mounts, collision geometry, inertials, gait, actuator control and hardware calibration changes before training or deployment."


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_json(path):
    def reject_constant(value):
        raise ValueError(f"nonfinite JSON number: {value}")
    return json.loads(Path(path).read_text(), parse_constant=reject_constant)


def _positive(value, name, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (value < 0 if allow_zero else value <= 0):
        raise ValueError(f"{name} must be finite and {'nonnegative' if allow_zero else 'positive'}")
    return float(value)


def _vector(value, name):
    result = np.asarray(value, dtype=float)
    if result.shape != (3,) or not np.isfinite(result).all():
        raise ValueError(f"{name} must contain three finite numbers")
    return result


def _same(actual, expected, name):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.allclose(a, b, atol=1e-10, rtol=0):
        raise ValueError(f"{name} differs from declared profile")


def _source(profile_path, entry, name):
    path = (profile_path.parent / entry["path"]).resolve()
    digest = sha256(path)
    expected = entry.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64 or expected != digest:
        raise ValueError(f"{name} SHA-256 mismatch or missing pinned hash: {path}")
    return path, {"path": str(path), "sha256": digest}


def _origin(joint):
    origin = joint.find("origin")
    return {key: _vector([float(v) for v in (origin.get(key, "0 0 0") if origin is not None else "0 0 0").split()], f"joint {key}").tolist() for key in ("xyz", "rpy")}


@dataclass(frozen=True)
class DesignProfile:
    path: Path
    document: dict
    geometry: LegGeometry
    limits: np.ndarray
    neutral: np.ndarray
    report: dict


def load_profile(path=DEFAULT_PROFILE):
    """Load only after hashes, chain geometry, limits and declared masses agree."""
    path = Path(path).resolve()
    doc = _read_json(path)
    if doc.get("schema_version") != 1 or doc.get("family") != FAMILY or doc.get("transmission") != "direct":
        raise ValueError("only schema 1 direct_yaw_pitch_pitch profiles with direct transmission are supported; four-bar mechanisms require another solver")
    if not isinstance(doc.get("profile_id"), str) or not doc["profile_id"].strip():
        raise ValueError("profile_id must be a nonempty string")
    geometry = LegGeometry(**{key: doc["geometry"][key] for key in LENGTH_KEYS})
    limits = validate_limits(np.radians(doc["geometry"]["limits_deg"]))
    neutral = validate_angles(np.radians(doc["geometry"]["neutral_deg"]), limits=limits)
    if geometry.coxa_m + geometry.femur_m * math.cos(neutral[1]) + geometry.tibia_m * math.cos(neutral[1] + neutral[2]) <= 0:
        raise ValueError("neutral must use the outward radial branch")
    source_paths, sources = {}, {}
    for name, entry in doc["sources"].items():
        if name not in ("urdf", "manifest", "config"):
            raise ValueError(f"unsupported source: {name}")
        source_paths[name], sources[name] = _source(path, entry, name)
    if "urdf" not in source_paths:
        raise ValueError("a pinned source URDF is required")
    root = ET.parse(source_paths["urdf"]).getroot()
    if root.tag != "robot" or root.findall(".//mimic") or root.findall(".//transmission") or root.findall(".//loop_joint"):
        raise ValueError("unsupported URDF mechanism; mimic, transmission and loop joints are not direct drive")
    joints = root.findall("joint")
    names = doc["joints"]
    ordered = [names[key] for key in ("yaw", "hip", "knee")]
    if len(set(ordered)) != 3 or sorted(j.get("name") for j in joints if j.get("type") != "fixed") != sorted(ordered):
        raise ValueError("source must contain exactly the three declared revolute joints; extra or unsupported axes require another solver")
    if len({j.get("name") for j in joints}) != len(joints):
        raise ValueError("duplicate URDF joint names")
    links = root.findall("link")
    link_names = {link.get("name") for link in links}
    if len(link_names) != len(links):
        raise ValueError("duplicate URDF link names")
    parents = {}
    for joint in joints:
        parent, child = joint.find("parent").get("link"), joint.find("child").get("link")
        if parent not in link_names or child not in link_names or child in parents:
            raise ValueError("URDF links must form a tree with one parent per child")
        parents[child] = parent
    for link in parents:
        seen, current = set(), link
        while current in parents:
            if current in seen:
                raise ValueError("closed-loop/four-bar URDF is unsupported")
            seen.add(current)
            current = parents[current]
    if len(link_names - set(parents)) != 1:
        raise ValueError("source URDF must be one connected tree")
    chain, joint_report = [], []
    expected_xyz = ([0, 0, 0], [geometry.coxa_m, 0, 0], [geometry.femur_m, 0, 0])
    for index, name in enumerate(ordered):
        joint = next(j for j in joints if j.get("name") == name)
        if joint.get("type") != "revolute":
            raise ValueError("direct-drive joints must be revolute with finite limits")
        origin = _origin(joint)
        axis = _vector([float(v) for v in joint.find("axis").get("xyz").split()], "joint axis")
        _same(origin["xyz"], expected_xyz[index], f"{name} origin")
        _same(origin["rpy"], [0, 0, 0], f"{name} origin rotation")
        _same(axis, [0, 0, 1] if index == 0 else [0, 1, 0], f"{name} axis (unsupported convention)")
        limit = joint.find("limit")
        source_limit = [float(limit.get(key)) for key in ("lower", "upper")]
        _same(source_limit, limits[index], f"{name} limits")
        parent, child = joint.find("parent").get("link"), joint.find("child").get("link")
        if chain and parent != chain[-1]:
            raise ValueError("yaw, hip and knee must form one serial direct-drive chain")
        chain.append(child)
        joint_report.append({"name": name, "parent": parent, "child": child, "xyz_m": origin["xyz"], "rpy_rad": origin["rpy"], "axis": axis.tolist(), "limits_rad": source_limit,
                             "source_effort_nm": _positive(float(limit.get("effort")), "URDF effort"), "source_velocity_rad_s": _positive(float(limit.get("velocity")), "URDF velocity")})
    manifest = _read_json(source_paths["manifest"]) if "manifest" in source_paths else None
    lengths = [getattr(geometry, key) for key in LENGTH_KEYS]
    if manifest is not None:
        _same(np.asarray(manifest["lengths_mm"]) / 1000, lengths, "CAD manifest lengths")
        manifest_limits = manifest["operating_limits_deg"]
        if isinstance(manifest_limits, dict):
            manifest_limits = [manifest_limits[key] for key in ("yaw", "hip", "knee")]
        _same(manifest_limits, doc["geometry"]["limits_deg"], "CAD manifest limits")
        _same(manifest["neutral_deg"], doc["geometry"]["neutral_deg"], "CAD manifest neutral")
    toe = doc["toe_reference"]
    if toe["link"] != chain[-1]:
        raise ValueError("toe reference must be on the knee's child link")
    _same(toe["xyz_m"], [geometry.tibia_m, 0, 0], "toe reference")
    if toe["basis"] == "urdf_fixed_joint":
        toe_joint = next((joint for joint in joints if joint.get("name") == toe["joint"]), None)
        if toe_joint is None or toe_joint.get("type") != "fixed" or toe_joint.find("parent").get("link") != chain[-1]:
            raise ValueError("toe must reference a fixed joint on the tibia")
        _same(_origin(toe_joint)["xyz"], toe["xyz_m"], "source toe origin")
        _same(_origin(toe_joint)["rpy"], [0, 0, 0], "source toe rotation")
    elif toe["basis"] != "cad_manifest_lengths" or manifest is None:
        raise ValueError("tibia length requires a source toe joint or a pinned CAD manifest")
    elif any(joint.get("type") == "fixed" and joint.find("parent").get("link") == chain[-1] for joint in joints):
        raise ValueError("source has fixed frames on the tibia; select and audit the toe joint explicitly")
    masses, declared = {}, doc["declared_link_masses_kg"]
    if set(declared) != link_names:
        raise ValueError("declared masses must cover exactly every source link")
    for link in links:
        name = link.get("name")
        mass = _positive(float(link.find("inertial/mass").get("value")), f"{name} mass", allow_zero=True)
        _positive(declared[name], f"declared {name} mass", allow_zero=True)
        _same(mass, declared[name], f"{name} mass")
        masses[name] = mass
    config_report = None
    if "config" in source_paths:
        config = _read_json(source_paths["config"])
        for key in (*LENGTH_KEYS, "limits_deg", "neutral_deg"):
            _same(config["geometry"][key], doc["geometry"][key], f"config geometry {key}")
        config_root = (path.parent / doc["sources"]["config"]["source_root"]).resolve()
        if (config_root / config["sources"]["leg_urdf"]).resolve() != source_paths["urdf"]:
            raise ValueError("config selects a different source URDF")
        if manifest is not None and (config_root / config["sources"]["leg_manifest"]).resolve() != source_paths["manifest"]:
            raise ValueError("config selects a different CAD manifest")
        config_report = {"actuator_assumptions": config.get("actuator", {}), "body_assumptions": config.get("body", {}), "note": "Source joint effort/velocity and configured actuator limits can differ. Neither is measured actuator performance."}
    calibration = doc["calibration"]
    if calibration.get("status") != "pending":
        raise ValueError("profile calibration must remain pending; measured status belongs in a separate measurement record")
    report = {"schema_version": 1, "profile_id": doc["profile_id"], "family": FAMILY, "profile_sha256": sha256(path), "audit_status": "consistent", "calibration_status": "pending",
              "sources": sources, "geometry_m": dict(zip(LENGTH_KEYS, lengths)), "joints": joint_report, "toe_reference": toe,
              "toe_note": "URDF has no audited toe frame; tibia length comes from the pinned CAD manifest." if toe["basis"] == "cad_manifest_lengths" else "Toe origin agrees with the source URDF fixed joint.",
              "source_link_masses_kg": masses, "source_total_mass_kg": sum(masses.values()), "declared_config": config_report, "adaptation_required": ADAPTATION_NOTE}
    return DesignProfile(path, doc, geometry, limits, neutral, report)


def compare_profiles(profile, baseline):
    """Describe design changes; these deltas are not a performance comparison."""
    return {"baseline_profile_id": baseline.document["profile_id"], "baseline_sha256": baseline.report["profile_sha256"],
            "length_delta_m": {key: getattr(profile.geometry, key) - getattr(baseline.geometry, key) for key in LENGTH_KEYS},
            "limits_delta_rad": (profile.limits - baseline.limits).tolist(), "neutral_delta_rad": (profile.neutral - baseline.neutral).tolist(),
            "source_total_mass_delta_kg": profile.report["source_total_mass_kg"] - baseline.report["source_total_mass_kg"]}


def measurement_template(profile):
    """Leave all physical measurements empty until bench evidence exists."""
    return {"schema_version": 1, "profile_id": profile.document["profile_id"], "profile_sha256": profile.report["profile_sha256"],
            "source_sha256": {key: value["sha256"] for key, value in profile.report["sources"].items()}, "status": "pending",
            "provenance": {"measured_at_utc": None, "operator": None, "instrument": None, "procedure": None,
                           "conditions": {"supply_voltage_v": None, "ambient_temperature_c": None, "duration_s": None, "load_description": None}, "evidence": []},
            "measurements": {"geometry_m": {key: None for key in LENGTH_KEYS}, "link_masses_kg": {key: None for key in profile.report["source_link_masses_kg"]},
                             "actuator": {"continuous_torque_nm": None, "no_load_speed_rad_s": None, "latency_s": None},
                             "joint_zero_offset_rad": [None, None, None], "joint_direction": [None, None, None], "body_com_m": [None, None, None]},
            "notes": "Pending values are not measurements. Keep raw evidence and its SHA-256 hash. This record does not change config.json or enable hardware deployment."}


def audit_measurements(path, profile):
    """Validate supplied measurements and compare them with declared assumptions."""
    path = Path(path).resolve()
    record = _read_json(path)
    template = measurement_template(profile)
    for key in ("schema_version", "profile_id", "profile_sha256", "source_sha256"):
        if record.get(key) != template[key]:
            raise ValueError(f"measurement record {key} does not match the audited profile")
    if record.get("status") not in ("pending", "measured"):
        raise ValueError("measurement status must be pending or measured")
    values, missing = record["measurements"], []
    def check_tree(actual, expected, prefix="measurements"):
        if isinstance(expected, dict):
            if not isinstance(actual, dict) or set(actual) != set(expected):
                raise ValueError(f"{prefix} must match the template fields")
            for key in expected:
                check_tree(actual[key], expected[key], f"{prefix}.{key}")
        elif isinstance(expected, list):
            if not isinstance(actual, list) or len(actual) != len(expected):
                raise ValueError(f"{prefix} must contain three values")
            for index, item in enumerate(actual):
                check_tree(item, None, f"{prefix}[{index}]")
        elif actual is None:
            missing.append(prefix)
        elif "joint_direction" in prefix:
            if isinstance(actual, bool) or actual not in (-1, 1):
                raise ValueError("joint_direction entries must be -1 or 1")
        elif "offset" in prefix or "body_com" in prefix:
            if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(actual):
                raise ValueError(f"{prefix} must be finite")
        else:
            _positive(actual, prefix, allow_zero="latency_s" in prefix or "link_masses_kg" in prefix)
    check_tree(values, template["measurements"])
    provenance = record["provenance"]
    evidence = provenance.get("evidence", [])
    evidence_report = []
    for entry in evidence:
        _, item = _source(path, entry, "measurement evidence")
        evidence_report.append(item)
    if record["status"] == "measured":
        from datetime import datetime
        if missing or not evidence or any(not isinstance(provenance.get(key), str) or not provenance[key].strip() for key in ("measured_at_utc", "operator", "instrument", "procedure")):
            raise ValueError("measured status requires all values, provenance and hashed raw evidence")
        conditions = provenance["conditions"]
        for key in ("supply_voltage_v", "duration_s"):
            _positive(conditions[key], f"measurement conditions {key}")
        temperature = conditions["ambient_temperature_c"]
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not math.isfinite(temperature):
            raise ValueError("measurement ambient temperature must be finite")
        if not isinstance(conditions["load_description"], str) or not conditions["load_description"].strip():
            raise ValueError("measurement load description is required")
        stamp = datetime.fromisoformat(provenance["measured_at_utc"].replace("Z", "+00:00"))
        if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError("measurement timestamp must include UTC timezone")
    config = profile.report["declared_config"]
    assumptions = config["actuator_assumptions"] if config is not None else {}
    return {"status": record["status"], "record_sha256": sha256(path), "missing_fields": missing, "evidence": evidence_report,
            "geometry_delta_m": {key: None if values["geometry_m"][key] is None else values["geometry_m"][key] - getattr(profile.geometry, key) for key in LENGTH_KEYS},
            "link_mass_delta_kg": {key: None if value is None else value - profile.report["source_link_masses_kg"][key] for key, value in values["link_masses_kg"].items()},
            "actuator_comparison": {key: {"measured": values["actuator"][key], "configured": assumptions.get(config_key), "delta": None if values["actuator"][key] is None or config_key not in assumptions else values["actuator"][key] - assumptions[config_key]}
                                    for key, config_key in (("continuous_torque_nm", "torque_limit_nm"), ("no_load_speed_rad_s", "no_load_speed_rad_s"), ("latency_s", "latency_s"))},
            "torque_note": "Measured continuous torque is compared with the configured command cap, which is an analysis choice rather than a claimed measurement.",
            "note": "Differences require review and explicit config/model updates; measurement records never change runtime settings."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "template", "measurements"))
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--baseline", type=Path, help="Audited design profile used for geometry and mass deltas")
    parser.add_argument("--record", type=Path, help="Measurement JSON for the measurements command")
    parser.add_argument("--output", type=Path, help="Write JSON; an existing file is never overwritten")
    args = parser.parse_args(argv)
    try:
        profile = load_profile(args.profile)
        if args.command == "audit":
            result = dict(profile.report)
        elif args.command == "template":
            result = measurement_template(profile)
        else:
            if args.record is None:
                parser.error("measurements requires --record")
            result = audit_measurements(args.record, profile)
        if args.baseline:
            result["baseline_comparison"] = compare_profiles(profile, load_profile(args.baseline))
        payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x") as handle:
                handle.write(payload)
        else:
            print(payload, end="")
        return 0
    except (ValueError, KeyError, TypeError, AttributeError, OSError, ET.ParseError) as error:
        print(f"profile audit failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
