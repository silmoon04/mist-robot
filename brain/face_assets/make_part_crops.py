"""Crop each face part (normalized space) for close visual inspection."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "part_crops"
OUT.mkdir(exist_ok=True)

records = json.loads((ROOT / "measurements_normalized.json").read_text())
for rec in records:
    name = Path(rec["file"]).stem
    clean = cv2.imread(str(ROOT / "cleaned" / f"{name}.png"))
    s, tx, ty = rec["norm_scale"], rec["norm_tx"], rec["norm_ty"]
    for comp in rec["components"]:
        x, y, w, h = comp["bbox_xywh"]
        role = comp["role"]
        x0 = int(x * s + tx) - 40
        y0 = int(y * s + ty) - 40
        x1 = int((x + w) * s + tx) + 40
        y1 = int((y + h) * s + ty) + 40
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(clean.shape[1], x1), min(clean.shape[0], y1)
        crop = clean[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        # upscale small crops for legibility
        scale = max(1, int(360 / max(crop.shape[0], 1)))
        if scale > 1:
            crop = cv2.resize(crop, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(str(OUT / f"{name}__{role}.png"), crop)
print("done", len(list(OUT.glob('*.png'))))
