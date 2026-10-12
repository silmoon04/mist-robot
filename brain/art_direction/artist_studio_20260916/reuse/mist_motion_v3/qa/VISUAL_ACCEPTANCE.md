# Independent motion review

Status: awaiting replacement assets. This document defines the review; it is not an approval.

Reviewer: mist_v3_motion_review. Frame numbers in findings will be one-based, matching the gallery.

## Reference inspected

The original 39_neutral_02, 01_angry_01, 09_happy_03 and 26_sad_01 PNG faces were visually inspected. MIST uses open C contours and hooks, rounded ends, mint strokes, and a small simple mouth. The open ring is the eye itself; it is not a white surrounding an internal pupil. Happy and sad contours are valid separate expressions, but a blink must not jump between them.

The v2 blink, acting and pipeline audits establish the rejected defects: curvature reversal; temporary pupils, caps or eyebrows; unrelated mouth silhouettes; eye shifts introduced by mouth-based registration; and an acting beat compressed into a few unsupported poses. Technical file integrity did not establish motion quality.

## Acceptance checklist

- Inspect generated source components, not only the final composites. A source with a mismatched middle shape cannot be approved because later cropping hides it.
- Compare each rendered eye to its chosen original MIST family. No internal pupil, filled disk, extra cap, detached eyebrow, bell silhouette, tongue or teeth appears at any point.
- Inspect all twelve poses and every adjacent pair, including 12 to 1, for every clip. Record the exact pair of a defect, including asymmetry that changes without an acting reason.
- Preserve eye contour identity across acting poses. Rigid glances and small rotations are allowed; replacing one contour with an unrelated eye is not.
- Inspect each independent blink: opening shrinks toward a consistent closed contour, closure does not flip concavity, and reopening retraces compatible drawings. A clipped or squashed eye is not automatically a drawn lid closure.
- Inspect mouth identity separately. A bar may form a smile through intermediate curvature, or open continuously into a bowl; it must not jump through a dot, grin and frown in successive poses.
- Check eye anchors while mouth changes. Mouth opening must not shift the eyes, alter overall face scale, or reset the apparent head position.
- Confirm exactly one legible acting idea per clip, with an anticipation, readable accent or hold, and coherent return. Avoid unrelated gestures and one-frame emotional montages.
- Check the movement at the gallery's displayed size. A nominal animation whose movement is invisible at that size is not a useful replacement, even if hashes differ.
- Check authored timing at the intended 15 fps timebase and slower playback. Twelve poses may have multiple exposure ticks. An unreadable one-tick peak must be intentional and visually supported.
- Check transitions between all used eye families, including source-to-target and reverse directions. Shared anchors must remain stable while changing the drawing; a crossfade showing two incompatible contours is not a drawn in-between.
- Keep the same eighteen IDs and review data. This is a compatibility check, separate from visual acceptance.

## Per-clip review record

For each clip record: style verdict; adjacent-frame observations; mouth path; eye path; loop seam; action legibility; displayed-size legibility; intended-speed evidence; slow-playback evidence; remaining limitations; and final decision.

An item can be accepted visually, require repair, or remain unverified. Do not convert unverified playback into a pass based on contact sheets. File counts, hashes, alpha reconstruction and runtime timing tests will be reported separately.

## Motion evidence limitations

An image viewer may show only one frame of a GIF. If so, report contact-sheet and sampled-frame inspection only. Browser playback must be evaluated from actual timed visual evidence or another supported motion-viewing method before calling temporal feel verified. A screenshot of a playing canvas is still a screenshot.

## Action intent

| ID | Intended action | Avoid |
| --- | --- | --- |
| aardman/listening | Attentive closed-mouth response | Bored sustained lids or a talking mouth |
| aardman/disbelief | Restrained skeptical response | Surprise flash or dismissive hostility |
| aardman/realisation | A thought resolves | Instant grin unrelated to the eye action |
| bluey/reassurance | Concern eases into warmth | Celebrating distress |
| bluey/delight | Shared modest happiness | Generic blink consuming the whole action |
| bluey/uncertainty | A tentative question | Confidence or celebratory smile |
| pixar/recall | Brief thoughtful glance and return | Pupils introduced into MIST rings |
| pixar/checking | A deliberate checking glance | Eye contour breaking into a new model |
| pixar/discovery | A useful answer is found | Bar-dot-smile-bar montage |
| mickey/double_take | Supported comic attention accent | Unconnected one-frame extreme |
| mickey/mock_outrage | Restrained playful squeeze | An angry shout or unrelated wink montage |
| mickey/triumph | Short confident smile | Happy blink curvature inserted as a closure |
| simons_cat/notice | Directed attention | Random motion with no target |
| simons_cat/waiting | Patient opening for a reply | Impatient repeated restart |
| simons_cat/clarify | A small questioning asymmetry | Instant full-to-half eye replacement |
| peanuts/company | Quiet acknowledgement | Imperceptible movement or pupil notches |
| peanuts/wry | Affectionate small response | Extra detached brows during a wink |
| peanuts/pride | Modest contentment | Eye caps appearing only at the peak |

