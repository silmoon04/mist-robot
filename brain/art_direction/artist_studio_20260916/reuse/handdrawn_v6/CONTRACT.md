# MIST activity animation requirements

On 2026-09-24 the user chose to keep MIST's original eye style and retain the new hand-drawn activity animations. This replaces the earlier eye redesign direction.

- Keep all forty original face IDs, eye contours, left/right differences, blink drawings, blink orientation fixes and expression transitions.
- Use the nine generated activity symbols beside or above the original face: coding, reading, writing, email, searching, planning, calculating, connecting and checking.
- Keep each face's existing speaking-mouth family and audio-clock timing.
- Make room for symbols by moving/scaling the complete face uniformly, with no independent stretching or rearrangement of its features.
- Play four entrance cels, loop four working cels until the operation ends, then play four exit cels. Playback is 15 fps with deliberate frame holds.
- Match completion and cancellation by ownership token. An old completion must not clear a newer activity.
- Show actual work, not invented success. The connecting symbol stays unjoined and checking uses a scan mark while waiting for results.
- The active manifest contains nine symbol assets and 108 transparent PNG cels. New eye designs are inactive studies in eye_study_manifest.json and must not load in the preview or voice page.
- Keep the preview simple: moving grid, pause, step, blink, replay entrances, exit, voice recording and separate-layer inspection. Downloads include the active symbols, original face dependencies and exact ImageGen prompts.

Original generation instructions are preserved in CONTRACT.eye_study.md for provenance. They do not govern the current face design.
