// optimize.js — auto-optimizer: search the geometry space for configs that meet
// hard constraints (torque margin, tipping, fuses, sag, reach, collisions, flex)
// and best satisfy the chosen goal. Candidates are scored on a POSE BATTERY —
// stand, low squat, one-leg lift, slope — so a config can't win by being good at
// standing still only.
//
// Method: uniform random exploration, then (1+1)-style gaussian refinement with
// shrinking step size. evaluate() is ~1ms, so a few hundred candidates run in
// seconds; the loop yields to the UI between chunks.

import { evaluate } from './pipeline.js';
import { getPath, setPath } from './config.js';
import { poseCollisions } from './rom.js';

export const OPT_VARS = [
  { key: 'leg.femur', label: 'Femur', min: 70, max: 200, on: true },
  { key: 'leg.tibia', label: 'Tibia', min: 70, max: 220, on: true },
  { key: 'leg.d1', label: 'Hip offset', min: 20, max: 70, on: true },
  { key: 'geo.frontAz', label: 'Front azimuth', min: 25, max: 80, on: true },
  { key: 'geo.rearAz', label: 'Rear azimuth', min: 100, max: 155, on: true },
  { key: 'pose.stanceR', label: 'Stance radius', min: 120, max: 330, on: true },
  { key: 'pose.bodyH', label: 'Body height', min: 50, max: 200, on: true },
  { key: 'wheel.dia', label: 'Wheel Ø', min: 45, max: 110, on: false },
  { key: 'masses.batteryH', label: 'Battery height', min: 10, max: 250, on: false },
  { key: 'leg.beamW', label: 'Beam width', min: 14, max: 30, on: false },
  { key: 'leg.beamT', label: 'Beam thickness', min: 10, max: 24, on: false },
];

export const GOALS = {
  torque: { label: 'Min worst-servo load', f: (m) => m.worstUtil },
  tip: { label: 'Max tipping margin', f: (m) => -m.minTip / 90 },
  runtime: { label: 'Max runtime', f: (m) => -Math.min(m.runtime, 600) / 600 },
  mass: { label: 'Min total mass', f: (m) => m.mass / 5 },
  balanced: {
    label: 'Balanced (torque+tip+runtime)',
    f: (m) => m.worstUtil + Math.max(0, (18 - m.minTip)) / 36 + (1 - Math.min(m.runtime, 240) / 240) * 0.3,
  },
};

export const DEFAULT_CONSTRAINTS = {
  maxUtil: 0.35,     // worst servo torque / stall@brownout across the battery
  minTipDeg: 12,
  maxLegAmp: 10.8,
  maxTotalAmp: 28,
  minVrail: 9.9,
  maxDeflMm: 0.8,
  maxReachFrac: 0.86, // stand pose may use ≤86% of leg length — the rest is stride headroom
  requireReach: true,
  noCollisions: true,
};

// body shift (mm) toward the centroid of the 3 feet supporting when leg li lifts
export function supportShift(cfg, li, k = 0.55) {
  const D2R = Math.PI / 180;
  const azs = [cfg.geo.frontAz, -cfg.geo.frontAz, cfg.geo.rearAz, -cfg.geo.rearAz].map((a) => a * D2R);
  const R = cfg.pose.stanceR;
  const others = azs.map((a) => [Math.cos(a) * R, Math.sin(a) * R]).filter((_, i) => i !== li);
  return [k * others.reduce((s, f) => s + f[0], 0) / 3, k * others.reduce((s, f) => s + f[1], 0) / 3];
}

// pose battery: worst case across these determines the candidate's metrics
function poseBattery(cfg) {
  const poses = [];
  const p0 = JSON.parse(JSON.stringify(cfg));
  p0.pose.mode = 'stand'; p0.pose.lifts = [0, 0, 0, 0]; p0.pose.stepX = [0, 0, 0, 0];
  p0.pose.bodyX = 0; p0.pose.bodyY = 0; p0.env.slopeDeg = 0;
  poses.push(p0);
  const squat = JSON.parse(JSON.stringify(p0));
  squat.pose.bodyH = Math.max(40, p0.pose.bodyH * 0.55);
  poses.push(squat);
  const lift = JSON.parse(JSON.stringify(p0));
  lift.pose.lifts = [50, 0, 0, 0];
  const sh = supportShift(cfg, 0);
  lift.pose.bodyX = sh[0]; lift.pose.bodyY = sh[1];
  poses.push(lift);
  const slope = JSON.parse(JSON.stringify(p0));
  slope.env.slopeDeg = 10;
  poses.push(slope);
  return poses;
}

export function scoreConfig(cfg, goal, cons) {
  const m = {
    worstUtil: 0, minTip: Infinity, maxLegAmp: 0, maxTotalAmp: 0, minVrail: Infinity,
    maxDeflMm: 0, mass: 0, runtime: Infinity, reachOK: true, collisions: 0,
    maxReachFrac: 0,
  };
  let first = true;
  for (const pc of poseBattery(cfg)) {
    let r;
    try { r = evaluate(pc); } catch { return { score: 1e9, metrics: m }; }
    if (first) { // stride headroom measured on the stand pose
      first = false;
      const Lmax = r.P.L1 + r.P.L2;
      r.legs.forEach((l) => {
        const dx = l.fk.axle[0] - l.fk.p1[0], dy = l.fk.axle[1] - l.fk.p1[1], dz = l.fk.axle[2] - l.fk.p1[2];
        m.maxReachFrac = Math.max(m.maxReachFrac, Math.hypot(dx, dy, dz) / Lmax);
      });
    }
    m.worstUtil = Math.max(m.worstUtil, ...r.power.perServo.map((s) => s.utilization));
    if (r.contacts.length >= 3) m.minTip = Math.min(m.minTip, r.stab.minTipDeg);
    else m.minTip = Math.min(m.minTip, 0);
    if (r.grf.dropped.length) m.minTip = Math.min(m.minTip, 0);
    m.maxLegAmp = Math.max(m.maxLegAmp, ...r.power.legAmps);
    m.maxTotalAmp = Math.max(m.maxTotalAmp, r.power.iTotal);
    m.minVrail = Math.min(m.minVrail, r.power.vRail);
    m.maxDeflMm = Math.max(m.maxDeflMm, Math.max(...r.deflections, 0) * 1000);
    m.mass = r.M;
    m.runtime = Math.min(m.runtime, r.power.runtimeMin);
    if (!r.legs.every((l) => l.reachable && !l.romClamped)) m.reachOK = false;
    m.collisions += poseCollisions(r.P, r.legs.map((l) => l.fk), r.bodyPos).length;
  }
  // hard-constraint penalties (quadratic, heavily weighted)
  let pen = 0;
  const over = (v, lim, scale) => Math.pow(Math.max(0, v - lim) / scale, 2) * 50;
  const under = (v, lim, scale) => Math.pow(Math.max(0, lim - v) / scale, 2) * 50;
  pen += over(m.worstUtil, cons.maxUtil, 0.1);
  pen += under(m.minTip, cons.minTipDeg, 5);
  pen += over(m.maxLegAmp, cons.maxLegAmp, 2);
  pen += over(m.maxTotalAmp, cons.maxTotalAmp ?? cfg.thresholds.totAmpMax, 3);
  pen += under(m.minVrail, cons.minVrail, 0.3);
  pen += over(m.maxDeflMm, cons.maxDeflMm, 0.5);
  pen += over(m.maxReachFrac, cons.maxReachFrac ?? 1, 0.05);
  if (cons.requireReach && !m.reachOK) pen += 200;
  if (cons.noCollisions && m.collisions > 0) pen += 100 * m.collisions;
  return { score: GOALS[goal].f(m) + pen, metrics: m, feasible: pen < 1e-9 };
}

export async function optimize(baseCfg, { vars, goal, cons, nRandom = 220, nRefine = 160, onProgress }) {
  const active = vars.filter((v) => v.on);
  const rand = mulberry32(42);
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const mkCfg = (u) => {
    const c = JSON.parse(JSON.stringify(baseCfg));
    active.forEach((v, i) => setPath(c, v.key, Math.round(v.min + u[i] * (v.max - v.min))));
    return c;
  };
  const uOf = () => active.map((v) => {
    const cur = getPath(baseCfg, v.key);
    return clamp01((cur - v.min) / (v.max - v.min));
  });

  const results = [];
  const consider = (u) => {
    const cfg = mkCfg(u);
    const s = scoreConfig(cfg, goal, cons);
    results.push({ u: u.slice(), cfg, ...s });
    return s.score;
  };

  // seed with the current config
  let bestU = uOf();
  let bestScore = consider(bestU);

  let evals = 1;
  // NOT setTimeout: background tabs throttle it to >=1s, which turns a 2s search
  // into minutes as soon as the report tab steals focus. MessageChannel isn't throttled.
  const mc = new MessageChannel();
  const yieldUI = () => new Promise((r) => { mc.port1.onmessage = () => r(); mc.port2.postMessage(0); });
  // phase 1: random exploration
  for (let i = 0; i < nRandom; i++) {
    const u = active.map(() => rand());
    const s = consider(u);
    if (s < bestScore) { bestScore = s; bestU = u; }
    if (++evals % 12 === 0) { onProgress?.(evals, nRandom + nRefine, bestScore); await yieldUI(); }
  }
  // phase 2: gaussian refinement with shrinking sigma
  let sigma = 0.12;
  for (let i = 0; i < nRefine; i++) {
    const u = bestU.map((x) => clamp01(x + gauss(rand) * sigma));
    const s = consider(u);
    if (s < bestScore) { bestScore = s; bestU = u; } else sigma *= 0.985;
    sigma = Math.max(sigma, 0.02);
    if (++evals % 12 === 0) { onProgress?.(evals, nRandom + nRefine, bestScore); await yieldUI(); }
  }

  // top-5 distinct results (distinct = differs meaningfully in u-space)
  results.sort((a, b) => a.score - b.score);
  const top = [];
  for (const r of results) {
    if (top.every((t) => dist(t.u, r.u) > 0.08)) top.push(r);
    if (top.length >= 5) break;
  }
  return { top, evals, active };
}

function dist(a, b) { return Math.sqrt(a.reduce((s, v, i) => s + (v - b[i]) ** 2, 0)); }
function gauss(rand) {
  let u = 0, v = 0;
  while (u === 0) u = rand();
  while (v === 0) v = rand();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}
function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
