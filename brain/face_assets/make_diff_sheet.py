"""Overlay fitted rasterization vs normalized target mask for inspection."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

import fit_svg

ROOT = Path(__file__).resolve().parent
records = json.loads((ROOT / "measurements_normalized.json").read_text())
only = set(sys.argv[1:])

panels = []
for rec in records:
    name = Path(rec["file"]).stem
    if only and not any(k in name for k in only):
        continue
    core = (cv2.imread(str(ROOT / "masks" / f"{name}_core.png"), 0) > 127).astype(np.uint8)
    n, labels = cv2.connectedComponents(core, 8)
    sw = rec["stroke_width_px"]
    s, tx, ty = rec["norm_scale"], rec["norm_tx"], rec["norm_ty"]
    lab_cent = {}
    for lab in range(1, n):
        ys, xs = np.nonzero(labels == lab)
        if len(xs) < 50:
            continue
        lab_cent[lab] = (xs.mean(), ys.mean())
    parts = []
    for comp in rec["components"]:
        cx, cy = comp["centroid_xy"]
        lab = min(lab_cent, key=lambda L: (lab_cent[L][0] - cx) ** 2 +
                  (lab_cent[L][1] - cy) ** 2)
        m = (labels == lab).astype(np.uint8)
        parts.append(fit_svg.transform_part(fit_svg.fit_component(m, sw), s, tx, ty))
    render = fit_svg.rasterize(parts) > 0
    target = cv2.imread(str(ROOT / "normalized" / f"{name}_core.png"), 0) > 127
    vis = np.zeros((fit_svg.H, fit_svg.W, 3), np.uint8)
    vis[np.logical_and(render, target)] = (70, 190, 70)
    vis[np.logical_and(target, ~render)] = (60, 60, 235)   # missed = red
    vis[np.logical_and(render, ~target)] = (235, 190, 60)  # extra = cyan-blue
    vis = cv2.resize(vis, (fit_svg.W // 3, fit_svg.H // 3))
    iou = np.logical_and(render, target).sum() / max(np.logical_or(render, target).sum(), 1)
    cv2.putText(vis, f"{name} IoU={iou:.3f}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (255, 255, 255), 1, cv2.LINE_AA)
    panels.append(vis)

cols = 3
rows = []
for i in range(0, len(panels), cols):
    row = panels[i:i + cols]
    while len(row) < cols:
        row.append(np.zeros_like(panels[0]))
    rows.append(np.hstack(row))
sheet = np.vstack(rows)
out = ROOT / "reports" / ("diff_sheet.png" if not only else f"diff_{'_'.join(sorted(only))}.png")
cv2.imwrite(str(out), sheet)
print("wrote", out, sheet.shape)
