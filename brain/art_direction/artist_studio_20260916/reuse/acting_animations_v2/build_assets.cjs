'use strict';

// Mechanical extraction only: the selected ImageGen sheets are never altered.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sharp = require('<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const ROOT = __dirname;
const CATALOG = path.join(ROOT, '../acting_studies_v1/catalog.json');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const json = (file, value) => fs.writeFileSync(path.join(ROOT, file), JSON.stringify(value, null, 2) + '\n');
const save = (file, bytes) => { fs.mkdirSync(path.dirname(path.join(ROOT, file)), {recursive:true}); fs.writeFileSync(path.join(ROOT, file), bytes); };
const round = n => Math.round(n * 1000) / 1000;
// Detection ignores <3.2% opacity specks, but extraction retains every pixel.
const STRUCTURE_ALPHA = 8;
const args = process.argv.slice(2);
const partial = args.includes('--partial') || args.includes('--group');
const groupArg = args.indexOf('--group');
const groupFilter = groupArg < 0 ? null : args[groupArg + 1];
if (groupArg >= 0 && (!groupFilter || groupFilter.startsWith('--'))) throw Error('--group requires an ID');

function metrics(raw, width, height, rect = {left:0, top:0, width, height}) {
  let count=0, weighted=0, sumX=0, sumY=0, minX=width, minY=height, maxX=-1, maxY=-1;
  for(let y=rect.top;y<rect.top+rect.height;y++) for(let x=rect.left;x<rect.left+rect.width;x++) {
    const a=raw[(y*width+x)*4+3];
    if(a<STRUCTURE_ALPHA) continue;
    count++; weighted+=a/255; sumX+=x*a/255; sumY+=y*a/255;
    minX=Math.min(minX,x); minY=Math.min(minY,y); maxX=Math.max(maxX,x); maxY=Math.max(maxY,y);
  }
  return {
    visiblePixels:count, alphaArea:round(weighted),
    bbox:count ? [minX,minY,maxX-minX+1,maxY-minY+1] : null,
    centroid:count ? [round(sumX/weighted),round(sumY/weighted)] : null,
    minimumMargin:count ? Math.min(minX-rect.left,minY-rect.top,rect.left+rect.width-1-maxX,rect.top+rect.height-1-maxY) : null
  };
}

function emptyRuns(occupied, low, high) {
  const runs=[];
  for(let start=Math.ceil(low);start<=Math.floor(high);start++) {
    if(occupied[start]) continue;
    let end=start;
    while(end+1<=Math.floor(high) && !occupied[end+1]) end++;
    runs.push({start,end,center:Math.floor((start+end)/2),length:end-start+1});
    start=end;
  }
  return runs;
}

function splitFeatures(frames,width,height) {
  const occupiedY = new Uint8Array(height);
  for(const raw of frames) for(let y=0;y<height;y++) for(let x=0;x<width;x++) if(raw[(y*width+x)*4+3]>=STRUCTURE_ALPHA) occupiedY[y]=1;
  const rows = emptyRuns(occupiedY,height*.32,height*.86).filter(run => frames.every(raw =>
    metrics(raw,width,height,{left:0,top:0,width,height:run.center}).visiblePixels>=30 &&
    metrics(raw,width,height,{left:0,top:run.center,width,height:height-run.center}).visiblePixels>=8));
  rows.sort((a,b)=>(b.length-Math.abs(b.center-height*.64)*.2)-(a.length-Math.abs(a.center-height*.64)*.2));
  if(!rows.length) throw Error('No transparent horizontal band shared by all 12 frames separates eyes from mouth.');
  const y=rows[0].center;
  const occupiedX=new Uint8Array(width);
  for(const raw of frames) for(let sy=0;sy<y;sy++) for(let x=0;x<width;x++) if(raw[(sy*width+x)*4+3]>=STRUCTURE_ALPHA) occupiedX[x]=1;
  const cols=emptyRuns(occupiedX,width*.30,width*.70).filter(run => frames.every(raw =>
    metrics(raw,width,height,{left:0,top:0,width:run.center,height:y}).visiblePixels>=8 &&
    metrics(raw,width,height,{left:run.center,top:0,width:width-run.center,height:y}).visiblePixels>=8));
  cols.sort((a,b)=>(b.length-Math.abs(b.center-width*.5)*.5)-(a.length-Math.abs(a.center-width*.5)*.5));
  if(!cols.length) throw Error('No transparent central gap shared by all 12 frames separates the eyes.');
  const x=cols[0].center;
  return {
    horizontalBand:[rows[0].start,rows[0].end], centralGap:[cols[0].start,cols[0].end],
    rects:{leftEye:{left:0,top:0,width:x,height:y},rightEye:{left:x,top:0,width:width-x,height:y},mouth:{left:0,top:y,width,height:height-y}}
  };
}

function imageDifference(a,b,width,height) {
  let total=0, union=0;
  for(let i=0;i<a.length;i+=4) {
    const av=a[i+3]/255, bv=b[i+3]/255;
    if(av || bv) union++;
    total+=Math.abs(av-bv);
  }
  return {alphaDifferencePerVisiblePixel:round(total/Math.max(1,union)), visibleUnion:union};
}

function median(values) { const sorted=[...values].sort((a,b)=>a-b); return (sorted[Math.floor((sorted.length-1)/2)]+sorted[Math.ceil((sorted.length-1)/2)])/2; }

function separateByComponents(raw,width,height) {
  const length=width*height,seen=new Uint8Array(length),components=[];
  const queue=new Int32Array(length),directions=[[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]];
  for(let start=0;start<length;start++) {
    if(seen[start] || raw[start*4+3]<STRUCTURE_ALPHA) continue;
    let head=0,tail=1;queue[0]=start;seen[start]=1;
    const pixels=[];let minX=width,minY=height,maxX=-1,maxY=-1,sumX=0,sumY=0;
    while(head<tail) {
      const p=queue[head++],x=p%width,y=Math.floor(p/width);pixels.push(p);
      minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);sumX+=x;sumY+=y;
      for(const [dx,dy] of directions) {
        const nx=x+dx,ny=y+dy;if(nx<0||nx>=width||ny<0||ny>=height)continue;
        const n=ny*width+nx;if(!seen[n]&&raw[n*4+3]>=STRUCTURE_ALPHA){seen[n]=1;queue[tail++]=n;}
      }
    }
    components.push({pixels,visiblePixels:pixels.length,bbox:[minX,minY,maxX-minX+1,maxY-minY+1],centroid:[sumX/pixels.length,sumY/pixels.length]});
  }
  const major=[...components].sort((a,b)=>b.visiblePixels-a.visiblePixels).slice(0,3);
  if(major.length<3 || major.some(c=>c.visiblePixels<16)) throw Error('Cannot identify three distinct eye/mouth ink components.');
  const mouth=[...major].sort((a,b)=>b.centroid[1]-a.centroid[1])[0];
  const eyes=major.filter(c=>c!==mouth).sort((a,b)=>a.centroid[0]-b.centroid[0]);
  if(mouth.centroid[1]<=Math.max(...eyes.map(c=>c.centroid[1])) || eyes[1].centroid[0]-eyes[0].centroid[0]<width*.1) throw Error('Connected ink components do not form two eyes above a mouth.');
  const named={leftEye:eyes[0],rightEye:eyes[1],mouth};
  const names=['leftEye','rightEye','mouth'],labels=new Uint8Array(length);
  const distanceToBox=(p,b)=>{
    const x=p[0],y=p[1],dx=Math.max(b[0]-x,0,x-(b[0]+b[2]-1)),dy=Math.max(b[1]-y,0,y-(b[1]+b[3]-1));return dx*dx+dy*dy;
  };
  let head=0,tail=0;
  for(const component of components) {
    let feature=names.findIndex(name=>named[name]===component);
    if(feature<0) feature=names.map((name,index)=>({index,d:distanceToBox(component.centroid,named[name].bbox)})).sort((a,b)=>a.d-b.d)[0].index;
    for(const p of component.pixels){labels[p]=feature+1;queue[tail++]=p;}
  }
  // Assign faint antialiasing/noise to the nearest already-labelled ink. No alpha is removed.
  while(head<tail) {
    const p=queue[head++],x=p%width,y=Math.floor(p/width);
    for(const [dx,dy] of directions) {
      const nx=x+dx,ny=y+dy;if(nx<0||nx>=width||ny<0||ny>=height)continue;
      const n=ny*width+nx;if(!labels[n]){labels[n]=labels[p];queue[tail++]=n;}
    }
  }
  const masks=Object.fromEntries(names.map(name=>[name,Buffer.alloc(raw.length)]));
  const bounds=Object.fromEntries(names.map(name=>[name,{minX:width,minY:height,maxX:-1,maxY:-1}]));
  for(let p=0;p<length;p++) if(raw[p*4+3]) {
    const name=names[labels[p]-1],x=p%width,y=Math.floor(p/width),box=bounds[name];
    raw.copy(masks[name],p*4,p*4,p*4+4);
    box.minX=Math.min(box.minX,x);box.minY=Math.min(box.minY,y);box.maxX=Math.max(box.maxX,x);box.maxY=Math.max(box.maxY,y);
  }
  const rects=Object.fromEntries(names.map(name=>{const b=bounds[name];return [name,{left:b.minX,top:b.minY,width:b.maxX-b.minX+1,height:b.maxY-b.minY+1}];}));
  return {method:'connected-components',rects,masks,featureBounds:Object.fromEntries(names.map(name=>[name,named[name].bbox])),
    metadata:{method:'connected-components',structuralComponents:components.length,primaryBounds:Object.fromEntries(names.map(name=>[name,named[name].bbox])),
      lowAlphaAssignment:'nearest labelled ink by eight-neighbour propagation',pixelsRepainted:false}};
}

function separationForFrame(raw,width,height) {
  try { return {...splitFeatures([raw],width,height),method:'rectangular-bands'}; }
  catch(_) {return separateByComponents(raw,width,height);}
}

function equalVisibleRgba(a,b) {
  if(a.length!==b.length)return false;
  for(let p=0;p<a.length;p+=4) {
    if(a[p+3]!==b[p+3]) return false;
    if(a[p+3] && (a[p]!==b[p]||a[p+1]!==b[p+1]||a[p+2]!==b[p+2])) return false;
  }
  return true;
}

function normalizeTransparentRgb(raw) {
  const normalized=Buffer.from(raw);
  let pixelsCleared=0;
  for(let p=0;p<normalized.length;p+=4) if(normalized[p+3]===0) {
    if(normalized[p]||normalized[p+1]||normalized[p+2])pixelsCleared++;
    normalized[p]=0;normalized[p+1]=0;normalized[p+2]=0;
  }
  return {raw:normalized,pixelsCleared};
}

function appearanceHash(raw) {
  return sha(normalizeTransparentRgb(raw).raw);
}

function registerFrames(sourceRaws,sourceWidth,sourceHeight) {
  // Stable facial anchors distinguish sheet placement drift from an acting beat.
  // Only the full face is moved; individual features are never warped or scaled.
  const anchors=sourceRaws.map((raw,index)=>{
    let splits;try {splits=separationForFrame(raw,sourceWidth,sourceHeight);} catch(error){throw Error(`Frame ${index}: ${error.message}`);}
    const left=splits.featureBounds?.leftEye||metrics(raw,sourceWidth,sourceHeight,splits.rects.leftEye).bbox;
    const right=splits.featureBounds?.rightEye||metrics(raw,sourceWidth,sourceHeight,splits.rects.rightEye).bbox;
    const mouth=splits.featureBounds?.mouth||metrics(raw,sourceWidth,sourceHeight,splits.rects.mouth).bbox;
    return {x:((left[0]+left[2]/2)+(right[0]+right[2]/2))/2,y:mouth[1]+mouth[3]/2};
  });
  const target={x:median(anchors.map(a=>a.x)),y:median(anchors.map(a=>a.y))};
  const shifts=anchors.map(a=>({x:Math.round(target.x-a.x),y:Math.round(target.y-a.y)}));
  const minX=Math.min(...shifts.map(s=>s.x)),minY=Math.min(...shifts.map(s=>s.y));
  const maxX=Math.max(...shifts.map(s=>s.x)),maxY=Math.max(...shifts.map(s=>s.y));
  const width=sourceWidth+maxX-minX,height=sourceHeight+maxY-minY;
  const translations=shifts.map(s=>({x:s.x-minX,y:s.y-minY}));
  const raws=sourceRaws.map((raw,index)=>{
    const output=Buffer.alloc(width*height*4),offset=translations[index];
    for(let y=0;y<sourceHeight;y++) raw.copy(output,((y+offset.y)*width+offset.x)*4,y*sourceWidth*4,(y+1)*sourceWidth*4);
    return output;
  });
  return {width,height,raws,anchors,translations,target:{x:target.x-minX,y:target.y-minY}};
}

async function compileExample(group, original, report) {
  const key=`${group.id}/${original.id}`, sheet=`source/${key}.png`;
  const source=fs.readFileSync(path.join(ROOT,sheet));
  const meta=await sharp(source).metadata();
  if(!meta.hasAlpha) throw Error('Source has no alpha channel; regenerate with a genuinely transparent background.');
  const decoded=await sharp(source).ensureAlpha().raw().toBuffer();
  let transparent=0, translucent=0;
  for(let p=3;p<decoded.length;p+=4) { if(decoded[p]===0) transparent++; else if(decoded[p]<255) translucent++; }
  const transparentFraction=transparent/(meta.width*meta.height);
  if(transparentFraction<.25) throw Error(`Only ${round(transparentFraction*100)}% transparent pixels; the sheet is opaque or contains a backdrop.`);
  const sourceCellWidth=Math.ceil(meta.width/4), sourceCellHeight=Math.ceil(meta.height/3);
  const frameBuffers=[], sourceRaws=[], rects=[];
  for(let index=0;index<12;index++) {
    const col=index%4,row=Math.floor(index/4);
    const left=Math.round(col*meta.width/4),top=Math.round(row*meta.height/3);
    const cropWidth=Math.round((col+1)*meta.width/4)-left,cropHeight=Math.round((row+1)*meta.height/3)-top;
    const image=await sharp(source).extract({left,top,width:cropWidth,height:cropHeight})
      .extend({top:0,left:0,right:sourceCellWidth-cropWidth,bottom:sourceCellHeight-cropHeight,background:{r:0,g:0,b:0,alpha:0}}).png().toBuffer();
    sourceRaws.push(await sharp(image).ensureAlpha().raw().toBuffer());
    rects.push([left,top,cropWidth,cropHeight]);
  }
  const registered=registerFrames(sourceRaws,sourceCellWidth,sourceCellHeight);
  const {width,height}=registered;
  const normalization=registered.raws.map(before=>{
    const result=normalizeTransparentRgb(before),after=result.raw;
    const alphaBefore=Buffer.from(before.filter((_,index)=>index%4===3));
    const alphaAfter=Buffer.from(after.filter((_,index)=>index%4===3));
    const check={pixelsCleared:result.pixelsCleared,visibleRgbaUnchanged:equalVisibleRgba(before,after),
      beforeAppearanceSha256:appearanceHash(before),afterAppearanceSha256:appearanceHash(after),
      beforeAlphaSha256:sha(alphaBefore),afterAlphaSha256:sha(alphaAfter)};
    if(!check.visibleRgbaUnchanged || check.beforeAppearanceSha256!==check.afterAppearanceSha256 || check.beforeAlphaSha256!==check.afterAlphaSha256) throw Error('Transparent RGB normalization changed a visible pixel or alpha.');
    return {raw:after,check};
  });
  const raws=normalization.map(result=>result.raw);
  for(const raw of raws) frameBuffers.push(await sharp(raw,{raw:{width,height,channels:4}}).png().toBuffer());
  let sharedSplits=null;
  try {sharedSplits=splitFeatures(raws,width,height);} catch(_) { /* Per-frame partitions retain the same layer API. */ }
  const frameSplits=raws.map(raw=>sharedSplits?{...sharedSplits,method:'rectangular-bands'}:separationForFrame(raw,width,height));
  const hasMasks=frameSplits.some(s=>s.method==='connected-components');
  const {durations,...details}=original;
  const example={...details,key,sheet,width,height,restMs:1000,sourceSha256:sha(source),sourceWidth:meta.width,sourceHeight:meta.height,
    sourceGrid:{columns:4,rows:3,order:'row-major'},
    registration:{method:'rigid-integer-translation',sourceCellWidth,sourceCellHeight,anchor:'mean eye bounds x; mouth bounds center y',target:registered.target,pixelsResampled:false},
    displayOptimization:{method:'zero-rgb-only-where-alpha-equals-zero',sourceModified:false,alphaModified:false,visibleRgbModified:false},
    separation:{mode:sharedSplits?'shared':hasMasks?'mixed-components':'per-frame',structureAlphaThreshold:STRUCTURE_ALPHA,
      horizontalBand:sharedSplits?.horizontalBand??null,centralGap:sharedSplits?.centralGap??null},frames:[],poses:[],
    transition:{close:[0,1,2,3],open:[3,4,5,6,7,8,9,10,11]}};
  const checks={key,sheet,sourceSha256:example.sourceSha256,width,height,transparentFraction:round(transparentFraction),translucentPixels:translucent,
    separation:example.separation,registration:example.registration,displayOptimization:example.displayOptimization,frames:[],warnings:[],errors:[],layerReconstruction:true};
  if(!sharedSplits) checks.warnings.push('No common feature gap after rigid registration; per-frame transparent partitions preserve the independent layers.');
  if(hasMasks) checks.warnings.push('Some eye/mouth bounding rectangles overlap vertically; disconnected ink components are isolated without repainting. Hidden RGB at alpha zero is excluded from reconstruction comparisons.');
  const seen=new Map();
  for(let index=0;index<12;index++) {
    const id=String(index).padStart(2,'0'),file=`frames/${key}/${id}.png`, raw=raws[index];
    const splits=frameSplits[index];
    const frame={index,file,durationMs:66.666667,sourceRect:rects[index],
      sourcePadding:{right:sourceCellWidth-rects[index][2],bottom:sourceCellHeight-rects[index][3]},
      registration:{translation:registered.translations[index],measuredAnchor:registered.anchors[index]},
      transparentRgbNormalization:normalization[index].check,
      separation:splits.metadata||{method:splits.method,horizontalBand:splits.horizontalBand,centralGap:splits.centralGap},sha256:sha(frameBuffers[index]),layers:{}};
    const fullMetrics=metrics(raw,width,height);
    const check={index,file,sha256:frame.sha256,...fullMetrics,registration:frame.registration,transparentRgbNormalization:normalization[index].check,layers:{},splitCrossing:{pixels:0,maximumAlpha:0}};
    const splitY=splits.rects.mouth.top,splitX=splits.rects.rightEye.left;
    for(let y=0;y<height;y++) for(let x=0;x<width;x++) if(!splits.masks&&(y===splitY || (y<splitY&&x===splitX))) {
      const a=raw[(y*width+x)*4+3];
      if(a) {check.splitCrossing.pixels++;check.splitCrossing.maximumAlpha=Math.max(check.splitCrossing.maximumAlpha,a);}
    }
    if(fullMetrics.visiblePixels<40) checks.errors.push(`Frame ${index}: fewer than 40 visible pixels.`);
    if(fullMetrics.minimumMargin<3) checks.errors.push(`Frame ${index}: artwork is within ${fullMetrics.minimumMargin}px of a cell boundary.`);
    else if(fullMetrics.minimumMargin<8) checks.warnings.push(`Frame ${index}: cell boundary margin is only ${fullMetrics.minimumMargin}px.`);
    const rawHash=sha(raw);
    if(seen.has(rawHash)) checks.warnings.push(`Frame ${index} is pixel-identical to frame ${seen.get(rawHash)}; review the hold deliberately.`);
    else seen.set(rawHash,index);
    const reconstruction=Buffer.alloc(raw.length);
    for(const [name,rect] of Object.entries(splits.rects)) {
      const layerFile=`layers/${key}/${name}_${id}.png`;
      const layer=await (splits.masks ? sharp(splits.masks[name],{raw:{width,height,channels:4}}) : sharp(frameBuffers[index])).extract(rect).png().toBuffer();
      const layerRaw=await sharp(layer).ensureAlpha().raw().toBuffer();
      if(splits.masks) {
        for(let y=0;y<rect.height;y++)for(let x=0;x<rect.width;x++){
          const from=(y*rect.width+x)*4,to=((y+rect.top)*width+x+rect.left)*4;
          if(layerRaw[from+3]) {
            if(reconstruction[to+3])checks.errors.push(`Frame ${index}: duplicated visible pixel between component layers.`);
            layerRaw.copy(reconstruction,to,from,from+4);
          }
        }
      } else for(let y=0;y<rect.height;y++) layerRaw.copy(reconstruction,((y+rect.top)*width+rect.left)*4,y*rect.width*4,(y+1)*rect.width*4);
      frame.layers[name]={file:layerFile,x:rect.left,y:rect.top,width:rect.width,height:rect.height,sha256:sha(layer)};
      check.layers[name]=metrics(splits.masks?.[name]||raw,width,height,rect);
      save(layerFile,layer);
    }
    if(!(splits.masks?equalVisibleRgba(raw,reconstruction):raw.equals(reconstruction))) { checks.layerReconstruction=false; checks.errors.push(`Frame ${index}: separated layers do not reconstruct visible RGBA pixels exactly.`); }
    save(file,frameBuffers[index]); example.frames.push(frame); checks.frames.push(check);
  }
  example.poses=[0,7,11].map((index,i)=>({label:['Setup','Change','Settle'][i],file:example.frames[index].file,index}));
  checks.distinctFrames=seen.size;
  if(seen.size<10) checks.warnings.push(`Only ${seen.size} distinct drawings across 12 frames; review whether the hold is intentional.`);
  checks.loopSeam=imageDifference(raws[11],raws[0],width,height);
  checks.adjacentDifferences=raws.slice(1).map((raw,index)=>({from:index,to:index+1,...imageDifference(raws[index],raw,width,height)}));
  checks.blink={};
  for(const name of ['leftEye','rightEye']) {
    const open=checks.frames[0].layers[name],closed=checks.frames[3].layers[name];
    checks.blink[name]={openArea:open.alphaArea,closedArea:closed.alphaArea,closedToOpenArea:round(closed.alphaArea/Math.max(1,open.alphaArea)),
      openHeight:open.bbox?.[3]??0,closedHeight:closed.bbox?.[3]??0,
      centroidExcursion:round(Math.max(...checks.frames.map(f=>Math.hypot(f.layers[name].centroid[0]-open.centroid[0],f.layers[name].centroid[1]-open.centroid[1]))))};
    if(closed.bbox[3]>open.bbox[3]*.8 && closed.alphaArea>open.alphaArea*.8) checks.warnings.push(`${name}: frame 3 does not show a large reduction in height or visible area; visually confirm a complete blink.`);
  }
  const contactComposites=frameBuffers.map((input,index)=>({input,left:(index%4)*width,top:Math.floor(index/4)*height}));
  const contact=await sharp({create:{width:width*4,height:height*3,channels:4,background:'#101c20'}}).composite(contactComposites).png().toBuffer();
  example.contact=`contact/${key}.png`; save(example.contact,contact);
  const thumbWidth=160, thumbHeight=Math.round(height/width*thumbWidth);
  const thumbs=await Promise.all(frameBuffers.map(input=>sharp(input).resize(thumbWidth,thumbHeight).png().toBuffer()));
  const strip=await sharp({create:{width:thumbWidth*12,height:thumbHeight,channels:4,background:'#101c20'}}).composite(thumbs.map((input,index)=>({input,left:index*thumbWidth,top:0}))).png().toBuffer();
  example.filmstrip=`contact/${key}_strip.png`; save(example.filmstrip,strip);
  checks.sourceUnchanged=sha(fs.readFileSync(path.join(ROOT,sheet)))===example.sourceSha256;
  if(!checks.sourceUnchanged)checks.errors.push('Source sheet changed while compilation was running.');
  report.examples.push(checks);
  for(const error of checks.errors) report.errors.push(`${key}: ${error}`);
  for(const warning of checks.warnings) report.warnings.push(`${key}: ${warning}`);
  return example;
}

async function main() {
  const catalog=JSON.parse(fs.readFileSync(CATALOG,'utf8'));
  if(groupFilter && !catalog.groups.some(group=>group.id===groupFilter)) throw Error(`Unknown group: ${groupFilter}`);
  const manifest={version:2,fps:15,kind:'Twelve-frame generated acting studies',liveAssetsChanged:false,canvas:null,groups:[]};
  const report={version:2,passed:false,complete:false,partial,expectedExamples:18,expectedFrames:216,examples:[],missing:[],errors:[],warnings:[],
    structureAlphaThreshold:STRUCTURE_ALPHA,
    limitations:['Pixel checks establish extraction and separation, not acting quality or natural motion.','Faint alpha values below 8/255 are ignored only for feature detection. All nonzero alpha and visible RGB remain exact.','Derived display PNGs normalize RGB to zero only where alpha already equals zero. Before/after appearance and alpha hashes prove no visible change; source PNGs remain immutable.','Where feature bounds overlap, disconnected ink component masks isolate the existing drawing. Only hidden RGB at alpha zero is excluded from layer reconstruction comparisons.','Whole faces are registered with recorded integer translations; drawings are never scaled or warped.','Loop seams, blink arcs, emotion and registration need independent visual review.','Review assets are not connected to live voice in this pass.']};
  for(const originalGroup of catalog.groups) {
    if(groupFilter && originalGroup.id!==groupFilter) continue;
    const group={...originalGroup,examples:[]};
    for(const original of originalGroup.examples) {
      const sheet=`source/${group.id}/${original.id}.png`;
      if(!fs.existsSync(path.join(ROOT,sheet))) {report.missing.push(sheet);continue;}
      try { group.examples.push(await compileExample(group,original,report)); }
      catch(error) {report.errors.push(`${group.id}/${original.id}: ${error.message}`);}
    }
    if(group.examples.length) manifest.groups.push(group);
  }
  const examples=manifest.groups.flatMap(group=>group.examples);
  manifest.canvas={width:Math.max(0,...examples.map(e=>e.width)),height:Math.max(0,...examples.map(e=>e.height))};
  report.exampleCount=examples.length; report.frameCount=examples.length*12; report.layerCount=examples.length*36;
  report.complete=examples.length===18 && !report.missing.length && !groupFilter;
  report.passed=report.errors.length===0 && (partial || report.complete);
  manifest.complete=report.complete;
  // Group builds write their own manifests so they cannot overwrite a complete collection.
  const suffix=groupFilter?`.${groupFilter}`:'';
  json(`manifest${suffix}.json`,manifest);
  report.manifestSha256=sha(fs.readFileSync(path.join(ROOT,`manifest${suffix}.json`)));
  json(`asset_checks${suffix}.json`,report);
  console.log(JSON.stringify({passed:report.passed,complete:report.complete,examples:report.exampleCount,frames:report.frameCount,layers:report.layerCount,
    missing:report.missing,errors:report.errors,warnings:report.warnings},null,2));
  if(!report.passed) process.exitCode=1;
}

if(require.main===module) main().catch(error=>{console.error(error.stack);process.exitCode=1;});
module.exports={metrics,emptyRuns,splitFeatures,imageDifference,registerFrames,separateByComponents,equalVisibleRgba,normalizeTransparentRgb,appearanceHash};
