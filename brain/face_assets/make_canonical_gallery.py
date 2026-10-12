"""Render canonical faces with neon glow; build side-by-side gallery
(original photo | cleaned re-render | canonical) for visual verification."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "isolated_screens_highres"
OUT = ROOT / "canonical_renders"
CMP = ROOT / "compare"
OUT.mkdir(exist_ok=True)
CMP.mkdir(exist_ok=True)

W, H = 1600, 1024
lib = json.loads((ROOT / "parts_library.json").read_text())
fcs = json.loads((ROOT / "faces_canonical.json").read_text())

CORE_BGR = np.array([205, 232, 90], dtype=np.float32)
GLOW_BGR = np.array([120, 110, 10], dtype=np.float32)
HOT_BGR = np.array([245, 255, 210], dtype=np.float32)


def rot_mat(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s], [s, c]])


def face_mask(fc) -> np.ndarray:
    img = np.zeros((H, W), np.uint8)
    entries = []
    for role, entry in fc["slots"].items():
        entries.extend(entry if role == "tears" else [entry])
    for e in entries:
        part = lib[e["part"]]
        pts = np.array(part["points"], float)
        if e["mirror"]:
            pts = pts.copy()
            pts[:, 0] = -pts[:, 0]
        pts = pts @ rot_mat(np.radians(e["rot"])).T
        pts = (pts + np.array([e["x"], e["y"]])) * 16.0
        ip = np.round(pts).astype(np.int32)
        if part["kind"] == "fill":
            cv2.fillPoly(img, [ip], 255)
        else:
            th = max(1, int(round(part["width"] * 16)))
            cv2.polylines(img, [ip], False, 255, th, cv2.LINE_AA)
            cv2.circle(img, tuple(ip[0]), th // 2, 255, -1)
            cv2.circle(img, tuple(ip[-1]), th // 2, 255, -1)
    return img


def render_neon(mask: np.ndarray) -> np.ndarray:
    core = (mask > 127).astype(np.float32)
    img = np.zeros((H, W, 3), np.float32)
    glow = cv2.GaussianBlur(core, (0, 0), 16)
    glow /= max(glow.max(), 1e-6)
    img += GLOW_BGR * glow[..., None] * 1.5
    soft = cv2.GaussianBlur(core, (0, 0), 1.2)
    img += CORE_BGR * np.clip(soft, 0, 1)[..., None]
    hot = cv2.erode((core > 0.5).astype(np.uint8), np.ones((9, 9), np.uint8))
    hot = cv2.GaussianBlur(hot.astype(np.float32), (0, 0), 4)
    img += HOT_BGR * hot[..., None] * 0.30
    return np.clip(img, 0, 255).astype(np.uint8)


panels = []
for fc in fcs:
    name = fc["face"]
    canon = render_neon(face_mask(fc))
    cv2.imwrite(str(OUT / f"{name}.png"), canon)
    orig = cv2.imread(str(SRC / f"{name}.png"))
    clean = cv2.imread(str(ROOT / "cleaned" / f"{name}.png"))
    row = np.hstack([orig, clean, canon])
    row = cv2.resize(row, (row.shape[1] // 3, row.shape[0] // 3))
    cv2.putText(row, f"{name}  orig | cleaned | canonical", (8, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imwrite(str(CMP / f"{name}.png"), row)
    panels.append(row)

rows = [np.vstack(panels[i:i + 8]) for i in range(0, len(panels), 8)]
for k, r in enumerate(rows):
    cv2.imwrite(str(ROOT / "reports" / f"canonical_gallery_{k}.png"), r)
print(f"wrote {len(panels)} comparison panels + {len(rows)} gallery sheets")
