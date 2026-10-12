# Motion pipeline audit

The user's complaint is supported by the drawings and by the playback design. Passing extraction and reconstruction tests did not establish animation quality. The most obvious middle-frame failures are present in the generated source art. Registration and the generic timing/transition recipes add further motion problems.

This review inspected the compiler, renderer, gallery clock, preview builder, extraction metrics and earlier review records. Dark contact sheets were directly inspected for Aardman/disbelief, Bluey/uncertainty, Pixar/recall and Mickey/mock_outrage. No artwork or runtime was changed. All frame numbers below are zero based; add one for the gallery's 1–12 display.

## Confirmed middle-frame discontinuities

| Example | Frames | Observation | Consequence |
|---|---|---|---|
| Aardman/disbelief | 4 → 5 → 6 | Half-lidded eyes reopen as two fully circular O-rings at 5, then the left one immediately drops back to a half lid at 6. Left eye height goes 67 → 106 → 72 px. | The unrelated wide-eyed flash precedes the intended one-eye skeptical beat. This is in the source drawing, not a layer crop problem. |
| Mickey/mock_outrage | 5 → 6 → 7 → 8 | Mouth changes from asymmetric smile to upper arch to a much larger downward triangle, then collapses to a broad smile/wink. Mouth height is 46 → 70 → 113 → 66 px. At 7 → 8 both eye centers move down 33–36.5 px. | The mouth changes topology and emotional reading while the eyes make a large jump; there are insufficient connective drawings. A static description calling this a “playful wink” missed the temporal problem. |
| Mickey/double_take | 5 → 6 → 7 | Left eye height 100 → 149 → 71 px; its center rises 22.5 px then falls 34 px on consecutive 67 ms exposures. | A very strong single-frame peak followed by an immediate squash. It can read as a defective drawing unless the sequence is deliberately timed and bridged. These are metrics requiring visual review, not an automatic claim that squash is forbidden. |
| Bluey/uncertainty | 5 → 6 → 7 | Left eye changes from 85 px half-lid to 115 px ring, then 132 px ring with a long angled cap; the other eye's cap and opening also change identity. | The intended asymmetry exists, but intermediate silhouettes are not a consistent gradual lid action. |

## Registration is not a stable facial rig

`build_assets.cjs:registerFrames()` sets X from the mean of both eye bounding-box centers and Y from the mouth bounding-box center. That works for correcting much of the generated sprite-sheet row/column drift. Source translations of 20–110 px at row boundaries must **not** all be called bad jumps: most cancel source layout drift, leaving stable registered artwork.

However, the mouth's center is not a head-position landmark. Changes in mouth curvature, opening or angle change this anchor and move both eyes in response. Quantified examples:

- Aardman/realisation 5 → 6: mouth height grows 20 → 28 px. Registration adds +5 px Y. Both rendered eye centers move +4.5 px even though both raw eye centers move −0.5 px.
- Bluey/reassurance 5 → 6: mouth height grows 25 → 30 px. Registration adds +3 px Y, and both rendered eyes move exactly +3 px despite unchanged raw eye centers.
- Peanuts/wry 6 → 7: mouth height grows 13 → 32 px. Registration adds +6 px Y. The still-open right eye moves +7.5 px; +6 px of that comes from the registration operation.

These are small compared with the worst art jumps, but they create head bobbing tied to mouth changes. The X anchor can also erase intentional whole-eye translation (particularly dot-eye gaze), because any change in the pair's mean position is forcibly removed. That last point is an algorithmic risk; the current sheets' layout drift means intent cannot be recovered from coordinates alone.

Fix direction: establish a shared logical face rig with stable eye socket and mouth attachment anchors; record per-sheet/per-frame registration against those anchors. Preserve intended eye motion and mouth opening around them. Do not derive vertical face placement from the animated mouth bounds. For a generated sheet, manually confirmed anchors or a fixed per-cell grid correction are more reliable than pretending changing ink bounds identify the head. Retain the source and record all registration offsets.

## All clips use the same rushed timing

`runtime.frameAt()` ignores `frame.durationMs`, and computes 12 equal 66.67 ms exposures at 15 fps, then jumps to frame 0 for a 1000 ms rest. Every clip therefore has an 800 ms active sequence and an 1800 ms loop.

Every generated sequence spends frames 0–5 on the same blink/reopen procedure. Only frames 6–11 remain for anticipation, emotion change, reaction and return: about 400 ms total. A peak at frames 7–8 survives only 133 ms; some peaks survive 67 ms. Adding more distinct PNGs did not provide enough time to read the acting.

Fix direction: keep the requested 15 fps timebase but assign each drawing one or more ticks. Plan individual exposure sheets, including anticipation and a readable emotion hold. A 12-drawing animation does not have to last 12 ticks. For these subtle expressions, consider 20–32 ticks total before any rest, depending on the beat. Use the same authored exposure metadata in the gallery and GIF builder. Avoid adding a mandatory full blink before every emotional reaction; separate blink and acting clips when appropriate.

The clock's `Math.min(delta, 100)` clamp can slow elapsed animation after a stalled browser frame. It does not explain a visibly malformed middle drawing and is not the primary defect.

## Transitions teleport closed eyes between different face layouts

`runtime.paint()` computes a separate contain-fit scale and offset for every example. Registered canvases vary from 389–424 px wide and 383–452 px tall. Their padding is generated from correction ranges, not a common visual layout. `transitionPlan()` hard-swaps source frame 3 for target frame 3 at step 5. Closed lids are still visible; closing them does not hide changes in their position and size.

Replaying the renderer's exact contain-fit formula using the recorded eye bounds gives:

- Peanuts/wry → Aardman/listening: a **52.0 px** closed-eye center jump in a 409 px source canvas.
- Aardman/listening → Peanuts/wry: **49.2 px**.
- Peanuts/pride → Aardman/listening: **47.4 px**.

Those are 12–13% of the source canvas width in the worst cases, in one transition step. `pipeline_metrics.json` includes all 306 directed handoffs.

The mouth crossfade is weighted additive compositing between two differently placed source and target mouth images. Its midpoint can visibly contain two different mouth contours. The existing test that avoids opacity dimming only proves correct pixel blending; it does not prove a convincing mouth transition.

Fix direction: render all faces on the same logical rig and scale; author closed-lid bridge positions and compatible shapes instead of swapping arbitrary closed drawings. Treat substantially different eye families as needing their own transition path. Mouth transitions need approved intermediate silhouettes or deliberate closure to a shared rest shape. Crossfading two unrelated shapes should not be described as a drawn transition.

## Why the previous verification missed it

- `visual_review_first.json` explicitly has `movingPlaybackInspected: false`.
- `visual_review_second.json` says “Static review only: smooth playback is not claimed.”
- The existing compiler tests validate alpha, file integrity, crop margins and exact layer reconstruction. They preserve bad source drawings perfectly.
- The runtime transition tests use synthetic fixtures and exact endpoint equality. They do not assert a bound on closed-lid position, common eye scale or intermediate visual continuity.
- Most judgments described what a frame was meant to express; they did not reject an unplanned shape change, an unreadable one-frame event, or a pop at the loop boundary.

## Acceptance checks for the replacement pass

1. Review the full-size filmstrip **and** actual-speed moving playback, with frame numbers visible.
2. Review 4→5→6→7→8 and the 11→0 seam for every clip. Record each anomalous frame by index, not just a per-sheet pass.
3. Compare each feature's silhouette, eye model and attachment point between neighbors. Intentional squash needs deliberate anticipation and recovery; no arbitrary ring/half-lid/cap change.
4. Make motion metrics warnings, not automatic quality verdicts. A blink's bounds change legitimately; the mouth must not move the whole face while opening.
5. Inspect transitions at every handoff, using the shared rig. A unit test for a maximum allowed anchor displacement is useful after anchors are semantically defined.
6. Do not publish a new “all frames passed” claim until moving playback has actually been reviewed. Separate technical extraction success from visual acceptance.

Reproduce the numeric audit with `python qa_v3/pipeline_audit.py` from this animation directory. It only reads the manifest and existing asset metrics and writes its own diagnostic JSON.
