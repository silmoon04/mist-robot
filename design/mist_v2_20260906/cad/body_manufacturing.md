# MIST body candidate

The body recipe creates 26 printed parts and seven hardware/display references. The last OpenCascade replay produced 33 valid single solids, with zero positive-volume intersections between body components and zero ineffective cuts. Those checks cover the body at its assembly pose. They do not cover the four moving hip modules, fastener access, cables, or a physical fit test.

The original-show reference was viewed at `misc/mist_face_extraction/sources/misc.png`. The design keeps the white upper barrel, grey lower region, twin lid bands, shallow crown, bridge handle, black square face and smaller dark panel below it. The tall phone sits inside the barrel; the white shell masks the unused screen area. The broad lower openings are reserved for the remote-servo hip pods. They leave more of the core visible than the show reference, so the lower cosmetic covers remain unfinished until the moving pods are integrated.

## Files and coordinate system

- `body_native.py` defines `build_body(root, params) -> {occurrence, components, bodies, spec, status}`. It creates native Fusion sketches, extrusions, revolutions and explicit Combine features through `native_parts.py`.
- `export_body.py` replays the same recipe in CadQuery/OpenCascade. This produced `output/MIST_body_candidate.step` and `output/MIST_body_candidate.glb`.
- `output/body_geometry_report.json` records each solid's volume, bounds, centre, mass assumption and interference result. `output/body_recipe.json` is the exact dimensional recipe.
- `output/body_preview.png` is a software render of the generated geometry. The GLB viewer is preferable for occlusion and close inspection.
- `output/candidate_parts_not_print_release/` contains exactly the 26 current part STLs, in assembly coordinates. It is not a sliced plate or a released parts set.

All recipe dimensions are millimetres above the body bottom. The body occurrence translates down by 35 mm to put the hip yaw plane at the simulation origin. Forward is +X, left is +Y, up is +Z. The barrel is 180 mm in diameter and 220 mm high; the lid and handle reach 260 mm overall. The face bezel extends to X=99 mm and is 94 mm wide by 86 mm high.

The native recipe is prepared but has not executed in Fusion while the application is blocked at sign-in. Its geometric dimensions are generation-linked to the recipe; this is not yet a completed Fusion document with every dimension driven by a named user parameter. Color attributes accompany native parts, while the offline STEP/GLB assemblies carry actual colors. Physical material assignment and a native Fusion mass check remain open.

## Mass and placement used by the simulation

The CAD estimate uses 1.27 g/cm3 for fully solid PETG. It is a conservative geometric estimate, not an instruction to print every part at 100% infill. Replace it with slicer estimates and weighed parts after choosing wall counts and infill.

| Group | Mass | Centre relative to hip plane, mm |
| --- | ---: | --- |
| Printed body excluding face cassette and bezel | 706.208 g | (-5.696, 0.005, 82.320) |
| Face cassette B13 plus bezel B14 | 63.555 g | (82.390, 0, 102.277) |
| Mi 9 SE face phone, assumed | 155 g | (73.775, 0, 105) |
| Face phone plus its two printed mounts | 218.555 g | (76.280, 0, 104.208) |
| Battery, repository envelope | 174 g | (-25, 0, -14.5) |
| Brain phone, provisional envelope | 155 g | (0, 0, 34) |

All printed body parts together weigh 769.763 g by this method. The simulator must use the first and fourth rows as separate groups; adding the 769.763 g total to a phone-with-frame mass would count the frame twice. Fasteners, straps, boards and wiring are outside the printed-body estimate.

The known Mi 9 SE is provisionally assigned to the face. Its 147.5 x 70.5 x 7.45 mm envelope sits in portrait orientation, with 0.4 mm nominal pocket clearance per side. The visible phone region is 64 x 68 mm. The recessed screen limits viewing at oblique angles and must be tested with the actual active-screen boundary, case, buttons and app orientation. The model does not prove those dimensions are correct for a second phone.

The unknown brain phone has a 75 x 155 x 10 mm envelope laid flat, with its long axis across the body. Rotating it 90 degrees from an earlier layout removed an actual phone-on-phone collision. The battery envelope is 104 x 34.5 x 24.5 mm, on two rails near the bottom. Its forward/rearward rail position can be adjusted later to trim the assembled centre of mass.

## Structure and assembly order

The lower deck takes the leg-root loads. The 2.4 mm shell walls are cosmetic. The four 10 mm OD spacer stacks separate the lower deck, the phone deck and the upper locating ring. A continuous M3 tie rod through each stack is the proposed clamp; suitable rod, nuts and washers are not confirmed in the existing inventory. Leg-root tabs currently have 4.4 mm bores at radii 78 and 98 mm. These are provisional interfaces, not a verified match to the leg cassette.

1. Print and measure the coupons before releasing the body interfaces. The rail slots assume 15 mm straps, phone pockets assume 0.4 mm clearance per side, and the lid spigot assumes 0.35 mm radial clearance. Each assumption needs its own result.
2. Fit the lower-deck hardware, then bolt on the two battery rails. The pack sits against padded contact faces and is retained by two straps. Keep the battery connector and main disconnect reachable from the rear opening.
3. Add the lower spacer sections and phone deck. Fit the brain phone and its strap before the upper spacers and ring. Leave its charging/data connector and cooling area clear.
4. Route the four fused power and data branches through the lower openings. Add strain relief to the structural core. The present geometric model does not include a proven cable loom or plug insertion sweep.
5. Install the face cassette from the open top and plug it in through the lower central cable relief. Fit the separate bezel and lower fascia. A positive cassette lock, board-specific mount holes and all shell seam attachments still need final design.
6. Fit the cosmetic shell halves and slip-on bands after the hip-pod interference sweep. Fit the lid and screw its bridge handle through the four holes. The handle removes the lid; it is not a lifting point for the robot.

Printed blind insert bores have deliberately not been invented for the body. The user's insert OD, length and installation behavior are still unknown. Existing holes are clearance bores or explicit provisional interfaces. The coupon results should define inserts before the final seam and cassette fasteners are modeled.

## Print orientation and remaining checks

The 180-184 mm circular parts fit the stated 225 x 225 mm Neptune 4 Pro bed. Print decks flat, shell sections with their lower rims on the bed, and the lid with its rim down. Print the handle on its broad side so the arch follows the layer plane. Compression spacers can print upright with through metal ties carrying tensile loads. Loaded root attachments need a separate bending and layer-strength review; the body shell must not become an accidental structural load path.

The shallow lid has a closed crown and needs a slicer check for bridging or support inside it. Phone-cassette ribs, cable exits, narrow bridges around the face opening, screw-head access and assembly tool clearance are not established by a solid-intersection check. Recheck them in the actual slicer and in the coupon material. PETG is the structural candidate; the assumed modulus, heat behavior and layer strength have not been measured for the user's printer.

The export script completed all geometry and artifact writes, but the shared CadQuery runtime returns process exit code 1 during interpreter shutdown without an error message. A minimal script that imports CadQuery and calculates the volume of a 1 x 2 x 3 mm box also prints 6.0 and exits 1. This runtime condition is separate from the recorded geometry checks; it remains unresolved and must not be reported as a clean process exit.

The next CAD gate is the complete four-pod assembly sweep against these body parts. Then finalize the service joints, actual hardware mounts and two phone interfaces, repeat the mass calculation, and regenerate the native Fusion document and print plates from the approved coupon values.
