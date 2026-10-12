# MIST eye closure components

The selected strips are provisionally accepted as components, pending composed playback review. These are six closure drawings per family, not complete twelve-frame acting animations. Reopening reuses them in reverse.

## Files and rig contract

- `round/cell_0.png` through `round/cell_5.png` and corresponding `hook` paths.
- Every cell is 128 by 112 pixels. Bottom attachment is `(64, 92)`.
- Cell 0 is the original canonical raster glyph, uniformly resized to 86 pixels wide. It is not a generated approximation.
- Cells 1–4 come from selected ImageGen source sheets. Each family uses one uniform scale; translations alone align the bottom attachment.
- Cell 5 is the same round-family closed drawing in both families. The two PNGs are byte identical, allowing a closed-eye transition without a silhouette jump.
- Place the attachment at a fixed rig point, such as `(145, 190)` for the left eye. Do not center each pose on its changing bounds.
- Alpha-mask rendering uses common ink `#5eeadd`. The source color drift is preserved in immutable source sheets and corrected only in the extracted component palette.

## Changes and remaining observations

The original hook pilot ended with an open aperture. The selected endpoint is now a single closed stroke. The round pilot was thinner than the canonical C, so a targeted ImageGen repair brought the line weight closer to the original. A common endpoint avoids different hook and round closure silhouettes at transition handoff.

All selected drawings preserve the same lower curve direction. They have no pupils, detached eyebrows, inverted closed arcs or unrelated eye models. Near-closed poses keep the connected top-and-lower-lid construction. At enlarged scale the meeting point of the rounded ends remains visible; at component scale it does not create a separate feature.

Round pose 3 widens from the canonical 86 pixels to 95 pixels. This is actual source geometry, not hidden per-frame stretching. Root and independent reviewer inspected `contact_final.png` at component size and found it a minor width wobble rather than an identity change. Composed playback must still confirm it does not distract. Hook widths stay within 86–87 pixels until the shared closed endpoint, which is 90 pixels wide. The shared endpoint is exactly the same for both families.

Technical extraction checks establish dimensions, attachments and source traceability only. They do not establish that motion is natural.

## Generation provenance

Seven built-in ImageGen calls produced four round versions and three hook versions. Full prompts are under `../../prompts/eyes/`. The first sources used mechanically cropped canonical reference rasters from `reuse/parts/circle_gap_03.png` and `reuse/parts/angry_hook_00.png`. Each subsequent source was an edit of its previous version. The immutable selected sources are `round/source_v4.png` and `hook/source_v3.png`. Earlier versions remain for inspection.

The extraction script reproduces cells, contacts and the manifest. `manifest.json` records selected source hashes and per-cell provenance.
