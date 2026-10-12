"""Check staged nut entry and clamp access with the actual head-washer datum."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import geom
import leg
import servo_contract as sc
import check_r4_clamp_access as access
from check_leg import transformed


CAD = Path(__file__).resolve().parent
WASHER_THICKNESS = 0.5
CLAMPS = (
    ("yaw", "base_mount", None, 0.0, "yaw_case_saddle", "servo_yaw", "case_cap_yaw"),
    ("hip", "coxa", True, 50.0, "coxa_upper_and_hip_saddle", "servo_hip", "case_cap_hip"),
    ("knee", "femur", False, 90.0, "femur_main_and_knee_saddle", "servo_knee", "case_cap_knee"),
)


def _hashes():
    paths = [CAD / name for name in ("leg.py", "servo_contract.py", "geom.py", "check_leg.py",
                                     "check_r4_clamp_access.py", "check_r4_staged_nuts.py")]
    paths.append(CAD / "hardware" / "ST3215.step")
    return {str(path.relative_to(CAD)).replace("\\", "/"):
            hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _mapped(shape, spec):
    return shape if spec[2] is None else leg._pitch(shape, spec[2], spec[3])


def _tool(shape, spec, index, kind, **extra):
    return {
        "name": f"{spec[0]}_clamp_{index}_{kind}", "clamp": spec[0],
        "bolt_index": index, "kind": kind, "link": spec[1],
        "raw_bolt_xz_mm": list(sc.CLAMP_BOLT_XZ[index - 1]),
        "shape": _mapped(shape, spec), **extra,
    }


def _washer(x, z):
    y = sc.CASE_HALF_WIDTH + 4.0
    return geom.cut(
        geom.cylinder(3.5, WASHER_THICKNESS, (x, y, z), (0, 1, 0)),
        geom.cylinder(1.6, WASHER_THICKNESS + 2, (x, y - 1, z), (0, 1, 0)),
    )


def _nut(x, z):
    return geom.cut(access._hex_y(x, -16.1, z, 2.4, 5.5),
                    geom.cylinder(1.5, 4.4, (x, -17.1, z), (0, 1, 0)))


def _hull(points):
    values = sorted(set(points))
    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    lower = []
    for point in values:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(values):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def _lateral_nut_sweep(x, start_z, end_z):
    radius = 5.5 / math.sqrt(3.0)
    points = [(x + radius * math.cos(math.radians(30 + 60 * i)),
               z - radius * math.sin(math.radians(30 + 60 * i)))
              for z in (start_z, end_z) for i in range(6)]
    return geom.prism_xz(_hull(points), -20.0, 2.4)


def _summarize(pairs, tools, before):
    after = _hashes()
    changes = [name for name in before if before[name] != after[name]]
    failures = [row for row in pairs if row["blocked"]]
    tool_results = []
    for tool in tools:
        rows = [row for row in pairs if row["tool"] == tool["name"]]
        tool_results.append({key: value for key, value in tool.items() if key not in ("shape", "bbox")} | {
            "blocked": any(row["blocked"] for row in rows),
            "blocking_parts": [row["part"] for row in rows if row["blocked"]],
        })
    return {
        "passed": not failures and not changes,
        "fully_verified_access": False,
        "intersection_threshold_mm3": access.INTERSECTION_THRESHOLD_MM3,
        "source_hashes_before": before, "source_hashes_after": after,
        "source_files_changed_during_check": changes,
        "counts": {
            "clamps": 3, "clamp_bolts": 9, "tools": len(tools),
            "tool_part_pairs": len(pairs),
            "boolean_pairs_tested": sum(row["boolean_tested"] for row in pairs),
            "blocked_pairs": len(failures),
            "blocked_tools": sum(row["blocked"] for row in tool_results),
            "errors": sum("error" in row for row in pairs),
            "contacts_without_blocking_volume": sum(row.get("contact_or_overlap", False)
                                                     and not row["blocked"] for row in pairs),
        },
        "tools": tool_results, "pair_results": pairs, "failures": failures,
        "positive_volumes_below_threshold": [row for row in pairs
                                              if row.get("positive_volume_below_threshold")],
    }


def run_staged_nuts(parts):
    """Check continuous entry into bare carriers, then the seated hardware stack."""
    before = _hashes()
    physical = {p["name"]: p for p in parts if not p.get("allowance_only")}
    tools, pairs, stages = [], [], []
    for spec in CLAMPS:
        carrier, own_servo, own_cap = (physical[name] for name in spec[4:7])
        bare = transformed([carrier], **access.POSE)[0]
        seated_obstacles = transformed([carrier, own_servo, own_cap], **access.POSE)
        for index, (x, z) in enumerate(sc.CLAMP_BOLT_XZ, 1):
            if spec[0] == "hip" and index in (2, 3):
                start_z = -40.0 if index == 2 else 5.0
                sweeps = [
                    ("preload_lateral_entry", _lateral_nut_sweep(x, start_z, z),
                     {"raw_start_nut_y_range_mm": [-20.0, -17.6],
                      "raw_center_z_path_mm": [start_z, z]}),
                    ("preload_axial_seating", access._hex_y(x, -20.0, z, 6.3, 5.5),
                     {"raw_nut_rear_face_y_path_mm": [-20.0, -16.1]}),
                ]
            else:
                sweeps = [("preload_axial_entry", access._hex_y(x, -60.0, z, 46.3, 5.5),
                           {"raw_nut_rear_face_y_path_mm": [-60.0, -16.1]})]
            for kind, shape, coordinates in sweeps:
                tool = transformed([_tool(shape, spec, index, kind,
                                          stage="bare_carrier_nut_entry", **coordinates)],
                                   **access.POSE)[0]
                tools.append(tool)
                row = access._measure_pair(tool, bare)
                pairs.append({**row, "stage": "bare_carrier_nut_entry"})
            under_head = sc.CASE_HALF_WIDTH + 4.0 + WASHER_THICKNESS
            seated = [
                ("seated_nut", _nut(x, z)),
                ("seated_screw_shank", geom.cylinder(1.5, 35.0,
                                                     (x, under_head - 35, z), (0, 1, 0))),
                ("seated_screw_head", geom.cylinder(2.75, 3.0,
                                                    (x, under_head, z), (0, 1, 0))),
                ("seated_head_washer", _washer(x, z)),
            ]
            for kind, shape in seated:
                tool = transformed([_tool(shape, spec, index, kind,
                                          stage="seated_stack_with_own_servo_and_cap")],
                                   **access.POSE)[0]
                tools.append(tool)
                for obstacle in seated_obstacles:
                    row = access._measure_pair(tool, obstacle)
                    pairs.append({**row, "stage": "seated_stack_with_own_servo_and_cap"})
            stages.append({"clamp": spec[0], "bolt_index": index,
                           "bare_carrier": carrier["name"],
                           "seated_obstacle_names": [p["name"] for p in seated_obstacles]})
    result = _summarize(pairs, tools, before)
    result.update({
        "scope": "Continuous entry of all nine nuts into bare printed carriers, followed by seated hardware checks with each carrier's own servo and cap.",
        "pose_deg": dict(access.POSE), "stages": stages,
        "assumed_nut_mm": {"across_flats": 5.5, "thickness": 2.4,
                            "seated_raw_y_range": [-16.1, -13.7]},
        "procedure": [
            "Preload the bare yaw saddle, hip coxa carrier and knee femur carrier before installing their servos or caps. Keep the hip lower arm, surrounding femur and tibia assemblies absent. The hip carrier's integrated post remains present.",
            "For all yaw nuts, the hip rear nut and all knee nuts, align the nut flats to the printed trap and feed from the open negative raw-Y side. The checked continuous entry begins with the nut rear face at raw Y=-60 mm and ends at Y=-16.1 mm.",
            "For the hip front lower nut at raw X=13.915, Z=-23 mm, hold its thickness at raw Y=-20 to -17.6 mm and slide its center from raw Z=-40 to -23 mm through the side opening.",
            "For the hip front upper nut at raw X=13.915, Z=-7 mm, hold the same raw-Y thickness interval and slide its center from raw Z=5 to -7 mm through the opposite side opening.",
            "After either hip front nut reaches its bolt axis, translate it 3.9 mm along positive raw Y. Its seated interval is Y=-16.1 to -13.7 mm. This lateral-then-axial route avoids assuming the nut starts inside the reopened channel.",
            "Keep each nut seated while installing its servo and cap. Place a 0.5 mm OD7/ID3.2 head washer under each M3 x 35 screw, then engage the nut from the cap side before fitting surrounding leg assemblies.",
            "For later hip nut removal or replacement, remove surrounding parts to recover the bare-carrier access used here. The original assembled-leg nut-tool obstructions remain reported separately.",
        ],
        "limitations": [
            "Entry sweeps use a filled nut exterior, conservatively including its thread hole. Seated nuts use a simple 3 mm bore; thread geometry and tightening are not simulated.",
            "The nominal matching-flat clearance is 0.1 mm per side and needs a printed fit check.",
            "The checks establish a route for the nut itself, not clearance for fingers, a wrench or a particular nut-holding tool.",
            "Keeping a loose nut seated during servo and cap installation remains a physical assembly task.",
            "Servo and cap insertion motions are not swept; their final seated relationship to the nuts, screws and washers is checked.",
            "These staged checks deliberately exclude the body, lower arm and surrounding moving links before they are fitted. They do not replace the full assembled-leg service-access report.",
            "Physical fit, plastic deformation, washer tolerances and thread engagement remain unverified.",
            "Input parts must come from the production build matching the recorded sources. Before/after hashes detect file changes during this check, not the caller's earlier shape construction.",
        ],
    })
    return result


def run_actual_washer_access(parts):
    """Repeat full-leg tool checks using the 0.5 mm head washer stack."""
    before = _hashes()
    physical = [p for p in parts if not p.get("allowance_only")]
    obstacles = transformed(physical, **access.POSE)
    raw_tools = []
    shifted = {"seated_screw_shank", "screw_head_insertion", "driver_at_seated_head"}
    for spec in CLAMPS:
        for index, (x, z) in enumerate(sc.CLAMP_BOLT_XZ, 1):
            for kind, shape, y_range in access._raw_tools(x, z):
                if kind in shifted:
                    shape = geom.translate(shape, (0, WASHER_THICKNESS, 0))
                    y_range = [v + WASHER_THICKNESS for v in y_range]
                raw_tools.append(_tool(shape, spec, index, kind,
                                       raw_tool_y_range_mm=y_range))
            raw_tools.append(_tool(_washer(x, z), spec, index, "seated_head_washer",
                                   raw_tool_y_range_mm=[16.365, 16.865]))
    tools = transformed(raw_tools, **access.POSE)
    pairs = [access._measure_pair(tool, obstacle) for tool in tools for obstacle in obstacles]
    result = _summarize(pairs, tools, before)
    result.update({
        "scope": "All original full-leg screw and tool checks with the actual head-washer offset, plus nine seated head washers. Nut tool paths are unchanged.",
        "pose_deg": dict(access.POSE),
        "actual_head_washer_mm": {"outer_diameter": 7.0, "inner_diameter": 3.2,
                                  "thickness": 0.5, "raw_y_range": [16.365, 16.865]},
        "under_head_raw_y_mm": 16.865,
        "screw_tip_raw_y_mm": -18.135,
        "driver_start_raw_y_mm": 19.865,
        "physical_part_count": len(obstacles),
        "excluded_hardware_part_names": [],
        "limitations": [
            "All supplied physical leg parts remain in the obstruction test, including neighboring moving links.",
            "Nut insertion and holder paths are unchanged from the original report, so staged preload does not hide service-access obstructions.",
            "The washer is checked seated; the route used to place it under the screw head is not swept.",
            "The driver remains a 3 mm straight shaft with 40 mm exposed length at the seated head; handles and hand clearance are absent.",
            "The M3 x 35 screw assumes a 5.5 mm diameter, 3 mm tall head. Actual screw dimensions and thread engagement need confirmation.",
            "The complete local leg is checked at one pose; the body, neighboring legs, flexible wiring and unmodeled connectors are absent.",
            "No blocking volume above threshold does not establish physical access or a manufacturing tolerance allowance.",
        ],
    })
    for kind in ("seated_screw_shank", "screw_head_insertion", "driver_at_seated_head",
                 "nut_insertion", "nut_holding_tube", "seated_head_washer"):
        result["counts"][kind + "_blocked_tools"] = sum(
            row["kind"] == kind and row["blocked"] for row in result["tools"])
    return result


if __name__ == "__main__":
    parts = leg.build_leg()
    for title, check in (("staged_nuts", run_staged_nuts),
                         ("actual_washer_access", run_actual_washer_access)):
        report = check(parts)
        print(title, "passed", report["passed"], report["counts"], flush=True)
        for failure in report["failures"]:
            print(failure, flush=True)
