# MIST face studies — delivered 29 September 2026

Review: https://silmoon04.github.io/mist/game-face-studies/

Download: https://silmoon04.github.io/mist/game-face-studies/faces-pack.zip

The user's selected scope was five faces for every study on the game reference board: 35 studies, 175 static face concepts. Seven parallel generation agents used the built-in ImageGen tool. Each selected original sheet contains attentive, considering, skeptical, amused and concerned poses; the sixth grid cell is blank. The page presents the five faces individually by clipping the original PNG with CSS.

The review page supports per-face saves and notes, search, category filtering, a saved filter, an enlarged inspector, original-sheet downloads and JSON/Markdown note exports. Saves are browser-local; exports let the user share their choices. Prompt files and research links preserve the origin of each study without implying the referenced game artists made these generated faces.

## Verification

- Independent visual reviews covered all 35 current selected sheets and all 175 poses. Both reports passed the selected files with no current blocking defects. The earlier Night in the Woods speck was resolved through a fresh ImageGen version.
- Asset checks found all selected sheets at 1536 by 1024, occupied poses inside their cell bounds, no cyan in the unused sixth cell, and no current flagged sheets.
- The review-state suite passed all 20 tests. Browser checks covered rendering, independent saves/notes, reload persistence, saved filtering, keyboard focus, real note downloads and a 390-pixel phone viewport.
- Public verification matched all 97 receipted files and the complete 33.6 MB ZIP against the local release. `qa/public-verification.json` records `zipMatches: true`.

Published to `silmoon04/mist`, Pages `main:/docs`, in commit `761f307d2e8b9ddff6899a20af6d2e8f836cbb69`. The GitHub Pages build reported `built` for that commit. Only `docs/game-face-studies/` was added; the live voice and existing review routes were not changed.

## Limits and next use

These are static concept studies, not animation frames, separated eyes/mouths, or a replacement for the live MIST face system. The download contains 35 complete raster sheets rather than 175 individually extracted PNGs. Some sheets deliberately retain the shared MIST C-eye vocabulary and faint generated background variation. Process-only references inform an authored pose approach rather than a claimed source facial style. Prompts include named attempts that were discarded; the catalog identifies the selected sheet and prompt.

Use the user's saved faces and exported reasons to choose the directions worth turning into consistent, separated animation assets. No new animation or live-face replacement was authorized in this pass.
