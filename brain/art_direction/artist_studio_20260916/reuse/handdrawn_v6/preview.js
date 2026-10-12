(function(){
  'use strict';
  const $=id=>document.getElementById(id),cards=[],FPS=15,FRAME=1000/FPS;
  let time=0,lastWall=null,playing=true,selected=null,manifest=null,ready=false,held={},lastFrame=-1;
  const voice={context:null,playback:null,speech:null,samples:[],loading:false,generation:0,active:false};
  function setPlaying(value){playing=value;lastWall=null;$('play').textContent=$('inspect-play').textContent=value?'Pause':'Play';if(voice.active){if(value)voice.context?.resume();else voice.context?.suspend();}}
  function draw(){
    for(const item of cards){item.face.update(time);const state=item.face.renderTo(item.canvas,time);item.phase.textContent=state.handdrawn.activity?.phase||'Rest';}
    if(selected&&$('inspector').open){
      const state=selected.face.renderTo($('focus'),time),s=state.handdrawn;
      $('phase').textContent=`Original MIST eyes${s.activity?` / ${s.activity.phase} ${s.activity.frame+1}`:''}${state.speaking?' / voice':''}`;
      for(const [i,b]of [...$('activity-strip').children].entries())b.setAttribute('aria-pressed',String(i===s.activity?.frame));
    }
    lastFrame=Math.floor(time/FRAME+1e-7);
  }
  function step(){setPlaying(false);time+=FRAME;draw();}
  function blink(){for(const item of cards)item.face.blink();if(!playing)time+=FRAME;draw();}
  function replay(){for(const item of cards)item.face.setActivity(item.config.id,{owner:'preview',restart:true});draw();}
  function exit(){for(const item of cards)item.face.clearActivity();draw();}
  function inspect(id){
    if(selected)selected.face.inspect({});selected=cards.find(c=>c.config.id===id);held={};$('layers').value='all';
    $('inspect-name').textContent=selected.config.label;strips();$('inspector').showModal();draw();
  }
  function strips(){
    if(!selected)return;
    for(const [assetId,target]of [[selected.config.id,$('activity-strip')]]){
      target.replaceChildren();
      manifest.assets[assetId].frames.forEach((frame,index)=>{
        const b=document.createElement('button'),img=document.createElement('img'),caption=document.createElement('span');
        img.src=frame.file;img.alt='';caption.textContent=frame.pose.replaceAll('_',' ');b.append(img,caption);
        b.setAttribute('aria-label',`${assetId.replaceAll('_',' ')} ${caption.textContent}`);b.setAttribute('aria-pressed','false');
        b.onclick=()=>{held.activityFrame=index;selected.face.inspect({...held,layers:$('layers').value});draw();};target.append(b);
      });
    }
  }
  $('play').onclick=$('inspect-play').onclick=()=>setPlaying(!playing);
  $('step').onclick=$('inspect-step').onclick=step;$('blink').onclick=$('inspect-blink').onclick=blink;
  $('enter').onclick=replay;$('exit').onclick=exit;$('close').onclick=()=>$('inspector').close();
  $('inspector').onclose=()=>{selected?.face.inspect({});selected=null;held={};draw();};
  $('layers').onchange=()=>{selected?.face.inspect({...held,layers:$('layers').value});draw();};
  $('inspect-follow').onclick=()=>{held={};selected?.face.inspect({layers:$('layers').value});draw();};
  $('expression').onchange=()=>{for(const c of cards)c.face.setExpression($('expression').value||c.defaultFace);strips();draw();};
  for(const face of MIST_DATA.faces){const option=document.createElement('option');option.value=face.id;option.textContent=face.id.replace('_manual','').replaceAll('_',' ');$('expression').append(option);}
  function stopVoice(){
    voice.generation++;voice.active=false;voice.loading=false;voice.speech=null;voice.playback?.reset();
    for(const c of cards)c.face.stopSpeech();$('voice-play').disabled=!voice.samples.length;$('voice-stop').disabled=true;
    $('voice-status').textContent='Saved MIST voice';$('speed').disabled=false;draw();
  }
  async function playVoice(){
    if(voice.loading)return;stopVoice();const generation=voice.generation,stale=()=>generation!==voice.generation;
    const sample=voice.samples[Number($('voice-sample').value)];if(!sample)return;
    voice.loading=true;$('voice-play').disabled=true;$('voice-stop').disabled=false;$('voice-status').textContent='Loading recording';
    try{
      const {Playback}=await import('../runtime/playback.js?v=fps15-th');if(stale())return;
      voice.context??=new AudioContext();await voice.context.resume();if(stale())return;
      const response=await fetch('../drawn/audio/'+sample.file);if(!response.ok)throw new Error('Recording unavailable');
      const decoded=await voice.context.decodeAudioData(await response.arrayBuffer());if(stale())return;
      const channels=Array.from({length:decoded.numberOfChannels},(_,i)=>decoded.getChannelData(i)),pcm=new Int16Array(decoded.length);
      for(let i=0;i<pcm.length;i++)pcm[i]=Math.round(Math.max(-1,Math.min(1,channels.reduce((sum,c)=>sum+c[i],0)/channels.length))*32767);
      const bytes=new Uint8Array(pcm.buffer);let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
      const adapter={startSpeech(settings){voice.speech=settings;for(const c of cards)c.face.startSpeech(settings);},stopSpeech(){voice.speech=null;for(const c of cards)c.face.stopSpeech();}};
      voice.playback??=new Playback(voice.context,adapter,()=>{$('voice-status').textContent='Interrupted';},()=>{stopVoice();$('voice-status').textContent='Finished';});
      voice.active=true;$('speed').value='1';$('speed').disabled=true;setPlaying(true);
      voice.playback.append({epoch:voice.playback.epoch+1,pcm:btoa(binary),sample_rate:decoded.sampleRate,text:sample.text||'',alignment_source:'audio_energy'});
      $('voice-status').textContent='Recorded voice / mouth follows audio energy';
    }catch(e){if(stale())return;stopVoice();$('voice-status').textContent=e.message;}
    finally{if(!stale()){voice.loading=false;$('voice-play').disabled=false;}}
  }
  $('voice-play').onclick=playVoice;$('voice-stop').onclick=stopVoice;$('voice-sample').onchange=stopVoice;
  async function init(){
    try{
      const response=await fetch('manifest.json',{cache:'no-store'});if(!response.ok)throw new Error('Drawings unavailable');manifest=await response.json();
      MistHanddrawnRuntime.helpers.validateManifest(manifest);
      for(const [i,config]of manifest.activities.entries()){
        const button=document.createElement('button'),screen=document.createElement('div'),canvas=document.createElement('canvas'),label=document.createElement('div'),title=document.createElement('span'),phase=document.createElement('small');
        button.className='card';screen.className='screen';label.className='label';canvas.width=1000;canvas.height=640;canvas.setAttribute('aria-label',config.label+' animation');
        title.textContent=config.label;label.append(title,phase);screen.append(canvas);button.append(screen,label);$('grid').append(button);button.onclick=()=>inspect(config.id);
        const defaultFace={coding:'40_neutral_03_manual',reading:'39_neutral_02_manual',writing:'36_misc_03_manual',email:'11_happy_05_manual',searching:'20_neutral_06_manual',planning:'24_neutral_2_01_manual',calculating:'17_misc_2_01_manual',connecting:'11_happy_05_manual',checking:'36_misc_03_manual'}[config.id];
        const face=MistHanddrawnRuntime.create(null,{data:MIST_DATA,expression:defaultFace,manifest,manifestUrl:'manifest.json',atlasUrl:'../drawn/atlas.json',autoStart:false,reducedMotion:false,now:()=>time,seed:i});
        cards.push({config,face,canvas,phase,defaultFace});face.setActivity(config.id,{owner:'preview'});
      }
      const results=await Promise.all(cards.map(c=>c.face.ready));if(results.some(x=>!x))throw new Error(cards.find(c=>!c.face.loaded)?.face.error?.message||'Some drawings could not load');
      ready=true;replay();$('status').textContent='9 activities / original MIST eyes';draw();
    }catch(e){$('status').textContent='Could not load';$('error').hidden=false;$('error').textContent=e.message;console.error(e);}
  }
  async function initVoice(){
    try{const r=await fetch('../drawn/audio/samples.json');if(!r.ok)throw new Error();voice.samples=await r.json();$('voice-sample').replaceChildren();voice.samples.forEach((s,i)=>$('voice-sample').add(new Option(s.name||s.id,String(i))));$('voice-sample').value='1';$('voice-play').disabled=false;}
    catch{$('voice-sample').replaceChildren(new Option('Unavailable',''));}
  }
  function tick(wall){if(lastWall===null)lastWall=wall;if(playing&&!document.hidden){time+=Math.min(100,wall-lastWall)*Number($('speed').value);if(ready&&Math.floor(time/FRAME+1e-7)!==lastFrame)draw();}lastWall=wall;requestAnimationFrame(tick);}
  window.MistHanddrawnPreview={cards,voice,draw,step,blink,replay,exit,inspect,playVoice,stopVoice,get ready(){return ready;},get time(){return time;},get manifest(){return manifest;}};
  init();initVoice();requestAnimationFrame(tick);
})();
