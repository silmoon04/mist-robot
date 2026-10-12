# Native 17-component fixture passed

The root agent ran the actual Fusion fixture on **2026-09-07 at 11:08:54 UTC**. Its final status is `native_fixture_passed` and its errors list is empty. The test used the real native feature constructors, placement helper and `motion.apply_motion_plan`.

Evidence is in `../fusion_live_20260907/joint_fixture_runs/20260907T110854554885Z/`:

- `fixture_report.json`: complete fixture, world-datum, restoration and preserved-body results.
- `native_motion_report.json`: all 16 created revolutes, measured directions, offsets and applied limit mappings.
- `MIST_JOINT_FIXTURE_TEST_ONLY.f3d`: exported native test assembly.

The run used `motion.py` SHA-256 **0ffe07cdf15fcd6d6c18abcd1d8d096d8ee7ed9bc411ead40fd3cadb393704c8**. The passing fixture source hash is **f08842f673c7ccdcdaef88f31f23858d6b9745acbbb42ea147995f5e616aa64a**.

| Native check | Result |
|---|---|
| Components / solids | 17 / 17 |
| Created and probed revolutes | 16 |
| Baseline transform and joint-world-origin checks | 32 / 32 passed |
| Combined FL +5° yaw, +4° hip, -3° knee checks | 32 / 32 passed |
| Restored baseline checks | 32 / 32 passed |
| Existing MIST body reactivated | True |
| Existing body fingerprint unchanged | True |
| Native F3D export | Succeeded |
| Multi-part rigid groups created | 0, not exercised |

The largest reported world-origin discrepancy during combined motion was **6.04e-13 mm**. The largest transform-matrix discrepancy was **5.68e-14**, with translation expressed in centimetres. These are floating-point CAD comparisons, not manufacturing or physical positioning accuracy.

The first native run failed. A staged diagnostic identified wrong-axis rotation in the custom sketch-line path, rounding of a 0.001 rad request to exactly 0.1°, and resetting of the transient drive by Compute All. That failure and its sources remain in `../fusion_live_20260907/`; `DRIVE_DIAGNOSTIC.md` records the evidence.

The passing version uses a fixed parent-owned sketch point on a plane whose normal is the intended axis, with standard joint Z. It commands exactly **0.1°** for the probe and measures after doEvents/viewport refresh. It calls Compute All only after restoring the assembled value. Original angle, axis, centre and restoration tolerances were not loosened.

All four yaw joints measured sign +1. All hip, knee and wheel joints measured sign -1. The helper continues to measure each sign instead of assuming these values for future assemblies. The report records the native angle mappings; the fixture did not drive against every stop or test limit enforcement over full travel.

This is validation of a **small native kinematic fixture**. Its 17 components are root-level leaves with one component per link. It does not validate the full 657-part recipe, nested occurrence proxies, multi-part rigid groups, rotor attachments, gear/belt mates, collisions, cables, full range, structural strength, actuator response or physical robot motion. Those flags remain false. The sub-agent prepared the scripts and inspected the returned files; the root agent alone executed the serial live Fusion calls.
