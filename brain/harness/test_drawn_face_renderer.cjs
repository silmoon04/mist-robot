'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const crypto=require('node:crypto');
const ROOT=path.resolve(__dirname,'../..');
const dataContext={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(ROOT,'brain/face_assets/app/app_data.js'),'utf8'),dataContext);
const data=dataContext.window.MIST_DATA;
const runtime=require('../ui/static/face_runtime.js');
const drawn=require('../ui/static/drawn_face_renderer.js');
const atlas=JSON.parse(fs.readFileSync(path.join(ROOT,'brain/art_direction/artist_studio_20260916/reuse/drawn/atlas.json'),'utf8'));
const images=Object.fromEntries(Object.keys(atlas.assets).map(id=>[id,{}]));
for(const asset of Object.values(atlas.assets)) {
  images[asset.file]=images[asset.id];
  for(const frame of asset.frames)if(frame.file)images[frame.file]??={};
}
const dimensions=asset=>({w:asset.masterWidth||asset.frames[0].w,h:asset.masterHeight||asset.frames[0].h});
const rotate=(point,angle)=>[Math.cos(angle)*point[0]-Math.sin(angle)*point[1],Math.sin(angle)*point[0]+Math.cos(angle)*point[1]];
function mouthCorners(p,frame) {
  const cx=frame.cx??frame.x+frame.w/2,cy=frame.cy??frame.y+frame.h/2;
  return [[frame.x,frame.y],[frame.x+frame.w,frame.y],[frame.x,frame.y+frame.h],[frame.x+frame.w,frame.y+frame.h]].map(([x,y])=> {
    const sourceScale=frame.sourceScale??1;
    const result=rotate([(x-cx)*sourceScale*p.scale*p.mirror,((y-cy)*sourceScale-p.master.h/2)*p.scale],p.rotation);
    return [result[0]+p.x,result[1]+p.y];
  });
}

(async()=> {
  let time=0,audio=0,sampleCalls=0;
  const face=drawn.create(null,{data,runtime,atlas,images,now:()=>time,autoStart:false,reducedMotion:true});
  assert.equal(await face.ready,true);
  face.startSpeech({events:[{time:0,viseme:'MBP'},{time:.15,viseme:'AA'},{time:.7,viseme:'OO'}],duration:1,clock:()=>audio});
  assert.equal(face.snapshot().viseme,'MBP');
  time=5000;assert.equal(face.snapshot().viseme,'MBP','wall time must not advance speech');
  audio=.3;assert.equal(face.snapshot().viseme,'AA');
  audio=.8;assert.equal(face.snapshot().viseme,'OO');
  assert.equal(face.snapshot().drawnPlacements.find(p=>p.role==='mouth').frame,atlas.assets.mouth_neutral.frames.findIndex(f=>f.pose==='OO'));
  face.stopSpeech();assert.equal(face.snapshot().drawnPlacements.some(p=>p.role==='mouth'),false);

  let sample={active:false,viseme:'AA',amount:.7,time:0,source:'alignment'};
  face.startSpeech({events:[],duration:Infinity,clock:()=>audio,sample:()=>{sampleCalls++;return sample;}});
  assert.equal(face.snapshot().drawnPlacements.some(p=>p.role==='mouth'),false,'pre-roll remains closed');
  sample={...sample,active:true,viseme:'OO',time:.4};
  assert.equal(face.update().viseme,'OO');assert.equal(face.snapshot().speechTime,.4);assert.equal(face.snapshot().syncSource,'alignment');
  sample={...sample,active:false};assert.equal(face.update().drawnPlacements.some(p=>p.role==='mouth'),false,'audio gaps restore original rest');
  sample={...sample,active:true};face.stopSpeech();assert.equal(face.snapshot().speaking,false,'cancel clears stale sampler');
  assert(sampleCalls>=4,'sampler must be read continuously');

  let mouthChecks=0,eyeChecks=0,eyeCornerChecks=0,readableSpeechChecks=0;
  for(const expression of data.faces) {
    face.setExpression(expression.id,{durationMs:1});time+=2;
    const staticFace=runtime.create(null,{data,expression:expression.id,autoStart:false,reducedMotion:true});
    const original=staticFace.snapshot().layers.find(layer=>layer.role==='mouth');
    const xs=original?.points.map(p=>p[0]),ys=original?.points.map(p=>p[1]);
    const originalCenter=original?[(Math.min(...xs)+Math.max(...xs))/2,(Math.min(...ys)+Math.max(...ys))/2]:null;
    sample={active:true,viseme:'AA',amount:1,time:.25,source:'fixture'};
    face.startSpeech({sample:()=>sample,clock:()=>.25,duration:Infinity});
    const state=face.snapshot(),mouth=state.drawnPlacements.find(p=>p.role==='mouth');
    if(original) {
      assert(mouth,expression.id+' has a mouth placement');
      assert(Math.abs(mouth.x-originalCenter[0])<1e-8 && Math.abs(mouth.y-originalCenter[1])<1e-8,'mouth stays at original expression center: '+expression.id);
      for(const frame of atlas.assets[mouth.id].frames) for(const [x,y] of mouthCorners(mouth,frame)) {
        assert(x>=6-1e-6 && x<=94+1e-6 && y>=6-1e-6 && y<=58+1e-6,expression.id+' mouth crop fits viewport');mouthChecks++;
      }
    } else {
      assert(!mouth,'A mouthless expression keeps its original character');
    }
    if(expression.id.startsWith('20_')||expression.id.startsWith('40_')) {
      for(const [viseme,minimum] of [['AA',5],['LNT',5],['FV',5.7],['TH',5.4]]) {
        sample={...sample,viseme};const p=face.snapshot().drawnPlacements.find(item=>item.role==='mouth');
        const frame=atlas.assets[p.id].frames[p.frame],ink=frame.inkBounds||frame,width=ink.w*(frame.sourceScale??1)*p.scale;
        assert(width>=minimum,expression.id+' '+viseme+' remains readable during speech');
        assert(Math.abs(p.master.w*p.scale-8)<1e-8,'Small rest dots use one bounded 8-unit speech master width');
        readableSpeechChecks++;
      }
    }
    const eyes=state.drawnPlacements.filter(p=>p.role.startsWith('eye'));
    assert.equal(eyes.length,2,expression.id+' maps both eyes');
    for(const eye of eyes) {
      assert(Number.isFinite(eye.scale)&&eye.scale>0);const asset=atlas.assets[eye.id];
      const slot=eye.slot,part=data.parts[slot.part],angle=(slot.rot||0)*Math.PI/180;
      const raw=part.points.map(([x,y])=>{const p=rotate([x*(slot.mirror?-1:1),y],angle);return[p[0]+slot.x,p[1]+slot.y];});
      const prepared=staticFace.snapshot().layers.find(layer=>layer.role===eye.role);
      const scale=Math.hypot(prepared.points[1][0]-prepared.points[0][0],prepared.points[1][1]-prepared.points[0][1])/Math.hypot(raw[1][0]-raw[0][0],raw[1][1]-raw[0][1]);
      const shift=[prepared.points[0][0]-raw[0][0]*scale,prepared.points[0][1]-raw[0][1]*scale];
      for(const frame of asset.frames) {
        assert(frame.w>0&&frame.h>0);eyeChecks++;
        const cx=frame.cx??frame.x+frame.w/2,cy=frame.cy??frame.y+frame.h/2;
        for(const [x,y] of [[frame.x,frame.y],[frame.x+frame.w,frame.y],[frame.x,frame.y+frame.h],[frame.x+frame.w,frame.y+frame.h]]) {
          let p=[(x-cx)*eye.scale*(eye.fit.mirror?-1:1),(y-cy+eye.master.h/2)*eye.scale];
          p=rotate(p,eye.fit.rotation);p=[p[0]+eye.box.x+eye.box.w/2+eye.inkOffset.x*eye.scale,p[1]+eye.box.y+eye.box.h/2+eye.inkOffset.y*eye.scale];
          p=rotate([p[0]*(slot.mirror?-1:1),p[1]],angle);p=[(p[0]+slot.x)*scale+shift[0],(p[1]+slot.y)*scale+shift[1]];
          assert(p[0]>=3&&p[0]<=97&&p[1]>=3&&p[1]<=61,'Eye crop fits viewport: '+expression.id+' '+eye.role+' '+frame.pose);eyeCornerChecks++;
        }
      }
      const closed=asset.frames.findIndex(frame=>frame.pose==='closed');
      assert.equal(drawn.helpers.blinkPose(asset,140),closed,'closed frame selected by name');
    }
    staticFace.destroy();face.stopSpeech();
  }
  face.destroy();

  const eight={frames:['rest','anticipation','closing','near_closed','closed','opening_low','opening','settled'].map(pose=>({pose}))};
  assert.equal(drawn.helpers.blinkPose(eight,90),3);assert.equal(drawn.helpers.blinkPose(eight,260),5);
  for(let offset=0;offset<125;offset++) {
    const samples=[];for(let age=offset;age<375;age+=125)samples.push(drawn.helpers.blinkPose(eight,age));
    assert(samples.includes(4),'8 fps sampling cannot skip closed hold');
  }
  const sixteen={frames:['rest','MBP','release','small_AA','AA','EH','EE','OH','OO','FV','LNT','S','TH','wide_close','round_close','SMILE'].map(pose=>({pose}))};
  assert.equal(drawn.helpers.mouthPose(sixteen,'AA',.4),3);assert.equal(drawn.helpers.mouthPose(sixteen,'AA',.9),4);
  assert.equal(drawn.helpers.mouthPose(sixteen,'AA',.1),2);assert.equal(drawn.helpers.mouthPose(sixteen,'EE',.1),13);
  assert.equal(drawn.helpers.mouthPose(sixteen,'OO',.1),14);assert.equal(drawn.helpers.mouthPose(sixteen,'FV',.9),9);
  assert.equal(drawn.helpers.mouthPose(sixteen,'TH'),12);assert.equal(drawn.helpers.mouthPose(sixteen,'OO'),8);
  const white=new Uint8ClampedArray(404);for(let i=0;i<white.length;i+=4)white.set([255,255,255,255],i);white.set([94,234,221,255],4);
  drawn.helpers.colorizePixels(white);assert.equal(white[3],0);assert.equal(white[7],255);assert.deepEqual(Array.from(white.slice(4,7)),[94,234,221]);
  const transparent=new Uint8ClampedArray([94,234,221,0,80,230,190,123]);drawn.helpers.colorizePixels(transparent);
  assert.equal(transparent[7],123);assert.deepEqual(Array.from(transparent.slice(4,7)),[94,234,221]);
  const missing=drawn.create(null,{data,runtime,atlas:{assets:{}},images:{},autoStart:false,reducedMotion:true});
  assert.equal(await missing.ready,false);assert.equal(missing.snapshot().renderer,'original');assert(missing.snapshot().drawnError);missing.destroy();
  let transitionPairs=0,transitionSamples=0,rapidRetargets=0;
  const animated=drawn.create(null,{data,runtime,atlas,images,now:()=>time,autoStart:false,reducedMotion:false});await animated.ready;
  animated.setGaze(0,0);
  const beforeBlink=JSON.stringify(animated.snapshot().drawnLayers);animated.blink();
  assert.equal(JSON.stringify(animated.snapshot().drawnLayers),beforeBlink,'Blink starts without an eye identity pop');time+=500;
  const picture=state=>JSON.stringify({layers:state.drawnLayers,placements:state.drawnPlacements,visuals:state.drawnVisuals});
  const eyeCenters=state=>['eye_L','eye_R'].map(role=>{
    const views=state.drawnVisuals.filter(view=>view.role===role),weight=views.reduce((sum,view)=>sum+view.opacity,0);
    return [views.reduce((sum,view)=>sum+view.x*view.opacity,0)/weight,views.reduce((sum,view)=>sum+view.y*view.opacity,0)/weight];
  });
  function validateTransition(state) {
    transitionSamples++;
    for(const role of ['eye_L','eye_R']) {
      const eyeViews=state.drawnVisuals.filter(view=>view.role===role);
      assert.equal(eyeViews.length,1,'Each transition has a single eye visual per side');
      const opacity=eyeViews.reduce((sum,view)=>sum+view.opacity,0);
      assert(Math.abs(opacity-1)<.00001,'Eye group retains full opacity throughout changes');
    }
    for(const view of state.drawnVisuals) assert(Number.isFinite(view.x)&&Number.isFinite(view.y)&&view.opacity>=0&&view.opacity<=1&&view.closure>=0&&view.closure<=1);
    for(const p of state.drawnPlacements) {
      assert(Number.isFinite(p.scale)&&p.scale>0,'Transitions never use a negative scale');
      if(p.role==='mouth')for(const [x,y] of mouthCorners(p,atlas.assets[p.id].frames[p.frame]))assert(x>=6-1e-6&&x<=94+1e-6&&y>=6-1e-6&&y<=58+1e-6,'Moving mouth stays inside viewport');
    }
    assert(state.drawnPlacements.filter(p=>p.role==='mouth').length<=1,'Speaking transitions never overlay two viseme mouths');
    assert(state.drawnLayers.filter(p=>p.role==='mouth').length<=1,'Silent transitions never overlay two resting mouths');
  }
  const originalEyes=new Map();
  for(const expression of data.faces) {
    const f=runtime.create(null,{data,expression:expression.id,autoStart:false,reducedMotion:true});
    originalEyes.set(expression.id,f.snapshot().layers.filter(layer=>layer.role.startsWith('eye')));f.destroy();
  }
  for(const from of data.faces)for(const to of data.faces) {
    animated.stopSpeech();animated.setExpression(from.id);time+=700;
    const resting=animated.snapshot();
    assert.equal(JSON.stringify(resting.drawnLayers.filter(layer=>layer.role.startsWith('eye'))),JSON.stringify(originalEyes.get(from.id)),'Rest keeps the exact original eye geometry: '+from.id);
    const before=picture(resting);animated.setExpression(to.id);assert.equal(picture(animated.snapshot()),before,'A new transition starts at the displayed image');
    const at=time;
    sample={active:true,viseme:'AA',amount:.65,time:1.25,source:'transition-fixture'};
    animated.startSpeech({sample:()=>sample,clock:()=>1.25,duration:Infinity});
    for(const offset of [0,5,20,66.7,100,133.4,200,266.7,333.4,400,466.7,533.4,600]) {
      time=at+offset;const state=animated.snapshot();validateTransition(state);
      assert.equal(state.viseme,'AA');assert.equal(state.speechTime,1.25,'Expression transitions never move the audio clock');
    }
    const first=eyeCenters(animated.snapshot(at+209.99)),second=eyeCenters(animated.snapshot(at+210.01));
    for(let i=0;i<2;i++)assert(Math.hypot(first[i][0]-second[i][0],first[i][1]-second[i][1])<.01,'No midpoint eye placement jump');
    assert.equal(animated.snapshot().drawnTransition.active,false);assert.equal(animated.snapshot().drawnTransition.target,to.id);transitionPairs++;
  }
  for(let i=0;i<120;i++) {
    time+=57+(i%5)*43;const before=picture(animated.snapshot());
    animated.setExpression(data.faces[(i*17+3)%data.faces.length].id);
    assert.equal(picture(animated.snapshot()),before,'Rapid retarget starts from displayed groups, including tears and speech');
    validateTransition(animated.snapshot());rapidRetargets++;
  }
  animated.stopSpeech();assert(!animated.snapshot().drawnPlacements.some(p=>p.role==='mouth'),'Cancellation closes every mouth contributor immediately');
  animated.setExpression('05_annoyed_01_manual');time+=700;animated.setExpression('28_sad_03_manual',{durationMs:1200});time+=540;
  const ghostRegression=animated.snapshot();assert.equal(ghostRegression.drawnPlacements.filter(p=>p.kind==='eye_bridge').length,2);
  assert.equal(ghostRegression.drawnLayers.filter(p=>p.role==='mouth').length,1);assert.equal(ghostRegression.drawnLayers.find(p=>p.role==='mouth').part,'transition-closure');
  time+=700;assert.equal(animated.snapshot().drawnTransition.active,false);
  global.Path2D=class{constructor(value){this.value=value;}};
  let rasterDraws=0,vectorDraws=0;const imageDraws=[];
  const mockContext={setTransform(){},clearRect(){},save(){},restore(){},beginPath(){},rect(){},clip(){},translate(){},rotate(){},scale(){},fill(){vectorDraws++;},stroke(){vectorDraws++;},drawImage(...args){rasterDraws++;imageDraws.push(args);}};
  const mockCanvas={width:500,height:320,dataset:{},getContext(){return mockContext;}};
  animated.setExpression('39_neutral_02_manual');time+=700;
  const restRendered=animated.renderTo(mockCanvas,time,{gaze:{x:0,y:0}});assert(vectorDraws>=3);assert.equal(rasterDraws,0,'Shared preview renderer preserves exact original resting eyes');
  const held=animated.renderTo(mockCanvas,time,{blinkFrame:{eye_L:4,eye_R:4},mouthFrame:8});
  assert.equal(held.drawnPlacements.filter(p=>p.role.startsWith('eye')).every(p=>p.frame===4),true);assert.equal(held.drawnPlacements.find(p=>p.role==='mouth').frame,8);assert.equal(rasterDraws,3);
  const assigned=drawn.helpers.mouthAssetForFace(animated.expression,atlas),fvIndex=atlas.assets[assigned].frames.findIndex(frame=>frame.pose==='FV');
  const consonant=animated.renderTo(mockCanvas,time,{mouthFrame:fvIndex}),fv=atlas.assets[assigned].frames[fvIndex],placement=consonant.drawnPlacements.find(p=>p.role==='mouth'),call=imageDraws.at(-1);
  assert.equal(call[0],images[fv.file||assigned],'Replacement consonants draw from their per-frame sheet');
  assert(Math.abs(call[7]-fv.w*(fv.sourceScale??1)*placement.scale)<1e-8,'Replacement sheet normalization applies once to drawing width');
  assert(Math.abs(call[8]-fv.h*(fv.sourceScale??1)*placement.scale)<1e-8,'Replacement sheet normalization applies once to drawing height');
  assert.equal(placement.scale,held.drawnPlacements.find(p=>p.role==='mouth').scale,'The mouth retains one display scale across mixed sheets');
  assert.equal(animated.snapshot().viseme,null,'Inspector overrides do not change speech timeline');
  assert.equal(animated.snapshot().drawnPlacements.some(p=>p.role==='mouth'),false,'Inspector overrides do not leak into subsequent renders');
  assert.equal(restRendered.drawnLayers.filter(layer=>layer.role.startsWith('eye')).length,2);
  animated.setExpression('20_neutral_06_manual');time+=700;
  sample={active:true,viseme:'AA',amount:.7,time:2.5,source:'readability-fixture'};
  animated.startSpeech({sample:()=>sample,clock:()=>2.5,duration:Infinity});
  const mouthGeometry=()=>{const p=animated.snapshot().drawnPlacements.find(item=>item.role==='mouth');return{x:p.x,y:p.y,width:p.scale*p.master.w,rotation:p.rotation};};
  assert(Math.abs(mouthGeometry().width-8)<1e-8);
  animated.setExpression('01_angry_01_manual');time+=200;const midSpeech=mouthGeometry();
  assert(midSpeech.width>8,'Speech width expands continuously from the minimum toward a larger expression');
  animated.setExpression('40_neutral_03_manual');assert.deepEqual(mouthGeometry(),midSpeech,'Retargeting preserves the currently displayed speech anchor and width');
  time+=700;assert(Math.abs(mouthGeometry().width-8)<1e-8,'A small-mouth endpoint does not collapse below the readable speech width');
  animated.setExpression('20_neutral_06_manual');const dotTransitionStart=time;
  for(const elapsed of [0,66.7,133.4,200,333.4,466.7,600]) {
    time=dotTransitionStart+elapsed;assert(Math.abs(mouthGeometry().width-8)<1e-8,'Both dot-mouth endpoints preserve readable width throughout their transition');
    assert.equal(animated.snapshot().speechTime,2.5);
  }
  animated.stopSpeech();const restingDot=animated.snapshot().drawnLayers.find(layer=>layer.role==='mouth');
  assert.equal(restingDot.part,data.faces.find(expression=>expression.id==='20_neutral_06_manual').slots.mouth.part,'Stopping restores the canonical small mouth');animated.destroy();
  const report={passed:true,checkedAt:new Date().toISOString(),rendererSha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT,'brain/ui/static/drawn_face_renderer.js'))).digest('hex'),faces:data.faces.length,atlasCels:Object.values(atlas.assets).reduce((count,asset)=>count+asset.frames.length,0),eyeFrameChecks:eyeChecks,eyeCornerChecks,mouthCornerChecks:mouthChecks,transitionPairs,transitionSamples,rapidRetargets,readableSpeechChecks,
    checks:['Audio clock drives event poses independently of wall time','Streaming sampler drives every frame','Pre-roll and gaps use original rest','Stop clears stale speech sampler','Every expression keeps its original mouth center','All mouth crops fit viewport','6- and 8-frame blink poses by name','Closed hold survives every 8 fps phase','12- and 16-frame mouth poses by name','Quiet vowels use release and closure cels','White removal and canonical color preserve coverage','Invalid atlas keeps original renderer','Exact original resting eye geometry in all 40 faces','All 1600 expression pairs preserve audio clock and have no midpoint placement jump','Rapid retarget captures displayed eye, mouth and tear groups','Shared renderTo canvas API preserves identity and isolates inspector overrides','Mixed-sheet consonants use their own image and normalize source scale exactly once','Faces 20 and 40 have readable AA, LNT, FV and TH with exact resting dots','Speech width and anchor survive retargets between small and large mouths'],
    limits:['Geometry checks use source-contour fitting support in the headless harness. Browsers fit the actual keyed image ink.','These checks validate state and placement; visual motion quality still requires browser inspection.']};
  fs.writeFileSync(path.join(__dirname,'drawn_face_renderer_checks.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});
