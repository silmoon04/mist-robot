"""Check nine clamp fastener and tool paths against one complete local leg."""

from __future__ import annotations

import math

from OCP.BRepExtrema import BRepExtrema_DistShapeShape

import geom
import leg
import servo_contract as sc
from check_leg import transformed


POSE = {"hip": 25.0, "knee": 81.0, "yaw": 0.0}
INTERSECTION_THRESHOLD_MM3 = 0.01
CONTACT_TOLERANCE_MM = 1e-6
SCREW_LENGTH_MM = 35.0
SCREW_DIAMETER_MM = 3.0
HEAD_DIAMETER_MM = 5.5
HEAD_HEIGHT_MM = 3.0
DRIVER_DIAMETER_MM = 3.0
DRIVER_LENGTH_MM = 40.0
NUT_AF_MM = 5.5
NUT_THICKNESS_MM = 2.4
NUT_HOLDER_OD_MM = 5.0
NUT_HOLDER_ID_MM = 3.4
NUT_HOLDER_LENGTH_MM = 40.0


def _hex_y(x, y, z, length, across_flats):
    """Use the same flat orientation as the production captive-nut cuts."""
    radius = across_flats / math.sqrt(3.0)
    points = [
        (x + radius * math.cos(math.radians(30 + 60 * i)),
         -z + radius * math.sin(math.radians(30 + 60 * i)))
        for i in range(6)
    ]
    shape = geom.prism_xy(points, 0, length)
    return geom.translate(geom.rotate(shape, (1, 0, 0), -90), (0, y, 0))


def _raw_tools(x, z):
    cap_outer = sc.CASE_HALF_WIDTH + 4.0
    nut_seat = -16.5 + 2.8
    nut_outer = nut_seat - NUT_THICKNESS_MM
    holder_start = nut_outer - NUT_HOLDER_LENGTH_MM
    head_outer = cap_outer + HEAD_HEIGHT_MM
    holder = geom.cut(
        geom.cylinder(NUT_HOLDER_OD_MM / 2, NUT_HOLDER_LENGTH_MM,
                      (x, holder_start, z), (0, 1, 0)),
        geom.cylinder(NUT_HOLDER_ID_MM / 2, NUT_HOLDER_LENGTH_MM + 2,
                      (x, holder_start - 1, z), (0, 1, 0)),
    )
    return [
        ("seated_screw_shank",
         geom.cylinder(SCREW_DIAMETER_MM / 2, SCREW_LENGTH_MM,
                       (x, cap_outer - SCREW_LENGTH_MM, z), (0, 1, 0)),
         [cap_outer - SCREW_LENGTH_MM, cap_outer]),
        ("screw_head_insertion",
         geom.cylinder(HEAD_DIAMETER_MM / 2, SCREW_LENGTH_MM + HEAD_HEIGHT_MM,
                       (x, cap_outer, z), (0, 1, 0)),
         [cap_outer, cap_outer + SCREW_LENGTH_MM + HEAD_HEIGHT_MM]),
        ("driver_at_seated_head",
         geom.cylinder(DRIVER_DIAMETER_MM / 2, DRIVER_LENGTH_MM,
                       (x, head_outer, z), (0, 1, 0)),
         [head_outer, head_outer + DRIVER_LENGTH_MM]),
        ("nut_insertion",
         _hex_y(x, -25.0, z, nut_seat + 25.0, NUT_AF_MM),
         [-25.0, nut_seat]),
        ("nut_holding_tube",
         holder,
         [holder_start, nut_outer]),
    ]


def _tool_parts():
    parts = []
    for clamp, link, tail_out, origin_x in (
        ("yaw", "base_mount", None, 0.0),
        ("hip", "coxa", True, 50.0),
        ("knee", "femur", False, 90.0),
    ):
        for index, (x, z) in enumerate(sc.CLAMP_BOLT_XZ, 1):
            for kind, shape, y_range in _raw_tools(x, z):
                if tail_out is not None:
                    shape = leg._pitch(shape, tail_out, origin_x)
                parts.append({
                    "name": f"{clamp}_clamp_{index}_{kind}",
                    "clamp": clamp,
                    "bolt_index": index,
                    "raw_bolt_xz_mm": [float(x), float(z)],
                    "raw_tool_y_range_mm": y_range,
                    "kind": kind,
                    "shape": shape,
                    "link": link,
                })
    return parts


def _measure_pair(tool, obstacle):
    row = {
        "tool": tool["name"],
        "clamp": tool["clamp"],
        "bolt_index": tool["bolt_index"],
        "kind": tool["kind"],
        "part": obstacle["name"],
        "part_link": obstacle["link"],
    }
    amin, amax = tool["bbox"]
    bmin, bmax = obstacle["bbox"]
    gaps = [max(0.0, bmin[k] - amax[k], amin[k] - bmax[k]) for k in range(3)]
    lower_bound = math.sqrt(sum(value * value for value in gaps))
    if lower_bound > CONTACT_TOLERANCE_MM:
        return {
            **row,
            "intersection_mm3": 0.0,
            "distance_mm": lower_bound,
            "distance_kind": "axis_aligned_bounds_lower_bound",
            "boolean_tested": False,
            "blocked": False,
        }
    try:
        intersection = geom.common_volume(tool["shape"], obstacle["shape"])
        distance = BRepExtrema_DistShapeShape(tool["shape"], obstacle["shape"])
        distance.Perform()
        if not distance.IsDone():
            raise RuntimeError("OpenCascade distance did not finish")
        minimum = float(distance.Value())
        pa, pb = distance.PointOnShape1(1), distance.PointOnShape2(1)
        return {
            **row,
            "intersection_mm3": float(intersection),
            "distance_mm": minimum,
            "distance_kind": "OpenCascade_exact_shapes",
            "closest_tool_point_mm": [pa.X(), pa.Y(), pa.Z()],
            "closest_part_point_mm": [pb.X(), pb.Y(), pb.Z()],
            "boolean_tested": True,
            "blocked": intersection > INTERSECTION_THRESHOLD_MM3,
            "contact_or_overlap": minimum <= CONTACT_TOLERANCE_MM,
            "positive_volume_below_threshold": 0 < intersection <= INTERSECTION_THRESHOLD_MM3,
        }
    except Exception as exc:
        return {**row, "boolean_tested": True, "blocked": True,
                "error": f"{type(exc).__name__}: {exc}"}


def run_clamp_access(parts):
    """Return serializable findings; leave source geometry and output files alone."""
    source_parts = list(parts)
    physical = [p for p in source_parts if not p.get("allowance_only", False)]
    required = {
        "yaw_case_saddle", "case_cap_yaw", "servo_yaw",
        "coxa_upper_and_hip_saddle", "case_cap_hip", "servo_hip",
        "femur_main_and_knee_saddle", "case_cap_knee", "servo_knee",
        "femur_auxiliary_cheek", "tibia_curved_main_and_foot", "tibia_auxiliary_cheek",
    }
    missing = required - {p["name"] for p in physical}
    if missing:
        raise ValueError("Incomplete local leg assembly: " + ", ".join(sorted(missing)))
    unexpected_links = {p["link"] for p in physical} - {"base_mount", "coxa", "femur", "tibia"}
    if unexpected_links:
        raise ValueError("Expected untransformed local leg parts; unexpected links: "
                         + ", ".join(sorted(unexpected_links)))
    obstacles = transformed(physical, **POSE)
    tools = transformed(_tool_parts(), **POSE)
    pairs = [_measure_pair(tool, obstacle) for tool in tools for obstacle in obstacles]
    failures = [row for row in pairs if row["blocked"]]
    contacts = [row for row in pairs if row.get("contact_or_overlap") and not row["blocked"]]
    subthreshold = [row for row in pairs if row.get("positive_volume_below_threshold")]
    tool_results = []
    for tool in tools:
        rows = [row for row in pairs if row["tool"] == tool["name"]]
        tool_results.append({
            key: tool[key] for key in (
                "name", "clamp", "bolt_index", "raw_bolt_xz_mm",
                "raw_tool_y_range_mm", "kind", "link"
            )
        } | {
            "blocked": any(row["blocked"] for row in rows),
            "blocking_parts": [row["part"] for row in rows if row["blocked"]],
            "contact_parts": [row["part"] for row in rows if row.get("contact_or_overlap")],
        })
    counts = {
        "clamps": 3,
        "clamp_bolts": 9,
        "physical_parts": len(obstacles),
        "tool_envelopes": len(tools),
        "tool_part_pairs": len(pairs),
        "boolean_pairs_tested": sum(row["boolean_tested"] for row in pairs),
        "blocked_pairs": len(failures),
        "blocked_tools": sum(row["blocked"] for row in tool_results),
        "contact_pairs_without_blocking_volume": len(contacts),
        "positive_volume_pairs_below_threshold": len(subthreshold),
        "errors": sum("error" in row for row in pairs),
    }
    for kind in ("seated_screw_shank", "screw_head_insertion", "driver_at_seated_head",
                 "nut_insertion", "nut_holding_tube"):
        counts[kind + "_blocked_tools"] = sum(
            row["kind"] == kind and row["blocked"] for row in tool_results)
    return {
        "scope": "Nine clamp screw and tool paths in one complete local leg at one assembly pose.",
        "pose_deg": dict(POSE),
        "passed": not failures,
        "fully_verified_access": False,
        "status": ("Blocked proxy paths require review" if failures
                   else "No blocking volume above threshold for the specified proxies"),
        "intersection_threshold_mm3": INTERSECTION_THRESHOLD_MM3,
        "contact_tolerance_mm": CONTACT_TOLERANCE_MM,
        "assumed_hardware_and_tools_mm": {
            "screw_diameter": SCREW_DIAMETER_MM,
            "screw_length_under_head": SCREW_LENGTH_MM,
            "head_diameter": HEAD_DIAMETER_MM,
            "head_height": HEAD_HEIGHT_MM,
            "driver_diameter": DRIVER_DIAMETER_MM,
            "driver_exposed_length": DRIVER_LENGTH_MM,
            "nut_across_flats": NUT_AF_MM,
            "nut_thickness": NUT_THICKNESS_MM,
            "nut_capture_across_flats": 5.7,
            "nut_holder_outer_diameter": NUT_HOLDER_OD_MM,
            "nut_holder_inner_diameter": NUT_HOLDER_ID_MM,
            "nut_holder_length": NUT_HOLDER_LENGTH_MM,
        },
        "counts": counts,
        "source_part_names": [p["name"] for p in obstacles],
        "excluded_allowance_part_names": [p["name"] for p in source_parts if p.get("allowance_only")],
        "excluded_hardware_part_names": [],
        "hardware_solids_present": [p["name"] for p in obstacles
                                    if any(word in p["name"].lower()
                                           for word in ("screw", "bolt", "nut", "washer", "retainer"))],
        "tools": tool_results,
        "pair_results": pairs,
        "failures": failures,
        "contacts_without_blocking_volume": contacts,
        "positive_volumes_below_threshold": subthreshold,
        "limitations": [
            "Results apply to this pose and these explicit proxy dimensions only.",
            "All supplied physical solids are tested, including servo cases, horns and discs; none is exempted for sharing a link.",
            "Current leg geometry does not include clamp fasteners or central retainers. Their real dimensions and seating need confirmation.",
            "The screw assumes a bare seated M3 x 35 cap head. Washers, a different head, nut or screw length change the envelopes.",
            "The nut insertion starts at raw Y=-25 mm, matching the opened access passage; initial nut positioning outside that entry is not swept.",
            "The matched hex envelope allows normal captive-nut flats. It does not prove printed fit or resistance to nut rotation under tightening.",
            "The hollow nut holder clears a projecting screw but is an assumed aid; it does not establish how a real tool holds the nut.",
            "The driver checks a straight exposed shaft at the seated head. Driver handles, hand clearance and the whole driver insertion motion are absent.",
            "The local leg test omits the body, neighboring legs, ground, flexible wiring and unmodeled connectors.",
            "Touching surfaces and positive intersections below the reporting threshold are retained in the report and require interpretation.",
            "No blocking volume above threshold is not a physical access verification or a tolerance allowance.",
        ],
    }


if __name__ == "__main__":
    result = run_clamp_access(leg.build_leg())
    print(result["status"], result["counts"], flush=True)
    for failure in result["failures"]:
        print(failure, flush=True)
    raise SystemExit(0 if result["passed"] else 1)
