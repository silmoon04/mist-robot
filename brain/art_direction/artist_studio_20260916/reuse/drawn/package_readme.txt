MIST drawn animation pack

This pack includes the current 40-face viewer, expression transitions, saved voice
samples, the previous procedural preview, source sheets, and validation reports.

Extract the ZIP. Open a terminal in the extracted folder and run:
python -m http.server 8795
Then open http://127.0.0.1:8795/drawn/
Transitions: http://127.0.0.1:8795/drawn/transitions.html
Use a local HTTP server because the viewer fetches data and audio files.
Any static HTTP server works. The in-page download link belongs to the hosted studio;
the ZIP does not contain itself.

The active atlas has 14 reusable motion assets and 164 animation entries.
Those entries select 124 distinct source crops across 11 source sheets.
Repeated pose aliases and shared drawings do not count as new artwork. A source crop
is identified by its sheet path and x, y, width and height, not by its pose name.
Six emotion families and a neutral shared base reuse rounded vowels, lip closures
and clean consonants. Five new families provide the seven requested poses plus a
release pose each: angry, sad, flat, worried and skeptical. The existing happy set stays.
The new ImageGen drawings are combined with exact
original MIST resting faces. This is a hybrid renderer, not 40 independently drawn
face animations. Original mode and the previous grid use the original vector artwork.
The current atlas targets 15 fps. FV and TH use the shared clean v3 consonant
drawings. Happy and neutral LNT poses also use v3; each of the five new emotion
families has its own v4 LNT drawing. Other poses use reviewed v2 and v4 sheets. Rejected consonant
positions remain visible in those source sheets but are not selected by the atlas.
Per-frame file, sha256 and sourceScale metadata are preserved for replacement cels.
PNG bytes are unchanged. Background removal and sprite registration happen at display time.
Shared source sheets are packaged once. Earlier sheets are retained under legacy/v1;
its sheet_index.json identifies any files shared with the active atlas.

The 6 saved recordings demonstrate audio timing. Their alignment metadata is in
drawn/audio/samples.json. Energy-only playback is not phoneme-aligned lip-sync.
Fresh aligned voice samples could not be verified because a failed provider payment
blocked generation. This pack makes no new API calls and contains no API credentials.

drawn/validation.json checks source integrity and populated cells.
drawn/motion_checks.json checks grid transforms, bounds and blink timing.
To repeat those motion checks with Node.js: node drawn/motion_checks.cjs
Identity, visual-quality and renderer reports are included with their own limits.
integration/mouth_family_checks.json records the current family-routing checks.
The test sources in integration/tests preserve their original repository paths;
run them from the full source workspace, not directly from this viewer pack.
Earlier reports are retained as comparisons; they do not certify the current viewer.
Archived v4 reports and reviews are under history/v4. They retain the hashes of that
earlier renderer and are not required to match the current blink-orientation fix.
Available v5 refinement reports and review notes are under refinement_v5.
The unversioned motion, identity, renderer and mouth-family checks are the current
packaging requirements; their renderer and atlas hashes are checked before building.
These checks do not establish subjective animation quality or fresh live lip-sync.
package_manifest.json lists SHA-256 hashes for every payload file.
