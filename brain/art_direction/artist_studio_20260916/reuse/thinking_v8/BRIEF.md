# Thinking revision

Keep the original MIST eye shapes, blinks and speech mouths. The user likes coding,
drafting and sorting, but wants quicker action and more actual drawings. Reading
must keep a coherent viewing direction, page turn and text placement. Searching
must be clearly separated from the eyes. Quiet thought needs smoother motion and
the runtime must vary between at least three appropriate original faces.

Eight studies: reading/book, coding/terminal, writing/note, sorting/cards,
searching/searching, pondering/planning, connecting/connecting, checking/checking.
Every new sprite sheet is 6 columns by 4 rows, 24 drawings: 4 entrance, 16 active
loop, 4 exit. Save untouched RGBA originals in source and exact prompts in prompts.
Use common registration and uniform scale, with 256px transparent exported cels.
No generated eyes or mouths. Original shapes must remain recognizable.

The player stays at 15 fps. Coding, drafting and sorting should complete an active
phrase in about 2.2-2.8 seconds rather than 4.2 seconds, with brief readable pauses.
Reading may be slightly slower. A working sequence does not imply successful
completion. Connection and checking loops must not contain success ticks.

Three original face variants rotate on activity starts and at slow natural phrase
boundaries during long waits. Explicit agent/user expression choices override
rotation. Speech keeps its own unquantized audio clock and quiets activity motion.
Do not randomly change faces every frame, switch during speech, or let a stale
tool completion clear a newer activity. A face selector must offer auto variation
as well as all forty explicit original faces.

The new preview lives in thinking_v8. Keep v7 art for comparison. Runtime code,
asset checks, a moving grid, frame inspector, saved voice test, and downloadable
pack must agree on the actual manifest. Independent QA should check source art,
phase reachability, face preservation, speech, cancellation and prop placement.

## Corrections after the first contact sheets

The user rejected a book page that lands blank and suddenly regains text. Print
both sides of the turning sheet and preserve those marks through the turn.
Text may be occluded or edge-on; it must not appear on an already flat blank page.

The user also rejected checking poses repeated three times at each row and a scan
bracket that returns suddenly before disappearing. Sixteen work cels need actual
intermediate action positions. Different pixel noise does not make a new pose.
Use playback holds for pauses, not duplicate files to pad the drawing count.
Search and checking scans should remain visible throughout a continuous down/up
or left/right loop. Entrances and exits must show deliberate reveal/retraction.
Review every source sequence for these defects, including cards and planning.

Where repeated ImageGen redraws change a rigid object or miss its timing, reuse
the generated parts and animate their placement. Keep the unmodified source,
component crops, provenance and per-frame positions. Do not call those assembled
poses separate ImageGen drawings. Judge consecutive motion and the loop seam;
reusing an earlier position on a return path is expected.

Export 24 transparent frames per activity. Keep page and path bodies stable,
reveal writing along the pen's path, and let exit motion begin from the current
pose. Version changed images and scripts so a reload shows the reviewed assets.
