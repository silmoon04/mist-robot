# Tonight: four-leg main hub and eight spacers

Print Tonight_Hub_And_8_Spacers.3mf using Neptune4Pro_Hub_PLA_028.curaprofile. The plate contains one centre hub and eight general M3 spacers, 8 mm tall by 13 mm outside diameter with a 3.4 mm bore. Those dimensions follow the direct reading of your request; verify the filename dimensions before slicing if you intended the 13 mm dimension to mean height. They are not replacements for the 11.6 mm long, OD5.8 yaw spacers or the integral annular pitch stand-offs.

The hub is the robot's four-leg centre deck, not the earlier rectangular bench fixture. It provides all four saddle mounting patterns now, even if you have only two complete legs. Keep the plate for the robot build. It is the first physical hub revision, so full-body load tests and later cover/electronics work can still lead to changes.

## Print settings and time

The complete single-bed estimate is 7 h 50 min and 119.6 g PLA. The hub measures approximately 178.4 x206 x12 mm, comprising a 6 mm deck with upward ribs. Put its flat underside on the bed and keep the ribs upward. Spacers stand on their flat annular ends. Supports are OFF for the whole plate. All functional holes run vertically, and the checked geometry has no downward overhang faces above the bed.

Use your existing Neptune 4 Pro printer definition and 0.4 mm nozzle. Import the profile through Preferences > Profiles > Import, then open the 3MF as models and select that profile. This 3MF carries geometry and placement only; it does not automatically activate the profile. Keep 100 percent scale and the supplied orientations. A combined STL and individual part STLs are included as alternatives.

The profile uses 0.28 mm layers, five walls, 25 percent gyroid infill, five top/bottom layers, 210 C nozzle, 60 C bed and a 2 mm outside brim. Outer walls and top/bottom surfaces are increased from 40 to 46 mm/s, a 15 percent increase. Travel rises from 150 to 175 mm/s. Inner walls and infill remain 65 mm/s, because increasing these further would exceed the conservative flow envelope used on the previous prints. First-layer speeds, bridge speeds, acceleration and cooling are unchanged.

An actual hub-only A/B slice changed from 7 h 34 min to 7 h 16 min, approximately 3.9 percent less total time. A15 percent increase in selected speeds does not produce a 15 percent reduction for the entire job. The complete hub-plus-spacer slice peaks at 7.76 mm3/s commanded deposition flow, below 8. The lowest XY travel margin to the nominal bed boundary is 2.97 mm. Firmware, heating and filament behaviour can change the elapsed time and finish. No printer start/end G-code or calibration values are overridden.

## Attach the legs

Each leg's stationary yaw servo sits in its separate saddle. The saddle's four feet bolt onto the hub; the moving coxa bracket does not bolt directly to the hub. There are four identical 38 x40 mm fixing patterns, with yaw shafts positioned 75 mm from the hub centre at 45, -45,135 and -135 degrees. The shaft end of each servo faces outward and its case tail points inward toward the hub centre. Retain the existing eight-part leg assemblies without changing their geometry.

For each attached leg, use four M3x12 screws, four M3 nuts and four flat washers. Insert the screws from the saddle-foot side, with heads directly against the printed feet. Put one washer and one nut underneath the hub. Omit upper washers: the approximately 7.7 mm washers would touch the servo clamp. For your two legs this is eight screws, eight nuts and eight washers; four legs require 16 of each.

The nominal stack is 6 mm hub + 3 mm saddle foot + 0.5 mm flat washer + 2.2 mm nut. A 12 mm screw extends approximately 0.3 mm beyond that nut, so actual thickness matters. Before tightening or loading, confirm that every screw passes through the full nut. The nut measurement is approximate and washer thickness is still unconfirmed. Do not substitute longer M3x18 screws blindly: their tips can enter the rotating lower-arm region.

The eight large spacers on tonight's plate are general-purpose requested parts. Do not insert them between the saddle and this hub: that would change the checked mounting height and screw stack. The four narrow yaw spacers per leg remain the earlier nominal 11.6 mm set.

## What is included and what remains

The deck preserves the existing leg-hole patterns and the four cover fixing locations, but has wider openings for the newer coxa motion and lower hardware. It adds full-width material beneath the outer feet and a central cross of upward ribs. Cable/strap slots remain available. The old battery tray mounting pattern conflicted with the enlarged openings, so that tray is not directly compatible with this hub. Four new central mounting holes are reserved for a later tray; the old cover and electronics mounts also need their vertical clearances adapted to the 6 mm ribbed deck. Do not print the older cover or battery tray on the assumption that it has already been fitted to this version.

The yaw saddles, caps, servos, narrow yaw spacers and completed legs are not on this plate. Some may already be in your previous prints. In particular, the older test saddle needs its actual nut engagement checked before loaded reuse.

The two-leg assembly is not a self-balancing robot yet. Support the hub during assembly and initial powered movement. Full-body payload, walking balance and contact forces remain to be qualified.

## Verification

The hub is one valid solid and one closed, consistently wound mesh. All four leg mounting patterns and their material around the screw holes were checked. Exact hub/leg intersection checks passed for 140 sampled leg poses across the four positions, including yaw endpoints to 60 degrees and representative pitch guard poses. The mounting screw, nut and washer envelopes also passed. The plate's nine meshes, profile import structure, actual no-support slicing and printer travel envelope passed.

These checks establish sampled hub clearance, not unrestricted independent motion of all four legs. Inter-leg collision, full gait dynamics and physical strength are not established. A simple section screen with assumed PLA strength passed its selected 1 Nm comparison case, but is not FEA or a guarantee against screw preload, fatigue, thin-tab stress or impact. Commission the printed assembly under restraint before loading it.

Main_Hub_And_Spacers.f3d is the new Fusion print-parts document. Main_Hub_4Leg.step and Spacer_8H_13OD_M3.step are editable solids. Hub_With_Four_Legs.step shows the complete mechanical layout at a neutral pose; the legs in it are for context and are not additional objects in the print plate.
