'use strict';
const fs=require('node:fs'),path=require('node:path');
const sharp=require(process.env.MIST_SHARP_PATH||'<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const here=__dirname,manifest=JSON.parse(fs.readFileSync(path.join(here,'manifest.json')));
(async()=>{
 const result={purpose:'Supplement manual contact-sheet review with visible filled-marker positions. These estimates do not establish motion quality.',assets:{}};
 for(const id of ['connecting','planning']){
  const asset=manifest.assets[id];if(!asset)continue;const positions=[];
  for(let i=4;i<20;i++){
   const frame=asset.frames[i],{data,info}=await sharp(path.join(here,frame.file)).ensureAlpha().raw().toBuffer({resolveWithObject:true});
   const [left,top,width,height]=frame.bounds,profile=[];let mass=0,xSum=0,ySum=0;
   const xMin=Math.ceil(left+(id==='connecting'?width*.16:0)),xMax=Math.floor(left+width-(id==='connecting'?width*.16:0));
   for(let x=xMin;x<xMax;x++){
    let count=0,ys=0;for(let y=Math.max(0,top);y<Math.min(info.height,top+height);y++)if(data[(y*info.width+x)*4+3]>80){count++;ys+=y;}
    const excess=Math.max(0,count-(id==='connecting'?7:8));profile.push({x,excess});if(excess){mass+=excess;xSum+=x*excess;ySum+=ys/count*excess;}
   }
   positions.push({frame:i,markerMass:mass,center:mass?[+(xSum/mass).toFixed(2),+(ySum/mass).toFixed(2)]:null,trackFraction:mass?+((xSum/mass-left)/width).toFixed(3):null});
  }result.assets[id]={sourceSha256:asset.sourceSha256,positions};
 }
 fs.writeFileSync(path.join(here,'qa_semantic_probe.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
