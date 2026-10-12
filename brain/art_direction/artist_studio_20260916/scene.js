/* Existing MIST assets, rendered by the existing animation engine. */
(function(root){
let data,renderer;
if(typeof module!=='undefined'){
 const fs=require('fs'),path=require('path'),vm=require('vm'),scope={window:{}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'existing/app_data.js'),'utf8'),scope);
 data=scope.window.MIST_DATA;renderer=require('./existing/face_runtime.js');
}else{data=root.MIST_DATA;renderer=root.MistFaceRuntime;}
const definitions=[
 ['available','Available','State',true,'round',72,['neutral 39','happy 12'],['39_neutral_02_manual','12_happy_09_manual']],
 ['listening','Listening','State',false,'round',48,['listening 25','alert 24','attentive 07'],['25_neutral_2_03_manual','24_neutral_2_01_manual','07_annoyed_03_manual']],
 ['thinking','Thinking','State',false,'focused',72,['neutral 39','focused 40','variant 18'],['39_neutral_02_manual','40_neutral_03_manual','18_misc_2_02_manual']],
 ['happy','Happy','Speaking',true,'happy',48,['happy 09'],['09_happy_03_manual']],
 ['focused','Focused','Speaking',true,'focused',48,['focused 40'],['40_neutral_03_manual']],
 ['concerned','Concerned','Speaking',true,'soft',48,['sad 32'],['32_sad_07_manual']],
 ['surprised','Surprised','Reaction',false,'wide',12,['surprised 38'],['38_misc_2_06_manual']],
 ['sleepy','Sleepy','Reaction',false,'heavy',12,['sleepy 16'],['16_misc_16_manual']],
 ['skeptical','Skeptical','Reaction',false,'focused',12,['suspicious 08'],['08_annoyed_04_manual']],
 ['delighted','Delighted','Reaction',false,'happy',12,['happy 13'],['13_happy_14_manual']]
];
const states=definitions.map(([id,name,kind,talk,family,frames,options,sources])=>{const face=data.faces.find(f=>f.id===sources[0]);return{id,name,kind,talk,family,frames,options,sources,eyes:face.slots.eye_L?.part||'none',mouth:face.slots.mouth?.part||'none',note:'Existing face geometry. '+(id==='thinking'?'Current thinking gaze.':kind==='Reaction'?'Brief hold.':'')};});
const families=['round','happy','focused','soft','heavy','wide'];
const familyFace={round:'39_neutral_02_manual',happy:'09_happy_03_manual',focused:'40_neutral_03_manual',soft:'32_sad_07_manual',heavy:'16_misc_16_manual',wide:'38_misc_2_06_manual'};
const cache=new Map();
function render(settings={}){
 const key=JSON.stringify(settings);if(cache.has(key))return cache.get(key);
 const s=states.find(s=>s.id===settings.state)||states[0],mode=settings.mode||'state',frame=Math.max(0,settings.frame||0),index=Math.max(0,s.options.indexOf(settings.option)),id=settings.family?familyFace[settings.family]:s.sources[index];
 let now=0;const face=renderer.create(null,{data,expression:mode==='transition'?'39_neutral_02_manual':id,autoStart:false,now:()=>now,reducedMotion:false});
 if(mode==='transition')face.setExpression(id,{durationMs:260});
 if(mode==='blink')face.blink();
 if(s.id==='thinking'&&mode==='state')face.setGaze(-.55,-.3);
 if(mode==='speech'&&s.talk)face.startSpeech({duration:2,clock:()=>now/1000,events:Array.from({length:16},(_,i)=>({time:i*.125,viseme:settings.viseme&&settings.viseme!=='cycle'?settings.viseme:['rest','MBP','AA','EE','OO','AA','rest','MBP'][i%8],amount:.8}))});
 for(let t=0;t<frame*1000/24;t+=1000/60){now=t;face.update(now);}now=frame*1000/24;const snapshot=face.update(now);
 const paths=snapshot.layers.filter(l=>!(settings.eyes===false&&l.role.startsWith('eye'))&&!(settings.mouth===false&&l.role==='mouth')).map(l=>`<path data-role="${l.role}" data-part="${l.part}" d="${renderer.pathData(l.points,l.mode==='fill')}" fill="${l.mode==='fill'?'#5eeadd':'none'}" stroke="${l.mode==='stroke'?'#5eeadd':'none'}" stroke-width="${l.width}" stroke-linecap="round" stroke-linejoin="round" opacity="${l.opacity}"/>`).join('');
 const guides=settings.guides?'<path d="M50 4V60M5 29H95M5 48H95" stroke="#ffffff19" stroke-width=".3"/>':'';
 const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 64" width="800" height="512" role="img" aria-label="${s.name} existing face" data-source="${id}"><title>${id}, existing renderer, frame ${frame}</title>${settings.background===false?'':'<rect width="100" height="64" fill="#101917"/>'}${guides}${paths}</svg>`;
 if(cache.size>256)cache.clear();cache.set(key,svg);return svg;
}
const api={states,families,render,data};if(typeof module!=='undefined')module.exports=api;else root.MistScenes=api;
})(typeof window==='undefined'?globalThis:window);
