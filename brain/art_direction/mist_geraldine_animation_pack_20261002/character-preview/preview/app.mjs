import {createGeraldineAdapter} from '../adapter/geraldine-adapter.mjs';
import {SceneTransport} from './transport.mjs';
import {PreviewPlayback} from './playback.mjs';
const VERSION='1.0.1', $=id=>document.getElementById(id), storeKey='mist-character-preview-notes-v1';
let face, transport, playback, scenes, profiles, clips, buffers, scene, clip, profile='restrained', cursor=0, timer=null, finished=false, loading=true, frame=null, events=[], noteId=null, notes=[];
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
try{notes=JSON.parse(localStorage.getItem(storeKey)||'[]');if(!Array.isArray(notes))notes=[];}catch{$('saved').textContent='Browser storage unavailable. Export notes before leaving.';}
const format=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
async function json(path){const response=await fetch(path);if(!response.ok)throw new Error(`${path}: HTTP ${response.status}`);return response.json();}
function fail(error){stopLoop();if(playback){playback.stop('error');playback.update();}else{transport?.pause();face?.stopSpeech();} $('error').hidden=false;$('error').textContent=`Could not load or play the local preview: ${error.message}. Check that the complete animation pack is present, launch character-preview/serve.py, then reload this page.`;$('play').disabled=true;$('interrupt').disabled=true;$('replay').disabled=true;}
function log(type,detail=''){events.push({time:Math.round((transport?.time()||0)*1000),type,detail,epoch:playback?.epoch||0});if(events.length>150)events.shift();}
function stopLoop(){if(timer!==null)clearInterval(timer);timer=null;}
function startLoop(){stopLoop();timer=setInterval(tick,1000/15);}
function resetScene(reason='reset'){
  stopLoop();playback.reset(scene,clip,buffers.get(clip.id),reason);cursor=0;finished=false;events=[];frame=null;
  $('scene-title').textContent=scene.title;$('scene-description').textContent=scene.context;$('context').textContent='';$('caption').textContent='Press Play to begin.';$('caption-label').textContent='Recording transcript';$('progress').max=scene.durationMs;noteId=null;clearNote();log(reason);tick();
}
function applyEvent(event){
  const p=event.payload;
  if(transport.interrupted&&event.type!=='context'){log('canceled-event',`${event.type} · ${p.faceId||p.state||p.reason||''}`);return;}
  log(event.type,p.text||p.faceId||p.state||p.reason||'');
  if(event.type==='context'){$('speaker').textContent=p.speaker==='user'?'Simulated user':'Simulated context';$('context').textContent=p.text;return;}
  if(event.type==='state')face.handleEvent({type:'state',state:p.state,epoch:playback.epoch});
  if(event.type==='intent')face.setExpression(p.faceId,{epoch:playback.epoch});
  if(event.type==='reaction')face.setExpression(p.faceId,{epoch:playback.epoch,durationMs:profiles.find(x=>x.id===profile)[p.durationKey]});
  if(event.type==='interrupt')interrupt(p.reason);
}
function interrupt(reason='Review interruption'){
  if(loading||finished||!playback.interrupt())return;
  log('interrupt',reason);$('caption-label').textContent='Full recording transcript · playback interrupted';
  render();if(!transport.running&&playback.recovery)startLoop();
}
function tick(){
  if(!scene||loading)return;
  const time=transport.time()*1000;
  if(transport.running)while(cursor<scene.events.length&&scene.events[cursor].atMs<=time)applyEvent(scene.events[cursor++]);
  else if(time===0&&!transport.interrupted)while(cursor<scene.events.length&&scene.events[cursor].atMs===0)applyEvent(scene.events[cursor++]);
  if(time>=scene.audio.startMs)$('caption').textContent=clip.text;
  if(time>=scene.durationMs&&!finished){playback.stop('ended');finished=true;stopLoop();log('end');}
  render();
  if(!transport.running&&!playback.recovery)stopLoop();
  else if(!transport.running&&playback.recovery&&timer===null)startLoop();
}
function render(){
  const time=transport.time()*1000,result=playback.update();frame=result.frame;const audio=transport.sample();
  if(result.recovered)log('recovery',`${result.recovered.intent} · ${Math.round(result.recovered.durationMs)} ms`);
  $('time').textContent=`${format(time/1000)} / ${format(scene.durationMs/1000)}`;$('progress').value=time;
  $('play').textContent=finished?'Play again':transport.running||transport.pending?'Pause':time>0?'Resume':'Play';$('interrupt').disabled=finished||transport.interrupted||!(transport.running||transport.pending||time>0);
  $('state').textContent=finished?'Scene complete':transport.pending?'Starting audio…':transport.interrupted?(transport.running?'Listening · recording interrupted':'Paused · recording interrupted'):!transport.running?(time>0?'Paused':'Ready when you are'):audio.reason==='packet-gap'?'Delivery paused · holding the same thought':audio.active?'Speaking':frame.state==='thinking'?'Considering…':'Listening';
  if(!$('review').hidden&&$('inspector').open){
    const detail=playback.sampler.inspect({renderedCel:frame.pose,sceneId:scene.id,timelineTime:time,event:events.at(-1)});
    $('inspection').textContent=JSON.stringify({sceneMs:Math.round(time),faceMs:Math.round(result.time),audibleSeconds:+detail.audiblePosition.toFixed(3),target:detail.currentMouthTarget,renderedCel:detail.renderedCel,silence:detail.silence,reason:detail.reason,source:detail.source,alignmentSource:detail.alignmentSource,timingKind:detail.timingKind,intent:frame.intent,expression:frame.expression,epoch:playback.epoch,activeSources:transport.nodes.size},null,2);
    $('events').replaceChildren(...events.map(event=>{const li=document.createElement('li');li.textContent=`${(event.time/1000).toFixed(3)}s · ${event.type}${event.detail?' · '+event.detail:''}`;return li;}));
  }
}
async function play(){
  if(loading)return;
  if(transport.running||transport.pending){playback.pause();log('pause');stopLoop();render();if(playback.recovery)startLoop();return;}
  if(finished)resetScene('replay');
  const token=playback.epoch;try{const start=playback.play();render();const started=await start;if(!started||token!==playback.epoch||loading){if(!loading)render();return;}log('play');tick();if(!finished)startLoop();}catch(error){if(token===playback.epoch&&!loading)fail(error);}
}
function clearNote(){$('note').value='';document.querySelectorAll('[data-verdict]').forEach(button=>button.setAttribute('aria-pressed','false'));$('moment').textContent='Choose Keep / Revise or write a note to capture this moment.';}
function saveNote(verdict){
  let note=notes.find(x=>x.id===noteId);if(!note){note={id:globalThis.crypto?.randomUUID?.()||`${Date.now()}-${notes.length}`,sceneId:scene.id,time:Math.round(transport.time()*1000),audiblePosition:transport.sample().position,version:VERSION,profile,verdict:null,text:'',createdAt:new Date().toISOString()};notes.push(note);noteId=note.id;}
  if(verdict)note.verdict=verdict;note.text=$('note').value;
  document.querySelectorAll('[data-verdict]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.verdict===note.verdict)));
  $('moment').textContent=`${scene.title} · ${(note.time/1000).toFixed(2)}s · ${note.profile}`;
  try{localStorage.setItem(storeKey,JSON.stringify(notes));$('saved').textContent=`Saved in this browser · ${notes.length} ${notes.length===1?'moment':'moments'}.`;}catch{$('saved').textContent='Storage unavailable. Export notes before leaving.';}
}
$('play').addEventListener('click',play);$('interrupt').addEventListener('click',()=>interrupt());
$('replay').addEventListener('click',()=>{resetScene('replay');play();});
$('scene').addEventListener('change',()=>{scene=scenes.find(x=>x.id===$('scene').value);clip=clips.find(x=>x.id===scene.audio.clipId);resetScene('scene-change');});
document.querySelectorAll('[data-profile]').forEach(button=>button.addEventListener('click',()=>{if(profile===button.dataset.profile)return;const wasRunning=transport.running;profile=button.dataset.profile;document.querySelectorAll('[data-profile]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));resetScene('profile-change');if(wasRunning)play();}));
$('review-toggle').addEventListener('click',()=>{const open=$('review').hidden;$('review').hidden=!open;$('review-toggle').setAttribute('aria-expanded',String(open));if(open&&!loading)render();});
$('inspector').addEventListener('toggle',()=>{if(!loading)render();});$('new-note').addEventListener('click',()=>{noteId=null;clearNote();});$('note').addEventListener('input',()=>saveNote());document.querySelectorAll('[data-verdict]').forEach(b=>b.addEventListener('click',()=>saveNote(b.dataset.verdict)));
$('export').addEventListener('click',()=>{$('json').value=JSON.stringify({version:VERSION,units:{time:'scene milliseconds',audiblePosition:'recording seconds'},notes},null,2);$('export-panel').hidden=false;$('json').focus();});
$('copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('json').value);$('copy-status').textContent='Copied.';}catch{$('json').focus();$('json').select();$('copy-status').textContent='JSON selected. Press Ctrl+C (or ⌘C) to copy.';}});
$('download').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([$('json').value],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='geraldine-character-notes.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('copy-status').textContent='If the download did not open, use Copy JSON.';});
document.addEventListener('keydown',event=>{if(event.target.closest('input,textarea,select,button,summary')||loading)return;if(event.code==='Space'){event.preventDefault();play();}if(event.key.toLowerCase()==='i')interrupt();});
window.addEventListener('pagehide',()=>{loading=true;stopLoop();if(playback)playback.destroy();else{face?.destroy();transport?.destroy();}});
async function init(){
  const [sceneFile,profileFile,clipFile]=await Promise.all([json('../direction/scenes.json'),json('../direction/timing-profiles.json'),json('../../site/speech-clips.json')]);scenes=sceneFile.scenes;profiles=profileFile.profiles;clips=clipFile.clips;profile=profileFile.defaultProfile;
  const Audio=window.AudioContext||window.webkitAudioContext;if(!Audio)throw new Error('This browser does not support Web Audio');transport=new SceneTransport(new Audio());buffers=new Map();
  transport.context.addEventListener('statechange',()=>{if(!loading&&playback.suspendAudio()){stopLoop();log('audio-suspended');render();if(playback.recovery)startLoop();}});
  await Promise.all(clips.map(async c=>{const path=`../../site/${c.audio}`,response=await fetch(path);if(!response.ok)throw new Error(`${path}: HTTP ${response.status}`);buffers.set(c.id,await transport.context.decodeAudioData(await response.arrayBuffer()));}));
  face=createGeraldineAdapter($('face'),{now:()=>playback?.faceTime()??transport.time()*1000,reducedMotion:reduced});if(!await face.ready)throw new Error(face.snapshot().error||'The face atlas could not load');
  playback=new PreviewPlayback({face,transport});
  $('scene').replaceChildren(...scenes.map(s=>new Option(s.title,s.id)));$('scene').disabled=false;$('profiles').disabled=false;$('play').disabled=false;$('replay').disabled=false;
  scene=scenes[0];clip=clips.find(c=>c.id===scene.audio.clipId);loading=false;resetScene('ready');if(reduced)$('motion-note').textContent='Reduced motion: idle blinks and glances are off. Speech and expression changes play when started.';
  if(notes.length)$('saved').textContent=`${notes.length} saved ${notes.length===1?'moment':'moments'} restored. Export notes to review them.`;
  window.characterPreview={snapshot:()=>({version:VERSION,scene:scene.id,profile,epoch:playback.epoch,time:transport.time(),faceTimeMs:playback.faceTime(),audio:transport.sample(),face:face.snapshot(),running:transport.running,pending:transport.pending,recovering:!!playback.recovery,loopActive:timer!==null,sources:transport.nodes.size,events:[...events],notes:[...notes]}),interrupt,reset:()=>resetScene(),play};
}
init().catch(fail);
