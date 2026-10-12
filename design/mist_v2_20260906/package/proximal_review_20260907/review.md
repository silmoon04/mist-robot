# Proximal-femur knee drive review

7 September 2026. The useful next architecture is a femur-mounted knee motor driving a supported input pulley at the hip axis through a 20:40 spur pair, with the existing 32:32 remote belt to the knee. It keeps the motor near the hip, preserves the known belt centre distance and brings its reaction torque into the femur. It can make the hip smaller and lighter. It does not eliminate the input shaft, its two bearings or the need for a real pulley attachment.

This review preserves the 577-part candidate and shared simulation. It reads the checked geometry report, its embedded part specifications, the native recipe, the existing structural screen and the supplier interface notes. Calculations and outputs are confined to this directory. The four scripts cover mass, printed sections, shaft loading and 3D case clearance; each writes a corresponding JSON file. The source-report SHA-256 is recorded in the mass inventory. The new contract below came from the leg implementation agent before its completed CAD export and requires a later geometry review.

## Actual mass to remove

Each checked leg contains 415.24 g of fully solid printed material and 736.88 g of declared or estimated hardware, totalling 1,152.12 g before a completed harness or new torque locks. The body contributes another 798.59 g of printed material. These figures must not be confused with weighed assemblies. Bearings use solid steel annulus envelopes, pulley teeth/grooves are simplified, and the tire is unselected. Some entries overestimate hardware while unfinished attachments can add mass.

The hardware assignment is not accidentally treating the actuators as solid steel: three C018s are 55 g each, FIT0493 is 98 g including its shaft, pulleys use aluminium and the tire uses an assumed TPU density. Moving the knee motor retains its 55 g.

| Current part or family, per leg | Mass | Useful change |
|---|---:|---|
| All K-prefixed input parts, excluding the servo and F04 pulley | 143.52 g; 67.48 g printed | Replace the wide carriage-mounted assembly with a carrier tied into the femur. Retained bearings/gears still count. |
| Rotating coxa + fixed root bridge | 72.18 g printed | Delete the long knee-servo branch from the coxa; retain the short yaw-to-hip load path and root supports. |
| Hip servo saddle + cap | 35.61 g printed | Rib the floor and use separate clamp bars with hard stops. |
| Knee servo saddle + cap | 35.58 g printed | Count its replacement inside the K-subsystem budget, not a second saving. |
| Femur cheeks | 52.53 g printed | Reduce midspan web material while retaining edge rails, bearing nodes and tie nodes. |
| Tibia cheeks | 49.37 g printed | Apply the same section strategy, retaining the wheel motor reaction bracket. |
| Wheel motor cradle | 32.19 g printed | Use two retained case hoops and a ribbed bridge into the tibia. |
| Wheel hub | 27.67 g printed | Remove web/rim material away from the axle and tire-retention features. |
| Remote 627 pair | 37.55 g envelope estimate | Still required by the selected contract; weigh real bearings before claiming a saving. |
| Knee shaft + steel inner-race spacers | 44.09 g | Shorten the stack when the complete pulley/retainer design permits. |
| Two matched pulley envelopes | 59.50 g | Replace estimates with selected part masses; ensure that a lighter attachment still carries torque. |

The five solid steel shaft estimates total 100.02 g per leg. The knee shaft alone is diameter 8 x 76 mm, about 29.99 g. Each removed millimetre of an unchanged 8 mm shaft saves 0.395 g; for 7 mm it saves 0.302 g. Shortening the associated ties and spacers adds savings. Reducing shaft diameter is a different structural change: an 8-to-6 mm reduction increases nominal bending/torsional stress 2.37 times and bending deflection 3.16 times at the same span and load. Preserve support quality before pursuing that trade.

The checked bearing BOM is now 4 x 608, 2 x 687, 2 x 627 and 2 x 626 per leg. Four legs require sixteen 608s, approximately six beyond the recorded ten-per-size stock. The new arrangement should publish its actual count rather than inherit the earlier 685 draft allocation.

## Selected single-leg architecture

Keep the body yaw cassette and a short, two-bearing hip support. Attach a compact knee-input carrier to both femur cheeks or to a rigid crossmember tying them together. Its housing rotates with hip angle. Its gear and belt pulley rotate with knee angle relative to that housing. Keep the input shaft independent of the hip-drive trunnion even though their axes are collinear.

The chosen belt input remains at the hip axis, with the knee 139.5 mm down the femur. The 375 mm, 3 mm-pitch belt and equal 32T pulleys therefore retain `C = (375 - 32*3)/2 = 139.5 mm`. The knee motor axis sits 30 mm down the femur to mesh a 20T pinion with the coaxial 40T input gear. Its case centre sits about 40.115 mm down the femur. Align the case's long dimension along the upper femur. This removes the former motor case projecting sideways at the hip without inventing another belt length.

The motor mapping is now `s = [2*yaw, 2*hip, 2*knee]`, with calibrated offsets and signs. Before losses, motor torques are `[tau_yaw/2, tau_hip/2, tau_knee/2]`. The old hip-minus-knee torque subtraction belongs to the earlier carriage-mounted absolute-tibia drive and must not carry over. Add the knee motor, carrier and any relocated bearings to the correct moving link. A 55 g motor 40 mm from the hip adds at most 0.0216 N m of gravity moment and 0.000088 kg m2 about the hip axis; its lateral offset and the carrier mass add further terms.

There are two separate load paths. Wheel force passes through the supported wheel axle, tibia, knee bearings, femur cheeks, hip bearings and yaw cassette into the deck. Knee drive torque passes from the motor case into its femur mount, through the horn/pinion and 40T gear, through the pulley face attachment and belt, and through the distal pulley attachment into the tibia. A stationary support shaft may carry radial/axial load without transmitting drive torque, but both pulley attachments still need explicit torque paths. A free pulley bore on a shaft or an axial collar does not supply them.

## Contract clearances to resolve in CAD

The input stack uses a 14 mm A-shape pulley at Y14.125 to 28.125 and an 8 mm gear at Y28.125 to 36.125. Face fastening uses four M4 screws on a 16 mm pitch circle. The first contract left only 1.875 mm between the gear and the outer 627 bearing, too little for ordinary 4 mm-high M4 socket heads. Their radial footprint also overlaps the bearing annulus.

The implementation agent corrected that contract to bearings at Y5 to 12 and Y42.325 to 49.325, with the outer housing floor beginning at Y41.125. The heads end at Y40.125, leaving 1 mm to that floor. The proposed 8.6 mm OD spacer leaves only 0.2 mm radial clearance to the heads' innermost radius; check the actual head diameter, runout and bolt-circle tolerance. Tool approach and the completed solid assembly still need checking.

At bearing centres Y8.5 and 45.825, a 300 N pulley pull at Y21.125 gives 198.53/101.47 N reactions, 2.506 N m peak bending moment and 74.43 MPa nominal bending stress in a smooth 7 mm shaft. The load-point deflection is 0.0111 mm at assumed E = 200 GPa. Adding the module-1 gear's 2.75 N m torque produces 137.5 N tangential and 50.05 N radial mesh force at Y32.125. The bending screen gives 70.14 MPa when the radial gear force opposes the belt pull, or 83.49 MPa if it adds. The actual motor-below-input arrangement determines that direction. These are static smooth-shaft results; threads, notches, fits, fatigue and purchased material remain outside the screen. If the shaft also transmits 3 N m, the combined stress reaches approximately 104 to 114 MPa instead. The primary torque path must therefore match the stated face-bolted gear/pulley design.

The new motor location does not remove every neighbouring-leg conflict. `contract_clearance.py` uses its confirmed case centre `(0, +/-59.125, -40.115)` mm and 24.73 x 35 x 45.23 mm case dimensions in each femur frame. At the nominal 58.04-degree hip angle, FL yaw +20 / RL yaw -20 degrees intersects those case boxes; the +22/-22 pair has a 15.46 mm minimum separation deficit along the tested 3D separating axes. Common-heading offsets of -10, 0 and +10 degrees leave these case pairs separate. Those three samples say nothing about the rest of the mechanism or continuous travel. Retain a restricted pose domain until the complete solid assembly establishes its actual usable region.

Other constraints for the first CAD review:

- The bearing supports must straddle the pulley load. Retain the diameter, support span and hub placement required by the structural screen; mounting two bearings on one side recreates the old overhang penalty.
- The selected A-shape pulley is a different interface from the old 20.6 mm-long B-shape envelope. Use its complete actual dimensions, including face threads, flange and locating register. Do not combine dimensions from the two suppliers into a fictional part.
- The motor case, horn and rotating pinion need their full width, centre screw and tool access. Its case must have positive torque stops, with TPU supplying clamp preload rather than the whole reaction path.
- Keep the 30 mm transverse coxa offset and the barrel boundary explicit. Cycle hip as well as yaw: a case moved down the femur can swing upward beside the deck or into the fixed hip servo. Test the same four leg poses together.
- Route one controlled cable loop from the yaw carriage onto the femur, anchored on both stages. Keep it clear of the hip-coaxial belt input, the spur mesh and the added carrier crossmember.
- Reserve shaft retention and assembly access before narrowing the cheeks. The supplier collar envelopes need 9 mm axial length each and up to 22.4 mm radial hardware clearance. A removable bearing cap should reach the shaft without dismantling a glued shell.

The supplier notes' rated MSM locking-bush route adds 40 g per pulley, or 80 g per leg before a change to the pulley itself. That can consume most of the savings below. Its availability as a rated component does not make it a suitable default for this lighter arrangement. Use a defined compact pulley/face attachment and verify its holding torque; a simple unverified set screw cannot be used to close the mass budget.

## Concrete printed-section changes

Use two cheeks printed broad-face down, with long roads running along each member. For the 26 mm-wide, 6 mm-thick femur midspan, retain a 2.4 mm web and two 5 mm-wide edge rails raised to 6 mm total thickness. The ideal cross-sectional area falls from 156 to 98.4 mm2 while the in-plane second moment remains 86% of the original. The corresponding 28 mm tibia section keeps 84% at 61% of its original area. These are section comparisons, not strength tests.

Keep full material around bearing seats, shaft locks, cross ties and motor attachment nodes. Apply the lighter section only between those nodes. If 70 mm of each femur cheek and 60 mm of each tibia cheek can use it, the ideal volume saving is about 20.1 g per leg. The paired cheeks still require well-spaced ties to share load and resist twist. Do not treat sparse infill or an open slot as a closed torsion box.

For each remaining servo mount, reducing a 53.23 x 39 mm floor from 6 to 3 mm removes about 7.91 g. Replacing its full 4 mm cap with two 8 mm-wide crossbars removes another 7.38 g before adding local ribs. Keep hard stops and through-bolt lands so tightening does not crush the case. Use shallow triangular ribs in the broad print plane and metal spacers under bolt preload. Give the case shoulders a direct path into the femur carrier; avoid a narrow upright adapter loaded in peel across print layers.

For the wheel cradle, replace its long solid side walls with two retained case hoops and a ribbed floor. Retain a stiff front bridge that delivers motor reaction to both tibia sides, not a single flexible cover. A 12 to 16 g saving from the current 32.19 g is a CAD target to verify. This distal change helps inertia as well as total mass. Keep the separate wheel bearings and axle; use the motor only for torque.

## Weight target and MIST appearance

Use a non-overlapping first-pass target of roughly 65 to 110 g saved per leg, about 0.26 to 0.44 kg across four. The calculation allocates 13.5 to 38.5 g to replacing the 143.52 g K subsystem with a 105 to 130 g assembly, 10 to 14 g to the remaining hip-servo mount, 16 to 20 g to link webs, 12 to 16 g to the wheel cradle, 5 to 8 g to the hub and 8 to 12 g to the shortened root/coxa structure. These are targets before final torque locks, shaft retention, actual hardware mass and fit-driven reinforcement. They must be replaced by the next geometry report; moving parts between names or link frames is not a saving.

The inspected checked render has large rectangular motor pods dominating the lower barrel. Moving the knee case along the upper femur should reduce that cluster while preserving the 180 mm barrel, four diagonal mounts, leg lengths, wheel diameter, face and lid. Keep the root dark and compact and the lower legs visually narrow. Add cosmetic covers only after the moving clearances and service access exist; a larger shell would conceal the packaging problem and alter the reference proportions.

This direction can produce a more coherent first leg, but its expected savings do not restore the old light simulation mass by themselves. The next review should compare its actual part inventory, mass, motor reaction frame and full assembled clearances before any new load or mobility claim. Stair performance and print release remain unestablished.
