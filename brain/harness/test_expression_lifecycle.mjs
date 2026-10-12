import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const source = await readFile(new URL('../duplex/static/expression_policy.js', import.meta.url), 'utf8');
const {ExpressionPolicy} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const map = JSON.parse(await readFile(new URL('../duplex/face_map.json', import.meta.url), 'utf8'));
let now = 0;
const policy = new ExpressionPolicy(map, {now:() => now, transitionMs:600});
const at = time => {now = time; return policy.snapshot();};

// The voice converter may start output several seconds after the tool receipt.
policy.setState('thinking');
assert.equal(policy.request({expression:'happy'}, {source:'model', sequenceKey:1}).status, 'applied');
assert.equal(at(5000).expression, 'happy', 'a default face must survive delayed speech');
policy.setState('speaking');
assert.equal(at(5600).expression, 'happy', 'audible speech keeps the selected mood');
policy.setState('listening');
policy.interrupt();
assert.equal(at(5700).expression, 'happy', 'interruption retains the current persistent mood');

// Separate calls in one model turn need enough display time to be visible.
assert.equal(policy.request({expression:'angry'}, {source:'model', sequenceKey:2}).status, 'applied');
at(5710);
assert.equal(policy.request({expression:'curious'}, {source:'model', sequenceKey:2}).status, 'queued');
at(5720);
assert.equal(policy.request({expression:'proud'}, {source:'model', sequenceKey:2}).status, 'queued');
assert.equal(at(6699).expression, 'angry');
assert.equal(at(6700).expression, 'curious');
assert.equal(at(7700).expression, 'proud');
assert.equal(at(20000).expression, 'proud', 'last face persists until replaced');

// An explicitly timed flash expires; a newer user choice cancels old queued faces.
assert.equal(policy.request({expression:'surprised', duration_ms:400}, {source:'model', sequenceKey:3}).status, 'applied');
assert.equal(at(20999).expression, 'surprised');
assert.equal(at(21000).expression, 'proud', 'the short flash restores the persistent face underneath');
policy.request({expression:'sad'}, {source:'model', sequenceKey:4});
at(21010); policy.request({expression:'panic'}, {source:'model', sequenceKey:4});
policy.request({expression:'happy'}, {source:'manual'});
assert.equal(at(23000).expression, 'happy', 'manual choice replaces the model sequence');
assert.equal(policy.snapshot().queueDepth, 0);

console.log('PASS: persistent delayed-speech face, ordered same-turn faces, timed flash, and manual cancellation.');
