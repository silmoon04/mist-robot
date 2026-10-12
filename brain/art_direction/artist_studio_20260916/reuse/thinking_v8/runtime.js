/* Activity drawings around the original MIST eyes and speech mouths. */
(function(root){
  'use strict';
  const FPS=15,TICK=1000/FPS,ENTER=600,EXIT=600,EXIT_BLEND=200,SCAN_HALF=16*TICK,FRAME_COUNT=24;
  const IDS=['reading','coding','writing','sorting','searching','pondering','connecting','checking'];
  const AUTO_FACES=['39_neutral_02_manual','40_neutral_03_manual','36_misc_03_manual'];
  const CONTINUOUS=['searching','connecting','checking'];
  const clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n));
  const ease=n=>{n=clamp(n);return n*n*(3-2*n);};
  const mix=(a,b,t)=>a+(b-a)*t;
  // Duration, beat, gaze x/y, first/last loop cel, whole-face lean.
  const PHRASES={
    reading:[[1050,'lift page',.35,.6,0,6,.08],[400,'turn page',0,.55,7,8,0],[1000,'lay page',-.35,.65,9,14,-.08],[550,'read',-.25,.65,15,15,-.04]],
    coding:[[500,'type',.25,.65,0,3,.2],[200,'check',.2,.45,3,3,.08],[500,'type',.3,.65,4,7,.2],[150,'consider',-.15,.15,7,7,-.08],[650,'continue',.25,.65,8,12,.18],[400,'inspect',.2,.45,13,15,.08]],
    writing:[[650,'write',.85,.4,0,4,.18],[180,'read back',.7,.2,4,4,.08],[650,'continue',.85,.45,5,9,.18],[170,'consider',.25,-.12,9,9,-.05],[750,'write',.8,.4,10,15,.15]],
    sorting:[[600,'compare',.85,.05,0,3,.1],[200,'weigh up',.6,.15,3,3,0],[600,'arrange',.8,.4,4,7,.13],[200,'check order',.55,.25,7,7,0],[650,'compare',.9,.1,8,12,.1],[350,'settle',.7,.2,13,15,.04]],
    searching:[[SCAN_HALF,'scan across',.4,.65,0,7,.1],[SCAN_HALF,'scan back',-.35,.65,8,15,-.1]],
    pondering:[[720,'wonder',-.2,-.42,0,3,-.09],[180,'hold',-.2,-.42,3,3,-.09],[850,'consider',.2,-.25,4,8,.09],[150,'hold',.2,-.25,8,8,.09],[1000,'return',-.2,-.42,9,15,-.09]],
    connecting:[[SCAN_HALF,'trace outward',.9,.1,0,7,.08],[SCAN_HALF,'trace back',.55,.1,8,15,-.04]],
    checking:[[SCAN_HALF,'scan down',.8,.45,0,7,.08],[SCAN_HALF,'scan up',.8,-.1,8,15,-.04]]
  };
  const DURATIONS=Object.fromEntries(IDS.map(id=>[id,PHRASES[id].reduce((sum,b)=>sum+b[0],0)]));
  function sampleChoreography(id,elapsed,options={}){
    if(!IDS.includes(id))throw new Error('Unknown thinking study: '+id);
    if((options.frameCount??FRAME_COUNT)!==FRAME_COUNT)throw new Error('Thinking v8 assets need 24 frames');
    const age=Math.max(0,Number(elapsed)||0),phrase=PHRASES[id],duration=DURATIONS[id],exitAge=options.exitAge;
    const loopAge=Math.max(0,age-ENTER),loop=Math.floor(loopAge/duration+1e-8),loopTime=Math.max(0,loopAge-loop*duration);
    let phase='loop',beat='settle',frame=4,alpha=1,gx=0,gy=0,lean=0,progress=0,exitBlend=null;
    const first=phrase[0],loopStart=phrase[phrase.length-1];
    if(exitAge!==undefined&&exitAge!==null){
      const p=clamp(exitAge/EXIT);phase=p>=1?'rest':'exit';beat=p>=1?'rest':'put away';progress=p;
      frame=20+Math.min(3,Math.floor(Math.max(0,exitAge-EXIT_BLEND)/((EXIT-EXIT_BLEND)/4)+1e-7));alpha=1-ease(p);
      if(exitAge<EXIT_BLEND)exitBlend={frame:clamp(options.exitFrom?.frame??19,0,23),amount:ease(exitAge/EXIT_BLEND)};
      gx=(options.exitFrom?.gaze.x??first[2])*alpha;gy=(options.exitFrom?.gaze.y??first[3])*alpha;lean=(options.exitFrom?.lean??0)*alpha;
    }else if(age<ENTER){
      const p=age/ENTER;phase='entrance';beat=p<.35?'notice':'begin';progress=p;
      frame=Math.min(3,Math.floor(p*4));alpha=ease(p);gx=loopStart[2]*alpha;gy=loopStart[3]*alpha;lean=loopStart[6]*alpha;
    }else{
      let cursor=loopTime,index=0;
      while(index<phrase.length-1&&cursor>=phrase[index][0]-1e-7)cursor-=phrase[index++][0];
      const b=phrase[index],previous=phrase[(index+phrase.length-1)%phrase.length],f=clamp(cursor/b[0]);
      const s=CONTINUOUS.includes(id)?ease(f):ease(cursor/Math.min(id==='pondering'?650:260,b[0]*.8));
      beat=b[1];progress=loopTime/duration;
      gx=mix(previous[2],b[2],s);gy=mix(previous[3],b[3],s);lean=mix(previous[6],b[6],s);
      frame=4+b[4]+Math.min(b[5]-b[4],Math.floor(f*(b[5]-b[4]+1)+1e-7));
    }
    const quiet=clamp(options.speechMix??(options.speaking?1:0));
    if(options.comparison){gx=0;gy=0;lean=0;if(phase==='loop')frame=4+Math.floor(loopTime/(duration/16)+1e-7)%16;beat=phase==='loop'?'drawing loop':beat;}
    if(options.reducedMotion){gx=0;gy=0;lean=0;frame=phase==='rest'?23:4;exitBlend=null;}
    const layout=phase==='entrance'?ease(age/ENTER):phase==='exit'||phase==='rest'?alpha:1,quietFace=1-quiet;
    const below=['reading','coding','searching'].includes(id),thought=id==='pondering';
    const target=below?{x:10,y:-3,scale:.8}:thought?{x:6,y:7,scale:.81}:{x:2,y:7,scale:.72};
    const faceTransform={x:target.x*layout+lean*.9*quietFace,y:target.y*layout+Math.abs(lean)*.25*quietFace,scale:mix(1,target.scale,layout)};
    const prop={x:below?50:thought?79:82,y:below?51:thought?16:37,size:below?27:thought?27:31,alpha:alpha*(1-quiet*.45),dy:phase==='entrance'?(1-ease(age/ENTER))*4:phase==='exit'?ease(exitAge/EXIT)*3:0};
    return {id,phase,beat:quiet>.5&&phase!=='rest'?'speaking':beat,frame,alpha,progress,duration,loop,gaze:{x:gx*quietFace||0,y:gy*quietFace||0},lean,faceTransform,prop,exitBlend,speechMix:quiet,eyeSource:'original-mist',fps:FPS};
  }
  function validateManifest(manifest){
    if(manifest?.version!==8||manifest.fps!==FPS)throw new Error('Expected thinking manifest v8 at 15 fps');
    if(manifest.studies?.length!==IDS.length||new Set(manifest.studies.map(s=>s.id)).size!==IDS.length)throw new Error('Expected eight distinct thinking studies');
    for(const id of IDS){
      const config=manifest.studies.find(x=>x.id===id),asset=manifest.assets?.[config?.asset];
      if(!config||!asset||asset.frames?.length!==FRAME_COUNT||asset.frames.some(f=>typeof f.file!=='string'||!f.file.startsWith('frames/')))throw new Error('Invalid thinking study: '+id);
    }
    return manifest;
  }
  const sharedLoads=new Map();
  function create(container,options={}){
    const now=options.now||(()=>root.performance.now()),data=options.data||root.MIST_DATA,drawn=options.drawnRuntime||root.MistDrawnFaceRuntime;
    if(!drawn)throw new Error('Load the original MIST renderer first');
    if(AUTO_FACES.some(id=>!data?.faces.some(f=>f.id===id)))throw new Error('Original MIST thinking faces are missing');
    const origin=now(),visualTime=time=>origin+Math.floor((time-origin)/TICK+1e-7)*TICK;
    let manifest=options.manifest||null,images=options.thinkingImages||{},loaded=false,error=null,dead=false,raf=null;
    let current=null,serial=0,revision=0,held={},comparison=false,speechAt=now(),speechFrom=0,speechTarget=0,frozenCel=null;
    let automatic=options.expression==null||options.expression==='auto',variantCursor=((Math.trunc(Number(options.variantSeed??options.seed)||0)%3)+3)%3;
    let startedActivity=false,pendingExpression=null,variantChanges=0;
    const reduced=options.reducedMotion??!!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    function mixSpeech(time){return mix(speechFrom,speechTarget,ease((time-speechAt)/240));}
    function shot(time=now()){
      const at=visualTime(time),config=current&&manifest?.studies.find(s=>s.id===current.id);
      const common={ready:loaded,fps:FPS,time:at,eyeSource:'original-mist',layers:held.layers||'all',comparison,expressionMode:automatic?'auto':'explicit',variantChanges};
      if(!current)return {...common,activity:null,faceTransform:{x:0,y:0,scale:1},gaze:{x:0,y:0}};
      const activity=sampleChoreography(current.id,at-current.at,{frameCount:manifest?.assets[config?.asset]?.frames.length,exitAge:current.exitAt===null?null:Math.max(0,at-current.exitAt),exitFrom:current.exitFrom,speechMix:mixSpeech(at),comparison,reducedMotion:reduced});
      if(Number.isInteger(held.activityFrame)){activity.frame=clamp(held.activityFrame,0,23);activity.exitBlend=null;}
      else if(frozenCel!==null&&activity.phase==='loop'&&activity.speechMix>.05)activity.frame=frozenCel;
      activity.asset=config?.asset;activity.file=manifest?.assets[config?.asset]?.frames[activity.frame]?.file||null;
      if(activity.exitBlend)activity.exitBlend.file=manifest?.assets[config?.asset]?.frames[activity.exitBlend.frame]?.file||null;
      return {...common,activity,faceTransform:activity.faceTransform,gaze:activity.gaze};
    }
    const layer={get ready(){return loaded;},get revision(){return revision;},replaceEyes:false,
      get showEyes(){return !held.layers||held.layers==='all'||held.layers==='eyes';},
      get showMouth(){return !held.layers||held.layers==='all'||held.layers==='mouth';},
      get showDecorations(){return !held.layers||held.layers==='all';},
      faceTransform(state){return shot(state.drawnAnimation.time).faceTransform;},
      paint(context,state){const s=shot(state.drawnAnimation.time),a=s.activity;if(!a||a.phase==='rest'||(s.layers!=='all'&&s.layers!=='activity'))return;
        const image=images[a.file];if(!image)return;const p=a.prop;
        const blend=a.exitBlend,previous=blend&&images[blend.file],amount=previous?blend.amount:1;
        context.save();
        if(previous&&amount<1){context.globalAlpha=p.alpha*(1-amount);context.drawImage(previous,p.x-p.size/2,p.y+p.dy-p.size/2,p.size,p.size);}
        if(amount>0){context.globalAlpha=p.alpha*amount;context.drawImage(image,p.x-p.size/2,p.y+p.dy-p.size/2,p.size,p.size);}
        context.restore();}
    };
    const base=drawn.create(container,{...options,expression:automatic?AUTO_FACES[variantCursor]:options.expression,fps:FPS,eyeLayer:layer,autoStart:false});
    function blockedFace(time){return speechTarget===1||mixSpeech(time)>.05||base.speaking;}
    function chooseNext(){
      variantCursor=(variantCursor+1)%AUTO_FACES.length;
      if(AUTO_FACES[variantCursor]===base.expression)variantCursor=(variantCursor+1)%AUTO_FACES.length;
      variantChanges++;revision++;base.setExpression(AUTO_FACES[variantCursor]);
    }
    function prepare(time){
      if(!loaded||!base.loaded||dead)return;
      if(pendingExpression&&!blockedFace(time)){base.setExpression(pendingExpression.id,pendingExpression.settings);pendingExpression=null;revision++;}
      if(!current||current.exitAt!==null||!automatic)return;
      const age=visualTime(time)-current.at;
      if(age<ENTER)return;
      const loop=Math.floor((age-ENTER)/DURATIONS[current.id]+1e-8);
      if(loop===current.lastLoop)return;
      current.lastLoop=loop;
      if(loop>=current.nextVariantLoop&&!blockedFace(time)){
        chooseNext();current.nextVariantLoop=loop+2+(current.rotations++%2);
      }
    }
    function loadingState(time){return {expression:base.expression,speaking:false,drawnReady:false,thinking:shot(time)};}
    const api={
      setActivity(id,settings={}){
        if(dead||!IDS.includes(id))return {accepted:false,reason:dead?'destroyed':'unknown_activity'};
        if(current?.id===id&&current.owner===(settings.owner??null)&&current.exitAt===null&&!settings.restart)return {accepted:true,token:current.token};
        current={id,owner:settings.owner??null,token:++serial,at:visualTime(now()),exitAt:null,lastLoop:-1,nextVariantLoop:2,rotations:1};
        if(automatic&&startedActivity){if(!blockedFace(now())&&base.loaded)chooseNext();else current.nextVariantLoop=0;}
        startedActivity=true;
        frozenCel=speechTarget===1||mixSpeech(now())>.05?4:null;
        revision++;return {accepted:true,token:current.token};
      },
      clearActivity(token,settings={}){
        if(!current||(token!=null&&token!==current.token))return false;
        if(settings.immediate)current=null;else if(current.exitAt===null){current.exitFrom=shot().activity;current.exitAt=visualTime(now());}
        revision++;return true;
      },
      setExpression(id,settings={}){
        if(dead)return false;
        if(id==null||id==='auto'){
          automatic=true;pendingExpression=null;
          const index=AUTO_FACES.indexOf(base.expression);if(index>=0)variantCursor=index;
          if(current){const loop=Math.max(0,Math.floor((visualTime(now())-current.at-ENTER)/DURATIONS[current.id]));current.nextVariantLoop=loop+1;}
          revision++;return true;
        }
        if(!data.faces.some(f=>f.id===id))return false;
        automatic=false;revision++;
        if(!base.loaded||blockedFace(now())){pendingExpression={id,settings};return true;}
        pendingExpression=null;return base.setExpression(id,settings);
      },
      startSpeech(settings){const a=shot().activity;speechFrom=mixSpeech(now());speechTarget=1;speechAt=now();frozenCel=a?clamp(a.frame,4,19):null;revision++;return base.startSpeech(settings);},
      stopSpeech(){speechFrom=mixSpeech(now());speechTarget=0;speechAt=now();revision++;return base.stopSpeech();},
      blink(){revision++;base.blink();},
      setComparison(value){comparison=!!value;revision++;},
      inspect(settings={}){held={...settings};revision++;return shot();},
      update(time=now()){if(dead)return null;prepare(time);if(!loaded||!base.loaded)return loadingState(time);const s=shot(time);base.setGaze(s.gaze.x,s.gaze.y);const state=base.update(time);return state?{...state,thinking:s}:null;},
      snapshot(time=now(),overrides={}){prepare(time);if(!loaded||!base.loaded)return loadingState(time);const s=shot(time),state=base.snapshot(time,{...overrides,gaze:overrides.gaze||s.gaze});return {...state,thinking:s};},
      renderTo(canvas,time=now(),overrides={}){prepare(time);if(!loaded||!base.loaded)return loadingState(time);const s=shot(time),state=base.renderTo(canvas,time,{...overrides,gaze:overrides.gaze||s.gaze});return {...state,thinking:s};},
      destroy(){dead=true;current=null;pendingExpression=null;if(raf!==null)root.cancelAnimationFrame?.(raf);base.destroy();},
      get expression(){return base.expression;},get expressionMode(){return automatic?'auto':'explicit';},get expressions(){return base.expressions;},get speaking(){return base.speaking;},
      get canvas(){return base.canvas;},get loaded(){return loaded&&base.loaded;},get error(){return error||base.error;},get manifest(){return manifest;}
    };
    api.ready=(async()=>{try{
      const manifestUrl=options.manifestUrl||'manifest.json';
      if(!manifest){const r=await root.fetch(manifestUrl,{cache:'no-cache'});if(!r.ok)throw new Error('Thinking manifest HTTP '+r.status);manifest=await r.json();}
      validateManifest(manifest);
      const frameMetadata=new Map(manifest.studies.flatMap(s=>manifest.assets[s.asset].frames.map(frame=>[frame.file,frame]))),files=[...frameMetadata.keys()];
      if(!options.thinkingImages)await Promise.all(files.map(async file=>{const imageUrl=new URL(file,new URL(manifestUrl,root.location.href)),hash=frameMetadata.get(file).sha256;
        if(hash)imageUrl.searchParams.set('v',hash);const url=imageUrl.href;
        if(!sharedLoads.has(url))sharedLoads.set(url,(async()=>{const img=new root.Image();img.src=url;await img.decode();if(img.naturalWidth!==256||img.naturalHeight!==256)throw new Error('Unregistered prop: '+file);return img;})().catch(problem=>{sharedLoads.delete(url);throw problem;}));
        const image=await sharedLoads.get(url);if(!dead)images[file]=image;}));
      if(dead)return false;if(files.some(f=>!images[f]))throw new Error('Thinking drawings incomplete');
      if(!await base.ready)throw base.error||new Error('Original MIST drawings could not load');
      if(dead)return false;loaded=true;revision++;api.update(now());return true;
    }catch(problem){if(dead)return false;error=problem;loaded=false;options.onError?.(problem);return false;}})();
    if(options.autoStart!==false&&root.requestAnimationFrame){const tick=time=>{if(dead)return;api.update(time);raf=root.requestAnimationFrame(tick);};raf=root.requestAnimationFrame(tick);}
    return api;
  }
  root.MistThinkingRuntime={create,sampleChoreography,validateManifest,version:'8.0.0',fps:FPS,activities:IDS,phrases:PHRASES,autoFaces:AUTO_FACES,entranceMs:ENTER,exitMs:EXIT};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.MistThinkingRuntime;
})(typeof window!=='undefined'?window:globalThis);
