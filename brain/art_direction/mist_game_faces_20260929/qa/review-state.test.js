'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../board/review-state.js'), 'utf8');
const KEY = 'mist.generated-game-faces.20260929.v1';
const SCHEMA = 'mist-generated-game-faces-review';
const clone = value => JSON.parse(JSON.stringify(value));

function load(initial = {}, options = {}) {
  const values = options.sharedValues || new Map(Object.entries(initial));
  const failures = { read: Boolean(options.readFailure), write: Boolean(options.writeFailure) };
  const writes = [];
  const storage = {
    getItem(key) {
      if (failures.read) throw new Error('Storage read denied');
      return values.get(key) || null;
    },
    setItem(key, value) {
      if (failures.write) throw new Error('Storage write denied');
      writes.push({ key, value });
      values.set(key, value);
    }
  };
  const context = vm.createContext(options.noStorage ? {} : { localStorage: storage });
  vm.runInContext(source, context, { filename: 'review-state.js' });
  return { api: context.MistFaceReview, context, failures, values, writes };
}

function face(id, extra = {}) {
  return {
    id,
    studyId: 'study-a',
    displayTitle: 'A source study',
    poseLabel: 'Attentive welcome',
    category: 'Graphic acting',
    approach: 'Our restrained gaze and small closed mouth',
    sheet: 'sheets/study-a.png',
    prompt: 'prompts/study-a.txt',
    sourceStudyUrl: 'https://example.com/study',
    referenceUrl: '../game_face_research_20260929/board/index.html#study-a',
    ...extra
  };
}

test('publishes the API under its own key and returns independent records', () => {
  const { api, writes } = load();
  assert.equal(api.key, KEY);
  assert.deepEqual(Object.keys(api).sort(), ['exportData', 'get', 'importData', 'key', 'markdown', 'storageAvailable', 'sync', 'update']);
  assert.deepEqual(clone(api.get('study-a/1')), { saved: false, note: '', updatedAt: '' });
  const record = api.update('study-a/1', { saved: true, note: 'Keep the gaze' });
  assert.equal(record.saved, true);
  assert.equal(record.note, 'Keep the gaze');
  assert.match(record.updatedAt, /^\d{4}-\d{2}-\d{2}T/);
  record.note = 'External mutation';
  assert.equal(api.get('study-a/1').note, 'Keep the gaze');
  api.update('study-a/1', { saved: false });
  assert.equal(api.get('study-a/1').note, 'Keep the gaze');
  assert.equal(writes.length, 2);
  assert.ok(writes.every(write => write.key === KEY));
});

test('loads only its own stored records and sanitizes fields', () => {
  const { api } = load({
    'mist.game-face-references.v1': JSON.stringify({ 'other/1': { saved: true, note: 'Other board' } }),
    [KEY]: JSON.stringify({
      'study-a/1': { saved: true, note: 'A'.repeat(20001), updatedAt: '2026-09-29T09:00:00.000Z', unknown: 'drop' },
      'study-a/2': { saved: 'true', note: 42, updatedAt: 'invalid' },
      'study-a/3': [],
      'invalid id': { saved: true, note: 'drop' }
    })
  });
  assert.equal(api.storageAvailable(), true);
  assert.equal(api.get('study-a/1').note.length, 20000);
  assert.deepEqual(Object.keys(api.get('study-a/1')).sort(), ['note', 'saved', 'updatedAt']);
  assert.deepEqual(clone(api.get('study-a/2')), { saved: false, note: '', updatedAt: '' });
  assert.equal(api.get('other/1').saved, false);
  assert.equal(api.get('study-a/3').saved, false);
});

test('exports only saved or meaningful noted records and allowed face metadata', () => {
  const { api } = load();
  api.update('study-a/1', { saved: true });
  api.update('study-a/2', { note: 'The concern reads clearly' });
  api.update('study-a/3', { saved: false, note: '   ' });
  api.update('study-a/4', { saved: true });
  api.update('study-a/4', { saved: false });
  api.update('future-study/1', { note: 'Keep an imported note without catalog metadata' });
  const entries = [face('study-a/1', { unrelated: 'drop' }), face('study-a/2'), face('study-a/3'), face('study-a/4'), face('study-a/1')];
  const exported = clone(api.exportData(entries));
  assert.equal(exported.schema, SCHEMA);
  assert.equal(exported.version, 1);
  assert.match(exported.exportedAt, /^\d{4}-\d{2}-\d{2}T/);
  assert.deepEqual(Object.keys(exported.records), ['study-a/1', 'study-a/2', 'future-study/1']);
  assert.deepEqual(exported.faces.map(entry => entry.id), ['study-a/1', 'study-a/2']);
  assert.deepEqual(Object.keys(exported.faces[0]), ['id', 'studyId', 'displayTitle', 'poseLabel', 'category', 'approach', 'sheet', 'prompt', 'sourceStudyUrl', 'referenceUrl']);
  exported.records['study-a/1'].saved = false;
  assert.equal(api.get('study-a/1').saved, true);
  assert.deepEqual(clone(api.exportData().faces), []);
});

test('imports a valid export, merges records, and ignores untrusted metadata', () => {
  const first = load().api;
  first.update('study-a/1', { saved: true, note: 'Favourite pose' });
  const exported = clone(first.exportData([face('study-a/1')]));
  exported.faces[0].displayTitle = 'Do not replace the catalog';
  const { api } = load();
  api.update('study-b/1', { note: 'Existing note' });
  assert.equal(api.importData(exported), 1);
  assert.equal(api.get('study-a/1').note, 'Favourite pose');
  assert.equal(api.get('study-b/1').note, 'Existing note');
  assert.equal(api.exportData([face('study-a/1')]).faces[0].displayTitle, 'A source study');
  assert.equal(api.importData({ schema: SCHEMA, version: 1, records: { 'study-a/1': { saved: false, note: 'Revised note' } } }), 1);
  assert.equal(api.get('study-a/1').saved, false);
  assert.equal(api.get('study-a/1').note, 'Revised note');
  assert.equal(api.importData({ schema: SCHEMA, version: 1, records: { 'study-a/1': { saved: true } } }), 1);
  assert.equal(api.get('study-a/1').note, 'Revised note');
  assert.equal(api.importData({ schema: SCHEMA, version: 1, records: { 'study-a/1': { note: 'Partial note' } } }), 1);
  assert.equal(api.get('study-a/1').saved, true);
  assert.equal(api.get('study-a/1').note, 'Partial note');
});

test('rejects wrong or missing schema, version, and records without changing state', () => {
  const { api, writes } = load();
  api.update('study-a/1', { saved: true, note: 'Keep me' });
  const before = JSON.stringify(api.exportData([]).records);
  const invalid = [
    null, [], 'text', {},
    { schema: 'mist-game-face-review', version: 1, records: {} },
    { schema: SCHEMA, version: 2, records: {} },
    { schema: SCHEMA, version: '1', records: {} },
    { schema: SCHEMA, version: 1 },
    { schema: SCHEMA, version: 1, records: [] },
    { schema: SCHEMA, version: 1, records: null },
    Object.create({ schema: SCHEMA, version: 1, records: {} })
  ];
  for (const value of invalid) assert.throws(() => api.importData(value), /JSON review export/);
  assert.equal(JSON.stringify(api.exportData([]).records), before);
  assert.equal(writes.length, 1);
});

test('validates malformed colliding imports completely before changing state or storage', () => {
  const { api, writes } = load();
  api.update('study-a/1', { saved: true, note: 'Keep me' });
  const before = JSON.stringify(api.exportData([]).records);
  for (const invalidRecord of [{ note: 42 }, { saved: 'true' }]) {
    assert.throws(() => api.importData({
      schema: SCHEMA,
      version: 1,
      records: { 'study-b/1': { saved: true, note: 'Must not commit early' }, 'study-a/1': invalidRecord }
    }), /unsupported format/);
    assert.equal(JSON.stringify(api.exportData([]).records), before);
  }
  assert.equal(writes.length, 1);
  assert.equal(api.importData({ schema: SCHEMA, version: 1, records: { 'study-a/1': {} } }), 0);
  assert.equal(JSON.stringify(api.exportData([]).records), before);
});

test('ignores prototype keys and inherited fields without changing any prototype', () => {
  const { api, context } = load();
  const data = JSON.parse('{"schema":"mist-generated-game-faces-review","version":1,"records":{"__proto__":{"saved":true,"note":"pollution"},"constructor":{"saved":true},"prototype":{"saved":true},"study-a/1":{"saved":true,"note":"safe","__proto__":{"polluted":true}}}}');
  assert.equal(api.importData(data), 1);
  assert.deepEqual(Object.keys(api.exportData([]).records), ['study-a/1']);
  assert.equal(api.get('__proto__').saved, false);
  assert.equal(api.get('constructor').saved, false);
  assert.throws(() => api.update('__proto__', { saved: true }), /unsupported review ID/);
  assert.equal(vm.runInContext('Object.prototype.polluted', context), undefined);
  assert.equal({}.polluted, undefined);
  const inherited = Object.create({ saved: true, note: 'Inherited note', updatedAt: '2026-09-29T09:00:00.000Z' });
  assert.equal(api.importData({ schema: SCHEMA, version: 1, records: { 'study-a/2': inherited } }), 0);
  assert.deepEqual(clone(api.get('study-a/2')), { saved: false, note: '', updatedAt: '' });
  api.update('study-a/1', Object.create({ saved: false, note: 'Inherited replacement' }));
  assert.equal(api.get('study-a/1').note, 'safe');
});

test('enforces the note limit through updates and imports', () => {
  const { api } = load();
  api.update('study-a/1', { note: 'N'.repeat(20010) });
  assert.equal(api.get('study-a/1').note.length, 20000);
  api.importData({ schema: SCHEMA, version: 1, records: { 'study-a/2': { note: 'I'.repeat(21000), saved: false, updatedAt: 'x'.repeat(10000) } } });
  assert.equal(api.get('study-a/2').note.length, 20000);
  assert.equal(api.get('study-a/2').saved, false);
  assert.equal(api.get('study-a/2').updatedAt, '');
});

test('keeps updates and imported notes in memory when localStorage is unavailable', () => {
  for (const options of [{ noStorage: true }, { readFailure: true, writeFailure: true }]) {
    const { api } = load({}, options);
    assert.equal(api.storageAvailable(), false);
    api.update('study-a/1', { saved: true, note: 'Memory survives' });
    assert.equal(api.get('study-a/1').note, 'Memory survives');
    api.importData({ schema: SCHEMA, version: 1, records: { 'study-a/2': { note: 'Imported in memory' } } });
    assert.equal(api.get('study-a/2').note, 'Imported in memory');
    assert.equal(api.storageAvailable(), false);
    assert.deepEqual(Object.keys(api.exportData([]).records), ['study-a/1', 'study-a/2']);
  }
});

test('recovers persistence without replacing newer in-memory records with stale storage', () => {
  const old = JSON.stringify({ 'study-a/1': { saved: false, note: 'Old storage' } });
  const { api, failures, values } = load({ [KEY]: old }, { writeFailure: true });
  api.update('study-a/1', { note: 'New memory' });
  assert.equal(api.storageAvailable(), false);
  assert.equal(values.get(KEY), old);
  failures.write = false;
  api.update('study-a/2', { saved: true });
  assert.equal(api.storageAvailable(), true);
  assert.equal(JSON.parse(values.get(KEY))['study-a/1'].note, 'New memory');
  assert.equal(JSON.parse(values.get(KEY))['study-a/2'].saved, true);
});

test('merges edits to different faces from two contexts sharing storage', () => {
  const tabA = load();
  const tabB = load({}, { sharedValues: tabA.values });
  tabA.api.update('study-a/1', { note: 'Tab A note' });
  tabB.api.update('study-b/1', { saved: true });
  const stored = JSON.parse(tabA.values.get(KEY));
  assert.equal(stored['study-a/1'].note, 'Tab A note');
  assert.equal(stored['study-b/1'].saved, true);
  assert.equal(tabA.api.get('study-b/1').saved, true);
  assert.equal(tabB.api.get('study-a/1').note, 'Tab A note');
  assert.deepEqual(Object.keys(tabA.api.exportData([]).records), ['study-a/1', 'study-b/1']);
});

test('merges a note and save flag for the same face without copying stale fields', () => {
  const tabA = load();
  const tabB = load({}, { sharedValues: tabA.values });
  tabA.api.update('study-a/1', { note: 'Written in tab A' });
  tabB.api.update('study-a/1', { saved: true });
  let stored = JSON.parse(tabA.values.get(KEY));
  assert.equal(stored['study-a/1'].note, 'Written in tab A');
  assert.equal(stored['study-a/1'].saved, true);
  tabA.api.update('study-a/1', { saved: false });
  tabB.api.update('study-a/1', { note: '' });
  stored = JSON.parse(tabA.values.get(KEY));
  assert.equal(stored['study-a/1'].saved, false);
  assert.equal(stored['study-a/1'].note, '');
  const secondA = load();
  const secondB = load({}, { sharedValues: secondA.values });
  secondA.api.update('study-a/1', { saved: true });
  secondB.api.update('study-a/1', { note: 'Note after the saved flag' });
  stored = JSON.parse(secondA.values.get(KEY));
  assert.equal(stored['study-a/1'].saved, true);
  assert.equal(stored['study-a/1'].note, 'Note after the saved flag');
});

test('sync refreshes shared changes without writing storage', () => {
  const tabA = load();
  const tabB = load({}, { sharedValues: tabA.values });
  tabA.api.update('study-a/1', { note: 'Storage event note' });
  assert.equal(tabB.api.sync(), true);
  assert.equal(tabB.api.get('study-a/1').note, 'Storage event note');
  assert.equal(tabB.writes.length, 0);
  tabB.failures.read = true;
  assert.equal(tabB.api.sync(), false);
  assert.equal(tabB.api.get('study-a/1').note, 'Storage event note');
});

test('does not replay successfully persisted patches over a newer edit from another context', () => {
  const tabA = load({}, { writeFailure: true });
  const tabB = load({}, { sharedValues: tabA.values });
  tabA.api.update('study-a/1', { note: 'First pending note' });
  tabA.failures.write = false;
  tabA.api.update('study-c/1', { saved: true });
  tabB.api.update('study-a/1', { note: 'Later persisted note' });
  tabA.api.update('study-d/1', { saved: true });
  const stored = JSON.parse(tabA.values.get(KEY));
  assert.equal(stored['study-a/1'].note, 'Later persisted note');
  assert.equal(stored['study-c/1'].saved, true);
  assert.equal(stored['study-d/1'].saved, true);
});

test('preserves pending explicit clears without replacing another context\'s untouched fields', () => {
  const tabA = load({ [KEY]: JSON.stringify({ 'study-a/1': { saved: true, note: 'Old note' } }) }, { writeFailure: true });
  const tabB = load({}, { sharedValues: tabA.values });
  tabA.api.update('study-a/1', { saved: false });
  tabB.api.update('study-a/1', { note: 'New remote note' });
  tabA.failures.write = false;
  tabA.api.importData({ schema: SCHEMA, version: 1, records: {} });
  let stored = JSON.parse(tabA.values.get(KEY));
  assert.equal(stored['study-a/1'].saved, false);
  assert.equal(stored['study-a/1'].note, 'New remote note');
  tabA.failures.write = true;
  tabA.api.update('study-a/1', { note: '' });
  tabB.api.update('study-a/1', { saved: true });
  tabA.failures.write = false;
  tabA.api.importData({ schema: SCHEMA, version: 1, records: {} });
  stored = JSON.parse(tabA.values.get(KEY));
  assert.equal(stored['study-a/1'].saved, true);
  assert.equal(stored['study-a/1'].note, '');
});

test('recovers failed writes by merging pending fields with another context\'s newer changes', () => {
  const tabA = load({}, { writeFailure: true });
  const tabB = load({}, { sharedValues: tabA.values });
  tabA.api.update('study-a/1', { note: 'Pending local note' });
  tabB.api.update('study-a/1', { saved: true });
  tabB.api.update('study-b/1', { note: 'Remote note' });
  assert.equal(tabA.api.get('study-a/1').note, 'Pending local note');
  assert.equal(tabA.api.get('study-a/1').saved, true);
  assert.equal(tabA.api.storageAvailable(), false);
  assert.equal(JSON.parse(tabA.values.get(KEY))['study-a/1'].note, '');
  tabA.failures.write = false;
  tabA.api.update('study-c/1', { saved: true });
  const stored = JSON.parse(tabA.values.get(KEY));
  assert.equal(stored['study-a/1'].note, 'Pending local note');
  assert.equal(stored['study-a/1'].saved, true);
  assert.equal(stored['study-b/1'].note, 'Remote note');
  assert.equal(stored['study-c/1'].saved, true);
  assert.equal(tabA.api.storageAvailable(), true);
  assert.equal(load({}, { sharedValues: tabA.values }).api.get('study-a/1').note, 'Pending local note');
});

test('does not overwrite unseen remote changes during read denial and merges when reads recover', () => {
  const tabA = load({ [KEY]: JSON.stringify({ 'study-a/1': { saved: false, note: 'Old note' } }) });
  const tabB = load({}, { sharedValues: tabA.values });
  tabA.failures.read = true;
  tabB.api.update('study-a/1', { saved: true });
  tabB.api.update('study-b/1', { note: 'Remote while denied' });
  const before = tabA.values.get(KEY);
  tabA.api.update('study-a/1', { note: 'New local note' });
  assert.equal(tabA.api.get('study-a/1').note, 'New local note');
  assert.equal(tabA.values.get(KEY), before);
  assert.equal(tabA.writes.length, 0);
  assert.equal(tabA.api.storageAvailable(), false);
  tabA.failures.read = false;
  tabA.api.update('study-c/1', { saved: true });
  const stored = JSON.parse(tabA.values.get(KEY));
  assert.equal(stored['study-a/1'].saved, true);
  assert.equal(stored['study-a/1'].note, 'New local note');
  assert.equal(stored['study-b/1'].note, 'Remote while denied');
  assert.equal(stored['study-c/1'].saved, true);
  assert.equal(tabA.api.storageAvailable(), true);
});

test('merges partial imports with fresh shared storage and keeps rejected imports atomic', () => {
  const tabA = load();
  const tabB = load({}, { sharedValues: tabA.values });
  tabA.api.update('study-a/1', { note: 'Remote before import' });
  assert.equal(tabB.api.importData({ schema: SCHEMA, version: 1, records: { 'study-a/1': { saved: true } } }), 1);
  assert.equal(JSON.parse(tabA.values.get(KEY))['study-a/1'].note, 'Remote before import');
  assert.equal(tabA.api.importData({ schema: SCHEMA, version: 1, records: { 'study-a/1': { note: 'Partial imported note' } } }), 1);
  assert.equal(JSON.parse(tabA.values.get(KEY))['study-a/1'].saved, true);
  tabA.failures.write = true;
  tabA.api.update('study-a/1', { note: 'Pending before rejected import' });
  tabB.api.update('study-b/1', { note: 'Remote before rejection' });
  const beforeMemory = JSON.stringify(tabA.api.exportData([]).records);
  const beforeStorage = tabA.values.get(KEY);
  const beforeWrites = tabA.writes.length;
  assert.throws(() => tabA.api.importData({
    schema: SCHEMA,
    version: 1,
    records: { 'study-c/1': { saved: true }, 'study-a/1': { note: 42 } }
  }), /unsupported format/);
  assert.equal(JSON.stringify(tabA.api.exportData([]).records), beforeMemory);
  assert.equal(tabA.values.get(KEY), beforeStorage);
  assert.equal(tabA.writes.length, beforeWrites);
  tabA.failures.write = false;
  tabA.api.importData({ schema: SCHEMA, version: 1, records: {} });
  const stored = JSON.parse(tabA.values.get(KEY));
  assert.equal(stored['study-a/1'].note, 'Pending before rejected import');
  assert.equal(stored['study-a/1'].saved, true);
  assert.equal(stored['study-b/1'].note, 'Remote before rejection');
  assert.equal(stored['study-c/1'], undefined);
});

test('handles corrupt stored JSON while retaining later review changes', () => {
  const { api, values } = load({ [KEY]: '{broken' });
  assert.equal(api.storageAvailable(), false);
  api.update('study-a/1', { note: 'Start again' });
  assert.equal(api.storageAvailable(), true);
  assert.equal(JSON.parse(values.get(KEY))['study-a/1'].note, 'Start again');
});

test('writes accurate Markdown with selected pose context and safely quoted notes', () => {
  const { api } = load();
  api.update('study-a/1', { saved: true, note: 'Closed mouth\r\n# Keep <this> [shape]' });
  api.update('study-a/2', { note: 'A note without saving' });
  const markdown = api.markdown([
    face('study-a/1', { displayTitle: 'Title\n# injected', poseLabel: 'Consideration / doubt' }),
    face('study-a/2', { poseLabel: 'Gentle concern / sadness' }),
    face('study-a/3', { displayTitle: 'Unreviewed study' })
  ]);
  assert.match(markdown, /Static MIST expression studies generated with ImageGen/);
  assert.match(markdown, /our adaptations/);
  assert.match(markdown, /not ready animations or the original artists' work/);
  assert.match(markdown, /2 faces saved or noted/);
  assert.match(markdown, /## Title \\# injected \/ Consideration \/ doubt/);
  assert.match(markdown, /Consideration \/ doubt/);
  assert.match(markdown, /Gentle concern \/ sadness/);
  assert.match(markdown, /Our adaptation: Our restrained gaze/);
  assert.match(markdown, /Original sheet: sheets\/study-a.png/);
  assert.match(markdown, /ImageGen prompt: prompts\/study-a.txt/);
  assert.match(markdown, /Source study: https:\/\/example.com\/study/);
  assert.match(markdown, /Original inspiration: \.\.\/game\\_face\\_research\\_20260929\/board\/index.html\\#study-a/);
  assert.match(markdown, /> Closed mouth\n> \\# Keep \\<this\\> \\\[shape\\\]/);
  assert.ok(!markdown.includes('Unreviewed study'));
  assert.ok(!markdown.includes('\n# injected'));
  assert.match(api.markdown(), /0 faces saved or noted/);
});
