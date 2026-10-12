# R5 leg interfaces

R5 uses an inward-facing hip case and a straight knee-to-toe main member. The femur remains 90 mm and tibia 105 mm. The coxa is 70 mm, allowing room for the hip case and reinforced yaw support. The final yaw operating range is 19 degrees each side of neutral; broader diagnostic poses do not qualify operation.

The main lower-leg body is one continuous printed part. A short removable auxiliary cheek supports the opposite shaft and lets both parts print on their broad faces. There is no extra joint within the shin. The stable internal SKU tibia_curved_main_and_foot remains in the source, but its R5 geometry and display label are straight.

Use the [R5 fastener stacks](../printing/R5_FASTENER_STACKS.md) and [assembly guide](../printing/PRINT_AND_ASSEMBLE.md) for actual quantities and assembly order. The hip cap has a relocated rear screw at servo-local X=-38.915,Z=-27.5 mm and is not interchangeable with the knee cap. The post bolts are at coxa X28.5,Y±4.5 mm. The straight-tibia bridge bolts are at X36 and X44, Z0 mm.

Preload the hip nuts from above into the bare carrier, then fit its servo and dedicated cap. Build the leg modules before mounting them to the body. Complete shaft, washer, screw-tip and wire-clearance checks before powered use. The hardware interfaces retain the C018 midpoint shaft datum, 1.1 mm auxiliary lands, 7.8 mm center access and specified paired washers.

The [changed-interface check](output/r5_interface_check.txt) covers deck/arm gaps and hip nut entry/seating. [Full motion](output/full_motion_check.txt) covers the complete robot's sampled poses and phone pan. [The strength report](../manufacturing/strength/r5_strength_assessment.md) evaluates current sections and simulated loads. These remain digital checks with provisional material and hardware assumptions.

[Plate 02](../printing/coupon_plate_02.3mf) contains the five revised production parts as reusable fit specimens. Use common fit gauges if they have not been measured with the actual servos and printer. Test the complete coxa frame and supported leg before printing three more sets. Physical fit, PLA strength, warm creep, calibration and reliable hardware walking remain unqualified.
