// Actual inline simulation UI, deferred state replies, no browser or network.
// Run: node --test locomotion/scripts/test_remote_speed_ui.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const html = readFileSync(new URL('../sim_remote.html', import.meta.url), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const flush = () => new Promise(resolve => setImmediate(resolve));
class Element {
  constructor(tag = 'div') {
    this.tagName = tag.toUpperCase(); this.value = ''; this.checked = false;
    this.dataset = {}; this.listeners = new Map(); this.children = [];
    this.classList = { toggle() {}, add() {}, remove() {} };
  }
  addEventListener(name, fn) { if (!this.listeners.has(name)) this.listeners.set(name, []); this.listeners.get(name).push(fn); }
  fire(name, extra = {}) {
    const event = { target: this, preventDefault() {}, ...extra };
    for (const fn of this.listeners.get(name) || []) fn(event);
    if (this['on' + name]) this['on' + name](event);
  }
  closest(selector) { return selector.includes('input') && ['INPUT', 'TEXTAREA', 'SELECT'].includes(this.tagName) ? this : null; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
}
function state(controller = 'fast', overrides = {}) {
  const fast = controller === 'fast';
  return { controller, image: 'fixture', fell: false, error: null, seed: 42,
    policy_status: fast ? 'preview_unqualified' : 'baseline_unqualified',
    status: 'simulation only; walking and real transfer are unqualified',
    info: { terrain: 'flat', phone_mass_kg: .155, time_s: 1, command: [0, 0, 0],
      body_velocity: [0, 0, 0], rpy: [0, 0, 0], torque_saturation_fraction: 0, ik_rejections: 0 },
    sensor: { mode: 'mpu6050', valid: true, ready: true, stale: false },
    interactive: { version: 1, profile: fast ? 'Faster crawl preview' : 'Original frozen settings',
      max_translation_m_s: fast ? .03 : .012, default_translation_m_s: fast ? .025 : .01,
      motor_target_rate_rad_s: fast ? 3 : 1.8, cycle_s: fast ? 1.2 : 3.2, real_time_factor: .98,
      status: 'Experimental simulation settings; loaded motor response is unmeasured' },
    setup: { terrain: 'flat', payload: .155, sensor_mode: 'mpu6050', seed: 42,
      randomize: false, sensor_profile: {} }, ...overrides };
}
async function harness(initial = state(), deferred = false) {
  const elements = new Map();
  for (const item of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g)) elements.set(item[2], new Element(item[1]));
  for (const [id, value] of Object.entries({ speed: '.025', controller: 'fast', terrain: 'flat',
    payload: '.155', sensor: 'mpu6050', seed: '42', sensorprofile: '{}', checkpoint: '' })) elements.get(id).value = value;
  const window = new Element(), document = new Element(), intervals = [];
  Object.assign(document, { hidden: false, getElementById: id => elements.get(id),
    querySelectorAll: () => [], createElement: tag => new Element(tag) });
  let current = initial;
  const requests = [];
  function fetch(path, options = {}) {
    let resolve;
    const promise = new Promise(yes => { resolve = yes; });
    const request = { path, body: options.body ? JSON.parse(options.body) : null,
      reply(value) { resolve({ ok: true, json: async () => value }); } };
    requests.push(request);
    if (path === '/api/state') { if (!deferred) request.reply(current); }
    else request.reply({ ok: true });
    return promise;
  }
  vm.runInNewContext(script, { document, window, Element, fetch, AbortController, console,
    setTimeout: () => 0, clearTimeout() {}, setInterval: (fn, delay) => { intervals.push({ fn, delay }); return intervals.length; } });
  await flush();
  return { elements, window, requests,
    async firstReply(value) { deferred = false; current = value; requests.find(request => request.path === '/api/state').reply(value); await flush(); },
    async poll(value) { current = value; intervals.find(timer => timer.delay === 200).fn(); await flush(); },
    async move() { window.fire('keydown', { key: 'w', repeat: false }); await flush(); return requests.filter(request => request.path === '/api/command').at(-1).body.command; },
    edit(id, value, event = 'change') { elements.get(id).value = value; elements.get(id).fire(event); } };
}

test('fast state initializes speed and metadata from the applied profile', async () => {
  const ui = await harness();
  assert.equal(Number(ui.elements.get('speed').value), .025);
  assert.equal(Number(ui.elements.get('speed').max), .03);
  assert.match(ui.elements.get('motorrateval').textContent, /3\.0 rad\/s/);
  assert.match(ui.elements.get('simrateval').textContent, /0\.98/);
  assert.deepEqual(await ui.move(), [.025, 0, 0]);
});

test('legacy state retains its applied cap while faster settings are pending', async () => {
  const ui = await harness(state('ik'));
  ui.edit('controller', 'fast'); ui.edit('speed', '.025', 'input');
  assert.deepEqual(await ui.move(), [.012, 0, 0]);
  await ui.poll(state('ik'));
  assert.equal(ui.elements.get('controller').value, 'fast');
  assert.equal(Number(ui.elements.get('speed').max), .012);
});

test('pending legacy selector does not reduce an applied fast controller speed', async () => {
  const ui = await harness(); ui.edit('controller', 'ik'); await ui.poll(state());
  assert.equal(ui.elements.get('controller').value, 'ik');
  assert.equal(Number(ui.elements.get('speed').max), .03);
  assert.deepEqual(await ui.move(), [.025, 0, 0]);
});

test('initial state preserves settings edited while the first reply is pending', async () => {
  const ui = await harness(state(), true);
  ui.edit('controller', 'ppo'); ui.edit('payload', '0');
  ui.edit('sensorprofile', '{"transport_delay_s":0.02}', 'input'); ui.edit('speed', '.02', 'input');
  await ui.firstReply(state());
  assert.equal(ui.elements.get('controller').value, 'ppo');
  assert.equal(ui.elements.get('payload').value, '0');
  assert.equal(ui.elements.get('sensorprofile').value, '{"transport_delay_s":0.02}');
  assert.equal(Number(ui.elements.get('speed').value), .02);
  assert.equal(Number(ui.elements.get('speed').max), .03);
});

test('first setup reply preserves randomized and custom sensor settings on Apply', async () => {
  const initial = state(); initial.setup.randomize = true;
  initial.setup.sensor_profile = { transport_delay_s: .02, max_age_s: .1 };
  const ui = await harness(initial);
  assert.equal(ui.elements.get('randomize').checked, true);
  assert.deepEqual(JSON.parse(ui.elements.get('sensorprofile').value), initial.setup.sensor_profile);
  ui.elements.get('reset').fire('click'); await flush();
  const reset = ui.requests.find(request => request.path === '/api/reset'); assert.ok(reset);
  assert.equal(reset.body.randomize, true);
  assert.deepEqual(reset.body.sensor_profile, initial.setup.sensor_profile);
});

test('new applied legacy state clamps speed without erasing a pending controller choice', async () => {
  const ui = await harness(); ui.edit('controller', 'sac'); await ui.poll(state('ik'));
  assert.equal(Number(ui.elements.get('speed').max), .012);
  assert.equal(Number(ui.elements.get('speed').value), .012);
  assert.equal(ui.elements.get('controller').value, 'sac');
  assert.deepEqual(await ui.move(), [.012, 0, 0]);
});
