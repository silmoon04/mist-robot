# MIST face board UI checks

The board uses the catalog supplied by the generation and assembly workflow. No fixture art was created or shown as generated output.

## Implementation

- Every included study retains five pose tiles in one row. Search and saved filters select matching poses, show their study rows, and outline only matching poses. The count reports matching faces and included studies.
- Each face is a CSS background crop of the same original sheet: 300% by 200%, with horizontal positions 0%, 50%, 100% and vertical positions 0%, 100%. Its aspect ratio is `(sheet width / 3) / (sheet height / 2)`. The blank sixth cell is never displayed.
- Original image bytes are not edited. No canvas, SVG or programmatic face drawing is used.
- Artwork loads when its tile approaches the viewport. The five crops share one image request and status promise for their original sheet.
- Per-pose review records use `mist.generated-game-faces.20260929.v1`, separate from the source-reference board. Notes save on input. JSON import/export and a Markdown shortlist are available.
- The inspector links the original sheet, sheet download, exact prompt, source-study board entry and original inspiration. Both the board and inspector identify the work as static ImageGen adaptations, not ready animations or original artists' work.
- Desktop rows use five equal columns. Phone rows scroll horizontally inside the page. The native dialog provides protected keyboard focus, Escape closes it, arrow keys navigate faces when a text field is not focused, and closing restores the opener.

## Completed checks

- `node --check board/app.js`: passed.
- `node --test qa/review-state.test.js`: 20 passed, 0 failed.
- State checks cover unique storage, independent records, only selected export metadata, validated imports, atomic failure, omitted fields, prototype keys, note length, unavailable storage, recovery from storage failure, corrupt stored data and accurately quoted Markdown. Shared two-context checks cover different faces, same-face save/note edits in both orders, pending clears, read and write denial, patch consumption and partial imports.
- Independent read-only code review confirmed the crop ratio and fixed-grid position math. It found focus loss when an inspector pose button was replaced; the selected replacement button now receives focus.
- The same review found focus loss when an unsaved face disappeared under the Saved filter; rerendering now restores the same or next visible control, with the Saved checkbox as the empty-board fallback.
- Review also reproduced a stale cross-tab overwrite. The state module now merges current storage and patches only changed fields before writing. A read-only `sync()` updates the UI on storage events. Writes that cannot read storage wait for recovery, retaining the in-memory edits.
- The design detector reported metadata below 12px. Metadata and control text were raised to 12px; the detector is a single-pass check.
- Measured contrast ratios: body text 13.08:1, secondary text 5.06:1 on the board and 5.62:1 in the inspector, saved controls 4.99:1, art-loading text 10.41:1. Phone text fields use 16px to avoid focus zoom.

## Browser validation

Actual generated artwork was tested at `http://127.0.0.1:9051/` with a 1440 by 1000 desktop viewport.

- The real catalog rendered 35 study rows and 175 face tiles. Each row contained five faces. The page had no horizontal overflow.
- The first row's computed crop positions were `0% 0%`, `50% 0%`, `100% 0%`, `0% 100%`, `50% 100%`; all used `300% 200%` background size. Each visible crop had width/height ratio 1, matching its 1536 by 1024 source sheet's cell dimensions. The inspector crop also measured ratio 1.
- Top rows showed clean, distinct silhouettes from Later Alligator, Slime Rancher and Dicey Dungeons, without neighboring-cell bleed or clipped face features. Fifteen near-viewport crops loaded; the final row's five remained deferred. No failed crops were present.
- Saved Attentive independently from Considering, then wrote a note for Considering. The inspector showed the original enlarged artwork and the exact pose label, without drawing or warping it.
- Pressing Enter on Amused preserved focus on its selected replacement button. ArrowRight advanced to Concerned. Escape closed the native dialog and restored the Considering note button.
- Searching `OMORI` returned five matching faces in one study. Selecting category `process` returned 50 matching faces in ten studies, all with the process category. Searching `Skeptical` matched pose labels and approaches and kept five tiles in each included row.
- The source-board and external-inspiration fields were reversed in the initial assembled catalog. Assembly corrected them; the source UI remains unchanged. The corrected field values are present in the catalog, but a final live-link check remains pending.

Screenshots: `ui-desktop.png` and `ui-inspector.png`.

The browser connection timed out during the next reload/export batch and reset. Subsequent tab calls failed with `Unable to load browser request-header policy` on three documented retries. Browser discovery still listed the extension. Extension and native-host diagnostics passed; the Chrome process diagnostic reported not running. No browser settings or installation were changed.

Phone screenshot/layout, saved-filter empty/focus behavior, real downloaded JSON/Markdown, and reload persistence still need a live-browser check. The corresponding state logic is covered by the 20 passing Node tests, but this is not claimed as browser validation. The test created a save on `later-alligator-sweet-geraldine__attentive` and the note `QA check: directional gaze stays readable.` on Considering; remove these through the board after recovery if they remain.
