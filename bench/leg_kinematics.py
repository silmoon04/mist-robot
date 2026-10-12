"""Kinematics for the physical MIST single-leg linkage test.

The coordinate and joint conventions match ``sim/js/kin.js``:

* +X points away from the body through the hip mount.
* +Y is lateral and +Z is up, so a standing foot has negative Z.
* q1 is hip roll about +X.
* q2 is hip pitch, with zero pointing the femur straight down.
* q3 is knee angle relative to the femur.

The test mechanism uses a 1:1 parallelogram for the remote knee. Its servo
driver angle is the tibia's absolute pitch, ``q2 + q3``. Treating that servo as
if it directly commanded q3 is the main source of bad coordinated motion.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence


TAU = 2.0 * math.pi
TICKS_PER_REVOLUTION = 4096
TICKS_PER_RADIAN = TICKS_PER_REVOLUTION / TAU


@dataclass(frozen=True)
class LegGeometry:
    """Dimensions in millimetres for one no-wheel test leg."""

    hip_offset_mm: float = 32.0
    femur_mm: float = 110.0
    tibia_mm: float = 70.0

    def validate(self) -> None:
        if self.hip_offset_mm < 0:
            raise ValueError("hip_offset_mm must be non-negative")
        if self.femur_mm <= 0 or self.tibia_mm <= 0:
            raise ValueError("femur_mm and tibia_mm must be positive")


@dataclass(frozen=True)
class IKResult:
    reachable: bool
    target_mm: tuple[float, float, float]
    joints_rad: tuple[float, float, float] | None
    fk_error_mm: float | None
    planar_distance_mm: float
    min_reach_mm: float
    max_reach_mm: float
    reason: str | None = None


@dataclass(frozen=True)
class TickTarget:
    role: str
    requested_tick: int
    within_limits: bool
    min_tick: int | None
    max_tick: int | None


def _xyz(values: Sequence[float]) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError("expected exactly three values")
    out = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in out):
        raise ValueError("all coordinates and angles must be finite")
    return out  # type: ignore[return-value]


def _rotate_x(point: Sequence[float], angle_rad: float) -> tuple[float, float, float]:
    x, y, z = _xyz(point)
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return x, y * c - z * s, y * s + z * c


def fk_tip_mm(
    geometry: LegGeometry,
    joints_rad: Sequence[float],
) -> tuple[float, float, float]:
    """Return the tibia-tip position relative to the hip-roll axis."""

    geometry.validate()
    q1, q2, q3 = _xyz(joints_rad)
    absolute_tibia = q2 + q3
    planar = (
        geometry.hip_offset_mm
        + geometry.femur_mm * math.sin(q2)
        + geometry.tibia_mm * math.sin(absolute_tibia),
        0.0,
        -geometry.femur_mm * math.cos(q2)
        - geometry.tibia_mm * math.cos(absolute_tibia),
    )
    return _rotate_x(planar, q1)


def ik_tip_mm(
    geometry: LegGeometry,
    target_mm: Sequence[float],
    knee_sign: int = -1,
    tolerance_mm: float = 1e-8,
) -> IKResult:
    """Solve the no-wheel leg IK for one of the two knee branches.

    ``knee_sign=-1`` selects the usual spider-leg branch. An unreachable target
    returns a structured result instead of silently clipping it onto the
    workspace boundary.
    """

    geometry.validate()
    if knee_sign not in (-1, 1):
        raise ValueError("knee_sign must be -1 or +1")

    x, y, z = _xyz(target_mm)
    q1 = math.atan2(y, -z)
    radial_down = math.hypot(y, z)
    px = x - geometry.hip_offset_mm
    planar_distance = math.hypot(px, radial_down)
    min_reach = abs(geometry.femur_mm - geometry.tibia_mm)
    max_reach = geometry.femur_mm + geometry.tibia_mm

    if planar_distance > max_reach + tolerance_mm:
        return IKResult(
            False, (x, y, z), None, None, planar_distance, min_reach, max_reach,
            f"target is {planar_distance - max_reach:.3f} mm beyond full extension",
        )
    if planar_distance < min_reach - tolerance_mm:
        return IKResult(
            False, (x, y, z), None, None, planar_distance, min_reach, max_reach,
            f"target is {min_reach - planar_distance:.3f} mm inside the folded workspace",
        )

    denominator = 2.0 * geometry.femur_mm * geometry.tibia_mm
    cosine_knee = (
        px * px + radial_down * radial_down
        - geometry.femur_mm * geometry.femur_mm
        - geometry.tibia_mm * geometry.tibia_mm
    ) / denominator
    cosine_knee = max(-1.0, min(1.0, cosine_knee))
    q3 = knee_sign * math.acos(cosine_knee)
    target_angle = math.atan2(px, radial_down)
    triangle_angle = math.atan2(
        geometry.tibia_mm * math.sin(q3),
        geometry.femur_mm + geometry.tibia_mm * math.cos(q3),
    )
    q2 = target_angle - triangle_angle
    joints = (q1, q2, q3)
    solved = fk_tip_mm(geometry, joints)
    error = math.sqrt(sum((actual - wanted) ** 2 for actual, wanted in zip(solved, (x, y, z))))
    return IKResult(
        True, (x, y, z), joints, error, planar_distance, min_reach, max_reach,
    )


def servo_angles_from_joints(
    joints_rad: Sequence[float],
) -> dict[str, float]:
    """Map logical joints to the three physical servo angles."""

    q1, q2, q3 = _xyz(joints_rad)
    return {
        "roll": q1,
        "hip": q2,
        "knee_driver": q2 + q3,
    }


def joints_from_servo_angles(
    servo_angles_rad: Mapping[str, float],
) -> tuple[float, float, float]:
    """Recover q1, q2 and q3 from the remote-knee servo angles."""

    missing = {"roll", "hip", "knee_driver"} - set(servo_angles_rad)
    if missing:
        raise ValueError(f"missing servo angle roles: {', '.join(sorted(missing))}")
    roll = float(servo_angles_rad["roll"])
    hip = float(servo_angles_rad["hip"])
    knee_driver = float(servo_angles_rad["knee_driver"])
    values = (roll, hip, knee_driver - hip)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("servo angles must be finite")
    return values


def radians_from_tick(tick: int, calibration: Mapping[str, object]) -> float:
    """Convert a tick using the captured printed-reference pose."""

    center = calibration.get("center_tick")
    sign = calibration.get("sign")
    if center is None:
        raise ValueError("reference tick must be captured first")
    if sign not in (-1, 1):
        raise ValueError("direction sign must be calibrated first")
    reference = math.radians(float(calibration.get("reference_angle_deg", 0.0)))
    return reference + (int(tick) - int(center)) * int(sign) / TICKS_PER_RADIAN


def tick_target(
    role: str,
    angle_rad: float,
    calibration: Mapping[str, object],
) -> TickTarget:
    """Convert an angle without clamping or hiding a limit violation."""

    if not math.isfinite(angle_rad):
        raise ValueError("angle_rad must be finite")
    center = calibration.get("center_tick")
    sign = calibration.get("sign")
    if center is None or sign not in (-1, 1):
        raise ValueError(f"{role}: center_tick and sign must be calibrated first")
    reference = math.radians(float(calibration.get("reference_angle_deg", 0.0)))
    requested = round(int(center) + int(sign) * (angle_rad - reference) * TICKS_PER_RADIAN)
    minimum = calibration.get("min_tick")
    maximum = calibration.get("max_tick")
    min_tick = int(minimum) if minimum is not None else None
    max_tick = int(maximum) if maximum is not None else None
    if min_tick is not None and max_tick is not None and min_tick > max_tick:
        raise ValueError(f"{role}: min_tick is greater than max_tick")
    within = 0 <= requested < TICKS_PER_REVOLUTION
    if min_tick is not None:
        within = within and requested >= min_tick
    if max_tick is not None:
        within = within and requested <= max_tick
    return TickTarget(role, requested, within, min_tick, max_tick)


def degrees(values_rad: Sequence[float]) -> tuple[float, float, float]:
    return tuple(math.degrees(value) for value in _xyz(values_rad))
