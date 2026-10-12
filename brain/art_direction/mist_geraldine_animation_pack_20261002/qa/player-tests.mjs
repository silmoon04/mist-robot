import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  FPS, FRAME_MS, TRANSITION_MS, EYE_FRAMES, MOUTH_FRAMES,
  canonicalViseme, normalizeCues, rawVisemeAt, mouthAt,
  createFaceState, requestPreset, sampleFace, stopFace,
  audibleContextTime, audiblePositionMs
} from '../site/state.mjs';
import { AtlasRenderer, validateManifest, SharedClock, SpeechPlayer, createFrameLoop } from '../site/player.mjs';

const contract = JSON.parse(await readFile(new URL('../production-contract.json', import.meta.url), 'utf8'));
const presets = contract.presets;
const failures = [];
let passed = 0;
let edgeCount = 0;
let scrubCount = 0;
const EPSILON = 0.001;

async function test(name, check) {
  try {
    await check();
    passed++;
  } catch (error) {
    failures.push({ name, error });
    console.error(`FAIL ${name}: ${error.message}`);
  }
}

function close(actual, expected, label = '') {
  assert.ok(Math.abs(actual - expected) < 0.000001, `${label}: expected ${expected}, got ${actual}`);
}

function legalPose(pose) {
  assert.ok(presets.some(preset => preset.id === pose.presetId), `Unknown preset ${pose.presetId}`);
  assert.ok(contract.eyeAtlas.families.includes(pose.eyeFamily), `Unknown eye family ${pose.eyeFamily}`);
  assert.ok(contract.mouthAtlas.families.includes(pose.mouthFamily), `Unknown mouth family ${pose.mouthFamily}`);
  assert.ok(EYE_FRAMES.includes(pose.eyeFrame), `Unknown eye cel ${pose.eyeFrame}`);
  assert.ok(MOUTH_FRAMES.includes(pose.mouthFrame), `Unknown mouth cel ${pose.mouthFrame}`);
}

const longVowel = [{ startMs: 0, endMs: 3000, viseme: 'AA' }];
const speechAt = (positionMs, cues = longVowel, playing = true) => ({ playing, positionMs, cues });
const quiet = { quiet: true };

await test('contract timing and native cel names', () => {
  assert.equal(presets.length, 13);
  assert.equal(FPS, contract.timing.fps);
  assert.equal(FPS, 15);
  assert.equal(TRANSITION_MS, contract.timing.transitionMs);
  close(FRAME_MS, 1000 / 15, '15 fps frame duration');
  assert.deepEqual(EYE_FRAMES, contract.eyeAtlas.frames);
  assert.deepEqual(MOUTH_FRAMES, contract.mouthAtlas.frames);
});

for (const source of presets) {
  for (const target of presets) {
    if (source.id === target.id) continue;
    edgeCount++;
    await test(`directed edge ${source.id} -> ${target.id}, every transition frame`, () => {
      const start = 1000;
      const state = createFaceState(presets, source.id);
      const before = sampleFace(state, start, quiet);
      requestPreset(state, target.id, start, null, quiet);
      assert.equal(state.requestCount, 1);
      assert.deepEqual(state.transition.source, before);
      for (let frame = 0; frame <= 6; frame++) {
        const at = start + frame * FRAME_MS;
        const pose = sampleFace(state, at, quiet);
        legalPose(pose);
        assert.equal(pose.presetId, target.id);
        assert.equal(pose.mouthFamily, target.mouth);
        assert.equal(pose.mouthFrame, target.rest);
        assert.equal(pose.phase, frame < 6 ? 'transition' : 'hold');
        assert.deepEqual(sampleFace(state, at, quiet), pose, 'Repeated sampling must be deterministic');
        if (source.eyes === target.eyes) {
          assert.equal(pose.eyeFamily, target.eyes);
          assert.equal(pose.eyeFrame, 'rest');
        } else {
          const expected = [
            [source.eyes, 'half'], [source.eyes, 'closed'], ['attentive', 'closed'],
            [target.eyes, 'closed'], [target.eyes, 'opening-low'], [target.eyes, 'opening'],
            [target.eyes, 'rest']
          ][frame];
          assert.deepEqual([pose.eyeFamily, pose.eyeFrame], expected);
        }
      }
      assert.equal(sampleFace(state, start + TRANSITION_MS - EPSILON, quiet).phase, 'transition');
      const final = sampleFace(state, start + TRANSITION_MS, quiet);
      assert.equal(final.phase, 'hold');
      assert.equal(final.eyeFamily, target.eyes);
      assert.equal(final.mouthFamily, target.mouth);
    });

    await test(`mid-speech edge ${source.id} -> ${target.id}, bounded mouth switch`, () => {
      const start = 1000;
      const position = 200;
      const state = createFaceState(presets, source.id);
      requestPreset(state, target.id, start, speechAt(position), quiet);
      const deadline = state.transition.mouthAtMs;
      assert.ok(deadline <= start + TRANSITION_MS);
      assert.equal(deadline, source.mouth === target.mouth ? start : start + TRANSITION_MS);
      for (let frame = 0; frame <= 8; frame++) {
        const elapsed = frame * FRAME_MS;
        const pose = sampleFace(state, start + elapsed, { ...quiet, speech: speechAt(position + elapsed) });
        legalPose(pose);
        assert.equal(pose.presetId, target.id);
        assert.equal(pose.mouthFamily, start + elapsed < deadline ? source.mouth : target.mouth);
      }
      if (source.mouth !== target.mouth) {
        assert.equal(sampleFace(state, deadline, { ...quiet, speech: speechAt(position + TRANSITION_MS) }).mouthFrame, 'MBP');
        assert.equal(sampleFace(state, deadline + FRAME_MS + EPSILON, { ...quiet, speech: speechAt(position + TRANSITION_MS + FRAME_MS) }).mouthFrame, 'release');
        assert.equal(sampleFace(state, deadline + 2 * FRAME_MS + EPSILON, { ...quiet, speech: speechAt(position + TRANSITION_MS + 2 * FRAME_MS) }).mouthFrame, 'AA');
      }
    });
  }
}

await test('unknown preset rejects without changing state', () => {
  const state = createFaceState(presets, 'attentive');
  const before = structuredClone(state);
  assert.throws(() => requestPreset(state, 'missing', 10), /Unknown face preset/);
  assert.deepEqual(state, before);
  assert.throws(() => createFaceState(presets, 'missing'), /Unknown face preset/);
});

await test('same ID and repeated requests preserve the original deadline', () => {
  const state = createFaceState(presets, 'attentive');
  assert.equal(requestPreset(state, 'attentive', 200), state);
  assert.equal(state.requestCount, 0);
  assert.equal(state.transition, null);
  requestPreset(state, 'considering', 300, speechAt(100), quiet);
  const transition = state.transition;
  const snapshot = structuredClone(transition);
  for (const now of [300, 301, 367, 499, 699, 700, 900]) {
    assert.equal(requestPreset(state, 'considering', now, speechAt(100 + now - 300), quiet), state);
    assert.equal(state.transition, transition);
    assert.deepEqual(state.transition, snapshot);
    assert.equal(state.requestCount, 1);
  }
});

for (const elapsed of [0, FRAME_MS / 2, FRAME_MS, 2 * FRAME_MS, 3 * FRAME_MS, 4 * FRAME_MS, 5 * FRAME_MS, 399]) {
  await test(`interrupted A -> B -> C at ${elapsed.toFixed(3)} ms`, () => {
    const state = createFaceState(presets, 'skeptical');
    const start = 1000;
    requestPreset(state, 'concerned', start, speechAt(100), quiet);
    const now = start + elapsed;
    const before = sampleFace(state, now, { ...quiet, speech: speechAt(100 + elapsed) });
    requestPreset(state, 'laughing', now, speechAt(100 + elapsed), quiet);
    assert.deepEqual(state.transition.source, before, 'The new source must be the currently sampled pose');
    const immediate = sampleFace(state, now, { ...quiet, speech: speechAt(100 + elapsed) });
    assert.equal(immediate.eyeFamily, before.eyeFamily);
    assert.equal(immediate.mouthFamily, state.transition.mouthAtMs <= now ? 'friendly' : before.mouthFamily);
    if (before.mouthFrame === 'MBP') assert.equal(immediate.mouthFrame, 'MBP', 'Interrupting at a safe closure must preserve that closure');
    assert.equal(state.requestCount, 2);
    for (let frame = 0; frame <= 7; frame++) {
      const pose = sampleFace(state, now + frame * FRAME_MS, { ...quiet, speech: speechAt(100 + elapsed + frame * FRAME_MS) });
      legalPose(pose);
      assert.equal(pose.presetId, 'laughing', 'A superseded target cannot return');
    }
    const final = sampleFace(state, now + TRANSITION_MS, quiet);
    assert.deepEqual([final.eyeFamily, final.mouthFamily, final.mouthFrame, final.phase], ['laughing', 'friendly', 'AA', 'hold']);
  });
}

await test('repeated interruptions preserve the original forced closure deadline and release', () => {
  const state = createFaceState(presets, 'skeptical');
  const start = 1000;
  requestPreset(state, 'concerned', start, speechAt(100), quiet);
  const closureUntil = start + TRANSITION_MS + FRAME_MS;
  requestPreset(state, 'laughing', start + 399, speechAt(499), quiet);
  close(state.transition.preservedClosureUntilMs, closureUntil);
  requestPreset(state, 'considering', start + 430, speechAt(530), quiet);
  close(state.transition.preservedClosureUntilMs, closureUntil);
  const poseAt = now => sampleFace(state, now, { ...quiet, speech: speechAt(100 + now - start) });
  assert.equal(poseAt(closureUntil - EPSILON).mouthFrame, 'MBP');
  assert.equal(poseAt(closureUntil).mouthFrame, 'release');
  assert.equal(poseAt(closureUntil + FRAME_MS - EPSILON).mouthFrame, 'release');
  assert.equal(poseAt(closureUntil + FRAME_MS + EPSILON).mouthFrame, 'AA');
});

await test('source/common/target closed bridge remains closed across both family changes', () => {
  const state = createFaceState(presets, 'skeptical');
  requestPreset(state, 'concerned', 0, null, { ...quiet, bridgeFamily: 'attentive' });
  for (const [frame, family] of [[1, 'skeptical'], [2, 'attentive'], [3, 'concerned']]) {
    const pose = sampleFace(state, frame * FRAME_MS, quiet);
    assert.equal(pose.eyeFrame, 'closed');
    assert.equal(pose.eyeFamily, family);
  }
  for (const boundary of [2 * FRAME_MS, 3 * FRAME_MS]) {
    assert.equal(sampleFace(state, boundary - EPSILON * 2, quiet).eyeFrame, 'closed');
    assert.equal(sampleFace(state, boundary + EPSILON, quiet).eyeFrame, 'closed');
  }
});

await test('same eye family retains its blink schedule during a mouth-only request', () => {
  const baseline = createFaceState(presets, 'attentive');
  const changed = createFaceState(presets, 'attentive');
  let blinkAt;
  for (let now = 3000; now < 6000; now++) {
    if (sampleFace(baseline, now).eyeFrame === 'half') { blinkAt = now; break; }
  }
  assert.ok(Number.isFinite(blinkAt));
  requestPreset(changed, 'quiet-listening', blinkAt, speechAt(100));
  for (let frame = 0; frame <= 12; frame++) {
    const now = blinkAt + frame * FRAME_MS;
    assert.equal(sampleFace(changed, now).eyeFrame, sampleFace(baseline, now).eyeFrame);
  }
});

await test('idle blink uses four native cels over the contract 267 ms', () => {
  assert.equal(Math.round(FRAME_MS * 4), contract.timing.blinkMs);
  for (const preset of presets) {
    const state = createFaceState(presets, preset.id);
    let firstHalf;
    for (let now = 3000; now < 6000; now++) {
      if (sampleFace(state, now).eyeFrame === 'half') { firstHalf = now; break; }
    }
    assert.ok(Number.isFinite(firstHalf), `${preset.id} must reach its first blink`);
    for (const [frame, expected] of ['half', 'closed', 'opening-low', 'opening', 'rest-after-blink'].entries()) {
      assert.equal(sampleFace(state, firstHalf + frame * FRAME_MS + EPSILON).eyeFrame, expected);
    }
    assert.equal(sampleFace(state, firstHalf + 5 * FRAME_MS + EPSILON).eyeFrame, 'rest');
  }
});

const safeSwitches = [
  ['current MBP', [{ startMs: 0, endMs: 600, viseme: 'MBP' }], 100, 0],
  ['current rest', [{ startMs: 0, endMs: 600, viseme: 'rest' }], 100, 0],
  ['current gap', [{ startMs: 0, endMs: 50, viseme: 'AA' }, { startMs: 400, endMs: 800, viseme: 'AA' }], 100, 0],
  ['next MBP', [{ startMs: 0, endMs: 200, viseme: 'AA' }, { startMs: 200, endMs: 350, viseme: 'MBP' }, { startMs: 350, endMs: 800, viseme: 'AA' }], 100, 100],
  ['next rest', [{ startMs: 0, endMs: 250, viseme: 'AA' }, { startMs: 250, endMs: 300, viseme: 'rest' }, { startMs: 300, endMs: 800, viseme: 'AA' }], 100, 150],
  ['next gap', [{ startMs: 0, endMs: 220, viseme: 'AA' }, { startMs: 300, endMs: 800, viseme: 'AA' }], 100, 120],
  ['safe boundary at deadline', [{ startMs: 0, endMs: 500, viseme: 'AA' }, { startMs: 500, endMs: 800, viseme: 'MBP' }], 100, 400],
  ['safe boundary after deadline', [{ startMs: 0, endMs: 501, viseme: 'AA' }, { startMs: 501, endMs: 800, viseme: 'MBP' }], 100, 400]
];
for (const [name, cues, position, wait] of safeSwitches) {
  await test(`mouth family uses ${name}`, () => {
    const start = 1000;
    const state = createFaceState(presets, 'attentive');
    requestPreset(state, 'considering', start, speechAt(position, cues), quiet);
    close(state.transition.mouthAtMs, start + wait, name);
    assert.equal(state.transition.forcedMouth, name === 'safe boundary after deadline');
    if (wait > 0) {
      assert.equal(sampleFace(state, start + wait - EPSILON, { ...quiet, speech: speechAt(position + wait - EPSILON, cues) }).mouthFamily, 'friendly');
    }
    assert.equal(sampleFace(state, start + wait, { ...quiet, speech: speechAt(position + wait, cues) }).mouthFamily, 'dry');
  });
}

for (const preset of presets) {
  await test(`preset rest and silence ${preset.id}`, () => {
    const state = createFaceState(presets, preset.id);
    for (const [options, expectedRest] of [
      [quiet, preset.rest],
      [{ ...quiet, speech: speechAt(10, [], false) }, preset.rest],
      [{ ...quiet, speech: speechAt(10, []) }, 'rest'],
      [{ ...quiet, speech: speechAt(10, [{ startMs: 0, endMs: 100, viseme: 'rest' }]) }, 'rest'],
      [{ ...quiet, speech: { ...speechAt(0, [], false), active: true } }, 'rest']
    ]) {
      const pose = sampleFace(state, 0, options);
      assert.equal(pose.mouthFrame, expectedRest);
      assert.equal(pose.mouthFamily, preset.mouth);
    }
  });
  for (let frame = 0; frame < 12; frame++) {
    scrubCount++;
    await test(`scrub ${preset.id} cel ${frame}`, () => {
      const state = createFaceState(presets, preset.id);
      const pose = sampleFace(state, 9876, { scrubFrame: frame, speech: speechAt(200) });
      legalPose(pose);
      assert.deepEqual([pose.eyeFamily, pose.eyeFrame, pose.mouthFamily, pose.mouthFrame, pose.phase], [preset.eyes, EYE_FRAMES[frame], preset.mouth, MOUTH_FRAMES[frame], 'scrub']);
      assert.deepEqual(sampleFace(state, 1, { scrubFrame: frame, speech: speechAt(200) }), pose);
    });
  }
}

await test('scrub clamps to the authored first and last cells', () => {
  const state = createFaceState(presets, 'attentive');
  assert.equal(sampleFace(state, 0, { scrubFrame: -10 }).eyeFrame, EYE_FRAMES[0]);
  assert.equal(sampleFace(state, 0, { scrubFrame: 99 }).mouthFrame, MOUTH_FRAMES[11]);
});

await test('cue aliases, equivalent merge, sort, duration bounds and invalid entries', () => {
  assert.equal(canonicalViseme('TH'), 'LNT');
  assert.equal(canonicalViseme('dental'), 'LNT');
  assert.equal(canonicalViseme('unknown phoneme'), 'rest');
  assert.equal(canonicalViseme(null), 'rest');
  assert.equal(canonicalViseme('small-aa'), 'small-AA');
  const cues = normalizeCues([
    { startMs: 200, endMs: 300, viseme: 'TH' },
    { startMs: 100, endMs: 200, viseme: 'AA' },
    { startMs: 0, endMs: 100, viseme: 'A' },
    { startMs: 300, endMs: 1000, viseme: 'unknown' },
    { startMs: -1, endMs: 50, viseme: 'AA' },
    { startMs: 400, endMs: 400, viseme: 'MBP' },
    { time: 'invalid', viseme: 'AA' }
  ], 400);
  assert.deepEqual(cues, [
    { startMs: 0, endMs: 200, viseme: 'AA' },
    { startMs: 200, endMs: 300, viseme: 'LNT' },
    { startMs: 300, endMs: 400, viseme: 'rest' }
  ]);
  assert.deepEqual(normalizeCues([{ time: 0.1, viseme: 'M' }, { start: 0.2, viseme: 'AA' }], 500), [
    { startMs: 100, endMs: 200, viseme: 'MBP' }, { startMs: 200, endMs: 500, viseme: 'AA' }
  ]);
});

await test('cue merge protects closures and explicit gaps', () => {
  const cues = normalizeCues([
    { startMs: 0, endMs: 100, viseme: 'AA' },
    { startMs: 100, endMs: 120, viseme: 'MBP' },
    { startMs: 120, endMs: 140, viseme: 'release' },
    { startMs: 140, endMs: 300, viseme: 'AA' },
    { startMs: 400, endMs: 600, viseme: 'AA' }
  ], 600);
  assert.deepEqual(cues.map(cue => cue.viseme), ['AA', 'MBP', 'release', 'AA', 'AA']);
  assert.equal(rawVisemeAt(cues, 99.999), 'AA');
  assert.equal(rawVisemeAt(cues, 100), 'MBP');
  assert.equal(rawVisemeAt(cues, 119.999), 'MBP');
  assert.equal(rawVisemeAt(cues, 120), 'release');
  assert.equal(rawVisemeAt(cues, 350), 'rest');
  assert.equal(mouthAt(cues, 350, 'small-AA'), 'small-AA');
  assert.equal(mouthAt(cues, 600, 'AA'), 'AA');
  for (const invalid of [-1, NaN, Infinity]) {
    assert.equal(rawVisemeAt(cues, invalid), 'rest');
    assert.equal(mouthAt(cues, invalid, 'small-AA'), 'small-AA');
  }
});

await test('short MBP holds one 15 fps frame then releases for one frame', () => {
  const cues = [{ startMs: 0, endMs: 8, viseme: 'MBP' }, { startMs: 8, endMs: 500, viseme: 'AA' }];
  for (const at of [0, 7.999, 8, FRAME_MS - EPSILON]) assert.equal(mouthAt(cues, at), 'MBP');
  for (const at of [FRAME_MS, FRAME_MS + EPSILON, 2 * FRAME_MS - EPSILON]) assert.equal(mouthAt(cues, at), 'release');
  assert.equal(mouthAt(cues, 2 * FRAME_MS), 'AA');
  const fullClosure = [{ startMs: 0, endMs: 200, viseme: 'MBP' }, { startMs: 200, endMs: 500, viseme: 'AA' }];
  assert.equal(mouthAt(fullClosure, 199.999), 'MBP');
  assert.equal(mouthAt(fullClosure, 200), 'release');
  assert.equal(mouthAt(fullClosure, 200 + FRAME_MS + EPSILON), 'AA');
});

await test('ordinary EE -> OH -> LNT targets do not gain an injected release', () => {
  for (const [eeEnd, ohEnd, lntEnd] of [[20, 40, 60], [120, 250, 390]]) {
    const cues = [
      { startMs: 0, endMs: eeEnd, viseme: 'EE' },
      { startMs: eeEnd, endMs: ohEnd, viseme: 'OH' },
      { startMs: ohEnd, endMs: lntEnd, viseme: 'LNT' }
    ];
    assert.equal(mouthAt(cues, eeEnd - EPSILON), 'EE');
    assert.equal(mouthAt(cues, eeEnd), 'OH');
    assert.equal(mouthAt(cues, eeEnd + EPSILON), 'OH');
    assert.equal(mouthAt(cues, ohEnd - EPSILON), 'OH');
    assert.equal(mouthAt(cues, ohEnd), 'LNT');
    assert.equal(mouthAt(cues, ohEnd + EPSILON), 'LNT');
    assert.equal(mouthAt(cues, lntEnd - EPSILON), 'LNT');
  }
});

await test('speech gaps close the mouth and cancellation restores the preset rest', () => {
  const state = createFaceState(presets, 'attentive');
  const cues = [{ startMs: 0, endMs: 200, viseme: 'AA' }, { startMs: 600, endMs: 900, viseme: 'EE' }];
  requestPreset(state, 'amused', 1000, speechAt(100, cues), quiet);
  assert.equal(sampleFace(state, 1200, { ...quiet, speech: speechAt(300, cues) }).mouthFrame, 'rest');
  stopFace(state, 1200);
  const pose = sampleFace(state, 1200, { ...quiet, speech: speechAt(100, cues, false) });
  assert.equal(state.transition, null);
  assert.equal(pose.presetId, 'amused');
  assert.equal(pose.mouthFrame, 'small-AA');
  assert.equal(pose.speaking, false);
});

await test('fresh output timestamp projects audible time and caps it at current context time', () => {
  const context = { currentTime: 2, outputLatency: 0.1, baseLatency: 0.03, getOutputTimestamp: () => ({ contextTime: 1.5, performanceTime: 1000 }) };
  close(audibleContextTime(context, 1100), 1.6);
  close(audibleContextTime(context, 1250), 1.75);
  close(audibleContextTime(context, 980), 1.5);
  context.getOutputTimestamp = () => ({ contextTime: 2.5, performanceTime: 1000 });
  close(audibleContextTime(context, 1100), 2);
});

for (const [name, timestamp, performanceMs] of [
  ['stale', { contextTime: 1, performanceTime: 1000 }, 1250.001],
  ['too far in future', { contextTime: 1, performanceTime: 1000 }, 979.999],
  ['zero performance time', { contextTime: 1, performanceTime: 0 }, 0],
  ['invalid context time', { contextTime: NaN, performanceTime: 1000 }, 1000],
  ['invalid performance time', { contextTime: 1, performanceTime: NaN }, 1000],
  ['missing', undefined, 1000]
]) {
  await test(`output timestamp ${name} uses latency fallback`, () => {
    close(audibleContextTime({ currentTime: 2, outputLatency: 0.1, baseLatency: 0.03, getOutputTimestamp: () => timestamp }, performanceMs), 1.9);
  });
}

await test('timestamp exception and latency fallback preference', () => {
  close(audibleContextTime({ currentTime: 2, outputLatency: 0.1, baseLatency: 0.03, getOutputTimestamp() { throw new Error('unsupported'); } }, 1000), 1.9);
  close(audibleContextTime({ currentTime: 2, outputLatency: 0, baseLatency: 0.03 }, 1000), 1.97);
  close(audibleContextTime({ currentTime: 2 }, 1000), 2);
  close(audibleContextTime({ currentTime: 0.01, outputLatency: 0.1 }, 1000), 0);
});

await test('audible position follows sample time and clips to duration', () => {
  const context = { currentTime: 2, outputLatency: 0.1 };
  close(audiblePositionMs(context, 1000, 1, 25, 2000), 925);
  close(audiblePositionMs(context, 1000, 3, 0, 2000), 0);
  close(audiblePositionMs(context, 1000, 0, 500, 1000), 1000);
  close(audiblePositionMs(context, 1000, 0, 0, 0), 0);
});

await test('scheduled audio start preserves a seek offset until it becomes audible', () => {
  close(audiblePositionMs({ currentTime: 1 }, 1000, 1.04, 400, 2000), 400);
  close(audiblePositionMs({ currentTime: 1.04 }, 1040, 1.04, 400, 2000), 400);
  close(audiblePositionMs({ currentTime: 1.14 }, 1140, 1.04, 400, 2000), 500);
});

await test('SharedClock play, repeated play, pause, offset seek and reset', () => {
  let now = 1000;
  const clock = new SharedClock(() => now);
  assert.equal(clock.time(), 0);
  assert.equal(clock.running, false);
  clock.play();
  now = 1150;
  assert.equal(clock.time(), 150);
  clock.play();
  now = 1200;
  assert.equal(clock.time(), 200);
  clock.pause();
  now = 5000;
  assert.equal(clock.time(), 200);
  clock.pause();
  assert.equal(clock.time(), 200);
  clock.offset = 7 * FRAME_MS;
  assert.equal(clock.frame(), 7);
  close(clock.time(), 7 * FRAME_MS);
  clock.play();
  now += FRAME_MS;
  close(clock.time(), 8 * FRAME_MS);
  clock.pause();
  clock.reset();
  assert.equal(clock.time(), 0);
  assert.equal(clock.running, false);
  assert.equal(clock.explicit, true);
});

await test('render frequency, pause and seek do not alter sampled face state', () => {
  let now = 0;
  const clock = new SharedClock(() => now);
  const state = createFaceState(presets, 'considering');
  clock.play();
  for (let at = 0; at < 3549; at += 17) {
    now = at;
    sampleFace(state, clock.time());
  }
  now = 3549;
  const once = sampleFace(createFaceState(presets, 'considering'), 3549);
  assert.deepEqual(sampleFace(state, clock.time()), once);
  clock.pause();
  now = 20000;
  assert.deepEqual(sampleFace(state, clock.time()), once);
  clock.offset = 2 * FRAME_MS;
  const seeked = sampleFace(state, clock.time(), { mode: 'reaction' });
  assert.equal(seeked.eyeFrame, EYE_FRAMES[2]);
  assert.deepEqual(sampleFace(state, clock.time(), { mode: 'reaction' }), seeked);
});

await test('15 fps render loop emits once per frame and skips missed frames deterministically', () => {
  let now = 0;
  const queue = [];
  const seen = [];
  const stop = createFrameLoop((time, frame) => seen.push([time, frame]), () => now, callback => queue.push(callback));
  const tick = at => { now = at; assert.ok(queue.length > 0); queue.shift()(); };
  tick(0);
  tick(FRAME_MS / 2);
  tick(FRAME_MS + EPSILON);
  tick(FRAME_MS + EPSILON);
  tick(9 * FRAME_MS + EPSILON);
  assert.deepEqual(seen.map(item => item[1]), [0, 1, 9]);
  stop();
  tick(20 * FRAME_MS);
  assert.equal(seen.length, 3);
  assert.equal(queue.length, 0);
});

function audioMock() {
  const sources = [];
  const context = {
    currentTime: 0, outputLatency: 0, baseLatency: 0, destination: {},
    async resume() {},
    createBufferSource() {
      const source = {
        stopped: false, disconnected: false, connected: false,
        connect() { this.connected = true; },
        start(...args) { this.started = args; },
        stop() { this.stopped = true; },
        disconnect() { this.disconnected = true; }
      };
      sources.push(source);
      return source;
    }
  };
  return { context, sources };
}

await test('speech snapshot is active but not playing before scheduled audible onset', async () => {
  const { context } = audioMock();
  const player = new SpeechPlayer({ contextFactory: () => context, now: () => 1000 });
  player.buffers.set('mock.wav', { duration: 2 });
  await player.play({ id: 'onset', audio: 'mock.wav', cues: [{ startMs: 0, endMs: 2000, viseme: 'AA' }] });
  for (const at of [0, player.startedAt - EPSILON / 1000]) {
    context.currentTime = at;
    const snapshot = player.snapshot();
    assert.equal(snapshot.active, true);
    assert.equal(snapshot.playing, false);
    close(snapshot.positionMs, 0);
    const pose = sampleFace(createFaceState(presets, 'amused'), 0, { ...quiet, speech: snapshot });
    assert.equal(pose.mouthFrame, 'rest');
    assert.equal(pose.speaking, false);
  }
  context.currentTime = player.startedAt;
  const audible = player.snapshot();
  assert.equal(audible.active, true);
  assert.equal(audible.playing, true);
  close(audible.positionMs, 0);
  assert.equal(sampleFace(createFaceState(presets, 'amused'), 0, { ...quiet, speech: audible }).mouthFrame, 'AA');
});

await test('mock speech pause, seek, resume and cancellation use the audible clock', async () => {
  let now = 1000;
  const { context, sources } = audioMock();
  const player = new SpeechPlayer({ contextFactory: () => context, now: () => now });
  player.buffers.set('mock.wav', { duration: 2 });
  const clip = { id: 'mock', audio: 'mock.wav', cues: [{ startMs: 0, endMs: 2000, viseme: 'AA' }] };
  assert.equal(await player.play(clip), true);
  assert.deepEqual(sources[0].started, [0.04, 0]);
  context.currentTime = 0.24;
  now = 1240;
  close(player.position(), 200);
  const pose = sampleFace(createFaceState(presets, 'attentive'), 200, { ...quiet, speech: player.snapshot() });
  assert.equal(pose.mouthFrame, 'AA');
  player.pause();
  assert.equal(player.playing, false);
  assert.equal(player.active, true);
  assert.equal(sources[0].stopped, true);
  assert.equal(sources[0].disconnected, true);
  context.currentTime = 3;
  now = 4000;
  close(player.position(), 200);
  assert.deepEqual(sampleFace(createFaceState(presets, 'attentive'), 200, { ...quiet, speech: player.snapshot() }), pose);
  assert.equal(await player.resume(), true);
  close(sources[1].started[1], 0.2);
  context.currentTime = player.startedAt;
  close(player.position(), 200);
  context.currentTime += 0.1;
  close(player.position(), 300);
  assert.equal(await player.play(clip, 1200), true);
  close(sources.at(-1).started[1], 1.2);
  context.currentTime = player.startedAt;
  close(player.position(), 1200);
  player.stop();
  assert.equal(player.active, false);
  assert.equal(player.playing, false);
  assert.equal(player.position(), 0);
  const cancelled = sampleFace(createFaceState(presets, 'amused'), 0, { ...quiet, speech: player.snapshot() });
  assert.equal(cancelled.mouthFrame, 'small-AA');
});

await test('mock speech resumed offset never moves backwards before its scheduled start', async () => {
  const { context } = audioMock();
  const player = new SpeechPlayer({ contextFactory: () => context, now: () => 1000 });
  player.buffers.set('mock.wav', { duration: 2 });
  await player.play({ id: 'seek', audio: 'mock.wav', cues: [] }, 400);
  close(player.position(), 400);
});

await test('superseded speech preparation and cancelled preparation cannot start late', async () => {
  const { context, sources } = audioMock();
  const player = new SpeechPlayer({ contextFactory: () => context });
  player.context = context;
  const pending = new Map();
  player.prepare = raw => new Promise(resolve => pending.set(raw.id, () => resolve({ ...raw, durationMs: 2000, cues: [], buffer: { duration: 2 } })));
  const first = player.play({ id: 'old' });
  const second = player.play({ id: 'new' });
  pending.get('new')();
  assert.equal(await second, true);
  pending.get('old')();
  assert.equal(await first, false);
  assert.equal(player.clip.id, 'new');
  assert.equal(sources.length, 1);
  const cancelled = player.play({ id: 'cancelled' });
  player.stop();
  pending.get('cancelled')();
  assert.equal(await cancelled, false);
  assert.equal(player.active, false);
  assert.equal(player.playing, false);
  assert.equal(sources.length, 1);
});

function donorManifest() {
  const manifest = { version: 1, fps: FPS, presets: structuredClone(presets), eyes: {}, mouths: {} };
  for (const family of contract.eyeAtlas.families) {
    manifest.eyes[family] = {
      file: `eye-${family}.png`, width: 256, height: 192, scale: 0.25,
      positions: { left: [31, 25], right: [69, 25] },
      frames: EYE_FRAMES.map(id => ({ id, source: [0, 0, 256, 192],
        left: { rect: [10, 20, 18, 24], anchor: [19, 32] },
        right: { rect: [100, 20, 18, 24], anchor: [109, 32] } }))
    };
  }
  for (const family of contract.mouthAtlas.families) {
    manifest.mouths[family] = {
      file: `mouth-${family}.png`, width: 128, height: 128, scale: 0.5, position: [50, 46],
      frames: MOUTH_FRAMES.map(id => ({ id, source: [0, 0, 128, 128], rect: [20, 30, 16, 8], anchor: [28, 34] }))
    };
  }
  manifest.eyes.laughing.frames[0].right = {
    file: 'right-eye-donor.png', width: 64, height: 48,
    rect: [12, 8, 20, 10], anchor: [22, 13], scale: 0.7
  };
  return manifest;
}

function canvasMock() {
  const draws = []; const transforms = [];
  const context = { setTransform: (...args) => transforms.push(args), clearRect() {}, fillRect() {}, drawImage: (...args) => draws.push(args) };
  return { canvas: { clientWidth: 300, width: 300, height: 192, getContext: () => context }, draws, transforms };
}

function seedImages(renderer) {
  const assets = [...Object.values(renderer.manifest.eyes), ...Object.values(renderer.manifest.mouths)];
  for (const asset of assets) renderer.images.set(asset.file, { file: asset.file });
  for (const asset of assets) for (const frame of asset.frames) for (const component of [frame, frame.left, frame.right].filter(Boolean)) {
    if (component.file) renderer.images.set(component.file, { file: component.file });
  }
  renderer.loaded = true;
}

await test('right-eye component draws donor pixels while the original left eye stays on its base sheet', () => {
  const manifest = donorManifest(); const renderer = new AtlasRenderer(manifest); seedImages(renderer);
  const { canvas, draws, transforms } = canvasMock();
  renderer.draw(canvas, { eyeFamily: 'laughing', eyeFrame: 'rest', mouthFamily: 'friendly', mouthFrame: 'rest' });
  assert.equal(draws.length, 3, 'Draw exactly one image per eye and one mouth');
  assert.equal(draws[0][0].file, 'eye-laughing.png');
  assert.equal(draws[1][0].file, 'right-eye-donor.png');
  assert.equal(draws[2][0].file, 'mouth-friendly.png');
  assert.deepEqual(draws[0].slice(1, 5), [10, 20, 18, 24], 'Retain original left crop');
  assert.deepEqual(draws[1].slice(1, 5), [12, 8, 20, 10], 'Read the donor crop');
  const expectedLeft = [28.75, 22, 4.5, 6]; const expectedRight = [62, 21.5, 14, 7];
  draws[0].slice(5).forEach((value, index) => close(value, expectedLeft[index], 'Base eye placement'));
  draws[1].slice(5).forEach((value, index) => close(value, expectedRight[index], 'Donor eye uniform scale and anchor'));
  close(transforms[0][0], transforms[0][3], 'Canvas transform must scale both axes equally');
  assert.equal(transforms[0][1], 0); assert.equal(transforms[0][2], 0);
});

await test('component file and scale take priority over frame overrides without changing the other eye', () => {
  const manifest = donorManifest();
  const frame = manifest.eyes.laughing.frames[0]; frame.file = 'frame-donor.png'; frame.width = 256; frame.height = 192; frame.scale = 0.4;
  const renderer = new AtlasRenderer(manifest); seedImages(renderer); const { canvas, draws } = canvasMock();
  renderer.draw(canvas, { eyeFamily: 'laughing', eyeFrame: 'rest', mouthFamily: 'friendly', mouthFrame: 'rest' });
  assert.equal(draws[0][0].file, 'frame-donor.png');
  assert.equal(draws[1][0].file, 'right-eye-donor.png');
  close(draws[0][7], 18 * 0.4); close(draws[0][8], 24 * 0.4);
  close(draws[1][7], 20 * 0.7); close(draws[1][8], 10 * 0.7);
});

async function withImages(dimensions, check) {
  const originalImage = globalThis.Image; const requested = [];
  globalThis.Image = class {
    set src(file) {
      this.file = file; requested.push(file);
      const size = dimensions.get(file);
      if (size) { [this.naturalWidth, this.naturalHeight] = size; queueMicrotask(() => this.onload()); }
      else queueMicrotask(() => this.onerror());
    }
  };
  try { await check(requested); }
  finally { if (originalImage === undefined) delete globalThis.Image; else globalThis.Image = originalImage; }
}

function imageDimensions(manifest) {
  const dimensions = new Map();
  for (const asset of [...Object.values(manifest.eyes), ...Object.values(manifest.mouths)]) {
    dimensions.set(asset.file, [asset.width, asset.height]);
    for (const frame of asset.frames) for (const component of [frame, frame.left, frame.right].filter(Boolean)) {
      if (component.file) dimensions.set(component.file, [component.width || frame.width || asset.width, component.height || frame.height || asset.height]);
    }
  }
  return dimensions;
}

await test('component donor files preload and deduplicate without extraAssets', async () => {
  const manifest = donorManifest();
  manifest.eyes.laughing.frames[1].right = structuredClone(manifest.eyes.laughing.frames[0].right);
  assert.equal(manifest.extraAssets, undefined);
  await withImages(imageDimensions(manifest), async requested => {
    const renderer = new AtlasRenderer(manifest); const progress = [];
    await renderer.load((loaded, total) => progress.push([loaded, total]));
    assert.equal(renderer.loaded, true);
    assert.equal(requested.filter(file => file === 'right-eye-donor.png').length, 1);
    assert.equal(requested.length, 10, 'Nine base sheets plus the component donor');
    assert.equal(renderer.images.get('right-eye-donor.png').file, 'right-eye-donor.png');
    assert.deepEqual(progress.at(-1), [10, 10]);
  });
});

await test('component donor dimensions control crop bounds instead of the larger base sheet', () => {
  for (const rect of [[55, 8, 20, 10], [12, 42, 20, 10]]) {
    const manifest = donorManifest(); manifest.eyes.laughing.frames[0].right.rect = rect;
    assert.throws(() => validateManifest(manifest), /Crop outside atlas bounds: laughing\/rest/);
  }
  assert.equal(validateManifest(donorManifest()).eyes.laughing.frames[0].right.width, 64);
});

await test('invalid declared donor dimensions are rejected rather than silently falling back', () => {
  for (const [key, value] of [['width', 0], ['height', 0], ['width', NaN], ['height', Infinity]]) {
    const manifest = donorManifest(); manifest.eyes.laughing.frames[0].right[key] = value;
    assert.throws(() => validateManifest(manifest), /override|dimension|bounds|atlas/i, `${key}=${value} must be rejected`);
  }
});

await test('invalid declared donor scales are rejected before drawing', () => {
  for (const value of [0, -0.7, NaN, Infinity]) {
    const manifest = donorManifest(); manifest.eyes.laughing.frames[0].right.scale = value;
    assert.throws(() => validateManifest(manifest), /scale|override/i, `Donor scale ${value} must be rejected`);
  }
});

await test('dimension overrides cannot permit a crop beyond an inherited base image', () => {
  for (const layer of ['component', 'frame']) {
    const manifest = donorManifest(); const frame = manifest.eyes.attentive.frames[0];
    const metadata = layer === 'component' ? frame.left : frame;
    metadata.width = 512; metadata.height = 192;
    frame.left.rect = [240, 20, 80, 24]; frame.left.anchor = [280, 32];
    assert.throws(() => validateManifest(manifest), /file|dimension|bounds|override/i, `${layer} dimensions cannot enlarge the inherited 256 px image`);
  }
});

await test('component donor image size mismatch leaves loading incomplete with the donor path', async () => {
  const manifest = donorManifest(); const dimensions = imageDimensions(manifest);
  dimensions.set('right-eye-donor.png', [256, 192]);
  await withImages(dimensions, async () => {
    const renderer = new AtlasRenderer(manifest);
    await assert.rejects(renderer.load(), /right-eye-donor\.png dimensions differ/);
    assert.equal(renderer.loaded, false);
    assert.equal(renderer.images.has('right-eye-donor.png'), false);
  });
});

await test('release manifest registers 108 cels and preloads all 11 native sheets without extraAssets', async () => {
  const manifest = JSON.parse(await readFile(new URL('../site/asset-manifest.json', import.meta.url), 'utf8'));
  delete manifest.extraAssets;
  validateManifest(manifest);
  const assets = [...Object.values(manifest.eyes), ...Object.values(manifest.mouths)];
  assert.equal(assets.reduce((count, asset) => count + asset.frames.length, 0), 108);
  const dimensions = imageDimensions(manifest);
  assert.equal(dimensions.size, 11);
  await withImages(dimensions, async requested => {
    const renderer = new AtlasRenderer(manifest);
    await renderer.load();
    assert.equal(renderer.loaded, true);
    assert.equal(requested.length, 11);
    const laughing = manifest.eyes.laughing;
    let donorCount = 0;
    for (const frame of laughing.frames) {
      const { canvas, draws } = canvasMock();
      renderer.draw(canvas, { eyeFamily: 'laughing', eyeFrame: frame.id, mouthFamily: 'friendly', mouthFrame: 'rest' });
      assert.equal(draws[0][0].file, laughing.file, `${frame.id}: preserve the original left arch`);
      assert.deepEqual(draws[0].slice(1, 5), frame.left.rect);
      assert.equal(draws[1][0].file, frame.right.file || frame.file || laughing.file);
      assert.deepEqual(draws[1].slice(1, 5), frame.right.rect);
      if (frame.right.file) {
        donorCount++;
        assert.notEqual(draws[1][0].file, draws[0][0].file, `${frame.id}: donor applies only to the right eye`);
      }
    }
    assert.ok(donorCount > 0, 'At least one laughing right-eye cel uses its registered native donor');
  });
});

await test('coverage includes every directed edge and every preset scrub cel', () => {
  assert.equal(edgeCount, 156);
  assert.equal(scrubCount, 156);
});

console.log(`Player checks: ${passed} passed, ${failures.length} failed; ${edgeCount} directed edges tested quiet and mid-speech, ${scrubCount} scrub cells.`);
if (failures.length) {
  for (const { name, error } of failures) console.error(`\n${name}\n${error.stack}`);
  process.exitCode = 1;
}
