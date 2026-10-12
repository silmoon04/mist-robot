# Simon's Cat animation source review

Three original ImageGen PNG sheets: `notice`, `waiting`, `clarify`, each 1536 by 1024 RGBA and a 4-column by 3-row sequence of twelve drawings.

Reviewed actual RGBA composited onto #101c20. The ImageGen raw RGB preview misleadingly displays cyan fog under zero-alpha pixels; diagnostic JPGs show the rendered result. Final sheets have clear negative space between the two eyes and below the eyes. Frame 3 in every sheet is fully closed curved eyelids without pupil dots. The blink now removes the upper outline as the lid lowers, rather than drawing an extra line through a complete round eye.

Notice uses a directional glance to the right and returns; a gaze repair removed the abrupt leftward jump. Waiting uses a closed smiling mouth that settles to a flat closed line while both pupils glance upward; the final repair removed the pupil circling. Clarify uses one lowered eyelid and a slightly angled dash mouth, then returns toward rest. These are acting animations, not phoneme mouth libraries.

All final PNGs are byte-for-byte copies of tool outputs. Only diagnostic previews were alpha-composited; no generated feature was redrawn, recolored or reconstructed in code. Prompts and hashes are recorded next to each source receipt. Horizontal and vertical cell registration still need the shared compiler's extraction checks because the model does not follow requested percentage anchors precisely.
