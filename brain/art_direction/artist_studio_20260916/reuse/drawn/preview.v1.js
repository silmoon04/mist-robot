'use strict';
(() => {
 const $=s=>document.querySelector(s),data=window.MIST_DATA,audit=window.REUSE_AUDIT;
 const familyIds={'Round gap':'round','Hooked lid':'hook','Arc':'arc','Loop with crossbar':'loop','Narrow slot':'slot','Chevron':'chevron','Flat bar':'bar'};
 const blinkNames=['Rest','Ready','Lowering','Closed','Opening','Settled'];
 const mouthNames=['rest','MBP','small AA','AA','EH','EE','OH','OO','FV','LNT','S','SMILE'];
 const partFamily={};for(const [name,parts] of Object.entries(audit.motion_families))for(const part of parts)partFamily[part]=familyIds[name];
 const references={round:'circle_gap_03',hook:'angry_hook_00',arc:'happy_arc_16',loop:'e_shape_12',slot:'open_C_44',chevron:'chevron_01',bar:'flat_bar_14'};
 // Fit the family drawing once to each canonical eye, before the face's own placement.
 function resample(part){const points=part.points.slice();if(part.kind==='fill')points.push(points[0]);const lengths=[0];for(let i=1;i<points.length;i++)lengths.push(lengths.at(-1)+Math.hypot(points[i][0]-points[i-1][0],points[i][1]-points[i-1][1]));const result=[];for(let n=0;n<64;n++){const t=lengths.at(-1)*n/(part.kind==='fill'?64:63);let i=1;while(i<lengths.length-1&&lengths[i]<t)i++;const amount=(t-lengths[i-1])/(lengths[i]-lengths[i-1]||1);result.push([points[i-1][0]+(points[i][0]-points[i-1][0])*amount,points[i-1][1]+(points[i][1]-points[i-1][1])*amount]);}const mean=[0,1].map(axis=>result.reduce((s,p)=>s+p[axis],0)/result.length);return result.map(p=>[p[0]-mean[0],p[1]-mean[1]]);}
 function align(source,target){const a=resample(source),b=resample(target);let best={score:Infinity,rotation:0,mirror:false};for(const mirror of [false,true])for(const reverse of [false,true])for(let shift=0;shift<(source.kind==='fill'?64:1);shift+=4){let dot=0,cross=0;for(let i=0;i<a.length;i++){const p=[a[i][0]*(mirror?-1:1),a[i][1]],q=b[((reverse?63-i:i)+shift)%64];dot+=p[0]*q[0]+p[1]*q[1];cross+=p[0]*q[1]-p[1]*q[0];}const angle=Math.atan2(cross,dot),c=Math.cos(angle),s=Math.sin(angle);let score=0;for(let i=0;i<a.length;i++){const x=a[i][0]*(mirror?-1:1),y=a[i][1],q=b[((reverse?63-i:i)+shift)%64];score+=(c*x-s*y-q[0])**2+(s*x+c*y-q[1])**2;}score+=Math.abs(angle)*1e-8+(mirror?1e-8:0);if(score<best.score)best={score,rotation:angle,mirror};}return best;}
 const alignments={};for(const [part,family]of Object.entries(partFamily))alignments[part]=align(data.parts[references[family]],data.parts[part]);
 let atlas,ready=false,time=0,lastWall=null,lastDraw=-Infinity,playing=!matchMedia('(prefers-reduced-motion: reduce)').matches,manualBlink=-1e9,selected=0,heldEye=null,heldMouth=null;
 const loaded={},faces=[];
 const events=['rest','MBP','AA','EH','EE','LNT','OO','OH','FV','S','rest','MBP','AA','SMILE','EH','OO','LNT','EE','rest','rest'].map((viseme,i)=>({time:i*.19,viseme,amount:.8}));
 const speechPattern=[0,1,2,3,3,4,5,9,1,7,7,6,8,10,0,0,1,2,3,4,11,11,5,9,1,7,6,9,5,0,0,0,0,0,0,0,0,0,0,0];
 function box(points,pad=0){const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);const x=Math.min(...xs)-pad,y=Math.min(...ys)-pad;return{x,y,w:Math.max(...xs)+pad-x,h:Math.max(...ys)+pad-y};}
 function label(face){return face.name.replaceAll('_',' ');}
 for(const [index,face] of data.faces.entries()){
  const slots={};for(const group of audit.groups)for(const use of group.uses)if(use.face===face.id)slots[use.role]={...use};
  const card=document.createElement('button');card.className='card';card.dataset.expression=face.id;card.setAttribute('aria-label',`Inspect ${label(face)}`);
  const canvas=document.createElement('canvas');canvas.width=500;canvas.height=320;
  const caption=document.createElement('span');caption.className='label';const num=document.createElement('span');num.className='number';num.textContent=face.id.slice(0,2);const name=document.createElement('span');name.className='name';name.textContent=label(face);caption.append(num,name);card.append(canvas,caption);$('#grid').append(card);
  const original=MistFaceRuntime.create(null,{data,expression:face.id,autoStart:false,reducedMotion:false,now:()=>time});
  const staticRenderer=MistFaceRuntime.create(null,{data,expression:face.id,autoStart:false,reducedMotion:true,now:()=>0});
  const staticLayers=staticRenderer.snapshot(0).layers;staticRenderer.destroy();
  faces.push({face,index,slots,canvas,original,staticLayers,speechPhase:-1});
  card.onclick=()=>openInspector(index);
 }
 function paintLayer(ctx,layer){if(!layer.points.length)return;ctx.save();ctx.globalAlpha=layer.opacity??1;ctx.fillStyle=ctx.strokeStyle='#5eeadd';ctx.lineWidth=layer.width||1;ctx.lineCap='round';ctx.lineJoin='round';const path=new Path2D(MistFaceRuntime.pathData(layer.points,layer.mode==='fill'));if(layer.mode==='fill')ctx.fill(path);else ctx.stroke(path);ctx.restore();}
 function keySheet(img){
  const canvas=document.createElement('canvas');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(img,0,0);
  const pixels=ctx.getImageData(0,0,canvas.width,canvas.height),p=pixels.data;let transparent=0,white=0;
  for(let n=0;n<p.length;n+=400){if(p[n+3]<30)transparent++;else if(Math.min(p[n],p[n+1],p[n+2])>235)white++;}
  if(white>transparent){
   for(let n=0;n<p.length;n+=4){const low=Math.min(p[n],p[n+1],p[n+2]),high=Math.max(p[n],p[n+1],p[n+2]);if(high-low<22){p[n+3]=0;continue;}const alpha=Math.min(1,(255-low)/161);if(alpha<.035){p[n+3]=0;continue;}for(let c=0;c<3;c++)p[n+c]=Math.max(0,Math.min(255,(p[n+c]-255*(1-alpha))/alpha));p[n+3]*=alpha;}
   ctx.putImageData(pixels,0,0);
  }
  return canvas;
 }
 function drawAsset(ctx,id,frameIndex,scaleX,scaleY=scaleX){
  const asset=atlas.assets[id],f=asset.frames[frameIndex],sheet=loaded[id];if(!f||!sheet)return;
  const cx=f.cx??(f.x+f.w/2),cy=f.cy??(f.y+f.h/2);
  ctx.drawImage(sheet,f.x,f.y,f.w,f.h,(f.x-cx)*scaleX,(f.y-cy)*scaleY,f.w*scaleX,f.h*scaleY);
 }
 function dimensions(id){const a=atlas.assets[id],f=a.frames[0];return{w:a.masterWidth||f.w,h:a.masterHeight||f.h};}
 function blinkFrame(item){
  let elapsed=time-manualBlink;
  if(elapsed<0||elapsed>=375){const offset=$('#sync').checked?0:(item.index*887)%4200;elapsed=(time+offset)%5400-3700;}
  // Hold the closed cel for one full 8 fps interval so each blink reads.
  if(elapsed<0||elapsed>=375)return 0;
  if(elapsed<30)return 1;if(elapsed<80)return 2;if(elapsed<205)return 3;if(elapsed<330)return 4;return 5;
 }
 function speechStep(item){return(Math.floor(time/125)+($('#sync').checked?0:item.index*3))%speechPattern.length;}
 function mouthFrame(item){return speechPattern[speechStep(item)];}
 function mouthAsset(item){return /happy|love/.test(item.face.id)||['09','10','11','12','13','14','37'].includes(item.face.id.slice(0,2))?'mouth_smile':'mouth_neutral';}
 function drawFace(item,canvas,inspection=false){
  const ctx=canvas.getContext('2d');ctx.setTransform(canvas.width/100,0,0,canvas.height/64,0,0);ctx.clearRect(0,0,100,64);ctx.fillStyle='#101c20';ctx.fillRect(0,0,100,64);
  if($('#mode').value==='original'){
   const phase=Math.floor(time/5000),speak=$('#talk').checked&&time%5000<4000;
   if(speak&&item.speechPhase!==phase){item.original.startSpeech({events,duration:4,clock:()=>time%5000/1000});item.speechPhase=phase;}else if(!speak){item.original.stopSpeech();item.speechPhase=-1;}
   item.original.setGaze($('#gaze').checked?Math.sin(time/1700)*.4:0,$('#gaze').checked?Math.sin(time/2400)*.22:0);item.original.update(time);for(const layer of item.original.snapshot(time).layers)paintLayer(ctx,layer);return;
  }
  if(!ready)return;
  const blink=inspection&&heldEye!==null?heldEye:blinkFrame(item),gx=$('#gaze').checked?Math.sin(time/1700)*.65:0,gy=$('#gaze').checked?Math.sin(time/2400)*.35:0;
  for(const role of ['eye_L','eye_R']){
   const slot=item.slots[role];if(!slot)continue;const id=partFamily[slot.part];if(!id)continue;const original=data.parts[slot.part],bounds=box(original.points,(original.width||0)/2),master=dimensions(id),fit=alignments[slot.part];
   const rotatedWidth=Math.abs(Math.cos(fit.rotation))*master.w+Math.abs(Math.sin(fit.rotation))*master.h,rotatedHeight=Math.abs(Math.sin(fit.rotation))*master.w+Math.abs(Math.cos(fit.rotation))*master.h;
   const scale=Math.min(bounds.w/rotatedWidth,bounds.h/rotatedHeight);
   ctx.save();ctx.translate(slot.x+gx,slot.y+gy);ctx.rotate((slot.rot||0)*Math.PI/180);ctx.scale(slot.mirror?-1:1,1);ctx.translate(bounds.x+bounds.w/2,bounds.y+bounds.h/2);ctx.rotate(fit.rotation);ctx.scale(fit.mirror?-1:1,1);ctx.translate(0,master.h*scale/2);drawAsset(ctx,id,blink,scale);ctx.restore();
  }
  for(const layer of item.staticLayers)if(!layer.role.startsWith('eye')&&layer.role!=='mouth')paintLayer(ctx,layer);
  if(($('#talk').checked&&speechStep(item)<32)||(inspection&&heldMouth!==null)){
   const id=mouthAsset(item),master=dimensions(id),frame=inspection&&heldMouth!==null?heldMouth:mouthFrame(item);
   const widest=Math.max(master.w,...atlas.assets[id].frames.map(f=>f.w));
   ctx.save();ctx.translate(50,46.5);drawAsset(ctx,id,frame,22/widest);ctx.restore();
  }else for(const layer of item.staticLayers)if(layer.role==='mouth')paintLayer(ctx,layer);
 }
 function draw(){for(const item of faces)drawFace(item,item.canvas);if($('#inspect').open){const item=faces[selected];drawFace(item,$('#focus'),true);const bf=heldEye??blinkFrame(item),mf=heldMouth??mouthFrame(item);$('#phase').textContent=`${blinkNames[bf]} / ${$('#talk').checked||heldMouth!==null?mouthNames[mf]:'Rest'}`;$('#eye-strip').querySelectorAll('button').forEach((b,i)=>b.classList.toggle('selected',i===bf));$('#mouth-strip').querySelectorAll('button').forEach((b,i)=>b.classList.toggle('selected',i===mf&&($('#talk').checked||heldMouth!==null)));}lastDraw=time;}
 function strip(container,id,names,type){
  container.replaceChildren();const master=dimensions(id),asset=atlas.assets[id],maxWidth=Math.max(master.w,...asset.frames.map(f=>f.w)),maxHeight=Math.max(master.h,...asset.frames.map(f=>f.h));
  for(const [index,name]of names.entries()){
   const button=document.createElement('button');button.title=`Hold ${name}`;const canvas=document.createElement('canvas');canvas.width=180;canvas.height=120;const ctx=canvas.getContext('2d');ctx.fillStyle='#101c20';ctx.fillRect(0,0,180,120);const scale=Math.min(120/maxWidth,80/maxHeight);ctx.translate(90,60+(type==='eye'?1:-1)*maxHeight*scale/2);drawAsset(ctx,id,index,scale);const text=document.createElement('span');text.textContent=name;button.append(canvas,text);button.onclick=()=>{if(type==='eye')heldEye=index;else heldMouth=index;draw();};container.append(button);
  }
 }
 function populateStrips(){if(!ready)return;const item=faces[selected],slot=item.slots[$('#eye-side').value],family=partFamily[slot.part],mouth=mouthAsset(item);$('#family-label').textContent=`${family} / ${slot.part}`;$('#mouth-label').textContent=mouth==='mouth_smile'?'Smile':'Neutral';strip($('#eye-strip'),family,blinkNames,'eye');strip($('#mouth-strip'),mouth,mouthNames,'mouth');}
 function openInspector(index){if(!ready)return;selected=index;heldEye=heldMouth=null;$('#focus-name').textContent=`${faces[index].face.id.slice(0,2)} / ${label(faces[index].face)}`;populateStrips();$('#inspect').showModal();draw();}
 function setPlaying(value){playing=value;$('#play').textContent=$('#focus-play').textContent=playing?'Pause':'Play';lastWall=null;}
 function step(){setPlaying(false);time+=1000/Number($('#fps').value);draw();}
 function blink(){heldEye=null;manualBlink=time;for(const item of faces)item.original.blink();if(!playing)time+=125;draw();}
 $('#play').onclick=$('#focus-play').onclick=()=>setPlaying(!playing);$('#step').onclick=$('#focus-step').onclick=step;$('#blink').onclick=$('#focus-blink').onclick=blink;
 $('#close').onclick=()=>$('#inspect').close();$('#eye-side').onchange=populateStrips;$('#resume-cels').onclick=()=>{heldEye=heldMouth=null;draw();};
 for(const id of ['talk','gaze','sync','mode'])$('#'+id).onchange=draw;$('#fps').onchange=()=>lastDraw=-Infinity;$('#speed').onchange=()=>lastWall=null;
 document.addEventListener('visibilitychange',()=>lastWall=null);
 function tick(now){if(lastWall===null)lastWall=now;if(playing&&!document.hidden){time+=Math.min(100,now-lastWall)*Number($('#speed').value);if(time-lastDraw>=1000/Number($('#fps').value)-.1)draw();}lastWall=now;requestAnimationFrame(tick);}
 async function init(){
  try{
   const response=await fetch('atlas.json',{cache:'no-store'});if(!response.ok)throw new Error(`Atlas: HTTP ${response.status}`);atlas=await response.json();
   const required=['round','hook','arc','loop','slot','chevron','bar','mouth_neutral','mouth_smile'];for(const id of required)if(!atlas.assets[id]||atlas.assets[id].frames.length!==(id.startsWith('mouth')?12:6))throw new Error(`Missing drawings: ${id}`);
   await Promise.all(required.map(async id=>{const image=new Image();image.src=atlas.assets[id].file;await image.decode();loaded[id]=keySheet(image);}));
   for(const item of faces)for(const role of ['eye_L','eye_R'])if(!partFamily[item.slots[role]?.part])throw new Error(`Unmapped eye: ${item.face.id} ${role}`);
   ready=true;$('#status').textContent='40 faces / 7 eye families / 2 mouth sets';draw();
  }catch(error){$('#status').textContent='Drawings unavailable';$('#error').hidden=false;$('#error').textContent=`Could not load the generated sheets. ${error.message} Refresh once the asset export is complete.`;console.error(error);}
 }
 window.MistDrawnPreview={get ready(){return ready;},get time(){return time;},faces,partFamily,alignments,draw,step,blink,openInspector,get atlas(){return atlas;}};
 setPlaying(playing);draw();requestAnimationFrame(tick);init();
})();
