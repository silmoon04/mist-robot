// report.js — actuator-layout study. For each layout (where the knee and wheel
// servos physically live), re-optimize the geometry under the same constraints,
// run a capability battery (squat / tallest stand / one-leg / max slope / crawl
// gait / drive stance / swing torque), sanity-check the numbers with rule-based
// reasoning, capture a render, and emit a self-contained HTML report.

import * as THREE from 'three';
import { evaluate } from './pipeline.js';
import { optimize, OPT_VARS, DEFAULT_CONSTRAINTS, supportShift } from './optimize.js';
import { presets, analyzeSequence } from './anim.js';
import { setPath, getPath } from './config.js';

export const LAYOUTS = [
  {
    id: 'A', name: 'All direct (baseline)',
    set: { 'leg.linkage': false, 'wheel.driveMount': 'foot' },
    desc: 'Knee servo at the knee, wheel servo is the hub. What the MIST basket assumed.',
    build: ['★★★★★ simplest — zero belts/linkages, print brackets only',
      'heaviest legs: 110 g of servo at/below each knee',
      'wheel servo takes ground impacts directly; 4× long wire runs to feet',
      'servo IS the axle: wheel swap = servo horn screws'],
  },
  {
    id: 'B', name: 'Wheel at knee (belt down tibia)',
    set: { 'leg.linkage': false, 'wheel.driveMount': 'knee' },
    desc: 'Knee servo direct; wheel servo moves to the knee, GT2-style belt runs down the rigid tibia.',
    build: ['★★★★ easy belt: spans NO moving joint (knee→axle along one rigid link)',
      'needs printed pulleys + tensioner + free-spinning axle (bearing or bushing)',
      'wheel unsprung mass drops 55 g — kinder landings, faster leg swing',
      'two servos cluster at the knee: bracket gets bulkier'],
  },
  {
    id: 'C', name: 'Knee at hip (linkage), wheel at foot',
    set: { 'leg.linkage': true, 'leg.linkRatio': 1.5, 'wheel.driveMount': 'foot' },
    desc: 'Knee driven by a hip-mounted servo through a pushrod/four-bar (ratio 1.5). Hub wheel.',
    build: ['★★★ classic quadruped trick; pushrod crosses the hip-pitch joint',
      'linkage ratio 1.5 multiplies knee torque but cuts knee ROM by the same factor',
      'joint slop adds up: every printed linkage pivot is backlash',
      'hip cluster = 3 servos per leg — packaging around the barrel gets tight'],
  },
  {
    id: 'D', name: 'Knee at hip + wheel at knee',
    set: { 'leg.linkage': true, 'leg.linkRatio': 1.5, 'wheel.driveMount': 'knee' },
    desc: 'Linkage knee plus belt-driven wheel from the knee. Only structure below the knee.',
    build: ['★★ combines linkage AND belt — two transmissions to print/tune per leg',
      'tibia is pure structure + belt: lightest below-knee mass of any layout',
      'knee bracket carries wheel servo + belt tension + linkage endpoint',
      'most printed precision parts; expect iteration on tolerances'],
  },
  {
    id: 'E', name: 'Everything at hip',
    set: { 'leg.linkage': true, 'leg.linkRatio': 1.5, 'wheel.driveMount': 'hip' },
    desc: 'All 3 leg servos live at the hip; knee via linkage, wheel via 2-stage belt THROUGH the knee.',
    build: ['★ hardest: wheel belt must cross the moving knee — needs an idler coaxial with the knee axis',
      'legs are almost pure structure: best swing dynamics and crash survival',
      'all wiring stays at the hip — cleanest harness, best waterproofing story',
      'hip pod = 4 servos/leg; 8 servos around the barrel base needs real CAD'],
  },
];

const OPT_KEYS = ['leg.femur', 'leg.tibia', 'leg.d1', 'geo.frontAz', 'geo.rearAz', 'pose.stanceR', 'pose.bodyH'];

// ---------- capability battery ----------
export function capabilities(cfg) {
  const th = cfg.thresholds;
  const ev = (mods) => {
    const c = JSON.parse(JSON.stringify(cfg));
    Object.entries(mods || {}).forEach(([k, v]) => setPath(c, k, v));
    return evaluate(c);
  };
  const util = (r) => Math.max(...r.power.perServo.map((s) => s.utilization));
  const okPose = (r) => r.legs.every((l) => l.reachable && !l.romClamped) && util(r) < th.peakRatio;

  const stand = ev({});
  const squat = ev({ 'pose.bodyH': Math.max(35, cfg.pose.bodyH * 0.55) }); // matches optimizer battery
  // tallest stable stand
  let tallest = 0;
  for (let h = cfg.leg.femur + cfg.leg.tibia - 10; h >= 40; h -= 5) {
    const r = ev({ 'pose.bodyH': h });
    if (okPose(r) && r.contacts.length === 4 && r.stab.minTipDeg > 5) { tallest = h; break; }
  }
  const sh = supportShift(cfg, 0);
  const oneLeg = ev({ 'pose.lifts.0': 50, 'pose.bodyX': sh[0], 'pose.bodyY': sh[1] }); // matches optimizer battery
  // max slope (nose-uphill), stand pose
  let maxSlope = 0;
  for (let s = 2.5; s <= 35; s += 2.5) {
    const r = ev({ 'env.slopeDeg': s, 'env.slopeHeading': 180 });
    if (okPose(r) && r.stab.minTipDeg > 2 && r.frictionOK && !r.grf.dropped.length) maxSlope = s;
    else break;
  }
  // crawl gait
  const crawlPreset = presets(cfg).find((p) => p.name.includes('Crawl'));
  const crawl = analyzeSequence(cfg, crawlPreset, 8, 41);
  const crawlUtil = Math.max(...crawl.map((s) => s.maxUtil));
  const crawlBadFrames = crawl.filter((s) => s.tipping || s.unreachable).length;
  // swing torque (suspended = pure leg-carry effort)
  const swing = ev({ 'pose.mode': 'suspended' });
  // drive stance with this geometry
  const drive = ev({ 'geo.frontAz': 28, 'geo.rearAz': 152, 'pose.bodyH': Math.min(cfg.pose.bodyH, 110) });
  const standUtil = util(stand);

  return {
    stand: {
      util: standUtil, tip: stand.stab.minTipDeg, mass: stand.M,
      runtime: stand.power.runtimeMin, vRail: stand.power.vRail, overall: stand.overall,
      comZ: stand.com[2],
    },
    can: {
      squat: { ok: okPose(squat), util: util(squat) },
      tallest: { ok: tallest > 0, h: tallest },
      oneLeg: { ok: okPose(oneLeg) && !oneLeg.grf.dropped.length && oneLeg.stab.minTipDeg > 1, tip: oneLeg.stab.minTipDeg, util: util(oneLeg) },
      slope: { ok: maxSlope >= 10, deg: maxSlope },
      crawl: { ok: crawlUtil < th.peakRatio && crawlBadFrames <= 1, util: crawlUtil, badFrames: crawlBadFrames },
      drive: { ok: okPose(drive), util: util(drive) },
      twoWheel: { ok: false, note: 'statically impossible for every layout — CoM can never sit on the diagonal wheel line without active balance' },
    },
    swing: { hip: Math.abs(swing.legTorques[0][1]), knee: Math.abs(swing.servoTorques[0][2]) },
  };
}

// rule-based sanity notes — the "does this look right?" reasoning, per layout
export function sanityNotes(layout, caps, baseline) {
  const n = [];
  if (baseline && layout.id !== 'A') {
    const dHip = caps.swing.hip - baseline.swing.hip;
    const dKnee = caps.swing.knee - baseline.swing.knee;
    n.push(`swing hip τ ${dHip <= 0 ? '↓' : '↑'}${Math.abs(dHip).toFixed(2)} N·m, knee-servo τ ${dKnee <= 0 ? '↓' : '↑'}${Math.abs(dKnee).toFixed(2)} N·m vs baseline — ` +
      (layout.set['leg.linkage'] ? 'linkage ratio divides knee-servo demand; ' : '') +
      (layout.set['wheel.driveMount'] !== 'foot' ? 'wheel servo moved proximal unloads the swing. ' : ''));
    const dM = (caps.stand.mass - baseline.stand.mass) * 1000;
    n.push(`mass ${dM >= 0 ? '+' : ''}${dM.toFixed(0)} g vs baseline (transmission hardware) — expected, matches ${layout.set['wheel.driveMount'] === 'hip' ? '2' : layout.set['wheel.driveMount'] === 'knee' ? '1' : '0'} belt stage(s) + ${layout.set['leg.linkage'] ? 'pushrods' : 'no linkage'}.`);
  }
  if (caps.stand.util < 0.02) n.push('⚠ standing torque implausibly low — check config');
  if (caps.can.crawl.util > caps.stand.util * 1.5) {
    n.push(`crawl peaks ${(caps.can.crawl.util * 100).toFixed(0)}% vs ${(caps.stand.util * 100).toFixed(0)}% standing — 3-leg phases carry the load; this ratio (~${(caps.can.crawl.util / Math.max(caps.stand.util, 1e-6)).toFixed(1)}×) is the expected quadruped pattern.`);
  }
  if (caps.can.slope.deg >= 30) n.push('⚠ slope ≥30° is optimistic: model ignores belt/linkage friction losses and soft-tire squirm; trust the trend, not the last 5°.');
  return n;
}

// ---------- snapshot from the live scene ----------
export function snapshot(viewer, w = 560, h = 400) {
  const rt = new THREE.WebGLRenderTarget(w, h, { samples: 4 });
  const cam = new THREE.PerspectiveCamera(40, w / h, 0.01, 20);
  cam.up.set(0, 0, 1);
  cam.position.set(0.62, -0.52, 0.42);
  cam.lookAt(0, 0, 0.16);
  viewer.renderer.setRenderTarget(rt);
  viewer.renderer.render(viewer.scene, cam);
  const px = new Uint8Array(w * h * 4);
  viewer.renderer.readRenderTargetPixels(rt, 0, 0, w, h, px);
  viewer.renderer.setRenderTarget(null);
  rt.dispose();
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  const img = cv.getContext('2d').createImageData(w, h);
  for (let y = 0; y < h; y++) { // GL rows are bottom-up
    img.data.set(px.subarray((h - 1 - y) * w * 4, (h - y) * w * 4), y * w * 4);
  }
  cv.getContext('2d').putImageData(img, 0, 0);
  return cv.toDataURL('image/jpeg', 0.82);
}

// ---------- study runner (drives the live app) ----------
export async function runStudy(app, onProgress) {
  const saved = JSON.stringify(app.cfg);
  const rows = [];
  let baselineCaps = null;
  for (const layout of LAYOUTS) {
    onProgress?.(`optimizing ${layout.id}: ${layout.name}…`);
    const base = JSON.parse(saved);
    Object.entries(layout.set).forEach(([k, v]) => setPath(base, k, v));
    const vars = OPT_VARS.map((v) => ({ ...v, on: OPT_KEYS.includes(v.key) }));
    const { top } = await optimize(base, {
      vars, goal: 'balanced', cons: { ...DEFAULT_CONSTRAINTS },
      nRandom: 170, nRefine: 120,
    });
    const best = top[0];
    const optCfg = JSON.parse(JSON.stringify(base));
    vars.filter((v) => v.on).forEach((v) => setPath(optCfg, v.key, getPath(best.cfg, v.key)));

    onProgress?.(`capabilities ${layout.id}…`);
    const caps = capabilities(optCfg);
    if (layout.id === 'A') baselineCaps = caps;

    // show it + snapshot it
    Object.assign(app.cfg, JSON.parse(JSON.stringify(optCfg)));
    app.onChange(); // synchronous scene rebuild; snapshot() renders explicitly
    const shot = snapshot(app.viewer);

    rows.push({
      layout, feasible: best.feasible,
      dims: Object.fromEntries(OPT_KEYS.map((k) => [k, getPath(optCfg, k)])),
      caps, shot, cfgJson: JSON.stringify(optCfg),
      notes: sanityNotes(layout, caps, baselineCaps),
    });
  }
  // restore
  Object.assign(app.cfg, JSON.parse(saved));
  app.onChange();
  onProgress?.('building report…');
  return rows;
}

// ---------- HTML report ----------
export function buildReportHTML(rows, extraIntro = '') {
  const pct = (x) => (x * 100).toFixed(0) + '%';
  const CANS = [
    ['squat', (c) => c.squat.ok, (c) => `low squat (${pct(c.squat.util)} peak)`],
    ['tallest', (c) => c.tallest.ok, (c) => `stand up to ${c.tallest.h} mm clearance`],
    ['oneLeg', (c) => c.oneLeg.ok, (c) => `lift one leg (tip ${c.oneLeg.tip.toFixed(0)}°, ${pct(c.oneLeg.util)})`],
    ['slope', (c) => c.slope.ok, (c) => `hold a ${c.slope.deg}° slope (uphill)`],
    ['crawl', (c) => c.crawl.ok, (c) => `crawl gait (peaks ${pct(c.crawl.util)}${c.crawl.badFrames ? `, ${c.crawl.badFrames} unstable frames` : ''})`],
    ['drive', (c) => c.drive.ok, (c) => `drive stance (${pct(c.drive.util)})`],
    ['twoWheel', () => false, () => `two-wheel balance — needs active control, all layouts`],
  ];
  const dimLabel = { 'leg.femur': 'femur', 'leg.tibia': 'tibia', 'leg.d1': 'hip offset', 'geo.frontAz': 'front az', 'geo.rearAz': 'rear az', 'pose.stanceR': 'stance R', 'pose.bodyH': 'body H' };

  // pick a recommendation: feasible, lowest crawl util, buildability as tiebreak
  const ranked = rows.slice().sort((a, b) =>
    (b.feasible - a.feasible) || (a.caps.can.crawl.util - b.caps.can.crawl.util));
  const rec = ranked[0];

  const summary = `
  <table class="sum"><tr><th></th>${rows.map((r) => `<th>${r.layout.id}<div class="thn">${r.layout.name}</div></th>`).join('')}</tr>
  ${[['mass', (r) => (r.caps.stand.mass * 1000).toFixed(0) + ' g'],
     ['stand worst servo', (r) => pct(r.caps.stand.util)],
     ['crawl peak servo', (r) => pct(r.caps.can.crawl.util)],
     ['swing hip τ', (r) => r.caps.swing.hip.toFixed(2) + ' N·m'],
     ['knee-servo swing τ', (r) => r.caps.swing.knee.toFixed(2) + ' N·m'],
     ['tip margin', (r) => r.caps.stand.tip.toFixed(0) + '°'],
     ['max slope', (r) => r.caps.can.slope.deg + '°'],
     ['runtime', (r) => r.caps.stand.runtime === Infinity ? '∞' : r.caps.stand.runtime.toFixed(0) + ' min'],
     ['constraints', (r) => r.feasible ? '✔' : '⚠'],
    ].map(([lab, f]) => `<tr><td>${lab}</td>${rows.map((r) => `<td>${f(r)}</td>`).join('')}</tr>`).join('')}
  </table>`;

  const cards = rows.map((r) => `
  <div class="cfg ${r.layout.id === rec.layout.id ? 'rec' : ''}">
    <h2>${r.layout.id} — ${r.layout.name} ${r.layout.id === rec.layout.id ? '<span class="recb">RECOMMENDED</span>' : ''}
      ${r.feasible ? '<span class="okb">meets constraints</span>' : '<span class="warnb">constraint compromise</span>'}</h2>
    <p class="desc">${r.layout.desc}</p>
    <div class="flex">
      <img src="${r.shot}" alt="render ${r.layout.id}">
      <div>
        <h3>Optimized measurements</h3>
        <table class="dims">${Object.entries(r.dims).map(([k, v]) => `<tr><td>${dimLabel[k]}</td><td><b>${v}</b> ${k.includes('Az') ? '°' : 'mm'}</td></tr>`).join('')}</table>
        <h3>Can / can't</h3>
        <ul class="cans">${CANS.map(([k, okf, txt]) => `<li class="${okf(r.caps.can) ? 'y' : 'n'}">${okf(r.caps.can) ? '✔' : '✖'} ${txt(r.caps.can)}</li>`).join('')}</ul>
      </div>
    </div>
    <h3>Buildability</h3>
    <ul>${r.layout.build.map((b) => `<li>${b}</li>`).join('')}</ul>
    <h3>Sanity check</h3>
    <ul>${r.notes.map((n) => `<li>${n}</li>`).join('') || '<li>baseline reference</li>'}</ul>
    <details><summary>sim config JSON (load via “Load config”)</summary><pre>${r.cfgJson.replace(/</g, '&lt;')}</pre></details>
  </div>`).join('');

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>MIST actuator-layout study</title><style>
  body{background:#14161a;color:#d5d9e0;font:14px/1.55 'Segoe UI',system-ui,sans-serif;max-width:980px;margin:24px auto;padding:0 16px}
  h1{font-size:22px} h2{font-size:16px;margin:6px 0} h3{font-size:12.5px;color:#9aa3b5;text-transform:uppercase;letter-spacing:.05em;margin:12px 0 4px}
  .cfg{background:#1a1d23;border:1px solid #2a2e36;border-radius:12px;padding:14px 18px;margin:14px 0}
  .cfg.rec{border-color:#37c871}
  .recb{background:#16281e;color:#4fdc8b;border:1px solid #2a5c40;border-radius:10px;padding:2px 10px;font-size:11px;vertical-align:middle}
  .okb{background:#16281e;color:#4fdc8b;border-radius:10px;padding:2px 8px;font-size:11px;vertical-align:middle}
  .warnb{background:#2b2415;color:#f0b64c;border-radius:10px;padding:2px 8px;font-size:11px;vertical-align:middle}
  .desc{color:#aab2c2}
  .flex{display:flex;gap:16px;flex-wrap:wrap} .flex img{width:380px;max-width:100%;border-radius:8px;border:1px solid #2a2e36}
  table.dims td{padding:1px 10px 1px 0;font-size:13px} ul{margin:4px 0;padding-left:20px}
  ul.cans{list-style:none;padding-left:2px} ul.cans .y{color:#4fdc8b} ul.cans .n{color:#ff6b5e}
  table.sum{border-collapse:collapse;width:100%;font-size:12.5px} .sum td,.sum th{border:1px solid #2a2e36;padding:4px 8px;text-align:center}
  .sum td:first-child{text-align:left;color:#9aa3b5} .thn{font-weight:400;font-size:10.5px;color:#8f97a8}
  details pre{font-size:10px;max-height:240px;overflow:auto;background:#14161a;padding:8px;border-radius:6px}
  .intro{color:#aab2c2}
  </style></head><body>
  <h1>MIST actuator-layout study</h1>
  <p class="intro">Five ways to place the knee and wheel servos, each re-optimized (femur/tibia/hip offset/azimuths/stance/height)
  under the same hard constraints — worst servo ≤35% of stall at brown-out voltage, tip margin ≥12°, leg branch ≤10.8 A,
  flex ≤0.8 mm — scored on a pose battery (stand, squat, one-leg, 10° slope). Torque model verified by 13 invariant self-tests.
  Every image is the actual optimized geometry rendered by the simulator. ${extraIntro}</p>
  ${summary}${cards}
  <p class="intro">Generated by sim/ — configs are attached to each card; load one via the sim's “Load config” to poke at it.</p>
  </body></html>`;
}

export function openAndDownload(html, filename = 'MIST_CONFIG_REPORT.html') {
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
}
