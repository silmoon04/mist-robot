"""Stage 5: build the canonical, deduplicated part library.

- merges fitted geometry (faces.json) with vision classifications
- mirrors right eyes into left-orientation space, clusters equal shapes
  within a family using rotation-aware Procrustes distance
- canonical shape = rotation-aligned cluster mean (kills hand-jitter);
  per-face placement stores translation + rotation + mirror
- snaps geometric families (circle_gap, arcs, lines, dots) to primitives

Placement semantics (also used by the JS runtime):
  rendered = T + R(rot_deg) @ (Mirror_x if mirror else I) @ canonical_points

Outputs: parts_library.json, faces_canonical.json, fidelity report.
Coordinates in the 100x64 face-local viewBox; strokes = 48 centerline
points, fills = 64 outline points.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
N_STROKE, N_FILL = 48, 64
FACE_CX = 50.0
MAX_ROT = np.radians(40)

faces = json.loads((ROOT / "faces.json").read_text())
cls = {c["file"].replace(".png", ""): c
       for c in json.loads((ROOT / "classifications.json").read_text())}


# ---------------------------------------------------------------- geometry

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


def orient_open(pts: np.ndarray) -> np.ndarray:
    a, b = pts[0], pts[-1]
    if (a[0], a[1]) > (b[0], b[1]):
        return pts[::-1]
    return pts


def orient_closed(pts: np.ndarray) -> np.ndarray:
    i = int(np.argmin(pts[:, 1]))
    pts = np.roll(pts, -i, axis=0)
    area = np.sum((pts[1:, 0] - pts[:-1, 0]) * (pts[1:, 1] + pts[:-1, 1]))
    if area < 0:
        pts = np.vstack([pts[:1], pts[1:][::-1]])
    return pts


def rot_mat(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s], [s, c]])


def kabsch_angle(a: np.ndarray, b: np.ndarray) -> float:
    """Angle rotating b (centered) onto a (centered), clamped."""
    H = b.T @ a
    ang = np.arctan2(H[0, 1] - H[1, 0], H[0, 0] + H[1, 1])
    return float(np.clip(ang, -MAX_ROT, MAX_ROT))


def align(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, float, bool]:
    """Best (rotated_b, angle, reversed) aligning b onto a."""
    a0 = a - a.mean(0)
    best = None
    for rev in (False, True):
        b0 = (b[::-1] if rev else b)
        b0 = b0 - b0.mean(0)
        ang = kabsch_angle(a0, b0)
        rb = b0 @ rot_mat(ang).T
        d = float(np.linalg.norm(a0 - rb, axis=1).mean())
        if best is None or d < best[0]:
            best = (d, rb, ang, rev)
    return best[1], best[2], best[3]


def shape_dist(a: np.ndarray, b: np.ndarray) -> float:
    a0 = a - a.mean(0)
    rb, _, _ = align(a, b)
    return float(np.linalg.norm(a0 - rb, axis=1).mean())


def fit_circle(pts: np.ndarray) -> tuple[np.ndarray, float]:
    A = np.column_stack([pts[:, 0], pts[:, 1], np.ones(len(pts))])
    b = (pts ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = np.sqrt(sol[2] + cx ** 2 + cy ** 2)
    return np.array([cx, cy]), float(r)


def render_shape(pts: np.ndarray, width: float, kind: str) -> np.ndarray:
    S = 8
    img = np.zeros((72 * S, 72 * S), np.uint8)
    ip = np.round((pts - pts.mean(0) + 36) * S).astype(np.int32)
    if kind == "fill":
        cv2.fillPoly(img, [ip], 255)
    else:
        th = max(1, int(round(width * S)))
        cv2.polylines(img, [ip], False, 255, th, cv2.LINE_8)
        cv2.circle(img, tuple(ip[0]), th // 2, 255, -1)
        cv2.circle(img, tuple(ip[-1]), th // 2, 255, -1)
    return img


def render_iou(a, wa, b, wb, kind) -> float:
    ra = render_shape(a, wa, kind) > 0
    rb = render_shape(b, wb, kind) > 0
    return np.logical_and(ra, rb).sum() / max(np.logical_or(ra, rb).sum(), 1)


def straighten(pts: np.ndarray, closed=False, dev_tol=0.42,
               corner_deg=32.0, k=3) -> np.ndarray:
    """Replace nearly-straight runs (photo-extraction wobble) with true
    straight segments; genuine curves deviate from their chord and are
    left untouched."""
    n = len(pts)
    corners = []
    for i in range(n):
        i0, i1 = i - k, i + k
        if not closed and (i0 < 0 or i1 >= n):
            continue
        a = pts[i] - pts[i0 % n]
        b = pts[i1 % n] - pts[i]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-9 or nb < 1e-9:
            continue
        ang = np.degrees(np.arccos(np.clip(np.dot(a, b) / (na * nb), -1, 1)))
        if ang > corner_deg:
            corners.append(i)
    # collapse corner runs to their center
    merged = []
    for c in corners:
        if merged and c - merged[-1] <= k:
            merged[-1] = c
        else:
            merged.append(c)
    bounds = [0] + merged + [n - 1] if not closed else merged + [merged[0] + n] \
        if merged else []
    out = pts.copy()
    if not closed:
        segs = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
    else:
        segs = [(bounds[i] % n, bounds[i + 1]) for i in range(len(bounds) - 1)] \
            if merged else []
    for a, b in segs:
        idx = [j % n for j in range(a, b + 1)]
        if len(idx) < 5:
            continue
        p0, p1 = pts[idx[0]], pts[idx[-1]]
        chord = p1 - p0
        L = np.linalg.norm(chord)
        if L < 1e-9:
            continue
        d = np.abs(np.cross(np.broadcast_to(chord, (len(idx), 2)),
                            pts[idx] - p0)) / L
        if d.max() < dev_tol:
            t = np.linspace(0, 1, len(idx))
            out[idx] = p0 + t[:, None] * chord
    return out


# ---------------------------------------------------------------- collect parts

records = []
for f in faces:
    stem = f["file"]
    c = cls.get(stem)
    for p in f["parts"]:
        if p["kind"] == "none" or not p["points_local"]:
            continue
        role = p["role"]
        if role in ("eye_L", "eye_R"):
            fam = c[role]["family"]
        elif role == "mouth":
            fam = "m_" + c["mouth"]["family"]
        else:
            fam = "tear_bar"
        main = max((np.array(sp) for sp in p["points_local"]), key=len)
        n = N_FILL if p["kind"] == "fill" else N_STROKE
        pts = resample(main, n, closed=p["closed"])
        pts = orient_closed(pts) if p["closed"] else orient_open(pts)
        rec = {
            "face": stem, "role": role, "family": fam, "kind": p["kind"],
            "closed": p["closed"], "width": p["stroke_width_local"],
            "pts": pts, "centroid": pts.mean(0),
        }
        shape = pts - rec["centroid"]
        if role == "eye_R":
            m = shape.copy()
            m[:, 0] = -m[:, 0]
            shape = orient_closed(m) if p["closed"] else orient_open(m)
        rec["shape"] = shape
        records.append(rec)

# unify dots regardless of how they were fitted
for r in records:
    if r["family"] == "m_dot":
        if r["kind"] == "fill":
            rad = float(np.linalg.norm(r["shape"], axis=1).mean())
        else:
            rad = max(r["width"] / 2, 0.9)
        r["dot_radius"] = rad
        r["kind"] = "fill"
        r["closed"] = True
        t = np.linspace(0, 2 * np.pi, N_FILL)
        r["shape"] = np.column_stack([rad * np.cos(t), rad * np.sin(t)])
        r["pts"] = r["shape"] + r["centroid"]
        r["width"] = 0.0

# ---------------------------------------------------------------- cluster

groups: dict[str, list[int]] = {}
for i, r in enumerate(records):
    key = f'{r["family"]}|{r["kind"]}'
    groups.setdefault(key, []).append(i)


def greedy_cluster(idxs: list[int], tol: float) -> list[list[int]]:
    out = []
    pool = list(idxs)
    while pool:
        seed = pool.pop(0)
        members = [seed]
        for j in list(pool):
            if shape_dist(records[seed]["shape"], records[j]["shape"]) < tol:
                members.append(j)
                pool.remove(j)
        out.append(members)
    return out


def mean_of(members: list[int]) -> np.ndarray:
    base = records[members[0]]["shape"]
    base = base - base.mean(0)
    aligned = [base]
    for i in members[1:]:
        rb, _, _ = align(base, records[i]["shape"])
        aligned.append(rb)
    return np.mean(aligned, axis=0)


clusters: list[dict] = []
for key, idxs in sorted(groups.items()):
    kind = records[idxs[0]]["kind"]
    membership = greedy_cluster(idxs, tol=1.6)
    for _ in range(3):
        changed = False
        refined = []
        ejected: list[int] = []
        for members in membership:
            if len(members) == 1:
                refined.append(members)
                continue
            mean_shape = mean_of(members)
            w = float(np.median([records[i]["width"] for i in members]))
            keep = []
            for i in members:
                rb, _, _ = align(mean_shape, records[i]["shape"])
                iou = render_iou(mean_shape, w, rb, records[i]["width"], kind)
                (keep if iou >= 0.82 else ejected).append(i)
            if not keep:
                keep = [members[0]]
                ejected.remove(members[0])
            if len(keep) != len(members):
                changed = True
            refined.append(keep)
        if ejected:
            refined.extend(greedy_cluster(ejected, tol=0.9))
        membership = refined
        if not changed:
            break
    for members in membership:
        clusters.append({"key": key, "members": members})

# ---------------------------------------------------------------- canonical parts

parts_library: dict[str, dict] = {}
for ci, cl in enumerate(clusters):
    mem = [records[i] for i in cl["members"]]
    mean_shape = mean_of(cl["members"])
    fam = cl["key"].split("|")[0]
    kind = mem[0]["kind"]
    closed = mem[0]["closed"]
    width = float(np.median([r["width"] for r in mem]))

    def guarded(snapped: np.ndarray) -> np.ndarray:
        """Accept a primitive snap only if it stays close to the mean."""
        if render_iou(mean_shape, width, snapped, width, kind) >= 0.86:
            return snapped
        return mean_shape

    if fam == "m_dot":
        rad = float(np.mean([r["dot_radius"] for r in mem]))
        t = np.linspace(0, 2 * np.pi, N_FILL)
        mean_shape = np.column_stack([rad * np.cos(t), rad * np.sin(t)])
    elif fam == "circle_gap" and not closed:
        c0, rad = fit_circle(mean_shape)
        ang = np.unwrap(np.arctan2(mean_shape[:, 1] - c0[1],
                                   mean_shape[:, 0] - c0[0]))
        t = np.linspace(ang[0], ang[-1], N_STROKE)
        arc = np.column_stack([c0[0] + rad * np.cos(t),
                               c0[1] + rad * np.sin(t)])
        mean_shape = guarded(arc - arc.mean(0))
    elif fam in ("closed_lid_arc", "happy_arc", "m_smile_arc",
                 "m_frown_arc") and not closed:
        c0, rad = fit_circle(mean_shape)
        ang = np.unwrap(np.arctan2(mean_shape[:, 1] - c0[1],
                                   mean_shape[:, 0] - c0[0]))
        if abs(ang[-1] - ang[0]) < np.pi * 1.6:
            t = np.linspace(ang[0], ang[-1], N_STROKE)
            arc = np.column_stack([c0[0] + rad * np.cos(t),
                                   c0[1] + rad * np.sin(t)])
            mean_shape = guarded(arc - arc.mean(0))
    elif fam in ("m_line", "flat_bar") and not closed:
        p0, p1 = mean_shape[0], mean_shape[-1]
        tilt = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
        if abs(tilt) < 5 or abs(abs(tilt) - 180) < 5:
            L = float(np.linalg.norm(p1 - p0))
            mean_shape = np.column_stack([
                np.linspace(-L / 2, L / 2, N_STROKE), np.zeros(N_STROKE)])
    elif kind == "fill":
        m = mean_shape.copy()
        m[:, 0] = -m[:, 0]
        m = orient_closed(m)
        if np.linalg.norm(m - mean_shape, axis=1).mean() < 2.2:
            mean_shape = (mean_shape + m) / 2

    if kind == "stroke":
        mean_shape = straighten(mean_shape)

    pid = f"{fam.replace('m_', 'mouth_')}_{ci:02d}"
    parts_library[pid] = {
        "family": fam, "kind": kind, "closed": closed,
        "width": round(width, 2),
        "points": np.round(mean_shape - mean_shape.mean(0), 3).tolist(),
    }
    cl["pid"] = pid

# the physical display draws every stroke at the same width; pull
# blur-inflated outliers back toward the global median
stroke_ws = [p["width"] for p in parts_library.values()
             if p["kind"] == "stroke" and p["width"] > 0]
w_med = float(np.median(stroke_ws))
for p in parts_library.values():
    if p["kind"] == "stroke" and p["width"] > 0:
        p["width"] = round(float(np.clip(p["width"],
                                         0.90 * w_med, 1.08 * w_med)), 2)

pid_of = {i: cl["pid"] for cl in clusters for i in cl["members"]}

# ---------------------------------------------------------------- placements

by_face: dict[str, list[int]] = {}
for i, r in enumerate(records):
    by_face.setdefault(r["face"], []).append(i)

faces_canonical = []
for f in faces:
    stem = f["file"]
    idxs = by_face.get(stem, [])
    slots: dict = {}
    tears = []
    eyeL = next((i for i in idxs if records[i]["role"] == "eye_L"), None)
    eyeR = next((i for i in idxs if records[i]["role"] == "eye_R"), None)
    exL = records[eyeL]["centroid"] if eyeL is not None else None
    exR = records[eyeR]["centroid"] if eyeR is not None else None
    if exL is not None and exR is not None:
        sep = (exR[0] - exL[0]) / 2
        same_y = abs(exL[1] - exR[1]) < 1.6
        ey = (exL[1] + exR[1]) / 2
        exL_s = np.array([FACE_CX - sep, ey if same_y else exL[1]])
        exR_s = np.array([FACE_CX + sep, ey if same_y else exR[1]])
    else:
        exL_s, exR_s = exL, exR

    for i in idxs:
        r = records[i]
        canon = np.array(parts_library[pid_of[i]]["points"], float)
        _, ang, _ = align(canon, r["shape"])
        rot = -np.degrees(ang) if r["role"] == "eye_R" else np.degrees(ang)
        pos = r["centroid"]
        if r["role"] == "eye_L" and exL_s is not None:
            pos = exL_s
        elif r["role"] == "eye_R" and exR_s is not None:
            pos = exR_s
        entry = {"part": pid_of[i],
                 "x": round(float(pos[0]), 2), "y": round(float(pos[1]), 2),
                 "rot": round(float(-rot), 2),
                 "mirror": r["role"] == "eye_R"}
        if r["role"] == "tear":
            tears.append(entry)
        else:
            slots[r["role"]] = entry
    if tears:
        slots["tears"] = tears
    faces_canonical.append({"face": stem, "expression": f["expression"],
                            "slots": slots})

# ---------------------------------------------------------------- fidelity


def render_face(fc: dict, size=(1024, 1600)) -> np.ndarray:
    img = np.zeros(size, np.uint8)
    entries = []
    for role, entry in fc["slots"].items():
        entries.extend(entry if role == "tears" else [entry])
    for e in entries:
        part = parts_library[e["part"]]
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
            cv2.polylines(img, [ip], False, 255, th, cv2.LINE_8)
            cv2.circle(img, tuple(ip[0]), th // 2, 255, -1)
            cv2.circle(img, tuple(ip[-1]), th // 2, 255, -1)
    return img


(ROOT / "parts_library.json").write_text(json.dumps(parts_library, indent=1))

print(f"{len(records)} placed parts -> {len(parts_library)} canonical parts")
for key in sorted(groups):
    cls_of = [c for c in clusters if c["key"] == key]
    sizes = [len(c["members"]) for c in cls_of]
    print(f"  {key:<28} clusters={len(cls_of)} sizes={sizes}")

ious = []
for fc in faces_canonical:
    img = render_face(fc)
    target = cv2.imread(str(ROOT / "normalized" / f'{fc["face"]}_core.png'), 0) > 127
    iou = np.logical_and(img > 0, target).sum() / max(
        np.logical_or(img > 0, target).sum(), 1)
    ious.append(iou)
    fc["canonical_iou"] = round(float(iou), 3)

(ROOT / "faces_canonical.json").write_text(json.dumps(faces_canonical, indent=1))
print(f"\ncanonical fidelity: mean IoU={np.mean(ious):.3f} min={np.min(ious):.3f}")
worst = sorted(zip([f["face"] for f in faces_canonical],
                   [round(i, 3) for i in ious]), key=lambda t: t[1])[:6]
print("worst:", worst)
