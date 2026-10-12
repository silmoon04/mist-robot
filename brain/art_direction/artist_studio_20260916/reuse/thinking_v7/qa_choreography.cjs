'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const here=__dirname,api=require('./runtime.js'),TICK=1000/15;
const assetFor={reading:'book',coding:'terminal',writing:'note',sorting:'cards',searching:'searching',pondering:'planning'};
const countFor=id=>['searching','pondering'].includes(id)?12:16;
const manifest={version:7,fps:15,complete:true,studies:api.activities.map(id=>({id,asset:assetFor[id],faceId:'test'})),assets:Object.fromEntries(api.activities.map(id=>[assetFor[id],{type:'activity',frames:Array.from({length:countFor(id)},(_,i)=>({file:`frames/${assetFor[id]}/${i}.png`}))}]))};
const thinkingImages=Object.fromEntries(Object.values(manifest.assets).flatMap(a=>a.frames.map(f=>[f.file,{}])));
const report={passed:false,checkedAt:new Date().toISOString(),runtimeSha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(here,'runtime.js'))).digest('hex'),checks:[],failures:[],warnings:[],counts:{samples:0,speechCases:0},limits:['This test uses in-memory prop-image placeholders and a recording speech adapter to isolate choreography. Final image quality and full original-renderer integration have separate checks.']};
function test(name,fn){try{fn();report.checks.push(name);}catch(error){report.failures.push({name,error:error.message});}}
function fixture(){
  let wall=0,speech=null,stopped=0;
  const base={expression:'test',loaded:true,ready:Promise.resolve(true),startSpeech(settings){speech=settings;return true;},stopSpeech(){speech=null;stopped++;},setGaze(){},setExpression(){return true;},blink(){},destroy(){},update(time){return this.snapshot(time);},snapshot(time){const sampled=speech?.sample?.();return {drawnReady:true,drawnAnimation:{time},speaking:!!speech,speechTime:sampled?.time};}};
  const face=api.create(null,{data:{faces:[{id:'test',slots:{}}]},drawnRuntime:{create(){return base;}},manifest,thinkingImages,autoStart:false,reducedMotion:false,now:()=>wall});
  return {face,base,setTime(time){wall=time;},getTime:()=>wall,getSpeech:()=>speech,getStops:()=>stopped};
}
(async()=>{
  for(const id of api.activities){
    test(id+' has entrance, active cel changes, held consideration, resumed work, and explicit exit',()=>{
      const beats=new Map(),frames=new Set();let first=null,last=null,maxGazeStep=0;
      const duration=api.sampleChoreography(id,1000).duration;
      for(let tick=0;tick<Math.ceil((600+duration*2)/TICK);tick++){
        const age=tick*TICK,s=api.sampleChoreography(id,age,{frameCount:countFor(id)});assert(s.frame>=0&&s.frame<countFor(id));assert.equal(s.eyeSource,'original-mist');assert.equal(s.fps,15);
        assert(s.alpha>=0&&s.alpha<=1);assert(s.phase!=='rest');
        if(last)maxGazeStep=Math.max(maxGazeStep,Math.hypot(s.gaze.x-last.gaze.x,s.gaze.y-last.gaze.y));
        if(s.phase==='loop'){frames.add(s.frame);const list=beats.get(s.beat)||[];list.push(s.frame);beats.set(s.beat,list);}
        first??=s;last=s;report.counts.samples++;
      }
      assert.equal(first.phase,'entrance');assert.equal(first.beat,'notice');assert(frames.size>=3);
      assert([...beats.values()].some(values=>values.length>=8&&new Set(values).size===1),'An actual held cel must accompany consideration');
      assert(beats.size>=4);assert(maxGazeStep<.7,'No abrupt large gaze jump');
      const long=api.sampleChoreography(id,86400000);assert.equal(long.phase,'loop');assert(long.alpha>0);
      const end=api.sampleChoreography(id,86400000,{exitAge:600});assert.equal(end.phase,'rest');assert.equal(end.alpha,0);
      const before=api.sampleChoreography(id,600+duration-1e-5),after=api.sampleChoreography(id,600+duration);
      assert([4,countFor(id)-5].includes(before.frame),'Loop ends on its settling cel');assert.equal(after.frame,4,'Loop restarts on its first action cel');assert(Math.hypot(before.gaze.x-after.gaze.x,before.gaze.y-after.gaze.y)<.01,'Loop gaze is continuous');
    });
    for(const start of [100,1500,4300]){
      const f=fixture();await f.face.ready;f.face.setActivity(id,{owner:'qa'});f.setTime(start);
      const speech={sample:()=>({active:true,time:f.getTime()/1000+.017,viseme:'AA',amount:.5}),duration:Infinity};f.face.startSpeech(speech);
      test(id+' speech from '+start+' ms quiets a stable active cel and preserves audio',()=>{
        const frames=new Set();for(let tick=0;tick<45;tick++){
          f.setTime(start+tick*TICK);const s=f.face.snapshot();assert.equal(s.speechTime,f.getTime()/1000+.017);assert.equal(f.getSpeech(),speech);assert.equal(f.getStops(),0);
          const a=s.thinking.activity;if(a.phase==='loop'&&a.speechMix>=.999){assert.equal(a.beat,'speaking');assert(Math.abs(a.gaze.x)<1e-10);assert(Math.abs(a.gaze.y)<1e-10);assert(a.frame>=4&&a.frame<countFor(id)-4,'Quiet speech must not freeze an entrance or exit cel inside the active loop');frames.add(a.frame);}
        }
        assert.equal(frames.size,1,'Action remains quiet during sustained speech');
      });
      f.face.stopSpeech();test(id+' stops speech without clearing ongoing thought',()=>{assert.equal(f.getStops(),1);assert(f.face.snapshot().thinking.activity);});f.face.destroy();report.counts.speechCases++;
    }
    const f=fixture();await f.face.ready;f.face.setActivity(id);f.setTime(1500);const speech={sample:()=>({active:true,time:f.getTime()/1000}),duration:Infinity};f.face.startSpeech(speech);f.setTime(2300);
    const next=api.activities[(api.activities.indexOf(id)+1)%api.activities.length];f.face.setActivity(next,{owner:'replacement'});
    test(id+' activity replacement during speech stays quiet',()=>{
      const frames=new Set();for(let i=0;i<40;i++){f.setTime(2300+i*TICK);const a=f.face.snapshot().thinking.activity;if(a.phase==='loop'){assert.equal(a.beat,'speaking');frames.add(a.frame);}}
      assert.equal(frames.size,1,'Changing activity must not resume animated work while speech is active');assert.equal(f.getSpeech(),speech);
    });f.face.destroy();
  }
  report.passed=!report.failures.length;fs.writeFileSync(path.join(here,'qa_choreography_report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(!report.passed)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
