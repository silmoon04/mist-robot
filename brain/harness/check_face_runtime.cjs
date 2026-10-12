const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const ctx={window:{}};vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root,'face_assets/app/app_data.js'),'utf8'),ctx);
const data=ctx.window.MIST_DATA;
const runtime=require('../ui/static/face_runtime.js');
let now=0,audioTime=0,checks=0,minGap=Infinity;
const renderer=runtime.create(null,{data,autoStart:false,now:()=>now});
function valid(state,label) {
  const b=state.bounds;
  assert(b.left>=5.49 && b.top>=5.49 && b.right<=94.51 && b.bottom<=58.51,label+' leaves safe region');
  for(const l of state.layers) {
    assert(l.points.every(p=>p.every(Number.isFinite)),label+' non-finite coordinates');
    assert(l.opacity>=0 && l.opacity<=1 && l.width>=0,label+' invalid style');
  }
  assert(state.layers.filter(l=>l.role==='mouth'&&l.opacity>.001).length<=1,label+' draws two mouths');
  checks++;
}
for(const face of data.faces) {
  renderer.setExpression(face.id,{durationMs:1});now+=2;renderer.update(now);
  valid(renderer.snapshot(now),face.id);
  for(const name of Object.keys(data.visemes)) {
    for(const [x,y] of [[-1,-1],[1,-1],[-1,1],[1,1],[0,0]]) {
      renderer.setGaze(x,y);audioTime=.5;
      renderer.startSpeech({events:[{time:0,viseme:name,amount:1}],duration:2,clock:()=>audioTime});
      now+=150;
      const s=renderer.update(now);valid(s,face.id+'/'+name);
      const mouth=s.layers.filter(l=>l.role==='mouth' && l.opacity>.1),eyes=s.layers.filter(l=>l.role.startsWith('eye'));
      const mb=runtime.bounds(mouth);
      assert(mb.left>=38 && mb.right<=62 && mb.top>=42 && mb.bottom<=57,face.id+' oversized speech mouth');
      for(const eye of eyes) {
        const eb=runtime.bounds([eye]);
        const gapX=Math.max(0,eb.left-mb.right,mb.left-eb.right);
        const gapY=Math.max(0,eb.top-mb.bottom,mb.top-eb.bottom);
        const gap=Math.hypot(gapX,gapY);
        minGap=Math.min(minGap,gap);
        assert(gap>.1,face.id+'/'+name+' mouth overlaps eye box');
      }
      renderer.stopSpeech();now+=150;renderer.update(now);
    }
  }
}
// Every expression pair is sampled while the audio clock is held steady.
for(const from of data.faces) {
  for(const to of data.faces) {
    renderer.setExpression(from.id,{durationMs:1});now+=2;renderer.update(now);
    renderer.setExpression(to.id,{durationMs:260});
    for(let i=0;i<9;i++) {
      now+=35;const s=renderer.update(now);valid(s,from.id+' -> '+to.id+' silent');
      if(from.slots.mouth && to.slots.mouth) assert(s.layers.find(l=>l.role==='mouth')?.opacity>=.99,'mouth vanishes between expressions');
    }
    renderer.setExpression(from.id,{durationMs:1});now+=2;renderer.update(now);
    audioTime=.25;renderer.startSpeech({events:[{time:0,viseme:'AA'}],duration:2,clock:()=>audioTime});
    now+=100;renderer.update(now);
    renderer.blink();renderer.setExpression(to.id,{durationMs:260});
    for(let i=0;i<9;i++) {
      now+=35;const s=renderer.update(now);valid(s,from.id+' -> '+to.id);
      assert.equal(s.expression,to.id);assert.equal(s.viseme,'AA');assert.equal(s.speechTime,.25);
    }
    assert.equal(renderer.expression,to.id,'blink restored an older expression');
    renderer.stopSpeech();now+=150;renderer.update(now);
  }
}
renderer.setExpression('39_neutral_02_manual',{durationMs:1});now+=2;renderer.update(now);
const neutral=renderer.snapshot(now).layers.find(l=>l.role==='mouth');
audioTime=0;
renderer.startSpeech({events:[{time:0,viseme:'AA'}],duration:1,clock:()=>audioTime});
const first=renderer.snapshot(now).layers.find(l=>l.role==='mouth');
assert.deepEqual(first.points,neutral.points,'speech start collapses the closed mouth');
for(let i=0;i<10;i++){audioTime=i*.015;now+=15;valid(renderer.snapshot(now),'speech entry '+i);}
audioTime=.2;now+=100;renderer.update(now);
const paused=renderer.snapshot(now).layers.filter(l=>l.role==='mouth');
now+=100;const still=renderer.snapshot(now).layers.filter(l=>l.role==='mouth');
// Compare before presentation gaze/breath transforms via reduced-motion instance.
const frozen=runtime.create(null,{data,autoStart:false,reducedMotion:true,now:()=>now});
frozen.startSpeech({events:[{time:0,viseme:'AA'},{time:.4,viseme:'OO'}],duration:1,clock:()=>audioTime});
now+=100;const p=frozen.snapshot(now).layers.filter(l=>l.role==='mouth');
now+=500;assert.deepEqual(frozen.snapshot(now).layers.filter(l=>l.role==='mouth'),p,'mouth drifts while audio is paused');
audioTime=2;assert.equal(frozen.snapshot(now).viseme,'rest','audio completion leaves mouth open');
frozen.stopSpeech();now+=150;assert.equal(frozen.snapshot(now).speaking,false);
assert.equal(renderer.setExpression('unknown'),false);
console.log(JSON.stringify({passed:true,statesChecked:checks,expressionPairs:1600,faces:40,visemes:11,
  minEyeMouthBoxGap:minGap,checks:['safe bounds','all expression speech poses','all expression pairs during speech',
    'blink interruption','closed-mouth preservation','single mouth during transitions','audio pause','audio completion','invalid expression']},null,2));

if(process.argv.includes('--export')) {
  const out=path.resolve(root,'../design/mist_v2_20260906/brain_v2_20260907/faces');
  fs.mkdirSync(out,{recursive:true});
  const frames=[],tags=[];now=0;
  const r=runtime.create(null,{data,autoStart:false,now:()=>now});
  function add(label,durationMs=65) {
    const state=r.update(now);
    frames.push({label,durationMs,expression:state.expression,viseme:state.viseme,
      layers:state.layers.map(l=>({...l,role:l.role.startsWith('eye')?'eyes':l.role.startsWith('tear')?'tears':l.role}))});
  }
  for(const face of data.faces) {
    r.setExpression(face.id,{durationMs:260});const from=frames.length;
    for(let i=0;i<5;i++){add(face.id+' transition '+i);now+=65;}
    r.blink();for(let i=0;i<4;i++){add(face.id+' blink '+i);now+=65;}
    add(face.id+' settled',650);now+=650;
    tags.push({name:face.id.replace('_manual',''),from,to:frames.length-1,direction:'forward'});
  }
  const from=frames.length;r.setExpression('39_neutral_02_manual',{durationMs:1});now+=2;
  r.startSpeech({events:Object.keys(data.visemes).map((v,i)=>({time:i*.26,viseme:v})),duration:3,clock:()=>audioTime});
  for(let i=0;i<46;i++){audioTime=i*.065;add('speech '+audioTime.toFixed(3));now+=65;}
  r.stopSpeech();for(let i=0;i<4;i++){add('speech release '+i);now+=65;}
  tags.push({name:'speech_shapes',from,to:frames.length-1,direction:'forward'});
  fs.writeFileSync(path.join(out,'animation_frames.json'),JSON.stringify({width:100,height:64,scale:4,
    color:'#5eeadd',background:'#07090c',layerOrder:['eyes','mouth','tears'],frames,tags}));
  const settled=data.faces.map(f=>{r.setExpression(f.id,{durationMs:1});now+=1000;return {...r.update(now),label:f.id};});
  fs.writeFileSync(path.join(out,'settled_frames.json'),JSON.stringify(settled));
  console.log('Exported '+frames.length+' animation frames and '+settled.length+' settled frames to '+out);
}
