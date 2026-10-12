"""Validate discrete R4 leg poses, connector reserves and mounting interfaces."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import traceback

from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

import geom as g
import leg
import servo_contract as sc
from check_leg import transformed


CAD = Path(__file__).resolve().parent
OUTPUT = CAD / "output" / "r4_leg_interface_check"
INTERSECTION_MM3 = 0.01
AABB_TOLERANCE_MM = 1e-8


def source_hashes():
    names = ("leg.py", "servo_contract.py", "geom.py", "check_leg.py",
             "check_r4_leg_interfaces.py", "check_r4_clamp_access.py", "hardware/ST3215.step")
    return {name: hashlib.sha256((CAD / name).read_bytes()).hexdigest() for name in names}


def bbox_overlap(a, b):
    amin, amax = a
    bmin, bmax = b
    return all(amax[k] > bmin[k] + AABB_TOLERANCE_MM and
               bmax[k] > amin[k] + AABB_TOLERANCE_MM for k in range(3))


def shape_checks(parts):
    records = []
    failures = []
    for part in parts:
        explorer = TopExp_Explorer(part["shape"], TopAbs_SOLID)
        solids = 0
        while explorer.More():
            solids += 1
            explorer.Next()
        record = dict(name=part["name"], valid=g.valid(part["shape"]),
                      solids=solids, volume_mm3=g.volume(part["shape"]),
                      bounds_mm=g.bounds(part["shape"]), printable=part["printable"])
        records.append(record)
        if not record["valid"] or record["volume_mm3"] <= 0 or solids < 1:
            failures.append(dict(record, reason="Invalid or empty physical shape"))
        elif part["printable"] and solids != 1:
            failures.append(dict(record, reason="Printable part contains multiple solids"))
    return dict(part_count=len(parts), parts=records, failures=failures, passed=not failures)


def motion_checks(parts):
    samples = []
    failures = []
    for yaw, hip, knee in itertools.product((-22, 0, 22), (16, 25, 34), (70, 81, 91)):
        moved = transformed(parts, hip=hip, knee=knee, yaw=yaw)
        considered = 0
        booleans = 0
        hits = []
        for a, b in itertools.combinations(moved, 2):
            if a["link"] == b["link"]:
                continue
            considered += 1
            if not bbox_overlap(a["bbox"], b["bbox"]):
                continue
            booleans += 1
            volume = g.common_volume(a["shape"], b["shape"])
            if volume > INTERSECTION_MM3:
                hits.append(dict(a=a["name"], b=b["name"], link_a=a["link"],
                                 link_b=b["link"], intersection_mm3=volume))
        sample = dict(yaw_deg=yaw, hip_deg=hip, knee_deg=knee,
                      cross_link_pairs_considered=considered,
                      boolean_pairs_tested=booleans, failures=hits)
        failures.extend(dict(sample_index=len(samples), **hit) for hit in hits)
        samples.append(sample)
        print("Motion", yaw, hip, knee, "Boolean", booleans, "failures", len(hits), flush=True)
    return dict(sample_count=len(samples), samples=samples, failures=failures,
                cross_link_pairs_considered=sum(s["cross_link_pairs_considered"] for s in samples),
                boolean_pairs_tested=sum(s["boolean_pairs_tested"] for s in samples),
                passed=not failures,
                scope="Twenty-seven local leg poses; same-link pairs are excluded from motion checking")


def proxy_checks(parts):
    raw = sc.plugged_profile_reserve()
    proxies = [
        dict(name="yaw_connector_reserve", owner="servo_yaw", shape=raw, link="base_mount"),
        dict(name="hip_connector_reserve", owner="servo_hip", link="coxa",
             shape=leg._pitch(raw, True, 50)),
        dict(name="knee_connector_reserve", owner="servo_knee", link="femur",
             shape=leg._pitch(raw, False, 90)),
    ]
    samples = []
    failures = []
    for hip, knee in ((16, 70), (25, 81), (34, 91)):
        moved = transformed(parts, hip=hip, knee=knee, yaw=0)
        reserves = transformed(proxies, hip=hip, knee=knee, yaw=0)
        for reserve in reserves:
            considered = 0
            booleans = 0
            hits = []
            for part in moved:
                if part["name"] == reserve["owner"]:
                    continue
                considered += 1
                if not bbox_overlap(reserve["bbox"], part["bbox"]):
                    continue
                booleans += 1
                volume = g.common_volume(reserve["shape"], part["shape"])
                if volume > INTERSECTION_MM3:
                    hits.append(dict(part=part["name"], intersection_mm3=volume))
            sample = dict(hip_deg=hip, knee_deg=knee, yaw_deg=0, reserve=reserve["name"],
                          owner_excluded=reserve["owner"], bounds_mm=reserve["bbox"],
                          pairs_considered=considered, boolean_pairs_tested=booleans,
                          failures=hits)
            failures.extend(dict(sample_index=len(samples), **hit) for hit in hits)
            samples.append(sample)
            print("Connector", hip, knee, reserve["name"], "Boolean", booleans,
                  "failures", len(hits), flush=True)
    return dict(raw_servo_reserve_bounds_mm=g.bounds(raw), samples=samples, sample_count=len(samples),
                pairs_considered=sum(s["pairs_considered"] for s in samples),
                boolean_pairs_tested=sum(s["boolean_pairs_tested"] for s in samples),
                added_profile_reserve_mm=sc.REFERENCE_REAR_PROFILE_Z-sc.PORT_CLEARANCE_OUTER_Z,
                failures=failures, passed=not failures,
                scope="Three critical poses at yaw zero; each proxy is checked against every part except its owning servo",
                limitation="The proxy is a provisional plugged-profile and wire reserve, not a measured cable sweep")


def distance_mm(a, b):
    result = BRepExtrema_DistShapeShape(a, b)
    result.Perform()
    if not result.IsDone():
        raise RuntimeError("Retention distance computation failed")
    return float(result.Value())


def retention_checks(parts):
    # The washer bears on the fixed stub at its inner face, away from the disc.
    washer = g.cut(g.cylinder(3.5, 0.5, (0, 0, sc.AUX_STUB_TIP_Z-0.5)),
                   g.cylinder(1.6, 0.7, (0, 0, sc.AUX_STUB_TIP_Z-0.6)))
    washers = [
        dict(name="yaw_center_washer", shape=washer, link="base_mount", disc="horn_yaw_auxiliary",
             cheek="coxa_lower_auxiliary_arm"),
        dict(name="hip_center_washer", shape=leg._pitch(washer, True, 50), link="coxa",
             disc="horn_hip_auxiliary", cheek="femur_auxiliary_cheek"),
        dict(name="knee_center_washer", shape=leg._pitch(washer, False, 90), link="femur",
             disc="horn_knee_auxiliary", cheek="tibia_auxiliary_cheek"),
    ]
    moved = transformed(parts, hip=25, knee=81, yaw=0)
    named = {p["name"]: p for p in moved}
    positioned = transformed(washers, hip=25, knee=81, yaw=0)
    records = []
    failures = []
    for entry in positioned:
        hits = []
        for part in moved:
            if not bbox_overlap(entry["bbox"], part["bbox"]):
                continue
            overlap = g.common_volume(entry["shape"], part["shape"])
            if overlap > INTERSECTION_MM3:
                hits.append(dict(part=part["name"], intersection_mm3=overlap))
        record = dict(name=entry["name"], fixed_link=entry["link"],
                      washer_bounds_mm=entry["bbox"],
                      disc_distance_mm=distance_mm(entry["shape"], named[entry["disc"]]["shape"]),
                      cheek_distance_mm=distance_mm(entry["shape"], named[entry["cheek"]]["shape"]),
                      failures=hits)
        records.append(record)
        failures.extend(dict(washer=entry["name"], **hit) for hit in hits)
    metrics = dict(
        washer_od_mm=7.0, washer_id_mm=3.2, washer_thickness_mm=0.5,
        washer_case_facing_plane_z_mm=sc.AUX_STUB_TIP_Z,
        disc_case_gap_mm=sc.AUX_FACE_Z-(sc.AUX_DISC_OUTER_Z+sc.AUX_DISC_TOTAL),
        disc_retainer_gap_mm=sc.AUX_DISC_OUTER_Z-sc.AUX_STUB_TIP_Z,
        pitch_cheek_access_diameter_mm=leg.CONSTANTS["auxiliary_center_access_diameter"],
        pitch_washer_to_access_radial_clearance_mm=(leg.CONSTANTS["auxiliary_center_access_diameter"]-7)/2,
        stub_diameter_mm=6.0, disc_bore_diameter_mm=6.05,
        disc_to_stub_diametral_clearance_mm=0.05,
        washer_overlap_beyond_disc_bore_radial_mm=(7-6.05)/2,
        reserve_to_horn_bore_radial_lower_bound_mm=abs(sc.PORT_X[1]+sc.PORT_IN_PLANE_ALLOWANCE)-8.7,
        reserve_to_standoff_radial_lower_bound_mm=abs(sc.PORT_X[1]+sc.PORT_IN_PLANE_ALLOWANCE)-10,
        nominal_blind_pocket_floor_mm=23-(abs(sc.PORT_CLEARANCE_OUTER_Z)-14.5),
    )
    if any(metrics[key] <= 0 for key in (
            "disc_case_gap_mm", "disc_retainer_gap_mm", "pitch_washer_to_access_radial_clearance_mm",
            "washer_overlap_beyond_disc_bore_radial_mm", "nominal_blind_pocket_floor_mm")):
        failures.append(dict(reason="A required nominal retention clearance is not positive"))
    return dict(pose=dict(hip_deg=25, knee_deg=81, yaw_deg=0), metrics=metrics,
                washers=records, failures=failures, passed=not failures,
                retention_logic="The screw and washer tighten onto the fixed stub. The washer overlaps the disc bore while remaining axially clear of the rotating disc.",
                limitations=[
                    "The 1.6 mm blind floor is nominal remaining material, not a verified load capacity.",
                    "Measure the actual stub, disc bore and washer before confirming free rotation.",
                    "The retaining screw head and thread engagement are not modeled by this washer check.",
                    "A compatible supplier shell is used; it is not certified as the exact owned C018 build.",
                ])


def write_report(report):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["R4 production leg interface check", "", "Passed: " + str(report["passed"]),
             "Created UTC: " + report["created_utc"], ""]
    if "runtime_error" in report:
        lines += ["Runtime error:", report["runtime_error"], ""]
    for name in ("solid_checks", "motion", "connector_reserves", "clamp_access", "retention"):
        if name in report:
            result = report[name]
            lines.append(name + ": " + str(result.get("passed", not result.get("failures"))))
            for key in ("part_count", "sample_count", "cross_link_pairs_considered", "pairs_considered",
                        "boolean_pairs_tested"):
                if key in result:
                    lines.append("  " + key + ": " + str(result[key]))
            lines.append("  failures: " + str(len(result.get("failures", []))))
    if "retention" in report:
        lines += ["", "Nominal retention and pocket dimensions:"]
        lines += ["  " + name + ": " + str(value) for name, value in report["retention"]["metrics"].items()]
    lines += ["", "Limitations:"] + ["  " + text for text in report["limitations"]]
    lines += ["", "Source SHA256 before:"]
    lines += ["  " + name + ": " + value for name, value in report["source_sha256_before"].items()]
    lines += ["", "Source SHA256 after:"]
    lines += ["  " + name + ": " + value for name, value in report["source_sha256_after"].items()]
    lines += ["", "Changed sources: " + str(report["source_files_changed"]), ""]
    OUTPUT.with_suffix(".txt").write_text("\n".join(lines), encoding="utf-8")


def main():
    initial_hashes = source_hashes()
    report = dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256_before=initial_hashes,
        intersection_failure_threshold_mm3=INTERSECTION_MM3,
        intersection_failure_comparison="strictly greater than",
        aabb_tolerance_mm=AABB_TOLERANCE_MM,
        limitations=[
            "Discrete local leg samples do not establish continuous clearance or full robot clearance.",
            "Connector proxies are provisional envelopes and do not reproduce flexible cable behavior.",
            "The blind connector pocket leaves about 1.6 mm of material; fit and loaded strength require physical tests.",
            "Printed tolerances, loaded deflection, retainer seating and servo thermal behavior remain physical checks.",
            "Tool envelopes establish access only for their specified dimensions and approach directions.",
        ],
    )
    try:
        parts = leg.build_leg()
        report["solid_checks"] = shape_checks(parts)
        report["motion"] = motion_checks(parts)
        report["connector_reserves"] = proxy_checks(parts)
        from check_r4_clamp_access import run_clamp_access
        report["clamp_access"] = run_clamp_access(parts)
        report["retention"] = retention_checks(parts)
    except Exception:
        report["runtime_error"] = traceback.format_exc()
    final_hashes = source_hashes()
    report["source_sha256_after"] = final_hashes
    report["source_files_changed"] = [name for name in initial_hashes if initial_hashes[name] != final_hashes[name]]
    sections = ("solid_checks", "motion", "connector_reserves", "clamp_access", "retention")
    report["passed"] = (not report.get("runtime_error") and not report["source_files_changed"] and
                        all(report.get(name, {}).get("passed", False) for name in sections))
    write_report(report)
    print("R4 interface report", OUTPUT.with_suffix(".json"), "passed", report["passed"], flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
