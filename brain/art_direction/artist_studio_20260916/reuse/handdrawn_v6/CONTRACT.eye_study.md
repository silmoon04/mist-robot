# MIST hand-drawn activity set

The user approved the eye styles in reference.png, including the focused hooks and filled upward-looking eyes. Keep their character; do not soften them into the old eye system.

Use built-in ImageGen and read its skill. Inspect reference.png first. All generated originals belong in source/. Save exact prompts under prompts/. No new paid API or CLI fallback.

## Generation contract

One sprite sheet per named asset. No labels, borders, grid lines, shadows, panels, mouths, other objects, or numerals in eye/icon sheets. Ask for transparent background. Use turquoise hand-drawn strokes matching the reference. Allow subtle organic contours, avoid flicker in size or weight. Keep equal cells and generous padding. Return original PNG dimensions and grid in source/<id>.json. Root will slice and register the drawings for runtime; do not independently process pixels.

Activity sheets: IDs coding, reading, writing, email, searching, planning, calculating, connecting, checking. Exactly 4 columns x 3 rows, 12 drawings of the activity symbol only. Row 1 is four entrance frames (small emerging to established); row 2 is four smoothly looping active frames (last naturally leads into first); row 3 is four exit frames (established to small disappearing). First and last must still have visible art so cells can be checked. The runtime finishes the fade. Activity symbols match their reference panel. No faces on these sheets. Checking loops mean inspection, not fabricated success; use scanning checklist lines, reserve ticks for confirmed results. Connecting loops must remain unjoined until completion.

Eye sheets: IDs eye_round, eye_hook, eye_half, eye_up, eye_arc. Exactly 4 columns x 2 rows, eight drawings of ONE isolated eye in fixed framing. Reading order: open, anticipation, half_closed, closed, opening_low, opening, gaze_left, gaze_right. Open is reference shape; closed must be a drawn lid with natural thickness, not squashed open eye. Keep closure plane approximately horizontal except hook's modest natural slant. eye_up is the filled eye glancing upward, including dark negative-space pupil from Planning. eye_hook is the asymmetric focused eyelid from Coding/Writing. eye_half is Calculating. eye_round is Reading files. eye_arc is the happy arc from Checking email. Runtime mirrors individual eyes where appropriate, never rotates closed lids from a fitted source angle.

## Runtime contract

Root generates manifest.json with {version:6,fps:15,assets:{[id]:{type:'eye'|'activity',frames:[{file:'frames/<id>/00.png',pose:'...'}]}},activities:[{id,label,eyes:[leftId,rightId],mouth:'neutral'|'smile',placement:'side'|'above'}]}. Frames are registered transparent square PNGs (256px). Same eye width anchor across all blink phases; never stretch each frame to its individual bounding box. Activity alignment preserves intended emergence.

Separate eyes, mouth, and activity layers. Preserve audio-clock-driven speaking mouth behavior and emotion mouth families from the existing renderer. 15 fps artwork with real audio clock. Activity entry -> loop until done -> exit; rapid changes and cancel must clear stale activity. Do not infer email/search completion from elapsed time. Avoid giant headings or copy in preview. Show all nine in a moving grid, pause/step/blink/replay entrances/exit, inspect separated cels, download pack.

Live integration should replace eyes with these assets, preserve forty expression IDs and speech mouth mapping, and expose explicit setActivity/clearActivity for agents. Use existing runtime as fallback until new assets load. Keep previous assets available.
