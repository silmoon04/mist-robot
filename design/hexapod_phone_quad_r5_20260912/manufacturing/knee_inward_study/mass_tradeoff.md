# Knee inward mass tradeoff

The corrected drawing places the case center **12.5 mm from the shaft**, with case ends **−35.115 and +10.115 mm**. Reversing it moves the case center **25 mm**. The old 20.23 mm figure used an incorrect datum and is retained only as historical data in the JSON.

This A/B reference assumes each 55 g case's COM is at that corrected case center: femur X102.5 mm outward and X77.5 mm inward. Actual internal servo COM remains unmeasured. The four knee-case references are rebased in memory; other components stay at frozen R3 values. Model mass remains 2.709883 kg, with no production edits or dynamics rerun.

For that 25 mm reversal at a 30° hip angle, the case's own gravity moment decreases by **0.011682 N·m per leg**, about 2.0% of the 0.588 N·m screening cap. An unsupported leg requires less self-weight holding torque. In a loaded stance, the case weight opposes the upward foot reaction, so unchanged foot load requires **more** positive hip torque by that amount. The case belongs to the femur, so there is no direct knee gravity change.

At the symmetric 30°/81° pose, the four horizontal shifts cancel and whole-robot COM rises by **1.015 mm**. The polar inertia about the central vertical axis decreases by **4.76%**, using the complete registered mass model. This can reduce inertia during yaw acceleration, but it does not establish a walking-energy or servo-temperature improvement.

Across the saved nominal gait, the direct per-leg hip holding-torque change is **0.011242 to 0.012923 N·m**. Maximum horizontal whole-COM movement is **0.268 mm**. A separate fixed-pose gravity calculation allowing support-force redistribution changes the peak absolute hip load from **0.456120 to 0.467189 N·m**. That calculation is not a dynamic rerun.

The largest existing gravity-load screen is at knee_RR, which changes from **0.542061 to 0.541912 N·m** after the small support-force redistribution. Direct knee gravity from the case is still zero. At the neutral pose, the complete moving leg's yaw inertia falls by **9.73%**, and its hip subtree inertia falls by **14.66%**.

For scale only, the old R3 detachable cap is 6.592 g per leg. A pure 25 mm translation would add another 0.001400 N·m of moment change. The 34.644 g integrated femur-and-saddle part includes structural material that cannot all be treated as a moving clamp. A complete case-plus-clamp comparison awaits corrected candidate geometry and mass properties.

The static load changes are small, and the robot keeps the same weight. Appearance, connector clearance, hardware access and the complete inward geometry still need their own review.
