"""Read-only native-image metrics for the selected static pose set."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent


def main() -> None:
    concepts = json.loads((ROOT / "concepts.json").read_text(encoding="utf-8"))["concepts"]
    results = []
    for concept in concepts:
        for pose in concept["poses"]:
            path = ROOT / "images" / pose["filename"]
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                pixels = np.asarray(image.convert("RGB"))
                width, height = image.size
            cyan = (pixels[:, :, 1] > 110) & (pixels[:, :, 2] > 110) & (pixels[:, :, 0] < pixels[:, :, 1] * .8)
            ys, xs = np.where(cyan)
            flags = []
            if width != height or min(width, height) < 768:
                flags.append("Not a clear native square pose")
            if not len(xs):
                flags.append("No readable turquoise artwork")
                bounds, margin, colour = None, None, None
            else:
                bounds = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
                margin = min(bounds[0], bounds[1], width - 1 - bounds[2], height - 1 - bounds[3])
                if margin < min(width, height) * .025:
                    flags.append("Artwork is too close to the image edge")
                colour = np.median(pixels[cyan], axis=0).astype(int).tolist()
            results.append({"id": pose["id"], "file": "images/" + pose["filename"],
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "width": width, "height": height, "cyanBounds": bounds,
                            "minimumMarginPx": margin, "medianCyanRGB": colour, "flags": flags})
    output = {"scope": "Static image decode, hashes, bounds and colour measurements only; no image changes or animation tests.",
              "imageCount": len(results), "flagged": sum(bool(r["flags"]) for r in results), "images": results}
    (ROOT / "qa/asset-metrics.json").write_bytes((json.dumps(output, indent=2) + "\n").encode())
    print(json.dumps({"images": len(results), "flagged": output["flagged"]}))
    if output["flagged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
