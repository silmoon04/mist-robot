# Hexapod reference to phone quadruped

Use Emre Kalem's video as the design reference. Earlier MIST work supplies tool-operation lessons and inventory only; its geometry is excluded. The active revision is hex_quad_r4_inward_knee.

## Required result

1. Four articulated legs with the faceted central hexagonal body and open printed leg structure. No wheels.
2. Three direct STS3215 C018 joints per leg, using supplied metal horns and auxiliary discs. No gears or belts.
3. One additional servo rotates a bare Xiaomi Mi 9 SE upright in landscape orientation. Keep screen, camera and side USB access. Wi-Fi and phone battery during unrestricted pan; USB only while parked.
4. Accommodate the owned battery, ESP32, servo-bus adapter and power distribution with removable cover and assembly access.
5. Reviewable source CAD, native Fusion, STEP, oriented STL, fit coupons and PLA printing/assembly instructions for the Neptune 4 Pro.
6. URDF with reconciled mass and inertia, bounded contact simulation, geometric checks and explicit failure cases.
7. Interactive preview and one indexed package whose files match the tested revision.
8. Inward knee servo case, provided the bridge, cable routing, clamping and supported motion remain feasible. Assess actual mass/load trade-offs rather than assuming inward placement reduces every servo load.
9. Use the operator's approximate 35 mm bare-case thickness, 1.5 mm cable addition and 2 to 3 mm cable clearance. A separate combined case-and-shaft gauge must verify the actual interface.

## Verification gates

| Gate | Current digital result | Remaining physical work |
|---|---|---|
| Reference | Visual reconstruction, creator attribution and acquisition limits recorded | Original hexapod CAD was unavailable |
| Servo | Correct midpoint datum, auxiliary-face sockets, supplied accessories and retention stacks | Measure seating, screw entry, clearances and free rotation |
| Geometry | R4 valid solids, zero saved-pose interference, all 62 print/coupon meshes checked | Actual screw/washer stock and print shrinkage |
| Motion | Sampled R4 poses, 360-degree pan and thirteen native joint probes | Flexible harness sweep and real joint calibration |
| Printing | 34 types, 76 pieces; every type sliced and oriented | First-fit prints, measured mass, support removal and layer bonding |
| Fit specimens | Sixteen first-stage and twelve optional pieces on two plates | Feedback remains unmeasured |
| Strength | Actual section calculations and nominal walking-load screen | Complete coxa test at the access opening, side-load sharing, impact, creep and endurance |
| Simulation | Four of five bounded cases pass; largest feedback uncertainty fails | Controller implementation, thermal limits, physical balance and walking |
| Phone software | Existing behavior and connection limits documented; isolated R4 command preview tested | Real landscape phone session, network setup and calibrated robot transport |
| Delivery | Current CAD, native export, slices, URDF, viewer and plates checked against source hashes | No physical print or hardware commissioning performed |

Manufacturer drawings and simulation justify a controlled first-fit prototype, not a guarantee of reliable hardware walking. Print and record the representative coupons first. The nut-window post coupon omits the critical Z=-25 mm access cut; test the complete coxa before loading a leg. Retain failures and distinguish geometric fit, assumed-load calculations and measured physical qualification.
