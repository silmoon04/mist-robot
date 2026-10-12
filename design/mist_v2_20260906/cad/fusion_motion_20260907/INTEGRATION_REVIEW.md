# Proximal recipe integration

The proximal recipe passes offline motion-plan creation for **657 parts: 33 body parts and 156 parts per leg**. It creates a plan for **16 main revolute joints, 33 rigid groups and 16 fixed-phase rotor attachments**. No part is assigned twice, and no plan error remains. This full assembly has not been validated by the later native 17-component fixture; that separate fixture passed 16 joint probes and 96 world checks, as recorded in `NATIVE_VERIFICATION.md`.

`current_integration.json` identifies the final run directory. That directory contains the exact input source snapshots, parameter/body/leg specifications, `group_overrides.json`, `assignment_audit.json`, `motion_plan.json` and `integration_report.json`. Earlier integration runs are retained. The model plan hash is `41e08706d426d6a213371c45ce0b878acdfd995f3b4df9f05307b0478e1af909`.

`reviewed_groups.py` supplies **392 explicit overrides**, comprising 97 reviewed retained parts plus the rotating proximal input shaft, for each of four legs. It uses names and physical function, not placement links. New proximal and retention parts retain their explicit recipe groups; an unknown retained name or missing expected part stops the run for review.

| Parts | Assigned motion group | Reason |
|---|---|---|
| Y06 yaw output gear and Y05 shaft | yaw | Rotate the yaw carriage. |
| Y07 input pinion and Y08 horn | yaw_motor_rotor | Rotate relative to the stationary yaw motor case. |
| H06 output gear and H05 trunnion | femur | Carry hip output motion. |
| H07 input pinion and H09 horn | hip_motor_rotor | Rotate relative to the hip case on the yaw carriage. |
| W05 motor case, W07 cradle, W08 braces and W01 bearing envelopes | tibia | The motor/support housing stays with the tibia. |
| W02 axle, W03 hub, W04 tyre, W06 output shaft and W09 coupler | wheel | Direct 1:1 output rotation, independent of the motor case. |
| PF06 input shaft | knee_input_rotor | Confirmed by the design owner as a rotating shaft, not a fixed dead axle. |
| PF07 input pulley, PF08 output gear, matching spacers and end retention | knee_input_rotor | Supported input rotor; kept separate from the femur housing. |
| PF09 pinion and PF11 horn | knee_motor_rotor | Knee actuator input rotor. |
| PF07 knee pulley and knee output retention | tibia | Output rotates with the tibia. |

The inner and outer races within each simplified bearing are not separate solids. The bearing envelope is assigned to its housing; inner-race rotation is omitted. The belt pitch ribbon follows the femur without circulation. Each input rotor is explicitly attached at fixed phase to its housing for the native kinematic preview. Neither a gear mate nor a belt mate is inferred.

The existing `native_replay.py` returns unique component objects, which the motion helper resolves to root-context leaf occurrences. This is a valid contract even though the replay's local `occurrences` dictionary is not returned. It checks one solid body per part, converts recipe translations from millimetres to Fusion centimetres and uses `transform2`. No concrete API mismatch was found in that wrapper.

The final pass corrected three issues in the root-owned `fusion_run.py` wrapper and wired the grouping map at both plan calls:

1. Entry modules were reloaded but dependencies could remain cached in Fusion's persistent Python process. Dependencies now reload in order from captured source bytes. Those executed bytes and their hashes are saved, so a later run cannot silently execute a stale same-name module while reporting current source hashes.
2. The wrapper set `native_motion_verified=True` after small joint probes. It now reports `native_motion_joints_created` and `native_direction_probes_completed` separately, while retaining false full-motion verification. Successful creation does not establish full travel or collision clearance.
3. Viewport fitting and image export return values were ignored. Failure now reaches the existing error report instead of silently claiming the preview was produced.

A separate agent checked the wrappers against installed Autodesk declarations and the motion-helper contract. These were its concrete findings, beyond the already identified grouping requirement and motion-verification wording. At this integration stage, Python compilation, **48 installed API checks**, and **22 offline tests** passed. The subsequent live-drive fix raises the API declaration count to 50. The repeat-load test changes a module without changing its size or timestamp and verifies that the executed value and recorded hash both update.

This result remains an offline integration result for the full recipe. The later small native fixture establishes joint creation, direction/axis/centre checks, restoration, upstream world-datum behavior and F3D export for 17 root-level components. Native nested proxies, multi-part groups, rotor attachments and full motion of the 657-part assembly remain unverified. This integration pass did not modify leg geometry, the checked old candidate or the installed launcher.
