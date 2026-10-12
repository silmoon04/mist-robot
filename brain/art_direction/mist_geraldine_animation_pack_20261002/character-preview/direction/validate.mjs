import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const read = async name => JSON.parse(await readFile(new URL(name, import.meta.url), 'utf8'));
const fixtures = await read('./scenes.json');
const timing = await read('./timing-profiles.json');
const source = await read(fixtures.clipSource);
const manifest = await read('../../site/asset-manifest.json');
const presets = new Set(manifest.presets.map(p => p.id));
assert.equal(fixtures.scenes.length, 3);
assert.equal(new Set(fixtures.scenes.map(s => s.id)).size, 3);
assert.deepEqual(fixtures.scenes.map(s => s.audio.clipId).sort(), source.clips.map(c => c.id).sort());
for (const scene of fixtures.scenes) {
  const clip = source.clips.find(c => c.id === scene.audio.clipId);
  assert.equal(scene.audio.textRef, `clips[id=${clip.id}].text`);
  assert.ok(scene.context.startsWith('Synthetic scene:'));
  assert.ok(scene.audio.startMs >= 0 && scene.audio.startMs < scene.durationMs);
  let prior = -1;
  let intent;
  for (const event of scene.events) {
    assert.ok(Number.isFinite(event.atMs) && event.atMs >= prior && event.atMs < scene.durationMs);
    prior = event.atMs;
    assert.ok(['context', 'state', 'intent', 'reaction', 'interrupt'].includes(event.type));
    if (event.type === 'context') {
      assert.equal(event.payload.synthetic, true);
      assert.ok(['user', 'context'].includes(event.payload.speaker));
    }
    if (event.type === 'state') assert.ok(['listening', 'thinking', 'speaking'].includes(event.payload.state));
    if (event.type === 'intent') intent = event.payload.faceId;
    if (['intent', 'reaction'].includes(event.type)) assert.ok(presets.has(event.payload.faceId));
    if (event.type === 'reaction') {
      assert.ok(intent);
      assert.equal(event.payload.returnToIntent, true);
      for (const profile of timing.profiles) {
        const duration = profile[event.payload.durationKey];
        assert.ok(Number.isFinite(duration) && duration >= timing.transitionMs);
        assert.ok(event.atMs + duration <= scene.durationMs);
      }
    }
  }
  let added = 0;
  let previousGap = -1;
  for (const gap of scene.audio.packetGaps) {
    assert.ok(gap.atClipMs > previousGap && gap.atClipMs < clip.duration * 1000);
    assert.ok(gap.durationMs > 0);
    const cue = clip.cues.findLast(c => c.time * 1000 <= gap.atClipMs);
    assert.equal(cue.viseme, 'rest');
    previousGap = gap.atClipMs;
    added += gap.durationMs;
  }
  assert.ok(scene.events.some(e => e.type === 'interrupt') || scene.audio.startMs + clip.duration * 1000 + added <= scene.durationMs);
}
assert.equal(timing.selectionStatus, 'provisional');
assert.equal(timing.profiles.length, 2);
assert.ok(timing.profiles.some(p => p.id === timing.defaultProfile));
assert.equal(timing.eyePolicy.mode, 'idle');
console.log('PASS: three unique native clips, verbatim transcript references, valid presets, ordered scene events, finite profile holds, and silent packet-gap position.');
