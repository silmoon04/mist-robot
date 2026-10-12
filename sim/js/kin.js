// kin.js — pure-JS vector math + leg forward/inverse kinematics.
// All math here is SI (meters, radians). No rendering deps, unit-testable.
//
// Frames: world X = forward (phone face), Y = left, Z = up, ground plane z=0.
// Each leg mounts on the cylinder at azimuth phi (rad, CCW from +X).
// Mount frame: Xm = radial outward, Ym = tangential (CCW), Zm = up.
// Chain (per leg): q1 hip roll about Xm  ->  offset d1 along Xm
//                  q2 hip pitch about rolled Ym (0 = femur straight down, + = swings outward)
//                  q3 knee about same axis      (0 = tibia aligned with femur)
//                  wheel: disc radius rw, axis = knee axis; contact = lowest rim point.

export const V = {
  add: (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]],
  sub: (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]],
  scale: (a, s) => [a[0] * s, a[1] * s, a[2] * s],
  dot: (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2],
  cross: (a, b) => [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ],
  len: (a) => Math.hypot(a[0], a[1], a[2]),
  norm: (a) => {
    const l = Math.hypot(a[0], a[1], a[2]);
    return l < 1e-12 ? [0, 0, 0] : [a[0] / l, a[1] / l, a[2] / l];
  },
  rotZ: (a, ang) => {
    const c = Math.cos(ang), s = Math.sin(ang);
    return [c * a[0] - s * a[1], s * a[0] + c * a[1], a[2]];
  },
  // Rodrigues rotation of v about unit axis k by ang
  rotAxis: (v, k, ang) => {
    const c = Math.cos(ang), s = Math.sin(ang);
    const kxv = V.cross(k, v);
    const kdv = V.dot(k, v);
    return [
      v[0] * c + kxv[0] * s + k[0] * kdv * (1 - c),
      v[1] * c + kxv[1] * s + k[1] * kdv * (1 - c),
      v[2] * c + kxv[2] * s + k[2] * kdv * (1 - c),
    ];
  },
};

const DOWN = [0, 0, -1];

// Direction (unit) from wheel axle to ground-contact point, given wheel axis n (unit).
// = projection of straight-down into the wheel plane. Falls back to down if axis ~vertical.
export function wheelContactDir(n) {
  const d = V.sub(DOWN, V.scale(n, V.dot(DOWN, n)));
  const l = V.len(d);
  if (l < 1e-6) return DOWN.slice();
  return V.scale(d, 1 / l);
}

// P: derived SI params (see config.js derive()). leg: {phi} azimuth rad.
// q = [q1,q2,q3] rad. bodyPos = [x,y,z] of the leg-mount plane center (cylinder axis).
// Returns all joint points, axes, and link directions in WORLD coords.
export function legFK(P, phi, q, bodyPos) {
  const [q1, q2, q3] = q;
  const cph = Math.cos(phi), sph = Math.sin(phi);
  const rz = (v) => [cph * v[0] - sph * v[1], sph * v[0] + cph * v[1], v[2]];

  // mount-frame chain
  const s1 = Math.sin(q1), c1 = Math.cos(q1);
  const rx = (v) => [v[0], v[1] * c1 - v[2] * s1, v[1] * s1 + v[2] * c1]; // Rx(q1)
  const planar = (ang, L) => [L * Math.sin(ang), 0, -L * Math.cos(ang)]; // in leg plane

  const mount_m = [0, 0, 0];
  const p1_m = [P.d1, 0, 0]; // hip-pitch axis point (on roll axis -> unaffected by q1)
  const knee_m = V.add(p1_m, rx(planar(q2, P.L1)));
  const axle_m = V.add(knee_m, rx(planar(q2 + q3, P.L2)));

  const Xm = rz([1, 0, 0]);
  const a1 = Xm;                       // hip roll axis (world)
  // planar(+q) swings the link toward +Xm, which is a rotation about -Ym;
  // the joint axis must match that sign convention (self-test 5/6 enforce this)
  const a2 = rz(rx([0, -1, 0]));       // hip pitch axis (world, rolled)
  const a3 = a2;                       // knee axis parallel to hip pitch
  const wheelAxis = a2;                // wheel spins about knee-parallel axis

  const mountLocal = [P.mountR, 0, 0]; // hip-roll axis sits at cylinder radius + standoff
  const toWorld = (pm) => V.add(bodyPos, rz(V.add(mountLocal, pm)));

  const mount = toWorld(mount_m);
  const p1 = toWorld(p1_m);
  const knee = toWorld(knee_m);
  const axle = toWorld(axle_m);
  const u = wheelContactDir(wheelAxis);
  const contact = V.add(axle, V.scale(u, P.rw));

  return {
    mount, p1, knee, axle, contact,
    a1, a2, a3, wheelAxis,
    femurDir: V.norm(V.sub(knee, p1)),
    tibiaDir: V.norm(V.sub(axle, knee)),
    q: q.slice(),
  };
}

// Inverse kinematics: contact-point target (world) -> q. kneeSign -1 = knee bows
// outward/up (spider), +1 = tucked/inward. Iterates because the axle offset from the
// contact point depends on the roll angle.
export function legIK(P, phi, targetContact, bodyPos, kneeSign = -1) {
  let u = DOWN.slice();
  let q = [0, 0, 0];
  let reachable = true;
  // The wheel contact offset depends on roll. Four fixed-point iterations can
  // miss otherwise valid targets by several millimetres near the ROM edges.
  for (let iter = 0; iter < 12; iter++) {
    const axleT = V.sub(targetContact, V.scale(u, P.rw));
    // into mount frame
    const rel = V.sub(axleT, bodyPos);
    const vlocal = V.rotZ(rel, -phi);
    const v = V.sub(vlocal, [P.mountR, 0, 0]);
    const [vx, vy, vz] = v;

    // roll: leg-plane points satisfy y = rho*sin(q1), z = -rho*cos(q1)
    const q1 = Math.atan2(vy, -vz);
    const rho = Math.hypot(vy, vz);
    const px = vx - P.d1;
    const r2 = px * px + rho * rho;

    const D = (r2 - P.L1 * P.L1 - P.L2 * P.L2) / (2 * P.L1 * P.L2);
    reachable = D >= -1 && D <= 1;
    const Dc = Math.max(-1, Math.min(1, D));
    const q3 = kneeSign * Math.acos(Dc);
    const gamma = Math.atan2(px, rho); // target angle from straight-down toward +Xm
    const q2 = gamma - Math.atan2(P.L2 * Math.sin(q3), P.L1 + P.L2 * Math.cos(q3));
    q = [q1, q2, q3];

    // refine wheel-contact direction with the new pose
    const fk = legFK(P, phi, q, bodyPos);
    u = wheelContactDir(fk.wheelAxis);
  }
  const fk = legFK(P, phi, q, bodyPos);
  const err = V.len(V.sub(fk.contact, targetContact));
  // wheel-offset iteration can fail to converge near roll ~±90° (wheel plane
  // vertical); a solution that misses the target is not a usable pose
  if (err > 0.0005) reachable = false;
  return { q, reachable, err, fk };
}

// Clamp q to ROM limits (rad). Returns {q, clamped:boolean}
export function clampROM(q, rom) {
  const c = [
    Math.max(rom.roll[0], Math.min(rom.roll[1], q[0])),
    Math.max(rom.hip[0], Math.min(rom.hip[1], q[1])),
    Math.max(rom.knee[0], Math.min(rom.knee[1], q[2])),
  ];
  const clamped = Math.abs(c[0] - q[0]) + Math.abs(c[1] - q[1]) + Math.abs(c[2] - q[2]) > 1e-9;
  return { q: c, clamped };
}
