// Runs the checked-in legacy geometry without a browser or wall-clock timers.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const brain = path.resolve(__dirname, '../../../../brain');
const elements = new Map();
const document = {getElementById(id) {
  if (!elements.has(id)) elements.set(id, {setAttribute(){},addEventListener(){}, style:{}, value:400, classList:{toggle(){}}});
  return elements.get(id);
}, querySelectorAll(){return []}};
const timers=[];
const ctx = {window:{addEventListener(){}},document,performance:{now:()=>0},__timers:timers,
  setTimeout(fn){timers.push(fn);},clearTimeout(){},requestAnimationFrame(){},console,URLSearchParams,
  location:{hash:''},navigator:{},innerWidth:1000,innerHeight:640};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(brain,'face_assets/app/app_data.js'),'utf8'),ctx);
const html=fs.readFileSync(path.join(__dirname,'legacy_before.html'),'utf8');
const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1].split('buildButtons();')[0];
vm.runInContext(script,ctx);
const result=vm.runInContext(`(() => {
  const f=D.faces.find(f=>f.id.startsWith('39'));
  applyFace(f,1); for(const ch of Object.values(chans)) tickChannel(ch,2);
  const before=chans.mouth.cur;
  const bounds=s=>({width:Math.max(...s.pts.map(p=>p[0]))-Math.min(...s.pts.map(p=>p[0]))+s.width,
    height:Math.max(...s.pts.map(p=>p[1]))-Math.min(...s.pts.map(p=>p[1]))+s.width});
  const initial=bounds(before);
  retarget(chans.mouth,visemeState('AA',talkAnchor()),80);
  tickChannel(chans.mouth,0);
  const first=bounds(chans.mouth.cur);
  const aa=visemeState('AA',{x:50,y:49},1.14);
  const maxY=Math.max(...aa.pts.map(p=>p[1]))+2.2;
  doBlink();
  applyFace(D.faces.find(f=>f.id.startsWith('04')),1);
  for(const ch of Object.values(chans))tickChannel(ch,2);
  const newExpressionEye=bounds(chans.eye_L.cur);
  __timers.shift()();
  for(const ch of Object.values(chans))tickChannel(ch,200);
  const afterBlinkCallback=bounds(chans.eye_L.cur);
  return {initial,first,speakingMaxYWithGaze:maxY,newExpressionEye,afterBlinkCallback,
    checks:{mouthRetainsThickness:first.height>=initial.height*.8,glowMargin:maxY<=61,
      blinkRetainsNewExpression:Math.abs(newExpressionEye.height-afterBlinkCallback.height)<.01}};
})()`,ctx);
console.log(JSON.stringify(result,null,2));
process.exitCode=Object.values(result.checks).every(Boolean)?0:1;
