// anim.js — keyframed pose sequences evaluated through the full pipeline.
// A keyframe is a partial pose override; playback lerps between keyframes,
// runs evaluate() each frame, and precomputes a worst-utilization strip so the
// timeline shows exactly where a sequence would stall a servo or tip the robot.

import { evaluate } from './pipeline.js';

const lerp = (a, b, t) => a + (b - a) * t;
const lerpArr = (a, b, t) => a.map((v, i) => lerp(v, b[i], t));

// Each preset: {name, dur (s at speed 1), frames: [{t, pose partial}]}
export function presets(cfg) {
  const H = cfg.pose.bodyH, R = cfg.pose.stanceR;
  const Hlow = Math.max(35, H * 0.4), Hhigh = Math.min(H * 1.4, cfg.leg.femur + cfg.leg.tibia - 25);
  const base = { bodyH: H, bodyX: 0, bodyY: 0, stanceR: R, lifts: [0, 0, 0, 0], stepX: [0, 0, 0, 0] };
  const F = (t, p) => ({ t, pose: { ...base, ...p } });

  // crawl: shift body away from the swing leg, lift it, step it forward, repeat.
  // Leg order RL(2), FL(0), RR(3), FR(1). Shift direction = away from swing leg.
  // Shifts and step length SCALE with the geometry — fixed millimeters tip over
  // short-legged configs and under-use long ones.
  const crawl = [];
  const order = [2, 0, 3, 1];
  const step = Math.min(42, cfg.leg.femur * 0.42);
  // shift the body toward the CENTROID of the 3 supporting feet before each
  // lift — a fixed sideways lean tips over as soon as geometry changes
  const D2R2 = Math.PI / 180;
  const azs = [cfg.geo.frontAz, -cfg.geo.frontAz, cfg.geo.rearAz, -cfg.geo.rearAz].map((a) => a * D2R2);
  const feet = azs.map((a) => [Math.cos(a) * R, Math.sin(a) * R]);
  const shiftFor = (li) => {
    const others = feet.filter((_, i) => i !== li);
    const cx = others.reduce((s, f) => s + f[0], 0) / 3;
    const cy = others.reduce((s, f) => s + f[1], 0) / 3;
    return [cx * 0.55, cy * 0.55];
  };
  const stepsSoFar = [0, 0, 0, 0];
  let t = 0, adv = 0; // body ADVANCES step/4 per leg cycle (while 4 feet are down)
  const seg = 1 / (order.length * 4 + 1);
  order.forEach((li) => {
    const [sx, sy] = shiftFor(li);
    crawl.push(F(t, { lifts: [0, 0, 0, 0], stepX: stepsSoFar.slice(), bodyY: 0, bodyX: adv })); t += seg;
    adv += step / 4; // advance happens on 4 feet, together with the safety shift
    crawl.push(F(t, { stepX: stepsSoFar.slice(), bodyY: sy, bodyX: adv + sx })); t += seg;
    const mid = stepsSoFar.slice(); mid[li] += step / 2;
    const lift = [0, 0, 0, 0]; lift[li] = 40;
    crawl.push(F(t, { lifts: lift, stepX: mid, bodyY: sy, bodyX: adv + sx })); t += seg;
    stepsSoFar[li] += step;
    crawl.push(F(t, { lifts: [0, 0, 0, 0], stepX: stepsSoFar.slice(), bodyY: sy, bodyX: adv + sx })); t += seg;
  });
  crawl.push(F(1, { stepX: stepsSoFar.slice(), bodyX: adv }));

  return [
    {
      name: 'Squat cycle', dur: 4,
      frames: [F(0, {}), F(0.25, { bodyH: Hlow }), F(0.5, {}), F(0.75, { bodyH: Hhigh }), F(1, {})],
    },
    {
      name: 'Stand up (from floor)', dur: 3,
      frames: [
        F(0, { bodyH: Math.max(28, Hlow * 0.7), stanceR: R * 1.25 }),
        F(0.5, { bodyH: Hlow, stanceR: R * 1.1 }),
        F(1, {}),
      ],
    },
    {
      name: 'Crawl gait (4 steps)', dur: 8,
      frames: crawl,
    },
    {
      name: 'Lean circle (CoM tour)', dur: 5,
      frames: Array.from({ length: 17 }, (_, i) => {
        const a = (i / 16) * 2 * Math.PI;
        return F(i / 16, { bodyX: Math.cos(a) * 45, bodyY: Math.sin(a) * 45 });
      }),
    },
    {
      name: 'Two-wheel (diagonal lift)', dur: 4,
      frames: [F(0, {}), F(0.3, { bodyX: 0, lifts: [30, 0, 0, 30] }), F(0.7, { lifts: [55, 0, 0, 55] }), F(1, {})],
    },
    {
      name: 'One leg up (3-leg stance)', dur: 3,
      frames: [F(0, {}), F(0.3, { bodyX: -25, bodyY: -25 }), F(0.6, { bodyX: -25, bodyY: -25, lifts: [60, 0, 0, 0] }), F(1, { bodyX: -25, bodyY: -25, lifts: [60, 0, 0, 0] })],
    },
    {
      name: 'Leg wave (suspended)', dur: 4, suspended: true,
      frames: Array.from({ length: 21 }, (_, i) => {
        const t2 = i / 20;
        const lifts = [0, 1, 2, 3].map((l) => 30 + 28 * Math.sin(2 * Math.PI * (t2 * 2 - l / 4)));
        return F(t2, { lifts, stanceR: R * 0.9 });
      }),
    },
  ];
}

export function poseAt(preset, t) {
  const fr = preset.frames;
  if (t <= fr[0].t) return fr[0].pose;
  for (let i = 1; i < fr.length; i++) {
    if (t <= fr[i].t) {
      const a = fr[i - 1], b = fr[i];
      const u = (t - a.t) / Math.max(b.t - a.t, 1e-9);
      const out = {};
      for (const k of Object.keys(b.pose)) {
        const av = a.pose[k], bv = b.pose[k];
        out[k] = Array.isArray(bv) ? lerpArr(av, bv, u) : lerp(av, bv, u);
      }
      return out;
    }
  }
  return fr[fr.length - 1].pose;
}

// Apply a preset pose at time t onto a config copy (returns new cfg object).
export function cfgAt(cfg, preset, t) {
  const c = JSON.parse(JSON.stringify(cfg));
  Object.assign(c.pose, poseAt(preset, t));
  if (preset.suspended) c.pose.mode = 'suspended';
  return c;
}

// Precompute the timeline strip: N samples of worst utilization / tip margin /
// speed feasibility. Joint speeds come from finite differences between samples,
// scaled by the actual playback duration.
export function analyzeSequence(cfg, preset, durationS, N = 61) {
  const dt = durationS / (N - 1);
  const samples = [];
  let prevLegQ = null, prevStep = null;
  for (let i = 0; i < N; i++) {
    const t = i / (N - 1);
    const c = cfgAt(cfg, preset, t);
    const r0 = evaluate(c);
    const legQ = r0.legs.map((l) => l.q);
    const wheelW = r0.legs.map((_, li) => {
      if (!prevStep) return 0;
      const ds = (c.pose.stepX[li] - prevStep[li]) / 1000;
      return ds / dt / r0.P.rw; // rolling wheel speed if stepping via wheels
    });
    const speeds = prevLegQ ? {
      joints: legQ.map((q, li) => q.map((v, j) => (v - prevLegQ[li][j]) / dt)),
      wheels: wheelW,
    } : null;
    const r = speeds ? evaluate(c, { speeds }) : r0;
    const maxUtil = Math.max(...r.power.perServo.map((s) => s.utilization));
    const speedBad = r.power.perServo.some((s) => !s.speedFeasible);
    samples.push({
      t, maxUtil,
      tipDeg: r.stab.minTipDeg,
      tipping: r.grf.dropped.length > 0 || (c.pose.mode === 'stand' && r.stab.margin < 0),
      speedBad,
      unreachable: r.legs.some((l) => !l.reachable || l.romClamped),
      vRail: r.power.vRail,
      overall: r.overall,
    });
    prevLegQ = legQ; prevStep = c.pose.stepX.slice();
  }
  return samples;
}
