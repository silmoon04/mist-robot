# MIST history and available hardware, 6 September 2026

This report reconciles the local MIST files with the relevant Codex conversations. It does not change historical calibration or treat a proposed design as a completed physical test. Paths below are relative to `<LOCAL_HOME>/Downloads/03_Programming_Projects` unless stated otherwise.

## Findings that affect the new design

- The owned joint actuator is the Feetech STS3215, ordered as the 12 V / 30 kg·cm ST-3215-C018 variant. There are 18 in the inventory record, sufficient for 12 leg joints and six spare or experimental units when separate wheel motors are selected. The old 16-installed count assumed an STS3215 at every wheel.
- Existing physical failures already show why fit, assembly access, layer direction and thermal load need explicit treatment. The user had to hammer bearings into the previous leg, and upright printed bearing adapters snapped before removal. An earlier servo cap also failed to contact and preload the case. A powered yaw servo later reached 52 °C and triggered the bench controller's 50 °C cutoff.
- The bearing assortment is identified in the Fusion conversation: 693ZZ, 623ZZ, 685ZZ, 624ZZ, 687ZZ, 627ZZ, 626ZZ and 608ZZ. The current user says about ten of each. The exact count and delivered dimensions remain unmeasured here.
- The user has timing-belt arrangements, gears and heat inserts. Their pitches, lengths, bores and insert dimensions have not been recovered as reliable measurements. Earlier M3/M4 insert coupon dimensions were assumptions.
- The known phone is a Xiaomi Mi 9 SE. Today's request adds a second phone for the face. Its model, envelope, mass, connector position and case are not identified in the inspected records.
- The strongest local visual reference is the original-show contact sheet `misc/mist_face_extraction/sources/misc.png`. The engineering-looking generated pictures contain invented dimensions and are unsuitable as dimensional authority.
- The Candi Coms MIST model showcase is recorded locally. A separate exact July Claude conversation proves that the user exported a real `mist_3d/MIST.stl` from Blender. That STL is now absent, but its original four-view render was recovered losslessly from the transcript; see the mesh-history section below. The connection between the user's STL and Candi Coms' model has not been established.
- The `job-finder/holodeck-mist` generated packages describe fictional evaluation scenarios. They are useful design-review context, but their generated test records and BOM values cannot establish actual inventory or completed physical tests.

## Source priority

1. Current user instructions and actual physical observations in the relevant conversations.
2. Current physical calibration files and received-part observations, with their dates and limits.
3. The July order record for purchased quantities, then the later available-parts summary.
4. Native CAD, print manifests and analysis files for what geometry was prepared. A successful export is not proof of fit or strength.
5. Historical studies and generated illustrations as context. Synthetic Holodeck records remain separate.

`spider-robot/docs/mist/MIST_ACTUAL_INVENTORY.md` records orders placed on 6 July. `MIST_AVAILABLE_PARTS.md` was later condensed for the Holodeck Phase 1 discussion. The condensed file is useful but has stale statements, including an absent bearing inventory and supposedly missing bus cables. The later video audit identified likely bus leads, and August Fusion conversations identify the bearing set.

## Hardware evidence

| Item | Best supported status | Quantity and useful envelope | Design implication or unresolved detail |
|---|---|---|---|
| Feetech STS3215 ST-3215-C018 | Three six-packs ordered; available-parts record says 18 present; C018 cartons visible in physical video; three servos later communicated on the bench | 18 recorded; nominal body 45.2 × 24.7 × 35 mm, approximately 55 g | Design around the 12 V variant. The project distinguishes 10 kg·cm rated torque from 30 kg·cm peak stall. Measure ears, horn, auxiliary shaft, body, cables and actual lot before manufacturing interfaces. |
| Wheel motors | Existing architecture used four STS3215s; separate fast lightweight motors are a new design request | None of the requested approximately £15 wheel motors is confirmed purchased | Any selected external wheel motor is an additional purchase, with driver and encoder needs accounted for. |
| FE-URT adapter | Ordered FE-URT-1, physical adapter visible; later user called their bench adapter FE-URT-2 | One recorded | Read the actual PCB label before freezing its mounting. This is primarily bench equipment. |
| Bus Servo Adapter A | Ordered and visibly identified in July video | One | The 5 A board limit in the project documentation is not a full-leg power-distribution rating. |
| ESP32 DevKitC / WROOM-32 CP2102 Type-C | Ordered; DevKit visible in July video | One recorded | Separate from the ESP32-CAM, which is also visible. Breakout envelope and USB access need measurement. |
| Xiaomi Mi 9 SE | Assigned phone; sensor streaming previously exercised | Nominal 147.5 × 70.5 × 7.45 mm, 155 g | Case, retention, connector and camera clearance are additional. No identified dimensions for the second face phone. |
| VL53L0X | Ordered | One | Breakout size, orientation and wiring route unmeasured here. |
| HOOVO LiPo | Two-pack ordered; available-parts record says both present; one visible in video | Two 3S / 11.1 V nominal / 2200 mAh / XT60 packs; nominal envelope 104 × 34.5 × 24.5 mm and 174 g per pack | Earlier mass model installs one pack at a time. These are nominal reference dimensions rather than this audit's measurements. |
| SKYRC B6Neo | Ordered and physically seen powered | One | Bench charger, excluded from moving robot mass. A video audit accidentally called it ISDT; the order/manual identity is SKYRC B6Neo. |
| Anker 317 PD supply and 5 A cable | Recorded as already owned | 100 W supply | Bench charger supply, excluded from moving mass. |
| XT60-to-eight-XT30 PDB | Ordered; matching distribution board visible | One | Seller current claim is not a verified continuous harness capability. |
| XT90-S anti-spark lead | Ordered | One | Envelope, bend radius, strain relief and reachable disconnect access need accounting. |
| 5 V / 5 A UBEC-like modules | Order option implies four; four matching boards visible | Approximately four | Exact output setting and loaded capability require electrical verification. |
| 4700 µF / 25 V capacitors | Ordered | Ten | Earlier plan placed capacitors near leg roots; include dimensions and lead protection. |
| XT30 pigtails | Ordered | Ten male/female pairs | Length and wire gauge require direct confirmation. |
| XT60 pigtails | Ordered; visibly present | Five male/female pairs | Include installed harness mass, not all spare stock. |
| Fuse holders and blade fuses | Ordered; visibly present | Five holders plus assortment | Current values and matching blade format need checking. Existing 30 A / 15 A notes are an earlier architecture, not automatically the new motor system's release values. |
| Feetech 5264 three-pin bus leads | Three packs of six ordered; July video shows likely candidates in a white tray at approximately 34 s | Intended eighteen | Candidate housing fit, pin order and cable length require confirmation. Generic PWM leads are separately present and do not establish compatibility. |
| Silicone wire, heat shrink, braid and ties | Order and video evidence | Stock exists; detailed lengths/gauges unverified | Earlier claim that all silicone wire was missing is stale; video shows coils. |
| 80-piece bearing assortment | User purchase statement in August Fusion thread; current user reports about ten per size | Eight codes below | A title saying '6 Sizes' conflicts with its eight listed codes. Use the codes, then physically count. |
| Heat inserts | User says owned; prior coupon work discussed M3/M4 | Actual insert types unmeasured | Old assumed M3 4.6 × 5.7 mm and M4 5.6 × 8 mm dimensions must not become final CAD without identification. |
| Belts, pulleys and gears | Current user says several setups are available | Types and quantities unknown | Pitch, width, tooth count, closed/open belt length and pulley bores are open fields. |
| Screws, washers and nuts | Small machine-screw and washer organisers visible; old notes use M3×12 with plain nuts and washers | Useful count by size not frozen | July inventory alone does not prove every required M3 length, nut, shoulder pin or retainer is present. |
| Printer | Elegoo Neptune 4 Pro recorded as owned and used for actual coupons | Approximately 225 × 225 × 265 mm; earlier packed releases used a conservative 215 mm XY area | Preserve the real print orientation and process when transferring fit evidence. |
| Materials | About 3 kg PLA owned; white Creality PETG 1 kg and black JAYO TPU 95A 0.5 kg ordered | Remaining stock unknown | Old PLA results do not qualify PETG fit or loaded structural behavior. |
| Tools | Soldering iron, calipers, scales, wire tools and multimeter recorded and/or visible | One of each principal tool | July multimeter battery was missing; current readiness has not been checked here. |

The original order IDs and private account details remain in the existing order evidence and are intentionally not duplicated in this design report.

### Bearing assortment

The nominal dimensions below come from the existing first-party lookup recorded in `fusion360/docs/BEARING_KIT_STANDARD_DIMENSIONS.md`. They are boundary dimensions for the bearing codes, not measurements of the user's inexpensive assortment.

| Marking | ID × OD × width, mm | Current quantity evidence |
|---|---|---|
| 693ZZ | 3 × 8 × 4 | Approximately ten, per current user description |
| 623ZZ | 3 × 10 × 4 | Approximately ten |
| 685ZZ | 5 × 11 × 5 | Approximately ten |
| 624ZZ | 4 × 13 × 5 | Approximately ten; this size was previously fitted into the printed leg |
| 687ZZ | 7 × 14 × 5 | Approximately ten |
| 627ZZ | 7 × 22 × 7 | Approximately ten |
| 626ZZ | 6 × 19 × 6 | Approximately ten |
| 608ZZ | 8 × 22 × 7 | Approximately ten |

## Physical fit and movement history

The following points were recovered from **Inspect Fusion360 MCP (4)** and **Inspect Fusion360 MCP (5)**, with supporting local release files.

1. The first compact coupon used 0.30 mm PLA layers, five walls and 30% cubic infill. The user reported that only the largest bearing housing fitted tightly and the middle inner post fitted. The assistant interpreted those stations as 13.25 mm housing and 3.90 mm upright post for a 624ZZ bearing. The user's station report is direct evidence; the bearing-family/station interpretation was initially conditional.
2. The user had not tried the heat inserts at that point. No successful insert diameter can be inferred from the bearing result.
3. The compact bearing rings were only 3 mm thick. The later full-leg design used a short 13.25 mm contact band, 13.45 mm relief and a 5.2 mm pocket. The user nevertheless needed a hammer to fit bearings into the printed arms. This is direct evidence that a thin-ring coupon did not fully predict the production boss.
4. Printed upright inner-race adapters broke before removal. The subsequent design changed to headless, horizontal, twelve-sided adapters. This revision addresses orientation, but does not provide measured strength or fatigue evidence.
5. Later prepared geometry enlarged the bearing seat to 13.40 mm and pocket relief to 13.55 mm. These revised values were prepared after the failure; the inspected conversation does not establish a successful subsequent fit of those revised seats.
6. The user had already assembled the original printed arms and requested that they not be reprinted. The final adapter-only release therefore used 4.10 mm linkage plugs for those existing arms. The 5.10 mm plug belonged to a separate v2 arm/socket revision. These interfaces are incompatible without the matching arm revision.
7. The remote-knee geometry was 40 mm driver, 110 mm coupler, 40 mm follower, 110 mm femur and 70 mm tibia. The reference arrangement has femur and coupler horizontal, driver/follower upward and tibia downward. Logical reference angles are q1 = 0°, q2 = +90°, q3 = −90°.
8. The historical Fusion sweep covered relative linkage input −30° to +40°. The bench controller added a 5° margin, giving −25° to +35°, equivalent to relative knee q3 of −115° to −55°. These are limits of that old mechanism, not whole-robot stair capability.
9. The user reported inverted hip motion and very slow drag response. The latest inspected controller history corrected the hip sign to −1, then offered up to approximately 158°/s from a 30 Hz update loop and 60 ticks per cycle. This is a command-rate limit, not a measurement of loaded mechanical speed.
10. The same latest thread records yaw ID 1 at 52 °C, tripping the 50 °C controller cutoff, then cooling to 33 °C. It is evidence of a real thermal limitation during commissioning. It does not identify the root cause or prove that a gear ratio alone resolves it.

Relevant prepared releases include:

- `fusion360/bearing_heatset_calibration_kit_compact_v2/`, including the 192.8 × 195.15 mm full compact plate and first 624ZZ/M4 subset.
- `fusion360/coupon.curaprofile`, the process attached to the reported coupon result.
- `fusion360/remote_knee_624zz_test_leg_v1/`, the arm revision the user printed and hammer-fitted.
- `fusion360/remote_knee_624zz_test_leg_v2/`, the later enlarged-seat proposal.
- `fusion360/remote_knee_624zz_fixture_adapter_plate_v3/PRINT_THIS_ADAPTERS_COXA_CARRIAGE_N4PRO.3mf`, the five-object adapter/carriage/coxa release for the existing arms.
- `fusion360/REV_F_DESIGN.md`, which documents an earlier 0.75 mm cap-to-servo gap, false clamp preload, axial location problems and layer-loaded nut-pocket roofs.
- `fusion360/TEST_KIT.md`, whose 5 August status holds the old Stage-2 kit because of remaining collisions, wrong cradle print orientation and an absent bench-mount interface. Its older headline 'print these' must not override that hold status.

### Current stored calibration

Read on 6 September from `spider-robot/bench/leg_calibration.json`; unchanged by this audit.

| Role | ID | Reference tick | Direction | Raw endpoints | Reference angle |
|---|---:|---:|---:|---|---:|
| Hip roll/coxa | 1 | 3075 | +1 | 2179 to 4082 | 0° |
| Hip pitch | 2 | 1386 | −1 | 717 to 2091 | +90° |
| Remote knee driver | 3 | 2085 | +1 | 1531 to 2493 | 0° absolute driver |

This file retains 32 mm hip offset, 110 mm femur and 70 mm tibia. Earlier thread observations of ticks 3052 / 1312 / 2143 are superseded by this stored calibration. `REV_F_DESIGN.md` separately retained a 42 mm offset, so old mechanical and kinematic revisions need reconciliation before reuse. None of these stored ticks should be copied into a rebuilt mechanism without calibration.

## Visual reference and mesh provenance

The following files exist and were inspected or indexed:

- `misc/mist_face_extraction/sources/misc.png`: visually inspected original-show contact sheet, with full-body and close-up views. This is the most useful recovered reference for the overall identity.
- Other source sheets in the same folder: `angry.png`, `annoyed.png`, `happy.png`, `misc_2.png`, `neutral.png`, `neutral_2.png`, `sad.png`. `reports/sources.json` records their dimensions and hashes.
- `misc/mist_face_extraction/reports/face_contact_sheet.png`, extracted screens and recreation recipes: useful face and expression history.
- `spider-robot/brain/face_assets/`: the current reusable face assets.
- `spider-robot/mist_3d/images/` and `mist_fusion_guide/`: generated instructional illustrations. The viewed `fe804363-f90c-4404-9761-6218dc9ec42b.png` labels a 280 mm body and 432 mm overall height. Those numbers conflict with other design revisions and are not measured source dimensions.
- `misc/Pantheon - MIST 3D model [NuraXFVdfVg].info.json`: metadata for [Candi Coms' MIST model showcase](https://www.youtube.com/watch?v=NuraXFVdfVg), uploaded 12 November 2024, duration 20 seconds. The description identifies a Maya hard-surface recreation of M.I.S.T from Pantheon season two.

The visually observed identity is a white cylindrical upper body, a stepped double-rim lid and carry handle, a dark grey lower drum, a black cyan-expression screen projecting from the front at the white/grey boundary, a smaller black horizontal panel below it, four angular light-grey leg covers, dark circular joints and narrow dark wheels. The lid, cylinder proportions, face placement, colour break and angular legs all matter to recognition; the source images do not establish hidden structure or physical dimensions.

A hidden/no-ignore file search of `spider-robot/mist_3d` and `misc` did not locate OBJ, GLB, FBX, BLEND, F3D or STEP model files. A broader filename search under Downloads also found no MIST/Pantheon-named mesh or model/video archive; two unrelated inaccessible temporary directories were skipped by the filesystem. The result is 'mesh not located', not proof that one never existed or that the artist supplied a downloadable model.

### Recovered original mesh history

An exact follow-up lookup found the original user-provided model in Claude session `d00a2645-7795-4a31-ad22-5b663c455d51`, stored at `<LOCAL_HOME>/.claude/projects/C--Users-hssil-Downloads-03-Programming-Projects-spider-robot/d00a2645-7795-4a31-ad22-5b663c455d51.jsonl`.

- Line 204, 6 July 2026 at 13:46:42 UTC: the user states they exported `mist_3d/MIST.stl` from a Blender file.
- Line 208: a real directory listing records `MIST.stl`, 786,384 bytes, modified 6 July at 14:42 BST.
- Line 218: the mesh analysis records 8,198 vertices, 15,726 faces, 108 connected components, a 2.56 × 3.48 × 3.65 model-unit bounding box and `watertight=False`. These are historical model coordinates, not physical millimetres. The later ×100 scaling was an assumption.
- Line 226 preserves the original mesh's four-view PNG as embedded image data. It was decoded without editing to [original_mesh_four_views.png](references/original_mesh_four_views.png): 342,740 bytes, SHA-256 `8efcfecc2ef0de3a4f8614e21266ccdc534ebea53f4641f65b92e64b4a93d24f`.

The old temporary `mist_views.png` no longer exists. The recovered PNG supplies visual evidence of the original mesh, not recoverable triangle coordinates or manufacturable solids. No actual Blender filename/path or deletion notice appeared in that exact session. `MIST.blend` elsewhere in the session is only an illustrative assistant command. The original STL's association with the Candi Coms showcase remains unproven.

## Relevant conversations

Titles below are those returned by Codex's thread reader for the read conversations, and the local session index for the earlier indexed conversations.

| Thread title | Thread ID | Evidence used |
|---|---|---|
| Inspect Fusion360 MCP (5) | `01a035b5-eddd-7010-9284-a12881cbd366` | Connected three-servo leg, reference pose, calibration, corrected hip direction, command response and 52 °C yaw event, August 2026 |
| Inspect Fusion360 MCP (4) | `01a024ed-ba8b-7f71-abb5-4a7123d48d22` | Bearing purchase, coupon feedback, hammer fit, broken vertical adapters, v1/v2/v3 interface distinction, August 2026 |
| Analyze parts and HTML guides | `019fb016-4e77-7590-9a14-46115bce263b` | July physical-video audit, likely rediscovered 5264 cables and corrected photographic component boards |
| Find a suitable project task | `01a0456e-74d2-7900-939d-83d870559b52` | MIST Holodeck Phase 1, creation of the concise available-parts inventory, inventory and design-document mismatch discussion |
| Find Holodeck Phase 1 chat | `01a05933-163a-71f2-bd0e-673c07b7c652` | Identified the preceding Phase 1 thread and distinguished it from the later task |
| Inspect Fusion360 MCP (3) | `019fe819-7644-7a53-ad31-2c721dda4df2` | Indexed earlier Fusion history; not used as new physical evidence in this audit |
| Inspect Fusion360 MCP (2) | `019fc98d-3904-7043-b882-72555a2c26b7` | Indexed earlier Fusion history; not used as new physical evidence in this audit |
| Inspect Fusion360 MCP | `019f8991-ba83-71e0-afd0-b2c6a277f1de` | Indexed original Fusion task |
| Polish Fusion 360 guide | `019f56c7-03ff-7b81-85af-a12e46c6f100` | Indexed generated visual-guide work |
| Continue GPT fusion guide | `019f58c8-0fe1-7e40-9c42-06a428996192` | Indexed continuation of guide work |

The older thread IDs were recovered with read-only queries to the local Codex session index and thread database, then read through the app where available. Search terms were restricted to the requested projects and MIST/Fusion context. No account messages, purchases or external communications were sent.

## Useful existing software and evidence

- `spider-robot/brain/` contains the agent, voice, expression and robot-tool starting point.
- `spider-robot/bench/` contains the physical servo bench, calibration page, stored calibration and kinematic tests. It is a separate interface from the visual simulator.
- `spider-robot/sim/` contains the previous browser simulator, statics, power, actuator-layout and gait calculations. Its predictions are historical analysis rather than completed physical validation.
- `spider-robot/tools/sensors/README.md` records Mi 9 SE IMU/magnetometer streaming on 30 June: 148 messages over six seconds. It does not establish current online status or latency with the new brain.
- `spider-robot/docs/mist/order-verified-guides/work/video_frames/VIDEO_COMPONENT_AUDIT.md` indexes photographed hardware from a 53.9-second 8K video. It explicitly distinguishes visible presence from exact count, electrical rating, pinout and working condition.
- `job-finder/holodeck-mist/PROGRAMME_MAP.md` provides a useful decomposition of representative-leg release, print qualification, whole-robot integration, control, perception and learning work. Its generated `dist/` scenarios remain synthetic.

No applicable `AGENTS.md` was found in the three project roots or the inspected MIST directories. The checked `spider-robot` folder was not a Git checkout, so no historical mesh could be recovered from local Git history there. This audit created this report and, after a specific follow-up request, the losslessly recovered original-mesh PNG. The later assembly plan is a separate integration deliverable.
