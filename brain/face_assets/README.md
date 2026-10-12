# Mist SVG Face Pipeline

The surviving source for 40 MIST robot expressions and their SVG animation.

> **Provenance limit:** the original `../isolated_screens_highres/` screenshots
> are not present in this repository. Stage 1 cannot currently be reproduced;
> the checked-in masks/measurements and later derivatives are the surviving
> source for stages 2–8. Restore that directory from the original capture
> archive before claiming a full end-to-end regeneration.

## Pipeline (stage 1 requires the missing source archive; stages 2–8 use the
checked-in derivatives)

| # | Script | Output | What it does |
|---|--------|--------|--------------|
| 1 | `analyze_faces.py` | `masks/`, `measurements.json`, `reports/analysis_contact_sheet.png` | Cyan-glow mask extraction, component segmentation, stroke-width + layout measurement |
| 2 | `normalize_faces.py` | `normalized/`, `cleaned/`, `measurements_normalized.json` | Role assignment (eyes/mouth/tears), scale to eye-sep 700px, center eye-midpoint at (800,470), clean neon re-render |
| 3 | `make_part_crops.py` | `part_crops/` | Zoomed per-part crops (used by the vision-classification workflow) |
| 4 | *(agent workflow)* | `classifications.json` | 40 vision agents documented each part's exact geometry + family taxonomy |
| 5 | `fit_svg.py` | `svg/`, `faces.json`, `reports/fit_metrics.json` | Skeleton → Eulerian trace (spur-as-corner stitching, loop-cut joins for 'e') → smoothed, corner-split cubic-bezier fit. Mean IoU 0.92 vs masks |
| 6 | `canonicalize.py` | `parts_library.json`, `faces_canonical.json` | Rotation-aware Procrustes clustering dedupes 120 placed parts → ~55 canonical parts; IoU-guarded ejection; primitive snapping (arcs/lines/dots) with revert guard; near-straight run straightening; stroke widths clamped to ±~10% of global median; symmetric eye placement |
| 7 | `make_canonical_gallery.py` | `canonical_renders/`, `compare/`, `reports/canonical_gallery_*.png` | Visual verification sheets: original vs cleaned vs canonical |
| 8 | `make_app_data.py` | `app/app_data.js` | Adds blink variants (bottom-envelope lids), talk visemes (from the robot's own mouth shapes), capsule outlines for stroke↔fill morphs |

Diff tooling: `make_diff_sheet.py [name-filter...]` overlays fitted render vs
target mask (green=match, red=missed, blue=extra).

## The animator (`app/index.html`)

Open `/face/` through the MIST console server, or serve the `brain/` folder:

```
python -m http.server 8621
# http://127.0.0.1:8621/face_assets/app/
```

The console and studio both use `ui/static/face_runtime.js`. The studio provides
40 expression thumbnails, a blink control, pointer gaze, an expression cycle,
browser-voice and mouth-only previews, and an editable SVG download.

The renderer retains the canonical MIST contours. It fits each source expression
inside a margin that leaves room for gaze, breathing, and glow. Identical parts
move continuously; incompatible eye contours change during a brief lid closure.
Mouth shape changes fade at their own positions so raised and low source mouths
do not travel through the face. Open eyes blink from a single animation clock,
so a delayed blink cannot restore an older expression.

Speech uses a centered, bounded mouth region and retains the active expression,
including the four source poses previously marked `talkSafe:false`. Original
mouthless poses remain mouthless after speech. The console supplies the audio
playback clock and timestamped mouth events. The studio's browser voice uses an
estimated text timeline. Reduced-motion settings suppress idle gaze, breathing,
and automatic blinks.

`window.MistFaceRuntime.create(container, options)` exposes `setExpression`,
`startSpeech`, `stopSpeech`, `setGaze`, `clearGaze`, `blink`, `snapshot`, `update`,
and `destroy`. The studio preserves `window.MIST.selectFace`, `doBlink`,
`startTalk`, `startVisemes`, and `stopTalk` as preview helpers. `#face=<id>` selects
a starting expression.

Run the renderer regression from `brain/`:

```powershell
node harness/check_face_runtime.cjs
```

The check covers every expression pair during speech and blinking, every speech
shape at gaze extremes, safe frame bounds, speech pauses, completion, and the
first closed-mouth frame. `--export` also rebuilds the 450-frame geometry study
in `../design/mist_v2_20260906/brain_v2_20260907/faces/`. That folder contains the
source audit, visual reviews, a layered native Aseprite document, a timed GIF,
and the exporter needed to rebuild them.

## Placement semantics (shared Python ⇄ JS)

`rendered = T + R(rot_deg) · (Mirror_x if mirror) · part.points`
in a 100×64 viewBox (1600×1024 = 16×). Right eyes are mirrored instances of
left-eye canonical parts, so identical eyes across faces stay literally the
same asset — morphs between expressions only move what actually differs.
