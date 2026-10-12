// Run the real preview in a DOM stub and audit its draw transforms and timing.
'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),crypto=require('crypto'),zlib=require('zlib');
const root=__dirname,source=fs.readFileSync(path.join(root,'preview.js'),'utf8');
const geometryOnly=process.argv.includes('--geometry-only');
const assetsOnly=process.argv.includes('--assets-only');
const blinksOnly=process.argv.includes('--blinks-only');
const reportPath=path.join(root,blinksOnly?'motion_blinks_v5.json':assetsOnly?'motion_assets_v5.json':geometryOnly?'motion_geometry_v5.json':'motion_checks_v5.json');
const sharedRuntimePath=path.join(root,'../runtime/drawn_face_renderer.js'),sharedRuntime=fs.readFileSync(sharedRuntimePath,'utf8');
const atlasSource=fs.readFileSync(path.join(root,'atlas.json'),'utf8'),atlas=JSON.parse(atlasSource);
const mouthAssetIds=Object.keys(atlas.assets).filter(id=>atlas.assets[id].kind==='mouth');
const emotionAssetIds=['mouth_angry','mouth_sad','mouth_flat','mouth_worried','mouth_skeptical'];
const failures=[],warnings=[];
function check(ok,message){if(!ok)failures.push(message);}
function mul(a,b){return[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];}
function polygonClip(points,clip){
 if(!points.length||clip.length<3)return points;
 const area=clip.reduce((sum,p,index)=>{const q=clip[(index+1)%clip.length];return sum+p[0]*q[1]-q[0]*p[1];},0),sign=area<0?-1:1;
 const side=(a,b,p)=>sign*((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]));
 let output=points;
 for(let edge=0;edge<clip.length&&output.length;edge++){
  const a=clip[edge],b=clip[(edge+1)%clip.length],input=output;output=[];
  let previous=input.at(-1),before=side(a,b,previous);
  for(const point of input){const after=side(a,b,point);if((before>=-1e-8)!==(after>=-1e-8)){const ratio=before/(before-after);output.push([previous[0]+ratio*(point[0]-previous[0]),previous[1]+ratio*(point[1]-previous[1])]);}if(after>=-1e-8)output.push(point);previous=point;before=after;}
 }
 return output;
}
function insideClips(point,clips){return clips.every(clip=>polygonClip([point],clip).length>0);}
const pngCache=new Map();
function readPNG(file){
 if(pngCache.has(file))return pngCache.get(file);const bytes=fs.readFileSync(file),width=bytes.readUInt32BE(16),height=bytes.readUInt32BE(20),depth=bytes[24],type=bytes[25],channels={0:1,2:3,4:2,6:4}[type];
 if(depth!==8||bytes[28]!==0||!channels)throw Error('Unsupported test PNG encoding');const chunks=[];for(let p=8;p<bytes.length;){const n=bytes.readUInt32BE(p),tag=bytes.toString('ascii',p+4,p+8);if(tag==='IDAT')chunks.push(bytes.subarray(p+8,p+8+n));p+=n+12;}
 const raw=zlib.inflateSync(Buffer.concat(chunks)),stride=width*channels,pixels=new Uint8ClampedArray(width*height*4);let prior=new Uint8Array(stride),offset=0;
 for(let y=0;y<height;y++){const filter=raw[offset++],line=new Uint8Array(stride);for(let x=0;x<stride;x++){const a=x>=channels?line[x-channels]:0,b=prior[x],c=x>=channels?prior[x-channels]:0,p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c),prediction=filter===0?0:filter===1?a:filter===2?b:filter===3?Math.floor((a+b)/2):pa<=pb&&pa<=pc?a:pb<=pc?b:c;line[x]=(raw[offset++]+prediction)&255;}for(let x=0;x<width;x++){const i=(y*width+x)*4,j=x*channels;pixels[i]=line[j];pixels[i+1]=type===0||type===4?line[j]:line[j+1];pixels[i+2]=type===0||type===4?line[j]:line[j+2];pixels[i+3]=type===6?line[j+3]:type===4?line[j+1]:255;}prior=line;}
 const value={width,height,pixels};pngCache.set(file,value);return value;
}
class Context{
 constructor(canvas){this.canvas=canvas;this.matrix=[1,0,0,1,0,0];this.stack=[];this.draws=[];this.paths=[];this.clips=[];this.pendingPath=[];this.globalAlpha=1;this.lineWidth=1;this.lineCap='butt';this.inkCache=new Map();}
 setTransform(...m){this.matrix=m;}save(){this.stack.push({matrix:[...this.matrix],alpha:this.globalAlpha,width:this.lineWidth,cap:this.lineCap,clips:this.clips.slice()});}restore(){const s=this.stack.pop();this.matrix=s.matrix;this.globalAlpha=s.alpha;this.lineWidth=s.width;this.lineCap=s.cap;this.clips=s.clips;}
 translate(x,y){this.matrix=mul(this.matrix,[1,0,0,1,x,y]);}scale(x,y){this.matrix=mul(this.matrix,[x,0,0,y,0,0]);}rotate(a){this.matrix=mul(this.matrix,[Math.cos(a),Math.sin(a),-Math.sin(a),Math.cos(a),0,0]);}
 point(px,py){const m=this.matrix;return[(m[0]*px+m[2]*py+m[4])*100/this.canvas.width,(m[1]*px+m[3]*py+m[5])*64/this.canvas.height];}
 clearRect(){this.draws=[];this.paths=[];this.clears=(this.clears||0)+1;this.onClear?.();}fillRect(){this.fills=(this.fills||0)+1;this.onFill?.();}
 beginPath(){this.pendingPath=[];}moveTo(x,y){this.pendingPath.push(this.point(x,y));}lineTo(x,y){this.pendingPath.push(this.point(x,y));}closePath(){}
 rect(x,y,w,h){this.pendingPath.push(...[[x,y],[x+w,y],[x+w,y+h],[x,y+h]].map(point=>this.point(...point)));}
 pathPoints(p){const values=Array.from(p.d.matchAll(/-?\d+(?:\.\d+)?/g),m=>+m[0]),points=[];for(let i=0;i<values.length;i+=2)points.push(this.point(values[i],values[i+1]));return points;}
 clip(path){const points=path?this.pathPoints(path):this.pendingPath;if(points.length>=3)this.clips.push(points.slice());}
 path(p,stroke){const points=p?this.pathPoints(p):this.pendingPath.slice();this.paths.push({points,opacity:this.globalAlpha,width:stroke?this.lineWidth:0,lineCap:this.lineCap,clips:this.clips.slice()});}fill(p){this.path(p,false);}stroke(p){this.path(p,true);}
 getImageData(x,y,w,h){const data=new Uint8ClampedArray(w*h*4);if(this.pixels)for(let row=0;row<h;row++)data.set(this.pixels.subarray(((y+row)*this.canvas.width+x)*4,((y+row)*this.canvas.width+x+w)*4),row*w*4);return{data};}
 putImageData(image){this.pixels=image.data;}
 drawImage(image,...a){if(a.length===2){this.pixels=image.pixels.slice();this.sourceFile=image.path;return;}if(a.length!==8)throw Error('Unsupported canvas draw arity');const[sx,sy,sw,sh,x,y,w,h]=a;
  const pixels=image.getContext('2d'),key=[sx,sy,sw,sh].join(','),cached=pixels.inkCache.get(key);let ink=cached;
  if(!ink){const rgba=pixels.getImageData(sx,sy,sw,sh).data;ink={l:sw,t:sh,r:0,b:0};for(let iy=0;iy<sh;iy++)for(let ix=0;ix<sw;ix++)if(rgba[(iy*sw+ix)*4+3]>64){ink.l=Math.min(ink.l,ix);ink.r=Math.max(ink.r,ix+1);ink.t=Math.min(ink.t,iy);ink.b=Math.max(ink.b,iy+1);}pixels.inkCache.set(key,ink);}
  const corners=[[x,y],[x+w,y],[x+w,y+h],[x,y+h]].map(p=>this.point(...p));
  const rawInkCorners=[[ink.l,ink.t],[ink.r,ink.t],[ink.r,ink.b],[ink.l,ink.b]].map(([px,py])=>this.point(x+px/sw*w,y+py/sh*h));
  const inkCorners=this.clips.reduce((points,clip)=>polygonClip(points,clip),rawInkCorners);
  this.draws.push({sx,sy,sw,sh,corners,inkCorners,opacity:this.globalAlpha,sourceFile:pixels.sourceFile,image,clips:this.clips.slice()});
 }
}
class Element{
 constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.value='';this.checked=false;this.width=500;this.height=320;this.open=false;this.classList={toggle(){}};}
 append(...items){this.children.push(...items);}replaceChildren(...items){this.children=items;}setAttribute(){}removeAttribute(){}getContext(){return this.ctx??=new Context(this);}querySelectorAll(){return this.children;}showModal(){this.open=true;}close(){this.open=false;}
 get options(){return this.children;}
}
const elements={};function get(selector){return elements[selector]??=new Element('div');}
get('#fps').value='15';get('#speed').value='1';get('#mode').value='generated';get('#talk').checked=true;get('#eye-side').value='eye_L';
const allowedImageFiles=new Set(Object.values(atlas.assets).flatMap(a=>[a.file,...a.frames.map(f=>f.file).filter(Boolean)]));
const sandbox={console,Uint8ClampedArray,Math,Map,Set,Number,JSON,Promise,performance:{now:()=>0},Path2D:class{constructor(d){this.d=d;}},matchMedia:()=>({matches:true}),requestAnimationFrame(){},document:{hidden:false,querySelector:get,createElement:tag=>new Element(tag),addEventListener(){}},fetch:async url=>({ok:true,json:async()=>String(url).includes('samples.json')?{samples:[]}:atlas}),Image:class{set src(v){this.path=v;if(!allowedImageFiles.has(v))throw Error('Unknown test image: '+v);const png=readPNG(path.join(root,v));this.naturalWidth=png.width;this.naturalHeight=png.height;this.pixels=png.pixels;}async decode(){}}};sandbox.window=sandbox;vm.createContext(sandbox);
for(const file of ['../runtime/app_data.js','../runtime/face_runtime.js','../runtime/drawn_face_renderer.js','../audit.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),sandbox,{filename:file});
const instrumented=source.replace('window.MistDrawnPreview={','window.__checks={blinkFrame,mouthFrame,drawFace,loaded,tick,tickComparison,setPlaying,resetClock:()=>{time=0;lastWall=null;lastDraw=-Infinity;},setTime:t=>time=t,setHeld:(e,m)=>{heldEye=e;heldMouth=m;}};window.MistDrawnPreview={').replace(/await import\('\.\.\/runtime\/playback\.js(?:\?[^']*)?'\)/g,'await window.__testImport()');
check(instrumented!==source,'Preview test export hook must exist');vm.runInContext(instrumented,sandbox,{filename:'preview.js'});
async function productionChecks(data,images){
 let time=0,cue={active:false,viseme:'rest',amount:0,time:0,source:'independent-fixture'};
 const Runtime=sandbox.MistDrawnFaceRuntime,canvas=new Element('canvas');
 for(const id of mouthAssetIds)for(const pose of ['FV','LNT','TH']){
  const selected=Runtime.helpers.mouthPose(atlas.assets[id],pose,.8);
  check(atlas.assets[id].frames[selected]?.pose===pose,`${id} ${pose} cue must use its own replacement cel`);
 }
 const restReferences=new Map(sandbox.MistDrawnPreview.faces.map(item=>[item.face.id,item.staticLayers]));
 const face=Runtime.create(null,{data,atlas,images,expression:data.faces[0].id,autoStart:false,reducedMotion:false,now:()=>time});await face.ready;face.setGaze(0,0);
 const issues={ghosted:0,clipped:0,invalid:0,missingEyes:0,interruptPops:0,midpointPops:0,wrongEndIdentity:0,wrongMouthFamily:0,wrongMouthPose:0};const examples={};const measuredFits=new Set(),lidRegistrations=new Set();let samples=0,pairCount=0,speechPairs=0,maxMidpointTravel=0,interruptions=0,familySamples=0;
 function issue(kind,detail){issues[kind]++;if(!examples[kind])examples[kind]=[];if(examples[kind].length<5)examples[kind].push(detail);}
 function signature(state){return JSON.stringify({layers:state.drawnLayers.map(l=>({role:l.role,part:l.part,width:l.width,opacity:l.opacity,points:l.points})),placements:state.drawnPlacements.map(p=>({role:p.role,id:p.id,frame:p.frame,x:p.x,y:p.y,dx:p.dx,dy:p.dy,scale:p.scale,opacity:p.opacity,pose:p.pose,rigId:p.rigId}))},(key,value)=>typeof value==='number'?Math.round(value*1e8)/1e8:value);}
 function center(state,role){const parts=state.drawnVisuals.filter(p=>p.role===role),weight=parts.reduce((s,p)=>s+p.opacity,0);return weight?[parts.reduce((s,p)=>s+p.x*p.opacity,0)/weight,parts.reduce((s,p)=>s+p.y*p.opacity,0)/weight]:null;}
 function inspect(state,tag,middle=false){
  samples++;for(const role of ['eye_L','eye_R']){const weight=state.drawnVisuals.filter(p=>p.role===role).reduce((s,p)=>s+p.opacity,0);if(Math.abs(weight-1)>1e-5)issue('missingEyes',{tag,role,weight});}
  for(const p of state.drawnPlacements){if(p.kind==='eyelid')lidRegistrations.add(p.registration);else if(p.role.startsWith('eye')&&p.kind!=='eye_bridge')measuredFits.add(p.inkFit);if(!atlas.assets[p.id]?.frames[p.frame]||!Number.isFinite(p.scale)||p.scale<=0||!Number.isFinite(p.opacity))issue('invalid',{tag,role:p.role});}
  for(const draw of canvas.ctx.draws)if(draw.opacity>.001)for(const[x,y]of draw.inkCorners){if(!Number.isFinite(x)||!Number.isFinite(y))issue('invalid',{tag,x,y});else if(x<3-1e-6||x>97+1e-6||y<3-1e-6||y>61+1e-6)issue('clipped',{tag,x,y});}
  for(const l of state.drawnLayers)if(l.opacity>.001)for(const[x,y]of l.points)if(!Number.isFinite(x)||!Number.isFinite(y))issue('invalid',{tag,role:l.role});
  if(middle)for(const role of ['eye_L','eye_R','mouth']){const entries=[...state.drawnLayers,...state.drawnPlacements].filter(p=>p.role===role&&(p.opacity??1)>.08);if(entries.length>1)issue('ghosted',{tag,role,contributions:entries.map(p=>({part:p.part||p.id,opacity:p.opacity,pose:p.pose}))});}
 }
 const render=(tag,middle=false)=>{const state=face.renderTo(canvas,time);inspect(state,tag,middle);return state;};
 const fractions=[0,.12,.25,.36,.4,.45,.49999,.50001,.55,.6,.64,.82,1,1.1];
 for(const from of data.faces)for(const to of data.faces){if(from.id===to.id)continue;pairCount++;
  face.stopSpeech();face.setExpression(from.id);time+=1500;face.renderTo(canvas,time);const begin=time;face.setExpression(to.id,{durationMs:600});let beforeMid=null;
  for(const fraction of fractions){time=begin+600*fraction;const state=render(`${from.id}>${to.id}@${fraction}`,fraction>=.4&&fraction<=.6);
   if(fraction===.49999)beforeMid=state;if(fraction===.50001&&beforeMid&&beforeMid.drawnAnimation?.index===state.drawnAnimation?.index)for(const role of ['eye_L','eye_R','mouth']){const a=center(beforeMid,role),b=center(state,role);if(a&&b){const delta=Math.hypot(a[0]-b[0],a[1]-b[1]);maxMidpointTravel=Math.max(maxMidpointTravel,delta);if(delta>.05)issue('midpointPops',{from:from.id,to:to.id,role,delta});}}
   if(fraction>=1){const reference=restReferences.get(to.id);for(const role of ['eye_L','eye_R']){const l=state.drawnLayers.find(l=>l.role===role),r=reference.find(l=>l.role===role);if(!l||!r||l.part!==r.part||l.points.length!==r.points.length||l.points.some((p,i)=>Math.hypot(p[0]-r.points[i][0],p[1]-r.points[i][1])>1e-6))issue('wrongEndIdentity',{from:from.id,to:to.id,role});}}
  }
  // Keep the source family through one sound, then require the target at a cue boundary.
  for(const [firstCue,nextCue] of [['AA','EE'],['EE','LNT'],['LNT','AA']]) {
   face.stopSpeech();face.setExpression(from.id);time+=1500;face.renderTo(canvas,time);
   cue={active:true,viseme:firstCue,amount:.8,time:.3,source:'independent-fixture'};
   face.startSpeech({sample:()=>cue,events:[],duration:Infinity,clock:()=>cue.time});face.renderTo(canvas,time);
   face.setExpression(to.id,{durationMs:600});const speakingBegin=time;
   for(const fraction of fractions){
    time=speakingBegin+600*fraction;const crossedBoundary=fraction>=.45,viseme=crossedBoundary?nextCue:firstCue;
    cue={...cue,viseme};const tag=`speech:${firstCue}:${from.id}>${to.id}@${fraction}`,speaking=render(tag,fraction>=.4&&fraction<=.6);
    check(speaking.speaking&&speaking.viseme===viseme&&speaking.speechTime===.3,'Speech output clock must remain unchanged while expression time advances');
    const expectedFamily=atlas.mouthFamilies?.[crossedBoundary?to.id:from.id];
    for(const placement of speaking.drawnPlacements.filter(p=>p.role==='mouth'&&p.opacity>.001)) {
     familySamples++;if(placement.id!==expectedFamily)issue('wrongMouthFamily',{tag,expected:expectedFamily,actual:placement.id});
     const pose=atlas.assets[placement.id]?.frames[placement.frame]?.pose;
     if(pose!==viseme)issue('wrongMouthPose',{tag,expected:viseme,actual:pose});
    }
   }
   speechPairs++;face.stopSpeech();
  }
 }
 for(const speaking of [false,true])for(const[index,from]of data.faces.entries()){
  face.stopSpeech();face.setExpression(from.id);time+=1500;face.renderTo(canvas,time);
  if(speaking){cue={active:true,viseme:'AA',amount:.8,time:.3,source:'independent-fixture'};face.startSpeech({sample:()=>cue,events:[],duration:Infinity,clock:()=>cue.time});face.renderTo(canvas,time);}
  face.setExpression(data.faces[(index+13)%40].id,{durationMs:600});
  for(const interval of [40,100,50,30]){time+=interval;const before=face.renderTo(canvas,time),s=signature(before);face.setExpression(data.faces[(index+interval)%40].id,{durationMs:600});const after=face.renderTo(canvas,time);inspect(after,`interrupt:${from.id}/${interval}/speaking=${speaking}`);interruptions++;if(signature(after)!==s)issue('interruptPops',{from:from.id,interval,speaking});}
 }
 check(measuredFits.size===1&&measuredFits.has('measured-raster'),'Production fitting must measure actual keyed PNG pixels, not source contour fallback');
 check(lidRegistrations.size===1&&lidRegistrations.has('measured-raster-PCA'),'Eyelid registration must measure actual keyed PNG pixels, not fallback angles');
 for(const[kind,count]of Object.entries(issues))check(count===0,`Independent transition check ${kind}: ${count}`);
 let reducedChecks=0;const quiet=Runtime.create(null,{data,atlas,images,autoStart:false,reducedMotion:true,now:()=>time});await quiet.ready;
 for(const target of data.faces){quiet.setExpression(target.id);const state=quiet.renderTo(canvas,time);check(!state.drawnTransition.active,'Reduced motion must not animate expression transitions');check(state.drawnVisuals.filter(p=>p.role.startsWith('eye')).every(p=>p.closure===0&&p.pose==='rest'),'Reduced motion must not force a transition blink');check(state.drawnRig===target.id,'Reduced motion must select target immediately');reducedChecks++;}
 quiet.destroy();face.destroy();
 return{directedPairs:pairCount,pairSamples:samples,activeSpeechDirectedPairs:speechPairs,activeSpeechCues:['AA','EE','LNT'],mouthFamilySamples:familySamples,rapidInterruptions:interruptions,reducedMotionExpressions:reducedChecks,inkFitMethods:[...measuredFits],lidRegistrationMethods:[...lidRegistrations],maxMidpointCenterTravel:maxMidpointTravel,issues,examples};
}
async function mouthFamilyChecks(data,images){
 const Runtime=sandbox.MistDrawnFaceRuntime,canvas=new Element('canvas'),counts={};
 const customPoses=['rest','release','small_AA','AA','EH','EE','LNT','wide_close'];
 const cues=['MBP','AA','EH','EE','OH','OO','FV','LNT','S','TH','release','wide_close','round_close'];
 const mapping=atlas.mouthFamilies||{};let time=0,cue={active:false,viseme:'rest',amount:0,time:.3};
 const face=Runtime.create(null,{data,atlas,images,autoStart:false,reducedMotion:true,now:()=>time});await face.ready;
 check(atlas.version===4,'Emotion-mouth acceptance requires the version 4 atlas');
 check(Object.keys(mapping).length===data.faces.length,'Every face must have an explicit mouth-family assignment');
 check(Object.keys(mapping).every(id=>data.faces.some(face=>face.id===id)),'Mouth-family assignments must not refer to unknown faces');
 const pixelSignature=(id,frame)=>{
  const asset=atlas.assets[id],image=images[frame.file||id];
  if(!image)return null;
  const rgba=image.getContext('2d').getImageData(frame.x,frame.y,frame.w,frame.h).data;
  return `${frame.w}x${frame.h}:`+crypto.createHash('sha256').update(rgba).digest('hex');
 };
 const happySignatures=new Set(atlas.assets.mouth_smile.frames.map(frame=>pixelSignature('mouth_smile',frame)));
 const customSignatures=new Set(),artwork=[];
 for(const id of emotionAssetIds){
  const asset=atlas.assets[id];check(!!asset,`Required emotion-mouth family exists: ${id}`);if(!asset)continue;
  check(asset.inherits==='mouth_neutral',`${id} must inherit its shared articulation from neutral`);
  for(const pose of customPoses){
   const frame=asset.frames.find(frame=>frame.pose===pose);check(!!frame,`${id} supplies ${pose}`);if(!frame)continue;
   check(frame.file?.includes(id),`${id}/${pose} must select its own generated source file`);
   const signature=pixelSignature(id,frame);check(!!signature&&!happySignatures.has(signature),`${id}/${pose} must not reuse a happy-mouth cel`);
   customSignatures.add(signature);artwork.push({family:id,pose,file:frame.file,pixelSignature:signature});
  }
  const rest=asset.frames.find(frame=>frame.pose==='rest'),smile=asset.frames.find(frame=>frame.pose==='SMILE');
  check(!!rest&&!!smile&&pixelSignature(id,rest)===pixelSignature(id,smile),`${id} legacy SMILE frame must use its own resting shape`);
  const smileCue=asset.frames[Runtime.helpers.mouthPose(asset,'SMILE',.8)];
  check(smileCue?.pose!=='SMILE',`${id} SMILE speech cue must not introduce a grin`);
 }
 check(customSignatures.size===40,'The five new families must contain 40 distinct generated poses');
 let routedCues=0,restChecks=0,manualFrameChecks=0;
 for(const item of sandbox.MistDrawnPreview.faces){
  const expected=mapping[item.face.id];counts[expected]=(counts[expected]||0)+1;
  check(!!atlas.assets[expected],`Mapped mouth family exists for ${item.face.id}`);
  if(!atlas.assets[expected])continue;
  check(Runtime.helpers.mouthAssetForFace(item.face.id,atlas)===expected,`Renderer routing agrees with explicit assignment: ${item.face.id}`);
  if(/^(angry|sad|annoyed|neutral)$/.test(item.face.group))check(expected!=='mouth_smile',`Negative or neutral expression cannot select happy speech: ${item.face.id}`);
  face.stopSpeech();face.setExpression(item.face.id);time+=2000;
  const rest=face.renderTo(canvas,time),canonical=item.staticLayers.find(layer=>layer.role==='mouth'),actual=rest.drawnLayers.find(layer=>layer.role==='mouth');
  check(!rest.drawnPlacements.some(placement=>placement.role==='mouth'),`Canonical rest must not be replaced by a speaking sprite: ${item.face.id}`);
  check(!!actual===!!canonical,`Rest mouth presence is preserved: ${item.face.id}`);
  if(actual&&canonical)check(actual.part===canonical.part&&actual.points.length===canonical.points.length&&actual.points.every((point,index)=>Math.hypot(point[0]-canonical.points[index][0],point[1]-canonical.points[index][1])<1e-6),`Exact canonical rest mouth is preserved: ${item.face.id}`);
  restChecks++;
  for(const frame of atlas.assets[expected].frames){
   const state=face.renderTo(canvas,time,{mouthFrame:frame.index}),mouths=state.drawnPlacements.filter(placement=>placement.role==='mouth');
   check(mouths.length===(canonical?1:0),`Manual cel inspection preserves mouth presence: ${item.face.id}/${frame.pose}`);
   if(canonical)check(mouths[0].id===expected&&mouths[0].frame===frame.index,`Every supplied cel routes to the assigned family: ${item.face.id}/${frame.pose}`);
   manualFrameChecks++;
  }
  for(const viseme of cues){
   cue={active:true,viseme,amount:.8,time:.3};face.startSpeech({sample:()=>cue,events:[],duration:Infinity,clock:()=>cue.time});
   const state=face.renderTo(canvas,time),mouths=state.drawnPlacements.filter(placement=>placement.role==='mouth');
   check(mouths.length===(canonical?1:0),`Active cue preserves mouth presence: ${item.face.id}/${viseme}`);
   if(canonical){const mouth=mouths[0];check(mouth.id===expected,`Active cue uses assigned family: ${item.face.id}/${viseme}`);check(atlas.assets[mouth.id].frames[mouth.frame].pose===viseme,`Active cue selects its named articulation: ${item.face.id}/${viseme}`);}
   routedCues++;
  }
 }
 face.destroy();return{familyFaceCounts:counts,canonicalRestChecks:restChecks,manualFrameChecks,routedCues,customGeneratedPoses:customSignatures.size,artwork};
}
async function boundedFamilyChecks(data,images){
 const Runtime=sandbox.MistDrawnFaceRuntime,canvas=new Element('canvas'),frameMs=1000/15;
 let time=0,cue={active:true,viseme:'AA',amount:.8,time:.3},heldCases=0,quietCases=0,boundaryCases=0,maxObservedHoldMs=0;
 const face=Runtime.create(null,{data,atlas,images,autoStart:false,reducedMotion:false,now:()=>time});await face.ready;
 const family=id=>atlas.mouthFamilies[id];
 const failuresByKind={earlyHoldSwitch:0,lateHoldSwitch:0,staleCueBoundary:0,lateQuietSwitch:0,wrongPlacementFamily:0,changedOutputClock:0},examples={};
 function record(kind,detail){failuresByKind[kind]++;(examples[kind]??=[]);if(examples[kind].length<4)examples[kind].push(detail);}
 function inspect(state,expected,tag){
  if(state.speechTime!==.3)record('changedOutputClock',{tag,time:state.speechTime});
  for(const mouth of state.drawnPlacements.filter(p=>p.role==='mouth'&&p.opacity>.001)){
   if(mouth.id!==expected)record('wrongPlacementFamily',{tag,expected,actual:mouth.id});
   const asset=atlas.assets[mouth.id],frame=asset.frames[mouth.frame];
   if(!canvas.ctx.draws.some(draw=>draw.sourceFile===(frame.file||asset.file)&&draw.sx===frame.x&&draw.sy===frame.y&&draw.sw===frame.w&&draw.sh===frame.h))record('wrongPlacementFamily',{tag,expected,actual:'Canvas retained a different source crop'});
  }
 }
 function begin(from,to,viseme,amount=.8){
  face.stopSpeech();face.setExpression(from.id);time=Math.ceil((time+2000)/frameMs)*frameMs;face.renderTo(canvas,time);
  cue={active:true,viseme,amount,time:.3};face.startSpeech({sample:()=>cue,events:[],duration:Infinity,clock:()=>cue.time});face.renderTo(canvas,time);
  face.setExpression(to.id,{durationMs:600});face.renderTo(canvas,time);return time;
 }
 for(const from of data.faces)for(const to of data.faces){if(from.id===to.id)continue;
  for(const viseme of ['AA','EE','LNT']){
   const started=begin(from,to,viseme),sameFamily=family(from.id)===family(to.id);let observed=null;
   for(const elapsed of [100,300,399,400,400+frameMs]){
    time=started+elapsed;const state=face.renderTo(canvas,time),active=state.drawnMouthFamily?.active,tag=`${from.id}>${to.id}/${viseme}/${elapsed}`;
    if(!sameFamily&&elapsed<400&&active!==family(from.id))record('earlyHoldSwitch',{tag,actual:active});
    if(elapsed>=400+frameMs-1e-6&&active!==family(to.id))record('lateHoldSwitch',{tag,actual:active});
    if(!sameFamily&&active===family(to.id)&&observed===null)observed=elapsed;
    inspect(state,active,tag);
   }
   if(observed!==null)maxObservedHoldMs=Math.max(maxObservedHoldMs,observed);heldCases++;
  }
 }
 for(const from of data.faces){
  const to=data.faces.find(candidate=>candidate.slots.mouth&&family(candidate.id)!==family(from.id));
  const started=begin(from,to,'AA',.2);
  for(const elapsed of [100,150+frameMs]){
   time=started+elapsed;const state=face.renderTo(canvas,time),active=state.drawnMouthFamily?.active,tag=`quiet:${from.id}>${to.id}/${elapsed}`;
   if(elapsed>=150+frameMs-1e-6&&active!==family(to.id))record('lateQuietSwitch',{tag,actual:active});inspect(state,active,tag);
  }
  quietCases++;
  for(const viseme of ['EE','rest','MBP']){
   const started=begin(from,to,'AA');time=started+100;cue={...cue,viseme};const state=face.renderTo(canvas,time),active=state.drawnMouthFamily?.active,tag=`boundary:${from.id}>${to.id}/${viseme}`;
   if(active!==family(to.id))record('staleCueBoundary',{tag,actual:active});inspect(state,active,tag);boundaryCases++;
  }
 }
 for(const[kind,count]of Object.entries(failuresByKind))check(count===0,`Bounded mouth-family check ${kind}: ${count}`);
 face.destroy();return{heldCases,heldCues:['AA','EE','LNT'],quietCases,boundaryCases,maxObservedHoldMs,allowedHoldMs:400+frameMs,failuresByKind,examples};
}
function comparisonChecks(preview,test){
 get('#comparison-pose').value='rest';preview.openComparison();
 const comparison=preview.comparison,expected=[...new Set(Object.values(atlas.mouthFamilies))].filter(Boolean);let poseChecks=0;
 check(get('#mouth-comparison').open,'Mouth comparison opens');
 check(comparison.cards.length===expected.length&&expected.every(id=>comparison.cards.some(card=>card.id===id)),'Comparison includes all six assigned emotion-mouth families');
 for(const option of get('#comparison-pose').options){
  get('#comparison-pose').value=option.value;for(const card of comparison.cards)card.canvas.getContext('2d').draws=[];
  get('#comparison-pose').onchange();
  for(const card of comparison.cards){
   const asset=atlas.assets[card.id],frame=asset.frames.find(frame=>frame.pose===option.value),draws=card.canvas.getContext('2d').draws;
   check(!!frame,`Comparison has a drawing for ${card.id}/${option.value}`);if(!frame)continue;
   check(draws.some(draw=>draw.sourceFile===(frame.file||asset.file)&&draw.sx===frame.x&&draw.sy===frame.y),`Comparison draws the correct source crop: ${card.id}/${option.value}`);
   check(draws.every(draw=>draw.inkCorners.every(([x,y])=>x>=0&&x<=100&&y>=0&&y<=64)),`Comparison artwork remains inside its canvas: ${card.id}/${option.value}`);poseChecks++;
  }
 }
 const before=comparison.time;get('#comparison-step').onclick();check(!comparison.playing&&Math.abs(comparison.time-before-1000/15)<1e-6,'Comparison steps one 15 fps frame while paused');
 const paints=[];let wall=0;comparison.cards[0].canvas.getContext('2d').onFill=()=>paints.push(wall);get('#comparison-play').onclick();
 for(let index=0;index<=180;index++){wall=index*1000/60;test.tickComparison(wall);}
 const measured=paints.filter(time=>time>=1000&&time<3000);check(Math.abs(measured.length-30)<=1,`Comparison paints at 15 fps: ${measured.length} draws in 2 seconds`);
 get('#comparison-close').onclick();get('#mouth-comparison').onclose();const last=comparison.time;test.tickComparison(wall+100);check(!comparison.playing&&comparison.time===last,'Closing comparison stops its animation clock');
 comparison.cards[0].canvas.getContext('2d').onFill=null;return{families:comparison.cards.map(card=>card.id),poseChecks,measuredSeconds:2,paints:measured.length};
}
const rasterPointsCache=new WeakMap();
function rasterPoints(draw){
 let frames=rasterPointsCache.get(draw.image);if(!frames){frames=new Map();rasterPointsCache.set(draw.image,frames);}
 const key=[draw.sx,draw.sy,draw.sw,draw.sh].join(',');let sourcePoints=frames.get(key);
 if(!sourcePoints){
  const rgba=draw.image.getContext('2d').getImageData(draw.sx,draw.sy,draw.sw,draw.sh).data;sourcePoints=[];
  for(let y=0;y<draw.sh;y++)for(let x=0;x<draw.sw;x++)if(rgba[(y*draw.sw+x)*4+3]>64)sourcePoints.push([x+.5,y+.5]);
  frames.set(key,sourcePoints);
 }
 const a=draw.corners[0],b=draw.corners[1],d=draw.corners[3];
 return sourcePoints.map(([x,y])=>[a[0]+x/draw.sw*(b[0]-a[0])+y/draw.sh*(d[0]-a[0]),a[1]+x/draw.sw*(b[1]-a[1])+y/draw.sh*(d[1]-a[1])]).filter(point=>insideClips(point,draw.clips));
}
function lineDegrees(a,b){let angle=Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI;while(angle>90)angle-=180;while(angle<=-90)angle+=180;return angle;}
function angleDistance(a,b){return Math.abs(lineDegrees([0,0],[Math.cos((a-b)*Math.PI/180),Math.sin((a-b)*Math.PI/180)]));}
function shapeMeasure(points){
 if(!points.length)return null;
 const left=Math.min(...points.map(p=>p[0])),right=Math.max(...points.map(p=>p[0])),top=Math.min(...points.map(p=>p[1])),bottom=Math.max(...points.map(p=>p[1]));
 const average=values=>values.length?[values.reduce((sum,p)=>sum+p[0],0)/values.length,values.reduce((sum,p)=>sum+p[1],0)/values.length]:null;
 const band=(lo,hi)=>average(points.filter(point=>point[0]>=left+(right-left)*lo&&point[0]<=left+(right-left)*hi));
 const a=band(.05,.22),b=band(.78,.95),middle=band(.4,.6);
 if(!a||!b||!middle)return null;
 return{axis:lineDegrees(a,b),center:[(left+right)/2,(top+bottom)/2],width:right-left,height:bottom-top,concavity:middle[1]-(a[1]+(b[1]-a[1])*(middle[0]-a[0])/(b[0]-a[0]||1))};
}
function pointCurveDistance(point,curve){
 let nearest=Infinity;
 for(let index=1;index<curve.length;index++){
  const a=curve[index-1],b=curve[index],dx=b[0]-a[0],dy=b[1]-a[1],amount=Math.max(0,Math.min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/(dx*dx+dy*dy||1)));
  nearest=Math.min(nearest,Math.hypot(point[0]-a[0]-amount*dx,point[1]-a[1]-amount*dy));
 }
 return nearest;
}
async function blinkOrientationChecks(data,images){
 const auditFile=path.join(root,'blink_orientation_review_v5.json'),review=JSON.parse(fs.readFileSync(auditFile,'utf8'));
 const reference=new Map(review.rows.map(row=>[row.face+'/'+row.role,row])),rows=[],issues={wrongPlane:0,reversedConcavity:0,missingGeneratedLid:0,mirroredAxis:0,mirroredPosition:0,mirroredHandedness:0,earlyContourRotation:0,bottomContourClipped:0,flatStrokeCaps:0,roundEyeFragments:0,wrongBridgePlane:0,missingBridgeLid:0,ghostedBridge:0};
 const examples={};function record(kind,detail){issues[kind]++;if(!examples[kind])examples[kind]=[];if(examples[kind].length<6)examples[kind].push(detail);}
 let time=0,earlyContourChecks=0,mirrorChecks=0,bridgeChecks=0;const Runtime=sandbox.MistDrawnFaceRuntime,canvas=new Element('canvas');
 const face=Runtime.create(null,{data,atlas,images,autoStart:false,reducedMotion:false,now:()=>time});await face.ready;face.setGaze(0,0);
 function feature(state,role,targetCanvas=canvas){
  const visual=state.drawnVisuals.find(view=>view.role===role),placements=state.drawnPlacements.filter(p=>p.role===role&&p.opacity>.08),context=targetCanvas.getContext('2d');
  const matches=[];
  for(const p of placements){if(p.layer)continue;const asset=atlas.assets[p.id],frame=asset.frames[p.frame];for(const draw of context.draws)if(draw.opacity>.08&&draw.sourceFile===(frame.file||asset.file)&&draw.sx===frame.x&&draw.sy===frame.y&&draw.sw===frame.w&&draw.sh===frame.h){const points=rasterPoints(draw),measurement=shapeMeasure(points),distance=measurement?Math.hypot(measurement.center[0]-visual.x,measurement.center[1]-visual.y):Infinity;if(measurement&&distance<15)matches.push({kind:'raster',points,measurement,draw,pose:frame.pose,distance});}}
  if(!matches.length)for(const drawn of context.paths)if(drawn.opacity>.08){const points=drawn.points.filter(point=>insideClips(point,drawn.clips)),measurement=shapeMeasure(points);if(measurement)matches.push({kind:'path',points,measurement,pose:visual.pose,distance:Math.hypot(measurement.center[0]-visual.x,measurement.center[1]-visual.y)});}
  return matches.filter(item=>item.distance<15).sort((a,b)=>a.distance-b.distance)[0]||null;
 }
 function checkTrimmedContour(state,item,role,tag){
  const proposed=reference.get(item.face.id+'/'+role);if(['arc','bar'].includes(proposed.family))return;
  const visual=state.drawnVisuals.find(view=>view.role===role);if(!visual||visual.closure<=.001||visual.closure>=.65)return;
  const layer=item.staticLayers.find(layer=>layer.role===role),source=layer.points;
  // Every emitted control/end point must remain on the original, unrotated contour.
  const paths=canvas.ctx.paths.filter(path=>path.opacity>.08&&path.width>0&&path.points.length>1&&path.points.every(point=>pointCurveDistance(point,source)<.005));
  if(!paths.length)record('earlyContourRotation',{tag});earlyContourChecks++;
  if(paths.some(path=>path.lineCap!=='round'))record('flatStrokeCaps',{tag});
  if(proposed.family==='round'&&paths.length!==1)record('roundEyeFragments',{tag,count:paths.length});
  if(paths.length){
   const angle=proposed.recommendedTargetDegrees*Math.PI/180,vertical=point=>-Math.sin(angle)*point[0]+Math.cos(angle)*point[1],values=source.map(vertical),maximum=Math.max(...values),minimum=Math.min(...values),lower=source.filter(point=>vertical(point)>maximum-(maximum-minimum)*.2);
   const missing=lower.filter(point=>!paths.some(path=>pointCurveDistance(point,path.points)<.01&&insideClips(point,path.clips)));
   if(missing.length)record('bottomContourClipped',{tag,points:lower.length,missing:missing.length});
  }
 }
 for(const item of sandbox.MistDrawnPreview.faces){
  face.setExpression(item.face.id);time=Math.ceil((time+1500)/(1000/15))*(1000/15);face.renderTo(canvas,time);face.blink();const began=time;
  time=began+1000/15;const early=face.renderTo(canvas,time);for(const role of ['eye_L','eye_R'])checkTrimmedContour(early,item,role,`${item.face.id}/${role}/closing`);
  time=began+2000/15;const state=face.renderTo(canvas,time);
  for(const role of ['eye_L','eye_R']){
   const proposed=reference.get(item.face.id+'/'+role),rendered=feature(state,role),tag=item.face.id+'/'+role;
   if(!rendered){record('missingGeneratedLid',{tag});continue;}
   const measured=rendered.measurement,expected=proposed.recommendedTargetDegrees;
   if(angleDistance(measured.axis,expected)>6)record('wrongPlane',{tag,expected,actual:measured.axis});
   if(!['arc','bar'].includes(proposed.family)&&(rendered.kind!=='raster'||rendered.pose!=='closed'))record('missingGeneratedLid',{tag,actual:rendered.kind,pose:rendered.pose});
   const canonical=item.staticLayers.find(layer=>layer.role===role),sourceMeasure=shapeMeasure(canonical.points);
   if(proposed.family==='arc'&&sourceMeasure&&Math.abs(sourceMeasure.concavity)>.4&&measured.concavity*sourceMeasure.concavity<=0)record('reversedConcavity',{tag,source:sourceMeasure.concavity,actual:measured.concavity});
   const vector=rendered.draw?[rendered.draw.corners[1][0]-rendered.draw.corners[0][0],rendered.draw.corners[1][1]-rendered.draw.corners[0][1]]:null;
   const handedness=vector?Math.sign(vector[0]*Math.cos(measured.axis*Math.PI/180)+vector[1]*Math.sin(measured.axis*Math.PI/180)):null;
   rows.push({face:item.face.id,role,family:proposed.family,targetDegrees:expected,actualDegrees:measured.axis,kind:rendered.kind,pose:rendered.pose||'source-contour',center:measured.center,width:measured.width,concavity:measured.concavity,sourceConcavity:sourceMeasure?.concavity,handedness});
  }
  time=began+5000/15;const reopening=face.renderTo(canvas,time);for(const role of ['eye_L','eye_R'])checkTrimmedContour(reopening,item,role,`${item.face.id}/${role}/reopening`);
 }
 const roundTarget=sandbox.MistDrawnPreview.faces.find(item=>item.face.id==='09_happy_03_manual');
 face.setExpression('35_sad_10_manual');time=Math.ceil((time+1500)/(1000/15))*(1000/15);face.renderTo(canvas,time);face.setExpression(roundTarget.face.id,{durationMs:600});const reopeningStart=time;
 for(const fraction of [5/6,8/9]){time=reopeningStart+600*fraction;const state=face.renderTo(canvas,time);for(const role of ['eye_L','eye_R'])checkTrimmedContour(state,roundTarget,role,`35>09/${role}/${fraction}`);}
 for(const[index,from]of data.faces.entries()){
  const to=data.faces[(index+13)%data.faces.length];face.setExpression(from.id);time=Math.ceil((time+1500)/(1000/15))*(1000/15);face.renderTo(canvas,time);face.setExpression(to.id,{durationMs:600});const began=time;
  for(const fraction of [.35,.5,.64]){
   time=began+600*fraction;const state=face.renderTo(canvas,time);
   for(const role of ['eye_L','eye_R']){
    const rendered=feature(state,role),a=rows.find(row=>row.face===from.id&&row.role===role),b=rows.find(row=>row.face===to.id&&row.role===role),tag=`${from.id}>${to.id}/${role}/${fraction}`;
    const contourBridge=state.drawnPlacements.some(placement=>placement.role===role&&placement.layer);
    if(!rendered||(rendered.kind!=='raster'&&!contourBridge)||rendered.pose!=='closed')record('missingBridgeLid',{tag});
    else if(a&&b&&(rendered.measurement.axis<Math.min(a.actualDegrees,b.actualDegrees)-6||rendered.measurement.axis>Math.max(a.actualDegrees,b.actualDegrees)+6))record('wrongBridgePlane',{tag,from:a.actualDegrees,to:b.actualDegrees,actual:rendered.measurement.axis});
    const contributors=[...state.drawnPlacements,...state.drawnLayers].filter(part=>part.role===role&&(part.opacity??1)>.08);
    if(contributors.length!==1)record('ghostedBridge',{tag,count:contributors.length});bridgeChecks++;
   }
  }
 }
 const mirroredData=JSON.parse(JSON.stringify(data));
 for(const sourceFace of mirroredData.faces){
  for(const value of Object.values(sourceFace.slots))for(const slot of Array.isArray(value)?value:[value])if(slot?.part){slot.x=100-slot.x;slot.rot=-(slot.rot||0);slot.mirror=!slot.mirror;}
  [sourceFace.slots.eye_L,sourceFace.slots.eye_R]=[sourceFace.slots.eye_R,sourceFace.slots.eye_L];
 }
 const mirror=Runtime.create(null,{data:mirroredData,atlas,images,autoStart:false,reducedMotion:false,now:()=>time});await mirror.ready;mirror.setGaze(0,0);
 for(const target of mirroredData.faces){
  mirror.setExpression(target.id);time=Math.ceil((time+1500)/(1000/15))*(1000/15);mirror.renderTo(canvas,time);mirror.blink();time+=2000/15;const state=mirror.renderTo(canvas,time);
  for(const role of ['eye_L','eye_R']){
   const original=rows.find(row=>row.face===target.id&&row.role!==(role)),rendered=feature(state,role);if(!original||!rendered){record('mirroredPosition',{face:target.id,role,missing:true});continue;}
   const measured=rendered.measurement;if(angleDistance(measured.axis,-original.actualDegrees)>1)record('mirroredAxis',{face:target.id,role,expected:-original.actualDegrees,actual:measured.axis});
   if(Math.hypot(measured.center[0]-(100-original.center[0]),measured.center[1]-original.center[1])>.5||Math.abs(measured.width/original.width-1)>.05)record('mirroredPosition',{face:target.id,role,original:original.center,actual:measured.center});
   if(original.handedness!==null&&rendered.draw){const v=[rendered.draw.corners[1][0]-rendered.draw.corners[0][0],rendered.draw.corners[1][1]-rendered.draw.corners[0][1]],hand=Math.sign(v[0]*Math.cos(measured.axis*Math.PI/180)+v[1]*Math.sin(measured.axis*Math.PI/180));if(hand!==-original.handedness)record('mirroredHandedness',{face:target.id,role,expected:-original.handedness,actual:hand});}
   mirrorChecks++;
  }
 }
 face.destroy();mirror.destroy();for(const[kind,count]of Object.entries(issues))check(count===0,`Blink orientation ${kind}: ${count}`);
 return{eyes:rows.length,earlyContourChecks,mirrorChecks,bridgeChecks,reviewSha256:crypto.createHash('sha256').update(fs.readFileSync(auditFile)).digest('hex'),rows,issues,examples,limits:['Closed-lid angles are measured from displayed keyed pixels or actual source paths. Art-direction targets allow six degrees for the drawn curve.','Mirrored fixtures reflect complete face geometry and exchange eye roles; they do not edit production data.']};
}
async function voiceCancellationChecks(preview){
 const originalFetch=sandbox.fetch;let stage='',release=null,appends=0,cases=0;
 const decoded={numberOfChannels:1,length:16,sampleRate:16000,duration:.001,getChannelData:()=>new Float32Array(16)};
 const waitAt=(name,value)=>name===stage?new Promise(resolve=>{release=()=>resolve(value);}):Promise.resolve(value);
 class MockPlayback{constructor(context,adapter){this.epoch=0;this.adapter=adapter;}reset(){this.epoch++;this.adapter.stopSpeech();}append(){appends++;}}
 sandbox.__testImport=()=>waitAt('import',{Playback:MockPlayback});sandbox.btoa=value=>Buffer.from(value,'binary').toString('base64');
 sandbox.AudioContext=class{constructor(){this.currentTime=0;this.state='running';}resume(){return waitAt('resume',undefined);}suspend(){return Promise.resolve();}decodeAudioData(){return waitAt('decode',decoded);}};
 const cueData={mouth_cues:[{time:0,viseme:'AA',amount:.7}]};
 sandbox.fetch=url=>String(url).includes('cues')?waitAt('cuesFetch',{ok:true,json:()=>waitAt('cuesJson',cueData)}):waitAt('fetch',{ok:true,arrayBuffer:()=>waitAt('body',new ArrayBuffer(16))});
 for(const cancel of ['stop','selection-change'])for(const hold of ['import','resume','fetch','body','decode','cuesFetch','cuesJson']){
  preview.stopVoice();preview.voice.context=null;preview.voice.playback=null;preview.voice.samples=[{file:'fixture.wav',cues:'fixture-cues.json'}];get('#voice-sample').value='0';stage=hold;release=null;const before=appends,pending=preview.playVoice();
  for(let i=0;i<30&&!release;i++)await Promise.resolve();check(!!release,`Voice cancellation fixture reached ${hold}`);
  if(cancel==='stop')preview.stopVoice();else get('#voice-sample').onchange();if(release)release();await pending;
  check(appends===before,`${cancel} during ${hold} must prevent stale playback append`);check(!preview.voice.active&&!preview.voice.loading,`${cancel} during ${hold} must leave voice inactive`);cases++;
 }
 stage='';sandbox.fetch=originalFetch;return{cases,stages:['import','resume','fetch','body','decode','cuesFetch','cuesJson'],staleAppends:appends};
}
function previewCadenceChecks(preview,test){
 const saved=preview.faces.map(item=>item.drawn.renderTo),counts=[];let wall=0,drawTimes=[];
 for(const item of preview.faces.slice(1))item.drawn.renderTo=()=>{};
 preview.faces[0].canvas.getContext('2d').onClear=()=>drawTimes.push(wall);
 const oldContext=preview.voice.context;
 preview.voice.context={currentTime:0,resume:()=>Promise.resolve(),suspend:()=>Promise.resolve()};
 for(const voiceActive of [false,true])for(const displayHz of [60,120]){
  preview.voice.active=voiceActive;preview.voice.paused=false;preview.voice.speech={events:[],duration:Infinity,clock:()=>.3,sample:()=>({active:true,viseme:'OO',amount:.8,time:.3})};
  get('#fps').value='15';get('#speed').value='1';test.resetClock();test.setPlaying(true);drawTimes=[];
  for(let frame=0;frame<=displayHz*6;frame++){wall=frame*1000/displayHz;test.tick(wall);}
  const steady=drawTimes.filter(t=>t>=2000&&t<6000),gaps=steady.slice(1).map((t,i)=>t-steady[i]);
  const row={voiceActive,displayHz,measurementSeconds:4,draws:steady.length,actualFps:steady.length/4,minGapMs:Math.min(...gaps),maxGapMs:Math.max(...gaps)};counts.push(row);
  check(Math.abs(steady.length-60)<=1,`15 fps cadence at ${displayHz} Hz, voice=${voiceActive}: ${steady.length} draws in 4 seconds`);
  check(gaps.every(gap=>gap>=1000/15-1),`15 fps cadence must not draw faster during voice=${voiceActive}`);
 }
 preview.voice.active=false;preview.voice.paused=false;preview.voice.context=oldContext;
 preview.faces[0].canvas.getContext('2d').onClear=null;
 preview.faces.forEach((item,index)=>item.drawn.renderTo=saved[index]);test.setPlaying(false);test.resetClock();
 const html=fs.readFileSync(path.join(root,'index.html'),'utf8');check(/value=["']15["']/.test(html),'15 fps must be selectable in the real page');
 return counts;
}
function pausedMouthChecks(preview,test){
 let checks=0;get('#talk').checked=true;get('#gaze').checked=false;
 for(const scenario of ['paused','inactive-cue','stopped']){
  preview.voice.active=scenario!=='stopped';preview.voice.paused=scenario==='paused';
  preview.voice.speech={events:[],duration:Infinity,clock:()=>.3,sample:()=>({active:scenario!=='inactive-cue',viseme:'AA',amount:1,time:.3})};
  if(scenario==='stopped')get('#talk').checked=false;
  for(const item of preview.faces)for(const time of [0,1000,10000]){
   test.setTime(time);test.drawFace(item,item.canvas);const state=item.drawn.snapshot(time);
   check(!state.drawnPlacements.some(p=>p.role==='mouth'&&(p.opacity??1)>.001),`No animated mouth while ${scenario}: ${item.face.id}`);
   check(!state.speaking,`Speech is inactive while ${scenario}: ${item.face.id}`);checks++;
  }
 }
 preview.voice.active=false;preview.voice.paused=false;preview.voice.speech=null;return{faceStates:checks};
}
function outputClockChecks(){
 const file=path.join(root,'../runtime/playback.js'),source=fs.readFileSync(file,'utf8');let wall=0;
 const vmContext={console,performance:{now:()=>wall},atob:s=>Buffer.from(s,'base64').toString('binary'),setTimeout:()=>1,clearTimeout(){}};
 vm.createContext(vmContext);vm.runInContext(source.replace('export class Playback','class Playback')+'\nglobalThis.PlaybackUnderTest=Playback;',vmContext);
 const audio={currentTime:0,state:'running',destination:{},outputLatency:0,baseLatency:0,createBuffer(channels,length,rate){const data=new Float32Array(length);return{duration:length/rate,getChannelData:()=>data};},createBufferSource(){return{connect(){},disconnect(){},start(){},stop(){}};}};
 const playback=new vmContext.PlaybackUnderTest(audio,{startSpeech(){},stopSpeech(){}}),pcm=Buffer.alloc(8000);
 const cues=[{time:0,viseme:'FV',amount:.8},{time:.1,viseme:'TH',amount:.8},{time:.2,viseme:'LNT',amount:.8},{time:.3,viseme:'OO',amount:.8}];
 playback.append({epoch:1,seq:1,pcm:pcm.toString('base64'),sample_rate:8000,mouth_cues:cues,alignment_source:'qa'});
 audio.currentTime=.21;const initial=playback.sample();check(initial.viseme==='FV','FV voice cue must be retained');
 wall=100000;check(playback.sample().viseme==='FV','Wall time alone must not advance the voice cue');
 audio.currentTime=.31;check(playback.sample().viseme==='TH','TH voice cue must be retained rather than discarded');
 audio.currentTime=.41;check(playback.sample().viseme==='LNT','LNT voice cue must be retained');
 for(const state of ['suspended','interrupted']){audio.state=state;const sample=playback.sample();check(sample.active===false&&sample.viseme==='rest'&&sample.amount===0,`${state} output must return silence`);}
 audio.state='running';audio.currentTime=5;audio.outputLatency=.08;audio.baseLatency=.02;check(Math.abs(playback.outputTime()-4.9)<1e-9,'Fallback output clock must subtract device latency');
 wall=200010;audio.getOutputTimestamp=()=>({contextTime:4.75,performanceTime:200000});check(Math.abs(playback.outputTime()-4.76)<1e-9,'Output timestamp clock must follow the audible output estimate');
 playback.reset();check(!playback.sample().active,'Reset must clear output-clock speech');
 return{playbackSha256:crypto.createHash('sha256').update(source).digest('hex'),tested:['FV, TH, LNT routing','Frozen audio clock with advancing wall time','Suspended and interrupted silence','Latency fallback','Output timestamp','Reset']};
}
async function run(){
 for(let i=0;i<10&&!sandbox.MistDrawnPreview.ready;i++)await new Promise(r=>setImmediate(r));
 const preview=sandbox.MistDrawnPreview,test=sandbox.__checks,data=sandbox.MIST_DATA;
 check(preview.ready,'Preview initialization must complete');check(preview.faces.length===40,'All 40 faces must exist');
 if(blinksOnly){
  const blinkOrientation=await blinkOrientationChecks(data,test.loaded);
  check(fs.readFileSync(sharedRuntimePath,'utf8')===sharedRuntime,'Renderer changed during the blink check');
  const report={passed:!failures.length,scope:'blinks-only',checkedAt:new Date().toISOString(),sharedRuntimeSha256:crypto.createHash('sha256').update(sharedRuntime).digest('hex'),atlasSha256:crypto.createHash('sha256').update(atlasSource).digest('hex'),blinkOrientation,failures,warnings};
  fs.writeFileSync(report.passed?reportPath:reportPath.replace(/\.json$/,'_failed.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(failures.length)process.exitCode=1;return;
 }
 const parts=new Set(),uses={},missing=[];
 for(const item of preview.faces)for(const role of ['eye_L','eye_R']){const slot=item.slots[role],family=preview.partFamily[slot?.part];if(!family)missing.push(`${item.face.id}/${role}`);else{parts.add(slot.part);uses[family]=(uses[family]||0)+1;}}
 check(parts.size===30,'All 30 source eye parts must be mapped');check(!missing.length,`Unmapped eye placements: ${missing.join(', ')}`);check(Object.values(uses).reduce((a,b)=>a+b,0)===80,'All 80 eye placements must be covered');
 const assetChecks={};let celCount=0;
 for(const[id,a]of Object.entries(atlas.assets)){
  const bytes=fs.readFileSync(path.join(root,a.file));check(crypto.createHash('sha256').update(bytes).digest('hex')===a.sha256,`Sheet hash mismatch: ${id}`);
  check(bytes.readUInt32BE(16)===a.imageWidth&&bytes.readUInt32BE(20)===a.imageHeight,`PNG dimensions mismatch: ${id}`);
  for(const f of a.frames){const png=readPNG(path.join(root,f.file||a.file));celCount++;check(f.x>=0&&f.y>=0&&f.x+f.w<=png.width&&f.y+f.h<=png.height,`Crop outside its actual sheet: ${id}/${f.index}`);check(f.inkPixels>0,`Blank cel: ${id}/${f.index}`);check(f.x>=f.cell.x&&f.y>=f.cell.y&&f.x+f.w<=f.cell.x+f.cell.w&&f.y+f.h<=f.cell.y+f.cell.h,`Crop enters another cel: ${id}/${f.index}`);check(Number.isFinite(f.sourceScale??1)&&(f.sourceScale??1)>0,`Valid source scale: ${id}/${f.index}`);if(f.file&&f.sha256)check(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,f.file))).digest('hex')===f.sha256,`Frame source hash mismatch: ${id}/${f.pose}`);}
  const closedIndex=a.frames.findIndex(f=>f.pose==='closed');
  check((a.kind==='eye'?[6,8]:[12,16]).includes(a.frames.length),`Unsupported cel count: ${id}/${a.frames.length}`);
  check(a.kind!=='eye'||closedIndex>=0,`Closed pose missing: ${id}`);
  const actualInkPixels=a.frames.map(f=>{const key=f.file||id,image=test.loaded[key];check(!!image,`Actual frame-specific sheet is loaded: ${id}/${f.index}/${key}`);if(!image)return 0;const rgba=image.getContext('2d').getImageData(f.x,f.y,f.w,f.h).data;let count=0;for(let n=3;n<rgba.length;n+=4)if(rgba[n]>64)count++;check(count>0,`Actual keyed PNG cel must contain ink: ${id}/${f.index}`);return count;});
  assetChecks[id]={frames:a.frames.length,actualInkPixels,frameFiles:a.frames.map(f=>f.file||a.file),restHeight:a.frames[0].inkBounds.h,closedIndex,closedHeight:a.kind==='eye'?a.frames[closedIndex].inkBounds.h:null};
 }
 check(Array.isArray(atlas.expectedAssets)&&atlas.expectedAssets.length===14&&atlas.expectedAssets.every(id=>assetChecks[id]),'Expected seven eye families and seven mouth sets');
 check(celCount===164,'Expected 164 indexed cels, including the inherited articulation poses');
 const bounds={left:Infinity,top:Infinity,right:-Infinity,bottom:-Infinity};let drawCount=0,replacementDrawChecks=0;const clipped=[];
 for(const item of preview.faces){
  const eyeCount=Math.max(...['eye_L','eye_R'].map(role=>atlas.assets[preview.partFamily[item.slots[role].part]].frames.length));
  const mouthCount=atlas.assets[atlas.mouthFamilies?.[item.face.id]]?.frames.length||Math.max(...mouthAssetIds.map(id=>atlas.assets[id].frames.length));
  const configurations=[...Array.from({length:eyeCount},(_,eye)=>[eye,0]),...Array.from({length:mouthCount},(_,mouth)=>[0,mouth])];
  for(const[eye,mouth]of configurations){
   test.setHeld(eye,mouth);for(const t of [0,2000]){get('#gaze').checked=true;test.setTime(t);test.drawFace(item,item.canvas,true);const draws=item.canvas.ctx.draws;check(draws.length+item.canvas.ctx.paths.length>=2,`Face must render visible components: ${item.face.id}/${eye}/${mouth}`);for(const d of draws){drawCount++;for(const[x,y]of d.inkCorners){check(Number.isFinite(x)&&Number.isFinite(y),'Draw transform must be finite');bounds.left=Math.min(bounds.left,x);bounds.top=Math.min(bounds.top,y);bounds.right=Math.max(bounds.right,x);bounds.bottom=Math.max(bounds.bottom,y);if(x<0||x>100||y<0||y>64)clipped.push({face:item.face.id,eye,mouth,x,y});}}
    const mouthPlacement=item.drawn.snapshot(t,{mouthFrame:mouth}).drawnPlacements.find(p=>p.role==='mouth');
    if(mouthPlacement){const frame=atlas.assets[mouthPlacement.id].frames[mouthPlacement.frame];if(frame.file){const draw=draws.find(d=>d.sourceFile===frame.file&&d.sx===frame.x&&d.sy===frame.y);check(!!draw,`Replacement PNG actually drawn: ${item.face.id}/${frame.pose}`);if(draw){const width=Math.hypot(draw.corners[1][0]-draw.corners[0][0],draw.corners[1][1]-draw.corners[0][1]);check(Math.abs(width-frame.w*mouthPlacement.scale*(frame.sourceScale??1))<1e-6,`Replacement sourceScale applied once: ${item.face.id}/${frame.pose}`);replacementDrawChecks++;}}}
   }
  }
 }
 check(!clipped.length,`${clipped.length} sprite crop corners fall outside the face canvas`);
 test.setHeld(null,null);get('#gaze').checked=false;
 const timing=[],frameInterval=1000/15;check(atlas.fps===15,'The final atlas cadence must be 15 fps');
 for(const sync of [false,true]){get('#sync').checked=sync;for(const item of preview.faces)for(const role of ['eye_L','eye_R']){const family=preview.partFamily[item.slots[role].part],poses=new Set();for(let t=0;t<10800;t+=frameInterval){test.setTime(t);poses.add(test.blinkFrame(item,family));}const expected=assetChecks[family].closedIndex;check(poses.has(expected),`Closed blink never sampled at 15 fps: ${item.face.id}/${role}/sync=${sync}`);timing.push({face:item.face.id,role,family,sync,poses:[...poses].sort()});}}
 const phaseClosedMisses=[];
 // Arbitrary sampling phase, one millisecond resolution, avoids lucky frame alignment.
 let phaseChecks=0;
 for(const[family,a]of Object.entries(assetChecks).filter(([id])=>!id.startsWith('mouth')))for(let phase=0;phase<frameInterval;phase++){phaseChecks++;let hit=false;for(let t=phase;t<5400+phase;t+=frameInterval){test.setTime(t);if(test.blinkFrame(preview.faces[0],family)===a.closedIndex)hit=true;}if(!hit)phaseClosedMisses.push({family,phase});}
 check(!phaseClosedMisses.length,`15 fps sampling skips closure for phases: ${JSON.stringify(phaseClosedMisses)}`);
 const skippedPoses=Object.fromEntries(Object.entries(assetChecks).filter(([id])=>!id.startsWith('mouth')).map(([family,a])=>[family,Array.from({length:a.frames},(_,i)=>i).filter(p=>!timing.filter(t=>t.family===family).some(t=>t.poses.includes(p)))]));if(Object.values(skippedPoses).some(p=>p.length))warnings.push('Not every available breakdown appears in the selected blink timing. The report lists unused poses.');
 const closedFamilies=Object.fromEntries(Object.entries(assetChecks).filter(([id])=>!id.startsWith('mouth')).map(([id,a])=>[id,{restHeight:a.restHeight,closedHeight:a.closedHeight,ratio:+(a.closedHeight/a.restHeight).toFixed(3)}]));
 const blinkOrientation=await blinkOrientationChecks(data,test.loaded),mouthFamilies=await mouthFamilyChecks(data,test.loaded),transitions=assetsOnly?null:await productionChecks(data,test.loaded),boundedFamilies=assetsOnly?null:await boundedFamilyChecks(data,test.loaded),comparison=comparisonChecks(preview,test),cadence=geometryOnly||assetsOnly?null:previewCadenceChecks(preview,test),pausedMouth=geometryOnly||assetsOnly?null:pausedMouthChecks(preview,test),outputClock=geometryOnly||assetsOnly?null:outputClockChecks(),voiceCancellation=geometryOnly||assetsOnly?null:await voiceCancellationChecks(preview);
 const productionPath=path.join(root,'../../../../ui/static/drawn_face_renderer.js');
 if(fs.existsSync(productionPath))check(fs.readFileSync(productionPath,'utf8')===sharedRuntime,'Preview shared renderer must equal production renderer bytes');
 else warnings.push('Standalone pack: checked the bundled renderer. No separate production file is available for byte comparison.');
 check(fs.readFileSync(sharedRuntimePath,'utf8')===sharedRuntime,'Renderer changed during the test run; rerun against the new version');
 check(fs.readFileSync(path.join(root,'atlas.json'),'utf8')===atlasSource,'Atlas changed during the test run; rerun against the new version');
 if(!geometryOnly)check(fs.readFileSync(path.join(root,'preview.js'),'utf8')===source,'Preview changed during the test run; rerun against the new version');
 const report={passed:!failures.length,scope:assetsOnly?'assets-only':geometryOnly?'geometry-only':'full',checkedAt:new Date().toISOString(),sourceSha256:crypto.createHash('sha256').update(source).digest('hex'),sharedRuntimeSha256:crypto.createHash('sha256').update(sharedRuntime).digest('hex'),atlasSha256:crypto.createHash('sha256').update(atlasSource).digest('hex'),actualPngPixelsDecoded:true,faces:preview.faces.length,uniqueEyeParts:parts.size,eyePlacements:80,familyPlacements:uses,celCount,assetChecks,poseDrawChecks:drawCount,replacementDrawChecks,canvasBounds:bounds,clippedCornerCount:clipped.length,closedFamilies,blinkTiming:{fps:15,faceRoleAndSyncConfigurations:timing.length,arbitraryPhaseChecks:phaseChecks,closedPhaseMisses:phaseClosedMisses,unusedBreakdowns:skippedPoses,poseCoverage:timing},blinkOrientation,mouthFamilies,transitions,boundedFamilies,comparison,cadence,pausedMouth,outputClock,voiceCancellation,failures,warnings,limits:['DOM and canvas stubs execute the actual preview and production affine draw transforms. They do not judge perceived motion quality or GPU antialiasing.','PNG pixels are decoded from source bytes and keyed by the real preview. Raster ink support and alpha bounds are measured independently of atlas inkBounds.','Clock fixtures verify scheduling behavior; they do not measure device audio latency.']};
 const reportText=JSON.stringify(report,null,2)+'\n';fs.writeFileSync(report.passed?reportPath:reportPath.replace(/\.json$/,'_failed.json'),reportText);
 if(!geometryOnly&&!assetsOnly&&report.passed)fs.writeFileSync(path.join(root,'motion_checks.json'),reportText);
 console.log(JSON.stringify({...report,blinkTiming:{...report.blinkTiming,poseCoverage:undefined}},null,2));if(failures.length)process.exitCode=1;
}
run().catch(e=>{console.error(e);process.exitCode=1;});
