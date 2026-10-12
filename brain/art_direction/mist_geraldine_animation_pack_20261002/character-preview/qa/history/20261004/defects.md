# Independent findings

## QA-01: zero-amount sampled speech remains open

First run: 59 of 72 sampled-runtime checks passed. All thirteen failures have the same cause. Start with `{active:true,viseme:'AA',amount:0.8}`, render, then provide `{active:true,viseme:'AA',amount:0}` and render the next 15 fps frame. Every preset still reports an AA mouth and `speaking:true`.

Replay: `node brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/qa/acceptance.mjs`, cases `zero/<preset>`.

Expected: a registered closed cel by the next frame. The actual runtime permits an active segment with zero amount, so active alone is insufficient. Requested fix: require positive amount when deciding whether to articulate; preserve sampled provenance in the diagnostic snapshot. Adapter ownership remains with its author. Retest status is recorded in `acceptance-results.json`.

Resolved on independent rerun: 72 of 72 cases pass, including zero amount for all thirteen presets.

## QA-02: pause can leave an open cel indefinitely

Static integration finding in the first preview implementation: `play()` pauses the transport, stops the interval, and renders with frozen `transport.time()`. The adapter skips an update if it falls in the same 15 fps frame as its previous draw. Pausing while AA is visible can therefore leave that cel visible, with no later frame scheduled to close it. The sampler correctly returns rest while paused; the missing render prevents that rest from reaching the canvas.

Replay for browser verification: play a scene, pause during an open speech cel within its current 66.67 ms frame, wait at least 100 ms, inspect both canvas and snapshot. Expected closed cel. Requested fix: advance the render clock independently of scene/audio time or explicitly schedule one cancellation frame. Browser retest remains pending.

## Evidence boundaries

The independent oracle was written before implementation inspection. Tests use a fake audio clock and injected renderer for deterministic scheduling. Full scene checks use the delivered adapter, sampler and transport, with an independent dispatcher. They do not prove that the browser dispatcher behaves identically, and they do not measure audible latency. Browser, native source hashes, and visual continuity need separate evidence.
