# Calibration failure audit

The user reported a second unsuccessful calibration print on 15 September 2026. Three photographs show loose strands, irregular deposits and clumps on the base paths. Stop using the original and V2 hand-generated calibration files. They have not demonstrated a usable printing process.

## Confirmed findings

The earlier robot coupons and overnight parts succeeded with the supplied Cura profiles. The inspected DFM profile uses PLA at 210 C / 60 C, 0.28 mm layers, first-layer speed 25 mm/s, first-layer printing acceleration 500 mm/s2, first-layer travel 60 mm/s, retraction 0.5 mm at 35 mm/s, and no Z hop. Outer walls are 40 mm/s and inner walls/infill 65 mm/s. Configured rates describe the profile; they do not establish achieved speed on every feature or the hotend's maximum flow.

V2 slowed the first layer to 12 mm/s and added four solid base layers. Inspection of its recorded motion paths found:

- 1,208 retractions during the four base layers.
- Approximately 119,726 mm of non-extruding base travel.
- Approximately 102.5 minutes of base motion at commanded speeds, excluding acceleration overhead and retract time.
- First-layer deposition alone takes approximately 25.3 minutes.
- Nominal first-layer flow is 0.42 x 0.28 x 12 = 1.4112 mm3/s.
- Commanded filament length is approximately 4.89 mm per 100 mm of deposited path, using 1.75 mm filament and the generator's rectangular bead model.

The scanline planner alternates between separated spans around hollow bases. Each disconnected path retracts, lifts 0.6 mm, travels, lowers and primes. This creates excessive travel and extrusion restarts. It explains the wasted time and gives many opportunities for ooze and poor restarts; it does not by itself prove the cause of every physical defect in the photographs.

The first-layer material demand is low. There is no evidence here that the print failed because the hotend reached its maximum volumetric flow. Large empty centres are intentional in the base geometry; loose lines spanning them are not intended deposition.

The previous validator checked numerical extrusion, schedules, coordinate limits and a simplified toolhead clearance. It did not validate practical path efficiency, pressure recovery, first-layer contact, active bed mesh, physical adhesion or actual nozzle output. A pass was insufficient evidence to release these files with confidence.

## What remains unknown

The photographs do not distinguish nozzle too high, nozzle too low, adhesion loss, partial obstruction, or poor restarts caused by the custom paths. The printer's active mesh, Z offset and live extrusion state were not captured. Whether another conventionally sliced print works on the same setup is the most useful immediate comparison. Do not change Z offset or flow multiplier solely on these photographs.

## What the next useful test must establish

1. Generate extrusion, first layers, travel and retraction with Cura or OrcaSlicer. Start from the successfully used process and startup configuration. Do not hand-generate those paths again.
2. Establish a small clean baseline using the proven settings, ideally on a useful robot feature. A normal first layer must pass before interpreting any speed result. If the user's other sliced print already provides that comparison, avoid duplicating it unnecessarily.
3. Test moderate flow increases, starting around 8, 10, 12, 14 and 16 mm3/s at the existing temperature. Long straight sections must be long enough to approach the target, with actual sliced feed and extrusion checked. Do not start by pursuing the advertised travel speed.
4. Compare a known-good robot hole/tab specimen with the same geometry at higher speed. Require acceptable hole fit, roof quality, layer bonding, surface quality and no shifts, and report the actual time saved.
5. Hold retraction and acceleration fixed while checking the first speed/flow increase. Tune acceleration afterward only if travel and cornering dominate the measured time. Defer minor stringing tuning until extrusion and first layers are reliable.
6. If combining specimens on one bed, use normal layer-by-layer slicing and clearly label controls and variants. Inspect the real slicer preview for travel and retraction counts. Avoid another tall-object-first sequence and custom lowering around completed objects.

No higher production speed has been validated by the failed calibration prints. The successful robot process remains the baseline. No replacement G-code is released by this audit; existing archives remain unchanged for traceability.

General first-layer reference: https://help.prusa3d.com/article/first-layer-issues_1804
OrcaSlicer flow-limit reference: https://github.com/orcaslicer/orcaslicer/wiki/material_volumetric_speed_limitation
