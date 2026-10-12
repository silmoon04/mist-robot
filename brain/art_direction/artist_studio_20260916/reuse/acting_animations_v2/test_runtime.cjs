'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const runtime = require('./runtime.js');
const studies = require('../acting_studies_v1/manifest.json');

// Canvas calls and decoded images are test doubles only; no artwork is fabricated.
function fixture(group, example, width = 384, height = 342) {
  const key = `${group.id}/${example.id}`;
  const midX = width / 2;
  const splitY = Math.floor(height * .6);
  return {
    id: example.id, key, width, height, restMs: 1000,
    frames: Array.from({ length: 12 }, (_, index) => ({
      index,
      layers: {
        leftEye: { file: `${key}/leftEye_${index}.png`, x: 0, y: 0, width: midX, height: splitY },
        rightEye: { file: `${key}/rightEye_${index}.png`, x: midX, y: 0, width: midX, height: splitY },
        mouth: { file: `${key}/mouth_${index}.png`, x: 0, y: splitY, width, height: height - splitY }
      }
    }))
  };
}
const examples = studies.groups.flatMap(group => group.examples.map(example => fixture(group, example)));
const manifest = { version: 2, groups: [{ id: 'test', examples }] };

function mockAssets(examplesToLoad = examples) {
  const images = new Map();
  for (const example of examplesToLoad) for (const frame of example.frames) {
    for (const layer of Object.values(frame.layers)) images.set(layer.file, {
      file: layer.file, naturalWidth: layer.width, naturalHeight: layer.height
    });
  }
  return { images, disposed: false };
}

function context(width = 768, height = 684) {
  const calls = [];
  const stack = [];
  return {
    canvas: { width, height }, calls, globalAlpha: .3,
    globalCompositeOperation: 'multiply',
    save() { calls.push(['save']); stack.push([this.globalAlpha, this.globalCompositeOperation]); },
    restore() {
      calls.push(['restore']);
      [this.globalAlpha, this.globalCompositeOperation] = stack.pop();
    },
    setTransform(...args) { calls.push(['transform', ...args]); },
    clearRect(...args) { calls.push(['clear', ...args]); },
    drawImage(image, ...args) { calls.push(['draw', image.file, this.globalAlpha, ...args]); }
  };
}
function drawn(ctx) { return ctx.calls.filter(call => call[0] === 'draw'); }

test('fixtures cover every original example exactly once', () => {
  assert.equal(examples.length, 18);
  assert.equal(new Set(examples.map(example => example.key)).size, 18);
});

test('all 306 directed transitions have exactly 12 steps and exact source/target endpoints', () => {
  const assets = mockAssets();
  let pairs = 0;
  for (const source of examples) for (const target of examples) {
    if (source === target) continue;
    pairs++;
    const plan = runtime.transitionPlan(source, target);
    assert.equal(plan.length, 12);
    assert.deepEqual(plan.map(step => step.index), Array.from({ length: 12 }, (_, i) => i));
    assert.deepEqual(plan[0].eyes, { side: 'source', frame: 0 });
    assert.deepEqual(plan[11].eyes, { side: 'target', frame: 0 });
    const originalStart = context();
    const transitionStart = context();
    const originalEnd = context();
    const transitionEnd = context();
    runtime.drawFrame(originalStart, source, 0, assets);
    runtime.drawTransition(transitionStart, source, target, 0, assets);
    runtime.drawFrame(originalEnd, target, 0, assets);
    runtime.drawTransition(transitionEnd, source, target, 1, assets);
    assert.deepEqual(transitionStart.calls, originalStart.calls, `${source.key} start`);
    assert.deepEqual(transitionEnd.calls, originalEnd.calls, `${target.key} end`);
  }
  assert.equal(pairs, 306);
});

test('closed-eye handoff never crossfades or transforms eye shapes', () => {
  const plan = runtime.transitionPlan(examples[0], examples[1]);
  const handoff = plan.findIndex(step => step.phase === 'closed-handoff');
  assert.equal(plan[handoff - 1].eyes.frame, 3);
  assert.equal(plan[handoff - 1].eyes.side, 'source');
  assert.equal(plan[handoff].eyes.frame, 3);
  assert.equal(plan[handoff].eyes.side, 'target');
  const assets = mockAssets();
  for (let i = 0; i < 12; i++) {
    const ctx = context();
    runtime.drawTransition(ctx, examples[0], examples[1], i / 11, assets);
    const eyes = drawn(ctx).filter(call => !call[1].includes('mouth'));
    assert.equal(eyes.length, 2);
    assert.ok(eyes.every(call => call[2] === 1));
    assert.deepEqual(ctx.calls.filter(call => call[0] === 'transform'), [['transform', 1, 0, 0, 1, 0, 0]]);
  }
});

test('mouth blends independently, briefly, while endpoints remain unblended', () => {
  const plan = runtime.transitionPlan(examples[0], examples[1]);
  assert.equal(plan[0].mouth.targetWeight, 0);
  assert.equal(plan[11].mouth.targetWeight, 1);
  assert.equal(plan.filter(step => step.mouth.targetWeight > 0 && step.mouth.targetWeight < 1).length, 3);
  const ctx = context();
  runtime.drawTransition(ctx, examples[0], examples[1], 5 / 12, mockAssets());
  assert.deepEqual(drawn(ctx).filter(call => call[1].includes('mouth')).map(call => call[2]), [.5, .5]);
});

test('identical mouth pixels retain opacity at the blend midpoint while eyes remain unchanged', () => {
  const ctx = context();
  const pixels = { leftEye: 0, rightEye: 0, mouth: 0 };
  const operations = [];
  ctx.clearRect = () => { for (const layer of Object.keys(pixels)) pixels[layer] = 0; };
  ctx.drawImage = function (image) {
    const layer = runtime.LAYERS.find(name => image.file.includes(name));
    const sourceAlpha = this.globalAlpha;
    const destinationAlpha = pixels[layer];
    operations.push([layer, this.globalCompositeOperation]);
    if (this.globalCompositeOperation === 'lighter') {
      pixels[layer] = Math.min(1, sourceAlpha + destinationAlpha);
    } else {
      pixels[layer] = sourceAlpha + destinationAlpha * (1 - sourceAlpha);
    }
  };
  runtime.drawTransition(ctx, examples[0], examples[0], 5 / 12, mockAssets());
  assert.deepEqual(pixels, { leftEye: 1, rightEye: 1, mouth: 1 });
  assert.deepEqual(operations, [
    ['leftEye', 'source-over'], ['rightEye', 'source-over'],
    ['mouth', 'source-over'], ['mouth', 'lighter']
  ]);
});

test('frame clock advances at 15 fps and holds frame0 for the specified rest', () => {
  const example = examples[0];
  for (let i = 0; i < 12; i++) {
    assert.equal(runtime.frameAt(i * 1000 / 15, example), i);
    assert.equal(runtime.frameAt((i + .999) * 1000 / 15, example), i);
  }
  assert.equal(runtime.frameAt(800, example), 0);
  assert.equal(runtime.frameAt(1799, example), 0);
  assert.equal(runtime.frameAt(1800, example), 0);
  assert.equal(runtime.frameAt(1800 + 1000 / 15, example), 1);
  assert.equal(runtime.frameAt(-10, example), 0);
});

test('frame clock supports speed changes and a zero-length rest', () => {
  assert.equal(runtime.frameAt(11 * 1000 / 30, examples[0], 30), 11);
  assert.equal(runtime.frameAt(400, examples[0], 30), 0);
  assert.equal(runtime.frameAt(800 + 1000 / 15, { restMs: 0 }), 1);
  assert.throws(() => runtime.frameAt(0, examples[0], 0), /FPS/);
  assert.throws(() => runtime.frameAt(NaN, examples[0]), /finite/);
  assert.throws(() => runtime.frameAt(0, { restMs: -1 }), /Rest/);
});

test('transition clock includes all 12 bins and clamps endpoints', () => {
  for (let i = 0; i < 12; i++) assert.equal(runtime.stepAtProgress(i / 12), i);
  assert.equal(runtime.stepAtProgress(1), 11);
  assert.equal(runtime.stepAtProgress(-1), 0);
  assert.equal(runtime.stepAtProgress(2), 11);
  assert.throws(() => runtime.stepAtProgress(NaN), /finite/);
});

test('left eye, right eye and mouth can be advanced independently', () => {
  const ctx = context();
  runtime.drawFrame(ctx, examples[0], 7, mockAssets(), { leftEyeFrame: 2, rightEyeFrame: 5, mouthFrame: 10 });
  assert.deepEqual(drawn(ctx).map(call => call[1]), [
    `${examples[0].key}/leftEye_2.png`, `${examples[0].key}/rightEye_5.png`, `${examples[0].key}/mouth_10.png`
  ]);
});

test('layers can be hidden individually, including a fully empty canvas', () => {
  const assets = mockAssets();
  for (const layer of runtime.LAYERS) {
    const ctx = context();
    runtime.drawFrame(ctx, examples[0], 0, assets, { layers: [layer] });
    assert.equal(drawn(ctx).length, 1);
    assert.ok(drawn(ctx)[0][1].includes(layer));
  }
  const ctx = context();
  runtime.drawFrame(ctx, examples[0], 0, assets, { layers: [] });
  assert.equal(drawn(ctx).length, 0);
  assert.equal(ctx.calls.filter(call => call[0] === 'clear').length, 1);
  assert.throws(() => runtime.drawFrame(context(), examples[0], 0, assets, { layers: ['unknown'] }), /Layers/);
});

test('canvas is cleared before drawing and context state is restored', () => {
  const ctx = context();
  runtime.drawFrame(ctx, examples[0], 0, mockAssets());
  assert.deepEqual(ctx.calls.slice(0, 3), [['save'], ['transform', 1, 0, 0, 1, 0, 0], ['clear', 0, 0, 768, 684]]);
  assert.equal(ctx.calls.at(-1)[0], 'restore');
  assert.equal(ctx.globalAlpha, .3);
  assert.equal(ctx.globalCompositeOperation, 'multiply');
});

test('contain fitting preserves aspect ratio and the exact layer positions', () => {
  const ctx = context(1000, 342);
  runtime.drawFrame(ctx, examples[0], 0, mockAssets());
  assert.deepEqual(drawn(ctx)[0].slice(3), [308, 0, 192, 205]);
  assert.deepEqual(drawn(ctx)[1].slice(3), [500, 0, 192, 205]);
  assert.deepEqual(drawn(ctx)[2].slice(3), [308, 205, 384, 137]);
});

test('differently sized examples keep each endpoint pixel-identical to drawFrame', () => {
  const source = examples[0];
  const target = fixture({ id: 'odd' }, { id: 'dimensions' }, 512, 300);
  const assets = mockAssets([source, target]);
  const a = context(); const b = context();
  runtime.drawFrame(a, target, 0, assets);
  runtime.drawTransition(b, source, target, 1, assets);
  assert.deepEqual(a.calls, b.calls);
});

test('missing artwork fails before changing the existing canvas', () => {
  const assets = mockAssets();
  assets.images.delete(examples[0].frames[0].layers.mouth.file);
  const ctx = context();
  assert.throws(() => runtime.drawFrame(ctx, examples[0], 0, assets), /Missing decoded artwork/);
  assert.equal(ctx.calls.length, 0);
  assets.disposed = true;
  assert.throws(() => runtime.drawFrame(ctx, examples[0], 0, assets), /not available/);
});

test('manifest validation rejects missing frames and invalid layer rectangles', () => {
  const example = structuredClone(examples[0]);
  example.frames.pop();
  assert.throws(() => runtime.validateExample(example), /exactly 12/);
  const invalid = structuredClone(examples[0]);
  invalid.frames[2].layers.leftEye.x = -1;
  assert.throws(() => runtime.validateExample(invalid), /bounds/);
  delete invalid.frames[2].layers.leftEye;
  assert.throws(() => runtime.validateExample(invalid), /missing leftEye/);
});

test('preload decodes each unique layer once with bounded concurrency', async () => {
  const single = { groups: [{ examples: [examples[0], examples[0]] }] };
  const images = mockAssets([examples[0]]).images;
  let active = 0; let peak = 0; let calls = 0;
  const assets = await runtime.preload(single, 'https://example.test/review/', {
    concurrency: 4,
    async loadImage(url) {
      active++; peak = Math.max(peak, active); calls++;
      await new Promise(resolve => setImmediate(resolve));
      active--;
      const file = url.replace('https://example.test/review/', '');
      return images.get(file);
    }
  });
  assert.equal(calls, 36);
  assert.equal(assets.images.size, 36);
  assert.equal(peak, 4);
  assert.equal(assets.baseUrl, 'https://example.test/review/');
  assets.dispose();
  assert.equal(assets.disposed, true);
  assert.equal(assets.images.size, 0);
  assets.dispose();
});

test('preload reports missing and incorrectly sized artwork instead of placeholder frames', async () => {
  const single = { groups: [{ examples: [examples[0]] }] };
  const images = mockAssets([examples[0]]).images;
  await assert.rejects(runtime.preload(single, 'https://example.test/', {
    async loadImage(url) {
      const file = url.replace('https://example.test/', '');
      if (file.endsWith('leftEye_0.png')) throw new Error('404');
      if (file.endsWith('mouth_0.png')) return { width: 1, height: 1 };
      return images.get(file);
    }
  }), error => {
    assert.equal(error.assets.length, 2);
    assert.ok(error.assets.some(item => item.message === '404'));
    assert.ok(error.assets.some(item => item.message.includes('dimensions')));
    return true;
  });
});

test('preload rejects an empty manifest and conflicting file dimensions', async () => {
  await assert.rejects(runtime.preload({ groups: [] }, 'https://example.test/'), /no groups/);
  const example = structuredClone(examples[0]);
  example.frames[1].layers.leftEye.file = example.frames[0].layers.leftEye.file;
  example.frames[1].layers.leftEye.width--;
  await assert.rejects(runtime.preload({ groups: [{ examples: [example] }] }, 'https://example.test/'), /Conflicting dimensions/);
});

const builtManifestPath = path.join(__dirname, 'manifest.json');
const builtManifest = fs.existsSync(builtManifestPath) ? JSON.parse(fs.readFileSync(builtManifestPath, 'utf8')) : null;
test('real compiled artwork satisfies runtime contracts', {
  skip: !builtManifest || builtManifest.complete === false ? 'Generated artwork is still being compiled.' : false
}, () => {
  const built = JSON.parse(fs.readFileSync(builtManifestPath, 'utf8'));
  const compiled = built.groups.flatMap(group => group.examples);
  assert.equal(compiled.length, 18);
  for (const example of compiled) {
    runtime.validateExample(example);
    for (const frame of example.frames) for (const layer of Object.values(frame.layers)) {
      assert.ok(fs.existsSync(path.join(__dirname, layer.file)), layer.file);
    }
  }
});
