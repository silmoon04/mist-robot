const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const review = require('./review-state.js');
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'manifest.json'), 'utf8'));
const known = [...review.catalog(manifest)];
const first = known[0][0];
const second = known[1][0];
const entry = (overrides = {}) => ({ id: first, selected: true, note: '', poses: [0, 2], ...overrides });
const documentFor = (...entries) => review.envelope(entries);
const parse = value => review.parse(JSON.stringify(value), manifest);
const sampleNote = 'The eyelids feel kind, not sad.\n中文 / العربية / café / 👀✨\n<script>alert("x")</script> [bad](javascript:alert(1)) `code`';

test('all 18 example identities and all 54 pose references survive a JSON review roundtrip', () => {
  assert.equal(known.length, 18);
  const entries = known.map(([id, { example }], index) => entry({ id, selected: index % 2 === 0, note: sampleNote + index, poses: example.poses.map((_, poseIndex) => poseIndex) }));
  const input = documentFor(...entries);
  assert.deepEqual(review.fromState(review.toState(parse(input))), input);
  assert.equal(entries.reduce((count, value) => count + value.poses.length, 0), 54);
});

test('notes-only and individual-pose reviews survive without forcing sequence selection', () => {
  const input = documentFor(entry({ selected: false, poses: [], note: sampleNote }), entry({ id: second, selected: false, note: '', poses: [1] }));
  const result = review.fromState(review.toState(parse(input)));
  assert.deepEqual(result, input);
  assert.equal(review.hasSelection(result.entries[0]), false);
  assert.equal(review.hasSelection(result.entries[1]), true);
});

test('empty entries are omitted without dropping genuine notes', () => {
  const state = new Map([[first, { selected: false, poses: [], note: '  \n' }], [second, { selected: false, poses: [], note: 'Keep this pause.' }]]);
  assert.deepEqual(review.fromState(state).entries.map(value => value.id), [second]);
});

test('schema, version, study, entry list and JSON shape are enforced', () => {
  for (const invalid of [null, [], {}, { ...documentFor(), schema: 'other' }, { ...documentFor(), version: 2 }, { ...documentFor(), studyId: 'other' }, { ...documentFor(), entries: {} }]) assert.throws(() => parse(invalid));
  assert.throws(() => review.parse('{broken', manifest), /valid JSON/);
});

test('unknown and duplicate identities are rejected', () => {
  for (const id of ['unknown/face', '__proto__', 'constructor', 'aardman/../../secret']) assert.throws(() => parse(documentFor(entry({ id }))));
  assert.throws(() => parse(documentFor(entry(), entry())), /repeated/);
});

test('prototype-related keys are rejected even when nested in ignored metadata', () => {
  for (const forbidden of ['__proto__', 'constructor', 'prototype']) {
    const input = documentFor(entry());
    input.metadata = JSON.parse(`{"nested":{"${forbidden}":{"polluted":true}}}`);
    assert.throws(() => parse(input), /unsupported|prototype|unsafe|key|format/i);
  }
  assert.equal({}.polluted, undefined);
});

test('selection and note values require exact types', () => {
  for (const selected of [1, 'true', null, {}, []]) assert.throws(() => parse(documentFor(entry({ selected }))));
  for (const note of [1, null, {}, []]) assert.throws(() => parse(documentFor(entry({ note }))));
});

test('pose indices must be unique integers in this example', () => {
  for (const poses of [[-1], [3], [0.5], ['1'], [null], [0, 0], [0, 1, 2, 3], {}, null]) assert.throws(() => parse(documentFor(entry({ poses }))));
  assert.deepEqual(parse(documentFor(entry({ poses: [2, 0, 1] }))).entries[0].poses, [0, 1, 2]);
});

test('note and file limits accept the boundary and reject oversize', () => {
  assert.equal(parse(documentFor(entry({ note: 'x'.repeat(review.MAX_NOTE) }))).entries[0].note.length, review.MAX_NOTE);
  assert.throws(() => parse(documentFor(entry({ note: 'x'.repeat(review.MAX_NOTE + 1) }))));
  assert.throws(() => review.parse(' '.repeat(review.MAX_FILE + 1), manifest), /large/);
});

test('merge preserves both conflicting notes and unions selections and poses', () => {
  const original = review.toState(parse(documentFor(entry({ selected: false, poses: [0], note: 'Keep the gaze.' }))));
  const before = JSON.stringify(review.fromState(original));
  const incoming = parse(documentFor(entry({ poses: [2], note: 'Slow the final blink.' }), entry({ id: second, poses: [1], note: 'This one too.' })));
  const merged = review.merge(original, incoming);
  assert.deepEqual(merged.get(first), { selected: true, poses: [0, 2], note: 'Keep the gaze.\n\nImported note:\nSlow the final blink.' });
  assert.equal(merged.get(second).note, 'This one too.');
  assert.equal(JSON.stringify(review.fromState(original)), before);
  assert.deepEqual(review.merge(merged, incoming), merged);
});

test('failed oversized note merge leaves every original entry and incoming record unchanged', () => {
  const original = review.toState(parse(documentFor(entry({ note: 'a'.repeat(review.MAX_NOTE) }))));
  const incoming = parse(documentFor(entry({ id: second, note: 'Valid first record.' }), entry({ note: 'A conflicting note.' })));
  const originalBefore = JSON.stringify(review.fromState(original));
  const incomingBefore = JSON.stringify(incoming);
  assert.throws(() => review.merge(original, incoming), /not changed/);
  assert.equal(JSON.stringify(review.fromState(original)), originalBefore);
  assert.equal(JSON.stringify(incoming), incomingBefore);
});

test('state conversion, validation and merge do not retain mutable input pose arrays', () => {
  const input = documentFor(entry());
  const validated = review.validate(input, manifest);
  input.entries[0].poses.push(1);
  assert.deepEqual(validated.entries[0].poses, [0, 2]);
  const state = review.toState(validated);
  validated.entries[0].poses.push(1);
  assert.deepEqual(state.get(first).poses, [0, 2]);
  const exported = review.fromState(state);
  exported.entries[0].poses.push(1);
  assert.deepEqual(state.get(first).poses, [0, 2]);
});

test('exports resolve only selected canonical pose paths under the deployed project subpath', () => {
  const state = review.toState(parse(documentFor(entry({ note: sampleNote }))));
  const pageUrl = 'https://example.github.io/mist-review/';
  const exported = review.exportReview(state, manifest, pageUrl);
  const output = exported.entries[0];
  assert.equal(output.id, first);
  assert.equal(output.note, sampleNote);
  assert.equal(output.selectedPoses.length, 2);
  assert.deepEqual(output.selectedPoses.map(pose => pose.index), [0, 2]);
  for (const pose of output.selectedPoses) {
    assert.equal(pose.url, new URL(pose.file, pageUrl).href);
    assert.ok(pose.url.startsWith(pageUrl + 'poses/'));
  }
  assert.deepEqual(review.fromState(review.toState(parse(exported))), review.fromState(state));
});

test('Markdown notes remain quoted text and do not become HTML or injected link labels', () => {
  const state = review.toState(parse(documentFor(entry({ note: sampleNote }))));
  const exported = review.exportReview(state, manifest, 'https://example.github.io/mist-review/');
  const markdown = review.markdown(exported);
  assert.ok(markdown.includes('中文 / العربية / café / 👀✨'));
  assert.ok(!markdown.includes('<script>'));
  assert.ok(!markdown.includes('[bad]('));
  assert.ok(markdown.includes('> \\<script\\>'));
  assert.ok(markdown.includes(exported.entries[0].selectedPoses[0].url));
});

test('Unicode, line breaks and punctuation survive shared links without leaking notes into query parameters', () => {
  const state = review.toState(parse(documentFor(entry({ note: sampleNote }))));
  const url = new URL(review.shareLink(state, 'https://example.github.io/mist-review/#old'));
  assert.equal(url.search, '');
  assert.ok(url.hash.startsWith('#review='));
  assert.deepEqual(review.parseShare(url.hash, manifest), review.fromState(state));
});

test('damaged, unknown and oversized link payloads fail explicitly', () => {
  for (const hash of ['', '#anything', '#review=%xx', '#review=' + encodeURIComponent('{broken'), '#review=' + encodeURIComponent(JSON.stringify(documentFor(entry({ id: 'wrong' }))))]) assert.throws(() => review.parseShare(hash, manifest));
  assert.throws(() => review.parseShare('#review=' + 'a'.repeat(review.MAX_LINK), manifest), /too long/);
  const state = review.toState(parse(documentFor(entry({ note: '👀'.repeat(4000) }))));
  assert.throws(() => review.shareLink(state, 'https://example.github.io/mist-review/'), /too long/);
});

test('deep ignored metadata fails without stack exhaustion', () => {
  const input = documentFor(entry());
  let cursor = input;
  for (let index = 0; index < 25; index++) cursor = cursor.metadata = {};
  assert.throws(() => review.validate(input, manifest), /structure/);
});

test('a full review with maximum-length Unicode notes stays importable by the file byte limit', () => {
  for (const character of ['界', '\u0001']) {
    const fullReview = documentFor(...known.map(([id]) => entry({ id, note: character.repeat(review.MAX_NOTE) })));
    const state = review.toState(review.validate(fullReview, manifest));
    const exported = JSON.stringify(review.exportReview(state, manifest, 'https://example.github.io/mist-review/'), null, 2);
    assert.ok(Buffer.byteLength(exported, 'utf8') <= review.MAX_FILE, 'The UI file-size guard must accept every review its own editor can export');
    assert.equal(review.parse(exported, manifest).entries.length, 18);
  }
});

async function bootApp({ getItem = () => null, setItem = () => {}, hash = '' } = {}) {
  const allNodes = [];
  class Node {
    constructor(tag = '') {
      this.tag = tag; this.children = []; this.events = new Map(); this.attributes = {};
      this.value = ''; this.checked = false; this.hidden = false; this.textContent = '';
      this.classList = { toggle() {} };
      allNodes.push(this);
    }
    addEventListener(type, callback) { this.events.set(type, [...(this.events.get(type) || []), callback]); }
    async dispatch(type, event = { target: this }) { for (const callback of this.events.get(type) || []) await callback(event); }
    append(...nodes) { this.children.push(...nodes); }
    replaceChildren(...nodes) { this.children = nodes; }
    setAttribute(name, value) { this.attributes[name] = value; }
    add(value) { this.children.push(value); }
    click() { return this.dispatch('click'); }
    remove() {}
    focus() {}
    select() {}
  }
  const ids = new Map();
  const byId = id => { if (!ids.has(id)) ids.set(id, new Node()); return ids.get(id); };
  byId('filter').value = 'all';
  const blobs = [];
  const pageUrl = 'https://example.github.io/mist-review/';
  const location = { href: pageUrl + hash, hash };
  const document = { body: new Node('body'), getElementById: byId, createElement: tag => new Node(tag), addEventListener() {} };
  const context = vm.createContext({
    document, location, Blob,
    URL: { createObjectURL(blob) { blobs.push(blob); return 'blob:test'; }, revokeObjectURL() {} },
    window: { MistReview: review, matchMedia: () => ({ matches: false, addEventListener() {} }), addEventListener() {}, clearTimeout() {}, setTimeout() {} },
    history: { replaceState(_state, _title, url) { location.href = url; location.hash = ''; } },
    localStorage: { getItem, setItem },
    navigator: { clipboard: { async writeText() { throw new Error('Clipboard denied'); } } },
    fetch: async () => ({ ok: true, async json() { return manifest; } }),
    Option: function (label, value) { return { label, value }; },
    console, setTimeout() {}
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(byId('filter').disabled, false, 'App reached ready state');
  const byLabel = label => allNodes.find(node => node.attributes['aria-label'] === label);
  return { byId, byLabel, blobs, location };
}

test('denied browser storage keeps edited choices and notes available for JSON export and copied-link fallback', async () => {
  const app = await bootApp({ getItem() { throw new Error('SecurityError'); }, setItem() { throw new Error('QuotaExceededError'); } });
  const label = `${known[0][1].example.label}, ${known[0][1].group.label}`;
  const choose = app.byLabel(`Animate this: ${label}`);
  choose.checked = true;
  await choose.dispatch('change');
  const note = app.byLabel(`What should we keep or change? ${label}`);
  note.value = sampleNote;
  await note.dispatch('input');
  const pose = app.byLabel(`Keep Change: ${label}`);
  pose.checked = true;
  await pose.dispatch('change');
  assert.match(app.byId('save-status').textContent, /unavailable/);
  await app.byId('export-json').click();
  const exported = JSON.parse(await app.blobs[0].text());
  assert.equal(exported.entries[0].selected, true);
  assert.equal(exported.entries[0].note, sampleNote);
  assert.deepEqual(exported.entries[0].poses, [1]);
  await app.byId('copy-review').click();
  assert.equal(app.byId('share-fallback').hidden, false);
  assert.equal(review.parseShare(new URL(app.byId('share-url').value).hash, manifest).entries[0].note, sampleNote);
});

test('unreadable existing storage is not overwritten by new edits', async () => {
  let writes = 0;
  const app = await bootApp({ getItem: () => '{broken', setItem() { writes++; } });
  const label = `${known[0][1].example.label}, ${known[0][1].group.label}`;
  const note = app.byLabel(`What should we keep or change? ${label}`);
  note.value = 'New review is still exportable.';
  await note.dispatch('input');
  await app.byId('export-json').click();
  assert.equal(writes, 0);
  assert.match(app.byId('save-status').textContent, /could not be read/);
  assert.equal(JSON.parse(await app.blobs[0].text()).entries[0].note, note.value);
});

test('startup merges shared and saved review notes, restores controls, and removes the fragment', async () => {
  const saved = documentFor(entry({ selected: false, poses: [0], note: 'Local reason.' }));
  const shared = review.shareLink(review.toState(documentFor(entry({ poses: [2], note: sampleNote }))), 'https://example.github.io/mist-review/');
  const app = await bootApp({ getItem: () => JSON.stringify(saved), hash: new URL(shared).hash });
  const label = `${known[0][1].example.label}, ${known[0][1].group.label}`;
  assert.equal(app.byLabel(`Animate this: ${label}`).checked, true);
  assert.equal(app.byLabel(`Keep Setup: ${label}`).checked, true);
  assert.equal(app.byLabel(`Keep Settle: ${label}`).checked, true);
  assert.equal(app.byLabel(`What should we keep or change? ${label}`).value, 'Local reason.\n\nImported note:\n' + sampleNote);
  assert.equal(app.location.hash, '');
});
