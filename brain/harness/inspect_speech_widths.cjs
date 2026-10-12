'use strict';
const fs=require('node:fs'),vm=require('node:vm');
const context={window:{}};vm.runInNewContext(fs.readFileSync('brain/face_assets/app/app_data.js','utf8'),context);
const data=context.window.MIST_DATA,runtime=require('../ui/static/face_runtime.js'),drawn=require('../ui/static/drawn_face_renderer.js');
const atlas=JSON.parse(fs.readFileSync('brain/art_direction/artist_studio_20260916/reuse/drawn/atlas.json','utf8'));
const images=Object.fromEntries(Object.values(atlas.assets).flatMap(asset=>[[asset.id,{}],[asset.file,{}],...asset.frames.filter(frame=>frame.file).map(frame=>[frame.file,{}]) ]));
(async()=>{
 const face=drawn.create(null,{data,runtime,atlas,images,reducedMotion:true,autoStart:false,now:()=>0});await face.ready;
 let viseme='LNT';face.startSpeech({sample:()=>({active:true,viseme,time:1,amount:1}),clock:()=>1});
 const rows=[];
 for(const expression of data.faces){face.setExpression(expression.id);const widths={};let p;
  for(const pose of ['AA','LNT','FV','TH','OO']){viseme=pose;p=face.snapshot().drawnPlacements.find(item=>item.role==='mouth');if(p){const frame=atlas.assets[p.id].frames[p.frame],ink=frame.inkBounds||frame;widths[pose]=+(ink.w*(frame.sourceScale??1)*p.scale).toFixed(2);}}
  rows.push({face:expression.id,...widths,scale:p?.scale,masterWidth:p?p.master.w*p.scale:null});
 }
 console.log(JSON.stringify(rows,null,2));face.destroy();
})().catch(error=>{console.error(error);process.exitCode=1;});
