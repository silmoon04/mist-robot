# MIST face repair, 7 September 2026

The MIST console and face studio now share one renderer. It keeps all 40 source expressions, bounds gaze and mouth motion inside the display, and changes incompatible contours through a visible closure. Speech keeps its own playback clock while expressions and blinks change around it.

## What was wrong

The preserved legacy renderer reproduces three failures with `node reproduce_legacy.cjs`. The command intentionally exits 1; `legacy_reproduction.json` records the result.

| Failure | Reproduced evidence | Repair |
| --- | --- | --- |
| Closed mouth collapses on its first speech frame | Height falls from 3.551 to 0.749 face units; width falls from 26.040 to 1.046 | Speech enters through one visible closed-lip shape. Stroke geometry stays intact at the entry frame. |
| Speech reaches the display edge | Largest AA mouth with gaze reaches y=63.705 on a 64-unit display before glow | Speech shapes fit a central region; the complete face has a final inset bound and a separate SVG clip. |
| A completed blink restores an older eye shape | After changing to angry04, the old blink callback replaces an eye of height 18.122 with neutral geometry of height 22.277 | Blinks use the current renderer clock and current expression. There are no delayed restoration callbacks. |

The first replacement export also exposed dim expression midpoints and two faint mouths at speech start and release. All 450 of those frames were reviewed before revision. The evidence remains under `repaired_visual_review/`, including the double line at frame 401 and smile bowl behind the returning line at frame 447. The final closure transition fixes those defects, and the regression now rejects more than one visible mouth.

## Source review

`source_audit/source_audit.md` records the complete inventory and a review row for each expression. The audit covered all 40 faces across six surviving source stages, 40 glow masks, 120 part crops, and 47 historical report PNGs. Its inventory lists 466 original files and 53 canonical parts.

The original high-resolution captures remain absent. Comparison strips preserve downsampled originals, so the audit can assess broad contours and layout. It cannot regenerate the original capture stage. Fitted SVGs 27 and 30 contain small join defects already removed by the canonical geometry. The runtime uses that canonical geometry.

Face 13's source smile had only 1.39 units beneath its stroke, with glow visible at the bottom row. Source tears 28 and 32 also had limited clearance. The runtime fits each entire expression inside an inset before adding motion. This preserves relative feature placement and the aspect ratio of its contours. Raised mouths 06, 21, and 29 remain recognizable in their resting expressions and close before speech takes its centered position. Mouthless faces 12 and 35 remain mouthless after speech.

The source capsules in faces 15, 18, and 27 are tilted compared with their nearly level cleaned-source counterparts. Those authored rotations remain in this repair; the source report identifies them for a later art-direction decision. MIST's asymmetric hooks, bracket eyes, loops, squiggles, smirks, and tears are retained.

## Runtime behavior

- All facial geometry stays within x=5.5..94.5 and y=5.5..58.5 in the 100 x 64 screen. The SVG clip has additional room around this region. Glow is restrained to a 0.55-unit blur.
- Identical parts move continuously. Incompatible eyes close briefly around a common lid position, then open into the next contour. Mouth transitions keep one visible shape and pass through a small closed-lip bridge.
- Open-C and loop eye families blink consistently, including faces 27, 37, and 40 whose old per-face flags disagreed with similar shapes. Deliberate closed-lid expressions retain their resting contour.
- Speech uses 11 shapes derived from the existing mouth vocabulary. Radial correspondence avoids contour twisting. Every full speech pose has at least 4.317 units of separation from the conservative eye bounding boxes at the tested gaze extremes.
- The caller supplies an audio clock in seconds. Mouth events and speech entry follow that clock, including pauses and seeks. Completion selects closed lips; `stopSpeech()` restores the expression's resting mouth over 130 milliseconds.
- Idle breathing and gaze are small. System reduced-motion settings suppress idle motion and automatic blinks. The explicit Blink control remains available.

The renderer consumes supplied mouth timing. It does not derive phoneme alignment from audio. The standalone browser-voice preview uses an estimated text timeline; exact provider alignment depends on the caller's event data.

## Validation

`runtime_regression.json` records a passing deterministic run across **31,050 sampled states**. It covers all **1,600 expression pairs** in silence and during speech, all **40 expressions x 11 visemes x 5 gaze settings**, blink interruption, initial mouth preservation, one visible mouth, audio pause and completion, finite geometry, opacity, and frame bounds.

Run from `brain/`:

```powershell
node harness/check_face_runtime.cjs
```

Every one of the **450 final export frames** was visually inspected through labeled contact sheets. `repaired_visual_review/revised/` records the final review, exact input hashes, and per-frame bounds. No new clipping or severe contour defects were observed. The tightest measured raster padding is **15 pixels** in the 200 x 128 review images. Faces 13, 28, and 32 retain their source identity with visible lower clearance.

The native document was reopened with installed **Aseprite 1.3.18.2**. All **450 frame durations, 41 tag ranges, four layer names, and the 400 x 256 canvas** matched the input. Native and GIF timelines both run for **52.65 seconds**. `aseprite_check/aseprite_validation.json` contains the checks and SHA-256 identity.

## Editable files and rebuilding

`MIST_expression_study.aseprite` contains editable background, eyes, mouth, and tears cels. Its 40 expression tags each include transition, blink, and hold frames. A final speech tag covers all 11 mouth shapes. `MIST_expression_study.gif` is the flattened timed preview. Aseprite edits affect the raster document; the procedural source remains `brain/face_assets/app/app_data.js` and `brain/ui/static/face_runtime.js`.

`editable_svg/` contains 40 standalone vector expressions with named part paths. The face studio also offers Save current SVG for any live pose. Open the studio at `/face/` through the console server, or serve the `brain/` folder and open `/face_assets/app/`.

Rebuild the geometry study from `brain/`:

```powershell
node harness/check_face_runtime.cjs --export
```

Then run from this report's folder:

```powershell
node export_svg.cjs
python export_aseprite.py animation_frames.json MIST_expression_study.aseprite --verify --gif --preview-dir aseprite_check
```

`ASEPRITE_EXPORT.md` documents the snapshot schema and exporter options. Rebuilding changes the snapshot hashes, so a later visual review should record the new hashes alongside its conclusions.
