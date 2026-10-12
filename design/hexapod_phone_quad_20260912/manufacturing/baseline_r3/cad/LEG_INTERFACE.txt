# R3 leg geometry and assembly interface

This leg was reconstructed from the linked hexapod video's open servo yokes and curved tapered feet. It uses no earlier MIST robot geometry. The source is a visual reference; the STS3215 C018 clamps, supported yaw joint and phone quadruped layout are new work. Nominal hardware dimensions come from [the hardware contract](../references/hardware_contract.md).

R3 enlarges the transverse bridges, restores the full cheek thickness behind their external nuts, deepens the lower yaw arm and staggers the post's nut windows. Short edge flanges improve lateral stiffness while leaving the broad outer cheek faces flat for printing. Joint centers, servo positions and horn seating planes are unchanged. The frozen one-cheek side-load screen still requires an assembled fixture test; these revisions do not establish a general printed-strength pass.

## Coordinates

`build_leg()` returns separate parts in their owning link frame. Local X points outward, Y points left and Z points up. Positive rotation about Y tips a link downward. The yaw mount frame is at the main servo bearing face.

| Interface | Final nominal location |
|---|---|
| Hip axis in coxa frame | X 50, Y 0, Z 0 mm |
| Knee axis in femur frame | X 90, Y 0, Z 0 mm |
| Toe center in tibia frame | X 105, Y 0, Z 0 mm |
| Pitch case main and auxiliary faces | Y +14.5 and -14.5 mm |
| Pitch cheek inner faces | Y +19 and -19 mm |
| Main and auxiliary cheek thickness | 4 mm each |
| Main horn screw pattern | Four M3 on a 14 mm pitch circle |
| Horn retaining-screw access | 7 mm diameter through printed cheek |
| Yaw clamp deck interface | Z -32 mm; holes at X -29 and +9, Y -20 and +20 mm |
| Lower yaw arm | Z -53 to -44 mm; 9 mm thickness |
| Yaw auxiliary disc outer face | Z -33.5 mm, provisional seating |
| Auxiliary spacers | Four, 10.5 mm long, 5.8 mm outside diameter, 3.4 mm bore |
| Lower yaw peripheral counterbores | 6.2 mm diameter, 2.5 mm deep from Z -53; washer seats at Z -50.5 |
| Lower arm to upper coxa screws | X 32, Y -4.5 and +4.5 mm, along Z |
| Negative-Y post nut pocket | Z -41.5 to -38.9 mm; loaded 2.4 mm nut center at Z -40.3 mm |
| Positive-Y post nut pocket | Z -37.5 to -34.9 mm; loaded 2.4 mm nut center at Z -36.3 mm |
| Femur bridge and screw | Nominal 14 by 14 mm section with 2 mm beveled corners; screw X 70, Z -16 mm, along Y |
| Tibia bridge and screws | Nominal 16 by 13 mm section with 1.5 mm beveled corners; screws X 48 and 56, Z 19.5 mm, along Y |

Both pitch servo tails face +X in their parent link frame. Their rear connectors point away from the preceding servo. The yaw servo tail points toward the body. The femur grew from the initial 80 mm proposal to 90 mm because the real exterior clamp tabs collided at 80 mm. The retained 90 mm spacing and outward knee connector then cleared the provisional connector volumes.

The post is 8.5 mm wide along X. Its lower shoulders reach Y +/-11.5 below Z -34, taper to Y +/-8.5 by Z -28 and retain that width above. Only one nut window crosses the post at each height. The lower nut has a 2.5 mm floor above the arm interface; the upper nut has a 6.5 mm floor. Hold nuts in the side openings until their screws capture them. The bolt clearance holes continue to Z -30, leaving room for both projecting screw tips.

Main-cheek edge flanges are 4 mm high and extend inward from Y 19 to 15. The auxiliary flanges extend only 1 mm inward inside a 44.5 mm radius from the joint, then reach 4 mm farther out. This asymmetric relief clears the C018 rear profile and clamp shelves, which project beyond the nominal 29 mm case depth. Horn relief remains at least 11 mm radius. Flanges stop or are relieved at the detachable bridge seating faces and knee clamp. They do not make a proven closed box section.

The rounded toe is a 5 mm radius cylinder across a 14 mm width. Its small flat is 4.8 mm from the toe center and lies horizontally when hip plus knee equals 105 degrees. The flat is approximately 2.8 by 14 mm. At nearby angles the curved surface gives a maximum 5 mm contact depth. A 5 mm sphere in a reduced simulation differs in height by up to 0.2 mm near this stance, and does not represent the full 14 mm lateral patch. The blade has a transverse strap slot near the toe for optional padding.

## Clamp and fastener access

Each case clamp has a fixed rail, positive X end walls, a bottom shelf and an independent side cap. The side rails contact the nominal 24.73 mm case width. The cap has 0.8 mm of closure space before its tab ends meet the fixed wall. Its three screws tighten the rail against the case; the design does not rely on a loose pocket for retention. End clearance is 0.3 mm per end in the production candidate. The three end-clearance coupons vary that value to 0.2, 0.3 and 0.4 mm. They do not alter the nominal side-contact width.

Three M3 clamp screws run along the case's short side. One sits above the rear connector aperture and two sit at the opposite end. A fourth screw through the rear middle would cross the connector opening, so it was removed. The fixed rail has 5.7 mm across-flat nut pockets. Test those pockets with actual M3 nuts before printing the assembly.

The main and auxiliary yoke cheeks detach independently. Fit the powered metal horn and auxiliary metal disc to the servo, check their seating, install each cheek on its own side, then install the bridge fastener. No cheek needs to spring over the servo. The central retaining screws remain accessible through the 7 mm holes. The auxiliary disc uses the supplied PA3.0 x 5 screw; do not substitute the powered output's M3 screw.

The modeled 38 mm distance between pitch cheek inner faces is a candidate assembled horn stack. The specification does not establish it as an exact installed dimension. Test it with the dedicated pitch-yoke coupon and actual supplied discs. A rigid bridge that draws the two discs together can preload or bind the auxiliary stub. Adjust the bridge width or add measured shims before printing full legs if the stack differs.

| Leg fastener interface | Quantity per leg | Initial length to test |
|---|---:|---|
| Three case caps | 9 M3 screws and 9 nuts | M3 x 35, with thin washers |
| Yaw clamp feet to 4 mm body deck | 4 M3 screws and 4 nuts | M3 x 12, verify deck and washer stack |
| Main powered horn to printed cheek, three joints | 12 M3 screws | M3 x 6 with one OD6 by 0.5 mm washer; 1.5 mm nominal engagement |
| Pitch auxiliary discs to printed cheeks | 8 M3 screws | M3 x 6 with one OD6 by 0.5 mm washer; 1.5 mm nominal engagement |
| Yaw auxiliary disc through lower arm and spacers | 4 M3 screws and 8 washers | M3 x 20 with two OD6 by 0.5 mm washers per screw; 2.0 mm nominal engagement |
| Lower yaw arm to coxa post | 2 M3 screws and 2 nuts | M3 x 20 with one OD7 by 0.5 mm washer per screw |
| Femur and tibia auxiliary cheek bridges | 3 M3 screws, 3 nuts and 6 washers | M3 x 50, plain 2.4 mm nuts and two OD7 by 0.5 mm washers per screw |
| Main shaft retention | 3 supplied screws | M3 x 6 from the supplied horn set |
| Auxiliary stub retention | 3 supplied screws | PA3.0 x 5 from the supplied disc set |

These are fit-test starting lengths, not an assertion that every length and quantity is in stock. The powered flange is only 2.5 mm thick and the auxiliary flange only 2.1 mm. A longer peripheral screw can project behind the disc and touch the case. Check tip clearance through a full unloaded rotation before powering a joint. Screws and nuts are not represented as threaded solids in this leg module, so the solid collision checks do not certify their head, tip or tool clearances.

The lower yaw auxiliary screws seat at Z -51.5 beneath their two thin washers and end at Z -31.5. Nominal clearance to the flange's inner face at Z -31.4 is only 0.1 mm. The 6.2 mm counterbore also gives only 0.1 mm radial clearance around an OD6 washer; an OD7 washer will not fit. With an approximately 3 mm socket head, these heads project about 1.5 mm below the arm. The post screw heads reach approximately Z -56.5. The shallow counterbores leave 0.4 mm local webs beside the central access opening in their recessed underside layer; inspect those webs for missing extrusion or handling damage. The remaining 6.5 mm thickness carries the washer seats.

The bridge recesses have been removed from the production cheeks. The external stack is 46 mm between outer faces, 1 mm of washers and a 2.4 mm plain nut, totaling 49.4 mm. An M3 x 50 screw projects only 0.6 mm beyond that nut. A taller locknut requires a different screw stack. The tibia's 8 mm hole spacing leaves 1 mm between OD7 washers; use a slim 5.5 mm AF wrench or socket and inspect nut movement after short fixture runs. Do not apply a generic metal-joint tightening torque to printed nut floors.

The three cap parts are the same shape after rigid rotation. A complete quadruped needs twelve copies of that cap shape. The four small yaw spacers are also a shared shape; the complete quadruped uses sixteen. Per-part exports retain distinct names to make assembly placement unambiguous.

## Print and coupon use

Print orientation is recorded as `print_rotation` on every returned printable part. The export driver applies that rotation and moves the part onto the build plate. The yaw saddle and lower yaw arm print on their broad deck faces. Separate auxiliary cheeks and the main cheek faces lie along the build plate to keep their long structural fibers within layers. The coxa uses +90 degrees about X, following the R2 orientation comparison; its new geometry still requires a fresh slice. Case saddle coupons use their native Z orientation, matching the principal case axis in the revised coxa. The main coxa, femur and tibia pieces contain offset geometry and require support under those offsets. Review the support preview around the case rails, nut pockets, horn seats and connector aperture before slicing. Remove support residue from contact faces before testing fit.

The sixteen leg coupons contain three case saddles and matching caps, two horn cheeks, a 38 mm pitch-yoke bridge, an M3 clearance strip, three yaw spacers and three new strength sections. Assemble the horn cheeks around an actual servo with the 38 mm bridge and one M3 x 50 bridge screw. This tests case clearance, central screw access, peripheral screw engagement and whether the auxiliary disc turns freely when both cheeks are connected. That older fit fixture retains a captured nut and is not the R3 load-test specimen. The 10.2, 10.5 and 10.8 mm yaw spacer coupons test the supported yaw stack. Select a measured stack, not whichever value tightens hardest.

The new bridge main and auxiliary coupons are cropped directly from the R3 production shapes. They retain the real cross section, full 4 mm external nut face and print orientation. The third coupon reproduces the staggered post windows and lower shoulder. Use the complete production lower yaw arm with that post coupon to check the two post screws, counterbores, washers and auxiliary-disc stack. These specimens support sacrificial fixture testing; their geometry does not prescribe or certify a safe test load.

Use the same material, wall count and contact-face orientation for coupons and final parts. PLA is suitable for this requested first-fit set. The geometry checks do not establish PLA creep, impact or thermal life under the assembled load. The broad contact rails and supported output reduce local loads, but physical loaded testing is still required.

## Recorded checks and limits

`check_leg.py` found one solid and one watertight mesh component for each of the fourteen printable shapes in a repeated leg. It found no positive-volume part intersections at the nominal pose and the listed sampled hip/knee poses, including 30/75, 25/76 and 3.35/30.46 degrees. Individual yaw samples at -25 and +25 degrees also passed.

`check_leg_grid.py` sampled 27 combinations: yaw -18.78, 0 and +18.78 degrees; hip 13.90, 24 and 34.15 degrees; knee 55, 70 and 86.79 degrees. No part-to-part, connector-reserve-to-part or connector-reserve-to-reserve positive-volume intersections were found. Each reserve extends 15 mm from its insertion plane with an 18 by 18 mm cross section. Actual plugs and bend radii remain unmeasured. This reserve tests the leg's local packaging, not the complete cable route through the body.

The configured operating yaw range in `settings.json` is -22 to +22 degrees. The leg module retains -25 to +25 degrees as diagnostic extrema; those wider angles have only 0.429639 mm nominal clearance between the coxa shoulder and yaw saddle. Hip 3 to 35 and knee 30 to 100 degrees remain provisional part-level bounds. These bounds contain sampled checks and do not certify every combination or the complete swept volume between samples.

The final R3 whole-assembly check includes the original nine coupled leg poses, the 30 degree hip and 81 degree knee stance at yaw -22, 0 and +22 degrees, and thirteen phone pan angles. All of those sampled intersections pass. Four rounded deck-edge reliefs clear the widened coxa shoulders. Exact BRep distance checks at both operating yaw endpoints on all four legs found a minimum 1.501665 mm gap to the yaw saddle and a minimum 2.159715 mm gap to the deck. The additional -25 and +25 degree stance probes also have zero nominal intersection after those reliefs, but their small direct clamp gaps do not qualify that range for physical operation. Full-body cable, screw-head, strength, stability and physical fit checks must be read alongside these geometric results.

Final R3 printed solid volume per repeated leg is 143577.588 cubic millimeters, approximately 178.036 g at 1.24 g per cubic centimeter. This is 24.044 g more solid PLA per leg than R2. It is a solid-volume estimate before the slicer applies infill. Three servo masses are separately specified as 55 g each. Supplied metal horn mass is estimated from geometry by the assembly exporter. Fasteners are accounted for separately by the distributed hardware model.

The revised bridges and yaw arm target the weak connections identified by the frozen R2 beam screen. Modest main-cheek ribs reduce the isolated combined sagittal and side-load estimate, but do not meet the assumed 12 MPa allowable when one cheek receives the entire 5 N lateral disturbance. Actual paired-cheek load sharing and printed layer strength need fixture evidence. The unchanged clamp end ligaments and preload-sensitive nut floors also remain inspection and test items. Read the current strength assessment alongside this geometry result before selecting physical operating loads.
