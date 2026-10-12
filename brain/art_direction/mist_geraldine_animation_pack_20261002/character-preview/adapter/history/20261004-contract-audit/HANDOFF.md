# Adapter worker handoff

`geraldine-adapter.mjs` wraps snapshot copies of the current site transition engine and native atlas renderer. The copies include the local source as inspected, regardless of its Git status. `contract/source-hashes.json` records SHA-256 for those sources, the manifest, and the inspected live playback/app files. `contract/asset-hashes.json` records the native PNG bytes read in place.

Run `node brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/adapter/check.mjs` from the repository root. The result is written to `adapter/worker-checks.json`. These checks use an injected clock and renderer; parent acceptance owns browser motion and perceptual judgments.

The wrapper supports the live speech sampling call, including untagged rest samples, and preserves provenance in its snapshot. It retains emotional intent through silence and reset. All render frames use the manifest's existing registered cels. Expression aliases are intentionally small; all 13 pack IDs also work. Unknown IDs return false, so a logic owner must map the remaining live catalog IDs before changing the runtime default.

Stop cancels the current sampler generation. Reset additionally establishes an epoch boundary; callers testing tagged stale traffic should call `reset({epoch:newEpoch})` before attaching new speech. Untagged live calls cannot identify stale work. A host must retain its current turn arbitration and discard stale callbacks before making those calls. Optional activity, listening waveform and gaze hooks remain unsupported. No live runtime, production default, audio source, service, or publication was changed.

The caller must await readiness, drive update frames, and stop its audio and frame loop on disconnect or teardown. `destroy()` prevents future adapter drawing, including completion of an outstanding asset load. It cannot stop audio owned by the host. Finite reactions accept 1..10000 milliseconds and return to the latest persistent intent; repeats neither restart transitions nor extend the reaction timer.
