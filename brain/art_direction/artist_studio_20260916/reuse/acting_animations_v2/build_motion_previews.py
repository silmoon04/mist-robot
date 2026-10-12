"""Encode review GIFs from validated, immutable generated frame PNGs.

This only lays out, resizes and encodes existing art. It does not draw facial
features, change registration or synthesize in-between animation frames.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "previews"
BACKGROUND = (15, 29, 33)
LABEL = (214, 229, 226)
MUTED = (139, 164, 163)
GRID_WIDTH = 1260
TILE_WIDTH = 210
TILE_HEIGHT = 230
FRAME_COUNT = 12
REST_MS = 1000
FPS = 15
# GIF stores centiseconds. Alternating 70 / 60 / 70 ms gives exactly 15 fps
# across each three-frame group; the 1000 ms rest is added to frame zero.
DURATIONS = [70, 60, 70] * 4
DURATIONS[0] += REST_MS


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_path(relative: str) -> Path:
    candidate = (ROOT / relative).resolve()
    if not candidate.is_relative_to(ROOT):
        raise ValueError(f"Asset escapes the study folder: {relative}")
    return candidate


def font(size: int) -> ImageFont.FreeTypeFont:
    # Keep the output deterministic across reruns on the review build host.
    # This host font path is never written into a published receipt.
    candidates = (Path("C:/Windows/Fonts/segoeui.ttf"),)
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    raise SystemExit("Segoe UI is required to build these labeled previews.")


def fit(source: Image.Image, width: int, height: int) -> Image.Image:
    scale = min(width / source.width, height / source.height)
    size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
    return source.resize(size, Image.Resampling.LANCZOS)


def composite(stage: Image.Image, source: Image.Image, box: tuple[int, int, int, int]) -> None:
    x, y, width, height = box
    fitted = fit(source, width, height)
    at = (x + (width - fitted.width) // 2, y + (height - fitted.height) // 2)
    stage.paste(fitted, at, fitted)


def centered_label(draw: ImageDraw.ImageDraw, text: str, center: int, y: int,
                   face: ImageFont.FreeTypeFont, colour: tuple[int, int, int],
                   max_width: int) -> None:
    # The source label remains in the receipt; only the compact preview can be
    # ellipsized if a future example title grows beyond its column.
    while draw.textlength(text, font=face) > max_width and len(text) > 1:
        text = text[:-2].rstrip() + "…"
    draw.text((center, y), text, font=face, fill=colour, anchor="mt")


def encode_gif(path: Path, frames: list[Image.Image]) -> dict:
    if len(frames) != FRAME_COUNT:
        raise ValueError("Every preview must use exactly 12 generated drawings.")
    # Use one palette learned from all frames to avoid palette flicker. No
    # dithering: cyan antialiased edges remain clean against the dark stage.
    sample = Image.new("RGB", (frames[0].width, frames[0].height * len(frames)))
    for index, frame in enumerate(frames):
        sample.paste(frame, (0, index * frame.height))
    palette = sample.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                              dither=Image.Dither.NONE)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    path.parent.mkdir(parents=True, exist_ok=True)
    indexed[0].save(path, format="GIF", save_all=True, append_images=indexed[1:],
                    duration=DURATIONS, loop=0, disposal=2, optimize=False)
    with Image.open(path) as decoded:
        actual_durations = []
        for index in range(decoded.n_frames):
            decoded.seek(index)
            actual_durations.append(decoded.info.get("duration", 0))
        if decoded.n_frames != FRAME_COUNT:
            raise ValueError(f"GIF encoder merged drawings in {path.name}: {decoded.n_frames}")
        if actual_durations != DURATIONS or decoded.info.get("loop") != 0:
            raise ValueError(f"GIF timing verification failed for {path.name}")
        dimensions = list(decoded.size)
    return {"file": path.relative_to(ROOT).as_posix(), "sha256": digest(path),
            "bytes": path.stat().st_size, "width": dimensions[0], "height": dimensions[1],
            "encodedFrames": FRAME_COUNT, "durationMs": actual_durations,
            "loopMs": sum(actual_durations), "loop": "infinite"}


def main() -> None:
    manifest_path = ROOT / "manifest.json"
    checks_path = ROOT / "asset_checks.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = json.loads(checks_path.read_text(encoding="utf-8"))
    if manifest.get("complete") is not True:
        raise SystemExit("Refusing previews: manifest.complete must be true.")
    if checks.get("passed") is not True:
        raise SystemExit("Refusing previews: asset_checks.passed must be true.")
    groups = manifest["groups"]
    if len(groups) != 6 or any(len(group["examples"]) != 3 for group in groups):
        raise SystemExit("Expected six groups with three examples each.")
    if manifest.get("fps") != FPS:
        raise SystemExit("Preview timing expects the study's 15 fps playback rate.")

    loaded = {}
    inputs = []
    for group in groups:
        for example in group["examples"]:
            if len(example["frames"]) != FRAME_COUNT or example.get("restMs") != REST_MS:
                raise ValueError(f"Unexpected frame count or rest duration: {example['key']}")
            frames = []
            for index, frame in enumerate(example["frames"]):
                if frame["index"] != index:
                    raise ValueError(f"Frame order mismatch: {example['key']}")
                path = source_path(frame["file"])
                actual_sha = digest(path)
                if actual_sha != frame["sha256"]:
                    raise ValueError(f"Source hash mismatch: {frame['file']}")
                with Image.open(path) as source:
                    if source.size != (example["width"], example["height"]):
                        raise ValueError(f"Canvas mismatch: {frame['file']}")
                    frames.append(source.convert("RGBA"))
                inputs.append({"file": frame["file"], "sha256": actual_sha})
            loaded[example["key"]] = frames

    small_font = font(13)
    group_font = font(10)
    individual_font = font(18)
    individual_group_font = font(13)
    outputs = []
    grid_frames = []
    for index in range(FRAME_COUNT):
        grid = Image.new("RGB", (GRID_WIDTH, TILE_HEIGHT * 3), BACKGROUND)
        draw = ImageDraw.Draw(grid)
        for column, group in enumerate(groups):
            for row, example in enumerate(group["examples"]):
                x, y = column * TILE_WIDTH, row * TILE_HEIGHT
                composite(grid, loaded[example["key"]][index], (x + 9, y + 4, 192, 181))
                centered_label(draw, example["label"], x + TILE_WIDTH // 2, y + 191,
                               small_font, LABEL, TILE_WIDTH - 12)
                centered_label(draw, group["label"], x + TILE_WIDTH // 2, y + 212,
                               group_font, MUTED, TILE_WIDTH - 12)
        grid_frames.append(grid)
    outputs.append(encode_gif(OUT / "all-animations.gif", grid_frames))

    for group in groups:
        for example in group["examples"]:
            individual_frames = []
            for source in loaded[example["key"]]:
                stage = Image.new("RGB", (480, 480), BACKGROUND)
                composite(stage, source, (12, 0, 456, 416))
                draw = ImageDraw.Draw(stage)
                centered_label(draw, example["label"], 240, 430,
                               individual_font, LABEL, 456)
                centered_label(draw, group["label"], 240, 458,
                               individual_group_font, MUTED, 456)
                individual_frames.append(stage)
            output = encode_gif(OUT / group["id"] / f"{example['id']}.gif", individual_frames)
            output["key"] = example["key"]
            output["label"] = example["label"]
            outputs.append(output)

    receipt = {"version": 1, "kind": "Mechanical GIF previews of validated generated frame PNGs",
               "manifestSha256": digest(manifest_path), "assetChecksSha256": digest(checks_path),
               "builderSha256": digest(Path(__file__)), "font": "Segoe UI",
               "frameCount": FRAME_COUNT, "nominalFps": FPS, "restMs": REST_MS,
               "durationMs": DURATIONS, "loopMs": sum(DURATIONS),
               "grid": {"columns": 6, "rows": 3, "columnOrder": [g["id"] for g in groups],
                        "rowOrder": "example order within each group"},
               "processing": "Aspect-fit Lanczos resize, alpha composite on dark stage, fixed 256-colour GIF palette; no new artwork",
               "inputs": inputs, "outputs": outputs}
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Acting animation previews\n\n"
        "`all-animations.gif` plays all 18 examples together in six columns and three rows. "
        "Each column is one inspiration group; each row is that group's corresponding example. "
        "The group folders contain the 18 individual previews.\n\n"
        "Each GIF contains all 12 generated drawings and loops indefinitely. "
        "Timing is 15 fps on average: GIF's 10 ms precision is represented with "
        "70, 60, 70 ms frame durations. Frame zero includes a 1000 ms rest, "
        "giving a total loop length of 1800 ms.\n\n"
        "Previews mechanically resize and composite the validated frame PNGs on a dark stage. "
        "The original transparent PNGs and separate eye/mouth layers remain unchanged. "
        "GIF is a review format with a 256-colour palette, not the production asset format. "
        "These examples are not connected to live speech.\n\n"
        "`receipt.json` records source and output SHA-256 hashes, canvas sizes and "
        "verified encoded frame counts and timings. Run `python build_motion_previews.py` "
        "from the study directory to rebuild after the manifest is complete and asset checks pass.\n",
        encoding="utf-8")
    print(json.dumps({"outputs": len(outputs), "examples": 18, "drawings": 216,
                      "grid": "previews/all-animations.gif", "totalBytes": sum(x["bytes"] for x in outputs)}))


if __name__ == "__main__":
    main()

