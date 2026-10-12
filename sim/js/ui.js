// ui.js — declarative control panel. Sliders write into config via dotted paths,
// then call app.onChange(). Readouts are re-rendered from the pipeline result.

import { getPath, setPath, LEG_NAMES, FILAMENTS } from './config.js';
import { JOINT_NAMES } from './exports.js';
import { renderDashboard } from './dashboard.js';
import { OPT_VARS, GOALS, DEFAULT_CONSTRAINTS } from './optimize.js';

// quick pose/geometry presets — includes the drive-stance finding
const POSE_PRESETS = [
  { name: 'CAD Layout A', rebuild: true, set: { 'leg.femur': 110, 'leg.tibia': 70, 'leg.d1': 32, 'geo.frontAz': 25, 'geo.rearAz': 109, 'wheel.dia': 70, 'pose.bodyH': 148, 'pose.stanceR': 176, 'leg.linkage': false, 'leg.linkRatio': 1, 'wheel.driveMount': 'foot' }, hint: 'Current Fusion master dimensions; use before CAD or hardware exports' },
  { name: 'Stand', set: { 'pose.bodyH': 120, 'pose.stanceR': 190, 'pose.lifts.0': 0, 'pose.lifts.1': 0, 'pose.lifts.2': 0, 'pose.lifts.3': 0, 'pose.bodyX': 0, 'pose.bodyY': 0 } },
  { name: 'Squat', set: { 'pose.bodyH': 60, 'pose.stanceR': 210 } },
  { name: 'Tall', set: { 'pose.bodyH': 185, 'pose.stanceR': 160 } },
  { name: 'Drive stance', set: { 'geo.frontAz': 28, 'geo.rearAz': 152, 'pose.bodyH': 100, 'pose.stanceR': 200 }, hint: 'legs fore/aft so wheels roll forward' },
  { name: 'Wide sprawl', set: { 'geo.frontAz': 50, 'geo.rearAz': 130, 'pose.bodyH': 90, 'pose.stanceR': 250 } },
];

const SLIDERS = [
  { group: 'Pose', key: 'pose.bodyH', label: 'Body height (ground→cyl bottom)', min: 25, max: 260, step: 1, unit: 'mm' },
  { group: 'Pose', key: 'pose.stanceR', label: 'Stance radius (feet from axis)', min: 80, max: 400, step: 1, unit: 'mm' },
  { group: 'Pose', key: 'pose.bodyX', label: 'Body lean X (fwd)', min: -80, max: 80, step: 1, unit: 'mm' },
  { group: 'Pose', key: 'pose.bodyY', label: 'Body lean Y (left)', min: -80, max: 80, step: 1, unit: 'mm' },
  { group: 'Pose', key: 'pose.azOff', label: 'Feet azimuth twist', min: -30, max: 30, step: 1, unit: '°' },
  { group: 'Pose', key: 'pose.lifts.0', label: 'Lift FL foot', min: 0, max: 100, step: 1, unit: 'mm' },
  { group: 'Pose', key: 'pose.lifts.1', label: 'Lift FR foot', min: 0, max: 100, step: 1, unit: 'mm' },
  { group: 'Pose', key: 'pose.lifts.2', label: 'Lift RL foot', min: 0, max: 100, step: 1, unit: 'mm' },
  { group: 'Pose', key: 'pose.lifts.3', label: 'Lift RR foot', min: 0, max: 100, step: 1, unit: 'mm' },

  { group: 'Leg geometry', key: 'leg.femur', label: 'Femur length', min: 60, max: 220, step: 1, unit: 'mm' },
  { group: 'Leg geometry', key: 'leg.tibia', label: 'Tibia length', min: 60, max: 240, step: 1, unit: 'mm' },
  { group: 'Leg geometry', key: 'leg.d1', label: 'Hip roll→pitch offset', min: 15, max: 90, step: 1, unit: 'mm' },
  { group: 'Leg geometry', key: 'geo.frontAz', label: 'Front legs azimuth', min: 25, max: 85, step: 1, unit: '°' },
  { group: 'Leg geometry', key: 'geo.rearAz', label: 'Rear legs azimuth', min: 95, max: 155, step: 1, unit: '°' },
  { group: 'Leg geometry', key: 'wheel.dia', label: 'Wheel diameter', min: 40, max: 130, step: 1, unit: 'mm' },
  { group: 'Leg geometry', key: 'wheel.mass', label: 'Wheel mass (each)', min: 25, max: 180, step: 5, unit: 'g' },

  { group: 'Body & payload', key: 'body.cylD', label: 'Cylinder diameter', min: 120, max: 260, step: 2, unit: 'mm' },
  { group: 'Body & payload', key: 'body.cylH', label: 'Cylinder height', min: 140, max: 420, step: 5, unit: 'mm' },
  { group: 'Body & payload', key: 'body.shellMass', label: 'Shell+deck mass', min: 400, max: 1800, step: 25, unit: 'g' },
  { group: 'Body & payload', key: 'body.legMountH', label: 'Leg mount height on cyl', min: 15, max: 120, step: 1, unit: 'mm' },
  { group: 'Body & payload', key: 'masses.batteryH', label: 'Battery height', min: 10, max: 400, step: 5, unit: 'mm' },
  { group: 'Body & payload', key: 'masses.batteryR', label: 'Battery radial offset', min: 0, max: 80, step: 2, unit: 'mm' },
  { group: 'Body & payload', key: 'masses.batteryAz', label: 'Battery azimuth', min: 0, max: 360, step: 5, unit: '°' },
  { group: 'Body & payload', key: 'masses.phoneH', label: 'Phone height', min: 30, max: 400, step: 5, unit: 'mm' },
  { group: 'Body & payload', key: 'masses.headServoN', label: 'Servos in head', min: 0, max: 3, step: 1, unit: '' },
  { group: 'Body & payload', key: 'masses.payloadM', label: 'Extra top payload', min: 0, max: 1000, step: 25, unit: 'g' },

  { group: 'Structure & filament', key: 'leg.beamW', label: 'Beam width', min: 12, max: 32, step: 1, unit: 'mm' },
  { group: 'Structure & filament', key: 'leg.beamT', label: 'Beam thickness', min: 8, max: 26, step: 1, unit: 'mm' },
  { group: 'Structure & filament', key: 'leg.structFactor', label: 'Solidity (infill) factor', min: 0.3, max: 1, step: 0.05, unit: '' },
  { group: 'Structure & filament', key: 'leg.linkRatio', label: 'Linkage ratio (knee)', min: 0.8, max: 2.5, step: 0.05, unit: ':1' },

  { group: 'Environment & power', key: 'env.slopeDeg', label: 'Slope', min: 0, max: 35, step: 0.5, unit: '°' },
  { group: 'Environment & power', key: 'env.slopeHeading', label: 'Downhill heading (0=nose downhill)', min: 0, max: 360, step: 5, unit: '°' },
  { group: 'Environment & power', key: 'env.mu', label: 'Tire friction µ', min: 0.2, max: 1.2, step: 0.05, unit: '' },
  { group: 'Environment & power', key: 'power.soc', label: 'Battery charge', min: 0.05, max: 1, step: 0.05, unit: '×' },
  { group: 'Environment & power', key: 'power.rInt', label: 'Pack+harness resistance', min: 15, max: 150, step: 5, unit: 'mΩ' },

  { group: 'ROM limits', key: 'rom.rollLim', label: 'Hip roll ±limit', min: 20, max: 90, step: 1, unit: '°' },
  { group: 'ROM limits', key: 'rom.hipMin', label: 'Hip pitch min', min: -90, max: 0, step: 1, unit: '°' },
  { group: 'ROM limits', key: 'rom.hipMax', label: 'Hip pitch max', min: 30, max: 150, step: 1, unit: '°' },
  { group: 'ROM limits', key: 'rom.kneeMin', label: 'Knee min', min: -150, max: 0, step: 1, unit: '°' },
  { group: 'ROM limits', key: 'rom.kneeMax', label: 'Knee max', min: 0, max: 150, step: 1, unit: '°' },
];

const TOGGLES = [
  ['com', 'CoM + plumb line'], ['polygon', 'Support polygon'], ['grf', 'GRF arrows'],
  ['joints', 'Joint load markers'], ['targets', 'Foot targets'], ['rom', 'ROM arcs'],
  ['workspace', 'Workspace cloud'], ['masses', 'Mass markers'], ['gravity', 'Gravity arrow'],
];

export function buildUI(app) {
  const panel = document.getElementById('panel');
  const cfg = app.cfg;
  UI_SLIDERS.length = 0;

  // ---- top verdict chips ----
  const chips = document.getElementById('chips');

  // ---- dashboard (filled by refreshReadouts) ----
  const dash = div(panel, 'group');
  dash.innerHTML = `<div id="dashboard"></div>`;

  // ---- pose presets ----
  const pre = div(panel, 'group');
  pre.innerHTML = `<div class="gtitle">Quick poses</div>`;
  const preRow = div(pre, 'row');
  POSE_PRESETS.forEach((p) => {
    const b = button(p.name, () => {
      Object.entries(p.set).forEach(([k, v]) => setPath(cfg, k, v));
      if (p.rebuild) {
        document.getElementById('panel').innerHTML = '';
        document.getElementById('chips').innerHTML = '';
        buildUI(app);
      }
      syncSliders(cfg);
      app.onChange();
    });
    if (p.hint) b.title = p.hint;
    preRow.appendChild(b);
  });

  // ---- mode & discrete controls ----
  const modeBar = div(panel, 'group');
  modeBar.innerHTML = `<div class="gtitle">Mode</div>`;
  const modeRow = div(modeBar, 'row');
  modeRow.appendChild(select('mode', [['stand', 'Standing on ground'], ['suspended', 'Suspended in air']],
    cfg.pose.mode, (v) => { cfg.pose.mode = v; app.onChange(); }));
  modeRow.appendChild(select('filament', Object.keys(FILAMENTS).map((k) => [k, FILAMENTS[k].label]),
    cfg.leg.filament, (v) => { cfg.leg.filament = v; app.onChange(); }));
  const lkRow = div(modeBar, 'row');
  lkRow.appendChild(checkbox('Knee servo at hip via linkage', cfg.leg.linkage, (v) => { cfg.leg.linkage = v; app.onChange(); }));
  lkRow.appendChild(checkbox('Knee tucked low (mammal-style)', cfg.leg.kneeSign > 0, (v) => { cfg.leg.kneeSign = v ? 1 : -1; app.onChange(); }));
  const wmRow = div(modeBar, 'row');
  wmRow.innerHTML = `<label class="slabel">Wheel servo</label>`;
  wmRow.appendChild(select('wheelmount', [
    ['foot', 'At foot (hub motor)'],
    ['knee', 'At knee — belt down tibia'],
    ['hip', 'At hip — belt down femur+tibia'],
  ], cfg.wheel.driveMount, (v) => { cfg.wheel.driveMount = v; app.onChange(); }));

  // ---- sliders by group ----
  const groups = {};
  for (const s of SLIDERS) {
    if (!groups[s.group]) {
      const d = document.createElement('details');
      d.className = 'group';
      d.open = ['Pose', 'Leg geometry'].includes(s.group);
      d.innerHTML = `<summary class="gtitle">${s.group}</summary>`;
      panel.appendChild(d);
      groups[s.group] = d;
    }
    groups[s.group].appendChild(sliderRow(s, cfg, app));
  }

  // ---- overlay toggles ----
  {
    const d = document.createElement('details');
    d.className = 'group';
    d.innerHTML = `<summary class="gtitle">Overlays</summary>`;
    TOGGLES.forEach(([key, label]) => {
      d.appendChild(checkbox(label, app.viewer.toggles[key], (v) => {
        app.viewer.toggles[key] = v;
        if (key === 'workspace') app.updateWorkspace();
        app.refreshView();
      }));
    });
    panel.appendChild(d);
  }

  // ---- readouts ----
  const read = div(panel, 'group');
  read.innerHTML = `<div class="gtitle">Readouts</div><div id="readouts"></div>`;
  const bars = div(panel, 'group');
  bars.innerHTML = `<div class="gtitle">Servo torque (vs stall @ brown-out V)</div><div id="torquebars"></div>`;

  // ---- animation ----
  const anim = div(panel, 'group');
  anim.innerHTML = `<div class="gtitle">Animation</div>`;
  const aRow = div(anim, 'row');
  const presetSel = select('preset', app.presets.map((p, i) => [String(i), p.name]), '0', (v) => app.selectPreset(+v));
  aRow.appendChild(presetSel);
  const playBtn = button('▶ Play', () => app.togglePlay());
  playBtn.id = 'playbtn';
  aRow.appendChild(playBtn);
  const scrub = document.createElement('input');
  scrub.type = 'range'; scrub.min = 0; scrub.max = 1000; scrub.value = 0; scrub.id = 'scrub';
  scrub.addEventListener('input', () => app.scrubTo(scrub.value / 1000));
  anim.appendChild(scrub);
  const durRow = div(anim, 'row');
  durRow.innerHTML = `<label class="slabel">Duration <span id="durval"></span>s</label>`;
  const dur = document.createElement('input');
  dur.type = 'range'; dur.min = 1; dur.max = 20; dur.step = 0.5; dur.value = app.animDur; dur.id = 'duration';
  document.getElementById('durval').textContent = app.animDur;
  dur.addEventListener('input', () => { app.animDur = +dur.value; document.getElementById('durval').textContent = dur.value; app.analyzeAnim(); });
  durRow.appendChild(dur);
  const strip = document.createElement('canvas');
  strip.id = 'flagstrip'; strip.width = 320; strip.height = 26;
  anim.appendChild(strip);
  anim.insertAdjacentHTML('beforeend', `<div class="hint">strip: green ok · amber warn · red overload/tip · purple too-fast</div>`);

  // ---- physics ----
  const phys = div(panel, 'group');
  phys.innerHTML = `<div class="gtitle">Physics (Rapier dynamics)</div>`;
  const pRow = div(phys, 'row');
  pRow.appendChild(button('Enable', () => app.physicsStart(0)));
  pRow.appendChild(button('Drop 5cm', () => app.physicsStart(50)));
  pRow.appendChild(button('Push', () => app.physicsPush()));
  pRow.appendChild(button('Stop', () => app.physicsStop()));
  const dRow = div(phys, 'row');
  dRow.innerHTML = `<label class="slabel">Drive</label>`;
  const drive = document.createElement('input');
  drive.type = 'range'; drive.min = -0.5; drive.max = 0.5; drive.step = 0.02; drive.value = 0; drive.id = 'drive';
  drive.addEventListener('input', () => { app.driveV = +drive.value; });
  drive.addEventListener('dblclick', () => { drive.value = 0; app.driveV = 0; });
  dRow.appendChild(drive);
  const tRow = div(phys, 'row');
  tRow.innerHTML = `<label class="slabel">Turn</label>`;
  const turn = document.createElement('input');
  turn.type = 'range'; turn.min = -0.4; turn.max = 0.4; turn.step = 0.02; turn.value = 0;
  turn.addEventListener('input', () => { app.turnV = +turn.value; });
  turn.addEventListener('dblclick', () => { turn.value = 0; app.turnV = 0; });
  tRow.appendChild(turn);
  phys.insertAdjacentHTML('beforeend', `<div id="physstatus" class="hint"></div>`);

  // ---- gait lab (video math: torque-speed-coupled gait speed) ----
  {
    const gl = document.createElement('details');
    gl.className = 'group'; gl.open = false;
    gl.innerHTML = `<summary class="gtitle">Gait lab — speed vs torque (video math)</summary>
      <div class="hint">The servo torque-speed line makes loaded gait phases slower — ground speed bends onto an asymptote instead of scaling with your command (per the.Amazing PhD's Charlotte analysis, adapted to position servos). Sliders re-run the model on the real crawl gait.</div>`;
    const mk = (label, id, min, max, step, val) => {
      const row = div(gl, 'srow');
      row.innerHTML = `<label class="slabel">${label}</label>`;
      const inp = document.createElement('input');
      inp.type = 'range'; inp.min = min; inp.max = max; inp.step = step; inp.value = val; inp.id = id;
      const out = document.createElement('span'); out.className = 'sval'; out.textContent = val;
      inp.addEventListener('input', () => { out.textContent = inp.value; app.runGaitLab(); });
      row.appendChild(inp); row.appendChild(out);
    };
    mk('Battery charge ×', 'gl_soc', 0.1, 1, 0.05, 0.8);
    mk('Load factor k (dynamics)', 'gl_k', 1.0, 2.0, 0.05, 1.3);
    mk('Payload g', 'gl_pay', 0, 600, 25, 0);
    const cv1 = document.createElement('canvas'); cv1.id = 'gl_speed'; cv1.width = 330; cv1.height = 170;
    const cv2 = document.createElement('canvas'); cv2.id = 'gl_tau'; cv2.width = 330; cv2.height = 150;
    gl.appendChild(cv1); gl.appendChild(cv2);
    gl.insertAdjacentHTML('beforeend', `<div id="gl_read" class="hint"></div>`);
    gl.addEventListener('toggle', () => { if (gl.open) app.runGaitLab(); });
    panel.appendChild(gl);
  }

  // ---- auto-optimizer ----
  {
    const opt = document.createElement('details');
    opt.className = 'group'; opt.open = false;
    opt.innerHTML = `<summary class="gtitle">Auto-optimize</summary>
      <div class="hint">Searches the checked variables for configs passing the constraints on a pose battery (stand, squat, one-leg, 10° slope), then optimizes the goal.</div>`;
    const gRow = div(opt, 'row');
    gRow.innerHTML = `<label class="slabel">Goal</label>`;
    gRow.appendChild(select('goal', Object.entries(GOALS).map(([k, g]) => [k, g.label]), 'balanced',
      (v) => { app.optGoal = v; }));
    app.optGoal = 'balanced';
    app.optCons = { ...DEFAULT_CONSTRAINTS };
    const cRow = div(opt, 'consgrid');
    const consInput = (key, label, step) => {
      const l = document.createElement('label');
      l.className = 'cons';
      l.innerHTML = `${label} `;
      const i = document.createElement('input');
      i.type = 'number'; i.value = app.optCons[key]; i.step = step ?? 1;
      i.addEventListener('change', () => { app.optCons[key] = +i.value; });
      l.appendChild(i);
      cRow.appendChild(l);
    };
    consInput('maxUtil', 'torque ≤ (×stall)', 0.05);
    consInput('minTipDeg', 'tip ≥ °');
    consInput('maxLegAmp', 'leg ≤ A', 0.5);
    consInput('maxTotalAmp', 'main ≤ A', 0.5);
    consInput('maxDeflMm', 'flex ≤ mm', 0.1);
    app.optVars = OPT_VARS.map((v) => ({ ...v }));
    const vWrap = div(opt, 'varsgrid');
    app.optVars.forEach((v) => {
      vWrap.appendChild(checkbox(v.label, v.on, (on) => { v.on = on; }));
    });
    const runRow = div(opt, 'row');
    const runBtn = button('▶ Optimize', () => app.runOptimize(runBtn));
    runRow.appendChild(runBtn);
    runRow.insertAdjacentHTML('beforeend', `<span id="optprog" class="hint"></span>`);
    opt.insertAdjacentHTML('beforeend', `<div id="optresults"></div>`);
    panel.appendChild(opt);
  }

  // ---- tools ----
  const tools = div(panel, 'group');
  tools.innerHTML = `<div class="gtitle">Tools & exports</div>`;
  const t1 = div(tools, 'row');
  t1.appendChild(button('Self-tests', () => app.runSelfTests()));
  t1.appendChild(button('Pose scan', () => app.runScan()));
  t1.appendChild(button('Config study', () => app.runStudy()));
  t1.appendChild(button('Leg studio ↗', () => window.open('./leg.html', '_blank')));
  const t2 = div(tools, 'row');
  t2.appendChild(button('Save config', () => app.exportConfig()));
  t2.appendChild(button('Load config', () => document.getElementById('loadfile').click()));
  const t3 = div(tools, 'row');
  t3.appendChild(button('Servo table (.h)', () => app.exportServoHeader()));
  t3.appendChild(button('Spec sheet (.md)', () => app.exportSpec()));
  t3.appendChild(button('Bench predictions', () => app.exportBench()));
  const lf = document.createElement('input');
  lf.type = 'file'; lf.id = 'loadfile'; lf.accept = '.json'; lf.style.display = 'none';
  lf.addEventListener('change', (e) => app.importConfig(e.target.files[0]));
  tools.appendChild(lf);
  tools.insertAdjacentHTML('beforeend', `<pre id="output" class="output" style="display:none"></pre>`);

  return { chips };
}

// ------- readout refresh (called every pipeline update) -------
export function refreshReadouts(app, res) {
  // chips
  const chips = document.getElementById('chips');
  chips.innerHTML = res.verdicts.map((v) =>
    `<span class="chip ${v.status}" title="${esc(v.detail)}">${v.label}: ${v.value}</span>`).join('');

  // graphic dashboard
  const dash = document.getElementById('dashboard');
  if (dash) dash.innerHTML = renderDashboard(res);

  // detail numbers (things not on the dashboard)
  const R = [];
  R.push(kv('CoM (x,y,z)', res.com.map((c) => (c * 1000).toFixed(0)).join(', ') + ' mm'));
  R.push(kv('Foot loads', res.contacts.length ? res.contacts.map((c, i) =>
    `${LEG_NAMES[c.legIdx]} ${(res.grf.N[i] / 9.81 * 1000).toFixed(0)}g`).join(' · ') : 'none (suspended/airborne)'));
  R.push(kv('Power', `${res.power.vRail.toFixed(2)} V · ${res.power.iTotal.toFixed(2)} A · ${res.power.watts.toFixed(1)} W`));
  R.push(kv('Femur flex', `${(Math.max(...res.deflections, 0) * 1000).toFixed(2)} mm`));
  if (app.collisionIssues?.length) R.push(kv('⚠ collisions', app.collisionIssues.join('; ')));
  document.getElementById('readouts').innerHTML = R.join('');

  // torque bars
  const tb = [];
  res.power.perServo.forEach((s) => {
    const u = Math.min(s.utilization, 1.3);
    const cls = s.utilization < res.cfg.thresholds.contRatio ? 'ok' : s.utilization < res.cfg.thresholds.peakRatio ? 'warn' : 'bad';
    tb.push(`<div class="tbar"><span class="tname">${LEG_NAMES[s.leg]} ${JOINT_NAMES[s.joint]}</span>
      <span class="track"><span class="fill ${cls}" style="width:${(u * 100 / 1.3).toFixed(1)}%"></span></span>
      <span class="tval">${s.tau.toFixed(2)} N·m ${(s.utilization * 100).toFixed(0)}%${s.speedFeasible ? '' : ' ⚡'}</span></div>`);
  });
  document.getElementById('torquebars').innerHTML = tb.join('');
}

export function drawFlagStrip(samples) {
  const cv = document.getElementById('flagstrip');
  const g = cv.getContext('2d');
  g.clearRect(0, 0, cv.width, cv.height);
  if (!samples) return;
  const w = cv.width / samples.length;
  samples.forEach((s, i) => {
    let c = '#37c871';
    if (s.overall === 'warn') c = '#e0a63c';
    if (s.overall === 'bad' || s.tipping || s.unreachable) c = '#e0483c';
    if (s.speedBad) c = '#9d6fff';
    g.fillStyle = c;
    g.fillRect(i * w, 4, Math.ceil(w), cv.height - 8);
  });
}

export function showOutput(text) {
  const o = document.getElementById('output');
  o.style.display = 'block';
  o.textContent = text;
}

// ------- tiny DOM helpers -------
function div(parent, cls) { const d = document.createElement('div'); d.className = cls; parent.appendChild(d); return d; }
function esc(s) { return String(s).replace(/"/g, '&quot;'); }
function kv(k, v) { return `<div class="kv"><span>${k}</span><b>${v}</b></div>`; }

const UI_SLIDERS = []; // registry so presets/optimizer can refresh slider positions

export function syncSliders(cfg) {
  UI_SLIDERS.forEach(({ key, inp, out, unit }) => {
    const v = getPath(cfg, key);
    inp.value = v;
    out.textContent = `${v}${unit}`;
  });
}

function sliderRow(s, cfg, app) {
  const row = document.createElement('div');
  row.className = 'srow';
  const val = getPath(cfg, s.key);
  row.innerHTML = `<label class="slabel">${s.label}</label>`;
  const inp = document.createElement('input');
  inp.type = 'range'; inp.min = s.min; inp.max = s.max; inp.step = s.step; inp.value = val;
  const out = document.createElement('span');
  out.className = 'sval';
  out.textContent = `${val}${s.unit}`;
  inp.addEventListener('input', () => {
    const v = +inp.value;
    setPath(cfg, s.key, v);
    out.textContent = `${v}${s.unit}`;
    app.onChange();
  });
  row.appendChild(inp); row.appendChild(out);
  UI_SLIDERS.push({ key: s.key, inp, out, unit: s.unit });
  return row;
}

function select(id, options, value, onchange) {
  const s = document.createElement('select');
  s.id = 'sel_' + id;
  options.forEach(([v, label]) => {
    const o = document.createElement('option');
    o.value = v; o.textContent = label;
    if (v === value) o.selected = true;
    s.appendChild(o);
  });
  s.addEventListener('change', () => onchange(s.value));
  return s;
}

function checkbox(label, checked, onchange) {
  const l = document.createElement('label');
  l.className = 'check';
  const c = document.createElement('input');
  c.type = 'checkbox'; c.checked = checked;
  c.addEventListener('change', () => onchange(c.checked));
  l.appendChild(c);
  l.appendChild(document.createTextNode(' ' + label));
  return l;
}

function button(label, onclick) {
  const b = document.createElement('button');
  b.textContent = label;
  b.addEventListener('click', onclick);
  return b;
}
