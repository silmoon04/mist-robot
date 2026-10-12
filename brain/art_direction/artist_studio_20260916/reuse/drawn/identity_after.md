# Identity verification after the renderer changes

Rest identity: PASS. 40 faces, 80 eyes and 120 actual canonical canvas paths checked.

All 1560 directed transitions ended on the exact canonical target geometry. Rest drew 0 raster eyes.

Renderer SHA-256: `9ade474f61fc9a6f3eee260b6bb07ef4adc2a4e6f56cae3a4871acbc531563ff`

Every original eye now keeps its exact canonical path, size, stroke width, mirror and rotation outside the blink. The actual canvas commands were checked against the original runtime; this is not an assertion copied from the renderer owner.

Pixel-backed fitting ran for all 30 eye parts. The following ratios concern a forced generated rest cel for diagnostics, not the visible resting face.

| Source part | Uses | Width ratio range | Height ratio range | Largest center difference |
|---|---:|---:|---:|---:|
| angry_hook_00 | 4 | 0.993 to 1.023 | 0.980 to 0.981 | 0.276 |
| chevron_01 | 8 | 0.995 to 1.013 | 0.944 to 0.945 | 0.148 |
| circle_gap_02 | 6 | 0.991 to 1.002 | 0.965 to 0.979 | 0.145 |
| circle_gap_03 | 6 | 0.982 to 0.994 | 0.957 to 0.970 | 0.112 |
| circle_gap_04 | 1 | 0.996 to 0.996 | 0.849 to 0.849 | 0.047 |
| closed_lid_arc_05 | 6 | 0.865 to 0.869 | 0.981 to 1.001 | 0.078 |
| closed_lid_arc_06 | 2 | 0.863 to 0.868 | 0.996 to 0.998 | 0.076 |
| closed_lid_arc_07 | 2 | 0.994 to 0.998 | 0.920 to 0.921 | 0.082 |
| droop_hook_08 | 1 | 0.996 to 0.996 | 0.926 to 0.926 | 0.046 |
| droop_hook_09 | 2 | 0.996 to 0.997 | 0.978 to 0.981 | 0.050 |
| droop_hook_10 | 1 | 0.977 to 0.977 | 0.997 to 0.997 | 0.050 |
| e_shape_11 | 3 | 0.994 to 0.998 | 0.914 to 0.935 | 0.135 |
| e_shape_12 | 6 | 0.993 to 0.995 | 0.913 to 0.948 | 0.147 |
| e_shape_13 | 1 | 0.995 to 0.995 | 0.995 to 0.995 | 0.064 |
| flat_bar_14 | 4 | 0.997 to 0.997 | 0.942 to 0.947 | 0.031 |
| happy_arc_15 | 2 | 0.889 to 0.889 | 0.996 to 0.997 | 0.058 |
| happy_arc_16 | 4 | 0.988 to 0.994 | 0.904 to 1.070 | 0.697 |
| happy_arc_17 | 2 | 0.877 to 0.879 | 0.998 to 1.002 | 0.067 |
| happy_arc_18 | 2 | 0.933 to 0.933 | 0.996 to 0.996 | 0.063 |
| happy_arc_19 | 2 | 0.859 to 0.861 | 0.997 to 1.002 | 0.088 |
| open_C_42 | 1 | 0.991 to 0.991 | 1.000 to 1.000 | 0.048 |
| open_C_43 | 2 | 0.994 to 1.000 | 0.962 to 0.965 | 0.073 |
| open_C_44 | 4 | 0.997 to 1.008 | 0.987 to 1.036 | 0.135 |
| open_C_45 | 1 | 0.844 to 0.844 | 0.999 to 0.999 | 0.032 |
| open_C_46 | 1 | 0.996 to 0.996 | 0.914 to 0.914 | 0.053 |
| open_C_47 | 1 | 0.996 to 0.996 | 0.953 to 0.953 | 0.046 |
| open_C_48 | 2 | 0.994 to 0.997 | 0.935 to 0.956 | 0.179 |
| open_C_49 | 1 | 0.905 to 0.905 | 0.999 to 0.999 | 0.048 |
| open_C_50 | 1 | 0.963 to 0.963 | 1.000 to 1.000 | 0.068 |
| open_C_51 | 1 | 0.871 to 0.871 | 0.999 to 0.999 | 0.033 |

Warning: Canonical-mouthless faces have no speech mouth: 12_happy_09_manual, 35_sad_10_manual


This verifies exact rest identity and endpoint geometry. Visual motion quality and audible synchronisation require separate playback review.
