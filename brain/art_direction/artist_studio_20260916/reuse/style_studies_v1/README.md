# MIST style studies

Ten existing faces, each with three static ImageGen variations. The live artwork
and animation frames are unchanged. Compare Current, Hand ink, Soft rounded and
Fine line in index.html, served through the existing artist studio.

The selection combines everyday defaults with expressive alternatives. Seven
selected faces account for 387 of 391 distinct expression transitions across 33
saved studio traces. Those traces include fixtures and tests. Deadpan, Sleepy and
Delighted add a wider expression range and appeared in prior Luna evaluations.
These counts do not measure organic popularity or time spent displaying a face.

Original faces are copied from the existing reuse/faces directory. Each generated
sheet is an unchanged built-in ImageGen output. Exact prompts and provenance are
in prompts/ and source/. The 30 individual PNGs in variants/ are rectangular
extractions of those sheets. These are visual proposals; making a chosen style
speak and blink would require its own matching animation artwork.

## Start the previews

Run in PowerShell, leaving the window open:

```powershell
Set-Location ''
python -m http.server 9041 --bind 127.0.0.1 --directory brain/art_direction/artist_studio_20260916
```

Open http://127.0.0.1:9041/reuse/style_studies_v1/.
Thinking animations: http://127.0.0.1:9041/reuse/thinking_v8/.
All forty animated faces: http://127.0.0.1:9041/reuse/drawn/.
Transitions: http://127.0.0.1:9041/reuse/drawn/transitions.html.

## Start the voice app

Port 9053 was already running when these studies were created. Start this only
when that server is stopped, in a separate PowerShell window:

```powershell
Set-Location ''
python -m brain.duplex.live_studio --port 9053
```

Open http://127.0.0.1:9053/try. This is the current voice comparison app.
The older native-only app uses `python brain/duplex/server.py --port 8790` and
http://127.0.0.1:8790/. Its pairing code is printed by that process on startup.

For an extracted standalone pack, run `python -m http.server 9042 --bind 127.0.0.1`
inside the extracted folder, then open http://127.0.0.1:9042/. Links to previous
animations require the original artist studio server on port 9041.
