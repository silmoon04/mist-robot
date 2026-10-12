# Thinking studies v8

Eight studies show reading, coding, writing, sorting, searching, pondering, connecting and checking. Each uses 24 frames: four to enter, sixteen for the repeating activity and four to exit. Coding and writing repeat in 2.4 seconds; sorting takes 2.6 seconds. Searching, connecting and checking each repeat continuously in about 2.13 seconds, with two display ticks per work cel and gaze following the outward and return motion. Pondering takes 2.9 seconds and reading takes 3 seconds. Short pauses remain in the reading, typing, writing, sorting and thinking phrases. An activity continues until its owner clears it and never signals successful completion by itself.

The art comes from ImageGen. Sorting reuses one generated card drawing as three
rigid parts, with occlusion between them. Drafting, connecting and checking reuse
generated bodies and moving parts with controlled placement. These exported frames
are assembled animation poses, not claims of 24 separately drawn illustrations.
Their component origins and positions are recorded in the manifest.

The preview starts with Auto variations. It cycles through the original faces `39_neutral_02_manual`, `40_neutral_03_manual` and `36_misc_03_manual`. Cards start with different faces. During a long activity, the first change starts after two loops, around 4.9 to 6.6 seconds including the entrance. Later changes alternate between three and two loops. Selecting any of the forty original expressions locks that choice; selecting Auto variations restores rotation. Face changes wait while speech is active.

Click a card to inspect it. Pause and Step examine the 15 fps animation. Click a drawing to hold that cel, then choose Follow animation to release it. The layer selector isolates the original eyes, original mouth or activity art. Drawing loop only removes task gaze and holds for a simpler motion comparison. Compare v7 opens the previous studies.

Play recording uses a saved MIST voice sample. The original mouth follows the audio clock while activity gaze and lean settle over 240 ms. The prop dims and holds a work cel. Slow motion is disabled during speech. Pause suspends the audio context; Stop voice stops the recording and lets the gesture return. The page makes no model or voice-provider requests.

## Runtime

Load `app_data.js`, `face_runtime.js` and `drawn_face_renderer.js` from the shared runtime before this `runtime.js`. `MistThinkingRuntime.create(container, options)` wraps that renderer with an activity layer whose `replaceEyes` remains `false`. Whole-face translation and uniform scale keep props separate from the original eye and mouth geometry. The reading book, coding terminal and search document sit below the face. The player waits for the manifest, all activity cels and the original renderer before drawing the combined scene.

Await `player.ready`; it resolves to `true` on success and `false` if loading fails. Read `player.error` for the cause. The manifest must be version 8 at 15 fps, with all eight studies and 24 frame files for each. Production cels are 256 by 256 transparent images. Frame requests include their manifest `sha256` as a URL query, so a corrected frame gets a fresh browser and shared-cache entry while its logical file key stays unchanged. `variantSeed` chooses the initial automatic face deterministically. A valid `expression` option starts with that explicit choice locked instead.

`setActivity(id, {owner, restart})` returns `{accepted, token}`. Calling it again with the same activity and owner keeps the existing token unless `restart` is true. `clearActivity(token)` plays the exit; a stale token cannot end a newer activity. `clearActivity(token, {immediate: true})` removes it at once. Omitting a token is intended for manual preview controls that deliberately clear the current activity.

Use actual tool events to select an activity. Reading fits a file read, searching a search request, coding a code edit, writing a document draft, sorting a reordering operation, connecting a connection attempt, and checking a validation operation. Pondering can accompany an explicit planning interval. Do not imply access to files, email or external services unless that operation has actually started. Connection and checking loops mean work is in progress; they do not announce that a connection worked or a check passed.

Keep the returned token with the operation that owns it. Clear that token when the operation finishes, fails or is cancelled, and report its actual result separately:

```js
const activity = player.setActivity('searching', {owner: request.id});
try {
  const result = await runSearch(request);
  return result;
} finally {
  player.clearActivity(activity.token);
}
```

If another operation starts before this one settles, the old token cannot clear it. On cancellation, use the cancelled operation's token. Use `{immediate: true}` only when an immediate stop is needed; the normal exit lasts 600 ms. Its first 200 ms blend the captured work cel into the first exit cel, so an interruption does not snap the marker back to a fixed pose.

`setExpression(originalFaceId)` locks an explicit face. `setExpression(null)` or `setExpression('auto')` restores automatic variation at a following phrase boundary. An explicit request received during speech is stored and applied after speech quieting has ended. An invalid face ID returns `false` and leaves the current mode unchanged. `expressionMode` reports `auto` or `explicit`.

`startSpeech(settings)` and `stopSpeech()` retain the original playback interface. Call both around playback, including interruptions. Audio samples keep their unrounded time; visual drawing remains at 15 fps. A new activity arriving during speech freezes its own first work cel instead of inheriting a frame from the previous activity. Automatic face changes resume at a later phrase boundary.

`sampleChoreography(id, elapsedMs, options)` is a pure sampler. Options include `frameCount` (24), `exitAge`, `exitFrom`, `speechMix`, `speaking`, `comparison` and `reducedMotion`. The result includes phase, beat, cel, loop index, gaze, whole-face transform and prop placement. It never changes an expression or completes an operation. Reduced motion holds a work drawing and removes task gaze and lean.

Run `node test_choreography.cjs` from this directory for frame reachability at 15 fps, phrase timing, original geometry across all forty faces, speech clocks and freezing, face variation, token ownership, cancellation and delayed loading. The script uses real manifest metadata when it exists and a clearly reported fixture while assets are being prepared. Placeholder image handles verify rendering calls; inspect the actual drawings and play the saved voice in the browser as well.
