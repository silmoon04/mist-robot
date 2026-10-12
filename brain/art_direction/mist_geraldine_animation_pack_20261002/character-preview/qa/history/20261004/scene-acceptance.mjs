import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createGeraldineAdapter} from '../adapter/geraldine-adapter.mjs';
import {AtlasRenderer} from '../adapter/source/player.mjs';
import {createSpeechSampler} from '../speech-review/sampler.mjs';
import {SceneTransport} from '../preview/transport.mjs';
const read=async path=>JSON.parse(await fs.readFile(new URL(path,import.meta.url)));
const manifest=await read('../../site/asset-manifest.json');
const {scenes}=await read('../direction/scenes.json');
const {profiles}=await read('../direction/timing-profiles.json');
const {clips}=await read('../../site/speech-clips.json');
const results=[];
async function test(id,fn){try{results.push({id,pass:true,...await fn()});}catch(e){results.push({id,pass:false,error:e.stack});}}
function context(){return {currentTime:0,state:'running',destination:{},sources:[],resume:async()=>{},close(){this.state='closed';},createBufferSource(){const n={connect(){},disconnect(){this.disconnected=true;},start(...args){this.started=args;},stop(){this.stopped=true;}};this.sources.push(n);return n;}};}
function ownership(pose){assert.ok(manifest.presets.some(p=>p.id===pose.presetId));assert.ok(manifest.eyes[pose.eyeFamily]?.frames.some(f=>f.id===pose.eyeFrame));assert.ok(manifest.mouths[pose.mouthFamily]?.frames.some(f=>f.id===pose.mouthFrame));}
async function runScene(scene,profile){
  let now=0,index=0;const trace=[],events=[],ctx=context(),clip=clips.find(c=>c.id===scene.audio.clipId),transport=new SceneTransport(ctx);
  transport.configure(scene,{duration:clip.duration});await transport.play();
  const face=createGeraldineAdapter(null,{manifest,now:()=>now,renderer:{load:async()=>{},draw:()=>{}}});assert.equal(await face.ready,true);
  const sampler=createSpeechSampler({clip,clock:()=>transport.sample().position,isRunning:()=>transport.sample().active,epoch:0});face.startSpeech(sampler);
  for(let frame=0;frame<=Math.ceil(scene.durationMs*15/1000);frame++){
    now=frame*1000/15;ctx.currentTime=now/1000;
    while(index<scene.events.length&&scene.events[index].atMs<=now+.00001){
      const e=scene.events[index++];events.push(e);
      if(e.type==='intent')face.setExpression(e.payload.faceId);
      if(e.type==='reaction')face.setExpression(e.payload.faceId,{durationMs:profile[e.payload.durationKey]});
      if(e.type==='state')face.handleEvent({type:'state',state:e.payload.state});
      if(e.type==='interrupt'){transport.interrupt();sampler.cancel();face.reset();}
    }
    const shot=face.update(now);ownership(shot.pose);
    if(!transport.sample().active)assert.ok(['rest','MBP'].includes(shot.pose.mouthFrame));
    if(scene.id==='patience'&&now>=5100&&now<6000){assert.equal(shot.intent,'reassuring');assert.equal(transport.sample().position,1.1);}
    trace.push({time:now,pose:shot.pose,intent:shot.intent,expression:shot.expression,state:shot.state,speech:shot.speech});
  }
  assert.deepEqual(events,scene.events);transport.destroy();face.destroy();assert.equal(transport.nodes.size,0);assert.ok(ctx.sources.every(n=>n.stopped&&n.disconnected));
  return {events,trace};
}
for(const scene of scenes)for(const profile of profiles)await test(`complete-replay/${scene.id}/${profile.id}`,async()=>{const a=await runScene(scene,profile),b=await runScene(scene,profile);assert.deepEqual(a,b);return {events:a.events.length,frames:a.trace.length};});
await test('native-crop-renderer-all-cels',async()=>{
  const renderer=new AtlasRenderer(manifest);renderer.loaded=true;
  const families=[...Object.values(manifest.eyes),...Object.values(manifest.mouths)];
  const files=new Set(families.flatMap(a=>[a.file,...a.frames.flatMap(f=>[f.file,f.left?.file,f.right?.file])]).filter(Boolean));
  for(const file of files)renderer.images.set(file,{file});
  let draws=0;const context={setTransform(a,b,c,d){assert.equal(a,d);assert.equal(b,0);assert.equal(c,0);},clearRect(){},fillRect(){},drawImage(image,x,y,w,h,dx,dy,dw,dh){assert.ok(files.has(image.file));assert.ok(w>0&&h>0);assert.ok(Math.abs(dw/w-dh/h)<1e-9);draws++;}};
  const canvas={clientWidth:600,getContext:()=>context};
  for(const preset of manifest.presets)for(const eye of manifest.eyes[preset.eyes].frames)for(const mouth of manifest.mouths[preset.mouth].frames){const pose={presetId:preset.id,eyeFamily:preset.eyes,eyeFrame:eye.id,mouthFamily:preset.mouth,mouthFrame:mouth.id};ownership(pose);renderer.draw(canvas,pose);}
  return {poses:13*12*12,componentDraws:draws,claim:'Registered existing cells and uniform registration only; source hashes and visual judgment are separate.'};
});
await test('transport-pause-resume-gap-reset-disconnect',async()=>{
  const ctx=context(),t=new SceneTransport(ctx);t.configure(scenes.find(s=>s.id==='patience'),{duration:2.618});await t.play();ctx.currentTime=5.2;assert.equal(t.sample().active,false);assert.equal(t.sample().position,1.1);
  t.pause();assert.equal(t.nodes.size,0);await t.play();ctx.currentTime+=.9;assert.equal(t.sample().active,true);
  ctx.state='suspended';assert.equal(t.sample().active,false);ctx.state='running';assert.equal(t.sample().active,true);
  t.reset();assert.equal(t.nodes.size,0);assert.equal(t.sample().active,false);t.destroy();assert.equal(ctx.state,'closed');assert.ok(ctx.sources.every(n=>n.stopped&&n.disconnected));
});
await test('pending-play-canceled-before-resume',async()=>{
  const ctx=context();let resolve;ctx.resume=()=>new Promise(r=>resolve=r);const t=new SceneTransport(ctx);t.configure(scenes[0],{duration:6.234});const promise=t.play();t.reset();resolve();await promise;assert.equal(t.running,false);assert.equal(t.nodes.size,0);assert.equal(ctx.sources.length,0);t.destroy();
});
await fs.writeFile(new URL('./scene-results.json',import.meta.url),JSON.stringify({scope:'Authored scene traversal using real adapter, sampler and transport with fake audio context; browser dispatcher separately reviewed',total:results.length,passed:results.filter(r=>r.pass).length,results},null,2)+'\n');
console.log(JSON.stringify(results,null,2));if(results.some(r=>!r.pass))process.exitCode=1;
