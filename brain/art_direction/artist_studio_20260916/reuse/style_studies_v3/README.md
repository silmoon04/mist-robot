# MIST face study

Ten everyday and expressive faces, redrawn in two directions using the user's
illustration as the style reference. Current shows the existing artwork;
Reference style and More expressive show the new static concepts.

The comparison supports filtering, enlarging each face and downloading the PNGs.
The pack includes original images, new crops, generated source sheets, prompts
and review notes. Blinking, speaking and transitions still need separate artwork
after a direction is chosen.

From the project root, start the studio with:

```powershell
python -m http.server 9041 --bind 127.0.0.1 --directory brain/art_direction/artist_studio_20260916
```

Open http://127.0.0.1:9041/reuse/style_studies_v3/. If it already opens, leave the
existing server running. In an extracted pack, run
`python -m http.server 9042 --bind 127.0.0.1` and open http://127.0.0.1:9042/.

The ten faces come from everyday defaults and expressive alternatives. Saved
usage traces include tests, so this is not an organic popularity ranking.
The detailed selection basis is in manifest.json.
