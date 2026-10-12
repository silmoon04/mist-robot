# Crawl with the fitted CAD mass and inertia

The fitted 7.108 kg mass/inertia input does not preserve the earlier fast, continuously supported crawl. The 80 mm / 3-second controller fails swing clearance and final lateral drift. One bounded fallback, 60 mm / 4 seconds, meets the recorded aggregate criteria but still recovers from transient two-wheel support. Neither result establishes a robust physical crawl or stair capability.

The two new runs use the authoritative 17-link inertials in `../proximal_cad_20260907/parameters_cad_inertials.json`. Root converted and validated these from the frozen 657-solid CAD candidate. The 7.108 kg value retains the CAD's full-solid print and hardware-envelope mass assumptions. Collision geometry is still the simulation's coarse boxes/cylinders; zero overlap in the CAD's single checked pose does not validate these trajectories against the full assembly.

The older 6.341 kg result remains unchanged and is included only to show the model-input regression. All three cases below use the same joint torque/current limits. The matched runs use `runtime_cad`, whose exact per-link COM helper and complete base inertial-frame transform were verified before execution.

| Case | Mass kg | Forward mm / s | Drift mm | Tilt ° | Shaft RMS Nm | Minimum swing peak mm | <3 contacts % | Minimum support margin mm | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| [stride80_force_feedback_3s_3cycles](stride80_force_feedback_3s_3cycles/report.json) | 6.341 | 237.35 / 39.50 | -1.34 | 1.75 | 0.663 | 26.65 | 0.000 | 18.23 | Pass |
| [matched_cad_80mm_3s_3cycles](matched_cad_80mm_3s_3cycles/report.json) | 7.108 | 239.49 / 39.50 | 11.85 | 6.76 | 0.708 | 7.87 | 0.842 | -29.86 | Fail |
| [matched_cad_60mm_4s_3cycles](matched_cad_60mm_4s_3cycles/report.json) | 7.108 | 168.63 / 51.58 | -0.72 | 4.11 | 0.680 | 22.78 | 1.277 | -122.93 | Pass |

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
