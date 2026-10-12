// config.js — simulator parameter schema and generic start state.
// derive() converts EVERYTHING to SI once; all math modules consume only P.
// CAD authority remains docs/mist/MIST_FUSION_MASTER_DIMENSIONS.md; use the
// explicit Layout A quick preset before producing CAD or hardware exports.

export const FILAMENTS = {
  PLA:  { rho: 1.24, E: 3.5,  label: 'PLA (proto only)' },   // rho g/cm3, E GPa
  PETG: { rho: 1.27, E: 2.1,  label: 'PETG (structural)' },
  TPU:  { rho: 1.22, E: 0.08, label: 'TPU 95A (flex!)' },
};

export function defaultConfig() {
  return {
    body: {
      cylD: 180,          // cylinder diameter mm
      cylH: 260,          // cylinder height mm
      shellMass: 900,     // printed barrel + deck + lid g
      legMountH: 35,      // leg mount height above cylinder bottom mm
      mountStandoff: 10,  // bracket standoff from shell to hip-roll axis mm
    },
    masses: {
      batteryM: 174, batteryH: 40, batteryR: 0, batteryAz: 180, // HOOVO 3S 2200
      phoneM: 205, phoneH: 170,                                  // phone+frame+straps, front (az 0)
      elecM: 350, elecH: 15,                                     // PDB/adapter/ESP32/UBEC/fuses
      harnessM: 150, harnessH: 60,                               // wire/caps/straps allowance
      headServoN: 0,                                             // optional servos in head (top)
      payloadM: 0, payloadH: 260,                                // extra top payload
    },
    geo: {
      frontAz: 50,   // front pair azimuth deg from +X (legs at +/-frontAz)
      rearAz: 130,   // rear pair azimuth deg (legs at +/-rearAz)
    },
    leg: {
      d1: 35,          // hip-roll axis -> hip-pitch axis offset mm
      femur: 120, tibia: 140,             // link lengths mm
      beamW: 20, beamT: 14,               // printed beam cross-section mm
      structFactor: 0.7,                  // infill/solidity factor for mass & stiffness
      bracketPerSeg: 18,                  // screws/brackets allowance per link g
      filament: 'PETG',
      linkage: false,                     // knee servo relocated to hip via linkage
      linkRatio: 1.0,                     // linkage transmission ratio (>1 = torque advantage)
      linkRodMass: 15,                    // pushrod g (added at femur mid when linkage on)
      kneeSign: -1,                       // -1 = spider look: knee bows up/out, tibia dives to wheel (matches MIST refs); +1 = femur tucked, knee low/in
    },
    wheel: {
      dia: 70, mass: 60,        // TPU tire + PETG hub g (servo counted separately)
      driveMount: 'foot',       // wheel servo location: 'foot' (hub motor) | 'knee' | 'hip' (remote via belt/shaft)
      transMass: 12,            // transmission mass per remote stage g (belt+pulleys or shaft+bevels)
    },
    servo: {
      mass: 55, stallNm: 2.94, stallA: 2.7, idleA: 0.06, noLoadRPM: 45, // STS3215 C018 @12V
    },
    power: {
      cells: 3, capAh: 2.2, soc: 0.8, rInt: 50,  // pack internal + harness resistance mΩ
      fuseLeg: 15, fuseMain: 30, cutoffV: 9.9,
    },
    pose: {
      mode: 'stand',      // 'stand' | 'suspended'
      bodyH: 120,         // cylinder-bottom ground clearance mm
      bodyX: 0, bodyY: 0, // body offset (lean) mm
      stanceR: 190,       // foot contact distance from cylinder axis mm
      azOff: 0,           // rotate feet around their mount azimuth deg
      lifts: [0, 0, 0, 0],   // per-leg foot lift mm (FL, FR, RL, RR)
      stepX: [0, 0, 0, 0],   // per-leg foot forward offset mm
    },
    env: { slopeDeg: 0, slopeHeading: 0, mu: 0.8 },
    rom: { rollLim: 60, hipMin: -35, hipMax: 110, kneeMin: -135, kneeMax: 135 }, // deg
    thresholds: {
      contRatio: 0.30, peakRatio: 0.55,   // torque / stall(Vworst)
      legAmpWarn: 8, legAmpMax: 10.8,     // vs 15A blade fuse
      totAmpWarn: 20, totAmpMax: 28,      // vs 30A main
      vWarn: 10.5, vMin: 9.9,
      tipWarnDeg: 15, tipMinDeg: 8,
      deflWarnMm: 0.6, deflMaxMm: 1.5,
    },
  };
}

export const LEG_NAMES = ['FL', 'FR', 'RL', 'RR'];

export function legAzimuthsDeg(cfg) {
  const f = cfg.geo.frontAz, r = cfg.geo.rearAz;
  return [f, -f, r, -r]; // FL, FR, RL, RR
}

const D2R = Math.PI / 180;

// One-shot conversion to SI. Everything downstream uses P only.
export function derive(cfg) {
  const fil = FILAMENTS[cfg.leg.filament] || FILAMENTS.PETG;
  const mm = (x) => x / 1000;
  const g = (x) => x / 1000;
  const Aeff_mm2 = cfg.leg.beamW * cfg.leg.beamT * cfg.leg.structFactor;
  const beamMassG = (Lmm) => fil.rho * (Aeff_mm2 * Lmm) / 1000 + cfg.leg.bracketPerSeg; // cm3*rho
  const Ieff_mm4 = (cfg.leg.beamW * Math.pow(cfg.leg.beamT, 3) / 12) * cfg.leg.structFactor;

  const linkRatio = cfg.leg.linkage ? Math.max(cfg.leg.linkRatio, 1e-6) : 1;
  return {
    // geometry
    R: mm(cfg.body.cylD) / 2,
    H: mm(cfg.body.cylH),
    legMountH: mm(cfg.body.legMountH),
    mountR: mm(cfg.body.cylD) / 2 + mm(cfg.body.mountStandoff),
    d1: mm(cfg.leg.d1),
    L1: mm(cfg.leg.femur),
    L2: mm(cfg.leg.tibia),
    rw: mm(cfg.wheel.dia) / 2,
    phis: legAzimuthsDeg(cfg).map((a) => a * D2R),
    kneeSign: cfg.leg.kneeSign,
    // masses (kg)
    mShell: g(cfg.body.shellMass),
    mBattery: g(cfg.masses.batteryM),
    mPhone: g(cfg.masses.phoneM),
    mElec: g(cfg.masses.elecM),
    mHarness: g(cfg.masses.harnessM),
    mHead: cfg.masses.headServoN * g(cfg.servo.mass),
    mPayload: g(cfg.masses.payloadM),
    mServo: g(cfg.servo.mass),
    mFemur: g(beamMassG(cfg.leg.femur)),
    mTibia: g(beamMassG(cfg.leg.tibia)),
    mWheel: g(cfg.wheel.mass),
    wheelMount: cfg.wheel.driveMount || 'foot',
    mTrans: g(cfg.wheel.transMass),
    mLinkRod: g(cfg.leg.linkRodMass),
    linkage: cfg.leg.linkage,
    linkRatio,
    // mass positions on body (SI, relative to cylinder bottom center)
    posBattery: [Math.cos(cfg.masses.batteryAz * D2R) * mm(cfg.masses.batteryR),
                 Math.sin(cfg.masses.batteryAz * D2R) * mm(cfg.masses.batteryR),
                 mm(cfg.masses.batteryH)],
    posPhone: [mm(cfg.body.cylD) / 2 + 0.012, 0, mm(cfg.masses.phoneH)],
    posElec: [0, 0, mm(cfg.masses.elecH)],
    posHarness: [0, 0, mm(cfg.masses.harnessH)],
    posHead: [0, 0, mm(cfg.body.cylH) + 0.01],
    posPayload: [0, 0, mm(cfg.masses.payloadH)],
    // beam stiffness
    E_Pa: fil.E * 1e9,
    I_m4: Ieff_mm4 * 1e-12,
    // servo
    stallNm12: cfg.servo.stallNm, stallA12: cfg.servo.stallA,
    idleA: cfg.servo.idleA,
    wNoLoad12: cfg.servo.noLoadRPM * 2 * Math.PI / 60, // rad/s
    // power
    capAh: cfg.power.capAh, soc: cfg.power.soc,
    rInt: cfg.power.rInt / 1000, cells: cfg.power.cells,
    cutoffV: cfg.power.cutoffV,
    fuseLeg: cfg.power.fuseLeg,
    fuseMain: cfg.power.fuseMain,
    // env: gravity unit vector tilted by slope (frame where ground stays z=0)
    gDir: (() => {
      const th = cfg.env.slopeDeg * D2R, hd = cfg.env.slopeHeading * D2R;
      // downhill direction = heading; gravity acquires a horizontal component
      return [Math.sin(th) * Math.cos(hd), Math.sin(th) * Math.sin(hd), -Math.cos(th)];
    })(),
    mu: cfg.env.mu,
    g: 9.81,
    // ROM rad
    rom: {
      roll: [-cfg.rom.rollLim * D2R, cfg.rom.rollLim * D2R],
      hip: [cfg.rom.hipMin * D2R, cfg.rom.hipMax * D2R],
      // A linkage with ratio R moves the servo R times the joint angle, so the
      // joint-space range is the configured servo range divided by R.
      knee: [cfg.rom.kneeMin * D2R / linkRatio, cfg.rom.kneeMax * D2R / linkRatio],
    },
  };
}

// LiPo open-circuit voltage from state of charge (per cell), coarse curve.
export function socToV(soc) {
  const pts = [[0, 3.27], [0.1, 3.55], [0.2, 3.65], [0.4, 3.72], [0.6, 3.82], [0.8, 3.95], [1.0, 4.2]];
  const s = Math.max(0, Math.min(1, soc));
  for (let i = 1; i < pts.length; i++) {
    if (s <= pts[i][0]) {
      const t = (s - pts[i - 1][0]) / (pts[i][0] - pts[i - 1][0]);
      return pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1]);
    }
  }
  return 4.2;
}

// Foot target positions (world, SI) for the current pose.
export function footTargets(cfg) {
  const P = derive(cfg);
  const azOff = cfg.pose.azOff * D2R;
  const mm = (x) => x / 1000;
  const lift0 = cfg.pose.mode === 'suspended' ? 0.15 : 0;
  return P.phis.map((phi, i) => [
    Math.cos(phi + azOff) * mm(cfg.pose.stanceR) + mm(cfg.pose.stepX[i]),
    Math.sin(phi + azOff) * mm(cfg.pose.stanceR),
    mm(cfg.pose.lifts[i]) + lift0,
  ]);
}

// Body position (leg-mount plane center, world SI) for the current pose.
export function bodyPosOf(cfg) {
  const lift0 = cfg.pose.mode === 'suspended' ? 0.15 : 0;
  return [cfg.pose.bodyX / 1000, cfg.pose.bodyY / 1000,
          (cfg.pose.bodyH + cfg.body.legMountH) / 1000 + lift0];
}

// deep get/set by dotted path — used by UI sliders and window.sim
export function getPath(obj, path) {
  return path.split('.').reduce((o, k) => (o == null ? o : o[k]), obj);
}
export function setPath(obj, path, val) {
  const ks = path.split('.');
  let o = obj;
  for (let i = 0; i < ks.length - 1; i++) o = o[ks[i]];
  o[ks[ks.length - 1]] = val;
}
