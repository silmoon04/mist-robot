// dashboard.js — the "important metrics" graphics: overall banner, stat cards,
// voltage gauge with sag + brown-out zone, per-leg fuse bars, worst-servo dial,
// and a tip compass (which way it wants to fall, and how much margin per direction).
// Pure HTML/SVG string generation; re-rendered on every pipeline update.

import { LEG_NAMES } from './config.js';
import { JOINT_NAMES } from './exports.js';

const C = { ok: '#37c871', warn: '#e0a63c', bad: '#e0483c', dim: '#5b6478', txt: '#c6ccd8' };
const col = (s) => C[s] || C.dim;

export function renderDashboard(res) {
  const th = res.cfg.thresholds;
  const worst = res.power.perServo.reduce((a, s) => (s.utilization > a.utilization ? s : a));
  const suspended = res.cfg.pose.mode === 'suspended';

  const failing = res.verdicts.filter((v) => v.status === 'bad');
  const warning = res.verdicts.filter((v) => v.status === 'warn');
  const headline = res.overall === 'ok'
    ? 'All margins green — buildable pose'
    : (failing[0] || warning[0]).label + ': ' + (failing[0] || warning[0]).detail;
  const banner = `
    <div class="banner ${res.overall}">
      <div class="bstate">${res.overall === 'ok' ? '✔ BUILDABLE' : res.overall === 'warn' ? '⚠ MARGINAL' : '✖ FAILING'}</div>
      <div class="bwhy">${esc(headline)}</div>
    </div>`;

  const cards = `
    <div class="cards">
      ${card('Total mass', (res.M * 1000).toFixed(0), 'g', 'ok')}
      ${card('CoM height', (res.com[2] * 1000).toFixed(0), 'mm', 'ok')}
      ${card('Runtime', res.power.runtimeMin === Infinity ? '∞' : res.power.runtimeMin.toFixed(0), 'min',
        res.power.runtimeMin < 15 ? 'warn' : 'ok')}
      ${card('Worst servo', (worst.utilization * 100).toFixed(0), `% · ${LEG_NAMES[worst.leg]} ${JOINT_NAMES[worst.joint]}`,
        worst.utilization < th.contRatio ? 'ok' : worst.utilization < th.peakRatio ? 'warn' : 'bad')}
    </div>`;

  return banner + cards
    + torqueGauge(worst, th)
    + voltageGauge(res.power, th)
    + fuseBars(res.power, th, res.cfg.power)
    + (suspended ? '' : tipCompass(res.stab, res.cfg, th));
}

function card(label, value, unit, status) {
  return `<div class="card ${status}"><div class="cval">${value}<span class="cunit">${unit}</span></div><div class="clabel">${label}</div></div>`;
}

// worst-servo dial: 0..130% with the 30% continuous and 55% peak zone marks
function torqueGauge(worst, th) {
  const pct = Math.min(worst.utilization, 1.3) / 1.3 * 100;
  const cont = th.contRatio / 1.3 * 100, peak = th.peakRatio / 1.3 * 100;
  const c = worst.utilization < th.contRatio ? C.ok : worst.utilization < th.peakRatio ? C.warn : C.bad;
  return `
  <div class="gauge"><div class="glabel">Worst servo torque <b style="color:${c}">${(worst.utilization * 100).toFixed(0)}%</b> of stall @ brown-out</div>
  <svg viewBox="0 0 320 26" class="gsvg">
    <rect x="0" y="8" width="320" height="10" rx="5" fill="#14161a"/>
    <rect x="0" y="8" width="${cont * 3.2}" height="10" rx="5" fill="#1e3529"/>
    <rect x="${cont * 3.2}" y="8" width="${(peak - cont) * 3.2}" height="10" fill="#3a3122"/>
    <rect x="${peak * 3.2}" y="8" width="${(100 - peak) * 3.2}" height="10" fill="#3a2422"/>
    <rect x="0" y="8" width="${pct * 3.2}" height="10" rx="5" fill="${c}"/>
    <line x1="${cont * 3.2}" y1="4" x2="${cont * 3.2}" y2="22" stroke="#4fdc8b" stroke-width="1.5"/>
    <line x1="${peak * 3.2}" y1="4" x2="${peak * 3.2}" y2="22" stroke="#f0b64c" stroke-width="1.5"/>
    <text x="${cont * 3.2 + 3}" y="7" class="gtick">cont ${(th.contRatio * 100).toFixed(0)}%</text>
    <text x="${peak * 3.2 + 3}" y="7" class="gtick">peak ${(th.peakRatio * 100).toFixed(0)}%</text>
  </svg></div>`;
}

// pack voltage: open-circuit ghost, sagged rail needle, brown-out zone
function voltageGauge(power, th) {
  const lo = 9.0, hi = 12.7;
  const X = (v) => Math.max(0, Math.min(1, (v - lo) / (hi - lo))) * 320;
  const c = power.vRail > th.vWarn ? C.ok : power.vRail > th.vMin ? C.warn : C.bad;
  return `
  <div class="gauge"><div class="glabel">Rail voltage <b style="color:${c}">${power.vRail.toFixed(2)} V</b>
    <span class="dim">(sag ${(power.vOC - power.vRail).toFixed(2)} V · draw ${power.iTotal.toFixed(1)} A)</span></div>
  <svg viewBox="0 0 320 26" class="gsvg">
    <rect x="0" y="8" width="320" height="10" rx="5" fill="#14161a"/>
    <rect x="0" y="8" width="${X(th.vMin)}" height="10" rx="5" fill="#3a2422"/>
    <rect x="${X(th.vMin)}" y="8" width="${X(th.vWarn) - X(th.vMin)}" height="10" fill="#3a3122"/>
    <rect x="${X(th.vWarn)}" y="8" width="${320 - X(th.vWarn)}" height="10" fill="#1e3529"/>
    <line x1="${X(power.vOC)}" y1="5" x2="${X(power.vOC)}" y2="21" stroke="#7d8494" stroke-width="2" stroke-dasharray="2 2"/>
    <rect x="${X(power.vRail) - 2.5}" y="4" width="5" height="18" rx="2" fill="${c}"/>
    <text x="${X(th.vMin) - 2}" y="7" class="gtick" text-anchor="end">${th.vMin}V cutoff</text>
    <text x="${X(power.vOC) + 3}" y="7" class="gtick">no-load</text>
  </svg></div>`;
}

// per-leg branch current vs 15A blades + total vs 30A main
function fuseBars(power, th, cfgPower) {
  const bar = (label, amps, fuse, warn, max) => {
    const c = amps < warn ? C.ok : amps < max ? C.warn : C.bad;
    const w = Math.min(amps / fuse, 1.05) * 100;
    return `<div class="fbar"><span class="fname">${label}</span>
      <span class="ftrack"><span style="width:${w}%;background:${c}" class="ffill"></span>
      <span class="fmark" style="left:${(max / fuse) * 100}%"></span></span>
      <span class="fval" style="color:${c}">${amps.toFixed(1)}/${fuse}A</span></div>`;
  };
  return `
  <div class="gauge"><div class="glabel">Fuse margins</div>
    ${power.legAmps.map((a, i) => bar(LEG_NAMES[i], a, cfgPower.fuseLeg, th.legAmpWarn, th.legAmpMax)).join('')}
    ${bar('MAIN', power.iTotal, cfgPower.fuseMain, th.totAmpWarn, th.totAmpMax)}
  </div>`;
}

// polar plot: tip margin per direction. Radius = margin (bigger blob = safer);
// the needle points where it would fall first.
function tipCompass(stab, cfg, th) {
  const R = 52, cx = 60, cy = 60;
  const maxDeg = 40;
  if (!stab.edges.length) return '';
  const pts = [];
  const es = stab.edges.map((e) => {
    const ex = e.b[0] - e.a[0], ey = e.b[1] - e.a[1];
    const az = Math.atan2(-ex, ey); // outward normal azimuth (CCW hull)
    return { az, tip: Math.max(0, Math.min(maxDeg, e.tipDeg)), raw: e.tipDeg };
  }).sort((a, b) => a.az - b.az);
  // closed polygon through per-edge margins (screen: x=east=world -Y? draw world X up)
  const P = (az, r) => [cx + Math.sin(az) * r, cy - Math.cos(az) * r]; // world +X = up
  es.forEach((e) => pts.push(P(e.az, (e.tip / maxDeg) * R)));
  const weakest = es.reduce((a, b) => (b.raw < a.raw ? b : a));
  const wc = weakest.raw > th.tipWarnDeg ? C.ok : weakest.raw > th.tipMinDeg ? C.warn : C.bad;
  const [wx, wy] = P(weakest.az, R + 4);
  const rings = [10, 20, 30].map((d) =>
    `<circle cx="${cx}" cy="${cy}" r="${(d / maxDeg) * R}" fill="none" stroke="#2a2e36" stroke-width="1"/>
     <text x="${cx + 2}" y="${cy - (d / maxDeg) * R + 3}" class="gtick">${d}°</text>`).join('');
  const slope = cfg.env.slopeDeg > 0 ? (() => {
    const h = cfg.env.slopeHeading * Math.PI / 180;
    const [sx, sy] = P(h, R + 10);
    return `<text x="${sx}" y="${sy}" class="gtick" text-anchor="middle" fill="${C.warn}">⛰${cfg.env.slopeDeg}°</text>`;
  })() : '';
  return `
  <div class="gauge"><div class="glabel">Tip compass <b style="color:${wc}">${weakest.raw.toFixed(1)}°</b>
    <span class="dim">to tip (worst direction)</span></div>
  <div class="tiprow"><svg viewBox="0 0 120 120" class="tipsvg">
    ${rings}
    <polygon points="${pts.map((p) => p.map((v) => v.toFixed(1)).join(',')).join(' ')}"
      fill="${wc}22" stroke="${wc}" stroke-width="1.5" stroke-linejoin="round"/>
    <line x1="${cx}" y1="${cy}" x2="${wx}" y2="${wy}" stroke="${wc}" stroke-width="2"/>
    <circle cx="${cx}" cy="${cy}" r="2.5" fill="#e8ecf4"/>
    <text x="${cx}" y="9" class="gtick" text-anchor="middle">front</text>
    ${slope}
  </svg>
  <div class="tipnote">Blob = how many degrees of tilt each direction survives.<br>
  Needle = falls this way first.<br>CoM inside polygon by <b>${(stab.margin * 1000).toFixed(0)} mm</b>.</div></div>
  </div>`;
}

function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
