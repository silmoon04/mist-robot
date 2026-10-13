// Run with: node --test locomotion/scripts/test_remote_ui.mjs
// Uses the actual inline UI script. No browser, HTTP server or serial device.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import test from 'node:test';

const htmlPath = fileURLToPath(new URL('../sim_remote.html', import.meta.url));
const html = readFileSync(htmlPath, 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, 'Simulation HTML must contain its executable inline script');
const jointPath = fileURLToPath(new URL('../hardware/remote.html', import.meta.url));
const jointHtml = readFileSync(jointPath, 'utf8');
const flush = () => new Promise(resolve => setImmediate(resolve));

class FakeElement {
  constructor(tagName = 'div') {
    this.tagName = tagName.toUpperCase();
    this.value = ''; this.checked = false; this.disabled = false;
    this.dataset = {}; this.children = []; this.listeners = new Map();
    this.classList = { toggle() {}, add() {}, remove() {} };
    this.textContent = ''; this.isContentEditable = false;
  }
  addEventListener(name, handler) {
    if (!this.listeners.has(name)) this.listeners.set(name, []);
    this.listeners.get(name).push(handler);
  }
  dispatch(name, properties = {}) {
    const event = { target: this, button: 0, pointerId: 1, repeat: false,
      preventDefault() {}, stopPropagation() {}, ...properties };
    const returns = (this.listeners.get(name) || []).map(fn => fn(event));
    if (typeof this['on' + name] === 'function') returns.push(this['on' + name](event));
    return returns;
  }
  closest(selector) {
    if (selector.includes('input') && ['INPUT', 'TEXTAREA', 'SELECT'].includes(this.tagName)) return this;
    if (selector.includes('contenteditable') && this.isContentEditable) return this;
    return null;
  }
  setPointerCapture() {} releasePointerCapture() {} focus() {}
  setAttribute(name, value) { this[name] = value; }
  removeAttribute(name) { delete this[name]; }
  replaceChildren(...children) { this.children = children; this.textContent = ''; }
  append(...children) { for (const child of children) child.parentElement = this; this.children.push(...children); }
  querySelector(selector) {
    for (const child of this.children) {
      if (selector.startsWith('.') && child.className === selector.slice(1)) return child;
      const found = child.querySelector(selector); if (found) return found;
    }
    return null;
  }
}

// Fields follow Simulation.state(), MistEnv._info() and SimulatedIMU.status().
function simulationState() {
  return { image: 'fixture-jpeg', fell: false, controller: 'ik', error: null,
    seed: 42, policy_status: 'baseline_unqualified',
    status: 'simulation only; walking and real transfer are unqualified',
    info: { time_s: 1, terrain: 'flat', phone_mass_kg: .155,
      body_velocity: [0, 0, 0], rpy: [0, 0, 0], command: [0, 0, 0],
      torque_saturation_fraction: 0, ik_rejections: 0 },
    sensor: { mode: 'mpu6050', open_loop: false, frame: 'body',
      units: 'unit down vector; rad/s', measurement_time_s: 1,
      arrival_time_s: 1, valid: true, ready: true, stale: false,
      sample_age_s: 0, received_age_s: 0, generated_samples: 100,
      dropped_samples: 0, profile: {} } };
}

// Bridge.status() shape, with no serial link and no physical feedback.
function bridgeState(overrides = {}) {
  return { mode: 'dry-run', armed: false, intent_generation: 0, fault: null,
    q: Array.from({ length: 12 }, (_, i) => [0, Math.PI / 6, 81 * Math.PI / 180][i % 3]),
    joint_order: ['FL', 'FR', 'RL', 'RR'].flatMap(leg => ['yaw', 'hip', 'knee'].map(joint => `${leg}_${joint}`)),
    calibrated: false, profile_hash: null, gait_active: false, telemetry: {}, imu_raw: {},
    hardware_gait: 'disabled until body IMU and loaded commissioning are validated', ...overrides };
}

async function harness(kind = 'simulation') {
  const selectedHtml = kind === 'simulation' ? html : jointHtml;
  const selectedScript = kind === 'simulation' ? script : selectedHtml.match(/<script>([\s\S]*?)<\/script>/)[1];
  const elements = new Map();
  for (const match of selectedHtml.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g)) {
    elements.set(match[2], new FakeElement(match[1]));
  }
  for (const [id, value] of Object.entries({ speed: '.01', terrain: 'flat',
    payload: '.155', controller: 'ik', sensor: 'mpu6050', checkpoint: '',
    sensorprofile: '{}', seed: '42', xyz: '122.3, 0, -143.0', x: '.12', y: '0', z: '-.14' })) {
    if (elements.has(id)) elements.get(id).value = value;
  }
  const buttons = [...selectedHtml.matchAll(/<button\b[^>]*data-dir="([^"]+)"[^>]*>/g)].map(match => {
    const button = new FakeElement('button'); button.dataset.dir = match[1];
    button.dataset.cmd = match[0].match(/data-cmd="([^"]+)"/)?.[1]; return button;
  });
  const createdElements = [];
  const window = new FakeElement();
  const document = new FakeElement();
  Object.assign(document, { hidden: false, visibilityState: 'visible', activeElement: null,
    getElementById: id => { assert.ok(elements.has(id), `Unknown element ${id}`); return elements.get(id); },
    querySelectorAll: selector => ['[data-dir]', '[data-cmd]'].includes(selector) ? buttons : [],
    createElement: tag => { const item = new FakeElement(tag); createdElements.push(item); return item; }, hasFocus: () => true });
  const requests = [], timers = new Map(), intervals = new Map(); let nextTimer = 0;
  function fetch(path, options = {}) {
    let resolve, reject;
    const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
    const request = { path, options, body: options.body ? JSON.parse(options.body) : null,
      settled: false, reply(value = { ok: true }, ok = true) {
        if (this.settled) return; this.settled = true;
        resolve({ ok, status: ok ? 200 : 400, json: async () => value });
      } };
    options.signal?.addEventListener('abort', () => {
      if (!request.settled) { request.settled = true; reject(new DOMException('Timeout', 'AbortError')); }
    });
    requests.push(request);
    if (path === '/api/state') request.reply(simulationState());
    if (path === '/api/status') request.reply(bridgeState());
    return promise;
  }
  const context = vm.createContext({ document, window, Element: FakeElement,
    AbortController, DOMException, console, fetch,
    setTimeout: (fn, delay) => { const id = ++nextTimer; timers.set(id, { fn, delay }); return id; },
    clearTimeout: id => timers.delete(id),
    setInterval: (fn, delay) => { const id = ++nextTimer; intervals.set(id, { fn, delay }); return id; },
    clearInterval() {}, performance });
  vm.runInContext(selectedScript, context, { filename: kind === 'simulation' ? htmlPath : jointPath });
  await flush();
  const commandRequests = () => requests.filter(request => request.path === '/api/command');
  return { elements, buttons, document, window, requests, commandRequests, createdElements,
    key(name, key, properties = {}) { window.dispatch(name, { key, ...properties }); },
    tickInterval(delay) { for (const timer of intervals.values()) if (timer.delay === delay) timer.fn(); },
    runShortTimers() { for (const [id, timer] of [...timers]) if (timer.delay < 1000) { timers.delete(id); timer.fn(); } },
    async settleCommands() {
      for (let round = 0; round < 4; round++) {
        commandRequests().filter(request => !request.settled).forEach(request => request.reply());
        await flush();
      }
    },
    expireRequestTimeouts() {
      for (const [id, timer] of [...timers]) {
        if (timer.delay >= 1000) { timers.delete(id); timer.fn(); }
      }
    } };
}

const nonzero = request => request.body.command.some(value => value !== 0);

for (const boundary of ['blur', 'pagehide', 'hidden']) {
  test(`an in-flight movement receives a trailing stop after ${boundary}`, async () => {
    const ui = await harness();
    ui.key('keydown', 'w');
    const movement = ui.commandRequests().find(nonzero);
    assert.ok(movement, 'Fresh movement key must send a movement command');
    if (boundary === 'hidden') {
      ui.document.hidden = true; ui.document.visibilityState = 'hidden';
      ui.document.dispatch('visibilitychange');
    } else ui.window.dispatch(boundary);
    // A keepalive zero can reach the threaded server before the pending move.
    ui.commandRequests().filter(request => request !== movement).forEach(request => request.reply());
    await flush();
    const beforeMoveCompletes = ui.requests.length;
    movement.reply(); await flush();
    const trailing = ui.requests.slice(beforeMoveCompletes).filter(request => request.path === '/api/command');
    assert.ok(trailing.some(request => !nonzero(request)), 'Must send zero after outstanding movement completes');
    assert.ok(trailing.every(request => !nonzero(request)), 'Boundary release must not renew movement');
  });
}

for (const stop of ['button', ' ', 'Escape']) {
  test(`Stop (${JSON.stringify(stop)}) cannot be undone by a held key's autorepeat`, async () => {
    const ui = await harness(); ui.key('keydown', 'w'); await ui.settleCommands();
    if (stop === 'button') ui.elements.get('stop').dispatch('click');
    else ui.key('keydown', stop);
    await ui.settleCommands();
    const beforeRepeat = ui.commandRequests().length;
    ui.key('keydown', 'w', { repeat: true }); await ui.settleCommands();
    assert.ok(ui.commandRequests().slice(beforeRepeat).every(request => !nonzero(request)), 'Repeated held key restarted motion after Stop');
    ui.key('keyup', 'w'); ui.key('keydown', 'w'); await ui.settleCommands();
    assert.ok(nonzero(ui.commandRequests().at(-1)), 'A fresh press after release must still work');
  });
}

test('typing movement keys in editable fields does not send motion', async () => {
  const ui = await harness();
  for (const tag of ['input', 'textarea', 'select', 'div']) {
    const target = new FakeElement(tag); target.isContentEditable = tag === 'div';
    for (const key of ['w', 'a', 's', 'd', 'q', 'e']) ui.key('keydown', key, { target });
  }
  assert.equal(ui.commandRequests().filter(nonzero).length, 0);
});

test('pointer cancellation sends a stop after a held movement', async () => {
  const ui = await harness(); const forward = ui.buttons.find(button => button.dataset.dir === 'forward');
  forward.dispatch('pointerdown', { pointerId: 7 }); await ui.settleCommands();
  assert.ok(nonzero(ui.commandRequests().at(-1)));
  forward.dispatch('pointercancel', { pointerId: 7 }); await ui.settleCommands();
  assert.deepEqual(ui.commandRequests().at(-1).body.command, [0, 0, 0]);
});

test('explicit reset refusal and transport timeout have different outcome messages', async () => {
  const messages = [];
  for (const outcome of ['refused', 'timeout']) {
    const ui = await harness(); ui.elements.get('reset').dispatch('click');
    await ui.settleCommands();
    const reset = ui.requests.find(request => request.path === '/api/reset');
    assert.ok(reset, 'Valid reset settings must reach the API');
    if (outcome === 'refused') reset.reply({ error: 'phone sensor mode requires a present phone payload; use mpu6050 or explicit none mode' }, false);
    else ui.expireRequestTimeouts();
    await flush();
    messages.push(ui.elements.get('settingsnote').textContent);
  }
  assert.notEqual(messages[0], messages[1], 'A lost response cannot establish the same outcome as explicit server refusal');
  assert.doesNotMatch(messages[1], /settings were not applied/i, 'Server reset may complete after client timeout');
});

async function enabledJointHarness() {
  const ui = await harness('joints');
  ui.elements.get('arm').dispatch('click'); await flush();
  const arm = ui.commandRequests().find(request => request.body.op === 'arm');
  assert.ok(arm, 'Preview enable must send arm intent');
  assert.equal(arm.body.intent_generation, 0);
  arm.reply(bridgeState({ armed: true, intent_generation: 1 })); await flush();
  return ui;
}

test('joint slider intent is applied after a delayed older gait request', async () => {
  const ui = await enabledJointHarness(); ui.key('keydown', 'w'); await flush();
  const gait = ui.commandRequests().find(request => request.body.op === 'gait');
  assert.ok(gait, 'Fresh direction must request gait');
  const slider = ui.createdElements.find(item => item.tagName === 'INPUT');
  slider.value = .1; slider.dispatch('input'); ui.tickInterval(35); await flush();
  // Simulate an early q finishing first if the UI wrongly uses independent queues.
  for (const q of ui.commandRequests().filter(request => request.body.op === 'q')) {
    q.reply(bridgeState({ armed: true, intent_generation: 1, q: q.body.q }));
  }
  await flush();
  const beforeGaitCompletes = ui.requests.length;
  gait.reply(bridgeState({ armed: true, intent_generation: 1, gait_active: true })); await flush();
  ui.tickInterval(35); ui.runShortTimers(); await flush();
  const trailing = ui.requests.slice(beforeGaitCompletes).filter(request => request.body?.op === 'q');
  assert.ok(trailing.length, 'Slider must own the final target after the older gait completes');
  assert.ok(Math.abs(trailing.at(-1).body.q[0] - .1 * Math.PI / 180) < 1e-12);
});

test('new joint gait intent waits for an outstanding older slider target', async () => {
  const ui = await enabledJointHarness();
  const slider = ui.createdElements.find(item => item.tagName === 'INPUT');
  slider.value = .1; slider.dispatch('input'); ui.tickInterval(35); await flush();
  const q = ui.commandRequests().find(request => request.body.op === 'q'); assert.ok(q);
  ui.key('keydown', 'w'); await flush();
  // Applying a new gait before this q finishes lets the old q cancel it on the bridge.
  for (const gait of ui.commandRequests().filter(request => request.body.op === 'gait')) {
    gait.reply(bridgeState({ armed: true, intent_generation: 1, gait_active: true }));
  }
  await flush(); const beforeQCompletes = ui.requests.length;
  q.reply(bridgeState({ armed: true, intent_generation: 1, q: q.body.q })); await flush();
  ui.runShortTimers(); await flush();
  const trailing = ui.requests.slice(beforeQCompletes).filter(request => request.body?.op === 'gait');
  assert.ok(trailing.some(request => request.body.command[0] > 0), 'Fresh gait must own the final target after older q completes');
});

test('joint gait release queues standing after the pending movement completes', async () => {
  const ui = await enabledJointHarness(); ui.key('keydown', 'w'); await flush();
  const gait = ui.commandRequests().find(request => request.body.op === 'gait'); assert.ok(gait);
  ui.key('keyup', 'w'); const before = ui.requests.length;
  gait.reply(bridgeState({ armed: true, intent_generation: 1, gait_active: true })); await flush();
  const trailing = ui.requests.slice(before).filter(request => request.body?.op === 'gait');
  assert.ok(trailing.some(request => request.body.command.every(value => value === 0)));
});

test('late arm response cannot re-enable joints after a newer confirmed stop', async () => {
  const ui = await harness('joints'); ui.elements.get('arm').dispatch('click'); await flush();
  const arm = ui.commandRequests().find(request => request.body.op === 'arm'); assert.ok(arm);
  ui.elements.get('stop').dispatch('click'); await flush();
  const stop = ui.commandRequests().find(request => request.body.op === 'estop'); assert.ok(stop);
  stop.reply(bridgeState({ intent_generation: 2, fault: 'remote stop' })); await flush();
  arm.reply(bridgeState({ armed: true, intent_generation: 1 })); await flush();
  assert.ok(ui.buttons.every(button => button.disabled), 'Stale arm response must not enable gait buttons');
  assert.ok(ui.createdElements.filter(item => item.tagName === 'INPUT').every(slider => slider.disabled));
  const before = ui.requests.length; ui.key('keydown', 'w'); await flush();
  assert.ok(!ui.requests.slice(before).some(request => request.body?.op === 'gait'));
});
