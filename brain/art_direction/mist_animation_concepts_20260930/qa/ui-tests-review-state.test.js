'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../board/review-state.js'), 'utf8');
const KEY = 'mist.animation-concepts.20260930.v1';
const SCHEMA = 'mist-animation-concepts-review';
const IDS = ['available-blink', 'available-blink__1', 'available-blink__2', 'available-blink__3', 'listening-focus'];
const copy = value => JSON.parse(JSON.stringify(value));
const envelope = records => ({ schema: SCHEMA, version: 1, records });

function load(options = {}) {
  const values = options.values || new Map();
  const failures = { read: Boolean(options.readFailure), write: Boolean(options.writeFailure) };
  const writes = [];
  const context = vm.createContext(options.noStorage ? {} : { localStorage: {
    getItem(key) { if (failures.read) throw new Error('Read denied'); return values.get(key) || null; },
    setItem(key, value) { if (failures.write) throw new Error('Write denied'); values.set(key, value); writes.push(value); }
  } });
  vm.runInContext(source, context, { filename: 'review-state.js' });
  const api = context.MistAnimationReview;
  api.configure(IDS);
  return { api, values, failures, writes, context };
}

function catalog() {
  return [{ id: 'available-blink', title: 'Available / blink', wave: 1, poses: [
    { id: 'available-blink__1', label: 'Open', image: 'images/available-blink-1.png' },
    { id: 'available-blink__2', label: 'Lower lids', image: 'images/available-blink-2.png' },
    { id: 'available-blink__3', label: 'Closed', image: 'images/available-blink-3.png' }
  ] }];
}

test('separates idea choices from individual pose feedback and returns independent records', () => {
  const { api } = load();
  assert.equal(api.key, KEY);
  api.update('available-blink', { choice: 'revise', note: 'Keep the open eyes.' });
  api.update('available-blink__2', { note: 'The middle lid shape needs work.' });
  assert.equal(api.get('available-blink').choice, 'revise');
  assert.equal(api.get('available-blink__2').choice, '');
  assert.equal(api.get('available-blink__1').note, '');
  const record = api.get('available-blink');
  record.note = 'External mutation';
  assert.equal(api.get('available-blink').note, 'Keep the open eyes.');
  assert.match(record.updatedAt, /^\d{4}-\d{2}-\d{2}T/);
});

test('exports meaningful feedback with pose identity and round-trips the JSON', () => {
  const first = load();
  first.api.update('available-blink', { choice: 'develop' });
  first.api.update('available-blink__2', { note: 'Middle pose: soften the lid.' });
  first.api.update('available-blink__3', { note: '   ' });
  const exported = copy(first.api.exportData(catalog()));
  assert.equal(exported.schema, SCHEMA);
  assert.equal(exported.version, 1);
  assert.deepEqual(Object.keys(exported.records).sort(), ['available-blink', 'available-blink__2']);
  assert.equal(exported.ideas.length, 1);
  assert.equal(exported.ideas[0].poses[1].id, 'available-blink__2');
  assert.equal(exported.ideas[0].poses[1].image, 'images/available-blink-2.png');
  const second = load();
  assert.equal(second.api.importData(exported), 2);
  assert.deepEqual(copy(second.api.exportData(catalog()).records), exported.records);
  exported.records['available-blink'].choice = 'skip';
  assert.equal(first.api.get('available-blink').choice, 'develop');
});

test('rejects unsupported schemas and malformed imports before committing any record', () => {
  const { api, writes } = load();
  api.update('available-blink', { choice: 'develop', note: 'Keep me.' });
  const before = copy(api.exportData([]).records), count = writes.length;
  const invalid = [
    null, [], {}, { schema: 'another-board', version: 1, records: {} },
    { schema: SCHEMA, version: 2, records: {} }, { schema: SCHEMA, version: 1, records: [] },
    envelope({ 'listening-focus': { note: 'Do not partially commit.' }, 'available-blink': { choice: 'maybe' } }),
    envelope({ 'listening-focus': { note: 'Do not partially commit.' }, 'available-blink': { note: 42 } }),
    envelope({ 'unknown-concept': { note: 'Unknown ID' } })
  ];
  for (const value of invalid) assert.throws(() => api.importData(value));
  assert.deepEqual(copy(api.exportData([]).records), before);
  assert.equal(writes.length, count);
});

test('rejects prototype IDs and does not import inherited record fields', () => {
  const { api, context } = load();
  const malicious = JSON.parse('{"schema":"mist-animation-concepts-review","version":1,"records":{"__proto__":{"choice":"develop","note":"polluted"}}}');
  assert.throws(() => api.importData(malicious));
  assert.throws(() => api.update('constructor', { note: 'No' }));
  const inherited = Object.create({ choice: 'skip', note: 'Inherited note' });
  api.importData(envelope({ 'available-blink': inherited }));
  assert.equal(api.get('available-blink').choice, '');
  assert.equal(api.get('available-blink').note, '');
  assert.equal(vm.runInContext('Object.prototype.polluted', context), undefined);
  assert.equal({}.polluted, undefined);
});

test('holds exportable feedback in memory when storage is absent or blocked', () => {
  for (const options of [{ noStorage: true }, { readFailure: true, writeFailure: true }]) {
    const { api, writes } = load(options);
    api.update('available-blink', { choice: 'develop', note: 'Held in memory.' });
    api.importData(envelope({ 'available-blink__2': { note: 'Pose held in memory.' } }));
    assert.equal(api.storageAvailable(), false);
    assert.equal(api.exportData(catalog()).records['available-blink__2'].note, 'Pose held in memory.');
    assert.equal(api.get('available-blink').note, 'Held in memory.');
    assert.equal(writes.length, 0);
  }
});

test('repairs corrupt storage on a user edit and isolates this board from other keys', () => {
  const values = new Map([[KEY, '{broken'], ['mist.generated-game-faces.20260929.v1', '{"available-blink":{"note":"Another board"}}']]);
  const { api } = load({ values });
  assert.equal(api.storageAvailable(), false);
  assert.equal(api.get('available-blink').note, '');
  api.update('available-blink', { note: 'New recoverable feedback.' });
  assert.equal(api.storageAvailable(), true);
  assert.equal(JSON.parse(values.get(KEY))['available-blink'].note, 'New recoverable feedback.');
  assert.equal(values.get('mist.generated-game-faces.20260929.v1'), '{"available-blink":{"note":"Another board"}}');
});

test('merges separate fields and records from two browser contexts', () => {
  const a = load(), b = load({ values: a.values });
  a.api.update('available-blink', { note: 'Tab A note.' });
  b.api.update('available-blink', { choice: 'revise' });
  a.api.update('available-blink__2', { note: 'Pose A note.' });
  b.api.update('listening-focus', { choice: 'develop' });
  const stored = JSON.parse(a.values.get(KEY));
  assert.equal(stored['available-blink'].note, 'Tab A note.');
  assert.equal(stored['available-blink'].choice, 'revise');
  assert.equal(stored['available-blink__2'].note, 'Pose A note.');
  assert.equal(a.api.get('listening-focus').choice, 'develop');
});

test('read-denial recovery flushes local edits without replacing unseen remote fields', () => {
  const a = load(), b = load({ values: a.values });
  a.api.update('available-blink', { note: 'Old note.', choice: 'develop' });
  const count = a.writes.length;
  a.failures.read = true;
  a.api.update('available-blink', { note: 'New local note.' });
  b.api.update('available-blink', { choice: 'skip' });
  assert.equal(a.writes.length, count);
  a.failures.read = false;
  a.api.update('listening-focus', { note: 'Flush local edits.' });
  assert.equal(a.api.storageAvailable(), true);
  assert.equal(a.api.get('available-blink').note, 'New local note.');
  assert.equal(a.api.get('available-blink').choice, 'skip');
});

test('write-denial recovery preserves explicit clears and latest remote notes', () => {
  const a = load(), b = load({ values: a.values });
  a.api.update('available-blink', { choice: 'develop', note: 'Old note.' });
  a.failures.write = true;
  a.api.update('available-blink', { choice: '' });
  b.api.update('available-blink', { note: 'New remote note.' });
  assert.equal(a.api.storageAvailable(), false);
  a.failures.write = false;
  a.api.update('available-blink__2', { note: 'Trigger flush.' });
  assert.equal(a.api.get('available-blink').choice, '');
  assert.equal(a.api.get('available-blink').note, 'New remote note.');
  assert.equal(a.api.storageAvailable(), true);
});

test('partial imports preserve choices and enforce the note length', () => {
  const { api } = load();
  api.update('available-blink', { choice: 'revise', note: 'A'.repeat(20001) });
  assert.equal(api.get('available-blink').note.length, 20000);
  api.importData(envelope({ 'available-blink': { note: 'Imported note.' } }));
  assert.equal(api.get('available-blink').choice, 'revise');
  api.importData(envelope({ 'available-blink': { choice: 'develop' } }));
  assert.equal(api.get('available-blink').note, 'Imported note.');
  api.importData(envelope({ 'available-blink__2': { note: 'B'.repeat(20010), updatedAt: 'Invalid timestamp' } }));
  assert.equal(api.get('available-blink__2').note.length, 20000);
  assert.equal(api.get('available-blink__2').updatedAt, '');
});
