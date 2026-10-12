# MIST motion correction

User rejected acting_animations_v2 because many middle frames look bad, then asked for a result closer to the original MIST style. Existing technical pass reports are not visual acceptance.

## Visual invariants

Use the original MIST faces and parts in ../faces, ../parts and ../runtime/app_data.js as the visual authority: mint cyan #5eeadd, rounded consistent strokes, open-ring C eyes, hooks and simple closed arcs, compact bar/smile/bowl mouths. No pupils, filled eye disks, detached eyebrows, bell-shaped eyes, anatomical teeth or tongue. Preserve the 18 acting concepts and original review IDs, while unifying their MIST identity.

## Motion

- Every acting clip has 12 composed poses for one action, with authored exposure holds on a 15fps timebase. Stop forcing a blink into the first six poses.
- Independent eye-family blink clips can be triggered separately. Blinks must preserve curvature direction and eye identity, with real drawn lid closure instead of scaling or rotating the eye.
- Keep left eye, right eye and mouth independent on one shared 512x320 rig. Mouth changes never move the eyes. Do not center the entire face on its changing mouth.
- Eye centers and mouth attachment points are common across all faces. Transitions cannot teleport between differently padded canvases.
- Use built-in ImageGen for new raster components and preserve selected source images. Existing original MIST raster/vector source components may be mechanically extracted and assembled without changing their silhouettes. Do not substitute a full-face sheet of loosely related key poses for continuous inbetweens.
- Reuse component drawings and author small rigid gaze/tilt movements. Report composed frames honestly; do not claim every composed pose was separately generated.

## Acceptance

Inspect every intermediate pose against its immediate neighbours. Reject a changed eye model, detached new feature, curved-lid inversion, unrelated mouth topology or large unexplained shift. Compare intended-speed and slow playback with the old version. Pixel counts, unique hashes and correct layer extraction are necessary technical checks, not proof of natural motion.

Keep previous assets as history. Retain review selections, notes, per-layer inspection, full grid and downloads. Publish the corrected gallery after motion review, preserving the existing voice application.
