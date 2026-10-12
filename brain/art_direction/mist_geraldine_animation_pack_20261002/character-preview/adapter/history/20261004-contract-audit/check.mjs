import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createGeraldineAdapter} from './geraldine-adapter.mjs';
const manifest = JSON.parse(await readFile(new URL('../../site/asset-manifest.json',import.meta.url)));
let at = 0, draws = [], checks = [];
const face = createGeraldineAdapter(null,{manifest,now:()=>at,renderer:{load:async()=>{},draw:(_,pose)=>draws.push({...pose})}});
function check(name,fn) { fn(); checks.push(name); }
function step(time) { at=time; return face.update(at); }
assert.equal(await face.ready,true);
check('initial closed native rest',()=>assert.equal(step(0).viseme,'rest'));
face.setExpression('concerned'); const count = face.snapshot().requestCount;
face.setExpression('concerned');
check('repeat intent does not restart transition',()=>assert.equal(face.snapshot().requestCount,count));
let cue = {active:true,viseme:'AA',amount:.6,time:.1,source:'estimated_phonemes',epoch:1,sequence:3,turn_id:'t1'};
face.startSpeech({sample:()=>cue,epoch:1});
let shot = step(100);
check('sample opens registered mouth and retains metadata',()=>{assert.equal(shot.viseme,'AA');assert.equal(shot.speech.source,'estimated_phonemes');assert.equal(shot.speech.sequence,3);assert.equal(shot.speech.turn_id,'t1');});
cue={active:false,viseme:'rest',time:.2,source:'silence'};
shot=step(200);
check('untagged gap closes while concern persists',()=>{assert.equal(shot.viseme,'rest');assert.equal(shot.intent,'concerned');assert.equal(shot.speech.epoch,null);});
cue={active:true,viseme:'OH',time:.3,epoch:1}; step(300);
face.stopSpeech();
check('stop closes next frame and invalidates callback',()=>{const before=face.snapshot().generation; assert.equal(step(400).viseme,'rest');assert.equal(face.snapshot().generation,before);});
face.setExpression('laughing'); step(500);
check('open-rest preset still closed without audio',()=>assert.equal(face.snapshot().viseme,'rest'));
face.startSpeech({sample:()=>({active:true,viseme:'AA',time:1,epoch:1})}); step(600); face.reset({epoch:2});
check('reset closes next frame, preserves intent',()=>{shot=step(700);assert.equal(shot.viseme,'rest');assert.equal(shot.intent,'laughing');});
check('stale tagged start and expression rejected',()=>{assert.equal(face.startSpeech({epoch:1}),false);assert.equal(face.setExpression('amused',{epoch:1}),false);assert.equal(face.snapshot().intent,'laughing');});
face.startSpeech({epoch:2,sample:()=>({active:true,viseme:'AA',time:2,epoch:1})});
check('late sampled old epoch cannot reopen mouth',()=>assert.equal(step(800).viseme,'rest'));
face.stopSpeech();face.setExpression('concerned');face.setExpression('amused',{durationMs:400,epoch:2});const rc=face.snapshot().requestCount;
at=900;face.setExpression('amused',{durationMs:400,epoch:2});
check('repeated reaction does not extend expiry or transition',()=>{assert.equal(face.snapshot().reaction.untilMs,1200);assert.equal(face.snapshot().requestCount,rc);});
face.setExpression('reassuring',{epoch:2});step(1200);
check('reaction restores latest intent',()=>{assert.equal(face.snapshot().expression,'reassuring');assert.equal(face.snapshot().reaction,null);});
check('unknown ID is rejected',()=>{assert.equal(face.setExpression('not-a-face'),false);assert.equal(face.snapshot().intent,'reassuring');});
check('state metadata does not replace emotional intent',()=>{face.handleEvent({type:'state',state:'listening'});assert.equal(face.snapshot().intent,'reassuring');});
face.startSpeech({sample:()=>{face.stopSpeech();return {active:true,viseme:'AA',time:1};}});
check('reentrant canceled sampler cannot reopen',()=>assert.equal(step(1300).viseme,'rest'));
face.startSpeech({sample:()=>{throw new Error('fixture');}});
check('sampler exception closes and reports error',()=>{assert.equal(step(1400).viseme,'rest');assert.match(face.snapshot().error,/fixture/);});
face.startSpeech({events:[{time:0,viseme:'AA',source:'fixture'},{time:.2,viseme:'rest'}],duration:1,clock:()=>.1});
check('optional timed cues use seconds',()=>assert.equal(step(1500).viseme,'AA'));
face.startSpeech({events:[],clock:()=>.2});
check('missing cues close',()=>assert.equal(step(1600).viseme,'rest'));
check('optional hooks explicitly unsupported',()=>{for(const method of ['setGaze','clearGaze','setListeningSignal','setActivity','clearActivity','resetActivities','previewActivity']) assert.equal(face[method]().supported,false);});
for (const preset of manifest.presets) {
  face.setExpression(preset.id);
  for (const amount of [0,-1,NaN,Infinity,null]) {
    face.startSpeech({sample:()=>({active:true,viseme:'AA',amount,time:2,source:'amount_fixture'})});
    at += 100; shot=step(at);
    assert.equal(shot.viseme,'rest');assert.equal(shot.speech.viseme,'AA');assert.equal(shot.speech.source,'amount_fixture');
  }
}
checks.push('all 13 presets close for zero, negative and invalid amounts while preserving cue provenance');
face.startSpeech({sample:()=>({active:true,viseme:'AA',time:3})});at+=100;
check('omitted amount preserves timed-cue compatibility',()=>assert.equal(step(at).viseme,'AA'));
face.stopSpeech();
check('stop at frozen clock renders closure on next host update',()=>assert.equal(step(at).viseme,'rest'));
check('every rendered cel belongs to selected native manifest',()=>{for(const pose of draws){assert.ok(manifest.eyes[pose.eyeFamily].frames.some(f=>f.id===pose.eyeFrame));assert.ok(manifest.mouths[pose.mouthFamily].frames.some(f=>f.id===pose.mouthFrame));}});
const drawCount=draws.length;face.destroy();step(1700);
check('destroy prevents future rendering and attachment',()=>{assert.equal(draws.length,drawCount);assert.equal(face.startSpeech({}),false);assert.equal(face.loaded,false);});
const delayed = createGeraldineAdapter(null,{manifest,renderer:{load:()=>Promise.resolve(),draw(){throw Error('must not draw');}}});delayed.destroy();
assert.equal(await delayed.ready,false);checks.push('destroy during loading stays destroyed');
const hashes=JSON.parse((await readFile(new URL('../contract/source-hashes.json',import.meta.url),'utf8')).replace(/^\uFEFF/,''));
for(const file of hashes.files){ const bytes=await readFile(new URL('../../../../../'+file.path,import.meta.url)); assert.equal(createHash('sha256').update(bytes).digest('hex'),file.sha256); }
checks.push('shared source hashes unchanged');
for(const name of ['state.mjs','player.mjs']) assert.deepEqual(await readFile(new URL('./source/'+name,import.meta.url)),await readFile(new URL('../../site/'+name,import.meta.url)));
checks.push('snapshot module bytes exactly match current site sources');
const assetHashes=JSON.parse((await readFile(new URL('../contract/asset-hashes.json',import.meta.url),'utf8')).replace(/^\uFEFF/,''));
for(const file of assetHashes.files) assert.equal(createHash('sha256').update(await readFile(new URL('../../'+file.path,import.meta.url))).digest('hex'),file.sha256);
checks.push('all native atlas asset hashes unchanged');
const result={version:'1.0.0',passed:checks.length,checks,scope:'Deterministic injected-clock checks; no acoustic latency or browser acceptance claim.'};
await writeFile(new URL('./worker-checks.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
