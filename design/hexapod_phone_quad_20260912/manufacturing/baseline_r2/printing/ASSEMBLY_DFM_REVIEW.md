# Assembly and print review

Reviewed the landscape revision `hex_quad_r2_landscape`, manifest SHA256 `d9bac35b0a898eb79191fd82129685c86f88caea7185f9766b5af6c3d78f5a67`, on 12 September 2026. This is a review of that baseline, not certification of subsequent geometry. Inputs were the actual print meshes, assembly preview, `leg.py`, `phone.py`, `body.py`, interface notes and manufacturing BOM. No physical assembly or slicer support calculation was performed.

The BOM contains 33 named export rows and 75 printed pieces. Twelve clamp caps share one shape, sixteen yaw spacers share another, and four cover spacers share another. Assembly names are useful, but a slicer shopping list should consolidate those identities.

## Load path and orientation

Toe force bends the curved blade, transfers through the tibia bridge into both cheeks, then through the supplied metal discs into the knee case. The femur cheeks and their clamp carry that load to the hip. The coxa post and supported yaw arm deliver it to the deck. The auxiliary disc provides a second support only if its seating and bridge width leave it free to turn. Tightening a bridge cannot correct the wrong disc stack.

The baseline femur bridge is only 5.97 mm by 6.8 mm across the cheek gap. Its 3.4 mm hole leaves a 1.6 mm lower ligament and approximately 1.27 mm minimum side ligament. This junction deserves attention before hollowing the broad cheeks. The tibia bridge is 12.5 mm by 10 mm with two closure holes; its abrupt meeting with the centered blade can concentrate lateral loads. The phone's separate feet already print with their L profiles in the layer plane. Keep their corners and bolt lands substantial.

Printing a broad cheek flat keeps its long bending load path within layers, but the integrated transverse bridge and offset clamp require accessible local support. A bolt-on clamp printed flat could improve underside finish and replacement, but adds at least one piece per affected joint, joining hardware and a new load-transfer interface. It is not an automatic simplification.

Projected downward-facing mesh areas are 1,433 mm² for the coxa, 962 for the femur, 766 for the tibia and 860 for the battery tray. These sum faces steeper than a 45-degree overhang, above 0.4 mm from the bed. They are screening values, not support volume. Rolling rectangular parts exactly 45 degrees can make this threshold score zero while leaving unsupported starting islands. Compare sliced layers, adhesion, horn-face finish and removal access before choosing that orientation.

## Three proposed changes

1. Enlarge and blend the femur bridge around its closure hole and add short gussets at abrupt bridge roots where the servo and connector reserves allow. Keep the cheek seating planes unchanged. This adds little local material and no assembly pieces. Recheck actual moving geometry and tool clearance.
2. Replace the battery tray's elevated rectangular tab undersides with chamfered gussets rising from the sidewalls. This keeps the piece count unchanged, reduces support below four attachment points and spreads tab bending into the wall. Keep the nut-loading openings accessible. Lightweight the tray's broad floor only after retaining ribs between straps and attachment points.
3. Consider one open-center four-hole yaw spacer carrier instead of four loose spacers per leg. This could reduce 75 pieces to 63, while preserving the selected spacer length. Keep the central auxiliary retaining screw accessible and avoid contact with the rotating case. The carrier needs a new fit coupon; it is a proposal, not an approved substitution.

## One-leg assembly findings

Load recessed clamp nuts before inserting the servo. Fit and retain its metal discs, attach the powered cheek, then assemble the separate auxiliary cheek. Load the coxa's two nuts through opposite side slots before fitting the lower arm. Close the femur and tibia bridges only after checking free disc rotation. Finally insert leads and sweep manually with torque disabled before multiplying the assembly by four.

The selected clamp stack is M3x35 with one 0.5 mm head washer and the recessed plain nut. It projects 1.77 mm beyond the 32.73 mm rail span; verify that tip through the unloaded sweep. The selected M3x6 horn stack uses a 0.5 mm washer, leaving 1.5 mm nominal engagement through the 4 mm cheek into the 2.1 mm auxiliary flange. Exact owned screw lengths, heads and quantities remain unresolved.

The preferred bridge revision removes the captured-nut recess and restores the full 4 mm cheek. Put one plain external nut and an OD6 washer on that face, retaining the existing screw-side OD6 washer. The nominal stack is 46 + 0.5 + 0.5 + 2.4 = 49.4 mm, leaving 0.6 mm emergence with M3x50. Merely placing an external washer over the existing cavity would preserve the weak floor. No new screw or nut is required; the second washer adds one item per bridge. The tibia's 7 mm hole spacing excludes ordinary OD7 washers. Use heads and washers no larger than 6 mm, and check a slim socket, small spanner or pliers can grip each nut without bearing on the printed cheek. The outward faces clear the local servo envelope, but actual tools and hardware still require a swept assembly check.

The accompanying `fastener_mass.py` counts 225 screws, including 25 supplied retainers, 100 nuts and 180 washers for those selected stacks. Its distributed estimate is 259.214 to 372.112 g, with a nominal 318.243 g. This replaces the previous 50 g fastener allowance. Keep the separate wiring allowance until weighed. See `fastener_mass.json` for assumptions, per-link centers and inertias, and the possible overlap between supplied-retainer mass and the stated bare servo mass.
