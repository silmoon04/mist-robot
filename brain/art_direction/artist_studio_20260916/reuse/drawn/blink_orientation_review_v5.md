# Blink orientation review

No production edits. Open canonical faces remain the reference. Angles are clockwise degrees in screen coordinates; positive slopes downward to the right.

The current renderer carries glyph-fitting rotation into the closed lid. This is incorrect for many round eyes and some drooping hooks. A uniform zero-angle rule would also discard intentional expression tilt.

| Face | Side | Source part | Current closed angle | Proposed target | Strategy | Severity |
|---|---|---|---:|---:|---|---|
| 01_angry_01_manual | eye_L | open_C_47 | -14.2 | 7.0 | upper-lid-led tilt | high |
| 01_angry_01_manual | eye_R | open_C_42 | 0.5 | -16.7 | upper-lid-led tilt | medium |
| 02_angry_02_manual | eye_L | angry_hook_00 | -3.0 | 17.6 | upper-lid-led tilt | high |
| 02_angry_02_manual | eye_R | angry_hook_00 | -0.2 | -18.0 | upper-lid-led tilt | medium |
| 03_angry_07_manual | eye_L | open_C_48 | 1.1 | 1.5 | slot-axis closure | low |
| 03_angry_07_manual | eye_R | open_C_48 | 0.7 | 0.3 | slot-axis closure | low |
| 04_angry_08_manual | eye_L | angry_hook_00 | -1.0 | 18.0 | upper-lid-led tilt | high |
| 04_angry_08_manual | eye_R | angry_hook_00 | 0.9 | -18.0 | upper-lid-led tilt | high |
| 05_annoyed_01_manual | eye_L | droop_hook_08 | -25.2 | 3.0 | upper-lid-led tilt | high |
| 05_annoyed_01_manual | eye_R | droop_hook_10 | 27.7 | -2.4 | upper-lid-led tilt | high |
| 06_annoyed_02_manual | eye_L | happy_arc_17 | 9.8 | 5.1 | source-arc squeeze | low |
| 06_annoyed_02_manual | eye_R | happy_arc_17 | -12.2 | -7.5 | source-arc squeeze | low |
| 07_annoyed_03_manual | eye_L | circle_gap_04 | 24.0 | 3.9 | upper-lid-led tilt | high |
| 07_annoyed_03_manual | eye_R | open_C_43 | 4.0 | -3.7 | screen-level round-eye blink | low |
| 08_annoyed_04_manual | eye_L | chevron_01 | 0.0 | 0.2 | centered chevron squeeze | low |
| 08_annoyed_04_manual | eye_R | chevron_01 | 1.4 | 0.2 | centered chevron squeeze | low |
| 09_happy_03_manual | eye_L | circle_gap_02 | 33.4 | 0.0 | screen-level round-eye blink | high |
| 09_happy_03_manual | eye_R | circle_gap_02 | -32.1 | 0.0 | screen-level round-eye blink | high |
| 10_happy_04_manual | eye_L | happy_arc_16 | 0.1 | 4.7 | source-arc squeeze | low |
| 10_happy_04_manual | eye_R | happy_arc_16 | 6.2 | 1.5 | source-arc squeeze | low |
| 11_happy_05_manual | eye_L | circle_gap_02 | 0.9 | 0.0 | screen-level round-eye blink | low |
| 11_happy_05_manual | eye_R | circle_gap_03 | 0.2 | 0.0 | screen-level round-eye blink | low |
| 12_happy_09_manual | eye_L | chevron_01 | 0.8 | 0.0 | centered chevron squeeze | low |
| 12_happy_09_manual | eye_R | chevron_01 | -0.7 | 0.0 | centered chevron squeeze | low |
| 13_happy_14_manual | eye_L | happy_arc_19 | -5.1 | -0.4 | source-arc squeeze | low |
| 13_happy_14_manual | eye_R | happy_arc_19 | 8.3 | 3.7 | source-arc squeeze | low |
| 14_happy_16_manual | eye_L | happy_arc_16 | -5.1 | -0.4 | source-arc squeeze | low |
| 14_happy_16_manual | eye_R | happy_arc_16 | 7.6 | 2.9 | source-arc squeeze | low |
| 15_misc_15_manual | eye_L | flat_bar_14 | -0.5 | -0.5 | bar-axis squeeze | low |
| 15_misc_15_manual | eye_R | flat_bar_14 | -0.8 | -0.8 | bar-axis squeeze | low |
| 16_misc_16_manual | eye_L | closed_lid_arc_05 | -6.6 | -1.9 | source-arc squeeze | low |
| 16_misc_16_manual | eye_R | closed_lid_arc_05 | 5.1 | 0.4 | source-arc squeeze | low |
| 17_misc_2_01_manual | eye_L | flat_bar_14 | -0.1 | -0.1 | bar-axis squeeze | low |
| 17_misc_2_01_manual | eye_R | flat_bar_14 | -0.3 | -0.3 | bar-axis squeeze | low |
| 18_misc_2_02_manual | eye_L | e_shape_12 | 0.0 | 2.4 | gentle tired-lid tilt | low |
| 18_misc_2_02_manual | eye_R | e_shape_11 | -3.6 | -0.9 | gentle tired-lid tilt | low |
| 19_misc_2_03_manual | eye_L | chevron_01 | -3.4 | -0.4 | centered chevron squeeze | low |
| 19_misc_2_03_manual | eye_R | chevron_01 | 0.5 | -0.4 | centered chevron squeeze | low |
| 20_neutral_06_manual | eye_L | circle_gap_02 | 24.2 | 0.0 | screen-level round-eye blink | high |
| 20_neutral_06_manual | eye_R | circle_gap_02 | -23.9 | 0.0 | screen-level round-eye blink | high |
| 21_neutral_11_manual | eye_L | closed_lid_arc_06 | -9.7 | -5.0 | source-arc squeeze | low |
| 21_neutral_11_manual | eye_R | closed_lid_arc_05 | 5.9 | 1.3 | source-arc squeeze | low |
| 22_neutral_12_manual | eye_L | closed_lid_arc_05 | -8.8 | -4.2 | source-arc squeeze | low |
| 22_neutral_12_manual | eye_R | closed_lid_arc_05 | 4.8 | 0.1 | source-arc squeeze | low |
| 23_neutral_13_manual | eye_L | closed_lid_arc_06 | -4.3 | 0.3 | source-arc squeeze | low |
| 23_neutral_13_manual | eye_R | closed_lid_arc_05 | 4.1 | -0.5 | source-arc squeeze | low |
| 24_neutral_2_01_manual | eye_L | open_C_51 | -4.6 | -1.4 | slot-axis closure | low |
| 24_neutral_2_01_manual | eye_R | open_C_45 | -7.3 | -1.9 | slot-axis closure | low |
| 25_neutral_2_03_manual | eye_L | circle_gap_03 | -1.1 | 0.0 | screen-level round-eye blink | low |
| 25_neutral_2_03_manual | eye_R | circle_gap_03 | 1.9 | 0.0 | screen-level round-eye blink | low |
| 26_sad_01_manual | eye_L | closed_lid_arc_07 | -11.0 | -15.7 | source-arc squeeze | low |
| 26_sad_01_manual | eye_R | closed_lid_arc_07 | 13.7 | 18.4 | source-arc squeeze | low |
| 27_sad_02_manual | eye_L | e_shape_13 | -39.1 | -10.0 | gentle tired-lid tilt | high |
| 27_sad_02_manual | eye_R | e_shape_12 | 18.7 | 8.8 | gentle tired-lid tilt | medium |
| 28_sad_03_manual | eye_L | e_shape_11 | -16.4 | -10.0 | gentle tired-lid tilt | low |
| 28_sad_03_manual | eye_R | e_shape_12 | 19.0 | 8.9 | gentle tired-lid tilt | medium |
| 29_sad_04_manual | eye_L | happy_arc_15 | -20.0 | -15.4 | source-arc squeeze | low |
| 29_sad_04_manual | eye_R | happy_arc_15 | 20.4 | 15.8 | source-arc squeeze | low |
| 30_sad_05_manual | eye_L | chevron_01 | -1.3 | -0.1 | centered chevron squeeze | low |
| 30_sad_05_manual | eye_R | chevron_01 | 0.3 | -0.1 | centered chevron squeeze | low |
| 31_sad_06_manual | eye_L | droop_hook_09 | -40.5 | -8.0 | upper-lid-led tilt | high |
| 31_sad_06_manual | eye_R | droop_hook_09 | 37.8 | 6.3 | upper-lid-led tilt | high |
| 32_sad_07_manual | eye_L | circle_gap_03 | -20.6 | -0.3 | screen-level round-eye blink | high |
| 32_sad_07_manual | eye_R | circle_gap_02 | 8.8 | -0.3 | screen-level round-eye blink | medium |
| 33_sad_08_manual | eye_L | open_C_46 | -22.7 | -8.0 | upper-lid-led tilt | medium |
| 33_sad_08_manual | eye_R | open_C_50 | 0.4 | -2.6 | screen-level round-eye blink | low |
| 34_sad_09_manual | eye_L | e_shape_12 | -18.8 | -8.9 | gentle tired-lid tilt | medium |
| 34_sad_09_manual | eye_R | e_shape_12 | 18.6 | 8.7 | gentle tired-lid tilt | medium |
| 35_sad_10_manual | eye_L | happy_arc_18 | -24.2 | -19.5 | source-arc squeeze | low |
| 35_sad_10_manual | eye_R | happy_arc_18 | 24.2 | 19.5 | source-arc squeeze | low |
| 36_misc_03_manual | eye_L | open_C_49 | -8.6 | 0.6 | upper-lid-led tilt | medium |
| 36_misc_03_manual | eye_R | open_C_43 | 2.4 | -4.0 | screen-level round-eye blink | low |
| 37_misc_06_manual | eye_L | open_C_44 | 0.0 | 1.8 | slot-axis closure | low |
| 37_misc_06_manual | eye_R | open_C_44 | 1.4 | -0.3 | slot-axis closure | low |
| 38_misc_2_06_manual | eye_L | e_shape_12 | -2.2 | 1.1 | gentle tired-lid tilt | low |
| 38_misc_2_06_manual | eye_R | e_shape_11 | 0.9 | 1.8 | gentle tired-lid tilt | low |
| 39_neutral_02_manual | eye_L | circle_gap_03 | -2.0 | -0.0 | screen-level round-eye blink | low |
| 39_neutral_02_manual | eye_R | circle_gap_03 | 1.5 | -0.0 | screen-level round-eye blink | low |
| 40_neutral_03_manual | eye_L | open_C_44 | -2.1 | -0.4 | slot-axis closure | low |
| 40_neutral_03_manual | eye_R | open_C_44 | 1.2 | -0.4 | slot-axis closure | low |

Recommended targets are starting points for visual review, not precision measurements of an ideal blink.

- Never apply a single zero-angle rule to all 80 eyes: angry hooks, tired crossbars, source closed arcs and bars have intentional attitudes.
- Round eyes need independent screen-level blink coordinates; slot.rot and reference alignment encode circle-gap placement, not head tilt.
- For source closed arcs, preserve concavity and endpoints in a squeeze. Several aligned arcs rotate roughly 160 to 180 degrees, which reverses generic lid curvature.
- For hook eyes, derive a bounded target from the source upper lid, not the generic hook alignment.
- Make closure angle approach its target during closing and undo it during reopening; prevent a sudden orientation jump when entering or leaving the closed frame.
- Expression-transition closed bridges must use the same per-eye closure orientation as ordinary blinks.
