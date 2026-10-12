const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
global.window=global;global.Path2D=class{constructor(value){this.value=value;}};
require('../runtime/app_data.js');require('../runtime/face_runtime.js');require('../runtime/drawn_face_renderer.js');
const runtime=require('./runtime.js');
const assets={reading:'book',coding:'terminal',writing:'note',sorting:'cards',searching:'searching',pondering:'planning'};
const manifest=fs.existsSync(path.join(__dirname,'manifest.json'))?JSON.parse(fs.readFileSync(path.join(__dirname,'manifest.json'))):{version:7,fps:15,assets:{},studies:runtime.activities.map(id=>({id,asset:assets[id],faceId:'24_neutral_2_01_manual'}))};
for(const study of manifest.studies)if(!manifest.assets[study.asset])manifest.assets[study.asset]={type:'activity',frames:Array.from({length:['searching','pondering'].includes(study.id)?12:16},(_,i)=>({file:`frames/${study.asset}/${String(i).padStart(2,'0')}.png`}))};
const atlas=JSON.parse(fs.readFileSync(path.join(__dirname,'../drawn/atlas.json'))),images={},thinkingImages={};
for(const [id,a]of Object.entries(atlas.assets)){images[a.file]={file:a.file};images[id]=images[a.file];for(const f of a.frames)if(f.file)images[f.file]={file:f.file};}
for(const asset of Object.values(manifest.assets))for(const frame of asset.frames)thinkingImages[frame.file]={file:frame.file};
let checks=0,time=0;const ok=(v,m)=>{checks++;assert.ok(v,m);},eq=(a,b,m)=>{checks++;assert.deepEqual(a,b,m);};
function canvas(){const calls=[],context=new Proxy({}, {get(target,key){if(!(key in target))target[key]=(...args)=>calls.push({name:key,args});return target[key];}});return {width:1000,height:640,dataset:{},calls,getContext:()=>context};}
(async()=>{
  runtime.validateManifest(manifest);let samples=0;
  for(const id of runtime.activities){const frameCount=manifest.assets[assets[id]].frames.length,beats=new Set(),frames=new Set();
    for(let tick=0;tick<1200;tick++){
      const age=tick*1000/15,s=runtime.sampleChoreography(id,age,{frameCount});samples++;
      ok(s.frame>=0&&s.frame<frameCount&&Number.isInteger(s.frame),'valid frame '+id);ok(s.alpha>=0&&s.alpha<=1,'alpha bounded');
      ok(Math.abs(s.gaze.x)<=1&&Math.abs(s.gaze.y)<=1,'gaze bounded');eq(s.eyeSource,'original-mist');
      if(age>=600){eq(s.phase,'loop','never auto-completes');beats.add(s.beat);frames.add(s.frame);}
      const talking=runtime.sampleChoreography(id,age,{frameCount,speaking:true});eq(talking.gaze,{x:0,y:0},'speech cancels task gaze');
      ok(talking.prop.alpha<=s.prop.alpha,'speech quiets prop');
    }
    ok(beats.size>=3,'work phrases need distinct beats');eq(frames.size,frameCount-8,'every loop cel reachable');
    const start=runtime.sampleChoreography(id,0),entered=runtime.sampleChoreography(id,600);eq(start.alpha,0);eq(entered.phase,'loop');
    const exitFrom=runtime.sampleChoreography(id,1723,{frameCount});
    for(let tick=0;tick<=9;tick++){const s=runtime.sampleChoreography(id,2000,{frameCount,exitAge:tick*1000/15,exitFrom});ok(s.frame>=frameCount-4);if(tick===9){eq(s.phase,'rest');eq(s.faceTransform,{x:0,y:0,scale:1});eq(s.prop.alpha,0);}}
    const speech=runtime.sampleChoreography(id,1430,{frameCount,speechMix:1});eq(speech.beat,'speaking');
    const reduced=runtime.sampleChoreography(id,3200,{frameCount,reducedMotion:true});eq(reduced.gaze,{x:0,y:0});
    eq(runtime.sampleChoreography(id,3200,{frameCount,comparison:true}).gaze,{x:0,y:0});
  }
  const options={data:MIST_DATA,atlas,images,manifest,thinkingImages,autoStart:false,reducedMotion:false,now:()=>time,expression:'24_neutral_2_01_manual'};
  const face=runtime.create(null,options),original=MistDrawnFaceRuntime.create(null,options);eq(await face.ready,true);await original.ready;
  const target=canvas();let identitySnapshots=0,drawn=0;
  for(const expression of MIST_DATA.faces){
    face.setExpression(expression.id);original.setExpression(expression.id);face.setActivity('reading',{restart:true});
    for(let i=0;i<11;i++){time+=1000/15;const a=face.snapshot(time),b=original.snapshot(time);identitySnapshots++;eq(a.drawnLayers,b.drawnLayers,'original eye paths retained');eq(a.drawnPlacements,b.drawnPlacements,'original mouth and blink cels retained');}
    face.blink();original.blink();
    for(let i=0;i<8;i++){time+=1000/15;const a=face.snapshot(time),b=original.snapshot(time);identitySnapshots++;eq(a.drawnLayers,b.drawnLayers);eq(a.drawnPlacements,b.drawnPlacements);}
    let audioTime=1.123456;face.startSpeech({sample:()=>({active:true,viseme:'AA',amount:.8,time:audioTime,source:'audio-clock'})});
    eq(face.snapshot(time).speechTime,audioTime,'unquantized voice clock');audioTime=1.129876;eq(face.snapshot(time).speechTime,audioTime);
    time+=300;eq(face.snapshot(time).thinking.gaze,{x:0,y:0});face.stopSpeech();eq(face.snapshot(time).speaking,false);time+=300;
  }
  for(const id of runtime.activities){face.setActivity(id,{restart:true});for(let i=0;i<90;i++){time+=1000/15;face.update(time);const before=target.calls.length,s=face.renderTo(target,time);drawn++;
    eq(s.thinking.eyeSource,'original-mist');const props=target.calls.slice(before).filter(c=>c.name==='drawImage'&&c.args[0].file?.startsWith('frames/'));eq(props.length,1,'one prop, no replacement eye art');eq(props[0].args.length,5,'registered cel, no ink crop');}}
  const a=face.setActivity('reading',{owner:'old'}),b=face.setActivity('coding',{owner:'new'});eq(face.clearActivity(a.token),false);eq(face.snapshot(time).thinking.activity.id,'coding');
  eq(face.setActivity('coding',{owner:'new'}).token,b.token);eq(face.setActivity('invalid').accepted,false);
  face.clearActivity(b.token);time+=601;eq(face.snapshot(time+67).thinking.activity.phase,'rest');
  face.setActivity('pondering',{restart:true});time+=1000;face.inspect({layers:'eyes'});const eyeOnly=canvas();face.renderTo(eyeOnly,time);ok(!eyeOnly.calls.some(c=>c.name==='drawImage'&&c.args[0].file?.startsWith('frames/')),'eyes layer contains no generated props');
  face.inspect({activityFrame:15});eq(face.snapshot(time).thinking.activity.frame,11,'inspector clamps actual frame count');
  face.destroy();original.destroy();eq(face.update(),null);eq(face.setActivity('reading').accepted,false);
  const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,file))).digest('hex');
  const report={passed:true,checks,samples,identitySnapshots,renderedFrames:drawn,runtimeSha256:hash('runtime.js'),rendererSha256:hash('../runtime/drawn_face_renderer.js'),coverage:['six entrances and indefinite work phrases','all 12/16-frame loops reachable','explicit exit and stale token safety','all 40 original faces, blinks and mouth placements','speech quiets gaze and symbols','unquantized audio clock','original-eye canvas hook','single registered prop per frame','inspector layers'],limits:['Canvas image placeholders do not judge drawing quality.','Saved recordings are tested separately in browser.']};
  fs.writeFileSync(path.join(__dirname,'runtime_checks.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});
