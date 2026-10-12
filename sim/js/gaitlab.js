// gaitlab.js — interactive gait-speed lab, adapted from the analysis in
// "How To Make Your Robot Work, The First Time" (the.Amazing PhD / Charlotte).
//
// His core insight, transplanted: an actuator's torque-speed line makes LOADED
// gait phases slower than unloaded ones, so ground speed vs commanded speed is
// NOT the naive straight line — it bends onto an asymptote set by the torque
// margin. His robot: DC motor + cam legs, v_d(ω0) = β(ω0²−ω0A)/(ω0−bA).
// Ours: position-servo legs — same physics enters through per-phase durations:
//   ω_avail(τ) = ω_noload(V)·(1 − τ/τ_stall(V))        (servo line)
//   T_phase   = max over joints (Δq_joint / ω_avail(τ_joint,phase))
//   T_cycle   = Σ legs (T_swing + T_shift),  v = bodyAdvance / T_cycle
// Commanding a faster cycle can't beat T_cycle,min — that's the asymptote.
//
// Also from the video: the stride/leg-interference rule (feet paths must not
// overlap fore-aft) and the spec-table habit (targets vs achieved, revise).
// From the MIST PDF guide: the k load factor (dynamic multiplier on stance
// force) and the 10 kg·cm sustained budget line drawn on the torque plot.

import { evaluate } from './pipeline.js';
import { presets, cfgAt, poseAt } from './anim.js';
import { socToV } from './config.js';
import { solvePower } from './power.js';

// analyze the actual crawl preset: per-phase joint excursions + torques
export function gaitModel(cfg0, opts) {
  const cfg = JSON.parse(JSON.stringify(cfg0));
  cfg.pose.mode = 'stand';
  cfg.power.soc = opts.soc;
  cfg.masses.payloadM = opts.payloadG;
  const crawl = presets(cfg).find((p) => p.name.includes('Crawl'));

  // sample the cycle; classify each interval swing (any leg lifted) vs shift
  const N = 48;
  let prevQ = null, prevPose = null;
  const phases = { swing: { dq: [0, 0, 0], tau: [0, 0, 0] }, shift: { dq: [0, 0, 0], tau: [0, 0, 0] } };
  let stanceTauMax = 0, swingTauMax = 0, maxLegAmp = 0, iPeak = 0;
  const tauTrace = [];
  let advance = 0;
  for (let i = 0; i <= N; i++) {
    const t = i / N;
    const c = cfgAt(cfg, crawl, t);
    const r = evaluate(c);
    const lifted = c.pose.lifts.some((l) => l > 2);
    const ph = lifted ? phases.swing : phases.shift;
    // track the busiest leg's joints (worst over legs)
    const q = r.legs.map((l) => l.q);
    if (prevQ) {
      for (let j = 0; j < 3; j++) {
        let dq = 0;
        for (let li = 0; li < 4; li++) dq = Math.max(dq, Math.abs(q[li][j] - prevQ[li][j]));
        ph.dq[j] += dq;
      }
    }
    for (let j = 0; j < 3; j++) {
      let tj = 0;
      for (let li = 0; li < 4; li++) tj = Math.max(tj, Math.abs(r.servoTorques[li][j]));
      ph.tau[j] = Math.max(ph.tau[j], tj * (lifted ? 1 : opts.kLoad));
    }
    const torqueScale = lifted ? 1 : opts.kLoad;
    const dynamicPower = solvePower(
      r.P,
      r.servoTorques.map((leg) => leg.map((tau) => tau * torqueScale)),
      r.wheelTorques.map((tau) => tau * torqueScale),
      null,
    );
    const worst = Math.max(...dynamicPower.perServo.map((s) => s.tau));
    tauTrace.push({ t, tau: worst, lifted });
    if (lifted) swingTauMax = Math.max(swingTauMax, worst);
    else stanceTauMax = Math.max(stanceTauMax, worst);
    maxLegAmp = Math.max(maxLegAmp, ...dynamicPower.legAmps);
    iPeak = Math.max(iPeak, dynamicPower.iTotal);
    prevQ = q;
    if (i === N) advance = (c.pose.bodyX - poseAt(crawl, 0).bodyX) / 1000;
  }

  // servo line at this pack state
  const vOC = socToV(opts.soc) * cfg.power.cells;
  const vRail = vOC - iPeak * (cfg.power.rInt / 1000);
  const tauStall = cfg.servo.stallNm * (vRail / 12);
  const wNoLoad = (cfg.servo.noLoadRPM * 2 * Math.PI / 60) * (vRail / 12);
  const wAvail = (tau) => Math.max(wNoLoad * (1 - tau / tauStall), 1e-3);

  // minimum phase times (slowest joint governs), for the whole 4-leg cycle.
  // Linkage knee: the servo sweeps linkRatio × the joint angle, so joint-space
  // speed is divided by the ratio (torque was already divided the other way).
  const JN = ['hipRoll', 'hipPitch', 'knee'];
  const jointSpeedScale = (j) => (j === 2 && cfg.leg.linkage ? 1 / cfg.leg.linkRatio : 1);
  let tSwingMin = 0, tShiftMin = 0, limiter = '';
  let worstRatio = 0;
  for (let j = 0; j < 3; j++) {
    const ts = phases.swing.dq[j] / (wAvail(phases.swing.tau[j]) * jointSpeedScale(j));
    const tf = phases.shift.dq[j] / (wAvail(phases.shift.tau[j]) * jointSpeedScale(j));
    if (ts > tSwingMin) { tSwingMin = ts; }
    if (tf > tShiftMin) { tShiftMin = tf; }
    const ratio = Math.max(ts, tf);
    if (ratio > worstRatio) { worstRatio = ratio; limiter = JN[j] + (ts > tf ? ' (swing)' : ' (shift)'); }
  }
  const tCycleMin = tSwingMin + tShiftMin;
  const vMax = advance / Math.max(tCycleMin, 1e-6);

  // ground speed vs commanded cycle time: v = advance / max(Tcmd, Tmin)
  const curve = [];
  for (let k = 0; k <= 60; k++) {
    const rate = 0.02 + (k / 60) * 1.4; // commanded cycles per second
    const Tcmd = 1 / rate;
    curve.push({
      rate,
      vNaive: advance * rate,
      vReal: advance / Math.max(Tcmd, tCycleMin),
    });
  }

  // leg interference (video: feet closer than a stride collide)
  const D2R = Math.PI / 180;
  const foreAftGap = cfg.pose.stanceR * (Math.cos(cfg.geo.frontAz * D2R) - Math.cos(cfg.geo.rearAz * D2R));
  const step = Math.min(42, cfg.leg.femur * 0.42);
  const clearNeeded = step + cfg.wheel.dia + 10;
  const legClearOK = foreAftGap >= clearNeeded;

  return {
    advance, tCycleMin, vMax, limiter, curve, tauTrace,
    tauStall, vRail, stanceTauMax, swingTauMax, maxLegAmp,
    sustainBudget: 0.981, // 10 kg·cm — the PDF's hold-forever budget
    legClearOK, foreAftGap, clearNeeded, step,
    holdOK: stanceTauMax < 0.981,
  };
}

// ---- canvas plots (Desmos-style, minimal) ----
export function drawSpeedPlot(cv, model) {
  const g = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  g.clearRect(0, 0, W, H);
  const pad = 30;
  const xMax = 1.45, yMax = Math.max(model.vMax * 1.6, 0.02);
  const X = (r) => pad + (r / xMax) * (W - pad - 8);
  const Y = (v) => H - 18 - (v / yMax) * (H - 30);
  g.strokeStyle = '#2a2e36'; g.beginPath();
  g.moveTo(pad, 6); g.lineTo(pad, H - 18); g.lineTo(W - 6, H - 18); g.stroke();
  const line = (key, color, dash) => {
    g.strokeStyle = color; g.lineWidth = 1.8;
    g.setLineDash(dash || []);
    g.beginPath();
    model.curve.forEach((p, i) => { const x = X(p.rate), y = Y(Math.min(p[key], yMax)); i ? g.lineTo(x, y) : g.moveTo(x, y); });
    g.stroke(); g.setLineDash([]);
  };
  line('vNaive', '#7d8494', [4, 4]);   // the naive straight line from the video
  line('vReal', '#4f8fe8');            // torque-speed-limited reality
  // asymptote
  g.strokeStyle = '#e0a63c'; g.setLineDash([2, 3]);
  g.beginPath(); g.moveTo(pad, Y(model.vMax)); g.lineTo(W - 6, Y(model.vMax)); g.stroke();
  g.setLineDash([]);
  g.fillStyle = '#e0a63c'; g.font = '10px Segoe UI';
  g.fillText(`v_max ${(model.vMax * 100).toFixed(1)} cm/s — limited by ${model.limiter}`, pad + 4, Y(model.vMax) - 4);
  g.fillStyle = '#7d8494';
  g.fillText('naive (no torque-speed coupling)', W - 175, 14);
  g.fillStyle = '#4f8fe8'; g.fillText('actual', W - 175, 26);
  g.fillStyle = '#8f97a8'; g.fillText('commanded gait cycles /s →', W / 2 - 40, H - 5);
  g.save(); g.translate(10, H / 2 + 20); g.rotate(-Math.PI / 2); g.fillText('ground speed m/s', 0, 0); g.restore();
}

export function drawTorquePlot(cv, model) {
  const g = cv.getContext('2d');
  const W = cv.width, H = cv.height;
  g.clearRect(0, 0, W, H);
  const pad = 30;
  const yMax = Math.max(model.tauStall * 1.05, model.stanceTauMax * 1.2);
  const X = (t) => pad + t * (W - pad - 8);
  const Y = (v) => H - 18 - (v / yMax) * (H - 30);
  // zones: sustained budget (PDF 10 kg·cm) and stall
  g.fillStyle = '#1e3529'; g.fillRect(pad, Y(model.sustainBudget), W - pad - 8, H - 18 - Y(model.sustainBudget));
  g.fillStyle = '#2b1815'; g.fillRect(pad, 6, W - pad - 8, Y(model.tauStall) - 6);
  g.strokeStyle = '#2a2e36'; g.beginPath();
  g.moveTo(pad, 6); g.lineTo(pad, H - 18); g.lineTo(W - 6, H - 18); g.stroke();
  // swing/stance shading + torque trace
  g.lineWidth = 1.8;
  g.beginPath();
  model.tauTrace.forEach((p, i) => { const x = X(p.t), y = Y(Math.min(p.tau, yMax)); i ? g.lineTo(x, y) : g.moveTo(x, y); });
  g.strokeStyle = '#4f8fe8'; g.stroke();
  model.tauTrace.forEach((p) => {
    if (p.lifted) { g.fillStyle = '#9d6fff22'; g.fillRect(X(p.t) - 1.5, 6, 3, H - 24); }
  });
  g.fillStyle = '#4fdc8b'; g.font = '10px Segoe UI';
  g.fillText(`hold budget 10 kg·cm`, pad + 4, Y(model.sustainBudget) + 11);
  g.fillStyle = '#ff6b5e';
  g.fillText(`stall @ ${model.vRail.toFixed(1)}V = ${(model.tauStall / 0.0981).toFixed(0)} kg·cm`, pad + 4, Y(model.tauStall) + 11);
  g.fillStyle = '#8f97a8';
  g.fillText('worst-servo torque through one crawl cycle (purple = leg in air)', pad + 4, H - 5);
}
