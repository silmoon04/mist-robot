"""Direct +Z yaw, +Y hip, +Y knee kinematics in metres and radians.

Default calls retain the R7 geometry. Other dimensions are for analysis;
model export, mounts, gait and hardware calibration must be adapted together.
Inverse kinematics uses the outward radial branch (positive radial reach).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from collections.abc import Mapping
import numpy as np

COXA = 0.082
FEMUR = 0.090
TIBIA = 0.105
LIMITS = np.radians([[-55.0, 55.0], [-30.0, 65.0], [5.0, 115.0]])
NEUTRAL = np.radians([0.0, 30.0, 81.0])


@dataclass(frozen=True)
class LegGeometry:
    """Lengths between joint origins and from knee origin to toe centre."""

    coxa_m: float = COXA
    femur_m: float = FEMUR
    tibia_m: float = TIBIA

    def __post_init__(self):
        for name in ("coxa_m", "femur_m", "tibia_m"):
            value = getattr(self, name)
            try:
                number = float(value)
            except (TypeError, ValueError) as error:
                raise ValueError(f"{name} must be positive and finite") from error
            if isinstance(value, bool) or not math.isfinite(number) or number <= 0:
                raise ValueError(f"{name} must be positive and finite")
            object.__setattr__(self, name, number)


R7_GEOMETRY = LegGeometry()


def _geometry(value=None):
    if value is None:
        return R7_GEOMETRY
    if isinstance(value, LegGeometry):
        return value
    if isinstance(value, Mapping):
        return LegGeometry(**{key: value[key] for key in ("coxa_m", "femur_m", "tibia_m")})
    raise ValueError("geometry must be a LegGeometry or a mapping of metre lengths")


def validate_limits(limits=None):
    """Return three ordered, finite lower/upper pairs in radians."""
    result = np.asarray(LIMITS if limits is None else limits, dtype=float)
    if result.shape != (3, 2) or not np.isfinite(result).all() or np.any(result[:, 0] >= result[:, 1]):
        raise ValueError("limits must contain three finite lower/upper pairs with lower < upper")
    if result[0,0] < -math.pi or result[0,1] > math.pi:
        raise ValueError("yaw limits must lie in the principal [-pi, pi] interval")
    return result.copy()


def _vector(value, name):
    result = np.asarray(value, dtype=float)
    if result.shape != (3,) or not np.isfinite(result).all():
        raise ValueError(f"{name} must contain three finite numbers")
    return result


def validate_angles(q, tolerance=1e-9, *, limits=None):
    """Reject angles beyond the selected limits; defaults are provisional R7."""
    q = _vector(q, "joint angles")
    selected = validate_limits(limits)
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be finite and nonnegative")
    if np.any(q < selected[:, 0] - tolerance) or np.any(q > selected[:, 1] + tolerance):
        raise ValueError(f"joint angles exceed selected limits: {np.degrees(q).tolist()} degrees")
    return q


def forward(q, check_limits=False, *, geometry=None, limits=None):
    """Toe centre in the local yaw-origin frame, with +Z pointing up."""
    lengths = _geometry(geometry)
    selected = validate_limits(limits)
    yaw, hip, knee = validate_angles(q, limits=selected) if check_limits else _vector(q, "joint angles")
    radial = lengths.coxa_m + lengths.femur_m * math.cos(hip) + lengths.tibia_m * math.cos(hip + knee)
    z = -lengths.femur_m * math.sin(hip) - lengths.tibia_m * math.sin(hip + knee)
    return np.array([radial * math.cos(yaw), radial * math.sin(yaw), z])


def inverse(xyz, elbow="positive", check_limits=True, *, geometry=None, limits=None):
    """Solve the outward knee branch; reject unreachable or invalid targets.

    There is no silent workspace projection or servo-limit clipping. The R7
    positive knee limits select the normal outward branch. A negative branch
    can be examined with check_limits=False for geometry analysis.
    """
    x, y, z = _vector(xyz, "foot target")
    lengths = _geometry(geometry)
    selected = validate_limits(limits)
    coxa, femur, tibia = lengths.coxa_m, lengths.femur_m, lengths.tibia_m
    if elbow not in ("positive", "negative"):
        raise ValueError("elbow must be 'positive' or 'negative'")
    radial = math.hypot(x, y)
    if radial < 1e-9:
        raise ValueError("yaw is undefined for a target on the vertical yaw axis")
    yaw = math.atan2(y, x)
    planar_x = radial - coxa
    planar_down = -z
    c = (planar_x**2 + planar_down**2 - femur**2 - tibia**2) / (2 * femur * tibia)
    if c < -1.0 - 1e-10 or c > 1.0 + 1e-10:
        raise ValueError("foot target is outside the leg's geometric reach")
    # Clamp only floating-point roundoff at the analytic reach boundary.
    knee = math.acos(max(-1.0, min(1.0, c)))
    if elbow == "negative":
        knee = -knee
    hip = math.atan2(planar_down, planar_x) - math.atan2(tibia * math.sin(knee), femur + tibia * math.cos(knee))
    result = np.array([yaw, hip, knee])
    return validate_angles(result, limits=selected) if check_limits else result


def jacobian(q, *, geometry=None, limits=None, check_limits=False):
    """Derivative of toe xyz with respect to yaw, hip and knee."""
    lengths = _geometry(geometry)
    selected = validate_limits(limits)
    yaw, hip, knee = validate_angles(q, limits=selected) if check_limits else _vector(q, "joint angles")
    coxa, femur, tibia = lengths.coxa_m, lengths.femur_m, lengths.tibia_m
    cy, sy = math.cos(yaw), math.sin(yaw)
    radial = coxa + femur * math.cos(hip) + tibia * math.cos(hip + knee)
    dh = -femur * math.sin(hip) - tibia * math.sin(hip + knee)
    dk = -tibia * math.sin(hip + knee)
    return np.array([
        [-radial * sy, dh * cy, dk * cy],
        [ radial * cy, dh * sy, dk * sy],
        [0.0, -femur * math.cos(hip) - tibia * math.cos(hip + knee), -tibia * math.cos(hip + knee)],
    ])


def rotation_z(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def foot_in_body(q, mount, *, geometry=None, limits=None, check_limits=False):
    """Use a mount mapping with xyz in metres and yaw in radians."""
    return _vector(mount["xyz"], "mount xyz") + rotation_z(mount["yaw"]) @ forward(q, check_limits, geometry=geometry, limits=limits)


def inverse_body(xyz, mount, *, geometry=None, limits=None):
    target = rotation_z(-mount["yaw"]) @ (_vector(xyz, "body foot target") - _vector(mount["xyz"], "mount xyz"))
    return inverse(target, geometry=geometry, limits=limits)


# Explicit aliases make the convention visible at call sites.
fk = forward
ik = inverse
