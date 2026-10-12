# R5 assembly and print review

Use the R5 files and [R5 fastener stacks](R5_FASTENER_STACKS.md). The R4 design remains in its separate directory. Its access routes, local section limitations and numerical load results are not a qualification of the revised R5 mechanism.

R5 reverses the hip case inward and increases yaw-to-hip spacing to 70 mm. The lower-arm post bolts move to X28.5, Y±4.5, and the upper coxa includes a full-depth triangular flange. The hip cap is a dedicated part: its rear screw is at servo-local X=-38.915, Z=-27.5. A generic yaw or knee cap is not interchangeable with it.

The 105 mm tibia is straight and uses a short auxiliary cheek. Its bridge bolts are at X36 and X44, both Z0. User-facing display names identify the new parts; an internal SKU may retain its older curved wording for compatibility.

The dedicated revision-check plate contains five complete reusable production first articles: upper coxa/hip carrier, lower arm, hip cap, straight tibia main/foot and short auxiliary cheek. Test them together with the real cases, discs and screws. A passing undamaged specimen can count toward the production BOM. The old cropped post coupon is not included as a surrogate for the complete R5 frame.

These five selected specimens are not the complete change set. The [change audit](../manufacturing/slicing_r5/R5_CHANGE_AUDIT.md) records seven changed SKUs, including the R5 femur auxiliary cheek with its inward-hip cable reserve and the R5 body deck with revised reliefs. Use both R5 parts when completing the supported leg and body assembly; do not substitute their R4 versions. Their production BOM quantities remain unchanged.

Preload clamp and staggered post nuts into bare carriers before fitting servos or surrounding links. All three hip nuts enter from above; their bare-carrier entry and seated positions passed the R5 digital check. Both hip and knee cap screws enter from below. Verify the dedicated rear-bolt path, nut restraint and driver withdrawal. Install the yaw auxiliary disc and its centre washer before closing the removable lower arm. Complete leg modules before body mounting, and tighten pan-body and servo-cap screws before installing the horn/hub.

The denser yaw sweep passes 312 BRep distance checks across four legs at every integer angle from -19° to +19°, against the deck and fixed saddle. The minimum deck gap is 1.57 mm, exactly 1.573865 mm at 18°, above the 1.5 mm target. The fixing-hole ligament remains 3.747382 mm. The previous failed sweep remains under manufacturing/clearance_revision. This establishes discrete digital clearance, not printed clearance or a deck-strength rating.

Final yaw operation is limited to ±19° to retain a 1.61054 mm nominal gap to the fixed saddle. At ±22° the remaining 0.656 mm gap fails the minimum-clearance criterion despite no solid intersection. The limit update changes no printed parts, quantities or mass estimates.

Pitch auxiliary screws remain M3×8 with TWO OD6 ×0.5 mm washers and 1.1 mm integral lands. Yaw screws use M3×20, paired OD6 washers, 3.5 mm counterbores and nominal 11.6 mm spacers. Both peripheral arrangements leave only 0.2 mm nominal rear margin. Auxiliary centre retainers use the specified OD7 washer against the fixed stub; check actual blind-hole depth and free disc movement. The bridge closures use external plain nuts and paired OD7 washers, with 1 mm nominal separation between adjacent washers at the 8 mm bolt spacing.

[Current production slicing](../manufacturing/slicing_r5/output/PRODUCTION_SLICING.md) covers 34 SKUs and 76 pieces: approximately 1.056056 kg deposited model PLA, 55.8 g removable support and 1.1 g adhesion. Individually sliced jobs total 105.4 predicted hours. Packed plates require their own slice. The [mass comparison](assembled_mass_comparison.json) gives 2.756962 kg deposited-material assembly mass and 2.936135 kg full-solid comparison mass. Infill percentage is not a mass multiplier, and neither mass scenario proves strength.

The complete 70 mm coxa load fixture must retain the actual upper yaw attachment, lower arm, triangular flange and hardware. Apply small measured vertical force at hip X70 and independently reversible Y torque, recording displacement, twist and residual set. The longer lever and new support topology need R5 evidence. Test the straight-tibia bridge and both lateral directions as an assembled unit. Do not carry the former R4 Z=-25 access-cut interpretation into this geometry.

Follow [PRINT_AND_ASSEMBLE.md](PRINT_AND_ASSEMBLE.md) for staged fit, load and creep checks. Stop for forced alignment, binding, screw bottoming, roof lift, cracking, whitening, slip, progressive deflection or permanent set. Full physical fit, load capacity, fatigue, warm behavior and long-duration standing remain unqualified until measured.
