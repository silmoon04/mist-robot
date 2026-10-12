import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createGeraldineAdapter} from '../adapter/geraldine-adapter.mjs';

const manifest=JSON.parse(await fs.readFile(new URL('../../site/asset-manifest.json',import.meta.url)));
const results=[];
const frameMs=1000/15;
async function test(id,fn){try{const evidence=await fn();results.push({id,pass:true,evidence});}catch(error){results.push({id,pass:false,error:error.stack});}}
async function fixture(expression='concerned'){
  let time=0;
  const draws=[];
  const face=createGeraldineAdapter(null,{manifest,expression,epoch:30,now:()=>time,renderer:{load:async()=>{},draw:(_canvas,pose)=>draws.push(structuredClone(pose))}});
  assert.equal(await face.ready,true);
  return {face,draws,tick:(ms=time+frameMs+.001)=>{time=ms;return face.update(time);}};
}
const open=time=>({active:true,viseme:'AA',amount:.8,source:'boundary-fixture',time,epoch:30,sequence:1,turn_id:'qa-boundary'});
function closed(shot){assert.ok(['rest','MBP'].includes(shot.pose.mouthFrame),`Expected closed cel; got ${shot.pose.mouthFrame}`);assert.equal(shot.pose.speaking,false);}

await test('sampled-finite-duration-authoritative-clock',async()=>{
  const f=await fixture();let audioTime=.9;
  f.face.startSpeech({duration:1,clock:()=>audioTime,sample:()=>open(.25),epoch:30});
  const before=f.tick(1000);assert.equal(before.speech.active,true);assert.equal(before.pose.speaking,true);
  audioTime=1;const boundary=f.tick();closed(boundary);
  audioTime=1.1;const after=f.tick();closed(after);
  assert.equal(after.intent,'concerned');f.face.destroy();
  return {before:before.speech,boundary:boundary.speech,after:after.speech};
});
await test('sampled-duration-zero',async()=>{
  const f=await fixture('laughing');
  f.face.startSpeech({duration:0,clock:()=>0,sample:()=>open(0),epoch:30});
  const shot=f.tick(1000);closed(shot);f.face.destroy();return shot.speech;
});
await test('cancel-during-sampler-callback',async()=>{
  const f=await fixture();let calls=0;
  f.face.startSpeech({duration:Infinity,clock:()=>.5,sample:()=>{calls++;f.face.stopSpeech();return open(.5);},epoch:30});
  closed(f.tick(1000));closed(f.tick());assert.equal(calls,1);f.face.destroy();return {calls};
});
await test('destroy-during-sampler-callback',async()=>{
  const f=await fixture();
  f.face.startSpeech({sample:()=>{f.face.destroy();return open(.5);},epoch:30});
  const before=f.draws.length;const shot=f.tick(1000);assert.equal(shot.destroyed,true);assert.equal(f.draws.length,before);return {drawsAfterDestroy:f.draws.length-before};
});
await test('finite-reaction-new-intent-survives-rest',async()=>{
  const f=await fixture();
  f.face.setExpression('amused',{durationMs:400,epoch:30});
  f.face.setExpression('reassuring',{epoch:30});
  f.face.startSpeech({sample:()=>({active:false,viseme:'rest',amount:0}),epoch:30});
  const reacting=f.tick(300);assert.equal(reacting.intent,'reassuring');assert.equal(reacting.expression,'amused');closed(reacting);
  const returned=f.tick(800);assert.equal(returned.intent,'reassuring');assert.equal(returned.expression,'reassuring');assert.equal(returned.reaction,null);closed(returned);
  f.face.destroy();return {intent:returned.intent,expression:returned.expression};
});

const receipt={version:1,scope:'Independent boundary tests against the sampled-runtime contract; no acoustic measurement',total:results.length,passed:results.filter(r=>r.pass).length,failed:results.filter(r=>!r.pass).length,results};
await fs.writeFile(new URL('./boundary-results.json',import.meta.url),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt,null,2));if(receipt.failed)process.exitCode=1;
