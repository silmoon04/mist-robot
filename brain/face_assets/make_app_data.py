"""Build app_data.js for the animator: canonical parts + faces + generated
variants (blinks, talk visemes, capsule outlines for stroke<->fill morphs).

Blink design (per user spec): an open eye collapses to only the BOTTOM part
of its shape, still with rounded corners -> we extract the bottom envelope
of the eye outline and emit it as a short stroked curve with the same width.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d

ROOT = Path(__file__).resolve().parent
N_STROKE, N_FILL = 48, 64

lib = json.loads((ROOT / "parts_library.json").read_text())
fcs = json.loads((ROOT / "faces_canonical.json").read_text())
cls = {c["file"].replace(".png", ""): c
       for c in json.loads((ROOT / "classifications.json").read_text())}


def resample(pts: np.ndarray, n: int, closed=False) -> np.ndarray:
    if closed and np.linalg.norm(pts[0] - pts[-1]) > 1e-6:
        pts = np.vstack([pts, pts[:1]])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    keep = np.r_[True, np.diff(d) > 1e-9]
    pts, d = pts[keep], d[keep]
    if d[-1] < 1e-9:
        return np.repeat(pts[:1], n, 0)
    s = np.linspace(0, d[-1], n)
    return np.column_stack([np.interp(s, d, pts[:, 0]),
                            np.interp(s, d, pts[:, 1])])


def stroke_outline(pts: np.ndarray, width: float, n=N_FILL) -> np.ndarray:
    """Capsule outline of a stroked polyline (round caps/joins approx)."""
    pts = resample(np.asarray(pts, float), 40)
    r = width / 2
    d = np.gradient(pts, axis=0)
    L = np.linalg.norm(d, axis=1, keepdims=True)
    L[L < 1e-9] = 1
    t = d / L
    nrm = np.column_stack([-t[:, 1], t[:, 0]])
    up = pts + nrm * r
    dn = pts - nrm * r
    a0 = np.arctan2(nrm[0, 1], nrm[0, 0])
    cap0 = [pts[0] + r * np.array([np.cos(a), np.sin(a)])
            for a in np.linspace(a0, a0 + np.pi, 9)]
    a1 = np.arctan2(-nrm[-1, 1], -nrm[-1, 0])
    cap1 = [pts[-1] + r * np.array([np.cos(a), np.sin(a)])
            for a in np.linspace(a1, a1 + np.pi, 9)]
    outline = np.vstack([up, cap1, dn[::-1], cap0])
    return resample(outline, n, closed=True)


def blink_shape(part: dict) -> tuple[list, float]:
    """Bottom envelope of the eye -> flattened closed-lid curve."""
    pts = np.asarray(part["points"], float)
    w = part["width"] if part["kind"] == "stroke" else 3.2
    if part["kind"] == "stroke":
        sample = pts
    else:
        sample = pts  # outline points already
    x0, x1 = sample[:, 0].min(), sample[:, 0].max()
    span = x1 - x0
    xs = np.linspace(x0 + 0.08 * span, x1 - 0.08 * span, 24)
    ys = []
    for x in xs:
        near = sample[np.abs(sample[:, 0] - x) < span * 0.09]
        ys.append(near[:, 1].max() if len(near) else np.nan)
    ys = np.array(ys)
    ok = ~np.isnan(ys)
    xs, ys = xs[ok], ys[ok]
    ys = gaussian_filter1d(ys, 2.2, mode="nearest")
    # flatten toward the mean so the lid reads as a gentle arc, keep a hint
    # of the original bottom curvature ("circle corners")
    ys = ys.mean() + (ys - ys.mean()) * 0.55
    curve = np.column_stack([xs, ys])
    curve = resample(curve, N_STROKE)
    curve -= curve.mean(0)
    # place lid at the lower third of the original eye
    lid_y = sample[:, 1].mean() + (sample[:, 1].max() - sample[:, 1].mean()) * 0.55
    return (np.round(curve + [0, lid_y], 3)).tolist(), round(w, 2)


# ---------------------------------------------------------------- variants

out_parts = {}
for pid, p in lib.items():
    entry = {"family": p["family"], "kind": p["kind"], "closed": p["closed"],
             "width": p["width"], "points": p["points"]}
    if p["kind"] == "stroke":
        entry["outline"] = np.round(
            stroke_outline(p["points"], max(p["width"], 0.6)), 3).tolist()
    out_parts[pid] = entry

# blink variants for eye parts that appear open anywhere
eye_open = {}
for fc in fcs:
    c = cls[fc["face"]]
    for role in ("eye_L", "eye_R"):
        if role in fc["slots"]:
            pid = fc["slots"][role]["part"]
            eye_open[pid] = eye_open.get(pid, False) or bool(c[role]["open"])

blinks = {}
for pid, is_open in eye_open.items():
    if not is_open:
        continue
    pts, w = blink_shape(lib[pid])
    bid = f"{pid}__blink"
    out_parts[bid] = {"family": "blink", "kind": "stroke", "closed": False,
                      "width": w, "points": pts,
                      "outline": np.round(stroke_outline(pts, w), 3).tolist()}
    blinks[pid] = bid

# ---------------------------------------------------------------- visemes
# built from the robot's own canonical mouth shapes where possible


def find_part(pred):
    for pid, p in lib.items():
        if pred(pid, p):
            return pid
    return None


def ellipse(rx, ry, n=N_FILL):
    t = np.linspace(-np.pi / 2, 1.5 * np.pi, n)
    return np.round(np.column_stack([rx * np.cos(t), ry * np.sin(t)]), 3).tolist()


line_pid = find_part(lambda i, p: p["family"] == "m_line")
oval_pid = find_part(lambda i, p: p["family"] == "m_oval_tall_filled")
rect_pid = find_part(lambda i, p: p["family"] == "m_rounded_rect_filled")
dome_pid = find_part(lambda i, p: p["family"] == "m_dome_filled")
smileD_pid = find_part(lambda i, p: p["family"] == "m_open_smile_filled")

lineW = lib[line_pid]["width"] if line_pid else 3.0
line_pts = lib[line_pid]["points"] if line_pid else \
    np.column_stack([np.linspace(-9, 9, N_STROKE), np.zeros(N_STROKE)]).tolist()

visemes = {
    # closed / rest
    "rest": {"kind": "fill", "points": np.round(
        stroke_outline(line_pts, lineW), 3).tolist()},
    "MBP": {"kind": "fill", "points": np.round(stroke_outline(
        (np.asarray(line_pts) * [0.72, 1.0]).tolist(), lineW), 3).tolist()},
    "FV": {"kind": "fill", "points": np.round(stroke_outline(
        (np.asarray(line_pts) * [0.85, 1.0]).tolist(), lineW * 0.8), 3).tolist()},
}


def scaled_fill(pid, sx, sy):
    pts = np.asarray(lib[pid]["points"], float)
    return np.round(resample(pts * [sx, sy], N_FILL, closed=True), 3).tolist()


visemes["AA"] = {"kind": "fill", "points": scaled_fill(oval_pid, 0.95, 0.9)
                 if oval_pid else ellipse(5.5, 8.0)}
visemes["EH"] = {"kind": "fill", "points": scaled_fill(rect_pid, 1.0, 0.9)
                 if rect_pid else ellipse(6.5, 3.5)}
visemes["EE"] = {"kind": "fill", "points": scaled_fill(rect_pid, 1.25, 0.55)
                 if rect_pid else ellipse(7.5, 2.2)}
visemes["OH"] = {"kind": "fill", "points": ellipse(4.6, 5.6)}
visemes["OO"] = {"kind": "fill", "points": ellipse(3.8, 4.5)}
visemes["S"] = {"kind": "fill", "points": scaled_fill(rect_pid, 0.85, 0.55)
                if rect_pid else ellipse(5.0, 2.0)}
visemes["LNT"] = {"kind": "fill", "points": scaled_fill(dome_pid, 0.8, 0.75)
                  if dome_pid else ellipse(5.0, 4.0)}
visemes["SMILE"] = {"kind": "fill", "points": scaled_fill(smileD_pid, 0.9, 0.85)
                    if smileD_pid else ellipse(6.0, 4.5)}

# ---------------------------------------------------------------- faces

out_faces = []
for fc in fcs:
    c = cls[fc["face"]]
    slots = {}
    for role, e in fc["slots"].items():
        if role == "tears":
            slots["tears"] = e
            continue
        slots[role] = dict(e)
        if role in ("eye_L", "eye_R"):
            slots[role]["open"] = bool(c[role]["open"])
    label = fc["face"].split("_", 1)[1].rsplit("_", 1)[0]
    # talking swaps the mouth for centered visemes anchored near (50, 45.5);
    # if this face's own mouth lives far from there (e.g. up between the
    # eyes), talking on it looks wrong -> the app reverts to neutral first
    m = fc["slots"].get("mouth")
    talk_safe = m is None or (abs(m["x"] - 50) <= 6 and abs(m["y"] - 45.5) <= 7)
    out_faces.append({"id": fc["face"], "name": label,
                      "group": fc["expression"].rstrip("_0123456789"),
                      "talkSafe": talk_safe,
                      "slots": slots})

data = {
    "viewBox": [0, 0, 100, 64],
    "mouthDefault": {"x": 50.0, "y": 45.5},
    "parts": out_parts,
    "blinks": blinks,
    "visemes": visemes,
    "faces": out_faces,
}
js = "window.MIST_DATA = " + json.dumps(data) + ";\n"
app_dir = ROOT / "app"
app_dir.mkdir(exist_ok=True)
(app_dir / "app_data.js").write_text(js)
print(f"parts={len(out_parts)} (incl {len(blinks)} blinks), "
      f"visemes={len(visemes)}, faces={len(out_faces)}, "
      f"size={len(js)//1024}KB")
print("talk-unsafe faces:",
      [f["id"] for f in out_faces if not f["talkSafe"]])
