# Face identity audit

Coverage: 40 faces, 80 placed eyes, 30 source eye parts. This report records the implementation before identity fixes.

Generated rest ink / original dimensions. Values below 1 mean the rest eye is smaller than the canonical eye. Severity is a diagnostic threshold, not a naturalness rating.

| Part | Family | Severity | Width | Height | Alignment angle | Affected faces |
|---|---|---|---:|---:|---:|---|
| droop_hook_10 | hook | high | 0.56 | 0.57 | -27.7 | 05 |
| droop_hook_09 | hook | high | 0.61 | 0.60 | -40.5 | 31 |
| droop_hook_08 | hook | high | 0.63 | 0.58 | -25.2 | 05 |
| open_C_46 | hook | high | 0.66 | 0.61 | -22.7 | 33 |
| happy_arc_15 | arc | high | 0.70 | 0.78 | 160.0 | 29 |
| circle_gap_04 | hook | high | 0.70 | 0.59 | -156.1 | 07 |
| e_shape_13 | loop | high | 0.71 | 0.71 | -39.1 | 27 |
| happy_arc_18 | arc | high | 0.72 | 0.77 | 155.8 | 35 |
| happy_arc_17 | arc | high | 0.72 | 0.82 | -167.8 | 06 |
| closed_lid_arc_06 | arc | high | 0.73 | 0.85 | 170.3 | 21, 23 |
| open_C_49 | hook | high | 0.73 | 0.81 | -8.6 | 36 |
| circle_gap_02 | round | high | 0.74 | 0.73 | 31.2 | 09, 11, 20, 32 |
| happy_arc_19 | arc | high | 0.74 | 0.87 | -7.9 | 13 |
| open_C_47 | hook | high | 0.75 | 0.72 | -14.2 | 01 |
| closed_lid_arc_05 | arc | high | 0.77 | 0.88 | 173.7 | 16, 21, 22, 23 |
| open_C_45 | slot | high | 0.79 | 0.94 | 7.2 | 24 |
| e_shape_11 | loop | high | 0.95 | 0.88 | 3.6 | 18, 28, 38 |
| open_C_51 | slot | medium | 0.83 | 0.96 | 175.3 | 24 |
| closed_lid_arc_07 | arc | medium | 0.90 | 0.83 | 168.9 | 26 |
| open_C_43 | round | medium | 0.92 | 0.90 | -4.0 | 07, 36 |
| open_C_50 | round | low | 0.95 | 0.99 | -0.4 | 33 |
| open_C_42 | hook | low | 0.97 | 0.98 | -0.5 | 01 |
| angry_hook_00 | hook | low | 0.99 | 0.97 | 0.0 | 02, 04 |
| open_C_48 | slot | low | 0.99 | 0.93 | -0.7 | 03 |
| circle_gap_03 | round | low | 0.99 | 0.96 | 0.0 | 11, 25, 32, 39 |
| e_shape_12 | loop | low | 0.99 | 0.91 | 0.0 | 18, 27, 28, 34, 38 |
| happy_arc_16 | arc | low | 0.99 | 0.91 | 0.0 | 10, 14 |
| flat_bar_14 | bar | low | 0.99 | 0.94 | 0.0 | 15, 17 |
| chevron_01 | chevron | low | 0.99 | 0.94 | 0.0 | 08, 12, 19, 30 |
| open_C_44 | slot | low | 1.00 | 0.99 | 0.0 | 37, 40 |

## Findings

**high: Canonical identities replaced at rest**

Every eye uses its generated family representative at rest; grouping was broad motion compatibility, not shape equivalence.

Fix: Keep canonical source art for rest and settled; preserve exact slot placement. Use generated cels only within blink, with per-part retargeting.

**high: Arbitrary rectangle rotation shrinks eyes**

Uniform scale uses rotated master rectangle bounds. Rotating a mostly empty rectangle overestimates ink extents and can substantially shrink both dimensions.

Fix: Fit measured ink support or explicit family basis, not rotated crop rectangles. Enforce source width and endpoints in per-part blink retargeting.

**high: Mid-transition hard cut**

rigAt selects previous before half and current after half. Blink only changes lid pose; mouth, tears, eye slots and sizes jump at the midpoint.

Fix: Interpolate shared layer placement and use opacity transitions for incompatible topology. Keep speech timeline independent of expression changes.

**medium: Preview and production speaking geometry disagree**

Preview clamps mouth width and omits rotation/mirror; production uses raw width, rotation/mirror and face fitting. Face 37 uses different mouth family. Faces 12 and 35 have no mouth: preview fabricates one, production cannot speak visually.

Fix: One shared renderer and explicit per-face speech policy.

## Per-face review

| Face | Left eye | Right eye | Severity | Mouth issue |
|---|---|---|---|---|
| 01_angry_01_manual | open_C_47 | open_C_42 | high | Preview ignores original mouth rotation -0.88 degrees |
| 02_angry_02_manual | angry_hook_00 | angry_hook_00 | low | No extra transform discrepancy detected |
| 03_angry_07_manual | open_C_48 | open_C_48 | low | No extra transform discrepancy detected |
| 04_angry_08_manual | angry_hook_00 | angry_hook_00 | low | No extra transform discrepancy detected |
| 05_annoyed_01_manual | droop_hook_08 | droop_hook_10 | high | No extra transform discrepancy detected |
| 06_annoyed_02_manual | happy_arc_17 | happy_arc_17 | high | Preview ignores original mouth rotation 2.72 degrees |
| 07_annoyed_03_manual | circle_gap_04 | open_C_43 | high | No extra transform discrepancy detected |
| 08_annoyed_04_manual | chevron_01 | chevron_01 | low | Preview ignores original mouth rotation 0.53 degrees |
| 09_happy_03_manual | circle_gap_02 | circle_gap_02 | high | No extra transform discrepancy detected |
| 10_happy_04_manual | happy_arc_16 | happy_arc_16 | low | No extra transform discrepancy detected |
| 11_happy_05_manual | circle_gap_02 | circle_gap_03 | high | No extra transform discrepancy detected |
| 12_happy_09_manual | chevron_01 | chevron_01 | low | No canonical mouth: production suppresses speech mouth, preview invents fallback mouth |
| 13_happy_14_manual | happy_arc_19 | happy_arc_19 | high | Preview ignores original mouth rotation -5.4 degrees |
| 14_happy_16_manual | happy_arc_16 | happy_arc_16 | low | Preview ignores original mouth rotation 1.17 degrees |
| 15_misc_15_manual | flat_bar_14 | flat_bar_14 | low | Preview ignores original mouth rotation -7.17 degrees |
| 16_misc_16_manual | closed_lid_arc_05 | closed_lid_arc_05 | high | Preview ignores original mouth rotation -6.01 degrees |
| 17_misc_2_01_manual | flat_bar_14 | flat_bar_14 | low | No extra transform discrepancy detected |
| 18_misc_2_02_manual | e_shape_12 | e_shape_11 | high | Preview ignores original mouth rotation 6.36 degrees |
| 19_misc_2_03_manual | chevron_01 | chevron_01 | low | Preview ignores original mouth rotation -0.79 degrees |
| 20_neutral_06_manual | circle_gap_02 | circle_gap_02 | high | No extra transform discrepancy detected |
| 21_neutral_11_manual | closed_lid_arc_06 | closed_lid_arc_05 | high | Preview ignores original mouth rotation -3.26 degrees |
| 22_neutral_12_manual | closed_lid_arc_05 | closed_lid_arc_05 | high | Preview ignores original mouth rotation -0.77 degrees |
| 23_neutral_13_manual | closed_lid_arc_06 | closed_lid_arc_05 | high | Preview ignores original mouth rotation -5.83 degrees |
| 24_neutral_2_01_manual | open_C_51 | open_C_45 | high | Preview ignores original mouth rotation -1.68 degrees |
| 25_neutral_2_03_manual | circle_gap_03 | circle_gap_03 | low | No extra transform discrepancy detected |
| 26_sad_01_manual | closed_lid_arc_07 | closed_lid_arc_07 | medium | No extra transform discrepancy detected |
| 27_sad_02_manual | e_shape_13 | e_shape_12 | high | Preview ignores original mouth rotation -9.84 degrees |
| 28_sad_03_manual | e_shape_11 | e_shape_12 | high | No extra transform discrepancy detected |
| 29_sad_04_manual | happy_arc_15 | happy_arc_15 | high | No extra transform discrepancy detected |
| 30_sad_05_manual | chevron_01 | chevron_01 | low | No extra transform discrepancy detected |
| 31_sad_06_manual | droop_hook_09 | droop_hook_09 | high | Preview ignores original mouth rotation 2.11 degrees |
| 32_sad_07_manual | circle_gap_03 | circle_gap_02 | high | Preview ignores original mouth rotation -1.54 degrees |
| 33_sad_08_manual | open_C_46 | open_C_50 | high | Preview ignores original mouth rotation -1.6 degrees |
| 34_sad_09_manual | e_shape_12 | e_shape_12 | low | Preview ignores original mouth rotation -2.49 degrees |
| 35_sad_10_manual | happy_arc_18 | happy_arc_18 | high | No canonical mouth: production suppresses speech mouth, preview invents fallback mouth |
| 36_misc_03_manual | open_C_49 | open_C_43 | high | Preview ignores original mouth rotation -0.59 degrees |
| 37_misc_06_manual | open_C_44 | open_C_44 | low | Preview selects smile speech set; production selects neutral speech set |
| 38_misc_2_06_manual | e_shape_12 | e_shape_11 | high | Preview ignores original mouth rotation -0.62 degrees |
| 39_neutral_02_manual | circle_gap_03 | circle_gap_03 | low | No extra transform discrepancy detected |
| 40_neutral_03_manual | open_C_44 | open_C_44 | low | No extra transform discrepancy detected |
