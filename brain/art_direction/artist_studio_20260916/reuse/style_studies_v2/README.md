# MIST drawing styles

Ten existing expressions reinterpreted in three drawing styles. The previous
study mostly changed line weight. These proposals let the contours and mark
making change while keeping the expression and cyan-on-dark palette.

Current shows the existing artwork. Gesture ink uses tilted loops and tapered lines;
Dry brush uses painted strokes and bristle gaps; Cartoon cel uses organic eye
silhouettes and crescent lids. These are static concepts. The live face set,
blinks, speech mouths and thinking animations are unchanged.

Open the comparison through the artist studio:

```powershell
Set-Location ''
python -m http.server 9041 --bind 127.0.0.1 --directory brain/art_direction/artist_studio_20260916
```

Visit http://127.0.0.1:9041/reuse/style_studies_v2/. If the server is already
running, open the link without starting a second process.

The source directory holds untouched built-in ImageGen output and provenance.
Exact prompts are in prompts/. Individual images in variants/ are rectangular
crops of those source sheets. All ten originals are in originals/.

The selection uses everyday defaults plus expressive alternatives. Saved traces
include tests, so it is not a measured organic popularity ranking. The full
selection basis is in manifest.json.

For this extracted pack, run `python -m http.server 9042 --bind 127.0.0.1` in
the extracted folder and open http://127.0.0.1:9042/. Previous-preview links need
the original artist studio on port 9041. The current voice app can be started
separately with `python -m brain.duplex.live_studio --port 9053` from the project
root and opened at http://127.0.0.1:9053/try.
