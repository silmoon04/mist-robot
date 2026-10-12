"""Independent planar packaging screen. Millimetres; no CAD or hardware actions.

The audit box is a reserved volume, not an assertion that every point is solid.
The draft servo boxes follow the dimensions supplied by the leg implementation
agent on 2026-09-07. Results must be rerun against the finished recipe.
"""
import itertools
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / "simulation/parameters.json").read_text())
G = P["geometry"]
R = G["hip_mount_radius_m"] * 1000
BARREL = G["body_diameter_m"] * 500
AZ = G["mount_azimuths_deg"]
HANDS = [1, -1, -1, 1]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def box(leg, yaw, center, size):
    phi = math.radians(AZ[leg])
    theta = phi + math.radians(yaw)
    u = (math.cos(theta), math.sin(theta))
    v = (-u[1], u[0])
    c = (R * math.cos(phi) + center[0] * u[0] + center[1] * v[0],
         R * math.sin(phi) + center[0] * u[1] + center[1] * v[1])
    return c, u, v, (size[0] / 2, size[1] / 2)


def corners(b):
    c, u, v, h = b
    return [(c[0] + a*h[0]*u[0] + d*h[1]*v[0],
             c[1] + a*h[0]*u[1] + d*h[1]*v[1])
            for a, d in itertools.product((-1, 1), repeat=2)]


def distance_to_point(b, p=(0, 0)):
    c, u, v, h = b
    relative = (p[0] - c[0], p[1] - c[1])
    return math.hypot(max(abs(dot(relative, u))-h[0], 0),
                      max(abs(dot(relative, v))-h[1], 0))


def overlap(a, b):
    ca, ua, va, ha = a
    cb, ub, vb, hb = b
    delta = (cb[0] - ca[0], cb[1] - ca[1])
    depths = []
    for axis in (ua, va, ub, vb):
        ar = ha[0]*abs(dot(ua, axis)) + ha[1]*abs(dot(va, axis))
        br = hb[0]*abs(dot(ub, axis)) + hb[1]*abs(dot(vb, axis))
        depths.append(ar + br - abs(dot(delta, axis)))
    return min(depths)


def audit_box(leg, yaw):
    return box(leg, yaw, (35, HANDS[leg]*30), (75, 90))


def servo_box(leg, yaw, which):
    # Pitch-local y spans -74..-39 or +59..+94. Full assembly mirrored.
    py = -56.5 if which == "hip" else 76.5
    return box(leg, yaw, (65, HANDS[leg]*(30+py)), (45.2, 35))


def first_pair_overlap(factory, step=2):
    candidates = [(i, j) for i in range(4) for j in range(i+1, 4)]
    best = None
    yaws = range(-100, 101, step)
    poses = {(i, q): factory(i, q) for i in range(4) for q in yaws}
    for i, j in candidates:
        for qi in yaws:
            for qj in yaws:
                depth = overlap(poses[i, qi], poses[j, qj])
                if best is None or depth > best["sat_overlap_mm"]:
                    best = dict(legs=[G["leg_names"][i], G["leg_names"][j]],
                                yaw_deg=[qi, qj], sat_overlap_mm=depth)
    return best


def main():
    yaws = range(-100, 101)
    nominal_yaw = [-45, 45, 45, -45]
    def in_rear_window(point):
        for az in (135, -135):
            a = math.radians(az)
            radial = point[0]*math.cos(a) + point[1]*math.sin(a)
            tangential = -point[0]*math.sin(a) + point[1]*math.cos(a)
            if 72 <= radial <= 126 and abs(tangential) <= 44:
                return True
        return -102 <= point[0] <= -72 and abs(point[1]) <= 22
    # The remaining lower rear shell exists between body-bottom z6 and z82.
    shell_samples = [(r*math.cos(math.radians(a)), r*math.sin(math.radians(a)))
                     for r in (87.6, 88.8, 90) for a in range(90, 271)]
    shell_samples = [x for x in shell_samples if not in_rear_window(x)]
    results = {
        "status": "conservative_planar_screen_not_final_CAD_clearance",
        "parameters_sha256": hashlib.sha256((ROOT / "simulation/parameters.json").read_bytes()).hexdigest(),
        "draft_servo_assumption": "45.2 X by35 Y mm; pitch-local centre X30,Y-56.5/+76.5; complete handed mirror; overlapping Z span",
        "adjacent_mount_spacing_mm": math.sqrt(2)*R,
        "barrel_to_yaw_axis_mm": R-BARREL,
        "audit_box_assumption": "75 radial x90 transverse x65 high, centred on pitch axis (35,+/-30,0)",
        "audit_box_height_bodybottom_mm": [2.5, 67.5],
        "audit_box_max_radius_about_yaw_mm": math.hypot(35+37.5, 30+45),
        "audit_box_min_radius_to_bodycenter": min(
            (dict(distance_mm=distance_to_point(audit_box(0, q)), yaw_deg=q)
             for q in yaws), key=lambda d: d["distance_mm"]),
        "audit_box_nominal_drive_min_body_radius_mm": distance_to_point(audit_box(0, -45)),
        "audit_box_strongest_pair_overlap_2deg_grid": first_pair_overlap(audit_box),
        "draft_servo_boxes": {},
    }
    for which in ("hip", "remote"):
        factory = lambda i, q: servo_box(i, q, which)
        best = min((dict(leg=G["leg_names"][i], yaw_deg=q,
                         distance_mm=distance_to_point(factory(i, q)))
                    for i in range(4) for q in yaws), key=lambda x: x["distance_mm"])
        shell_hit = next((dict(leg=G["leg_names"][i], yaw_deg=q, shell_point_mm=pt)
                          for i in range(4) for q in yaws for pt in shell_samples
                          if distance_to_point(factory(i,q),pt)<1e-8), None)
        results["draft_servo_boxes"][which] = {
            "min_radius_to_bodycenter": best,
            "nominal_drive_min_radius_mm": [distance_to_point(factory(i,q))
                                             for i,q in enumerate(nominal_yaw)],
            "strongest_pair_overlap_2deg_grid": first_pair_overlap(factory),
            "sampled_rear_shell_intersection_at_bodybottom_z35": shell_hit,
        }
    lo, hi = P["transmission"]["motor_travel_limits_deg"][0]
    span = hi-lo
    results["travel"] = {
        "motor_usable_span_deg": span,
        "full_yaw_joint_span_deg": 200,
        "full_yaw_motor_span_at_2_deg": 400,
        "full_hip_joint_span_deg": 165,
        "full_hip_motor_span_at_2_deg": 330,
        "full_hip_motor_span_at_3p5_deg": 577.5,
        "max_hip_span_at_3p5_deg": span/3.5,
        "absolute_tibia_full_rectangular_limits_span_deg": (125-15)-(-40-150),
        "absolute_tibia_motor_span_at_2_deg": 600,
    }
    l1, l2, reach, down = 140, 130, 60, 190
    knee = -math.acos((reach**2+down**2-l1*l1-l2*l2)/(2*l1*l2))
    hip = math.atan2(reach,down)-math.atan2(l2*math.sin(knee),l1+l2*math.cos(knee))
    hd, kd = math.degrees(hip), math.degrees(knee)
    results["travel"]["drive_neutral_hip_knee_deg"] = [hd,kd]
    results["travel"]["hip_range_if_centered_at_drive_2_deg"] = [hd-span/4,hd+span/4]
    results["travel"]["hip_range_if_centered_at_drive_3p5_deg"] = [hd-span/7,hd+span/7]
    m = P["mass"]
    total = sum(m[k] for k in ("shell_kg", "battery_kg", "brain_phone_kg",
                              "face_phone_with_frame_kg", "electronics_kg", "harness_kg"))
    total += 4*(3*m["proximal_servo_kg"] + sum(m[k] for k in (
        "yaw_carriage_without_servos_kg", "femur_with_pulleys_kg", "tibia_with_carrier_kg",
        "wheel_motor_with_mount_kg", "wheel_hub_and_tire_kg")))
    results["mass"] = {"total_estimate_kg": total,
                       "eight_pitch_and_remote_servos_kg": 8*m["proximal_servo_kg"],
                       "com_z_rise_if_these_servos_raise_50mm": 8*m["proximal_servo_kg"]*50/total,
                       "four_added_50g_pods_total_kg": total+.2}
    text = json.dumps(results, indent=2)
    (ROOT / "packaging_screen_20260907.json").write_text(text+"\n")
    print(text)


if __name__ == "__main__":
    main()
