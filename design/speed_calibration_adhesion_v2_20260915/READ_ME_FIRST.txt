# Calibration V2: slower start and wider bases

Print EN4Pro_Calibration_V2_Slow_Start.gcode directly. Do not re-slice it.
Neptune 4 Pro, stock 0.4 mm nozzle, same PLA, 210 C nozzle and 60 C bed.

The earlier claimed 55-minute replacement was not generated. This file is the checked replacement.
Allow about 3.5 hours plus heating and homing, using approximately 37 g PLA.
The calculated motion estimates are 174 to 193 minutes; these are not measured printer times.

Each base extends 1 mm beyond its previous outline and now has four solid layers, 1.12 mm total.
These attached foundations stay on the calibration pieces. No supports are needed.

Layer | Extrusion speed | XY travel | Acceleration | Fan
1 | 12 mm/s | 40 mm/s | 250 mm/s2 | off
2 | 20 mm/s | 50 mm/s | 400 mm/s2 | off
3 | 25 mm/s | 60 mm/s | 500 mm/s2 | 25 percent
4 | 30 mm/s | 70 mm/s | 600 mm/s2 | 50 percent

Raised labels print at 20 mm/s and 500 mm/s2 with 60 mm/s travel.
The original six test bands then run at their original settings. This includes up to
10000 mm/s2 in the final acceleration band and 28 mm3/s in the final flow band.
Those later levels deliberately test the limits; the gentler base cannot guarantee they will succeed.

Wash and dry the build plate as planned. Check that the first-layer lines join and stay attached.
If they curl, separate or follow the nozzle, stop instead of letting the test continue.
Slower motion cannot correct an unsuitable Z offset, dirty surface or a loose part.
Stop if a piece detaches, the nozzle catches it or the extruder repeatedly skips.

Band heights have changed because the base is thicker. Use the included Band_Reference.png.
The front flow tower finishes first; the printer then lowers behind it to build the rear pieces.
That lowering is intentional, with the stock toolhead clearance checked.

The software checks verify commands and geometry, not physical adhesion or printer condition.
No file has been copied to USB and no printer commands have been sent.

# One-run Neptune 4 Pro calibration

**Print the supplied .gcode directly. Do not re-slice it and do not apply a Cura or Orca process profile to it.** The speed, acceleration, flow and retraction changes are already embedded. Open it in a G-code viewer if you want to inspect the paths.

Target: your ELEGOO Neptune 4 Pro, stock 0.4 mm nozzle, same 1.75 mm PLA that printed the robot parts, 210 C nozzle and 60 C bed. Approximately 37 g PLA, 12.4 m filament. Motion estimates are 174 to 193 minutes before heating and homing. Allow about 3.5 hours plus startup. These are calculated estimates, not measured printer times.

It runs once, without pauses, filament changes or manual setting changes. It is a limit-finding test, so supervise the first layer and stop if the extruder repeatedly skips/clicks, the nozzle drags, the printer loses steps or a specimen detaches. A calibration file cannot guarantee unattended operation.

## What is on the plate

| Letter on base | Purpose | What changes | What stays fixed |
| --- | --- | --- | --- |
| F | Flow tower with 180 mm straight sides | Commanded flow from 8 to 28 mm3/s | 0.28 mm layers, 0.42 mm line width, 3000 mm/s2 acceleration |
| A | Acceleration and ringing, with corners/notches in both X and Y | Acceleration from 1000 to 10000 mm/s2 | 120 mm/s, 0.14 mm layers, approximately 7.06 mm3/s |
| R | Robot-like bracket wall with repeated 3.4 mm holes and 45-degree upper roofs | Feature speed from 40 to 180 mm/s | 0.28 mm layers, 2000 mm/s2, fixed nominal geometry |
| C | Companion bracket control | Nothing | Same bracket geometry at 40 mm/s in all bands |
| S | Stringing pair | Retraction amount | 40 mm/s walls, 180 mm/s transfer, 35 mm/s retract/unretract |
| T | Stringing control pair | Nothing | 0.5 mm retraction in every band |

The thin layers on A are deliberate: testing high acceleration at 0.28 mm and 120 mm/s would also demand 14.1 mm3/s, well above the previously conservative flow setting. A uses half that flow so the motion test does not become another hotend-flow test.

F is a single-wall screening specimen. R and C use three perimeter passes around their contours, rather than the full five-wall production process. These are diagnostic pieces with similar hole and wall features, not structural replicas or proof of final part strength.

## Print order and reading the bands

The bases and raised letters print first. The front flow tower F then prints continuously from low flow to high flow. This gives each flow level a sustained run instead of only a brief burst between other objects. A thin two-layer low-flow recovery rim finishes F. That rim is not a seventh band.

The printer then prints the rear specimens together in layers. It deliberately returns to a lower Z behind the completed front tower. That is expected. The layout and travel path were checked with a conservative 50 mm XY head/fan footprint; the minimum calculated gap from that footprint to the front tower is about 12.9 mm. This clearance assumes the stock toolhead, with no unusually large fan duct or attached accessory. Do not rearrange the G-code coordinates.

Each specimen has six bands separated by small horizontal ribs. Band 1 is at the bottom immediately above the base; band 6 is at the top. The printed letters identify the specimens. Use Band_Reference.png to identify the settings; the bands do not contain raised numeric text. The preview colours are illustrative only: your print uses one filament colour.

| Band, bottom to top | Height above bed | F flow | F requested speed | A acceleration | R requested speed | S retract |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.12 to 6.72 mm | 8 mm3/s | 68.0 mm/s | 1000 mm/s2 | 40 mm/s | 0.20 mm |
| 2 | 6.72 to 12.32 mm | 12 mm3/s | 102.0 mm/s | 2000 mm/s2 | 65 mm/s | 0.35 mm |
| 3 | 12.32 to 17.92 mm | 16 mm3/s | 136.1 mm/s | 3000 mm/s2 | 90 mm/s | 0.50 mm |
| 4 | 17.92 to 23.52 mm | 20 mm3/s | 170.1 mm/s | 5000 mm/s2 | 120 mm/s | 0.65 mm |
| 5 | 23.52 to 29.12 mm | 24 mm3/s | 204.1 mm/s | 8000 mm/s2 | 150 mm/s | 0.80 mm |
| 6 | 29.12 to 34.72 mm | 28 mm3/s | 238.1 mm/s | 10000 mm/s2 | 180 mm/s | 0.50 mm |

The first and last layer of a band have a small marker rib. Score the middle of the band, not the seam, rib or first few transition lines. C is always 40 mm/s and T is always 0.5 mm retract. S repeats 0.5 mm in bands 3 and 6 to expose drift over the print.

## How to inspect it

F: inspect both long faces in raking light. Look for gaps, intermittent thin lines, rough or grainy extrusion, loss of wall consistency and layers that separate unusually easily. A gloss change alone is not a definite failure. Compare mid-band wall thickness to the low-flow band with calipers using very light pressure; the thin wall flexes. The short recovery rim should look normal after the high-flow band. If delivery does not recover, stop and treat later results as suspect.

A: look along both long and short walls after each corner or notch. Score repeated ripples, corner bulges, rounded-off detail and any layer shift. Ignore a solitary vertical seam blemish. If you see shifts, the failing acceleration is unsuitable even if the rest of the band looks smooth. A tall thin shell can vibrate more than a thick robot bracket, so this is a screening result, not an exact production acceleration limit.

R against C: compare holes at the same height. Try the same M3 screw or gauge gently in both. Compare roof sag, hole width, corner sharpness, wall regularity and seam blobs. A hole that was marginal in C is not evidence that speed caused it. If R worsens while C stays clean, feature speed is a plausible cause; if both worsen, investigate a shared extrusion, temperature or contamination issue. Keep the printed hole specimens for the next profile decision.

S against T: photograph both gaps before removing any strings. Judge string quantity/thickness and missing material just after the travel seam. Pick the smallest retraction that controls strings without underextrusion or holes at restart. A larger retraction is not automatically better. If S bands 3 and 6 differ a lot despite both being 0.5 mm, or T also drifts, do not attribute everything to retraction. Moisture, heat, height and pressure history can contribute.

Record one score per band in RESULTS.csv. Use PASS, BORDERLINE or FAIL, with a short reason. Photos of F in side lighting, A on both axes, R/C together and both stringing gaps are enough for an initial review.

## Turning the result into a faster robot profile

Use the last consistently clean flow band before the first failure, then begin production at about 80 percent of that value. If all bands pass, the test establishes only that the ceiling is at least 28 mm3/s under these conditions; it has not measured an absolute maximum. Do not extrapolate to a different filament, nozzle or temperature.

At the robot process of 0.42 mm line width and 0.28 mm layer height, the nominal relationship is Q = width x layer height x speed. Thus 16 mm3/s corresponds to about 136 mm/s; 20 mm3/s to about 170 mm/s. A nominal 500 mm/s would require 58.8 mm3/s at that bead size, which the printer marketing speed does not establish.

Choose outer-wall speed from R versus C, capped by the chosen flow limit. Faster infill and long inner walls may use more of the clean flow capacity. Keep the established slow bridge/overhang settings until those features also remain acceptable. Do not fix high-flow starvation by increasing the flow multiplier; that increases the hotend demand further.

Choose acceleration below the first visibly poor A band, then verify it on one real printed leg part at the chosen higher speeds. A is tested at 120 mm/s, whereas R is tested at 2000 mm/s2, so this one print does not test every combination of high speed and high acceleration. A higher-throughput profile still needs that final combined check before producing several load-bearing parts.

A useful starting policy is one acceleration band below the first clearly poor result, and about 80 percent of the last clean flow value. These are initial engineering margins, not certified material or machine limits. The physical printer result controls the choice.

## G-code implementation and checks

The file explicitly sets 100 percent speed and flow overrides, 210/60 C, fan off on the first two base layers and full fan for the test sections. It uses absolute XYZ, relative E, explicit retract/unretract moves, and M204 to change acceleration per section. Only the stringing pairs use deliberate no-hop transfers between their two posts; other transfers are retracted and lifted.

The runtime velocity cap is set to 300 mm/s; the fastest commanded extrusion is about 238 mm/s. Acceleration reaches 10000 mm/s2 in the final A band. At completion the file sets acceleration to2500 mm/s2 and switches heaters/fan off. These are documented runtime settings, not restoration of unknown previous values. Your next slicing profile should set its own speeds and acceleration as usual. No firmware configuration is saved.

Pressure advance, input shaping, corner velocity, cruise-ratio settings, motor current and thermal protection are left unchanged. Their existing values still affect the observed result. The independent length/acceleration check shows long enough segments to reach the requested speeds in a simple trapezoidal model; it is not an exact simulation of your firmware planner.

Startup follows the locally installed Cura Neptune 4/4 Pro pattern: warm the bed, home, raise the nozzle, heat to print temperature, then purge. The purge is calculated from bead volume and kept inside the bed. No guessed named bed-mesh profile is loaded and no Z offset is changed. It relies on your existing successful homing/mesh setup. The saved printer address was found in Orca settings, but its read-only status request timed out; live firmware settings were not verified.

Static validation passed: 29730 spatial moves and all 36 zone/band combinations, including the revised base limits. G-code SHA-256: 98d3446f6e979ba0eabdf96519e39dac55ddfbc2d8c4a58fb9f75ce3e479c6d2. This is code validation, not a completed physical print.

## Sources

The printer specification lists up to500 mm/s and20000 mm/s2, but does not establish those rates at the robot bead size: https://www.elegoo.com/products/elegoo-neptune-4-pro-fdm-3d-printer

Klipper documents M204 acceleration, M83 relative extrusion and SET_VELOCITY_LIMIT: https://www.klipper3d.org/G-Codes.html

The current Klipper implementation confirms that M204 changes the runtime acceleration; it should not be assumed to preserve an independent lower cap: https://github.com/Klipper3d/klipper/blob/master/klippy/toolhead.py
