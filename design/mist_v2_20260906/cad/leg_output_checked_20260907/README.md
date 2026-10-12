# MIST leg CAD candidate

This folder contains the current offline mechanical candidate: 577 valid solids, including four legs and the body. OpenCascade checked all part pairs in the recorded drive pose and reported 0 intersections above 0.01 mm3, 0 Boolean failures, and 0 shape-check issues. These checks do not establish clearance throughout motion or a completed torque path.

The leg recipe is in `../leg_native.py`; `../leg_gears.py` supplies sampled involute spur outlines. `build_leg` and `build_four_legs` create native Fusion sketch/extrude components when run inside Fusion. Native Fusion execution and motion joints are separate checks. The exported STEP and GLB files are offline solids and meshes.

The parameter snapshot is `\design\mist_v2_20260906\simulation\design_parameters_20260907.json`. Its SHA256 is `8a2b78413699581b4bc2b2253e432bf8b32e6ff3811ac0ba80635f5cf8682208`. The fit snapshot SHA256 is `c9ef46f4dfa19b0c73f55f7df48c83b577f54b10adfae9e9295e242187ddaefd`. Source and STEP hashes are recorded in `source_and_step_hashes.json`.

| Interface | Current geometry | Remaining work |
|---|---|---|
| Body attachment | Four M4 bolts per leg, radii 78/98 mm and tangent offsets +/-22 mm; 52 mm bridge, washers and nuts | Verify tool access in assembly order and loaded deck stiffness |
| Yaw | 8 mm metal shaft, two 608 bearings, 20:40 module-1 involute gears, fixed servo station at 45 degrees around the yaw axis | Shaft torque lock, axial retention, running clearances and motion test |
| Hip | 7 mm trunnion, two 687 bearings, separate C018 case clamp and 20:40 gears | Hub clamp/key and loaded reversal test |
| Remote knee input | Independent 7 mm trunnion, two 627 bearings bracketing the purchased pulley envelope | Supplier bore reaming and torque-lock details |
| Knee | 8 mm axle, two 608 bearings, 32 mm bosses, keepers and steel inner-race spacers | Confirm inner-race land and axial locking; fatigue and full-load deflection |
| Belt | Reinforced 375-3M-9 selection, equal 32T pulleys, 139.5 mm centers; 9 mm pitch ribbon | Exact matched tooth geometry is omitted; tension adjustment is unfinished |
| Purchased pulleys | 29.8 mm outside diameter, 33.6 mm flanges, 21.6 mm hub diameter, 20.6 mm total length | Obtain matched GT parts; supplier bore is 6 mm and must be reamed to 7/8 mm |
| Wheel | 85 x 24 mm tire envelope, supported 6 mm axle on two 626 bearings, exact FIT0493 case and 4 mm D-shaft envelope | Tire selection, wheel hub torque lock, motor clamping and coupling detail |
| C018 clamps | Manufacturer 45.23 x 24.73 x 35 mm case, axis 12.5 mm from short end; 19.95 mm horn, 14 mm bolt circle and 4.5 mm horn thickness | Compare delivered actuators and set measured clamp preload |

The three clamp pads are separate TPU95A candidates. The H/K pads have 0.7 mm free thickness and 0.5 mm assembled thickness; the yaw pad has 1.2 mm free thickness and 1.0 mm assembled thickness. Recipes retain both states. The exporter manifest must identify which state each STL contains before it is used for printing.

Each leg uses four 608, two 687, two 627 and two 626 bearings. Four legs therefore need 16, 8, 8 and 8 respectively. Six extra 608 bearings are needed if the assumed stock of ten is correct. No purchase has been made.

The original 4 mm knee shaft was removed after a belt-load screen indicated excessive bending. With the current 53.4 mm bearing-center span and a 300 N radial pulley load at Y=21.125 mm, the 8 mm shaft sees about 76.7 MPa nominal bending stress. Adding 2.75 N m torsion gives about 90.2 MPa von Mises stress before stress concentrations, fatigue, bearing fit and material variation. These are calculations, not measurements.

The old generic leg mass estimates are superseded by this geometry. The exporter lists 415.24 g of fully solid printed material per FL leg, including TPU pads in their free state. Use the material-aware mass audit for metal parts, manufacturer motor masses, bearing-envelope upper bounds and the complete robot total. Infill and measured bought-part masses still need replacement values.

The bearing seat diameters and servo pocket come from `coupons/fit_parameters.json`. Current proximal towers retain 2 mm shoulders; the coupon uses 1.2 mm. The distal knee has a 1.2 mm floor and 7.2 mm seat depth, but a wider boss and inner-race clearance. Lead-in geometry and the wheel's through seats also differ. A successful coupon cannot yet certify these complete housings.

The candidate has no completed shaft keys/clamps, no modeled belt tensioner, no verified cable route, and no native motion joints. It is suitable for reviewing the load path and making the next interface specimens. It is not a full-leg print release or evidence that this robot can walk or climb stairs.
