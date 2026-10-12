# R4 inward-knee leg interface

The leg follows the video's open servo-yoke arrangement with new STS3215 C018 interfaces. No earlier MIST geometry is used. R4 reverses the knee case inward, moves the femur bridge above it, corrects the case midpoint datum and opens the auxiliary-side cable pocket. The geometry is frozen against assembly manifest 6cac852c196e29e2da100816a7d3b96f545e62dba92c3009a46417eb7d9bc449.

## Coordinates and nominal interfaces

Each part uses its owning link frame: X outward along the leg, Y to the side and Z upward. Positive pitch about Y tips X down. The hip axis is at coxa X 50, the knee axis at femur X 90 and the toe reference at tibia X 105. The knee case belongs to the femur; the output horn and auxiliary disc belong to the tibia.

| Interface | R4 nominal value |
|---|---|
| Case footprint | 45.23 x 24.73 mm |
| Shaft from case midpoint | 12.5 mm |
| Servo-local case ends | X=-35.115 and +10.115 mm |
| Main and auxiliary reference faces | Servo Z=0 and -29 mm |
| Main shaft / auxiliary stub tip | Servo Z=+3.4 / -33.1 mm |
| Auxiliary disc outer face | Servo Z=-32.4 mm, with 0.3 mm case clearance |
| Auxiliary retainer washer | OD 7, ID 3.2, thickness 0.5 mm, against fixed stub |
| Disc to retainer washer clearance | 0.7 mm nominal |
| Pitch cheek inner faces | Link Y=+19 and -19 mm |
| Auxiliary standoff lands | 1.1 mm high |
| Auxiliary center access | Diameter 7.8 mm, with 0.4 mm radial clearance around OD 7 washer |
| Remaining center-to-PCD-hole ligament | 1.4 mm nominal |
| Lower yaw arm | Z=-53 to -44 mm, thickness 9 mm |
| Yaw auxiliary spacers | 11.6 mm nominal; coupon alternatives 11.3 and 11.9 mm |
| Yaw peripheral counterbores | Diameter 6.2 mm, depth 3.5 mm |
| Femur bridge | X 58 to 72, Z 13.5 to 27.5 mm; bolt at X 65,Z 20.5 |
| Tibia bridge | X 44 to 60,Z 13 to 26 mm; bolts at X 48 and 56,Z 19.5 |

The [hardware contract](../references/hardware_contract.md) explains the C018 drawing and compatible supplier STEP. The earlier short-end interpretation of 12.5 mm was wrong. The supplier's outer case is retained with documented conservative changes; exact owned-unit fit is not established by that reference.

The sockets face the auxiliary shaft side. The operator reported approximately 35 mm across the bare case including the rear bulge,1.5 mm added by the cable, and 2 to 3 mm working clearance. R4 uses 2 mm additional clearance around its provisional plugged profile. The old 15 mm tail-X reserve is superseded. The [interface report](output/r4_leg_interface_check.txt) records the proxy and about 1.6 mm remaining pocket floor. Wire routing, extraction and loaded deflection need a physical check.

## Fastener stacks

Use [R4_FASTENER_STACKS.md](../printing/R4_FASTENER_STACKS.md) for complete quantities and ownership. These are required lengths and nominal interfaces, not verified inventory or thread engagement.

| Attachment | Required nominal stack |
|---|---|
| Case caps | M3x35 with one OD 7 x 0.5 mm head washer and plain M3 nut |
| Main horns to cheeks | M3x6, one OD 6 x 0.5 mm washer;1.5 mm flange engagement |
| Pitch auxiliary discs | M3x8, TWO OD 6 x 0.5 mm washers,4 mm cheek and 1.1 mm land;1.9 mm engagement |
| Yaw auxiliary disc | M3x20, TWO OD 6 x 0.5 mm washers,9 mm arm with 3.5 mm counterbore and 11.6 mm spacer;1.9 mm engagement |
| Bridge attachment | M3x50, two OD 7 x 0.5 mm washers and 2.4 mm plain nut |
| Main shaft retention | Supplied M3x6 screw |
| Auxiliary stub retention | Supplied PA3.0x5 screw with the specified OD 7 x 0.5 mm washer |

The auxiliary flange is only 2.1 mm thick, leaving 0.2 mm nominal rear margin for the peripheral screws. The yaw OD 6 washer has 0.1 mm radial clearance in its 6.2 mm counterbore; OD 7 washers do not fit there. Verify every actual washer and screw, remove support from seats and rotate each unpowered assembly freely before further assembly. Do not tighten an incorrect stack until it binds.

## Assembly order and service access

The [staged assembly addendum](output/r4_leg_staged_assembly_check.txt) passes the documented nut-entry routes and corrected washer, screw and driver checks. The original [complete-leg service diagnostic](output/r4_leg_interface_check.txt) remains failed: seven obstructed tool/part pairs involve one nut-entry tool and three nut holders. Preassembly does not make those later service routes accessible.

1. Preload all nine captive nuts into the bare yaw saddle, hip coxa carrier and knee femur carrier. Leave servos, caps, lower yaw arm and surrounding moving links off. The hip carrier's integral post remains present.
2. Insert all yaw nuts, the hip rear nut and all knee nuts from the open negative servo-local Y side, matching the nut flats to the trap.
3. The two hip front nuts require side entry. For the lower nut at servo X 13.915,Z=-23, slide its center from Z=-40 to-23 while its thickness spans Y=-20 to-17.6. For the upper nut at X 13.915,Z=-7, approach from Z=+5 to-7 at the same Y interval. Then move either nut 3.9 mm toward positive Y to seat it at Y=-16.1 to-13.7. The report preserves the corresponding transforms into the real hip carrier.
4. Keep each nut seated while adding its servo and cap. Fit the head washer and engage its M3x35 screw before adding surrounding parts. The nominal nut-to-pocket clearance is only 0.1 mm per flat. Verify this with the printer and actual nuts; hand or holder access and retention of loose nuts are physical tasks.
5. Fit the supplied horns, discs and retainers, checking case gaps and free auxiliary rotation. Install the yaw disc and its center washer before the removable lower arm. Fit the 11.6 mm spacers and required paired washers.
6. Add moving cheeks and bridges without springing them over a case. The knee case points inward toward the hip, and the femur bridge passes above it. Keep the plugs on the auxiliary side and test the complete intended sweep with the actual flexible lead.
7. To replace the obstructed hip nuts later, remove the surrounding femur/lower-arm obstructions and recover the bare-carrier access. The checked screw heads, seated washers and straight drivers are clear at the reported assembled pose; this does not establish clearance for every handle or hand.

The staged check covers 47 tools,119 tool/part pairs and 61 Boolean tests with zero blocked pairs. The corrected assembled check covers 54 tools and 1242 pairs; screw shanks, heads, drivers and seated washers are clear, while the seven nut-service pairs remain blocked. Exact servo/cap insertion motions and tightening behavior are not simulated.

## Printing, coupons and strength

Use the exported print rotations. The main and auxiliary cheek faces lie on the bed, the coxa uses+90 degrees about X, and the lower yaw arm lies on its broad face. Retain the ribs. Remove support from clamp rails, horn seats, nut pockets and cable openings without cutting load-bearing material. The all-SKU R4 slice is in [PRODUCTION_SLICING.md](../manufacturing/slicing_r4/output/PRODUCTION_SLICING.md).

`cad/fit_coupons.py` provides 17 leg pieces. Together with 11 phone pieces, the packer selects 16 first-stage pieces and 12 optional alternatives. The combined case-to-shaft registration plate must be tested with the actual clamped servo and main horn. It rejects the earlier 2.385 mm datum error. The horn/auxiliary fixtures and 11.3/11.6/11.9 mm spacer alternatives test seating and free rotation; use the measured stack, not the tightest one.

The cropped coxa nut-window coupon ends at Z=-28 and misses the critical screw-access cut at Z=-25. Test the complete production coxa with both yaw arms and real fasteners before loading a leg. [The strength assessment](../manufacturing/strength/r4_strength_assessment.md) separates ordinary sagittal/vertical loads from unresolved torque sharing, lateral disturbance and shock loads. A coupon that fits does not prove those structural cases.

R4 full-assembly checks pass nine operating poses, three additional loaded-stance poses and thirteen pan samples. Local checks pass 27 leg poses and nine connector-reserve samples. Minimum checked operating clearance around the coxa is 2.16 mm. Retain the configured yaw limit of 22 degrees. These discrete checks do not establish every continuous pose, actual cable motion or loaded deformation.

Start with [PRINT_FIRST.txt](../printing/PRINT_FIRST.txt) and record the results. The current disposition is controlled first-fit printing, followed by the documented coxa, supported-leg and dummy-phone tests. Physical fit, printed strength, thermal behavior and reliable hardware walking remain unqualified.
