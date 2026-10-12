# R5: inward hips and straight lower legs

R5 applies the requested changes to the video-derived quadruped: the hip servo cases face inward, and each lower leg has a straight knee-to-toe main body. The inward knee servos, four-leg layout and upright landscape Mi 9 SE pan mount remain. R4 is preserved separately.

## Changes and trade-offs

The old curve followed the reference robot's silhouette. It did not add a joint or simplify the kinematics. R5 keeps the same 105 mm knee-to-toe distance but uses a straight tapered load path. The main shank is one continuous printed part. A short removable auxiliary cheek supports the opposite shaft, allowing flat printing and easier service. Fusing both sides would require substantial support across the fork gap.

The hip case is rotated 180 degrees inward. Flipping it at the old 50 mm spacing interfered with the yaw support, so the coxa is now 70 mm. A relocated rear clamp screw and dedicated cap avoid cutting through the central post. A triangular flange continues down to the lower arm around both nut windows. The case footprint ends about 5 mm farther inward, while the hip and downstream joints move 20 mm outward. This improves the arrangement but widens the stance; it does not establish lower whole-leg inertia.

The deck has rounded peripheral reliefs for the new coxa. Yaw operation is limited to 19 degrees each side of neutral. The 22-degree diagnostic had only 0.656 mm nominal saddle clearance; 19 degrees gives 1.611 mm. An integer-angle scan finds a minimum deck gap of 1.574 mm. Actual printed gaps remain unmeasured.

## Open and print

- [Interactive R5 model](http://127.0.0.1:8139/review/). Restart with `python review/serve.py` from this directory.
- [Native Fusion assembly](cad/output/fusion/quadruped_phone_native.f3d) and [assembly STEP](cad/output/Hex_Quad_Phone_assembly.step).
- [Print-first instructions](printing/PRINT_FIRST.txt), [assembly guide](printing/PRINT_AND_ASSEMBLE.md) and [R5 fastener stacks](printing/R5_FASTENER_STACKS.md).
- [Plate 01](printing/coupon_plate_01.3mf): 15 common fit/section specimens. [Plate 02](printing/coupon_plate_02.3mf): five complete reusable revision specimens. [Plate 03](printing/coupon_plate_03.3mf): 12 optional alternatives.
- [Nominal URDF](simulation/output_r5_printed_nominal/quadruped.urdf), [recorded motion](simulation/output_r5_printed_nominal/recorded_motion_6x.mp4) and [simulation comparison](simulation/output_r5_comparison/case_comparison.txt).

![R5 quadruped](review/hero.png)

[The side comparison](manufacturing/straight_tibia_study/straight_tibia_comparison.png) shows the old curve and new straight shank using actual CAD meshes. The internal SKU `tibia_curved_main_and_foot` is retained for pipeline compatibility; its R5 shape and display label are straight.

## Size and printing

| Item | Final R5 value |
|---|---|
| Link lengths | 70 mm coxa, 90 mm femur, 105 mm tibia |
| Saved envelope | 373.79 x 373.79 x 310.22 mm |
| Actuators | 13 STS3215 C018 servos |
| Phone | Bare Mi 9 SE, upright landscape, 147.5 x 70.5 x 7.45 mm nominal |
| Estimated assembled mass | 2.756962 kg from sliced deposition and declared hardware |
| Full-solid reference | 2.936135 kg |
| Production prints | 34 STL types, 76 pieces |
| Fit/fixture plates | 32 objects across three plates |
| Retained PLA / removable support | 1056.06 g / 55.83 g |
| Individual-job time estimate | 105.4 hours; actual batches differ |

The assembled estimate is about 8.4 g above R4. The straight tibia needs more support beneath its raised central shank: about 3.98 g per main part versus 2.61 g in R4. Keep the broad-cheek print orientations. The [slicing report](manufacturing/slicing_r5/output/PRODUCTION_SLICING.md) and [change audit](manufacturing/slicing_r5/R5_CHANGE_AUDIT.md) document deposition, support, bed contact and source hashes.

PLA starting settings: 0.4 mm nozzle, 0.20 mm layers, 0.42 mm lines, five walls, six top/bottom layers and 35% gyroid. Nominal temperatures are 210 C nozzle and 60 C bed, within the filament's range, with an 8 mm3/s flow ceiling. Inspect the machine-specific slice and support removal. The 3MF plates contain geometry, not a printer profile or executable G-code.

Plate 02 contains five selected specimens, not every changed SKU. Use the R5 femur auxiliary cheek and R5 body deck when completing the assembly; their R4 versions are not substitutes. All seven changed SKUs appear in the audit. Preload hip nuts into bare carriers from above and assemble leg modules before mounting them to the body. The new hip cap is not interchangeable with the knee cap.

## Verification and physical limits

The [static check](cad/output/static_interference.json) finds zero intersections in the saved pose. [Full motion](cad/output/full_motion_check.txt) passes nine operating poses, three additional stance samples and thirteen phone-pan samples. It preserves failing 25-degree diagnostics outside the operating range. The [changed-interface check](cad/output/r5_interface_check.txt) covers hip nut entry/seating and deck clearance. The [312-pair scan](cad/output/r5_yaw_dense.txt) checks every integer yaw from -19 to 19 degrees. Minimum recorded clearance is 1.573865 mm against the 1.5 mm target; the nearest listed fixing-hole ligament is 3.747 mm. These are sampled checks, not continuous-motion or loaded-deflection proofs.

Fusion contains 14 link components, 133 closed solids and 13 verified revolute joints. Every joint passed a measured one-degree native motion and neutral restoration. Actual getters confirm the four yaw limits at -19 to +19 degrees. Native interference at neutral is zero, and independent STEP roundtrip and F3D archive checks pass. [Native provenance](cad/output/fusion/tooling_provenance.json) records the exact inputs and outputs.

All 34 production and 32 coupon meshes pass the print-pack checks. The 3MF files reload with 15, 5 and 12 objects. The package checks the CAD, slices, printed mass, simulation, viewer and plate bindings before archiving.

The final 64-second free-base simulation passes standing, one phone turn and one slow crawl cycle, advancing 24.553 mm under the 0.588 N m cap. Half controller stiffness and the full-solid case also pass. Half stiffness with either 0.5-degree or 1-degree feedback half-width fails walking and stance accuracy. R5 is more sensitive in this comparison than R4. These feedback dead zones are uncertainty proxies, not measured mechanical backlash.

The [strength assessment](manufacturing/strength/r5_strength_assessment.md) uses current meshes and the final nominal trajectory. Conditional ordinary-load margins are about 2.70 at the femur root, 1.70 at the tibia root and 1.19 at the post. The centred shank's normal-contact screen has more reserve. The separate one-cheek 5 N lateral bound and post 2g reference remain unmet. Material allowables, actual load sharing, warm creep, damage and fatigue need physical tests. These calculations are not anisotropic FEA or printed-strength qualification.

Start with fit specimens and a complete supported coxa/leg fixture. Record force, lever arm, displacement, twist, residual set and warm behavior before duplicating the leg or attempting loaded walking. Physical fit, servo calibration, thermal endurance and hardware walking have not been demonstrated.

The [existing brain interface and offline R5 preview](references/brain_integration.md) are documented separately. This revision does not deploy the app, change phone networking or command hardware. Use Wi-Fi and the phone battery during unrestricted pan; attach USB only while parked with pan disabled.

## Reproduce

Run `python cad/build.py` with the direct-OCP dependencies in `cad/requirements.txt`. The generator rejects leg-length settings that differ from the selected geometry. Run `python cad/check_full_motion.py`, `python cad/check_r5_interfaces.py` and `python printing/pack_prints.py` after a changed export. Refresh slicing with `manufacturing/slicing_r5/run_production_slices.py`, then run `python printing/build_printed_mass.py` before following [R5_DYNAMICS.md](simulation/R5_DYNAMICS.md). Rebuild software previews with `python software/run_checks.py`.

Fusion helpers use the local MCP adapter and a dedicated R5 runtime namespace. STEP import produces editable BRep solids; it does not recreate Python construction history as Fusion sketches. Refresh dependent reports, previews and checksums together. Earlier R4 and interim R5 files remain outside the current release package.
