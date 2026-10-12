# R5 printing and changed support audit

The audit covers 34 production SKUs and 76 printed pieces. All current meshes are watertight, consistently wound and have positive volume. The overall result is `pass`. Component counts and bed fit are checked for every current export.

The legacy `tibia_curved_main_and_foot` SKU contains the straight R5 tibia. Its broad main cheek remains the print base; the central transverse shank and short bridge require local support review. Remove support from the knee interface and transverse fastener access before measuring fit. The separate auxiliary cheek remains on its broad face.

The complete recorded slices predict 1056.06 g of part PLA and 55.83 g of removable support. Relative to R4, model PLA changes by +8.42 g and support by +4.88 g. These are commanded-filament estimates.

| Changed SKU | Current dimensions, mm | Current bed contact, mm2 | R4 / R5 support, g | R4 / R5 time, min |
| --- | --- | ---: | ---: | ---: |
| `body_deck` | 178.40 x 206.00 x 4.00 | 21409.0 | 0.00 / 0.00 | 535.40 / 524.68 |
| `coxa_upper_and_hip_saddle` | 102.11 x 60.37 x 31.50 | 596.4 | 2.65 / 2.50 | 169.81 / 173.85 |
| `coxa_lower_auxiliary_arm` | 46.97 x 28.00 x 9.00 | 904.8 | 0.12 / 0.12 | 55.77 / 52.58 |
| `case_cap_hip` | 61.23 x 30.00 x 4.00 | 1480.0 | 0.00 / 0.00 | 38.71 / 36.23 |
| `femur_auxiliary_cheek` | 93.00 x 46.50 x 8.00 | 2997.5 | 0.00 / 0.00 | 79.87 / 80.09 |
| `tibia_curved_main_and_foot` | 124.00 x 28.00 x 42.00 | 1419.2 | 2.61 / 3.98 | 150.37 / 178.34 |
| `tibia_auxiliary_cheek` | 65.00 x 28.00 x 5.10 | 1409.9 | 0.00 / 0.00 | 43.86 / 38.78 |

The JSON records volumes, dimensions, connected components, print rotations, bed contact and projected downward area for every SKU. A low support mass does not establish that an inaccessible interface will cleanly release. Inspect the actual sliced layers around servo seats, nut pockets and the central tibia shank. Use local support and an appropriate brim where the supplied orientation has small first-layer contact.

Added SKUs: none. Removed SKUs: none. Quantity changes: 0.

Source manifest SHA-256: `67f0d5e3bfb633414722b17305cef4212ca7f8fa753aa922a252bc383306ad3d`. Production-properties SHA-256: `ab1bf424b18f5d8d96ab792fa2a05b18a8f186988033876dbc758074ee76c7f8`.
