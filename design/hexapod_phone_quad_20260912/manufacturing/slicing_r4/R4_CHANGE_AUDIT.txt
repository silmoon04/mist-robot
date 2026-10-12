# R4 print geometry and support changes

All 34 production SKUs and all 76 quantities are preserved. Every current mesh is closed, consistently wound and has positive volume. All current footprints fit a nominal 225 mm bed with 4 mm added on each side for a brim. There are 21 changed STL byte hashes; byte differences alone do not establish a meaningful geometry change.

Keep the exported orientations for the next fit build. The femur's broad bed face is about 3,007 mm2, the coxa has about 412 mm2 of planar bed contact and the tibia main has about 1,505 mm2. These retain substantial bed contact while the recorded slices reduce support on the coxa and femur. No whole-part 45 degree tilt is justified by this comparison.

Only the power-distribution tray's print-rotation metadata changes, from [180, 0, 0] to [180, 0, 45]. Its actual exported 47 x 47 x 4 mm footprint, volume and 2,127 mm2 bed contact remain the same, with no downward overhang. The added Z rotation leaves the tray parallel to the bed.

Inspect local support in the offset servo saddles, transverse bridges and raised foot, and remove it before assessing case, nut and horn fits. The pan-servo saddle has about 496 mm2 of bed contact; check its first layer and local support islands. The thin yaw spacers have only about 17.3 mm2 each, so an appropriate brim and clean bed matter more than changing their upright orientation. The cover still requires local support review under pockets and fixing features.

The actual quantities use 50.96 g of removable support, 17.8% less than the final R3 profile. Model PLA rises by 30.74 g to 1,047.64 g. These are commanded-filament estimates, with actual masses and fit still needing measurement.

| Changed SKU | R4 print dimensions, mm | R3 / R4 bed contact, mm2 | R3 / R4 support, g | R3 / R4 time, min |
| --- | --- | ---: | ---: | ---: |
| `body_deck` | 178.40 x 206.00 x 4.00 | 22487 / 21777 | 0.000 / 0.000 | 548.2 / 535.4 |
| `hex_faceted_cover` | 184.00 x 208.00 x 57.50 | 23633 / 23387 | 6.203 / 6.203 | 884.3 / 880.7 |
| `power_distribution_tray` | 47.00 x 47.00 x 4.00 | 2127 / 2127 | 0.000 / 0.000 | 31.0 / 31.0 |
| `servo_bus_adapter_tray` | 19.00 x 38.00 x 22.00 | 678 / 662 | 0.141 / 0.141 | 32.5 / 32.3 |
| `esp32_tray` | 19.00 x 33.60 x 22.00 | 594 / 578 | 0.139 / 0.141 | 26.4 / 26.1 |
| `phone_pan_servo_saddle` | 67.99 x 49.99 x 22.50 | 1291 / 496 | 1.373 / 1.162 | 135.5 / 126.5 |
| `phone_pan_servo_cap` | 52.23 x 48.00 x 14.20 | 757 / 475 | 0.919 / 0.944 | 54.4 / 49.4 |
| `yaw_case_saddle` | 61.23 x 52.00 x 30.00 | 1412 / 1395 | 1.348 / 0.591 | 114.1 / 118.1 |
| `case_cap_yaw` | 61.23 x 27.00 x 4.00 | 1620 / 1626 | 0.000 / 0.000 | 38.8 / 39.2 |
| `coxa_upper_and_hip_saddle` | 107.11 x 55.56 x 31.50 | 378 / 412 | 3.181 / 2.653 | 161.7 / 169.8 |
| `coxa_lower_auxiliary_arm` | 50.47 x 28.00 x 9.00 | 996 / 996 | 0.086 / 0.119 | 56.0 / 55.8 |
| `case_cap_hip` | 61.23 x 27.00 x 4.00 | 1620 / 1626 | 0.000 / 0.000 | 38.5 / 38.7 |
| `yaw_auxiliary_spacer_1` | 5.79 x 5.80 x 11.60 | 17 / 17 | 0.000 / 0.000 | 3.8 / 4.3 |
| `yaw_auxiliary_spacer_2` | 5.79 x 5.80 x 11.60 | 17 / 17 | 0.000 / 0.000 | 3.8 / 4.3 |
| `yaw_auxiliary_spacer_3` | 5.79 x 5.80 x 11.60 | 17 / 17 | 0.000 / 0.000 | 3.8 / 4.3 |
| `yaw_auxiliary_spacer_4` | 5.79 x 5.80 x 11.60 | 17 / 17 | 0.000 / 0.000 | 3.8 / 4.3 |
| `femur_main_and_knee_saddle` | 122.11 x 46.50 x 42.00 | 2638 / 3007 | 3.429 / 1.990 | 207.0 / 215.3 |
| `femur_auxiliary_cheek` | 93.00 x 46.50 x 8.00 | 2638 / 2997 | 0.018 / 0.000 | 70.4 / 79.9 |
| `case_cap_knee` | 61.23 x 27.00 x 4.00 | 1620 / 1626 | 0.000 / 0.000 | 38.5 / 39.2 |
| `tibia_curved_main_and_foot` | 123.98 x 42.00 x 42.00 | 1505 / 1505 | 2.608 / 2.608 | 151.2 / 150.4 |
| `tibia_auxiliary_cheek` | 77.00 x 42.00 x 8.00 | 1505 / 1496 | 0.000 / 0.000 | 43.9 / 43.9 |

The JSON records both solid volumes, all dimensions, print rotations and exact projected overhang areas for every SKU. Slicer motion envelopes were checked separately in `output/validation.json`. The comparison uses retained R3 source snapshots rather than live R3 paths, which now belong to R4.

Final source manifest SHA-256: `6cac852c196e29e2da100816a7d3b96f545e62dba92c3009a46417eb7d9bc449`. R4 production-properties SHA-256: `3b69ffb7bfd212296b85fb1846181dd86a7fffb2451e6f961c821fc1e8f24209`.
