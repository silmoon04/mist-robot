'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),vm=require('node:vm'),crypto=require('node:crypto');
const here=__dirname,root=path.resolve(here,'../../../../..');
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const TICK=1000/15;
const hand=require('./runtime.js');
const runtime=require(path.join(root,'brain/ui/static/face_runtime.js'));
const drawn=require(path.join(root,'brain/ui/static/drawn_face_renderer.js'));
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(root,'brain/face_assets/app/app_data.js'),'utf8'),context);
const data=context.window.MIST_DATA;
const atlas=JSON.parse(fs.readFileSync(path.join(here,'../drawn/atlas.json'),'utf8'));
const manifest=JSON.parse(fs.readFileSync(path.join(here,'manifest.json'),'utf8'));
const images={};
for(const [id,asset] of Object.entries(atlas.assets)){
  const image={key:'old:'+id};images[id]=image;images[asset.file]=image;
  for(const frame of asset.frames)if(frame.file)images[frame.file]={key:'old:'+frame.file};
}
for(const asset of Object.values(manifest.assets))for(const frame of asset.frames)images[frame.file]={key:frame.file};
global.Path2D=class{};
let drawings=[];
const paint={setTransform(){},clearRect(){drawings=[];},save(){},restore(){},beginPath(){},rect(){},clip(){},translate(){},rotate(){},scale(){},fill(){},stroke(){},drawImage(image,...args){drawings.push({key:image?.key,args});}};
const canvas={width:500,height:320,dataset:{},getContext(){return paint;}};
const report={passed:false,checkedAt:new Date().toISOString(),runtimeSha256:sha(path.join(here,'runtime.js')),rendererSha256:sha(path.join(root,'brain/ui/static/drawn_face_renderer.js')),manifestSha256:sha(path.join(here,'manifest.json')),checks:[],counts:{},limits:['Canvas calls are inspected with a recording context; this does not rate artistic quality or replace browser review.','No microphone, provider, or live tool connection is used. Speech is tested against a deterministic audio clock.']};
function check(name,fn){try{fn();report.checks.push(name);}catch(error){(report.failures??=[]).push({name,error:error.message});}}
(async()=>{
  assert.equal(manifest.complete,true,'Final assets must be present');
  let wall=0,audioTime=0,viseme='AA',active=true;
  const face=hand.create(null,{data,runtime,drawnRuntime:drawn,atlas,images,handdrawnImages:images,manifest,autoStart:false,reducedMotion:false,now:()=>wall});
  assert.equal(await face.ready,true);assert.equal(face.loaded,true);
  check('Original MIST eyes remain active and replacement eye cels are absent',()=>{
    const state=face.renderTo(canvas,wall);assert.equal(state.handdrawn.eyeSource,'original-mist');
    assert.equal(drawings.filter(d=>d.key?.startsWith('frames/eye_')).length,0);
    assert(state.drawnLayers.some(layer=>layer.role.startsWith('eye'))||state.drawnPlacements.some(layer=>layer.role.startsWith('eye')));
  });
  let lifecycleSamples=0;
  for(const id of hand.activities){
    wall+=1000;const result=face.setActivity(id,{owner:'qa:'+id});assert(result.accepted);
    const at=wall;const enter=face.snapshot(wall).handdrawn.activity;assert.equal(enter.id,id);assert.equal(enter.phase,'entrance');
    const frames=new Set();
    for(let tick=0;tick<180;tick++){
      wall=at+tick*TICK;const s=face.renderTo(canvas,wall).handdrawn;
      assert.equal(s.activity.id,id);assert(s.activity.frame>=0&&s.activity.frame<8);assert(s.activity.alpha>=0&&s.activity.alpha<=1);
      if(tick>10)assert.equal(s.activity.phase,'loop');
      if(s.activity.phase==='loop')frames.add(s.activity.frame);
      assert.equal(s.eyeSource,'original-mist');assert.equal(s.eyes.length,2);
      assert(!drawings.some(d=>d.key?.startsWith('frames/eye_')));
      assert(drawings.some(d=>d.key===manifest.assets[id].frames[s.activity.frame].file));lifecycleSamples++;
    }
    assert.deepEqual([...frames].sort(),[4,5,6,7],id+' uses all loop cels');
    assert(face.clearActivity(result.token));const exitAt=wall;
    for(let tick=0;tick<8;tick++){
      wall=exitAt+tick*TICK;const s=face.snapshot().handdrawn.activity;assert(s);assert.equal(s.phase,'exit');assert(s.frame>=8&&s.frame<=11);lifecycleSamples++;
    }
    wall=exitAt+9*TICK;assert.equal(face.snapshot().handdrawn.activity,null);
  }
  report.counts.lifecycleSamples=lifecycleSamples;
  report.checks.push('All nine activities enter, use every loop cel for twelve seconds, remain active until cleared, then exit');
  report.checks.push('Every activity keeps the original MIST eyes and paints no replacement eye cels');
  let replacements=0;
  for(const first of hand.activities)for(const second of hand.activities){
    wall+=1000;const a=face.setActivity(first,{owner:'first'});wall+=TICK;
    const b=face.setActivity(second,{owner:'second'});assert.notEqual(a.token,b.token);
    assert.equal(face.clearActivity(a.token),false);assert.equal(face.snapshot().handdrawn.activity.id,second);
    assert.equal(face.snapshot().handdrawn.activity.token,b.token);
    face.clearActivity(b.token,{immediate:true});assert.equal(face.snapshot().handdrawn.activity,null);replacements++;
  }
  report.counts.replacements=replacements;report.checks.push('All 81 ordered activity replacements reject stale completion tokens');
  check('Explicit event ownership prevents an old tool or brain completion from clearing a newer activity',()=>{
    face.handleEvent({type:'brain_job',job_id:'a',status:'running'});
    face.handleEvent({type:'debug_tool',name:'recall',call_id:'b',phase:'started'});
    face.handleEvent({type:'brain_job',job_id:'a',status:'finished'});
    assert.equal(face.snapshot().handdrawn.activity.id,'reading');
    face.handleEvent({type:'state',state:'thinking'});assert.equal(face.snapshot().handdrawn.activity.id,'reading');
    face.handleEvent({type:'debug_tool',name:'recall',call_id:'b',phase:'finished'});assert.equal(face.snapshot().handdrawn.activity.id,'planning');assert.equal(face.snapshot().handdrawn.activity.owner,'state');
    face.handleEvent({type:'state',state:'available'});assert.equal(face.snapshot().handdrawn.activity.phase,'exit');
    face.resetActivities();assert.equal(face.snapshot().handdrawn.activity,null);
    assert.equal(face.handleEvent({type:'debug_tool',name:'unknown',call_id:'x',phase:'started'}),false);
  });
  let expressions=0;
  for(const item of data.faces){
    wall+=1000;assert(face.setExpression(item.id));const s=face.snapshot(wall+650);
    assert.equal(s.handdrawn.expression,item.id);assert.equal(face.expression,item.id);
    assert.deepEqual(s.handdrawn.eyes.map(eye=>eye.part),[item.slots.eye_L.part,item.slots.eye_R.part]);expressions++;
  }
  assert.equal(expressions,40);report.counts.expressions=expressions;report.checks.push('All forty expression IDs preserve their original left and right source part IDs');
  wall+=2000;face.blink();const blinkAt=wall;
  for(let i=0;i<8;i++){wall=blinkAt+i*TICK;const s=face.renderTo(canvas,wall);assert(Number.isFinite(s.drawnBlinkAge));assert(!drawings.some(d=>d.key?.startsWith('frames/eye_')));}
  report.checks.push('Explicit blinking stays with the original renderer');
  face.startSpeech({sample:()=>({active,viseme,amount:.7,time:audioTime,source:'audible-output-clock'}),duration:Infinity,clock:()=>audioTime});
  face.setActivity('coding',{owner:'voice-check'});wall+=1000;
  const start=wall;let paints=0,speechSamples=0;
  for(let tick=0;tick<120;tick++){
    wall=start+tick*1000/120;audioTime=wall/1000+.017;
    const state=face.renderTo(canvas,wall);assert.equal(state.speechTime,audioTime);assert.equal(state.drawnAnimation.fps,15);
    if(state.drawnPainted)paints++;speechSamples++;
  }
  assert.equal(paints,15,'Activity overlay does not raise actual paint cadence');
  report.counts.speechSamples=speechSamples;report.counts.paintsInOneSecond=paints;
  wall=start+1000;face.renderTo(canvas,wall);wall+=10;audioTime=wall/1000+.017;viseme='MBP';
  assert.equal(face.renderTo(canvas,wall).drawnPainted,true,'Immediate lip closure preserved');
  wall+=10;active=false;const end=face.renderTo(canvas,wall);assert.equal(end.drawnPainted,true);assert(!end.drawnPlacements.some(p=>p.role==='mouth'));
  face.stopSpeech();assert.equal(face.snapshot().speaking,false);
  report.checks.push('Existing audio clock stays unquantized, 120 Hz updates paint at 15 fps, and lip closures and stopped audio update immediately');
  const before=face.snapshot().handdrawn.activity;assert.equal(face.setActivity('not-real').accepted,false);assert.equal(face.snapshot().handdrawn.activity.token,before.token);
  face.destroy();assert.equal(face.update(),null);
  const bad=hand.create(null,{data,runtime,drawnRuntime:drawn,atlas,images,handdrawnImages:images,manifest:{version:6,fps:15,assets:{},activities:[]},autoStart:false,now:()=>wall});
  assert.equal(await bad.ready,false);assert(bad.error);assert.notEqual(bad.snapshot().renderer,'handdrawn');bad.destroy();
  report.checks.push('Invalid activity names leave the running activity intact, bad manifests use fallback, and destroyed runtimes no longer update');
  report.passed=!report.failures?.length;fs.writeFileSync(path.join(here,'qa_runtime_report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(!report.passed)process.exitCode=1;
})().catch(error=>{report.failure=error.stack;fs.writeFileSync(path.join(here,'qa_runtime_report.json'),JSON.stringify(report,null,2)+'\n');console.error(error);process.exitCode=1;});
