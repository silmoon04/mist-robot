"""Check sampled full-assembly poses; this is not a continuous sweep proof."""
from __future__ import annotations

from datetime import datetime, timezone
import itertools
import json
import math
from pathlib import Path

import build
import geom

CAD = Path(__file__).resolve().parent
ROOT = CAD.parent
OUT = CAD / "output" / "full_motion_check.json"
TEXT_OUT = OUT.with_suffix(".txt")
INTERSECTION_MM3 = 0.01
AABB_TOLERANCE_MM = 1e-5


def source_hashes():
    paths = [CAD / name for name in ("geom.py", "body.py", "leg.py", "phone.py", "build.py")]
    for name in ("servo_contract.py","hardware/ST3215.step"):
        if (CAD/name).is_file():paths.append(CAD/name)
    paths.append(ROOT / "settings.json")
    return {str(p.relative_to(ROOT)): build.sha(p) for p in paths}


def leg_poses(cfg, initial, yaw_deg, hip_deg, knee_deg):
    result = {name: matrix.copy() for name, matrix in initial.items()}
    for label, azimuth in cfg["leg_azimuth_deg"].items():
        a = math.radians(azimuth)
        mount = build.pose([cfg["yaw_radius_mm"] * math.cos(a),
                            cfg["yaw_radius_mm"] * math.sin(a),
                            cfg["yaw_height_mm"]], [0, 0, azimuth])
        result["coxa_" + label] = mount @ build.pose(rpy=[0, 0, yaw_deg])
        result["femur_" + label] = result["coxa_" + label] @ build.pose(
            [cfg["coxa_mm"], 0, 0], [0, hip_deg, 0])
        result["tibia_" + label] = result["femur_" + label] @ build.pose(
            [cfg["femur_mm"], 0, 0], [0, knee_deg, 0])
    return result


def cross_link_intersections(parts, poses):
    physical = [p for p in parts if not p.get("allowance_only")]
    shapes = [build.shape_at(p["shape"], poses[p["link"]]) for p in physical]
    boxes = [geom.bounds(s) for s in shapes]
    pair_count = 0
    boolean_count = 0
    failures = []
    for i, j in itertools.combinations(range(len(physical)), 2):
        a, b = physical[i], physical[j]
        if a["link"] == b["link"]:
            continue
        pair_count += 1
        amin, amax = boxes[i]
        bmin, bmax = boxes[j]
        if any(amax[k] <= bmin[k] + AABB_TOLERANCE_MM or
               bmax[k] <= amin[k] + AABB_TOLERANCE_MM for k in range(3)):
            continue
        boolean_count += 1
        v = geom.common_volume(shapes[i], shapes[j])
        if v > INTERSECTION_MM3:
            failures.append({"a": a["name"], "b": b["name"],
                             "link_a": a["link"], "link_b": b["link"],
                             "intersection_mm3": v})
    return {"physical_parts": len(physical), "cross_link_pairs_considered": pair_count,
            "boolean_pairs_tested": boolean_count, "failures": failures}


def main():
    initial_hashes = source_hashes()
    manifest_path=CAD/"output"/"assembly_manifest.json"
    manifest_hash=build.sha(manifest_path)
    cfg, parts, initial, _ = build.load_assembly()
    operating_yaw=float(cfg.get("yaw_operating_limit_deg",22.0))
    is_inward=cfg.get("knee_servo_orientation")=="tail inward toward hip"
    yaw_samples=(-operating_yaw,0.0,operating_yaw) if is_inward else (-18.8,0.0,18.8)
    coupled_samples=((16.0,70.0),(30.0,81.0),(34.0,91.0)) if is_inward else ((13.9,55.0),(30.0,75.0),(34.15,86.79))
    samples = []
    for yaw, (hip, knee) in itertools.product(yaw_samples,coupled_samples):
        poses = leg_poses(cfg, initial, yaw, hip, knee)
        audit = cross_link_intersections(parts, poses)
        samples.append({"yaw_deg_all_legs": yaw, "hip_deg_all_legs": hip,
                        "knee_deg_all_legs": knee,
                        "link_to_base_matrices_mm": {name: m.tolist() for name, m in poses.items()},
                        **audit})
        print("Leg pose", yaw, hip, knee, "Boolean pairs", audit["boolean_pairs_tested"],
              "Failures", len(audit["failures"]), flush=True)
    stance_samples=[]
    for yaw in (-operating_yaw,0.0,operating_yaw):
        poses=leg_poses(cfg,initial,yaw,30.0,81.0)
        audit=cross_link_intersections(parts,poses)
        stance_samples.append({"yaw_deg_all_legs":yaw,"hip_deg_all_legs":30.0,
                               "knee_deg_all_legs":81.0,
                               "link_to_base_matrices_mm":{name:m.tolist() for name,m in poses.items()},
                               **audit})
        print("Additional stance",yaw,30.0,81.0,"Boolean pairs",audit["boolean_pairs_tested"],
              "Failures",len(audit["failures"]),flush=True)
    diagnostic_samples=[]
    for yaw in (-25.0,25.0):
        poses=leg_poses(cfg,initial,yaw,30.0,81.0)
        audit=cross_link_intersections(parts,poses)
        diagnostic_samples.append({"yaw_deg_all_legs":yaw,"hip_deg_all_legs":30.0,
                                   "knee_deg_all_legs":81.0,
                                   "link_to_base_matrices_mm":{name:m.tolist() for name,m in poses.items()},
                                   **audit})
        print("Outside operating range",yaw,30.0,81.0,"Boolean pairs",audit["boolean_pairs_tested"],
              "Failures",len(audit["failures"]),flush=True)
    from check_phone_pan_samples import run_phone_samples
    phone_report = run_phone_samples(cfg, parts, initial)
    from check_yaw_clearance import run_yaw_clearance,run_operating_yaw_clearance
    yaw_clearance=run_yaw_clearance(cfg,parts,initial)
    operating_clearance=run_operating_yaw_clearance(cfg,parts,initial)
    final_hashes = source_hashes()
    changed_sources = [name for name in initial_hashes if initial_hashes[name] != final_hashes[name]]
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "design_revision":cfg.get("revision"),
        "yaw_operating_limit_deg":operating_yaw,
        "coupled_leg_pose_set_deg":[list(p) for p in coupled_samples],
        "assembly_manifest_sha256":manifest_hash,
        "assembly_manifest_sha256_after_check":build.sha(manifest_path),
        "scope": "Discrete full-assembly poses. This is not a continuous swept-volume proof.",
        "units": {"translation": "mm", "rotation_input": "degrees", "intersection": "mm3"},
        "geometry_source_sha256": initial_hashes,
        "geometry_source_sha256_after_check": final_hashes,
        "source_files_changed_during_check": changed_sources,
        "checker_sha256": build.sha(Path(__file__)),
        "phone_checker_sha256": build.sha(CAD / "check_phone_pan_samples.py"),
        "yaw_clearance_checker_sha256":build.sha(CAD/"check_yaw_clearance.py"),
        "positive_intersection_threshold_mm3": INTERSECTION_MM3,
        "aabb_tolerance_mm": AABB_TOLERANCE_MM,
        "same_link_pairs": "Excluded; evaluated by the separate static assembly check.",
        "allowance_only_parts": "Excluded because they are mass accounting volumes.",
        "unmodeled_items": ["Fastener heads and tips", "Actual plug dimensions and flexible cable routing"],
        "leg_samples": samples,
        "leg_sample_count": len(samples),
        "total_leg_cross_link_pairs_considered": sum(s["cross_link_pairs_considered"] for s in samples),
        "total_leg_boolean_pairs_tested": sum(s["boolean_pairs_tested"] for s in samples),
        "leg_failures": [{"sample_index": i, **hit} for i, sample in enumerate(samples)
                         for hit in sample["failures"]],
        "phone_samples": phone_report,
        "additional_stance_samples":stance_samples,
        "additional_stance_sample_count":len(stance_samples),
        "additional_stance_boolean_pairs_tested":sum(s["boolean_pairs_tested"] for s in stance_samples),
        "additional_stance_failures":[{"sample_index":i,**hit} for i,s in enumerate(stance_samples)
                                      for hit in s["failures"]],
        "yaw_clamp_clearance":yaw_clearance,
        "operating_yaw_clearance":operating_clearance,
        "operating_yaw_minimum_gap_target_mm":1.0,
        "outside_operating_range_diagnostics":diagnostic_samples,
        "outside_operating_range_diagnostic_scope":
            "The plus and minus 25 degree probes are outside the configured yaw operating range. "
            "Their results remain visible but do not qualify that range for operation.",
    }
    phone_failures = phone_report.get("failures", []) if phone_report else []
    report["passed"] = not (report["leg_failures"] or changed_sources or phone_failures
                            or report["additional_stance_failures"] or operating_clearance.get("failures",[])
                            or operating_clearance["minimum_gap_mm"]<1.0
                            or report["assembly_manifest_sha256_after_check"]!=manifest_hash)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    notes=[f"Design revision: {report['design_revision']}",
           f"Assembly manifest SHA256: {manifest_hash}",
           f"Passed intersection checks: {report['passed']}",
           f"Whole-assembly leg samples: {len(samples)}",
           f"Additional 30 degree hip and 81 degree knee stance samples: {len(stance_samples)}",
           f"Phone pan samples: {phone_report['sample_count']}",
           f"Configured yaw operating limit: plus or minus {operating_yaw} degrees",
           f"Minimum operating coxa gap to the deck, yaw saddle or cap: {operating_clearance['minimum_gap_mm']:.6f} mm",
           f"The plus and minus 25 degree diagnostic clamp gap is {yaw_clearance['minimum_gap_mm']:.6f} mm; that angle is outside the operating range.",
           f"Positive intersection threshold: {INTERSECTION_MM3} mm3",
           "The JSON report records each matrix, source hash, Boolean result and measured yaw gap.",
           "Positive nominal gaps are not physical fit qualification. Printed dimensions, fasteners and cable routing remain unmeasured.",
           "These are discrete poses, not a continuous swept-volume proof."]
    TEXT_OUT.write_text("\n".join(notes)+"\n",encoding="utf-8")
    print("Report", OUT, "passed", report["passed"], flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
