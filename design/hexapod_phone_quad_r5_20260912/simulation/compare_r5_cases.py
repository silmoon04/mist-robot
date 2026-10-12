"""Assemble a comparison of completed R5 runs without changing their reports."""
import argparse
import hashlib
import json
from pathlib import Path


GATES=("standing","phone_full_pan","crawl","actual_foot_steps","mid_swing_support_margin","stance_position","quasi_static_torque","sustained_torque_screen")


def compare(paths,output):
    rows=[]
    for path in paths:
        data=json.loads(path.read_text(encoding="utf-8-sig"))
        if not str(data.get("design_revision","")).startswith("hex_quad_r5"):
            raise ValueError(f"Expected a completed R5 report: {path}")
        params,observed=data["parameters"],data["observed"]
        rows.append({
            "case":path.parent.name,
            "report_path":str(path.resolve()),
            "report_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "manifest_sha256":data["inputs"]["manifest_sha256"],
            "mass_model":data.get("mass_model",{"kind":"unspecified_manifest"}),
            "mass_kg":data["mass_kg"],
            "status":data["status"],
            "inputs_unchanged":data["inputs"]["unchanged_during_run"],
            "uncertainty":data.get("uncertainty_case"),
            "initial_joint_deg":params["initial_joint_deg"],
            "stride_mm":params["stride_mm"],
            "lift_mm":params["lift_mm"],
            "com_shift_mm":params["com_shift_mm"],
            "effort_cap_nm":params["effort_cap_nm"],
            "advance_mm":observed["advance_x_mm"],
            "maximum_stance_error_mm":observed["maximum_stance_error_mm"],
            "minimum_mid_swing_margin_mm":observed["minimum_mid_swing_margin_mm"],
            "peak_static_torque_nm":max(observed["static_peak_joint_torque_nm"].values(),default=None),
            "peak_sampled_torque_nm":max(observed["dynamic_peak_joint_torque_nm"].values(),default=None),
            "failed_dynamics_gates":[key for key in GATES if not data["gates"].get(key,False)],
            "failure":data.get("failure"),
            "printed_strength_verified":data["gates"].get("printed_material_strength",False),
        })
    result={
        "scope":"Comparison of the explicitly listed rigid-body runs. No material-strength, hardware-control or physical-walking qualification is implied.",
        "interpretation":"Compare controller sensitivity only within matching manifest, posture, gait and effort settings. Full-solid and part-only extrusion masses are distinct scenarios.",
        "case_count":len(rows),
        "cases":rows,
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"case_comparison.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    lines=["R5 RIGID-BODY DYNAMICS CASES",result["scope"],result["interpretation"],""]
    for row in rows:
        lines.extend([
            row["case"],
            f"  Status: {row['status']}; mass: {row['mass_kg']:.6f} kg; torque cap: {row['effort_cap_nm']:.3f} Nm",
            f"  Advance: {row['advance_mm']:.3f} mm; maximum stance error: {row['maximum_stance_error_mm']:.3f} mm",
            f"  Failed dynamics gates: {', '.join(row['failed_dynamics_gates']) or 'none'}",
            f"  Manifest SHA256: {row['manifest_sha256']}",
            f"  Report SHA256: {row['report_sha256']}",
            "",
        ])
    (output/"case_comparison.txt").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"cases":len(rows),"output":str(output.resolve())}))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports",type=Path,nargs="+")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    compare(args.reports,args.output)
