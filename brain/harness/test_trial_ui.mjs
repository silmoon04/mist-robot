// Offline UI contracts. This test opens no browser, network, model, or microphone.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const html = fs.readFileSync(new URL('../duplex/static/trials.html', import.meta.url), 'utf8');
const script = fs.readFileSync(new URL('../duplex/static/trials.js', import.meta.url), 'utf8');
const debugHtml = fs.readFileSync(new URL('../duplex/static/debug.html', import.meta.url), 'utf8');
const debugScript = fs.readFileSync(new URL('../duplex/static/debug.js', import.meta.url), 'utf8');
const catalog = [
  {id: 'cerebras-balanced', label: 'Cerebras', provider: 'cerebras', model: 'foreground-a', background_model: 'worker-a', endpoint_ms: 300, floor: 'selective', available: true},
  {id: 'luna', label: 'Luna', provider: 'codex', model: 'foreground-b', background_model: 'worker-b', endpoint_ms: 700, floor: 'selective', available: true},
];
class Element {
  constructor(id = '') { Object.assign(this, {id, children: [], value: '', textContent: '', hidden: false, dataset: {}, checked: id === 'newest', contentWindow: {}, attrs: {}}); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(key, value) { this.attrs[key] = value; }
  removeAttribute(key) { delete this.attrs[key]; }
  querySelectorAll() { return []; }
}
const settle = async () => { for (let n = 0; n < 12; n++) await new Promise(setImmediate); };
const text = node => [node.textContent, ...node.children.map(text)].join(' ');
function harness(override = null) {
  const nodes = new Map([...html.matchAll(/id="([^"]+)"/g)].map(match => [match[1], new Element(match[1])]));
  nodes.get('category').value = 'all'; nodes.get('session').value = '__live';
  const calls = [], listeners = {};
  let handler = override;
  const defaultReply = path => {
    if (path === '/trial/bootstrap' || path === '/trial/disconnect') return {};
    if (path === '/trial/catalog') return {architectures: catalog, default: catalog[0].id};
    if (path === '/trial/sessions') return {sessions: []};
    const url = new URL(path, 'http://localhost');
    return {trace_id: url.searchParams.get('session'), events: [], cursor: Number(url.searchParams.get('after')), head: 0};
  };
  const context = {
    document: {getElementById: id => nodes.get(id), createElement: () => new Element()},
    window: {addEventListener: (name, callback) => { listeners[name] = callback; }},
    location: {origin: 'http://localhost'}, URL, AbortController, Map, Set,
    setTimeout: () => 1, clearTimeout: () => {},
    fetch: async (path, options) => {
      calls.push({path, options});
      const reply = handler ? await handler(path, options, defaultReply) : defaultReply(path);
      return {ok: reply?.__status ? reply.__status < 400 : true, status: reply?.__status || 200,
        json: async () => reply?.__body || reply};
    },
  };
  vm.createContext(context); vm.runInContext(script, context);
  return {nodes, calls, listeners, context, evaluate: code => vm.runInContext(code, context), setHandler: callback => {handler = callback;},
    ingest: rows => {context.inputRows = rows; vm.runInContext('for(const row of inputRows)ingestMetric(row)', context);}};
}
const row = (id, elapsed_ms, event, source = 'server') => ({id, elapsed_ms, source, event});

test('bootstrap embeds the production face without opening microphone or voice transport', async () => {
  const h = harness(); await settle();
  assert.equal(h.nodes.get('voice').src, '/?architecture=cerebras-balanced&trial=1');
  assert.equal(h.calls[0].path, '/trial/bootstrap');
  assert.equal(h.calls[0].options.body, '{}');
  assert.equal(h.calls[0].options.method, 'POST');
  assert(!h.calls.some(call => /\/trial\/voice|\/voice$/.test(call.path)));
});

test('bootstrap errors stay visible and offer retry', async () => {
  const h = harness((path, options, fallback) => path === '/trial/bootstrap' ? {__status: 403, __body: {error: 'Loopback pairing rejected'}} : fallback(path));
  await settle(); assert.match(h.nodes.get('error').textContent, /Loopback pairing rejected/);
  assert.equal(h.nodes.get('error').hidden, false); assert.equal(h.nodes.get('retry').hidden, false);
  assert.equal(h.nodes.get('voice').src, undefined);
});

test('architecture switches wait for close and preserve the old iframe after a failed close', async () => {
  const h = harness(); await settle(); let finish;
  h.setHandler((path, options, fallback) => path === '/trial/disconnect' ? new Promise(resolve => {finish = resolve;}) : fallback(path));
  const switching = h.evaluate("switchArchitecture('luna')"); await settle();
  assert.equal(h.nodes.get('voice').src, '/?architecture=cerebras-balanced&trial=1');
  finish({}); await switching;
  assert.equal(h.nodes.get('voice').src, '/?architecture=luna&trial=1');
  h.setHandler((path, options, fallback) => path === '/trial/disconnect' ? {__status: 500, __body: {error: 'Close failed'}} : fallback(path));
  await h.evaluate("switchArchitecture('cerebras-balanced')");
  assert.equal(h.nodes.get('voice').src, '/?architecture=luna&trial=1');
  assert.equal(h.nodes.get('architecture').value, 'luna'); assert.match(h.nodes.get('error').textContent, /Close failed/);
});

test('historical configurations use stored values, not the current catalog', async () => {
  const h = harness(); await settle();
  h.evaluate(`state.sessions=[{trace_id:'old',architecture:{id:'cerebras-balanced',label:'Saved run',model:'old-model',provider:'old-provider',endpoint_ms:500,floor:'old-floor'}},{trace_id:'other',architecture:{id:'luna',model:'saved-second',endpoint_ms:900}}];state.mode='history';state.trace='old';`);
  h.nodes.get('compare').value = 'other'; h.evaluate('renderConfiguration()');
  const output = text(h.nodes.get('config-body'));
  assert.match(output, /old-model/); assert.match(output, /500 ms/); assert.match(output, /saved-second/); assert.match(output, /900 ms/);
  assert(!output.includes('foreground-a')); assert(!output.includes('foreground-b'));
});

test('late event responses and new live-session announcements do not replace a historical selection', async () => {
  const h = harness(); await settle(); let finishOld;
  h.setHandler((path, options, fallback) => {
    if (path.startsWith('/trial/events?')) {
      const trace = new URL(path, 'http://localhost').searchParams.get('session');
      if (trace === 'old') return new Promise(resolve => {finishOld = resolve;});
      return {trace_id: trace, events: [row(1, 10, {type: 'ready', text: trace})], cursor: 1, head: 1};
    }
    return fallback(path);
  });
  h.evaluate("state.mode='history';chooseTrace('old')"); await settle(); h.evaluate("chooseTrace('chosen')"); await settle();
  finishOld({trace_id: 'old', events: [row(99, 10, {type: 'error'})], cursor: 99, head: 99}); await settle();
  assert.equal(h.evaluate('state.trace'), 'chosen'); assert.equal(h.evaluate("state.rows.has('99')"), false);
  h.listeners.message({origin: 'http://localhost', source: h.nodes.get('voice').contentWindow, data: {type: 'mist-session', trace_id: 'new-live', architecture: 'cerebras-balanced'}});
  await settle(); assert.equal(h.evaluate('state.trace'), 'chosen'); assert.equal(h.evaluate('state.liveTrace'), 'new-live');
  h.listeners.message({origin: 'https://unrelated.example', source: h.nodes.get('voice').contentWindow, data: {type: 'mist-session', trace_id: 'forged'}});
  assert.equal(h.evaluate('state.liveTrace'), 'new-live');
});

test('pagination retains all loaded events but renders 100 per page and exports the whole session', async () => {
  const h = harness(); await settle();
  h.setHandler((path, options, fallback) => {
    if (!path.startsWith('/trial/events?')) return fallback(path);
    const url = new URL(path, 'http://localhost'), after = Number(url.searchParams.get('after'));
    const ids = Array.from({length: Math.min(400, 1001 - after)}, (_, index) => after + index + 1);
    return {trace_id: 'paged', events: ids.map(id => row(id, id, {type: 'transcript_delta', text: '<script>inert</script>'})), cursor: ids.at(-1) || after, head: 1001};
  });
  h.evaluate("chooseTrace('paged')"); await settle();
  assert.equal(h.evaluate('state.rows.size'), 1001); assert.equal(h.evaluate('state.cursor'), 1001);
  assert.equal(h.nodes.get('events').children.length, 100); assert.equal(h.nodes.get('export').href, '/trial/export?session=paged');
  h.nodes.get('search').value = 'does not exist'; h.nodes.get('search').oninput();
  assert.equal(h.evaluate('state.rows.size'), 1001); assert.equal(h.nodes.get('export').href, '/trial/export?session=paged');
});

test('timing cards follow actual public cascade stages and distinguish requested waits', async () => {
  const h = harness(); await settle();
  const debug = (phase, at_ms, fields = {}) => ({type: 'debug_model', phase, backend: 'cascade', at_ms, ...fields});
  h.ingest([row(1, 110, debug('speech_started', 100)), row(2, 450, debug('stt_partial', 400, {text: 'Hello'})),
    row(3, 600, debug('stt_final', 550, {text: 'Hello'})), row(4, 610, debug('floor_incomplete_hold', 560, {hold_ms: 700})),
    row(5, 1340, debug('user_committed', 1280)), row(6, 1350, debug('thinking_started', 1290, {turn_id: 't1'})),
    row(7, 1600, debug('text_delta', 1500, {turn_id: 't1', source: 'cascade_text_model', delta: 'Hi'})),
    row(8, 1650, debug('text_delta', 1560, {turn_id: 't1', delta: ' again'}))]);
  assert.equal(h.evaluate("state.metrics.get('Speech detected to STT text').value"), 300);
  assert.equal(h.evaluate("state.metrics.get('Requested clause hold').value"), 700);
  assert.match(h.evaluate("state.metrics.get('Requested clause hold').provenance"), /not measured/);
  assert.equal(h.evaluate("state.metrics.get('Clause hold until commit').value"), 720);
  assert.equal(h.evaluate("state.metrics.get('Model first text').value"), 210);
  assert.equal(h.evaluate("state.metrics.get('Model first text').event_id"), 7);
});

test('receipt-to-playback anchor excludes protocol duplicates, acknowledgements and interrupted turns', async () => {
  const h = harness(); await settle();
  h.ingest([row(1, 90, {type: 'turn.done', turn: {role: 'user', transcript: 'Hello'}}, 'model_protocol'),
    row(2, 100, {type: 'transcript_done', role: 'user', text: 'Hello'}),
    row(3, 180, {type: 'turn.done', turn: {role: 'user', transcript: 'Hello'}}, 'model_protocol'),
    row(4, 450, {type: 'playback_started'}, 'browser'), row(5, 700, {type: 'playback_started'}, 'browser')]);
  assert.equal(h.evaluate("state.metrics.get('Final transcript to playback').value"), 350);
  assert.match(h.evaluate("state.metrics.get('Final transcript to playback').provenance"), /Server receipts/);
  for (const reset of [{type: 'barge_in'}, {event: 'playback_interrupt'}, {type: 'turn.created', turn: {role: 'user'}}, {type: 'native_turn', role: 'user'}]) {
    h.ingest([row(6, 800, {type: 'transcript_done', role: 'user', text: 'Old'}), row(7, 900, reset), row(8, 1200, {type: 'playback_started'}, 'browser')]);
    assert.equal(h.evaluate("state.metrics.get('Final transcript to playback').value"), 350);
  }
  h.ingest([row(9, 1300, {type: 'transcript_done', role: 'user', text: 'yeah', backchannel: true, floor_preserved: true}), row(10, 1500, {type: 'playback_started'}, 'browser')]);
  assert.equal(h.evaluate("state.metrics.get('Final transcript to playback').value"), 350);
});

test('native backing timing cannot be mislabeled by a realtime text delta', async () => {
  const h = harness(); await settle();
  h.ingest([row(1, 100, {type: 'debug_model', phase: 'thinking_started', source: 'native_backing', turn_id: 'same'}),
    row(2, 200, {type: 'debug_model', phase: 'text_delta', source: 'native_realtime', turn_id: 'same', delta: 'Spoken text'}),
    row(3, 350, {type: 'debug_model', phase: 'text_delta', source: 'native_backing', turn_id: 'same', delta: 'Tool response'})]);
  assert.equal(h.evaluate("state.metrics.has('Model first text')"), false);
  assert.equal(h.evaluate("state.metrics.get('Backing model first text').value"), 250);
});

test('director decisions and speech style are visible with their measured timing', async () => {
  const h = harness(); await settle();
  const affect = row(1, 1500, {type:'affect_decision', phase:'finished', outcome:'applied_before_speech',
    elapsed_ms:175, decision:{change:true, expression:'curious', variant:1, delivery:'warm'}});
  const style = row(2, 1560, {type:'speech_style', delivery:'warm', model:'eleven_flash_v2_5', stability:.4});
  h.ingest([affect, style]);
  h.context.affectRow = affect; h.context.styleRow = style;
  assert.equal(h.evaluate("matchesCategory(affectRow,'expressions')"), true);
  assert.equal(h.evaluate("matchesCategory(affectRow,'model')"), true);
  assert.equal(h.evaluate("matchesCategory(styleRow,'audio')"), true);
  assert.match(h.evaluate('snippet(affectRow)'), /curious variant 1.*warm.*175 ms/);
  assert.match(h.evaluate('snippet(styleRow)'), /warm.*eleven_flash_v2_5.*stability 0.4/);
  assert.equal(h.evaluate("state.metrics.get('Affect decision').value"), 175);
  assert.equal(h.evaluate("state.metrics.get('Affect to speech style').value"), 60);
  assert.match(h.evaluate("state.metrics.get('Affect to speech style').provenance"), /Server receipt/);
  h.evaluate('clearTrace()');
  assert.equal(h.evaluate('state.affectAnchor'), null);
});

test('live debug filters and summaries include director decisions and speech style', async () => {
  const nodes = new Map([...debugHtml.matchAll(/id="([^"]+)"/g)].map(match => [match[1], new Element(match[1])]));
  nodes.get('category').value = 'expression'; nodes.get('follow').checked = false;
  const context = {document:{getElementById:id=>nodes.get(id), createElement:()=>new Element()},
    fetch:async()=>({ok:true,json:async()=>({trace_id:'test',events:[],cursor:0,oldest:0})}),
    setTimeout:()=>1, URL, Blob};
  vm.createContext(context); vm.runInContext(debugScript, context); await settle();
  context.testRows = [row(1, 1500, {type:'affect_decision', phase:'finished', outcome:'applied_before_speech',
    elapsed_ms:175, decision:{change:true,expression:'curious',delivery:'warm'}}),
    row(2, 1560, {type:'speech_style',delivery:'warm',model:'eleven_flash_v2_5',stability:.4})];
  vm.runInContext('rows=testRows;for(const item of rows)ingest(item);render()', context);
  assert.equal(nodes.get('events').children.length, 1);
  assert.match(text(nodes.get('events').children[0]), /curious.*warm.*175 ms/);
  assert.equal(vm.runInContext("metrics.get('Affect decision')", context), '175 ms');
  assert.equal(vm.runInContext("metrics.get('Affect to speech style')", context), '60 ms');
  nodes.get('category').value = 'tts'; vm.runInContext('render()', context);
  assert.equal(nodes.get('events').children.length, 1);
  assert.match(text(nodes.get('events').children[0]), /warm.*eleven_flash_v2_5/);
});

test('failed or refused tools appear in errors even when the event type is tool', async () => {
  const h = harness(); await settle();
  for (const event of [{type: 'tool', result: {status: 'error'}}, {type: 'tool', result: {status: 'refused'}},
    {type: 'debug_tool', phase: 'failed'}, {type: 'debug_tool', phase: 'finished', success: false}, {type: 'tool', result: {isError: true}}]) {
    h.context.testRow = row(1, 10, event); assert.equal(h.evaluate("matchesCategory(testRow,'errors')"), true);
  }
  h.context.testRow = row(1, 10, {type: 'tool', result: {status: 'ok'}, success: true});
  assert.equal(h.evaluate("matchesCategory(testRow,'errors')"), false);
});
