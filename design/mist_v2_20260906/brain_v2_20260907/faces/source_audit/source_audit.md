# MIST face source audit, 7 September 2026

All 40 expression IDs were visually inspected across the surviving original thumbnails, extracted cores, normalized cores, cleaned rasters, fitted SVG renders, and canonical rasters. The audit also covered all 40 extracted glow masks, all 120 part crops, and all 47 historical report PNGs. The static canonical strokes and fills fit the 100 x 64 canvas in every face. Face 13's glow reaches the lower canvas edge, and its smile leaves too little margin for unrestricted movement.

The audit wrote only new files in this directory. No source asset or runtime file was edited. No applicable AGENTS.md was found in the repository, the relevant source/design subtrees, or the checked ancestor directories.

## Inventory and provenance

There are **466 existing files** in `brain/face_assets`: 407 PNGs, 40 SVGs, 8 JSON files, 8 Python scripts, one JavaScript file, one HTML file, and one README. The 40 faces use **53 canonical parts**, and `face_map.json` defines 20 expression mappings.

| Existing material | Exact count | Meaning |
|---|---:|---|
| `canonical_renders/*.png` | 40 | One canonical face raster per expression |
| `cleaned/*.png` | 40 | Normalized mask re-renders |
| `compare/*.png` | 40 | Original preview, cleaned, canonical comparison strips |
| `masks/*_core.png` | 40 | Extracted bright geometry |
| `masks/*_glow.png` | 40 | Broader photo glow extraction |
| `normalized/*.png` | 40 | Normalized core masks |
| `part_crops/*.png` | 120 | 80 eyes, 38 mouths, 2 tears |
| `svg/*.svg` | 40 | Fitted vector faces |
| `reports/*.png` and `reports/app_shots/*.png` | 47 | 25 report images, 18 individual app shots, 4 app sheets |

The original `brain/isolated_screens_highres` directory is absent, as the asset README already records. The surviving `compare` strips are 1600 x 341 pixels; their first approximately 533 x 341 panel preserves a downsampled original screen preview with an overlaid label. It can support broad shape comparisons, but cannot restore the original capture quality. Current core/normalized/canonical full-face rasters are 1600 x 1024. No native Aseprite source exists inside the repository search scope.

`inventory.json` records every existing file's relative path, size, SHA-256, and image dimensions where applicable. Its count distinguishes files and derivatives from the 40 unique expressions.

## Findings that affect future authoring

- **Face 13 needs more lower margin.** Its canonical smile bound ends at y=62.61, leaving 1.39 of the 64 canvas units. At 1600 x 1024 this is about 22 pixels. The last image row has a maximum channel value of 35/255, confirming that visible glow reaches the boundary. No stroke/fill itself crosses the screen.
- **Faces 28, 32, and 38 also have limited lower margin.** The two tears leave 4.57 and 4.48 units, while face 38's tall mouth leaves 5.14. These are source layout constraints for translations, breathing, talking, and any raster export padding.
- **Faces 06, 13, 21, and 29 need expression-specific mouth handling.** Face 06's raised, right-shifted frown approaches the right eye; faces 21 and 29 place the mouth in the eye band; face 13 places it very low. The existing README independently identifies these four as `talkSafe:false` and documents a fallback to face 39 before speech.
- **Canonicalization introduces three visible mouth tilts.** Faces 15, 18, and 27 use capsule rotations of -7.17, +6.36, and -9.84 degrees. Their cleaned mouths read nearly level, and face 27's difference is especially noticeable. Confirm the intended direction before using these poses as identity references.
- **Two fitted SVGs preserve small join defects.** Face 27 has a protruding eye-loop join; face 30 has a short horizontal spur at the left chevron tip. The corresponding canonical rasters remove them. The fitted SVG folder should not be assumed to be the final polished source.
- **Glow masks cannot supply clean part geometry.** Faces 06, 21, 24, 28, and 32 visibly merge neighboring features. Face 24 is almost a single featureless blob, despite having readable bracket eyes in its core and later stages. Use core masks or canonical geometry for part extraction.
- **31 inspection crops across 10 faces include neighboring components.** The affected IDs are 04, 05, 06, 07, 21, 28, 29, 32, 33, and 34. The crop script adds 40 pixels of padding around a part's box without masking its neighbors. These files are visual inspection aids, not isolated transparent animation assets. `crop_secondary_components.json` records components with at least 8 pixels at green-channel intensity above 180, corroborated by visual inspection.
- **Faces 12 and 35 intentionally have no mouth.** The omission is visible in the original previews, masks, and every later face stage. Treating it as an extraction failure would change the expressions.
- **Face-map prose has at least one geometry mismatch.** The `alert` entry describes face 24 as wide open C-shaped eyes; all surviving visual stages show narrow bracket eyes. This is a labeling issue, separate from rendering quality.

The stored fitted-mask IoU averages 0.919775. The stored canonical IoU averages 0.828075, with a range of 0.650 to 0.935. These are different pipeline stages. IDs 01, 05, 08, 12, and 13 have stored canonical IoU below 0.75 and visibly lighter/smoothed stroke mass, while retaining the broad expression. This audit did not recompute those stored IoU values and does not use them as a perceptual pass/fail score.

## Per-frame visual review

Every row passed static canonical core/stroke canvas bounds. Notes identify layout risks, stage-specific defects, or intentional identity details. A clean note applies to this source review and does not certify animation or runtime transitions.

| Face | Categories | Visual finding |
|---|---|---|
| `01_angry_01_manual` | stored_canonical_iou_under_0_75 | Angry hook eyes and level mouth retained; canonical strokes are lighter than the extracted core. |
| `02_angry_02_manual` | No source issue observed | Angry hooks and tall filled oval retained; static parts remain separate. |
| `03_angry_07_manual` | No source issue observed | Bracket eyes and off-center asymmetric frown retained. The asymmetry exists in the original preview. |
| `04_angry_08_manual` | inspection_crop_contains_neighbors | Angry hooks and centered frown retained. All three inspection crops contain neighboring fragments. |
| `05_annoyed_01_manual` | stored_canonical_iou_under_0_75, inspection_crop_contains_neighbors | Half-lidded hooks and pointed frown retained; canonical stroke mass is lighter. All three crops contain neighbors. |
| `06_annoyed_02_manual` | unusual_mouth_placement, raw_glow_merges_features, inspection_crop_contains_neighbors | The raised right-shifted frown nearly meets the right eye. The raw glow merges them; eye_R and mouth crops include one another. |
| `07_annoyed_03_manual` | inspection_crop_contains_neighbors | Mismatched eyes and filled half-dome mouth retained. All three crops include neighboring fragments. |
| `08_annoyed_04_manual` | stored_canonical_iou_under_0_75 | Chevron eyes and filled capsule retained; canonical strokes are lighter than the extracted core. |
| `09_happy_03_manual` | No source issue observed | Gap-circle eyes and broad filled smile bowl retained. No static geometry defect observed. |
| `10_happy_04_manual` | No source issue observed | Closed happy arcs and omega-shaped mouth retained. No static geometry defect observed. |
| `11_happy_05_manual` | No source issue observed | Gap-circle eyes and open smile arc retained. No static geometry defect observed. |
| `12_happy_09_manual` | source_has_no_mouth, stored_canonical_iou_under_0_75 | Mouthlessness is present in the original preview and all stages. Canonical chevrons are thinner; do not treat the absent mouth as missing data. |
| `13_happy_14_manual` | glow_at_canvas_edge, bottom_margin_under_6, unusual_mouth_placement, stored_canonical_iou_under_0_75 | Low smile leaves 1.39 canvas units below its stroke. Its glow reaches the bottom pixel row. Canonical strokes are lighter than the extracted core. |
| `14_happy_16_manual` | No source issue observed | Happy arcs and low straight mouth retained; the low mouth is source-authored. |
| `15_misc_15_manual` | canonical_mouth_tilt_change | Canonical capsule mouth tilts -7.17 degrees although the cleaned source reads level. |
| `16_misc_16_manual` | No source issue observed | Closed lower arcs and tall yawn oval retained. Their shared vertical band is source-authored. |
| `17_misc_2_01_manual` | No source issue observed | Three horizontal strokes retained. No static geometry defect observed. |
| `18_misc_2_02_manual` | canonical_mouth_tilt_change | Looped letter eyes retained. Canonical capsule mouth tilts +6.36 degrees compared with the nearly level cleaned source. |
| `19_misc_2_03_manual` | No source issue observed | Chevrons and short level mouth retained. No static geometry defect observed. |
| `20_neutral_06_manual` | No source issue observed | Open gap-circle eyes and tiny dot mouth retained. Preserve dot scale when authoring speech variants. |
| `21_neutral_11_manual` | unusual_mouth_placement, raw_glow_merges_features, inspection_crop_contains_neighbors | Raised half-dome mouth sits in the eye band. Raw glow merges all features; all three crops contain neighbors. A legacy quarter-sheet has conflicting scale. |
| `22_neutral_12_manual` | No source issue observed | Closed lower arcs and level mouth retained. No static geometry defect observed. |
| `23_neutral_13_manual` | No source issue observed | Closed lower arcs and small filled oval retained. No static geometry defect observed. |
| `24_neutral_2_01_manual` | raw_glow_merges_features | Bracket eyes and level mouth survive in core/normalized/vector stages, but raw glow is almost one featureless blob. The alert mapping prose incorrectly calls these open C-shaped eyes. |
| `25_neutral_2_03_manual` | No source issue observed | Open gap-circle eyes and small filled oval retained. Normalization recenters the off-center captured screen. |
| `26_sad_01_manual` | No source issue observed | Drooping asymmetric lower arcs and level mouth retained. No static geometry defect observed. |
| `27_sad_02_manual` | canonical_mouth_tilt_change, fitted_svg_join_spur | Fitted SVG has a protruding eye-loop join. Canonical eyes remove it, but its capsule mouth tilts -9.84 degrees versus the level cleaned source. |
| `28_sad_03_manual` | bottom_margin_under_6, raw_glow_merges_features, inspection_crop_contains_neighbors | Looped eyes, wavy mouth, and right tear retained. Tear bottom margin is 4.57 units; all four part crops contain neighbors. |
| `29_sad_04_manual` | unusual_mouth_placement, inspection_crop_contains_neighbors | Raised wavy mouth shares the lower-eye band. All three crops contain neighbors; maintain distinct mouth and eye roles. |
| `30_sad_05_manual` | fitted_svg_join_spur | Fitted SVG has a short horizontal spur at the left chevron tip. Canonical render removes it and retains the pointed frown. |
| `31_sad_06_manual` | No source issue observed | Sad hooks and tall filled oval retained. The mouth has 6.38 units below its stroke/fill bound. |
| `32_sad_07_manual` | bottom_margin_under_6, raw_glow_merges_features, inspection_crop_contains_neighbors | Gap-circle eyes, curved frown, and right tear retained. Tear bottom margin is 4.48 units; all four crops contain neighbors. |
| `33_sad_08_manual` | inspection_crop_contains_neighbors | Mismatched eyes and wavy mouth retained. All three crops contain neighboring fragments. |
| `34_sad_09_manual` | inspection_crop_contains_neighbors | Looped eyes and curved frown retained. All three crops contain neighboring fragments. |
| `35_sad_10_manual` | source_has_no_mouth | Mouthlessness is present in the original preview and every surviving face stage; preserve it as an expression choice. |
| `36_misc_03_manual` | No source issue observed | Mismatched eyes and tilted line mouth retained. Their asymmetry is part of the source identity. |
| `37_misc_06_manual` | No source issue observed | Bracket eyes and tilted smirk retained. No static geometry defect observed. |
| `38_misc_2_06_manual` | bottom_margin_under_6 | Looped eyes and tall filled oval retained. Mouth bottom margin is 5.14 units. |
| `39_neutral_02_manual` | No source issue observed | Gap-circle eyes and flat neutral mouth retained. No static geometry defect observed. |
| `40_neutral_03_manual` | No source issue observed | Bracket eyes and tiny dot mouth retained. Preserve dot scale and bracket openings. |

## Historical report evidence

All 47 saved report PNGs opened successfully. Their contents represent several revisions, so a failure in an old sheet is not proof of current runtime behavior.

- In `app_shots/sheet.png`, happy09 has a collapsed mouth, sad28 loses its eyelid loops and wavy mouth, blink18 loses its eyes, and visAA/vis12OO fill the display cyan. Later sheets and individual screenshots show different, recognizable shapes.
- `q_morph16_0.png` has opposing square notches in a small mouth; `q_morph16_1` through `_3` show smooth tall ovals. This is saved evidence of a transitional deformation.
- `diff_08_annoyed.png` has a stray diagonal cyan stroke entering from the left edge and crossing an eye. It is absent from the corresponding canonical gallery and final diff sheet.
- `canon_debug.png` shows an intermediate face 27 fit disagreement, including eye-loop shape and mouth orientation.
- `diff_third_0/1/2` are exact slices of `diff_sheet.png`; their cut rows are pagination, not source clipping. All `norm_q` sheets match their parent. `sheet_q2` differs from `analysis_contact_sheet.png` specifically at face 21, whose extracted features are larger in the quarter-sheet.

The supplementary `legacy_reports` directory contains contact sheets for every saved report image, an enlarged face 21 comparison, its inventory, and deterministic parent/slice comparisons. The 18 individual saved app screenshots did not show unambiguous face-shape clipping at the display edge; the earlier solid-cyan panels are separate rendering failures.

## Aseprite availability

Installed executable: `C:/Program Files (x86)/Steam/steamapps/common/Aseprite/Aseprite.exe`, Windows product version 1.3.18.2, 22,082,648 bytes. It is absent from PATH. No installation was performed.

The repository search included hidden and ignored files and excluded `node_modules` and `.git`; it found zero `.ase` or `.aseprite` documents. A separate `<LOCAL_HOME>/Downloads/Sprite-0001.aseprite` has a valid Aseprite header and contains one 64 x 64 frame. Its connection to MIST is unestablished, so it was not treated as a face source.

Executable lookup checked PATH and conventional Aseprite/Steam directories under Program Files and LocalAppData Programs. An initial broader Downloads executable search encountered an unrelated malformed gitignore and two inaccessible temporary directories, so absence is not claimed across all Downloads.

## Audit artifacts and method

- `stages_01.png` through `stages_08.png`: every face across six surviving stages, five expressions per sheet.
- `extracted_glow_01.png` and `_02.png`: all 40 broader glow masks.
- `part_crops_01.png` through `_04.png`: all 120 inspection crops.
- `fitted_svg_renders/`: 40 geometry renders used for the visual comparison.
- `canonical_geometry_metrics.json`: transformed canonical part bounds, including half stroke width and excluding glow, in 100 x 64 coordinates.
- `per_frame_review.json`: machine-readable review of all 40 expression IDs.
- `legacy_reports/`: the independent visual pass over all 47 historical report PNGs.

The contact sheets assemble existing raster previews and rendered vectors for review. They do not alter the source art. CairoSVG rendered the fitted SVG geometry; its filter support may differ from the browser, so the flatter glow in that column is not itself a defect. This source audit does not test live transitions, blinking, visemes, device display behavior, or the relation of old screenshots to the current app.
