"""Compare saved matched-inertia crawl runs without changing raw evidence."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    cases = ["stride80_force_feedback_3s_3cycles", "matched_cad_80mm_3s_3cycles", "matched_cad_60mm_4s_3cycles"]
    rows = []
    for name in cases:
        folder = HERE / name
        report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
        parameters = json.loads((folder / "parameters_used.json").read_text(encoding="utf-8"))
        assert hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest() == report["parameters_sha256"]
        assert all(hashlib.sha256((folder / path).read_bytes()).hexdigest() == sha for path, sha in report["source_sha256"].items())
        rows.append({"run": name, "mass_kg": report["mass_kg"], "status": report["status"],
                     "failed_criteria": [k for k, value in report["criteria"].items() if not value],
                     "duration_s": report["duration_s"], "forward_mm": report["base_displacement_m"][0] * 1000,
                     "lateral_mm": report["base_displacement_m"][1] * 1000, "mean_forward_mm_s": report["mean_forward_speed_m_s"] * 1000,
                     "tilt_deg": report["max_tilt_deg"], "shaft_rms_nm": report["max_servo_rms_nm"],
                     "saturation_pct": report["motor_saturation_fraction"] * 100,
                     "min_swing_peak_mm": min(s["max_swing_clearance_m"] for s in report["swing_audits"]) * 1000,
                     "contact_loss_pct": report["fewer_than_three_contact_sample_fraction"] * 100,
                     "min_sampled_support_margin_mm": report["min_sampled_support_margin_m"] * 1000,
                     "source_sha256": report["source_sha256"], "parameters_sha256": report["parameters_sha256"]})
    (HERE / "matched_cad_comparison.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    fallback = cases[-1]
    manifest = {"schema_version": 1, "status": "matched_mass_inertia_fallback_passes_aggregate_criteria_with_support_transients",
                "mass_kg": rows[-1]["mass_kg"], "candidate_run": fallback, "rejected_fast_run": cases[1],
                "parameters": fallback + "/parameters_used.json", "controller": fallback + "/controller.json",
                "trajectory": fallback + "/trajectory.json", "scene": fallback + "/scene.json", "report": fallback + "/report.json",
                "runtime": "runtime_cad", "uses_fitted_link_inertials": True, "uses_fitted_collision_geometry": False,
                "continuously_supported_in_samples": False, "hardware_or_print_release": False,
                "parameters_sha256": rows[-1]["parameters_sha256"], "source_sha256": rows[-1]["source_sha256"]}
    (HERE / "matched_cad_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    text = """# Crawl with the fitted CAD mass and inertia

The fitted 7.108 kg mass/inertia input does not preserve the earlier fast, continuously supported crawl. The 80 mm / 3-second controller fails swing clearance and final lateral drift. One bounded fallback, 60 mm / 4 seconds, meets the recorded aggregate criteria but still recovers from transient two-wheel support. Neither result establishes a robust physical crawl or stair capability.

The two new runs use the authoritative 17-link inertials in `../proximal_cad_20260907/parameters_cad_inertials.json`. Root converted and validated these from the frozen 657-solid CAD candidate. The 7.108 kg value retains the CAD's full-solid print and hardware-envelope mass assumptions. Collision geometry is still the simulation's coarse boxes/cylinders; zero overlap in the CAD's single checked pose does not validate these trajectories against the full assembly.

The older 6.341 kg result remains unchanged and is included only to show the model-input regression. All three cases below use the same joint torque/current limits. The matched runs use `runtime_cad`, whose exact per-link COM helper and complete base inertial-frame transform were verified before execution.

| Case | Mass kg | Forward mm / s | Drift mm | Tilt ° | Shaft RMS Nm | Minimum swing peak mm | <3 contacts % | Minimum support margin mm | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
"""
    for r in rows:
        text += f"| [{r['run']}]({r['run']}/report.json) | {r['mass_kg']:.3f} | {r['forward_mm']:.2f} / {r['duration_s']:.2f} | {r['lateral_mm']:.2f} | {r['tilt_deg']:.2f} | {r['shaft_rms_nm']:.3f} | {r['min_swing_peak_mm']:.2f} | {r['contact_loss_pct']:.3f} | {r['min_sampled_support_margin_mm']:.2f} | {'Pass' if r['status']=='PASS_IN_MODEL' else 'Fail'} |\n"
    text += """
The faster matched run advances 239.49 mm in 39.50 s, but the weakest swing clears only 7.87 mm against the 15 mm requirement, and final lateral displacement is 11.85 mm against a 10 mm limit. Individual shaft RMS remains below the assumed 0.728 Nm continuous limit, but at least one servo reaches its instantaneous envelope during 24.04% of physics steps, compared with 5.08% in the earlier coarse-mass run. More frequent saturation coincides with the reduced clearance and increased tilt. Both total mass and its distribution changed, so these runs do not isolate a single cause.

The slower fallback advances 168.63 mm in 51.58 s, or 3.27 mm/s. All 12 swings unload, clear at least 22.78 mm and show touchdown. It ends 0.72 mm sideways and reaches 0.680 Nm worst shaft RMS. Its current pass criterion permits fewer than three loaded wheels in up to 5% of recorded samples. The actual fraction is 1.277%, and sampled support margin reaches −122.93 mm. The robot recovers within a 4.11° maximum tilt in this model; the pass label must not be presented as continuous quasistatic support.

No extra parameter sweep or torque increase was performed after the bounded fallback. Both runs use 40 mm commanded lift, the same support-COM planning and the same contact-load correction as the selected earlier controller. The fallback's four-second leg period and 60 mm stride are the only controller changes from the matched fast run.

## Why the mass distribution matters

The fitted input is about 12.1% heavier overall. More importantly, moving links differ substantially: each fitted femur group is about 570 g, compared with about 227 g in the earlier coarse model, while each yaw group falls from about 377 g to 189 g. Mass alone is insufficient to infer joint inertia because the fitted mass can be close to an axis. The independent [mass/COM comparison](geometry_study/matched_cad_mass_comparison.md) therefore examines transformed COMs and parallel-axis inertia instead of treating the change as uniform mass scaling.

For the neutral FL leg with its descendant joints locked, inertia about the yaw axis rises from 0.007212 to 0.014657 kg·m², about 103%. The corresponding hip-axis increase is 16.5%, and the knee-axis increase 7.1%. The femur group's own hip-axis inertia rises about 80%, while its COM moves closer to the hip (62.53 to 41.69 mm). Whole-robot COM is about 2.45 mm lower in the fitted neutral pose. The regression cannot be explained as a simply raised COM.

At an unchanged earlier RL support pose, the fitted COM moves laterally by about 5.50 mm, reducing a nominal 30 mm support margin to 25.18 mm. Restoring the planned margin requires roughly 10.6 mm more lateral body movement. The maximum quasistatic shaft demand for that replanned pose rises from about 1.022 to 1.137 Nm. The matched controller does recompute the COM plan, so its body shift differs even when stride and period stay the same. These static calculations explain changes in balance, required travel and load; they do not isolate inertia as the sole cause of the dynamic failure.

The wheel COMs lie on their local rotation axes (local Y approximately ±2.231 mm; local X/Z are numerical zero), so the planner's nominal zero wheel angle does not introduce a rotating wheel-COM error for this fitted input. The full 17-link COM helper includes the laterally offset femur cartridge directly from the authoritative inertials; the older scalar component allowances are not summed as the robot mass.

## Review and next boundary

[matched_cad_manifest.json](matched_cad_manifest.json) identifies the fallback and the rejected fast case for review integration. Each case contains a complete 50 Hz trajectory, a 1 kHz servo-torque archive, parameters, controller settings, source snapshots/hashes, URDF and scene. `matched_cad_comparison.json` records independently verified source/parameter hashes and the comparison values.

The aggregate pass leaves a clear controller limitation: body shifts can temporarily unload an unintended support wheel. The next controller experiment should preserve measured support through these shifts, rather than relying only on a pre-lift gate. It also needs the fitted collision geometry and measured loaded reversal, compliance, servo timing and tire grip. The earlier doubled-backlash sensitivity already predicts a clearance/torque failure; these matched runs have not repeated that sensitivity.

This study does not operate hardware, validate print orientation or Z strength, fit native Fusion motion joints, or demonstrate stair traversal. Those engineering checks remain separate from this contact-dynamics result.
"""
    (HERE / "MATCHED_CAD_REPORT.md").write_text(text, encoding="utf-8")
    print(json.dumps({"cases": len(rows), "matched_mass_kg": rows[-1]["mass_kg"], "fallback_status": rows[-1]["status"]}))


if __name__ == "__main__":
    main()
