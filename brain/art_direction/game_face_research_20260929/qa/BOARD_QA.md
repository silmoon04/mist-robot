# Board QA

Tested the real curated 35-entry catalog at `http://127.0.0.1:9050/`, alongside a disposable branch-data preview at port 9056. These checks concern delivery and interaction, not proof that all reference animation has been continuously inspected.

- Desktop first row: Later Alligator, Slime Rancher, Dicey Dungeons and OMORI actual source GIFs decoded at 800 / 853 / 1280 / 640 pixels. No media-error overlays in the inspected board state.
- Source and named artist credits are visible in the inspector. Visual observations and creator statements carry separate labels and source links. MIST ideas appear under an inference label.
- The Start here filter returns 24 of 35. Searching Tina Nawrocki returns three Cuphead studies; applying the motion-only filter narrows those still-only references to zero.
- GIF pause displays frozen current-frame canvases (10 loaded GIFs in the real board check; inspector freezing checked on the earlier preview). Play reveals the original GIFs again.
- Save and typed why notes survive reload. Closing an inspector reapplies the saved-only filter.
- JSON and Markdown download controls created actual files in the user's Downloads directory. JSON read-back confirmed schema `mist-game-face-review`, version 1, the correct Later Alligator ID and typed QA note. The browser download-event listener timed out although the file was saved; this is a tool event limitation, not an export failure. The local test save/note was cleared afterwards.
- Native dialogs close with the close control and restore the opening control's focus. Detail previous/next controls honor the current filtered set.
- A Vimeo source creates exactly one click-triggered iframe; closing removes it. YouTube/Vimeo/native video are absent from the untouched board. Vimeo hash preservation was repaired after parent audit; the fixed embed constructs the same supplied `h` parameter.
- At 390 × 844: body scroll width 375 (the remaining 15 px is the vertical scrollbar), two grid columns of 167 px, no horizontal overflow. Inspector width 374, internal scroll width 357, media width 333. Viewport override was reset after testing.
- Malformed `#%` fragments no longer make a valid catalog appear to have failed.

Independent logic audit found and repaired imported array records that erased notes, inherited-property IDs, stale storage-success messaging after quota failures, malformed fragment decoding, and detached native video playback. Seven regression checks pass in `review_state.test.cjs` for persistence, array rejection, inherited IDs, schema rejection without mutation, exportable notes on storage failure, JSON/Markdown roundtrip and bounded notes.

Screenshots: `board-real-desktop.png`, `board-real-mobile.png`, `board-real-inspector-mobile.png`. They are local UI evidence, not animation source assets. Reduced-motion startup is implemented via the browser media query; no operating-system preference was changed for this test.
