"""Stage 2: assign part roles, normalize geometry, re-render cleaned faces.

Normalization: uniform scale so eye separation = 700px, then translate so the
eye midpoint sits at (800, 470) in the 1600x1024 frame. Roles: two largest
top-region components are eyes; thin vertical bars near eye height are tears;
the rest is the mouth.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
MASKS = ROOT / "masks"
OUT_NORM = ROOT / "normalized"
OUT_CLEAN = ROOT / "cleaned"
OUT_REPORTS = ROOT / "reports"
for d in (OUT_NORM, OUT_CLEAN, OUT_REPORTS):
    d.mkdir(parents=True, exist_ok=True)

W, H = 1600, 1024
EYE_SEP_TARGET = 700.0
EYE_MID_TARGET = (800.0, 470.0)

# manual role overrides: file -> list of roles matching component order in
# measurements.json (sorted by centroid y, then x)
OVERRIDES: dict[str, list[str]] = {}

CORE_BGR = np.array([205, 232, 90], dtype=np.float32)    # bright cyan
GLOW_BGR = np.array([120, 110, 10], dtype=np.float32)    # dim teal halo
HOT_BGR = np.array([245, 255, 210], dtype=np.float32)    # near-white core


def assign_roles(rec: dict) -> list[str]:
    comps = rec["components"]
    if rec["file"] in OVERRIDES:
        return OVERRIDES[rec["file"]]
    gx, gy, gw, gh = rec["glyph_bbox_xywh"]
    sw = rec["stroke_width_px"]
    n = len(comps)
    roles = ["?"] * n
    if n == 2:
        return ["eye_L", "eye_R"] if comps[0]["centroid_xy"][0] < comps[1]["centroid_xy"][0] else ["eye_R", "eye_L"]
    # eyes = the pair that looks most like a symmetric, similar pair at
    # plausible separation; robust against big filled mouths
    best, best_score = None, -1.0
    for i in range(n):
        for j in range(i + 1, n):
            ci, cj = comps[i], comps[j]
            dy = abs(ci["centroid_xy"][1] - cj["centroid_xy"][1]) / max(gh, 1)
            sep = abs(ci["centroid_xy"][0] - cj["centroid_xy"][0])
            if not 350 <= sep <= 1000:
                continue
            ar = min(ci["area"], cj["area"]) / max(ci["area"], cj["area"])
            score = (np.exp(-4.0 * dy) * (0.4 + 0.6 * ar)
                     * np.exp(-0.5 * ((sep - 700) / 300) ** 2))
            if score > best_score:
                best, best_score = (i, j), score
    if best is None:
        best = (0, min(1, n - 1))
    eyes = sorted(best, key=lambda i: comps[i]["centroid_xy"][0])
    roles[eyes[0]] = "eye_L"
    roles[eyes[1]] = "eye_R"
    rest = [i for i in range(n) if roles[i] == "?"]
    mouth_pick = None
    for i in rest:
        x, y, w, h = comps[i]["bbox_xywh"]
        thin_vertical = h / max(w, 1) > 2.0 and w < 1.6 * sw
        if thin_vertical:
            roles[i] = "tear"
        else:
            roles[i] = "mouth" if mouth_pick is None else "extra"
            mouth_pick = i
    return roles


def transform_for(rec: dict, roles: list[str]) -> tuple[float, float, float]:
    comps = rec["components"]
    eyes = [comps[i] for i, r in enumerate(roles) if r in ("eye_L", "eye_R")]
    sw = rec["stroke_width_px"]
    if len(eyes) == 2:
        sep = abs(eyes[1]["centroid_xy"][0] - eyes[0]["centroid_xy"][0])
        scale = EYE_SEP_TARGET / sep if sep > 100 else 52.0 / sw
        mx = (eyes[0]["centroid_xy"][0] + eyes[1]["centroid_xy"][0]) / 2
        my = (eyes[0]["centroid_xy"][1] + eyes[1]["centroid_xy"][1]) / 2
    else:
        scale = 52.0 / sw
        mx, my = rec["glyph_centroid_xy"]
    scale = float(np.clip(scale, 0.55, 1.75))
    tx = EYE_MID_TARGET[0] - mx * scale
    ty = EYE_MID_TARGET[1] - my * scale
    return scale, tx, ty


def smooth_mask(mask: np.ndarray, sigma: float) -> np.ndarray:
    f = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)
    return (f >= 0.5).astype(np.uint8)


def render_clean(core: np.ndarray) -> np.ndarray:
    img = np.zeros((H, W, 3), np.float32)
    glow = cv2.GaussianBlur(core.astype(np.float32), (0, 0), 16)
    glow /= max(glow.max(), 1e-6)
    img += GLOW_BGR * glow[..., None] * 1.5
    soft = cv2.GaussianBlur(core.astype(np.float32), (0, 0), 1.2)
    img += CORE_BGR * np.clip(soft, 0, 1)[..., None]
    hot = cv2.erode(core, np.ones((9, 9), np.uint8))
    hot = cv2.GaussianBlur(hot.astype(np.float32), (0, 0), 4)
    img += HOT_BGR * hot[..., None] * 0.30
    return np.clip(img, 0, 255).astype(np.uint8)


def main() -> None:
    records = json.loads((ROOT / "measurements.json").read_text())
    out = []
    panels = []
    role_colors = {"eye_L": (255, 160, 60), "eye_R": (160, 100, 255),
                   "mouth": (80, 220, 255), "tear": (255, 255, 120),
                   "extra": (0, 0, 255), "?": (128, 128, 128)}
    for rec in records:
        name = Path(rec["file"]).stem
        roles = assign_roles(rec)
        scale, tx, ty = transform_for(rec, roles)
        M = np.array([[scale, 0, tx], [0, scale, ty]], np.float32)

        core = (cv2.imread(str(MASKS / f"{name}_core.png"), 0) > 127).astype(np.uint8)
        sw_n = rec["stroke_width_px"] * scale
        core_n = cv2.warpAffine(core, M, (W, H), flags=cv2.INTER_LINEAR)
        core_n = smooth_mask(core_n, max(1.5, sw_n / 9.0))
        cv2.imwrite(str(OUT_NORM / f"{name}_core.png"), core_n * 255)

        clean = render_clean(core_n)
        cv2.imwrite(str(OUT_CLEAN / f"{name}.png"), clean)

        # role panel in normalized space
        vis = np.zeros((H, W, 3), np.uint8)
        n, labels = cv2.connectedComponents(core_n, 8)
        # map normalized centroids to roles by transforming original centroids
        role_pts = []
        for c, r in zip(rec["components"], roles):
            cx, cy = c["centroid_xy"]
            role_pts.append((cx * scale + tx, cy * scale + ty, r))
        for lab in range(1, n):
            m = labels == lab
            ys, xs = np.nonzero(m)
            mx, my = xs.mean(), ys.mean()
            best = min(role_pts, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
            vis[m] = role_colors.get(best[2], (128, 128, 128))
        panel = np.hstack([clean, vis])
        panel = cv2.resize(panel, (panel.shape[1] // 4, panel.shape[0] // 4))
        cv2.putText(panel, f"{name} s={scale:.2f} roles={','.join(roles)}",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        panels.append(panel)

        out.append({**{k: v for k, v in rec.items() if k != "components"},
                    "components": [{**c, "role": r} for c, r in zip(rec["components"], roles)],
                    "norm_scale": scale, "norm_tx": tx, "norm_ty": ty,
                    "norm_stroke_width_px": sw_n})
        print(f"{name:<30} s={scale:.2f} sw_n={sw_n:5.1f} roles={roles}")

    (ROOT / "measurements_normalized.json").write_text(json.dumps(out, indent=1))
    rows = [np.hstack(panels[i:i + 2]) if i + 1 < len(panels)
            else np.hstack([panels[i], np.zeros_like(panels[i])])
            for i in range(0, len(panels), 2)]
    sheet = np.vstack(rows)
    cv2.imwrite(str(OUT_REPORTS / "normalized_roles_sheet.png"), sheet)
    h = sheet.shape[0] // 4
    for i in range(4):
        cv2.imwrite(str(OUT_REPORTS / f"norm_q{i}.png"), sheet[i * h:(i + 1) * h])
    print("wrote normalized masks, cleaned renders, measurements_normalized.json")


if __name__ == "__main__":
    main()
