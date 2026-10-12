"""Measure sheet cell bounds; this never changes the generated images."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent


def inspect(path: Path) -> dict:
    with Image.open(path) as image:
        pixels = np.asarray(image.convert("RGB"), dtype=np.int16)
    height, width, _ = pixels.shape
    cyan = (pixels[:, :, 1] > 110) & (pixels[:, :, 2] > 110) & (pixels[:, :, 1] - pixels[:, :, 0] > 35) & (pixels[:, :, 2] - pixels[:, :, 0] > 35)
    cells = []
    for row in range(2):
        for col in range(3):
            x0, x1 = round(width * col / 3), round(width * (col + 1) / 3)
            y0, y1 = round(height * row / 2), round(height * (row + 1) / 2)
            ys, xs = np.where(cyan[y0:y1, x0:x1])
            box = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None
            margin = min(box[0], box[1], x1 - x0 - box[2], y1 - y0 - box[3]) if box else None
            cells.append({"row": row, "column": col, "cyanPixels": len(xs), "bbox": box, "marginPixels": margin})
    flags = []
    for index, cell in enumerate(cells[:5]):
        if cell["cyanPixels"] < width * height / 6 * .003:
            flags.append(f"Pose {index + 1} has very little cyan artwork")
        if cell["marginPixels"] is not None and cell["marginPixels"] < 5:
            flags.append(f"Pose {index + 1} needs a boundary/crop check")
    if cells[5]["cyanPixels"] > 50:
        flags.append("Sixth cell contains cyan marks")
    return {"file": path.name, "width": width, "height": height, "cells": cells, "flags": flags,
            "scope": "Pixel availability and grid bounds only; visual emotion and face count require human review."}


def main() -> None:
    references = json.loads((ROOT.parent / "game_face_research_20260929/board/catalog.json").read_text(encoding="utf-8"))
    paths = [ROOT / "sheets" / (entry["id"] + ".png") for entry in references]
    records = [inspect(path) for path in paths if path.is_file()]
    (ROOT / "qa").mkdir(exist_ok=True)
    (ROOT / "qa/asset-metrics.json").write_bytes((json.dumps(records, indent=2) + "\n").encode())
    print(json.dumps({"sheets": len(records), "flagged": [{"file": r["file"], "flags": r["flags"]} for r in records if r["flags"]]}))


if __name__ == "__main__":
    main()
