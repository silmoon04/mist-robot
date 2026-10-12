# Reference board

The board is a wall of source artwork with compact credit and one acting note underneath. Details, bibliography and our MIST inferences sit in an inspector rather than competing with the pictures.

Palette: pale grey `#eeeeef`, off-white controls `#fafafa`, dark grey text `#202326`, secondary grey `#666b70`, restrained MIST green `#207d73`. Segoe UI Variable Text / Segoe UI provide plain legibility. The small original MIST mark identifies the project without making the real artists’ work look like generated MIST assets.

The wall uses a measured masonry grid: four columns at common desktop widths, three below 1200 px, two on phones. A ResizeObserver fits the rows to each natural-height reference so the curated order reads across the first row. Images keep their natural proportions, with a height cap. Actual direct GIFs/images are preferred for previews; video sources are explicit click-to-load controls. No guessed thumbnail URL or generated imitation is used.

Data: `board/catalog.json` accepts an array or `{entries: [...]}` using BRIEF.md. Optional `featured: true` floats starting references to the top. Optional `displayTitle` shortens the card header. Optional `previewIndex` chooses a verified media entry from the original media array and opens that same media in the inspector. Optional `indie: true` or an `indie` tag enables the indie filter. Optional media `focus` sets object-position; `crop: "contain"` avoids cutting content; `portrait: true` uses portrait limits. A verified media URL is required to display it. Every card has an original source link; each observation displays visual-analysis or creator-statement provenance.

Notes use the new `mist.game-face-references.v1` localStorage key. Existing animation reviews are untouched. JSON export/import schema is `mist-game-face-review` version 1. Markdown downloads contain saved or annotated entries, credits and source links. Storage failure is reported in the inspector so notes can be exported.

GIF pause draws the currently decoded frame to an on-screen canvas and hides the GIF. It does not read pixels, save or download remote source assets. Reduced motion starts with GIF motion off. Videos never load before a user selects the source. YouTube uses its privacy-enhanced embed host; Vimeo preserves a supplied private `h` query. Unknown video-page sources open at the original URL. Closing the inspector pauses and clears native video, or removes the active iframe. Native dialog supports focus containment and Escape; left/right keys move references outside input controls.

Publish the four UI files, `catalog.json`, and root-provided `research.md` together under `/game-face-references/`. Relative nav links lead to the MIST root and existing `/acting-animations/` route.
