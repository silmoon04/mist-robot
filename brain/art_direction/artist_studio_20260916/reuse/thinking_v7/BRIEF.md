# Thinking studies

Make a separate preview of improved thinking animations inspired by EMO's activity sequences and Lordicon's entrance/action/loop distinctions. Keep the current approved activity page and live phone default untouched. MIST retains its original forty face shapes, blinks, speaking-mouth families and transitions.

The improvement is choreography: notice the task, begin it, work in short bursts, pause to consider, resume. Use quiet gaze cues and original expression changes. Avoid a constant spinner, frantic bouncing, opening the mouth to show thought, or implying that work succeeded. The animation loops until explicitly stopped. Speech uses the actual audio clock and interrupts any attention-grabbing movement without muting playback.

Six preview studies: reading a book/page, typing code, drafting a note, sorting ideas, searching/inspecting, quiet pondering. The first four get original ImageGen prop sheets. Searching and pondering can reuse existing generated searching/planning cels with better staging and timing.

## New prop sheets

IDs: book, terminal, note, cards. Each sheet exactly 4 columns x 4 rows, 16 isolated drawings. Reading order: 0-3 entrance; 4-11 eight loop action poses; 12-15 exit. Transparent background, turquoise linework with rounded hand-drawn edges consistent with ../handdrawn_v6/source/reading.png and writing.png. No faces, eyes, mouths, bodies, hands, labels, glyph text, cell borders or decorative sparkles. Stable prop silhouette/placement, intentional progressive inner changes; frame 11 should settle naturally into frame 4. Keep the objects lightweight and readable when small. All cells must have visible ink. Prop movement should explain the activity, not just pulse opacity.

Save untouched ImageGen originals as source/<id>.png, exact prompts prompts/<id>.txt, source/<id>.json with grid 4x4 and dimensions. Root handles slicing/registration, not redrawing. New eye art is prohibited.

## Player contract

Root publishes manifest.json {version:7,fps:15,assets:{[id]:{type:'activity',frames:[{file:'frames/<id>/00.png',pose:'enter_0'...}]}},studies:[{id,label,asset,faceId,note}]}. New files are 256-square transparent registered cels. All frames of a prop share scale and alignment. Existing assets searching/planning are copied mechanically to frames/ and retain 12 frames; validate according to actual frame count.

The preview should show six moving studies, compare the previous icon-only motion where practical, pause/step, replay entrance, exit, individual study focus, slow motion, saved MIST voice, and concise beat labels such as notice/read/pause/resume. Show the six as real motion, not a generated still. Keep browser rendering 15 fps, audio unquantized. Provide deterministic pure choreography sampling for independent tests. Agent root owns the manifest, extraction, packaging and browser review. No live backend changes needed for a concept preview.
