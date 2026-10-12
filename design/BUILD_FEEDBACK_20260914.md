# Physical feedback and next build decision

## Latest operator report

The operator printed and assembled the latest M3x30 bridge fixture. The hexagonal nuts could not be inserted normally and were driven into place using a screwdriver and hammer. The resulting assembly is reported as fixed and working.

Record this as successful assembly after forced nut insertion, not as an acceptable nut-pocket fit. Nut width, thickness, insertion force and any hidden damage are unmeasured. No powered sweep, applied load, operating temperature or endurance result was reported in this message. Do not infer those results from the word working.

Earlier feedback established that the STS3215 case pocket fitted well and that the assembled case clamp held the servo firmly. The operator reused the earlier flat cap, whose nominal geometry was unchanged. Some sanding was required; its exact location and cause remain unresolved. The case pocket and screw axes should be preserved unless new measurements contradict them.

## Next stage

Proceed to one complete three-servo leg on a rigid, restrained mounting plate. Use real production parts as the next test article rather than repeating the broad fit-coupon sequence. A small mounting plate can exercise the yaw saddle, fasteners and load path without committing to the complete body shell and phone assembly.

The existing downloadable R5 production leg is not yet the correct next print release. Inspection on 14 September found:

- The production fastener guide still specifies M3x50 femur/tibia bridge screws and M3x35 case-clamp screws.
- The M3x30 opposed-screw bridge is a separate fixture adaptation, not a completed redesign of the load-bearing femur and tibia connections.
- The successful support-free saddle roof geometry is a separate print trial; it has not been propagated to every production clamp and mounting orientation.
- Nut slots in the M3x30 fixture were nominally 2.6 mm thick with 5.7 mm across-flat geometry. The report of hammering does not establish which direction lacked clearance. Both entry and seated fit require review.

Before releasing the single-leg print set, consolidate the support-free hole treatment, accessible nut pockets and hardware limited to the available lengths. Preserve locating flats and adequate material around enlarged pockets. Check fastener seating, tip clearance, tool access, valid solids, print orientation, part clearances and the full leg range on the final geometry.

Do not directly transplant the small fixture's two-screw bridge into a loaded production link without checking its new load path and clearances. Do not globally scale the robot or all bores to compensate for the nut pockets. Measuring one actual nut across flats and through its thickness would help target the correction without another coupon plate.

## Testing the complete leg

1. Assemble the leg without hammering or forcing captive nuts. Check screw lengths, washer stacks, cable routing and auxiliary-disc freedom before joining the powered side.
2. Secure the mounting plate, support the leg and verify joint IDs, direction and limits one joint at a time with conservative motion. Do not use old mechanism calibration without checking it against the direct-drive leg.
3. Run a slow unloaded sequence through the intended working range while checking contact, cable strain and binding.
4. Apply measured load in stages with the leg restrained. Observe deflection, clamp slip, nut retention and temperature before increasing duration or load. Record the printed process and actual mass.
5. After that leg passes, print the main deck and duplicate the accepted leg parts. The full body cover and rotating phone mount can follow after the mechanical and electrical installation is confirmed.

The hammered fixture need not be dismantled destructively just for inspection, but it should not be treated as the structural reference for loading. Examine it for whitening, cracks, split layers or bowed walls. Replace its affected printed piece if damage or binding is apparent. The absence of visible cracks does not establish a measured load capacity.

The earlier nominal simulation and section calculations support proceeding to a controlled prototype. They do not establish printed strength, servo thermal endurance or reliable hardware walking. In particular, the R5 post had a conditional ordinary-load margin of about 1.19, and separate lateral/shock screens remained unresolved. The fit-only low-infill profiles do not automatically qualify the load-bearing leg's material/process.

## Source records checked

- `hexapod_phone_quad_r5_20260912/printing/R5_FASTENER_STACKS.md`
- `hexapod_phone_quad_r5_20260912/manufacturing/strength/r5_strength_assessment.md`
- `hexapod_phone_quad_r5_20260912/cad/hip_revision.py`
- `fusion_fixture_m30_20260914/build_fixture.py`

This note records the next-stage decision. It does not claim that a consolidated single-leg print package has already been generated.

## R6 single-leg print release

The operator's screw kit lists M3x4, x6, x8, x10, x12, x18, x20 and x30 socket screws. The longest measured approximately 32.5 mm overall with a 2.5 mm head, consistent with M3x30 under the head. Reported nuts measure approximately 5.2 mm across flats, 5.8 mm across corners and 2.2 mm thick. Treat these as approximate measurements.

Released design/single_leg_r6_20260914: one complete three-servo leg plus a bench mounting plate, 15 printable pieces on four plates. New captive pockets are 5.6 mm AF; side-entry slots are 2.7 mm thick. Case screws and integrated bridge screws use M3x30. Bench fixings use M3x18. Lower yaw arm counterbores were enlarged to 7.4 mm to accept washers up to OD7. Washer thickness is still unconfirmed; horn screw stacks assume 0.5 mm flat washers.

All 27 sampled poses passed rigid-part and provisional connector clearance checks. The final counterbore enlargement was verified as a strict subtraction from the checked lower arm, and new washer/head/shaft envelopes passed local checks. Native Fusion contains three verified revolute joints. The suspended URDF test passed; it does not validate walking, real servo heating or printed strength. A conditional net-section screen fails the conservative 5 N case at some bridges and bench rails, so begin with restrained unloaded articulation only.

Final settings: 0.28 mm, five walls, 25 percent gyroid. Four engine estimates: approximately 4 h 25 min, 3 h 16 min, 3 h 03 min and 3 h 44 min; total approximately 221 g PLA. Plates 02 to 04 use build-plate tree support, 2 mm XY distance and 0.56 mm top gap. The tested critical nut seats and screw bores contain no sampled support centre lines; exposed support in the rear-cap driver scallop must be removed. The larger gap may leave rougher undersides. Physical fit, bridge quality and support release remain to be observed.

## Active release: R7 wide joints

R7 supersedes the R6 print candidates after the operator requested more hip and knee travel. Active files are in design/single_leg_r7_wide_joints_20260914. The new operating limits are yaw -55..55, hip -30..65 and knee 5..115 degrees. Model lengths are 82/90/105 mm. The knee was checked at 120 degrees and the formerly colliding printed pieces each have approximately 1.19 mm clearance there. The 115-degree operating maximum leaves a five-degree guard. Limits are model angles, not calibrated physical servo commands.

The auxiliary cheeks are now 5 mm thick, with inner face Y=-22 and outer face Y=-27. Their integral OD19.8 annular stand-offs are 4.1 mm long and have an 8.4 mm central opening. Use M3x12 screws and two 0.5 mm flat washers at each auxiliary peripheral hole. Main peripheral screws remain M3x6 with one washer. Bridge nut slots moved to Y=-1.5..1.2 so bridge screws remain M3x30. The knee end of the femur is relieved to radius28 through the main cheek and ribs. The fitted case pockets and inward servo orientation remain.

The operator measured kit washers at approximately 7.7 mm OD. Counterbores are 8.2 mm. At the four bench mounting feet, omit top washers because OD7.7 washers would touch the servo clamp; use one washer under each nut. Actual washer thickness remains unconfirmed. The bench now has longitudinal ribs for the longer reach.

39 exact 3D operating/guard pose combinations passed, with no rigid-part or reserved-connector intersections. Another 63 yaw positions passed. One-degree hip and knee sweeps at 18 mesh section planes passed. Hardware envelopes, 15 watertight printable meshes, profile/schema and plate/bed checks passed. Native Fusion has three verified joints, named printed bodies and a video showing each joint through its complete operating range. The 36-second suspended PyBullet test passed with approximately 0.53 degrees maximum tracking error. Its target phase starts with continuous position, velocity and acceleration. It does not send commands to hardware.

Print estimates: plate01 ribbed mount plus yaw/hip caps 4 h 08; plate02 coxa and yaw saddle 3 h 20; plate03 femur, lower arm and knee cap 3 h 35; plate04 tibia, auxiliary cheeks and four yaw spacers 3 h 52. Total approximately 228 g PLA. Profiles use 0.28 mm layers, five walls and 25 percent gyroid. Plate01 support is off; others use the supplied tree profile with 2 mm XY and 0.56 mm top separation. No sampled support centre lines enter the checked nut seats or screw bores. Exposed support in the open coxa driver scallop still needs removal.

Physical load qualification remains open. The ribbed bench passes the selected conservative 5 N equivalent-load section screen, but simplified bridge checks remain below their assumed margins. Begin with restrained unloaded articulation. The full-body walking assembly, physical servo calibration, real wiring motion, material strength and balance are not qualified by this release. R6 and R7 fork pieces are not interchangeable. A CSV records ten unchanged STL geometries relative to the 82 mm R6 CAD set; this is not evidence that the older fixture coupons match.

## Overnight batching and reuse clarification

The operator wants longer overnight batches, not repeated short coupons or a temporary printed base. The R7 ribbed bench plate is a temporary fixture and is not intended as final robot bodywork. It is excluded from the current overnight handoff.

Prepared design/overnight_leg_20260914/R7_Overnight_Leg_Parts.zip: eight unchanged R7 parts, 9 h 51 min CuraEngine estimate, approximately 148 g PLA. Includes coxa upper/lower, femur main/auxiliary, tibia main/auxiliary, hip cap and knee cap. Excludes the bench base, existing matching yaw cap, existing nominal yaw spacers and the yaw saddle pending verification of the older clamp's nut engagement. The flat first/second-fit cap matches the current yaw-cap STL hash. The older saddle's nut stop was -13.7 mm Y versus -10 mm in R7, so case fit alone does not establish suitable M3x30 thread engagement. The old 47 mm lower yaw arm does not replace R7's 59 mm arm with wider washer seats. Old fixture cheeks/bridge remain useful test fixtures.

The operator's marked older-model image asks for the hip pivot toward the outward end of the motor. R7 already uses that orientation, with the case extending inward. Fusion was showing an older recovered full-body model while the user was inspecting it; they explicitly said this was intentional. R7 was brought forward for comparison without closing the recovered document. A same-case-centre schematic shows the 25 mm pivot shift from the 12.5 mm shaft eccentricity. No R7 geometry change was needed for that request.

Three-foot or two-foot support has not been validated as a complete robot. A static three-foot stance needs the centre-of-mass projection inside its support triangle; two small feet have very little lateral margin. Equal-sharing average leg load increases by 50 percent from three supports to two, but actual reactions and motor torques depend on posture and dynamics. Do not promise two-foot balance from a leg animation.
The overnight layout was tightened before handoff to improve bed-edge clearance. The final re-slice is approximately 9 h 50 min and 148 g, with at least 2 mm centreline travel margin to the nominal XY bed boundaries. Same eight source parts and 12 mm model spacing; fresh support checks pass.

## Local DFM update after overnight batch

Current alternate print handoff: design/print_dfm_20260914/DFM_Overnight_Print_Set.zip. User asked for a quick support/manufacturability improvement. Two coxa parts changed, remaining six overnight pieces unchanged. Flat 45-degree-chamfered flange outline, bottom rail, local bed-starting post/lip webs, pointed roofs on horizontal small bores and post pockets, and central hex preserving the original 7 mm circular clearance. Matching lower flange updated. Original circular screw and washer clearance envelopes and lower nut insertion route passed. Added material checked at all39 baseline poses with no intersections. No new full-body load certification.

Actual comparison: support4.72g to4.04g (approximately15percent reduction); total147.68g to149.13g because permanent material was added. Time9h50 to9h53, so no speed saving claim. Remaining broad underside support especially tibia stays. New profile sets support XY clearance4.3mm and top gap0.56mm so tree tips do not occupy central hex. Increased separation leaves short unsupported edges and may roughen undersides. The hex ceiling is a short approximately4mm bridge, not an entirely overhang-free feature. Profile matches actual slice, critical support midpoint checks pass, bed/mesh checks pass. The unchanged full R7 Fusion archive does not contain these new local coxa features; editable updated STEP files and assembled STEP are supplied.

Earlier overnight JSON/TXT and R7 first-print TXT registrations retired because the DFM guide supersedes them for this handoff. Historical files remain unchanged on disk. The ribbed temporary base and already printed matching yaw cap/spacers remain excluded from the updated overnight batch.

## Centred DFM flange correction

User rejected the visibly asymmetric DFM flanges. Both now have regular octagonal outlines centred at shaft XY0,0,28mm across flats. The original radius14 flange lies wholly inside that polygon, eliminating the previous mixed curved/polygon perimeter. The upright has a separate small45degree-sided print foot; the lower flange has no extra offset extension. Shaft, central hex and four PCD14 screw centres are unchanged. Large lower-arm washer recesses still symmetrically overlap the central opening at the outer face, preserving the existing washer fit.

Source: design/print_dfm_20260914/build_dfm.py. New handoff: DFM_Centred_Overnight_Print_Set.zip. New slice9h48min,147.93g. Added-material checks at39 baseline poses pass; original bore and counterbore clearance tests, nut insertion, updated slice support midpoint and bed envelope checks pass. Existing physical-load qualification limits remain. Use the new centred archive rather than the previous asymmetric DFM archive.

## Two overnight plates printed, assembly handoff 2026-09-15

User reports printing the overnight plate twice for a second leg. Treat these as two sets of eight robot-leg pieces, with no mirror requirement for the current geometry. Full leg count excludes the temporary bench base. Outside each overnight plate, a yaw saddle, yaw cap and four nominal11.6mm spacers are still needed: totals2 saddles,2 caps,8 spacers for two legs, less suitable earlier printed pieces. One previously printed matching cap covers one yaw cap. Older yaw saddle remains conditional on actual full nut/thread engagement; case fit alone is insufficient. Four existing uniform nominal spacers may cover one leg, subject to the axial-fit check. Do not suggest another complete overnight plate to fill these omissions.

Created design/assembly_two_legs_20260915/Assembly_9_Steps.mp4 and Two_Legs_Assembly_Guide.zip. Exact latest centred DFM solids imported into Fusion, named per printed piece; exploded then assembled via explanatory translations. Nine stages,297 frames at8fps, about37seconds. Captions show fastener sizes and washer counts. Screws,nuts,washers,cables are not drawn. Exploded paths are illustrative, not collision-verified assembly trajectories. Saved Exploded_Printed_Leg.f3d and Assembled_Printed_Leg.f3d preserve states, not Animation-workspace storyboard. New active Fusion document is ASSEMBLE THE PRINTED LEG - centred DFM parts. Final transforms verified against manifest.

New guide gives totals excluding bench/body fasteners: per leg12M30,6M20,8M12,12M6 peripheral screws,14nuts,53flatwashers plus supplied special centre retainers; double for two legs. Actual flat washer thickness remains unconfirmed at assumed0.5mm. First assemble and check one restrained unloaded leg. Prior R7 ASSEMBLY.txt and Fusion progress JSON registrations retired because the current user handoff uses the new assembly guide and animation report; files remain on disk.

## One-run speed/process calibration prepared 2026-09-15

User confirms the latest overnight robot prints and earlier coupons succeeded using the samePLA,0.4mm nozzle,210C nozzle and60C bed, with minor stringing. They request one thoroughly controlled G-code calibration covering speed, acceleration, flow and stringing rather than many separate Orca tests. Active calibration package: design/speed_calibration_20260915/Neptune4Pro_One_Run_Calibration.zip. Machine-ready G-code is explicitly authorized for this task. It was generated and statically validated; it was not sent to a printer.

Six labeled regions F/A/R/C/S/T, six5.6mm bands above a0.56mm base. F requests8,12,16,20,24,28mm3/s at0.28x0.42mm beads and3000mm/s2; 180mm long walls provide sustained runs. A uses0.14mm layers at120mm/s so flow remains7.06mm3/s while acceleration changes1000,2000,3000,5000,8000,10000. R repeats roofed3.4mm bracket holes at40,65,90,120,150,180mm/s, with C identical at40 throughout. S changes retraction0.20,0.35,0.50,0.65,0.80,0.50mm; T stays0.50. String transfers180mm/s and retract speed35mm/s; all thermal/material factors stay fixed. Marker ribs separate bands; band numbers are read bottom-to-top on the supplied chart, not embossed on each band.

The continuous front flow tower prints first with a two-layer low-flow recovery rim, then rear specimens print together. All bases/labels are printed before tall features. The return to lowerZ behind the finished flow tower is intentional; independent path checks maintain at least12.86mm clearance with a conservative50mm head footprint. Setup assumes stock toolhead; no custom large duct. About30.3g,10.16m filament; nominal motion lower bound91.6min and full stop-to-stop estimate108.4min, excluding heat/home. Allow roughly2h.

G-code uses M83 relativeE, explicit retracts, M204 and SET_VELOCITY_LIMIT VELOCITY=300. Max extrusion feed238.1mm/s, maxflow28mm3/s, accel10000. Ends at accel2500, heaters/fanoff, no savedconfig change. Pressure advance, shaping, corner settings and thermal protections unchanged. The stored Orca printer address had a read-only status request timeout; no live firmware config was obtained. Startup follows local stock Cura Neptune4 pattern with inboard, volume-calculated purge, without guessing a bed-mesh profile name. User should print G-code directly, not re-slice. This is supervised limit testing, not an unattended production promise.

Independent parser checked26014 spatial moves and all36 zone/band schedules, bounds, heat/home beforeextrusion, retractaccounting, bead crosssections and shutdown. Technical methodology references official Elegoo spec, Klipper G-code docs and current toolhead.py. Readme and CSV describe conservative interpretation: approximately80percent of last consistently clean flow band, compareR againstC, choose small effective retraction, confirm selected speed+acceleration on one actual leg part. This does not qualify full-body structural load.

Output registry retired prior R5 FUSION_JOINT_API.txt, LEG_INTERFACE.txt and old Fusion progress.json from current deliverables to register this calibration guide/validation. Historical files remain unchanged. Remaining pending prior work: user stopped native Fusion exploded-storyboard automation; brighter plastic appearances applied, storyboard not completed. Calibration was the subsequent task.

## Main four-leg hub and spacer plate, 2026-09-15

User requested the main robot centre hub for four legs, eight larger spacers and a modestly faster Neptune4Pro profile, all on one bed. Clarification was offered for spacer dimensions but no dimensional reply had arrived; after the user's continue instruction the direct reading was used and explicitly stated: height8mm, outside diameter13mm, M3 clearance bore3.4mm, quantity8. These are general spacers and are NOT substituted for the OD5.8 x11.6mm yaw spacers or pitch annular rings. If the user clarifies a different axis/dimension, regenerate the spacer and combined plate before printing.

Active files: design/main_hub_20260915/Tonight_Main_Hub_And_8_Spacers.zip. Hub178.4x206x12mm, flat6mm deck with6mm upper ribs. It is intended robot bodywork, not the temporary bench base. Retains16 yaw saddle holes in four38x40 patterns at radius75mm, azimuths+/-45,+/-135; yaw shaft height38mm. Enlarged forward clearances accommodate current82mm centred DFM coxa. Outer saddle seats have full-width bearing strips. Legacy cover fixing coordinates retained, but old cover/electronics vertical interfaces require adaptation. Legacy battery mounting pattern collided with larger openings; it is replaced by reserved central holes atx+/-14,y+/-8. Old battery tray is NOT drop-in compatible.

Hub versus actual DFM leg solids passed140 individual pose samples across four mounts. Mounting hardware envelopes passed116 checks. No inter-leg/gait or physical load qualification claim. Simple section screen at an assumed1Nm load and12MPa PLA allowable passed chosen sections but is not FEA, local tab-strength proof or real test. Hub valid single solid, mesh watertight, no downward unsupported faces above bed, actual sliced support0g.

Mount each stationary yaw saddle using4M3x12,4nuts,4flatwashers underneath; no upper washers. Nominal6mmdeck+3mmfoot+0.5washer+2.2nut leaves0.3mm tip projection. User must confirm full nut engagement with actual washer/nut thickness; do not blindly substituteM18 due rotating-arm path. Two legs need8 of each fastening item, four legs16. Large8x13spacers must not be inserted into this checked saddle-to-hub stack.

Single bed: hub plus8spacers, 7h50min,119.63g PLA, supportsOFF,0.28layers,5walls,25percentgyroid,2mmoutsidebrim,210/60C. Outer walls/topbottom40to46mm/s,travel150to175,inner/infill remain65 to retain nominal8mm3/s envelope. Actual max7.7568mm3/s, XYmotionedge margin2.966mm. Hub-only A/B slice7h34to7h16 (3.89percent total improvement); do not claim15percent faster complete print. Geometry3MF does not select profile automatically. Source-consistent archive and output-punctuation checks passed. Bright native Fusion document PRINT TONIGHT - four-leg main hub and eight spacers, local F3D and full neutral four-leg STEP included. No physical print started.
Spacer correction: user explicitly requests5.5mm diameter and13mm height. Generated8 pieces retaining3.4mm M3 bore in design/main_hub_20260915/corrected_spacers. Hub bytes and Cura settings unchanged. New combined estimate7h26min111.89g, supportsOFF. Archive Hub_And_8_Corrected_Spacers_5p5D_13H.zip supersedes earlier8H13OD spacer plate. Also provided eight-spacers-only3MF/STL. No change to checked leg axial stack or yaw spacer requirement.
