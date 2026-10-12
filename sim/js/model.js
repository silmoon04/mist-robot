// model.js — builds the list of point masses (SI) for the current config + pose.
// Every mass is {name, m (kg), p (world m), group}. CoM falls out of this list.

import { V } from './kin.js';

// legsFK: array of 4 FK results. bodyPos: mount-plane center world.
export function massItems(P, legsFK, bodyPos) {
  const bottom = V.sub(bodyPos, [0, 0, P.legMountH]); // cylinder bottom center
  const items = [];
  const add = (name, m, p, group) => { if (m > 1e-9) items.push({ name, m, p, group }); };

  // body-mounted masses
  add('shell', P.mShell, V.add(bottom, [0, 0, P.H / 2]), 'body');
  add('battery', P.mBattery, V.add(bottom, P.posBattery), 'body');
  add('phone', P.mPhone, V.add(bottom, P.posPhone), 'body');
  add('electronics', P.mElec, V.add(bottom, P.posElec), 'body');
  add('harness', P.mHarness, V.add(bottom, P.posHarness), 'body');
  add('headServos', P.mHead, V.add(bottom, P.posHead), 'body');
  add('payload', P.mPayload, V.add(bottom, P.posPayload), 'body');

  // legs
  legsFK.forEach((fk, i) => {
    const grp = 'leg' + i;
    add(`hipRollServo`, P.mServo, fk.mount, grp);
    add(`hipPitchServo`, P.mServo, fk.p1, grp);
    if (P.linkage) {
      add(`kneeServo@hip`, P.mServo, fk.p1, grp);
      add(`linkRod`, P.mLinkRod, V.scale(V.add(fk.p1, fk.knee), 0.5), grp);
    } else {
      add(`kneeServo`, P.mServo, fk.knee, grp);
    }
    const femurMid = V.scale(V.add(fk.p1, fk.knee), 0.5);
    const tibiaMid = V.scale(V.add(fk.knee, fk.axle), 0.5);
    add(`femur`, P.mFemur, femurMid, grp);
    add(`tibia`, P.mTibia, tibiaMid, grp);
    // wheel drive servo: hub motor at the axle, or remote at knee/hip with a
    // belt/shaft stage per link it spans
    const wm = P.wheelMount;
    add(`wheelServo`, P.mServo, wm === 'hip' ? fk.p1 : wm === 'knee' ? fk.knee : fk.axle, grp);
    if (wm !== 'foot') add(`wheelTransTibia`, P.mTrans, tibiaMid, grp);
    if (wm === 'hip') add(`wheelTransFemur`, P.mTrans, femurMid, grp);
    add(`wheel`, P.mWheel, fk.axle, grp);
  });
  return items;
}

export function centerOfMass(items) {
  let M = 0, p = [0, 0, 0];
  for (const it of items) {
    M += it.m;
    p = V.add(p, V.scale(it.p, it.m));
  }
  return { M, com: M > 0 ? V.scale(p, 1 / M) : [0, 0, 0] };
}

// Masses distal to a given joint of a given leg (act on that joint's torque).
// jointIdx: 0=hip roll (everything past mount), 1=hip pitch, 2=knee.
export function distalMasses(P, items, legIdx, jointIdx) {
  const grp = 'leg' + legIdx;
  const legItems = items.filter((it) => it.group === grp);
  // a hip-mounted wheel servo is NOT carried by the knee (or by anything distal
  // of the hip-pitch point it sits on) — only its transmission stages are
  const wheelServoPast = { foot: 2, knee: 2, hip: 1 }[P.wheelMount]; // deepest joint that carries it
  const namesPast = {
    0: null, // all leg items except the hip-roll servo body itself (sits on the roll axis mount)
    1: ['kneeServo', 'kneeServo@hip', 'linkRod', 'femur', 'tibia', 'wheel', 'wheelTransTibia', 'wheelTransFemur'],
    2: ['tibia', 'wheel', 'wheelTransTibia'],
  }[jointIdx];
  if (namesPast === null) return legItems.filter((it) => it.name !== 'hipRollServo');
  return legItems.filter((it) => namesPast.includes(it.name)
    || (it.name === 'wheelServo' && jointIdx <= wheelServoPast));
}
