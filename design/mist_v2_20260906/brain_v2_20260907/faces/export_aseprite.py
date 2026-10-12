#!/usr/bin/env python3
"""Export face geometry snapshots as a layered, timed Aseprite document."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zlib

from PIL import Image, ImageColor, ImageDraw


DEFAULT_ASEPRITE = Path("C:/Program Files (x86)/Steam/steamapps/common/Aseprite/Aseprite.exe")
SPEC_URL = "https://github.com/aseprite/aseprite/blob/main/docs/ase-file-specs.md"
DIRECTIONS = {"forward": 0, "reverse": 1, "ping-pong": 2, "ping-pong-reverse": 3}


def u16string(value):
    encoded = str(value).encode("utf-8")
    if len(encoded) > 65535:
        raise ValueError("Aseprite names must fit in 65535 UTF-8 bytes")
    return struct.pack("<H", len(encoded)) + encoded


def chunk(kind, data):
    return struct.pack("<IH", len(data) + 6, kind) + data


def layer_chunk(name):
    # Visible and editable normal image layer; blend mode normal, full opacity.
    return chunk(0x2004, struct.pack("<6HB3x", 3, 0, 0, 0, 0, 0, 255) + u16string(name))


def tags_chunk(tags):
    data = struct.pack("<H8x", len(tags))
    for tag in tags:
        direction = DIRECTIONS[tag.get("direction", "forward")]
        data += struct.pack("<HHBH6x3BB", tag["from"], tag["to"], direction,
                            tag.get("repeat", 0), 95, 193, 231, 0)
        data += u16string(tag["name"])
    return chunk(0x2018, data)


def cel_chunk(layer_index, image):
    bounds = image.getbbox()
    if bounds is None:
        return b""
    left, top, right, bottom = bounds
    cropped = image.crop(bounds)
    header = struct.pack("<HhhBHh5xHH", layer_index, left, top, 255, 2, 0,
                         right - left, bottom - top)
    return chunk(0x2005, header + zlib.compress(cropped.tobytes(), level=6))


def header(file_size, frames, width, height, duration):
    result = bytearray(128)
    struct.pack_into("<I5HIH", result, 0, file_size, 0xA5E0, frames, width, height, 32, 1, duration)
    # Square pixels, no grid. Remaining reserved bytes stay zero.
    struct.pack_into("<BB", result, 34, 1, 1)
    return result


def rgba(value, opacity=1):
    if isinstance(value, str):
        color = ImageColor.getcolor(value, "RGBA")
    else:
        color = tuple(value)
        if len(color) == 3:
            color += (255,)
    if len(color) != 4 or any(not 0 <= channel <= 255 for channel in color):
        raise ValueError(f"Invalid color: {value!r}")
    return tuple(round(channel) for channel in color[:3]) + (round(color[3] * opacity),)


def number(value, description):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{description} must be finite")
    return value


def geometry_points(item, factor):
    points = item.get("points", item.get("pts", []))
    return [(number(p["x"] if isinstance(p, dict) else p[0], "point x") * factor,
             number(p["y"] if isinstance(p, dict) else p[1], "point y") * factor) for p in points]


def draw_item(image, item, factor, default_color):
    points = geometry_points(item, factor)
    opacity = number(item.get("opacity", 1), "opacity")
    if not 0 <= opacity <= 1:
        raise ValueError("Shape opacity must be between 0 and 1")
    mode = item.get("mode", "stroke")
    if mode not in ("stroke", "fill", "fill-stroke", "none"):
        raise ValueError(f"Unsupported drawing mode: {mode!r}")
    if not points or opacity == 0 or mode == "none":
        return
    overlay = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(overlay)
    color = rgba(item.get("color", default_color), opacity)
    if mode in ("fill", "fill-stroke") and len(points) >= 3:
        draw.polygon(points, fill=color)
    if mode in ("stroke", "fill-stroke"):
        width = number(item.get("width", 2), "stroke width") * factor
        if width < 0:
            raise ValueError("Stroke width must not be negative")
        if width > 0:
            line_points = points + [points[0]] if item.get("closed") else points
            if len(line_points) > 1:
                draw.line(line_points, fill=color, width=max(1, round(width)), joint="curve")
            radius = width / 2
            for x, y in points:
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    image.alpha_composite(overlay)


def prepare(document, scale_override):
    frames = document.get("frames", [])
    if not 1 <= len(frames) <= 65535:
        raise ValueError("Provide between 1 and 65535 frames")
    scale = number(scale_override if scale_override is not None else document.get("scale", 8), "scale")
    width = round(number(document.get("width", 100), "canvas width") * scale)
    height = round(number(document.get("height", 64), "canvas height") * scale)
    if scale <= 0 or not (1 <= width <= 32767 and 1 <= height <= 32767):
        raise ValueError("Scaled canvas dimensions must be between 1 and 32767 pixels")
    roles = list(document.get("layerOrder", ["eyes", "mouth", "tears"]))
    if len(roles) != len(set(roles)) or not all(isinstance(role, str) and role for role in roles):
        raise ValueError("layerOrder must contain unique, non-empty layer names")
    for frame_index, frame in enumerate(frames):
        duration = frame.get("durationMs", frame.get("duration", 80))
        if not isinstance(duration, int) or not 1 <= duration <= 65535:
            raise ValueError(f"Frame {frame_index}: durationMs must be an integer from 1 to 65535")
        for item in frame.get("layers", []):
            role = item.get("role")
            if not isinstance(role, str) or not role:
                raise ValueError(f"Frame {frame_index}: each shape needs a role")
            if role not in roles:
                roles.append(role)
    if document.get("background") is not None:
        if "background" in roles:
            raise ValueError("The background role is reserved when a background color is set")
        roles.insert(0, "background")
    tags = document.get("tags", [])
    if len(tags) > 65535:
        raise ValueError("Too many tags")
    for tag in tags:
        if not isinstance(tag.get("name"), str) or not tag["name"]:
            raise ValueError("Each tag needs a non-empty name")
        if not (isinstance(tag.get("from"), int) and isinstance(tag.get("to"), int)
                and 0 <= tag["from"] <= tag["to"] < len(frames)):
            raise ValueError(f"Tag {tag['name']!r}: invalid inclusive frame range")
        if tag.get("direction", "forward") not in DIRECTIONS:
            raise ValueError(f"Tag {tag['name']!r}: invalid direction")
        if not isinstance(tag.get("repeat", 0), int) or not 0 <= tag.get("repeat", 0) <= 65535:
            raise ValueError(f"Tag {tag['name']!r}: invalid repeat count")
    return width, height, scale, roles


def export(document, destination, scale_override=None, antialias=2):
    width, height, scale, roles = prepare(document, scale_override)
    factor = scale * antialias
    render_size = (width * antialias, height * antialias)
    durations = [frame.get("durationMs", frame.get("duration", 80)) for frame in document["frames"]]
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(bytes(128))
            for frame_index, frame in enumerate(document["frames"]):
                pieces = []
                if frame_index == 0:
                    pieces.extend(layer_chunk(role) for role in roles)
                    pieces.append(chunk(0x2007, struct.pack("<HHI8x", 1, 0, 0)))
                    if document.get("tags"):
                        pieces.append(tags_chunk(document["tags"]))
                for layer_index, role in enumerate(roles):
                    background = (rgba(document["background"])
                                  if role == "background" and document.get("background") is not None
                                  else (0, 0, 0, 0))
                    image = Image.new("RGBA", render_size, background)
                    for item in frame.get("layers", []):
                        if item["role"] == role:
                            draw_item(image, item, factor, document.get("color", "#F2FBFF"))
                    if antialias > 1:
                        image = image.resize((width, height), Image.Resampling.LANCZOS)
                    cel = cel_chunk(layer_index, image)
                    if cel:
                        pieces.append(cel)
                data = b"".join(pieces)
                stream.write(struct.pack("<IHHH2xI", len(data) + 16, 0xF1FA, min(len(pieces), 0xFFFF),
                                         durations[frame_index], len(pieces)))
                stream.write(data)
            size = stream.tell()
            stream.seek(0)
            stream.write(header(size, len(document["frames"]), width, height, durations[0]))
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {"canvas": {"width": width, "height": height}, "frames": len(durations),
            "durationMs": sum(durations), "durations": durations, "layers": roles,
            "tags": document.get("tags", []), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def verify_aseprite(aseprite, destination, expected, preview_dir):
    preview_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = preview_dir / "aseprite_metadata.json"
    command = [str(aseprite), "--batch", "--noinapp", "--list-layers", "--list-tags",
               str(destination), "--format", "json-array", "--data", str(metadata_path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode or not metadata_path.exists():
        raise RuntimeError(f"Aseprite metadata export failed: {result.stdout}\n{result.stderr}")
    actual = json.loads(metadata_path.read_text(encoding="utf-8"))
    frames, meta = actual["frames"], actual["meta"]
    actual_layers = [layer["name"] for layer in meta.get("layers", [])]
    checks = {"frame_count": len(frames) == expected["frames"],
              "frame_durations": [frame["duration"] for frame in frames] == expected["durations"],
              "layer_names": actual_layers == expected["layers"],
              "canvas_size": all(frame["sourceSize"] == {"w": expected["canvas"]["width"],
                                                         "h": expected["canvas"]["height"]} for frame in frames),
              "tags": len(meta.get("frameTags", [])) == len(expected["tags"])}
    for expected_tag, actual_tag in zip(expected["tags"], meta.get("frameTags", [])):
        checks["tags"] &= all(actual_tag.get(key) == expected_tag[key] for key in ("name", "from", "to"))
        actual_direction = actual_tag.get("direction", "forward").replace("-", "").replace("_", "")
        expected_direction = expected_tag.get("direction", "forward").replace("-", "").replace("_", "")
        checks["tags"] &= actual_direction == expected_direction
    if not all(checks.values()):
        raise RuntimeError(f"Aseprite metadata mismatch: {json.dumps(checks)}")
    thumbnail_scale = min(1, 200 / expected["canvas"]["width"])
    sheet_path = preview_dir / "aseprite_frames.png"
    sheet_metadata_path = preview_dir / "aseprite_frames.json"
    command = [str(aseprite), "--batch", "--noinapp", str(destination), "--scale", str(thumbnail_scale),
               "--sheet-type", "rows", "--sheet-columns", "8", "--sheet", str(sheet_path),
               "--format", "json-array", "--data", str(sheet_metadata_path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if result.returncode or not sheet_path.exists():
        raise RuntimeError(f"Aseprite thumbnail export failed: {result.stdout}\n{result.stderr}")
    report = {"checks": checks, "asepriteVersion": meta.get("version"), "metadata": str(metadata_path),
              "thumbnailSheet": str(sheet_path), "expected": expected}
    (preview_dir / "aseprite_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def export_gif(aseprite, destination, document, scale_override, antialias):
    # GIF stores centiseconds. Round the cumulative timeline to avoid drift.
    rounded = copy.deepcopy(document)
    elapsed = previous = 0
    for frame in rounded["frames"]:
        elapsed += frame.get("durationMs", frame.get("duration", 80))
        boundary = ((elapsed + 5) // 10) * 10
        frame["durationMs"] = boundary - previous
        if frame["durationMs"] < 10:
            raise ValueError("GIF cannot preserve this timeline: each rounded frame must last at least 10 ms")
        previous = boundary
    gif_path = destination.with_suffix(".gif")
    with tempfile.TemporaryDirectory(prefix="aseprite-gif-", dir=destination.parent) as temp_dir:
        temporary = Path(temp_dir) / "rounded.aseprite"
        export(rounded, temporary, scale_override, antialias)
        result = subprocess.run([str(aseprite), "--batch", "--noinapp", str(temporary),
                                 "--save-as", str(gif_path)], capture_output=True, text=True, timeout=180)
        if result.returncode or not gif_path.exists():
            raise RuntimeError(f"Aseprite GIF export failed: {result.stdout}\n{result.stderr}")
    with Image.open(gif_path) as image:
        durations = []
        for index in range(image.n_frames):
            image.seek(index)
            durations.append(image.info["duration"])
        if durations != [frame["durationMs"] for frame in rounded["frames"]]:
            raise RuntimeError("GIF frame durations differ from the rounded timeline")
    return {"file": str(gif_path), "frames": len(durations), "durationMs": sum(durations),
            "bytes": gif_path.stat().st_size, "timing": "Cumulative timeline rounded to 10 ms"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshots", type=Path, help="JSON containing canvas, frames, shapes, and tags")
    parser.add_argument("output", type=Path, help="Destination .aseprite file")
    parser.add_argument("--scale", type=float, help="Override the JSON canvas scale; 8 gives 800 x 512")
    parser.add_argument("--antialias", type=int, default=2, choices=(1, 2, 3, 4))
    parser.add_argument("--verify", action="store_true", help="Reopen in Aseprite and export metadata and thumbnails")
    parser.add_argument("--gif", action="store_true", help="Export a GIF preview with cumulative 10 ms timing")
    parser.add_argument("--aseprite", type=Path, default=DEFAULT_ASEPRITE if DEFAULT_ASEPRITE.exists() else shutil.which("aseprite"))
    parser.add_argument("--preview-dir", type=Path, help="Validation output directory; defaults to <output stem>_check")
    args = parser.parse_args()
    document = json.loads(args.snapshots.read_text(encoding="utf-8-sig"))
    output = args.output.resolve()
    if (args.verify or args.gif) and not args.aseprite:
        parser.error("Pass --aseprite with the installed Aseprite executable path")
    expected = export(document, output, args.scale, args.antialias)
    gif = export_gif(args.aseprite, output, document, args.scale, args.antialias) if args.gif else None
    if args.verify:
        preview_dir = (args.preview_dir or output.with_name(output.stem + "_check")).resolve()
        report = verify_aseprite(args.aseprite, output, expected, preview_dir)
        if gif:
            report["gif"] = gif
            (preview_dir / "aseprite_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(output), "frames": expected["frames"], "layers": expected["layers"],
                          "tags": len(expected["tags"]), "checks": report["checks"], "previewDir": str(preview_dir),
                          "gif": gif}, indent=2))
    else:
        print(json.dumps({"output": str(output), **expected, "gif": gif}, indent=2))


if __name__ == "__main__":
    main()
