// Focused reproduction: production selection policy with production renderer timing.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
const require=createRequire(import.meta.url);
const runtime=require('../ui/static/face_runtime.js');
const drawn=require('../ui/static/drawn_face_renderer.js');
const policySource=await readFile(new URL('../duplex/static/expression_policy.js',import.meta.url),'utf8');
const {ExpressionPolicy}=await import('data:text/javascript;base64,'+Buffer.from(policySource).toString('base64'));
const source=await readFile(new URL('../face_assets/app/app_data.js',import.meta.url),'utf8');
const data=JSON.parse(source.replace(/^window\.MIST_DATA = /,'').trim().replace(/;$/,''));
const map=JSON.parse(await readFile(new URL('../duplex/face_map.json',import.meta.url),'utf8'));
const atlas=JSON.parse(await readFile(new URL('../art_direction/artist_studio_20260916/reuse/drawn/atlas.json',import.meta.url),'utf8'));
const images=Object.fromEntries(Object.keys(atlas.assets).map(id=>[id,{}]));
for(const asset of Object.values(atlas.assets)){
  images[asset.file]=images[asset.id];
  for(const frame of asset.frames)if(frame.file)images[frame.file]??={};
}

async function run(queued){
  let now=0,lastId=map.expressions.neutral.primary;
  const face=drawn.create(null,{data,runtime,atlas,images,expression:lastId,autoStart:false,reducedMotion:false,now:()=>now});
  await face.ready;
  const policy=new ExpressionPolicy(map,{now:()=>now,transitionMs:drawn.timing.transitionMs});
  const command=queued?{expression:'curious',duration_ms:400}:{expression:'happy',duration_ms:400};
  const target=map.expressions[command.expression].primary;
  const samples=[];let requestedAt=0,appliedAt=null,replacedAt=null;
  if(queued)policy.request({expression:'happy',duration_ms:3000});
  else policy.request(command);
  for(now=0;now<=1800;now+=50){
    if(queued&&now===100){policy.request(command);requestedAt=now;}
    const chosen=policy.snapshot();
    if(chosen.faceId!==lastId){
      if(lastId===target)replacedAt=now;
      lastId=chosen.faceId;face.setExpression(lastId);
      if(lastId===target&&appliedAt===null)appliedAt=now;
    }
    const shown=face.snapshot(now);
    if(shown.drawnRig===target)samples.push({at:now,progress:shown.drawnTransition.progress,phase:shown.drawnTransition.phase});
  }
  face.destroy();
  const fullyShownSamples=samples.filter(sample=>sample.progress===1);
  return {scenario:queued?'queued_minimum_hold':'immediate_minimum_hold',requestedAt,appliedAt,replacedAt,
    requestedHoldMs:400,rendererTransitionMs:drawn.timing.transitionMs,
    maxTargetProgress:Math.max(...samples.map(sample=>sample.progress)),fullyShownSamples:fullyShownSamples.length,
    fullyShownForMs:fullyShownSamples.length?replacedAt-fullyShownSamples[0].at:0,samples};
}
const scenarios=[await run(false),await run(true)];
const report={checkedAt:new Date().toISOString(),policySha256:createHash('sha256').update(policySource).digest('hex'),
  rendererDefaultTransitionMs:drawn.timing.transitionMs,animationFps:drawn.timing.fps,
  defectReproduced:scenarios.every(s=>s.fullyShownForMs<400),scenarios,
  limits:['Runs the actual policy and renderer layout with a controlled 50 ms app update clock. It does not inspect pixels or call models.']};
await mkdir(new URL('../results/',import.meta.url),{recursive:true});
await writeFile(new URL('../results/expression_hold_transition_20260922.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
if(process.argv.includes('--expect-fixed'))assert(scenarios.every(s=>s.fullyShownForMs>=400),'Requested face must be fully visible for its requested 400 ms hold');
else assert(report.defectReproduced,'Expected the current minimum-hold defect to be reproducible');
console.log(JSON.stringify(report,null,2));
