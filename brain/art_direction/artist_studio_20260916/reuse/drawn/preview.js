'use strict';
(() => {
 const $=s=>document.querySelector(s),data=window.MIST_DATA,audit=window.REUSE_AUDIT;
 const FPS=MistDrawnFaceRuntime.timing?.fps??15,FRAME_MS=1000/FPS;
 const familyIds={'Round gap':'round','Hooked lid':'hook','Arc':'arc','Loop with crossbar':'loop','Narrow slot':'slot','Chevron':'chevron','Flat bar':'bar'};
 const fallbackBlinkNames=['rest','anticipation','closing','closed','opening','settled'];
 const fallbackMouthNames=['rest','MBP','small_AA','AA','EH','EE','OH','OO','FV','LNT','S','SMILE'];
 const partFamily={};for(const [name,parts] of Object.entries(audit.motion_families))for(const part of parts)partFamily[part]=familyIds[name];
 const references={round:'circle_gap_03',hook:'angry_hook_00',arc:'happy_arc_16',loop:'e_shape_12',slot:'open_C_44',chevron:'chevron_01',bar:'flat_bar_14'};
 // Fit the family drawing once to each canonical eye, before the face's own placement.
 function resample(part){const points=part.points.slice();if(part.kind==='fill')points.push(points[0]);const lengths=[0];for(let i=1;i<points.length;i++)lengths.push(lengths.at(-1)+Math.hypot(points[i][0]-points[i-1][0],points[i][1]-points[i-1][1]));const result=[];for(let n=0;n<64;n++){const t=lengths.at(-1)*n/(part.kind==='fill'?64:63);let i=1;while(i<lengths.length-1&&lengths[i]<t)i++;const amount=(t-lengths[i-1])/(lengths[i]-lengths[i-1]||1);result.push([points[i-1][0]+(points[i][0]-points[i-1][0])*amount,points[i-1][1]+(points[i][1]-points[i-1][1])*amount]);}const mean=[0,1].map(axis=>result.reduce((s,p)=>s+p[axis],0)/result.length);return result.map(p=>[p[0]-mean[0],p[1]-mean[1]]);}
 function align(source,target){const a=resample(source),b=resample(target);let best={score:Infinity,rotation:0,mirror:false};for(const mirror of [false,true])for(const reverse of [false,true])for(let shift=0;shift<(source.kind==='fill'?64:1);shift+=4){let dot=0,cross=0;for(let i=0;i<a.length;i++){const p=[a[i][0]*(mirror?-1:1),a[i][1]],q=b[((reverse?63-i:i)+shift)%64];dot+=p[0]*q[0]+p[1]*q[1];cross+=p[0]*q[1]-p[1]*q[0];}const angle=Math.atan2(cross,dot),c=Math.cos(angle),s=Math.sin(angle);let score=0;for(let i=0;i<a.length;i++){const x=a[i][0]*(mirror?-1:1),y=a[i][1],q=b[((reverse?63-i:i)+shift)%64];score+=(c*x-s*y-q[0])**2+(s*x+c*y-q[1])**2;}score+=Math.abs(angle)*1e-8+(mirror?1e-8:0);if(score<best.score)best={score,rotation:angle,mirror};}return best;}
 const alignments={};for(const [part,family]of Object.entries(partFamily))alignments[part]=align(data.parts[references[family]],data.parts[part]);
 let atlas,ready=false,time=0,animationOrigin=0,lastWall=null,lastDraw=-Infinity,playing=!matchMedia('(prefers-reduced-motion: reduce)').matches,manualBlink=-1e9,selected=0,heldEye=null,heldMouth=null;
 const animationFrame=value=>Math.floor((value-animationOrigin)/FRAME_MS+1e-8);
 const sampledAnimationTime=()=>animationOrigin+animationFrame(time)*FRAME_MS;
 const loaded={},faces=[];
 const voice={active:false,paused:false,context:null,playback:null,speech:null,samples:[],sample:null,start:0,duration:0,loading:false,generation:0};
 const events=['rest','MBP','AA','EH','EE','LNT','OO','OH','FV','S','rest','MBP','AA','SMILE','EH','OO','LNT','EE','rest','rest'].map((viseme,i)=>({time:i*.19,viseme,amount:.8}));
 const speechPattern=[0,1,2,3,3,4,5,9,1,7,7,6,8,10,0,0,1,2,3,4,11,11,5,9,1,7,6,9,5,0,0,0,0,0,0,0,0,0,0,0];
 function box(points,pad=0){const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);const x=Math.min(...xs)-pad,y=Math.min(...ys)-pad;return{x,y,w:Math.max(...xs)+pad-x,h:Math.max(...ys)+pad-y};}
 function label(face){return face.name.replaceAll('_',' ');}
 function poseNames(id){return atlas.assets[id].frames.map((f,i)=>f.pose||f.name||(id.startsWith('mouth')?fallbackMouthNames:fallbackBlinkNames)[i]||`Pose ${i+1}`);}
 function poseIndex(id,name,fallback=0){const names=poseNames(id),needle=name.toLowerCase().replaceAll(/[^a-z0-9]/g,'');const index=names.findIndex(n=>n.toLowerCase().replaceAll(/[^a-z0-9]/g,'')===needle);return index<0?fallback:index;}
 for(const [index,face] of data.faces.entries()){
  const slots={};for(const group of audit.groups)for(const use of group.uses)if(use.face===face.id)slots[use.role]={...use};
  const card=document.createElement('button');card.className='card';card.dataset.expression=face.id;card.setAttribute('aria-label',`Inspect ${label(face)}`);
  const canvas=document.createElement('canvas');canvas.width=500;canvas.height=320;
  const caption=document.createElement('span');caption.className='label';const num=document.createElement('span');num.className='number';num.textContent=face.id.slice(0,2);const name=document.createElement('span');name.className='name';name.textContent=label(face);caption.append(num,name);card.append(canvas,caption);$('#grid').append(card);
  const original=MistFaceRuntime.create(null,{data,expression:face.id,autoStart:false,reducedMotion:false,now:()=>time});
  const staticRenderer=MistFaceRuntime.create(null,{data,expression:face.id,autoStart:false,reducedMotion:true,now:()=>0});
  const staticLayers=staticRenderer.snapshot(0).layers;staticRenderer.destroy();
  const item={face,index,slots,canvas,original,staticLayers,speechPhase:-1,voiceSpeech:null,drawn:null,drawnSpeech:null};
  item.silentSpeech={sample:()=>{const step=speechStep(item),viseme=fallbackMouthNames[speechPattern[step]];return{viseme:viseme==='small_AA'?'AA':viseme,amount:viseme==='small_AA'?.3:.85,active:$('#talk').checked&&step<32,time:time/1000,source:'silent-study'};},events:[],duration:Infinity,clock:()=>time/1000};
  faces.push(item);
  card.onclick=()=>openInspector(index);
 }
 function paintLayer(ctx,layer){if(!layer.points.length)return;ctx.save();ctx.globalAlpha=layer.opacity??1;ctx.fillStyle=ctx.strokeStyle='#5eeadd';ctx.lineWidth=layer.width||1;ctx.lineCap='round';ctx.lineJoin='round';const path=new Path2D(MistFaceRuntime.pathData(layer.points,layer.mode==='fill'));if(layer.mode==='fill')ctx.fill(path);else ctx.stroke(path);ctx.restore();}
 function keySheet(img){
  const canvas=document.createElement('canvas');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(img,0,0);
  const pixels=ctx.getImageData(0,0,canvas.width,canvas.height),p=pixels.data;let transparent=0,white=0;
  for(let n=0;n<p.length;n+=400){if(p[n+3]<30)transparent++;else if(Math.min(p[n],p[n+1],p[n+2])>235)white++;}
  for(let n=0;n<p.length;n+=4){if(white>transparent){const low=Math.min(p[n],p[n+1],p[n+2]),high=Math.max(p[n],p[n+1],p[n+2]);if(high-low<22){p[n+3]=0;continue;}const alpha=Math.min(1,(255-low)/161);if(alpha<.035){p[n+3]=0;continue;}p[n+3]*=alpha;}p[n]=94;p[n+1]=234;p[n+2]=221;}
  ctx.putImageData(pixels,0,0);
  return canvas;
 }
 function drawAsset(ctx,id,frameIndex,scaleX,scaleY=scaleX){
  const asset=atlas.assets[id],f=asset.frames[frameIndex];if(!f)return;const sheet=f.file?loaded[f.file]:loaded[id];if(!sheet)return;
  const cx=f.cx??(f.x+f.w/2),cy=f.cy??(f.y+f.h/2);
  const sourceScale=f.sourceScale??1;ctx.drawImage(sheet,f.x,f.y,f.w,f.h,(f.x-cx)*scaleX*sourceScale,(f.y-cy)*scaleY*sourceScale,f.w*scaleX*sourceScale,f.h*scaleY*sourceScale);
 }
 function dimensions(id){const a=atlas.assets[id],f=a.frames[0];return{w:a.masterWidth||f.w,h:a.masterHeight||f.h};}
 function blinkFrame(item,id=partFamily[item.slots.eye_L.part]){
  const sampledTime=sampledAnimationTime();let elapsed=sampledTime-manualBlink;
  const duration=MistDrawnFaceRuntime.timing?.blinkMs??FRAME_MS*6;
  if(elapsed<0||elapsed>=duration){const offset=$('#sync').checked?0:(item.index*887)%4200;elapsed=(sampledTime+offset)%5400-3700;}
  return MistDrawnFaceRuntime.helpers.blinkPose(atlas.assets[id],elapsed);
 }
 function speechStep(item){return(Math.floor(animationFrame(time)/2)+($('#sync').checked?0:item.index*3))%speechPattern.length;}
 function mouthFrame(item){const id=mouthAsset(item);if(voice.active){if(voice.paused||!voice.speech)return poseIndex(id,'rest');const event=voiceEvent();let pose=event.viseme||'rest';if(pose==='AA')pose=event.amount<.28?'release':event.amount<.5?'small_AA':'AA';if((pose==='OO'||pose==='OH')&&event.amount<.35)pose='round_close';return poseIndex(id,pose,poseIndex(id,event.viseme,poseIndex(id,'small_AA')));}return poseIndex(id,fallbackMouthNames[speechPattern[speechStep(item)]]);}
 function voiceEvent(){if(!voice.speech||voice.paused)return{viseme:'rest',amount:0,active:false};let event;if(voice.speech.sample)event=voice.speech.sample();else{const t=voice.speech.clock();if(t<0||t>voice.speech.duration)return{viseme:'rest',amount:0,active:false};const events=voice.speech.events;let low=0,high=events.length;while(low<high){const mid=(low+high)>>1;if(events[mid].time<=t)low=mid+1;else high=mid;}event=events[Math.max(0,low-1)]||{viseme:'rest',amount:0};}if(event.active===false)return{...event,viseme:'rest',amount:0};return event;}
 function mouthAsset(item){return MistDrawnFaceRuntime.helpers.mouthAssetForFace?.(item.face.id,atlas)||atlas.mouthFamilies?.[item.face.id]||'mouth_neutral';}
 function mouthLabel(id){return atlas.assets[id].label||id.replace(/^mouth_/,'').replaceAll('_',' ');}
 function drawFace(item,canvas,inspection=false){
  if($('#mode').value==='original'){
   const ctx=canvas.getContext('2d');ctx.setTransform(canvas.width/100,0,0,canvas.height/64,0,0);ctx.clearRect(0,0,100,64);ctx.fillStyle='#101c20';ctx.fillRect(0,0,100,64);
   const phase=Math.floor(time/5000),speak=!voice.active&&$('#talk').checked&&time%5000<4000;
   if(voice.active){const speech=voice.paused?null:voice.speech;if(item.voiceSpeech!==speech){if(speech)item.original.startSpeech(speech);else item.original.stopSpeech();item.voiceSpeech=speech;}}
   else if(speak&&item.speechPhase!==phase){item.original.startSpeech({events,duration:4,clock:()=>time%5000/1000});item.speechPhase=phase;}else if(!speak){item.original.stopSpeech();item.speechPhase=-1;}
   item.original.setGaze($('#gaze').checked?Math.sin(time/1700)*.4:0,$('#gaze').checked?Math.sin(time/2400)*.22:0);item.original.update(time);for(const layer of item.original.snapshot(time).layers)paintLayer(ctx,layer);return;
  }
  if(!ready)return;
  const speech=voice.active?(voice.paused?null:voice.speech):($('#talk').checked?item.silentSpeech:null);
  if(item.drawnSpeech!==speech){if(speech)item.drawn.startSpeech(speech);else item.drawn.stopSpeech();item.drawnSpeech=speech;}
  item.drawn.setGaze($('#gaze').checked?Math.sin(time/1700)*.4:0,$('#gaze').checked?Math.sin(time/2400)*.22:0);
  const eyeFrames={};for(const role of ['eye_L','eye_R']){const id=partFamily[item.slots[role].part];eyeFrames[role]=inspection&&heldEye!==null?Math.min(heldEye,atlas.assets[id].frames.length-1):blinkFrame(item,id);}
  const overrides={blinkFrame:eyeFrames};if(inspection&&heldMouth!==null&&!voice.active)overrides.mouthFrame=heldMouth;
  item.drawn.renderTo(canvas,time,overrides);
 }
 function draw(){for(const item of faces)drawFace(item,item.canvas);if(ready&&$('#inspect').open){const item=faces[selected],id=partFamily[item.slots[$('#eye-side').value].part];drawFace(item,$('#focus'),true);const bf=heldEye??blinkFrame(item,id),mf=heldMouth??mouthFrame(item);$('#phase').textContent=`${poseNames(id)[bf]} / ${$('#talk').checked||heldMouth!==null||voice.active?poseNames(mouthAsset(item))[mf]:'Rest'}`;$('#eye-strip').querySelectorAll('button').forEach((b,i)=>b.classList.toggle('selected',i===bf));$('#mouth-strip').querySelectorAll('button').forEach((b,i)=>b.classList.toggle('selected',i===mf&&($('#talk').checked||heldMouth!==null||voice.active)));}if(voice.active&&voice.context)$('#voice-status').textContent=`${voice.paused?'Paused':'Voice timing'} / ${Math.max(0,voice.context.currentTime-voice.start).toFixed(1)} / ${voice.duration.toFixed(1)} s`;lastDraw=time;}
 function strip(container,id,names,type){
  container.replaceChildren();const master=dimensions(id),asset=atlas.assets[id],maxWidth=Math.max(master.w,...asset.frames.map(f=>f.w*(f.sourceScale??1))),maxHeight=Math.max(master.h,...asset.frames.map(f=>f.h*(f.sourceScale??1)));
  for(const [index,name]of names.entries()){
   const button=document.createElement('button');button.title=`Hold ${name}`;const canvas=document.createElement('canvas');canvas.width=180;canvas.height=120;const ctx=canvas.getContext('2d');ctx.fillStyle='#101c20';ctx.fillRect(0,0,180,120);const scale=Math.min(120/maxWidth,80/maxHeight);ctx.translate(90,60+(type==='eye'?1:-1)*maxHeight*scale/2);drawAsset(ctx,id,index,scale);const text=document.createElement('span');text.textContent=name;button.append(canvas,text);button.onclick=()=>{if(type==='eye')heldEye=index;else heldMouth=index;draw();};container.append(button);
  }
 }
 function populateStrips(){if(!ready)return;const item=faces[selected],slot=item.slots[$('#eye-side').value],family=partFamily[slot.part],mouth=mouthAsset(item);$('#family-label').textContent=`${family} / ${slot.part}`;$('#mouth-label').textContent=mouthLabel(mouth);strip($('#eye-strip'),family,poseNames(family),'eye');strip($('#mouth-strip'),mouth,poseNames(mouth),'mouth');}
 function openInspector(index){if(!ready)return;selected=index;heldEye=heldMouth=null;$('#focus-name').textContent=`${faces[index].face.id.slice(0,2)} / ${label(faces[index].face)}`;populateStrips();$('#inspect').showModal();draw();}
 function setPlaying(value){playing=value;$('#play').textContent=$('#focus-play').textContent=playing?'Pause':'Play';lastWall=null;if(voice.active){voice.paused=!value;if(value)voice.context.resume();else voice.context.suspend();$('#voice-play').textContent=value?'Pause voice':'Resume voice';draw();}}
 function step(){setPlaying(false);time+=FRAME_MS;draw();}
 function blink(){heldEye=null;manualBlink=sampledAnimationTime();for(const item of faces)item.original.blink();if(!playing)time+=FRAME_MS;draw();}
 $('#play').onclick=$('#focus-play').onclick=()=>setPlaying(!playing);$('#step').onclick=$('#focus-step').onclick=step;$('#blink').onclick=$('#focus-blink').onclick=blink;
 $('#close').onclick=()=>$('#inspect').close();$('#eye-side').onchange=populateStrips;$('#resume-cels').onclick=()=>{heldEye=heldMouth=null;draw();};
 for(const id of ['talk','gaze','sync','mode'])$('#'+id).onchange=draw;$('#fps').onchange=()=>lastDraw=-Infinity;$('#speed').onchange=()=>lastWall=null;
 document.addEventListener('visibilitychange',()=>lastWall=null);
 function tick(now){if(lastWall===null)lastWall=now;if(playing&&!document.hidden){time+=Math.min(100,now-lastWall)*Number($('#speed').value);if(voice.active||animationFrame(time)>animationFrame(lastDraw))draw();}lastWall=now;requestAnimationFrame(tick);}
 async function initVoice(){
  try{const response=await fetch('audio/samples.json',{cache:'no-store'});if(!response.ok)throw Error('No saved samples');const json=await response.json();voice.samples=Array.isArray(json)?json:json.samples;$('#voice-sample').replaceChildren();for(const [i,sample]of voice.samples.entries()){const option=document.createElement('option');option.value=String(i);option.textContent=sample.name||sample.label||sample.id||`Sample ${i+1}`;$('#voice-sample').append(option);}$('#voice-play').disabled=!voice.samples.length;$('#voice-status').textContent='Saved MIST voice / audio timing test';}
  catch{$('#voice-sample').options[0].textContent='No saved samples';$('#voice-status').textContent='Voice samples unavailable';}
 }
 function stopVoice(){voice.generation++;voice.loading=false;voice.active=false;voice.paused=false;voice.speech=null;voice.sample=null;voice.playback?.reset();$('#talk').checked=false;$('#voice-play').disabled=!voice.samples.length;$('#voice-play').textContent='Play voice';$('#voice-stop').disabled=true;$('#voice-status').textContent='Stopped';$('#study-mode').textContent='ImageGen cels. Silent speech study.';$('#speed').disabled=false;for(const item of faces){item.original.stopSpeech();item.voiceSpeech=null;}draw();}
 async function playVoice(){
  if(voice.loading)return;
  if(voice.active){setPlaying(voice.paused);draw();return;}
  const sample=voice.samples[Number($('#voice-sample').value)];if(!sample)return;
  const generation=++voice.generation,stale=()=>generation!==voice.generation;
  voice.loading=true;$('#voice-play').disabled=true;$('#voice-stop').disabled=false;$('#voice-status').textContent='Loading voice...';
  try{
   const {Playback}=await import('../runtime/playback.js?v=fps15-th');if(stale())return;
   voice.context??=new AudioContext();await voice.context.resume();if(stale())return;
   let file=sample.file||sample.path||sample.url;if(!file)throw Error('Sample has no audio file');if(!file.startsWith('audio/')&&!file.startsWith('/')&&!file.startsWith('http'))file='audio/'+file;
   const response=await fetch(file);if(stale())return;if(!response.ok)throw Error(`Audio: HTTP ${response.status}`);const bytesBuffer=await response.arrayBuffer();if(stale())return;const decoded=await voice.context.decodeAudioData(bytesBuffer);if(stale())return;
   let cues=null;if(sample.cues){const cuesPath=sample.cues.startsWith('audio/')?sample.cues:'audio/'+sample.cues;const cueResponse=await fetch(cuesPath);if(stale())return;if(!cueResponse.ok)throw Error(`Cues: HTTP ${cueResponse.status}`);cues=await cueResponse.json();if(stale())return;if(!Array.isArray(cues.mouth_cues))throw Error('Invalid character timing data');}
   const channels=Array.from({length:decoded.numberOfChannels},(_,i)=>decoded.getChannelData(i)),pcm=new Int16Array(decoded.length);for(let i=0;i<pcm.length;i++){let value=0;for(const channel of channels)value+=channel[i];pcm[i]=Math.round(Math.max(-1,Math.min(1,value/channels.length))*32767);}
   const bytes=new Uint8Array(pcm.buffer);let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
   const adapter={startSpeech(options){voice.speech=options;voice.start=voice.context.currentTime-options.clock();},stopSpeech(){voice.speech=null;}};
   voice.playback??=new Playback(voice.context,adapter,()=>$('#voice-status').textContent='Playback interrupted',()=>{stopVoice();$('#voice-status').textContent='Finished';});
   voice.active=true;voice.paused=false;voice.sample=sample;voice.duration=decoded.duration;voice.start=voice.context.currentTime+.2;voice.speech=null;heldMouth=null;setPlaying(true);$('#talk').checked=true;$('#speed').disabled=true;$('#speed').value='1';
   $('#study-mode').textContent=cues?'Character timing + audio. Not phoneme recognition.':'Saved voice. Audio energy controls the mouth; no phoneme alignment.';$('#voice-play').textContent='Pause voice';$('#voice-stop').disabled=false;
   voice.playback.append({epoch:voice.playback.epoch+1,pcm:btoa(binary),sample_rate:decoded.sampleRate,text:sample.text||sample.transcript||'',...(cues?{mouth_cues:cues.mouth_cues,alignment_source:cues.alignment_source||'character_timing'}:{alignment_source:'audio_energy'})});draw();
  }catch(error){if(stale())return;stopVoice();$('#voice-status').textContent=`Voice unavailable: ${error.message}`;console.error(error);}finally{if(!stale()){voice.loading=false;$('#voice-play').disabled=false;}}
 }
 $('#voice-play').onclick=playVoice;$('#voice-stop').onclick=stopVoice;$('#voice-sample').onchange=stopVoice;
 async function init(){
  try{
   const response=await fetch('atlas.json',{cache:'no-store'});if(!response.ok)throw new Error(`Atlas: HTTP ${response.status}`);atlas=await response.json();
   const required=['round','hook','arc','loop','slot','chevron','bar','mouth_neutral','mouth_smile'];for(const id of required)if(!atlas.assets[id]||atlas.assets[id].frames.length<4)throw new Error(`Missing drawings: ${id}`);
   const allAssets=Object.values(atlas.assets),imageFiles=new Set(allAssets.flatMap(asset=>[asset.file,...asset.frames.map(frame=>frame.file).filter(Boolean)]));
   await Promise.all([...imageFiles].map(async file=>{const image=new Image();image.src=file;await image.decode();loaded[file]=keySheet(image);}));
   for(const [id,asset]of Object.entries(atlas.assets))loaded[id]=loaded[asset.file];
   for(const item of faces)for(const role of ['eye_L','eye_R'])if(!partFamily[item.slots[role]?.part])throw new Error(`Unmapped eye: ${item.face.id} ${role}`);
   animationOrigin=time;
   for(const item of faces){item.drawn=MistDrawnFaceRuntime.create(null,{data,expression:item.face.id,atlas,images:loaded,autoStart:false,reducedMotion:false,fps:FPS,now:()=>time});if(typeof item.drawn.renderTo!=='function')throw Error('Publish the updated production renderer with renderTo');}
   await Promise.all(faces.map(item=>item.drawn.ready));
   ready=true;$('#status').textContent='40 faces / 15 fps';$('#compare-mouths').disabled=false;draw();
  }catch(error){$('#status').textContent='Drawings unavailable';$('#error').hidden=false;$('#error').textContent=`Could not load the generated sheets. ${error.message} Refresh once the asset export is complete.`;console.error(error);}
 }
 const comparison={cards:[],playing:false,time:0,lastWall:null,lastFrame:-1};
 const comparisonSequence=['rest','rest','MBP','release','small_AA','AA','AA','EH','EE','LNT','wide_close','rest','OH','OO','round_close','FV','TH','S','rest','rest'];
 function drawComparison(){
  const pose=$('#comparison-pose').value;
  for(const card of comparison.cards){const index=poseIndex(card.id,pose,-1),frame=index<0?poseIndex(card.id,'rest'):index,ctx=card.canvas.getContext('2d');ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle='#101c20';ctx.fillRect(0,0,600,300);ctx.translate(300,80);drawAsset(ctx,card.id,frame,card.scale);card.pose.textContent=index<0?`${pose} / no drawing`:pose;}
 }
 function comparisonStep(){comparison.playing=false;$('#comparison-play').textContent='Animate';comparison.time+=FRAME_MS;setComparisonPose();}
 function setComparisonPose(){const index=Math.floor(comparison.time/(FRAME_MS*2)+1e-8)%comparisonSequence.length;const pose=comparisonSequence[index];if([...$('#comparison-pose').options].some(option=>option.value===pose))$('#comparison-pose').value=pose;drawComparison();}
 function openComparison(){
  comparison.cards=[];$('#comparison-grid').replaceChildren();$('#comparison-pose').replaceChildren();
  const mapped=[...new Set(faces.map(mouthAsset))],emotionIds=mapped.filter(id=>id!=='mouth_neutral');const ids=emotionIds.length>=6?emotionIds:mapped;
  const poses=[...new Set(ids.flatMap(poseNames))];for(const pose of poses){const option=document.createElement('option');option.value=pose;option.textContent=pose;$('#comparison-pose').append(option);}
  for(const id of ids){const asset=atlas.assets[id],card=document.createElement('article');card.className='comparison-card';const canvas=document.createElement('canvas');canvas.width=600;canvas.height=300;const caption=document.createElement('div');caption.className='comparison-label';const label=document.createElement('span');label.textContent=mouthLabel(id);const pose=document.createElement('small');caption.append(label,pose);card.append(canvas,caption);$('#comparison-grid').append(card);const maxWidth=Math.max(...asset.frames.map(frame=>frame.w*(frame.sourceScale??1))),maxHeight=Math.max(...asset.frames.map(frame=>frame.h*(frame.sourceScale??1)));comparison.cards.push({id,canvas,pose,scale:Math.min(380/maxWidth,180/maxHeight)});}
  comparison.time=0;comparison.lastFrame=-1;comparison.lastWall=null;comparison.playing=false;$('#comparison-play').textContent='Animate';$('#mouth-comparison').showModal();drawComparison();
 }
 function tickComparison(wall){if(comparison.lastWall===null)comparison.lastWall=wall;if($('#mouth-comparison').open&&comparison.playing&&!document.hidden){comparison.time+=Math.min(100,wall-comparison.lastWall);const frame=Math.floor(comparison.time/FRAME_MS+1e-8);if(frame!==comparison.lastFrame){setComparisonPose();comparison.lastFrame=frame;}}comparison.lastWall=wall;requestAnimationFrame(tickComparison);}
 $('#compare-mouths').onclick=openComparison;$('#comparison-close').onclick=()=>$('#mouth-comparison').close();$('#mouth-comparison').onclose=()=>comparison.playing=false;$('#comparison-pose').onchange=()=>{comparison.playing=false;$('#comparison-play').textContent='Animate';drawComparison();};$('#comparison-play').onclick=()=>{comparison.playing=!comparison.playing;comparison.lastWall=null;$('#comparison-play').textContent=comparison.playing?'Pause':'Animate';};$('#comparison-step').onclick=comparisonStep;requestAnimationFrame(tickComparison);
 window.MistDrawnPreview={get ready(){return ready;},get time(){return time;},faces,partFamily,alignments,voice,comparison,draw,step,blink,openInspector,openComparison,playVoice,stopVoice,poseNames,get atlas(){return atlas;}};
 setPlaying(playing);draw();requestAnimationFrame(tick);init();initVoice();
})();
