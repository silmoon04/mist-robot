# Thinking studies

The first card, Quiet pondering, is the everyday thinking option. The other cards describe a particular task. Each enters, works in a short phrase with pauses, and continues until Exit is pressed. A loop never reports that a task succeeded.

Click a card to inspect it. Pause and Step examine motion at 15 fps; Slow motion keeps the same frames visible for longer. Click an individual prop cel to hold it. Follow animation releases that hold. The face selector includes all forty original expressions.

Icon loop only removes the task gaze and pauses, so the same drawings can be compared with simple repeated icon motion. Previous animations opens the unchanged v6 page.

Play recording uses a saved MIST voice sample. It quiets the task gesture while the original mouth follows the playback clock. Slow motion is disabled during speech. Pause suspends the audio context; Stop voice stops the recording and lets the task gesture return. The page makes no model or voice-provider requests.

## Runtime

`MistThinkingRuntime.create(container, options)` wraps the original drawn renderer. It supplies an activity layer with `replaceEyes: false` and one uniform transform for the whole face. It does not replace eye shapes or choose a new expression automatically. `setExpression` accepts the original forty IDs.

`setActivity(id, {owner, restart})` returns a token. `clearActivity(token)` plays the exit; a stale token cannot end another activity. `clearActivity(token, {immediate: true})` removes it at once. Valid activities: reading, coding, writing, sorting, searching, pondering. The caller maps actual tool events to these activities. They should not be selected from guessed access to files or email.

`startSpeech` and `stopSpeech` retain the existing playback interface. The activity pose settles over 240 ms, the prop dims and holds a cel, and speech timing continues through the original renderer. The visual cadence remains 15 fps; the supplied audio sample time is not rounded.

`sampleChoreography(id, elapsedMs, options)` is pure. Options: `frameCount` (12 or 16), `exitAge` (milliseconds since explicit clear), `exitFrom` (previous sampled state), `speechMix` (0 to 1), `speaking`, `comparison`, and `reducedMotion`. Its result describes phase, beat, selected cel, gaze, whole-face transform, prop placement and opacity. Sampling the same arguments gives the same result.

The manifest selects each asset and default face. New book, terminal, note and cards sheets use four entrance, eight work and four exit cels. Reused searching and planning sheets have four of each. No animation changes the live phone default.
