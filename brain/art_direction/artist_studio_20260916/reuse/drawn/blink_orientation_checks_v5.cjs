// Independent physical ink checks. Run only after the final renderer hash is stable.
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path');
const prefix=fs.readFileSync(path.join(__dirname,'identity_after.cjs'),'utf8').split('async function run(){')[0];
const audit=String.raw`
function angleBetween(a,b){let degrees=Math.atan2(b[1]-a[1],b[0]-a[0])*180/Math.PI;while(degrees>90)degrees-=180;while(degrees<=-90)degrees+=180;return degrees;}
function average(points){return [0,1].map(k=>points.reduce((s,p)=>s+p[k],0)/points.length);}
function axis(points){
 const sorted=points.slice().sort((a,b)=>a[0]-b[0]),n=Math.max(2,Math.round(sorted.length*.08));
 return angleBetween(average(sorted.slice(0,n)),average(sorted.slice(-n)));
}
function curve(points,angle){
 const r=angle*Math.PI/180,c=Math.cos(r),s=Math.sin(r),local=points.map(([x,y])=>[x*c+y*s,-x*s+y*c]);
 const b=bounds(local),cx=b.x+b.w/2;const p=local.map(([x,y])=>[(x-cx)/b.w,y]);
 const m=Array.from({length:3},()=>[0,0,0,0]);
 for(const [x,y]of p){const a=[1,x,x*x];for(let i=0;i<3;i++){for(let j=0;j<3;j++)m[i][j]+=a[i]*a[j];m[i][3]+=a[i]*y;}}
 for(let i=0;i<3;i++){let pivot=i;for(let j=i+1;j<3;j++)if(Math.abs(m[j][i])>Math.abs(m[pivot][i]))pivot=j;[m[i],m[pivot]]=[m[pivot],m[i]];const q=m[i][i];if(Math.abs(q)<1e-10)return null;for(let k=i;k<4;k++)m[i][k]/=q;for(let j=0;j<3;j++)if(j!==i){const z=m[j][i];for(let k=i;k<4;k++)m[j][k]-=z*m[i][k];}}
 return {quadratic:m[2][3],linear:m[1][3],axis:angle,width:b.w};
}
function spriteFrame(draw){
 const asset=measurements.assets[draw.id];
 const all=asset?asset.frames:Object.values(measurements.assets).flatMap(a=>a.frames).filter(f=>f.file===draw.id);
 return all.find(f=>f.x===draw.sx&&f.y===draw.sy&&f.w===draw.sw&&f.h===draw.sh);
}
function inkCenterline(draw){
 const frame=spriteFrame(draw);if(!frame?.columnCenters)throw Error('Missing column measurements; run identity_after_extract.py first: '+draw.id);
 return frame.columnCenters.map(([px,py])=>{
  const x=draw.dx+(px-draw.sx)/draw.sw*draw.dw,y=draw.dy+(py-draw.sy)/draw.sh*draw.dh,m=draw.matrix;
  return[(m[0]*x+m[2]*y+m[4])/10,(m[1]*x+m[3]*y+m[5])/10];
 });
}
(async()=>{
 const rig=Drawn.create(null,{data:DATA,runtime:Base,atlas,images,expression:DATA.faces[0].id,autoStart:false,reducedMotion:false,now:()=>time});if(!await rig.ready)throw Error(rig.error?.message);
 const rows=[],arcFaces=new Set(['16','21','22','23','26','29','35']),angryFaces=new Set(['02','04']);
 for(const face of DATA.faces){
  rig.setExpression(face.id,{durationMs:600});time+=1000;
  const rest=originals.get(face.id),indices={};
  for(const role of ['eye_L','eye_R']){const family=Drawn.helpers.PART_FAMILY[face.slots[role].part];indices[role]=atlas.assets[family].frames.findIndex(f=>f.pose==='closed');}
  const state=rig.renderTo(canvas,time,{gaze:{x:0,y:0},blinkFrame:indices});
  const spriteDraws=context.sprites.filter(d=>d.alpha>.001);
  let spriteIndex=0;
  for(const role of ['eye_L','eye_R']){
   const vector=state.drawnLayers.find(layer=>layer.role===role&&(layer.opacity??1)>.001);
   const draw=vector?null:spriteDraws[spriteIndex++];
   check(!!vector||!!draw,'Missing visible closed lid for '+face.id+'/'+role);if(!vector&&!draw)continue;
   let points,sourceFile;
   if(vector){
    const command=context.strokes.find(d=>d.path===Base.pathData(vector.points,vector.mode==='fill'));
    check(!!command,'Closed vector not sent to canvas '+face.id+'/'+role);if(!command)continue;
    const m=command.matrix;points=vector.points.map(([x,y])=>[(m[0]*x+m[2]*y+m[4])/10,(m[1]*x+m[3]*y+m[5])/10]);sourceFile='canonical vector path';
   }else{points=inkCenterline(draw);sourceFile=spriteFrame(draw).file;}
   const source=rest.find(l=>l.role===role),sourceAxis=axis(source.points),closedAxis=axis(points);
   const canonicalCurve=curve(source.points,sourceAxis),closedCurve=curve(points,sourceAxis);
   const row={face:face.id,role,part:face.slots[role].part,closedVisibleAxisDegrees:closedAxis,canonicalEndpointAxisDegrees:sourceAxis,canonicalCurve,closedCurve,sourceFile,renderedAs:vector?'canonical vector squeeze':'registered PNG lid'};rows.push(row);
   if(arcFaces.has(face.id.slice(0,2))){
    const originalSign=Math.sign(canonicalCurve.quadratic),closedSign=Math.sign(closedCurve.quadratic);
    check(originalSign===closedSign,'Closed-arc concavity reversed: '+face.id+'/'+role);
    check(Math.abs(closedAxis-sourceAxis)<12,'Closed-arc endpoint attitude lost: '+face.id+'/'+role);
   }
   if(angryFaces.has(face.id.slice(0,2))){
    const expectedSign=role==='eye_L'?1:-1;
    check(Math.sign(closedAxis)===expectedSign&&Math.abs(closedAxis)>=5&&Math.abs(closedAxis)<=25,'Intentional angry lid tilt missing or excessive: '+face.id+'/'+role+' angle='+closedAxis.toFixed(2));
   }
   if(['09','20'].includes(face.id.slice(0,2)))check(Math.abs(closedAxis)<5,'Round-eye closure still rolls with circle gap: '+face.id+'/'+role+' angle='+closedAxis.toFixed(2));
  }
 }
 const report={version:5,checkedAt:new Date().toISOString(),passed:failures.length===0,rendererSha256:hash(drawnSource),baseRuntimeSha256:hash(runtimeSource),faceDataSha256:hash(dataSource),atlasSha256:hash(path.join(HERE,'atlas.json')),scope:{faces:40,eyes:rows.length,sourceClosedArcChecks:14,intentionalAngryTiltChecks:4,roundGapClosureChecks:4,pngLids:rows.filter(r=>r.renderedAs==='registered PNG lid').length,vectorLids:rows.filter(r=>r.renderedAs==='canonical vector squeeze').length},criteria:['Measured transformed PNG ink centerlines from actual drawImage commands, and verified vector squeeze paths against their actual canvas path commands. Reported glyph rotation alone is not used as proof.','Source closed arcs on faces 16, 21, 22, 23, 26, 29 and 35 retain their curvature sign and endpoint attitude within 12 degrees.','Angry faces 02 and 04 retain mirrored lid tilt: left positive, right negative, with a broad 5 to 25 degree range.','Round faces 09 and 20 close within 5 degrees of screen level.','Ranges are visual acceptance choices, not claims about anatomical correctness.'],rows,failures,warnings,limitations:['The tests assess fully closed poses. Root browser review must also judge the visible closing and reopening motion.','Centerline measurement approximates a stylized thick stroke; it does not measure GPU antialiasing.','Preserving source arc concavity is distinct from forcing all eyes to the same closure curve.']};
 const basename=process.argv.includes('--candidate')?'blink_orientation_candidate_v5':'blink_orientation_checks_v5';
 fs.writeFileSync(path.join(HERE,basename+'.json'),JSON.stringify(report,null,2)+'\n');
 const lines=['# Final blink orientation checks','',report.passed?'PASS':'FAIL','', 'Physical raster ink was measured after the real renderer canvas transforms. Proposed angle bands are visual acceptance choices, not anatomical targets.', '', '| Face | Side | Part | Visible closed angle | Source arc curvature | Closed curvature |','|---|---|---|---:|---:|---:|'];
 for(const r of rows)lines.push('| '+r.face+' | '+r.role+' | '+r.part+' | '+r.closedVisibleAxisDegrees.toFixed(2)+' | '+r.canonicalCurve.quadratic.toFixed(3)+' | '+r.closedCurve.quadratic.toFixed(3)+' |');
 lines.push('',...failures.map(f=>'Failure: '+f),'','Renderer SHA-256: '+report.rendererSha256);
 fs.writeFileSync(path.join(HERE,basename+'.md'),lines.join('\n')+'\n');
 console.log(JSON.stringify({passed:report.passed,scope:report.scope,renderer:report.rendererSha256,failures},null,2));rig.destroy();if(failures.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});
`;
vm.runInNewContext(prefix+audit,{require,__dirname,console,Buffer,process,Uint8ClampedArray},{filename:__filename});
