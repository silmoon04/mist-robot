// selftest.js — invariant checks over the math core. Run from the UI button or
// window.sim.selftest(). Every test returns {name, pass, detail}. These exist to
// catch sign/frame/unit bugs — the classic quadruped-sim failure modes.

import { defaultConfig, derive, footTargets, bodyPosOf } from './config.js';
import { legFK, legIK, V } from './kin.js';
import { massItems, centerOfMass, distalMasses } from './model.js';
import { solveGRF, legJointTorques } from './statics.js';
import { evaluate } from './pipeline.js';

function approx(a, b, tol) { return Math.abs(a - b) <= tol; }

export function runSelfTests(inputCfg = defaultConfig()) {
  const tests = [];
  const T = (name, pass, detail = '') => tests.push({ name, pass: !!pass, detail });

  // Validate the current geometry/masses/limits, normalized to a level,
  // symmetric stance so slider changes are actually covered by this button.
  const cfg = JSON.parse(JSON.stringify(inputCfg));
  cfg.pose = { ...cfg.pose, mode: 'stand', bodyX: 0, bodyY: 0, azOff: 0, lifts: [0, 0, 0, 0], stepX: [0, 0, 0, 0] };
  cfg.env = { ...cfg.env, slopeDeg: 0, slopeHeading: 0 };
  const P = derive(cfg);
  const bodyPos = bodyPosOf(cfg);

  // 1. FK->IK roundtrip from known-valid joint poses. Do not skip failures:
  // legIK's reachable flag includes its own error threshold, so skipping
  // unreachable results made the previous test tautological.
  {
    let maxErr = 0, nFailed = 0, rng = 12345;
    const rand = () => { rng = (rng * 1103515245 + 12345) & 0x7fffffff; return rng / 0x7fffffff; };
    for (let k = 0; k < 200; k++) {
      const li = k % 4, phi = P.phis[li];
      const q1 = P.rom.roll[0] * 0.5 + rand() * (P.rom.roll[1] - P.rom.roll[0]) * 0.5;
      const q2 = P.rom.hip[0] * 0.25 + P.rom.hip[1] * 0.25
        + rand() * (P.rom.hip[1] - P.rom.hip[0]) * 0.5;
      const kneeLimit = P.kneeSign < 0 ? Math.abs(P.rom.knee[0]) : Math.abs(P.rom.knee[1]);
      const q3 = P.kneeSign * (0.2 + rand() * Math.max(0.05, Math.min(kneeLimit, 1.9) - 0.2));
      const target = legFK(P, phi, [q1, q2, q3], bodyPos).contact;
      const ik = legIK(P, phi, target, bodyPos, P.kneeSign);
      maxErr = Math.max(maxErr, ik.err);
      if (!ik.reachable || ik.err >= 5e-4) nFailed++;
    }
    T('FK↔IK roundtrip < 0.5 mm', nFailed === 0 && maxErr < 5e-4,
      `max err ${(maxErr * 1000).toFixed(3)} mm, ${nFailed}/200 failed`);
  }

  // 2-4. GRF invariants on the symmetric default stance
  {
    const r = evaluate(cfg);
    const W = r.M * 9.81;
    T('ΣGRF = weight', approx(r.grf.Nsum, W, W * 1e-6), `Σ=${r.grf.Nsum.toFixed(3)} N vs W=${W.toFixed(3)} N`);
    const Ns = r.grf.N;
    // note: not exactly equal — the phone biases the front pair; check pair symmetry
    const pairSym = Ns.length === 4 && Math.abs(Ns[0] - Ns[1]) < 0.01 && Math.abs(Ns[2] - Ns[3]) < 0.01;
    T('symmetric stance → L/R pair-equal forces', pairSym, `N = ${Ns.map((n) => n.toFixed(2)).join(', ')} (${Ns.length} contacts)`);
    T('GRF residual ≈ 0', r.grf.residual < 1e-6, `residual ${r.grf.residual.toExponential(2)}`);
    T('CoM on axis for symmetric config', Math.hypot(r.com[0] - cfgComExpectX(cfg), r.com[1]) < 0.02, `com=[${r.com.map((c) => (c * 1000).toFixed(1))}] mm`);
  }

  // 5. gravity joint torques vs finite-difference of potential energy (suspended)
  {
    const cs = JSON.parse(JSON.stringify(cfg));
    cs.pose.mode = 'suspended';
    cs.pose.lifts = [10, 0, 25, 5]; // asymmetric on purpose
    const Ps = derive(cs);
    const bp = bodyPosOf(cs);
    const targets = footTargets(cs);
    const gF = V.scale(Ps.gDir, Ps.g);
    let maxDiff = 0, sample = '';
    for (let li = 0; li < 4; li++) {
      const ik = legIK(Ps, Ps.phis[li], targets[li], bp, Ps.kneeSign);
      const q0 = ik.q;
      const U = (q) => {
        const fk = legFK(Ps, Ps.phis[li], q, bp);
        const items = massItems(Ps, [fk, fk, fk, fk], bp).filter((it) => it.group === 'leg0');
        // reuse leg0 group for this leg's chain: positions computed from fk are what matter
        return -items.reduce((s, it) => s + it.m * V.dot(gF, it.p), 0);
      };
      const fk0 = legFK(Ps, Ps.phis[li], q0, bp);
      const items0 = massItems(Ps, [fk0, fk0, fk0, fk0], bp);
      const tau = legJointTorques(Ps, items0, 0, fk0, [0, 0, 0], gF, false);
      for (let j = 0; j < 3; j++) {
        const e = 1e-5;
        const qp = q0.slice(); qp[j] += e;
        const qm = q0.slice(); qm[j] -= e;
        const dU = (U(qp) - U(qm)) / (2 * e);
        const diff = Math.abs(-dU - tau[j]);
        if (diff > maxDiff) { maxDiff = diff; sample = `leg${li} j${j}: τ=${tau[j].toFixed(4)} vs -dU/dq=${(-dU).toFixed(4)}`; }
      }
    }
    T('gravity torque = -∂U/∂q (finite diff)', maxDiff < 1e-4, `${sample} (maxΔ ${maxDiff.toExponential(2)})`);
  }

  // 6. contact-point Jacobian column = a × r (validates axes/points bookkeeping)
  {
    const targets = footTargets(cfg);
    const ik = legIK(P, P.phis[0], targets[0], bodyPos, P.kneeSign);
    const q0 = ik.q;
    const fk0 = legFK(P, P.phis[0], q0, bodyPos);
    const joints = [
      { p: fk0.mount, a: fk0.a1 },
      { p: fk0.p1, a: fk0.a2 },
      { p: fk0.knee, a: fk0.a3 },
    ];
    let maxDiff = 0;
    for (let j = 0; j < 3; j++) {
      const e = 1e-6;
      const qp = q0.slice(); qp[j] += e;
      const qm = q0.slice(); qm[j] -= e;
      const num = V.scale(V.sub(legFK(P, P.phis[0], qp, bodyPos).axle, legFK(P, P.phis[0], qm, bodyPos).axle), 1 / (2 * e));
      const ana = V.cross(joints[j].a, V.sub(fk0.axle, joints[j].p));
      maxDiff = Math.max(maxDiff, V.len(V.sub(num, ana)));
    }
    T('axle Jacobian: ∂p/∂q = a×r', maxDiff < 1e-6, `maxΔ ${maxDiff.toExponential(2)} m/rad`);
  }

  // 7. stability symmetry: +bodyY vs -bodyY lean must mirror the tip margin
  {
    const ca = JSON.parse(JSON.stringify(cfg)); ca.pose.bodyY = 40;
    const cb = JSON.parse(JSON.stringify(cfg)); cb.pose.bodyY = -40;
    const ra = evaluate(ca), rb = evaluate(cb);
    T('lean ±Y → mirrored tip margin', approx(ra.stab.minTipDeg, rb.stab.minTipDeg, 0.05),
      `+Y: ${ra.stab.minTipDeg.toFixed(2)}°, -Y: ${rb.stab.minTipDeg.toFixed(2)}°`);
  }

  // 8. three-leg case: lifted leg gets no force, sum still = W
  {
    const c3 = JSON.parse(JSON.stringify(cfg));
    c3.pose.lifts = [40, 0, 0, 0];
    const r3 = evaluate(c3);
    const W = r3.M * 9.81;
    T('3-contact: ΣGRF = W, lifted leg = 0', r3.contacts.length === 3 && approx(r3.grf.Nsum, W, W * 1e-6),
      `${r3.contacts.length} contacts, Σ=${r3.grf.Nsum.toFixed(2)} vs W=${W.toFixed(2)}`);
  }

  // 9. slope tilts load downhill (uphill feet unload)
  {
    const csl = JSON.parse(JSON.stringify(cfg));
    csl.env.slopeDeg = 15; csl.env.slopeHeading = 0; // gravity tips toward +X
    const rs = evaluate(csl);
    const frontN = rs.contacts.map((c, i) => ({ x: c.p[0], n: rs.grf.N[i] }));
    const front = frontN.filter((f) => f.x > 0).reduce((s, f) => s + f.n, 0);
    const rear = frontN.filter((f) => f.x < 0).reduce((s, f) => s + f.n, 0);
    T('15° slope shifts load downhill', front > rear, `downhill ${front.toFixed(1)} N vs uphill ${rear.toFixed(1)} N`);
  }

  // 10. power fixed point converged & sane
  {
    const r = evaluate(cfg);
    T('power: rail below OC, above 8V', r.power.vRail < r.power.vOC && r.power.vRail > 8,
      `Voc=${r.power.vOC.toFixed(2)} rail=${r.power.vRail.toFixed(2)} I=${r.power.iTotal.toFixed(2)}A`);
  }

  // 11. linkage halves knee-servo demand at ratio 2 & relocates mass
  {
    const cl = JSON.parse(JSON.stringify(cfg));
    cl.leg.linkage = true; cl.leg.linkRatio = 2.0;
    const rn = evaluate(cfg), rl = evaluate(cl);
    const kneeN = Math.abs(rn.servoTorques[0][2]);
    const kneeL = Math.abs(rl.servoTorques[0][2]);
    T('linkage ratio 2 → ~half knee-servo torque', kneeL < kneeN * 0.75,
      `plain ${kneeN.toFixed(3)} N·m vs linkage ${kneeL.toFixed(3)} N·m (joint torque itself may differ slightly via mass shift)`);
  }

  // 12. remote wheel servo lightens distal load: suspended-hold hip torque must
  // drop foot -> knee -> hip, and total mass rises only by the transmission
  {
    const mk = (mount) => {
      const c = JSON.parse(JSON.stringify(cfg));
      c.pose.mode = 'suspended';
      c.wheel.driveMount = mount;
      return evaluate(c);
    };
    const rF = mk('foot'), rK = mk('knee'), rH = mk('hip');
    const hip = (r) => Math.abs(r.legTorques[0][1]);
    const knee = (r) => Math.abs(r.legTorques[0][2]);
    // true invariants: knee joint stops carrying the servo when it moves off the
    // foot; hip joint is unloaded by a hip mount; mass grows by the belt stages.
    // (NOT monotone foot>knee>hip for hip torque: in the spider sprawl the knee
    // sits farther out than the foot, so a knee mount can RAISE hip torque.)
    const ok = knee(rK) < knee(rF) && knee(rH) < knee(rF) && hip(rH) < hip(rF)
      && Math.abs((rH.M - rF.M) * 1000 - 2 * cfg.wheel.transMass * 4) < 1;
    T('remote wheel servo unloads knee/hip correctly', ok,
      `knee τ foot/knee/hip: ${knee(rF).toFixed(3)}/${knee(rK).toFixed(3)}/${knee(rH).toFixed(3)} · ` +
      `hip τ: ${hip(rF).toFixed(3)}/${hip(rK).toFixed(3)}/${hip(rH).toFixed(3)} N·m ` +
      `(knee-mount raising hip τ is real: the knee sticks out farther than the foot in sprawl)`);
  }

  return tests;
}

// expected CoM x for symmetric config: phone (front) pulls +X, battery az pulls its way
function cfgComExpectX() { return 0.005; } // loose: within ±20mm of slightly-forward is checked above

export function formatTests(tests) {
  return tests.map((t) => `${t.pass ? 'PASS' : 'FAIL'}  ${t.name}${t.detail ? ' — ' + t.detail : ''}`).join('\n');
}
