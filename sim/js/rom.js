// rom.js — reachable-workspace sampling and self-collision checks.
// Workspace = cloud of wheel-contact points over the ROM grid, minus poses that
// collide with the body or cross the ground weirdly. Collisions treat femur/tibia
// as capsules and the body as a cylinder.

import { legFK, V } from './kin.js';

const LINK_RADIUS = 0.014; // capsule radius for links incl. servo bodies (m)

function segSegDist(p1, q1, p2, q2) {
  const d1 = V.sub(q1, p1), d2 = V.sub(q2, p2), r = V.sub(p1, p2);
  const a = V.dot(d1, d1), e = V.dot(d2, d2), f = V.dot(d2, r);
  let s, t;
  if (a <= 1e-12 && e <= 1e-12) return V.len(r);
  if (a <= 1e-12) { s = 0; t = Math.max(0, Math.min(1, f / e)); }
  else {
    const c = V.dot(d1, r);
    if (e <= 1e-12) { t = 0; s = Math.max(0, Math.min(1, -c / a)); }
    else {
      const b = V.dot(d1, d2), den = a * e - b * b;
      s = den > 1e-12 ? Math.max(0, Math.min(1, (b * f - c * e) / den)) : 0;
      t = (b * s + f) / e;
      if (t < 0) { t = 0; s = Math.max(0, Math.min(1, -c / a)); }
      else if (t > 1) { t = 1; s = Math.max(0, Math.min(1, (b - c) / a)); }
    }
  }
  const c1 = V.add(p1, V.scale(d1, s)), c2 = V.add(p2, V.scale(d2, t));
  return V.len(V.sub(c1, c2));
}

// distance from segment to the body cylinder surface (axis vertical through bodyAxisXY)
function segCylinderClear(p, q, axisXY, R, zBot, zTop) {
  let minClear = Infinity;
  for (let i = 0; i <= 8; i++) {
    const t = i / 8;
    const pt = V.add(p, V.scale(V.sub(q, p), t));
    const dr = Math.hypot(pt[0] - axisXY[0], pt[1] - axisXY[1]) - R;
    const dz = pt[2] < zBot ? zBot - pt[2] : pt[2] > zTop ? pt[2] - zTop : 0;
    const clear = pt[2] >= zBot && pt[2] <= zTop ? dr : (dr > 0 ? Math.hypot(dr, dz) : dz);
    minClear = Math.min(minClear, clear);
  }
  return minClear;
}

// Check one leg pose against body + a neighbor leg's pose. Returns list of issues.
export function poseCollisions(P, legsFK, bodyPos) {
  const issues = [];
  const zBot = bodyPos[2] - P.legMountH;
  const zTop = zBot + P.H;
  const axisXY = [bodyPos[0], bodyPos[1]];
  legsFK.forEach((fk, i) => {
    for (const [a, b, nm] of [[fk.p1, fk.knee, 'femur'], [fk.knee, fk.axle, 'tibia']]) {
      if (segCylinderClear(a, b, axisXY, P.R, zBot, zTop) < LINK_RADIUS) {
        issues.push(`leg ${i} ${nm} hits body`);
      }
    }
    if (Math.hypot(fk.axle[0] - axisXY[0], fk.axle[1] - axisXY[1]) < P.R + P.rw
      && fk.axle[2] > zBot - P.rw && fk.axle[2] < zTop + P.rw) {
      issues.push(`leg ${i} wheel hits body`);
    }
    for (let j = i + 1; j < legsFK.length; j++) {
      const o = legsFK[j];
      for (const [a1, b1, n1] of [[fk.p1, fk.knee, 'femur'], [fk.knee, fk.axle, 'tibia']]) {
        for (const [a2, b2, n2] of [[o.p1, o.knee, 'femur'], [o.knee, o.axle, 'tibia']]) {
          if (segSegDist(a1, b1, a2, b2) < 2 * LINK_RADIUS) {
            issues.push(`leg ${i} ${n1} hits leg ${j} ${n2}`);
          }
        }
      }
      if (V.len(V.sub(fk.axle, o.axle)) < 2 * P.rw) issues.push(`wheels ${i}&${j} collide`);
    }
  });
  return issues;
}

// Sample the reachable workspace of one leg → Float32Array of contact points +
// colors (green = free, red = collides with body). Cached by caller.
export function sampleWorkspace(P, legIdx, bodyPos, n1 = 7, n2 = 17, n3 = 17) {
  const phi = P.phis[legIdx];
  const pts = [], cols = [];
  const zBot = bodyPos[2] - P.legMountH, zTop = zBot + P.H;
  const axisXY = [bodyPos[0], bodyPos[1]];
  for (let i = 0; i < n1; i++) {
    const q1 = P.rom.roll[0] + (i / (n1 - 1)) * (P.rom.roll[1] - P.rom.roll[0]);
    for (let j = 0; j < n2; j++) {
      const q2 = P.rom.hip[0] + (j / (n2 - 1)) * (P.rom.hip[1] - P.rom.hip[0]);
      for (let k = 0; k < n3; k++) {
        const q3 = P.rom.knee[0] + (k / (n3 - 1)) * (P.rom.knee[1] - P.rom.knee[0]);
        const fk = legFK(P, phi, [q1, q2, q3], bodyPos);
        if (fk.contact[2] < -0.005) continue; // below ground: not usable from this body pose
        const collide =
          segCylinderClear(fk.p1, fk.knee, axisXY, P.R, zBot, zTop) < LINK_RADIUS ||
          segCylinderClear(fk.knee, fk.axle, axisXY, P.R, zBot, zTop) < LINK_RADIUS;
        pts.push(fk.contact[0], fk.contact[1], fk.contact[2]);
        cols.push(collide ? 0.9 : 0.15, collide ? 0.2 : 0.8, 0.25);
      }
    }
  }
  return { positions: new Float32Array(pts), colors: new Float32Array(cols) };
}
