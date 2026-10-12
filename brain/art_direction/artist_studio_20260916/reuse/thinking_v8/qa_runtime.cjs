'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),vm=require('node:vm');
const here=__dirname,repo=path.resolve(here,'../../../../..'),TICK=1000/15,contractOnly=process.argv.includes('--contract');
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const report={passed:false,scope:contractOnly?'Runtime behavior with in-memory placeholders; final manifest and geometry not validated':'Final manifest runtime and geometry',checkedAt:new Date().toISOString(),checks:[],failures:[],counts:{},timings:{},searchClearance:{minimum:Infinity,samples:0},limits:['Recorded drawing calls verify source art and geometry, not pixel antialiasing or subjective animation quality.','Search clearance uses conservative bounding rectangles for visible export bounds and recorded eye paths/crops.','DOM selector wiring and audible voice playback require the separate browser review.']};
async function check(name,fn){try{await fn();report.checks.push(name);}catch(e){report.failures.push({name,error:e.stack});}}
const matrix=(a,b)=>[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
const inverse=a=>{const d=a[0]*a[3]-a[1]*a[2];return[a[3]/d,-a[1]/d,-a[2]/d,a[0]/d,(a[2]*a[5]-a[3]*a[4])/d,(a[1]*a[4]-a[0]*a[5])/d];};
function recorder(){
 let m=[1,0,0,1,0,0],stack=[],alpha=1,width=1;const calls=[];
 const ctx={setTransform(...v){m=v;},clearRect(){calls.length=0;},save(){stack.push({m:[...m],alpha,width});},restore(){({m,alpha,width}=stack.pop());},translate(x,y){m=matrix(m,[1,0,0,1,x,y]);},scale(x,y){m=matrix(m,[x,0,0,y,0,0]);},rotate(r){m=matrix(m,[Math.cos(r),Math.sin(r),-Math.sin(r),Math.cos(r),0,0]);},beginPath(){},rect(){},clip(){},fill(p){calls.push({kind:'fill',path:p?.d,matrix:[...m],alpha,width});},stroke(p){calls.push({kind:'stroke',path:p?.d,matrix:[...m],alpha,width});},drawImage(img,...args){calls.push({kind:'image',key:img?.key,args,matrix:[...m],alpha,width});},set globalAlpha(v){alpha=v;},get globalAlpha(){return alpha;},set lineWidth(v){width=v;},get lineWidth(){return width;}};
 return{calls,canvas:{width:100,height:64,dataset:{},getContext(){return ctx;}}};
}
const point=(m,[x,y])=>[m[0]*x+m[2]*y+m[4],m[1]*x+m[3]*y+m[5]];
function callBounds(call){
 let pts,pad=0;
 if(call.kind==='image'){const a=call.args;const [x,y,w,h]=a.length===8?a.slice(4):a;pts=[[x,y],[x+w,y],[x,y+h],[x+w,y+h]];}
 else {const nums=(call.path.match(/-?\d*\.?\d+(?:e[+-]?\d+)?/gi)||[]).map(Number);pts=[];for(let i=0;i<nums.length;i+=2)pts.push([nums[i],nums[i+1]]);if(call.kind==='stroke')pad=call.width*Math.max(Math.hypot(...call.matrix.slice(0,2)),Math.hypot(...call.matrix.slice(2,4)))/2;}
 pts=pts.map(p=>point(call.matrix,p));return[Math.min(...pts.map(p=>p[0]))-pad,Math.min(...pts.map(p=>p[1]))-pad,Math.max(...pts.map(p=>p[0]))+pad,Math.max(...pts.map(p=>p[1]))+pad];
}
function gap(a,b){const dx=Math.max(a[0]-b[2],b[0]-a[2],0),dy=Math.max(a[1]-b[3],b[1]-a[3],0);return Math.hypot(dx,dy);}
(async()=>{
 const api=require('./runtime.js'),drawn=require('../runtime/drawn_face_renderer.js'),runtime=require(path.join(repo,'brain/ui/static/face_runtime.js'));
 const baselinePath=path.join(here,'../handdrawn_v6/qa_v5_reference_renderer.cjs'),baseline=require(baselinePath);
 const sandbox={window:{}};vm.runInNewContext(fs.readFileSync(path.join(repo,'brain/face_assets/app/app_data.js'),'utf8'),sandbox);const data=sandbox.window.MIST_DATA;
 const manifest=JSON.parse(fs.readFileSync(path.join(here,'manifest.json'))),atlas=JSON.parse(fs.readFileSync(path.join(here,'../drawn/atlas.json'))),images={};
 if(contractOnly)for(const s of manifest.studies)manifest.assets[s.asset]??={type:'activity',frames:Array.from({length:24},(_,n)=>({file:`frames/${s.asset}/${String(n).padStart(2,'0')}.png`}))};
 report.runtimeSha256=sha(path.join(here,'runtime.js'));report.manifestSha256=sha(path.join(here,'manifest.json'));report.originalRendererSha256=sha(path.join(here,'../runtime/drawn_face_renderer.js'));report.referenceRendererSha256=sha(baselinePath);
 for(const [id,a] of Object.entries(atlas.assets)){images[id]=images[a.file]={key:'original:'+id};for(const f of a.frames)if(f.file)images[f.file]={key:'original:'+f.file};}
 for(const a of Object.values(manifest.assets))for(const f of a.frames)images[f.file]={key:f.file};
 global.Path2D=class{constructor(d){this.d=d;}};
 function fixture(extra={}){let wall=0;const opts={data,runtime,atlas,images,autoStart:false,reducedMotion:false,now:()=>wall,...extra};const face=api.create(null,{...opts,drawnRuntime:drawn,manifest,thinkingImages:images});return{face,opts,setTime(t){wall=t;},getTime:()=>wall};}
 await check('Manifest and automatic faces agree on three original identities',()=>{
  if(!contractOnly)assert.equal(manifest.complete,true,'Final runtime QA requires the complete generated manifest');
  assert(api.validateManifest(manifest));assert.equal(api.fps,15);assert.equal(api.activities.length,8);assert.equal(data.faces.length,40);assert.equal(new Set(api.autoFaces).size,3);
  assert.deepEqual([...api.autoFaces].sort(),[...manifest.faceVariants].sort());for(const id of api.autoFaces)assert(data.faces.some(f=>f.id===id));
  for(const s of manifest.studies)assert.deepEqual([...s.faceVariants].sort(),[...api.autoFaces].sort());
 });
 for(const id of api.activities)await check(id+' reaches every cel at 15 fps with bounded, continuous gaze',()=>{
  const duration=api.sampleChoreography(id,1000).duration;report.timings[id]=duration;
  if(['coding','writing','sorting'].includes(id))assert(duration>=2200&&duration<=2800,'Work phrase must last 2.2 to 2.8 seconds');
  const seen={entrance:new Set(),loop:new Set(),exit:new Set()};let prev=null,maxStep=0;
  for(let t=0;t<api.entranceMs+duration*2;t+=TICK){const s=api.sampleChoreography(id,t);assert(s.frame>=0&&s.frame<24);assert.equal(s.eyeSource,'original-mist');seen[s.phase]?.add(s.frame);if(prev)maxStep=Math.max(maxStep,Math.hypot(s.gaze.x-prev.gaze.x,s.gaze.y-prev.gaze.y));prev=s;}
  for(let t=0;t<api.exitMs;t+=TICK)seen.exit.add(api.sampleChoreography(id,1000,{exitAge:t}).frame);
  assert.deepEqual([...seen.entrance].sort((a,b)=>a-b),[0,1,2,3]);assert.deepEqual([...seen.loop].sort((a,b)=>a-b),Array.from({length:16},(_,n)=>n+4));assert.deepEqual([...seen.exit].sort((a,b)=>a-b),[20,21,22,23]);assert(maxStep<.7,'Abrupt gaze change');
  const a=api.sampleChoreography(id,api.entranceMs+duration-.00001),b=api.sampleChoreography(id,api.entranceMs+duration);assert(Math.hypot(a.gaze.x-b.gaze.x,a.gaze.y-b.gaze.y)<.01,'Gaze jumps at the loop seam');
  assert.equal(api.sampleChoreography(id,86400000).phase,'loop');assert.equal(api.sampleChoreography(id,86400000,{exitAge:api.exitMs}).phase,'rest');
 });
 const f=fixture(),face=f.face;assert(await face.ready);
 await check('Automatic faces rotate on starts and slow phrase boundaries',()=>{
  const starts=new Set();for(let n=0;n<6;n++){f.setTime(n*1500);face.setActivity('coding',{owner:n,restart:true});face.update();starts.add(face.expression);}assert.equal(starts.size,3);
  f.setTime(12000);face.setActivity('coding',{owner:'long-wait',restart:true});let previous=face.expression,lastChange=12000;const seen=new Set([previous]),changes=[];
  for(let n=0;n<15*40;n++){f.setTime(12000+n*TICK);face.update();if(face.expression!==previous){const age=f.getTime()-12000,phase=(age-api.entranceMs)%report.timings.coding;assert(Math.min(Math.abs(phase),Math.abs(report.timings.coding-phase))<TICK+.001,'Face changed away from a phrase boundary');assert(f.getTime()-lastChange>=4000,'Face changes too frequently');changes.push(f.getTime());lastChange=f.getTime();previous=face.expression;seen.add(previous);}}
  assert.equal(seen.size,3);assert(changes.length>=2);report.counts.automaticFaces=seen.size;report.counts.longWaitFaceChanges=changes.length;
 });
 await check('Speech freezes automatic faces and activity while keeping the audio clock unquantized',()=>{
  f.setTime(54000);face.setActivity('coding',{owner:'speech'});const speech={sample:()=>({active:true,viseme:'AA',amount:.65,time:f.getTime()/1000+.017}),duration:Infinity};face.startSpeech(speech);const expression=face.expression,frames=new Set();
  for(let n=0;n<15*15;n++){f.setTime(54000+n*TICK);const s=face.update();assert.equal(s.speechTime,f.getTime()/1000+.017);assert.equal(face.expression,expression);if(n>15){frames.add(s.thinking.activity.frame);assert.equal(s.thinking.activity.beat,'speaking');assert.equal(s.thinking.gaze.x,0);assert.equal(s.thinking.gaze.y,0);}}
  assert.equal(frames.size,1);
  face.setActivity('searching',{owner:'during-speech'});for(let n=0;n<45;n++){f.setTime(70000+n*TICK);face.update();assert.equal(face.expression,expression);}
  const chosen=data.faces.find(x=>!api.autoFaces.includes(x.id)).id;face.setExpression(chosen);assert.equal(face.expression,expression,'An explicit request during speech must wait');face.stopSpeech();f.setTime(74000);face.update();assert.equal(face.expression,chosen);
  for(let n=0;n<80;n++){f.setTime(75000+n*1000);if(n%10===0)face.setActivity(api.activities[(n/10)%8],{restart:true});face.update();assert.equal(face.expression,chosen);}assert.equal(face.expressionMode,'explicit');
  face.setExpression('auto');assert.equal(face.expressionMode,'auto');report.counts.speechFaceSamples=270;
 });
 await check('All activity replacements reject stale completion tokens',()=>{
  let pairs=0;for(const a of api.activities)for(const b of api.activities){const old=face.setActivity(a,{owner:'old'}),next=face.setActivity(b,{owner:'new'});assert.notEqual(old.token,next.token);assert.equal(face.clearActivity(old.token),false);assert.equal(face.snapshot().thinking.activity.id,b);assert(face.clearActivity(next.token,{immediate:true}));assert.equal(face.snapshot().thinking.activity,null);pairs++;}report.counts.staleCompletionPairs=pairs;
 });face.destroy();
 await check('All forty faces and blinks preserve the verified original drawing paths and source cels',async()=>{
  assert.equal(sha(baselinePath),'9ade474f61fc9a6f3eee260b6bb07ef4adc2a4e6f56cae3a4871acbc531563ff');
  const g=fixture({expression:data.faces[0].id}),current=g.face,original=baseline.create(null,g.opts);assert(await current.ready);assert(await original.ready);const rd=recorder(),td=recorder();let samples=0;
  for(let i=0;i<data.faces.length;i++){
   const item=data.faces[i];g.setTime(i*4000);original.setExpression(item.id);current.setExpression(item.id);current.setActivity(api.activities[i%8],{restart:true});
   for(let n=0;n<21;n++){
    g.setTime(i*4000+n*TICK);if(n===12){original.blink();current.blink();}
    const b=current.renderTo(td.canvas,g.getTime()),a=original.renderTo(rd.canvas,g.getTime(),{gaze:b.thinking.gaze});
    for(const key of ['drawnLayers','drawnPlacements','drawnVisuals'])assert.deepEqual(b[key],a[key],item.id+' '+key);
    const actual=td.calls.filter(c=>!c.key?.startsWith('frames/'));assert.equal(actual.length,rd.calls.length);let common=null;
    for(let j=0;j<rd.calls.length;j++){const aa=rd.calls[j],bb=actual[j];assert.equal(bb.kind,aa.kind);assert.equal(bb.path,aa.path);assert.equal(bb.key,aa.key);assert.deepEqual(bb.args,aa.args);const transform=matrix(bb.matrix,inverse(aa.matrix));common??=transform;for(let k=0;k<6;k++)assert(Math.abs(transform[k]-common[k])<1e-7);assert(Math.abs(transform[1])<1e-7&&Math.abs(transform[2])<1e-7);assert(Math.abs(transform[0]-transform[3])<1e-7);}
    samples++;
   }
  }report.counts.originalFaceSamples=samples;report.counts.originalExpressions=data.faces.length;current.destroy();original.destroy();
 });
 await check('Speech mouths match the original renderer and close promptly between display ticks',async()=>{
  const g=fixture({expression:'39_neutral_02_manual'}),current=g.face,original=baseline.create(null,g.opts);assert(await current.ready);assert(await original.ready);const rd=recorder(),td=recorder();
  let audioTime=0,viseme='AA',active=true;const speech={sample:()=>({active,viseme,amount:.7,time:audioTime,source:'independent-audio-clock'}),duration:Infinity,clock:()=>audioTime};
  original.startSpeech(speech);current.startSpeech(speech);current.setActivity('coding');let paints=0;
  for(let n=0;n<120;n++){
   g.setTime(1000+n*1000/120);audioTime=g.getTime()/1000+.017;const b=current.renderTo(td.canvas,g.getTime()),a=original.renderTo(rd.canvas,g.getTime(),{gaze:b.thinking.gaze});assert.equal(b.speechTime,audioTime);assert.equal(b.speechTime,a.speechTime);
   assert.deepEqual(b.drawnPlacements.filter(x=>x.role==='mouth'),a.drawnPlacements.filter(x=>x.role==='mouth'));if(b.drawnPainted)paints++;
  }
  assert.equal(paints,15);g.setTime(2000);current.renderTo(td.canvas,g.getTime());g.setTime(2010);audioTime=2.027;viseme='MBP';assert.equal(current.renderTo(td.canvas,g.getTime()).drawnPainted,true);
  g.setTime(2020);active=false;const closed=current.renderTo(td.canvas,g.getTime());assert.equal(closed.drawnPainted,true);assert(!closed.drawnPlacements.some(x=>x.role==='mouth'));report.counts.speechClockSamples=120;report.counts.speechPaintsPerSecond=paints;current.destroy();original.destroy();
 });
 if(!contractOnly)await check('Search prop remains geometrically clear of all forty original eye shapes',async()=>{
  const g=fixture({expression:data.faces[0].id}),current=g.face;assert(await current.ready);const d=recorder();current.inspect({layers:'eyes'});const overlaps=[];
  for(let index=0;index<data.faces.length;index++){
   const item=data.faces[index],base=index*10000;g.setTime(base);current.setExpression(item.id);g.setTime(base+1000);current.update();current.setActivity('searching',{owner:'geometry',restart:true});
   const duration=api.entranceMs+report.timings.searching;let exited=false;
   for(let n=0;n<Math.ceil((duration+api.exitMs)/TICK);n++){
    g.setTime(base+1000+n*TICK);if(!exited&&n*TICK>=duration){current.clearActivity();exited=true;}
    const s=current.renderTo(d.canvas,g.getTime()),a=s.thinking.activity;if(!a||a.prop.alpha<.001)continue;
    const visibleFrames=[];if(!a.exitBlend||a.exitBlend.amount>.001)visibleFrames.push(a.frame);if(a.exitBlend&&a.exitBlend.amount<.999)visibleFrames.push(a.exitBlend.frame);
    for(const frame of visibleFrames){
     const [x,y,w,h]=manifest.assets.searching.frames[frame].bounds,p=a.prop,scale=p.size/256;
     const box=[p.x-p.size/2+x*scale,p.y+p.dy-p.size/2+y*scale,p.x-p.size/2+(x+w)*scale,p.y+p.dy-p.size/2+(y+h)*scale];
     for(const call of d.calls.filter(c=>c.alpha>.001)){
      assert(!call.key?.startsWith('frames/'),'Eye-only inspector leaked a generated prop');const eye=callBounds(call),distance=gap(box,eye);if(distance<report.searchClearance.minimum){report.searchClearance.minimum=distance;report.searchClearance.closest={face:item.id,frame,phase:a.phase,prop:box,eye};}if(distance===0)overlaps.push({face:item.id,frame,phase:a.phase});
     }report.searchClearance.propLayerSamples=(report.searchClearance.propLayerSamples||0)+1;
    }report.searchClearance.samples++;
   }
  }
  report.searchClearance.overlaps=overlaps;assert.equal(overlaps.length,0,'Search prop overlaps eye bounds');assert(report.searchClearance.minimum>=1,'Search prop needs a visible gap of at least one face-coordinate unit');current.destroy();
 });
 await check('Runtime and manifest stayed stable during this run',()=>{assert.equal(sha(path.join(here,'runtime.js')),report.runtimeSha256);assert.equal(sha(path.join(here,'manifest.json')),report.manifestSha256);});
 report.passed=report.failures.length===0;
})().catch(e=>report.failures.push({name:'QA inputs',error:e.stack})).finally(()=>{fs.writeFileSync(path.join(here,contractOnly?'qa_runtime_contract_report.json':'qa_runtime_report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(!report.passed)process.exitCode=1;});
