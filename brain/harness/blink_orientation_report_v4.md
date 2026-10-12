# Blink orientation diagnostic

Renderer: 70d73a3b12f05e91e4f0c9a403012ba71d5ee91ddbc0fb9bb5d78aad7d924d0a

Measured 80 eyes. 27 are flagged: 9 have at least 30 degrees of extra closing-plane rotation; 18 reverse the upper-lid travel direction. No measured closed axes exceed 60 degrees.

The concrete browser-matched failure is face 09: circle_gap_02 contributes a 31.182-degree open-shape fit to an almost horizontal closed drawing. The face slot rotations are only +2.25 and -0.94 degrees.

| Face | Eye | Source part | Fit rotation | Slot rotation | Closed axis | Slot + source only | Inverted travel |
|---|---|---|---:|---:|---:|---:|---|
| 06_annoyed_02_manual | eye_L | happy_arc_17 | -167.832 | -2.38 | 10.386 | -1.782 | true |
| 06_annoyed_02_manual | eye_R | happy_arc_17 | -167.832 | -0.02 | -12.786 | -0.618 | true |
| 07_annoyed_03_manual | eye_L | circle_gap_04 | -156.063 | 0.07 | 13.712 | -10.225 | true |
| 09_happy_03_manual | eye_L | circle_gap_02 | 31.182 | 2.25 | 33.362 | 2.18 | false |
| 09_happy_03_manual | eye_R | circle_gap_02 | 31.182 | -0.94 | -32.052 | -0.87 | false |
| 11_happy_05_manual | eye_L | circle_gap_02 | 31.182 | -30.3 | 0.812 | -30.37 | false |
| 16_misc_16_manual | eye_L | closed_lid_arc_05 | 173.67 | -0.23 | -7.158 | -0.828 | true |
| 16_misc_16_manual | eye_R | closed_lid_arc_05 | 173.67 | -1.27 | 5.658 | -0.672 | true |
| 20_neutral_06_manual | eye_L | circle_gap_02 | 31.182 | -6.98 | 24.132 | -7.05 | false |
| 20_neutral_06_manual | eye_R | circle_gap_02 | 31.182 | 7.3 | -23.812 | 7.37 | false |
| 21_neutral_11_manual | eye_L | closed_lid_arc_06 | 170.335 | 0 | -10.263 | -0.598 | true |
| 21_neutral_11_manual | eye_R | closed_lid_arc_05 | 173.67 | -0.41 | 6.518 | 0.188 | true |
| 22_neutral_12_manual | eye_L | closed_lid_arc_05 | 173.67 | -2.48 | -9.408 | -3.078 | true |
| 22_neutral_12_manual | eye_R | closed_lid_arc_05 | 173.67 | -1.54 | 5.388 | -0.942 | true |
| 23_neutral_13_manual | eye_L | closed_lid_arc_06 | 170.335 | 5.32 | -4.943 | 4.722 | true |
| 23_neutral_13_manual | eye_R | closed_lid_arc_05 | 173.67 | -2.22 | 4.708 | -1.622 | true |
| 24_neutral_2_01_manual | eye_L | open_C_51 | 175.328 | 0.1 | -5.052 | -0.379 | true |
| 26_sad_01_manual | eye_L | closed_lid_arc_07 | 168.928 | 0.04 | -10.434 | 0.638 | true |
| 26_sad_01_manual | eye_R | closed_lid_arc_07 | 168.928 | 2.65 | 13.124 | 2.052 | true |
| 27_sad_02_manual | eye_L | e_shape_13 | -39.112 | 0 | -39.303 | -0.191 | false |
| 29_sad_04_manual | eye_L | happy_arc_15 | 159.964 | 0.01 | -20.625 | -0.588 | true |
| 29_sad_04_manual | eye_R | happy_arc_15 | 159.964 | 0.39 | 21.025 | 0.988 | true |
| 31_sad_06_manual | eye_L | droop_hook_09 | -40.527 | 0 | -30.231 | 10.295 | false |
| 31_sad_06_manual | eye_R | droop_hook_09 | -40.527 | -2.68 | 27.551 | -12.975 | false |
| 32_sad_07_manual | eye_R | circle_gap_02 | 31.182 | 40 | 8.888 | 40.07 | false |
| 35_sad_10_manual | eye_L | happy_arc_18 | 155.821 | -0.02 | -24.798 | -0.618 | true |
| 35_sad_10_manual | eye_R | happy_arc_18 | 155.821 | 0.02 | 24.798 | 0.618 | true |

The slot + source column is a counterfactual orientation calculation, not a proposed production interpolation. Applying it only to the final frame could still twist the eye; the closing sequence needs its own stable eyelid registration.

1. Open-glyph alignment rotation is reused as the eyelid closing plane. Keeping the source closed-lid angle and face slot rotation, but removing open-glyph fit rotation, removes the extra 31-degree tilt on circle_gap_02. Do not rotate the visible open eye to reach this frame; closing cels need separate registration.
2. Mirroring alone creates the bad lid direction. If this were the root cause, an unmirrored instance would be correctly oriented. Face09 eye_L is unmirrored yet tilts 33.36 degrees, so mirroring is an amplifier, not the initiating fault.
3. The generated closed artwork itself is diagonal. Its measured ink PCA should have the same large angle before any fit transform. Round source is near-horizontal, so this cannot explain face09; hook has a real gentle tilt that should remain.
4. Face placement intentionally tilted the closing plane. The final lid angle should agree with slot rotation plus source tilt. Face09 slots are approximately 2 and -1 degrees, excluding the observed mirrored 33-degree slopes.

- The slot plane is a diagnostic baseline; some original closed arcs can intentionally curve the opposite way. Inverted travel flags are review candidates, not all proven defects.
- No measured closed axes exceed 60 degrees; this run reproduces diagonal and inverted closure, not a fully vertical closed lid.
- The directional test uses actual renderer transforms and actual source ink orientation. Source-contour scale fallback does not affect the measured angle.
