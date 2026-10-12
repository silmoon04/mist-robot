# MIST acting studies

Eighteen original MIST examples inspired by six animation references, with three
key poses each. The studies explore attention, timing, emotional changes and
facial shape. They were generated with built-in ImageGen. Prompts and unchanged
source sheets are included alongside the 54 rectangular pose crops.

The examples are interpretations, not footage or production drawings from the
referenced shows. The inspiration links point to the research used to choose
the exercises.

Play timing cycles three poses with proposed holds and an extra 800 ms rest.
It is a timing sketch, not smooth animation. No in-between frames, speech mouths,
voice sync or live expression mappings were added. Some poses need refinement
before they can be used as reliable conversational signals.

Use the notes beside each example to judge its context. In a finished system,
waiting and checking poses would hold for real events; they would not imply a
successful result just because a preview timer expired.

From the project root:

```powershell
python -m http.server 9041 --bind 127.0.0.1 --directory brain/art_direction/artist_studio_20260916
```

Open http://127.0.0.1:9041/reuse/acting_studies_v1/. Leave an already-running
studio server alone. To view an extracted pack, run
`python -m http.server 9042 --bind 127.0.0.1` in its folder and open
http://127.0.0.1:9042/.
