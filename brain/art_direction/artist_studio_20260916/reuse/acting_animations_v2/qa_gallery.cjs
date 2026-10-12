'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const runtime = require('./runtime.js');
const review = require('./review-state.js');
const originals = require('../acting_studies_v1/manifest.json');

// These records test UI clocks and controls; they are never emitted as artwork.
const fixture = {
  version: 2,
  groups: originals.groups.map(group => ({ ...group, examples: group.examples.map(example => ({
    ...example,
    width: 384, height: 342, key: `${group.id}/${example.id}`, restMs: 1000,
    frames: Array.from({ length: 12 }, (_, index) => ({ index, file: `${group.id}/${example.id}/${index}.png` })),
    poses: example.poses.map((pose, index) => ({ ...pose, file: `${group.id}/${example.id}/${[0, 7, 11][index]}.png` }))
  })) }))
};
const first = fixture.groups[0].examples[0];
const key = first.key;
const firstLabel = `${first.label}, ${fixture.groups[0].label}`;

async function boot({ reduced = false, saved = null, hash = '', denyStorage = false } = {}) {
  const nodes = [];
  const frames = [];
  const transitions = [];
  const pendingRaf = new Map();
  const documentEvents = new Map();
  const motionEvents = new Map();
  const storage = [];
  const blobs = [];
  let sequence = 0;
  let now = 0;
  class Node {
    constructor(tag = '') {
      this.tag = tag; this.children = []; this.events = new Map(); this.attributes = {}; this.dataset = {};
      this.value = ''; this.checked = false; this.hidden = false; this.open = false; this.disabled = false;
      this.textContent = ''; this.nextSibling = { textContent: '' }; this.classList = { toggle() {} };
      nodes.push(this);
    }
    addEventListener(type, callback) { this.events.set(type, [...(this.events.get(type) || []), callback]); }
    async dispatch(type, event = { target: this }) { for (const callback of this.events.get(type) || []) await callback(event); }
    append(...items) { this.children.push(...items); }
    replaceChildren(...items) { this.children = items; }
    setAttribute(name, value) { this.attributes[name] = value; }
    add(option) { this.children.push(option); if (this.value === '') this.value = option.value; }
    click() { return this.dispatch('click'); }
    showModal() { this.open = true; }
    async close() { this.open = false; await this.dispatch('close'); }
    querySelectorAll(tag) { return this.children.flatMap(child => child instanceof Node ? [...(child.tag === tag ? [child] : []), ...child.querySelectorAll(tag)] : []); }
    getContext() { return { canvas: this }; }
    remove() {}
    focus() {}
    select() {}
  }
  const ids = new Map();
  const id = name => { if (!ids.has(name)) { const node = new Node(); node.id = name; ids.set(name, node); } return ids.get(name); };
  id('filter').value = 'all'; id('fps').value = '15';
  id('transition-from').value = '0'; id('transition-to').value = '1';
  const location = { href: 'https://example.github.io/mist/acting-animations/' + hash, hash };
  const document = {
    hidden: false, body: new Node('body'), getElementById: id, createElement: tag => new Node(tag),
    addEventListener(type, callback) { documentEvents.set(type, callback); }
  };
  let observer;
  const motion = { matches: reduced, addEventListener(type, callback) { motionEvents.set(type, callback); } };
  const spyRuntime = {
    ...runtime,
    async preload() { return { images: new Map() }; },
    drawFrame(ctx, example, index, assets, options = {}) { frames.push({ canvas: ctx.canvas, key: example.key, index, options: structuredClone(options) }); },
    drawTransition(ctx, from, to, progress) { transitions.push({ from: from.key, to: to.key, progress }); }
  };
  const context = vm.createContext({
    document, location, Blob,
    URL: { createObjectURL(blob) { blobs.push(blob); return 'blob:test'; }, revokeObjectURL() {} },
    window: { MistReview: review, MistActing: spyRuntime, matchMedia: () => motion, addEventListener() {} },
    history: { replaceState(_state, _title, url) { location.href = url; location.hash = ''; } },
    localStorage: {
      getItem(name) { assert.equal(name, 'mist.acting-studies.v1.review'); if (denyStorage) throw new Error('Denied'); return saved; },
      setItem(name, value) { if (denyStorage) throw new Error('Denied'); storage.push({ name, value }); }
    },
    navigator: { clipboard: { async writeText() { throw new Error('Denied'); } } },
    fetch: async () => ({ ok: true, async json() { return fixture; } }),
    Option: function (label, value) { return { label, value }; },
    IntersectionObserver: class {
      constructor(callback) { observer = this; this.callback = callback; this.observed = []; }
      observe(node) { this.observed.push(node); }
    },
    requestAnimationFrame(callback) { const next = ++sequence; pendingRaf.set(next, callback); return next; },
    cancelAnimationFrame(handle) { pendingRaf.delete(handle); },
    console, setTimeout() {}
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(id('status').hidden, true);
  assert.equal(id('error').textContent, '');
  observer.callback(observer.observed.map(target => ({ target, isIntersecting: true })));
  const byLabel = label => nodes.find(node => node.attributes['aria-label'] === label);
  function step(delta = 1000 / 60) {
    now += delta;
    const callbacks = [...pendingRaf.values()];
    pendingRaf.clear();
    for (const callback of callbacks) callback(now);
  }
  function run(milliseconds) { for (let index = 0; index < Math.ceil(milliseconds / 10); index++) step(10); }
  function latestCard() { return frames.findLast(frame => frame.key === key && frame.canvas.id !== 'inspector-canvas'); }
  async function visibility(hidden) { document.hidden = hidden; await documentEvents.get('visibilitychange')(); }
  return { id, byLabel, nodes, frames, transitions, storage, blobs, location, motion, pendingRaf, step, run, latestCard, visibility, motionEvents };
}

test('old saved selections and conceptual pose IDs restore and export against animation assets', async () => {
  const previous = review.envelope([{ id: key, selected: true, note: 'Keep the gentle eyes. 👀', poses: [0, 2] }]);
  const app = await boot({ saved: JSON.stringify(previous) });
  assert.equal(app.byLabel(`Animate this: ${firstLabel}`).checked, true);
  assert.equal(app.byLabel(`Keep Setup: ${firstLabel}`).checked, true);
  assert.equal(app.byLabel(`Keep Settle: ${firstLabel}`).checked, true);
  assert.equal(app.byLabel(`Keep Change: ${firstLabel}`).checked, false);
  await app.id('export-json').click();
  const exported = JSON.parse(await app.blobs[0].text());
  assert.deepEqual(review.parse(JSON.stringify(exported), originals), previous);
  assert.deepEqual(exported.entries[0].selectedPoses.map(pose => pose.file), [first.poses[0].file, first.poses[2].file]);
});

test('reduced motion starts paused; explicit Play all moves, Pause freezes, resume preserves position', async () => {
  const app = await boot({ reduced: true });
  assert.equal(app.pendingRaf.size, 0);
  assert.equal(app.latestCard().index, 0);
  assert.equal(app.id('play-all').disabled, false);
  await app.id('play-all').click();
  app.run(250);
  assert.ok(app.latestCard().index > 0);
  await app.id('pause-all').click();
  const frame = app.latestCard().index;
  app.run(1000);
  assert.equal(app.latestCard().index, frame);
  await app.id('play-all').click();
  app.step();
  assert.equal(app.latestCard().index, frame);
  app.run(150);
  assert.notEqual(app.latestCard().index, frame);
});

test('inspector scrubbing pauses playback without modifying conceptual pose choices; layers and mouth isolate', async () => {
  const app = await boot();
  await app.byLabel(`Inspect: ${firstLabel}`).click();
  app.id('inspector-frame').value = '8';
  await app.id('inspector-frame').dispatch('input');
  const inspectorDraws = () => app.frames.filter(frame => frame.canvas.id === 'inspector-canvas');
  assert.equal(inspectorDraws().at(-1).index, 8);
  assert.equal(app.id('inspector-play').disabled, false);
  app.run(500);
  assert.equal(inspectorDraws().at(-1).index, 8);
  assert.equal(app.byLabel(`Keep Change: ${firstLabel}`).checked, false);
  app.id('layer-leftEye').checked = false;
  await app.id('layer-leftEye').dispatch('change');
  assert.deepEqual(Array.from(inspectorDraws().at(-1).options.layers), ['rightEye', 'mouth']);
  app.id('mouth-independent').checked = true;
  await app.id('mouth-independent').dispatch('change');
  app.id('mouth-frame').value = '2';
  await app.id('mouth-frame').dispatch('input');
  assert.equal(inspectorDraws().at(-1).options.mouthFrame, 2);
  await app.id('inspector-next').click();
  assert.equal(inspectorDraws().at(-1).index, 9);
  assert.equal(inspectorDraws().at(-1).options.mouthFrame, 2);
  await app.id('inspector').close();
  assert.equal(app.id('inspector').open, false);
});

test('hidden document stops rendering and resumes without elapsed background time', async () => {
  const app = await boot();
  app.run(250);
  const previous = app.latestCard().index;
  await app.visibility(true);
  assert.equal(app.pendingRaf.size, 0);
  const count = app.frames.length;
  app.run(15000);
  assert.equal(app.frames.length, count);
  await app.visibility(false);
  app.step();
  assert.equal(app.latestCard().index, previous);
  app.run(150);
  assert.notEqual(app.latestCard().index, previous);
});

test('transition scrub has exactly 12 accessible steps and pauses playback', async () => {
  const app = await boot({ reduced: true });
  app.id('transitions').open = true;
  await app.id('transitions').dispatch('toggle');
  for (let index = 0; index < 12; index++) {
    app.id('transition-frame').value = String(index);
    await app.id('transition-frame').dispatch('input');
    assert.equal(runtime.stepAtProgress(app.transitions.at(-1).progress), index);
  }
  assert.equal(app.id('transition-position').textContent, '12 / 12');
  assert.equal(app.id('transition-pause').disabled, true);
  assert.equal(app.pendingRaf.size, 0);
});

test('changing FPS during a later rest interval preserves rest rather than jumping into an acting beat', async () => {
  const app = await boot();
  app.step(0);
  app.run(1700);
  assert.equal(app.latestCard().index, 0);
  await app.id('pause-all').click();
  app.id('fps').value = '8';
  await app.id('fps').dispatch('change');
  assert.equal(app.latestCard().index, 0, 'Speed changes must not move a paused resting face to a different drawing');
});

test('review imports retain existing notes and choices in the animation gallery', async () => {
  const previous = review.envelope([{ id: key, selected: false, note: 'Original reason.', poses: [0] }]);
  const app = await boot({ saved: JSON.stringify(previous), denyStorage: false });
  const incoming = JSON.stringify(review.envelope([{ id: key, selected: true, note: 'Also the mouth.', poses: [2] }]));
  const file = { size: Buffer.byteLength(incoming), async text() { return incoming; } };
  await app.id('import-file').dispatch('change', { target: { files: [file], value: 'file' } });
  assert.equal(app.byLabel(`Animate this: ${firstLabel}`).checked, true);
  assert.equal(app.byLabel(`What should we keep or change? ${firstLabel}`).value, 'Original reason.\n\nImported note:\nAlso the mouth.');
  assert.equal(app.byLabel(`Keep Setup: ${firstLabel}`).checked, true);
  assert.equal(app.byLabel(`Keep Settle: ${firstLabel}`).checked, true);
});

test('Grid and Review reuse the same edited controls without resetting saved choices or notes', async () => {
  const app = await boot();
  const note = app.byLabel(`What should we keep or change? ${firstLabel}`);
  const choose = app.byLabel(`Animate this: ${firstLabel}`);
  note.value = 'Keep this slower blink.';
  await note.dispatch('input');
  choose.checked = true;
  await choose.dispatch('change');
  await app.id('view-review').click();
  assert.equal(app.id('view-review').attributes['aria-pressed'], 'true');
  await app.id('view-grid').click();
  assert.equal(app.id('view-grid').attributes['aria-pressed'], 'true');
  assert.equal(app.id('view-review').attributes['aria-pressed'], 'false');
  assert.equal(app.byLabel(`What should we keep or change? ${firstLabel}`), note);
  assert.equal(app.byLabel(`Animate this: ${firstLabel}`), choose);
  assert.equal(note.value, 'Keep this slower blink.');
  assert.equal(choose.checked, true);
  await app.id('export-json').click();
  assert.equal(JSON.parse(await app.blobs[0].text()).entries[0].note, note.value);
});

test('repeated FPS changes keep the paused frame stable in active and rest phases across later loops', async () => {
  const app = await boot();
  app.step(0);
  for (const interval of [240, 650, 1700, 2100]) {
    app.run(interval);
    await app.id('pause-all').click();
    const previous = app.latestCard().index;
    for (const speed of ['8', '12', '15']) {
      app.id('fps').value = speed;
      await app.id('fps').dispatch('change');
      assert.equal(app.latestCard().index, previous, `Frame must remain ${previous} when changing to ${speed} fps`);
    }
    await app.id('play-all').click();
  }
});

const compiled = JSON.parse(fs.readFileSync(path.join(__dirname, 'manifest.json'), 'utf8'));
test('compiled manifest preserves every legacy review ID and distinct conceptual pose mapping', {
  skip: compiled.complete === false ? 'Generated artwork compilation is incomplete.' : false
}, () => {
  const originalCatalog = review.catalog(originals);
  const compiledCatalog = review.catalog(compiled);
  assert.deepEqual([...compiledCatalog.keys()].sort(), [...originalCatalog.keys()].sort());
  for (const [id, { example }] of compiledCatalog) {
    assert.equal(example.key, id);
    assert.deepEqual(example.poses.map(pose => pose.label), ['Setup', 'Change', 'Settle']);
    assert.equal(new Set(example.poses.map(pose => pose.file)).size, 3);
    for (const pose of example.poses) {
      assert.ok(example.frames.some(frame => frame.file === pose.file), `${id}: conceptual pose points to a current frame`);
      assert.ok(fs.existsSync(path.join(__dirname, pose.file)));
    }
  }
});
