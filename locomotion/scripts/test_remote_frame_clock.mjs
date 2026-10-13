import assert from 'node:assert/strict';
import test from 'node:test';
import {scheduleFrame} from '../viewer/frame_clock.mjs';

function clock() {
  const jobs = new Map(); let next = 0, time = 0;
  return {jobs, performance: {now: () => time},
    requestAnimationFrame: fn => {jobs.set(++next, {kind: 'display', fn}); return next;},
    cancelAnimationFrame: id => jobs.delete(id),
    setTimeout: (fn, delay) => {jobs.set(++next, {kind: 'timer', fn, delay}); return next;},
    clearTimeout: id => jobs.delete(id),
    fire(kind, at) {time = at; const job = [...jobs.values()].find(job => job.kind === kind); job?.fn();}};
}

test('a throttled display callback still draws on the bounded timer', () => {
  const api = clock(), times = [];
  scheduleFrame(time => times.push(time), api);
  assert.equal([...api.jobs.values()].find(job => job.kind === 'timer').delay, 33);
  api.fire('timer', 33); api.fire('display', 1000);
  assert.deepEqual(times, [33]); assert.equal(api.jobs.size, 0);
});

test('normal display cadence wins without a duplicate timer draw', () => {
  const api = clock(), times = [];
  scheduleFrame(time => times.push(time), api);
  api.fire('display', 16.7); api.fire('timer', 33);
  assert.deepEqual(times, [16.7]); assert.equal(api.jobs.size, 0);
});

test('canceling a frame disposes both scheduled callbacks', () => {
  const api = clock(), times = [];
  scheduleFrame(time => times.push(time), api)();
  api.fire('display', 16.7); api.fire('timer', 33);
  assert.deepEqual(times, []); assert.equal(api.jobs.size, 0);
});
