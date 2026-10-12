import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const source = fs.readFileSync(new URL('../ui/static/talk_capture.js', import.meta.url), 'utf8');
const workletSource = fs.readFileSync(new URL('../ui/static/talk_capture_worklet.js', import.meta.url), 'utf8');
const context = {Blob, AbortController, URL};
vm.createContext(context);
vm.runInContext(source, context);
const {createDetector, encodeWav} = context.MistTalkCapture;
const tests = [];
function test(name, run) { tests.push({name, run}); }
function feed(detector, ms, amplitude = 0, playback = false, sampleRate = 48000, blockSize = 1024) {
  let remaining = Math.round(ms * sampleRate / 1000);
  while (remaining > 0) {
    const size = Math.min(remaining, blockSize);
    const data = new Float32Array(size);
    for (let i = 0; i < size; i++) data[i] = i % 2 ? amplitude : -amplitude;
    detector.push(data, playback);
    remaining -= size;
  }
}
function detectorFixture(sampleRate = 48000) {
  const utterances = [], starts = [];
  const detector = createDetector({sampleRate, onUtterance: value => utterances.push(value),
    onSpeechStart: value => starts.push(value)});
  return {detector, utterances, starts};
}

test('complete utterance retains 200ms pre-roll and ends after 650ms silence', () => {
  const {detector, utterances, starts} = detectorFixture();
  feed(detector, 500, 0.001);
  feed(detector, 400, 0.05);
  feed(detector, 640);
  assert.equal(utterances.length, 0);
  feed(detector, 10);
  assert.equal(utterances.length, 1);
  assert.equal(starts.length, 1);
  assert.equal(utterances[0].metadata.speechMs, 400);
  assert.equal(utterances[0].metadata.durationMs, 1250);
  assert.equal(utterances[0].metadata.preRollMs, 200);
  assert.equal(utterances[0].metadata.trailingSilenceMs, 650);
  assert.equal(utterances[0].metadata.reason, 'silence');
});

for (const sampleRate of [16000, 44100, 48000]) {
  test(`short noises are rejected and 250ms speech is accepted at ${sampleRate}Hz`, () => {
    const {detector, utterances} = detectorFixture(sampleRate);
    feed(detector, 240, 0.05, false, sampleRate, 127);
    feed(detector, 700, 0, false, sampleRate, 113);
    assert.equal(utterances.length, 0);
    feed(detector, 250, 0.05, false, sampleRate, 233);
    feed(detector, 650, 0, false, sampleRate, 137);
    assert.equal(utterances.length, 1);
    assert.equal(utterances[0].metadata.speechMs, 250);
  });
}

test('playback requires sustained stronger input and preserves candidate onset', () => {
  const {detector, utterances, starts} = detectorFixture();
  feed(detector, 600, 0.02, true);
  assert.equal(starts.length, 0);
  feed(detector, 150, 0.05, true);
  feed(detector, 100, 0, true);
  assert.equal(starts.length, 0);
  feed(detector, 210, 0.05, true);
  assert.equal(starts.length, 0);
  feed(detector, 10, 0.05, true);
  assert.equal(starts.length, 1);
  feed(detector, 180, 0.05);
  feed(detector, 650);
  assert.equal(utterances.length, 1);
  assert.equal(utterances[0].metadata.bargeIn, true);
  assert.equal(utterances[0].metadata.speechMs, 400);
});

test('playback ending during a candidate keeps its stronger qualification', () => {
  const {detector, starts} = detectorFixture();
  feed(detector, 100, 0.05, true);
  feed(detector, 100, 0.05, false);
  assert.equal(starts.length, 0);
  feed(detector, 20, 0.05, false);
  assert.equal(starts.length, 1);
});

test('maximum duration is exactly 20 seconds including pre-roll', () => {
  const {detector, utterances} = detectorFixture();
  feed(detector, 300);
  feed(detector, 19800, 0.05);
  assert.equal(utterances.length, 1);
  assert.equal(utterances[0].metadata.durationMs, 20000);
  assert.equal(utterances[0].metadata.reason, 'max-duration');
  feed(detector, 700);
  assert.equal(utterances.length, 1);
});

test('WAV is self-contained mono PCM16 with actual sample-rate and clipping', async () => {
  const blob = encodeWav(new Float32Array([-2, -0.5, 0, 0.5, 2, NaN]), 44100);
  assert.equal(blob.type, 'audio/wav');
  const bytes = await blob.arrayBuffer();
  const view = new DataView(bytes);
  assert.equal(new TextDecoder().decode(bytes.slice(0, 4)), 'RIFF');
  assert.equal(new TextDecoder().decode(bytes.slice(8, 12)), 'WAVE');
  assert.equal(view.getUint32(24, true), 44100);
  assert.equal(view.getUint16(22, true), 1);
  assert.equal(view.getUint16(34, true), 16);
  assert.equal(view.getUint32(40, true), 12);
  assert.deepEqual(Array.from({length: 6}, (_, index) => view.getInt16(44 + index * 2, true)),
    [-32768, -16384, 0, 16384, 32767, 0]);
});

test('playback beginning mid-candidate requires 220ms of stronger evidence', () => {
  const {detector, starts} = detectorFixture();
  feed(detector, 80, 0.013);
  feed(detector, 140, 0.04, true);
  assert.equal(starts.length, 0);
  feed(detector, 80, 0.04, true);
  assert.equal(starts.length, 1);
  assert.equal(starts[0].confirmationMs, 220);
});

test('stopping synchronously from a speech notification discards the utterance', () => {
  let starts = 0;
  const detector = createDetector({sampleRate: 48000,
    onActivity: active => { if (active) detector.reset(); }, onSpeechStart: () => starts++});
  assert.doesNotThrow(() => feed(detector, 400, 0.05));
  assert.equal(starts, 0);
});

test('low background noise adapts without becoming speech or poisoning later detection', () => {
  const {detector, starts, utterances} = detectorFixture();
  feed(detector, 5000, 0.004);
  assert.equal(starts.length, 0);
  assert.ok(detector.getState().noiseFloor > 0.0035);
  feed(detector, 500, 0.04);
  feed(detector, 700, 0.004);
  assert.equal(utterances.length, 1);
  feed(detector, 3000, 0.02, true);
  assert.ok(detector.getState().noiseFloor < 0.005, 'Playback must not train the noise floor.');
});

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}
const tick = () => new Promise(resolve => setImmediate(resolve));
function fakeStream() {
  const listeners = new Map();
  const track = {stops: 0, stop() { this.stops++; },
    getSettings: () => ({echoCancellation: true, noiseSuppression: true, autoGainControl: false}),
    addEventListener(type, callback) { listeners.set(type, callback); },
    removeEventListener(type, callback) { if (listeners.get(type) === callback) listeners.delete(type); },
    end() { listeners.get('ended')?.(); }};
  return {track, getTracks: () => [track], getAudioTracks: () => [track]};
}
function browserFixture({media, addModule, resume, close, ...callbacks} = {}) {
  const contexts = [], nodes = [], streams = [], constraints = [], states = [], errors = [];
  class Context {
    constructor() {
      this.sampleRate = 48000; this.destination = {}; this.closes = 0;
      this.audioWorklet = {addModule: url => { this.moduleUrl = url; return addModule?.(this) ?? Promise.resolve(); }};
      contexts.push(this);
    }
    resume() { return resume?.(this) ?? Promise.resolve(); }
    close() { this.closes++; return close?.(this) ?? Promise.resolve(); }
    createMediaStreamSource(stream) { this.stream = stream; return {connect() {}, disconnect() {}}; }
    createGain() { this.sink = {gain: {value: 1}, connect() {}, disconnect() {}}; return this.sink; }
  }
  class WorkletNode {
    constructor(audioContext, name, options) {
      this.context = audioContext; this.name = name; this.options = options;
      this.port = {onmessage: null, closes: 0, close() { this.closes++; }, postMessage() {}};
      nodes.push(this);
    }
    connect() {}
    disconnect() {}
  }
  const browser = {Blob, AbortController, AudioContext: Context, AudioWorkletNode: WorkletNode,
    navigator: {mediaDevices: {getUserMedia(value) {
      constraints.push(value);
      if (media) return media();
      const stream = fakeStream(); streams.push(stream); return Promise.resolve(stream);
    }}}};
  vm.createContext(browser); vm.runInContext(source, browser);
  const capture = browser.MistTalkCapture.create({onState: state => states.push(state),
    onError: error => errors.push(error), ...callbacks});
  function pcm(ms, amplitude = 0) {
    const node = nodes.at(-1);
    feed({push: samples => node.port.onmessage?.({data: {type: 'pcm', samples}})}, ms, amplitude);
  }
  function utterance() { pcm(300, 0.05); pcm(660); }
  return {capture, browser, contexts, nodes, streams, constraints, states, errors, pcm, utterance};
}

test('create does not request a microphone; explicit starts coalesce and stop releases resources', async () => {
  const fixture = browserFixture();
  assert.equal(fixture.constraints.length, 0);
  assert.equal(fixture.contexts.length, 0);
  const first = fixture.capture.start(), second = fixture.capture.start();
  assert.equal(first, second);
  assert.equal(await first, true);
  assert.equal(fixture.constraints.length, 1);
  const audio = fixture.constraints[0].audio;
  assert.equal(audio.echoCancellation, true);
  assert.equal(audio.noiseSuppression, true);
  assert.equal(audio.autoGainControl, true);
  assert.equal(fixture.contexts[0].moduleUrl, '/static/talk_capture_worklet.js');
  assert.equal(fixture.contexts[0].sink.gain.value, 0);
  assert.equal(fixture.capture.getState().echoCancellation, true);
  assert.equal(fixture.capture.getState().autoGainControl, false);
  const staleMessage = fixture.nodes[0].port.onmessage;
  await fixture.capture.stop(); await fixture.capture.stop();
  staleMessage({data: {type: 'pcm', samples: new Float32Array(48000)}});
  assert.equal(fixture.capture.getState().status, 'idle');
  assert.equal(fixture.streams[0].track.stops, 1);
  assert.equal(fixture.contexts[0].closes, 1);
  assert.equal(fixture.nodes[0].port.closes, 1);
});

test('stop during microphone permission then restart isolates the late stream', async () => {
  const firstMedia = deferred(); let calls = 0;
  const oldStream = fakeStream(), newStream = fakeStream();
  const fixture = browserFixture({media: () => ++calls === 1 ? firstMedia.promise : Promise.resolve(newStream)});
  const oldStart = fixture.capture.start();
  await fixture.capture.stop();
  assert.equal(await fixture.capture.start(), true);
  firstMedia.resolve(oldStream);
  assert.equal(await oldStart, false);
  assert.equal(oldStream.track.stops, 1);
  assert.equal(newStream.track.stops, 0);
  assert.equal(fixture.capture.getState().status, 'listening');
  await fixture.capture.stop();
});

for (const stage of ['addModule', 'resume']) {
  test(`stop during ${stage} then restart cannot revive stale startup`, async () => {
    const pending = deferred(); let calls = 0;
    const fixture = browserFixture({[stage]: () => ++calls === 1 ? pending.promise : Promise.resolve()});
    const oldStart = fixture.capture.start(); await tick();
    await fixture.capture.stop();
    assert.equal(await fixture.capture.start(), true);
    pending.resolve();
    assert.equal(await oldStart, false);
    assert.equal(fixture.contexts[0].closes, 1);
    assert.equal(fixture.contexts[1].closes, 0);
    assert.equal(fixture.capture.getState().status, 'listening');
    await fixture.capture.stop();
  });
}

test('stopping from the startup notification never allocates resources', async () => {
  let capture;
  const fixture = browserFixture({onState: state => { if (state.status === 'starting') void capture.stop(); }});
  capture = fixture.capture;
  assert.equal(await capture.start(), false);
  assert.equal(fixture.contexts.length, 0);
  assert.equal(fixture.constraints.length, 0);
});

test('pending utterance is bounded across stop/restart and receives cancellation', async () => {
  const pending = deferred(); const deliveries = [];
  const fixture = browserFixture({onUtterance: async (blob, metadata) => {
    deliveries.push({blob, metadata}); if (deliveries.length === 1) await pending.promise;
  }});
  await fixture.capture.start(); fixture.utterance();
  assert.equal(deliveries.length, 1);
  assert.equal(fixture.capture.getState().pending, true);
  fixture.utterance(); assert.equal(deliveries.length, 1);
  await fixture.capture.stop();
  assert.equal(deliveries[0].metadata.signal.aborted, true);
  await fixture.capture.start(); fixture.utterance();
  assert.equal(deliveries.length, 1);
  assert.equal(fixture.capture.getState().pending, true);
  pending.resolve(); await tick();
  assert.equal(fixture.capture.getState().status, 'listening');
  fixture.utterance(); await tick();
  assert.equal(deliveries.length, 2);
  assert.equal(deliveries[1].metadata.signal.aborted, false);
  assert.equal(deliveries[1].metadata.preRollMs, 0, 'Pending audio must not enter the next clip.');
  await fixture.capture.stop();
});

test('failed delivery releases the gate and capture continues', async () => {
  let calls = 0;
  const fixture = browserFixture({onUtterance: async () => { calls++; throw new Error('fixture STT failure'); }});
  await fixture.capture.start(); fixture.utterance(); await tick();
  assert.equal(fixture.capture.getState().pending, false);
  assert.equal(fixture.capture.getState().status, 'listening');
  fixture.utterance(); await tick();
  assert.equal(calls, 2); assert.equal(fixture.errors.length, 2);
  await fixture.capture.stop();
});

test('a failed processing notification cannot lock delivery across restart', async () => {
  let calls = 0, throws = true;
  const fixture = browserFixture({onUtterance: async () => { calls++; }, onState: state => {
    if (state.status === 'processing' && throws) { throws = false; throw new Error('fixture state update failed'); }
  }});
  await fixture.capture.start(); fixture.utterance(); await tick();
  assert.equal(fixture.capture.getState().pending, false);
  assert.equal(fixture.errors.length, 1);
  await fixture.capture.stop(); await fixture.capture.start();
  fixture.utterance(); await tick();
  assert.equal(calls, 1);
  assert.equal(fixture.capture.getState().status, 'listening');
  await fixture.capture.stop();
});

for (const reason of ['track-ended', 'processor-error']) {
  test(`${reason} releases the session and allows retry`, async () => {
    const fixture = browserFixture();
    await fixture.capture.start();
    if (reason === 'track-ended') fixture.streams[0].track.end();
    else fixture.nodes[0].onprocessorerror();
    await tick();
    assert.equal(fixture.capture.getState().status, 'error');
    assert.equal(fixture.capture.getState().active, false);
    assert.equal(fixture.errors.length, 1);
    assert.equal(fixture.contexts[0].closes, 1);
    assert.equal(await fixture.capture.start(), true);
    await fixture.capture.stop();
  });
}

test('denied microphone permission and rejected close remain retryable', async () => {
  let calls = 0;
  const fixture = browserFixture({media: () => ++calls === 1 ? Promise.reject(new Error('Permission denied')) : Promise.resolve(fakeStream()),
    close: () => Promise.reject(new Error('Already closed'))});
  assert.equal(await fixture.capture.start(), false);
  assert.equal(fixture.capture.getState().status, 'error');
  assert.equal(fixture.contexts[0].closes, 1);
  assert.equal(fixture.errors.length, 1);
  assert.equal(await fixture.capture.start(), true);
  await fixture.capture.stop();
});

test('injected stream and context factories support saved-audio browser fixtures', async () => {
  const fixture = browserFixture();
  let requested = 0, contexts = 0;
  const stream = fakeStream();
  const capture = fixture.browser.MistTalkCapture.create({getUserMedia: async () => { requested++; return stream; },
    audioContextFactory: () => { contexts++; return new fixture.browser.AudioContext(); }});
  assert.equal(requested, 0); assert.equal(contexts, 0);
  assert.equal(await capture.start(), true);
  assert.equal(fixture.constraints.length, 0);
  assert.equal(requested, 1); assert.equal(contexts, 1);
  await capture.stop(); assert.equal(stream.track.stops, 1);
});

test('worklet batches actual quantum sizes into 20ms PCM and never outputs microphone audio', () => {
  let Processor;
  const messages = [];
  class Base { constructor() { this.port = {postMessage: (value, transfers) => messages.push({value, transfers})}; } }
  const worklet = {sampleRate: 48000, AudioWorkletProcessor: Base,
    registerProcessor: (name, value) => { assert.equal(name, 'mist-talk-capture'); Processor = value; }};
  vm.createContext(worklet); vm.runInContext(workletSource, worklet);
  const processor = new Processor({processorOptions: {batchMs: 20}});
  for (const size of [128, 128, 192, 256, 256]) {
    const first = new Float32Array(size).fill(0.2), second = new Float32Array(size).fill(0.4);
    const output = new Float32Array(size).fill(1);
    assert.equal(processor.process([[first, second]], [[output]]), true);
    assert.ok(output.every(value => value === 0));
  }
  assert.equal(messages.length, 1);
  assert.equal(messages[0].value.samples.length, 960);
  assert.ok(messages[0].value.samples.every(value => Math.abs(value - 0.3) < 0.00001));
  assert.equal(messages[0].transfers[0], messages[0].value.samples.buffer);
  processor.port.onmessage({data: {type: 'stop'}});
  assert.equal(processor.process([], []), false);
});

function streamingFixture(sampleRate = 48000, extra = {}) {
  const events = [], chunks = [], utterances = [];
  const detector = createDetector({sampleRate,
    onStreamStart: metadata => events.push({type: 'start', metadata}),
    onStreamData: (samples, metadata) => { events.push({type: 'data', metadata}); chunks.push(samples); },
    onStreamEnd: metadata => events.push({type: 'end', metadata}),
    onStreamCancel: metadata => events.push({type: 'cancel', metadata}),
    onUtterance: value => { events.push({type: 'wav', metadata: value.metadata}); utterances.push(value); }, ...extra});
  return {detector, events, chunks, utterances};
}
function concatenate(chunks) {
  const joined = new Float32Array(chunks.reduce((sum, samples) => sum + samples.length, 0));
  let offset = 0;
  for (const chunk of chunks) { joined.set(chunk, offset); offset += chunk.length; }
  return joined;
}

for (const sampleRate of [16000, 44100, 48000]) {
  test(`confirmed stream exactly matches completed WAV at ${sampleRate}Hz`, async () => {
    const {detector, events, chunks, utterances} = streamingFixture(sampleRate);
    feed(detector, 500, 0.001, false, sampleRate);
    assert.equal(events.length, 0, 'Idle PCM must never leave the detector.');
    feed(detector, 80, 0.05, false, sampleRate);
    assert.equal(events.length, 0);
    feed(detector, 10, 0.05, false, sampleRate);
    assert.equal(events[0].type, 'start');
    assert.equal(concatenate(chunks).length, Math.round(sampleRate * 0.29));
    feed(detector, 310, 0.06, false, sampleRate, 173);
    feed(detector, 650, 0, false, sampleRate, 257);
    assert.equal(utterances.length, 1);
    assert.deepEqual(events.slice(-2).map(event => event.type), ['end', 'wav']);
    assert.equal(events.filter(event => event.type === 'start').length, 1);
    assert.equal(events.filter(event => event.type === 'cancel').length, 0);
    const samples = concatenate(chunks);
    assert.deepEqual(Array.from(samples), Array.from(utterances[0].samples));
    assert.deepEqual(await encodeWav(samples, sampleRate).arrayBuffer(),
      await encodeWav(utterances[0].samples, sampleRate).arrayBuffer());
    const id = utterances[0].metadata.utteranceId;
    assert.ok(typeof id === 'string' && id.length > 0);
    assert.ok(events.every(event => event.metadata.utteranceId === id));
    assert.equal(events.at(-2).metadata.trailingSilenceMs, 650);
    assert.equal(events.at(-2).metadata.preRollMs, 200);
  });
}

test('unconfirmed noise emits no streaming callbacks and short confirmed noise cancels', () => {
  const {detector, events, utterances} = streamingFixture();
  feed(detector, 80, 0.05); feed(detector, 800);
  assert.equal(events.length, 0);
  feed(detector, 240, 0.05); feed(detector, 650);
  assert.equal(events[0].type, 'start');
  assert.equal(events.at(-1).type, 'cancel');
  assert.equal(events.at(-1).metadata.reason, 'too-short');
  assert.equal(events.filter(event => event.type === 'end').length, 0);
  assert.equal(utterances.length, 0);
});

test('playback streaming waits for stronger confirmation and replays its full onset', () => {
  const {detector, events, chunks, utterances} = streamingFixture();
  feed(detector, 300, 0.001, true);
  feed(detector, 210, 0.05, true);
  assert.equal(events.length, 0);
  feed(detector, 10, 0.05, true);
  assert.equal(events[0].metadata.bargeIn, true);
  assert.equal(concatenate(chunks).length, 48000 * 0.42);
  feed(detector, 100, 0.05); feed(detector, 650);
  assert.deepEqual(Array.from(concatenate(chunks)), Array.from(utterances[0].samples));
});

test('stream data copies protect the fallback WAV from mutation and buffer transfer', () => {
  let delivered;
  const detector = createDetector({sampleRate: 48000,
    onStreamData: samples => { samples.fill(0); structuredClone(samples, {transfer: [samples.buffer]}); },
    onUtterance: value => { delivered = value; }});
  feed(detector, 300, 0.05); feed(detector, 650);
  assert.ok(delivered.samples.some(value => Math.abs(value) > 0.04));
  assert.equal(delivered.samples.length, 48000 * 0.95);
});

for (const terminal of ['start', 'data', 'before-end', 'end']) {
  test(`reset from stream ${terminal} prevents further data and WAV delivery`, () => {
    let detector;
    const events = [];
    const stop = () => detector.reset('fixture-stop');
    detector = createDetector({sampleRate: 48000,
      onActivity: active => { if (!active && terminal === 'before-end') stop(); },
      onStreamStart: metadata => { events.push('start'); if (terminal === 'start') stop(); },
      onStreamData: samples => { events.push('data'); if (terminal === 'data') stop(); },
      onStreamEnd: metadata => { events.push('end'); if (terminal === 'end') stop(); },
      onStreamCancel: metadata => events.push('cancel'), onUtterance: value => events.push('wav')});
    const whole = new Float32Array(48000);
    for (let i = 0; i < 14400; i++) whole[i] = i % 2 ? 0.05 : -0.05;
    detector.push(whole);
    assert.equal(events.includes('wav'), false);
    if (terminal === 'start') assert.deepEqual(events, ['start', 'cancel']);
    if (terminal === 'data') assert.deepEqual(events, ['start', 'data', 'cancel']);
    if (terminal === 'before-end') { assert.equal(events.at(-1), 'cancel'); assert.equal(events.includes('end'), false); }
    if (terminal === 'end') { assert.equal(events.at(-1), 'end'); assert.equal(events.includes('cancel'), false); }
  });
}

test('capture stop cancels old stream once and stale PCM cannot reopen it', async () => {
  const events = [], deliveries = [];
  const fixture = browserFixture({onStreamStart: metadata => events.push({type: 'start', metadata}),
    onStreamData: (samples, metadata) => events.push({type: 'data', metadata}),
    onStreamEnd: metadata => events.push({type: 'end', metadata}),
    onStreamCancel: metadata => events.push({type: 'cancel', metadata}),
    onUtterance: (blob, metadata) => deliveries.push(metadata)});
  await fixture.capture.start(); fixture.pcm(300, 0.05);
  const stale = fixture.nodes[0].port.onmessage;
  await fixture.capture.stop(); await fixture.capture.stop();
  assert.equal(events.at(-1).type, 'cancel');
  assert.equal(events.at(-1).metadata.reason, 'stopped');
  assert.equal(events.at(-1).metadata.signal.aborted, true);
  assert.equal(events.at(-1).metadata.echoCancellation, true);
  const eventCount = events.length, firstId = events[0].metadata.utteranceId;
  stale({data: {type: 'pcm', samples: new Float32Array(48000)}});
  assert.equal(events.length, eventCount);
  assert.equal(deliveries.length, 0);
  await fixture.capture.start(); fixture.utterance(); await tick();
  assert.equal(deliveries.length, 1);
  assert.notEqual(deliveries[0].utteranceId, firstId);
  assert.equal(events.filter(event => event.type === 'cancel').length, 1);
  assert.equal(events.at(-1).type, 'end');
  assert.equal(events.at(-1).metadata.utteranceId, deliveries[0].utteranceId);
  await fixture.capture.stop();
});

test('stream duration cap includes a partial final frame exactly once', () => {
  const {detector, chunks, events, utterances} = streamingFixture(48000, {config: {maxDurationMs: 1005}});
  feed(detector, 200); feed(detector, 810, 0.05);
  assert.equal(utterances.length, 1);
  assert.equal(utterances[0].metadata.durationMs, 1005);
  assert.equal(events.at(-2).metadata.reason, 'max-duration');
  assert.deepEqual(Array.from(concatenate(chunks)), Array.from(utterances[0].samples));
  assert.equal(chunks.at(-1).length, 240);
});

for (const stage of ['start', 'data']) {
  test(`stream ${stage} failure cancels transport once and preserves the WAV fallback`, () => {
    const events = [], errors = [], utterances = [];
    let throws = true;
    const detector = createDetector({sampleRate: 48000,
      onStreamStart: metadata => { events.push('start'); if (stage === 'start' && throws) { throws = false; throw new Error('fixture start failed'); } },
      onStreamData: samples => { events.push('data'); if (stage === 'data' && throws) { throws = false; throw new Error('fixture data failed'); } },
      onStreamEnd: metadata => events.push('end'),
      onStreamCancel: metadata => { events.push('cancel'); assert.equal(metadata.reason, 'callback-error'); },
      onStreamError: error => errors.push(error), onUtterance: value => utterances.push(value)});
    feed(detector, 300, 0.05); feed(detector, 650);
    assert.equal(errors.length, 1);
    assert.equal(utterances.length, 1);
    assert.equal(events.filter(value => value === 'cancel').length, 1);
    assert.equal(events.includes('end'), false);
    feed(detector, 300, 0.05); feed(detector, 650);
    assert.equal(utterances.length, 2);
    assert.equal(events.at(-1), 'end');
    assert.equal(events.filter(value => value === 'cancel').length, 1);
  });
}

test('pending WAV handoff prevents new streams, including after stop/restart', async () => {
  const pending = deferred(), starts = [], ends = [], delivered = [];
  const fixture = browserFixture({onStreamStart: metadata => starts.push(metadata.utteranceId),
    onStreamData: () => {}, onStreamEnd: metadata => ends.push(metadata.utteranceId),
    onUtterance: async (blob, metadata) => { delivered.push(metadata.utteranceId); if (delivered.length === 1) await pending.promise; }});
  await fixture.capture.start(); fixture.utterance();
  assert.deepEqual(starts, ends); assert.deepEqual(ends, delivered);
  fixture.utterance(); assert.equal(starts.length, 1);
  await fixture.capture.stop(); await fixture.capture.start(); fixture.utterance();
  assert.equal(starts.length, 1);
  pending.resolve(); await tick(); fixture.utterance(); await tick();
  assert.equal(starts.length, 2); assert.deepEqual(starts, delivered);
  await fixture.capture.stop();
});

for (const {name, run} of tests) {
  await run();
  console.log(`PASS: ${name}`);
}
console.log(`PASS: ${tests.length} talk capture tests`);
