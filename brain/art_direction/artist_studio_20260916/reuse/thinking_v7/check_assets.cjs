'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const sharp=require(process.env.MIST_SHARP_PATH||'<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=__dirname,manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'),'utf8'));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 assert.equal(manifest.complete,true);assert.equal(manifest.faceStyle,'original-mist');assert.equal(manifest.studies.length,6);
 const report={passed:false,assets:0,frames:0,newFrames:0,reusedFrames:0,minimumMargin:256,details:{}};
 for(const[id,a]of Object.entries(manifest.assets)){
  assert.equal(a.type,'activity');assert.equal(a.frames.length,a.reusedFrom?12:16);
  assert.equal(hash(fs.readFileSync(path.join(root,a.source))),a.sourceSha256);
  const hashes=new Set();let minMargin=256;
  for(const f of a.frames){
   const png=fs.readFileSync(path.join(root,f.file));assert.equal(hash(png),f.sha256);hashes.add(f.sha256);
   const {data,info}=await sharp(png).ensureAlpha().raw().toBuffer({resolveWithObject:true});assert.equal(info.width,256);assert.equal(info.height,256);
   let ink=0,transparent=0;
   for(let y=0;y<256;y++)for(let x=0;x<256;x++){const alpha=data[(y*256+x)*4+3];if(alpha>42){ink++;minMargin=Math.min(minMargin,x,y,255-x,255-y);}if(alpha===0)transparent++;}
   assert.ok(ink>20,id+' blank cel');assert.ok(transparent>32768,id+' background not transparent');
   report.frames++;if(a.reusedFrom)report.reusedFrames++;else report.newFrames++;
  }
  assert.ok(minMargin>=8,id+' clipped');assert.ok(hashes.size>=a.frames.length-1,id+' insufficient distinct drawings');
  report.minimumMargin=Math.min(report.minimumMargin,minMargin);report.details[id]={frames:a.frames.length,distinct:hashes.size,minMargin};report.assets++;
 }
 assert.equal(report.frames,88);assert.equal(report.newFrames,64);assert.equal(report.reusedFrames,24);
 const guards=JSON.parse(fs.readFileSync(path.join(root,'approved_runtime_hashes.json'),'utf8').replace(/^\uFEFF/,''));
 const project=path.resolve(root,'../../../../..');
 for(const[name,sha]of Object.entries(guards))assert.equal(hash(fs.readFileSync(path.join(project,name))),sha,'Approved runtime changed: '+name);
 report.approvedRuntimeUnchanged=true;report.passed=true;
 fs.writeFileSync(path.join(root,'asset_checks.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
