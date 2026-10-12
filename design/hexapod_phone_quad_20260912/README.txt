# R4 quadruped with an upright landscape phone

This is a new four-leg reconstruction based on [Emre Kalem's hexapod video](https://www.youtube.com/watch?v=ciE2Z_92T7s). It retains the faceted hexagonal body and open articulated legs, uses thirteen STS3215 C018 servos, and carries a bare Xiaomi Mi 9 SE upright in landscape orientation. The knee servo cases now point inward between the femur cheeks. Earlier MIST geometry was not used.

The creator's MakerWorld download was blocked by the available browser. No original hexapod STEP was acquired. These are newly constructed solids based on the video and manufacturer interfaces. An official Waveshare servo STEP was acquired and checked against the C018 drawing; its small dimensional differences are recorded. [Sources and attribution](references/sources.md) and [the hardware contract](references/hardware_contract.md) explain the evidence.

## Open the design

- [Interactive assembly](http://127.0.0.1:8138/review/): orbit, pan the phone, hide the cover or hardware, and inspect the leg stance. Restart it with `python review/serve.py` from this design directory.
- [Native Fusion assembly](cad/output/fusion/quadruped_phone_native.f3d): fourteen links and thirteen verified revolute joints.
- [Assembly STEP](cad/output/Hex_Quad_Phone_assembly.step), with separate editable solids. Part STEP files and oriented print STLs are under `cad/output/parts_step` and `cad/output/print_stl`.
- [Print-first guide](printing/PRINT_FIRST.txt), [essential coupon plate](printing/coupon_plate_01.3mf) and [optional alternatives](printing/coupon_plate_02.3mf). The plates contain sixteen and twelve pieces respectively. They are geometry-only 3MF files.
- [Assembly guide](printing/PRINT_AND_ASSEMBLE.md), [fastener stacks](printing/R4_FASTENER_STACKS.md), [manufacturing BOM](printing/manufacturing_bom.csv) and [measurement sheet](printing/coupon_feedback.csv).
- [Printed-mass URDF](simulation/output_r4_printed_nominal/quadruped.urdf), [recorded simulation](simulation/output_r4_printed_nominal/recorded_motion_6x.mp4) and [five-case comparison](simulation/output_r4_comparison/case_comparison.txt).

![R4 inward-knee quadruped](review/hero.png)

## Dimensions and arrangement

| Item | R4 design |
|---|---|
| Servos | Twelve leg joints plus one fixed phone-pan servo |
| Leg lengths | 50 mm coxa, 90 mm femur, 105 mm tibia |
| Transmission | Supplied metal horns and auxiliary discs; no gears, belts or wheels |
| Phone | Bare Mi 9 SE, 147.5 mm across, 70.5 mm high, 7.45 mm nominal thickness |
| Saved assembly envelope | 345.51 x 345.51 x 310.22 mm |
| Estimated assembled mass | 2.74854 kg from sliced PLA, nominal hardware, conservative fastener masses and 150 g wiring allowance |
| Full-solid reference | 2.91145 kg with the same hardware |
| Printed production parts | 34 STL types, 76 pieces |
| Fit and section specimens | 28 pieces, with 16 selected for the first stage |
| Operating yaw limit | -22 to +22 degrees; sampled walking checks use hip 16 to 34 and knee 70 to 91 degrees |
| Printer | Neptune 4 Pro, nominal 225 x 225 x 265 mm volume |

The battery sits beneath the body. The removable cover and tied electronics trays leave access to the internal wiring. The PDB tray is turned 45 degrees to clear the corrected clamps. Board envelopes, actual screw stock and connector extraction space still require measurements on the owned components.

The phone remains upright while its pan axis rotates. Its servo case and cable remain fixed on the chassis. Use the phone's battery and Wi-Fi during unrestricted pan; park and disable pan before connecting its side USB port. No slip ring is included. The preview screen represents the phone envelope, not the running brain application.

## Why the knee points inward

The case can fit inward once the femur cross-bridge is moved above it and the auxiliary-side cheek has the correct cable opening. This gives a more compact outline and brings the servo's mass closer to the hip. It reduces the servo's contribution to swing inertia and unsupported-leg holding torque.

It does not guarantee lower hip torque while standing. Servo weight can partly oppose the upward foot reaction, so moving that weight inward can slightly increase loaded hip holding torque. The isolated case reversal changes its gravity moment by about 0.0117 N m at a 30-degree hip angle. [The comparison](manufacturing/knee_inward_study/mass_tradeoff.md) states its frozen baseline and unmeasured internal-COM assumption. R4's complete mass and dynamics were recalculated separately; the bracket and datum corrections add about 39 g to the assembled estimate compared with R3.

Two earlier interface interpretations were corrected during this review. The shaft is 12.5 mm from the case midpoint, not from the short end. The sockets face the auxiliary shaft side. R4 also corrects auxiliary-disc spacing, standoff lands and retaining-washer access. The combined case-to-shaft fixture checks these datums together so the earlier 2.385 mm offset cannot pass unnoticed.

The cable pocket uses the operator's approximate 35 mm case profile, 1.5 mm plugged-lead addition and 2 mm additional clearance. These are provisional clearances; inspect the actual plugged servo and wire sweep. Install captive clamp nuts before adding the surrounding leg cheeks. Some hip nuts cannot be inserted or held with the tested tool while the complete leg is assembled.

## Printing and assembly

The [R4 slicing report](manufacturing/slicing_r4/output/PRODUCTION_SLICING.md) covers every production type. Model PLA totals 1047.64 g, removable support 50.96 g and adhesion 1.16 g. The conservative individual-piece estimate totals 104.1 hours; packed plates and the actual printer will differ. R4 uses about 18% less support than R3 while adding about 31 g of deposited PLA.

Use the supplied orientations: broad cheek faces on the bed keep the main longitudinal bending direction within layers. The coxa orientation provides a larger contact face; the PDB and UBEC trays print flipped. A blanket 45-degree rotation is not beneficial. The earlier orientation comparison showed that its support demand changes sharply with support threshold. Prefer the checked orientation and inspect support inside clamp recesses before printing.

Starting PLA profile: 0.4 mm nozzle, 0.20 mm layers, 0.42 mm lines, five walls, six top and bottom layers, 35% gyroid, nominal 210 C nozzle and 60 C bed, and an 8 cubic millimetre per second flow ceiling. Follow the filament's temperature range and calibrate flow. Support separation and local orientation notes are in the assembly guide. Infill percentage is not a mass or strength multiplier.

The first plate includes fit fixtures and three section specimens required before loading. Assemble the real case, supplied horn and auxiliary disc in the registration fixture; check seating, clamp contact, screw engagement and free auxiliary rotation. The auxiliary peripheral stacks use M3x8 with two thin washers on pitch joints and M3x20 with two washers on the lower yaw arm. Exact lengths, washer diameters and assembly order are in the stack guide.

The cropped nut-window post coupon does not include the critical clamp-access opening at Z=-25 mm. Its result cannot qualify that opening. Test a complete production coxa with both yaw arms and the real fastening arrangement before loading a leg. Continue with the supported single-leg and dummy-phone tests in the guide before committing to all seventy-six production pieces.

## Verification and limits

[Static CAD verification](cad/output/static_interference.json) finds no solid intersections above 0.01 cubic millimetres in the saved pose. [Full-assembly motion checks](cad/output/full_motion_check.json) record discrete poses and clearances. The minimum checked operating coxa gap is 2.16 mm. The [staged leg assembly check](cad/output/r4_leg_staged_assembly_check.txt) passes the preloaded-nut procedure and corrected screw/driver stack; the [strict service-access diagnostic](cad/output/r4_leg_interface_check.txt) retains its seven obstructed tool/part pairs. The [phone check](cad/output/r4_phone_check.txt) covers twenty-four pan angles and its required screw-before-hub assembly order. Cable proxies remain provisional; these are not continuous flexible-cable proofs.

The Fusion document contains 14 link components, 133 closed solids and 13 revolute joints. Every joint passed a measured one-degree native drive in the expected world direction, followed by pose restoration. Native interference is zero in the checked pose. The exported STEP independently reloads with 133 solids and approximately 0.00027% volume difference. [Native evidence](cad/output/fusion/native_report.json) and [the API note](cad/FUSION_JOINT_API.md) preserve the checks. Use the manifests for engineering masses and inertia; Fusion appearances are not measured material assignments.

All 34 production and 28 coupon meshes passed the print-pack checks. Both coupon 3MF files reload with the expected object counts. The plate manifest, sliced properties, printed mass model, simulations and native geometry are checked against the current CAD hashes.

The 64-second nominal free-base simulation passes standing, a full phone turn and one slow crawl cycle, advancing 22.24 mm under the 0.588 N m torque cap. Half stiffness, half stiffness with a 0.5-degree feedback half-width, and the full-solid case also pass. Half stiffness with a one-degree feedback half-width fails walking and stance accuracy. This feedback proxy is not measured mechanical backlash. The static torque screen peaks at 0.5484 N m for printed mass and 0.5804 N m for the full-solid case, leaving little reserve in the latter.

The [R4 strength assessment](manufacturing/strength/r4_strength_assessment.md) uses actual mesh sections and declared PLA assumptions, not anisotropic FEA or printed test results. Sampled nominal walking gives conditional femur/tibia section margins of about 3.19/1.35. The post's vertical-load-only screen passes, but assigning all hip reaction torque to its lower section does not. The direct upper saddle path means actual load sharing remains unresolved. A separate 5 N one-cheek lateral bound and the 2g shock screens are not satisfied throughout the design. Those results require fixture testing and may require further reinforcement after measured deflection or damage.

No physical fit, thermal endurance, impact strength or hardware walking was demonstrated. The simulator assumes rigid links, specified friction and an uncalibrated finite PD/gravity-compensation controller. Mapping that behavior to real STS3215 control remains a commissioning task.

[Brain integration](references/brain_integration.md) records what the existing app actually supports. The existing voice/animation app, phone network access and thirteen-servo controller are not an end-to-end demonstrated system. The isolated software preview uses the R4 manifest and proposed IDs, has no servo transport, and rejects hardware mode. No existing app was deployed or hardware reconfigured. Follow [wiring and commissioning](printing/WIRING.md) before any powered work.

## Reproduce and revise

The generator uses direct OpenCascade through `cad/geom.py`, new geometry in `body.py`, `leg.py` and `phone.py`, the canonical `servo_contract.py` and `fit_coupons.py`. Install `cad/requirements.txt`, then run `python cad/build.py`. Repack with `python printing/pack_prints.py`, run `manufacturing/slicing_r4/run_production_slices.py`, then `python printing/build_printed_mass.py` before repeating the R4 dynamics cases. The supplied slicer scripts record the tested local engine and profile paths.

Fusion automation uses `cad/fusion_client.py` with the local MCP adapter, `fusion_import.py` for a new assembly and `fusion_finish.py` for joints and export. `fusion_present.py` removes construction glyphs for presentation. Imported BRep solids are editable; the Python construction sequence is not recreated as a Fusion sketch history.

`settings.json` records dimensions and `REQUIREMENTS.md` records the verification gates. Refresh all dependent reports and checksum records after a geometry change. The archive contains the current candidate and selected evidence; obsolete R2/R3 prints remain only in the workspace baseline folders. Keep attribution with the files and do not treat this private-build package as permission to redistribute the creator's design.
