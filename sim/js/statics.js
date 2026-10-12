// statics.js — ground reaction forces, joint torques, stability, beam deflection.
// Slope is modeled by tilting the gravity vector while the ground stays z=0
// (physically identical to a tilted plane; contact points remain the wheels'
// lowest rim points).

import { V } from './kin.js';
import { distalMasses } from './model.js';

// --- tiny linear algebra ------------------------------------------------
function solve3(A, b) { // 3x3 linear solve (Cramer)
  const [a, d, g_] = [A[0][0], A[1][0], A[2][0]];
  const [b_, e, h] = [A[0][1], A[1][1], A[2][1]];
  const [c, f, i] = [A[0][2], A[1][2], A[2][2]];
  const det = a * (e * i - f * h) - b_ * (d * i - f * g_) + c * (d * h - e * g_);
  if (Math.abs(det) < 1e-12) return null;
  const x = (b[0] * (e * i - f * h) - b_ * (b[1] * i - f * b[2]) + c * (b[1] * h - e * b[2])) / det;
  const y = (a * (b[1] * i - f * b[2]) - b[0] * (d * i - f * g_) + c * (d * b[2] - b[1] * g_)) / det;
  const z = (a * (e * b[2] - b[1] * h) - b_ * (d * b[2] - b[1] * g_) + b[0] * (d * h - e * g_)) / det;
  return [x, y, z];
}

// --- ground reaction forces ----------------------------------------------
// contacts: [{legIdx, p:[x,y,0]}]. M total kg, com world, gForce = g*gDir (m/s^2 vec).
// Solves min-norm normal forces N_i (up, along +z) satisfying force + moment balance:
//   sum N_i = -G_z ;  sum N_i*y_i = -(com x G)_x ;  sum N_i*x_i = (com x G)_y
// (in-plane friction forces act at z=0 so they add no x/y moments).
// Active-set: negative solutions are removed (foot lifting off) and re-solved.
export function solveGRF(contacts, M, com, gForce) {
  const G = V.scale(gForce, M); // total gravity force vector (N)
  const comxG = V.cross(com, G);
  const b = [-G[2], -comxG[0], comxG[1]];
  const active = contacts.map((_, i) => i);
  let N = contacts.map(() => 0);
  let dropped = [];
  let residual = 0;

  for (let pass = 0; pass < contacts.length + 1; pass++) {
    const n = active.length;
    if (n === 0) break;
    const rows = active.map((i) => [1, contacts[i].p[1], contacts[i].p[0]]); // [1, y, x]
    // min-norm solution of A^T? — we need A f = b with A rows = constraints, f length n.
    // A is 3 x n: A[0][j]=1, A[1][j]=y_j, A[2][j]=x_j
    let f;
    if (n >= 3) {
      // f = A^T (A A^T)^-1 b   (min norm)
      const AAT = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
      for (let j = 0; j < n; j++) {
        const col = [1, contacts[active[j]].p[1], contacts[active[j]].p[0]];
        for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) AAT[r][c] += col[r] * col[c];
      }
      const lam = solve3(AAT, b);
      if (!lam) { f = null; } else {
        f = active.map((i) => lam[0] + lam[1] * contacts[i].p[1] + lam[2] * contacts[i].p[0]);
      }
    } else if (n === 2) {
      // least squares: f = (A^T A)^-1 A^T b  (2 unknowns, 3 eqs)
      const a0 = [1, contacts[active[0]].p[1], contacts[active[0]].p[0]];
      const a1 = [1, contacts[active[1]].p[1], contacts[active[1]].p[0]];
      const m00 = V.dot(a0, a0), m01 = V.dot(a0, a1), m11 = V.dot(a1, a1);
      const r0 = V.dot(a0, b), r1 = V.dot(a1, b);
      const det = m00 * m11 - m01 * m01;
      f = Math.abs(det) < 1e-12 ? [b[0] / 2, b[0] / 2]
        : [(r0 * m11 - r1 * m01) / det, (r1 * m00 - r0 * m01) / det];
    } else {
      f = [b[0]];
    }
    if (!f) { f = active.map(() => b[0] / n); }

    // check negatives
    let worst = -1, worstVal = -1e-6;
    f.forEach((v, j) => { if (v < worstVal) { worstVal = v; worst = j; } });
    if (worst === -1) {
      N = contacts.map(() => 0);
      active.forEach((i, j) => { N[i] = f[j]; });
      // residual of moment balance (nonzero => statically unbalanced = tipping)
      const r = [0, 0, 0];
      active.forEach((i, j) => {
        r[0] += f[j]; r[1] += f[j] * contacts[i].p[1]; r[2] += f[j] * contacts[i].p[0];
      });
      residual = Math.hypot(r[0] - b[0], r[1] - b[1], r[2] - b[2]);
      break;
    }
    dropped.push(active[worst]);
    active.splice(worst, 1);
  }

  // friction requirement: in-plane gravity component split by normal share
  const Ftang = [-G[0], -G[1]]; // ground must supply this via friction (N)
  const Nsum = N.reduce((s, v) => s + v, 0);
  return {
    N,                       // per-contact normal (N), aligned with `contacts`
    dropped,                 // contact indices that lifted off
    residual,                // N·m-ish imbalance; > ~1e-3 means tipping/unbalanced
    Nsum,
    Ftang,
    frictionNeeded: Math.hypot(Ftang[0], Ftang[1]),
  };
}

// Full 3D force applied by ground at contact i (normal + its friction share).
export function contactForce(grf, i) {
  const share = grf.Nsum > 1e-9 ? grf.N[i] / grf.Nsum : 0;
  return [grf.Ftang[0] * share, grf.Ftang[1] * share, grf.N[i]];
}

// --- joint torques --------------------------------------------------------
// torque about joint axis from: contact force at wheel rim + gravity on distal masses.
// Returns [tauRoll, tauHip, tauKnee] (signed, N·m). Servo must supply the negation;
// magnitude is what matters vs rating.
export function legJointTorques(P, items, legIdx, fk, Fcontact, gForce, inContact) {
  const joints = [
    { p: fk.mount, a: fk.a1 },
    { p: fk.p1, a: fk.a2 },
    { p: fk.knee, a: fk.a3 },
  ];
  return joints.map((jt, jIdx) => {
    let m = [0, 0, 0];
    if (inContact) {
      m = V.add(m, V.cross(V.sub(fk.contact, jt.p), Fcontact));
    }
    for (const it of distalMasses(P, items, legIdx, jIdx)) {
      m = V.add(m, V.cross(V.sub(it.p, jt.p), V.scale(gForce, it.m)));
    }
    return V.dot(jt.a, m);
  });
}

// Wheel-motor holding torque on a slope: friction share along the wheel's rolling
// direction × wheel radius. Lateral friction is scrub (bearing load, not motor).
export function wheelHoldingTorque(P, fk, Fcontact) {
  const rollDir = V.norm(V.cross(fk.wheelAxis, [0, 0, 1]));
  const along = Fcontact[0] * rollDir[0] + Fcontact[1] * rollDir[1];
  return Math.abs(along) * P.rw;
}

// --- stability -------------------------------------------------------------
// convex hull (2D, xy) of contact points
export function hull2D(pts) {
  const p = pts.map((q) => [q[0], q[1]]).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (p.length < 3) return p;
  const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lo = [], up = [];
  for (const q of p) {
    while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop();
    lo.push(q);
  }
  for (const q of p.slice().reverse()) {
    while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop();
    up.push(q);
  }
  return lo.slice(0, -1).concat(up.slice(0, -1));
}

// stability of CoM projected ALONG GRAVITY onto z=0, vs support polygon.
// Returns margin (m, + inside), tipAngles per hull edge, min tip angle (deg).
export function stability(contacts, com, gDir) {
  const pts = contacts.map((c) => c.p);
  const t = gDir[2] < -1e-9 ? -com[2] / gDir[2] : 0;
  const proj = [com[0] + t * gDir[0], com[1] + t * gDir[1]];
  const hCom = com[2];

  if (pts.length === 0) return { proj, margin: -1, minTipDeg: 0, hull: [], edges: [] };
  if (pts.length === 1) {
    const d = Math.hypot(proj[0] - pts[0][0], proj[1] - pts[0][1]);
    return { proj, margin: -d, minTipDeg: 0, hull: [pts[0]], edges: [] };
  }
  let hull = pts.length === 2 ? [pts[0], pts[1]] : hull2D(pts);
  const edges = [];
  let margin = Infinity;
  const n = hull.length;
  for (let i = 0; i < n; i++) {
    const a = hull[i], b2 = hull[(i + 1) % n];
    if (n === 2 && i === 1) break; // line: single edge
    const ex = b2[0] - a[0], ey = b2[1] - a[1];
    const el = Math.hypot(ex, ey);
    if (el < 1e-9) continue;
    // inward normal (hull is CCW): left of edge
    const nx = -ey / el, ny = ex / el;
    let d = (proj[0] - a[0]) * nx + (proj[1] - a[1]) * ny;
    if (n === 2) d = -Math.abs((proj[0] - a[0]) * nx + (proj[1] - a[1]) * ny); // distance to line, always "critical"
    const tipDeg = Math.atan2(Math.max(d, 0), Math.max(hCom, 1e-3)) * 180 / Math.PI;
    edges.push({ a, b: b2, d, tipDeg });
    margin = Math.min(margin, d);
  }
  const minTipDeg = edges.length ? Math.min(...edges.map((e) => e.tipDeg)) : 0;
  return { proj, margin, minTipDeg, hull, edges };
}

// --- printed-beam deflection ------------------------------------------------
// femur as a cantilever loaded by the foot force component perpendicular to it.
export function femurDeflection(P, fk, Fcontact, inContact) {
  if (!inContact) return 0;
  const Fperp = V.len(V.sub(Fcontact, V.scale(fk.femurDir, V.dot(Fcontact, fk.femurDir))));
  return (Fperp * Math.pow(P.L1, 3)) / (3 * P.E_Pa * P.I_m4); // meters
}
