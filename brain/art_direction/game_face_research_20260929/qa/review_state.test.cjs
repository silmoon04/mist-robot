const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../board/review-state.js'), 'utf8');
function boot(storage = {}) {
  const box = { localStorage: { getItem: () => storage.value || null, setItem: (_, value) => { if (storage.fail) throw new Error('quota'); storage.value = value; } } };
  vm.createContext(box); vm.runInContext(source, box); return box.MistGameReview;
}
let passed = 0;
function check(name, fn) { fn(); passed++; console.log('PASS ' + name); }
const entries = [{ id: 'alpha', title: 'Alpha', studio: 'Studio', people: [{ name: 'Artist', role: 'Animator', sourceUrl: 'https://example.com/artist' }], sources: [{ title: 'Source', url: 'https://example.com/source' }] }];
check('save and note survive reload', () => { const storage = {}; const review = boot(storage); review.update('alpha', { saved: true, note: 'The held look works.' }); const again = boot(storage); assert.equal(again.get('alpha').saved, true); assert.equal(again.get('alpha').note, 'The held look works.'); });
check('malformed array record does not erase existing note', () => { const review = boot(); review.update('alpha', { saved: true, note: 'Keep me' }); const count = review.importData({ schema: 'mist-game-face-review', version: 1, records: { alpha: [] } }); assert.equal(count, 0); assert.equal(review.get('alpha').note, 'Keep me'); assert.equal(review.get('alpha').saved, true); });
check('inherited object names have a normal default', () => { const review = boot(); assert.equal(review.get('constructor').saved, false); assert.equal(review.get('constructor').note, ''); review.update('constructor', { saved: true, note: 'Own record' }); assert.equal(review.get('constructor').note, 'Own record'); });
check('wrong schema fails without mutation', () => { const review = boot(); review.update('alpha', { note: 'Keep me' }); assert.throws(() => review.importData({ schema: 'other', version: 1, records: { alpha: { note: 'Bad' } } })); assert.equal(review.get('alpha').note, 'Keep me'); });
check('storage failure retains exportable memory records', () => { const storage = { fail: true }; const review = boot(storage); review.update('alpha', { saved: true, note: 'Export me' }); assert.equal(review.storageAvailable(), false); const result = review.exportData(entries); assert.equal(result.records.alpha.note, 'Export me'); assert.equal(result.references.length, 1); });
check('JSON roundtrip and Markdown include credits and sources', () => { const first = boot(); first.update('alpha', { saved: true, note: 'A specific blink.' }); const second = boot(); second.importData(JSON.parse(JSON.stringify(first.exportData(entries)))); assert.equal(second.get('alpha').note, 'A specific blink.'); const markdown = second.markdown(entries); assert.match(markdown, /A specific blink/); assert.match(markdown, /Artist/); assert.match(markdown, /https:\/\/example.com\/source/); });
check('long note is bounded', () => { const review = boot(); review.update('alpha', { note: 'x'.repeat(25000) }); assert.equal(review.get('alpha').note.length, 20000); });
console.log(JSON.stringify({ passed }));
