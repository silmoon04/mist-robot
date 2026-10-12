# Emotion-specific speech mouths

Reviewed 23 September 2026. This revision addresses serious faces looking happy when they speak.

Five new ImageGen sheets provide 40 distinct drawings: eight each for anger, sadness, indifference, worry and skepticism. Each contains `rest`, `release`, `small_AA`, `AA`, `EH`, `EE`, `LNT` and `wide_close`. The existing happy set remains. Rounded O sounds, lip closures and clean shared consonants are reused where they do not introduce smiling corners. Original generated PNG bytes are preserved.

The 40 faces now have explicit assignments based on visual review, not filename guesses: four angry, three sad, sixteen flat, seven happy, five worried and five skeptical. Face 29 has a sad filename but serves a smug/embarrassed expression; it uses the restrained skeptical set. Every canonical silent face stays exact, including its original mouth or absence of a mouth.

## Visual review

The primary reviewer inspected all five source sheets and the browser comparison. The AA, EE and LNT comparisons show clear differences from the happy bowl. Angry AA and sad AA were also inspected on their complete faces at the actual display scale. Registration, relative aperture size and the absence of tongue-like tabs were checked.

- Angry mouths have a tense downturned rest and blunt, level apertures. Anger still depends partly on the eyes; the open vowels are intentionally restrained.
- Sad vowels retain downturned corners through wide and closing shapes.
- Indifferent mouths keep level corners. Wide close is shallow but is not thinner than the generated rest capsule.
- Worried mouths use a tense rest and taller openings. Their broad consonants rely on worried eyes for context.
- Skeptical mouths retain a consistent right-end-higher slant.

The new Mouth families dialog compares the same pose across all six styles, with animation and frame stepping. The 40-face grid and individual inspectors use the production renderer and the same assignment map. The studio and live voice page loaded without browser console warnings or errors during this review.

## Runtime checks

The source tests pass: four v4 tests and three retained v3 tests. They check all 40 assignments, source hashes, unchanged earlier artwork, shared-pose reuse, distinct custom crops, scale metadata and populated single-component shapes without clipping.

The final renderer family suite passes 40 mapping checks, 360 pose checks, 40 exact canonical rests and 67 frame-phase cases for a sustained vowel. A family change prefers a real cue boundary or closure. It can switch at a quiet amplitude after 150 ms, or switches during the same vowel on the first 15 fps tick at or after 400 ms. The tested upper bound is 466.7 ms. No fake closure, duplicate mouth or changed audio time is introduced. A forced change can still be visible during a long vowel.

Renderer checks pass 1,600 expression pairs, 20,920 transition samples and 120 rapid retargets. The separate cadence suite observes 15 actual paints from 60 animation callbacks and verifies that speech time remains unquantized. Silence and interruption close the mouth immediately. Independent identity checks preserve 40 faces, 80 eyes, 120 exact canvas paths and all 1,560 directed transition endpoints.

The independent final motion suite also passes all 1,560 directed transitions quietly and under AA, EE and LNT, totaling 87,680 sampled states and 4,680 held-cue handoffs. It checks 320 rapid interruptions, all 40 reduced-motion expressions, 640 manual pose selections, 520 speech-cue selections, 96 comparison-view poses, 360 paused-mouth states and 14 asynchronous cancellation cases. Source pixels were decoded from the actual PNGs. There were no failures or warnings. These are computational checks, not fresh provider or physical-audio measurements.

## Evidence and limits

Current source hashes, checks and per-face decisions are recorded in `atlas.json`, `validation.json`, `mouth_family_map_v4.json`, `emotion_mapping_v4_review.json`, `identity_v4.json` and the packaged runtime reports. `visual_quality_checks.json` contains measurements and historical source notes; those measurements are not a subjective quality score.

The active atlas contains 164 selected pose entries, including shared drawings and aliases. It selects 124 distinct source crops; these are not 164 new drawings. The five new sheets account for 40 new drawings.

The runtime uses the existing expression tool. Models request a face once; the renderer chooses its mouth family and drives articulation from playback. This revision does not require a second model call, a new expression API or per-frame agent instructions. The guide is `brain/duplex/FACE_CONTROL.md`.

These checks establish artwork routing, identity, geometry and playback-clock behavior. They do not establish perfect phoneme recognition or subjective live voice quality. The saved voice recordings remain available; no fresh ElevenLabs synthesis was attempted in this revision because of the previously recorded payment block.
