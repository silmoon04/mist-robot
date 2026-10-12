# Speaking mouth emotion

User requirement: the shared rest, small_AA, AA, EH, EE, LNT and wide_close drawings make serious faces look happy. Provide appropriate counterparts for anger, sadness, indifference and other expressions that need their own treatment.

Scope and checks:

- Keep the original 40 resting faces and the existing happy speech set. Generate eight coherent drawings for each of five families: angry, sad, flat, worried and skeptical. Include release as the eighth drawing to avoid a happy opening between sounds.
- Keep continuous cyan contours without the previously rejected tongue-like tabs, upper notches, teeth or interior details. Preserve original ImageGen PNG bytes.
- Share rounded O sounds, lip closures and the clean consonants where they fit. The old SMILE study cue must not select a happy drawing for a negative or flat family.
- Map every source face explicitly, using its actual visual identity rather than its filename. The renderer and inspectors must use the same map.
- During speech, changing emotion must keep the current audio time, one visible mouth and stable registration. Preserve 15 fps drawing, immediate silence, interruption and exact resting identity.
- Inspect the same pose across families and on complete faces. Check articulation, emotion and family switches separately. Publish the updated viewer and downloadable pack only after source and runtime checks pass.

The new mouth artwork conveys expression; it does not infer the user's emotion. Language models continue to request named faces through the existing tool, while the renderer chooses the matching mouth family. Fresh final-voice verification remains limited by the previously reported ElevenLabs billing block.
