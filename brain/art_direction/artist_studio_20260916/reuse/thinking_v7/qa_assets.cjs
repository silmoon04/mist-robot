'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const sharp=require(process.env.MIST_SHARP_PATH||'<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const here=__dirname,repo=path.resolve(here,'../../../../..');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const report={passed:false,checkedAt:new Date().toISOString(),checks:[],warnings:[],assets:{},counts:{assets:0,frames:0}};
const expected={book:16,terminal:16,note:16,cards:16,searching:12,planning:12};
const difference=(a,b)=>{let sum=0;for(let i=3;i<a.length;i+=4)sum+=Math.abs(a[i]-b[i])/255;return sum/(256*256);};
(async()=>{
  const text=fs.readFileSync(path.join(here,'manifest.json')),manifest=JSON.parse(text);report.manifestSha256=sha(text);
  assert.equal(manifest.version,7);assert.equal(manifest.fps,15);assert.equal(manifest.complete,true);assert.equal(manifest.faceStyle,'original-mist');
  assert.deepEqual(Object.keys(manifest.assets).sort(),Object.keys(expected).sort());assert.equal(manifest.studies.length,6);
  for(const study of manifest.studies){assert(expected[study.asset]);assert(study.faceId);}
  for(const [id,asset]of Object.entries(manifest.assets)){
    assert.equal(asset.type,'activity');assert.equal(asset.frames.length,expected[id]);assert.equal(sha(fs.readFileSync(path.join(here,asset.source))),asset.sourceSha256);
    const samples=[];let minMargin=255;const frameHashes=[];
    for(const frame of asset.frames){
      const bytes=fs.readFileSync(path.join(here,frame.file));assert.equal(sha(bytes),frame.sha256);frameHashes.push(frame.sha256);
      const {data,info}=await sharp(bytes).ensureAlpha().raw().toBuffer({resolveWithObject:true});assert.equal(info.width,256);assert.equal(info.height,256);
      let visible=0,transparent=0;
      for(let y=0;y<256;y++)for(let x=0;x<256;x++){
        const alpha=data[(y*256+x)*4+3];if(alpha>42){visible++;minMargin=Math.min(minMargin,x,y,255-x,255-y);}if(alpha===0)transparent++;
      }
      assert(visible>15,id+' visible cel');assert(transparent>256*256*.5,id+' transparent background');assert(minMargin>=8,id+' safe border');
      samples.push(data);report.counts.frames++;
    }
    const loopEnd=expected[id]-4,changes=[];for(let i=4;i<loopEnd;i++)changes.push(difference(samples[i],samples[i+1<loopEnd?i+1:4]));
    const inside=changes.slice(0,-1),seam=changes.at(-1),maxInside=Math.max(...inside);
    if(seam>maxInside*1.75+.004)report.warnings.push(id+' loop seam differs more than its inner steps; inspect visually');
    assert(new Set(frameHashes.slice(4,loopEnd)).size>=(loopEnd-4)/2,id+' actual changing loop art');
    if(asset.reusedFrom){const prior=JSON.parse(fs.readFileSync(path.join(here,'../handdrawn_v6/manifest.json'))).assets[id];assert.deepEqual(asset.frames.map(f=>f.sha256),prior.frames.map(f=>f.sha256));}
    report.assets[id]={frames:expected[id],minMargin,loopFrameHashes:new Set(frameHashes.slice(4,loopEnd)).size,loopDifferences:changes.map(v=>Number(v.toFixed(6))),sourceSha256:asset.sourceSha256};report.counts.assets++;
  }
  report.assetValidationPassed=true;
  const starting=JSON.parse(fs.readFileSync(path.join(here,'qa_baseline_files.json')));
  report.protectedFileDifferences=[];
  for(const [file,hash]of Object.entries(starting)){const current=sha(fs.readFileSync(path.join(repo,file)));if(current!==hash)report.protectedFileDifferences.push({file,expected:hash,actual:current});}
  report.protectedFilesUnchanged=report.protectedFileDifferences.length===0;
  for(const [file,hash]of Object.entries(starting))assert.equal(sha(fs.readFileSync(path.join(repo,file))),hash,'Separate preview must not change '+file);
  assert.equal(report.counts.frames,88);report.checks.push('Six props and 88 registered transparent cels match source and manifest hashes','New 16-frame and reused 12-frame props are accepted according to actual length','Every cel is nonempty with an eight-pixel or larger safety margin','Reused searching/planning cels remain byte-identical','Only props are included; original eyes remain supplied by the existing renderer','The approved v6 page and live phone files match their starting hashes');
  report.passed=true;fs.writeFileSync(path.join(here,'qa_assets_report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
})().catch(error=>{report.failure=error.stack;fs.writeFileSync(path.join(here,'qa_assets_report.json'),JSON.stringify(report,null,2)+'\n');console.error(error);process.exitCode=1;});
