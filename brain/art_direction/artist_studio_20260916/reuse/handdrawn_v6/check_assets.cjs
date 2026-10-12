'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const sharp=require(process.env.MIST_SHARP_PATH||'<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=__dirname,manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'),'utf8'));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 assert.equal(manifest.complete,true);assert.equal(manifest.fps,15);assert.equal(manifest.activities.length,9);
 const report={passed:false,sourceSheets:0,frames:0,eyeFamilies:0,activities:9,warnings:[],assets:{}};
 for(const[id,a]of Object.entries(manifest.assets)){
  const expected=a.type==='eye'?8:12;assert.equal(a.frames.length,expected,id);
  assert.equal(hash(fs.readFileSync(path.join(root,a.source))),a.sourceSha256,id+' source changed');
  const pixels=[];let minMargin=Infinity;
  for(const f of a.frames){
   const file=path.join(root,f.file);assert.equal(hash(fs.readFileSync(file)),f.sha256);
   const{data,info}=await sharp(file).ensureAlpha().raw().toBuffer({resolveWithObject:true});
   assert.equal(info.width,256);assert.equal(info.height,256);let ink=0,empty=0;
   for(let y=0;y<256;y++)for(let x=0;x<256;x++){const alpha=data[(y*256+x)*4+3];if(alpha>40){ink++;minMargin=Math.min(minMargin,x,y,255-x,255-y);}if(alpha===0)empty++;}
   assert.ok(ink>15,id+' blank');assert.ok(empty>256*256*.5,id+' not transparent');
   pixels.push(data);report.frames++;
  }
  assert.ok(minMargin>=8,id+' edge clipping');
  const compare=(a,b)=>{let n=0;for(let i=3;i<a.length;i+=4)n+=Math.abs(a[i]-b[i])/255;return Number((n/(256*256)).toFixed(5));};
  const item={frames:expected,minMargin,distinctFiles:new Set(a.frames.map(f=>f.sha256)).size};
  assert.ok(item.distinctFiles>=expected-1,id+' repeated cels');
  if(a.type==='eye'){
   report.eyeFamilies++;
   const open=a.frames[0].bounds,closed=a.frames[3].bounds;
   item.closedToOpenHeight=Number((closed[3]/open[3]).toFixed(3));
   assert.ok(closed[3]<open[3]*.82,id+' no visible blink closure');
   assert.ok(closed[2]>open[2]*.65,id+' closed lid shrinks too much horizontally');
  }else{
   item.loopDifferences=[compare(pixels[4],pixels[5]),compare(pixels[5],pixels[6]),compare(pixels[6],pixels[7]),compare(pixels[7],pixels[4])];
   if(item.loopDifferences[3]>Math.max(...item.loopDifferences.slice(0,3))*1.7+.007)report.warnings.push(id+' loop seam needs visual review');
  }
  report.assets[id]=item;report.sourceSheets++;
 }
 for(const activity of manifest.activities){assert.ok(manifest.assets[activity.id]);assert.equal(activity.eyes,undefined);}
 assert.equal(manifest.faceStyle,'original-mist');assert.equal(report.eyeFamilies,0);assert.equal(report.frames,108);
 report.passed=true;fs.writeFileSync(path.join(root,'asset_checks.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
