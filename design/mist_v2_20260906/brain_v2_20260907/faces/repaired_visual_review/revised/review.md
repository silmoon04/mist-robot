# Revised export visual review: all 450 frames pass

Every regenerated frame was visually inspected in `frames_01.png` through `frames_09.png`. This is a new pass over the revised Aseprite export, not a carry-forward of the earlier result. Frames 000-199 and 400-449 were checked by the primary reviewer; an independent reviewer checked every frame 200-399. The baseline sheets and baseline report remain in the parent directory.

The revised sample has no visible double-mouth ghosts, clipped features, catastrophic filled-screen panels, stepped mouth defects, severe new artifacts, or settled expression identity loss. All 450 vector frames stay within the 100 x 64 canvas, and all raster marks stay inside the 200 x 128 exported tiles. Minimum measured raster padding remains 15 pixels.

## Baseline findings and revised result

| Earlier finding | Revised evidence | Result |
|---|---|---|
| Speech-entry frame 401 showed two mouth lines. | Frame 401 now has one bright closed-lip line. | Fixed |
| Speech-release frame 447 showed a smile bowl behind the returning neutral line. | Frame 447 now has one bright closed-lip line; the old bowl is absent. | Fixed |
| Expression phase 2 dimmed the face and sometimes retained faint old/new mouths. | The reviewed midpoint frames keep bright eyes and a single mouth that closes before reopening into the target shape. | Fixed |
| Loop eyes 27 did not blink despite related eyes 34 blinking. | Frames 266, 267, 268 show closure, partial reopening, and restored loops. | Fixed |
| Bracket eyes 37 and 40 did not blink despite bracket eyes 24 blinking. | Frames 366-368 and 396-398 now show closure and reopening. | Fixed |

`before_after_fixes.png` places six exact baseline/revised frames side by side. It includes the midpoint example 012, both speech-boundary examples, and the three newly enabled blink closures.

The JSON independently confirms at most one visible mouth layer in every frame, exactly one mouth layer in all 50 speech/release frames, and eye opacity exactly 1 throughout all 450 frames. The only mouth opacity reductions occur in frames 111-113, 121-123, 341-343, and 351-353, when entering or leaving the intentionally mouthless faces 12 and 35. Those accessory fades preserve bright eyes and do not reproduce the previous dim whole-face transition.

## Source identity and clearance

The repaired settled poses retain the original visual identities. Face 13 keeps its happy arcs and broad smile with 15 pixels below its lowest raster mark. Face 28 keeps its loop eyes, wavy mouth, and right tear with 15 pixels below. Face 32 keeps its open eyes, curved frown, and right tear with 16 pixels below. The tear strokes and smile bowls remain complete.

The canonical capsule tilts in 15, 18, and 27 remain inherited source details, as previously recorded; the fit does not introduce a new rotation defect. Faces 12 and 35 remain mouthless, face 40 retains its tiny dot mouth, and asymmetric eyes and smirks remain recognizable. `settled_comparison.png` compares the original preview, source canonical raster, and regenerated settled export for seven representative expressions.

## Per-expression coverage

Each row covers five transition samples, four blink samples, and one settled frame. Every row passed clipping, double-mouth, severe-artifact, and settled-identity checks.

| Expression | Zero-based frames inspected | Observation |
|---|---:|---|
| `01_angry_01_manual` | 000-009 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `02_angry_02_manual` | 010-019 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `03_angry_07_manual` | 020-029 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `04_angry_08_manual` | 030-039 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `05_annoyed_01_manual` | 040-049 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `06_annoyed_02_manual` | 050-059 | Raised source mouth stays distinct from the right eye. |
| `07_annoyed_03_manual` | 060-069 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `08_annoyed_04_manual` | 070-079 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `09_happy_03_manual` | 080-089 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `10_happy_04_manual` | 090-099 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `11_happy_05_manual` | 100-109 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `12_happy_09_manual` | 110-119 | Intentional mouthlessness retained; outgoing mouth fades without dimming eyes. |
| `13_happy_14_manual` | 120-129 | Happy arcs and smile retained; 15 pixels of lower raster padding. |
| `14_happy_16_manual` | 130-139 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `15_misc_15_manual` | 140-149 | Inherited canonical capsule tilt remains unchanged. |
| `16_misc_16_manual` | 150-159 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `17_misc_2_01_manual` | 160-169 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `18_misc_2_02_manual` | 170-179 | Inherited canonical capsule tilt remains unchanged. |
| `19_misc_2_03_manual` | 180-189 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `20_neutral_06_manual` | 190-199 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `21_neutral_11_manual` | 200-209 | Raised dome mouth stays distinct from curved lids. |
| `22_neutral_12_manual` | 210-219 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `23_neutral_13_manual` | 220-229 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `24_neutral_2_01_manual` | 230-239 | Bracket-eye blink remains clear. |
| `25_neutral_2_03_manual` | 240-249 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `26_sad_01_manual` | 250-259 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `27_sad_02_manual` | 260-269 | Loop-eye blink is now visible at 266-268; inherited capsule tilt retained. |
| `28_sad_03_manual` | 270-279 | Wavy mouth and right tear retained; 15 pixels of lower raster padding. |
| `29_sad_04_manual` | 280-289 | Outgoing tear fades without a duplicate mouth. |
| `30_sad_05_manual` | 290-299 | No prior fitted-source chevron spur appears. |
| `31_sad_06_manual` | 300-309 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `32_sad_07_manual` | 310-319 | Open eyes, frown, and right tear retained; 16 pixels of lower raster padding. |
| `33_sad_08_manual` | 320-329 | Outgoing tear fades without a duplicate mouth. |
| `34_sad_09_manual` | 330-339 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `35_sad_10_manual` | 340-349 | Intentional mouthlessness retained; outgoing mouth fades without dimming eyes. |
| `36_misc_03_manual` | 350-359 | Mouth appears from the preceding mouthless expression while eyes remain bright. |
| `37_misc_06_manual` | 360-369 | Bracket-eye blink is now visible at 366-368. |
| `38_misc_2_06_manual` | 370-379 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `39_neutral_02_manual` | 380-389 | Clean single-mouth closure bridge, preserved settled shape, no severe new artifact. |
| `40_neutral_03_manual` | 390-399 | Bracket-eye blink is now visible at 396-398; tiny dot mouth retained. |

## Speech and scope

Every frame 400-449 was checked. The sample covers rest, MBP, FV, AA, EH, EE, OH, OO, S, LNT, SMILE, and release on neutral expression 39. The mouth stays separate from the eyes and transitions without a second visible mouth. The bright closure bridge solves the earlier ghosting without hiding it in a dark frame.

This verdict covers the exported pixels and the manifest geometry of these 450 sampled frames. It does not establish real-audio synchronization, perceived speed during live playback, every possible expression-pair transition, or speech on every expression. The implementation's wider regression tests are separate evidence and were not rerun as part of this visual subtask.

`snapshot.json` records the exact revised inputs and hashes; `verification.json` confirms those files still match at review completion. `frame_metrics.json` records per-frame bounds. Vector bounds include half stroke width for visible layers with opacity above 0.001. Raster checks select cyan pixels with green above 35 and green above 1.3 times red after compositing onto the export's dark background. These measurements support the completed visual review.

No runtime source or native Aseprite document was edited by this audit. Baseline evidence remains unchanged in the parent directory.
