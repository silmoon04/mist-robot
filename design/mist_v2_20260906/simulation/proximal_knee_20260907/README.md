# Proximal knee motor: same-mass simulation comparison

The physical alternative moves one 55 g knee servo per leg from the yaw carriage to 40 mm down the femur. Its housing reacts torque on the femur, so the knee reduction controls the relative knee angle. Total accounted mass stays at 6.341 kg and all three reductions stay at 2:1. No hypothetical weight saving is included. A corresponding CAD revision is being packaged separately.

For the old drive, motor coordinates are `[2*yaw, 2*hip, 2*(hip+knee)]`. For the alternative they are `[2*yaw, 2*hip, 2*knee]`. Virtual work and the relocation of exactly one servo mass per leg are covered by executable tests. A missing mounting-frame declaration or unrecognized topology is rejected.

| Case | Old carriage-mounted knee | Proximal-femur knee | New worst motor RMS | New displacement |
|---|---|---|---:|---:|
| stand | FAIL_IN_MODEL | PASS_IN_MODEL | 0.459 N m | 0.0 mm forward |
| drive | FAIL_IN_MODEL | PASS_IN_MODEL | 0.518 N m | 5106.7 mm forward |
| crawl | FAIL_IN_MODEL | PASS_IN_MODEL | 0.604 N m | 25.8 mm forward |
| step ascent | Not repeated in the mass-only baseline | FAIL_IN_MODEL | 0.765 N m | -68.7 mm forward |
| step descent | Not repeated in the mass-only baseline | FAIL_IN_MODEL | 1.022 N m | 115.8 mm forward |

The continuous motor criterion is an assumed 0.728 N m at 9.9 V. Passing it does not establish measured thermal capacity. Drive advances 5.107 m in 8 seconds in this model. The crawl pass is only a minimal bench criterion: 25.8 mm in 26 seconds, with 18.1 mm lateral drift. It is much too slow for the requested robot, and a separate controller revision is required. Both scripted stair attempts fail.

In the supported single-leg fixture at 20.735 N upward wheel load, the old 2:1 drive missed its criteria with about 15.8 mm foot error. The proximal-femur alternative gives 6.51 mm error and hip/knee RMS torques of 0.534/0.627 N m. At the more demanding 46.654 N case, both hip and knee saturate and the foot error reaches 367 mm. That failure remains part of the design boundary.

This comparison has coarse primitive collision shapes, approximate diagonal inertias, and command hysteresis/reduced stiffness for backlash and compliance. It does not include exact new mounts, supplier pulley changes, rotor/reflected gearbox inertia, thermal dynamics or measured print compliance. The new servo housing mass is included in the femur inertia; its detailed collision envelope is not. These results support the reaction-frame choice, not a full-leg print release.

The original 140 mm / 3.95376 kg simulation artifacts are preserved. Each physics run now loads a private temporary URDF, preventing parallel experiments from replacing the baseline file. The complete ten-test mechanics suite passes. Recorded parameter and source hashes are in `same_mass_summary.json`; interactive playback is indexed in the local engineering review.

Reproduce from `simulation` with `.venv/Scripts/python.exe run_proximal_sensitivity.py`.
