# Production slicing and deposited mass properties

CuraEngine sliced all 34 production SKUs, representing 76 printed pieces, from `hex_quad_r3_manufacturing`. The robot-part PLA estimate is 1017.8 g; removable support is 62.0 g and adhesion material is 1.2 g. Printing every piece separately at the recorded profile totals 102.6 predicted hours. A packed plate has different travel, cooling and adhesion overhead.

Part mass, centre of mass and inertia come from each emitted model-deposition path. Support, support interfaces and skirt material stay separate. The properties use the exact supplied print-STL frame in millimetres; `mass_kg`, `com_mm` and `inertia_kg_m2` are the fields to transform into each assembly link. The inertia tensor is about the deposited part's own centre of mass.

| SKU | Qty | Part PLA, g | Support, g | Adhesion, g | Time, min | Part / full-solid mass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `body_deck` | 1 | 90.420 | 0.000 | 0.000 | 552.7 | 0.802 |
| `hex_faceted_cover` | 1 | 157.410 | 6.203 | 0.038 | 884.3 | 0.941 |
| `pan_cover_spacer_1` | 1 | 0.204 | 0.000 | 0.000 | 1.8 | 1.002 |
| `pan_cover_spacer_2` | 1 | 0.204 | 0.000 | 0.000 | 1.8 | 1.002 |
| `pan_cover_spacer_3` | 1 | 0.204 | 0.000 | 0.000 | 1.8 | 1.002 |
| `pan_cover_spacer_4` | 1 | 0.204 | 0.000 | 0.000 | 1.8 | 1.002 |
| `battery_tray` | 1 | 45.864 | 6.187 | 0.061 | 282.6 | 0.962 |
| `power_distribution_tray` | 1 | 5.517 | 0.000 | 0.000 | 31.0 | 0.999 |
| `servo_bus_adapter_tray` | 1 | 5.325 | 0.141 | 0.008 | 32.5 | 0.959 |
| `esp32_tray` | 1 | 4.379 | 0.139 | 0.008 | 26.4 | 1.004 |
| `ubec_tray` | 1 | 2.845 | 0.000 | 0.000 | 17.8 | 0.995 |
| `phone_pan_servo_saddle` | 1 | 21.946 | 1.373 | 0.122 | 135.5 | 0.969 |
| `phone_pan_servo_cap` | 1 | 10.012 | 0.919 | 0.033 | 54.4 | 0.999 |
| `phone_pan_hub` | 1 | 9.652 | 0.101 | 0.015 | 61.0 | 0.794 |
| `phone_cradle_rear_frame` | 1 | 25.382 | 3.368 | 0.122 | 173.0 | 0.858 |
| `phone_cradle_top_cap` | 1 | 16.125 | 0.430 | 0.029 | 94.7 | 0.757 |
| `phone_cradle_lower_clip_left` | 1 | 0.622 | 0.000 | 0.000 | 4.2 | 0.970 |
| `phone_cradle_lower_clip_right` | 1 | 0.622 | 0.000 | 0.000 | 4.0 | 0.969 |
| `phone_cradle_foot_left` | 1 | 4.786 | 0.216 | 0.011 | 26.0 | 0.938 |
| `phone_cradle_foot_right` | 1 | 4.786 | 0.216 | 0.011 | 26.0 | 0.938 |
| `yaw_case_saddle` | 4 | 19.933 | 1.348 | 0.000 | 114.1 | 0.929 |
| `case_cap_yaw` | 4 | 6.592 | 0.000 | 0.000 | 38.8 | 0.820 |
| `coxa_upper_and_hip_saddle` | 4 | 26.527 | 3.181 | 0.085 | 161.7 | 0.912 |
| `coxa_lower_auxiliary_arm` | 4 | 9.005 | 0.086 | 0.015 | 56.0 | 0.763 |
| `case_cap_hip` | 4 | 6.592 | 0.000 | 0.000 | 38.5 | 0.820 |
| `yaw_auxiliary_spacer_1` | 4 | 0.222 | 0.000 | 0.000 | 3.8 | 0.987 |
| `yaw_auxiliary_spacer_2` | 4 | 0.222 | 0.000 | 0.000 | 3.8 | 0.987 |
| `yaw_auxiliary_spacer_3` | 4 | 0.222 | 0.000 | 0.000 | 3.8 | 0.987 |
| `yaw_auxiliary_spacer_4` | 4 | 0.222 | 0.000 | 0.000 | 3.8 | 0.987 |
| `femur_main_and_knee_saddle` | 4 | 34.644 | 3.429 | 0.056 | 207.0 | 0.877 |
| `femur_auxiliary_cheek` | 4 | 11.914 | 0.018 | 0.002 | 70.4 | 0.833 |
| `case_cap_knee` | 4 | 6.592 | 0.000 | 0.000 | 38.5 | 0.820 |
| `tibia_curved_main_and_foot` | 4 | 23.125 | 2.608 | 0.037 | 151.2 | 0.803 |
| `tibia_auxiliary_cheek` | 4 | 7.019 | 0.000 | 0.000 | 43.9 | 0.871 |

## Profile and validation

The numeric profile uses a 0.4 mm nozzle, 0.20 mm layers, 0.42 mm nominal line width, five walls, six top and bottom layers, 35% gyroid, 210/60 C PLA, and an 8 mm3/s flow ceiling. Support is normal zigzag at 15%, with a 60% roof, 0.6 mm roof thickness, 0.2 mm Z separation and 0.5 mm XY clearance. All resolved settings and source hashes accompany the individual cases. It is an analysis profile, not measured printer calibration.

All slice motions fit the recorded 225 x 225 x 265 mm envelope. Peak nominal deposition flow was 6.959 mm3/s. The maximum relative difference between integrated E volume and Cura's rounded volume was 0.3992%. Small parts allow for the integer-rounded engine volume. No deposition remained unclassified.

The parser accounts for absolute and relative E, G92 resets, G90/G91 coordinate modes, and retraction repayment. It rejects unsupported arcs, volumetric extrusion or moving-Z deposition. Mode behavior follows the [Marlin M82 documentation](https://marlinfw.org/docs/gcode/M082.html) and [G92 documentation](https://marlinfw.org/docs/gcode/G092.html). Eight analytic/parser tests and the independent R2 toolpath review are saved alongside the pipeline.

The engine uses explicit placement with automatic centering disabled. Each case records the original STL to G-code transform and its inverse, including nonzero mesh minima. Engine coordinates are quantized to 0.001 mm; float32 export and vertex rounding errors are also recorded.

## Mass and inertia model

For each fresh deposited filament length E, the volume is `E * pi * 1.75^2 / 4`. Multiplying by the nominal 1.24 g/cm3 density gives mass. The bead centre lies half a layer below the commanded nozzle Z. A line segment from p to q has midpoint c and central second moment `m * ((c-C)(c-C)^T + (q-p)(q-p)^T / 12)`, where C is the complete part COM. Summed second moments yield `I = trace(Q) * identity - Q`. Millimetres are converted to metres in the returned inertia tensor.

An additional rectangular bead model infers cross-section width from emitted volume divided by path length and layer height. Its largest spectral inertia correction was 0.1384% among these SKUs. This quantifies one geometric approximation; actual bead shape, pressure, corner overlap, shrinkage and density remain unmeasured. No single infill multiplier is applied to CAD mass or inertia.

The uniform full-solid PLA mass, COM and inertia remain in every case as a separate comparison scenario. Neither scenario establishes printed strength. Actual part masses should replace these estimates after printing, while placement and joint loads need separate mechanical checks.

Per-category deposition path times omit acceleration, travel and cooling. Use only the total Cura slice time for print scheduling. All retained G-code commands are disabled and compressed; there are no machine-ready toolpaths in this analysis output.

## R2 comparison of integrated leg parts

The comparison reslices the three R2 source meshes with the same explicit numeric profile. Coxa orientation and R3 geometry both change, so this measures the complete production proposal rather than geometry alone.

| Part | R2 / R3 model g | R2 / R3 support g | R2 / R3 minutes |
| --- | ---: | ---: | ---: |
| `coxa_upper_and_hip_saddle` | 25.88 / 26.53 | 3.33 / 3.18 | 156.8 / 161.7 |
| `femur_main_and_knee_saddle` | 27.19 / 34.64 | 3.58 / 3.43 | 172.3 / 207.0 |
| `tibia_curved_main_and_foot` | 19.60 / 23.12 | 2.94 / 2.61 | 132.6 / 151.2 |

Source manifest SHA-256: `82aed2d2889269b3630fe9f43d932f5a6d14a59f940d817e545511643ab4222f`. Source meshes were checked again after the batch. These results apply to those bytes; changes to geometry, orientation or slicing settings require a new run.
