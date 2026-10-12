"""Encode MIST review GIFs from composed PNG poses without changing the art."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "brain/art_direction/artist_studio_20260916/reuse/mist_motion_v3"
OUT = ROOT / "previews"
BACKGROUND = (15, 29, 33)
LABEL = (214, 229, 226)
MUTED = (139, 164, 163)
FPS = 15


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_path(name: str) -> Path:
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT.resolve()) or ":" in name or "\\" in name:
        raise ValueError(f"Asset escapes the study: {name}")
    return path


def font(size: int):
    for path in (Path("C:/Windows/Fonts/segoeui.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def duration_ticks(durations: list[float]) -> list[int]:
    """Round cumulative boundaries, avoiding timing drift from GIF centiseconds."""
    result, elapsed, previous = [], 0.0, 0
    for duration in durations:
        elapsed += duration
        boundary = round(elapsed / 10) * 10
        result.append(max(10, boundary - previous))
        previous = boundary
    return result


def encode(path: Path, frames: list[Image.Image], durations: list[float]) -> dict:
    if len(frames) != len(durations) or not frames:
        raise ValueError("GIF drawings and durations must match.")
    sample_count = min(len(frames), 18)
    sample = Image.new("RGB", (frames[0].width, frames[0].height * sample_count))
    for index in range(sample_count):
        sample.paste(frames[round(index * (len(frames) - 1) / max(1, sample_count - 1))], (0, index * frames[0].height))
    palette = sample.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    desired = duration_ticks(durations)
    path.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(path, format="GIF", save_all=True, append_images=indexed[1:],
                    duration=desired, loop=0, disposal=2, optimize=False)
    # Pillow may merge identical held poses. Their cumulative exposure must stay
    # exact; the PNG sequence remains the authoritative pose count.
    with Image.open(path) as decoded:
        actual = []
        for index in range(decoded.n_frames):
            decoded.seek(index)
            actual.append(decoded.info.get("duration", 0))
        if sum(actual) != sum(desired) or decoded.info.get("loop") != 0:
            raise ValueError(f"GIF duration verification failed: {path.name}")
        dimensions = list(decoded.size)
    return {"file": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "bytes": path.stat().st_size,
            "width": dimensions[0], "height": dimensions[1], "submittedSamples": len(frames),
            "encodedFrames": len(actual), "durationMs": actual, "loopMs": sum(actual)}


def draw_label(draw, text, x, y, label_font, colour, max_width):
    while len(text) > 1 and draw.textlength(text, font=label_font) > max_width:
        text = text[:-2].rstrip() + "…"
    draw.text((x, y), text, anchor="mt", font=label_font, fill=colour)


def stage(frame: Image.Image, label: str, subtitle: str, size=(512, 370)) -> Image.Image:
    output = Image.new("RGB", size, BACKGROUND)
    target = (size[0], round(size[0] * 320 / 512))
    image = frame.resize(target, Image.Resampling.LANCZOS)
    output.paste(image, (0, 0), image)
    draw = ImageDraw.Draw(output)
    draw_label(draw, label, size[0] // 2, target[1] + 6, font(17), LABEL, size[0] - 16)
    draw_label(draw, subtitle, size[0] // 2, target[1] + 30, font(11), MUTED, size[0] - 16)
    return output


def clip_durations(example: dict, kind="frames") -> list[float]:
    durations = [frame["durationMs"] for frame in example[kind]]
    rest = example.get("restMs", 0) if kind == "frames" else 1600
    if rest > 0:
        durations.append(rest)
    return durations


def frame_at(elapsed: float, durations: list[float]) -> int:
    within = elapsed % sum(durations)
    boundary = 0
    for index, duration in enumerate(durations):
        boundary += duration
        if within < boundary:
            return index
    return len(durations) - 1


def main():
    manifest_path = ROOT / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
    checks = json.loads((ROOT / "asset_checks.json").read_text(encoding="utf-8-sig"))
    if not manifest.get("complete") or not checks.get("passed") or manifest.get("fps") != FPS:
        raise ValueError("Build previews after the complete 15 fps manifest passes asset checks.")
    groups = manifest["groups"]
    examples = [example for group in groups for example in group["examples"]]
    if len(examples) != 18:
        raise ValueError("Expected 18 acting clips.")
    loaded, inputs, outputs = {}, [], []
    for example in examples:
        if len(example["frames"]) != 12:
            raise ValueError(f"Expected 12 acting poses: {example['key']}")
        loaded[example["key"]] = {}
        for kind in ("frames", "blinkFrames"):
            images = []
            for frame in example[kind]:
                path = source_path(frame["file"])
                if sha(path) != frame["sha256"]:
                    raise ValueError(f"Input hash mismatch: {frame['file']}")
                with Image.open(path) as image:
                    if image.size != (512, 320):
                        raise ValueError(f"Common canvas mismatch: {frame['file']}")
                    images.append(image.convert("RGBA"))
                inputs.append({"file": frame["file"], "sha256": frame["sha256"]})
            loaded[example["key"]][kind] = images
            frames = [stage(image, example["label"], "MIST · Acting" if kind == "frames" else "MIST · Separate blink") for image in images]
            if len(clip_durations(example, kind)) > len(frames):
                frames.append(frames[0])
            path = OUT / example["key"]
            name = path.with_suffix(".gif") if kind == "frames" else path.with_name(path.name + "_blink.gif")
            output = encode(name, frames, clip_durations(example, kind))
            output.update({"key": example["key"], "kind": "acting" if kind == "frames" else "blink", "composedPoses": len(images)})
            outputs.append(output)
    # One cycle for every clip, then a shared rest. Shorter clips hold their
    # neutral frame until the slowest clip finishes; no seam cuts a gesture.
    timelines = {example["key"]: clip_durations(example) for example in examples}
    grid_ms = max(sum(durations) for durations in timelines.values()) + 800
    grid_ticks = round(grid_ms * FPS / 1000)
    grid_frames = []
    tiny_font = font(12)
    for tick in range(grid_ticks):
        elapsed = tick * 1000 / FPS
        grid = Image.new("RGB", (1260, 480), BACKGROUND)
        draw = ImageDraw.Draw(grid)
        for column, group in enumerate(groups):
            for row, example in enumerate(group["examples"]):
                x, y = column * 210, row * 160
                durations = timelines[example["key"]]
                index = frame_at(elapsed, durations) if elapsed < sum(durations) else 0
                source_frames = loaded[example["key"]]["frames"]
                image = source_frames[index % len(source_frames)].resize((210, 131), Image.Resampling.LANCZOS)
                grid.paste(image, (x, y), image)
                draw_label(draw, example["label"], x + 105, y + 137, tiny_font, LABEL, 202)
        grid_frames.append(grid)
    outputs.append(encode(OUT / "all-animations.gif", grid_frames, [1000 / FPS] * grid_ticks))
    if sha(manifest_path) != manifest_sha:
        raise ValueError("Composition manifest changed during GIF export; retry after the composer finishes.")
    receipt = {"version": 3, "manifestSha256": manifest_sha, "nominalFps": FPS,
               "processing": "Composed PNG poses resized and alpha-composited on dark backgrounds; no new artwork or in-between synthesis",
               "timing": "Individual clips use authored exposures followed by a neutral hold; GIF boundaries round cumulatively to 10 ms. Grid plays each clip once, then holds until a common restart.",
               "grid": {"columns": 6, "rows": 3, "columnOrder": [g["id"] for g in groups]},
               "inputs": inputs, "outputs": outputs}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Motion previews\n\n"
        "`all-animations.gif` shows all 18 acting clips. Each group occupies a column, with three examples down the column. "
        "Each clip plays once at its authored speed, then waits at rest for the other clips before the grid repeats.\n\n"
        "Each individual acting GIF contains the 12 composed poses. The `_blink.gif` files show separate blink clips with a neutral pause. "
        "The browser uses a 15 fps timebase with authored holds; GIF timing rounds cumulative boundaries to the format's 10 ms precision. "
        "Identical held poses may be merged by the encoder without shortening their exposure.\n\n"
        "The transparent PNGs remain the source assets. GIF previews have 256 colours and a dark background. "
        "They do not demonstrate live speech synchronisation. `receipt.json` records input and output hashes and timings.\n", encoding="utf-8")
    print(json.dumps({"outputs": len(outputs), "examples": len(examples), "composedActingPoses": 216,
                      "grid": "previews/all-animations.gif", "totalBytes": sum(item["bytes"] for item in outputs)}))


if __name__ == "__main__":
    main()
