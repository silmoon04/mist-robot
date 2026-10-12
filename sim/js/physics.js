// physics.js — dynamic layer on Rapier (rigid-body contact physics).
// The analytic pipeline stays the source of truth for numbers; this layer answers
// "does it actually fall over / recover / roll" with real contacts and momentum.
// Bodies are built from the CURRENT analytic pose, joints get position motors with
// stiffness capped near the servo's real stall torque, so overloaded joints
// genuinely collapse instead of magically holding.

import * as THREE from 'three';
import { V } from './kin.js';

let RAPIER = null;

const QY2Z = { w: Math.SQRT1_2, x: Math.SQRT1_2, y: 0, z: 0 }; // rapier y-axis prims -> z-up

// Collision groups: robot parts overlap at every joint (capsule ends, wheel
// balls around axles), so robot-vs-robot contacts must be off or the solver
// generates huge internal forces. Self-collision is checked analytically instead.
const GRP_GROUND = 0x00010002; // membership 1, collides with 2
const GRP_ROBOT = 0x00020001;  // membership 2, collides with 1

function quatFromYTo(dir) {
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(...dir));
  return { w: q.w, x: q.x, y: q.y, z: q.z };
}

export class PhysicsSim {
  constructor() {
    this.world = null;
    this.active = false;
    this.visual = new THREE.Group();
    this.grfAvg = [0, 0, 0, 0];
    this.status = { tiltDeg: 0, fallen: false, bodyZ: 0 };
    this._stepAccumulator = 0;
  }

  async ensureInit() {
    if (RAPIER) return true;
    try {
      RAPIER = (await import('rapier')).default ?? (await import('rapier'));
      if (RAPIER.init) await RAPIER.init();
      return true;
    } catch (e) {
      console.error('Rapier failed to load:', e);
      return false;
    }
  }

  destroy() {
    if (this.world) { this.world.free(); this.world = null; }
    this.active = false;
    this.visual.clear();
    this.bodies = null;
    this._stepAccumulator = 0;
  }

  // Build the dynamic world from an analytic result.
  build(res, opts = {}) {
    this.destroy();
    const P = res.P;
    this.res = res;
    const slope = (opts.slopeDeg || 0) * Math.PI / 180;
    const head = (opts.slopeHeading || 0) * Math.PI / 180;
    // Work in the ground frame, matching the analytic model: the ground stays
    // flat and gravity tilts downhill. This avoids spawning upright wheels
    // intersecting a separately tilted ground plane.
    this.world = new RAPIER.World({
      x: 9.81 * Math.sin(slope) * Math.cos(head),
      y: 9.81 * Math.sin(slope) * Math.sin(head),
      z: -9.81 * Math.cos(slope),
    });
    // small links (I ~ 1e-4 kg·m²) + stiff explicit servo PD demand a small step:
    // stability needs kP < ~4·I/dt², kD < ~2·I/dt  ->  960 Hz gives plenty of margin
    this.world.timestep = 1 / 960;

    const groundRB = this.world.createRigidBody(RAPIER.RigidBodyDesc.fixed()
      .setTranslation(0, 0, -0.05));
    this.world.createCollider(
      RAPIER.ColliderDesc.cuboid(3, 3, 0.05).setFriction(res.P.mu)
        .setCollisionGroups(GRP_GROUND), groundRB);

    const dropH = opts.dropMm ? opts.dropMm / 1000 : 0;
    const lift = (p) => [p[0], p[1], p[2] + dropH];

    // ---- body ----
    // Hip-roll servo cases are fixed to the chassis side of each roll joint.
    const bodyItems = res.items.filter((i) => i.group === 'body' || i.name === 'hipRollServo');
    const bodyMass = bodyItems.reduce((s, i) => s + i.m, 0);
    const bodyComW = V.scale(bodyItems.reduce((s, i) => V.add(s, V.scale(i.p, i.m)), [0, 0, 0]), 1 / bodyMass);
    const bodyPos = lift(res.bodyPos);
    const comLocal = V.sub(lift(bodyComW), bodyPos);
    const Ixx = bodyMass * (3 * P.R * P.R + P.H * P.H) / 12;
    const Izz = 0.5 * bodyMass * P.R * P.R;
    const bodyRB = this.world.createRigidBody(RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(...bodyPos)
      .setAdditionalMassProperties(bodyMass, { x: comLocal[0], y: comLocal[1], z: comLocal[2] },
        { x: Ixx, y: Ixx, z: Izz }, { w: 1, x: 0, y: 0, z: 0 }));
    const bottomZLocal = -P.legMountH + P.H / 2;
    this.world.createCollider(
      RAPIER.ColliderDesc.cylinder(P.H / 2, P.R)
        .setTranslation(0, 0, bottomZLocal)
        .setRotation(QY2Z).setDensity(0).setFriction(0.4)
        .setCollisionGroups(GRP_ROBOT), bodyRB);
    this.bodyRB = bodyRB;
    this.topLocal = [0, 0, -P.legMountH + P.H];

    // ---- legs ----
    const capDensity = (m, halfHeight, r) => m / Math.max(
      Math.PI * r * r * (2 * halfHeight) + (4 / 3) * Math.PI * r ** 3,
      1e-9,
    );
    this.wheelColliders = [];
    this.joints = [];
    this.hinges = [];
    this.bodies = [bodyRB];
    this.colQuat = [null]; // per-body initial collider rotation (for visuals)
    this.meshMap = [];

    res.legs.forEach((leg, li) => {
      const fk = leg.fk;
      const mkLink = (a, b, mass, r) => {
        const mid = lift(V.scale(V.add(a, b), 0.5));
        const len = V.len(V.sub(b, a));
        const rb = this.world.createRigidBody(RAPIER.RigidBodyDesc.dynamic().setTranslation(...mid));
        const q = quatFromYTo(V.norm(V.sub(b, a)));
        const halfHeight = Math.max(len / 2 - r, 0.005);
        this.world.createCollider(
          RAPIER.ColliderDesc.capsule(halfHeight, r)
            .setRotation(q)
            .setDensity(capDensity(mass, halfHeight, r)).setFriction(0.3)
            .setCollisionGroups(GRP_ROBOT), rb);
        this.bodies.push(rb);
        this.colQuat.push(new THREE.Quaternion(q.x, q.y, q.z, q.w));
        return rb;
      };

      // hip bracket: small body carrying the d1 offset (roll joint connects it to the barrel)
      const bracketMid = lift(V.scale(V.add(fk.mount, fk.p1), 0.5));
      const bracket = this.world.createRigidBody(RAPIER.RigidBodyDesc.dynamic().setTranslation(...bracketMid));
      const bq = quatFromYTo(V.norm(V.sub(fk.p1, fk.mount)));
      const bracketHalfHeight = Math.max(P.d1 / 2, 0.008);
      this.world.createCollider(RAPIER.ColliderDesc.capsule(bracketHalfHeight, 0.014)
        .setRotation(bq)
        .setDensity(capDensity(P.mServo * (P.linkage ? 2 : 1) + 0.02, bracketHalfHeight, 0.014))
        .setCollisionGroups(GRP_ROBOT), bracket);
      this.bodies.push(bracket);
      this.colQuat.push(new THREE.Quaternion(bq.x, bq.y, bq.z, bq.w));

      // wheel-drive servo mass rides on the body its mount sits on
      const wm = P.wheelMount;
      const femurMass = P.mFemur + (P.linkage ? P.mLinkRod : P.mServo)
        + (wm === 'hip' ? P.mServo + P.mTrans : 0);
      const femur = mkLink(fk.p1, fk.knee, femurMass, 0.013);
      const tibiaMass = P.mTibia + (wm === 'knee' ? P.mServo : 0) + (wm !== 'foot' ? P.mTrans : 0);
      const tibia = mkLink(fk.knee, fk.axle, tibiaMass, 0.012);

      const wheelRB = this.world.createRigidBody(RAPIER.RigidBodyDesc.dynamic().setTranslation(...lift(fk.axle)));
      const wheelMass = P.mWheel + (wm === 'foot' ? P.mServo : 0);
      const wcol = this.world.createCollider(
        RAPIER.ColliderDesc.ball(P.rw).setDensity(wheelMass / ((4 / 3) * Math.PI * P.rw ** 3))
          .setFriction(P.mu).setActiveEvents(RAPIER.ActiveEvents.CONTACT_FORCE_EVENTS)
          .setContactForceEventThreshold(0.1)
          .setCollisionGroups(GRP_ROBOT), wheelRB);
      this.bodies.push(wheelRB);
      this.colQuat.push(null);
      this.wheelColliders[li] = wcol.handle;

      // joints (anchors = world point minus body translation; rotations are identity at build)
      const mkRev = (rb1, rb2, worldPt, axis) => {
        const t1 = rb1.translation(), t2 = rb2.translation();
        const p = lift(worldPt);
        const data = RAPIER.JointData.revolute(
          { x: p[0] - t1.x, y: p[1] - t1.y, z: p[2] - t1.z },
          { x: p[0] - t2.x, y: p[1] - t2.y, z: p[2] - t2.z },
          { x: axis[0], y: axis[1], z: axis[2] });
        const j = this.world.createImpulseJoint(data, rb1, rb2, true);
        return j;
      };
      const jRoll = mkRev(bodyRB, bracket, fk.mount, fk.a1);
      const jHip = mkRev(bracket, femur, fk.p1, fk.a2);
      const jKnee = mkRev(femur, tibia, fk.knee, fk.a3);
      const jWheel = mkRev(tibia, wheelRB, fk.axle, fk.wheelAxis);
      this.joints.push({ jRoll, jHip, jKnee, jWheel });

      // Servo motors are applied MANUALLY each substep (Rapier's built-in joint
      // motor behaved acceleration-based regardless of MotorModel in this build —
      // torque ~60× too weak for small links). PD about the hinge axis, hard
      // torque clamp at the real stall torque: overloads genuinely collapse.
      // GAINS ARE PER-HINGE, capped by the explicit-integration stability bound
      // of the child body's inertia about the axis (kP < 4I/dt², kD < 2I/dt) —
      // fixed gains shake violently as soon as a config makes a body light.
      const dt = this.world.timestep;
      const kpNom = res.power.stallNmAtRail / (3 * Math.PI / 180);
      const mkHinge = (rb1, rb2, axisW, Ieff) => ({
        rb1, rb2, axisLocal1: axisW.slice(), // rb1 rotation is identity at build
        target: 0, applied: 0,
        kP: Math.min(kpNom, 0.35 * 4 * Ieff / (dt * dt)),
        kD: Math.min(0.08, 0.35 * 2 * Ieff / dt),
      });
      const Ibracket = 0.5 * (P.mServo + 0.02) * 0.014 * 0.014; // about its own long (roll) axis
      const Ifemur = femurMass * P.L1 * P.L1 / 3;               // about the hip end
      const Itibia = tibiaMass * P.L2 * P.L2 / 3;
      const Iwheel = 0.4 * wheelMass * P.rw * P.rw;
      this.hinges.push({
        leg: li,
        servos: [
          mkHinge(bodyRB, bracket, fk.a1, Ibracket),
          mkHinge(bracket, femur, fk.a2, Ifemur),
          mkHinge(femur, tibia, fk.a3, Itibia),
        ],
        wheel: { ...mkHinge(tibia, wheelRB, fk.wheelAxis, Iwheel), targetVel: 0 },
      });
    });

    // structural damping (printed plastic + servo gearbox friction) — also
    // bleeds off any residual high-frequency energy from the explicit servo PD
    this.bodies.forEach((rb, i) => {
      rb.setAngularDamping(i === 0 ? 0.5 : 2.0);
      rb.setLinearDamping(i === 0 ? 0.1 : 0.3);
    });

    this.buildVisual(res, dropH);
    this.eventQueue = new RAPIER.EventQueue(true);
    this.grfAvg = [0, 0, 0, 0];
    this.active = true;
  }

  buildVisual(res, dropH) {
    this.visual.clear();
    this.meshMap = [];
    const P = res.P;
    const mat = (c) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.6 });
    this.bodies.forEach((rb, bi) => {
      let mesh;
      if (bi === 0) {
        const g = new THREE.Group();
        const cyl = new THREE.Mesh(new THREE.CylinderGeometry(P.R, P.R, P.H, 28), mat(0xd8d2c6));
        cyl.rotation.x = Math.PI / 2;
        cyl.position.z = -P.legMountH + P.H / 2;
        g.add(cyl);
        mesh = g;
      } else {
        const idx = (bi - 1) % 4; // bracket, femur, tibia, wheel
        if (idx === 3) {
          mesh = new THREE.Mesh(new THREE.SphereGeometry(P.rw, 16, 12), mat(0x15181d));
        } else {
          mesh = new THREE.Mesh(new THREE.CapsuleGeometry(0.013, idx === 1 ? P.L1 : idx === 2 ? P.L2 : Math.max(P.d1, 0.02), 4, 8), mat(idx === 0 ? 0x22262e : 0xcfc9bd));
        }
      }
      this.visual.add(mesh);
      this.meshMap.push({ rb, mesh, isBody: bi === 0 });
    });
  }

  // rotate capsules to match their collider orientation once (colliders were
  // rotated relative to the body; bodies start with identity rotation)
  syncVisual() {
    if (!this.active) return;
    this.meshMap.forEach(({ rb, mesh }, i) => {
      const t = rb.translation(), r = rb.rotation();
      mesh.position.set(t.x, t.y, t.z);
      mesh.quaternion.set(r.x, r.y, r.z, r.w);
      // capsules were built along their collider axis; reapply under body rotation
      const cq = this.colQuat?.[i];
      if (cq) mesh.quaternion.multiply(cq);
    });
  }

  // hinge angle: twist of the relative rotation (rb1^-1 * rb2) about the axis
  hingeState(h) {
    const q1 = this.q(h.rb1), q2 = this.q(h.rb2);
    const rel = q1.clone().invert().multiply(q2);
    const a = h.axisLocal1;
    const proj = rel.x * a[0] + rel.y * a[1] + rel.z * a[2];
    let ang = 2 * Math.atan2(proj, rel.w);
    if (ang > Math.PI) ang -= 2 * Math.PI;
    if (ang < -Math.PI) ang += 2 * Math.PI;
    const axisW = new THREE.Vector3(...a).applyQuaternion(q1);
    const w1 = h.rb1.angvel(), w2 = h.rb2.angvel();
    const relW = (w2.x - w1.x) * axisW.x + (w2.y - w1.y) * axisW.y + (w2.z - w1.z) * axisW.z;
    return { ang, vel: relW, axisW };
  }
  q(rb) { const r = rb.rotation(); return new THREE.Quaternion(r.x, r.y, r.z, r.w); }

  applyServoTorques(dt, driveV, turn) {
    const tauMax = this.res.power.stallNmAtRail;
    const P = this.res.P;
    this.hinges.forEach((leg, li) => {
      leg.servos.forEach((h) => {
        const s = this.hingeState(h);
        let tau = h.kP * (h.target - s.ang) - h.kD * s.vel;
        tau = Math.max(-tauMax, Math.min(tauMax, tau));
        h.applied = tau;
        const tv = { x: s.axisW.x * tau * dt, y: s.axisW.y * tau * dt, z: s.axisW.z * tau * dt };
        h.rb2.applyTorqueImpulse(tv, true);
        h.rb1.applyTorqueImpulse({ x: -tv.x, y: -tv.y, z: -tv.z }, true);
      });
      // wheel: velocity servo (wheel mode). Target = desired body twist projected
      // onto THIS wheel's rolling direction (axis × up) — with sprawled legs the
      // rolling directions differ per leg, so naive same-sign commands just scrub.
      const h = leg.wheel;
      const s = this.hingeState(h);
      const rollDir = [s.axisW.y, -s.axisW.x, 0]; // axisW × ẑ
      const rl = Math.hypot(rollDir[0], rollDir[1]) || 1;
      rollDir[0] /= rl; rollDir[1] /= rl;
      const bt = this.bodyRB.translation();
      const wt = h.rb2.translation();
      const wz = turn * 3; // yaw rate rad/s
      const vDes = [driveV - wz * (wt.y - bt.y), wz * (wt.x - bt.x)];
      const wTarget = (vDes[0] * rollDir[0] + vDes[1] * rollDir[1]) / Math.max(P.rw, 1e-3);
      let tau = h.kD * (wTarget - s.vel); // velocity gain = this wheel's own stability-bounded kD
      tau = Math.max(-tauMax, Math.min(tauMax, tau));
      h.applied = tau;
      const tv = { x: s.axisW.x * tau * dt, y: s.axisW.y * tau * dt, z: s.axisW.z * tau * dt };
      h.rb2.applyTorqueImpulse(tv, true);
      h.rb1.applyTorqueImpulse({ x: -tv.x, y: -tv.y, z: -tv.z }, true);
    });
  }

  step(elapsedS = 1 / 60, driveV = 0, turn = 0) {
    if (!this.active) return;
    const dt = this.world.timestep;
    this._stepAccumulator += Math.max(0, Math.min(elapsedS, 0.05));
    const substeps = Math.min(48, Math.floor(this._stepAccumulator / dt));
    this._stepAccumulator -= substeps * dt;
    for (let i = 0; i < substeps; i++) {
      this.applyServoTorques(dt, driveV, turn);
      this.world.step(this.eventQueue);
    }
    // wheel contact forces -> GRF estimate (exp moving average)
    const forces = [0, 0, 0, 0];
    this.eventQueue.drainContactForceEvents((e) => {
      const h1 = e.collider1(), h2 = e.collider2();
      const li = this.wheelColliders.indexOf(h1) !== -1 ? this.wheelColliders.indexOf(h1) : this.wheelColliders.indexOf(h2);
      if (li >= 0) forces[li] = Math.max(forces[li], e.totalForceMagnitude());
    });
    for (let i = 0; i < 4; i++) this.grfAvg[i] = this.grfAvg[i] * 0.92 + forces[i] * 0.08;

    const r = this.bodyRB.rotation();
    const up = new THREE.Vector3(0, 0, 1).applyQuaternion(new THREE.Quaternion(r.x, r.y, r.z, r.w));
    const tilt = Math.acos(Math.max(-1, Math.min(1, up.z))) * 180 / Math.PI;
    const t = this.bodyRB.translation();
    this.status = { tiltDeg: tilt, fallen: tilt > 55, bodyZ: t.z };
  }

  push(impulseN_s, dir = [1, 0, 0]) {
    if (!this.active) return;
    const t = this.bodyRB.translation();
    const p = { x: t.x + this.topLocal[0], y: t.y + this.topLocal[1], z: t.z + this.topLocal[2] };
    this.bodyRB.applyImpulseAtPoint(
      { x: dir[0] * impulseN_s, y: dir[1] * impulseN_s, z: dir[2] * impulseN_s }, p, true);
  }
}
