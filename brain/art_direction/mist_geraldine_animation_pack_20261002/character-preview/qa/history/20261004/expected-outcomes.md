# Independent acceptance oracle

Frozen before inspecting the new adapter, direction, speech-review or preview implementation. The inspected live seam passes `startSpeech({events: [], duration: Infinity, clock, sample})`. Its sampled gaps and suspended/interrupted audio return inactive rest without epoch identity. Active packets carry epoch, sequence and turn ID. Reset stops and disconnects every audio source, clears the timer, and calls `stopSpeech()`.

Tests must exercise that sampled interface, including a frozen speech clock with a changing sample. The render clock must still close the mouth by its next 15 fps frame. Clock tests establish scheduling behavior only. They cannot establish acoustic synchronization or a listening score.

The parent brief overrides the old catalog pause behavior: suspended playback closes speech instead of freezing an open articulation. Closed means an existing `rest` or `MBP` cel. `amused`, `laughing`, and `eager-delight` have open preset rests and therefore need explicit adversarial coverage after rest, inactivity, zero amount, stop and reset.

Cancellation is tested in both directions: old speech samples must not reopen the mouth, and old expression events must not replace the current emotional intent. Ordinary gaps must retain that intent. A finite reaction returns to the ongoing intent at its declared deadline. Repeating the current face must not restart its transition.

Full replay checks cover all three scenes, every authored event and each 15 fps sample through the scene end. Compare two clean executions, then test rapid replay with old callbacks still available. Teardown must make captured callbacks harmless and leave no loop or audio source alive.

Native asset acceptance checks family and cel ownership for all thirteen presets and all scene frames, followed by a visual review against the selected existing artwork. Mechanical ownership checks do not substitute for style judgment. Source hashes are the root owner's evidence. Subjective taste and final selection remain for the user.

Browser acceptance covers desktop and 851 by 393, keyboard operation, reduced motion, note persistence after reload, exported moment identity, local-only network requests, and a useful missing-asset error. The browser pass remains pending until the parent hands over the browser and a ready local server.
