"""Summarize the saved eight-case speed-ceiling screen without rerunning it."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE)]
from dev_fast_crawl_probe_v4 import check_prior, experiment_hashes, REFERENCE_PATH


def summarize(row):
    telemetry = row["telemetry_steady"]
    stance_count = stance_loaded = swing_count = swing_loaded = 0.
    for leg in telemetry["per_leg"].values():
        for phase in leg["phase_bins"]:
            count = phase["sample_count"]
            loaded = count*(phase["loaded_fraction"] or 0.)
            if phase["phase"][1] <= .8:
                stance_count += count
                stance_loaded += loaded
            else:
                swing_count += count
                swing_loaded += loaded
    diagnostics = row["motor_diagnostics"]
    command = row["requested_command"]
    return {"variant": row["case"]["variant"], "payload_kg": row["case"]["payload"],
            "seed": row["case"]["seed"], "cycle_s": row["gait"]["cycle_s"],
            "shift_m": row["gait"]["shift_m"], "requested_command": command,
            "average_progress_speed_m_s": row["average_progress_speed_m_s"],
            "steady_forward_speed_m_s": command[0]+row["steady"]["mean_velocity_bias_m_s"][0],
            "steady": row["steady"], "acceptance": row["acceptance"],
            "ik_rejections": row["ik_rejections"],
            "qdot_peak_rad_s": max(diagnostics["actual_joint_speed_peak_rad_s"]),
            "qdot_max_joint_p95_rad_s": max(diagnostics["actual_joint_speed_p95_rad_s"]),
            "qdot_p95_by_joint_rad_s": diagnostics["actual_joint_speed_p95_rad_s"],
            "filtered_target_peak_rad_s": max(diagnostics["filtered_target_speed_peak_rad_s"]),
            "mean_slew_limit_usage_fraction": float(np.mean(diagnostics["target_slew_limit_usage_fraction"])),
            "maximum_slew_limit_usage_fraction": max(diagnostics["target_slew_limit_usage_fraction"]),
            "maximum_joint_servo_target_lag_p95_rad": max(telemetry["p95_servo_target_lag_rad"]),
            "mean_joint_servo_target_lag_p95_rad": float(np.mean(telemetry["p95_servo_target_lag_rad"])),
            "maximum_joint_error_p95_rad": max(telemetry["p95_joint_error_rad"]),
            "pooled_stance_loaded_fraction_phase_0_to_08": stance_loaded/stance_count,
            "pooled_swing_loaded_fraction_phase_08_to_1": swing_loaded/swing_count,
            "contact_by_leg": telemetry["per_leg"],
            "effective_geometric_stride_cap_ratios": row["effective_geometric_stride_cap_ratios"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check_prior()
    record = json.loads(args.input.read_text())
    if record["status"] != "complete" or len(record["results"]) != 8:
        raise RuntimeError("Expected the complete eight-case receipt")
    if record["experiment_hashes"] != experiment_hashes():
        raise RuntimeError("Receipt-bound speed-ceiling experiment bytes changed")
    reference = [summarize(row) for row in json.loads(REFERENCE_PATH.read_text())["results"]]
    rows = [summarize(row) for row in record["results"]]
    selected = [row for row in rows if row["cycle_s"] == 1. and row["requested_command"][0] == .04]
    for row in rows:
        prior = next(saved for saved in reference if saved["payload_kg"] == row["payload_kg"])
        row["average_progress_ratio_to_saved_selected_profile"] = row["average_progress_speed_m_s"]/prior["average_progress_speed_m_s"]
    summary = {"schema": 1, "analysis_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "receipt_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
               "source_identity_unchanged": True, "original_acceptance_unchanged": True,
               "result_scope": "nominal flat-ground forward preview, 480 steps per case; no hardware or qualification claim",
               "default_recommendation": "Retain 1.2s/.025m/s selected preview as the default.",
               "higher_preview_recommendation": "Optional experimental 1.0s/.04m/s forward preview; additional directions are untested by this screen.",
               "selected_higher_profile": {"cycle_s": 1., "shift_m": .005/3.2,
                   "recovery_start": .82, "recovery_end": .96, "translational_stride_gain": 1.15,
                   "command_speed_rad_s": 1.8, "max_translation_m_s": .04,
                   "uncapped_requested_translation_m_s": .035/(.8*1.*1.15)},
               "saved_reference": reference, "results": rows,
               "selected_higher_profile_results": selected}
    with args.output.open("x", encoding="utf-8") as out:
        out.write(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    for row in reference+rows:
        print(row["variant"], row["payload_kg"],
              "speed", round(row["average_progress_speed_m_s"], 6),
              "stance", round(row["pooled_stance_loaded_fraction_phase_0_to_08"], 4),
              "swing", round(row["pooled_swing_loaded_fraction_phase_08_to_1"], 4),
              "lagp95", round(row["maximum_joint_servo_target_lag_p95_rad"], 5),
              "checks", row["acceptance"]["checks"])


if __name__ == "__main__":
    main()
