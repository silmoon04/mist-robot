# Shared asset and viewer contract

Paths are relative to this folder. Original studies are ../acting_studies_v1.

Image agents own source/<group>/<example>.png, prompts/<group>/, receipts/<group>/. Each sheet is a 4-column by 3-row grid of 12 chronological full-face drawings with transparency. Source files stay immutable after selection.

The compiler owns build_assets.cjs, manifest.json, layers/, frames/, contact/, asset_checks.json and the downloadable ZIP. The renderer owns runtime.js. The gallery owns index.html, style.css, app.js, and copied review-state.js (retain the existing review schema and IDs).

## Manifest v2

```json
{
  "version": 2,
  "fps": 15,
  "canvas": {"width": 384, "height": 342},
  "groups": [{
    "id": "aardman", "label": "Wallace & Gromit / Shaun",
    "sourceUrl": "https://...", "examples": [{
      "id": "listening", "label": "Attentive listening", "when": "...", "notes": "...",
      "key": "aardman/listening", "sheet": "source/aardman/listening.png",
      "width": 384, "height": 342, "restMs": 1000,
      "frames": [{
        "index": 0, "file": "frames/aardman/listening/00.png", "durationMs": 66.666667,
        "sourceRect": [0,0,384,341],
        "layers": {
          "leftEye": {"file": "layers/aardman/listening/leftEye_00.png", "x":0,"y":0,"width":192,"height":205},
          "rightEye": {"file": "layers/aardman/listening/rightEye_00.png", "x":192,"y":0,"width":192,"height":205},
          "mouth": {"file": "layers/aardman/listening/mouth_00.png", "x":0,"y":205,"width":384,"height":137}
        }
      }],
      "poses": [
        {"label":"Setup","file":"frames/aardman/listening/00.png"},
        {"label":"Change","file":"frames/aardman/listening/07.png"},
        {"label":"Settle","file":"frames/aardman/listening/11.png"}
      ],
      "transition": {"close":[0,1,2,3],"open":[3,4,5,6,7,8,9,10,11]}
    }]
  }]
}
```

Actual frame and layer dimensions come from each sheet; do not assume the example dimensions. Canvas coordinates refer to an example's own width and height. Crops can be padded by one pixel for even grid dimensions. Generated sheets also have measurable row/column placement drift: whole-face registration uses integer translations, anchored to the midpoint of the eye bounds horizontally and the mouth bounds center vertically. The canvas grows to preserve every original RGBA pixel; no feature is scaled, warped, repainted or erased. Each frame records its source crop, measured anchor and translation.

Separately from registration, derived display frames and layers normalize RGB to zero only where alpha already equals exactly zero. This removes invisible color noise that inflated PNG downloads. No alpha value changes, including alpha1 pixels, and every RGB value at alpha>0 remains exact. Per-frame before/after appearance hashes and alpha hashes must match. Original source PNGs and their hashes remain unchanged.

Most layers use rectangular crops, with transparent horizontal/central gaps shared by all frames when available, otherwise per-frame gaps. Some Mickey mouths curve upward into the eyes' vertical bounding range while their actual ink remains disconnected. Those frames use connected-component masks to separate the three existing features, with faint antialiasing/noise assigned to the nearest feature. Pixels retain their source color and alpha; no contours are repainted or smoothed. Layer bounding rectangles may overlap, but their nonzero alpha pixels do not. Reconstruction must match source alpha and visible RGB exactly; hidden RGB at alpha zero is ignored for masked layers.

Alpha values below 8/255 are ignored only while detecting structure because generated PNGs contain faint alpha specks; actual extraction retains their alpha and color. Checks report low-alpha pixels crossing rectangular split lines and which frames used component masks. Layer offsets and dimensions may vary per frame; the renderer always uses the manifest's x/y/width/height values.

Old review schema retains studyId acting_studies_v1 and group/example IDs, so prior choices and notes still apply. The three old pose choices correspond to conceptual Setup/Change/Settle; keep those controls distinct from the new 12-frame inspection strip.

## Browser runtime interface

Expose window.MistActing with:

- async preload(manifest, baseUrl = '.') returning an assets object with all decoded layer images.
- drawFrame(ctx, example, index, assets, options={}) draws into the supplied canvas; options.layers is an array subset of leftEye,rightEye,mouth; options.mouthFrame can override mouth index. Clear before drawing; stage colour belongs to CSS.
- transitionPlan(fromExample, toExample) returns exactly 12 steps with source/target frame indices and handoff phases. Reuse generated closed-eye poses, never squash or rotate eyes.
- drawTransition(ctx, fromExample, toExample, progress, assets, options={}) draws progress 0..1; frame0 matches source frame0 and frame11 matches target frame0 exactly. Use a closed-eye handoff and a short independent mouth blend. No new generated artwork is implied by these composite transition steps.
- frameAt(elapsedMs, example, fps=15) returns the current frame, with frame0 held during restMs after the 12-frame cycle. Loop boundary must be continuous from11 toward0.

Pure functions should work in Node for independent tests. The UI may use requestAnimationFrame, but visible artwork advances at the selected frame rate. Default 15fps. Explicit Play all overrides reduced-motion pause for this inspection page. Stop updates when hidden. Inspectors must provide frame scrubbing and separate layer visibility.

Asset generation and build may still be running while UI is implemented. Do not use fake drawn frames as final assets. Show a loading/error state if real assets are missing.
