// Read-only production audit of blink orientations. Writes only v5 review records.
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path');
const prefix=fs.readFileSync(path.join(__dirname,'identity_after.cjs'),'utf8').split('async function run(){')[0];
const audit=String.raw`
function lineAngle(a,b){let degrees=Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI;while(degrees>90)degrees-=180;while(degrees<=-90)degrees+=180;return degrees;}
function distAngle(a,b){return Math.abs(lineAngle([0,0],[Math.cos((a-b)*Math.PI/180),Math.sin((a-b)*Math.PI/180)]));}
function clip(x,m){return Math.max(-m,Math.min(m,x));}
function upperSlope(points){
 const b=bounds(points),samples=[];
 for(let i=1;i<9;i++){
  const low=b.x+b.w*(i-.5)/10,high=b.x+b.w*(i+.5)/10;
  const ps=points.filter(p=>p[0]>=low&&p[0]<high);
  if(ps.length)samples.push([b.x+b.w*i/10,Math.min(...ps.map(p=>p[1]))]);
 }
 const mx=samples.reduce((s,p)=>s+p[0],0)/samples.length,my=samples.reduce((s,p)=>s+p[1],0)/samples.length;
 return Math.atan2(samples.reduce((s,p)=>s+(p[0]-mx)*(p[1]-my),0),samples.reduce((s,p)=>s+(p[0]-mx)**2,0))*180/Math.PI;
}
function endpoints(points){return lineAngle(points[0],points.at(-1));}
function straightLid(points){
 const b=bounds(points);let best=null;
 for(let i=0;i<points.length-5;i++){
  let length=0;
  for(let j=i+1;j<points.length;j++){
   length+=Math.hypot(points[j][0]-points[j-1][0],points[j][1]-points[j-1][1]);
   const a=points[i],z=points[j],chord=Math.hypot(z[0]-a[0],z[1]-a[1]),cy=(z[1]+a[1])/2;
   if(j-i<4||Math.abs(z[0]-a[0])<b.w*.45||cy>b.y+b.h*.72||length/chord>1.012)continue;
   if(!best||chord>best.chord)best={angle:lineAngle(a,z),chord,ratio:length/chord};
  }
 }
 return best;
}
(async()=>{
 const rig=Drawn.create(null,{data:DATA,runtime:Base,atlas,images,expression:DATA.faces[0].id,autoStart:false,reducedMotion:false,now:()=>time});if(!await rig.ready)throw Error(rig.error?.message);
 const rows=[];
 for(const face of DATA.faces){
  rig.setExpression(face.id,{durationMs:600});time+=1000;
  const reference=originals.get(face.id),indices={};
  for(const role of ['eye_L','eye_R']){const family=Drawn.helpers.PART_FAMILY[face.slots[role].part];indices[role]=atlas.assets[family].frames.findIndex(f=>f.pose==='closed');}
  const state=rig.renderTo(canvas,time,{gaze:{x:0,y:0},blinkFrame:indices});
  for(const role of ['eye_L','eye_R']){
   const slot=face.slots[role],p=state.drawnPlacements.find(p=>p.role===role),layer=reference.find(l=>l.role===role),draw=context.sprites[role==='eye_L'?0:1];
   const family=Drawn.helpers.PART_FAMILY[slot.part],m=draw.matrix,angle=lineAngle([0,0],[m[0],m[1]]);
   const centerline=lineAngle(...['eye_L','eye_R'].map(role=>{const b=bounds(reference.find(l=>l.role===role).points);return[b.x+b.w/2,b.y+b.h/2];}));
   const top=upperSlope(layer.points),ends=endpoints(layer.points),lid=straightLid(layer.points);
   let strategy,target,note;
   if(family==='round') {strategy='screen-level round-eye blink';target=clip(centerline,4);note='Circle gap angle identifies an opening in a round glyph, not a rolling eyelid. Keep closure near the shared eye line.';}
   else if(family==='loop') {strategy='gentle tired-lid tilt';target=clip((lid?.angle??top)*.6,10);note='Retain a small amount of the straight crossbar attitude; do not rotate the whole closed lid by the C-gap alignment.';}
   else if(family==='hook') {strategy='upper-lid-led tilt';target=clip((lid?.angle??top)*.65,18);note='Use the actual straight upper-lid slope, softened. This preserves angry or drooping attitude without copying the reference-hook alignment angle.';}
   else if(family==='arc') {strategy='source-arc squeeze';target=clip(ends,20);note='This eye is already a closed arc. Keep its source endpoint direction and concavity during a small squeeze; a generic opening blink can reverse the expression.';}
   else if(family==='slot') {strategy='slot-axis closure';target=clip(top,7);note='Compress the gap around the nearly horizontal source bars. Preserve slight intentional bar tilt, not arbitrary C-end alignment.';}
   else if(family==='chevron') {strategy='centered chevron squeeze';target=clip(centerline,4);note='The chevron apex is symmetric around a horizontal axis; close around that axis without importing top-stroke slope.';}
   else {strategy='bar-axis squeeze';target=clip(ends,7);note='Preserve the near-horizontal source bar axis; use only a small squeeze.';}
   const mismatch=distAngle(angle,target),severity=mismatch>18?'high':mismatch>9?'medium':'low';
   // Shape concavity reference: positive midpoint residual means a U in screen coordinates.
   const points=layer.points,b=bounds(points),left=points.reduce((a,b)=>a[0]<b[0]?a:b),right=points.reduce((a,b)=>a[0]>b[0]?a:b),middle=points.filter(p=>Math.abs(p[0]-(b.x+b.w/2))<b.w*.15);
   const lineY=(left[1]+right[1])/2,arcConcavity=middle.length?middle.reduce((s,p)=>s+p[1],0)/middle.length-lineY:0;
   rows.push({face:face.id,role,part:slot.part,family,currentClosedAxisDegrees:angle,slotRotationDegrees:slot.rot||0,referenceAlignmentDegrees:p.fit.rotation*180/Math.PI,sourceUpperContourSlopeDegrees:top,sourceStraightLid:lid,sourceEndpointLineDegrees:ends,sourceArcConcavity:family==='arc'?arcConcavity:null,desiredStrategy:strategy,recommendedTargetDegrees:target,recommendedAbsoluteLimitDegrees:family==='hook'?18:family==='arc'?20:family==='loop'?10:family==='slot'||family==='bar'?7:4,diagnosticDifferenceDegrees:mismatch,severity,note,uncertainty:'Recommended angle is an art-direction starting point, not a measured anatomical target. Confirm in playback.'});
  }
 }
 const report={checkedAt:new Date().toISOString(),rendererSha256:hash(drawnSource),atlasSha256:hash(path.join(HERE,'atlas.json')),faceDataSha256:hash(dataSource),scope:{faces:40,eyes:80,parts:new Set(rows.map(r=>r.part)).size},method:['Executed production renderer with pixel-backed source sheets and captured actual drawImage transforms for every eye at its declared closed cel.','Compared the captured closed axis with canonical source geometry, upper-contour slope, arc endpoints, and common eye line.','Visually reviewed all 40 original faces. Recommendations separate circle-gap orientation from eyelid attitude; no original resting art was changed.'],rows,summary:{high:rows.filter(r=>r.severity==='high').length,medium:rows.filter(r=>r.severity==='medium').length,low:rows.filter(r=>r.severity==='low').length},recommendations:['Never apply a single zero-angle rule to all 80 eyes: angry hooks, tired crossbars, source closed arcs and bars have intentional attitudes.','Round eyes need independent screen-level blink coordinates; slot.rot and reference alignment encode circle-gap placement, not head tilt.','For source closed arcs, preserve concavity and endpoints in a squeeze. Several aligned arcs rotate roughly 160 to 180 degrees, which reverses generic lid curvature.','For hook eyes, derive a bounded target from the source upper lid, not the generic hook alignment.','Make closure angle approach its target during closing and undo it during reopening; prevent a sudden orientation jump when entering or leaving the closed frame.','Expression-transition closed bridges must use the same per-eye closure orientation as ordinary blinks.'],limitations:['This audit proposes art direction and identifies large rotation mismatches. It does not by itself certify natural motion.','PCA or whole-glyph alignment is unreliable for circular and asymmetric glyphs; source geometry measurements are supporting cues, not a complete automatic design rule.']};
 fs.writeFileSync(path.join(HERE,'blink_orientation_review_v5.json'),JSON.stringify(report,null,2)+'\n');
 const lines=['# Blink orientation review','', 'No production edits. Open canonical faces remain the reference. Angles are clockwise degrees in screen coordinates; positive slopes downward to the right.', '', 'The current renderer carries glyph-fitting rotation into the closed lid. This is incorrect for many round eyes and some drooping hooks. A uniform zero-angle rule would also discard intentional expression tilt.', '', '| Face | Side | Source part | Current closed angle | Proposed target | Strategy | Severity |','|---|---|---|---:|---:|---|---|'];
 for(const r of rows)lines.push('| '+r.face+' | '+r.role+' | '+r.part+' | '+r.currentClosedAxisDegrees.toFixed(1)+' | '+r.recommendedTargetDegrees.toFixed(1)+' | '+r.desiredStrategy+' | '+r.severity+' |');
 lines.push('', 'Recommended targets are starting points for visual review, not precision measurements of an ideal blink.', '', ...report.recommendations.map(x=>'- '+x));
 fs.writeFileSync(path.join(HERE,'blink_orientation_review_v5.md'),lines.join('\n')+'\n');
 console.log(JSON.stringify({renderer:report.rendererSha256,summary:report.summary,bad:rows.filter(r=>r.severity!=='low').map(r=>({face:r.face,side:r.role,part:r.part,current:r.currentClosedAxisDegrees,target:r.recommendedTargetDegrees,strategy:r.desiredStrategy}))},null,2));rig.destroy();
})().catch(e=>{console.error(e);process.exitCode=1;});
`;
vm.runInNewContext(prefix+audit,{require,__dirname,console,Buffer,process,Uint8ClampedArray},{filename:__filename});
