# R4 leg interfaces and first-fit fixtures

The inward candidate preserves 50, 90 and 105 mm joint-center spacing. Its knee clamp points inward and its femur cross-bridge sits above the case at X58 to72, Z13.5 to27.5 mm. The bridge screw is at X65, Z20.5 mm. All dimensions below are millimeters in the owning link frame unless stated otherwise.

The canonical servo-local frame places the main shaft at X0/Y0 on main face Z0. The case spans X-35.115 to10.115 and Y+/-12.365. The longitudinal case center is X-12.5. This replaces the earlier erroneous 12.5 mm shaft-to-end interpretation. The shared production contract owns these values.

## Fasteners and locations

| Interface | R4 arrangement |
|---|---|
| Three case-clamp bolts, servo-local frame | X/Z=(-38.915,-5.5), (13.915,-23), (13.915,-7). Axes run along local Y. |
| Case-clamp screw stack | M3x35 with one OD7 by0.5 washer. Native under-head plane Y16.865; loaded plain-nut center Y-14.9. |
| Hip clamp bolt locations, coxa frame | X88.915/Y9 and X36.085/Y-8.5,+7.5; axes along Z. Heads above the cap, nuts below. |
| Knee clamp bolt locations, femur frame | X51.085/Y9 and X103.915/Y-8.5,+7.5; axes along Z. Heads below the cap, nuts above. |
| Femur bridge | M3x50 along Y through X65/Z20.5. Two OD7 by0.5 washers and a plain2.4 nut; nominal49.4 stack. |
| Tibia bridges | Same external stack, through X48 and56 at Z19.5. |
| Main powered horn periphery | Four M3x6 per joint, each with one OD6 by0.5 washer;1.5 nominal thread engagement through the4 mm cheek. |
| Pitch auxiliary-disc periphery | Four M3x8 per joint, each with two OD6 by0.5 washers. Under-head plane Y-24; tip Y-16. |
| Auxiliary pitch lands and disc | Integral lands1.1 high. Disc outer face Y-17.9 and inner flange face Y-15.8 give1.9 mm engagement and0.2 mm nominal tip margin. |
| Yaw auxiliary support | Four11.6 mm spacers from Z-44 to-32.4. Existing9 mm arm has3.5 mm counterbores with washer seats at Z-49.5. |
| Yaw auxiliary periphery | M3x20 with two OD6 by0.5 washers. Under-head Z-50.5, tip Z-30.5; flange spans-32.4 to-30.3, giving1.9 engagement and0.2 margin. |
| Lower yaw arm to post | Existing M3x20 and OD7 by0.5 washer, under-head Z-53.5. Holes X32/Y+/-4.5; loaded nut centers Z-40.3 and-36.3. |
| Auxiliary center retention | Supplied PA3x5 with one OD7/ID3.2 by0.5 washer seated against the fixed stub tip, servo-local Z-33.1. |

The auxiliary washer overlaps the disc's6.05 mm bore by0.475 mm radially. Its disc-facing surface remains0.7 mm away from the disc outer face at Z-32.4. The screw tightens the washer against the fixed stub; it must not squeeze the rotating disc. The washer reduces nominal screw insertion from5 to4.5 mm. Confirm actual screw length and blind-hole depth before tightening.

Production pitch auxiliary cheeks now have7.8 mm central access. This gives0.4 mm radial clearance around an OD7 washer and leaves1.4 mm between the center opening and each3.4 mm PCD hole. The yaw lower arm retains its7 mm central driver opening to preserve the thin webs between its peripheral counterbores. Install its disc and retention washer before fitting that removable lower arm.

The eight pitch-auxiliary peripheral screws per leg change from M3x6 toM3x8 and receive one additional thin washer each. The four yaw auxiliary screws keep their M3x20 length and two-washer stack. Twelve auxiliary-center OD7 washers are added across the robot. Main powered-horn screws, case-clamp screw lengths, bridge stacks and lower-post screw lengths remain unchanged; their revised coordinates are listed above.

## Combined case-to-shaft registration fixture

`r4_coupons.py` provides17 coupon shapes and a `build_coupons()` integration function. Three saddle variants have0.2,0.3 and0.4 mm end clearance. They include the actual mounting feet; their three cap shapes are identical and reusable.

The reusable registration plate fixes to the saddle's two X9/Y+20 and X9/Y-20 feet. Its feet sit on the saddle at Z-29. Two posts outside the case connect them to a plate whose underside is at the nominal main-horn outer face Z4.5. That plate has the real four-hole14 mm PCD and central7 mm screw access. It therefore tests the actual clamped case and actual shaft axis together.

Use two M3x12 screws, two plain nuts and four OD6 by0.5 washers for the gauge feet. Use the actual main metal horn and the usual peripheral M3x6 screws with thin OD6 washers. The upper plate includes tool openings above the two foot screws. The gauge prints inverted on its broad upper plate, with removable support beneath the two offset feet.

Insert the actual servo in the chosen saddle, fit the cap loosely, attach its actual main horn, then attach the registration plate and seat the four peripheral screws by hand. The case, frame and horn must meet without pulling a misaligned part into position. Tighten the case cap only after checking registration. If the horn's flat face does not meet the plate axially, measure the actual seating height and revise the height parameter; do not reinterpret the shaft-to-case X datum to compensate.

This fixture would reject the old2.385 mm case-to-shaft offset. Its digital check verifies the assembled nominal geometry and the misplaced-case rejection; physical screw fit remains the acceptance test.

## Auxiliary float and section specimens

The main and auxiliary horn fixture cheeks close with the38 mm bridge, one M3x50 screw, two OD7 by0.5 washers and a plain2.4 mm nut. The auxiliary cheek includes the actual1.1 mm lands and7.8 mm center opening. Install the actual auxiliary disc, OD7 center washer and supplied PA3 screw. Tightening the center screw must leave the disc free to turn. Close the bridge gently and check rotation again; bridge tightening must not eliminate clearance by preloading the disc.

The11.3,11.6 and11.9 mm yaw spacers bracket the current nominal stack. Use them to measure the actual case face, disc seating, fixed-stub projection and free rotation. These are test variants, not permission to force the longest stack into place. The top-bridge load specimens are cropped at the new positive-Z bridge location, and the post specimen retains the staggered nut windows.

The current production cable allowance follows the auxiliary face and the user's approximate plugged-profile measurement. Exact socket housing dimensions, lead routing and case-to-shaft datum measurements remain physical checks. Thin pocket floors and printed joint strength require the separate fixture load tests; this alignment set is not a strength qualification.

The frozen inward-study model and its comparison remain unchanged. Its old inherited coupon function is superseded by this R4 fixture module.
