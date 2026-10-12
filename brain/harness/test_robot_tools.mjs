import assert from 'node:assert/strict';
import { test } from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import { readCapabilitySnapshot, OBSERVATION_TTL_MS, WORKER_HEARTBEAT_TTL_MS } from '../extensions/grounding.ts';

const brainDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let seq = 0;

async function fixture(t, sim = {}) {
  const runDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mist-tools-'));
  t.after(() => {
    assert.equal(path.dirname(path.resolve(runDir)), path.resolve(os.tmpdir()));
    assert.match(path.basename(runDir), /^mist-tools-/);
    fs.rmSync(runDir, { recursive: true, force: true });
  });
  process.env.ROBOT_BRAIN_DIR = brainDir;
  process.env.ROBOT_RUN_DIR = runDir;
  process.env.ROBOT_USE_DEMO_MEMORY = '0';
  const updateSim = (value) => fs.writeFileSync(path.join(runDir, 'sim_state.json'), JSON.stringify(value));
  updateSim(sim);
  const registered = new Map();
  const extension = await import(pathToFileURL(path.join(brainDir, 'extensions', 'robot-tools.ts')).href + `?test=${++seq}`);
  extension.default({ registerTool: (tool) => registered.set(tool.name, tool) });
  const call = (name, args = {}) => registered.get(name).execute('offline-test', args);
  const text = (receipt) => receipt.content[0].text;
  const json = (receipt) => JSON.parse(text(receipt));
  const state = () => JSON.parse(fs.readFileSync(path.join(runDir, 'robot_state.json'), 'utf8'));
  return { runDir, registered, updateSim, call, text, json, state };
}

test('capability registry cannot claim hardware or unavailable tools', async (t) => {
  const f = await fixture(t);
  const capabilities = f.json(await f.call('get_capabilities'));
  assert.equal(capabilities.motion.hardware_connected, false);
  assert.equal(capabilities.motion.stairs_validated, false);
  assert.equal(capabilities.perception.available, false);
  assert.equal(f.registered.size, 18);
  for (const name of ['bash', 'exec', 'send_email', 'write', 'read']) assert.equal(f.registered.has(name), false);
});

test('internal capability context reads do not emit tool events or rewrite robot state', async (t) => {
  const f = await fixture(t);
  const stateFile = path.join(f.runDir, 'robot_state.json');
  const original = JSON.stringify({ tickets: [], x_m: 1.25, face: 'curious' });
  fs.writeFileSync(stateFile, original);
  const before = fs.readdirSync(f.runDir).sort();
  assert.equal(readCapabilitySnapshot(f.runDir).motion.hardware_connected, false);
  const child = spawnSync(process.execPath, [path.join(brainDir, 'harness', 'codex_tool_bridge.mjs')], {
    env: { ...process.env, ROBOT_BRAIN_DIR: brainDir, ROBOT_RUN_DIR: f.runDir, ROBOT_USE_DEMO_MEMORY: '0' },
    input: '{"id":"context","method":"context"}\n{"id":"list","method":"list"}\n',
    encoding: 'utf8', timeout: 10_000, windowsHide: true,
  });
  assert.equal(child.status, 0, child.stderr);
  const responses = child.stdout.trim().split(/\r?\n/).map((line) => JSON.parse(line));
  const context = responses.find((response) => response.id === 'context');
  assert.equal(context.isError, false);
  assert.equal(context.result.schema_version, 1);
  assert.equal(context.result.perception.requires_fresh_observe, true);
  const specs = responses.find((response) => response.id === 'list').result;
  assert.equal(specs.length, 18);
  assert.equal(specs.some((spec) => spec.name === 'context'), false);
  assert.deepEqual(fs.readdirSync(f.runDir).sort(), before);
  assert.equal(fs.readFileSync(stateFile, 'utf8'), original);
  assert.equal(fs.existsSync(path.join(f.runDir, 'bus.jsonl')), false);
});

test('capability snapshots refresh worker and perception availability without caching reports', async (t) => {
  const f = await fixture(t);
  const now = Date.parse('2026-09-07T12:00:00.000Z');
  const heartbeat = path.join(f.runDir, 'worker.alive');
  const observation = path.join(f.runDir, 'observation.json');
  const missing = readCapabilitySnapshot(f.runDir, now);
  assert.equal(missing.executive.online, false);
  assert.equal(missing.perception.status, 'missing');
  fs.writeFileSync(heartbeat, '');
  fs.utimesSync(heartbeat, new Date(now - 100), new Date(now - 100));
  fs.writeFileSync(observation, JSON.stringify({ captured_at: new Date(now - 100).toISOString() }));
  const fresh = readCapabilitySnapshot(f.runDir, now);
  assert.equal(fresh.checked_at, new Date(now).toISOString());
  assert.equal(fresh.executive.online, true);
  assert.equal(fresh.perception.available, true);
  assert.equal(fresh.perception.status, 'available');
  assert.equal(fresh.perception.age_ms, 100);
  const staleObservation = readCapabilitySnapshot(f.runDir, now + OBSERVATION_TTL_MS);
  assert.equal(staleObservation.perception.status, 'stale');
  assert.equal(staleObservation.executive.online, true);
  assert.equal(readCapabilitySnapshot(f.runDir, now + WORKER_HEARTBEAT_TTL_MS).executive.online, false);
  fs.utimesSync(heartbeat, new Date(now + 2_000), new Date(now + 2_000));
  fs.writeFileSync(observation, '{broken');
  const invalid = readCapabilitySnapshot(f.runDir, now);
  assert.equal(invalid.executive.online, false);
  assert.equal(invalid.perception.status, 'invalid');
  assert.equal(fs.existsSync(path.join(f.runDir, 'bus.jsonl')), false);
});

test('trusted capability metadata excludes producer text while capability tools retain untrusted reports', async (t) => {
  const f = await fixture(t);
  const marker = 'UNTRUSTED-PRODUCER-INSTRUCTION';
  fs.writeFileSync(path.join(f.runDir, 'observation.json'), JSON.stringify({
    captured_at: new Date().toISOString(), source: marker, summary: marker,
    objects: [{ label: marker }], hazards: [marker],
  }));
  const snapshot = readCapabilitySnapshot(f.runDir);
  assert.equal(snapshot.perception.available, true);
  assert.equal(snapshot.perception.source_verified, false);
  assert.equal(snapshot.perception.requires_fresh_observe, true);
  assert.equal(JSON.stringify(snapshot).includes(marker), false);
  assert.deepEqual(Object.keys(snapshot.perception).sort(), [
    'age_ms', 'available', 'captured_at', 'max_age_ms', 'requires_fresh_observe', 'source_verified', 'status',
  ]);
  const capabilities = f.json(await f.call('get_capabilities'));
  for (const field of ['identity', 'body_design', 'motion', 'face', 'memory', 'unavailable']) {
    assert.deepEqual(capabilities[field], snapshot[field]);
  }
  assert.deepEqual(Object.keys(capabilities.executive).sort(), ['actions', 'autonomous_notifications', 'online']);
  assert.equal(capabilities.perception.untrusted, true);
  assert.equal(capabilities.perception.summary, marker);
  assert.equal(capabilities.perception.source, marker);
  assert.equal(f.registered.size, 18);
});

test('movement emits a simulation receipt with actual simulated odometry', async (t) => {
  const f = await fixture(t, { walk_scale: 0.95 });
  const receipt = await f.call('walk', { distance_m: 1 });
  assert.match(f.text(receipt), /^\[SIMULATION; hardware not connected\]/);
  assert.equal(receipt.details.execution, 'simulation');
  assert.equal(f.state().x_m, 0.95);
  const bus = JSON.parse(fs.readFileSync(path.join(f.runDir, 'bus.jsonl'), 'utf8').trim());
  assert.equal(bus.tool, 'walk');
  assert.match(bus.result, /SIMULATION/);
});

test('all motion tools share the heat interlock and stop still works', async (t) => {
  const f = await fixture(t, { servo_temp_max_c: 80 });
  const cases = [['walk', { distance_m: 0.1 }], ['drive', { distance_m: 0.1 }],
    ['turn', { angle_deg: 10 }], ['move', { vx: 0.1, vy: 0, omega: 0, duration_s: 1 }],
    ['pose', { height_mm: 50 }], ['dance', { name: 'ominous_sway' }]];
  for (const [name, args] of cases) await assert.rejects(f.call(name, args), /80C/);
  await f.call('stop');
  assert.equal(f.state().x_m, 0);
  assert.equal(f.state().body.height_mm, 90);
  await f.call('face', { expression: 'alert' });
  assert.equal(f.state().face, 'alert');
});

test('short commands cannot bypass low battery or a latched simulation stop', async (t) => {
  const f = await fixture(t, { battery_pct: 5 });
  await assert.rejects(f.call('walk', { distance_m: 0.1 }), /battery/);
  f.updateSim({ emergency_stop: true });
  await assert.rejects(f.call('drive', { distance_m: 0.1 }), /latched/);
  await f.call('stop');
  await assert.rejects(f.call('walk', { distance_m: 0.1 }), /latched/);
});

test('thermal cutoff matches the recovered 50C bench shutdown and permits only lower settings', async (t) => {
  const f = await fixture(t, { servo_temp_max_c: 49.9 });
  await f.call('walk', { distance_m: 0.1 });
  const before = f.state().x_m;
  f.updateSim({ servo_temp_max_c: 50 });
  await assert.rejects(f.call('walk', { distance_m: 0.1 }), /cutoff 50C/);
  assert.equal(f.state().x_m, before);
  f.updateSim({ servo_temp_max_c: 44.9, servo_temp_limit_c: 45 });
  await f.call('turn', { angle_deg: 5 });
  f.updateSim({ servo_temp_max_c: 45, servo_temp_limit_c: 45 });
  await assert.rejects(f.call('turn', { angle_deg: 5 }), /cutoff 45C/);
  const status = await f.call('get_status');
  assert.match(f.text(status), /"servo_temp_limit_c":45/);
  f.updateSim({ servo_temp_max_c: 44, servo_temp_limit_c: 51 });
  await assert.rejects(f.call('walk', { distance_m: 0.1 }), /bench shutdown limit/);
  await f.call('stop');
});

test('stairs, table edges and unknown terrain have no implicit motion permission', async (t) => {
  const f = await fixture(t);
  for (const surface of ['stairs', 'table', 'unknown', 'gravel']) {
    f.updateSim({ surface });
    await assert.rejects(f.call('walk', { distance_m: 1 }), /no validated motion controller/);
  }
  f.updateSim({ surface: 'rug' });
  await assert.rejects(f.call('drive', { distance_m: 1 }), /rug/);
  await f.call('walk', { distance_m: 1 });
});

test('nonfinite intent or malformed numeric telemetry leaves position unchanged', async (t) => {
  const f = await fixture(t);
  await assert.rejects(f.call('walk', { distance_m: NaN }), /finite/);
  await assert.rejects(f.call('move', { vx: 0.1, vy: Infinity, omega: 0, duration_s: 1 }), /finite/);
  f.updateSim({ battery_pct: 'full' });
  await assert.rejects(f.call('turn', { angle_deg: 20 }), /invalid battery/);
  f.updateSim({ walk_scale: -1 });
  await assert.rejects(f.call('walk', { distance_m: 1 }), /odometry scale/);
  assert.equal(f.state().x_m, 0);
});

test('corrupt simulator configuration fails closed while stop remains available', async (t) => {
  const f = await fixture(t);
  for (const content of ['null', '[]', '{broken']) {
    fs.writeFileSync(path.join(f.runDir, 'sim_state.json'), content);
    await assert.rejects(f.call('walk', { distance_m: 1 }), /invalid simulator configuration/);
    await f.call('stop');
  }
  assert.equal(f.state().x_m, 0);
});

test('gaze request cannot confirm detection or tracking', async (t) => {
  const f = await fixture(t);
  assert.match(f.text(await f.call('look_at', { target: 'door' })), /tracking are unverified/);
});

test('fresh observations preserve reported provenance but stale data is unavailable', async (t) => {
  const f = await fixture(t);
  const file = path.join(f.runDir, 'observation.json');
  const observation = { source: 'test-camera', captured_at: new Date().toISOString(),
    summary: 'A chair is ahead.', objects: [{ label: 'chair', distance_m: 0.8, confidence: 0.6 }], hazards: ['obstacle'] };
  fs.writeFileSync(file, JSON.stringify(observation));
  const fresh = f.json(await f.call('observe'));
  assert.equal(fresh.available, true);
  assert.equal(fresh.untrusted, true);
  assert.equal(fresh.objects[0].distance_m, 0.8);
  assert.match(fresh.provenance, /not independently verified/);
  fs.writeFileSync(file, JSON.stringify({ ...observation, captured_at: new Date(Date.now() - 10_000).toISOString() }));
  const stale = f.json(await f.call('observe'));
  assert.equal(stale.available, false);
  assert.equal(stale.reason, 'stale');
  assert.equal(stale.summary, undefined);
});

test('invalid and future observations are unavailable', async (t) => {
  const f = await fixture(t);
  const file = path.join(f.runDir, 'observation.json');
  for (const content of ['{broken', JSON.stringify({ captured_at: new Date(Date.now() + 20_000).toISOString() })]) {
    fs.writeFileSync(file, content);
    assert.equal(f.json(await f.call('observe')).available, false);
  }
});

test('saved memory is searchable without polluting demo memory', async (t) => {
  const demoFile = path.join(brainDir, 'memory', 'SCRATCH.md');
  const before = fs.readFileSync(demoFile, 'utf8');
  const f = await fixture(t);
  await f.call('note', { text: 'Owner prefers a quiet greeting.' });
  const notes = f.json(await f.call('recall_memory', { query: 'quiet greeting' }));
  assert.equal(notes.matches.length, 1);
  assert.equal(notes.matches[0].source, 'runtime notes');
  assert.equal(notes.untrusted, true);
  assert.equal(fs.readFileSync(demoFile, 'utf8'), before);
  await assert.rejects(f.call('note', { text: 'line one\nline two' }), /one nonempty line/);
});

test('offline executive stays pending instead of inventing an answer', async (t) => {
  const f = await fixture(t, { executive_delay_ms: 0 });
  assert.match(f.text(await f.call('ask_executive', { task: 'Research current weather.' })), /offline/);
  assert.match(f.text(await f.call('check_inbox')), /pending.*offline/);
  assert.equal(f.state().tickets[0].delivered, false);
});

test('explicit canned executive results are mocks and are delivered once', async (t) => {
  const f = await fixture(t, { executive_delay_ms: 0, executive_results: { weather: 'Sunny fixture.' } });
  await f.call('ask_executive', { task: 'Research weather' });
  const result = f.json(await f.call('check_inbox'));
  assert.equal(result.grounding, 'mock');
  assert.deepEqual(result.sources, []);
  assert.match(result.instruction, /not researched/);
  assert.equal(f.text(await f.call('check_inbox')), 'Inbox empty.');
});

test('real inbox provenance survives delivery and consumed ids survive a restart', async (t) => {
  const f = await fixture(t);
  await f.call('ask_executive', { task: 'Motor data' });
  const id = f.state().tickets[0].id;
  const sources = [{ title: 'Example data sheet', url: 'https://example.invalid/data', retrieved_at: '2026-09-06T00:00:00Z' }];
  fs.writeFileSync(path.join(f.runDir, 'inbox.jsonl'), JSON.stringify({ ticket_id: id, task: 'Motor data', result: 'Data sheet summary',
    grounding: 'fetched_sources', sources, coverage: { found: 1, fetched: 1, failed: 0 }, model: 'test-model', ts: '2026-09-06T00:00:01Z' }) + '\n');
  const receipt = f.json(await f.call('check_inbox'));
  assert.deepEqual(receipt.sources, sources);
  assert.equal(receipt.grounding, 'fetched_sources');
  assert.equal(receipt.coverage.fetched, 1);
  assert.equal(receipt.untrusted, true);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.runDir, 'inbox_consumed.json'), 'utf8')), [id]);
  const tools = new Map();
  const extension = await import(pathToFileURL(path.join(brainDir, 'extensions', 'robot-tools.ts')).href + `?restart=${++seq}`);
  extension.default({ registerTool: (tool) => tools.set(tool.name, tool) });
  assert.equal(f.text(await tools.get('check_inbox').execute('restart', {})), 'Inbox empty.');
});
