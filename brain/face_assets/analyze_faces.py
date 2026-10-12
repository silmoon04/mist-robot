"""Stage 1: measure all high-res isolated screens.

Extracts the cyan glow mask per face, segments stroke components,
estimates stroke widths and layout geometry, and emits a contact sheet
plus measurements.json used by the normalization + SVG fitting stages.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from skimage.morphology import skeletonize

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "isolated_screens_highres"
OUT_MASKS = ROOT / "masks"
OUT_REPORTS = ROOT / "reports"
for d in (OUT_MASKS, OUT_REPORTS):
    d.mkdir(parents=True, exist_ok=True)

CORE_FRAC = 0.45   # of robust max cyan score -> bright stroke core
# blur-heavy shots where the default threshold merges neighboring parts
CORE_FRAC_OVERRIDES = {"21_neutral_11_manual.png": 0.62}
GLOW_FRAC = 0.16   # of robust max -> outer glow extent
MIN_AREA_FRAC = 0.02  # of largest component
MIN_AREA_ABS = 400    # px at 1600x1024


def cyan_score(bgr: np.ndarray) -> np.ndarray:
    b = bgr[:, :, 0].astype(np.int16)
    g = bgr[:, :, 1].astype(np.int16)
    r = bgr[:, :, 2].astype(np.int16)
    score = np.minimum(g, b) - r
    return np.clip(score, 0, None).astype(np.float32)


def analyze(path: Path) -> dict:
    bgr = cv2.imread(str(path))
    h, w = bgr.shape[:2]
    score = cv2.GaussianBlur(cyan_score(bgr), (0, 0), 2.0)
    robust_max = float(np.percentile(score, 99.95))
    core_frac = CORE_FRAC_OVERRIDES.get(path.name, CORE_FRAC)
    core = (score >= robust_max * core_frac).astype(np.uint8)
    glow = (score >= robust_max * GLOW_FRAC).astype(np.uint8)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    core = cv2.morphologyEx(core, cv2.MORPH_CLOSE, kernel)
    glow = cv2.morphologyEx(glow, cv2.MORPH_CLOSE, kernel)

    # drop specks relative to the largest component
    n, labels, stats, cents = cv2.connectedComponentsWithStats(core, 8)
    if n <= 1:
        return {"file": path.name, "error": "no components"}
    areas = stats[1:, cv2.CC_STAT_AREA]
    biggest = int(areas.max())
    keep = [i + 1 for i, a in enumerate(areas)
            if a >= max(MIN_AREA_ABS, biggest * MIN_AREA_FRAC)]
    core_clean = np.isin(labels, keep).astype(np.uint8)

    # glow restricted to neighborhoods of kept core strokes
    n2, glabels = cv2.connectedComponents(glow, 8)
    glow_keep = np.unique(glabels[core_clean > 0])
    glow_clean = np.isin(glabels, glow_keep[glow_keep > 0]).astype(np.uint8)

    # stroke width from distance transform sampled on the skeleton
    dt = cv2.distanceTransform(core_clean, cv2.DIST_L2, 5)
    skel = skeletonize(core_clean > 0)
    widths = 2.0 * dt[skel]
    stroke_w = float(np.median(widths)) if widths.size else 0.0

    comps = []
    for lab in keep:
        m = labels == lab
        m &= core_clean > 0
        if not m.any():
            continue
        ys, xs = np.nonzero(m)
        comp_skel = skel & m
        cw = 2.0 * dt[comp_skel]
        comps.append({
            "centroid_xy": [float(xs.mean()), float(ys.mean())],
            "bbox_xywh": [int(xs.min()), int(ys.min()),
                          int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)],
            "area": int(m.sum()),
            "stroke_width": float(np.median(cw)) if cw.size else 0.0,
        })
    comps.sort(key=lambda c: (c["centroid_xy"][1], c["centroid_xy"][0]))

    ys, xs = np.nonzero(core_clean)
    gx0, gy0, gx1, gy1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())

    # naive role hints: components whose centroid sits in the top part = eyes
    cy_all = [c["centroid_xy"][1] for c in comps]
    y_split = gy0 + (gy1 - gy0) * 0.55
    eye_cands = [c for c in comps if c["centroid_xy"][1] < y_split]
    eye_cands.sort(key=lambda c: c["centroid_xy"][0])
    eye_row_y = float(np.mean([c["centroid_xy"][1] for c in eye_cands])) if eye_cands else None
    eye_sep = (eye_cands[-1]["centroid_xy"][0] - eye_cands[0]["centroid_xy"][0]
               if len(eye_cands) >= 2 else None)

    cv2.imwrite(str(OUT_MASKS / f"{path.stem}_core.png"), core_clean * 255)
    cv2.imwrite(str(OUT_MASKS / f"{path.stem}_glow.png"), glow_clean * 255)

    # panel: original | mask overlay (core white, glow dim) | components colored
    overlay = bgr.copy()
    overlay[glow_clean > 0] = (90, 90, 40)
    overlay[core_clean > 0] = (255, 255, 255)
    comp_vis = np.zeros_like(bgr)
    rng = np.random.default_rng(7)
    for lab in keep:
        color = tuple(int(v) for v in rng.integers(80, 255, 3))
        comp_vis[(labels == lab) & (core_clean > 0)] = color
    panel = np.hstack([bgr, overlay, comp_vis])
    panel = cv2.resize(panel, (panel.shape[1] // 4, panel.shape[0] // 4))
    label = f"{path.stem}  sw={stroke_w:.1f}px n={len(comps)} rmax={robust_max:.0f}"
    cv2.putText(panel, label, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255), 1, cv2.LINE_AA)

    return {
        "file": path.name,
        "robust_max_score": robust_max,
        "stroke_width_px": stroke_w,
        "glyph_bbox_xywh": [gx0, gy0, gx1 - gx0 + 1, gy1 - gy0 + 1],
        "glyph_centroid_xy": [float(xs.mean()), float(ys.mean())],
        "n_components": len(comps),
        "eye_row_y": eye_row_y,
        "eye_sep": eye_sep,
        "components": comps,
        "_panel": panel,
    }


def main() -> None:
    records = []
    panels = []
    for path in sorted(SRC.glob("*.png")):
        rec = analyze(path)
        panels.append(rec.pop("_panel", None))
        records.append(rec)
        c = rec.get("glyph_centroid_xy", [0, 0])
        print(f"{rec['file']:<32} sw={rec.get('stroke_width_px', 0):6.1f} "
              f"n={rec.get('n_components', 0)} cx={c[0]:7.1f} cy={c[1]:7.1f} "
              f"eyeY={rec.get('eye_row_y') and round(rec['eye_row_y']) } "
              f"eyeSep={rec.get('eye_sep') and round(rec['eye_sep'])}")

    with open(ROOT / "measurements.json", "w") as f:
        json.dump(records, f, indent=1)

    valid = [p for p in panels if p is not None]
    rows = [np.hstack(valid[i:i + 2]) if i + 1 < len(valid)
            else np.hstack([valid[i], np.zeros_like(valid[i])])
            for i in range(0, len(valid), 2)]
    sheet = np.vstack(rows)
    cv2.imwrite(str(OUT_REPORTS / "analysis_contact_sheet.png"), sheet)
    print(f"\nwrote measurements.json + {len(valid)} panels")


if __name__ == "__main__":
    main()
