# R7 single-leg print release

Build one complete direct-drive leg and a rigid bench mounting plate. Preserve the successful STS3215 C018 case pocket, inward hip/knee layout, straight tibia and 82/90/105 mm joint lengths after the wider-yaw revision. Do not print the full robot shell or duplicate four legs in this stage.

Incorporate the operator's feedback: case fit and clamped retention reported good; regular support obstructed screw holes; the revised roofed saddle worked; the M3x30 test bridge assembled but its nuts required hammering. Forced nut insertion is a defect to correct, not an accepted fit. No quantified powered/load/thermal result has been reported.

All production fasteners must be M3x30 or shorter, except supplied special centre retainers. The user also has shorter screws. Retain correctly sized metal horns, auxiliary discs and washers. Enlarge nut seating/entry locally with retained antirotation flats; never globally scale the fitted case or assume an unmeasured nut dimension.

The user's photographed assortment lists M3x4, x6, x8, x10, x12, x18, x20 and x30 socket screws, M3 nuts, flat washers and split lock washers. Their longest screw measures approximately 32.5 mm overall with a 2.5 mm head, consistent with 30 mm under the head. Head diameter, nut across-flats width and nut thickness remain unmeasured. Do not infer nut dimensions from the screw head. Do not require M3x16 screws, which are not listed in this kit. Use flat washers in the specified stacks; split lock washers are not equivalent spacers.

Subsequent nut measurements: approximately 5.2 mm across flats, 5.8 mm across corners and 2.2 mm thick. These supersede the initially unknown nut size. The corner-to-flat ratio differs slightly from a perfect regular hexagon; preserve the approximate nature of the readings. Final nominal pocket AF is 5.6 mm, and side-entry thickness is 2.7 mm. The pocket AF remains below the reported corner width to resist free rotation. A gentle actual fit check in the first full part remains necessary.

Use actual production leg pieces as the next test article, not another broad coupon plate. Check valid solids, assembled interference, nut insertion and screw entry, cable reservations, sampled motion, printing orientation, layer support and fastener load paths. Export editable CAD/STEP, individual oriented STLs, staged 3MF plates, a matched Cura profile, assembly instructions and a clear preview. Record physical limits separately from digital checks.

The mounting plate is for external restraint at a bench edge. It must leave the servo underside, cable and moving lower yaw arm clear. The bench and clamps are external fixtures, not simulated robot components.

Release only a source-consistent package. Any remaining geometry or access failures must be corrected or disclosed as a blocking issue, not hidden by a nominal simulation pass. Powered commissioning starts with a restrained, unloaded leg and verified IDs, direction and limits; no automated hardware actuation is part of this task.

Final washer measurement: kit flat washers are approximately 7.7 mm outside diameter. Final lower yaw arm recesses are 8.2 mm diameter and auxiliary centre access holes are 8.4 mm. The four bench mounting screws have no top washers because OD7.7 washers clash with the servo clamp; fit one washer below the plate under each nut. The operator has not confirmed washer thickness; the specified screw engagements assume 0.5 mm.

Wider-yaw steering: replace the 70 mm coxa with an 82 mm coxa and matched post/lower arm, trim the bench front corners, use provisional yaw limits of +/-55 degrees, and test a +/-60 degree guard. Compare yaw inertia and vertical-load bending instead of assuming that a wider angular range reduces motor torque. Recheck the whole leg and update Fusion, URDF, prints and guidance together.

R7 pitch revision: keep servo case fit and inward case orientation; use hip limits -30 to +65 degrees and knee limits 5 to 115 degrees. Check five-degree guard combinations. Auxiliary cheeks are 5 mm thick, with inner face Y=-22, outer face Y=-27 and integral annular stand-off 4.1 mm long, OD19.8 mm and centre opening 8.4 mm. Use M3x12 with two 0.5 mm flat washers on the pitch auxiliary discs; keep main M3x6 and bridge M3x30. Bridge captive nut slots shift to Y=-1.5..1.2. Relieve the knee end of the femur to radius 28 mm through the main cheek and ribs. Reinforce the rear bench rails for the longer reach. Report smoothness separately from angular range.
