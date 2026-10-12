'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const runtime = require('./runtime.js');
const review = require('./review-state.js');
const html = fs.readFileSync(__dirname + '/index.html', 'utf8');
const source = fs.readFileSync(__dirname + '/app.js', 'utf8');

// A small DOM harness drives the actual event handlers; rendering is tested separately.
async function openGallery({ reduced = false, saved = null, badTiming = false } = {}) {
  const nodes = new Map(), all = [], queued = new Map(), storage = new Map();
  const calls = [];
  let rafId = 0;
  let playbackNow = 0;
  if (saved) storage.set('mist.acting-studies.v1.review', JSON.stringify(saved));
  class Element {
    constructor(tag) {
      this.tagName = tag; this.children = []; this.events = {}; this.attributes = {};
      this.dataset = {}; this.value = ''; this.textContent = ''; this.hidden = false;
      this.disabled = false; this.checked = false; this.open = false;
      this.nextSibling = { textContent: '' };
      const classes = new Set();
      this.classList = { toggle: (name, force) => {
        const enabled = force ?? !classes.has(name);
        if (enabled) classes.add(name); else classes.delete(name);
        return enabled;
      }, contains: name => classes.has(name) };
      all.push(this);
    }
    setAttribute(name, value) { this.attributes[name] = value; }
    getAttribute(name) { return this.attributes[name]; }
    addEventListener(name, fn) { (this.events[name] ||= []).push(fn); }
    async dispatch(name) { for (const fn of this.events[name] || []) await fn({ target: this }); }
    click() { return this.dispatch('click'); }
    append(...items) { this.children.push(...items); }
    add(option) { this.children.push(option); }
    replaceChildren(...items) { this.children = items; }
    querySelectorAll(tag) {
      return this.children.flatMap(item => typeof item === 'object' ? [
        ...(item.tagName === tag ? [item] : []), ...(item.querySelectorAll?.(tag) || [])
      ] : []);
    }
    focus() { this.focused = true; }
    select() {}
    remove() {}
    getContext() { return { canvas: this }; }
    showModal() { this.open = true; }
    close() { this.open = false; return this.dispatch('close'); }
  }
  for (const match of html.matchAll(/<([a-z][a-z0-9]*)\b([^>]*\bid="([^"]+)"[^>]*)>/g)) {
    const node = new Element(match[1]);
    node.id = match[3]; node.hidden = /\bhidden\b/.test(match[2]);
    node.checked = /\bchecked\b/.test(match[2]); node.disabled = /\bdisabled\b/.test(match[2]);
    node.value = match[2].match(/\bvalue="([^"]*)"/)?.[1] || '';
    nodes.set(node.id, node);
  }
  nodes.get('fps').value = nodes.get('inspector-speed').value = '15';
  nodes.get('filter').value = 'all';
  const fixture = id => ({
    id, label: id, key: `aardman/${id}`, width: 512, height: 320, restMs: 500,
    poses: [{ label: 'Setup' }, { label: 'Change' }, { label: 'Settle' }],
    frames: [3, 1, 2, 1, 1, 4, 4, 2, 1, 1, 2, 3].map((ticks, index) => ({
      index, durationMs: ticks * 1000 / 15, exposureTicks: ticks, file: `${id}/${index}.png`
    })),
    blinkFrames: Array.from({ length: 7 }, (_, index) => ({ index, durationMs: 1000 / 15 }))
  });
  const examples = [fixture('listening'), fixture('disbelief')];
  if (badTiming) delete examples[0].frames[1].durationMs;
  const manifest = { version: 3, groups: [{ id: 'aardman', label: 'Aardman', examples }] };
  const fakeRuntime = {
    ...runtime, preload: async () => ({}),
    frameAt(ms, example, fps) { calls.push({ type: 'clock', ms, example, fps }); return runtime.frameAt(ms, example, fps); },
    drawFrame(ctx, example, index, assets, options = {}) { calls.push({ type: 'frame', at: playbackNow, ctx, example, index, options }); },
    drawBlink(ctx, example, index, assets, options = {}) { calls.push({ type: 'blink', at: playbackNow, ctx, example, index, options }); },
    drawTransition(ctx, from, to, progress) { calls.push({ type: 'transition', ctx, from, to, progress }); }
  };
  const media = { matches: reduced, addEventListener() {} };
  const sandbox = {
    window: { MistReview: review, MistActing: fakeRuntime, matchMedia: () => media, addEventListener() {} },
    document: { body: new Element('body'), hidden: false, getElementById: id => nodes.get(id), createElement: tag => new Element(tag), addEventListener() {} },
    location: { href: 'https://example.test/acting-animations/', hash: '' }, history: { replaceState() {} },
    localStorage: { getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value) },
    navigator: { clipboard: { writeText: async () => {} } },
    IntersectionObserver: class { constructor(callback) { this.callback = callback; } observe(target) { this.callback([{ target, isIntersecting: true }]); } },
    Option: class extends Element { constructor(text, value) { super('option'); this.textContent = text; this.value = value; } },
    fetch: async () => ({ ok: true, json: async () => manifest }),
    requestAnimationFrame: fn => { queued.set(++rafId, fn); return rafId; },
    cancelAnimationFrame: id => queued.delete(id),
    console: { error: (...args) => calls.push({ type: 'error', args }) },
    URL: { createObjectURL: () => 'blob:test', revokeObjectURL() {} }, Blob, setTimeout
  };
  vm.runInNewContext(source, sandbox);
  await new Promise(resolve => setImmediate(resolve));
  const el = id => nodes.get(id);
  const change = async (id, value, event = 'change') => { el(id).value = String(value); await el(id).dispatch(event); };
  const advance = now => { playbackNow = now; const callbacks = [...queued.values()]; queued.clear(); callbacks.forEach(callback => callback(now)); };
  const inspect = () => all.find(node => node.attributes['aria-label']?.startsWith('Inspect:'))?.click();
  return { el, change, advance, inspect, calls, all, storage, examples, manifest };
}

test('gallery restores prior review IDs, starts at actual timing and preserves notes', async () => {
  const saved = { schema: 'mist-acting-review', version: 1, studyId: 'acting_studies_v1', entries: [
    { id: 'aardman/listening', selected: true, note: 'Keep the eyes', poses: [1] }
  ] };
  const page = await openGallery({ saved });
  assert.equal(page.el('fps').value, '15');
  assert.equal(page.el('error').hidden, true);
  assert.match(page.el('selected-count').textContent, /1 selected/);
  assert.equal(page.all.find(node => node.tagName === 'textarea').value, 'Keep the eyes');
  assert.equal(page.all.find(node => node.attributes['aria-label']?.startsWith('Keep this:')).checked, true);
  assert.match(page.el('study-count').textContent, /12 poses · 15 fps timing · layered/);
});

test('scrub then play resumes from authored pose start rather than index times one tick', async () => {
  const page = await openGallery();
  await page.inspect();
  await page.change('inspector-frame', 7, 'input');
  assert.match(page.el('pose-duration').textContent, /2 ticks · 133 ms/);
  await page.el('inspector-play').click();
  page.advance(0);
  const clock = page.calls.filter(call => call.type === 'clock').at(-1);
  assert.ok(Math.abs(clock.ms - runtime.frameStartMs(page.examples[0], 7)) < .001);
  assert.equal(page.el('inspector-position').textContent, '8 / 12');
  page.advance(100);
  assert.equal(page.el('inspector-position').textContent, '8 / 12');
});

test('half speed preserves the selected pose and independent mouth frame', async () => {
  const page = await openGallery();
  await page.inspect();
  await page.change('inspector-frame', 7, 'input');
  page.el('mouth-independent').checked = true;
  await page.el('mouth-independent').dispatch('change');
  await page.change('mouth-frame', 10, 'input');
  await page.change('inspector-speed', 7.5);
  assert.equal(page.el('fps').value, '7.5');
  assert.match(page.el('pose-duration').textContent, /267 ms at ½ speed/);
  await page.el('inspector-play').click();
  page.advance(0);
  const clock = page.calls.filter(call => call.type === 'clock').at(-1);
  assert.equal(clock.fps, 7.5);
  assert.ok(Math.abs(clock.ms - runtime.frameStartMs(page.examples[0], 7, 7.5)) < .001);
  assert.equal(page.calls.filter(call => call.type === 'frame').at(-1).options.mouthFrame, 10);
});

test('separate blink plays once, preserves the chosen mouth, and action returns to its pose', async () => {
  const page = await openGallery();
  await page.inspect();
  await page.change('inspector-frame', 8, 'input');
  assert.equal(page.el('blink-controls').hidden, false);
  await page.el('inspector-blink').click();
  page.advance(0);
  for (let now = 100; now <= 600; now += 100) page.advance(now);
  const lastBlink = page.calls.filter(call => call.type === 'blink').at(-1);
  assert.equal(lastBlink.index, 6);
  assert.equal(lastBlink.options.mouthFrame, 8);
  assert.equal(page.el('blink-status').textContent, 'Blink finished');
  assert.equal(page.el('download-frame').hidden, true);
  await page.el('blink-back').click();
  assert.equal(page.calls.filter(call => call.type === 'frame').at(-1).index, 8);
  assert.equal(page.el('download-frame').hidden, false);
});

test('blink scrub and pause are independent from action and obey layer toggles', async () => {
  const page = await openGallery();
  await page.inspect();
  page.el('layer-rightEye').checked = false;
  await page.el('layer-rightEye').dispatch('change');
  await page.change('blink-progress', 3, 'input');
  const blink = page.calls.filter(call => call.type === 'blink').at(-1);
  assert.equal(blink.index, 3);
  assert.deepEqual(Array.from(blink.options.layers), ['leftEye', 'mouth']);
  assert.equal(page.el('blink-position').textContent, '4 / 7');
  assert.equal(page.el('inspector-play').disabled, false);
});

test('reduced motion starts paused and explicit Play still works', async () => {
  const page = await openGallery({ reduced: true });
  assert.equal(page.el('play-all').disabled, false);
  assert.match(page.el('playback-status').textContent, /reduced motion/);
  await page.el('play-all').click();
  assert.equal(page.el('playback-status').textContent, 'Playing');
  page.advance(0); page.advance(100);
  assert.ok(page.calls.some(call => call.type === 'clock' && call.ms === 100));
});

test('grid blinks occur only inside neutral rest, stagger across cycles, and respect pause and toggle', async () => {
  const page = await openGallery();
  assert.equal(page.el('grid-blinks').checked, true);
  page.advance(0);
  for (let now = 50; now <= 8800; now += 50) page.advance(now);
  const blinks = page.calls.filter(call => call.type === 'blink');
  assert.ok(blinks.length > 10);
  assert.equal(new Set(blinks.map(call => call.example.id)).size, 2);
  for (const call of blinks) {
    const clock = runtime.timeline(call.example);
    const phase = call.at % clock.totalMs;
    assert.ok(phase >= clock.activeMs, `Blink interrupted active pose at ${call.at}`);
    assert.ok(phase < clock.totalMs);
    assert.equal(call.options.mouthFrame, 0);
    const expectedParity = call.example.id === 'listening' ? 0 : 1;
    assert.equal(Math.floor(call.at / clock.totalMs) % 2, expectedParity);
  }
  await page.el('pause-all').click();
  const beforePause = page.calls.length;
  page.advance(8850);
  assert.equal(page.calls.length, beforePause);
  page.el('grid-blinks').checked = false;
  await page.el('grid-blinks').dispatch('change');
  await page.el('play-all').click();
  const beforeResume = page.calls.filter(call => call.type === 'blink').length;
  for (let now = 8900; now <= 13000; now += 50) page.advance(now);
  assert.equal(page.calls.filter(call => call.type === 'blink').length, beforeResume);
});

test('grid never truncates a slow blink that cannot fit the available rest', async () => {
  const page = await openGallery();
  await page.change('fps', 7.5);
  page.advance(0);
  for (let now = 50; now <= 6000; now += 50) page.advance(now);
  assert.equal(page.calls.filter(call => call.type === 'blink').length, 0);
});

test('missing authored durations fail visibly rather than using misleading default timing', async () => {
  const page = await openGallery({ badTiming: true });
  assert.equal(page.el('error').hidden, false);
  assert.equal(page.el('play-all').disabled, true);
  assert.match(page.calls.find(call => call.type === 'error').args[1].message, /Incomplete animation/);
});

test('speed changes retain position in the unscaled rest after an acting cycle', async () => {
  const page = await openGallery();
  const active = runtime.timeline(page.examples[0]).activeMs;
  page.advance(0);
  const elapsed = Math.ceil(active / 100) * 100 + 100;
  for (let now = 100; now <= elapsed; now += 100) page.advance(now);
  assert.ok(elapsed > active && elapsed < active + 500);
  await page.change('fps', 7.5);
  const clock = page.calls.filter(call => call.type === 'clock').at(-1);
  assert.ok(Math.abs(clock.ms - (active * 2 + elapsed - active)) < .001);
  assert.equal(runtime.frameAt(clock.ms, page.examples[0], clock.fps), 0);
});

test('transition scrub stops auto playback and sends exact source and target endpoints', async () => {
  const page = await openGallery();
  page.el('transitions').open = true;
  await page.el('transitions').dispatch('toggle');
  await page.change('transition-frame', 11, 'input');
  let transition = page.calls.filter(call => call.type === 'transition').at(-1);
  assert.equal(transition.progress, 1);
  assert.equal(transition.from.id, 'listening');
  assert.equal(transition.to.id, 'disbelief');
  await page.change('transition-frame', 0, 'input');
  transition = page.calls.filter(call => call.type === 'transition').at(-1);
  assert.equal(transition.progress, 0);
  assert.equal(page.el('transition-auto').checked, false);
});

test('public navigation and pack filename target corrected version and retained history', () => {
  assert.match(html, /href="MIST_motion_v3\.zip"/);
  assert.match(html, /href="\.\.\/acting-animations-v2\/"/);
  assert.match(html, /src="runtime\.js\?v=3"/);
  assert.doesNotMatch(html, /216.*generated|unique.*drawings/i);
});
