# First complete review of the 450-frame repaired face export

This is the baseline visual review before the subsequent mouth-transition correction. The exact input hashes are in `snapshot.json`; the nine contact sheets preserve those pixels even if the source files are regenerated later.

Every exported frame was visually reviewed: 200 expression-transition samples, 160 blink samples, 40 settled expressions, and 50 neutral-face speech/release samples. The review split at frame 200: one reviewer checked 000-199 and 400-449, while an independent reviewer checked 200-399. Both found the same transition brightness issue.

All 450 frames pass static vector bounds, and no measured cyan mark reaches a raster edge. The minimum raster padding is 15 pixels in the 200 x 128 export. No clipped tear, solid-cyan failure, new fitted-source join spur, stepped mouth, or settled expression identity loss was visible. This pass does not certify all expression-pair transitions or speech on all 40 faces; the sample contains the ordered expression sequence and speech on neutral face 39.

## Issues found

1. **Speech entry and release briefly show two mouths.** Frame 401 contains the old neutral line above the incoming speech-rest line. Frame 447 contains the outgoing smile bowl behind the incoming neutral line. The latter is plainly visible. `baseline_speech_boundary_closeups.png` shows both with their immediate neighbors.
2. **Expression transitions have a conspicuous dark midpoint.** Transition phase 2 dims the eyes and mouths. At frame 012, for example, eye opacity is about 0.232 and each outgoing/incoming mouth opacity is about 0.052. Several midpoints retain faint overlapping old/new mouths. This prevents bright geometric distortion but produces a visible dark beat and double contours in still frames. It appeared throughout the 40-expression sequence.
3. **Similar eye forms have inconsistent blink eligibility.** Face 27's loop eyes do not visibly blink, while face 34's do. Faces 37 and 40's bracket eyes do not visibly blink, while face 24's do. The manifest confirms different `open` flags: face 27 has `e_shape_13`/`e_shape_12` marked false, face 34's `e_shape_12` is true, faces 37/40 use `open_C_44` false, and face 24 uses `open_C_51`/`open_C_45` true. This is a motion-policy inconsistency, separate from visual geometry.

The first two findings were sent to the implementation owner before this report was written. A single closure bridge was proposed for the next export; this baseline does not claim that change is already verified. The blink observation was also sent for a deliberate eligibility decision.

## Repaired settled poses

Face 13 retains its happy arcs and broad smile while gaining 15 pixels of bottom padding. Face 28 preserves its loop eyes, wavy mouth, and right tear with 15 pixels below the lowest mark. Face 32 preserves its open eyes, curved frown, and right tear with 16 pixels below. No tear or smile was truncated to achieve the fit.

Faces 15, 18, and 27 retain the capsule tilts previously identified in the canonical source audit; those are inherited source choices. Faces 12 and 35 remain intentionally mouthless. The new export uses flat cyan art and antialiased pixels, so absence of the source raster's neon glow is a style difference and was not counted as lost geometry. Enlarged nearest-neighbor pixels in the comparison sheet are an inspection aid.

`settled_comparison.png` places original previews, prior canonical renders, and new settled export frames together for faces 13, 28, 32, 15, 18, 27, and 39.

## Per-expression coverage

All rows passed clipping and settled-identity checks. The common transition midpoint issue applies to the sequence as described above.

| Expression | Zero-based frames inspected | Specific observation |
|---|---:|---|
| `01_angry_01_manual` | 000-009 | Settled shape and sampled blink phases preserve source identity. |
| `02_angry_02_manual` | 010-019 | Settled shape and sampled blink phases preserve source identity. |
| `03_angry_07_manual` | 020-029 | Settled shape and sampled blink phases preserve source identity. |
| `04_angry_08_manual` | 030-039 | Settled shape and sampled blink phases preserve source identity. |
| `05_annoyed_01_manual` | 040-049 | Settled shape and sampled blink phases preserve source identity. |
| `06_annoyed_02_manual` | 050-059 | Raised source mouth stays separate from right eye. |
| `07_annoyed_03_manual` | 060-069 | Settled shape and sampled blink phases preserve source identity. |
| `08_annoyed_04_manual` | 070-079 | Settled shape and sampled blink phases preserve source identity. |
| `09_happy_03_manual` | 080-089 | Settled shape and sampled blink phases preserve source identity. |
| `10_happy_04_manual` | 090-099 | Settled shape and sampled blink phases preserve source identity. |
| `11_happy_05_manual` | 100-109 | Settled shape and sampled blink phases preserve source identity. |
| `12_happy_09_manual` | 110-119 | Intentional mouthlessness preserved. |
| `13_happy_14_manual` | 120-129 | Original happy arc/smile identity retained; new bottom padding is 15 pixels. |
| `14_happy_16_manual` | 130-139 | Settled shape and sampled blink phases preserve source identity. |
| `15_misc_15_manual` | 140-149 | Pre-existing canonical capsule tilt retained. |
| `16_misc_16_manual` | 150-159 | Settled shape and sampled blink phases preserve source identity. |
| `17_misc_2_01_manual` | 160-169 | Settled shape and sampled blink phases preserve source identity. |
| `18_misc_2_02_manual` | 170-179 | Pre-existing canonical capsule tilt retained. |
| `19_misc_2_03_manual` | 180-189 | Settled shape and sampled blink phases preserve source identity. |
| `20_neutral_06_manual` | 190-199 | Settled shape and sampled blink phases preserve source identity. |
| `21_neutral_11_manual` | 200-209 | Raised dome mouth and lids remain separate. |
| `22_neutral_12_manual` | 210-219 | Settled shape and sampled blink phases preserve source identity. |
| `23_neutral_13_manual` | 220-229 | Settled shape and sampled blink phases preserve source identity. |
| `24_neutral_2_01_manual` | 230-239 | Bracket eyes close and reopen visibly. |
| `25_neutral_2_03_manual` | 240-249 | Settled shape and sampled blink phases preserve source identity. |
| `26_sad_01_manual` | 250-259 | Settled shape and sampled blink phases preserve source identity. |
| `27_sad_02_manual` | 260-269 | Pre-existing canonical capsule tilt retained; no visible blink despite related loop-eye face 34 blinking. |
| `28_sad_03_manual` | 270-279 | Wavy mouth and right tear preserved; new bottom padding is 15 pixels. |
| `29_sad_04_manual` | 280-289 | Preceding tear disappears; raised wavy mouth stays distinct. |
| `30_sad_05_manual` | 290-299 | No fitted-source chevron spur appears in the new canonical export. |
| `31_sad_06_manual` | 300-309 | Settled shape and sampled blink phases preserve source identity. |
| `32_sad_07_manual` | 310-319 | Curved frown and right tear preserved; new bottom padding is 16 pixels. |
| `33_sad_08_manual` | 320-329 | Preceding tear disappears; asymmetric eyes preserved. |
| `34_sad_09_manual` | 330-339 | Settled shape and sampled blink phases preserve source identity. |
| `35_sad_10_manual` | 340-349 | Intentional mouthlessness preserved. |
| `36_misc_03_manual` | 350-359 | Settled shape and sampled blink phases preserve source identity. |
| `37_misc_06_manual` | 360-369 | Bracket eyes show no visible blink, unlike related bracket face 24. |
| `38_misc_2_06_manual` | 370-379 | Settled shape and sampled blink phases preserve source identity. |
| `39_neutral_02_manual` | 380-389 | Settled shape and sampled blink phases preserve source identity. |
| `40_neutral_03_manual` | 390-399 | Tiny mouth retained; bracket eyes show no visible blink, unlike related bracket face 24. |

## Speech coverage and measurement limits

Frames 400-449 cover rest, MBP, FV, AA, EH, EE, OH, OO, S, LNT, SMILE, and release. The mouth remains below the eyes and the source eye geometry stays recognizable. In addition to the boundary ghosts above, the still sequence does not establish timing against real audio or whether neighboring visemes look sufficiently different in motion.

`frame_metrics.json` records every label, visible layer count, vector bounds, raster cyan bounds, and padding. Vector bounds include half the stroke width for visible layers with opacity above 0.001. Raster checks identify pixels with green above 35 and green above 1.3 times red, after compositing the exported tile onto its dark background. The bounds check excludes no bright facial geometry, but is not a substitute for the completed visual inspection.

No runtime code or native Aseprite document was edited during this review.
