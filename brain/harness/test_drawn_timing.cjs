'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const crypto=require('node:crypto');
const ROOT=path.resolve(__dirname,'../..');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(ROOT,'brain/face_assets/app/app_data.js'),'utf8'),context);
const data=context.window.MIST_DATA;
const runtime=require('../ui/static/face_runtime.js');
const drawn=require('../ui/static/drawn_face_renderer.js');
const atlas=JSON.parse(fs.readFileSync(path.join(ROOT,'brain/art_direction/artist_studio_20260916/reuse/drawn/atlas.json'),'utf8'));
const images=Object.fromEntries(Object.keys(atlas.assets).map(id=>[id,{}]));
for(const asset of Object.values(atlas.assets)) {
  images[asset.file]=images[asset.id];
  for(const frame of asset.frames)if(frame.file)images[frame.file]??={};
}
global.Path2D=class{};
const canvas={width:500,height:320,dataset:{},getContext(){return paint;}};
const paint={setTransform(){},clearRect(){},save(){},restore(){},beginPath(){},rect(){},clip(){},translate(){},rotate(){},scale(){},fill(){},stroke(){},drawImage(){}};

(async()=>{
  let wall=0,audioTime=0,viseme='AA',active=true;
  const face=drawn.create(null,{data,runtime,atlas,images,autoStart:false,reducedMotion:false,now:()=>wall});await face.ready;
  face.startSpeech({sample:()=>({active,viseme,amount:.7,time:audioTime,source:'audible-output-clock'}),duration:Infinity,clock:()=>audioTime});
  face.setExpression('05_annoyed_01_manual');
  const painted=[],geometryByFrame=new Map();
  for(let tick=0;tick<60;tick++) {
    wall=tick*1000/60;audioTime=wall/1000+.013;
    const state=face.renderTo(canvas,wall);
    assert.equal(state.speechTime,audioTime,'Audio sampling must not use quantized animation time');
    assert.equal(state.drawnAnimation.fps,15);
    if(state.drawnPainted)painted.push({at:wall,index:state.drawnAnimation.index,audio:state.speechTime});
    const key=state.drawnAnimation.index,geometry=JSON.stringify(state.drawnVisuals);
    if(geometryByFrame.has(key))assert.equal(geometry,geometryByFrame.get(key),'Placement changes only at 15 fps boundaries');
    geometryByFrame.set(key,geometry);
  }
  assert.equal(painted.length,15,'60 RAF updates must yield exactly 15 painted animation frames');
  assert.deepEqual(painted.map(item=>item.index),Array.from({length:15},(_,index)=>index));
  for(let i=1;i<painted.length;i++)assert(Math.abs(painted[i].at-painted[i-1].at-1000/15)<1e-6);
  assert.equal(face.snapshot().drawnTransition.durationMs,600);
  wall=1000;audioTime=1.013;face.renderTo(canvas,wall);
  wall=1010;audioTime=1.023;viseme='OO';
  assert.equal(face.renderTo(canvas,wall).drawnPainted,false,'A new open vowel waits for the next frame');
  wall=1020;audioTime=1.033;viseme='MBP';
  assert.equal(face.renderTo(canvas,wall).drawnPainted,true,'A lip closure is not delayed by the animation cadence');
  wall=1030;audioTime=1.043;active=false;
  const stopped=face.renderTo(canvas,wall);assert.equal(stopped.drawnPainted,true);assert(!stopped.drawnPlacements.some(p=>p.role==='mouth'));
  wall=1040;face.stopSpeech();assert.equal(face.snapshot().speaking,false);
  face.setFps(15);face.blink();
  assert.equal(face.snapshot().drawnAnimation.fps,15);
  let blinkPhases=0;
  for(const id of ['round','hook','arc','loop','slot','chevron','bar'])for(let phase=0;phase<1000/15;phase++) {
    const asset=atlas.assets[id];let closed=0;
    for(let age=phase;age<drawn.timing.blinkMs;age+=1000/15)if(asset.frames[drawn.helpers.blinkPose(asset,age)].pose==='closed')closed++;
    assert(closed>=2,'Every 15 fps phase sees at least two closed frames: '+id+' phase '+phase);blinkPhases++;
  }
  face.setExpression('28_sad_03_manual',{durationMs:430});
  assert(Math.abs(face.snapshot().drawnTransition.durationMs-7*1000/15)<1e-6,'Requested durations round up to whole frames');
  face.destroy();
  const production=fs.readFileSync(path.join(ROOT,'brain/ui/static/drawn_face_renderer.js'));
  const studio=fs.readFileSync(path.join(ROOT,'brain/art_direction/artist_studio_20260916/reuse/runtime/drawn_face_renderer.js'));
  assert(production.equals(studio),'Studio and production must use byte-identical renderers');
  const report={passed:true,checkedAt:new Date().toISOString(),rendererSha256:crypto.createHash('sha256').update(production).digest('hex'),rafUpdates:60,paintedFrames:painted.length,fps:15,frameMs:1000/15,blinkMs:drawn.timing.blinkMs,closedHoldMs:drawn.timing.closedEndMs-drawn.timing.closedStartMs,blinkPhaseChecks:blinkPhases,
    checks:['Actual canvas paints at 15 fps under 60 Hz callbacks','Expression placement holds between animation frames','Audio time remains current and is never quantized','MBP and stopped audio close between paint ticks','Seven eye families retain two closed frames at every 15 fps sampling phase','Transition duration uses whole animation frames','Production and studio renderer bytes match']};
  fs.writeFileSync(path.join(__dirname,'drawn_timing_checks.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});
