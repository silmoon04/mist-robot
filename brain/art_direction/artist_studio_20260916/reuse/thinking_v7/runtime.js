/* Short work phrases around the original MIST face. */
(function(root){
  'use strict';
  const FPS=15,TICK=1000/FPS,ENTER=600,EXIT=600;
  const clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n));
  const ease=n=>{n=clamp(n);return n*n*(3-2*n);};
  const mix=(a,b,t)=>a+(b-a)*t;
  const IDS=['reading','coding','writing','sorting','searching','pondering'];
  // Milliseconds, beat, gaze x/y, first/last action cel, whole-face lean.
  const PHRASES={
    reading:[[650,'read',.65,.12,0,1,.25],[650,'next line',.95,.38,2,3,.35],[800,'pause',.45,.4,3,3,.2],[650,'read',.75,.62,4,5,.3],[650,'turn page',.55,.3,6,7,.15],[800,'settle',.55,.12,7,7,0]],
    coding:[[700,'type',.8,.35,0,2,.35],[700,'check',.9,.1,2,2,.2],[750,'consider',-.3,-.35,2,2,-.2],[700,'type',.8,.35,3,6,.35],[550,'inspect',.85,.15,7,7,.15],[700,'settle',.55,.12,7,7,0]],
    writing:[[850,'write',.85,.45,0,3,.3],[650,'read back',.55,.25,3,3,.15],[900,'consider',-.2,-.4,3,3,-.2],[850,'continue',.85,.5,4,7,.3],[850,'settle',.55,.12,7,7,0]],
    sorting:[[700,'compare',.9,.05,0,1,.1],[700,'compare',.45,.5,2,3,-.1],[900,'weigh up',-.25,-.25,3,3,-.2],[850,'arrange',.85,.2,4,7,.2],[850,'settle',.55,.12,7,7,0]],
    searching:[[900,'scan',.95,.15,0,1,.25],[900,'inspect',.95,.15,1,1,.25],[900,'scan',.25,.4,2,3,-.15],[900,'pause',.25,.4,3,3,-.15],[800,'settle',.55,.12,3,3,0]],
    pondering:[[1000,'wonder',-.25,-.55,0,1,-.15],[1250,'hold',-.25,-.55,1,1,-.15],[1000,'consider',.3,-.2,2,3,.12],[1250,'return',0,0,3,3,0]]
  };
  function sampleChoreography(id,elapsed,options={}){
    if(!IDS.includes(id))throw new Error('Unknown thinking study: '+id);
    const count=options.frameCount??(id==='searching'||id==='pondering'?12:16);
    if(![12,16].includes(count))throw new Error('Thinking assets need 12 or 16 frames');
    const age=Math.max(0,Number(elapsed)||0),loopCount=count-8,phrase=PHRASES[id];
    const duration=phrase.reduce((sum,b)=>sum+b[0],0),exitAge=options.exitAge;
    let phase='loop',beat='settle',frame=4,alpha=1,gx=.55,gy=.12,lean=0,progress=0;
    if(exitAge!==undefined&&exitAge!==null){
      const p=clamp(exitAge/EXIT);phase=p>=1?'rest':'exit';beat=p>=1?'rest':'put away';progress=p;
      frame=count-4+Math.min(3,Math.floor(p*4));alpha=1-ease(p);
      gx=(options.exitFrom?.gaze.x??.55)*alpha;gy=(options.exitFrom?.gaze.y??.12)*alpha;
      lean=(options.exitFrom?.lean??0)*alpha;
    }else if(age<ENTER){
      const p=age/ENTER;phase='entrance';beat=p<.35?'notice':'begin';progress=p;
      frame=Math.min(3,Math.floor(p*4));alpha=ease(p);gx=id==='pondering'?0:.55*ease(p);gy=id==='pondering'?0:.12*ease(p);
    }else{
      let cursor=(age-ENTER)%duration,index=0;
      while(cursor>=phrase[index][0])cursor-=phrase[index++][0];
      const b=phrase[index],previous=phrase[(index+phrase.length-1)%phrase.length];
      const f=clamp(cursor/b[0]),s=ease(cursor/Math.min(400,b[0]*.6));
      beat=b[1];progress=((age-ENTER)%duration)/duration;
      gx=mix(previous[2],b[2],s);gy=mix(previous[3],b[3],s);lean=mix(previous[6],b[6],s);
      const sourceMax=(id==='searching'||id==='pondering')?3:7;
      const cel=Math.round(mix(b[4],b[5],Math.min(.9999,f))*(loopCount-1)/sourceMax);
      frame=4+clamp(cel,0,loopCount-1);
    }
    const quiet=clamp(options.speechMix??(options.speaking?1:0));
    if(options.comparison){gx=0;gy=0;lean=0;if(phase==='loop')frame=4+Math.floor((age-ENTER)/240)%loopCount;beat=phase==='loop'?'icon loop':beat;}
    if(options.reducedMotion){gx=0;gy=0;lean=0;frame=phase==='rest'?count-1:4;}
    const layout=phase==='entrance'?ease(age/ENTER):phase==='exit'||phase==='rest'?alpha:1;
    const quietFace=1-quiet;
    const below=id==='reading'||id==='coding';
    const target=below?{x:10,y:-2,scale:.8}:id==='pondering'?{x:9,y:9,scale:.79}:{x:2,y:7,scale:.72};
    const transform={x:mix(0,target.x,layout)+lean*.9*quietFace,y:mix(0,target.y,layout)+Math.abs(lean)*.25*quietFace,scale:mix(1,target.scale,layout)};
    const prop={x:below?50:id==='pondering'?80:82,y:below?51:id==='pondering'?16:37,size:below?28:id==='pondering'?27:33,alpha:alpha*(1-quiet*.45),dy:phase==='entrance'?(1-ease(age/ENTER))*4:phase==='exit'?ease(exitAge/EXIT)*3:0};
    return {id,phase,beat:quiet>.5&&phase!=='rest'?'speaking':beat,frame,alpha,progress,duration,gaze:{x:gx*quietFace||0,y:gy*quietFace||0},lean,faceTransform:transform,prop,speechMix:quiet,eyeSource:'original-mist',fps:FPS};
  }
  function validateManifest(manifest){
    if(manifest?.version!==7||manifest.fps!==FPS)throw new Error('Expected thinking manifest v7 at 15 fps');
    for(const id of IDS){
      const config=manifest.studies?.find(x=>x.id===id),asset=manifest.assets?.[config?.asset];
      if(!config||!asset||![12,16].includes(asset.frames?.length)||asset.frames.some(f=>typeof f.file!=='string'||!f.file.startsWith('frames/')))throw new Error('Invalid thinking study: '+id);
    }
    return manifest;
  }
  const sharedLoads=new Map();
  function create(container,options={}){
    const now=options.now||(()=>root.performance.now()),data=options.data||root.MIST_DATA,drawn=options.drawnRuntime||root.MistDrawnFaceRuntime;
    if(!drawn)throw new Error('Load the original MIST renderer first');
    const origin=now(),visualTime=time=>origin+Math.floor((time-origin)/TICK+1e-7)*TICK;
    let manifest=options.manifest||null,images=options.thinkingImages||{},loaded=false,error=null,dead=false,raf=null;
    let current=null,serial=0,revision=0,held={},comparison=false,speechMix=0,speechAt=now(),speechFrom=0,speechTarget=0,frozenCel=null;
    const reduced=options.reducedMotion??!!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    function mixSpeech(time){return mix(speechFrom,speechTarget,ease((time-speechAt)/240));}
    function shot(time=now()){
      const at=visualTime(time),config=current&&manifest?.studies.find(s=>s.id===current.id);
      if(!current)return {ready:loaded,fps:FPS,eyeSource:'original-mist',activity:null,faceTransform:{x:0,y:0,scale:1},layers:held.layers||'all',gaze:{x:0,y:0}};
      const activity=sampleChoreography(current.id,at-current.at,{frameCount:manifest?.assets[config?.asset]?.frames.length,exitAge:current.exitAt===null?null:Math.max(0,at-current.exitAt),exitFrom:current.exitFrom,speechMix:mixSpeech(at),comparison,reducedMotion:reduced});
      if(Number.isInteger(held.activityFrame))activity.frame=clamp(held.activityFrame,0,(manifest?.assets[config?.asset]?.frames.length||16)-1);
      else if(frozenCel!==null&&activity.phase==='loop'&&activity.speechMix>.05)activity.frame=frozenCel;
      activity.asset=config?.asset;activity.file=manifest?.assets[config?.asset]?.frames[activity.frame]?.file||null;
      return {ready:loaded,fps:FPS,time:at,eyeSource:'original-mist',activity,faceTransform:activity.faceTransform,gaze:activity.gaze,layers:held.layers||'all',comparison};
    }
    const layer={get ready(){return loaded;},get revision(){return revision;},replaceEyes:false,
      get showEyes(){return !held.layers||held.layers==='all'||held.layers==='eyes';},
      get showMouth(){return !held.layers||held.layers==='all'||held.layers==='mouth';},
      get showDecorations(){return !held.layers||held.layers==='all';},
      faceTransform(state){return shot(state.drawnAnimation.time).faceTransform;},
      paint(context,state){const s=shot(state.drawnAnimation.time),a=s.activity;if(!a||a.phase==='rest'||(s.layers!=='all'&&s.layers!=='activity'))return;
        const image=images[a.file];if(!image)return;const p=a.prop;
        context.save();context.globalAlpha=p.alpha;context.drawImage(image,p.x-p.size/2,p.y+p.dy-p.size/2,p.size,p.size);context.restore();}
    };
    const base=drawn.create(container,{...options,fps:FPS,eyeLayer:layer,autoStart:false});
    const api={
      setActivity(id,settings={}){if(dead||!IDS.includes(id))return {accepted:false,reason:dead?'destroyed':'unknown_activity'};
        if(current?.id===id&&current.owner===(settings.owner??null)&&current.exitAt===null&&!settings.restart)return {accepted:true,token:current.token};
        current={id,owner:settings.owner??null,token:++serial,at:visualTime(now()),exitAt:null};
        // A new activity can arrive while the reply is still speaking.
        frozenCel=speechTarget===1||mixSpeech(now())>.05?4:null;
        revision++;return {accepted:true,token:current.token};},
      clearActivity(token,settings={}){if(!current||(token!=null&&token!==current.token))return false;
        if(settings.immediate)current=null;else if(current.exitAt===null){current.exitFrom=shot().activity;current.exitAt=visualTime(now());}revision++;return true;},
      setExpression(id,settings){return base.setExpression(id,settings);},
      startSpeech(settings){const a=shot().activity;speechFrom=mixSpeech(now());speechTarget=1;speechAt=now();frozenCel=a?clamp(a.frame,4,(manifest?.assets[a.asset]?.frames.length||16)-5):null;revision++;return base.startSpeech(settings);},
      stopSpeech(){speechFrom=mixSpeech(now());speechTarget=0;speechAt=now();revision++;return base.stopSpeech();},
      blink(){revision++;base.blink();},
      setComparison(value){comparison=!!value;revision++;},
      inspect(settings={}){held={...settings};revision++;return shot();},
      update(time=now()){if(dead)return null;const s=shot(time);base.setGaze(s.gaze.x,s.gaze.y);const state=base.update(time);return state?{...state,thinking:s}:null;},
      snapshot(time=now(),overrides={}){const s=shot(time),state=base.snapshot(time,{...overrides,gaze:overrides.gaze||s.gaze});return {...state,thinking:s};},
      renderTo(canvas,time=now(),overrides={}){const s=shot(time),state=base.renderTo(canvas,time,{...overrides,gaze:overrides.gaze||s.gaze});return {...state,thinking:s};},
      destroy(){dead=true;current=null;if(raf!==null)root.cancelAnimationFrame?.(raf);base.destroy();},
      get expression(){return base.expression;},get expressions(){return base.expressions;},get speaking(){return base.speaking;},
      get canvas(){return base.canvas;},get loaded(){return loaded&&base.loaded;},get error(){return error||base.error;},get manifest(){return manifest;}
    };
    api.ready=(async()=>{try{
      const manifestUrl=options.manifestUrl||'manifest.json';
      if(!manifest){const r=await root.fetch(manifestUrl,{cache:'no-cache'});if(!r.ok)throw new Error('Thinking manifest HTTP '+r.status);manifest=await r.json();}
      validateManifest(manifest);
      const files=[...new Set(manifest.studies.flatMap(s=>manifest.assets[s.asset].frames.map(f=>f.file)))];
      if(!options.thinkingImages)await Promise.all(files.map(async file=>{const url=new URL(file,new URL(manifestUrl,root.location.href)).href;
        if(!sharedLoads.has(url))sharedLoads.set(url,(async()=>{const img=new root.Image();img.src=url;await img.decode();if(img.naturalWidth!==256||img.naturalHeight!==256)throw new Error('Unregistered prop: '+file);return img;})().catch(problem=>{sharedLoads.delete(url);throw problem;}));
        const image=await sharedLoads.get(url);if(!dead)images[file]=image;}));
      if(dead)return false;if(files.some(f=>!images[f]))throw new Error('Thinking drawings incomplete');loaded=true;revision++;await base.ready;if(dead)return false;api.update(now());return base.loaded;
    }catch(problem){if(dead)return false;error=problem;loaded=false;options.onError?.(problem);return false;}})();
    if(options.autoStart!==false&&root.requestAnimationFrame){const tick=time=>{if(dead)return;api.update(time);raf=root.requestAnimationFrame(tick);};raf=root.requestAnimationFrame(tick);}
    return api;
  }
  root.MistThinkingRuntime={create,sampleChoreography,validateManifest,version:'7.0.0',fps:FPS,activities:IDS,phrases:PHRASES};
  if(typeof module!=='undefined'&&module.exports)module.exports=root.MistThinkingRuntime;
})(typeof window!=='undefined'?window:globalThis);
