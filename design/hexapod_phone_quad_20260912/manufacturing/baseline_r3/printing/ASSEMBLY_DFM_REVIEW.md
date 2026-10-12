# Assembly and print review

The R3 manufacturing revision addresses the principal assembly defects found in the landscape robot. The original review and fastener estimate are preserved in `../manufacturing/baseline_r2/printing/`. That baseline remains useful for comparing geometry, but its screw lengths, bridge coordinates and mass totals are superseded.

## Load path and practical changes

Toe force bends the curved blade, transfers through its bridge into both tibia cheeks, then through the supplied metal discs into the knee case. The femur cheeks and their case clamp carry that load to the hip. The coxa post and supported yaw arm deliver it to the deck. The auxiliary disc only provides a second support if its seating and bridge spacing leave it free to turn.

The baseline femur bridge had a 5.97 by 6.8 mm section with a 3.4 mm hole, leaving a narrow lower and side ligament. R3 enlarges that section and moves its closure to X70, Z-16. It adds edge ribs, strengthens the tibia bridge, thickens the lower yaw arm and staggers the coxa post's nut windows. The bridge nuts now sit outside full-thickness cheeks, eliminating the thin floors below deep captured-nut recesses. Keep material around these junctions before removing material from broad faces.

The battery tray now has sloping ribs under its raised attachment tabs. These distribute bending into the walls and reduce the support needed beneath horizontal projections. The phone pan saddle has side-loaded cap nuts beneath retained roofs. Its former open-top nut wells could not react the screws' upward pull. The cradle keeps its landscape orientation and uses two lower corner clips instead of a long screen-edge retainer.

The main leg cheeks still contain offset geometry. Printing a broad cheek flat keeps much of its bending load path within layers, but local supports need accessible removal paths. Printing at 45 degrees does not automatically improve strength or remove supports. A face-angle metric can report zero support area when rectangular faces land exactly at its threshold, while missing unsupported islands. Use the sliced layer results and orientation comparison alongside this assembly review.

## Hardware stacks and assembly access

The case clamp uses M3x35 with a 0.5 mm head washer and recessed plain nut. Its nominal tip extends 1.77 mm past the 32.73 mm rail span. The short peripheral horn screws are M3x6 with 0.5 mm washers, leaving 1.5 mm engagement through the 4 mm cheek into the 2.1 mm auxiliary flange.

The three transverse closures per leg use M3x50, two OD7 by 0.5 mm washers and one external 2.4 mm plain nut. The nominal stack is 49.4 mm, leaving 0.6 mm tip emergence. The tibia's revised 8 mm bolt spacing leaves 1 mm between washers. Use a slim socket or small spanner without bearing on the printed cheek; check the actual hardware throughout the sweep.

Each yaw auxiliary screw is M3x20 with two OD6 by 0.5 mm washers inside a 2.5 mm counterbore. The under-head plane is Z-51.5 and the tip reaches Z-31.5, giving 2.0 mm nominal flange engagement. The two lower-arm/post screws are also M3x20; their nuts load through opposite side windows at staggered heights.

Build one leg first. Load clamp nuts, fit the servo and retain its metal discs, then attach each cheek independently. Load the coxa nuts before closing the lower arm. Connect the transverse bridges only after checking free auxiliary rotation. Route the leads and sweep manually with torque disabled before multiplying by four. Captured nuts and separate cheeks avoid springing a rigid yoke over the servo.

The distributed hardware model counts 225 screws, including 25 supplied retainers, 100 nuts and 212 washers. It estimates 267.701 to 383.067 g, with a nominal 327.714 g. Replace the previous 50 g fastener allowance; retain the separate wiring allowance until weighed. The generator and JSON contain per-link positions, inertias and the uncertainty over whether the specified servo mass already includes supplied center retainers. Physical fit, tool access and loaded performance still require the coupon and one-leg tests.
