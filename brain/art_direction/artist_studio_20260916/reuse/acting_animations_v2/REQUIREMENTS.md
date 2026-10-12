# Acting animation pass

User request: make full 12-frame animations for all current acting studies, separating eyes, mouths and transitions, using subagent ImageGen, and show all of them moving.

Scope: all 18 examples from acting_studies_v1 (six inspiration groups), preserving their labels and acting intent. Keep the 54 reference poses and existing saved reviews intact. Publish the animated review on the existing GitHub Pages site after validation.

- Generate 18 new raster sprite sheets with the built-in ImageGen tool, one per example, each with exactly 12 full-face drawings in a 4-column, 3-row grid.
- Cyan MIST features on genuine transparent backgrounds. Preserve each reference's eye silhouette and emotional mouth shape. No phone frame, labels, cell borders, unrelated props, or simulated transparency checkerboard.
- Each sheet uses fixed registration: frame cells have the same face scale and position, eyes above the mouth with a clear separation gap, left and right eyes not touching.
- Animation phases: frame 0 expression at rest; 1 anticipate a blink; 2 partially closed; 3 fully closed; 4 opening; 5 eyes open; 6-8 character-specific acting beat; 9-11 return smoothly toward frame 0. No rotated-eye shortcut, rigid vertical scaling or repeated key-pose padding.
- Compile immutable generated sheets into rectangular source crops and independent left-eye, right-eye and mouth layers. No generated artwork redraws in code. Store source hashes and crop metadata.
- Default playback uses 15 fps for the 12 drawings, with an intentional rest between repetitions. Provide speed, pause and single-frame controls plus layer isolation.
- Reusable 12-step face transitions use source blink closing and target blink opening frames with a closed-eye handoff. Keep mouth changes independent. Test every directed pair among the 18 examples.
- Show all 18 animations in a gallery; provide a larger inspector, layer toggle, frame strip, transitions demo and downloadable asset pack. Preserve selection and note IDs used by the previous review page.
- Validate grid extraction, feature separation, frame counts, registration, loop seams, layer reconstruction, all transition pairs and browser playback. Inspect outputs visually, with independent reviewers.
- These are review animations. Do not claim live voice synchronization or replace deployed voice assets in this pass.

Visual direction: existing MIST cyan on dark stages, quiet cream review controls, compact labels. Animation and layer inspection are the content; no hero copy or decorative marketing sections.
