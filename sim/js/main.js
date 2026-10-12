// main.js — wires everything together and exposes window.sim for debugging:
//   sim.cfg            live config (mutate then sim.update())
//   sim.res            last pipeline result
//   sim.set('leg.femur', 150)  set + recompute
//   sim.selftest()     run invariant checks, returns + logs results
//   sim.scan()         worst-pose sweep
//   sim.pose(name)     jump an animation preset to t=0.5

import { defaultConfig, derive, setPath, getPath } from './config.js';
import { evaluate, scanPoses } from './pipeline.js';
import { Viewer } from './render.js';
import { buildUI, refreshReadouts, drawFlagStrip, showOutput, syncSliders } from './ui.js';
import { optimize } from './optimize.js';
import { runStudy, buildReportHTML, openAndDownload } from './report.js';
import { gaitModel, drawSpeedPlot, drawTorquePlot } from './gaitlab.js';
import { presets, cfgAt, analyzeSequence } from './anim.js';
import { runSelfTests, formatTests } from './selftest.js';
import { sampleWorkspace, poseCollisions } from './rom.js';
import { servoHeaderC, specSheetMd, benchPredictions, downloadText } from './exports.js';
import { PhysicsSim } from './physics.js';
import { bodyPosOf } from './config.js';

class App {
  constructor() {
    this.cfg = defaultConfig();
    this.viewer = new Viewer(document.getElementById('view'));
    this.presets = presets(this.cfg);
    this.presetIdx = 0;
    this.animT = 0;
    this.animDur = this.presets[0].dur;
    this.playing = false;
    this.animSamples = null;
    this.driveV = 0;
    this.turnV = 0;
    this.phys = new PhysicsSim();
    this.viewer.scene.add(this.phys.visual);
    this.collisionIssues = [];

    buildUI(this);
    this.onChange();
    this.loop();
  }

  // full recompute + redraw (config changed)
  onChange() {
    if (this.phys.active) this.physicsStop();
    this.presets = presets(this.cfg);
    this.presetIdx = Math.min(this.presetIdx, this.presets.length - 1);
    this.res = evaluate(this.cfg);
    this.collisionIssues = poseCollisions(this.res.P, this.res.legs.map((l) => l.fk), this.res.bodyPos);
    this.viewer.update(this.res);
    refreshReadouts(this, this.res);
    if (this.viewer.toggles.workspace) this.updateWorkspace();
    this.animSamples = null; // invalidate strip
    drawFlagStrip(null);
  }

  refreshView() { if (this.res) this.viewer.update(this.res); }

  updateWorkspace() {
    if (!this.viewer.toggles.workspace) { this.viewer.setWorkspace(null); return; }
    const P = derive(this.cfg);
    const bp = bodyPosOf(this.cfg);
    const clouds = P.phis.map((_, i) => sampleWorkspace(P, i, bp));
    this.viewer.setWorkspace(clouds);
  }

  // ---- animation ----
  selectPreset(i) {
    this.presetIdx = i;
    this.animT = 0;
    this.animDur = this.presets[i].dur;
    const dur = document.getElementById('duration');
    if (dur) dur.value = this.animDur;
    const durval = document.getElementById('durval');
    if (durval) durval.textContent = this.animDur;
    this.analyzeAnim();
    this.scrubTo(0);
  }
  analyzeAnim() {
    const p = this.presets[this.presetIdx];
    this.animSamples = analyzeSequence(this.cfg, p, this.animDur);
    drawFlagStrip(this.animSamples);
  }
  scrubTo(t) {
    this.animT = t;
    if (!this.animSamples) this.analyzeAnim();
    const c = cfgAt(this.cfg, this.presets[this.presetIdx], t);
    this.res = evaluate(c);
    this.collisionIssues = poseCollisions(this.res.P, this.res.legs.map((l) => l.fk), this.res.bodyPos);
    this.viewer.update(this.res);
    refreshReadouts(this, this.res);
    document.getElementById('scrub').value = Math.round(t * 1000);
  }
  togglePlay() {
    this.playing = !this.playing;
    if (this.playing && !this.animSamples) this.analyzeAnim();
    document.getElementById('playbtn').textContent = this.playing ? '⏸ Pause' : '▶ Play';
  }

  // ---- physics ----
  async physicsStart(dropMm) {
    const ok = await this.phys.ensureInit();
    if (!ok) { showOutput('Rapier failed to load (offline? CDN blocked?). Physics unavailable — analytics still work.'); return; }
    this.playing = false;
    this.res = evaluate(this.cfg);
    this.phys.build(this.res, {
      dropMm, slopeDeg: this.cfg.env.slopeDeg, slopeHeading: this.cfg.env.slopeHeading,
    });
    this.viewer.robot.visible = false;
    this.viewer.overlay.visible = false;
  }
  physicsPush() {
    if (!this.phys.active) return;
    this.phys.push(this.res.M * 0.35, [1, 0, 0]); // ~0.35 m/s shove at the head; click repeatedly for more
  }
  physicsStop() {
    this.phys.destroy();
    this.viewer.robot.visible = true;
    this.viewer.overlay.visible = true;
    document.getElementById('physstatus').textContent = '';
  }

  // ---- auto-optimizer ----
  async runOptimize(btn) {
    if (this._optRunning) return;
    this._optRunning = true;
    if (btn) { btn.disabled = true; btn.textContent = '… optimizing'; }
    const prog = document.getElementById('optprog');
    const resBox = document.getElementById('optresults');
    resBox.innerHTML = '';
    try {
      const { top, evals, active } = await optimize(this.cfg, {
        vars: this.optVars, goal: this.optGoal, cons: this.optCons,
        onProgress: (i, n, best) => { prog.textContent = `${i}/${n} evals · best ${best.toFixed(3)}`; },
      });
      prog.textContent = `${evals} evals done`;
      if (!top.length) { resBox.innerHTML = '<div class="hint">No results.</div>'; return; }
      const anyFeasible = top.some((t) => t.feasible);
      resBox.innerHTML = (anyFeasible ? '' :
        `<div class="hint" style="color:#e0a63c">⚠ Nothing satisfied every constraint — showing least-bad. Loosen constraints or free more variables.</div>`)
        + top.map((t, i) => `
        <div class="optrow ${t.feasible ? 'ok' : 'warn'}">
          <div class="opthead"><b>#${i + 1}</b> ${t.feasible ? '✔ feasible' : '⚠ violates constraints'}
            <button data-opt="${i}">Apply</button></div>
          <div class="optvals">${active.map((v, vi) => `${v.label}: <b>${getPath(t.cfg, v.key)}</b>`).join(' · ')}</div>
          <div class="optmet">worst servo ${(t.metrics.worstUtil * 100).toFixed(0)}% · tip ${t.metrics.minTip.toFixed(0)}° ·
            ${(t.metrics.mass * 1000).toFixed(0)}g · ${t.metrics.runtime === Infinity ? '∞' : t.metrics.runtime.toFixed(0)}min ·
            flex ${t.metrics.maxDeflMm.toFixed(2)}mm</div>
        </div>`).join('');
      this._optTop = top;
      resBox.querySelectorAll('button[data-opt]').forEach((b) => {
        b.addEventListener('click', () => {
          const t = this._optTop[+b.dataset.opt];
          active.forEach((v) => setPath(this.cfg, v.key, getPath(t.cfg, v.key)));
          syncSliders(this.cfg);
          this.onChange();
        });
      });
    } finally {
      this._optRunning = false;
      if (btn) { btn.disabled = false; btn.textContent = '▶ Optimize'; }
    }
  }

  // ---- gait lab: torque-speed-coupled crawl speed model ----
  runGaitLab() {
    if (this._glTimer) clearTimeout(this._glTimer);
    this._glTimer = setTimeout(() => {
      const opts = {
        soc: +document.getElementById('gl_soc').value,
        kLoad: +document.getElementById('gl_k').value,
        payloadG: +document.getElementById('gl_pay').value,
      };
      const m = gaitModel(this.cfg, opts);
      this._gaitModel = m;
      drawSpeedPlot(document.getElementById('gl_speed'), m);
      drawTorquePlot(document.getElementById('gl_tau'), m);
      document.getElementById('gl_read').innerHTML =
        `<b>v_max ${(m.vMax * 100).toFixed(1)} cm/s</b> (crawl, ${(m.advance * 1000).toFixed(0)} mm/cycle · min cycle ${m.tCycleMin.toFixed(2)} s, limited by ${m.limiter})<br>` +
        `stance torque ×k: ${(m.stanceTauMax / 0.0981).toFixed(1)} kg·cm ${m.holdOK ? '— <span style="color:#4fdc8b">inside the 10 kg·cm hold budget</span>' : '— <span style="color:#ff6b5e">EXCEEDS 10 kg·cm hold budget</span>'}<br>` +
        `leg stride clearance: fore-aft foot gap ${m.foreAftGap.toFixed(0)} mm vs needed ${m.clearNeeded.toFixed(0)} mm ` +
        (m.legClearOK ? '<span style="color:#4fdc8b">✔ feet cannot collide</span>' : '<span style="color:#ff6b5e">✖ strides overlap — feet can clash</span>');
    }, 120);
  }

  // ---- actuator-layout study -> HTML report ----
  async runStudy() {
    if (this._studyRunning) return;
    this._studyRunning = true;
    showOutput('Running actuator-layout study (5 layouts × optimize × capability battery)…');
    try {
      const rows = await runStudy(this, (msg) => showOutput('Config study: ' + msg));
      const html = buildReportHTML(rows);
      this._lastStudy = { rows, html };
      openAndDownload(html);
      showOutput('Report opened in a new tab and downloaded as MIST_CONFIG_REPORT.html\n\n'
        + rows.map((r) => `${r.layout.id} ${r.layout.name}: stand ${(r.caps.stand.util * 100).toFixed(0)}% · crawl ${(r.caps.can.crawl.util * 100).toFixed(0)}% · slope ${r.caps.can.slope.deg}° · ${r.feasible ? 'feasible' : 'compromised'}`).join('\n'));
      return rows;
    } finally { this._studyRunning = false; }
  }

  // ---- tools ----
  runSelfTests() {
    const tests = runSelfTests(this.cfg);
    const txt = formatTests(tests);
    const fails = tests.filter((t) => !t.pass).length;
    showOutput(`SELF-TESTS: ${tests.length - fails}/${tests.length} passed\n\n` + txt);
    console.log('[sim selftest]\n' + txt);
    return tests;
  }
  runScan() {
    const rows = scanPoses(this.cfg);
    const best = rows.filter((r) => r.ok).sort((a, b) => a.util - b.util).slice(0, 6);
    const worst = rows.filter((r) => r.ok).sort((a, b) => b.util - a.util).slice(0, 3);
    const fmt = (r) => `bodyH ${r.bodyH}mm stanceR ${r.stanceR}mm → worst servo ${(r.util * 100).toFixed(0)}%, tip ${r.tip.toFixed(0)}° [${r.overall}]`;
    showOutput(`POSE SCAN (height × stance sweep, current geometry)\n\nBest (lowest torque):\n` +
      best.map(fmt).join('\n') + `\n\nWorst reachable poses:\n` + worst.map(fmt).join('\n') +
      `\n\n${rows.filter((r) => !r.ok).length}/${rows.length} grid poses unreachable/ROM-clamped.`);
    return rows;
  }
  exportConfig() { downloadText('mist_sim_config.json', JSON.stringify(this.cfg, null, 2)); }
  importConfig(file) {
    if (!file) return;
    file.text().then((t) => {
      try {
        const c = JSON.parse(t);
        this.cfg = c;
        location.hash = '';
        // rebuild UI bound to new cfg object
        document.getElementById('panel').innerHTML = '';
        document.getElementById('chips').innerHTML = '';
        buildUI(this);
        this.presets = presets(this.cfg);
        this.onChange();
      } catch (e) { showOutput('Config load failed: ' + e.message); }
    });
  }
  exportServoHeader() {
    downloadText('mist_pose.h', servoHeaderC(this.res));
    showOutput(servoHeaderC(this.res));
  }
  exportSpec() {
    downloadText('MIST_SIM_SPEC.md', specSheetMd(this.res));
    showOutput(specSheetMd(this.res));
  }
  exportBench() { showOutput(benchPredictions(this.res)); }

  // ---- frame loop ----
  loop(nowMs = performance.now()) {
    requestAnimationFrame((nextMs) => this.loop(nextMs));
    const elapsedS = this._lastFrameMs == null ? 0 : Math.min((nowMs - this._lastFrameMs) / 1000, 0.05);
    this._lastFrameMs = nowMs;
    if (this.playing) {
      this.animT += elapsedS / this.animDur;
      if (this.animT > 1) this.animT = 0;
      this.scrubTo(this.animT);
    }
    if (this.phys.active) {
      this.phys.step(elapsedS, this.driveV, this.turnV);
      this.phys.syncVisual();
      const s = this.phys.status;
      document.getElementById('physstatus').textContent =
        `tilt ${s.tiltDeg.toFixed(1)}° · body z ${(s.bodyZ * 1000).toFixed(0)}mm · ` +
        `GRF ≈ ${this.phys.grfAvg.map((f) => (f / 9.81 * 1000).toFixed(0)).join('/')} g` +
        (s.fallen ? ' · FALLEN' : '');
    }
    this.viewer.controls.update();
    this.viewer.render();
  }
}

const app = new App();

// debug/drive API — usable from the console and from automated tests
window.sim = {
  app,
  get cfg() { return app.cfg; },
  get res() { return app.res; },
  set(path, v) { setPath(app.cfg, path, v); app.onChange(); return app.res.overall; },
  update() { app.onChange(); return app.res.overall; },
  selftest() { return app.runSelfTests(); },
  scan() { return app.runScan(); },
  pose(i, t = 0.5) { app.selectPreset(typeof i === 'number' ? i : app.presets.findIndex((p) => p.name.includes(i))); app.scrubTo(t); },
  verdicts() { return app.res.verdicts.map((v) => `${v.status.toUpperCase()} ${v.label}: ${v.value}`); },
};
console.log('[sim] ready — window.sim available. Try sim.selftest(), sim.verdicts(), sim.set("leg.femur",160)');
