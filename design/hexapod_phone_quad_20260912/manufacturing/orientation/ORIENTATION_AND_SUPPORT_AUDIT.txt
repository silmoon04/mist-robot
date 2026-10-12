# Printing orientation and support audit

Three production orientations should change: turn the supplied `power_distribution_tray`, `ubec_tray` and `coxa_upper_and_hip_saddle` STLs through 180 degrees about X. Keep the other existing orientations for the first physical fit build. The proposed rotations preserve assembled geometry. This audit itself did not modify CAD or production exports.

The audit covers all 33 production SKUs in `hex_quad_r2_landscape` and 330 orientation cases. Source manifest SHA-256: `d9bac35b0a898eb79191fd82129685c86f88caea7185f9766b5af6c3d78f5a67`. Results describe those exact bytes. Any later design revision needs a refreshed audit.

## Changes supported by the evidence

| Change | Measured reason | Assembly and fit consequence |
| --- | --- | --- |
| Flip `power_distribution_tray` and `ubec_tray` so their broad tray faces touch the bed | Their downward underside areas fall from 2,027 and 853 mm2 to zero. Bed contact increases from 100 mm2 each to 2,127 and 953 mm2. | No fastener or board position changes. Support is eliminated beneath the tray floors. |
| Flip `coxa_upper_and_hip_saddle` about the current STL X axis | Exact bed contact increases from 92 to 378 mm2. Actual slicing changes time from 156.8 to 156.5 minutes and total PLA from 29.31 to 29.19 g. | Source print rotation changes from X=-90 to X=90. The nominal long axis stays parallel to layers. Retest its case fit in the final orientation and inspect support near nut loading slots. |
| Correct support planning for `hex_faceted_cover` and `battery_tray` | Current orientations remain the practical choices. Their overhang columns occupy about 37.3 and 20.0 cm3 of air, chiefly below body-fixing bosses and battery tabs. | Remove supports before installing nuts, boards or the battery. If removal damages these interfaces, add local sloping ribs in a CAD revision rather than tilting either whole part. Ribs require connector, fastener and leg clearance checks. |

The cover guide currently mentions only nut recesses. The raised body-fixing bosses also need support. The coxa guide currently says broad cheeks are on the bed; its original orientation contacts the bed through only about 92 mm2 of narrow features. A brim and a first-layer preview remain appropriate after the flip, especially around separated support islands.

## Why 45 degrees is conditional

A 45 degree tilt is a change of layer direction and contact area, not a general strength improvement. The actual femur comparison makes the support tradeoff explicit:

| Femur orientation | Support angle from vertical | Predicted time | Total PLA | Support PLA |
| --- | ---: | ---: | ---: | ---: |
| Existing broad cheek down | 50 degrees | 172.4 min | 30.83 g | 3.58 g |
| Rotate 45 degrees about long X axis | 50 degrees | 154.8 min | 27.19 g | 0.32 g |
| Same rotated geometry | 40 degrees | 258.2 min | 41.54 g | 14.54 g |

At 50 degrees, Cura deliberately leaves the nominal 45 degree faces unsupported. Tightening the support threshold to 40 degrees changes the result substantially. The tilt also changes the femur's height from 42.0 to 48.8 mm and its ideal zero-height planar bed contact from 2,486 mm2 to zero. Real first-layer contact is finite because the first layer has thickness, but this remains an edge-start orientation. A model brim was not included in these slices. Test a diagonal coupon with the intended cooling and brim before considering this as a production alternative.

For a nominal tensile stress along a unit direction `a`, the normal traction on a layer with unit normal `n` is `sigma * (a dot n)^2`; the shear magnitude is `sigma * abs(a dot n) * sqrt(1 - (a dot n)^2)`. For the dominant long-axis bending fibres, rotating the femur about its long X axis keeps this nominal normal fraction at zero. Tilting about Y by 45 degrees raises it to 0.5. This is a stress-direction calculation, not a material strength ratio. Curved tibia regions, transverse bridges, horn fastener bearing and torsion have other local stress directions.

Broad-side printing keeps the main femur and tibia bending outlines in the layer plane. Raised transverse bridges still carry loads across their layer interfaces. A hollow shell, higher infill percentage or diagonal print does not by itself establish a safe load. The separate structural assessment must address the bridge roots, screw holes and load paths.

## Actual slicing

CuraEngine 5.13.0 completed 6 cases with a frozen numeric profile. Every movement stayed inside the nominal 225 x 225 x 265 mm envelope. The measured peak nominal deposition flow was 6.96 mm3/s. Source snapshots and extrusion accounting are in [the slicer comparison](slicer/SLICER_COMPARISON.md) and [validation](slicer/validation.json).

The profile uses a 0.4 mm nozzle, 0.20 mm layers, 0.42 mm lines, five walls, six top and bottom layers, 35% gyroid, 210/60 C PLA, and 20/35/60/80 mm/s first-layer, outer-wall, inner-wall and infill speeds. Support is normal zigzag at 15%, with a 0.6 mm roof at 60%, 0.2 mm Z separation and 0.5 mm XY clearance. These are recorded analysis settings, not a validated printer profile. The saved toolpaths are compressed evidence with every command disabled.

Across the three current integrated leg pieces, slicing predicts about 9.85 g of support per leg before any model brim. Four copies would use about 39.4 g of support. The coxa flip saves little filament; its benefit is adhesion. These figures exclude other robot parts and do not predict strength or physical support removal effort.

## Contact, access and dimensions

Red surfaces in the visual are downward faces above the bed at a conservative 45 degree threshold. The geometry screen does not know whether the printer can bridge a particular span. For example, small nut-pocket roofs and 3.4 mm fastener holes may be printable as bridges, but a support blocker should follow a successful coupon and an inspected layer preview.

Support that lands on another part surface can leave a second scar or obstruct a narrow opening. The screen records these lower contact areas and flags gaps below 6 mm. This is a tool-access warning, not a proof that support is trapped. Remove support before loading nuts, closing split cheeks or installing the phone. Fit coupons must preserve the final part orientation and settings at the interface being judged.

All current part footprints fit the physical 225 mm bed with a nominal 4 mm brim. The 208 mm cover plus brim needs 216 mm, so it should be printed alone and checked against the slicer's actual excluded edge, skirt and purge paths. The landscape phone frame is 83.5 x 164.5 x 12.5 mm in its current print orientation. Keep it on its rear face; the phone remains landscape and upright when assembled.

| SKU | Quantity | Current print dimensions, mm | Downward area, mm2 | Orientation and removal plan |
| --- | ---: | --- | ---: | --- |
| `body_deck` | 1 | 178.4 x 206.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `hex_faceted_cover` | 1 | 184.0 x 208.0 x 57.5 | 1065 | Keep current top face down. Support raised body-fixing bosses inside cover as well as nut recesses. Remove before assembly. |
| `pan_cover_spacer_1` | 1 | 8.0 x 8.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `pan_cover_spacer_2` | 1 | 8.0 x 8.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `pan_cover_spacer_3` | 1 | 8.0 x 8.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `pan_cover_spacer_4` | 1 | 8.0 x 8.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `battery_tray` | 1 | 112.0 x 71.0 x 32.0 | 860 | Keep current floor down. Local support below four raised tabs; strip support away from nut openings before fitting battery. |
| `power_distribution_tray` | 1 | 47.0 x 47.0 x 4.0 | 2027 | Flip X180. Broad tray top on bed; feet upward; no geometric support. |
| `servo_bus_adapter_tray` | 1 | 19.0 x 38.0 x 22.0 | 32 | Keep current. Local rail slots and relieved feet need preview; keep cable-tie access open. |
| `esp32_tray` | 1 | 19.0 x 33.6 x 22.0 | 43 | Keep current. Local rail slots and relieved feet need preview; keep cable-tie access open. |
| `ubec_tray` | 1 | 45.0 x 23.0 x 6.0 | 853 | Flip X180. Broad tray top on bed; feet upward; no geometric support. |
| `phone_pan_servo_saddle` | 1 | 68.0 x 50.0 x 22.5 | 937 | Keep floor down. Raised mounting feet and clamp tower undersides need preview; preserve case-seat dimensions. |
| `phone_pan_servo_cap` | 1 | 52.2 x 48.0 x 14.2 | 234 | Keep inverted. Inspect recessed features and raised shoulders; preserve case contact face. |
| `phone_pan_hub` | 1 | 48.0 x 58.6 x 5.0 | 80 | Keep current. Nut-pocket roofs are the local concern; preserve metal horn seating and flat foot attachment faces. |
| `phone_cradle_rear_frame` | 1 | 83.5 x 164.5 x 12.5 | 80 | Keep back down. Small nut-pocket roofs need preview; keep phone corner seats and nut faces clean. |
| `phone_cradle_lower_retainer` | 1 | 11.0 x 164.5 x 3.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `phone_cradle_top_cap` | 1 | 19.0 x 164.5 x 11.5 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `phone_cradle_foot_left` | 1 | 37.0 x 30.5 x 14.0 | 49 | Keep broad side down. Inspect horizontal screw holes; avoid support scarring of hub and rear-frame seating faces. |
| `phone_cradle_foot_right` | 1 | 37.0 x 30.5 x 14.0 | 49 | Keep broad side down. Inspect horizontal screw holes; avoid support scarring of hub and rear-frame seating faces. |
| `yaw_case_saddle` | 4 | 61.0 x 52.0 x 30.0 | 354 | Keep feet down. Inspect short internal ledges and transverse screw holes; support can obstruct case and nut fits. |
| `case_cap_yaw` | 4 | 61.0 x 27.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `coxa_upper_and_hip_saddle` | 4 | 104.5 x 55.6 x 31.5 | 1450 | Flip X180. Greater bed contact. Local support in clamp offsets and bridge; keep nut loading slots accessible. |
| `coxa_lower_auxiliary_arm` | 4 | 50.5 x 28.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `case_cap_hip` | 4 | 61.0 x 27.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `yaw_auxiliary_spacer_1` | 4 | 5.8 x 5.8 x 10.5 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `yaw_auxiliary_spacer_2` | 4 | 5.8 x 5.8 x 10.5 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `yaw_auxiliary_spacer_3` | 4 | 5.8 x 5.8 x 10.5 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `yaw_auxiliary_spacer_4` | 4 | 5.8 x 5.8 x 10.5 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `femur_main_and_knee_saddle` | 4 | 144.5 x 32.0 x 42.0 | 962 | Keep broad cheek down. Support raised knee saddle and transverse bridge; leave horn seating face clean. |
| `femur_auxiliary_cheek` | 4 | 93.0 x 32.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `case_cap_knee` | 4 | 61.0 x 27.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |
| `tibia_curved_main_and_foot` | 4 | 124.0 x 41.0 x 42.0 | 766 | Keep broad cheek down. Support elevated foot and bridge; remove from strap slot and transverse fastener access. |
| `tibia_auxiliary_cheek` | 4 | 75.0 x 39.0 x 4.0 | 0 | Keep current. No broad unsupported faces in the screen; inspect small holes in the slicer. |

## Method and numerical limits

`analyze_orientations.py` tests current, flipped X180, both X90 sides, both Y90 sides, and positive/negative X45 and Y45 rotations. All rotations are additional to the supplied print-oriented STL. The script checks watertightness and source hashes before and after the run.

Projected area sums downward triangle area multiplied by the magnitude of its vertical normal. Faces on the bed are excluded. The inclusive 45 degree result deliberately counts borderline diagonal faces; the stricter 50 degree result shows support-threshold sensitivity. Area sums can include vertically stacked faces.

A deterministic 0.5 mm XY grid intersects triangle planes and pairs each downward overhang with the closest upward surface below it, or the bed. The volume integral sums projected pixel area times free vertical distance after a 0.2 mm top gap. It is an air-column envelope: support density, roof thickness, XY spread, tree paths and slicer bridge rules are not modeled. It must not be read as deposited plastic volume.

The algorithm passed analytic flat-plate and raised-roof tests. Seven parts with small features were rechecked at 0.25 mm grid spacing. These checks do not validate mechanical strength, cooling, warping, support breakaway or physical dimensions.

| Part | Support envelope at 0.25 mm, cm3 | Change from 0.5 mm grid |
| --- | ---: | ---: |
| `hex_faceted_cover` | 37.292 | 0.5% |
| `battery_tray` | 20.042 | 0.4% |
| `yaw_case_saddle` | 3.125 | 1.7% |
| `coxa_upper_and_hip_saddle` | 7.316 | 0.2% |
| `femur_main_and_knee_saddle` | 10.559 | 0.1% |
| `tibia_curved_main_and_foot` | 11.431 | 0.3% |
| `phone_cradle_rear_frame` | 0.198 | 6.0% |

The largest relative grid difference occurs in small nut-pocket features. Use the exact projected area for orientation screening and actual slice previews for local support decisions. No support-removal force or service load has been experimentally established.
