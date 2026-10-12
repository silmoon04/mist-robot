// pipeline.js — the one-way dataflow:
//   config -> derive(P) -> pose targets -> IK -> FK -> masses/CoM
//          -> contacts -> GRF -> joint/wheel torques -> deflection
//          -> power (with voltage<->torque coupling) -> stability -> verdicts
// evaluate(cfg) is pure: same config in, same results out. Everything the UI,
// renderer, exports and self-tests display comes from this single object.

import { derive, footTargets, bodyPosOf, LEG_NAMES } from './config.js';
import { legIK, clampROM, legFK, V } from './kin.js';
import { massItems, centerOfMass } from './model.js';
import {
  solveGRF, contactForce, legJointTorques, wheelHoldingTorque,
  stability, femurDeflection,
} from './statics.js';
import { solvePower } from './power.js';

export function evaluate(cfg, opts = {}) {
  const P = derive(cfg);
  const bodyPos = bodyPosOf(cfg);
  const targets = footTargets(cfg);
  const gForce = V.scale(P.gDir, P.g); // m/s^2 vector

  // --- IK per leg (with ROM clamp) ---
  const legs = P.phis.map((phi, i) => {
    const ik = legIK(P, phi, targets[i], bodyPos, P.kneeSign);
    const rc = clampROM(ik.q, P.rom);
    const fk = rc.clamped ? legFK(P, phi, rc.q, bodyPos) : ik.fk;
    return {
      name: LEG_NAMES[i], phi, q: rc.q, fk,
      reachable: ik.reachable, romClamped: rc.clamped,
      ikErr: ik.err, target: targets[i],
    };
  });

  // --- masses / CoM ---
  const items = massItems(P, legs.map((l) => l.fk), bodyPos);
  const { M, com } = centerOfMass(items);

  // --- contacts (feet within 2mm of ground and not lifted) ---
  const contacts = [];
  legs.forEach((l, i) => {
    if (cfg.pose.mode === 'stand' && l.fk.contact[2] < 0.002 && l.reachable) {
      contacts.push({ legIdx: i, p: [l.fk.contact[0], l.fk.contact[1], 0] });
    }
  });

  // --- GRF ---
  const grf = contacts.length
    ? solveGRF(contacts, M, com, gForce)
    : { N: [], dropped: [], residual: 0, Nsum: 0, Ftang: [0, 0], frictionNeeded: 0 };
  const legContactForce = [null, null, null, null];
  contacts.forEach((c, ci) => {
    if (!grf.dropped.includes(ci)) legContactForce[c.legIdx] = contactForce(grf, ci);
  });

  // --- torques ---
  const legTorques = legs.map((l, i) => {
    const F = legContactForce[i] || [0, 0, 0];
    return legJointTorques(P, items, i, l.fk, F, gForce, !!legContactForce[i]);
  });
  // knee-servo demand after optional linkage (servo sits at hip, sees tau/ratio)
  const kneeServoTorques = legTorques.map((t) => P.linkage ? t[2] / P.linkRatio : t[2]);
  const servoTorques = legTorques.map((t, i) => [t[0], t[1], kneeServoTorques[i]]);
  const wheelTorques = legs.map((l, i) =>
    legContactForce[i] ? wheelHoldingTorque(P, l.fk, legContactForce[i]) : 0);

  // --- deflection ---
  const deflections = legs.map((l, i) =>
    femurDeflection(P, l.fk, legContactForce[i] || [0, 0, 0], !!legContactForce[i]));

  // --- power (speeds optional, from animation) ---
  let servoSpeeds = opts.speeds || null;
  if (servoSpeeds && P.linkage) {
    servoSpeeds = {
      ...servoSpeeds,
      joints: servoSpeeds.joints?.map((q) => q.map((w, j) => j === 2 ? w * P.linkRatio : w)),
    };
  }
  const power = solvePower(P, servoTorques, wheelTorques, servoSpeeds);

  // --- stability ---
  const stab = stability(
    contacts.filter((_, ci) => !grf.dropped.includes(ci)), com, P.gDir);

  // --- friction check ---
  const frictionOK = grf.frictionNeeded <= P.mu * grf.Nsum + 1e-9;

  // --- verdicts ---
  const th = cfg.thresholds;
  const maxUtil = Math.max(...power.perServo.map((s) => s.utilization), 0);
  const worstServo = power.perServo.reduce((w, s) => (s.utilization > (w?.utilization ?? -1) ? s : w), null);
  const maxLegAmp = Math.max(...power.legAmps, 0);
  const maxDeflMm = Math.max(...deflections, 0) * 1000;
  const status = (v, warn, bad, invert = false) => {
    if (invert) return v > warn ? 'ok' : v > bad ? 'warn' : 'bad';
    return v < warn ? 'ok' : v < bad ? 'warn' : 'bad';
  };
  const suspended = cfg.pose.mode === 'suspended';
  const verdicts = [
    {
      id: 'torque', label: 'Servo torque',
      value: `${(maxUtil * 100).toFixed(0)}% of stall@${P.cutoffV}V`,
      status: status(maxUtil, th.contRatio, th.peakRatio),
      detail: worstServo ? `worst: ${LEG_NAMES[worstServo.leg]} ${['roll', 'hip', 'knee', 'wheel'][worstServo.joint]} ${worstServo.tau.toFixed(2)} N·m` : '',
    },
    {
      id: 'legAmp', label: 'Leg current',
      value: `${maxLegAmp.toFixed(1)} A`,
      status: status(maxLegAmp, th.legAmpWarn, th.legAmpMax),
      detail: `${P.fuseLeg}A blade fuse per leg; stall math allows ${th.legAmpMax}A`,
    },
    {
      id: 'totAmp', label: 'Total current',
      value: `${power.iTotal.toFixed(1)} A`,
      status: status(power.iTotal, th.totAmpWarn, th.totAmpMax),
      detail: `${P.fuseMain}A main fuse`,
    },
    {
      id: 'vRail', label: 'Rail voltage',
      value: `${power.vRail.toFixed(2)} V`,
      status: status(power.vRail, th.vWarn, th.vMin, true),
      detail: `open-circuit ${power.vOC.toFixed(2)} V, sag ${(power.vOC - power.vRail).toFixed(2)} V`,
    },
    {
      id: 'tip', label: 'Tip margin',
      value: suspended ? 'n/a' : `${stab.minTipDeg.toFixed(1)}° / ${(stab.margin * 1000).toFixed(0)} mm`,
      status: suspended ? 'ok' : (grf.dropped.length || stab.margin < 0) ? 'bad'
        : status(stab.minTipDeg, th.tipWarnDeg, th.tipMinDeg, true),
      detail: grf.dropped.length ? `TIPPING: ${grf.dropped.length} foot lifting off` : `extra tilt to tip over`,
    },
    {
      id: 'defl', label: 'Femur flex',
      value: `${maxDeflMm.toFixed(2)} mm`,
      status: status(maxDeflMm, th.deflWarnMm, th.deflMaxMm),
      detail: `${cfg.leg.filament} ${cfg.leg.beamW}×${cfg.leg.beamT}mm beam`,
    },
    {
      id: 'friction', label: 'Wheel grip',
      value: suspended || !contacts.length ? 'n/a' : (frictionOK ? 'holds' : 'SLIPS'),
      status: suspended ? 'ok' : frictionOK ? 'ok' : 'bad',
      detail: `needs ${grf.frictionNeeded.toFixed(1)} N, µ×N = ${(P.mu * grf.Nsum).toFixed(1)} N`,
    },
    {
      id: 'reach', label: 'IK reach',
      value: legs.every((l) => l.reachable && !l.romClamped) ? 'all OK'
        : legs.map((l, i) => (!l.reachable ? LEG_NAMES[i] + '!' : l.romClamped ? LEG_NAMES[i] + '~' : null)).filter(Boolean).join(' '),
      status: legs.every((l) => l.reachable) ? (legs.some((l) => l.romClamped) ? 'warn' : 'ok') : 'bad',
      detail: '! = unreachable, ~ = ROM-clamped',
    },
  ];
  const overall = verdicts.some((v) => v.status === 'bad') ? 'bad'
    : verdicts.some((v) => v.status === 'warn') ? 'warn' : 'ok';

  return {
    P, cfg, bodyPos, targets, legs, items, M, com,
    contacts, grf, legContactForce, legTorques, servoTorques, wheelTorques,
    deflections, power, stab, frictionOK, verdicts, overall,
  };
}

// Worst-pose scan: sweep body height × stance radius, report utilization map.
export function scanPoses(cfg, nH = 8, nR = 8) {
  const c = JSON.parse(JSON.stringify(cfg));
  const out = [];
  const hMin = 40, hMax = Math.max(60, cfg.leg.femur + cfg.leg.tibia - 30);
  const rMin = cfg.body.cylD / 2 + 30, rMax = cfg.body.cylD / 2 + cfg.leg.femur + cfg.leg.tibia - 20;
  for (let i = 0; i < nH; i++) {
    for (let j = 0; j < nR; j++) {
      c.pose.bodyH = hMin + (i * (hMax - hMin)) / (nH - 1);
      c.pose.stanceR = rMin + (j * (rMax - rMin)) / (nR - 1);
      c.pose.lifts = [0, 0, 0, 0];
      const r = evaluate(c);
      const util = Math.max(...r.power.perServo.map((s) => s.utilization));
      out.push({
        bodyH: Math.round(c.pose.bodyH), stanceR: Math.round(c.pose.stanceR),
        util, tip: r.stab.minTipDeg,
        ok: r.legs.every((l) => l.reachable && !l.romClamped),
        overall: r.overall,
      });
    }
  }
  return out;
}
