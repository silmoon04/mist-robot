import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const source = fs.readFileSync(new URL('../ui/static/stt_stream.js', import.meta.url), 'utf8');
const tests = [];
const test = (name, run) => tests.push({name, run});

class Clock {
  time = 0;
  nextId = 0;
  timers = new Map();
  setTimeout = (callback, delay = 0) => {
    const id = ++this.nextId;
    this.timers.set(id, {at: this.time + Math.max(0, delay), callback});
    return id;
  };
  clearTimeout = id => this.timers.delete(id);
  advance(ms) {
    const target = this.time + ms;
    for (;;) {
      const next = [...this.timers].filter(([, item]) => item.at <= target)
        .sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
      if (!next) break;
      this.time = Math.max(this.time, next[1].at);
      this.timers.delete(next[0]);
      next[1].callback();
    }
    this.time = target;
  }
  stall(ms) { this.time += ms; }
}

function fixture(options = {}) {
  const clock = new Clock(), sockets = [], partials = [], statuses = [];
  let uuid = 0;
  class Socket {
    readyState = 0;
    bufferedAmount = 0;
    sent = [];
    closes = 0;
    sendError = false;
    constructor(url) { this.url = url; sockets.push(this); }
    send(data) {
      if (this.readyState !== 1 || this.sendError) throw new Error('Offline fake send failure');
      this.sent.push({at: clock.time, data: typeof data === 'string' ? data : data.slice(0)});
      this.onSend?.(data);
    }
    open() { this.readyState = 1; this.onopen?.({}); }
    message(value) { this.onmessage?.({data: JSON.stringify(value)}); }
    close() { this.closes++; this.readyState = 3; this.onclose?.({}); }
    controls() { return this.sent.filter(item => typeof item.data === 'string').map(item => JSON.parse(item.data)); }
    packets() { return this.sent.filter(item => typeof item.data !== 'string'); }
  }
  const context = {setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout,
    performance: {now: () => clock.time}, AbortController};
  vm.createContext(context);
  vm.runInContext(source, context);
  const client = context.MistSTTStream.create({
    socketFactory: url => new Socket(url),
    uuidFactory: () => `00000000-0000-4000-8000-${String(++uuid).padStart(12, '0')}`,
    onPartial: value => { partials.push(value); options.onPartial?.(value); },
    onStatus: value => { statuses.push(value); options.onStatus?.(value); },
    ...options
  });
  const meta = {utteranceId: 'capture-1', sampleRate: 48000};
  function open(value = meta, acknowledge = true) {
    assert.equal(client.start(value), true);
    const socket = sockets.at(-1);
    if (socket.readyState === 0) socket.open();
    const id = socket.controls().findLast(message => message.type === 'start').utterance_id;
    if (acknowledge) socket.message({type: 'started', utterance_id: id});
    return {socket, id};
  }
  function complete(socket, id, value = meta, transcript = 'Hello MIST.') {
    assert.equal(client.end(value), true);
    clock.advance(0);
    socket.message({type: 'final', utterance_id: id, transcript, confidence: 0.98,
      audio_seconds: 0.1, provider_processed_audio_seconds: 0.1, timings: {final_wait_s: 0.2}});
  }
  return {clock, sockets, partials, statuses, client, meta, open, complete};
}

function pcmSamples(socket) {
  return socket.packets().flatMap(({data}) => {
    const view = new DataView(data);
    return Array.from({length: data.byteLength / 2}, (_, i) => view.getInt16(i * 2, true));
  });
}

test('creation is passive and failed local connection returns null within one second', async () => {
  const f = fixture();
  assert.equal(f.sockets.length, 0);
  assert.equal(f.client.start(f.meta), true);
  assert.equal(f.sockets[0].url, 'ws://127.0.0.1:8788/stt');
  f.client.push(new Float32Array(4800), f.meta);
  const result = f.client.result(f.meta);
  f.clock.advance(999);
  assert.equal(f.sockets[0].closes, 0);
  f.clock.advance(1);
  assert.equal(await result, null);
  assert.equal(f.statuses.at(-1).reason, 'service-unavailable');
  assert.equal(f.sockets[0].closes, 1);
  assert.equal(f.clock.timers.size, 0);
});

test('start and matching acknowledgement precede all binary audio', () => {
  const f = fixture();
  f.client.start(f.meta);
  const socket = f.sockets[0];
  f.client.push(new Float32Array(9600), f.meta);
  f.clock.advance(100);
  assert.equal(socket.sent.length, 0);
  socket.open();
  const start = socket.controls()[0];
  assert.deepEqual(start, {type: 'start', utterance_id: '00000000-0000-4000-8000-000000000001', sample_rate: 48000});
  socket.message({type: 'started', utterance_id: 'unrelated'});
  f.clock.advance(100);
  assert.equal(socket.packets().length, 0);
  socket.message({type: 'started', utterance_id: start.utterance_id});
  f.clock.advance(0);
  assert.equal(socket.packets().length, 1);
  f.clock.advance(99);
  assert.equal(socket.packets().length, 1);
  f.clock.advance(1);
  assert.equal(socket.packets().length, 2);
  f.client.stop();
});

for (const sampleRate of [8000, 16000, 22050, 44100, 48000]) {
  test(`ordered PCM16 preserves every sample and actual ${sampleRate}Hz rate`, async () => {
    const f = fixture(), meta = {...f.meta, sampleRate};
    const {socket, id} = f.open(meta, false);
    const length = Math.round(sampleRate * 0.247);
    const samples = Float32Array.from({length}, (_, i) => Math.sin(i / 17) * 1.2);
    samples.set([-2, -0.5, 0, 0.5, 2, NaN, Infinity]);
    const expected = Array.from(samples, value => {
      const clipped = Number.isFinite(value) ? Math.max(-1, Math.min(1, value)) : 0;
      return Math.round(clipped * (clipped < 0 ? 32768 : 32767));
    });
    for (let offset = 0; offset < length; offset += 317) {
      const chunk = samples.slice(offset, offset + 317);
      assert.equal(f.client.push(chunk, meta), true);
      chunk.fill(0);
    }
    assert.equal(f.client.end(meta), true);
    socket.message({type: 'started', utterance_id: id});
    f.clock.advance(200);
    assert.equal(socket.controls()[0].sample_rate, sampleRate);
    assert.deepEqual(pcmSamples(socket), expected);
    assert.equal(socket.packets().length, 3);
    assert.equal(socket.packets()[0].data.byteLength, Math.round(sampleRate / 10) * 2);
    assert.equal(socket.controls().at(-1).type, 'end');
    assert.equal(socket.sent.at(-1).data.includes('"end"'), true);
    const result = f.client.result(meta);
    socket.message({type: 'final', utterance_id: id, transcript: 'All samples.', confidence: 0.9});
    assert.equal((await result).transcript, 'All samples.');
    assert.equal(f.clock.timers.size, 0);
    f.client.stop();
  });
}

test('a delayed pacing callback sends one packet without a catch-up burst', () => {
  const f = fixture(), {socket} = f.open();
  f.client.push(new Float32Array(48000), f.meta);
  f.clock.advance(0);
  assert.equal(socket.packets().length, 1);
  f.clock.stall(750);
  f.clock.advance(0);
  assert.equal(socket.packets().length, 2);
  assert.deepEqual(socket.packets().map(packet => packet.at), [0, 750]);
  f.clock.advance(99);
  assert.equal(socket.packets().length, 2);
  f.clock.advance(1);
  assert.equal(socket.packets().at(-1).at, 850);
  f.client.stop();
});

test('end waits for application PCM and socket buffered bytes to drain, then sends once', () => {
  const f = fixture(), {socket} = f.open();
  f.client.push(new Float32Array(4800), f.meta);
  socket.onSend = data => { if (typeof data !== 'string') socket.bufferedAmount = data.byteLength; };
  f.client.end(f.meta);
  f.clock.advance(0);
  assert.equal(socket.controls().filter(value => value.type === 'end').length, 0);
  f.clock.advance(50);
  socket.bufferedAmount = 0;
  f.clock.advance(50);
  assert.equal(socket.controls().filter(value => value.type === 'end').length, 1);
  f.client.end(f.meta);
  f.clock.advance(100);
  assert.equal(socket.controls().filter(value => value.type === 'end').length, 1);
  f.client.stop();
});

test('the full twenty seconds can stream, but one additional sample cancels the utterance', async () => {
  const f = fixture(), meta = {...f.meta, sampleRate: 8000}, {socket} = f.open(meta);
  assert.equal(f.client.push(new Float32Array(160000), meta), true);
  f.clock.advance(20000);
  assert.equal(socket.packets().length, 200);
  assert.equal(f.client.push(new Float32Array(1), meta), false);
  assert.equal(await f.client.result(meta), null);
  assert.equal(f.statuses.at(-1).reason, 'audio-too-long');
  assert.equal(socket.controls().at(-1).type, 'cancel');
  assert.equal(socket.closes, 1);
  assert.equal(f.clock.timers.size, 0);
});

test('an oversized startup buffer fails before sending any binary audio', async () => {
  const f = fixture(), {socket} = f.open(f.meta, false);
  assert.equal(f.client.push(new Float32Array(48000 * 20 + 1), f.meta), false);
  assert.equal(await f.client.result(f.meta), null);
  assert.equal(socket.packets().length, 0);
  assert.equal(f.clock.timers.size, 0);
});

test('the eight-second result deadline includes draining a full startup backlog', async () => {
  const f = fixture(), meta = {...f.meta, sampleRate: 8000}, {socket, id} = f.open(meta, false);
  f.client.push(new Float32Array(160000), meta);
  f.client.end(meta);
  const result = f.client.result(meta);
  socket.message({type: 'started', utterance_id: id});
  f.clock.advance(8000);
  assert.equal(await result, null);
  assert.equal(socket.packets().length, 80);
  assert.equal(socket.controls().some(value => value.type === 'end'), false);
  assert.equal(socket.controls().at(-1).type, 'cancel');
  assert.equal(f.statuses.at(-1).reason, 'result-timeout');
  assert.equal(f.clock.timers.size, 0);
});

test('late result calls and repeated end calls cannot extend the final deadline', async () => {
  const f = fixture(), {socket} = f.open();
  f.client.push(new Float32Array(4800), f.meta);
  f.client.end(f.meta);
  f.clock.advance(7000);
  f.client.end(f.meta);
  f.clock.advance(999);
  const result = f.client.result(f.meta);
  f.clock.advance(1);
  assert.equal(await result, null);
  assert.equal(socket.closes, 1);
  assert.equal(f.clock.time, 8000);
});

test('a missing started acknowledgement fails in three seconds and cancels its server slot', async () => {
  const f = fixture(), {socket} = f.open(f.meta, false);
  f.client.push(new Float32Array(4800), f.meta);
  const result = f.client.result(f.meta);
  f.clock.advance(3000);
  assert.equal(await result, null);
  assert.equal(f.statuses.at(-1).reason, 'start-timeout');
  assert.equal(socket.packets().length, 0);
  assert.equal(socket.controls().at(-1).type, 'cancel');
  assert.equal(f.clock.timers.size, 0);
});

test('final received before result is retained and repeated result calls share it', async () => {
  const f = fixture(), {socket, id} = f.open();
  f.client.push(new Float32Array(4800), f.meta);
  f.complete(socket, id);
  const first = f.client.result(f.meta), second = f.client.result(f.meta);
  assert.equal(first, second);
  assert.equal((await first).utteranceId, f.meta.utteranceId);
  assert.equal((await first).utterance_id, id);
  assert.equal((await first).provider_processed_audio_seconds, 0.1);
  assert.equal((await second).transcript, 'Hello MIST.');
  assert.equal(socket.closes, 0);
  assert.equal(f.clock.timers.size, 0);
  f.client.stop();
});

test('healthy connections are reused with new UUIDs and old events cannot affect the next result', async () => {
  const f = fixture(), capture = new AbortController();
  const firstMeta = {...f.meta, signal: capture.signal};
  const {socket, id: firstId} = f.open(firstMeta);
  f.client.push(new Float32Array(4800), firstMeta);
  f.complete(socket, firstId, firstMeta);
  assert.equal((await f.client.result(firstMeta)).transcript, 'Hello MIST.');
  const secondMeta = {...f.meta, utteranceId: 'capture-2'};
  const {id: secondId} = f.open(secondMeta, false);
  assert.equal(f.sockets.length, 1);
  assert.notEqual(firstId, secondId);
  capture.abort();
  socket.message({type: 'started', utterance_id: firstId});
  socket.message({type: 'partial', utterance_id: firstId, text: 'Stale text'});
  socket.message({type: 'final', utterance_id: firstId, transcript: 'Stale final'});
  assert.equal(f.partials.length, 0);
  assert.equal(await f.client.result(firstMeta), null);
  f.client.push(new Float32Array(4800), secondMeta);
  socket.message({type: 'started', utterance_id: secondId});
  socket.message({type: 'partial', utterance_id: secondId, text: 'Second preview'});
  assert.equal(f.partials[0].utteranceId, secondMeta.utteranceId);
  f.complete(socket, secondId, secondMeta, 'Second final');
  assert.equal((await f.client.result(secondMeta)).transcript, 'Second final');
  assert.equal(socket.closes, 0);
  f.client.stop();
});

test('cancellation invalidates old socket callbacks and reconnects for the next utterance', async () => {
  const f = fixture(), {socket, id} = f.open(f.meta, false);
  const oldMessage = socket.onmessage, oldOpen = socket.onopen;
  f.client.push(new Float32Array(4800), f.meta);
  const result = f.client.result(f.meta);
  f.client.cancel(f.meta);
  assert.equal(await result, null);
  const nextMeta = {...f.meta, utteranceId: 'capture-2'};
  const {socket: nextSocket, id: nextId} = f.open(nextMeta);
  oldOpen({});
  for (const type of ['started', 'partial', 'final', 'error']) {
    oldMessage({data: JSON.stringify({type, utterance_id: id, text: 'Old', transcript: 'Old'})});
  }
  assert.equal(f.partials.length, 0);
  assert.equal(nextSocket.closes, 0);
  f.client.push(new Float32Array(4800), nextMeta);
  f.complete(nextSocket, nextId, nextMeta);
  assert.equal((await f.client.result(nextMeta)).transcript, 'Hello MIST.');
  assert.equal(f.sockets.length, 2);
  f.client.stop();
});

test('capture abort before acknowledgement discards all pending audio before result is called', async () => {
  const f = fixture(), capture = new AbortController(), meta = {...f.meta, signal: capture.signal};
  const {socket} = f.open(meta, false);
  f.client.push(new Float32Array(4800), meta);
  capture.abort();
  assert.equal(await f.client.result({...meta, signal: new AbortController().signal}), null);
  assert.equal(socket.controls().at(-1).type, 'cancel');
  assert.equal(socket.packets().length, 0);
  assert.equal(socket.closes, 1);
  assert.equal(f.clock.timers.size, 0);
});

test('operation abort during drain cancels and clears all pacing work', async () => {
  const f = fixture(), {socket} = f.open(), operation = new AbortController();
  f.client.push(new Float32Array(48000), f.meta);
  f.client.end(f.meta);
  const result = f.client.result({...f.meta, signal: operation.signal});
  f.clock.advance(200);
  assert.equal(socket.packets().length, 3);
  operation.abort();
  f.clock.advance(10000);
  assert.equal(await result, null);
  assert.equal(socket.packets().length, 3);
  assert.equal(socket.controls().at(-1).type, 'cancel');
  assert.equal(socket.closes, 1);
  assert.equal(f.clock.timers.size, 0);
});

for (const stopMethod of ['stop', 'cancel', 'capture-abort', 'operation-abort']) {
  test(`${stopMethod} invalidates a completed final before it is consumed`, async () => {
    const f = fixture(), capture = new AbortController(), meta = {...f.meta, signal: capture.signal};
    const {socket, id} = f.open(meta);
    f.client.push(new Float32Array(4800), meta);
    f.complete(socket, id, meta);
    const operation = new AbortController();
    if (stopMethod === 'stop') f.client.stop();
    if (stopMethod === 'cancel') f.client.cancel(meta);
    if (stopMethod === 'capture-abort') capture.abort();
    if (stopMethod === 'operation-abort') operation.abort();
    assert.equal(await f.client.result({...meta, signal: operation.signal}), null);
    assert.equal(socket.closes, 1);
    assert.equal(f.clock.timers.size, 0);
  });
}

test('a changed sample rate fails the whole utterance before buffered PCM is sent', async () => {
  const f = fixture(), {socket} = f.open(f.meta, false);
  f.client.push(new Float32Array(4800), f.meta);
  assert.equal(f.client.push(new Float32Array(4410), {...f.meta, sampleRate: 44100}), false);
  assert.equal(await f.client.result(f.meta), null);
  assert.equal(f.statuses.at(-1).reason, 'sample-rate-changed');
  assert.equal(socket.packets().length, 0);
});

test('a mismatched acknowledgement rate cancels before binary audio is sent', async () => {
  const f = fixture(), {socket, id} = f.open(f.meta, false);
  f.client.push(new Float32Array(4800), f.meta);
  socket.message({type: 'started', utterance_id: id, sample_rate: 44100});
  f.clock.advance(0);
  assert.equal(await f.client.result(f.meta), null);
  assert.equal(f.statuses.at(-1).reason, 'sample-rate-mismatch');
  assert.equal(socket.packets().length, 0);
  assert.equal(socket.closes, 1);
});

for (const problem of ['send', 'close', 'error', 'invalid-response', 'backpressure']) {
  test(`${problem} failure returns null and releases the connection before fallback`, async () => {
    const f = fixture(), {socket, id} = f.open();
    f.client.push(new Float32Array(4800), f.meta);
    const result = f.client.result(f.meta);
    if (problem === 'send') socket.sendError = true;
    if (problem === 'close') socket.close();
    if (problem === 'error') socket.message({type: 'error', utterance_id: id, message: 'Offline error'});
    if (problem === 'invalid-response') socket.onmessage({data: 'invalid JSON'});
    if (problem === 'backpressure') socket.bufferedAmount = 48001;
    f.clock.advance(0);
    assert.equal(await result, null);
    assert.equal(socket.readyState, 3);
    assert.equal(f.clock.timers.size, 0);
  });
}

test('temporary socket backpressure pauses sending without bursting after it clears', () => {
  const f = fixture(), {socket} = f.open();
  f.client.push(new Float32Array(9600), f.meta);
  socket.bufferedAmount = 20000;
  f.clock.advance(100);
  assert.equal(socket.packets().length, 0);
  socket.bufferedAmount = 0;
  f.clock.advance(50);
  assert.equal(socket.packets().length, 1);
  f.clock.advance(99);
  assert.equal(socket.packets().length, 1);
  f.clock.advance(1);
  assert.equal(socket.packets().length, 2);
  f.client.stop();
});

for (const problem of ['uuid', 'unsupported-rate', 'empty-audio', 'socket-constructor']) {
  test(`${problem} failure requires no network and yields a null result`, async () => {
    const options = problem === 'uuid' ? {uuidFactory: () => undefined} :
      problem === 'socket-constructor' ? {socketFactory: () => { throw new Error('Offline'); }} : {};
    const f = fixture(options), meta = {...f.meta, sampleRate: problem === 'unsupported-rate' ? 96000 : 48000};
    f.client.start(meta);
    f.client.end(meta);
    assert.equal(await f.client.result(meta), null);
    assert.equal(f.clock.timers.size, 0);
    assert.equal(f.sockets.every(socket => socket.packets().length === 0), true);
  });
}

test('observer exceptions cannot interrupt transport cleanup or partial delivery', async () => {
  const f = fixture({onStatus: () => { throw new Error('Observer'); },
    onPartial: () => { throw new Error('Observer'); }});
  const {socket, id} = f.open();
  socket.message({type: 'partial', utterance_id: id, text: 'Preview'});
  f.client.push(new Float32Array(4800), f.meta);
  const result = f.client.result(f.meta);
  f.client.stop();
  assert.equal(await result, null);
  assert.equal(socket.closes, 1);
  assert.equal(f.clock.timers.size, 0);
});

test('stopping from a streaming callback prevents any queued audio from sending', async () => {
  let client;
  const f = fixture({onStatus: value => { if (value.status === 'streaming') client.stop(); }});
  client = f.client;
  const {socket} = f.open(f.meta, false);
  f.client.push(new Float32Array(4800), f.meta);
  socket.message({type: 'started', utterance_id: socket.controls()[0].utterance_id});
  f.clock.advance(10000);
  assert.equal(await f.client.result(f.meta), null);
  assert.equal(socket.packets().length, 0);
  assert.equal(socket.closes, 1);
  assert.equal(f.clock.timers.size, 0);
});

let failed = 0;
for (const {name, run} of tests) {
  try { await run(); process.stdout.write(`PASS ${name}\n`); }
  catch (error) { failed++; process.stderr.write(`FAIL ${name}\n${error.stack}\n`); }
}
process.stdout.write(`\n${tests.length - failed}/${tests.length} streaming client tests passed. No network, microphone, or providers used.\n`);
if (failed) process.exitCode = 1;
