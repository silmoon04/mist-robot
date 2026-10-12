"""Stage 4: fit smooth vector paths to each face part and verify fidelity.

Stroked parts: skeleton -> pruned graph -> ordered centerline -> smoothed,
corner-split, cubic-bezier fitted (Schneider). Filled parts: outer contour ->
smoothed closed bezier chain. Coordinates are fitted in original image space,
then mapped through the normalization transform, and finally emitted in the
100x64 face-local viewBox (1/16 of the 1600x1024 frame).

Outputs per face: svg/<name>.svg, face JSON in faces.json, and IoU metrics
against the normalized core mask.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from skimage.morphology import skeletonize

ROOT = Path(__file__).resolve().parent
MASKS = ROOT / "masks"
NORM = ROOT / "normalized"
OUT_SVG = ROOT / "svg"
OUT_REPORTS = ROOT / "reports"
OUT_SVG.mkdir(exist_ok=True)

W, H = 1600, 1024

# ---------------------------------------------------------------- skeleton graph

NB8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def skeleton_graph(skel: np.ndarray):
    """Return (nodes, edges): nodes are junction/end pixels, edges are pixel chains."""
    pts = set(zip(*np.nonzero(skel)))
    deg = {}
    for p in pts:
        deg[p] = sum((p[0] + dy, p[1] + dx) in pts for dy, dx in NB8)
    nodes = {p for p, d in deg.items() if d != 2}
    if not nodes and pts:  # pure cycle
        nodes = {next(iter(pts))}
    edges = []
    visited = set()
    for n in nodes:
        for dy, dx in NB8:
            q = (n[0] + dy, n[1] + dx)
            if q not in pts:
                continue
            step = frozenset((n, q))
            if step in visited:
                continue
            chain = [n, q]
            visited.add(step)
            prev, cur = n, q
            while cur not in nodes:
                nxt = None
                for dy2, dx2 in NB8:
                    r = (cur[0] + dy2, cur[1] + dx2)
                    if r in pts and r != prev and frozenset((cur, r)) not in visited:
                        nxt = r
                        break
                if nxt is None:
                    break
                visited.add(frozenset((cur, nxt)))
                chain.append(nxt)
                prev, cur = cur, nxt
            edges.append(chain)
    return nodes, edges


def prune_and_trace(skel: np.ndarray, min_spur: float) -> list[np.ndarray]:
    """Prune short spurs, then trace ordered centerline(s) as (x, y) arrays."""
    sk = skel.copy()
    for _ in range(6):
        nodes, edges = skeleton_graph(sk)
        deg_count = defaultdict(int)
        for ch in edges:
            deg_count[ch[0]] += 1
            deg_count[ch[-1]] += 1
        removed = False
        for ch in edges:
            a, b = ch[0], ch[-1]
            length = len(ch)
            a_end, b_end = deg_count[a] == 1, deg_count[b] == 1
            if length < min_spur and (a_end != b_end):  # spur off a junction
                for p in ch[:-1] if b_end is False else ch[1:]:
                    if p != a and p != b:
                        sk[p] = False
                # also drop the free endpoint itself
                sk[a if a_end else b] = False
                removed = True
        if not removed:
            break

    nodes, edges = skeleton_graph(sk)
    if not edges:
        return []
    chains = [np.array([(x, y) for y, x in ch], float) for ch in edges]
    if len(edges) == 1:
        return [chains[0]]

    # Eulerian walk (Hierholzer): these glyphs are single pen strokes, so
    # visiting every skeleton edge once recovers the drawing order — this
    # keeps both chevron legs and closes the 'e' loop.
    adj: dict[tuple, list[int]] = defaultdict(list)
    for i, ch in enumerate(edges):
        adj[ch[0]].append(i)
        adj[ch[-1]].append(i)
    odd = [v for v, es in adj.items() if len(es) % 2 == 1]
    used = [False] * len(edges)

    def walk(start: tuple) -> list[np.ndarray]:
        stack = [(start, None)]
        pieces: list[np.ndarray] = []
        cur = start
        while True:
            pick = None
            for i in adj[cur]:
                if not used[i]:
                    pick = i
                    break
            if pick is None:
                break
            used[pick] = True
            rev = edges[pick][-1] == cur and edges[pick][0] != cur
            seg = chains[pick][::-1] if rev else chains[pick]
            pieces.append(seg if not pieces else seg[1:])
            cur = edges[pick][0] if rev else edges[pick][-1]
        return pieces

    start = odd[0] if len(odd) in (1, 2) else max(
        adj, key=lambda v: sum(len(chains[i]) for i in adj[v]))
    pieces = walk(start)
    paths = [np.vstack(pieces)] if pieces else []
    # any disconnected leftovers become their own subpaths
    for i, ch in enumerate(edges):
        if not used[i]:
            more = walk(ch[0])
            if more:
                paths.append(np.vstack(more))
    return [p for p in paths if len(p) >= 3]


def stitch_paths(paths: list[np.ndarray], tol: float,
                 sw: float = 0.0) -> list[np.ndarray]:
    """Merge fragments into pen strokes.

    - endpoint-to-endpoint joins between long fragments; at sharp joins the
      medial-axis bisector spur (a short fragment poking into the corner
      tip) supplies the true corner point and is consumed
    - open-path onto closed-loop joins by cutting the loop at the junction
      (the 'e' glyph topology: tail + ring)
    """
    paths = list(paths)
    min_long = max(tol, 2.0 * sw)

    def frag_len(p):
        return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())

    while len(paths) > 1:
        longs = [k for k, p in enumerate(paths) if frag_len(p) >= min_long]
        best = None
        for i in longs:
            for j in longs:
                if j <= i:
                    continue
                for ei, pi in ((0, paths[i][0]), (1, paths[i][-1])):
                    for ej, pj in ((0, paths[j][0]), (1, paths[j][-1])):
                        d = float(np.linalg.norm(pi - pj))
                        if d < tol and (best is None or d < best[0]):
                            best = (d, i, j, ei, ej)
        if not best:
            break
        _, i, j, ei, ej = best
        a = paths[i] if ei == 1 else paths[i][::-1]
        b = paths[j] if ej == 0 else paths[j][::-1]
        join = (a[-1] + b[0]) / 2
        # corner hint: a short spur fragment whose near end sits at the join
        corner, spur_idx = None, None
        for k, p in enumerate(paths):
            if k in (i, j) or frag_len(p) >= min_long:
                continue
            d0 = float(np.linalg.norm(p[0] - join))
            d1 = float(np.linalg.norm(p[-1] - join))
            if min(d0, d1) < max(tol, sw):
                corner = p[-1] if d0 < d1 else p[0]
                spur_idx = k
                break
        merged = np.vstack([a, corner[None], b]) if corner is not None \
            else np.vstack([a, b])
        paths = [p for k, p in enumerate(paths)
                 if k not in (i, j) and k != spur_idx]
        paths.append(merged)

    # open-path -> loop joins
    while len(paths) > 1:
        loops = [k for k, p in enumerate(paths)
                 if np.linalg.norm(p[0] - p[-1]) < 3.0]
        opens = [k for k in range(len(paths)) if k not in loops]
        best = None
        for i in opens:
            for j in loops:
                for ei, pi in ((0, paths[i][0]), (1, paths[i][-1])):
                    d = np.linalg.norm(paths[j] - pi, axis=1)
                    k = int(d.argmin())
                    if d[k] < tol and (best is None or d[k] < best[0]):
                        best = (float(d[k]), i, j, ei, k)
        if not best:
            break
        _, i, j, ei, k = best
        a = paths[i] if ei == 1 else paths[i][::-1]
        loop = paths[j]
        if np.linalg.norm(loop[0] - loop[-1]) < 3.0 and len(loop) > 1:
            loop = loop[:-1]
        cut = np.roll(loop, -k, axis=0)
        merged = np.vstack([a, cut, cut[:1]])
        paths = [p for m, p in enumerate(paths) if m not in (i, j)]
        paths.append(merged)
    return paths


def drop_spurs(paths: list[np.ndarray], sw: float) -> list[np.ndarray]:
    """Drop short fragments (medial-axis bisector spurs) next to a
    dominant stroke."""
    if len(paths) < 2:
        return paths
    lens = [float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())
            for p in paths]
    main = max(lens)
    return [p for p, L in zip(paths, lens)
            if L >= 2.0 * sw or L >= main / 2.5] or paths


def raster_paths(paths: list[np.ndarray], width: float, shape: tuple) -> np.ndarray:
    img = np.zeros(shape, np.uint8)
    th = max(1, int(round(width)))
    for p in paths:
        ip = np.round(p).astype(np.int32)
        cv2.polylines(img, [ip], False, 255, th, cv2.LINE_8)
        r = th // 2
        cv2.circle(img, tuple(ip[0]), r, 255, -1)
        cv2.circle(img, tuple(ip[-1]), r, 255, -1)
    return img


# ---------------------------------------------------------------- bezier fitting

def fit_cubic(points: np.ndarray, max_err: float) -> list[np.ndarray]:
    """Schneider-style piecewise cubic fit. Returns list of [p0,c1,c2,p3]."""

    def bezier_point(bz, t):
        mt = 1 - t
        return (mt ** 3)[:, None] * bz[0] + 3 * (mt ** 2 * t)[:, None] * bz[1] + \
               3 * (mt * t ** 2)[:, None] * bz[2] + (t ** 3)[:, None] * bz[3]

    def chord_params(pts):
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
        return d / max(d[-1], 1e-9)

    def generate(pts, u, t0, t1):
        n = len(pts)
        A = np.zeros((n, 2, 2))
        A[:, 0] = t0 * (3 * (1 - u) ** 2 * u)[:, None]
        A[:, 1] = t1 * (3 * (1 - u) * u ** 2)[:, None]
        C = np.zeros((2, 2))
        X = np.zeros(2)
        p0, p3 = pts[0], pts[-1]
        base = ((1 - u) ** 3)[:, None] * p0 + (3 * (1 - u) ** 2 * u)[:, None] * p0 + \
               (3 * (1 - u) * u ** 2)[:, None] * p3 + (u ** 3)[:, None] * p3
        tmp = pts - base
        C[0, 0] = (A[:, 0] * A[:, 0]).sum()
        C[0, 1] = C[1, 0] = (A[:, 0] * A[:, 1]).sum()
        C[1, 1] = (A[:, 1] * A[:, 1]).sum()
        X[0] = (A[:, 0] * tmp).sum()
        X[1] = (A[:, 1] * tmp).sum()
        det = C[0, 0] * C[1, 1] - C[0, 1] * C[1, 0]
        if abs(det) > 1e-12:
            a1 = (X[0] * C[1, 1] - X[1] * C[0, 1]) / det
            a2 = (C[0, 0] * X[1] - C[1, 0] * X[0]) / det
        else:
            a1 = a2 = 0.0
        seg_len = np.linalg.norm(p3 - p0)
        eps = 1e-6 + 0.01 * seg_len
        if a1 < eps or a2 < eps:
            a1 = a2 = seg_len / 3.0
        return np.array([p0, p0 + t0 * a1, p3 + t1 * a2, p3])

    def max_error(pts, bz, u):
        pt = bezier_point(bz, u)
        errs = np.linalg.norm(pt - pts, axis=1)
        i = int(errs.argmax())
        return errs[i], i

    def tangent(pts, i, forward):
        j = min(len(pts) - 1, i + 4) if forward else max(0, i - 4)
        v = pts[j] - pts[i] if forward else pts[i] - pts[j]
        n = np.linalg.norm(v)
        return v / n if n > 1e-9 else np.array([1.0, 0.0])

    def rec(pts, t0, t1, depth=0):
        if len(pts) == 2:
            d = np.linalg.norm(pts[1] - pts[0]) / 3
            return [np.array([pts[0], pts[0] + t0 * d, pts[1] + t1 * d, pts[1]])]
        u = chord_params(pts)
        bz = generate(pts, u, t0, t1)
        err, split = max_error(pts, bz, u)
        if err < max_err:
            return [bz]
        if depth > 24 or len(pts) < 4:
            return [bz]
        split = int(np.clip(split, 1, len(pts) - 2))
        tc = tangent(pts, split, False)
        return rec(pts[:split + 1], t0, tc, depth + 1) + \
            rec(pts[split:], -tc, t1, depth + 1)

    t0 = tangent(points, 0, True)
    t1 = tangent(points, len(points) - 1, False)
    return rec(points, t0, t1)


def smooth_resample(pts: np.ndarray, sigma: float, n: int, closed=False) -> np.ndarray:
    if closed:
        sm = np.column_stack([
            gaussian_filter1d(pts[:, 0], sigma, mode="wrap"),
            gaussian_filter1d(pts[:, 1], sigma, mode="wrap")])
        sm = np.vstack([sm, sm[:1]])
    else:
        sm = np.column_stack([
            gaussian_filter1d(pts[:, 0], sigma, mode="nearest"),
            gaussian_filter1d(pts[:, 1], sigma, mode="nearest")])
        # smoothing retracts curved tips; push each endpoint back out along
        # its tangent by the distance it actually moved
        if len(sm) >= 6:
            e0 = min(float(np.linalg.norm(pts[0] - sm[0])), 2.0 * sigma)
            e1 = min(float(np.linalg.norm(pts[-1] - sm[-1])), 2.0 * sigma)
            t0 = sm[0] - sm[4]
            t1 = sm[-1] - sm[-5]
            n0, n1 = np.linalg.norm(t0), np.linalg.norm(t1)
            if n0 > 1e-6 and e0 > 0.5:
                sm = np.vstack([sm[0] + t0 / n0 * e0, sm])
            if n1 > 1e-6 and e1 > 0.5:
                sm = np.vstack([sm, sm[-1] + t1 / n1 * e1])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(sm, axis=0), axis=1))]
    if d[-1] < 1e-6:
        return sm[:1].repeat(n, 0)
    t = np.linspace(0, d[-1], n)
    return np.column_stack([np.interp(t, d, sm[:, 0]), np.interp(t, d, sm[:, 1])])


def find_corners(pts: np.ndarray, closed=False, k=4, thresh_deg=48.0) -> list[int]:
    n = len(pts)
    ang = np.zeros(n)
    for i in range(n):
        i0, i1 = i - k, i + k
        if not closed and (i0 < 0 or i1 >= n):
            continue
        a = pts[i] - pts[i0 % n]
        b = pts[i1 % n] - pts[i]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-6 or nb < 1e-6:
            continue
        cosv = np.clip(np.dot(a, b) / (na * nb), -1, 1)
        ang[i] = np.degrees(np.arccos(cosv))
    corners = []
    for i in range(n):
        if ang[i] > thresh_deg and ang[i] == max(
                ang[max(0, i - k):min(n, i + k + 1)]):
            if not corners or i - corners[-1] > k:
                corners.append(i)
    return corners


def fit_path(pts: np.ndarray, max_err: float, closed=False) -> list[list[np.ndarray]]:
    """Split at corners then bezier-fit each piece; returns segments of beziers."""
    corners = find_corners(pts, closed)
    if closed:
        if corners:
            rolled = np.roll(pts, -corners[0], axis=0)
            corners = [c - corners[0] for c in corners] + [len(pts)]
            rolled = np.vstack([rolled, rolled[:1]])
            pieces = [rolled[corners[i]:corners[i + 1] + 1]
                      for i in range(len(corners) - 1)]
        else:
            pieces = [np.vstack([pts, pts[:1]])]
    else:
        idx = [0] + corners + [len(pts) - 1]
        idx = sorted(set(np.clip(idx, 0, len(pts) - 1)))
        pieces = [pts[idx[i]:idx[i + 1] + 1] for i in range(len(idx) - 1)]
    return [fit_cubic(p, max_err) for p in pieces if len(p) >= 2]


def segments_to_d(subpaths: list[list[list[np.ndarray]]], scale=1 / 16, closed=False) -> str:
    def f(v):
        return f"{v * scale:.2f}"
    d = ""
    for segments in subpaths:
        first = True
        for beziers in segments:
            for bz in beziers:
                p0, c1, c2, p3 = bz
                if first:
                    d += f"M{f(p0[0])} {f(p0[1])}" if not d else f" M{f(p0[0])} {f(p0[1])}"
                    first = False
                d += f" C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p3[0])} {f(p3[1])}"
        if closed:
            d += " Z"
    return d


# ---------------------------------------------------------------- per-part fitting

def fit_component(mask: np.ndarray, sw: float) -> dict:
    """Fit one connected component. Returns geometry in original image coords."""
    dt = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    max_dt = float(dt.max())
    filled = max_dt > 0.95 * sw  # much thicker than a stroke -> filled shape

    if filled:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_NONE)
        cont = max(contours, key=cv2.contourArea).reshape(-1, 2).astype(float)
        n = max(64, min(160, len(cont) // 3))
        pts = smooth_resample(cont, sigma=max(2.0, sw / 5), n=n, closed=True)
        segments = fit_path(pts, max_err=1.8, closed=True)
        return {"kind": "fill", "subpaths": [segments], "closed": True,
                "stroke_width": 0.0}

    skel = skeletonize(mask > 0)
    comp_sw = float(np.median(2 * dt[skel])) if skel.any() else sw
    paths = prune_and_trace(skel, min_spur=max(6.0, comp_sw * 0.55))
    if not paths:
        return {"kind": "none"}
    if len(paths) > 1:
        # candidates: raw fragments, spur-dropped, stitched pen stroke;
        # prefer fewest subpaths whose rasterization still matches the mask
        target = mask > 0

        def mask_iou(cand):
            r = raster_paths(cand, comp_sw, mask.shape) > 0
            return np.logical_and(r, target).sum() / max(
                np.logical_or(r, target).sum(), 1)

        stitched = stitch_paths(paths, tol=max(6.0, comp_sw * 1.2),
                                sw=comp_sw)
        cands = [paths, drop_spurs(paths, comp_sw), stitched,
                 drop_spurs(stitched, comp_sw)]
        scores = [mask_iou(c) for c in cands]
        best_iou = max(scores)
        paths = min((c for c, s in zip(cands, scores)
                     if s >= best_iou - 0.015), key=len)
    paths.sort(key=len, reverse=True)
    subpaths = []
    for raw in paths:
        if len(raw) < max(8.0, comp_sw * 0.6) and subpaths:
            continue  # residual skeleton debris
        n = max(48, min(128, len(raw) // 2))
        pts = smooth_resample(raw, sigma=max(1.6, comp_sw / 5.5), n=n)
        subpaths.append(fit_path(pts, max_err=1.6))
    return {"kind": "stroke", "subpaths": subpaths, "closed": False,
            "stroke_width": comp_sw}


# ---------------------------------------------------------------- rasterize + IoU

def rasterize(parts: list[dict]) -> np.ndarray:
    img = np.zeros((H, W), np.uint8)

    def sample(bz, n=40):
        t = np.linspace(0, 1, n)
        mt = 1 - t
        return (mt ** 3)[:, None] * bz[0] + 3 * (mt ** 2 * t)[:, None] * bz[1] + \
               3 * (mt * t ** 2)[:, None] * bz[2] + (t ** 3)[:, None] * bz[3]

    for part in parts:
        if part.get("kind") == "none":
            continue
        for segments in part["subpaths"]:
            poly = np.vstack([sample(bz) for seg in segments for bz in seg])
            ipoly = np.round(poly).astype(np.int32)
            if part["kind"] == "fill":
                cv2.fillPoly(img, [ipoly], 255)
            else:
                th = max(1, int(round(part["stroke_width"])))
                cv2.polylines(img, [ipoly], False, 255, th, cv2.LINE_8)
                r = th // 2
                cv2.circle(img, tuple(ipoly[0]), r, 255, -1)
                cv2.circle(img, tuple(ipoly[-1]), r, 255, -1)
    return img


def transform_part(part: dict, s: float, tx: float, ty: float) -> dict:
    if part.get("kind") == "none":
        return part
    out = {**part}
    off = np.array([tx, ty])
    out["subpaths"] = [[[bz * s + off for bz in seg] for seg in segments]
                       for segments in part["subpaths"]]
    if part["kind"] == "stroke":
        out["stroke_width"] = part["stroke_width"] * s
    return out


# ---------------------------------------------------------------- svg emission

def sample_subpath(segments: list[list[np.ndarray]], n: int = 64) -> np.ndarray:
    """Even-arclength sample of one subpath's bezier chain (image coords)."""
    t = np.linspace(0, 1, 24)
    mt = 1 - t
    dense = np.vstack([
        (mt ** 3)[:, None] * bz[0] + 3 * (mt ** 2 * t)[:, None] * bz[1] +
        3 * (mt * t ** 2)[:, None] * bz[2] + (t ** 3)[:, None] * bz[3]
        for seg in segments for bz in seg])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))]
    keep = np.r_[True, np.diff(d) > 1e-9]
    dense, d = dense[keep], d[keep]
    s = np.linspace(0, d[-1], n)
    return np.column_stack([np.interp(s, d, dense[:, 0]),
                            np.interp(s, d, dense[:, 1])])


SVG_HEADER = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 64" width="800" height="512">
<defs>
  <filter id="glow" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="1.6" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<rect width="100" height="64" fill="#0c0f11"/>
<g filter="url(#glow)" stroke="#5eeadd" fill="none" stroke-linecap="round" stroke-linejoin="round">
"""


def face_svg(parts: list[dict], roles: list[str]) -> str:
    body = ""
    for part, role in zip(parts, roles):
        if part.get("kind") == "none":
            continue
        d = segments_to_d(part["subpaths"], closed=part["closed"])
        if part["kind"] == "fill":
            body += f'  <path d="{d}" fill="#5eeadd" stroke="none" data-role="{role}"/>\n'
        else:
            swl = part["stroke_width"] / 16
            body += f'  <path d="{d}" stroke-width="{swl:.2f}" data-role="{role}"/>\n'
    return SVG_HEADER + body + "</g>\n</svg>\n"


# ---------------------------------------------------------------- main

def main() -> None:
    records = json.loads((ROOT / "measurements_normalized.json").read_text())
    faces_out = []
    metrics = []
    for rec in records:
        name = Path(rec["file"]).stem
        core = (cv2.imread(str(MASKS / f"{name}_core.png"), 0) > 127).astype(np.uint8)
        n, labels = cv2.connectedComponents(core, 8)
        sw = rec["stroke_width_px"]
        s, tx, ty = rec["norm_scale"], rec["norm_tx"], rec["norm_ty"]

        # match measured components to label ids via centroid distance
        lab_cent = {}
        for lab in range(1, n):
            ys, xs = np.nonzero(labels == lab)
            if len(xs) < 50:
                continue
            lab_cent[lab] = (xs.mean(), ys.mean())

        parts, roles = [], []
        for comp in rec["components"]:
            cx, cy = comp["centroid_xy"]
            lab = min(lab_cent, key=lambda L: (lab_cent[L][0] - cx) ** 2 +
                      (lab_cent[L][1] - cy) ** 2)
            m = (labels == lab).astype(np.uint8)
            fitted = fit_component(m, sw)
            parts.append(transform_part(fitted, s, tx, ty))
            roles.append(comp["role"])

        render = rasterize(parts)
        target = (cv2.imread(str(NORM / f"{name}_core.png"), 0) > 127)
        inter = np.logical_and(render > 0, target).sum()
        union = np.logical_or(render > 0, target).sum()
        iou = inter / max(union, 1)
        metrics.append({"file": name, "iou": round(float(iou), 3)})

        (OUT_SVG / f"{name}.svg").write_text(face_svg(parts, roles))
        faces_out.append({
            "file": name,
            "expression": name.split("_", 1)[1].rsplit("_", 1)[0],
            "parts": [{
                "role": role,
                "kind": p.get("kind"),
                "closed": p.get("closed", False),
                "stroke_width_local": round(p.get("stroke_width", 0) / 16, 2),
                "d": segments_to_d(p["subpaths"], closed=p["closed"])
                if p.get("kind") != "none" else "",
                "points_local": [np.round(sample_subpath(sp) / 16, 3).tolist()
                                 for sp in p["subpaths"]]
                if p.get("kind") != "none" else [],
            } for p, role in zip(parts, roles)],
            "iou": round(float(iou), 3),
        })
        print(f"{name:<30} IoU={iou:.3f}")

    (ROOT / "faces.json").write_text(json.dumps(faces_out, indent=1))
    (OUT_REPORTS / "fit_metrics.json").write_text(json.dumps(metrics, indent=1))
    ious = [m["iou"] for m in metrics]
    print(f"\nmean IoU={np.mean(ious):.3f}  min={min(ious):.3f}")


if __name__ == "__main__":
    main()
