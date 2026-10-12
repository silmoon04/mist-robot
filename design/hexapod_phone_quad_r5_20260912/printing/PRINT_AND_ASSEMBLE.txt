# R5 print and assembly guide

R5 uses a 70 mm yaw-to-hip spacing, inward-facing hip and knee servo cases, and a straight 105 mm knee-to-toe member. Work only from this R5 directory. The R4 design, measurements and checks remain in their separate directory.

The corrected deck reliefs retain a minimum model gap of 1.57 mm in the denser yaw sweep: 312 BRep distance checks cover all four legs at each integer angle from -19° to +19°, against the deck and fixed saddle. The exact minimum deck gap is 1.573865 mm at 18°, above the 1.5 mm clearance target. The fixing-hole ligament remains 3.747382 mm. These discrete digital checks do not establish measured print clearance or strength. The earlier failed sweep remains in manufacturing/clearance_revision. Assemble each complete leg module before mounting it to the body.

The final yaw operating limit is ±19°, retaining a 1.61054 mm nominal gap to the fixed saddle in the checked model. At ±22° the solids remain separate, but the 0.656 mm gap fails the minimum-clearance criterion. Use ±19° during the restricted sweep and commissioning checks. This limit changes no printable geometry and requires no replacement print pieces.

Start with PRINT_FIRST.txt, FIRST_FIT_CHECKS.txt and the current plate manifest. Physical fit, printed strength and loaded operation remain prerequisites; a valid mesh or digital assembly does not establish them.

## Three print stages

Common first-fit plates contain the nominal case saddle and shared gauge cap, case-to-shaft registration plate, horn fixture cheeks and bridge, nominal yaw spacer, hole gauge, nominal phone fit pieces and two femur section specimens. The femur specimens are required before loading. Optional plates contain alternative case, spacer and phone fits. Source mandatory flags and the selected stage are recorded in coupon_bom.csv.

Dedicated revision-check plates contain five complete production parts: the upper coxa with inward-hip saddle, lower yaw arm, dedicated hip cap, straight tibia main member with foot, and short tibia auxiliary cheek. They are reusable first articles, not cropped substitutes. A passing part can count toward the production BOM; record that reuse to avoid printing unnecessary duplicates. The generic gauge cap is shared among case-clearance trials, but cannot replace the dedicated production hip cap.

Plate 02 contains five selected major revision specimens, not every changed SKU. The [change audit](../manufacturing/slicing_r5/R5_CHANGE_AUDIT.md) identifies seven changed SKUs: those five parts plus the femur auxiliary cheek and body deck. When completing the supported leg, use the R5 femur auxiliary cheek with its inward-hip cable reserve; when mounting the legs, use the R5 deck with its corrected reliefs. Do not mix R4 versions of either part into the R5 assembly. Both are included in the production BOM, although they are not on plate 02.

Read object display names in the 3MF and the display_name columns in both BOMs. Stable file identifiers may retain an older term such as curved; the R5 display label identifies the actual straight geometry. Do not choose a part by an old filename description alone.

All plates contain millimetre geometry with named objects and matching combined STL exports. They do not contain a printer profile or G-code. Preserve orientation and size. The packer uses a maximum 215 × 215 mm geometry region on the physical 225 mm bed and leaves at least 8 mm between object bounding boxes. Check support, skirt and brim too. Keep large body parts on individual plates when their brim approaches the bed boundary.

## Printer settings and slice review

Use the owned Neptune 4 Pro and actual installed nozzle. The planned PLA profile is a 0.4 mm nozzle, 0.20 mm layers, 0.42 mm lines, five walls, six top and bottom layers, 35% gyroid and an 8 mm³/s flow ceiling. Starting temperatures are 210/60 °C within the filament maker's range. Starting speeds are 20 mm/s first layer, 35 outer walls, 60 inner walls and 80 infill, limited by flow. Use full cooling after layer three.

The planned support is normal zigzag at 15%, with a 60% roof, 0.6 mm roof thickness, 0.2 mm Z separation and 0.5 mm XY clearance. Inspect the actual layer preview. These are analysis settings, not a measured machine calibration. Use a 4 mm brim where needed after checking its boundary.

Use the supplied R5 orientations for the full coxa, triangular flange, lower arm, dedicated cap and straight tibia. Do not reapply remembered R4 rotations. Check support under raised saddle and bridge features, counterbores and the straight member's foot. Preserve the full-depth triangular flange and material around post holes. The main tibia is now straight; old curved-foot support assumptions do not describe it.

The inverted body cover and ribbed battery tray retain local support requirements. The phone frame prints on its reinforced column backs with support beneath the offset central rear plate; its top cap prints inverted. Bridge the short roofed pan-nut pockets without trapping support inside. The case-to-shaft gauge prints inverted and needs support under its two offset feet. Keep removal scars off horn seats, nut roofs, washer lands and datum faces.

[R5 production slicing](../manufacturing/slicing_r5/output/PRODUCTION_SLICING.md) covers all 34 SKUs and 76 production pieces from the current manifest. It estimates 1.056056 kg deposited model PLA, 55.8 g removable support and 1.1 g adhesion. Individually sliced production jobs total 105.4 predicted hours; these three coupon plates need their own slice-time estimates. The [mass comparison](assembled_mass_comparison.json) gives 2.756962 kg deposited-material assembly mass and 2.936135 kg for the full-solid comparison. Thirty-five percent infill is not a 35% mass fraction. Many small reinforced parts consist largely of walls and skins. Material or process changes require new fit and load specimens; PLA settings and strength assumptions do not transfer unchanged to PETG.

## Hardware and R5 geometry

Use R5_FASTENER_STACKS.md and fastener_mass.csv for attachment-level requirements. The BOM requires 200 separately purchased screws: 52 M3×6, 32 M3×8, 20 M3×10, 16 M3×12, eight M3×16, 24 M3×20, 36 M3×35 and twelve M3×50. Add thirteen supplied main M3×6 and twelve supplied auxiliary PA3.0×5 retainers. It also requires 100 plain M3 nuts and 256 thin washers: 148 OD6 and 108 OD7, all ID3.2 and 0.5 mm thick. Counts exclude fixture-only hardware and spares. Available inventory does not prove every required size is present.

The hip axis is X=70 from yaw. Lower-arm post holes are X=28.5, Y=±4.5. The dedicated hip cap moves the rear bolt to servo-local X=-38.915, Z=-27.5. Its other bolts remain X=13.915 at Z=-23 and -7. Do not substitute a yaw or knee cap. Both hip and knee clamp screws enter from below in their parent-link frames. Straight-tibia bridge holes are X=36 and 44, both Z=0, leaving the same 8 mm spacing.

| Connection | Required stack and check |
|---|---|
| Case clamps | M3×35, one OD7 head washer and recessed plain nut; preload nuts before installing the case |
| Yaw saddles to deck | M3×12 with OD7 washer and nut |
| Main horn periphery | M3×6 plus one OD6 washer; 1.5 mm nominal engagement through a 4 mm cheek |
| Pitch auxiliary discs | M3×8 plus TWO OD6 washers and 1.1 mm integral lands; 1.9 mm engagement in a 2.1 mm flange |
| Yaw auxiliary discs | M3×20 plus TWO OD6 washers, 3.5 mm counterbores and nominal 11.6 mm spacers; 1.9 mm engagement |
| Lower arm to coxa post | Two M3×20 with OD7 washers and staggered side-loaded nuts at the new X28.5 holes |
| Femur and tibia bridges | M3×50, TWO OD7 washers and external 2.4 mm plain nut; 49.4 mm nominal stack and 0.6 mm tip emergence |
| Phone hub to horn | Four M3×6 with one OD6 washer each in counterbores; 2 mm nominal engagement |
| Pan saddle to cover | Four M3×16 through 4 mm feet and 4 mm spacers, with OD7 head washers |
| Pan servo cap | Four M3×10 into side-loaded nuts beneath retained roofs |
| Phone feet | Eight M3×10 total, four downward and four from behind |
| Phone clips and top cap | Four M3×16 total; secure edges without glass or button preload |
| Cover and battery tray | Eight M3×10 total with OD7 washers and nuts |
| Shaft centre retainers | Main supplied M3×6; auxiliary supplied PA3.0×5 with one added OD7 washer against the fixed stub |

Pitch and yaw auxiliary peripheral screws have only 0.2 mm nominal rear margin. Omitting a thin washer changes the engagement and can put the tip beyond the flange. OD7 washers do not fit the 6.2 mm peripheral counterbores. Each auxiliary centre washer overlaps the 6.05 mm disc bore and bears on the fixed stub; check the actual screw's pilot depth, head coverage and free disc movement. The nominal disc-to-washer axial gap is 0.7 mm. Never clamp the auxiliary disc until it binds.

Use plain nuts nominally 5.5 mm across flats and 2.4 mm thick, matching metric drivers, a slim socket or spanner and a caliper. Verify printed pockets and actual washer thickness. The two tibia OD7 washers have a nominal 1 mm gap at the 8 mm bolt spacing. Do not assume an old nut-entry route or fully assembled service clearance remains valid after the hip reversal.

## Assembly and measurement sequence

1. Print the common fits. Enter actual results in the fresh R5 coupon_feedback.csv. Preload the gauge saddle's nuts, insert the real servo and fit its cap loosely. Install the real main horn and registration plate together. The gauge feet use two M3×12 bolts, two nuts and four OD6 washers. Seat the four horn screws by hand, then tighten the cap only after case, plate and horn meet without forced alignment. The shaft is 12.5 mm from the CASE MIDPOINT. Measure axial seating if the horn face misses the gauge; do not change the longitudinal datum to compensate.

2. Assemble the main and auxiliary horn fixtures and bridge with actual metal discs, retainers and washers. Test free rotation before and after gentle bridge closure. Start with the 11.6 mm yaw spacer; use optional lengths only after measurement. Reject a cap that bottoms before contacting the case, case lift, screw bottoming or a disc that binds.

3. Print the five revision-check parts. Check the inward hip carrier with its dedicated cap before fitting surrounding links. Insert all three hip clamp nuts from above into the bare carrier; their entry and seated positions have been checked digitally. Preload the remaining clamp and post nuts before their servos or neighboring links block access. Verify the special rear hip bolt at Z=-27.5, actual connector bend clearance, cap contact and driver withdrawal. The post flange is a complete R5 load path, not the old cropped R4 access-cut specimen.

4. Fit yaw and hip servos with torque disabled. Install the yaw auxiliary disc, OD7 centre washer and supplied PA retainer before fitting the removable lower arm. Load both post nuts, then close the lower arm at X28.5 using its two M3×20 screws. Fit the four measured spacers and paired-washer auxiliary fasteners. Check rotation after each small tightening increment.

5. Preload the knee clamp nuts and fit the inward knee servo. Complete the clamp screw stage before neighboring links obstruct access. Add the R5 femur auxiliary cheek, whose revised reserve clears the inward-hip cable, and close its external nut-and-washer bridge. Fit the straight tibia main and short auxiliary cheek, then its two external bridge stacks at X36/44, Z0. Check foot contact, fastener tips, driver access and cable clearance throughout the current restricted joint range. Do not force a rigid yoke over a servo.

6. Use the complete 70 mm coxa fixture with its upper yaw attachment, lower arm, real discs, nuts and full-depth triangular flange. Apply small measured vertical force at the actual hip X70, while retaining the post reaction near X28.5, then test independently reversible hip torque about Y. Record force, lever arm, deflection, twist and residual set. The longer lever changes load demand; do not reuse R4 numerical margins or its obsolete Z=-25 access-cut interpretation as a current failure prediction.

7. Test the straight-tibia assembly and both load directions with the real knee supports and bridge screws. Test the femur section specimens before loading a complete leg. Begin below the intended service load with the assembly captured. Increase load only after reviewing a repeatable response. Stop for cracking, whitening, slip, progressive deflection, permanent set, binding or lifted nut roofs. Record results before choosing the next load; a torque setting or force limit needs the current R5 analysis and fixture evidence.

8. Mount the completed leg modules to the R5 body deck with its corrected reliefs after their assembly and unpowered sweep checks. Do not use the R4 deck. Fit the ribbed tray and measured electronics, routing straps and wiring before closing the cover. Follow WIRING.md. Tighten the four pan body screws before adding the horn or hub. Load the servo-cap nuts through the side slots beneath their retained roofs, then fit and tighten all four cap screws evenly. Check cap contact, remaining travel and roof retention. The horn/hub must not block unfinished screw work.

9. Fit the pan horn, centre retainer, hub and feet. Load frame and foot nuts before inserting a dummy landscape phone. Attach the two short lower clips and top cap without glass preload. Check camera openings, button relief and the parked side USB plug. Test small measured cradle loads with the dummy before inserting the real Mi9SE. Use Wi-Fi and the phone battery during pan; park and disable pan before USB charging.

10. Record clamp movement and fixture deflection after an hour and a day, and at the measured servo-adjacent operating temperature before prolonged standing. After successful full-frame fixtures and one supported leg, proceed to a supported low-speed level-floor robot test with immediate servo-power removal available. Repeat the relevant loop after any geometry, hardware, material or print-process change.

## Release limits and records

R5 has fresh measurement rows. Old R4 feedback stays in its original directory and is not a result for this geometry. Passing full revision-check pieces may enter the final assembly after inspection, but sacrificially loaded or damaged pieces must be replaced.

Use source-matched R5 slicing, mass and strength records. Full physical fit, printed load capacity, fatigue, warm behavior and creep are not established by the CAD, sliced material quantity or rigid-body simulation. The first-fit notice and plate manifest identify their source geometry.

Regenerate using python printing/pack_prints.py after the R5 manifest is frozen. It validates coupon and production meshes, preserves entered R5 measurements, uses display names, separates revision plates and records hashes. Slice the resulting geometry for the actual machine before printing.
