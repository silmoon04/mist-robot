# MIST first fit bed

Open `bed1/MIST_BED1_ALL_PARTS.3mf` as a model in the slicer. It contains seven
separate objects already arranged at Z = 0 in a **206 x 202.5 x 10 mm** envelope.
Center them as a group and keep their orientations. The STEP and individual STLs
are beside the 3MF. `BED1_TOP_VIEW.png` is the placement and measurement guide.

This is a fit test bed. Its 3MF contains geometry and millimetre units, with no
printer, material, temperature, speed or support profile. No G-code is supplied.
The full model volume is 75.35 cm3, about 93.4 g if it were solid PLA at
1.24 g/cm3. The slicer's actual estimate will depend on walls and infill.

The previous thin 624 coupon passed, but its 13.25 mm hole later needed hammering
in a full boss. Upright printed axles also snapped. These specimens therefore
use the proposed full bearing width, an 8 mm increase from bearing OD to boss OD,
a 1.2 mm floor, and the actual Z-axis print orientation. Metal shafts replace
printed structural journals. A result transfers only to a part with the same
boss section, orientation, material and relevant slicing settings.

## What is on the bed

| Object | Test |
| --- | --- |
| 01 bearing carrier | 28 full-depth seats, four sizes for each of seven bearing OD groups |
| 02 hardware board | M3/M4 insert pilots, clearance holes for metal shafts and bolts, nut traps, three loom slots |
| 03 servo gauge | 25.23 and 25.43 mm case-width openings |
| 04 and 05 clamp jaws | Two opposed jaws around an 8 mm metal shaft; 05 also carries a belt-pitch ruler |
| 06 and 07 retainer | A 13.40 mm 624 bearing seat and a separate cap with a 10 mm opening |

The bearing carrier has a thin connecting frame instead of a large backing
plate. The frame lets the 28 specimens print and be handled as one object. Keep
it intact during measurement. Its small inward ledge is confined to the bottom
1.2 mm. The full seat above that ledge has the stated cylindrical diameter;
there are no tabs projecting into the fit surface. Three underside access holes
let a small blunt pin push on the outer race during removal.

Numbers are cut into the model, not just drawn on the guide. Each boss has its
nominal OD on one rim and `025`, `040`, `055` or `070` on the opposite rim. These
mean +0.25, +0.40, +0.55 or +0.70 mm **on diameter**, respectively. Engravings are
0.4 mm deep, with strokes at least 0.4 mm wide. Hole choices increase left to
right, and the OD rows increase from the bottom of the guide upward.

| Bearings covered | ID x OD x width / mm | Four CAD seats / mm |
| --- | --- | --- |
| 693 | 3 x 8 x 4 | 8.25, 8.40, 8.55, 8.70 |
| 623 | 3 x 10 x 4 | 10.25, 10.40, 10.55, 10.70 |
| 685 | 5 x 11 x 5 | 11.25, 11.40, 11.55, 11.70 |
| 624 | 4 x 13 x 5 | 13.25, 13.40, 13.55, 13.70 |
| 687 | 7 x 14 x 5 | 14.25, 14.40, 14.55, 14.70 |
| 626 | 6 x 19 x 6 | 19.25, 19.40, 19.55, 19.70 |
| 627 and 608 | 7/8 x 22 x 7 | 22.25, 22.40, 22.55, 22.70 |

The housing pocket is nominal bearing width +0.2 mm deep, including a 0.6 mm
entry lead-in. Actual bearing OD and width still need measurement. The 627 and
608 share a housing test because their OD and width are the same; test their
different inner bores against the actual metal shafts separately.

On the hardware board, the two five-hole rows nearest Y = 0 are the insert
pilots. Row M3 is 4.2, 4.4, 4.6, 4.8 and 5.0 mm, 6 mm deep. Row M4 is 5.2, 5.4,
5.6, 5.8 and 6.0 mm, 8 mm deep. Both have 2 mm of material below the hole. The
insert names identify the intended thread only: **the purchased insert OD and
length have not been measured**, so neither row is an approved heat-insert fit.
Do not force an insert longer than its pilot depth into the floor. A cold slip
test alone cannot approve a heat-set joint.

Above them, the metal-shaft clearance tests are arranged as pairs of groups:
3/4 mm, then 5/6 mm, then 7/8 mm. Each group has nominal +0.15, +0.30 and
+0.45 mm bores left to right in a 2 mm wall. They test clearance in a printed
part. The actual bearing inner race is tested with the measured metal shaft,
not with a printed gauge pretending to be a structural axle.

The bolt rows use nominal +0.20, +0.40 and +0.60 mm in a 4 mm wall. Nut traps
use nominal across-flats 5.5 mm for M3 and 7.0 mm for M4, each with +0.15,
+0.30 and +0.45 mm choices. Their depths are 2.8 and 3.6 mm respectively in a
6 mm section. Measure the actual nuts before treating those assumptions as
correct. The top three wire slots are 4, 6 and 8 mm wide and 7 mm long. Pass the
actual connector and sleeved loom through them, and record the required width.

The servo gauge checks only case width. Opening 1 preserves the previously
successful 25.23 mm value; opening 2 adds 0.20 mm. It does not validate the case
length, ears, horn, cable exit, lid contact or a different servo case revision.

## Printing and recording the fit

Use the same filament, nozzle, flow, line width, wall count, cooling, speeds and
XY hole compensation intended for the robot carriers. Record these before
printing. A 0.20 mm layer height resolves the 1.2 mm floor and 0.4 mm labels
exactly. If the final parts will use 0.30 mm, test at that height instead and
record the slicer's rounding of the 0.4 mm lettering and 0.2 mm pocket allowance.
The earlier 0.30 mm profile is useful evidence, but it is not bundled as an
assumed compatible machine profile here.

All openings face upward and the clamp screw slots are open at the top. The
geometry needs no designed supports. Inspect the actual slicer preview for
thin walls, layer starts, label resolution and islands before printing. A brim
must still fit the configured bed after centering; the 206 mm part extent does
not include one.

1. Let the parts cool, remove strings and burrs, and measure the real hardware.
   Do not drill or sand the test surface before its first measurement.
2. Start a bearing in the largest seat and move toward smaller choices. Select
   a clean hand slip fit that reaches the shoulder and can be removed. Impact
   force, cracking or whitening is a failed fit, consistent with the earlier
   thick-boss failure.
3. Record measured hole diameter in two directions, bearing OD and width, the
   feature ID, fit result and print settings in `feedback_BED1.csv`. Put the
   second axis and seat-depth measurement in `notes`. Hole callipers are less
   reliable on tiny bores; also record the physical pass/fail with that hardware.
4. Check insert length and knurl OD before choosing a pilot. After heat setting
   and complete cooling, record spinning, cracks and pull-out behavior in notes.
   Insert retention remains a separate test from a cold dimensional fit.
5. Repeat the chosen bearing against a second specimen from its batch. A loose
   bearing can still be retained axially, but radial play remains in the joint.

`fit_result` accepts `slip`, `loose`, `tight`, `failed` or `not_tested`. Leave
unmeasured fields blank instead of filling in CAD dimensions as measurements.
For the insert rows, the `nominal_mm` field is the assumed intended pilot bore
(4.6 or 5.6), while `measured_hardware_mm` is the measured knurl OD. These two
numbers serve different purposes. The script never substitutes the knurl OD
for an insert pilot dimension.

## Clamp and retainer assembly trials

For the clamp, move object 05 by **(0, -4.5, 0) mm** relative to its printed
position to align the two circular grooves. The mating jaw faces then have a
0.5 mm gap; the 8.30 mm bore centres coincide at (157, 159.25) in the bed
coordinates. Place an 8 mm metal shaft through the grooves. Use two M3 x 30
bolts through the open slots, with 6–7 mm OD washers under heads and nuts. Seat
the bolts low in the slots. Tighten evenly by hand while watching the face gap
and the shaft. Record slipping and cracking. This specimen checks the clamp
interface and assembly, not a structural load rating. Its printed layers lie in
the jaw plane; the shaft itself is metal.

For the 624 retainer, first choose a slip seat on object 01. Object 06 is a fixed
13.40 mm trial; use it only if the bearing actually fits. Insert the bearing from
above and place object 07 at **(-37, 0, 6.4) mm** relative to its printed
position. This aligns the holes 25 mm apart. Use two M3 x 16 bolts with nuts and
washers. The cap leaves the inner race clear and overlaps the outer race. The
nominal 0.2 mm axial allowance avoids relying on a press fit for retention;
check that the cap does not rub the spinning inner race. An 8 mm shaft clamp
and a 4 mm-ID 624 retainer are independent tests and do not join together.

Those bolt lengths are test hardware requirements, not an assumption about
what is already in stock. M3 x 12 screws may not fully engage the nuts. Bearing,
width and clearance tests can be completed before that hardware is available.

The ruler attached to object 05 has 2 mm and 3 mm tick spacing. Compare several
successive belt teeth with it and measure the span with callipers. It does not
identify GT/HTD/other tooth shapes and is not a belt engagement specimen. A
functional pulley or belt clamp still requires the actual pitch, profile and
belt width.

## After the first print

The second bed is deliberately absent until measured feedback is supplied.
`refine_from_feedback.py` rejects an empty sheet, unmeasured test results,
missing print settings and invalid numbers. It produces interface-specific
candidate dimensions at a 0.05 mm step. A passing 13 mm bearing seat does not
silently change a 22 mm seat, nut pocket or insert pilot.

```powershell
python refine_from_feedback.py feedback_BED1.csv --out refinement_request.json
```

`build_refined_bed.py` turns a verified request into actual second-bed geometry
for the submitted interface groups. It checks the source CSV hash and rebuilds
the request before using its dimensions. It creates a new output directory,
keeps the bearing sections and print axes, and supplies another blank feedback
sheet. Clamp changes require a separate engineering review and are refused by
the generic refinement builder. Its output remains a fit test, not a production
release.

```powershell
python build_refined_bed.py refinement_request.json --out bed2_measured
```

Use a CAD-enabled Python environment for that command. On this Windows host,
CadQuery currently has a reproducible shutdown crash after export; the files
passed internal geometry checks, but the CLI did not exit cleanly. See
`TOOLING_CHECKS.md` for the exact limitation and the separately checked test
results. The script keeps the failure visible.

The working defaults in `fit_parameters.json` remain marked unvalidated. In
particular, 13.40 mm is a candidate, not a new measurement. After the second
physical fit check, copy only the approved dimensions to the matching carrier
parameters and regenerate the leg. A different material, orientation, wall
section or slicing profile requires another representative fit check.

## CAD source and checks

`build_coupon_bed.py` creates `coupon_recipe.json` and the CadQuery solids.
`fusion_coupon_bed.py` replays the same recipe as native Fusion components,
sketches, extrudes and cone lofts in a new document, with a separate output
folder for each run. The Fusion script has passed Python and recipe checks;
running it inside an authenticated Fusion session and reviewing the resulting
timeline remains outstanding.

The delivered first-bed exports passed valid-BRep, one-solid-per-object,
watertight mesh, consistent winding, bed-bounds and zero inter-part-volume
intersection checks. See `bed1/validation.json`. These tests do not establish
printed fit or load capacity. The 3MF is a geometry exchange file, not a native
Fusion design or a printer project.

The existing Fusion coupon files and printed-part history were left intact.
Their relevant evidence is in
`fusion360/bearing_heatset_calibration_kit_compact_v2/README_COMPACT_V2.md` and
`fusion360/remote_knee_624zz_test_leg_v2/README_PRINT_V2.md` beside this repository.
