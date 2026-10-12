# Blink orientation diagnostic

Renderer: 70d73a3b12f05e91e4f0c9a403012ba71d5ee91ddbc0fb9bb5d78aad7d924d0a

Measured 2 eyes. 2 are flagged: 2 have at least 30 degrees of extra closing-plane rotation; 0 reverse the upper-lid travel direction. No measured closed axes exceed 60 degrees.

The concrete browser-matched failure is face 09: circle_gap_02 contributes a 31.182-degree open-shape fit to an almost horizontal closed drawing. The face slot rotations are only +2.25 and -0.94 degrees.

| Face | Eye | Source part | Fit rotation | Slot rotation | Closed axis | Slot + source only | Inverted travel |
|---|---|---|---:|---:|---:|---:|---|
| 09_happy_03_manual | eye_L | circle_gap_02 | 31.182 | 2.25 | 33.362 | 2.18 | false |
| 09_happy_03_manual | eye_R | circle_gap_02 | 31.182 | -0.94 | -32.052 | -0.87 | false |

The slot + source column is a counterfactual orientation calculation, not a proposed production interpolation. Applying it only to the final frame could still twist the eye; the closing sequence needs its own stable eyelid registration.

1. Open-glyph alignment rotation is reused as the eyelid closing plane. Keeping the source closed-lid angle and face slot rotation, but removing open-glyph fit rotation, removes the extra 31-degree tilt on circle_gap_02. Do not rotate the visible open eye to reach this frame; closing cels need separate registration.
2. Mirroring alone creates the bad lid direction. If this were the root cause, an unmirrored instance would be correctly oriented. Face09 eye_L is unmirrored yet tilts 33.36 degrees, so mirroring is an amplifier, not the initiating fault.
3. The generated closed artwork itself is diagonal. Its measured ink PCA should have the same large angle before any fit transform. Round source is near-horizontal, so this cannot explain face09; hook has a real gentle tilt that should remain.
4. Face placement intentionally tilted the closing plane. The final lid angle should agree with slot rotation plus source tilt. Face09 slots are approximately 2 and -1 degrees, excluding the observed mirrored 33-degree slopes.

- The slot plane is a diagnostic baseline; some original closed arcs can intentionally curve the opposite way. Inverted travel flags are review candidates, not all proven defects.
- No measured closed axes exceed 60 degrees; this run reproduces diagonal and inverted closure, not a fully vertical closed lid.
- The directional test uses actual renderer transforms and actual source ink orientation. Source-contour scale fallback does not affect the measured angle.
