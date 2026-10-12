'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const runtime = require('./runtime.js');
const catalog = require('../acting_studies_v1/catalog.json');

function layer(file, name) {
  return { file, x: name === 'rightEye' ? 317 : name === 'mouth' ? 218 : 95,
    y: name === 'mouth' ? 230 : 110, width: name === 'mouth' ? 76 : 100,
    height: name === 'mouth' ? 40 : 90 };
}
function fixture(group, item) {
  const key = group.id + '/' + item.id;
  const frames = Array.from({ length: 12 }, (_, index) => ({ index,
    exposureTicks: [2, 1, 1, 2, 1, 3, 5, 3, 2, 1, 1, 2][index],
    layers: Object.fromEntries(runtime.LAYERS.map(name => [name, layer(`${key}/${name}_${index}.png`, name)]))
  }));
  frames[0].layers.mouth.file = 'shared/mouth_0.png';
  frames[11].layers = structuredClone(frames[0].layers);
  const blinkFrames = Array.from({ length: 7 }, (_, index) => ({ index, exposureTicks: 1,
    layers: Object.fromEntries(['leftEye', 'rightEye'].map(name => [name,
      index === 0 || index === 6 ? frames[0].layers[name]
        : layer(index === 3 ? `shared/closed_${name}.png` : `${key}/blink_${name}_${index}.png`, name)]))
  }));
  return { id: item.id, key, width: 512, height: 320, restMs: 1000, frames, blinkFrames };
}
const examples = catalog.groups.flatMap(group => group.examples.map(item => fixture(group, item)));
const manifest = { version: 3, groups: [{ id: 'fixture', examples }] };
function mockAssets(items = examples) {
  const images = new Map();
  for (const example of items) for (const frame of [...example.frames, ...example.blinkFrames]) {
    for (const value of Object.values(frame.layers)) images.set(value.file, {
      file: value.file, naturalWidth: value.width, naturalHeight: value.height
    });
  }
  return { images, disposed: false };
}
function context(width = 1024, height = 640) {
  const calls = [], stack = [];
  return {
    canvas: { width, height }, calls, globalAlpha: .3, globalCompositeOperation: 'multiply',
    save() { calls.push(['save']); stack.push([this.globalAlpha, this.globalCompositeOperation]); },
    restore() { calls.push(['restore']); [this.globalAlpha, this.globalCompositeOperation] = stack.pop(); },
    setTransform(...args) { calls.push(['transform', ...args]); },
    clearRect(...args) { calls.push(['clear', ...args]); },
    drawImage(image, ...args) { calls.push(['draw', image.file, this.globalAlpha, this.globalCompositeOperation, ...args]); }
  };
}
function drawn(ctx) { return ctx.calls.filter(call => call[0] === 'draw'); }
function fileFromUrl(url) { return new URL(url).pathname.replace(/^\/(?:review\/)?/, ''); }

test('18 original IDs resolve from controlled model intents and canonical keys', () => {
  assert.equal(examples.length, 18);
  assert.equal(new Set(Object.values(runtime.INTENTS)).size, 18);
  for (const example of examples) {
    assert.equal(runtime.resolveExpression(example.id, manifest), example.key);
    assert.equal(runtime.resolveExpression(example.key, manifest), example.key);
  }
  assert.equal(runtime.resolveExpression(' Double take '), 'mickey/double_take');
  assert.throws(() => runtime.resolveExpression('invent a happy face'), /Unknown expression/);
  for (const key of ['constructor', 'toString', '__proto__']) {
    assert.throws(() => runtime.resolveExpression(key), /Unknown expression/);
  }
  assert.throws(() => runtime.resolveExpression('delight', { groups: [] }), /not present/);
});

test('all 306 directed transitions use separate blink clips and exact resting endpoints', () => {
  const assets = mockAssets();
  let pairs = 0;
  for (const source of examples) for (const target of examples) {
    if (source === target) continue;
    pairs++;
    const plan = runtime.transitionPlan(source, target);
    assert.equal(plan.length, 12);
    assert.ok(plan.every(step => step.eyes.clip === 'blink'));
    assert.deepEqual(plan[0].eyes, { side: 'source', frame: 0, clip: 'blink' });
    assert.deepEqual(plan[11].eyes, { side: 'target', frame: 6, clip: 'blink' });
    for (const [endpoint, expected] of [[0, source], [1, target]]) {
      const direct = context(), transition = context();
      runtime.drawFrame(direct, expected, 0, assets);
      runtime.drawTransition(transition, source, target, endpoint, assets);
      assert.deepEqual(transition.calls, direct.calls, `${source.key} → ${target.key}, ${endpoint}`);
    }
  }
  assert.equal(pairs, 306);
});

test('closed handoff uses identical files and coordinates, never unrelated action frame3', () => {
  const assets = mockAssets();
  const before = context(), after = context();
  runtime.drawTransition(before, examples[0], examples[1], 4 / 12, assets, { layers: ['leftEye', 'rightEye'] });
  runtime.drawTransition(after, examples[0], examples[1], 5 / 12, assets, { layers: ['leftEye', 'rightEye'] });
  assert.deepEqual(before.calls, after.calls);
  assert.ok(drawn(before).every(call => call[1].startsWith('shared/closed_')));
  const invalid = structuredClone(examples[1]);
  invalid.blinkFrames[3].layers.leftEye.x++;
  assert.throws(() => runtime.transitionPlan(examples[0], invalid), /identical shared closed/);
});

test('shared resting mouth stays one opaque contour during every transition step', () => {
  const assets = mockAssets();
  for (let index = 0; index < 12; index++) {
    const ctx = context();
    runtime.drawTransition(ctx, examples[0], examples[1], index / 12, assets, { layers: ['mouth'] });
    assert.equal(drawn(ctx).length, 1);
    assert.deepEqual(drawn(ctx)[0].slice(1, 4), ['shared/mouth_0.png', 1, 'source-over']);
  }
  const invalid = structuredClone(examples[0]);
  invalid.frames[0].layers.mouth.file = 'different-mouth.png';
  assert.throws(() => runtime.transitionPlan(examples[0], invalid), /identical shared resting mouth/);
});

test('all acting exposure boundaries and loop/rest boundaries honor authored timings', () => {
  const example = examples[0];
  const clock = runtime.timeline(example);
  let start = 0;
  for (let index = 0; index < 12; index++) {
    assert.equal(runtime.frameAt(start, example), index);
    assert.equal(runtime.frameAt(start + clock.durations[index] - .001, example), index);
    assert.ok(Math.abs(runtime.frameStartMs(example, index) - start) < 1e-6);
    start += clock.durations[index];
  }
  assert.equal(runtime.frameAt(clock.activeMs, example), 0);
  assert.equal(runtime.frameAt(clock.totalMs - .001, example), 0);
  assert.equal(runtime.frameAt(clock.totalMs + clock.durations[0], example), 1);
  assert.equal(runtime.frameAt(-1, example), 0);
  assert.equal(runtime.cycleDurationMs(example), clock.totalMs);
  assert.equal(runtime.frameAt(clock.activeMs, { ...example, restMs: 0 }), 0);
});

test('speed controls scale only acting exposure, leaving rest duration unchanged', () => {
  const normal = runtime.timeline(examples[0]);
  for (const fps of [8, 12, 7.5, 30]) {
    const clock = runtime.timeline(examples[0], fps);
    assert.ok(Math.abs(clock.activeMs - normal.activeMs * 15 / fps) < 1e-6);
    assert.equal(clock.restMs, 1000);
    for (let index = 0; index < 12; index++) {
      assert.equal(runtime.frameAt(runtime.frameStartMs(examples[0], index, fps), examples[0], fps), index);
    }
  }
});

test('durationMs-only clips work and inconsistent or invalid timing fails clearly', () => {
  const example = structuredClone(examples[0]);
  example.frames.forEach((frame, index) => { delete frame.exposureTicks; frame.durationMs = 30 + index * 10; });
  assert.equal(runtime.frameAt(29, example), 0);
  assert.equal(runtime.frameAt(30, example), 1);
  example.frames[0].exposureTicks = 1;
  assert.throws(() => runtime.timeline(example), /disagree/);
  delete example.frames[0].exposureTicks;
  example.frames[0].durationMs = 0;
  assert.throws(() => runtime.timeline(example), /greater than zero/);
  delete example.frames[0].durationMs;
  assert.throws(() => runtime.timeline(example), /authored/);
  assert.throws(() => runtime.frameAt(NaN, examples[0]), /finite/);
  assert.throws(() => runtime.timeline(examples[0], 0), /FPS/);
  assert.throws(() => runtime.timeline({ ...examples[0], restMs: -1 }), /Rest/);
});

test('independent blink finishes open, never loops automatically or consumes acting time', () => {
  const example = examples[0];
  const duration = runtime.blinkDurationMs(example);
  assert.ok(Math.abs(duration - 7000 / 15) < 1e-6);
  for (let index = 0; index < 7; index++) assert.equal(runtime.blinkAt(index * 1000 / 15, example), index);
  assert.equal(runtime.blinkAt(duration + 5000, example), 6);
  assert.equal(runtime.blinkAt(-50, example), 0);
  assert.ok(Math.abs(runtime.blinkDurationMs(example, 7.5) - duration * 2) < 1e-6);
  const ctx = context();
  runtime.drawBlink(ctx, example, 3, mockAssets(), { mouthFrame: 8 });
  assert.deepEqual(drawn(ctx).map(call => call[1]), [
    'shared/closed_leftEye.png', 'shared/closed_rightEye.png', `${example.key}/mouth_8.png`
  ]);
});

test('acting layers retain independently selectable frames and shared fixed rig fitting', () => {
  const ctx = context(1024, 800);
  runtime.drawFrame(ctx, examples[0], 7, mockAssets(), { leftEyeFrame: 2, rightEyeFrame: 5, mouthFrame: 10 });
  assert.deepEqual(drawn(ctx).map(call => call[1]), [
    `${examples[0].key}/leftEye_2.png`, `${examples[0].key}/rightEye_5.png`, `${examples[0].key}/mouth_10.png`
  ]);
  assert.deepEqual(drawn(ctx)[0].slice(4), [190, 300, 200, 180]);
  assert.deepEqual(drawn(ctx)[1].slice(4), [634, 300, 200, 180]);
  assert.deepEqual(drawn(ctx)[2].slice(4), [436, 540, 152, 80]);
});

test('hidden layers clear correctly and missing artwork does not destroy prior canvas', () => {
  const assets = mockAssets();
  const empty = context();
  runtime.drawFrame(empty, examples[0], 0, assets, { layers: [] });
  assert.equal(drawn(empty).length, 0);
  assert.equal(empty.calls.filter(call => call[0] === 'clear').length, 1);
  assert.equal(empty.globalAlpha, .3);
  assert.equal(empty.globalCompositeOperation, 'multiply');
  assert.throws(() => runtime.drawFrame(context(), examples[0], 0, assets, { layers: ['eyebrows'] }), /Layers/);
  assets.images.delete(examples[0].frames[0].layers.mouth.file);
  const ctx = context();
  assert.throws(() => runtime.drawFrame(ctx, examples[0], 0, assets), /Missing decoded/);
  assert.equal(ctx.calls.length, 0);
  assets.disposed = true;
  assert.throws(() => runtime.drawBlink(context(), examples[0], 3, assets), /not available/);
});

test('schema rejects variable rig dimensions, missing blink clips and mismatched open anchors', () => {
  const example = structuredClone(examples[0]);
  runtime.validateExample(example);
  assert.throws(() => runtime.validateExample({ ...example, height: 342 }), /shared 512/);
  assert.throws(() => runtime.validateExample({ ...example, frames: example.frames.slice(1) }), /12 acting/);
  assert.throws(() => runtime.validateExample({ ...example, blinkFrames: undefined }), /7 separate/);
  example.blinkFrames[0].layers.leftEye = { ...example.blinkFrames[0].layers.leftEye, x: 96 };
  assert.throws(() => runtime.validateExample(example), /blink endpoints/);
  example.frames[1].layers.mouth.x = -1;
  assert.throws(() => runtime.validateExample(example), /bounds/);
  const badLoop = structuredClone(examples[0]);
  badLoop.frames[11].layers.rightEye.x++;
  assert.throws(() => runtime.validateExample(badLoop), /acting loop must return/);
});

test('transition clock covers twelve bins and clamps requested endpoints', () => {
  for (let index = 0; index < 12; index++) assert.equal(runtime.stepAtProgress(index / 12), index);
  assert.equal(runtime.stepAtProgress(-2), 0);
  assert.equal(runtime.stepAtProgress(2), 11);
  assert.throws(() => runtime.stepAtProgress(NaN), /finite/);
});

test('preload includes all blink images, deduplicates sources and bounds parallel decoding', async () => {
  const single = { groups: [{ examples: [examples[0], examples[0]] }] };
  const images = mockAssets([examples[0]]).images;
  let active = 0, peak = 0, calls = 0, closed = 0;
  const assets = await runtime.preload(single, 'https://example.test/review/', {
    concurrency: 4,
    async loadImage(url) {
      calls++; active++; peak = Math.max(peak, active);
      await new Promise(resolve => setImmediate(resolve));
      active--;
      assert.equal(new URL(url).searchParams.get('asset'), '3');
      return { ...images.get(fileFromUrl(url)), close() { closed++; } };
    }
  });
  assert.equal(calls, images.size);
  assert.equal(peak, 4);
  assert.equal(assets.images.size, images.size);
  assert.ok(assets.images.has('shared/closed_leftEye.png'));
  assets.dispose(); assets.dispose();
  assert.equal(closed, images.size);
  assert.equal(assets.images.size, 0);
  assert.equal(assets.disposed, true);
});

test('preload cleans both valid and wrongly sized decoded assets on failure', async () => {
  const images = mockAssets([examples[0]]).images;
  let closed = 0;
  await assert.rejects(runtime.preload({ groups: [{ examples: [examples[0]] }] }, 'https://example.test/', {
    async loadImage(url) {
      const file = fileFromUrl(url);
      if (file.endsWith('leftEye_0.png')) throw new Error('404');
      const image = { ...images.get(file), close() { closed++; } };
      if (file.endsWith('mouth_0.png')) image.naturalWidth = 1;
      return image;
    }
  }), error => {
    assert.equal(error.assets.length, 2);
    assert.ok(error.assets.some(item => item.message === '404'));
    assert.ok(error.assets.some(item => item.message.includes('dimensions')));
    return true;
  });
  assert.equal(closed, images.size - 1);
});

test('matching artwork hashes share one decoded image across file aliases and close only once', async () => {
  const example = structuredClone(examples[0]);
  const original = example.frames[1].layers.leftEye;
  const alias = example.frames[2].layers.leftEye;
  original.sha256 = alias.sha256 = 'a'.repeat(64);
  const images = mockAssets([example]).images;
  let loaded = 0, closed = 0;
  const assets = await runtime.preload({ groups: [{ examples: [example] }] }, 'https://example.test/', {
    async loadImage(url) {
      loaded++;
      const file = fileFromUrl(url);
      if (file === original.file) assert.equal(new URL(url).searchParams.get('asset'), original.sha256);
      return { ...images.get(file), close() { closed++; } };
    }
  });
  assert.equal(loaded, images.size - 1);
  assert.equal(assets.decodedCount, loaded);
  assert.equal(assets.images.size, images.size);
  assert.equal(assets.images.get(original.file), assets.images.get(alias.file));
  assets.dispose(); assets.dispose();
  assert.equal(closed, loaded);
});

test('preload fails incompatible closed anchors and shared file sizes before decoding', async () => {
  await assert.rejects(runtime.preload({ groups: [] }, 'https://example.test/'), /no groups/);
  const example = structuredClone(examples[0]);
  example.blinkFrames[3].layers.rightEye.file = 'different-closed.png';
  await assert.rejects(runtime.preload({ groups: [{ examples: [examples[1], example] }] }, 'https://example.test/'), /identical shared/);
  const invalid = structuredClone(examples[0]);
  invalid.frames[1].layers.leftEye.file = invalid.frames[0].layers.leftEye.file;
  invalid.frames[1].layers.leftEye.width--;
  await assert.rejects(runtime.preload({ groups: [{ examples: [invalid] }] }, 'https://example.test/'), /Conflicting dimensions/);
});

const builtPath = path.join(__dirname, 'manifest.json');
const builtManifest = fs.existsSync(builtPath) ? JSON.parse(fs.readFileSync(builtPath, 'utf8')) : null;
test('real compiled manifest has all18 expressions, shared anchors and existing images', {
  skip: !builtManifest || builtManifest.complete === false ? 'Composer has not completed artwork yet.' : false
}, () => {
  const built = JSON.parse(fs.readFileSync(builtPath, 'utf8'));
  const compiled = built.groups.flatMap(group => group.examples);
  assert.equal(compiled.length, 18);
  const checked = new Set();
  for (const example of compiled) {
    runtime.validateExample(example);
    runtime.transitionPlan(compiled[0], example);
    for (const frame of [...example.frames, ...example.blinkFrames]) {
      for (const value of Object.values(frame.layers)) {
        const filePath = path.join(__dirname, value.file);
        assert.ok(fs.existsSync(filePath), value.file);
        if (checked.has(value.file)) continue;
        checked.add(value.file);
        const bytes = fs.readFileSync(filePath);
        assert.deepEqual([...bytes.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10], value.file);
        assert.equal(bytes.readUInt32BE(16), value.width, value.file);
        assert.equal(bytes.readUInt32BE(20), value.height, value.file);
        if (value.sha256) assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), value.sha256, value.file);
      }
    }
  }
});
