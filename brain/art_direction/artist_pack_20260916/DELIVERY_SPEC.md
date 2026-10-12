# Files and registration

Supply the editable layered source in the artist's normal app: Krita, Photoshop, Clip Studio, Procreate, Aseprite or a vector editor are acceptable. Do not switch software just for this pack. Include neutral SVG exports if using vector art, or full-canvas transparent PNGs if painting. An editable source plus exported components is required; a flattened GIF alone is not enough.

Master canvas: 1600 x 1024 pixels, representing logical coordinates 100 x 64. The actual phone is landscape and has a wider display; fit the face art without stretching, with surrounding empty space as needed. This canvas follows the current renderer, not the full phone screenshot dimensions. Validate at phone size before increasing detail.

Anchors in logical coordinates: eye_L (28, 29.4), eye_R (72, 29.4), mouth (50, 49.5). In master pixels: (448, 470.4), (1152, 470.4), (800, 792). Left and right mean the VIEWER'S left and right. These are placement guides for the redesign, not exact bounds of every existing reference face. Keep artwork inside logical x 5.5 to 94.5 and y 5.5 to 58.5, leaving room for gaze and glow.

Every component export keeps the full canvas dimensions and registration. Do not trim transparent pixels or center each cropped part independently. Use eye_L, eye_R, mouth, accents and GUIDES layer names; keep each eye independently editable. GUIDE and REFERENCE layers are hidden in exported art. Separate lighting/glow from the solid silhouette. Use sRGB. Avoid baked black backgrounds in component PNGs; backgrounds are fine on review sheets.

Names: E01_available_eye_L.png, E01_available_eye_R.png, M01_rest.png. Equivalent SVG names are fine. Blink and accent pairs follow B01_eye_L / B01_eye_R and A01_eye_L / A01_eye_R. Redraws R01 to R06 keep exactly the base pose anchors. Include a source file, a contact sheet and the updated drawing_checklist.csv with notes. In a layered source, pose folders can contain both eye layers and the mouth layer, but keep a shared component library to avoid diverging duplicates.

The templates folder contains 38 blank SVG scaffolds with registration guides and empty part groups. They are NOT completed art. Use them directly in a vector editor or import one as a guide into a painting app. Their GUIDES group is visible intentionally and must be hidden before export. For eye-pair items, leave mouth empty. For mouth items, leave both eyes empty.

animation_clips.csv lists the 15 proposed review clips, their exact exposure counts at 24 fps, durations and reused components. Their 560 exposures reuse the component library; do not interpret the clip sheet as a request for another 560 drawings.

Open index.html after extracting the complete ZIP; it reads only local bundled scripts and assets. No server, account, microphone or API key is needed. Use browser Print to PDF for a review copy. The contact sheet in references/ALL_40_CONTACT_SHEET.svg can also be printed or opened in a vector editor.

## Acceptance checks

- All component IDs exist once, with the matching name and description in the checklist.
- Eye pair entries have separate left and right layers. No mandatory mirroring: slight asymmetry is welcome when intentional.
- Transparent exports share one canvas and anchors. Moving between poses does not jump because of cropping.
- Line weight reads at actual phone size, without relying on glow to hide broken joins.
- Closed blinks retain a clean line and volume. The mouth never collides with either eye at gaze extremes.
- Talking preserves the eye expression. On silence, the mouth returns to the emotional resting shape rather than always smiling.
- Neutral, listening and thinking remain visibly distinct with the sound off.
- A scene can remain still. Optional line variation does not look like display noise.

## Integration responsibilities

Artist: drawing design, component registration, style sheet, blink/gesture keys and layered review clips. Developer: import the assets, choose drawing or rig interpolation, map runtime states, align mouth timing to audio, implement alternate-contour playback, handle interruption and reduced motion, and test on the physical phone.

Changing hand-painted SVG/PNG files will not automatically rewrite the current polygon renderer. Vector shapes may need conversion and point correspondence; raster cels need a drawing-swap renderer. The pilot should decide that path before the artist draws 32 more components. No exact node-count requirement is imposed on the artist for unrelated poses. Compatible contours can be rigged; incompatible contours should use a blink bridge or intentional drawn cut.
