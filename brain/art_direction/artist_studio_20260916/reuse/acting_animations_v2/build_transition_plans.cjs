const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const runtime = require('./runtime.js');
const root = __dirname;
const manifestBytes = fs.readFileSync(path.join(root, 'manifest.json'));
const manifest = JSON.parse(manifestBytes);
if (!manifest.complete) throw new Error('A complete manifest is required.');
const examples = manifest.groups.flatMap(group => group.examples);
const plan = runtime.transitionPlan(examples[0], examples[1]);
const pairs = [];
for (const from of examples) for (const to of examples) {
  if (from.key === to.key) continue;
  const candidate = runtime.transitionPlan(from, to);
  if (JSON.stringify(candidate) !== JSON.stringify(plan)) throw new Error('A transition needs its own template.');
  pairs.push({from: from.key, to: to.key, template: 'blink-handoff'});
}
if (pairs.length !== 306) throw new Error('Expected all 306 directed pairs.');
const result = {
  schema: 'mist-layered-transitions', version: 2, fps: 15, frameCount: 12,
  manifestSha256: crypto.createHash('sha256').update(manifestBytes).digest('hex'),
  description: 'Generated source closing frames and target opening frames; mouth blending is independent. Frame indices are zero-based.',
  templates: {'blink-handoff': plan}, pairs
};
fs.writeFileSync(path.join(root, 'transition_plans.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({pairs: pairs.length, stepsPerPair: plan.length}));
