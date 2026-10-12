# Hexapod-derived quadruped with landscape phone

This is a new four-leg reconstruction based on [Emre Kalem's hexapod video](https://www.youtube.com/watch?v=ciE2Z_92T7s). It retains the faceted hexagonal body and exposed articulated legs, replaces the original MG996R interfaces with STS3215 C018 case clamps and supplied metal horns, and adds a rotating bare Xiaomi Mi 9 SE in landscape orientation. Earlier MIST geometry was not used.

The creator's MakerWorld download was blocked by the available browser. These are newly constructed solids based on the observed design and manufacturer dimensions, not an edited original STEP file. [Reference evidence and attribution](references/sources.md) records the accessible video, model page and builder feedback.

## Open and print

- Open [the interactive assembly](http://127.0.0.1:8138/review/) to orbit, rotate the phone, inspect the hardware and remove the cover visually. Start it again with `python review/serve.py` from this design directory if needed.
- The full assembly is [Hex_Quad_Phone_assembly.step](cad/output/Hex_Quad_Phone_assembly.step). Per-part STEP and already oriented STLs are under `cad/output/parts_step` and `cad/output/print_stl`.
- Open [quadruped_phone_native.f3d](cad/output/fusion/quadruped_phone_native.f3d) in Fusion for the assembled model with its thirteen working revolute joints.
- Start with [coupon plate 01](printing/coupon_plate_01.3mf) and [coupon plate 02](printing/coupon_plate_02.3mf). The first contains the leg interfaces and phone horn stack. The second contains three landscape phone-clearance trials. These are geometry-only 3MF files, not sliced printer instructions.
- Follow [PRINT_AND_ASSEMBLE.md](printing/PRINT_AND_ASSEMBLE.md), record measurements in [coupon_feedback.csv](printing/coupon_feedback.csv), and use [manufacturing_bom.csv](printing/manufacturing_bom.csv) for the full quantities.
- Read [WIRING.md](printing/WIRING.md) for the proposed power branches, TTL bus and servo IDs. No servo IDs, calibration or firmware were written to physical hardware.

![Landscape quadruped assembly](review/hero.png)

## What is in the design

| Item | Current design |
|---|---|
| Actuators | 13 STS3215 C018 units: 12 leg joints and one phone pan |
| Leg dimensions | 50 mm coxa, 90 mm femur, 105 mm tibia |
| Transmission | Direct metal horns and supported auxiliary discs; no gears, belts or wheels |
| Phone | Bare Mi 9 SE, 147.5 mm across and 70.5 mm high, screen upright |
| Rotation | Full mechanical pan with Wi-Fi and internal phone battery; USB attached only while parked |
| Assembly envelope | Approximately 369 x 369 x 310 mm in the saved pose |
| Calculated mass | Approximately 2.411 kg, including solid PLA geometry, nominal hardware and 200 g for wiring/fasteners |
| Printed parts | 33 named STL types, 75 pieces at the listed quantities |
| Printer | Neptune 4 Pro; every part fits the nominal build volume in its supplied orientation |

The underside battery tray keeps the pack low. The cover is removable. Board trays use ties and nominal envelopes because actual PCB mounting holes and connector dimensions remain unmeasured. The open phone frame leaves both rear ends and long-edge buttons accessible; the short-edge USB connector is a parked-service connection.

## Verification and limits

The [static CAD check](cad/output/static_interference.json) reports no positive-volume intersections above 0.01 cubic millimetres in the assembled pose. The [motion check](cad/output/full_motion_check.json) adds nine full-robot leg poses and thirteen phone pan angles without detected collisions. Local leg checks also include provisional connector volumes. These are sampled checks, not proof of every continuous cable or fastener sweep.

The actual Fusion document contains 14 link components, 119 closed solids and 13 revolute joints. Each joint passed a one-degree native drive with the measured world rotation axis and datum movement checked, followed by restoration to the saved pose. Fusion's native interference query also returned zero intersections. [Native verification](cad/output/fusion/progress.json) and [the API workaround](cad/FUSION_JOINT_API.md) preserve the result and the construction method. Native joint motion checks do not establish material strength or hardware performance.

All 33 production and 20 coupon STL files passed watertightness, winding, positive-volume and dimension checks. Both coupon 3MF plates reloaded with their expected named objects. The [plate manifest](printing/plate_manifest.json) binds those files to the CAD revision.

The [URDF](simulation/output/quadruped.urdf) uses calculated link masses, centres of mass and inertia tensors. The final 64-second free-base simulation passes standing, a complete phone rotation and one slow crawl cycle. It advances about 30.3 mm, keeps the intended three supporting feet during sampled swing phases, and records a maximum sampled roll/pitch of 0.235 degrees. Peak sampled commanded torque is 0.529 N m against the model's 0.588 N m cap. The [simulation notes](simulation/output/simulation_notes.txt) and [independent mass/frame audit](simulation/output/mass_frame_audit.json) record the exact inputs and limitations.

This uses an assumed finite PD and gravity-compensation controller. Mapping that behavior to the real servos remains a commissioning task. No physical walking, thermal endurance, impact strength or complete phone-to-robot control was demonstrated. The screen in the preview is a phone envelope; the existing brain software was not changed or deployed to the phone in this modeling task.

Print and measure the coupons before committing to the full set. In particular, confirm the assembled horn/disc spacing, auxiliary free rotation, clamp contact, M3 engagement and landscape phone retention. Nominal manufacturer dimensions cannot establish the fit of the actual printer, servo lot or screws. Use the same material and orientation between each accepted coupon and its part; qualify structural material and loaded behavior separately.

## Reproduce the files

The CAD generator uses direct OpenCascade through `cad/geom.py`, with new geometry in `body.py`, `leg.py` and `phone.py`. Install `cad/requirements.txt` in a suitable Python environment, then run `python cad/build.py`. The direct OpenCascade path avoids the observed CadQuery process-shutdown failure on this machine.

Run `python printing/pack_prints.py` after a changed CAD export. Use the simulator instructions in [simulation/README.md](simulation/README.md). Fusion automation uses `cad/fusion_client.py` against the installed local MCP adapter, `fusion_import.py` for the assembly and `fusion_finish.py` for joints and native export. STEP import preserves editable BRep solids; the original Python construction history is not recreated as native Fusion sketch features.

`settings.json` records the design dimensions. `REQUIREMENTS.md` records scope and verification gates. Generated manifests and checksum records must be refreshed together after any geometry change. The delivery archive is for this private build; attribution and source-access limits are retained with the references.
