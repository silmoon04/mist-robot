import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createGeraldineAdapter} from '../adapter/geraldine-adapter.mjs';

const manifest=JSON.parse(await fs.readFile(new URL('../../site/asset-manifest.json',import.meta.url)));
const results=[];
const frame=1000/15;
async function test(id,fn){try{await fn();results.push({id,pass:true});}catch(e){results.push({id,pass:false,error:e.stack});}}
async function fixture(expression='attentive'){
  let time=0; const draws=[];
  const face=createGeraldineAdapter(null,{manifest,expression,epoch:7,now:()=>time,renderer:{load:async()=>{},draw:(_canvas,pose)=>draws.push(structuredClone(pose))}});
  assert.equal(await face.ready,true);
  return {face,draws,tick:(ms=time+frame+.001)=>{time=ms;return face.update(time);},now:()=>time};
}
const open=(epoch=7)=>({active:true,viseme:'AA',amount:.8,source:'acceptance-fixture',time:.5,epoch,sequence:3,turn_id:'qa'});
function closed(shot){assert.ok(['rest','MBP'].includes(shot.pose.mouthFrame),`Expected closed mouth, got ${JSON.stringify(shot.pose)}`);}

for(const preset of manifest.presets)for(const kind of ['rest','inactive','zero','stop','reset'])await test(`${kind}/${preset.id}`,async()=>{
  const f=await fixture(preset.id);let sample=open();
  f.face.startSpeech({events:[],duration:Infinity,clock:()=>.5,sample:()=>sample});f.tick(1000);
  assert.equal(f.face.snapshot().speech.source,'acceptance-fixture');
  if(kind==='stop')f.face.stopSpeech();else if(kind==='reset')f.face.reset();else sample=kind==='rest'?{active:true,viseme:'rest',amount:0}:kind==='inactive'?{...open(),active:false}:{...open(),amount:0};
  closed(f.tick());closed(f.tick());f.face.destroy();
});
await test('suspended-clock-gap-resume-intent',async()=>{
  const f=await fixture('concerned');let sample=open();let clock=.5;
  f.face.startSpeech({events:[],duration:Infinity,clock:()=>clock,sample:()=>sample});f.tick(1000);
  sample={active:false,viseme:'rest',amount:0,source:'silence',time:.5};
  for(let i=0;i<8;i++){closed(f.tick());assert.equal(f.face.snapshot().intent,'concerned');}
  sample=open();clock=.7;const s=f.tick();assert.equal(s.intent,'concerned');assert.equal(s.speech.active,true);assert.equal(s.pose.mouthFamily,'concerned');f.face.destroy();
});
await test('stale-tagged-cue-and-expression',async()=>{
  const f=await fixture('concerned');f.face.reset({epoch:8});
  assert.equal(f.face.setExpression('laughing',{epoch:7}),false);
  assert.equal(f.face.snapshot().intent,'concerned');
  assert.equal(f.face.startSpeech({epoch:7,sample:()=>open(7)}),false);
  f.face.startSpeech({epoch:8,sample:()=>open(7)});closed(f.tick(1000));
  assert.equal(f.face.snapshot().epoch,8);f.face.destroy();
});
await test('repeat-face-transition',async()=>{
  const f=await fixture();f.face.setExpression('concerned');f.tick(100);
  const count=f.face.snapshot().requestCount;
  f.face.setExpression('concerned');assert.equal(f.face.snapshot().requestCount,count);
  const s=f.tick(600);assert.equal(s.pose.presetId,'concerned');
  f.face.setExpression('concerned');assert.equal(f.face.snapshot().requestCount,count);f.face.destroy();
});
await test('finite-reaction-return-after-gap',async()=>{
  const f=await fixture('concerned');f.face.setExpression('amused',{durationMs:500});
  f.face.startSpeech({sample:()=>({active:false,viseme:'rest',amount:0})});
  closed(f.tick(100));assert.equal(f.face.snapshot().intent,'concerned');
  f.tick(1100);assert.equal(f.face.snapshot().expression,'concerned');assert.equal(f.face.snapshot().reaction,null);f.face.destroy();
});
await test('missing-failed-sampler-and-finite-end',async()=>{
  const f=await fixture('laughing');f.face.startSpeech({events:[],duration:1,clock:()=>.5});closed(f.tick(100));
  f.face.startSpeech({sample:()=>{throw Error('intentional fixture');}});closed(f.tick());
  f.face.startSpeech({events:[{time:0,viseme:'AA',amount:1}],duration:.5,clock:()=>1});closed(f.tick());f.face.destroy();
});
await test('unknown-expression-and-optional-hooks',async()=>{
  const f=await fixture();assert.equal(f.face.setExpression('not-a-face'),false);assert.equal(f.face.snapshot().intent,'attentive');
  for(const name of ['setGaze','clearGaze','setListeningSignal','setActivity','clearActivity','resetActivities','previewActivity'])assert.equal(f.face[name]().supported,false);
  f.face.destroy();
});
await test('rapid-replay-retired-samplers-destroy',async()=>{
  const f=await fixture();let calls=Array(10).fill(0);
  for(let i=0;i<10;i++){f.face.reset({epoch:10+i});f.face.startSpeech({epoch:10+i,sample:()=>{calls[i]++;return open(10+i);}});}
  f.tick(1000);assert.deepEqual(calls.slice(0,9),Array(9).fill(0));assert.ok(calls[9]>0);
  f.face.stopSpeech();f.face.stopSpeech();closed(f.tick());
  f.face.destroy();const draws=f.draws.length;f.face.startSpeech({sample:()=>open(19)});f.face.setExpression('laughing');f.tick();assert.equal(f.draws.length,draws);assert.equal(f.face.snapshot().destroyed,true);
});

await fs.writeFile(new URL('./acceptance-results.json',import.meta.url),JSON.stringify({version:1,scope:'Independent sampled-runtime clock tests; no acoustic measurement',total:results.length,passed:results.filter(r=>r.pass).length,failed:results.filter(r=>!r.pass).length,results},null,2)+'\n');
console.log(JSON.stringify({total:results.length,passed:results.filter(r=>r.pass).length,failures:results.filter(r=>!r.pass)},null,2));
if(results.some(r=>!r.pass))process.exitCode=1;
