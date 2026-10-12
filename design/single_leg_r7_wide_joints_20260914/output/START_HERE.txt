# Single leg R7 print set

This release contains one complete three-servo leg and a restrained bench mounting plate: 15 printed pieces on four plates. It preserves the fitted STS3215 C018 pocket, the inward hip and knee cases, and the straight 105 mm lower leg. The coxa is now 82 mm long and its operating range is provisionally widened to -55 to +55 degrees. No new generic coupon plate is required.

Print plate 02 first if you want to check the revised nut insertion on a useful full part before printing the remaining batches. The nuts should enter gently and resist turning. All four plates are required for a complete leg unless you independently confirm that an already printed part is geometrically identical.

| Plate | Contents | Cura estimate | PLA including supports and brim | Profile |
| --- | --- | --- | --- | --- |
| 01_ribbed_mount_and_caps | Ribbed mounting plate, yaw cap and hip cap | 4 h 08 min | 63.9 g | No_Support_R7_PLA_028.curaprofile |
| 02_coxa_and_saddle | Coxa upper bracket and yaw saddle | 3 h 20 min | 55.4 g | Tree_Undersides_R7_PLA_028.curaprofile |
| 03_femur_lower_arm_and_knee_cap | Femur main bracket, lower yaw arm and knee cap | 3 h 35 min | 55.5 g | Tree_Undersides_R7_PLA_028.curaprofile |
| 04_tibia_and_cheeks | Straight tibia, two auxiliary cheeks and four yaw spacers | 3 h 52 min | 53.6 g | Tree_Undersides_R7_PLA_028.curaprofile |

Total estimated PLA is 228 g. Times come from CuraEngine 5.13 with the supplied process settings. Heating, firmware acceleration and actual printer behaviour can change them.

## Open and slice

Select your existing ELEGOO Neptune 4 Pro printer with a 0.4 mm nozzle in Cura. Import the two supplied .curaprofile files through Preferences > Profiles > Import. Open one plate .3mf as models and choose the profile listed in the table. These are geometry plates, not Cura project files: they do not automatically select a profile. Preserve the supplied orientation and 100 percent scale. Each plate also has a combined STL fallback.

The profiles set 0.28 mm layers, five walls, 25 percent gyroid infill, five top and bottom layers, 210 C nozzle and 60 C bed. Outer walls run at 40 mm/s, inner walls and infill at up to 65 mm/s. Bridges run at 15 to 20 mm/s, and overhang walls slow further. Maximum measured nominal deposition flow in these slices stays below 8 mm3/s. Use the filament manufacturer's stated temperature range if 210 C is unsuitable for your PLA.

Plate 01 has supports off. Plates 02 to 04 use build-plate tree supports for exposed undersides, with 2 mm horizontal clearance and a 0.56 mm top gap. That larger separation favours removal and can leave a rougher underside. Do not switch these plates to the old regular-support profile. Check the included support previews against your Cura preview before starting.

The final support check found no support centreline midpoints inside the sampled screw bores and nut seats. Exposed support remains in the open rear-cap screwdriver scallop on the coxa. Remove that accessible support before assembly; it is separate from the enclosed nut seat. Bead edges, bridge sag and removal force still need a physical check.

## What changed after your print

Nut pockets are 5.6 mm across flats with 2.7 mm side-entry slots, based on your approximate 5.2 mm nut flats and 2.2 mm thickness. The 6.1 mm provisional pocket was rejected because your reported 5.8 mm corner width could permit free rotation. Servo case dimensions were not scaled.

M3x30 case screws reach deeper captive-nut seats. The integrated femur and tibia bridges use one M3x30 per fixing into a captive nut, so no M3x50 screws or external 8 mm fixture spacers are needed. The mounting plate uses the M3x18 screws shown in your kit. Four lower-arm counterbores are 8.2 mm diameter to accept your approximately 7.7 mm flat washers. The auxiliary centre openings are 8.4 mm. At the four bench feet, omit the top washers because they would touch the servo clamp; retain one washer under each nut. Screw engagement still assumes 0.5 mm washer thickness; confirm your washers before tightening the short horn screws.

The four yaw spacers are nominally 11.6 mm. Print those from this set rather than mixing the older short fixture spacers into the leg. Follow ASSEMBLY.md for washer counts, disc retention, cable routing and the order of assembly.

## Hip and knee travel

The provisional operating limits are yaw -55 to +55 degrees, hip -30 to +65 degrees, and knee 5 to 115 degrees. This gives 110, 95 and 110 degrees of travel respectively. Hip zero means a horizontal femur; knee zero means the two leg segments are aligned. These are model coordinates, not raw servo commands.

The previous narrow hip/knee limits described the tested walking window. R7 moves the auxiliary cheek outward, thickens it to 5 mm and adds an integral annular stand-off of 4.1 mm. The fork is 4 mm wider overall, and the side plate now clears the plugged servo envelope. A larger cutout around the knee clears the folding tibia and the former rib interference.

Use eight M3x12 screws with two 0.5 mm flat washers each for the hip and knee auxiliary peripheral holes. The annular stand-offs are already part of the printed cheeks. The M3x8 arrangement from R6 is no longer correct. Main horn screws remain M3x6. The bridge nut seats moved so their screws can remain M3x30. Do not mix R6 and R7 fork pieces.

Knee motion was checked to 120 degrees, where the formerly colliding main and auxiliary printed parts each have approximately 1.19 mm clearance. The operating maximum is 115 degrees to leave a five-degree guard. A larger movement range allows more foot positions. Smooth movement still depends on speed and acceleration control, and a walking gait can use a smaller part of the available range.

## Wider coxa motion

The earlier 70 mm coxa was limited to approximately 19 degrees each way by collision with the fixed yaw clamp. The new 82 mm coxa, matching longer lower arm and trimmed mounting plate allow a provisional 55 degrees each way. Do not apply the new limits to the old coxa parts.

The same-pose full-solid comparison estimates 21.3 percent more inertia about the yaw axis. At the same angular acceleration that means more inertial torque, so the change improves reach rather than reducing torque. The 12 mm extension adds 0.012 Nm of bending at the yaw support per newton of vertical toe load. Vertical loading does not directly create torque about an ideal vertical yaw axis.

## Verification and limits

Valid solids, 15 closed oriented STL meshes, complete plate assignments and bed-envelope checks passed. All 39 sampled joint combinations, comprising 27 operating combinations and 12 guard combinations, were free of rigid-part and reserved-connector intersections. Separate hardware-envelope checks passed. Another 63 yaw samples cover -60 to +60 degrees. One-degree hip and knee sweeps at 18 transverse mesh sections also passed. These checks supplement each other; none is a continuous 3D collision proof.

The native Fusion assembly contains three revolute joints with verified axes and a preview of each joint's full operating travel. The URDF has SI units and positive link inertias. Its 36-second suspended-leg test passed broad, eased motion of all three joints, with 0.53 degrees maximum settled tracking error. Gravity torque agreed with an independent potential-energy derivative. The model uses uniform full-solid printed-part masses, declared servo masses and ideal motors, without measured fastener/cable masses.

The beam-section screen remains conditional. The ribbed bench passes the chosen 5 N equivalent-load screen, but the simplified bridge screens remain below the assumed margin. This release is ready to print as a restrained single-leg prototype for unloaded articulation, not a full-body load-qualified walking leg. It does not certify layer adhesion, screw preload, impact survival, motor heating or balance. Start with the bench plate restrained and the toe unloaded, then inspect the bridge roots, post and nut entries.

## Files

plates/ contains four 3MF plates, matching STLs and support previews. print_stl/ contains the 15 individual oriented pieces. parts_step/ and Single_Leg_R7_Assembly.step provide editable solids. fusion/Single_Leg_R7.f3d contains the jointed Fusion assembly. Single_Leg_R7_Motion.mp4 shows native joint movement. Single_Leg_R7.urdf uses the accompanying assembly_mesh/ folder. Keep those together.

The archive includes source CAD scripts and the compatible supplier servo STEP used as a reference. Imported Fusion BRep solids and joints are editable; the original Python construction history is not recreated as Fusion sketches. No machine-ready G-code or hardware actuation is included.

run_motion_test.py can rerun the suspended test from the extracted folder with NumPy and PyBullet installed. It communicates only with the local simulator. The compatibility CSV compares current STLs with the recent 82 mm R6 CAD files; it does not identify your older fixture coupons as reusable automatically.

Cura support-distance interpretation was checked against the official CuraEngine 5.13 TreeSupportSettings implementation: https://github.com/Ultimaker/CuraEngine/blob/5.13.0/include/TreeSupportSettings.h
