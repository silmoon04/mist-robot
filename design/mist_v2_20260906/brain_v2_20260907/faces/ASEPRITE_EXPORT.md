# Aseprite animation export

`export_aseprite.py` turns runtime geometry snapshots into a native `.aseprite` animation. Every frame has its own duration and separate editable `eyes`, `mouth`, and `tears` image layers. Named tags mark animation ranges in the timeline. An optional background color adds a separate editable backdrop layer.

The runtime source and geometry snapshots remain the source for procedural animation. Aseprite contains raster cels for painting and timeline editing; changes made there do not rewrite the runtime geometry.

Run from this folder with Python 3 and Pillow installed:

```powershell
python export_aseprite.py animation_frames.json MIST_expression_study.aseprite --verify --gif --preview-dir aseprite_check
```

The default canvas is 100 × 64 logical units at scale 8, producing an 800 × 512 document. Add `--scale 4` to produce 400 × 256. Shapes are rendered at twice the output resolution, then reduced with antialiasing. Use `--antialias 1` to draw directly at the output resolution.

The included `animation_frames.json` sets scale 4. Its export has 450 frames, 41 tags, and a 52.65-second timeline at 400 × 256. `MIST_expression_study.gif` is a flattened animation preview. `--gif` rebuilds it with Aseprite and rounds cumulative frame boundaries to GIF's 10-millisecond units. This keeps the preview's total duration within 5 milliseconds of the native timeline. Both included files run for 52.65 seconds. Timelines with frames too short to represent at 10-millisecond resolution are rejected for GIF export.

`--verify` opens the result in the installed Aseprite, compares frame count, every duration, layer names, canvas dimensions, and tag ranges/directions, and exports a thumbnail sheet. Validation files go to `<output stem>_check/` unless `--preview-dir` specifies another folder. `aseprite_validation.json` records those checks and the native file's SHA-256 hash. The exporter discovers Aseprite at the usual local Steam path or on `PATH`; `--aseprite` can provide a different executable.

## Snapshot format

```json
{
  "width": 100,
  "height": 64,
  "scale": 8,
  "color": "#F2FBFF",
  "background": "#000000",
  "layerOrder": ["eyes", "mouth", "tears"],
  "frames": [
    {
      "durationMs": 80,
      "layers": [
        {
          "role": "eyes",
          "points": [[25, 24], [25, 33]],
          "width": 3,
          "mode": "stroke",
          "opacity": 1
        },
        {
          "role": "mouth",
          "points": [[42, 45], [50, 48], [58, 45]],
          "width": 2,
          "mode": "stroke",
          "opacity": 1
        }
      ]
    }
  ],
  "tags": [
    {"name": "neutral", "from": 0, "to": 0, "direction": "forward"}
  ]
}
```

The `layers` array contains drawing shapes. Several shapes can share a `role`; they are composited into the same Aseprite layer in input order. A role absent from a frame produces an empty cel on that frame. Extra role names are added after the listed layers. Layer order runs from bottom to top.

| Field | Accepted values |
| --- | --- |
| `points` | Pairs `[x, y]` or objects `{"x": x, "y": y}` in logical canvas units. `pts` is an alias. |
| `mode` | `stroke`, `fill`, `fill-stroke`, or `none`. Default `stroke`. |
| `width` | Nonnegative stroke width in logical units. Default 2. A zero-width stroke adds no pixels. |
| `closed` | `true` connects the last stroke point to the first. Filled polygons close automatically. |
| `opacity` | A number from 0 to 1. Default 1. |
| `color` | A CSS color string or RGB/RGBA channel array, with channel values from 0 to 255. A shape overrides the document color. |
| `durationMs` | Integer frame duration from 1 to 65535 milliseconds. Default 80; `duration` is an alias. |
| Tag `from`, `to` | Inclusive, zero-based frame indices. |
| Tag `direction` | `forward`, `reverse`, `ping-pong`, or `ping-pong-reverse`. Default `forward`. |
| Tag `repeat` | Integer from 0 to 65535. Zero uses Aseprite's default repeat behavior. |

Omit `background`, or set it to `null`, for transparency. With a background color present, `background` is reserved for the generated backdrop layer. Stroke caps and joins are round.

The binary writer follows the [official Aseprite file specification](https://github.com/aseprite/aseprite/blob/main/docs/ase-file-specs.md). It writes RGBA compressed cels, normal image layers, sRGB color metadata, frame durations, and animation tags. Verification uses the [official Aseprite command-line interface](https://www.aseprite.org/docs/cli/).
