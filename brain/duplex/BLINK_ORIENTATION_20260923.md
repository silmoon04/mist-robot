# Blink direction

User report: some blinking animations look unnatural because they are rotated.

The browser reproduction is face 09, happy 03. Pause the transition viewer, select that face, click Blink and advance to the closed frame. Its circular eyes have closed axes of approximately +33 and -32 degrees. The source closed drawing is nearly level; the open-glyph fit contributes approximately 31 degrees.

The reproducible baseline is `node brain/harness/test_blink_orientation.cjs --face=09`. It fails for both eyes on renderer `70d73a3b12f05e91e4f0c9a403012ba71d5ee91ddbc0fb9bb5d78aad7d924d0a`. The broader diagnostic flags candidates for review, including some intentional inverted arcs and compensated rotations; its candidate count is not a count of confirmed defects.

Acceptance criteria:

- Preserve every canonical resting face, source PNG and emotion-specific speaking mouth.
- Keep round-eye closures close to the face's eye line. The orientation of the gap is not the orientation of the eyelid.
- Preserve gentle angry or tired lid slopes. Retain the concavity and endpoint direction of eyes that are already closed arcs.
- Avoid turning the entire open eye to reach the closing plane. Keep the early open contour registered, then close along the intended plane and use the registered drawn closing cels when the aperture is narrow.
- During reopening, leave no cut-off fragments near a circular gap. Retain rounded stroke ends and the lower curve. A rectangular mask that produces flat bottom edges or isolated cap fragments is not an acceptable fix.
- Use the same closing direction for ordinary blinks, inspector-held cels and expression-transition bridges. Keep lid centers and widths stable through the change.
- Keep 15 fps animation, exact silent identity, immediate interruption and independent audio timing.
- Verify actual transformed source-ink angles as well as the renderer's numeric configuration. Visually inspect round, hook, loop and already-closed eyes after the fix.

Per-eye review targets are in `blink_orientation_review_v5.json` under the drawn viewer directory. They are starting points for visual judgment, not anatomical measurements. The original v4 renderer is retained there as `drawn_face_renderer_v4.js` for comparison.
