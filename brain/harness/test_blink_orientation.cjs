'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),cp=require('node:child_process'),crypto=require('node:crypto');
const ROOT=path.resolve(__dirname,'../..'),DRAWN=path.join(ROOT,'brain/art_direction/artist_studio_20260916/reuse/drawn');
const inkRead=cp.spawnSync('python',[path.join(__dirname,'blink_orientation_pixels.py')],{encoding:'utf8'});if(inkRead.status!==0)throw Error(inkRead.stderr);
const ink=JSON.parse(inkRead.stdout),context={window:{}};
vm.runInNewContext(fs.readFileSync(path.join(ROOT,'brain/face_assets/app/app_data.js'),'utf8'),context);
const data=context.window.MIST_DATA,atlas=JSON.parse(fs.readFileSync(path.join(DRAWN,'atlas.json'),'utf8'));
const targets=JSON.parse(fs.readFileSync(path.join(DRAWN,'blink_orientation_review_v5.json'),'utf8')).rows;
const runtime=require('../ui/static/face_runtime.js'),drawn=require('../ui/static/drawn_face_renderer.js');
const selected=process.argv.find(arg=>arg.startsWith('--face='))?.slice(7),selectedFaces=data.faces.filter(face=>!selected||face.id.startsWith(selected));assert(selectedFaces.length);
const images=Object.fromEntries(Object.values(atlas.assets).flatMap(asset=>[[asset.id,{id:asset.id}],[asset.file,{id:asset.id}],...asset.frames.filter(f=>f.file).map(f=>[f.file,{id:asset.id}]) ]));
const mul=(a,b)=>[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];
const degrees=rad=>rad*180/Math.PI,round=value=>+value.toFixed(3),roles=['eye_L','eye_R'];
const axis=angle=>{while(angle>90)angle-=180;while(angle<=-90)angle+=180;return angle;};
let matrix=[1,0,0,1,0,0],stack=[],calls=[];
const paint={setTransform(...values){matrix=values;},save(){stack.push(matrix.slice());},restore(){matrix=stack.pop();},
  translate(x,y){matrix=mul(matrix,[1,0,0,1,x,y]);},scale(x,y){matrix=mul(matrix,[x,0,0,y,0,0]);},rotate(a){matrix=mul(matrix,[Math.cos(a),Math.sin(a),-Math.sin(a),Math.cos(a),0,0]);},
  clearRect(){},beginPath(){},rect(){},clip(){},fill(p){calls.push({type:'vector',path:p.value,matrix:matrix.slice(),lineCap:this.lineCap});},stroke(p){calls.push({type:'vector',path:p.value,matrix:matrix.slice(),lineCap:this.lineCap});},
  drawImage(image,sx,sy,sw,sh,dx,dy,dw,dh){calls.push({type:'sprite',image,matrix:matrix.slice(),sx,sy,sw,sh,dx,dy,dw,dh});}};
global.Path2D=class{constructor(value){this.value=value;}};
const canvas={width:100,height:64,dataset:{},getContext(){return paint;}};
const transform=(p,m)=>[m[0]*p[0]+m[2]*p[1]+m[4],m[1]*p[0]+m[3]*p[1]+m[5]];
const endpointAngle=points=>axis(degrees(Math.atan2(points.at(-1)[1]-points[0][1],points.at(-1)[0]-points[0][0])));
function rasterAngle(call,family) {
  const vector=ink[family].principalVector,sx=call.dw/call.sw,sy=call.dh/call.sh,m=call.matrix;
  return axis(degrees(Math.atan2(m[1]*vector[0]*sx+m[3]*vector[1]*sy,m[0]*vector[0]*sx+m[2]*vector[1]*sy)));
}
function concavity(points){
  const sorted=points.slice().sort((a,b)=>a[0]-b[0]),left=sorted[0],right=sorted.at(-1),width=right[0]-left[0];
  const middle=points.filter(p=>Math.abs(p[0]-(left[0]+right[0])/2)<width*.15);
  return middle.reduce((sum,p)=>sum+p[1]-(left[1]+(right[1]-left[1])*(p[0]-left[0])/width),0)/(middle.length||1);
}
(async()=>{
  let time=0;
  const face=drawn.create(null,{data,runtime,atlas,images,autoStart:false,reducedMotion:true,now:()=>time});assert(await face.ready);
  const rows=[];let phaseChecks=0,arcChecks=0,restChecks=0,rawRasterChecks=0;
  for(const expression of selectedFaces) {
    face.setExpression(expression.id);time+=1000;
    const original=runtime.create(null,{data,expression:expression.id,reducedMotion:true,autoStart:false});
    const rest=original.snapshot().layers,restState=face.renderTo(canvas,time,{gaze:{x:0,y:0}});
    for(const role of roles){assert.deepEqual(restState.drawnLayers.find(layer=>layer.role===role),rest.find(layer=>layer.role===role),'Exact canonical resting eye');restChecks++;}
    const overrides={gaze:{x:0,y:0},blinkFrame:{}};
    for(const role of roles)overrides.blinkFrame[role]=ink[drawn.helpers.PART_FAMILY[expression.slots[role].part]].frame;
    calls=[];const state=face.renderTo(canvas,time,overrides),sprites=calls.filter(call=>call.type==='sprite');let spriteIndex=0;
    for(const role of roles) {
      const p=state.drawnPlacements.find(item=>item.role===role&&item.opacity>0),slot=expression.slots[role],family=drawn.helpers.PART_FAMILY[slot.part];
      const target=targets.find(row=>row.face===expression.id&&row.role===role);assert(target);
      let worldAngle,method;
      if(p) {
        const call=sprites[spriteIndex++];assert(call,'Renderer paints its registered closed cel');
        worldAngle=rasterAngle(call,family);method='actual raster draw matrix + source PNG PCA';
        assert.equal(p.kind,'eyelid');assert(Math.abs(degrees(p.sourceAngle)-ink[family].principalAngleDegrees)<.001,'Fallback matches accepted PNG ink');
        assert(call.matrix[3]>0,'Closed lid never flips vertically');
      } else {
        const layer=state.drawnLayers.find(item=>item.role===role),pathData=runtime.pathData(layer.points,layer.mode==='fill');
        const call=calls.find(call=>call.type==='vector'&&call.path===pathData);assert(call,'Renderer paints the squeezed source contour');
        const coordinates=[...call.path.matchAll(/-?\d+\.\d+/g)].map(match=>Number(match[0]));
        worldAngle=endpointAngle([coordinates.slice(0,2),coordinates.slice(-2)].map(point=>transform(point,call.matrix)));method='actual vector path endpoints + draw matrix';
        const before=concavity(rest.find(item=>item.role===role).points),after=concavity(layer.points);
        if(Math.abs(before)>.05)assert(before*after>0,'A closed arc retains its original concavity');
        assert(Math.abs(after)<=Math.abs(before)+.1,'Squeeze does not inflate the arc');arcChecks++;
      }
      const error=axis(worldAngle-target.recommendedTargetDegrees);
      rows.push({face:expression.id,role,part:slot.part,family,actualClosedAxisDeg:round(worldAngle),reviewedTargetDeg:round(target.recommendedTargetDegrees),errorDeg:round(error),method,passed:Math.abs(error)<1});
    }
    for(const role of roles) {
      const source=rest.find(layer=>layer.role===role),family=drawn.helpers.PART_FAMILY[expression.slots[role].part],asset=atlas.assets[family];
      const expected={rest:0,anticipation:.12,closing:.5,near_closed:.8,closed:1,opening_low:.75,opening:.4,settled:0};
      for(const [index,frame]of asset.frames.entries()) {
        const state=face.renderTo(canvas,time,{gaze:{x:0,y:0},blinkFrame:{[role]:index}}),view=state.drawnVisuals.find(view=>view.role===role);
        assert.equal(view.closure,expected[frame.pose],'Inspector aperture follows the requested phase');
        const layers=state.drawnLayers.filter(layer=>layer.role===role),placements=state.drawnPlacements.filter(p=>p.role===role&&p.opacity>0);
        assert.equal(layers.length+placements.length,1,'Only one visible eye at each phase');
        if(view.closure>0&&view.closure<.65&&!['arc','bar'].includes(family)) {
          assert(layers[0].blinkClip,'Early closure uses an eyelid-plane clip');assert.deepEqual(layers[0].points,source.points,'Early closure does not rotate or squash the source eye');
          assert(layers[0].blinkClip.bottom>layers[0].blinkClip.top);
          const clip=layers[0].blinkClip,c=Math.cos(clip.angle),s=Math.sin(clip.angle);
          const lowest=Math.max(...source.points.map(([x,y])=>-s*(x-clip.x)+c*(y-clip.y)))+(source.mode==='stroke'?source.width/2:0);
          assert(clip.bottom>lowest,'Early occlusion retains the entire lower contour instead of cutting a flat bucket bottom');
          if(source.mode==='stroke') {
            assert(layers[0].blinkSegments?.length,'Visible source strokes are geometrically trimmed');
            if(family==='round')assert.equal(layers[0].blinkSegments.length,1,'Round eyes retain one continuous curve without detached gap fragments');
            for(const points of layers[0].blinkSegments)for(const [x,y]of points)assert(-s*(x-clip.x)+c*(y-clip.y)>=clip.top-1e-8,'Trimmed path follows the intended half-plane');
          }
          assert(Math.abs(degrees(layers[0].blinkClip.angle)-targets.find(row=>row.face===expression.id&&row.role===role).recommendedTargetDegrees)<1,'Early phase stays within the reviewed plane tolerance');
        }
        phaseChecks++;
      }
      const raw=face.renderTo(canvas,time,{gaze:{x:0,y:0},blinkFrame:{[role]:0},rasterEyes:true});
      assert(raw.drawnPlacements.some(p=>p.role===role&&p.opacity===1&&p.fit),'Raw-sheet inspection stays explicit');rawRasterChecks++;
    }
    original.destroy();
  }
  face.destroy();
  const animated=drawn.create(null,{data,runtime,atlas,images,autoStart:false,reducedMotion:false,now:()=>time});assert(await animated.ready);
  let transitionChecks=0,retargetChecks=0;const picture=state=>JSON.stringify({layers:state.drawnLayers,placements:state.drawnPlacements,visuals:state.drawnVisuals});
  for(const [from,to]of [['09_happy_03_manual','31_sad_06_manual'],['35_sad_10_manual','09_happy_03_manual'],['09_happy_03_manual','35_sad_10_manual'],['35_sad_10_manual','12_happy_09_manual']]) {
    animated.setExpression(from);time+=1400;animated.blink();time+=133.333333;
    const before=picture(animated.snapshot());animated.setExpression(to,{durationMs:1200});assert.equal(picture(animated.snapshot()),before,'Closed retarget preserves displayed geometry');retargetChecks++;
    const start=time;
    for(const elapsed of [66.7,133.4,266.7,400,533.4,666.7,800,933.4,1066.7,1200]) {
      time=start+elapsed;const state=animated.renderTo(canvas,time,{gaze:{x:0,y:0}});
      for(const role of roles) {
        assert.equal(state.drawnLayers.filter(layer=>layer.role===role).length+state.drawnPlacements.filter(p=>p.role===role&&p.opacity>0).length,1,'One eye through every transition phase');
        const p=state.drawnPlacements.find(p=>p.role===role&&p.opacity>0);
        if(p?.kind==='eye_bridge')assert(Math.abs(degrees(p.planeAngle))<=20.0001,'Bridge stays within reviewed directions');
      }
      assert(Number.isFinite(state.drawnTransition.progress));transitionChecks++;
    }
    time+=1000;
  }
  animated.destroy();
  let fleckChecks=0;time=0;
  const fleckFace=drawn.create(null,{data,runtime,atlas,images,expression:'35_sad_10_manual',autoStart:false,reducedMotion:false,now:()=>time});assert(await fleckFace.ready);
  const inspectTrim=(expectedMin,expectedMax)=>{
    calls=[];const state=fleckFace.renderTo(canvas,time,{gaze:{x:0,y:0}});
    for(const role of roles) {
      const view=state.drawnVisuals.find(view=>view.role===role),layer=state.drawnLayers.find(layer=>layer.role===role);
      assert(view.closure>=expectedMin&&view.closure<=expectedMax,'Reproduce the visible mid-phase aperture');
      assert.equal(layer.blinkSegments.length,1,'No detached cyan fleck survives beside the round eye');
      const points=layer.blinkSegments[0],pathData=runtime.pathData(points,false),emitted=calls.filter(call=>call.type==='vector'&&call.path===pathData);
      assert.equal(emitted.length,1,'Actual canvas receives exactly the main visible curve');assert.equal(emitted[0].lineCap,'round','New cut ends are rounded');
      const length=points.slice(1).reduce((sum,p,i)=>sum+Math.hypot(p[0]-points[i][0],p[1]-points[i][1]),0);
      assert(length>layer.width*4,'Remaining path is the eye curve, not a tiny isolated stroke');fleckChecks++;
    }
  };
  fleckFace.setExpression('09_happy_03_manual',{durationMs:600});time=8000/15;inspectTrim(.2,.3);
  time=1000;fleckFace.blink();time+=1000/15;inspectTrim(.5,.6);fleckFace.destroy();
  let reflectionChecks=0;const reflected=JSON.parse(JSON.stringify(data)),mirrorId='24_neutral_2_01_manual';
  for(const role of roles) {
    const slot=reflected.faces.find(face=>face.id===mirrorId).slots[role];slot.x=100-slot.x;slot.rot=-(slot.rot||0);slot.mirror=!slot.mirror;
  }
  const paired=[];
  for(const source of [data,reflected]) {
    const renderer=drawn.create(null,{data:source,runtime,atlas,images,expression:mirrorId,autoStart:false,reducedMotion:true,now:()=>0});assert(await renderer.ready);
    calls=[];renderer.renderTo(canvas,0,{gaze:{x:0,y:0},blinkFrame:{eye_L:ink.slot.frame,eye_R:ink.slot.frame}});
    paired.push(calls.filter(call=>call.type==='sprite').map(call=>rasterAngle(call,'slot')));renderer.destroy();
  }
  for(let i=0;i<2;i++){assert(Math.abs(axis(paired[0][i]+paired[1][i]))<.1,'Reflected slot eye has the opposite actual closed direction');reflectionChecks++;}
  const failures=rows.filter(row=>!row.passed),report={passed:failures.length===0,checkedAt:new Date().toISOString(),rendererSha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT,'brain/ui/static/drawn_face_renderer.js'))).digest('hex'),faces:selectedFaces.length,eyes:rows.length,failedEyes:failures.length,maxErrorDeg:Math.max(...rows.map(row=>Math.abs(row.errorDeg))),restChecks,phaseChecks,arcChecks,rawRasterChecks,transitionChecks,retargetChecks,
    method:'Actual renderer closed-eye output versus independent canonical-geometry targets. Raster axes combine captured Canvas matrices with read-only source PNG PCA; source arcs use emitted path endpoints. Early phases verify unchanged canonical points behind a plane clip.',sourceInk:ink,failures,eyesMeasured:rows,
    fleckChecks,reflectionChecks,checks:['Original paths exact at rest','Reviewed closing directions with source-cel PCA compensation','Original contour orientation during early closing','Distinct manual pose apertures','Closed arcs retain concavity','One visible eye per phase and transition','Closed retarget preserves displayed picture','Round mid-phase paths have rounded endpoints and no detached gap flecks','Reflected face 24 keeps opposite closed-lid directions','Raw-sheet diagnostic preserved'],
    limitations:['Geometry cannot establish natural motion quality; root performs browser review.','Headless image handles use accepted-sheet PCA; browsers also measure keyed pixels when available.']};
  const suffix=selected?'_'+selected.replace(/[^a-zA-Z0-9_-]/g,''):'';
  fs.writeFileSync(path.join(__dirname,'blink_orientation_report'+suffix+'.json'),JSON.stringify(report,null,2)+'\n');
  const lines=['# Blink orientation regression','',`Renderer: ${report.rendererSha256}`,'',`${rows.length} eyes measured; ${failures.length} outside the reviewed direction tolerance. Maximum error: ${report.maxErrorDeg} degrees.`, '',`${restChecks} exact rest checks, ${phaseChecks} inspector phases, ${arcChecks} contour checks, ${transitionChecks} transition samples, ${retargetChecks} closed retargets and ${fleckChecks} mid-phase emitted-path checks.`, '', '| Face | Eye | Family | Actual | Reviewed | Error |','|---|---|---|---:|---:|---:|',...rows.map(row=>`| ${row.face} | ${row.role} | ${row.family} | ${row.actualClosedAxisDeg} | ${row.reviewedTargetDeg} | ${row.errorDeg} |`),'',...report.limitations.map(text=>'- '+text),''];
  fs.writeFileSync(path.join(__dirname,'blink_orientation_report'+suffix+'.md'),lines.join('\n'));
  console.log(JSON.stringify({passed:report.passed,rendererSha256:report.rendererSha256,eyes:rows.length,failedEyes:failures.length,maxErrorDeg:report.maxErrorDeg,restChecks,phaseChecks,arcChecks,transitionChecks,retargetChecks,fleckChecks,reflectionChecks,failures},null,2));if(failures.length)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
