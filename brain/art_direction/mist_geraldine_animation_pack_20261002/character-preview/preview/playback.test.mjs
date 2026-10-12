import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createGeraldineAdapter} from '../adapter/geraldine-adapter.mjs';
import {SceneTransport} from './transport.mjs';
import {PreviewPlayback,RECOVERY_MS} from './playback.mjs';

const manifest=JSON.parse(await readFile(new URL('../../site/asset-manifest.json',import.meta.url),'utf8'));
const clip={id:'test',duration:8,alignmentSource:'estimated-fixture',nativeSha256:'fixture',cues:[{time:0,end:8,viseme:'AA',amount:1}]};
const scene={id:'test',durationMs:10000,audio:{startMs:0,packetGaps:[]}};
class Context {
  currentTime=0; state='running'; destination={}; created=[];
  async resume(){this.state='running';}
  createBufferSource(){const node={connect(){},disconnect(){this.disconnected=true;},start(...args){this.args=args;},stop(){this.stopped=true;}};this.created.push(node);return node;}
  close(){this.state='closed';}
}
async function fixture({reducedMotion=false,gaps=[]}={}) {
  const context=new Context(),transport=new SceneTransport(context),wall={ms:0},poses=[];let playback;
  const face=createGeraldineAdapter(null,{manifest,renderer:{load:async()=>{},draw:(_,pose)=>poses.push({...pose})},now:()=>playback?.faceTime()??transport.time()*1000,reducedMotion});
  assert.equal(await face.ready,true);playback=new PreviewPlayback({face,transport,wallClock:()=>wall.ms});
  playback.reset({...scene,audio:{...scene.audio,packetGaps:gaps}},clip,{duration:clip.duration});
  return {context,transport,wall,face,playback,poses};
}
function pose(value){return {...value.pose};}
async function reactionFixture() {
  const f=await fixture();await f.playback.play();
  f.face.setExpression('concerned',{epoch:f.playback.epoch});f.context.currentTime=.4;f.playback.update();
  f.face.setExpression('wry-teasing',{epoch:f.playback.epoch,durationMs:1000});f.context.currentTime=.8;f.playback.update();
  assert.equal(f.face.snapshot().intent,'concerned');assert.equal(f.face.snapshot().expression,'wry-teasing');return f;
}

test('Replay resets the adapter blink epoch at scene zero and repeats native poses',async()=>{
  const f=await fixture(),times=[0,900,1600,2000,3550,3600,3700,3800,6000];
  async function trace(){const anchor=f.context.currentTime;await f.playback.play();return times.map(ms=>{f.context.currentTime=anchor+ms/1000;return pose(f.playback.update().frame);});}
  const first=await trace();f.face.setExpression('concerned',{epoch:f.playback.epoch});f.context.currentTime=20;
  f.playback.reset(scene,clip,{duration:8},'replay');assert.equal(f.playback.faceTime(),0);assert.equal(f.face.snapshot().intent,'attentive');
  assert.deepEqual(await trace(),first);assert(first.some(p=>p.eyeFrame!=='rest'));
});
test('Interruption immediately starts the native 400 ms return to ongoing emotion',async()=>{
  const f=await reactionFixture(),stale=f.playback.sampler;f.playback.interrupt();const start=f.playback.update().frame;
  assert.equal(start.intent,'concerned');assert.equal(start.expression,'concerned');assert.equal(start.state,'listening');assert.equal(start.pose.phase,'transition');assert.equal(start.pose.mouthFrame,'rest');
  assert.equal(f.playback.recovery.untilMs-f.playback.recovery.startMs,RECOVERY_MS);assert.equal(f.transport.nodes.size,0);assert.equal(stale.sample().active,false);
  f.context.currentTime=1;assert.equal(f.playback.update().frame.pose.phase,'transition');
  f.context.currentTime=1.2;const end=f.playback.update();assert.equal(end.frame.pose.phase,'hold');assert.equal(end.frame.pose.eyeFrame,'rest');assert.equal(end.recovered.durationMs,400);assert.equal(end.frame.intent,'concerned');
  const inspection=f.playback.sampler.inspect();assert.equal(inspection.currentMouthTarget,'rest');assert.equal(inspection.source,'silence');assert.equal(inspection.reason,'interrupted');assert.equal(inspection.epoch,f.playback.epoch);
});
test('Paused recovery completes in real time without advancing the recording or rewinding resume',async()=>{
  const f=await reactionFixture();f.playback.pause();assert.equal(f.playback.update().frame.pose.phase,'transition');
  const frozen=f.transport.time();f.wall.ms=200;const middle=f.playback.update();assert.equal(middle.frame.pose.phase,'transition');assert.equal(f.transport.time(),frozen);
  f.wall.ms=400;const settled=f.playback.update();assert.equal(settled.frame.pose.eyeFrame,'rest');assert.equal(settled.frame.pose.phase,'hold');assert.equal(settled.frame.pose.mouthFrame,'rest');assert.equal(f.playback.recovery,null);assert.equal(settled.time,1200);
  f.context.currentTime=10;await f.playback.play();assert(Math.abs(f.playback.faceTime()-settled.time)<1e-9);f.context.currentTime=10.1;const resumed=f.playback.update();assert(resumed.time>=settled.time);assert.equal(resumed.frame.pose.mouthFrame,'AA');assert(Math.abs(f.transport.sample().position-.9)<1e-9);
});
test('Recovery completion inside the same render bucket cannot freeze an opening cel',async()=>{
  const f=await reactionFixture();f.context.currentTime=.801;f.playback.pause();f.playback.update();
  f.wall.ms=399;assert.equal(f.playback.update().frame.pose.phase,'transition');
  f.wall.ms=400;const end=f.playback.update();assert.equal(end.frame.pose.phase,'hold');assert.equal(end.frame.pose.eyeFrame,'rest');assert.equal(end.recovered.durationMs,400);
});
test('Resume during recovery keeps speech attached at and beyond the recovery boundary',async()=>{
  const f=await reactionFixture();f.playback.pause();f.playback.update();f.wall.ms=200;f.context.currentTime=10;await f.playback.play();f.playback.update();
  f.context.currentTime=10.201;const boundary=f.playback.update();assert(boundary.recovered);assert.equal(boundary.frame.pose.phase,'hold');assert.equal(boundary.frame.pose.mouthFrame,'AA');
  f.context.currentTime=10.5;const later=f.playback.update();assert.equal(later.frame.pose.mouthFrame,'AA');assert.equal(later.frame.speech.active,true);assert.equal(later.frame.intent,'concerned');assert.equal(f.transport.nodes.size,1);
});
test('Pause and paused interruption leave an open eye and cannot revive cancelled speech',async()=>{
  const f=await fixture();await f.playback.play();f.context.currentTime=3.6;assert.equal(f.playback.update().frame.pose.eyeFrame,'half');
  f.playback.pause();const paused=f.playback.update();assert.equal(paused.frame.pose.eyeFrame,'rest');assert.equal(paused.frame.pose.mouthFrame,'rest');
  f.playback.interrupt();const interrupted=f.playback.update();assert.equal(interrupted.frame.pose.eyeFrame,'rest');assert.equal(interrupted.frame.pose.mouthFrame,'rest');assert.equal(interrupted.frame.intent,'attentive');
  const time=interrupted.time,count=f.context.created.length;f.wall.ms+=1000;f.context.currentTime=10;await f.playback.play();const resumed=f.playback.update();
  assert(resumed.time>=time);assert.equal(f.context.created.length,count);assert.equal(resumed.frame.pose.mouthFrame,'rest');assert.equal(f.transport.sample().active,false);
});
test('Packet gap closes the mouth and holds concerned intent through resume',async()=>{
  const f=await fixture({gaps:[{atClipMs:1000,durationMs:900}]});await f.playback.play();f.face.setExpression('concerned',{epoch:f.playback.epoch});
  f.context.currentTime=.8;assert.equal(f.playback.update().frame.pose.mouthFrame,'AA');f.context.currentTime=1.2;const gap=f.playback.update();
  assert.equal(gap.frame.pose.mouthFrame,'rest');assert.equal(gap.frame.intent,'concerned');assert.equal(f.playback.sampler.inspect().reason,'packet-gap');assert.equal(f.transport.sample().position,1);
  f.context.currentTime=1.4;f.playback.pause();f.playback.update();f.context.currentTime=10;await f.playback.play();f.context.currentTime=10.51;
  const resumed=f.playback.update();assert.equal(resumed.frame.pose.mouthFrame,'AA');assert.equal(resumed.frame.intent,'concerned');assert(Math.abs(f.transport.sample().position-1.01)<1e-9);
});
test('Reset cancels a pending start and retires old sampler and expression traffic',async()=>{
  const f=await fixture();let resolve;f.context.resume=()=>new Promise(r=>resolve=r);
  const oldEpoch=f.playback.epoch,oldSampler=f.playback.sampler,pending=f.playback.play();f.playback.reset(scene,clip,{duration:8});resolve();
  assert.equal(await pending,false);assert.equal(f.transport.nodes.size,0);assert.equal(f.transport.running,false);assert.equal(oldSampler.sample().active,false);
  assert.equal(f.face.setExpression('concerned',{epoch:oldEpoch}),false);const result=f.playback.update();assert.equal(result.frame.intent,'attentive');assert.equal(result.frame.pose.mouthFrame,'rest');assert.equal(result.time,0);
});
test('Audio suspension closes speech, retires sources and resumes at the frozen clip position',async()=>{
  const f=await fixture();await f.playback.play();f.context.currentTime=.8;f.playback.update();f.context.state='suspended';
  assert.equal(f.playback.suspendAudio(),true);const paused=f.playback.update();assert.equal(paused.frame.pose.mouthFrame,'rest');assert.equal(paused.frame.pose.eyeFrame,'rest');assert.equal(f.transport.nodes.size,0);assert.equal(f.transport.time(),.8);
  f.context.currentTime=10;await f.playback.play();const resumed=f.playback.update();assert.equal(resumed.frame.pose.mouthFrame,'AA');assert(Math.abs(f.transport.sample().position-.8)<1e-9);
});
test('Scene end during the final return transition settles the eyes and closes speech',async()=>{
  const f=await fixture();await f.playback.play();f.context.currentTime=8.5;f.playback.update();
  f.face.setExpression('quietly-pleased',{epoch:f.playback.epoch,durationMs:800});f.context.currentTime=9.3;f.playback.update();
  f.context.currentTime=9.5;assert.equal(f.playback.update().frame.pose.phase,'transition');f.playback.stop('ended');
  const ended=f.playback.update();assert.equal(ended.frame.pose.phase,'hold');assert.equal(ended.frame.pose.eyeFrame,'rest');assert.equal(ended.frame.pose.mouthFrame,'rest');assert.equal(ended.frame.intent,'attentive');assert.equal(f.transport.nodes.size,0);assert.equal(f.playback.recovery,null);
});
test('Scene end during an active reaction completes its return without restarting audio',async()=>{
  const f=await reactionFixture();f.playback.stop('ended');const initial=f.playback.update();assert.equal(initial.frame.pose.phase,'transition');
  f.wall.ms=400;const ended=f.playback.update();assert.equal(ended.frame.pose.phase,'hold');assert.equal(ended.frame.pose.eyeFrame,'rest');assert.equal(ended.frame.pose.mouthFrame,'rest');assert.equal(ended.frame.intent,'concerned');assert.equal(f.transport.running,false);assert.equal(f.transport.nodes.size,0);assert.equal(f.playback.recovery,null);
});
test('Reduced motion removes idle blinks while keeping explicit native transitions and speech',async()=>{
  const f=await fixture({reducedMotion:true});await f.playback.play();f.context.currentTime=3.6;const still=f.playback.update();assert.equal(still.frame.pose.eyeFrame,'rest');assert.equal(still.frame.pose.mouthFrame,'AA');
  f.face.setExpression('concerned',{epoch:f.playback.epoch});f.context.currentTime=3.7;const transition=f.playback.update();assert.equal(transition.frame.pose.phase,'transition');assert.equal(transition.frame.pose.eyeFrame,'closed');
  f.context.currentTime=4;assert.equal(f.playback.update().frame.pose.phase,'hold');
});
