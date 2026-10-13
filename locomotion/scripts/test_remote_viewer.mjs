// Run: node --test locomotion/scripts/test_remote_viewer.mjs
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';

test('the live CAD view has its own animation canvas instead of a state-poll image stream', () => {
  const html = readFileSync(new URL('../sim_remote.html', import.meta.url), 'utf8');
  assert.match(html, /<canvas[^>]+id="viewer"/);
  assert.match(html, /type="module"[^>]+src="\/viewer\/main\.mjs"/);
});

function pose(time, x, epoch = 1, quaternion = [0, 0, 0, 1]) {
  return {version: 1, epoch, sequence: Math.round(time * 50), time_s: time,
    links: [{index: -1, position: [x, 0, .16], quaternion}]};
}

test('20 Hz poses produce distinct positions at each 60 Hz display frame', async () => {
  const {PoseTimeline} = await import('../viewer/pose_timeline.mjs');
  const timeline = new PoseTimeline({delayMs: 80});
  for (let i = 0; i <= 6; i++) timeline.push(pose(i * .05, i * .005), i * 50);
  const samples = [300, 316.6667, 333.3333].map(now => timeline.sample(now).links[0].position[0]);
  assert.ok(samples[0] < samples[1] && samples[1] < samples[2]);
  assert.ok(Math.abs(samples[1] - .02366667) < 1e-6);
});

test('a delayed snapshot does not extrapolate the CAD past measured physics', async () => {
  const {PoseTimeline} = await import('../viewer/pose_timeline.mjs');
  const timeline = new PoseTimeline();
  timeline.push(pose(0, 0), 0); timeline.push(pose(.05, .005), 50);
  assert.equal(timeline.sample(900).links[0].position[0], .005);
  assert.equal(timeline.ageMs(900), 850);
});

test('episode changes discard poses from the previous robot model', async () => {
  const {PoseTimeline} = await import('../viewer/pose_timeline.mjs');
  const timeline = new PoseTimeline();
  timeline.push(pose(1, .1), 1000); timeline.push(pose(0, -.2, 2), 1050);
  assert.equal(timeline.sample(1060).epoch, 2);
  assert.equal(timeline.sample(1060).links[0].position[0], -.2);
  assert.equal(timeline.length, 1);
});

test('rotation interpolation takes the short path across quaternion sign changes', async () => {
  const {PoseTimeline} = await import('../viewer/pose_timeline.mjs');
  const timeline = new PoseTimeline({delayMs: 0});
  timeline.push(pose(0, 0, 1, [0, 0, 0, 1]), 0);
  timeline.push(pose(.05, .005, 1, [0, 0, 0, -1]), 50);
  const q = timeline.sample(25).links[0].quaternion;
  assert.ok(Math.abs(q[3]) > .999999);
  assert.ok(Math.abs(Math.hypot(...q) - 1) < 1e-9);
});

test('out-of-order and malformed poses leave the last valid model pose intact', async () => {
  const {PoseTimeline} = await import('../viewer/pose_timeline.mjs');
  const timeline = new PoseTimeline();
  timeline.push(pose(.1, .01), 100);
  assert.equal(timeline.push(pose(.05, .005), 110), false);
  assert.equal(timeline.push({...pose(.2, .02), links: [{index: -1, position: [NaN, 0, 0], quaternion: [0, 0, 0, 1]}]}, 120), false);
  assert.equal(timeline.sample(130).links[0].position[0], .01);
});
