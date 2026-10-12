# Preliminary shaft, belt and printed-link screen

Calculated 7 September 2026. This is a comparative static screen, not a strength certification or a print release.

The current 3.95376 kg estimate gives 29.09 N per supporting leg for two contacts and a 1.5 load multiplier. The robot mass still contains estimated leg components. These calculations must be repeated using the complete CAD mass and actual load locations.

## Belt load and shaft support

At 3 N m and a 15 mm pitch radius, the tension difference is 200 N. An illustrative 150 N initial tension in each span gives 250 N in the tight span and 50 N in the slack span, for about 300 N resultant pulley pull when the spans are parallel. This is a load case, not an installation tension recommendation. Actual allowable tension, minimum pulley size and tooth engagement depend on the chosen belt.

Gates treats belt tension, sprocket size and precision/backlash as coupled design choices. Its rated reinforced belts and matched metal sprockets do not establish the strength or accuracy of an unknown belt and printed tooth profile. [Gates precision-drive design manual](https://www.gates.com/content/dam/documents-library/catalogs/light-power-and-precision-manual.pdf).

| Smooth shaft diameter | 3 N m / 300 N, centred in 24 mm span | Same load, 12 mm outside 24 mm span |
|---|---:|---:|
| 4 mm | 503.0 MPa | 706.6 MPa |
| 5 mm | 257.6 MPa | 361.8 MPa |
| 6 mm | 149.0 MPa | 209.4 MPa |
| 7 mm | 93.9 MPa | 131.8 MPa |
| 8 mm | 62.9 MPa | 88.3 MPa |

The shaft result combines bending and torsion with von Mises stress. It assumes a smooth solid circular shaft, simple bearing supports, static loading and a nominal steel elastic modulus of 200 GPa. It omits flats, holes, threads, clamp notches, stress concentrations, fatigue and fit wear. The 100 MPa comparison threshold in the JSON is an analyst-selected screen, not the strength of owned hardware.

For the overhung case, bearing reactions are -150 N and +450 N. The reversed reaction means both bearings and retainers must carry load in both directions. Merely adding a second bearing on the same side of the pulley does not provide the benefit of placing the pulley between its supports. A 5 mm knee-input trunnion deserves particular scrutiny; choose support spacing and material before committing it to the current bearing inventory.

The 3.5:1 hip gear can reach about 4.81 N m at the chosen 12 V short-peak shaft torque and 85% assumed efficiency. An 8 mm-face, module-1 20/70 pair has a 35 mm driven pitch radius and approximately 146 N resultant mesh force at that load. Tooth stress, mesh phase, wear and the servo horn still require separate checks. Raising ratio does not remove the need to transmit output torque through a real shaft and hub.

## Printed link comparisons

These are ideal 140 mm cantilevers under the same transverse force. They compare simple uninterrupted sections. The real linkage and motor coupling need their own free-body diagrams; this deliberately conservative section screen does not replace them.

| Section | Nominal bending stress | Illustrative stress with factor 2 | Deflection at assumed E = 1.5 GPa |
|---|---:|---:|---:|
| solid24x18 | 3.14 MPa | 6.28 MPa | 1.52 mm |
| closed24x18_wall2.4 | 4.59 MPa | 9.18 MPa | 2.22 mm |
| two4.2x20_cheeks_ideal_equal_share | 7.27 MPa | 14.54 MPa | 3.17 mm |
| two4.2x28_cheeks_ideal_equal_share | 3.71 MPa | 7.42 MPa | 1.15 mm |

The two-cheek cases assume equal load sharing and adequate bolted spacers. Without cross ties, one cheek may carry most of the force or the assembly may twist. The closed box result assumes continuous walls and bonded corners. Bearing holes, belt openings, seams and sparse infill reduce the useful section; a nominal infill percentage cannot simply be substituted for the section modulus.

Print the long cheeks broad-face down so roads run along the main bending path. Carry joint loads through smooth metal shafts, inner-race spacers and through-fasteners. A narrow upright printed spindle repeats the prior layer-splitting failure. Keep screws and caps from peeling a short Z-layer stack away from a bearing boss. The 10 MPa comparison threshold and 1.5 GPa modulus are sensitivity assumptions; no PETG strength, layer adhesion, creep or fatigue property has been measured for this printer/profile.

## Bearing and fastener implications

At a 30 mm transverse offset, the selected 29.09 N leg force alone adds 0.873 N m bending at the yaw support. A 24 mm bearing separation reacts that moment through a 36.4 N force couple, before other offsets, gear forces or impacts. Nominal bearing dimensions do not establish capacity for the purchased unbranded assortment. The final BOM must count two supports, spacers and retainers for every shaft; ten of a single bearing type can disappear quickly across four hips.

Do not make the two M3 coupon-clamp bolts proof of a torque-carrying hub. The test measures fit and assembly. Clamping friction depends on preload, material, contact radius and creep; none is known here. Positive torque transfer, metal clamping hardware or a tested interface remains necessary. Heat inserts are for measured retention loads, not journals or an assumed substitute for a through-bolt load path.

Run `python structural_screen.py` to regenerate the JSON and this table. The script checks nonphysical inputs; scaling checks confirm that doubling shaft diameter reduces stress by eight and bending deflection by sixteen at fixed load/span. No finite-element, fatigue, creep or physical test is claimed.
