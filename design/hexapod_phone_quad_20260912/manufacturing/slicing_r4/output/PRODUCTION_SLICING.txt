# Production slicing and deposited mass properties

CuraEngine sliced all 34 production SKUs, representing 76 printed pieces, from `hex_quad_r4_inward_knee`. The robot-part PLA estimate is 1047.6 g; removable support is 51.0 g and adhesion material is 1.2 g. Printing every piece separately at the recorded profile totals 104.1 predicted hours. A packed plate has different travel, cooling and adhesion overhead.

Part mass, centre of mass and inertia come from each emitted model-deposition path. Support, support interfaces and skirt material stay separate. The properties use the exact supplied print-STL frame in millimetres; `mass_kg`, `com_mm` and `inertia_kg_m2` are the fields to transform into each assembly link. The inertia tensor is about the deposited part's own centre of mass.

| SKU | Qty | Part PLA, g | Support, g | Adhesion, g | Time, min | Part / full-solid mass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `body_deck` | 1 | 87.075 | 0.000 | 0.000 | 535.4 | 0.806 |
| `hex_faceted_cover` | 1 | 156.673 | 6.203 | 0.038 | 880.7 | 0.942 |
| `pan_cover_spacer_1` | 1 | 0.204 | 0.000 | 0.000 | 1.8 | 1.002 |
| `pan_cover_spacer_2` | 1 | 0.204 | 0.000 | 0.000 | 1.8 | 1.002 |
| `pan_cover_spacer_3` | 1 | 0.204 | 0.000 | 0.000 | 1.8 | 1.002 |
| `pan_cover_spacer_4` | 1 | 0.204 | 0.000 | 0.000 | 1.8 | 1.002 |
| `battery_tray` | 1 | 45.864 | 6.187 | 0.061 | 282.6 | 0.962 |
| `power_distribution_tray` | 1 | 5.517 | 0.000 | 0.000 | 31.0 | 0.999 |
| `servo_bus_adapter_tray` | 1 | 5.280 | 0.141 | 0.008 | 32.3 | 0.959 |
| `esp32_tray` | 1 | 4.332 | 0.141 | 0.010 | 26.1 | 1.004 |
| `ubec_tray` | 1 | 2.845 | 0.000 | 0.000 | 17.8 | 0.995 |
| `phone_pan_servo_saddle` | 1 | 22.407 | 1.162 | 0.122 | 126.5 | 0.964 |
| `phone_pan_servo_cap` | 1 | 9.750 | 0.944 | 0.033 | 49.4 | 1.010 |
| `phone_pan_hub` | 1 | 9.652 | 0.101 | 0.015 | 61.0 | 0.794 |
| `phone_cradle_rear_frame` | 1 | 25.382 | 3.368 | 0.122 | 173.1 | 0.858 |
| `phone_cradle_top_cap` | 1 | 16.125 | 0.430 | 0.029 | 94.7 | 0.757 |
| `phone_cradle_lower_clip_left` | 1 | 0.622 | 0.000 | 0.000 | 4.2 | 0.970 |
| `phone_cradle_lower_clip_right` | 1 | 0.622 | 0.000 | 0.000 | 4.0 | 0.969 |
| `phone_cradle_foot_left` | 1 | 4.786 | 0.216 | 0.011 | 26.0 | 0.938 |
| `phone_cradle_foot_right` | 1 | 4.786 | 0.216 | 0.011 | 26.0 | 0.938 |
| `yaw_case_saddle` | 4 | 21.994 | 0.591 | 0.000 | 118.1 | 0.894 |
| `case_cap_yaw` | 4 | 6.631 | 0.000 | 0.000 | 39.2 | 0.822 |
| `coxa_upper_and_hip_saddle` | 4 | 29.245 | 2.653 | 0.084 | 169.8 | 0.885 |
| `coxa_lower_auxiliary_arm` | 4 | 8.990 | 0.119 | 0.015 | 55.8 | 0.769 |
| `case_cap_hip` | 4 | 6.632 | 0.000 | 0.000 | 38.7 | 0.822 |
| `yaw_auxiliary_spacer_1` | 4 | 0.248 | 0.000 | 0.000 | 4.3 | 0.996 |
| `yaw_auxiliary_spacer_2` | 4 | 0.248 | 0.000 | 0.000 | 4.3 | 0.996 |
| `yaw_auxiliary_spacer_3` | 4 | 0.248 | 0.000 | 0.000 | 4.3 | 0.996 |
| `yaw_auxiliary_spacer_4` | 4 | 0.248 | 0.000 | 0.000 | 4.3 | 0.996 |
| `femur_main_and_knee_saddle` | 4 | 37.494 | 1.990 | 0.037 | 215.3 | 0.845 |
| `femur_auxiliary_cheek` | 4 | 12.990 | 0.000 | 0.000 | 79.9 | 0.853 |
| `case_cap_knee` | 4 | 6.631 | 0.000 | 0.000 | 39.2 | 0.822 |
| `tibia_curved_main_and_foot` | 4 | 22.853 | 2.608 | 0.037 | 150.4 | 0.801 |
| `tibia_auxiliary_cheek` | 4 | 6.824 | 0.000 | 0.000 | 43.9 | 0.874 |

## Profile and validation

The numeric profile uses a 0.4 mm nozzle, 0.20 mm layers, 0.42 mm nominal line width, five walls, six top and bottom layers, 35% gyroid, 210/60 C PLA, and an 8 mm3/s flow ceiling. Support is normal zigzag at 15%, with a 60% roof, 0.6 mm roof thickness, 0.2 mm Z separation and 0.5 mm XY clearance. All resolved settings and source hashes accompany the individual cases. It is an analysis profile, not measured printer calibration.

All slice motions fit the recorded 225 x 225 x 265 mm envelope. Peak nominal deposition flow was 6.930 mm3/s. The maximum relative difference between integrated E volume and Cura's rounded volume was 0.4520%. Small parts allow for the integer-rounded engine volume. No deposition remained unclassified.

The parser accounts for absolute and relative E, G92 resets, G90/G91 coordinate modes, and retraction repayment. It rejects unsupported arcs, volumetric extrusion or moving-Z deposition. Mode behavior follows the [Marlin M82 documentation](https://marlinfw.org/docs/gcode/M082.html) and [G92 documentation](https://marlinfw.org/docs/gcode/G092.html). Eight analytic/parser tests accompany this pipeline. The unchanged parser's independent toolpath review remains in the preserved R3 analysis folder.

The engine uses explicit placement with automatic centering disabled. Each case records the original STL to G-code transform and its inverse, including nonzero mesh minima. Engine coordinates are quantized to 0.001 mm; float32 export and vertex rounding errors are also recorded.

## Mass and inertia model

For each fresh deposited filament length E, the volume is `E * pi * 1.75^2 / 4`. Multiplying by the nominal 1.24 g/cm3 density gives mass. The bead centre lies half a layer below the commanded nozzle Z. A line segment from p to q has midpoint c and central second moment `m * ((c-C)(c-C)^T + (q-p)(q-p)^T / 12)`, where C is the complete part COM. Summed second moments yield `I = trace(Q) * identity - Q`. Millimetres are converted to metres in the returned inertia tensor.

An additional rectangular bead model infers cross-section width from emitted volume divided by path length and layer height. Its largest spectral inertia correction was 0.1384% among these SKUs. This quantifies one geometric approximation; actual bead shape, pressure, corner overlap, shrinkage and density remain unmeasured. No single infill multiplier is applied to CAD mass or inertia.

The uniform full-solid PLA mass, COM and inertia remain in every case as a separate comparison scenario. Neither scenario establishes printed strength. Actual part masses should replace these estimates after printing, while placement and joint loads need separate mechanical checks.

Per-category deposition path times omit acceleration, travel and cooling. Use only the total Cura slice time for print scheduling. All retained G-code commands are disabled and compressed; there are no machine-ready toolpaths in this analysis output.

## R3 comparison of changed production parts

The comparison uses preserved R3 deposition records and the new R4 slices with the same numeric material and speed profile. R3 source meshes and toolpaths were preserved, and were not resliced for this comparison.

| Part | R3 / R4 model g | R3 / R4 support g | R3 / R4 minutes |
| --- | ---: | ---: | ---: |
| `body_deck` | 89.49 / 87.07 | 0.00 / 0.00 | 548.2 / 535.4 |
| `case_cap_hip` | 6.59 / 6.63 | 0.00 / 0.00 | 38.5 / 38.7 |
| `case_cap_knee` | 6.59 / 6.63 | 0.00 / 0.00 | 38.5 / 39.2 |
| `case_cap_yaw` | 6.59 / 6.63 | 0.00 / 0.00 | 38.8 / 39.2 |
| `coxa_lower_auxiliary_arm` | 9.00 / 8.99 | 0.09 / 0.12 | 56.0 / 55.8 |
| `coxa_upper_and_hip_saddle` | 26.53 / 29.25 | 3.18 / 2.65 | 161.7 / 169.8 |
| `esp32_tray` | 4.38 / 4.33 | 0.14 / 0.14 | 26.4 / 26.1 |
| `femur_auxiliary_cheek` | 11.91 / 12.99 | 0.02 / 0.00 | 70.4 / 79.9 |
| `femur_main_and_knee_saddle` | 34.64 / 37.49 | 3.43 / 1.99 | 207.0 / 215.3 |
| `hex_faceted_cover` | 157.41 / 156.67 | 6.20 / 6.20 | 884.3 / 880.7 |
| `phone_pan_servo_cap` | 10.01 / 9.75 | 0.92 / 0.94 | 54.4 / 49.4 |
| `phone_pan_servo_saddle` | 21.95 / 22.41 | 1.37 / 1.16 | 135.5 / 126.5 |
| `power_distribution_tray` | 5.52 / 5.52 | 0.00 / 0.00 | 31.0 / 31.0 |
| `servo_bus_adapter_tray` | 5.32 / 5.28 | 0.14 / 0.14 | 32.5 / 32.3 |
| `tibia_auxiliary_cheek` | 7.02 / 6.82 | 0.00 / 0.00 | 43.9 / 43.9 |
| `tibia_curved_main_and_foot` | 23.12 / 22.85 | 2.61 / 2.61 | 151.2 / 150.4 |
| `yaw_auxiliary_spacer_1` | 0.22 / 0.25 | 0.00 / 0.00 | 3.8 / 4.3 |
| `yaw_auxiliary_spacer_2` | 0.22 / 0.25 | 0.00 / 0.00 | 3.8 / 4.3 |
| `yaw_auxiliary_spacer_3` | 0.22 / 0.25 | 0.00 / 0.00 | 3.8 / 4.3 |
| `yaw_auxiliary_spacer_4` | 0.22 / 0.25 | 0.00 / 0.00 | 3.8 / 4.3 |
| `yaw_case_saddle` | 19.93 / 21.99 | 1.35 / 0.59 | 114.1 / 118.1 |

Source manifest SHA-256: `6cac852c196e29e2da100816a7d3b96f545e62dba92c3009a46417eb7d9bc449`. Source meshes were checked again after the batch. These results apply to those bytes; changes to geometry, orientation or slicing settings require a new run.
