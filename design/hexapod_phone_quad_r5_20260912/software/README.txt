# R5 offline joint preview

This folder supplies a local preview contract for the new thirteen-STS3215 quadruped. It does not connect the existing brain application to motors. It imports no existing bench controller and includes no serial or network transport. All IDs remain proposals and all calibration fields remain empty.

R5 changes the mechanical shape to an inward-facing hip servo and straight tibia. The current manifest supplies a 70 mm coxa, 90 mm femur and 105 mm tibia. The profile records these dimensions and every joint origin; hip origins must agree with the coxa length. Joint names, proposed IDs and dry-run behavior remain the same. The existing phone app and its network setup were not changed for this mechanical revision.

The current manifest limits each yaw preview to minus 19 through plus 19 degrees. Tests accept both endpoints and reject values just beyond them on all four legs. The 1.5 mm manufacturing clearance target belongs to the CAD checks; this software only validates angles against the manifest.

From this design directory, run:

```powershell
python software/run_checks.py
python software/r5_preview.py preview --profile software/r5_profile.json --request software/neutral_request.json
python software/r5_preview.py preview --profile software/r5_profile.json --request software/pan_request.json
```

The first command regenerates the profile and examples from `cad/output/assembly_manifest.json`, runs the offline checks and saves `validation_results.json` and `validation_results.txt`. The examples contain radian positions in the new CAD and URDF frames. The neutral pose has zero yaw, 30-degree hip and 75-degree knee angles on every leg; this is a geometric pose, not a servo startup command.

The supported preview actions are `get_capabilities`, `joint_pose`, `phone_pan` and `stop`. Every request contains exactly `schema_version`, `action` and `args`. A joint pose supplies all thirteen names through `positions_rad`. A pan request supplies `angle_rad`. Both motion previews require `usb_connected: false`; the standalone contract cannot verify the actual cable state. Missing or additional joint names, stale profiles, nonfinite values and angles outside the manifest ranges are rejected. No range check establishes collision clearance or an acceptable load.

Pan is represented by its principal angle from minus pi to plus pi. This preview neither accumulates revolutions nor selects raw servo registers. A saved zero-degree preview does not home the physical pan. `--mode hardware` always exits with a structured refusal, and even a modified calibration JSON cannot enable a hardware path in this package.

The proposed map is FL 1/2/3, FR 4/5/6, RL 7/8/9, RR 10/11/12 and phone pan 13. These values do not describe detected hardware. `raw_servo_counts` and `transport_packets` remain null; every result says `actuated: false`. A preview stop explicitly leaves `physical_stop_confirmed: false`.

`walk`, `drive`, `move`, `pose`, `dance`, `turn` and `look_at` from the existing brain are intentionally not converted into servo targets. That work needs the new controller, actual calibration and, for gaze, an observed target and camera frame. Do not forward `brain` audit-log entries to a motor interface.

See `../references/brain_integration.md` for existing app behavior, phone networking and the remaining commissioning steps. The software tests use only local files and Python subprocesses. They do not read secrets, start the brain app, open a microphone or call a provider.
