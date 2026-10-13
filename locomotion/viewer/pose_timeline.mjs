// Interpolate measured poses on the display clock without predicting motion.
const finiteVector = (v, length) => Array.isArray(v) && v.length === length && v.every(Number.isFinite);
function validPose(pose) {
  return pose?.version === 1 && Number.isFinite(pose.time_s) && pose.epoch !== undefined
    && Number.isSafeInteger(pose.sequence) && Array.isArray(pose.links) && pose.links.length > 0
    && pose.links.every(link => Number.isInteger(link.index) && finiteVector(link.position, 3)
      && finiteVector(link.quaternion, 4) && Math.hypot(...link.quaternion) > .1);
}
function rotation(a, b, amount) {
  let dot = a.reduce((sum, value, i) => sum + value * b[i], 0);
  const sign = dot < 0 ? -1 : 1;
  dot = Math.min(1, Math.abs(dot));
  let first = 1 - amount, second = amount;
  if (dot < .9995) {
    const angle = Math.acos(dot), sine = Math.sin(angle);
    first = Math.sin((1 - amount) * angle) / sine;
    second = Math.sin(amount * angle) / sine;
  }
  const q = a.map((value, i) => first * value + second * sign * b[i]);
  const norm = Math.hypot(...q);
  return q.map(value => value / norm);
}

export class PoseTimeline {
  constructor({delayMs = 80} = {}) {
    this.delayMs = delayMs;
    this.clear();
  }
  clear() { this.poses = []; this.lastArrivalMs = null; this.rate = 1; this.displayTime = -Infinity; }
  get length() { return this.poses.length; }
  get epoch() { return this.poses.at(-1)?.epoch; }
  ageMs(nowMs) { return this.lastArrivalMs === null ? Infinity : Math.max(0, nowMs - this.lastArrivalMs); }
  push(pose, arrivalMs) {
    if (!validPose(pose) || !Number.isFinite(arrivalMs)) return false;
    let latest = this.poses.at(-1);
    if (latest && latest.epoch !== pose.epoch) { this.clear(); latest = undefined; }
    if (latest && (pose.sequence < latest.sequence || pose.time_s < latest.time_s)) return false;
    // A repeated HTTP reply is not a new physics sample. Keep draining the
    // interpolation buffer toward the last measured pose, even after a stop.
    if (latest && pose.sequence === latest.sequence && pose.time_s === latest.time_s) return true;
    if (latest && arrivalMs > this.lastArrivalMs) {
      const rate = (pose.time_s - latest.time_s) * 1000 / (arrivalMs - this.lastArrivalMs);
      this.rate = Math.min(2, Math.max(0, rate));
    }
    this.lastArrivalMs = arrivalMs;
    this.poses.push(pose);
    if (this.poses.length > 12) this.poses.shift();
    return true;
  }
  sample(nowMs) {
    const latest = this.poses.at(-1);
    if (!latest) return null;
    // Receiving a delayed packet must never rewind an already displayed pose.
    const time = Math.min(latest.time_s, Math.max(this.displayTime,
      latest.time_s + (this.ageMs(nowMs) * this.rate - this.delayMs) / 1000));
    this.displayTime = time;
    let before = this.poses[0], after = before;
    for (const pose of this.poses) {
      after = pose;
      if (pose.time_s >= time) break;
      before = pose;
    }
    const span = after.time_s - before.time_s;
    const amount = span > 0 ? Math.min(1, Math.max(0, (time - before.time_s) / span)) : 0;
    const afterLinks = new Map(after.links.map(link => [link.index, link]));
    const links = before.links.map(link => {
      const next = afterLinks.get(link.index) || link;
      return {index: link.index,
        position: link.position.map((value, i) => value + amount * (next.position[i] - value)),
        quaternion: rotation(link.quaternion, next.quaternion, amount)};
    });
    return {epoch: latest.epoch, time_s: Math.max(before.time_s, time), links};
  }
}
