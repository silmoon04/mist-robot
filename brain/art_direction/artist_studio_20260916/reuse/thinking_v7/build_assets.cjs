'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sharp=require(process.env.MIST_SHARP_PATH||'<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=__dirname,previous=path.join(root,'../handdrawn_v6');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const studies=[
 {id:'reading',label:'Reading',asset:'book',faceId:'39_neutral_02_manual',note:'Follow a line, turn a page, take a moment.'},
 {id:'coding',label:'Coding',asset:'terminal',faceId:'40_neutral_03_manual',note:'Type a short burst, pause, carry on.'},
 {id:'writing',label:'Drafting',asset:'note',faceId:'36_misc_03_manual',note:'Write, lift the pen, consider the next line.'},
 {id:'sorting',label:'Sorting ideas',asset:'cards',faceId:'36_misc_03_manual',note:'Compare two ideas, set one aside, reconsider.'},
 {id:'searching',label:'Searching',asset:'searching',faceId:'20_neutral_06_manual',note:'Look across, inspect, then look again.'},
 {id:'pondering',label:'Quiet thought',asset:'planning',faceId:'39_neutral_02_manual',note:'A glance away and a pause before returning.'},
];
async function extract(id){
 const file=path.join(root,'source',id+'.png'),original=fs.readFileSync(file);
 const {data:rgba,info}=await sharp(original).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 let transparent=0;for(let i=3;i<rgba.length;i+=4)if(rgba[i]<240)transparent++;
 const nativeAlpha=transparent>info.width*info.height*.05;if(!nativeAlpha)throw Error(id+' requires a transparent original');
 const cells=[];
 for(let n=0;n<16;n++){
  const x0=Math.round(n%4*info.width/4),y0=Math.round(Math.floor(n/4)*info.height/4);
  const cw=Math.round((n%4+1)*info.width/4)-x0,ch=Math.round((Math.floor(n/4)+1)*info.height/4)-y0;
  let minX=cw,minY=ch,maxX=-1,maxY=-1,ink=0;const buf=Buffer.alloc(cw*ch*4);
  for(let y=0;y<ch;y++)for(let x=0;x<cw;x++){
   const si=((y+y0)*info.width+x+x0)*4,di=(y*cw+x)*4;
   for(let k=0;k<4;k++)buf[di+k]=rgba[si+k];
   if(buf[di+3]>42){ink++;minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);}
  }
  if(ink<15)throw Error(id+' empty cell '+n);
  if(minX<2||minY<2||maxX>=cw-2||maxY>=ch-2)throw Error(id+' boundary ink in cell '+n);
  const left=minX-2,top=minY-2,w=maxX-minX+5,h=maxY-minY+5;
  cells.push({buf,cw,ch,box:{left,top,width:w,height:h},sourceCell:[x0,y0,cw,ch],ink});
 }
 // A shared origin retains movement within the sheet; individual cels are never stretched.
 const centers=cells.slice(4,12).map(c=>[c.box.left+c.box.width/2-c.cw/2,c.box.top+c.box.height/2-c.ch/2]);
 const origin=[0,1].map(k=>centers.reduce((s,c)=>s+c[k],0)/centers.length);
 const radius=Math.max(...cells.flatMap(c=>[Math.abs(c.box.left-c.cw/2-origin[0]),Math.abs(c.box.left+c.box.width-c.cw/2-origin[0]),Math.abs(c.box.top-c.ch/2-origin[1]),Math.abs(c.box.top+c.box.height-c.ch/2-origin[1])]));
 const scale=108/radius,frames=[];fs.mkdirSync(path.join(root,'frames',id),{recursive:true});
 for(let i=0;i<cells.length;i++){
  const c=cells[i],w=Math.max(1,Math.round(c.box.width*scale)),h=Math.max(1,Math.round(c.box.height*scale));
  const sprite=await sharp(c.buf,{raw:{width:c.cw,height:c.ch,channels:4}}).extract(c.box).resize(w,h).png().toBuffer();
  const left=Math.round(128+(c.box.left-c.cw/2-origin[0])*scale),top=Math.round(128+(c.box.top-c.ch/2-origin[1])*scale);
  const out=await sharp({create:{width:256,height:256,channels:4,background:{r:0,g:0,b:0,alpha:0}}}).composite([{input:sprite,left,top}]).png().toBuffer();
  const file=`frames/${id}/${String(i).padStart(2,'0')}.png`;fs.writeFileSync(path.join(root,file),out);
  frames.push({file,pose:i<4?`enter_${i}`:i<12?`loop_${i-4}`:`exit_${i-12}`,bounds:[left,top,w,h],sourceCell:c.sourceCell,sha256:hash(out)});
 }
 return {type:'activity',source:`source/${id}.png`,sourceSha256:hash(original),sourceSize:[info.width,info.height],columns:4,rows:4,registration:'shared source origin',scale,frames};
}
(async()=>{
 const assets={};
 for(const id of ['book','terminal','note','cards']){
  if(!fs.existsSync(path.join(root,'source',id+'.png'))){if(process.argv.includes('--partial'))continue;throw Error('Missing '+id);}
  assets[id]=await extract(id);
 }
 const prior=JSON.parse(fs.readFileSync(path.join(previous,'manifest.json'),'utf8'));
 for(const id of ['searching','planning']){
  const a=prior.assets[id];fs.mkdirSync(path.join(root,'frames',id),{recursive:true});
  for(const f of a.frames)fs.copyFileSync(path.join(previous,f.file),path.join(root,f.file));
  fs.copyFileSync(path.join(previous,a.source),path.join(root,a.source));
  fs.copyFileSync(path.join(previous,'source',id+'.json'),path.join(root,'source',id+'.json'));
  fs.copyFileSync(path.join(previous,'prompts',id+'.txt'),path.join(root,'prompts',id+'.txt'));
  assets[id]={...a,reusedFrom:'handdrawn_v6'};
 }
 const complete=studies.every(s=>assets[s.asset]);
 fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify({version:7,fps:15,complete,faceStyle:'original-mist',assets,studies},null,2)+'\n');
 const composite=[];let row=0;
 for(const a of Object.values(assets)){
  for(let i=0;i<a.frames.length;i++)composite.push({input:await sharp(path.join(root,a.frames[i].file)).resize(88,88).png().toBuffer(),left:i*92,top:row*92});
  row++;
 }
 await sharp({create:{width:16*92,height:row*92,channels:4,background:'#101d20'}}).composite(composite).png().toFile(path.join(root,'contact_sheet.png'));
 console.log(JSON.stringify({complete,assets:Object.keys(assets),frames:Object.values(assets).reduce((s,a)=>s+a.frames.length,0)}));
})().catch(e=>{console.error(e);process.exitCode=1;});
