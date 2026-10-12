# Animation review, 22 September 2026

This pass reviews the drawings, their placement, their timing and their connection to audio. The previous bounds check established that frames fit on screen. It did not establish that the motion looked natural.

## What must hold

- Each eye keeps its identifying contour until it closes. Reopening must restore the same shape without losing a crossbar or creating a detached stroke.
- A blink at 8 fps must show a partial close, a closed hold and a partial reopen. Extra breakdown drawings can serve higher frame rates and slow inspection.
- One fixed scale applies throughout a sequence. Frame alignment may correct sheet placement; it must not stretch each drawing to equal bounds.
- Speaking mouths stay attached to the original expression's mouth position. Pauses and final closure must not teleport the mouth.
- Mouth movement follows the audio that reaches playback. Text arrival, network packet arrival and animation wall time are not speech clocks.
- Buffering, suspension, an underrun and interruption must not leave a talking mouth on a silent face. Stale packets and callbacks must not revive an old turn.
- Provider character timing may guide mouth categories when available. Spelling-based categories are approximate, not phoneme recognition. Energy-only recordings establish timing and pauses, not pronunciation-specific lip shapes.
- All 40 faces remain available for comparison. Original artwork and rejected generations remain separate from accepted replacement sheets.

## Findings in the first version

The round eye has no useful near-closed gap and narrows abruptly on reopening. The loop eye drops its crossbar and separates into two arcs. The arch eye reverses curvature abruptly while changing width. These three families now have eight replacement poses each.

The hook and chevron also have eight replacement poses, adding a narrow reopening slit and a gradual folding action. The slot and bar retain their six-pose sheets. The bar's pinch is an expression squeeze, since the resting bar is already closed. Five eight-pose eye families, two six-pose families and two sixteen-pose mouth families total 84 drawings.

Both mouth sheets lack distinct release shapes. Some consonant categories are too similar, and cheerful mouth character is weak during speech. Replacement sheets add release, near-closed and rounded transition drawings.

The new FV drawing still opens too far for this abstract style; playback uses the narrower S drawing for that category. The two mouth families remain subtly different rather than strongly emotional. The eyes and canonical resting mouth carry most of the expression.

The old renderer places every speaking mouth at the same coordinates, then switches directly back to differently placed expression mouths. The old voice player starts a new speech envelope for every 100 ms packet. Both are implementation problems that more drawings alone cannot repair.

The independent identity audit confirmed another implementation defect: fitting the rotated sprite rectangle shrank several eyes to 56-74% of their original width. Shared animation families were being treated as interchangeable resting artwork. The revised renderer retains exact canonical eyes at rest and fits actual raster ink during a blink.

Slow browser inspection of face 05 to face 28 found double eyelids and overlapping mouths during an initial crossfade implementation. The final renderer uses a single closed-lid bridge and one mouth closure instead. Repeating the slow browser inspection confirmed that the doubled contours were removed; a bounds-only test would not have detected this flaw.

## Final verification

Independent checks cover all 1,560 directed transitions between different faces, with and without speech, including 23,560 sampled states, 160 rapid interruptions and 40 reduced-motion cases. There were no duplicate or missing eyes, clipped parts, invalid coordinates or incorrect endpoints. The identity audit checked all 40 faces and 80 resting eyes against their original geometry. All 30 reusable eye parts were also checked using decoded raster ink, rather than a rectangle proxy.

The production renderer is shared by the live app, the grid and the transition inspector. Browser checks exercised the six saved voice recordings, pause, resume, stop and expression changes during playback. Audio time continued through expression changes, and pausing closed the mouth. Fourteen asynchronous cancellation cases passed; stopping while audio loads cannot start it later.

The model-facing controller exposes 21 named expression presets and variants covering all 40 faces. It rejects invalid calls, limits rapid changes and ignores stale turns. Seventy-two real GPT-6 Luna prompts were tested over three batches. All named presets passed. One case in the final 19-prompt batch substituted a related valid face for an unavailable requested name. The median first tool call in that batch was about 1.81 seconds, excluding process startup; this is not end-to-end voice latency. Production model defaults were left unchanged.

Provider alignment, audio clock selection, packet boundaries, silence, output tails and interruption have automated regression coverage. Fresh aligned synthesis is still blocked as described below. These results establish geometry and timing behavior, not a claim that every motion is subjectively finished.

## Live provider test

Fresh synthesis was attempted with the configured MIST voice and Eleven Flash v2.5. The voice lookup succeeded, but a minimal synthesis request returned payment_required and the subscription read showed past_due. WebSocket attempts also returned final responses without audio. No new aligned recordings were generated. The six saved MIST recordings remain usable for local energy-timed playback tests. Billing was not changed.

## Evidence

- `visual_quality_checks.json`: read-only silhouette measurements and first-version visual findings.
- `motion_checks.json`: latest placement and sampling checks, tied to the checked preview file hash.
- `validation.json`: source hashes, frame bounds and shape measurements for the current atlas.
- `audio/samples.json`: provenance and text for six saved MIST recordings used in local playback inspection.

No file in this review should be read as evidence of measurements on the physical phone speaker or Bluetooth path.

## Timing references

The output clock uses the browser's rendered audio timestamp where available. See [AudioContext.getOutputTimestamp](https://developer.mozilla.org/en-US/docs/Web/API/AudioContext/getOutputTimestamp). The streaming provider can return character alignment alongside audio; see [ElevenLabs realtime TTS](https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/realtime-tts). Character timing is not a phoneme transcript.
