'use strict';

// Reuses the original MIST glyphs. New drawn cels are separate ImageGen inputs.
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const sharp = require('<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const ROOT = __dirname;
const REUSE = path.dirname(ROOT);
const W = 512, H = 320;
const clear = {r:0,g:0,b:0,alpha:0};
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const two = n => String(n).padStart(2,'0');
const originalParts = {round:'circle_gap_03',hook:'angry_hook_00',line:'mouth_line_30',smile:'mouth_smile_arc_38',bowl:'mouth_open_smile_filled_33',concern:'mouth_frown_arc_28'};
const cache = new Map();
const missing = new Set();
const provenance = new Map();

async function save(rel, bytes) {
  await fs.mkdir(path.dirname(path.join(ROOT,rel)), {recursive:true});
  await fs.writeFile(path.join(ROOT,rel),bytes);
  return {file:rel,sha256:sha(bytes)};
}
async function exists(rel) { try { await fs.access(path.join(ROOT,rel)); return true; } catch { return false; } }
async function transparent(w=W,h=H) { return sharp({create:{width:w,height:h,channels:4,background:clear}}).png().toBuffer(); }
async function original(name,isEye) {
  const key=`original:${name}:${isEye}`;
  if(cache.has(key)) return cache.get(key);
  const source=await fs.readFile(path.join(REUSE,'parts',name+'.svg'));
  const copied=await save('sources/canonical/'+name+'.svg',source);
  provenance.set(copied.file,{...copied,kind:'original MIST glyph',operation:'Unmodified source; uniform raster scale and rigid pose only'});
  const trimmed=await sharp(source).trim({threshold:1}).png().toBuffer();
  const meta=await sharp(trimmed).metadata();
  const width=isEye?92:(name==='mouth_line_30'?68:76);
  const bitmap=await sharp(trimmed).resize({width}).png().toBuffer();
  const bm=await sharp(bitmap).metadata();
  const result={bitmap,width:bm.width,height:bm.height,anchorX:bm.width/2,anchorY:bm.height/2,source:copied.file};
  cache.set(key,result); return result;
}
async function component(kind,family,index) {
  const rel=`components/${kind}/${family}/cell_${index}.png`;
  if(!await exists(rel)){missing.add(rel);return null;}
  if(cache.has(rel)) return cache.get(rel);
  const bitmap=await fs.readFile(path.join(ROOT,rel));
  const m=await sharp(bitmap).metadata();
  const result={bitmap,width:m.width,height:m.height,anchorX:64,anchorY:kind==='eyes'?92:26,source:rel};
  provenance.set(rel,{file:rel,sha256:sha(bitmap),kind:index===0?'original MIST canonical raster seed':'ImageGen drawn component',operation:'Rigid placement and optional mirroring'});
  cache.set(rel,result);return result;
}
async function place(asset,anchor,movement=[0,0,0],amount=0,mirror=false) {
  // This SVG is a fixed raster placement container; it draws no new silhouette.
  // A constant rotation origin avoids expanded-bitmap crop rounding between poses.
  const px=Math.round(anchor.x+movement[0]*amount),py=Math.round(anchor.y+movement[1]*amount);
  const angle=movement[2]*amount;
  const container=`<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><g transform="translate(${px} ${py}) rotate(${angle}) scale(${mirror?-1:1} 1)"><image x="${-asset.anchorX}" y="${-asset.anchorY}" width="${asset.width}" height="${asset.height}" xlink:href="data:image/png;base64,${asset.bitmap.toString('base64')}"/></g></svg>`;
  return sharp(Buffer.from(container)).png().toBuffer();
}
async function mouthFor(spec,index,signal) {
  if(spec.mouth==='line'||index===0||index===11) return await component('mouths','smile',0)||original(originalParts.line,false);
  const stage=spec.mouthStages?spec.mouthStages[index]:Math.round(signal.mouthProgression[index]*(spec.mouthMax??5)/5);
  return await component('mouths',spec.mouth,stage) || original(originalParts[spec.mouth],false);
}
async function checkLayer(bitmap,context) {
  const {data,info}=await sharp(bitmap).raw().toBuffer({resolveWithObject:true});
  let count=0,edge=0,left=info.width,top=info.height,right=-1,bottom=-1;
  for(let y=0;y<info.height;y++)for(let x=0;x<info.width;x++){
    const alpha=data[(y*info.width+x)*4+3];
    if(alpha>0){left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);}
    if(alpha>8){count++;if(x===0||y===0||x===info.width-1||y===info.height-1)edge++;}
  }
  if(!count||edge)throw Error(`${context}: ${!count?'empty layer':'clipped layer'}`);
  const x=Math.max(0,left-2),y=Math.max(0,top-2);
  return {x,y,width:Math.min(info.width-1,right+2)-x+1,height:Math.min(info.height-1,bottom+2)-y+1};
}
async function frameFromLayers(key,index,bitmaps,ticks,folder='frames') {
  const layers={};
  for(const [name,bitmap] of Object.entries(bitmaps)){
    const bounds=await checkLayer(bitmap,`${key}/${folder}/${index}/${name}`);
    const cropped=await sharp(bitmap).extract({left:bounds.x,top:bounds.y,width:bounds.width,height:bounds.height}).png().toBuffer();
    layers[name]={...await save(`${folder==='frames'?'layers':'blink-layers'}/${key}/${name}_${two(index)}.png`,cropped),...bounds};
  }
  const full=await sharp({create:{width:W,height:H,channels:4,background:clear}}).composite(Object.values(bitmaps).map(input=>({input,left:0,top:0}))).png().toBuffer();
  const recomposed=await sharp({create:{width:W,height:H,channels:4,background:clear}}).composite(await Promise.all(Object.values(layers).map(async l=>({input:await fs.readFile(path.join(ROOT,l.file)),left:l.x,top:l.y})))).raw().toBuffer();
  const raw=await sharp(full).raw().toBuffer();
  if(!raw.equals(recomposed))throw Error(`${key}/${index}: recomposition changed visible pixels`);
  return {index,...await save(`${folder}/${key}/${two(index)}.png`,full),exposureTicks:ticks,durationMs:Number((ticks*1000/15).toFixed(6)),layers};
}
async function build() {
  cache.clear();missing.clear();provenance.clear();
  const specs=JSON.parse(await fs.readFile(path.join(ROOT,'motion_specs.json'),'utf8'));
  const catalog=JSON.parse(await fs.readFile(path.join(REUSE,'acting_studies_v1/catalog.json'),'utf8'));
  const manifest={version:3,fps:15,kind:'Original MIST glyphs with composed acting poses and drawn component cels',liveAssetsChanged:false,canvas:{width:W,height:H},rig:specs.rig,groups:[],complete:false};
  let maxDisplacement=0;
  for(const group of catalog.groups){
    const outputGroup={...group,examples:[]};
    for(const item of group.examples){
      const key=group.id+'/'+item.id,spec=specs.examples[key];
      if(!spec)throw Error('No motion spec for '+key);
      const example={...item,notes:spec.action,key,width:W,height:H,restMs:spec.restMs,rig:specs.rig,action:spec.action,eyeFamilies:spec.eyes,mouthFamily:spec.mouth,frames:[],blinkFrames:[],sourceProvenance:[],registration:{method:'fixed semantic rig',mouthDrivesEyeRegistration:false,eyeBottomAttachmentY:190},motion:{type:'composed original MIST components',comic:!!spec.comic}};
      delete example.durations;
      const firstLayers={};
      for(let i=0;i<12;i++){
        const amount=(spec.path||specs.signal)[i];
        const bitmaps={};
        for(const [n,name] of ['leftEye','rightEye'].entries()){
          const movement=spec[n?'right':'left'];
          const canonical=await original(originalParts[spec.eyes[n]],true);
          const seed=await component('eyes',spec.eyes[n],0);
          const asset=seed||canonical;
          const anchor=seed?{x:specs.rig[name].x,y:190}:specs.rig[name];
          bitmaps[name]=await place(asset,anchor,movement,amount,n===1);
          if(i){const prev=(spec.path||specs.signal)[i-1];const delta=Math.hypot(movement[0]*(amount-prev),movement[1]*(amount-prev));maxDisplacement=Math.max(maxDisplacement,delta);if(delta>(spec.comic?10:6)+.001)throw Error(`${key}: excessive adjacent eye displacement ${delta}`);}
        }
        bitmaps.mouth=await place(await mouthFor(spec,i,specs),specs.rig.mouth,spec.mouthMotion,amount);
        if(i===0)Object.assign(firstLayers,bitmaps);
        example.frames.push(await frameFromLayers(key,i,bitmaps,spec.ticks[i]));
      }
      const blinkStages=[0,2,4,5,4,2,0];
      for(let i=0;i<7;i++){
        const bitmaps={mouth:firstLayers.mouth};
        for(const [n,name] of ['leftEye','rightEye'].entries()){
          if(i===0||i===6){bitmaps[name]=firstLayers[name];continue;}
          // All families meet at the same generated round closed cel and attachment.
          const family=i===3?'round':spec.eyes[n];
          const generated=await component('eyes',family,blinkStages[i]);
          if(generated)bitmaps[name]=await place(generated,{x:specs.rig[name].x,y:190},[0,0,0],0,n===1);
          else if(i===3)bitmaps[name]=await place(await original('flat_bar_14',true),{x:specs.rig[name].x,y:190});
          else bitmaps[name]=firstLayers[name];
        }
        example.blinkFrames.push(await frameFromLayers(key,i,bitmaps,1,'blinks'));
      }
      example.transition={close:[0,1,2,3],open:[3,4,5,6],source:'blinkFrames',sharedClosedIndex:3};
      example.sourceProvenance={eyeParts:spec.eyes.map(f=>originalParts[f]),mouthPart:originalParts[spec.mouth],sourceAuthority:'Original MIST parts; generated intermediate cels only',frameKind:'Twelve composed poses, not twelve separately generated full faces'};
      example.poses=[{label:'Setup',index:0,file:example.frames[0].file},{label:'Change',index:7,file:example.frames[7].file},{label:'Settle',index:11,file:example.frames[11].file}];
      const contacts=[];
      for(const f of example.frames){const input=await sharp(path.join(ROOT,f.file)).resize(256,160).flatten({background:'#101d20'}).png().toBuffer();contacts.push({input,left:(f.index%4)*256,top:Math.floor(f.index/4)*160});}
      example.contact=(await save(`contact/${key}.png`,await sharp({create:{width:1024,height:480,channels:4,background:'#101d20'}}).composite(contacts).png().toBuffer())).file;
      const strips=contacts.map((c,i)=>({...c,left:i*256,top:0}));
      example.filmstrip=(await save(`contact/${key}_strip.png`,await sharp({create:{width:3072,height:160,channels:4,background:'#101d20'}}).composite(strips).png().toBuffer())).file;
      outputGroup.examples.push(example);
      process.stdout.write(key+' composed\n');
    }
    manifest.groups.push(outputGroup);
  }
  manifest.sources=[...provenance.values()];
  const publicAssets=new Map();
  function include(record){if(record?.file&&record.sha256)publicAssets.set(record.file,{file:record.file,sha256:record.sha256});}
  manifest.sources.forEach(include);
  for(const group of manifest.groups)for(const ex of group.examples){
    for(const frame of [...ex.frames,...ex.blinkFrames]){include(frame);Object.values(frame.layers).forEach(include);}
    for(const file of [ex.contact,ex.filmstrip])include({file,sha256:sha(await fs.readFile(path.join(ROOT,file)))});
  }
  const componentAssets=[];
  for(const [kind,families] of [['eyes',['round','hook']],['mouths',['smile','bowl','concern']]]){
    for(const family of families){for(let i=0;i<6;i++)componentAssets.push(`components/${kind}/${family}/cell_${i}.png`);}
  }
  if(await exists('components/eyes/manifest.json')){
    const eyes=JSON.parse(await fs.readFile(path.join(ROOT,'components/eyes/manifest.json'),'utf8'));
    for(const family of Object.values(eyes.families))componentAssets.push('components/eyes/'+family.selectedSource);
  }
  for(const family of ['smile','bowl','concern'])componentAssets.push(`components/mouths/${family}/source.png`);
  for(const file of componentAssets)if(await exists(file))include({file,sha256:sha(await fs.readFile(path.join(ROOT,file)))});
  manifest.publicAssets=[...publicAssets.values()];
  manifest.complete=missing.size===0;
  manifest.componentsReady=missing.size===0;
  manifest.validation={technicalPassed:true,layerRecomposition:'pixel-identical',emptyLayers:0,clippedLayers:0,maxAdjacentEyeTranslationPx:Number(maxDisplacement.toFixed(3)),visualReview:'pending independent motion review',missingComponents:[...missing]};
  await fs.writeFile(path.join(ROOT,'asset_checks.json'),JSON.stringify({passed:missing.size===0,...manifest.validation},null,2)+'\n');
  await fs.writeFile(path.join(ROOT,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
  process.stdout.write(JSON.stringify({complete:manifest.complete,missing:[...missing],validation:manifest.validation})+'\n');
}
if(require.main===module)build().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={build};
