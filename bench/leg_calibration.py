"""Persistent calibration state for the physical three-servo test leg."""

from __future__ import annotations

from copy import deepcopy
import json
import os
import tempfile
from typing import Any, Mapping

try:
    from .leg_kinematics import LegGeometry
except ImportError:  # Direct execution through bench/servo_bench.py.
    from leg_kinematics import LegGeometry


ROLE_NAMES = ("roll", "hip", "knee_driver")
REFERENCE_SERVO_ANGLES_DEG = {
    "roll": 0.0,
    "hip": 90.0,
    "knee_driver": 0.0,
}


def normalize_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Add non-destructive defaults introduced after the first bench build."""

    normalized = deepcopy(dict(config))
    normalized.setdefault("linkage", {
        "driver_mm": 40.0,
        "coupler_mm": 110.0,
        "follower_mm": 40.0,
        "follower_to_tibia_deg": 180.0,
        "reference_q3_deg": -90.0,
        "relative_input_min_deg": -30.0,
        "relative_input_max_deg": 40.0,
        "commissioning_margin_deg": 5.0,
    })
    linkage = normalized.get("linkage")
    if isinstance(linkage, dict):
        linkage.setdefault("reference_q3_deg", -90.0)
        linkage.setdefault("relative_input_min_deg", -30.0)
        linkage.setdefault("relative_input_max_deg", 40.0)
        linkage.setdefault("commissioning_margin_deg", 5.0)
    roles = normalized.get("roles")
    if isinstance(roles, Mapping):
        for name, angle in REFERENCE_SERVO_ANGLES_DEG.items():
            role = roles.get(name)
            if isinstance(role, dict):
                role.setdefault("reference_angle_deg", angle)
                role.setdefault("endpoint_a_tick", None)
                role.setdefault("endpoint_b_tick", None)
    return normalized


def default_config() -> dict[str, Any]:
    """Return a fresh, deliberately uncalibrated configuration."""

    return {
        "schema_version": 1,
        "geometry": {
            "hip_offset_mm": 32.0,
            "femur_mm": 110.0,
            "tibia_mm": 70.0,
        },
        "knee_sign": -1,
        "knee_driver_mode": "absolute_tibia_1to1",
        "linkage": {
            "driver_mm": 40.0,
            "coupler_mm": 110.0,
            "follower_mm": 40.0,
            "follower_to_tibia_deg": 180.0,
            "reference_q3_deg": -90.0,
            "relative_input_min_deg": -30.0,
            "relative_input_max_deg": 40.0,
            "commissioning_margin_deg": 5.0,
        },
        "roles": {
            "roll": {
                "id": 1,
                "label": "hip roll / coxa",
                "reference_angle_deg": 0.0,
                "endpoint_a_tick": None,
                "endpoint_b_tick": None,
                "center_tick": None,
                "sign": None,
                "min_tick": None,
                "max_tick": None,
            },
            "hip": {
                "id": 2,
                "label": "femur / hip pitch",
                "reference_angle_deg": 90.0,
                "endpoint_a_tick": None,
                "endpoint_b_tick": None,
                "center_tick": None,
                "sign": None,
                "min_tick": None,
                "max_tick": None,
            },
            "knee_driver": {
                "id": 3,
                "label": "remote knee driver",
                "reference_angle_deg": 0.0,
                "endpoint_a_tick": None,
                "endpoint_b_tick": None,
                "center_tick": None,
                "sign": None,
                "min_tick": None,
                "max_tick": None,
            },
        },
    }


def validate_config(config: Mapping[str, Any]) -> None:
    if int(config.get("schema_version", 0)) != 1:
        raise ValueError("unsupported calibration schema_version")
    if config.get("knee_driver_mode") != "absolute_tibia_1to1":
        raise ValueError("this tool only supports the current 1:1 remote-knee linkage")
    if config.get("knee_sign") not in (-1, 1):
        raise ValueError("knee_sign must be -1 or +1")

    linkage = config.get("linkage")
    if not isinstance(linkage, Mapping):
        raise ValueError("linkage must be an object")
    for field in ("driver_mm", "coupler_mm", "follower_mm"):
        if float(linkage.get(field, 0)) <= 0:
            raise ValueError(f"linkage {field} must be positive")
    if abs(float(linkage["driver_mm"]) - float(linkage["follower_mm"])) > 1e-6:
        raise ValueError("the 1:1 model requires equal driver and follower lengths")
    relative_min = float(linkage.get("relative_input_min_deg", 1))
    relative_max = float(linkage.get("relative_input_max_deg", -1))
    if relative_min >= relative_max:
        raise ValueError("relative_input_min_deg must be less than relative_input_max_deg")
    margin = float(linkage.get("commissioning_margin_deg", 0))
    if margin < 0 or relative_min + margin >= relative_max - margin:
        raise ValueError("commissioning_margin_deg leaves no usable linkage range")

    geometry = config.get("geometry")
    if not isinstance(geometry, Mapping):
        raise ValueError("geometry must be an object")
    LegGeometry(
        float(geometry.get("hip_offset_mm", -1)),
        float(geometry.get("femur_mm", 0)),
        float(geometry.get("tibia_mm", 0)),
    ).validate()

    roles = config.get("roles")
    if not isinstance(roles, Mapping) or set(roles) != set(ROLE_NAMES):
        raise ValueError(f"roles must be exactly: {', '.join(ROLE_NAMES)}")
    ids: list[int] = []
    for name in ROLE_NAMES:
        role = roles[name]
        if not isinstance(role, Mapping):
            raise ValueError(f"{name} calibration must be an object")
        servo_id = int(role.get("id", -1))
        if not 0 <= servo_id <= 253:
            raise ValueError(f"{name} id must be 0..253")
        ids.append(servo_id)
        sign = role.get("sign")
        if sign not in (None, -1, 1):
            raise ValueError(f"{name} sign must be null, -1 or +1")
        reference_angle = float(role.get("reference_angle_deg", 0))
        if not -360.0 <= reference_angle <= 360.0:
            raise ValueError(f"{name} reference_angle_deg must be within +/-360")
        for field in ("center_tick", "endpoint_a_tick", "endpoint_b_tick", "min_tick", "max_tick"):
            value = role.get(field)
            if value is not None and not 0 <= int(value) <= 4095:
                raise ValueError(f"{name} {field} must be null or 0..4095")
        minimum, maximum = role.get("min_tick"), role.get("max_tick")
        if minimum is not None and maximum is not None and int(minimum) >= int(maximum):
            raise ValueError(f"{name} min_tick must be less than max_tick")
    if len(set(ids)) != len(ids):
        raise ValueError("roll, hip and knee_driver must use distinct servo IDs")


def calibration_ready(config: Mapping[str, Any]) -> bool:
    validate_config(config)
    roles = config["roles"]
    return all(
        roles[name].get("center_tick") is not None
        and roles[name].get("sign") in (-1, 1)
        and roles[name].get("min_tick") is not None
        and roles[name].get("max_tick") is not None
        for name in ROLE_NAMES
    )


def geometry_from_config(config: Mapping[str, Any]) -> LegGeometry:
    validate_config(config)
    geometry = config["geometry"]
    return LegGeometry(
        hip_offset_mm=float(geometry["hip_offset_mm"]),
        femur_mm=float(geometry["femur_mm"]),
        tibia_mm=float(geometry["tibia_mm"]),
    )


class CalibrationStore:
    """Load and atomically save one calibration JSON file."""

    def __init__(self, path: str):
        self.path = os.path.abspath(path)

    def load(self) -> dict[str, Any]:
        if not os.path.exists(self.path):
            return default_config()
        with open(self.path, "r", encoding="utf-8") as handle:
            config = normalize_config(json.load(handle))
        validate_config(config)
        return config

    def save(self, config: Mapping[str, Any]) -> dict[str, Any]:
        candidate = normalize_config(config)
        validate_config(candidate)
        directory = os.path.dirname(self.path)
        os.makedirs(directory, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="leg_calibration_", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(candidate, handle, indent=2)
                handle.write("\n")
            os.replace(temporary, self.path)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
        return candidate

    def set_sign(self, role: str, sign: int) -> dict[str, Any]:
        if role not in ROLE_NAMES or sign not in (-1, 1):
            raise ValueError("role/sign must be a known role and -1 or +1")
        config = self.load()
        config["roles"][role]["sign"] = sign
        return self.save(config)

    def capture(self, role: str, field: str, tick: int) -> dict[str, Any]:
        if role not in ROLE_NAMES:
            raise ValueError(f"unknown role: {role}")
        if field not in ("center_tick", "min_tick", "max_tick"):
            raise ValueError(f"unsupported capture field: {field}")
        if not 0 <= int(tick) <= 4095:
            raise ValueError("captured tick must be 0..4095")
        config = self.load()
        config["roles"][role][field] = int(tick)
        return self.save(config)

    def capture_endpoint(self, role: str, endpoint: str, tick: int) -> dict[str, Any]:
        if role not in ROLE_NAMES:
            raise ValueError(f"unknown role: {role}")
        if endpoint not in ("a", "b"):
            raise ValueError("endpoint must be a or b")
        if not 0 <= int(tick) <= 4095:
            raise ValueError("captured tick must be 0..4095")
        config = self.load()
        role_config = config["roles"][role]
        role_config[f"endpoint_{endpoint}_tick"] = int(tick)
        a = role_config.get("endpoint_a_tick")
        b = role_config.get("endpoint_b_tick")
        if a is not None and b is not None:
            role_config["min_tick"] = min(int(a), int(b))
            role_config["max_tick"] = max(int(a), int(b))
        else:
            role_config["min_tick"] = None
            role_config["max_tick"] = None
        return self.save(config)
