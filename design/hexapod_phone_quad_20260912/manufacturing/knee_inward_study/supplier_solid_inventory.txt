# Supplier STEP solid inventory

Inspected 12 September 2026 with OCP. Index order is the `TopExp_Explorer` solid order in the unmodified official Waveshare `ST3215.step`. All coordinates below use the supplier frame: X along the case, Y along the shafts, Z across case width. Values are rounded to three decimal places. COM means uniform-volume centroid, not the physical mass center of a mixed-material component. Identity labels are geometry-based interpretations, not verified part names.

| Index | Likely identity | Volume, mm³ | X bounds, mm | Y bounds, mm | Z bounds, mm | Volume centroid XYZ, mm |
|---|---|---:|---|---|---|---|
| 0 | Middle case section | 14253.284 | -35.612 to 9.612 | -15.100 to -1.200 | -12.362 to 12.362 | (-12.873, -7.691, 0.004) |
| 1 | Main-side case cover | 8526.533 | -35.500 to 9.500 | -2.200 to 7.500 | -12.250 to 12.250 | (-11.997, 1.886, -0.001) |
| 2 | Auxiliary-side case cover with integral auxiliary stub | 11128.220 | -35.610 to 9.610 | -28.200 to -14.100 | -12.360 to 12.360 | (-12.822, -19.310, 0.000) |
| 3 | Internal motor-like component, axis displaced from output shaft | 5285.832 | -8.525 to 8.525 | -26.500 to 4.000 | -9.775 to 7.275 | (0.000, -11.429, -1.250) |
| 4 | Internal PCB-like slab with simplified attached volume | 1237.987 | -33.800 to -5.000 | -20.500 to -13.300 | -10.550 to 10.550 | (-15.722, -15.645, 0.060) |
| 5 | Output gear and splined shaft | 825.016 | -34.300 to -16.700 | -10.200 to 8.100 | -8.795 to 8.795 | (-25.500, -1.605, 0.011) |
| 6 | Main horn with female spline and four peripheral holes | 757.429 | -35.100 to -15.900 | 5.100 to 9.600 | -9.600 to 9.600 | (-25.500, 7.997, 0.000) |
| 7 | Auxiliary disc with plain center bore and four peripheral holes | 566.049 | -35.100 to -15.900 | -27.650 to -24.300 | -9.600 to 9.600 | (-25.500, -26.434, 0.000) |

The isolated line projections in `supplier_solid_inventory.png` establish these distinctions: solids 0, 1 and 2 have the case footprint; solid 5 contains gear teeth and the output spline; solid 6 has a female spline; solid 7 has a plain center bore. The internal identities of solids 3 and 4 are less certain and unnecessary for exterior clearance screening.

## Body and shaft envelope

Removing accessory solids 6 and 7 leaves a useful supplier body reference. Solids 0, 1 and 2 supply the case exterior and auxiliary stub, and solid 5 supplies the output shaft. Keeping internal solids 3 and 4 in a body compound should not change the exterior bounds, but they are unnecessary for a simplified exterior component. Do not sum these CAD volumes to estimate actual servo mass; use the manufacturer's 55 g nominal mass.

| Axial check | Supplier Y coordinates, mm | Result | C018 drawing |
|---|---|---:|---:|
| Main face to auxiliary face | 4.9 to -24.1 | 29.0 mm | 29.0 mm |
| Main shaft projection | 4.9 to 8.1 | 3.2 mm | 3.4 mm |
| Auxiliary stub projection | -24.1 to -28.2 | 4.1 mm | 4.1 mm |
| Body and shafts, horns removed | -28.2 to 8.1 | 36.3 mm | 36.5 mm |
| Entire supplied assembly | -28.2 to 9.6 | 37.8 mm | Accessories excluded from the 36.5 mm callout |

The main horn extends 1.5 mm beyond the supplier shaft tip and therefore increases the assembly extent from 36.3 to 37.8 mm. The auxiliary disc reaches Y = -27.65 and stays 0.55 mm inside the auxiliary stub tip, so it does not set the assembly minimum. Its 3.35 mm axial extent also differs from the C018 accessory drawing's 3.1 mm. Use the exact C018 drawing for independently constructed horns and disc rather than silently adopting this older STEP's accessory dimensions.

The shaft projection differs by 0.2 mm even though the footprint, shaft offset and opposed faces agree. For a conservative C018 exterior envelope, extend the main shaft reservation to local Z = +3.4 mm. The supplier body remains a substantially better source for stepped case topology than a single rectangular block, but it is not an exact substitute for the current drawing or owned-unit fit measurements. Main-shaft spline engagement, actual horn seating and connector plug clearance still need measurement.

The correct transform into the current servo frame is `x = -(X + 25.5), y = Z, z = Y - 4.9`. This puts the main face at local Z = 0 and the auxiliary face at local Z = -29. Geometry and measurements came from the downloaded official supplier model; no old robot geometry was adopted.
