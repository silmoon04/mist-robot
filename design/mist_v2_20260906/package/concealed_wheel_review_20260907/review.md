# Concealed wheel drive: silhouette and mechanical review

7 September 2026. Use the longitudinal upper-tibia motor arrangement as the next candidate. It can remove the visible foot motor while keeping the broad, faceted shin seen in the recovered MIST views. The motor, shaft support and right-angle transmission must occupy that leg envelope together. A casing around the existing foot outrigger would retain the unwanted shape and mass.

This bounded review reads `review/reference.png`, `references/original_mesh_four_views.png`, the 657-part proximal candidate's leg render/report, the existing wheel study and the leading dimensions supplied by the leg implementation agent. The recovered mesh image is a visual reference: its historical model units and earlier scaling assumption do not supply trustworthy manufacturing dimensions. No purchase or new wheel-motor budget is assumed. `envelope_screen.py` and its JSON record the arithmetic comparisons.

## Shape to preserve

The references show a broad flat shin face with chamfered edges, a compact dark knee joint and a clean lower foot. The shin is a continuous leg segment. Motors and cable loops do not project as separate cylinders or boxes from the foot. A narrow removable side seam and an inward-facing ventilation strip can fit that shape.

Keep the main side-view facade about 40 mm wide for this first enclosure study, with a short chamfer at the knee and a taper toward the wheel support. That is a design target around the existing 130 mm tibia, not a dimension measured from the screenshot. Review the front, side, rear and oblique views with the 180 mm barrel present. An outboard bulge can disappear in one view while remaining the dominant shape in another.

The implementation agent's leading target is approximately 40 mm in the leg plane by 65 to 70 mm across the wheel axis. This is already broader than a narrow bare cheek. Freeze the envelope only after the bearing caps, screws, encoder connector and miter-gear hubs fit inside it. Keep the removable cover flush with the structural outline rather than adding an external pod to accommodate an omitted component.

## Motor and structure actually fit only after these changes

Use `u` down the tibia from the knee, X in the leg plane and Y along the wheel axle. The leading contract places the FIT0493 case at u20 to 81 mm, its 12 mm shaft at u81 to 93, and the motor axis at X0/Y20. The wheel axle remains at u130. The gearbox face is at u81; the encoder and cable exit are at the proximal u20 end.

FIT0493 remains a conditional reference. Its 61 mm case/encoder envelope, 12 mm shaft and 25 mm maximum diameter require real space even when hidden. Its 98 g mass also remains in the model. A simple illustrative enclosure around the bare motor needs about 31 mm cross-section and 79 mm length with 1 mm gaps and 2 mm walls, before coupling, cable or right-angle-drive space.

| Constraint | Result and action |
|---|---|
| Current inner cheek gap | Y-16 to +26 mm, 42 mm total. The proposed motor reaches Y32.5, intruding 6.5 mm beyond the positive inner wall. Move or redesign that wall. |
| Motor bay alone | Positive inner wall at Y33.5 gives 1 mm motor clearance. Keeping a 6 mm cheek and 1.6 mm covers gives about 66.7 mm overall width. This excludes the lower gear/retainer stack. |
| Existing cross ties | X+/-9 at u48 and u75 pass through the proposed motor cylinder. Route new ties and ribs around the bay; deleting them without a replacement loses load sharing and torsional restraint. |
| Narrower outside ties | X+/-17 may clear the motor with small metal spacers. The old 6.8 mm-OD printed spacers extend to X+/-20.4, already outside a 40 mm shell before cover allowance. Model actual spacers and bolt heads. |
| Shaft extension | The motor shaft ends 37 mm before the wheel axis. Use a supported extension/coupling with an explicit bearing arrangement; the 4 mm motor shaft cannot become a long foot-load spindle. |
| Positive wheel bearing near Y40 | Specify whether 40 mm is a bearing face or centre. A centre at Y40, followed by an outward keeper, screw head, running gap and cover, can produce about 75.6 mm overall width in the illustrative stack. Internal retention or another arrangement may reduce this. |

Retain a real pair of wheel bearings to react wheel impacts, lateral forces and overturning moment. The present 626 pair has faces at Y-22 to -16 and +26 to +32, with 48 mm between centres. Changing that stack changes wheel-axle bending and deflection, so update its load screen and shaft length with the new faces.

## Right-angle drive, belt alternatives and forces

The chosen longitudinal motor needs a genuine 90-degree turn into the transverse wheel axle. The leading concept uses a 6 mm extension and a 1:1 miter pair near u130/Y20. Import the actual supplier gear dimensions and mounting distances before finishing the lower shin. Pitch-cone geometry, hub length, bore attachment and gear retention determine whether the pair fits; two cosmetic cones are insufficient.

The extension needs its own radial support near the miter stage. Both shafts also need a defined axial reaction path because bevel gears produce thrust. Keep these forces out of the motor's undocumented gearbox-bearing capacity. A support arrangement with both bearings above an overhung pinion still needs its overhang moment and reversed bearing reaction checked. Axial shoulders, spacers and retainers must locate the gears without dragging the races or shifting mesh under reversal.

For an ideal 1:1 straight miter pair with 20-degree pressure angle, each radial/axial component is approximately 25.7% of tangential tooth force. The mean pitch radius, rather than an arbitrary outside radius, sets `Ft = T/r`. This agrees with the manufacturer's force table. [SDP/SI metric gear technical reference, Table 16-2](https://sdp-si.com/D815/D815-Technical-Section.pdf)

At an illustrative 10 mm mean pitch radius, the earlier provisional 0.1719 N m wheel-drive ceiling gives 17.19 N tangential and 4.42 N radial/axial force. The 1.1768 N m stall reference gives 117.68 N tangential and 30.29 N radial/axial force. These are load scales, not a gear or bearing rating. The current limit is still unvalidated, and stall is not a continuous operating point.

A transverse motor just below the knee would allow a simple belt wholly on the tibia, but its 73 mm bare transverse length implies roughly 80 to 90 mm of housing with attachments. That was rejected as a poor fit to the intended profile. A motor on the femur or hip would require a transmission across the knee articulation; an ordinary open belt cannot simply cross that moving joint unchanged.

If a belt is reconsidered, preserve both pulleys on one rigid stage or explicitly design the articulation crossing. The existing 375 mm knee belt fixes 139.5 mm centres and does not automatically suit a wheel drive on a 130 mm tibia. At the wheel, the current tire leaves only 4 mm and 14 mm gaps beside it. The existing 20.6 to 22 mm commercial pulley envelope fits neither gap. A slimmer integrated wheel pulley or a revised bearing stack would be another real design change. Belt preload loads the input support as well as the wheel support.

## Printing, heat and maintenance

Make the bearing-carrying sidewalls, end bulkheads and connecting ribs the structural leg. Use a removable nonstructural panel to close the motor bay. Print the long load paths broad-face down so continuous roads run between the knee and wheel supports. Keep through-bolts and metal compression spacers at the nodes. Avoid narrow upright printed adapters whose load peels the layer stack. Thin decorative panels should not be the only member carrying motor reaction or a wheel bearing.

The new cross ties should connect the two structural sides around the motor, with room for its full can, gearbox and encoder. Do not reuse a tie coordinate simply because it cleared the empty old shin. A fixed bulkhead near each end of the motor bay can carry these loads without passing a rod through the motor.

Leave the encoder connector and bend space at the upper u20 end. Mount to the motor can/gearbox at defined hard stops; protect the encoder and terminals from clamp load. Provide an inward or rear ventilation path and access to the case for temperature measurement. A rough resistance estimate from the 12 V/5.5 A stall endpoint gives about 2.18 W of copper loss at 1 A, before gear losses. It is a heat allowance for planning, not a winding-temperature or continuous-duty prediction. Enclosure-fitted temperature measurements remain necessary; a foam wrap that hides the case also restricts cooling.

The side panel should expose motor clamp screws, the coupling, input support, gear-retention screws and wheel-axle retainers with straight tool paths. Reserve axial travel to disengage the motor shaft before lifting the motor from the side. Check this using the chosen coupling's real engagement; a 12 mm withdrawal allowance is a useful initial envelope. The motor should be removable without cutting a cover or extracting a wheel bearing through an inaccessible wall. Keep the knee cable loop outside the motor and gear meshes through the full intended knee range.

## Mass control and next acceptance check

Remove the obsolete foot W05/W06 motor representations and W07/W08/W09 mounting/coupling parts when their replacements are present. Relocate the 98 g motor once. The old foot cradle alone is 32.19 g of printed material. Two 110 x 40 x 1.6 mm PETG panels are already about 17.88 g before fasteners, ribs and end closures. Adding them over every old member would spend much of the deleted cradle mass before the new gears and shaft supports are counted.

Use the new sidewalls and bulkheads to replace redundant cheeks, spacers and brackets where the load path permits. Report the net mass of the complete relocated wheel-drive subsystem, including miter gears, shaft, bearings, coupling, covers and fasteners. Moving mass into another link name is not a weight saving. The 7.108 kg candidate is a comparison baseline to improve, not an allowance to fill with extra cover material.

The next acceptance view should show the motor physically inside a continuous shin envelope in all four main views, the complete supported shaft/miter stack, accessible retention and a reconciled mass delta. Keep exact motor, gear rating, price and supply decisions with their supplier study; none is approved by this profile review. This review does not establish thermal duty, dynamic walking or stair capability.
