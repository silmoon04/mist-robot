'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),vm=require('node:vm'),crypto=require('node:crypto');
const here=__dirname,root=path.resolve(here,'../../../../..'),TICK=1000/15;
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const baselineFile=path.join(here,'qa_v5_reference_renderer.cjs');
assert.equal(sha(baselineFile),'9ade474f61fc9a6f3eee260b6bb07ef4adc2a4e6f56cae3a4871acbc531563ff');
const baseline=require(baselineFile),drawn=require(path.join(root,'brain/ui/static/drawn_face_renderer.js')),hand=require('./runtime.js'),runtime=require(path.join(root,'brain/ui/static/face_runtime.js'));
const sandbox={window:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'brain/face_assets/app/app_data.js'),'utf8'),sandbox);const data=sandbox.window.MIST_DATA;
const atlas=JSON.parse(fs.readFileSync(path.join(here,'../drawn/atlas.json'),'utf8')),manifest=JSON.parse(fs.readFileSync(path.join(here,'manifest.json'),'utf8')),images={};
for(const [id,asset]of Object.entries(atlas.assets)){
  const image={key:'original:'+id};images[id]=image;images[asset.file]=image;for(const frame of asset.frames)if(frame.file)images[frame.file]={key:'original:'+frame.file};
}
for(const asset of Object.values(manifest.assets))for(const frame of asset.frames)images[frame.file]={key:frame.file};
global.Path2D=class{constructor(d){this.d=d;}};
const mul=(a,b)=>[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
const inv=a=>{const d=a[0]*a[3]-a[1]*a[2];assert(Math.abs(d)>1e-12);return [a[3]/d,-a[1]/d,-a[2]/d,a[0]/d,(a[2]*a[5]-a[3]*a[4])/d,(a[1]*a[4]-a[0]*a[5])/d];};
const close=(a,b,label)=>assert(Math.abs(a-b)<1e-7,label+': '+a+' != '+b);
function recorder(){
  let m=[1,0,0,1,0,0],stack=[];const calls=[];
  const ctx={setTransform(...values){m=values;},clearRect(){calls.length=0;},save(){stack.push([...m]);},restore(){m=stack.pop();},translate(x,y){m=mul(m,[1,0,0,1,x,y]);},scale(x,y){m=mul(m,[x,0,0,y,0,0]);},rotate(r){m=mul(m,[Math.cos(r),Math.sin(r),-Math.sin(r),Math.cos(r),0,0]);},beginPath(){},rect(){},clip(){},fill(p){calls.push({kind:'fill',path:p?.d,matrix:[...m]});},stroke(p){calls.push({kind:'stroke',path:p?.d,matrix:[...m]});},drawImage(image,...args){calls.push({kind:'image',key:image?.key,args,matrix:[...m]});}};
  return {calls,canvas:{width:500,height:320,dataset:{},getContext(){return ctx;}}};
}
const report={passed:false,checkedAt:new Date().toISOString(),runtimeSha256:sha(path.join(here,'runtime.js')),rendererSha256:sha(path.join(root,'brain/ui/static/drawn_face_renderer.js')),referenceRendererSha256:sha(baselineFile),manifestSha256:sha(path.join(here,'manifest.json')),counts:{samples:0,paths:0,originalRasterCels:0,generatedEyeCels:0},checks:[],limits:['This compares recorded canvas paths, original source-cel draw calls, and transforms. Pixel antialiasing and subjective appearance are left to browser review.']};
function compare(reference,tested,refDraw,testDraw,label){
  for(const key of ['drawnLayers','drawnPlacements','drawnVisuals'])assert.deepEqual(tested[key],reference[key],label+' '+key);
  const oldCalls=refDraw.calls,testCalls=testDraw.calls.filter(c=>!c.key?.startsWith('frames/'));
  assert.equal(testDraw.calls.filter(c=>c.key?.startsWith('frames/eye_')).length,0,label+' must not draw generated eye cels');
  assert.equal(testCalls.length,oldCalls.length,label+' original primitives count');let affine=null;
  for(let i=0;i<oldCalls.length;i++){
    const a=oldCalls[i],b=testCalls[i];assert.equal(b.kind,a.kind,label);assert.equal(b.path,a.path,label+' original path');assert.equal(b.key,a.key,label+' original raster source');assert.deepEqual(b.args,a.args,label+' original raster crop');
    const transform=mul(b.matrix,inv(a.matrix));
    if(!affine)affine=transform;else for(let j=0;j<6;j++)close(transform[j],affine[j],label+' common whole-face transform');
    close(transform[1],0,label+' no face skew');close(transform[2],0,label+' no face rotation');close(transform[0],transform[3],label+' uniform scale');assert(transform[0]>.4&&transform[0]<=1.01,label+' sensible scale');
    if(a.kind==='image')report.counts.originalRasterCels++;else report.counts.paths++;
  }
  report.counts.samples++;
}
(async()=>{
  let wall=0;const opts={data,runtime,atlas,images,autoStart:false,reducedMotion:false,now:()=>wall};
  const original=baseline.create(null,opts),current=hand.create(null,{...opts,drawnRuntime:drawn,manifest,handdrawnImages:images});
  assert(await original.ready);assert(await current.ready);const rd=recorder(),td=recorder();
  for(let index=0;index<data.faces.length;index++){
    const item=data.faces[index];wall+=2000;original.setExpression(item.id);current.setExpression(item.id);current.setActivity(hand.activities[index%hand.activities.length],{owner:'original-eye-check'});
    const at=wall;
    for(let tick=0;tick<=10;tick++){
      wall=at+tick*TICK;const a=original.renderTo(rd.canvas,wall),b=current.renderTo(td.canvas,wall);compare(a,b,rd,td,item.id+' transition '+tick);
    }
    wall=at+1000;original.blink();current.blink();const blinkAt=wall;
    for(let tick=0;tick<9;tick++){
      wall=blinkAt+tick*TICK;compare(original.renderTo(rd.canvas,wall),current.renderTo(td.canvas,wall),rd,td,item.id+' blink '+tick);
    }
    assert.equal(current.expression,item.id);
  }
  report.counts.expressions=40;report.counts.activities=9;
  report.checks.push('All forty face IDs preserve the verified v5 original paths, raster eye cels, placements, and transition visuals','All forty blinks and sampled expression transitions match the verified original renderer','Activities may move or uniformly scale the whole face, but cannot distort one eye, alter eye/mouth proportions, or change source art','No generated replacement eye cel is painted');
  original.destroy();current.destroy();report.passed=true;fs.writeFileSync(path.join(here,'qa_original_eyes_report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
})().catch(error=>{report.failure=error.stack;fs.writeFileSync(path.join(here,'qa_original_eyes_report.json'),JSON.stringify(report,null,2)+'\n');console.error(error);process.exitCode=1;});
