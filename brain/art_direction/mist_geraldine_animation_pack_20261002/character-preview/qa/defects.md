# Independent findings

## QA-01: zero-amount sampled speech remains open

First run: 59 of 72 sampled-runtime checks passed. All thirteen failures have the same cause. Start with `{active:true,viseme:'AA',amount:0.8}`, render, then provide `{active:true,viseme:'AA',amount:0}` and render the next 15 fps frame. Every preset still reports an AA mouth and `speaking:true`.

Replay: `node brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/qa/acceptance.mjs`, cases `zero/<preset>`.

Expected: a registered closed cel by the next frame. The actual runtime permits an active segment with zero amount, so active alone is insufficient. Requested fix: require positive amount when deciding whether to articulate; preserve sampled provenance in the diagnostic snapshot. Adapter ownership remains with its author. Retest status is recorded in `acceptance-results.json`.

Resolved on independent rerun: 72 of 72 cases pass, including zero amount for all thirteen presets.

## QA-02: pause can leave an open cel indefinitely

Static integration finding in the first preview implementation: `play()` pauses the transport, stops the interval, and renders with frozen `transport.time()`. The adapter skips an update if it falls in the same 15 fps frame as its previous draw. Pausing while AA is visible can therefore leave that cel visible, with no later frame scheduled to close it. The sampler correctly returns rest while paused; the missing render prevents that rest from reaching the canvas.

Replay for browser verification: play a scene, pause during an open speech cel within its current 66.67 ms frame, wait at least 100 ms, inspect both canvas and snapshot. Expected closed cel. Requested fix: advance the render clock independently of scene/audio time or explicitly schedule one cancellation frame. Resolved on the 4 October browser pass described below.

## Evidence boundaries

The independent oracle was written before implementation inspection. Tests use a fake audio clock and injected renderer for deterministic scheduling. Full scene checks use the delivered adapter, sampler and transport, with an independent dispatcher. They do not prove that the browser dispatcher behaves identically, and they do not measure audible latency. Browser, native source hashes, and visual continuity need separate evidence.

## Final independent review, 4 October 2026

Preview 1.0.1 and adapter 1.0.0 passed the defined local review checks. There are no open blocking findings from this pass. Prior receipts and this file's earlier state are preserved under `history/20261004/`.

- Sampled runtime: 72/72 checks pass. QA-01 remains resolved for all thirteen presets.
- Added boundary cases: 5/5 pass, including a finite clock expiring while its callback still reports active AA, duration zero, and cancellation/destruction inside a callback.
- Independent scene/cel checks: 9/9 pass. Both timing profiles repeat the same full authored traversal; every rendered cel belongs to the native manifest. These tests use an independent dispatcher.
- Actual browser: 20/20 checks pass. The normal page covers all three scenes, expressive ending, packet gap and resume, repeated replay, open-mouth pause, paused half-blink, pause and interruption during a finite reaction, early resume during recovery, keyboard controls, reduced motion, and note persistence/export. QA-02 is resolved in the browser: pausing an open AA cel closes speech, pausing a native half-blink settles to rest, and a paused reaction returns while scene time stays fixed.
- Manual interruption during an expressive reaction retained quiet-listening intent and completed its return at 410 ms in this run. A pause/recovery/early-resume run recorded 425 ms. These observations include frame scheduling; the native transition is 400 ms and the documented extra frame can add about 67 ms before any event-loop delay.
- Real AudioContext suspension and pagehide cleanup pass in the QA fixture, which imports the original app and styles and captures references for observation. Suspension leaves zero sources and a closed mouth; Resume produces speech again. Navigation closes the context, stops/disconnects the source, destroys the face and clears the interval.
- The isolated missing-WAV fixture deliberately returns HTTP 404. Its acceptance result is false, as expected; the page names the missing path, gives the launch/reload instruction and disables playback. Native assets were not edited.
- Network capture from the normal page contains 28 unique URLs, all on `127.0.0.1:9064`, with no truncated event history. The four tested implementation hashes are unchanged across the browser pass.

See `browser-review.json`, the per-scene browser traces, `suspension-teardown.json`, the two note exports, and the desktop/phone screenshots. The synthetic note was removed after verification; emulated media and viewport overrides were cleared, and both fixture tabs were closed.

## QA-03: duplicate authored interruption rows, non-blocking

The actual dry-reply trace logs `Authored user interruption` twice at 5.032 seconds: once for the authored event in epoch 7 and once when applying cancellation in epoch 8. The on-screen event list omits epoch, so those rows look identical. Cancellation, closed speech and preserved intent all work.

Replay: choose A dry reply, interrupted, open the timing inspector, and play beyond five seconds. Evidence: `browser-second-attempt-expressive.json`, final event transcript. A future copy cleanup could label the first row as an interruption request and the second as applied cancellation, or display epoch. This does not block local review readiness.

## Visual and acoustic limits

The selected cyan eye and mouth drawing remains consistent in the observed ordinary, dry and reassuring poses. Desktop and 851 by 393 layouts keep the face and playback controls visible. The inspector stays below the normal scene in the expandable review section. Native-cel ownership, discrete visual observations and scheduling traces support local review readiness; they are not a continuous perceptual motion score.

The reviewer did not hear the browser audio. No acoustic latency, listening quality or lip-sync score is claimed. Final taste, expression selection, live integration and production-default approval remain outside this QA verdict.
