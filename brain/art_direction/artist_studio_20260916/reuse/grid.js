'use strict';
const $=s=>document.querySelector(s),data=window.MIST_DATA;
let clock=0,lastWall=null,lastDraw=-Infinity,playing=!matchMedia('(prefers-reduced-motion: reduce)').matches;
let speaking=null,phaseStart=0,renderedFrames=0;
const sequence=['rest','MBP','AA','EH','EE','LNT','OO','OH','FV','S','rest','MBP','AA','SMILE','EH','OO','LNT','EE','rest','rest'];
const events=sequence.map((viseme,i)=>({time:i*.19,viseme,amount:.85}));
const faces=data.faces.map(face=>{
 const card=document.createElement('article');card.className='card';card.dataset.expression=face.id;
 const canvas=document.createElement('div');canvas.className='face';
 const label=document.createElement('div');label.className='label';
 const num=document.createElement('span');num.className='number';num.textContent=face.id.slice(0,2);
 const name=document.createElement('span');name.className='name';name.textContent=face.name.replaceAll('_',' ');
 label.append(num,name);card.append(canvas,label);$('#grid').append(card);
 const renderer=MistFaceRuntime.create(canvas,{data,expression:face.id,autoStart:false,reducedMotion:false,now:()=>clock});
 renderer.svg.setAttribute('aria-label',name.textContent);
 return renderer;
});
function draw(){
 const phase=clock%6000,wantsSpeech=$('#talk').checked&&phase<4100;
 if(wantsSpeech!==speaking){
  speaking=wantsSpeech;phaseStart=clock-phase;
  for(const face of faces){
   if(speaking)face.startSpeech({events,duration:4.1,clock:()=>Math.max(0,(clock-phaseStart)/1000)});
   else face.stopSpeech();
  }
 }
 for(const face of faces){if($('#gaze').checked)face.clearGaze();else face.setGaze(0,0);face.update(clock);}
 $('#phase').textContent=speaking?'Speaking':$('#talk').checked?'Rest between phrases':'Idle';
 $('#frame').textContent=`Frame ${renderedFrames++}`;
 lastDraw=clock;
}
function setPlaying(value){playing=value;$('#play').textContent=playing?'Pause':'Play';lastWall=null;}
$('#play').onclick=()=>setPlaying(!playing);
$('#step').onclick=()=>{setPlaying(false);clock+=1000/Number($('#fps').value);draw();};
$('#blink').onclick=()=>{for(const face of faces)face.blink();if(!playing)clock+=75;draw();};
$('#talk').onchange=()=>{speaking=null;draw();};
$('#gaze').onchange=draw;
$('#fps').onchange=()=>{lastDraw=-Infinity;};
$('#speed').onchange=()=>{lastWall=null;};
document.addEventListener('visibilitychange',()=>{lastWall=null;});
function tick(now){
 if(lastWall===null)lastWall=now;
 if(playing&&!document.hidden){clock+=Math.min(100,now-lastWall)*Number($('#speed').value);if(clock-lastDraw>=1000/Number($('#fps').value)-.1)draw();}
 lastWall=now;requestAnimationFrame(tick);
}
setPlaying(playing);draw();requestAnimationFrame(tick);
