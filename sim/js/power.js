// power.js — electrical model: servo currents from torque demand, pack sag,
// fuse margins, runtime. Torque capacity and current scale ~linearly with rail
// voltage, and the rail sags with total current -> solved by fixed-point iteration.

import { socToV } from './config.js';

// legTorques: [4][3] signed N·m, wheelTorques: [4] N·m (holding),
// speeds: same shapes rad/s (0 for statics).
export function solvePower(P, legTorques, wheelTorques, speeds) {
  const vOC = socToV(P.soc) * P.cells;
  let vRail = vOC;
  let iTotal = 0;
  let perServo = [];

  for (let iter = 0; iter < 8; iter++) {
    const stallNm = P.stallNm12 * (vRail / 12);
    const stallA = P.stallA12 * (vRail / 12);
    perServo = [];
    for (let l = 0; l < 4; l++) {
      for (let j = 0; j < 3; j++) {
        const tau = Math.abs(legTorques[l][j]);
        const w = speeds ? Math.abs(speeds.joints?.[l]?.[j] ?? 0) : 0;
        perServo.push({
          leg: l, joint: j,
          tau, w,
          amps: P.idleA + (stallNm > 1e-9 ? tau / stallNm : 0) * (stallA - P.idleA),
        });
      }
      const tauW = Math.abs(wheelTorques[l] || 0);
      const wW = speeds ? Math.abs(speeds.wheels?.[l] ?? 0) : 0;
      perServo.push({
        leg: l, joint: 3, tau: tauW, w: wW,
        amps: P.idleA + (stallNm > 1e-9 ? tauW / stallNm : 0) * (stallA - P.idleA),
      });
    }
    iTotal = perServo.reduce((s, sv) => s + sv.amps, 0) + 0.35; // + logic (ESP32/UBEC/sensors)
    const vNew = vOC - iTotal * P.rInt;
    if (Math.abs(vNew - vRail) < 1e-4) { vRail = vNew; break; }
    vRail = vNew;
  }

  const stallNmAtRail = P.stallNm12 * (vRail / 12);
  const stallNmWorst = P.stallNm12 * (P.cutoffV / 12); // capability at brown-out voltage
  const wNoLoad = P.wNoLoad12 * (vRail / 12);

  const legAmps = [0, 0, 0, 0];
  perServo.forEach((sv) => { legAmps[sv.leg] += sv.amps; });

  // torque-speed feasibility: available torque at speed w
  perServo.forEach((sv) => {
    const availAtW = stallNmAtRail * Math.max(0, 1 - sv.w / Math.max(wNoLoad, 1e-6));
    sv.utilization = sv.tau / Math.max(stallNmWorst, 1e-9);       // vs worst-case rating
    sv.speedFeasible = sv.tau <= availAtW + 1e-9;
    sv.speedUse = wNoLoad > 1e-9 ? sv.w / wNoLoad : 0;
  });

  return {
    vOC, vRail, iTotal, legAmps, perServo,
    stallNmAtRail, stallNmWorst, wNoLoad,
    watts: vRail * iTotal,
    runtimeMin: iTotal > 0.01 ? (P.capAh * P.soc) / iTotal * 60 : Infinity,
    converged: true,
  };
}
