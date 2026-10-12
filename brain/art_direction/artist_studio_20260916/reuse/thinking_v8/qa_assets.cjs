'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const sharp=require(process.env.MIST_SHARP_PATH||'<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const here=__dirname,sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const expected={reading:'book',coding:'terminal',writing:'note',sorting:'cards',searching:'searching',pondering:'planning',connecting:'connecting',checking:'checking'};
const report={passed:false,checkedAt:new Date().toISOString(),checks:[],failures:[],warnings:[],assets:{},counts:{assets:0,frames:0},limits:['Alpha and hash checks cannot establish coherent page perspective, natural movement, or the absence of misleading visual success symbols. Those need visual review.']};
async function check(name,fn){try{await fn();report.checks.push(name);}catch(e){report.failures.push({name,error:e.message});}}
const diff=(a,b)=>{let n=0;for(let i=3;i<a.length;i+=4)n+=Math.abs(a[i]-b[i])/255;return n/65536;};
(async()=>{
 const bytes=fs.readFileSync(path.join(here,'manifest.json')),manifest=JSON.parse(bytes);report.manifestSha256=sha(bytes);
 await check('Eight studies resolve to eight separate 24-cel assets',()=>{
  assert.equal(manifest.version,8);assert.equal(manifest.fps,15);assert.equal(manifest.complete,true);assert.equal(manifest.faceStyle,'original-mist');
  assert.deepEqual(Object.fromEntries(manifest.studies.map(s=>[s.id,s.asset])),expected);
  assert.deepEqual(Object.keys(manifest.assets).sort(),Object.values(expected).sort());
  assert.equal(new Set(manifest.studies.flatMap(s=>s.faceVariants)).size,3);
 });
 for(const id of Object.values(expected))await check(id+' source, registration, transparency, and pixel integrity',async()=>{
  const asset=manifest.assets[id];assert(asset,id+' absent');assert.equal(asset.type,'activity');assert.equal(asset.columns,6);assert.equal(asset.rows,4);assert.equal(asset.frames.length,24);assert.deepEqual(asset.phaseFrames,{entrance:4,loop:16,exit:4});
  assert(!asset.reusedFrom,'Undeclared v7 reuse is not accepted');assert(asset.scale>0&&Number.isFinite(asset.scale));
  const source=fs.readFileSync(path.join(here,asset.source));assert.equal(sha(source),asset.sourceSha256);
  const metadata=await sharp(source).metadata();assert(metadata.hasAlpha,'Source must retain native alpha');assert.deepEqual(asset.sourceSize,[metadata.width,metadata.height]);
  const assemblyParts=asset.assembly?(asset.assembly.components?Object.values(asset.assembly.components):[{file:asset.assembly.component,sha256:asset.assembly.componentSha256}]):[];
  if(asset.assembly){
   assert(asset.assembly.method,'Assembly must describe the component reuse');
   assert(assemblyParts.length,'Assembly must declare its generated components');
   for(const part of assemblyParts){const file=part.file||part.component,hash=part.sha256||part.componentSha256;assert(file&&hash,'Component file and hash are required');assert.equal(sha(fs.readFileSync(path.join(here,file))),hash);if(part.source){assert(part.sourceSha256,'Component source hash is required');assert.equal(sha(fs.readFileSync(path.join(here,part.source))),part.sourceSha256);}}
  }
  const promptCandidates=fs.readdirSync(path.join(here,'prompts')).filter(f=>f===id+'.txt'||f.startsWith(id+'_'));assert(promptCandidates.length,'Exact prompt must be saved');
  const samples=[],hashes=[],adjacentPoseSteps=[];let minMargin=256,minClear=65536;
  for(let n=0;n<24;n++){
   const frame=asset.frames[n];assert.equal(frame.pose,n<4?'enter_'+n:n<20?'loop_'+(n-4):'exit_'+(n-20));
   const sourceIndex=asset.assembly?(frame.sourceCellIndex??asset.assembly.sourceCell):n;
   if(Number.isInteger(sourceIndex)){
    const col=sourceIndex%6,row=Math.floor(sourceIndex/6),x=Math.round(col*metadata.width/6),y=Math.round(row*metadata.height/4);
    assert.deepEqual(frame.sourceCell,[x,y,Math.round((col+1)*metadata.width/6)-x,Math.round((row+1)*metadata.height/4)-y]);
   }else{
    assert(asset.assembly&&(frame.placements||frame.components),'Multi-source assembly must declare component poses for each exported cel');
    if(frame.sourceCell)assert(assemblyParts.some(p=>JSON.stringify(p.sourceCell)===JSON.stringify(frame.sourceCell)),'Frame source cell must match a declared generated component');
   }
   if(asset.assembly)assert(frame.placements||frame.components||frame.marker||frame.markerPosition,'Assembly must declare its per-frame component pose');
   if(asset.assembly&&n>4&&n<20){
    const positions=f=>f.placements||f.components||(f.marker?[f.marker]:f.markerPosition?[f.markerPosition]:[]),before=positions(asset.frames[n-1]),after=positions(frame);
    if(Array.isArray(before)&&Array.isArray(after)&&before.length===after.length){
     const changes=after.map((p,i)=>Math.max(Math.hypot((p.x??0)-(before[i].x??0),(p.y??0)-(before[i].y??0)),Math.abs((p.angle??0)-(before[i].angle??0)),Math.abs((p.scale??1)-(before[i].scale??1))*100,Math.abs((p.alpha??1)-(before[i].alpha??1))*100));
     const movement=Math.max(0,...changes);assert(movement>=1,id+' adjacent active poses '+(n-1)+'/'+n+' lack a meaningful declared component movement');adjacentPoseSteps.push(+movement.toFixed(4));
    }
   }
   const exported=fs.readFileSync(path.join(here,frame.file));assert.equal(sha(exported),frame.sha256);
   const {data,info}=await sharp(exported).ensureAlpha().raw().toBuffer({resolveWithObject:true});assert.equal(info.width,256);assert.equal(info.height,256);
   let visible=0,clear=0,left=256,top=256,right=-1,bottom=-1;
   for(let yy=0;yy<256;yy++)for(let xx=0;xx<256;xx++){
    const alpha=data[(yy*256+xx)*4+3];if(alpha===0)clear++;if(alpha>42){visible++;left=Math.min(left,xx);top=Math.min(top,yy);right=Math.max(right,xx);bottom=Math.max(bottom,yy);}
   }
   assert(visible>15,id+' cel '+n+' is empty');assert(clear>32768,id+' cel '+n+' lacks clear background');
   const margin=Math.min(left,top,255-right,255-bottom);assert(margin>=8,id+' cel '+n+' needs crop clearance');minMargin=Math.min(minMargin,margin);minClear=Math.min(minClear,clear);
   const [bx,by,bw,bh]=frame.bounds;assert(left>=bx&&top>=by&&right<bx+bw&&bottom<by+bh,'Manifest bounds must contain visible pixels');
   samples.push(data);hashes.push(sha(data));report.counts.frames++;
  }
  const uniqueActive=new Set(hashes.slice(4,20)).size;assert(uniqueActive>1,'The entire active sequence is pixel-identical');
  if(asset.assembly&&['checking','connecting'].includes(id)){
   const active=asset.frames.slice(4,20),markers=active.map(f=>f.markerPosition||f.marker);assert(markers.every(p=>Number.isFinite(p?.x)&&Number.isFinite(p?.y)),'Scan assembly needs a visible marker position per active frame');
   for(const f of active){assert.deepEqual(f.bodyBounds,active[0].bodyBounds,'Scan body bounds must remain fixed');assert.deepEqual(f.components[0],active[0].components[0],'Scan body component must remain fixed');}
   const distances=markers.map((p,i)=>Math.hypot(p.x-markers[(i+1)%16].x,p.y-markers[(i+1)%16].y));assert(distances.slice(0,-1).every(d=>d>=1),'Adjacent marker positions must advance');assert(distances.at(-1)<=Math.max(...distances.slice(0,-1))+.01,'Loop seam must not jump farther than an ordinary scan step');
  }
  const changes=Array.from({length:16},(_,n)=>diff(samples[4+n],samples[n===15?4:5+n]));
  if(changes.at(-1)>Math.max(...changes.slice(0,-1))*1.75+.004)report.warnings.push(id+' loop seam is larger than inner steps; inspect in motion');
  report.assets[id]={frames:24,construction:asset.assembly?'declared generated-component assembly':'source-sheet drawings',assemblyComponents:asset.assembly?.components?Object.keys(asset.assembly.components).length:asset.assembly?1:0,adjacentPoseSteps,uniquePixelFrames:new Set(hashes).size,uniqueActivePixelFrames:new Set(hashes.slice(4,20)).size,minMargin,minTransparentPixels:minClear,loopAlphaDifferences:changes.map(x=>+x.toFixed(6)),sourceSha256:asset.sourceSha256};report.counts.assets++;
 });
  await check('The exported manifest contains all 192 expected cels',()=>{assert.equal(report.counts.assets,8);assert.equal(report.counts.frames,192);});
 report.assetIntegrityPassed=report.failures.length===0;
 await check('Manual semantic-motion review approves these exact sources and contact sheets',()=>{
  const visual=JSON.parse(fs.readFileSync(path.join(here,'qa_visual_report.json')));assert.equal(visual.passed,true,'Visual review is pending or has rejected poses');
  for(const [id,asset] of Object.entries(manifest.assets)){
    const item=visual.assets[id];assert.equal(item?.approved,true,id+' has no manual approval');assert.equal(item.sourceSha256,asset.sourceSha256,id+' visual review belongs to an older source');assert.equal(item.contactSha256,sha(fs.readFileSync(path.join(here,'contact_'+id+'.png'))),id+' contact sheet changed after visual review');assert.equal(item.semanticReviewComplete,true,id+' lacks an actual consecutive-pose review');
  }
 });
  report.passed=report.failures.length===0;
})().catch(e=>report.failures.push({name:'QA inputs',error:e.stack})).finally(()=>{
 fs.writeFileSync(path.join(here,'qa_assets_report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(!report.passed)process.exitCode=1;
});
