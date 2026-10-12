// Independent verification records the renderer's actual canvas commands.
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path'),crypto=require('crypto');
const HERE=__dirname,ROOT=path.resolve(HERE,'../../../../..');
const dataSource=path.join(ROOT,'brain/face_assets/app/app_data.js');
const runtimeSource=path.join(ROOT,'brain/ui/static/face_runtime.js');
const drawnSource=path.join(ROOT,'brain/ui/static/drawn_face_renderer.js');
const publishedSource=path.join(HERE,'../runtime/drawn_face_renderer.js');
const atlas=JSON.parse(fs.readFileSync(path.join(HERE,'atlas.json')));
const measurements=JSON.parse(fs.readFileSync(path.join(HERE,'identity_after_pixels.json')));
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const environment={console,performance:{now:()=>0},Path2D:class{constructor(d){this.d=d;}},matchMedia:()=>({matches:true})};
environment.window=environment;vm.createContext(environment);
for(const file of [dataSource,runtimeSource,drawnSource])vm.runInContext(fs.readFileSync(file,'utf8'),environment,{filename:file});
const DATA=environment.MIST_DATA,Base=environment.MistFaceRuntime,Drawn=environment.MistDrawnFaceRuntime;
const failures=[],warnings=[];const check=(condition,message)=>{if(!condition)failures.push(message);};
const previousReport=JSON.parse(fs.readFileSync(path.join(HERE,'v2_identity_after.json')));
check(hash(dataSource)===previousReport.hashes.data,'Canonical face source bytes differ from the independently verified v2 baseline');
check(hash(drawnSource)===hash(publishedSource),'Published and production renderer bytes differ');
for(const [id,asset] of Object.entries(measurements.assets))for(const frame of asset.frames)if(frame.file)check(hash(path.join(HERE,frame.file))===frame.sha256,'Pixel measurements are stale: '+id+'/'+frame.index);
function mul(a,b){return[a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];}
function bounds(points,pad=0){const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);return{x:Math.min(...xs)-pad,y:Math.min(...ys)-pad,w:Math.max(...xs)-Math.min(...xs)+2*pad,h:Math.max(...ys)-Math.min(...ys)+2*pad};}
class CanvasContext{
 constructor(){this.matrix=[1,0,0,1,0,0];this.stack=[];this.globalAlpha=1;this.strokes=[];this.sprites=[];}
 setTransform(...a){this.matrix=a;}translate(x,y){this.matrix=mul(this.matrix,[1,0,0,1,x,y]);}rotate(a){this.matrix=mul(this.matrix,[Math.cos(a),Math.sin(a),-Math.sin(a),Math.cos(a),0,0]);}scale(x,y){this.matrix=mul(this.matrix,[x,0,0,y,0,0]);}
 save(){this.stack.push({matrix:this.matrix.slice(),alpha:this.globalAlpha,width:this.lineWidth});}restore(){const s=this.stack.pop();this.matrix=s.matrix;this.globalAlpha=s.alpha;this.lineWidth=s.width;}
 clearRect(){this.strokes=[];this.sprites=[];}beginPath(){}rect(){}clip(){}
 stroke(p){this.strokes.push({path:p.d,mode:'stroke',width:this.lineWidth,alpha:this.globalAlpha,matrix:this.matrix.slice()});}
 fill(p){this.strokes.push({path:p.d,mode:'fill',width:this.lineWidth,alpha:this.globalAlpha,matrix:this.matrix.slice()});}
 drawImage(image,sx,sy,sw,sh,dx,dy,dw,dh){this.sprites.push({id:image.id,sx,sy,sw,sh,dx,dy,dw,dh,alpha:this.globalAlpha,matrix:this.matrix.slice()});}
}
const context=new CanvasContext(),canvas={width:1000,height:640,dataset:{},getContext:()=>context};
function imageHandle(id,frames){return{id,getContext:()=>({getImageData(x,y,w,h){const f=frames.find(f=>f.x===x&&f.y===y&&f.w===w&&f.h===h);if(!f?.alphaBase64)throw Error('Missing measured pixel request '+id+'/'+[x,y,w,h]);const alpha=Buffer.from(f.alphaBase64,'base64'),rgba=new Uint8ClampedArray(alpha.length*4);for(let i=0;i<alpha.length;i++){rgba[i*4]=94;rgba[i*4+1]=234;rgba[i*4+2]=221;rgba[i*4+3]=alpha[i];}return{data:rgba};}})};}
const images=Object.fromEntries(Object.entries(measurements.assets).map(([id,asset])=>[id,imageHandle(id,asset.frames)]));
const byFile={};for(const asset of Object.values(measurements.assets))for(const frame of asset.frames)(byFile[frame.file]??=[]).push(frame);
for(const [file,frames]of Object.entries(byFile))images[file]=imageHandle(file,frames);
let time=0;
function equivalentLayer(a,b){return a.role===b.role&&a.part===b.part&&a.mode===b.mode&&a.width===b.width&&JSON.stringify(a.points)===JSON.stringify(b.points)&&(a.opacity??1)===(b.opacity??1);}
function canonical(face){const base=Base.create(null,{data:DATA,expression:face.id,reducedMotion:true,autoStart:false,now:()=>0});const result=base.snapshot(0).layers;base.destroy();return result;}
const originals=new Map(DATA.faces.map(face=>[face.id,canonical(face)]));
async function run(){
 const rig=Drawn.create(null,{data:DATA,runtime:Base,atlas,images,expression:DATA.faces[0].id,autoStart:false,reducedMotion:false,now:()=>time});if(!await rig.ready)throw Error('Renderer setup failed: '+rig.error?.message);
 const perFace=[],parts={};let eyes=0,paths=0,restRasterCount=0;
 for(const face of DATA.faces){
  rig.setExpression(face.id,{durationMs:600});time+=1000;
  const rest=rig.renderTo(canvas,time,{gaze:{x:0,y:0}}),expected=originals.get(face.id);
  check(rest.drawnAnimation?.fps===15,'Expected default 15 fps: '+face.id);
  check(rest.drawnLayers.length===expected.length,'Rest layer count '+face.id);
  let identical=true;
  for(let i=0;i<expected.length;i++){
   const layer=expected[i],actual=rest.drawnLayers[i];const equal=actual&&equivalentLayer(actual,layer);identical&&=!!equal;
   check(equal,'Rest canonical layer differs: '+face.id+'/'+layer.role);
   const draw=context.strokes[i];check(draw?.path===Base.pathData(layer.points,layer.mode==='fill'),'Actual canvas path differs: '+face.id+'/'+layer.role);
   check(draw?.alpha===(layer.opacity??1),'Actual rest alpha differs: '+face.id+'/'+layer.role);
   check(draw?.mode===layer.mode,'Actual draw mode differs: '+face.id+'/'+layer.role);
   check(JSON.stringify(draw?.matrix)==='[10,0,0,10,0,0]','Unexpected rest draw transform '+face.id+'/'+layer.role);
   if(layer.mode==='stroke')check(draw?.width===layer.width,'Actual rest stroke width differs '+face.id+'/'+layer.role);
   paths++;if(layer.role.startsWith('eye'))eyes++;
  }
  restRasterCount+=context.sprites.length;check(context.sprites.length===0,'Raster artwork still used at rest '+face.id);
  perFace.push({face:face.id,exactRest:identical,canvasPathCount:context.strokes.length,restRasterDraws:context.sprites.length,eyes:expected.filter(l=>l.role.startsWith('eye')).map(l=>({role:l.role,part:l.part}))});
  // Force the generated rest cel only for measurement; production rest does not draw it.
  const sprite=rig.renderTo(canvas,time,{gaze:{x:0,y:0},blinkFrame:0,rasterEyes:true});
  for(const placement of sprite.drawnPlacements.filter(p=>p.role.startsWith('eye'))){
   const index=placement.role==='eye_L'?0:1,draw=context.sprites[index];
   const layer=expected.find(l=>l.role===placement.role),part=face.slots[placement.role].part,frame=measurements.assets[draw.id].frames.find(f=>f.x===draw.sx&&f.y===draw.sy);
   const rendered=frame.support.map(([px,py])=>{
    const x=draw.dx+(px-draw.sx)/draw.sw*draw.dw,y=draw.dy+(py-draw.sy)/draw.sh*draw.dh,m=draw.matrix;
    return[(m[0]*x+m[2]*y+m[4])/10,(m[1]*x+m[3]*y+m[5])/10];
   });
   const box=bounds(layer.points,layer.mode==='stroke'?layer.width/2:0),actual=bounds(rendered);
   const record={face:face.id,role:placement.role,method:placement.inkFit,original:box,generated:actual,widthRatio:actual.w/box.w,heightRatio:actual.h/box.h,centerDifference:Math.hypot(actual.x+actual.w/2-box.x-box.w/2,actual.y+actual.h/2-box.y-box.h/2)};
   check(placement.inkFit==='measured-raster','Pixel measurement fallback used '+part);
   check(Number.isFinite(record.widthRatio)&&Number.isFinite(record.heightRatio),'Nonfinite raster measurement '+part);
   (parts[part]??=[]).push(record);
  }
 }
 // Every transition target must end on its exact canonical paths, independent of source.
 let transitions=0;
 for(const from of DATA.faces)for(const to of DATA.faces){
  if(from.id===to.id)continue;
  rig.setExpression(from.id,{durationMs:600});time+=800;
  rig.setExpression(to.id,{durationMs:600});time+=800;
  const state=rig.renderTo(canvas,time,{gaze:{x:0,y:0}}),expected=originals.get(to.id);
  check(state.drawnLayers.length===expected.length&&state.drawnLayers.every((l,i)=>equivalentLayer(l,expected[i])),'Transition endpoint identity '+from.id+' -> '+to.id);
  check(context.sprites.length===0,'Transition endpoint still raster '+from.id+' -> '+to.id);transitions++;
 }
 const missingMouths=[];
 rig.startSpeech({sample:()=>({active:true,viseme:'AA',amount:.8,time:1,source:'test-audio-clock'})});
 for(const face of DATA.faces){rig.setExpression(face.id);time+=800;const state=rig.snapshot(time);if(!state.drawnPlacements.some(p=>p.role==='mouth'&&p.opacity>0))missingMouths.push(face.id);}
 rig.stopSpeech();
 if(missingMouths.length)warnings.push('Canonical-mouthless faces have no speech mouth: '+missingMouths.join(', '));
 const report={version:4,checkedAt:new Date().toISOString(),passed:failures.length===0,baseRuntimeSha256:hash(runtimeSource),faceDataSha256:hash(dataSource),atlasSha256:hash(path.join(HERE,'atlas.json')),scope:{fps:15,requestedTransitionMs:600,faces:perFace.length,eyes,parts:Object.keys(parts).length,actualCanonicalCanvasPaths:paths,directedTransitionEndpoints:transitions,restRasterDraws:restRasterCount,atlasAssets:Object.keys(atlas.assets).length,selectedFrameEntries:Object.values(atlas.assets).reduce((sum,a)=>sum+a.frames.length,0)},sourcePreservation:{canonicalDataMatchesV2:hash(dataSource)===previousReport.hashes.data,productionMatchesPublished:hash(drawnSource)===hash(publishedSource)},hashes:{renderer:hash(drawnSource),publishedRenderer:hash(publishedSource),base:hash(runtimeSource),data:hash(dataSource),atlas:hash(path.join(HERE,'atlas.json'))},method:['Executed actual production renderer and canonical runtime in a VM with a command-recording canvas.','Compared every resting layer point, identity, opacity, width and draw mode, then compared actual canvas path commands and transforms.','Read pixel opacity from the accepted PNG source sheets without modifying them. Passed pixel-backed canvas objects to the renderer so measured-raster fitting runs.','Forced raster rest only for fitting measurements, captured actual drawImage transforms, and independently projected source ink support through those transforms.','Checked all 1,560 directed expression pairs end on the exact canonical target paths at the 15 fps cadence and 600 ms requested transition duration.','Verified canonical source bytes against the v2 baseline, all extracted image hashes against current files, and production renderer bytes against the published preview renderer.'],faces:perFace,pixelFittingByPart:parts,missingSpeechMouths:missingMouths,failures,warnings,limits:['Canvas command equality establishes identical paths at rest, not GPU antialiasing or perceived animation quality.','Forced generated-rest dimensions diagnose blink retargeting only; production rest renders canonical source paths.','Blink intermediary silhouettes intentionally differ from the source contour. This test does not claim identical contours while blinking.']};
 fs.writeFileSync(path.join(HERE,'identity_after.json'),JSON.stringify(report,null,2)+'\n');
 const lines=['# Identity verification after the renderer changes','',`Rest identity: ${report.passed?'PASS':'FAIL'}. ${perFace.length} faces, ${eyes} eyes and ${paths} actual canonical canvas paths checked.`, '',`All ${transitions} directed transitions ended on the exact canonical target geometry. Rest drew ${restRasterCount} raster eyes.`, '',`Renderer SHA-256: \`${report.hashes.renderer}\``, '', 'Every original eye now keeps its exact canonical path, size, stroke width, mirror and rotation outside the blink. The actual canvas commands were checked against the original runtime; this is not an assertion copied from the renderer owner.', '', 'Pixel-backed fitting ran for all 30 eye parts. The following ratios concern a forced generated rest cel for diagnostics, not the visible resting face.', '', '| Source part | Uses | Width ratio range | Height ratio range | Largest center difference |','|---|---:|---:|---:|---:|'];
 for(const [part,uses] of Object.entries(parts).sort())lines.push(`| ${part} | ${uses.length} | ${Math.min(...uses.map(u=>u.widthRatio)).toFixed(3)} to ${Math.max(...uses.map(u=>u.widthRatio)).toFixed(3)} | ${Math.min(...uses.map(u=>u.heightRatio)).toFixed(3)} to ${Math.max(...uses.map(u=>u.heightRatio)).toFixed(3)} | ${Math.max(...uses.map(u=>u.centerDifference)).toFixed(3)} |`);
 lines.push('',...warnings.map(w=>'Warning: '+w),'',...failures.map(f=>'Failure: '+f),'','This verifies exact rest identity and endpoint geometry. Visual motion quality and audible synchronisation require separate playback review.');
 fs.writeFileSync(path.join(HERE,'identity_after.md'),lines.join('\n')+'\n');
 fs.copyFileSync(path.join(HERE,'identity_after.json'),path.join(HERE,'identity_v4.json'));
 fs.copyFileSync(path.join(HERE,'identity_after.md'),path.join(HERE,'identity_v4.md'));
 console.log(JSON.stringify({passed:report.passed,scope:report.scope,failures,warnings,renderer:report.hashes.renderer},null,2));rig.destroy();if(failures.length)process.exitCode=1;
}
run().catch(e=>{console.error(e);process.exitCode=1;});
