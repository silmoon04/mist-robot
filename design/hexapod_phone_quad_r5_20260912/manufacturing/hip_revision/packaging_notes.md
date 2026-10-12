# Inward hip packaging

The selected hip points its case tail inward and uses 70 mm between the yaw and hip shafts. The earlier spacing was 50 mm. Keeping that spacing would put the inward case and its clamp in the yaw mechanism's space.

The new case footprint ends approximately 5 mm farther inward than the old outward case, after allowing for the longer coxa. The knee and foot frames move outward by 20 mm. The whole leg therefore needs new mass and motion checks; rotating the hip case does not establish a reduction in the whole leg's inertia.

The coxa keeps a central post, with a small triangular flange on its inner face. Moving the rear hip cap screw beside this post lets the removable cap clear the post without cutting through the main bending section. The flange reaches the lower arm and carries material around both staggered nut windows.

## Selected dimensions

| Item | Dimension in the coxa frame |
| --- | --- |
| Hip axis | X 70, Y 0, Z 0 mm |
| Rectangular post | X 24.5 to 33 mm, neck Y -8.5 to 8.5 mm |
| Inner flange | XY vertices (24.5, -8.5), (21.5, 0), (24.5, 8.5) mm |
| Flange height | Z -44 to 8.5 mm |
| Lower-arm post holes | (28.5, -4.5), (28.5, 4.5) mm |
| Lower-arm faces | Z -53 and -44 mm |
| Staggered nut windows | Z -41.5 to -38.9 and -37.5 to -34.9 mm |
| Rear hip cap screw | Servo coordinates X -38.915, Z -27.5 mm |
| Rear screw axis in coxa | X 31.085, Y -13 mm, parallel to Z |
| Rear screw access scallop | Radius 4 mm through lower arm and post below Z -18 mm |

The other two hip cap screws stay at servo coordinates (13.915, -23) and (13.915, -7) mm. All three remain M3 x 35 with the existing OD7 washers and nuts. The two post screws, horn mounting stacks, 11.6 mm yaw auxiliary spacers and 9 mm lower-arm thickness remain the same.

The hip cap is different from the knee cap. Its rear ear is narrowed beside the post and extended enough to support the full OD7 washer. Keep the parts labelled during assembly.

## Checks and limits

The final candidate passed 128 exact Boolean checks with no solid overlap. These include the supplier case exterior, five yaw positions from -22 to 22 degrees, the provisional plugged-cable space, all three hip cap washers and screw heads, and 7.5 mm diameter screw-extraction paths. Every printable part is one connected valid solid. Total solid PLA volume of the ten coxa-owned components is 43,258.36 cubic millimetres, including the four spacers.

The rear cap washer has 1 mm nominal clearance from the straight post neck. The access scallop is 0.25 mm larger radially than the checked extraction cylinder. The cable allowance retains the user's approximate 35 mm case profile, 1.5 mm cable addition and 2 mm extra clearance. Physical plugs, screw heads and printed shrinkage still need the complete coxa fixture test.

An independent mesh section scan found that extending the flange all the way to the lower arm removes the weak section at the upper nut window. With the preceding revision's 13.27 N peak foot normal force assigned fully to the post, the lowest scanned conditional margin is about 1.19 against the assumed 12 MPa printed PLA limit. That calculation includes the longer actual lever and a conservative stress multiplier. It is a section estimate, not a measured strength or a validated frame load-sharing model. Use the final R5 loads for the release assessment.

The historical `packaging_candidates.json` records rejected central-post attempts with the original unshaped hip cap. It is not the selected design. `packaging_candidate_final.json` records the current selected geometry.

## Assembly sequence

1. Insert the three hip clamp nuts from above, then seat the servo in the fixed saddle. Keep its auxiliary cable face toward the negative Y side.
2. Fit the custom hip cap from below. Start all three M3 x 35 screws with their OD7 washers, then tighten evenly. The closure gap must remain visible.
3. Fit the yaw horns and supplied center retainers using the established C018 stacks. Attach the upper carrier to the main horn.
4. Insert the two post nuts through the staggered side windows. Install the lower arm and 11.6 mm auxiliary spacers with the existing fastener stacks.
5. Check the rear hip clamp screw through the access scallop. Its washer and head must clear the printed post during insertion and removal.
6. Fit the hip-driven femur cheeks and their horn screws. Verify the inward hip cable pocket through the intended motion before fitting the complete leg to the body.

The component fits checked here do not replace the assembled body collision sweep or the physical fixture test. The root build owns those checks and the final print orientations.
