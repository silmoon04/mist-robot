# Hand-drawn runtime review

Final review passes after the user's change of direction: keep the original MIST eyes and retain the nine new activity animations. Runtime SHA256: `bf98617fe07d4146372c31cefdf2e17534c703f06e3caa301dc6ba61c09e4e00`.

Current results are in `qa_original_eyes_report.json`, `qa_runtime_report.json`, and `qa_async_report.json`. The current manifest hash is `c4d67775ced473b6e2f7d5c9b6fca33357c842ece92603a3a8744e8e227ea571` and the shared drawn renderer hash is `3a600d7b08f15bf96c5a74ee353bc01403c09b7bf744e12f9c7c62485ee60f5a`.

The original renderer was extracted from the prior downloadable pack into `qa_v5_reference_renderer.cjs`, with verified SHA256 `9ade474f61fc9a6f3eee260b6bb07ef4adc2a4e6f56cae3a4871acbc531563ff`. The new overlay was compared directly with that renderer, not just with a new implementation of the same expectation.

## Original face verification

- All forty expressions retain exactly the original source paths, eye cel selections, placement data, and transition visuals. This includes the fourteen expressions with different left and right source parts.
- Forty blinks and sampled expression transitions were compared across 800 states: 2,013 original vector paths and 444 original raster cel draws matched.
- The only allowed drawing difference is one common translation and uniform scale applied to the whole face to make room for an activity symbol. Every recorded original face primitive shares that transform, so eye/mouth proportions and left/right asymmetry remain intact.
- No generated replacement eye cel was painted. Only the 108 activity cels were requested by the new loader.
- The original audio-clock mouth and v5 blink timing remain active.

The earlier replacement-eye results are retained as `qa_runtime_report_neweyes_history.json` and `qa_async_report_neweyes_history.json`. They describe a superseded design, not the current live renderer. The initial failure evidence remains in the corresponding `*_beforefix.json` files.

## Earlier failure: blink boundary

Reproduced on runtime `b42dee84004572abca2a726dcadb252fca742d678a9e4b72330806a2d9fe7f87`, then fixed by bounding the sequence index and guarding frame drawing. This replacement-eye sequence is no longer used after the rollback to the original eyes.

`runtime.js:poseAt(age)` can return `undefined` at the last blink boundary. The guard compares `age >= 7*TICK` without tolerance, while the array index uses `Math.floor(age/TICK+1e-7)`. At a floating-point age just below the boundary, the guard accepts the age but the index rounds to 7, outside the seven-element sequence. This propagates an undefined eye frame and pose. A paint at that point can attempt `frames[undefined].file`.

Reproduction: `node brain/art_direction/artist_studio_20260916/reuse/handdrawn_v6/qa_runtime.cjs`. The eight expected sampled poses end with `open, open`; actual ends `open, undefined`.

Use a single bounded tick value for the guard and lookup, or return the open pose when the computed index is out of range. Keep the regression test.

## Earlier failure: callback after destruction

Reproduced on the same earlier runtime, then fixed by suppressing late error callbacks when the instance has been destroyed.

If an instance is destroyed while frame decoding is pending, successful decode results are deliberately not assigned to its image map. The readiness continuation then reports `Hand-drawn frames are incomplete` and calls `onError` on that destroyed instance. Reproduction: `node brain/art_direction/artist_studio_20260916/reuse/handdrawn_v6/qa_async.cjs`. Guard `dead` before checking missing images, and avoid reporting load errors from destroyed instances. The overlay does not revive, but the stale error callback could alter a newer page or session's status.

## Passed checks

- The real drawn renderer retains its original eyes; the new layer adds only an activity symbol.
- All nine activities enter, loop through all four active cels for twelve seconds without inventing completion, then exit. 1,692 sampled states.
- All 81 ordered activity changes reject obsolete completion tokens.
- Old brain/tool completions cannot clear a newer activity; state changes do not displace an active tool.
- When a tool finishes, an explicitly pending thinking state can resume. The next available state clears it. The test expectation was updated for this new owner-restoration behavior.
- All forty expression IDs keep their exact original left and right part IDs.
- Explicit blinking delegates to the original renderer and matches the independently retained v5 reference.
- 120 Hz updates still produce 15 painted frames per second. The speech clock remains unquantized. Lip closures and stopped audio update immediately.
- Failed images retain the old renderer, and retry reloads only the rejected image. Wrong image dimensions fail cleanly.
- Destruction during decoding no longer revives the overlay or calls a stale failure handler.

## Visual review

The activity contact sheet has been visually inspected. No clipped artwork is visible. Activity loop joins are comparable to the changes inside each loop; writing has the strongest change but remains coherent. The connecting symbol stays visibly unjoined, and checking uses a moving inspection dot rather than fabricated check marks.

The new eye styles were rejected by the user and are excluded from the current checks and live loader. The original eye shapes, rotations, asymmetry, and blink registration are verified against the prior release. Root owns the final browser inspection of the composed faces and symbols.

This review uses final cels and a recording canvas context. It does not replace the root's browser inspection. No live microphone, provider, or tool connection was exercised.
