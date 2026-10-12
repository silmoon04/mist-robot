/* Slice generated sprite sheets and register their cels without redrawing them. */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const sharp=require(process.env.MIST_SHARP_PATH||'<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=__dirname;
const eyePoses=['open','anticipation','half_closed','closed','opening_low','opening','gaze_left','gaze_right'];
const activities=[
 ['coding','Coding','eye_hook','eye_hook','neutral','side'],
 ['reading','Reading files','eye_round','eye_round','neutral','side'],
 ['writing','Writing','eye_half','eye_hook','neutral','side'],
 ['email','Checking email','eye_arc','eye_round','smile','side'],
 ['searching','Searching','eye_round','eye_round','neutral','side'],
 ['planning','Planning','eye_up','eye_up','neutral','above'],
 ['calculating','Calculating','eye_half','eye_half','neutral','above'],
 ['connecting','Connecting','eye_round','eye_round','smile','above'],
 ['checking','Checking results','eye_half','eye_round','neutral','side'],
].map(([id,label,left,right,mouth,placement])=>({id,label,eyes:[left,right],mouth,placement}));
const required=['eye_round','eye_hook','eye_half','eye_up','eye_arc',...activities.map(a=>a.id)];
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
async function extract(id){
 const file=path.join(root,'source',id+'.png');
 const type=id.startsWith('eye_')?'eye':'activity',columns=4,rows=type==='eye'?2:3;
 const source=await sharp(file).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 const {width,height}=source.info,rgba=source.data;
 // Keep native alpha when present; opaque sheets use their black matte.
 let transparent=0;for(let i=3;i<rgba.length;i+=4)if(rgba[i]<240)transparent++;
 const nativeAlpha=transparent>width*height*.05;
 const cells=[];
 for(let n=0;n<columns*rows;n++){
  const x0=Math.round(n%columns*width/columns),y0=Math.round(Math.floor(n/columns)*height/rows);
  const x1=Math.round((n%columns+1)*width/columns),y1=Math.round((Math.floor(n/columns)+1)*height/rows);
  const cw=x1-x0,ch=y1-y0,buf=Buffer.alloc(cw*ch*4);let minX=cw,minY=ch,maxX=-1,maxY=-1,ink=0;
  for(let y=0;y<ch;y++)for(let x=0;x<cw;x++){
   const si=((y0+y)*width+x0+x)*4,di=(y*cw+x)*4;
   const r=rgba[si],g=rgba[si+1],b=rgba[si+2];
   const alpha=nativeAlpha?rgba[si+3]:Math.round(Math.max(0,Math.min(1,(Math.min(g-r,b-r)-8)/48))*255);
   buf[di]=r;buf[di+1]=g;buf[di+2]=b;buf[di+3]=alpha;
   if(alpha>42){ink++;minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
  }
  if(ink<15)throw Error(id+' frame '+n+' is blank');
  if(minX<2||minY<2||maxX>=cw-2||maxY>=ch-2)throw Error(id+' frame '+n+' touches its cell boundary');
  const box={left:Math.max(0,minX-3),top:Math.max(0,minY-3),width:Math.min(cw-1,maxX+3)-Math.max(0,minX-3)+1,height:Math.min(ch-1,maxY+3)-Math.max(0,minY-3)+1};
  cells.push({buf,cw,ch,box,ink,sourceCell:[x0,y0,cw,ch],inkBox:[minX,minY,maxX-minX+1,maxY-minY+1]});
 }
 const maxWidth=Math.max(...cells.map(c=>c.box.width)),maxHeight=Math.max(...cells.map(c=>c.box.height));
 const scale=Math.min((type==='eye'?186:202)/maxWidth,(type==='eye'?176:202)/maxHeight);
 const frames=[];fs.mkdirSync(path.join(root,'frames',id),{recursive:true});
 for(let n=0;n<cells.length;n++){
  const c=cells[n],w=Math.max(1,Math.round(c.box.width*scale)),h=Math.max(1,Math.round(c.box.height*scale));
  const sprite=await sharp(c.buf,{raw:{width:c.cw,height:c.ch,channels:4}}).extract(c.box).resize(w,h,{kernel:'lanczos3'}).png().toBuffer();
  const left=Math.round((256-w)/2),top=type==='eye'?204-h:Math.round((256-h)/2);
  const out=await sharp({create:{width:256,height:256,channels:4,background:{r:0,g:0,b:0,alpha:0}}}).composite([{input:sprite,left,top}]).png().toBuffer();
  const rel=`frames/${id}/${String(n).padStart(2,'0')}.png`;fs.writeFileSync(path.join(root,rel),out);
  frames.push({file:rel,pose:type==='eye'?eyePoses[n]:`${n<4?'enter':n<8?'loop':'exit'}_${n%4}`,sourceCell:c.sourceCell,sourceBounds:c.inkBox,bounds:[left,top,w,h],sha256:hash(out)});
 }
 return {type,source:'source/'+id+'.png',sourceSha256:hash(fs.readFileSync(file)),sourceSize:[width,height],nativeAlpha,registration:type==='eye'?'common lower lid baseline':'center',scale,frames};
}
(async()=>{
 const assets={};
 for(const id of required){
  if(!fs.existsSync(path.join(root,'source',id+'.png'))){if(process.argv.includes('--partial'))continue;throw Error('Missing '+id);}
  assets[id]=await extract(id);
 }
 const studies=Object.fromEntries(Object.entries(assets).filter(([,a])=>a.type==='eye'));
 fs.writeFileSync(path.join(root,'eye_study_manifest.json'),JSON.stringify({active:false,reason:'User chose original MIST eyes on 2026-09-24',assets:studies},null,2)+'\n');
 for(const id of Object.keys(studies))delete assets[id];
 const complete=activities.every(a=>assets[a.id]);
 const manifest={version:6,fps:15,complete,faceStyle:'original-mist',assets,activities:activities.map(({eyes,...a})=>a),provenance:'ImageGen activity symbols combined with original MIST eyes, blinks, transitions and speaking mouths.'};
 fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
 const composite=[];let row=0;
 for(const [id,asset]of Object.entries(assets)){
  for(let n=0;n<asset.frames.length;n++)composite.push({input:await sharp(path.join(root,asset.frames[n].file)).resize(100,100).png().toBuffer(),left:n*104,top:row*104});
  row++;
 }
 if(row)await sharp({create:{width:12*104,height:row*104,channels:4,background:'#101d20'}}).composite(composite).png().toFile(path.join(root,'contact_sheet.png'));
 console.log(JSON.stringify({complete,assets:Object.keys(assets),frames:Object.values(assets).reduce((n,a)=>n+a.frames.length,0)},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
