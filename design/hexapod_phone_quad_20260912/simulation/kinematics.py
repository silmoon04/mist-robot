"""Independent direct-drive quadruped kinematics, SI throughout."""
from __future__ import annotations

import math
import json
from pathlib import Path
import numpy as np

SETTINGS_PATH = Path(__file__).resolve().parent.parent / "settings.json"
SETTINGS = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
LEGS = SETTINGS["leg_azimuth_deg"]
YAW_RADIUS = SETTINGS["yaw_radius_mm"] / 1000
YAW_Z = SETTINGS["yaw_height_mm"] / 1000
COXA, FEMUR, TIBIA = [SETTINGS[k] / 1000 for k in ("coxa_mm", "femur_mm", "tibia_mm")]
FOOT_RADIUS = 0.005
PHONE_Z = SETTINGS["phone_pan_origin_mm"][2] / 1000
YAW_LIMIT_DEG=float(SETTINGS.get("yaw_operating_limit_deg",25.0))
LIMITS = np.radians([[-YAW_LIMIT_DEG, YAW_LIMIT_DEG], [3.0, 35.0], [30.0, 100.0]])
NEUTRAL = np.radians([SETTINGS["neutral_deg"][k] for k in ("yaw", "hip", "knee")])


def rz(angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def root_origin(leg):
    az = math.radians(LEGS[leg])
    return np.array([YAW_RADIUS * math.cos(az), YAW_RADIUS * math.sin(az), YAW_Z])


def forward_local(angles):
    yaw, hip, knee = angles
    radial = COXA + FEMUR * math.cos(hip) + TIBIA * math.cos(hip + knee)
    z = -FEMUR * math.sin(hip) - TIBIA * math.sin(hip + knee)
    return np.array([radial * math.cos(yaw), radial * math.sin(yaw), z])


def forward_body(leg, angles):
    return root_origin(leg) + rz(math.radians(LEGS[leg])) @ forward_local(angles)


def inverse_local(point, enforce_limits=True):
    x, y, z = map(float, point)
    yaw = math.atan2(y, x)
    reach, drop = math.hypot(x, y) - COXA, -z
    ck = (reach * reach + drop * drop - FEMUR**2 - TIBIA**2) / (2 * FEMUR * TIBIA)
    if ck < -1 - 1e-9 or ck > 1 + 1e-9:
        raise ValueError(f"Unreachable toe: {point}; cosine knee {ck:.6f}")
    knee = math.acos(max(-1, min(1, ck)))
    hip = math.atan2(drop, reach) - math.atan2(TIBIA * math.sin(knee), FEMUR + TIBIA * math.cos(knee))
    angles = np.array([yaw, hip, knee])
    if enforce_limits and (np.any(angles < LIMITS[:, 0] - 1e-8) or np.any(angles > LIMITS[:, 1] + 1e-8)):
        raise ValueError(f"Joint limit exceeded: {np.degrees(angles).tolist()}")
    return angles


def inverse_world(leg, toe, base_position, base_rotation=None):
    rotation = np.eye(3) if base_rotation is None else np.asarray(base_rotation)
    point_body = rotation.T @ (np.asarray(toe) - np.asarray(base_position))
    point_local = rz(-math.radians(LEGS[leg])) @ (point_body - root_origin(leg))
    return inverse_local(point_local)


def nominal_stance(neutral=NEUTRAL):
    base = np.array([0.0, 0.0, FOOT_RADIUS - forward_body("FL", neutral)[2]])
    feet = {leg: base + forward_body(leg, neutral) for leg in LEGS}
    return base, feet


def convex_hull(points):
    pts = sorted(set(tuple(map(float, p[:2])) for p in points))
    if len(pts) < 3:
        return np.array(pts)
    def cross(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.array(lower[:-1] + upper[:-1])


def support_margin(com_xy, contact_xy):
    hull = convex_hull(contact_xy)
    if len(hull) < 3:
        return None
    margins = []
    for a, b in zip(hull, np.roll(hull, -1, axis=0)):
        edge = b-a
        offset = np.asarray(com_xy)-a
        margins.append(float((edge[0]*offset[1]-edge[1]*offset[0]) / np.linalg.norm(edge)))
    return min(margins)


def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def crawl_plan(stride=0.030, shift=0.020, lower=0.010, lift=0.020, neutral=NEUTRAL):
    """World stance toes stay fixed until that leg swings. Each item is one phase."""
    base, feet = nominal_stance(neutral)
    lowered = base.copy()
    lowered[2] -= lower
    phases = [{"kind": "lower", "seconds": 2.0, "base_start": base.copy(), "base_end": lowered.copy(), "feet": {k:v.copy() for k,v in feet.items()}}]
    current = lowered.copy()
    for leg in ["FL", "RR", "FR", "RL"]:
        az = math.radians(LEGS[leg])
        target = current.copy()
        target[:2] = np.mean([v[:2] for v in feet.values()], axis=0) - shift * np.array([math.cos(az), math.sin(az)])
        phases.append({"kind":"shift", "seconds":3.0, "base_start":current.copy(), "base_end":target.copy(), "feet":{k:v.copy() for k,v in feet.items()}})
        current = target
        phases.append({"kind":"swing", "leg":leg, "seconds":4.0, "base_start":current.copy(), "base_end":current.copy(), "feet":{k:v.copy() for k,v in feet.items()}, "stride":stride, "lift":lift})
        feet[leg] = feet[leg] + np.array([stride, 0.0, 0.0])
    target = current.copy()
    target[:2] = np.mean([v[:2] for v in feet.values()], axis=0)
    phases.append({"kind":"center", "seconds":3.0, "base_start":current.copy(), "base_end":target.copy(), "feet":{k:v.copy() for k,v in feet.items()}})
    return phases


def sample_phase(phase, t):
    s = smoothstep(t)
    base = phase["base_start"] * (1-s) + phase["base_end"] * s
    feet = {k:v.copy() for k,v in phase["feet"].items()}
    if phase["kind"] == "swing":
        feet[phase["leg"]] += np.array([phase["stride"]*s, 0, phase["lift"]*math.sin(math.pi*t)**2])
    return base, feet
