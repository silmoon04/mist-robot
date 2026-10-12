'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const ROOT=path.resolve(__dirname,'../..'),DRAWN=path.join(ROOT,'brain/art_direction/artist_studio_20260916/reuse/drawn');
const source={window:{}};vm.runInNewContext(fs.readFileSync(path.join(ROOT,'brain/face_assets/app/app_data.js'),'utf8'),source);
const data=source.window.MIST_DATA,runtime=require('../ui/static/face_runtime.js'),drawn=require('../ui/static/drawn_face_renderer.js');
const published=JSON.parse(fs.readFileSync(path.join(DRAWN,'atlas.json'),'utf8'));
const mapping=JSON.parse(fs.readFileSync(path.join(DRAWN,'emotion_mapping_v4_review.json'),'utf8')).mouthFamilies;
const atlas=structuredClone(published),synthetic=!atlas.mouthFamilies;
if(synthetic) {
  atlas.mouthFamilies=mapping;
  for(const id of new Set(Object.values(mapping)))if(!atlas.assets[id])atlas.assets[id]={...structuredClone(atlas.assets.mouth_neutral),id};
}
const images=Object.fromEntries(Object.values(atlas.assets).flatMap(asset=>[[asset.id,{}],[asset.file,{}],...asset.frames.filter(frame=>frame.file).map(frame=>[frame.file,{}]) ]));
(async()=>{
  let wall=0,sample={active:true,viseme:'AA',amount:.8,time:1.5,source:'speech-fixture'};
  const face=drawn.create(null,{data,runtime,atlas,images,autoStart:false,reducedMotion:true,now:()=>wall});assert(await face.ready);
  const poses=[['small_AA',.8,'small_AA'],['AA',.4,'small_AA'],['AA',.8,'AA'],['EH',.8,'EH'],['EE',.8,'EE'],['LNT',.8,'LNT'],['wide_close',.8,'wide_close'],['FV',.8,'FV'],['TH',.8,'TH']];
  let mappings=0,poseChecks=0,restChecks=0;
  for(const expression of data.faces) {
    const expected=atlas.mouthFamilies[expression.id];assert.equal(drawn.helpers.mouthAssetForFace(expression.id,atlas),expected);
    face.stopSpeech();face.setExpression(expression.id);face.startSpeech({sample:()=>sample,clock:()=>sample.time,duration:Infinity});
    for(const [viseme,amount,expectedPose] of poses) {
      sample={...sample,active:true,viseme,amount};const state=face.snapshot(),mouths=state.drawnPlacements.filter(p=>p.role==='mouth');
      assert.equal(state.drawnMouthFamily.assigned,expected);
      if(expression.slots.mouth){assert.equal(mouths.length,1);assert.equal(mouths[0].id,expected);assert.equal(atlas.assets[expected].frames[mouths[0].frame].pose,expectedPose);}
      else assert.equal(mouths.length,0,'A mouthless canonical face keeps its established policy');
      poseChecks++;
    }
    sample={...sample,viseme:'SMILE',amount:.8};const smile=face.snapshot().drawnPlacements.find(p=>p.role==='mouth');
    if(smile)assert.equal(atlas.assets[expected].frames[smile.frame].pose,expected==='mouth_smile'?'SMILE':'EE','SMILE cues cannot force a happy drawing into nonhappy families');
    sample={...sample,viseme:'rest'};const rest=face.snapshot();assert.equal(rest.drawnPlacements.some(p=>p.role==='mouth'),false);
    const canonical=runtime.create(null,{data,expression:expression.id,reducedMotion:true,autoStart:false});
    assert.equal(JSON.stringify(rest.drawnLayers.filter(p=>p.role==='mouth')),JSON.stringify(canonical.snapshot().layers.filter(p=>p.role==='mouth')),'Speech rest keeps exact canonical mouth');canonical.destroy();
    mappings++;restChecks++;
  }
  face.destroy();
  const animated=drawn.create(null,{data,runtime,atlas,images,autoStart:false,reducedMotion:false,expression:'01_angry_01_manual',now:()=>wall});assert(await animated.ready);
  sample={active:true,viseme:'AA',amount:.8,time:2.5,source:'speech-fixture'};animated.startSpeech({sample:()=>sample,clock:()=>sample.time,duration:Infinity});
  assert.equal(animated.snapshot().drawnMouthFamily.active,atlas.mouthFamilies['01_angry_01_manual']);
  animated.setExpression('31_sad_06_manual');
  for(const offset of [0,66.7,133.4,200,300,399]) {
    wall=offset;const state=animated.snapshot();assert.equal(state.drawnMouthFamily.active,'mouth_angry','Held vowel does not swap family at transition midpoint');
    assert.equal(state.speechTime,2.5);assert.equal(state.drawnPlacements.filter(p=>p.role==='mouth').length,1);
  }
  assert.equal(animated.snapshot().drawnMouthFamily.pending,true);
  wall=400;let bounded=animated.snapshot();assert.equal(bounded.drawnMouthFamily.active,'mouth_sad','A sustained vowel changes family by the bounded frame');
  assert.equal(bounded.drawnMouthFamily.switchReason,'bounded-timeout');assert.equal(bounded.viseme,'AA');assert.equal(bounded.speechTime,2.5);
  const sameCue=bounded.drawnPlacements.find(p=>p.role==='mouth');assert.equal(atlas.assets[sameCue.id].frames[sameCue.frame].pose,'AA','Bounded handoff does not insert a fake closure');
  wall=700;sample={...sample,viseme:'EH',time:2.7};assert.equal(animated.snapshot().drawnMouthFamily.active,'mouth_sad');
  const before=animated.snapshot().drawnPlacements.find(p=>p.role==='mouth');animated.setExpression('39_neutral_02_manual');
  assert.deepEqual(animated.snapshot().drawnPlacements.find(p=>p.role==='mouth'),before,'Retarget preserves currently displayed speaking mouth');
  wall+=200;sample={...sample,viseme:'MBP',time:2.9};assert.equal(animated.snapshot().drawnMouthFamily.active,'mouth_flat','Closed lips are a safe family boundary');
  animated.setExpression('09_happy_03_manual');sample={...sample,viseme:'rest',time:3};assert.equal(animated.snapshot().drawnMouthFamily.active,'mouth_smile');
  assert.equal(animated.snapshot().drawnPlacements.some(p=>p.role==='mouth'),false);
  animated.stopSpeech();assert.equal(animated.snapshot().speaking,false);
  function startAngry() {
    animated.stopSpeech();animated.setExpression('01_angry_01_manual');wall+=700;
    sample={active:true,viseme:'AA',amount:.8,time:10,source:'audio-energy-regression'};
    animated.startSpeech({sample:()=>sample,clock:()=>sample.time,duration:Infinity});animated.snapshot();
  }
  startAngry();animated.setExpression('31_sad_06_manual');const quietAt=wall;
  wall=quietAt+100;sample={...sample,amount:.2};assert.equal(animated.snapshot().drawnMouthFamily.active,'mouth_angry','Quiet amplitude does not switch before the minimum wait');
  wall=quietAt+220;const quiet=animated.snapshot();assert.equal(quiet.drawnMouthFamily.active,'mouth_sad');assert.equal(quiet.drawnMouthFamily.switchReason,'quiet-trough');
  startAngry();animated.setExpression('31_sad_06_manual');const retargetAt=wall;
  wall=retargetAt+250;const visibleBefore=animated.snapshot().drawnPlacements.find(p=>p.role==='mouth');animated.setExpression('39_neutral_02_manual');
  assert.deepEqual(animated.snapshot().drawnPlacements.find(p=>p.role==='mouth'),visibleBefore,'Pending-target replacement preserves visible mouth geometry');
  wall=retargetAt+450;assert.equal(animated.snapshot().drawnMouthFamily.active,'mouth_angry','An obsolete pending target cannot fire after retargeting');
  wall=retargetAt+750;assert.equal(animated.snapshot().drawnMouthFamily.active,'mouth_flat');
  animated.setExpression('09_happy_03_manual');animated.stopSpeech();wall+=700;
  assert.equal(animated.snapshot().drawnMouthFamily.pending,false);assert.equal(animated.snapshot().drawnPlacements.some(p=>p.role==='mouth'),false);
  sample={...sample,active:true,viseme:'AA',amount:.8};animated.startSpeech({sample:()=>sample,clock:()=>sample.time,duration:Infinity});
  assert.equal(animated.snapshot().drawnMouthFamily.active,'mouth_smile','Interruption clears old pending family before speech restarts');
  let boundPhaseChecks=0,latestHandoffMs=0;
  for(let phase=0;phase<67;phase++) {
    startAngry();wall+=phase;animated.setExpression('31_sad_06_manual');const selectedAt=wall;let changedAt=null;
    for(let elapsed=0;elapsed<=500;elapsed+=1000/60) {
      wall=selectedAt+elapsed;sample={...sample,time:10+elapsed/1000};const state=animated.snapshot();
      assert.equal(state.viseme,'AA');assert.equal(state.speechTime,sample.time);assert.equal(state.drawnPlacements.filter(p=>p.role==='mouth').length,1);
      if(state.drawnMouthFamily.active==='mouth_sad'&&changedAt===null)changedAt=elapsed;
    }
    assert(changedAt!==null&&changedAt>=400-1e-6&&changedAt<=466.667,'Every frame phase has a bounded same-viseme handoff');
    latestHandoffMs=Math.max(latestHandoffMs,changedAt);boundPhaseChecks++;
  }
  animated.destroy();
  const invalid=structuredClone(atlas);invalid.mouthFamilies['39_neutral_02_manual']='mouth_missing';
  const bad=drawn.create(null,{data,runtime,atlas:invalid,images,autoStart:false,reducedMotion:true});assert.equal(await bad.ready,false);assert.match(bad.error.message,/Invalid mouth-family assignment/);bad.destroy();
  const partial=structuredClone(atlas);delete partial.mouthFamilies['20_neutral_06_manual'];
  const incomplete=drawn.create(null,{data,runtime,atlas:partial,images,autoStart:false,reducedMotion:true});assert.equal(await incomplete.ready,false);assert.match(incomplete.error.message,/Missing mouth-family assignment/);incomplete.destroy();
  const misleading={...atlas,mouthFamilies:{...atlas.mouthFamilies,'09_happy_03_manual':'mouth_sad'}};
  assert.equal(drawn.helpers.mouthAssetForFace('09_happy_03_manual',misleading),'mouth_sad','Explicit maps override name heuristics');
  const report={passed:true,checkedAt:new Date().toISOString(),rendererSha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT,'brain/ui/static/drawn_face_renderer.js'))).digest('hex'),atlasMode:synthetic?'synthetic family-routing fixture; new artwork not yet published':'published atlas',faceMappings:mappings,poseChecks,canonicalRestChecks:restChecks,boundPhaseChecks,latestHandoffMs,
    checks:['Exact map controls all 40 faces','Matched cues choose poses in the assigned family','Nonhappy SMILE cues use the family EE drawing','A held vowel preserves its cue and switches family within the bounded frame window','Real cue boundaries and closed lips activate the pending family','Quiet amplitude can hand off after 150 ms','No fake closure, duplicate mouth or changed audio clock during forced handoff','Rapid retarget replaces the pending family and preserves visible geometry','Interruption clears pending family before speech restart','Every 15 fps phase switches sustained AA between 400 and 466.7 ms','Invalid or incomplete family assignments fail to the original renderer']};
  fs.writeFileSync(path.join(__dirname,'mouth_family_checks.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});
