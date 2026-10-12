# Selected 80 mm crawl: independent evidence review

The selected three-cycle run advances **237.35 mm in 39.501 seconds**, averaging **6.01 mm/s**. After initial settling, every recorded sample has at least three wheels carrying more than 1 N, and the smallest stored support margin is **+18.23 mm**. All 12 scheduled swings clear 15 mm, unload and subsequently confirm touchdown. The largest individual actuator RMS is **0.66335 Nm**, below the unchanged assumed continuous limit of **0.72814 Nm**.

This is a slow simulated crawl under the existing 6.341 kg coarse mass model. Contact and support telemetry is recorded at 50 Hz, so “no sampled loss of support” does not establish uninterrupted support between samples. It is not a validation of fitted CAD, stairs or physical hardware.

**The result is conditional on the assumed mechanical play.** A later [combined test with doubled servo/external backlash, lower grip and 40 ms delay](../stride80_sensitivity_double_backlash/report.json) fails: worst actuator RMS rises to **0.73497 Nm**, above **0.72814 Nm**, and one swing reaches only **12.838 mm** clearance, below **15 mm**. That case has no sampled loss of three-wheel contact and a positive **9.789 mm** minimum margin, so contact stability alone does not make it pass. The chart below retains the selected nominal run's data.

![Selected 80 mm crawl diagnostic](controller_selected80_3s_3cycles.png)

Exports: [SVG](controller_selected80_3s_3cycles.svg) · [PDF](controller_selected80_3s_3cycles.pdf). The reproducible generator is [plot_selected80_review.py](plot_selected80_review.py), with exact chart-source hashes in [controller_selected80_chart_sources.json](controller_selected80_chart_sources.json). The earlier [4-second review](controller_review.md) and all its artifacts are preserved.

## Checked results

An independent review recomputed displacement from the trajectory, tilt from its base quaternion, contact counts from wheel forces, each scheduled swing's clearance/unloading/touchdown, and every actuator RMS from the saved 1 kHz torque array. No numerical mismatches with either report were found.

| Metric | Selected nominal run | Lower-grip / longer-delay run |
|---|---:|---:|
| Tire friction coefficient | 0.75 | 0.60 |
| Servo command delay | 25 ms | 40 ms |
| Actual forward distance | 237.353 mm | 239.144 mm |
| Duration | 39.501 s | 39.501 s |
| Mean forward speed | 6.009 mm/s | 6.054 mm/s |
| Final lateral displacement | −1.343 mm | −1.928 mm |
| Maximum lateral excursion | 51.369 mm | 51.716 mm |
| Maximum tilt | 1.753° | 1.827° |
| Worst individual actuator RMS | 0.663351 Nm | 0.660543 Nm |
| Smallest peak clearance across all 12 swings | 26.647 mm | 26.083 mm |
| Smallest stored support margin after settling | +18.231 mm | +21.271 mm |
| Samples with fewer than three loaded wheels after settling | 0 / 1,901 | 0 / 1,901 |
| Negative or undefined stored margins after settling | 0 | 0 |
| Swings with verified unloading and touchdown | 12 / 12 | 12 / 12 |
| Saved model status | PASS_IN_MODEL | PASS_IN_MODEL |

Both runs contain 1,976 trajectory frames and 39,501 actuator samples. Every trajectory torque sample exactly matches the corresponding entry in the 1 kHz array. Each run has 602 post-settle samples with three loaded wheels and 1,299 with four. The 39.50 s label on the final trajectory frame is the start of its 1 ms physics step; the resulting duration is 39.501 s.

For the selected run, the per-actuator RMS values are:

| Leg | Yaw | Hip | Knee |
|---|---:|---:|---:|
| FL | 0.114132 Nm | 0.409086 Nm | 0.435824 Nm |
| FR | 0.096048 Nm | 0.315478 Nm | 0.569821 Nm |
| RL | 0.081657 Nm | 0.254738 Nm | 0.663351 Nm |
| RR | 0.140537 Nm | 0.355331 Nm | 0.553434 Nm |

These values are individual motor results, not averages pooled across legs. The worst motor has approximately 8.9% margin to the assumed continuous RMS limit. At least one actuator saturates during 5.08% of physics steps, so the passing RMS should not be described as unlimited torque headroom or a measured thermal qualification.

## What this controller does

The saved controller uses 80 mm strides, a 3 s period per leg, 40 mm commanded swing lift and order RL → FL → RR → FR. It targets a 30 mm COM inset before swing and uses bounded contact-force feedback at 0.25 mm/N, along with the existing body-pose feedback and wheel-orientation compensation. The desired body mount-plane height is **243.5 mm**: the loader starts at 233.5 mm, including its 1 mm initial floor gap, and the controller adds 10 mm. The earlier analytic 242.5 mm screen is a separate reference and is not the saved command height for this run.

The two consecutive cycle milestones at matching support phases advance 82.367 mm and 82.632 mm. The total three-cycle forward target is 240 mm; after final recentering, actual travel is 237.353 mm. Large lateral excursions are intentional shifts of the COM, while the final lateral displacement is only −1.343 mm.

Relative to the earlier 60 mm / 4 s run, the selected controller has no recorded repeat of that run's brief two-wheel support episode. Stride, period, lift and contact-force feedback changed together, so the comparison does not isolate a single cause. The separate lower-grip / longer-delay case also passes, but it tests one combined perturbation rather than a complete uncertainty envelope.

## Remaining evidence limits

The contact count uses aggregate wheel force greater than 1 N. The stored support margin comes from qualifying individual contacts above 0.25 N with sufficiently upward normals. The margin aggregation was independently checked, but the raw contact-point coordinates are absent from the trajectory; the underlying support polygon cannot be reconstructed independently from the saved data alone.

Both parameter files retain the original coarse link mass distribution and have no `link_mass_properties` override. The same 55 g knee actuator is relocated to the femur in that hypothetical reaction-frame model, with fitted hardware assessed separately. The exact-COM helper and complete inertial-frame transform corrections described in the [earlier review](controller_review.md) are necessary when switching to full CAD mass properties. These diagonal-inertia runs are unaffected by the earlier inertial-quaternion omission.

The simulator supplies ideal body pose and contact forces. Sensor estimation, real servo dynamics, force-side backlash, thermal duty, printed-part compliance, wire motion and exact collision geometry remain unvalidated. No new physics was run for this review, and no raw report was rewritten. The doubled-backlash failure above is included as a material qualification; other later sensitivity variants are outside this note.

## Evidence

- [Selected report](../stride80_force_feedback_3s_3cycles/report.json)
- [Selected trajectory](../stride80_force_feedback_3s_3cycles/trajectory.json)
- [Selected 1 kHz actuator trace](../stride80_force_feedback_3s_3cycles/servo_torques_1000hz.npz)
- [Selected controller](../stride80_force_feedback_3s_3cycles/controller.json)
- [Selected parameters](../stride80_force_feedback_3s_3cycles/parameters_used.json)
- [Lower-grip / longer-delay report](../stride80_sensitivity_3s_grip060_delay040/report.json)
- [Lower-grip / longer-delay parameters](../stride80_sensitivity_3s_grip060_delay040/parameters_used.json)

The generator checks that chart input files have identical SHA-256 hashes before and after rendering. Plot dependencies remain isolated from the simulation environment.
