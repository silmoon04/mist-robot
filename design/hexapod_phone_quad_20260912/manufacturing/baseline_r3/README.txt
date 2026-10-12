# R3 quadruped with landscape phone: manufacturing revision

This is a new four-leg reconstruction based on [Emre Kalem's hexapod video](https://www.youtube.com/watch?v=ciE2Z_92T7s). It retains the faceted hexagonal body and exposed articulated legs, replaces the original MG996R interfaces with STS3215 C018 case clamps and supplied metal horns, and adds a rotating bare Xiaomi Mi 9 SE in landscape orientation. Earlier MIST geometry was not used.

The creator's MakerWorld download was blocked by the available browser. These are newly constructed solids based on the observed design and manufacturer dimensions, not an edited original STEP file. [Reference evidence and attribution](references/sources.md) records the accessible video, model page and builder feedback.

## Open and print

- Open [the interactive assembly](http://127.0.0.1:8138/review/) to orbit, rotate the phone, inspect the hardware and remove the cover visually. Start it again with `python review/serve.py` from this design directory if needed.
- The full assembly is [Hex_Quad_Phone_assembly.step](cad/output/Hex_Quad_Phone_assembly.step). Per-part STEP and already oriented STLs are under `cad/output/parts_step` and `cad/output/print_stl`.
- Open [quadruped_phone_native.f3d](cad/output/fusion/quadruped_phone_native.f3d) in Fusion for the assembled model with its thirteen working revolute joints.
- Start with [PRINT_FIRST.txt](printing/PRINT_FIRST.txt) and [coupon plate 01](printing/coupon_plate_01.3mf), containing seventeen essential fit and section specimens. [Plate 02](printing/coupon_plate_02.3mf) contains ten optional alternatives. These are geometry-only 3MF files, not machine G-code.
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
| Estimated assembled mass | 2.710 kg from sliced model deposition, the high fastener estimate and 150 g of wiring; physical weighing pending |
| Full-solid comparison | 2.858 kg with every PLA solid filled, using the same hardware |
| Printed parts | 34 named STL types, 76 pieces at the listed quantities |
| Operating yaw range | -22 to +22 degrees, with measured nominal CAD clearance of at least 1.50 mm at the checked endpoints |
| Printer | Neptune 4 Pro; every part fits the nominal build volume in its supplied orientation |

The underside battery tray keeps the pack low. The cover is removable. Board trays use ties and nominal envelopes because actual PCB mounting holes and connector dimensions remain unmeasured. The open phone frame leaves both rear ends and long-edge buttons accessible; the short-edge USB connector is a parked-service connection.

## Printing and strength changes

The manufacturing pass compared 330 orientations and ran CuraEngine on all 34 production types. Broad cheek faces remain the main print surfaces, keeping the long bending fibres within layers. The coxa orientation was flipped for more bed contact, and two electronics trays were flipped to remove their underside supports. The 45-degree femur orientation remains a test option: a low support estimate at a 50-degree threshold became much worse at a 40-degree threshold. It is not an automatic strength or support improvement.

R3 enlarges the narrow leg bridges, removes deep bridge-nut recesses, thickens and ribs the lower yaw connection, staggers its nut slots, and adds modest inward cheek flanges. Sloped ribs support the cover bosses and battery tabs. The phone has reinforced six-millimetre USB spines, short corner clips, a deeper rear top beam and side-loaded cap nuts beneath retained roofs. Rounded deck notches clear the stronger coxa posts.

The [strength report](manufacturing/strength/r3_strength_assessment.md) records beam, net-section, bearing and layer-direction estimates from the actual meshes. Ordinary sampled walking loads give conditional section margins of about 3.19 for the femur and 1.42 for the tibia. The separate conservative lateral-load case remains unresolved near unreinforced regions; the two-leg, 2g post and horn-bearing screens are borderline. These are reasons for the documented fixture tests, not an overall printed-strength approval. Material allowables, warm creep and actual load sharing between bolted cheeks remain unmeasured.

The [Cura report](manufacturing/slicing_r3/output/PRODUCTION_SLICING.md) estimates 1,016.9 g of material retained in the robot, 62.0 g of support and 1.2 g of adhesion material. The approximately 102.5-hour total assumes every piece is printed individually with the conservative settings; real batch and machine times will differ. The 35% infill setting does not mean 35% of solid mass because skins, walls and small features occupy most of these parts.

Use the documented starting profile: 0.4 mm nozzle, 0.20 mm layers, 0.42 mm lines, five walls, six top and bottom layers, 35% gyroid, nominal 210 C nozzle and 60 C bed, with an 8 cubic millimetre per second flow ceiling. Review local supports and actual filament instructions before printing. Supplied analysis toolpaths have their commands disabled and are not a printer release.

## Verification and limits

The [static CAD check](cad/output/static_interference.json) reports no positive-volume intersections above 0.01 cubic millimetres in the assembled pose. The [motion check](cad/output/full_motion_check.json) covers nine full-robot poses, three additional loaded-stance poses, thirteen phone pan angles and twenty-four operating clearance measurements. Nominal endpoint gaps are at least 1.50 mm to the yaw saddle and 2.16 mm to the deck. Local leg checks also include provisional connector volumes. These are sampled checks, not proof of every continuous cable or fastener sweep.

The actual Fusion document contains 14 link components, 120 closed solids and 13 revolute joints. Each joint passed a one-degree native drive with the measured world rotation axis and datum movement checked, followed by restoration to the saved pose. Fusion's native interference query also returned zero intersections. [Native verification](cad/output/fusion/progress.json) and [the API workaround](cad/FUSION_JOINT_API.md) preserve the result and the construction method. Use the supplied manifests for engineering mass and inertia; imported Fusion appearances do not assign measured hardware properties.

All 34 production and 27 coupon STL files passed watertightness, winding, positive-volume and dimension checks. Both coupon 3MF plates reloaded with their expected named objects. The [plate manifest](printing/plate_manifest.json) binds those files to the CAD revision.

The [printed-mass URDF](simulation/output_r3_printed_nominal/quadruped.urdf) uses deposition-derived centres of mass and full inertia tensors transformed into every link. Support material is excluded; fastener masses and positions are modeled separately. The final 64-second free-base simulation passes standing, a complete phone rotation and one slow crawl cycle, advancing about 22.3 mm under the 0.588 N m cap. [The comparison](simulation/output_r3_comparison/case_comparison.txt) records five cases. Half controller stiffness, half stiffness with a 0.5-degree feedback dead zone, and the full-solid mass case pass. Doubling that feedback half-width to one degree fails walking. This is an uncertainty proxy, not a measured mechanical-backlash threshold.

This uses an assumed finite PD and gravity-compensation controller. Mapping that behavior to the real servos remains a commissioning task. No physical walking, thermal endurance, impact strength or complete phone-to-robot control was demonstrated. The screen in the preview is a phone envelope; the existing brain software was not changed or deployed to the phone in this modeling task.

Print and measure the coupons before committing to the full set. In particular, confirm the assembled horn/disc spacing, auxiliary free rotation, clamp contact, M3 engagement and landscape phone retention. Nominal manufacturer dimensions cannot establish the fit of the actual printer, servo lot or screws. Use the same material and orientation between each accepted coupon and its part; qualify structural material and loaded behavior separately.

## Reproduce the files

The CAD generator uses direct OpenCascade through `cad/geom.py`, with new geometry in `body.py`, `leg.py` and `phone.py`. Install `cad/requirements.txt` in a suitable Python environment, then run `python cad/build.py`. The direct OpenCascade path avoids the observed CadQuery process-shutdown failure on this machine.

Run `python printing/pack_prints.py` after a changed CAD export. Recreate slicer properties with `manufacturing/slicing_r3/run_production_slices.py`, then run `python printing/build_printed_mass.py` before repeating the [R3 dynamics cases](simulation/R3_DYNAMICS_PLAN.md). The slicer engine and profile paths describe the tested local Cura installation. Fusion automation uses `cad/fusion_client.py` against the installed local MCP adapter, `fusion_import.py` for the assembly and `fusion_finish.py` for joints and native export. STEP import preserves editable BRep solids; the original Python construction history is not recreated as native Fusion sketch features.

`settings.json` records the design dimensions. `REQUIREMENTS.md` records scope and verification gates. Generated manifests and checksum records must be refreshed together after any geometry change. The delivery archive is for this private build; attribution and source-access limits are retained with the references.
