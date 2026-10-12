# Mouth and transition refinement

The FV, LNT and TH drawings were replaced in both neutral and smiling mouth families. The current grid, inspector and live app share the 15 fps production renderer.

## Artwork

Built-in ImageGen produced six replacement cels in one accepted sheet, `sheets/mouth_consonants_v3.png`. Neutral FV is a compressed capsule, LNT a shallow bowl and TH a small oval. The smiling versions use broad, continuous curves. Visual inspection found no localized upper notches, lower tongue-like tabs, teeth or internal islands. The pixel audit found one connected shape per cell, no detached pixels and no internal column gaps.

The complete generation prompt and references are in `generated_mouth_consonants_v3.json`. The generated PNG was copied byte for byte. Each replacement frame declares its own source file and uniform source scale, 0.43310546875, derived from the two sheets' cell sizes. The original resting mouth, vowels, closures and all eye drawings remain unchanged. The selected atlas still contains 84 reusable poses.

The grid's inspector and the production renderer both load the new sheet. Runtime FV now selects FV instead of bypassing it through S. TH is accepted by both playback copies and the text-timing mapper. Written th/dh spans retain the dental cue across packet boundaries; this is a character heuristic, not phoneme recognition. The original vector renderer uses its existing LNT drawing as a TH compatibility fallback.

## Motion and display

- Drawing cadence is 15 fps. Geometry, gaze and automatic blink selection use the same sampled clock. Speech samples the current audible output clock independently.
- Face transitions take 600 ms by default, nine animation frames. Closed-lid transfer, eased travel and retargeting preserve one visible feature per eye or mouth group.
- Blinks take 400 ms, including a 133.3 ms closed hold. Closure remains visible at every 15 fps sampling phase.
- Silence, MBP lip closure and interruption can close a mouth immediately between scheduled paints.
- Faces 20 and 40 previously had almost invisible speech mouths. Their speaking master width now has an eight-unit minimum; their exact resting drawings and anchors are retained.
- An expression's requested hold begins after its entrance animation. Queue waiting no longer consumes the hold. Actual policy/renderer tests show a 400 ms request fully visible for 400 ms immediately, and 450 ms when queued because of frame alignment. A newer request or interruption can still replace it.
- The transition inspector's From/To controls now play the selected pair deliberately. Frame stepping advances 66.7 ms. Face buttons and Next retain continuous retargeting.

Browser review covered neutral TH/LNT, the complete mouth strip, a stepped annoyed-to-sad transition and the automatic face tour. Both source families were also inspected directly. The new consonants are clean at normal display size, and the stepped transition has no duplicate eye outlines. The existing mouthless faces 12 and 35 remain intentional; the conversation policy selects a related speaking variation while audio is audible.

## Verification

Independent identity checks pass for all 40 faces, 80 eyes, 120 exact canonical drawing paths and all 1,560 directed transition endpoints. Original canonical source bytes are unchanged. Production and studio renderer files are identical.

Renderer tests pass for all 40 faces, 1,600 pairs including unchanged selections, 20,920 sampled states and 120 rapid retargets. Targeted checks cover readable speech on faces 20/40, interpolation through their transitions and exact resting restoration. Replacement-sheet tests verify the selected image and single application of its scale. Timing tests verify 15 actual paints per 60 RAF callbacks, 469 blink phases and unquantized audio sampling.

The independent full preview suite passes with no failures. It covers 1,560 distinct directed pairs during both quiet and speech, 43,840 states, 160 interruptions, 228 replacement-sheet draw checks, 360 paused/inactive/stopped mouth states and 14 asynchronous cancellation races. At both 60 Hz and 120 Hz display callbacks, silent and constant-voice fixtures each produced exactly 60 actual canvas paints in four seconds, evenly spaced at 66.7 ms. The earlier extra-paint failure was fixed by sampling automatic blink overrides on the same frame clock.

Forty-three targeted Python tests pass across artwork integration, lip cues, streaming synthesis behavior and expression controls. JavaScript checks pass for packet playback, output-clock sampling, interruption, app handlers and delivery cues. The expression policy passes 38,359 assertions in 16 scenarios. Full independent preview measurements are recorded in `motion_checks_v3.json`; the package requires its current passing counterpart, `motion_checks.json`.

## Model control

The model guide at `brain/duplex/FACE_CONTROL.md` lists all 21 preset names, valid variants and holds covering 40 source faces. Models select expressions; the renderer owns transitions, blinking and speech cels. No per-frame or per-word tool calls are needed.

Sixteen fresh Luna low/default requests exercised switching, corrections, explicit variations, natural conversation and invalid selections. Fourteen strict model decisions passed. Two unwanted attempts were rejected by the runtime, so all 16 expected display outcomes were preserved. No case sent multiple expression calls or attempted to control individual frames. These trials are separate from the earlier complete 40-face sweeps. The later hold clarification in the prompt and tool description was not part of those 16 trials; the changed hold behavior was tested directly in the real policy and renderer.

## Limits

The new drawings are stylized articulation shapes. Frame and geometry checks do not replace a person's judgement of animation quality. Fresh ElevenLabs MIST synthesis remains blocked by the previously verified payment issue. This pass tested rendering, saved-audio infrastructure and controlled output clocks; it does not certify fresh audible latency or phone lip-sync.

The downloadable ZIP includes current artwork, metadata, viewers, saved audio and model-facing guidance. The original sheets remain for the still-active poses and provenance; their rejected FV/LNT/TH cells are not selected by the current atlas.
