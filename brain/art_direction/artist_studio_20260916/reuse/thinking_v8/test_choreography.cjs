const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
global.window=global;global.Path2D=class{constructor(value){this.value=value;}};
require('../runtime/app_data.js');require('../runtime/face_runtime.js');require('../runtime/drawn_face_renderer.js');
const runtime=require('./runtime.js'),STEP=1000/15;
const assets={reading:'book',coding:'terminal',writing:'note',sorting:'cards',searching:'searching',pondering:'planning',connecting:'connecting',checking:'checking'};
const manifestPath=path.join(__dirname,'manifest.json'),actualManifest=fs.existsSync(manifestPath);
const manifest=actualManifest?JSON.parse(fs.readFileSync(manifestPath)):{version:8,fps:15,assets:Object.fromEntries(Object.values(assets).map(asset=>[asset,{type:'activity',frames:Array.from({length:24},(_,i)=>({file:`frames/${asset}/${String(i).padStart(2,'0')}.png`}))}])),studies:runtime.activities.map((id,i)=>({id,asset:assets[id],faceId:runtime.autoFaces[i%3]}))};
const atlas=JSON.parse(fs.readFileSync(path.join(__dirname,'../drawn/atlas.json'))),images={},thinkingImages={};
for(const [id,a]of Object.entries(atlas.assets)){images[a.file]={file:a.file};images[id]=images[a.file];for(const f of a.frames)if(f.file)images[f.file]={file:f.file};}
for(const asset of Object.values(manifest.assets))for(const frame of asset.frames)thinkingImages[frame.file]={file:frame.file};
let checks=0,time=0;const ok=(v,m)=>{checks++;assert.ok(v,m);},eq=(a,b,m)=>{checks++;assert.deepEqual(a,b,m);};
function canvas(){const calls=[],context=new Proxy({}, {get(target,key){if(!(key in target))target[key]=(...args)=>calls.push({name:key,args,alpha:target.globalAlpha});return target[key];}});return {width:1000,height:640,dataset:{},calls,getContext:()=>context};}
const opts=extra=>({data:MIST_DATA,atlas,images,manifest,thinkingImages,autoStart:false,reducedMotion:false,now:()=>time,...extra});
(async()=>{
  runtime.validateManifest(manifest);eq(runtime.activities.length,8);eq(runtime.autoFaces.length,3);eq(MIST_DATA.faces.length,40);
  const broken=structuredClone(manifest);broken.assets[broken.studies[0].asset].frames.pop();assert.throws(()=>runtime.validateManifest(broken),/Invalid thinking study/);checks++;
  let samples=0,identitySnapshots=0,renderedFrames=0;
  for(const id of runtime.activities){
    const beats=new Set(),frames=new Set(),entrance=new Set(),duration=runtime.sampleChoreography(id,600).duration;
    const beforeLoop=runtime.sampleChoreography(id,600-STEP),atLoop=runtime.sampleChoreography(id,600),beforeRepeat=runtime.sampleChoreography(id,600+duration-STEP),atRepeat=runtime.sampleChoreography(id,600+duration);
    ok(Math.hypot(atLoop.gaze.x-beforeLoop.gaze.x,atLoop.gaze.y-beforeLoop.gaze.y)<.04,'entrance gaze meets the first loop at 15 fps: '+id);
    ok(Math.abs(atLoop.lean-beforeLoop.lean)<.01,'entrance lean meets the first loop: '+id);
    ok(Math.hypot(atRepeat.gaze.x-beforeRepeat.gaze.x,atRepeat.gaze.y-beforeRepeat.gaze.y)<.04,'repeated loop gaze stays continuous: '+id);
    eq(atLoop.gaze,atRepeat.gaze,'first loop and repeated loop begin at the same gaze: '+id);
    if(['coding','writing','sorting'].includes(id))ok(duration>=2200&&duration<=2800,'quick active phrase '+id);
    let previous=-1;
    for(let tick=0;tick<Math.ceil((600+duration)/STEP);tick++){
      const age=tick*STEP,s=runtime.sampleChoreography(id,age);samples++;
      ok(Number.isInteger(s.frame)&&s.frame>=0&&s.frame<24,'valid cel '+id);ok(s.alpha>=0&&s.alpha<=1,'alpha bounded');
      ok(Math.abs(s.gaze.x)<=1&&Math.abs(s.gaze.y)<=1,'gaze bounded');eq(s.eyeSource,'original-mist');
      if(age>=600){eq(s.phase,'loop');beats.add(s.beat);frames.add(s.frame);ok(s.frame>=previous&&s.frame-previous<=1+(previous<0?24:0),'loop draws in order without skipped cels');previous=s.frame;
        if(id==='reading')eq(s.beat,['lift page','lift page','lift page','lift page','lift page','lift page','lift page','turn page','turn page','lay page','lay page','lay page','lay page','lay page','lay page','read'][s.frame-4],'reading beat follows the actual right-to-left page turn');
      }
      else entrance.add(s.frame);
      const talking=runtime.sampleChoreography(id,age,{speaking:true});eq(talking.gaze,{x:0,y:0});ok(talking.prop.alpha<=s.prop.alpha);
    }
    eq([...frames].sort((a,b)=>a-b),Array.from({length:16},(_,i)=>i+4),'every work cel actually reached at 15 fps');eq([...entrance],[0,1,2,3]);ok(beats.size>=(['searching','connecting','checking'].includes(id)?2:3));
    if(['searching','connecting','checking'].includes(id)){
      ok(duration>=2000&&duration<=2200,'continuous scan finishes in 2.0 to 2.2 seconds');
      const counts=Array(16).fill(0);for(let tick=0;tick<320;tick++){const frame=runtime.sampleChoreography(id,600+tick*STEP).frame;counts[frame-4]++;eq(frame,4+Math.floor(tick/2)%16,'two-tick cadence survives repeated floating-point phase boundaries');}
      eq(counts,Array(16).fill(20),'all continuous scan cels last exactly two display ticks for ten loops');
      const axis=id==='checking'?'y':'x',outward=Array.from({length:16},(_,tick)=>runtime.sampleChoreography(id,600+tick*STEP).gaze[axis]),back=Array.from({length:16},(_,tick)=>runtime.sampleChoreography(id,600+(16+tick)*STEP).gaze[axis]);
      ok(outward.every((v,i)=>i===0||v>outward[i-1]),'gaze follows the outward half without a hold');ok(back.every((v,i)=>i===0||v<back[i-1]),'gaze follows the return half without a hold');
    }
    const exits=new Set(),exitFrom=runtime.sampleChoreography(id,1723);
    for(let tick=0;tick<=9;tick++){const s=runtime.sampleChoreography(id,2000,{exitAge:tick*STEP,exitFrom});exits.add(s.frame);if(tick===9){eq(s.phase,'rest');eq(s.faceTransform,{x:0,y:0,scale:1});eq(s.prop.alpha,0);}}
    eq([...exits],[20,21,22,23]);eq(runtime.sampleChoreography(id,600+duration*200).phase,'loop','work never declares completion');
    for(let frame=4;frame<20;frame++){
      const captured={...exitFrom,frame};
      eq(runtime.sampleChoreography(id,2000,{exitAge:0,exitFrom:captured}).exitBlend,{frame,amount:0},'exit starts with the captured work cel');
      const midway=runtime.sampleChoreography(id,2000,{exitAge:100,exitFrom:captured});eq(midway.frame,20);eq(midway.exitBlend,{frame,amount:.5},'exit blends into the first exit cel over 200 ms');
      eq(runtime.sampleChoreography(id,2000,{exitAge:200,exitFrom:captured}).exitBlend,null);
    }
    eq(runtime.sampleChoreography(id,3200,{reducedMotion:true}).gaze,{x:0,y:0});eq(runtime.sampleChoreography(id,3200,{comparison:true}).gaze,{x:0,y:0});
    if(['reading','coding','searching'].includes(id)){const s=runtime.sampleChoreography(id,1200);ok(s.prop.y-s.prop.size/2>=37,'document begins below eye region');ok(s.faceTransform.scale===.8);}
  }
  const explicit='39_neutral_02_manual',face=runtime.create(null,opts({expression:explicit})),original=MistDrawnFaceRuntime.create(null,opts({expression:explicit}));
  eq(await face.ready,true);eq(await original.ready,true);eq(face.expressionMode,'explicit');
  function compareIdentity(){const a=face.snapshot(time),b=original.snapshot(time);identitySnapshots++;eq(a.drawnLayers,b.drawnLayers,'original eyes and resting mouth geometry');eq(a.drawnPlacements,b.drawnPlacements,'original blinks and emotion mouth placements');return a;}
  for(const expression of MIST_DATA.faces){
    face.setExpression(expression.id);original.setExpression(expression.id);face.setActivity('reading',{restart:true});
    for(let i=0;i<11;i++){time+=STEP;compareIdentity();}
    face.blink();original.blink();for(let i=0;i<8;i++){time+=STEP;compareIdentity();}
    let audioTime=1.123456;const speech={sample:()=>({active:true,viseme:'AA',amount:.8,time:audioTime,source:'audio-clock'})};
    face.startSpeech(speech);original.startSpeech(speech);eq(compareIdentity().speechTime,audioTime);
    audioTime=1.129876;eq(compareIdentity().speechTime,audioTime,'audio clock stays unquantized within the same visual frame');
    time+=300;eq(compareIdentity().thinking.gaze,{x:0,y:0});face.stopSpeech();original.stopSpeech();time+=300;compareIdentity();
  }
  const target=canvas();
  for(const id of runtime.activities){
    face.setActivity(id,{restart:true});const reached=new Set(),duration=runtime.sampleChoreography(id,600).duration;
    for(let i=0;i<Math.ceil((600+duration)/STEP)+2;i++){
      time+=STEP;face.update(time);const before=target.calls.length,s=face.renderTo(target,time);renderedFrames++;
      const props=target.calls.slice(before).filter(c=>c.name==='drawImage'&&c.args[0].file?.startsWith('frames/'));
      eq(props.length,1,'one activity image per visual frame');eq(props[0].args.length,5,'registered full cel is drawn without a crop');eq(props[0].args[0].file,s.thinking.activity.file,'painted cel matches the sampled frame');reached.add(manifest.assets[assets[id]].frames.findIndex(f=>f.file===props[0].args[0].file));
    }
    face.clearActivity();for(let i=0;i<9;i++){const before=target.calls.length,s=face.renderTo(target,time);if(s.thinking.activity.phase!=='rest'){const props=target.calls.slice(before).filter(c=>c.name==='drawImage'&&c.args[0].file?.startsWith('frames/'));ok(props.length,'exit cel is painted');for(const prop of props)reached.add(manifest.assets[assets[id]].frames.findIndex(f=>f.file===prop.args[0].file));}renderedFrames++;time+=STEP;}
    eq([...reached].sort((a,b)=>a-b),Array.from({length:24},(_,i)=>i),'all 24 drawings reach the actual renderer: '+id);
  }
  for(const id of runtime.activities)for(const workAge of [800,1500,2400]){
    face.setActivity(id,{restart:true});time+=workAge;const captured=face.snapshot(time).thinking.activity;face.clearActivity();
    const startCanvas=canvas(),atStart=face.renderTo(startCanvas,time).thinking.activity,startProps=startCanvas.calls.filter(c=>c.name==='drawImage'&&c.args[0].file?.startsWith('frames/'));
    eq(startProps.map(c=>c.args[0].file),[captured.file],'clearing at an arbitrary point first paints the captured cel');eq(startProps[0].alpha,atStart.prop.alpha);
    time+=STEP;const blendCanvas=canvas(),during=face.renderTo(blendCanvas,time).thinking.activity,blendProps=blendCanvas.calls.filter(c=>c.name==='drawImage'&&c.args[0].file?.startsWith('frames/'));
    eq(blendProps.map(c=>c.args[0].file),[captured.file,manifest.assets[assets[id]].frames[20].file]);ok(blendProps.every(c=>c.alpha>0&&c.alpha<during.prop.alpha));ok(Math.abs(blendProps.reduce((sum,c)=>sum+c.alpha,0)-during.prop.alpha)<1e-9,'crossfade weights preserve the intended prop opacity');
    time+=200;const afterCanvas=canvas(),after=face.renderTo(afterCanvas,time).thinking.activity,afterProps=afterCanvas.calls.filter(c=>c.name==='drawImage'&&c.args[0].file?.startsWith('frames/'));
    eq(after.exitBlend,null);eq(afterProps.map(c=>c.args[0].file),[after.file],'captured work cel stops painting after the blend');
  }
  const old=face.setActivity('reading',{owner:'old'}),newer=face.setActivity('coding',{owner:'new'});
  eq(face.clearActivity(old.token),false);eq(face.snapshot(time).thinking.activity.id,'coding');eq(face.setActivity('coding',{owner:'new'}).token,newer.token);
  eq(face.setActivity('invalid').accepted,false);eq(face.clearActivity(newer.token),true);time+=700;eq(face.snapshot(time).thinking.activity.phase,'rest');
  const cancelled=face.setActivity('searching',{owner:'cancelled'});eq(face.clearActivity(cancelled.token,{immediate:true}),true);eq(face.snapshot(time).thinking.activity,null);
  face.setActivity('pondering',{restart:true});time+=1000;face.inspect({layers:'eyes'});const eyeOnly=canvas();face.renderTo(eyeOnly,time);ok(!eyeOnly.calls.some(c=>c.name==='drawImage'&&c.args[0].file?.startsWith('frames/')));
  face.inspect({activityFrame:99});eq(face.snapshot(time).thinking.activity.frame,23);face.inspect({});
  const autos=Array.from({length:3},(_,variantSeed)=>runtime.create(null,opts({variantSeed})));await Promise.all(autos.map(f=>f.ready));
  for(const f of autos)f.setActivity('coding');eq(new Set(autos.map(f=>f.expression)).size,3,'three distinct initial faces');
  const auto=autos[0],initial=auto.expression,changes=[initial],start=time;
  for(let tick=0;tick<400;tick++){time=start+tick*STEP;auto.update(time);if(auto.expression!==changes.at(-1))changes.push(auto.expression);if(tick===108)ok(changes.length>=2,'visible variation within 7.2 seconds');}
  ok(changes.length>=4,'long waits keep rotating');eq(new Set(changes).size,3);for(let i=1;i<changes.length;i++)ok(changes[i]!==changes[i-1]);
  const beforeStart=auto.expression;auto.setActivity('writing');ok(auto.expression!==beforeStart,'new activity varies its face');
  auto.setExpression('10_happy_04_manual');eq(auto.expressionMode,'explicit');
  for(let tick=0;tick<250;tick++){time+=STEP;auto.update(time);}eq(auto.expression,'10_happy_04_manual','explicit choice survives long waits');
  auto.setActivity('sorting');eq(auto.expression,'10_happy_04_manual','explicit choice survives activity changes');eq(auto.setExpression('missing'),false);eq(auto.expressionMode,'explicit');
  auto.setExpression(null);eq(auto.expressionMode,'auto');for(let tick=0;tick<65;tick++){time+=STEP;auto.update(time);}ok(runtime.autoFaces.includes(auto.expression),'null restores auto');
  auto.startSpeech({sample:()=>({active:true,viseme:'OH',amount:.8,time:9.123456,source:'audio-clock'})});const speakingFace=auto.expression;
  time+=120;const quieting=auto.snapshot(time).thinking.activity.speechMix;ok(quieting>0&&quieting<1,'speech gesture settles gradually over 240 ms');
  time+=180;eq(auto.snapshot(time).thinking.activity.speechMix,1);const frozen=auto.snapshot(time).thinking.activity.frame;
  for(let tick=0;tick<150;tick++){time+=STEP;const s=auto.update(time);eq(s.expression,speakingFace,'no automatic face switch during speech');eq(s.thinking.activity.frame,frozen,'speech holds the cel');eq(s.speechTime,9.123456);}
  auto.setActivity('checking');for(let tick=0;tick<20;tick++){time+=STEP;const s=auto.update(time);eq(s.expression,speakingFace);if(s.thinking.activity.phase==='loop')eq(s.thinking.activity.frame,4,'activity switched during speech freezes its own first work cel');}
  auto.setExpression('25_neutral_2_03_manual');eq(auto.expression,speakingFace,'explicit choice queues during speech');auto.stopSpeech();time+=400;auto.update(time);eq(auto.expression,'25_neutral_2_03_manual');eq(auto.expressionMode,'explicit');
  auto.setExpression('auto');for(let tick=0;tick<70;tick++){time+=STEP;auto.update(time);}ok(runtime.autoFaces.includes(auto.expression));
  const sameA=runtime.create(null,opts({variantSeed:2})),sameB=runtime.create(null,opts({variantSeed:2}));await Promise.all([sameA.ready,sameB.ready]);sameA.setActivity('reading');sameB.setActivity('reading');
  for(let tick=0;tick<150;tick++){time+=STEP;sameA.update(time);sameB.update(time);eq(sameA.expression,sameB.expression,'same event history has deterministic variation');}
  let releaseBase,baseReady=false,drawCalls=0;
  const delayedBase={create(_container,options){let expression=options.expression;return {ready:new Promise(resolve=>{releaseBase=()=>{baseReady=true;resolve(true);};}),get loaded(){return baseReady;},get expression(){return expression;},speaking:false,setExpression(id){expression=id;return true;},setGaze(){},update(){ok(baseReady);return {expression};},snapshot(){ok(baseReady);return {expression};},renderTo(){ok(baseReady);drawCalls++;return {expression};},destroy(){},stopSpeech(){},startSpeech(){},blink(){}};}};
  const delayed=runtime.create(null,opts({drawnRuntime:delayedBase}));delayed.setActivity('reading');eq(delayed.update(time).drawnReady,false);eq(delayed.renderTo(canvas(),time).drawnReady,false);eq(drawCalls,0,'no combined drawing before dependencies load');releaseBase();eq(await delayed.ready,true);delayed.renderTo(canvas(),time);eq(drawCalls,1);
  const savedImage=global.Image,savedLocation=global.location,decodedUrls=[];
  global.Image=class{naturalWidth=256;naturalHeight=256;async decode(){decodedUrls.push(this.src);}};global.location={href:'http://localhost/'};
  const firstRevision=structuredClone(manifest),firstFrame=firstRevision.assets[firstRevision.studies[0].asset].frames[0];firstFrame.sha256='revision-one';
  const cachedA=runtime.create(null,opts({manifest:firstRevision,thinkingImages:undefined,manifestUrl:'http://localhost/thinking_v8/manifest.json'}));eq(await cachedA.ready,true);
  const revisedUrl=new URL(firstFrame.file,'http://localhost/thinking_v8/manifest.json');revisedUrl.searchParams.set('v','revision-one');ok(decodedUrls.includes(revisedUrl.href),'frame request includes its manifest hash');
  const beforeReload=decodedUrls.length,secondRevision=structuredClone(firstRevision);secondRevision.assets[secondRevision.studies[0].asset].frames[0].sha256='revision-two';
  const cachedB=runtime.create(null,opts({manifest:secondRevision,thinkingImages:undefined,manifestUrl:'http://localhost/thinking_v8/manifest.json'}));eq(await cachedB.ready,true);
  revisedUrl.searchParams.set('v','revision-two');eq(decodedUrls.slice(beforeReload),[revisedUrl.href],'changed frame hash bypasses shared cache while unchanged frames reuse it');
  cachedA.destroy();cachedB.destroy();global.Image=savedImage;global.location=savedLocation;
  for(const f of [face,original,...autos,sameA,sameB,delayed])f.destroy();eq(face.update(),null);eq(face.setActivity('reading').accepted,false);
  const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,file))).digest('hex');
  console.log(JSON.stringify({passed:true,manifestSource:actualManifest?'manifest.json':'24-frame development fixture',checks,samples,identitySnapshots,renderedFrames,runtimeSha256:hash('runtime.js'),rendererSha256:hash('../runtime/drawn_face_renderer.js'),coverage:['eight entrances, ordered 16-cel loops and exits at 15 fps','all 24 actual rendering calls per activity','2.4/2.6-second active phrases and continuous 2.13-second scans','200 ms exit crossfades from arbitrary captured cels','all 40 original eyes, blinks, resting and speech mouths','three deterministic original faces and explicit overrides','speech quieting, frozen activity switch and unquantized audio','token ownership, stale completions and cancellation','layer inspector and delayed-loader guards','manifest frame hashes invalidate browser and shared image caches'],limits:['Image handles verify render calls, not raster drawing quality.','Saved recordings need a browser playback check.']},null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});
