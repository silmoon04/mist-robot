# Native drive failure and controlled correction

The corrected fixture subsequently **passed** at `joint_fixture_runs/20260907T110854554885Z/`: all 16 joint probes and 96 component/world-datum checks passed, the F3D exported, and the existing body stayed unchanged. The chronology below preserves the failure and the basis for the correction.

The first native 17-component fixture created its components and the first as-built joint, then failed the original strict probe check. The existing MIST body document was reactivated and its fingerprint was unchanged. The failure report is retained under `joint_fixture_runs/20260907T105705656211Z/`.

The subsequent staged diagnostic reused only that marked test fixture. `last_joint_drive_diagnostic.json` points to its raw report. It found three distinct behaviors:

| Stage | Native rotation value | Observed behavior |
|---|---:|---|
| Before drive | 0 rad | As-built pose. |
| Immediately after requesting 0.001 rad | 0.0017453292519943296 rad | Exactly 0.1°. Child rotates around world Y although the requested yaw axis is world Z. |
| After doEvents and viewport refresh | Same 0.1° | Wrong-axis pose remains. |
| After Compute All | 0 rad | Rotation and component transform return to the as-built pose. |

The diagnostic reapplied the original axis/centre/delta check at every stage and did not relax its tolerances. Final restoration error was zero for both parent and child, and the body fingerprint was unchanged.

The next controlled fixture changes three things in `motion.py`:

- Its fixed parent-owned sketch point lies on a plane whose normal is the intended joint axis. The as-built input uses standard joint Z. This avoids depending on the custom-line path that produced the wrong axis in the live test.
- The probe commands exactly **0.1°**, matching the observed setter resolution. The same strict geometric tolerance still compares commanded and actual rotation.
- Event/viewport refresh updates the transient driven pose before measuring. Compute All is retained after restoration, where returning to the as-built pose is intended.

The fixture's combined front-left yaw/hip/knee drive likewise refreshes without recomputing until its checks are complete. This is a temporary Drive Joints validation, not a claim that rotationValue creates a persistent parameterized pose.

Sources before the correction are preserved in `before_drive_fix/`. The corrected script compiles, passes 50 installed API declaration checks and preserves the 16 helper contract/math tests. Its separate native pass is established by the actual report linked above, not by those offline checks.
