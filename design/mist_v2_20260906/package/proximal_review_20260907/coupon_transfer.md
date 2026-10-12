# First fit-bed transfer audit

7 September 2026. The original seven-object bed is a useful fit ladder, but it does not cover the revised proximal-femur assembly by itself. The revised candidate is prepared separately in `coupons/bed1_proximal_20260907/`. The original `bed1`, recipe and feedback remain protected. The parent task authorized a fixed coupon contract so this first bed can be completed while the leg CAD is built. The new leg must adopt that section or record a mismatch before its fit results transfer.

The source bed has seven valid, separate objects inside 206 x 202.5 x 10 mm. Its manifest and feedback each contain 74 entries; every result is `not_tested`, and measured dimensions are blank. No physical result was inferred from a CAD dimension.

## Coverage of the original bed

| Interface | What exists | Transfer limit |
|---|---|---|
| Bearing OD | Four diameter offsets for OD8, 10, 11, 13, 14, 19 and 22 | Boss OD is bearing OD +8 mm. The revised R17/OD34 carrier differs from the OD30 test around a 22 mm bearing. |
| Bearing axial seat | Actual bearing width +0.2 mm pocket; 1.2 mm floor; 0.6 mm entry lead-in; print axis Z | A different shoulder, straight-bore length, chamfer, outer wall, nearby plate or print axis requires a matching section. |
| Metal shaft clearance | Diameter 3 to 8 mm, three clearances each, through a 2 mm printed wall | Does not test a long bore or a metal shaft's fit in a bearing inner race. Test those bought parts directly. |
| Screws | M3/M4 hole ladders in 4 mm walls | Does not test an 8 mm-deep steel-sleeve seat or the four-hole 16 mm pitch circle. |
| Nuts | Shallow M3/M4 nut traps, plus insert pilot ladders | Does not reproduce the long horizontal 7.2 mm AF coupling-nut pocket, its plate insertion path or slider clamp. |
| Shaft clamp | Two jaws around an 8.30 mm printed bore | Checks clamp fit and access only. It is not the revised shaft-end screw, inner-race spacer or pulley torque interface. |
| Bearing keeper | One 624/13.40 mm seat and separate cap, two holes 25 mm apart | Does not establish 627/608 race clearance or the new keeper bolt locations. |
| Servo | Two case-width openings, 25.23/25.43 mm | Does not test full case depth/length, horn offset, clamp preload, cable exit or a new motor orientation. |
| Belt | Short 2 and 3 mm pitch ticks | Does not test a GT tooth profile, working engagement, belt width or 139.5 mm shaft-centre distance. |
| Long scale | No dedicated datum | Local bore compensation cannot reveal a long X/Y scale error. |

The original carrier's entry chamfer consumes the top 0.6 mm of the stated pocket depth. For a 7 mm-wide bearing, the 7.2 mm total seat has about 6.6 mm straight wall below that lead-in. A 7.2 mm plain bore is a different contact section. Preserve the actual section when transferring a successful fit.

## Revised candidate and retained interfaces

Retain all seven handled objects and every original test surface. Extend object 06 into a connected frame, with detachable keeper and face-pattern specimens attached away from their working surfaces. The main frame must remain intact for scale measurement. Measure it before separating the assembly specimens.

The target envelope is no more than 216 x 216 mm, leaving 4.5 mm per side when centred on a 225 mm bed. That is the total available border, not an additional allowance for an arbitrary brim or purge line. The new 3MF is geometry only; verify the actual slicer's brim and printer exclusions inside the configured usable bed.

The prepared placement preserves the original coordinates. New horizontal and vertical rails sit near Y213 and X213. Raised 5 x 5 mm datum pads at (73.5,213), (213,213) and (213,73.5) give exactly 139.5 mm X and Y centre distances. Their nominal outside span is 144.5 mm and inside span 134.5 mm, both within a 150 mm calliper. The measurement faces stand above the connecting rails so those rails do not obstruct the inside jaws.

Spare regions carry actual revised bearing sections, the matched keeper, an 8 mm face-pattern wafer and a same-depth sleeve ladder. The live retention recipe uses four 6.6 mm sleeve-seat bores on a 16 mm pitch circle for metal sleeves of OD6.5, ID4.3 and length 8 mm. These are different from ordinary 4.4 mm M4 clearance holes. The wafer tests sleeve insertion, bolt-circle alignment, head access and length flushness with real hardware; it supplies no gear-strength or pulley slip-torque evidence.

The new slider has a 4.4 x 8.4 mm slot through a 4 mm plate. The coupling-nut trial must reproduce the actual horizontal print direction and long pocket, not stand the nut on its end to make printing easier. Its 18 x 18 x 2 mm load plate needs an explicit side-entry opening. An enclosed plate cavity accessible only through the screw bore and nut pocket cannot be assembled.

The fixed `interface_contract.json` specifies an OD34 x 8.4 mm carrier, 20 mm through opening, 1.2 mm floor and 7.2 mm straight seat with no lead-in. Its three seat diameters are 22.25, 22.40 and 22.70 mm. The matching keeper is OD34/ID20 x 2.4 mm; both pieces use two 3.4 mm screw holes 28 mm apart. The 8 mm face wafer reproduces the printed tibia adapter's 8.2 mm centre bore and four 6.6 mm sleeve seats on 16 mm PCD. Its minimum 0.6 mm inner ligament is a fit specimen, not an approved load path.

The contract status is `fixed_coupon_contract_pending_leg_adoption`. No physical measurements or manufacturing qualification are implied. Each new fit family has its own feature ID. A result from this plain-seat OD34 carrier must not silently overwrite the original chamfered OD30 bearing ladder's compensation. Keep the new profile's no-lead-in choice explicit when the leg adopts it.

The revised bed has now been exported and independently checked. It contains seven valid solids, 87 feature records and an 87-row blank feedback sheet preserving the original 74 rows. The actual STL/3MF envelope is 216 x 216 x 22 mm, with 2 mm minimum separation and no inter-object overlap. STEP re-import returned seven valid solids. The leg source now adopts the carrier and keeper profile and embeds the contract hash; confirmation against the final leg solids remains pending. `MEASURE_FIRST.md`, `FEEDBACK_MAPPING.md`, `leg_adoption_status.json` and the validation records accompany the files.

The independent mesh/3MF verifier exited successfully. CadQuery completed the exports, checks and renders, then failed during native shutdown; `execution_status.json` preserves that failure. The output checks do not imply a clean native process exit.

## Long X/Y scale measurement

Keep the frame flat and use light, repeatable calliper force. Measure the outside and inside spans between each pair of raised pads, at the same height. Repeat after turning the calliper around. For each axis, calculate `C_measured = (outside + inside)/2`. Averaging these spans removes the pads' combined width from the centre-distance result. Do not assume that either printed pad is exactly 5 mm wide.

Record the raw spans before calculating a scale factor. A descriptive factor is `139.5 / C_measured`; it is not an instruction to change printer motion steps after one print. Keep material shrink, slicer scaling and local hole compensation separate. Horizontal hole expansion changes bores and outlines; it is not a substitute for correcting an observed centre-distance error.

At 139.5 mm, a 0.2% scale error changes the centre distance by 0.279 mm; 0.5% changes it by 0.698 mm. With equal pulleys, the nominal pitch-path change is twice that amount, 0.558 or 1.395 mm. The real belt also has manufacturing variation and tension requirements. The new slider's stated -1 to +3 mm motion changes the belt centre distance in the opposite direction; its adjustment range does not excuse ignoring the printed scale error.

A thin gauge does not reproduce all cooling and warping of a full femur or carrier. It detects a gross axis-scale problem and gives evidence for the next revision. Inspect the actual link centres when the first leg is printed. Do not claim that the gauge establishes belt tension, structural straightness or a 0.05 mm rotor endfloat.

## Two feedback rounds

Use the intended final material and relevant print orientation on the first bed. A PLA result is not automatically a PETG result. Record nozzle, layer height, wall count, line width/flow and XY compensation. Measure the actual bearings, shafts, sleeves, screws and nuts before selecting a printed fit.

The first round should identify the successful local holes, confirm the actual carrier and keeper together, fit the sleeved 16 mm bolt circle, check the shaft-retention hardware and measure both long axes. Keep every unsuccessful result. Tightness requiring impact, a dragging bearing after retention, a sleeve longer than its intended compression stack, blocked tool access or an inaccessible nut/plate is unresolved.

The second round should contain only failed or ambiguous interfaces and one assembled representative stack using the selected values. Do not generate it before measured first-round feedback. The existing generic refinement builder does not automatically know the new carrier section, sleeve family, horizontal nut pocket or long-axis datums. Their second-round geometry must preserve these new sections and measurements explicitly.

Two rounds are a practical plan, not a guarantee that unknown hardware or a changed design will fit in two prints. Avoid changing the material, carrier section or attachment architecture between them. Leave measurements blank until made. The first bed cannot validate metal machining tolerances, transmission slip torque, bearing capacity, gear fatigue, print strength, heat, stairs or powered motion.

## Separate gear-release gate

The original module-1 20T pinion with an 8 mm face fails the project's provisional 10 MPa tooth-bending screen. Boston Gear's 20-degree full-depth Lewis factor is Y=0.320 for 20 teeth. At the supplied 0.728/1.335 N m shaft torques, `sigma = Ft/(b*m*Y)` gives 28.44/52.15 MPa before dynamic factors. The 10 MPa value is an analyst-selected FDM screen, not a tested material property. [Boston Gear engineering information, printed page 311](https://cdn.mscdirect.com/global/images/ProductDataSheet/pds_sku_1635039_charts_referenceimages_unclassified.pdf#page=6)

The generated pinion also leaves only about 0.079 mm between a horn-hole boundary and the tooth-root outline. Its root has no generated fillet. A wider face does not repair that near-zero web. The new knee stage has moved to a conditional 25:50 metal-gear direction; the original yaw/hip printed 20T stages still require resolution. Passing this fit bed is not permission to print and load those gears.
