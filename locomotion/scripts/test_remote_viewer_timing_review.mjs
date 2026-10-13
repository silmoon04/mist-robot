// Regression for repeated server snapshots: they must not rewind the display.
import assert from 'node:assert/strict';
import test from 'node:test';
import {PoseTimeline} from '../viewer/pose_timeline.mjs';

function pose(time, x) {
  return {version: 1, epoch: 'test-episode', sequence: Math.round(time * 50), time_s: time,
    links: [{index: -1, position: [x, 0, .16], quaternion: [0, 0, 0, 1]}]};
}

test('duplicate physics snapshots do not rewind the displayed robot or hide stalled physics', () => {
  const timeline = new PoseTimeline({delayMs: 80});
  for (let index = 0; index <= 6; index++) timeline.push(pose(index/20, index*.005), index*50);
  const displayed = timeline.sample(330).links[0].position[0];
  timeline.push(pose(.3, .03), 350);
  assert.ok(timeline.sample(360).links[0].position[0] >= displayed,
    'Duplicate arrival must preserve interpolation toward the last measured pose');
  timeline.push(pose(.3, .03), 400);
  timeline.push(pose(.3, .03), 450);
  assert.equal(timeline.sample(500).links[0].position[0], .03,
    'Display must reach the last measured pose after the interpolation buffer drains');
  assert.equal(timeline.ageMs(500), 200,
    'Repeated identical snapshots must not conceal the age of the newest physics sample');
});

test('a delayed new physics sample never rewinds a pose already displayed', () => {
  const timeline = new PoseTimeline({delayMs: 80});
  timeline.push(pose(0, 0), 0);
  timeline.push(pose(.05, .005), 50);
  const beforeDelayedArrival = timeline.sample(130).links[0].position[0];
  timeline.push(pose(.1, .01), 140);
  assert.ok(timeline.sample(140).links[0].position[0] >= beforeDelayedArrival,
    'Network jitter must not send the robot backwards along its measured trajectory');
  assert.ok(timeline.sample(170).links[0].position[0] >= beforeDelayedArrival);
});
