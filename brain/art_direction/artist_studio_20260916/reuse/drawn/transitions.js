import {Playback} from '../runtime/playback.js?v=fps15-th';
const $=s=>document.querySelector(s),faces=window.MIST_DATA.faces,visited=new Set();
const FPS=MistDrawnFaceRuntime.timing?.fps??15,FRAME_MS=1000/FPS;
let now=0,lastWall=null,lastRender=-Infinity,playing=true,renderer=null,ready=false,current=faces[0].id,source=current,target=current,transitionStart=-Infinity,transitionDuration=MistDrawnFaceRuntime.timing?.transitionMs??600,nextAt=Infinity;
const voice={context:null,playback:null,samples:[],loading:false,active:false,generation:0};
const name=id=>{const face=faces.find(f=>f.id===id);return face?`${face.id.slice(0,2)} ${face.name.replaceAll('_',' ')}`:id;};
for(const [i,face]of faces.entries()){
 for(const id of ['from','to']){const option=document.createElement('option');option.value=face.id;option.textContent=name(face.id);$('#'+id).append(option);}
 const button=document.createElement('button');button.textContent=name(face.id);button.title=name(face.id);button.dataset.id=face.id;button.disabled=true;button.onclick=()=>transition(face.id);$('#face-list').append(button);
}
$('#to').value=faces[1].id;
function updateReadout(state){
 const progress=Math.max(0,Math.min(1,(now-transitionStart)/transitionDuration));$('#progress').value=progress;$('#pair').textContent=source===target?name(target):`${name(source)} → ${name(target)}`;
 $('#cue').textContent=`${state?.viseme||'rest'}${state?.speechTime!=null?' / '+Math.max(0,state.speechTime).toFixed(2)+' s':''}`;
 $('#count').textContent=`${visited.size} / 40`;for(const button of $('#face-list').children){button.classList.toggle('active',button.dataset.id===target);button.classList.toggle('visited',visited.has(button.dataset.id));}
}
function transition(id=$('#to').value){if(!ready)return;source=renderer.expression;target=id;current=id;transitionStart=now;transitionDuration=Number($('#duration').value);renderer.setExpression(id,{durationMs:transitionDuration});$('#from').value=source;$('#to').value=target;visited.add(target);nextAt=now+transitionDuration+1500;updateReadout(renderer.update(now));}
function next(){const index=faces.findIndex(face=>face.id===target);transition(faces[(index+1)%faces.length].id);}
function settleSource(){if(!ready)return;source=target=current=$('#from').value;renderer.setExpression(current,{durationMs:400});now+=2000;transitionStart=-Infinity;visited.add(current);renderer.update(now);updateReadout(renderer.snapshot(now));}
function setPlaying(value){playing=value;lastWall=null;$('#pause').textContent=value?'Pause':'Resume';if(voice.active){if(value)voice.context.resume();else voice.context.suspend();$('#voice').textContent=value?'Pause voice':'Resume voice';}if(renderer)updateReadout(renderer.update(now));}
function stopVoice(){voice.generation++;voice.loading=false;voice.active=false;voice.playback?.reset();$('#voice').disabled=!voice.samples.length;$('#voice').textContent='Play voice';$('#stop').disabled=true;$('#voice-status').textContent='Stopped';if(renderer)updateReadout(renderer.update(now));}
async function playVoice(){
 if(voice.loading)return;if(voice.active){setPlaying(!playing);return;}
 const sample=voice.samples[Number($('#sample').value)];if(!sample)return;const generation=++voice.generation,stale=()=>generation!==voice.generation;voice.loading=true;$('#voice').disabled=true;$('#stop').disabled=false;$('#voice-status').textContent='Loading voice...';
 try{
  voice.context??=new AudioContext();await voice.context.resume();if(stale())return;const file=sample.file.startsWith('audio/')?sample.file:'audio/'+sample.file;const response=await fetch(file);if(stale())return;if(!response.ok)throw Error('Audio HTTP '+response.status);const bytesBuffer=await response.arrayBuffer();if(stale())return;const audio=await voice.context.decodeAudioData(bytesBuffer);if(stale())return;
  let cues=null;if(sample.cues){const cueResponse=await fetch(sample.cues.startsWith('audio/')?sample.cues:'audio/'+sample.cues);if(stale())return;if(!cueResponse.ok)throw Error('Cues HTTP '+cueResponse.status);cues=await cueResponse.json();if(stale())return;if(!Array.isArray(cues.mouth_cues))throw Error('Invalid character timing data');}
  const channels=Array.from({length:audio.numberOfChannels},(_,i)=>audio.getChannelData(i)),pcm=new Int16Array(audio.length);for(let i=0;i<pcm.length;i++){let value=0;for(const channel of channels)value+=channel[i];pcm[i]=Math.round(Math.max(-1,Math.min(1,value/channels.length))*32767);}
  const bytes=new Uint8Array(pcm.buffer);let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
  voice.playback??=new Playback(voice.context,renderer,()=>$('#voice-status').textContent='Interrupted',()=>{stopVoice();$('#voice-status').textContent='Finished';});
  voice.active=true;setPlaying(true);voice.playback.append({epoch:voice.playback.epoch+1,pcm:btoa(binary),sample_rate:audio.sampleRate,text:sample.text||'',...(cues?{mouth_cues:cues.mouth_cues,alignment_source:cues.alignment_source||'character_timing'}:{alignment_source:'audio_energy'})});$('#voice').textContent='Pause voice';$('#stop').disabled=false;$('#voice-status').textContent=cues?'Character timing + audio / not phoneme recognition':'Audio energy timing / no phoneme alignment';
 }catch(error){if(stale())return;stopVoice();$('#voice-status').textContent=error.message;}finally{if(!stale()){voice.loading=false;$('#voice').disabled=false;}}
}
$('#transition').onclick=()=>{const destination=$('#to').value;settleSource();transition(destination);};$('#next').onclick=next;$('#from').onchange=settleSource;$('#pause').onclick=()=>setPlaying(!playing);$('#step').onclick=()=>{setPlaying(false);now+=FRAME_MS;updateReadout(renderer?.update(now));};$('#blink').onclick=()=>{renderer?.blink();if(!playing)now+=FRAME_MS;updateReadout(renderer?.update(now));};$('#tour').onchange=()=>{nextAt=now+500;if($('#tour').checked){visited.clear();visited.add(target);setPlaying(true);}};
$('#voice').onclick=playVoice;$('#stop').onclick=stopVoice;$('#sample').onchange=stopVoice;document.addEventListener('visibilitychange',()=>lastWall=null);
function tick(wall){if(lastWall===null)lastWall=wall;if(playing&&!document.hidden){now+=Math.min(100,wall-lastWall);if(ready){if($('#tour').checked&&now>=nextAt)next();if(voice.active||Math.floor(now/FRAME_MS+1e-8)>Math.floor(lastRender/FRAME_MS+1e-8)){updateReadout(renderer.update(now));lastRender=now;}}}lastWall=wall;requestAnimationFrame(tick);}
async function init(){try{
 renderer=MistDrawnFaceRuntime.create($('#stage'),{data:MIST_DATA,expression:current,atlasUrl:'atlas.json',autoStart:false,reducedMotion:false,fps:FPS,now:()=>now});ready=await renderer.ready;if(!ready)throw renderer.error||Error('Drawn renderer unavailable');visited.add(current);$('#status').textContent='40 expressions / 15 fps';for(const element of document.querySelectorAll('#transition,#next,#face-list button'))element.disabled=false;updateReadout(renderer.update(now));
 const response=await fetch('audio/samples.json');voice.samples=await response.json();$('#sample').replaceChildren();for(const [i,sample]of voice.samples.entries()){const option=document.createElement('option');option.value=String(i);option.textContent=sample.label||sample.name||sample.id;$('#sample').append(option);}$('#voice').disabled=false;
 }catch(error){$('#error').hidden=false;$('#error').textContent=error.message;$('#status').textContent='Preview unavailable';console.error(error);}}
window.MistTransitions={get ready(){return ready;},get renderer(){return renderer;},get now(){return now;},get source(){return source;},get target(){return target;},voice,visited,transition,next,stopVoice};
requestAnimationFrame(tick);init();
