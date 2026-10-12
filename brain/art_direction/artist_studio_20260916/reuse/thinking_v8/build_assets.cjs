'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sharp=require(process.env.MIST_SHARP_PATH||'<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=__dirname,sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const columns=6,rows=4,count=24;
const variants=['39_neutral_02_manual','40_neutral_03_manual','36_misc_03_manual'];
const studies=[
 {id:'reading',label:'Reading',asset:'book',faceId:variants[0]},
 {id:'coding',label:'Coding',asset:'terminal',faceId:variants[1]},
 {id:'writing',label:'Drafting',asset:'note',faceId:variants[2]},
 {id:'sorting',label:'Sorting ideas',asset:'cards',faceId:variants[0]},
 {id:'searching',label:'Searching',asset:'searching',faceId:variants[1]},
 {id:'pondering',label:'Quiet thought',asset:'planning',faceId:variants[2]},
 {id:'connecting',label:'Connecting',asset:'connecting',faceId:variants[0]},
 {id:'checking',label:'Checking',asset:'checking',faceId:variants[1]},
].map(s=>({...s,faceVariants:variants}));

function anchor(id,c){
 const b=c.box;
 if(['connecting','planning'].includes(id))return [b.left+b.width/2-c.cw/2,b.top+b.height/2-c.ch/2];
 if(['checking','note','searching'].includes(id)){
  // The page's bottom stroke is independent of its pen, scan bracket or content.
  const candidates=[];
  for(let y=Math.floor(b.top+b.height*.65);y<Math.min(c.ch,b.top+b.height);y++){
   let first=c.cw,last=-1,pixels=0;
   for(let x=b.left;x<Math.min(c.cw,b.left+b.width);x++)if(c.buf[(y*c.cw+x)*4+3]>128){pixels++;first=Math.min(first,x);last=x;}
   if(pixels>Math.max(8,b.width*.4))candidates.push({pixels,x:(first+last)/2,y});
  }
  const maximum=Math.max(0,...candidates.map(c=>c.pixels));
  const best=candidates.find(c=>c.pixels>=maximum*.9);
  if(best)return [best.x-c.cw/2,best.y-c.ch/2];
 }
 return [b.left+b.width/2-c.cw/2,b.top+b.height-c.ch/2];
}

async function composeCards(original,info,cells){
 // Assemble the generated single-card cel as three reusable animation parts.
 // The source pixels are retained; only placement, rotation and uniform scale vary.
 const c=cells[0],component=await sharp(c.buf,{raw:{width:c.cw,height:c.ch,channels:4}}).extract(c.box).png().toBuffer();
 fs.mkdirSync(path.join(root,'components'),{recursive:true});
 fs.writeFileSync(path.join(root,'components/card.png'),component);
 const raw=await sharp(component).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 const outside=new Uint8Array(raw.info.width*raw.info.height),queue=[];
 const visit=(x,y)=>{const p=y*raw.info.width+x;if(x<0||y<0||x>=raw.info.width||y>=raw.info.height||outside[p]||raw.data[p*4+3]>42)return;outside[p]=1;queue.push(p);};
 for(let x=0;x<raw.info.width;x++){visit(x,0);visit(x,raw.info.height-1);}for(let y=0;y<raw.info.height;y++){visit(0,y);visit(raw.info.width-1,y);}
 for(let q=0;q<queue.length;q++){const p=queue[q],x=p%raw.info.width,y=Math.floor(p/raw.info.width);visit(x-1,y);visit(x+1,y);visit(x,y-1);visit(x,y+1);}
 const mask=Buffer.alloc(raw.data.length);for(let p=0;p<outside.length;p++)if(!outside[p]){mask[p*4]=mask[p*4+1]=mask[p*4+2]=mask[p*4+3]=255;}
 const maskPng=await sharp(mask,{raw:raw.info}).png().toBuffer();
 const frames=[],smooth=x=>x*x*(3-2*x),triangle=x=>1-Math.abs(2*x-1);
 for(let i=0;i<24;i++){
  let spread=1,scale=1,centerLift=0,leftLift=0;
  if(i<4){spread=[0,.28,.68,1][i];scale=[.66,.78,.9,1][i];}
  else if(i<20){
   const phase=(i-4)/16;
   if(phase<.5)centerLift=40*smooth(triangle(phase*2));
   else leftLift=34*smooth(triangle((phase-.5)*2));
  }else{spread=[.78,.46,.18,0][i-20];scale=[.95,.83,.68,.48][i-20];}
  const placements=[{x:128-43*spread,y:142-leftLift,angle:-22*spread},{x:128+43*spread,y:142,angle:22*spread},{x:128,y:142-centerLift,angle:0}];
  const composites=[];
  for(const p of placements){
   const width=Math.round(76*scale),height=Math.round(c.box.height/c.box.width*width);
   const img=await sharp(component).resize(width,height).rotate(p.angle,{background:{r:0,g:0,b:0,alpha:0}}).png().toBuffer();
   const occlusion=await sharp(maskPng).resize(width,height).rotate(p.angle,{background:{r:0,g:0,b:0,alpha:0}}).png().toBuffer();
   const m=await sharp(img).metadata(),left=Math.round(p.x-m.width/2),top=Math.round(p.y-m.height/2);
   composites.push({input:occlusion,left,top,blend:'dest-out'},{input:img,left,top});
  }
  const bytes=await sharp({create:{width:256,height:256,channels:4,background:{r:0,g:0,b:0,alpha:0}}}).composite(composites).png().toBuffer();
  const file=`frames/cards/${String(i).padStart(2,'0')}.png`;fs.mkdirSync(path.join(root,'frames/cards'),{recursive:true});fs.writeFileSync(path.join(root,file),bytes);
  const {data}=await sharp(bytes).raw().toBuffer({resolveWithObject:true});let l=256,t=256,r=-1,b=-1;
  for(let y=0;y<256;y++)for(let x=0;x<256;x++)if(data[(y*256+x)*4+3]>0){l=Math.min(l,x);r=Math.max(r,x);t=Math.min(t,y);b=Math.max(b,y);}
  frames.push({file,pose:i<4?`enter_${i}`:i<20?`loop_${i-4}`:`exit_${i-20}`,bounds:[l,t,r-l+1,b-t+1],sourceCell:c.sourceCell,placements,sha256:sha(bytes)});
 }
 return {type:'activity',source:'source/cards.png',sourceSha256:sha(original),sourceSize:[info.width,info.height],columns,rows,registration:'generated card component with rigid placement',scale:1,assembly:{components:[{file:'components/card.png',sha256:sha(component),source:'source/cards.png',sourceSha256:sha(original),sourceCell:c.sourceCell}],method:'Three copies of one ImageGen card; uniform scaling, rotation, translation and silhouette occlusion. Repeated positions on return paths intentionally reuse the same art.'},phaseFrames:{entrance:4,loop:16,exit:4},frames};
}

async function contact(id,frames){
 const composite=[];for(let i=0;i<count;i++)composite.push({input:await sharp(path.join(root,frames[i].file)).resize(128,128).png().toBuffer(),left:i%6*132,top:Math.floor(i/6)*132});
 await sharp({create:{width:792,height:528,channels:4,background:'#101c20'}}).composite(composite).png().toFile(path.join(root,`contact_${id}.png`));
}

async function extract(id){
 const source=`source/${id}.png`,original=fs.readFileSync(path.join(root,source));
 const native=await sharp(original).metadata();if(!native.hasAlpha)throw Error(id+' needs native transparency');
 const {data,info}=await sharp(original).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 let clear=0;for(let p=3;p<data.length;p+=4)if(data[p]<16)clear++;
 if(clear<info.width*info.height*.4)throw Error(id+' background is not transparent');
 const cells=[];
 for(let n=0;n<count;n++){
  const col=n%columns,row=Math.floor(n/columns),x0=Math.round(col*info.width/columns),y0=Math.round(row*info.height/rows);
  const cw=Math.round((col+1)*info.width/columns)-x0,ch=Math.round((row+1)*info.height/rows)-y0;
  const buf=Buffer.alloc(cw*ch*4);let minX=cw,minY=ch,maxX=-1,maxY=-1,ink=0;
  for(let y=0;y<ch;y++)for(let x=0;x<cw;x++){
   const src=((y+y0)*info.width+x+x0)*4,dst=(y*cw+x)*4;
   for(let k=0;k<4;k++)buf[dst+k]=data[src+k];
   if(buf[dst+3]>42){ink++;minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);}
  }
  if(ink<15)throw Error(id+' empty cell '+n);
  if(minX<2||minY<2||maxX>=cw-2||maxY>=ch-2)throw Error(id+' cell '+n+' touches grid boundary');
  cells.push({buf,cw,ch,box:{left:minX-2,top:minY-2,width:maxX-minX+5,height:maxY-minY+5},sourceCell:[x0,y0,cw,ch]});
 }
 if(id==='cards'){const result=await composeCards(original,info,cells);await contact(id,result.frames);return result;}
 if(id==='note'){const result=await require('./rigid_note.cjs').composeNote(id,original,info,cells,root,sha);await contact(id,result.frames);return result;}
 if(id==='checking'||id==='connecting'){const result=await require('./rigid_scans.cjs').composeScan(id,original,info,cells,root,sha);await contact(id,result.frames);return result;}
 const registered=id!=='cards';
 if(registered){
  const anchors=cells.map(c=>anchor(id,c)),reference=[0,1].map(k=>anchors.slice(4,20).reduce((sum,a)=>sum+a[k],0)/16);
  cells.forEach((c,i)=>{c.offset=[reference[0]-anchors[i][0],reference[1]-anchors[i][1]];c.anchor=anchors[i];});
 }else cells.forEach(c=>{c.offset=[0,0];});
 const centers=cells.slice(4,20).map(c=>[c.box.left+c.box.width/2-c.cw/2+c.offset[0],c.box.top+c.box.height/2-c.ch/2+c.offset[1]]);
 const origin=[0,1].map(k=>centers.reduce((sum,c)=>sum+c[k],0)/centers.length);
 const radius=Math.max(...cells.flatMap(c=>[Math.abs(c.box.left-c.cw/2+c.offset[0]-origin[0]),Math.abs(c.box.left+c.box.width-c.cw/2+c.offset[0]-origin[0]),Math.abs(c.box.top-c.ch/2+c.offset[1]-origin[1]),Math.abs(c.box.top+c.box.height-c.ch/2+c.offset[1]-origin[1])]));
 const scale=108/radius,frames=[];fs.mkdirSync(path.join(root,'frames',id),{recursive:true});
 for(let i=0;i<count;i++){
  const c=cells[i],width=Math.max(1,Math.round(c.box.width*scale)),height=Math.max(1,Math.round(c.box.height*scale));
  const cel=await sharp(c.buf,{raw:{width:c.cw,height:c.ch,channels:4}}).extract(c.box).resize(width,height).png().toBuffer();
  const left=Math.round(128+(c.box.left-c.cw/2+c.offset[0]-origin[0])*scale),top=Math.round(128+(c.box.top-c.ch/2+c.offset[1]-origin[1])*scale);
  const output=await sharp({create:{width:256,height:256,channels:4,background:{r:0,g:0,b:0,alpha:0}}}).composite([{input:cel,left,top}]).png().toBuffer();
  const file=`frames/${id}/${String(i).padStart(2,'0')}.png`;fs.writeFileSync(path.join(root,file),output);
  frames.push({file,pose:i<4?`enter_${i}`:i<20?`loop_${i-4}`:`exit_${i-20}`,bounds:[left,top,width,height],sourceCell:c.sourceCell,registrationOffset:c.offset,sha256:sha(output)});
 }
 await contact(id,frames);
 return {type:'activity',source,sourceSha256:sha(original),sourceSize:[info.width,info.height],columns,rows,registration:registered?'stable body anchor and uniform scale':'shared source origin and uniform scale',scale,phaseFrames:{entrance:4,loop:16,exit:4},frames};
}
(async()=>{
 const assets={};
 for(const study of studies){
  if(!fs.existsSync(path.join(root,'source',study.asset+'.png'))){if(process.argv.includes('--partial'))continue;throw Error('Missing source '+study.asset);}
  assets[study.asset]=await extract(study.asset);
 }
 const complete=studies.every(s=>assets[s.asset]);
 fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify({version:8,fps:15,complete,faceStyle:'original-mist',faceVariants:variants,assets,studies},null,2)+'\n');
 const composite=[];let row=0;
 for(const asset of Object.values(assets)){
  for(let i=0;i<count;i++)composite.push({input:await sharp(path.join(root,asset.frames[i].file)).resize(72,72).png().toBuffer(),left:i*76,top:row*76});
  row++;
 }
 if(row)await sharp({create:{width:count*76,height:row*76,channels:4,background:'#101c20'}}).composite(composite).png().toFile(path.join(root,'contact_sheet.png'));
 const indexPath=path.join(root,'index.html');
 let html=fs.readFileSync(indexPath,'utf8');
 for(const file of ['runtime.js','preview.js','style.css'])html=html.replace(new RegExp('(["\\\'])'+file.replace('.', '\\.')+'\\?v=[^"\\\']+(["\\\'])','g'),(_,quote,end)=>quote+file+'?v='+sha(fs.readFileSync(path.join(root,file))).slice(0,16)+end);
 fs.writeFileSync(indexPath,html);
 console.log(JSON.stringify({complete,assets:Object.keys(assets),frames:Object.values(assets).reduce((sum,a)=>sum+a.frames.length,0)}));
})().catch(error=>{console.error(error);process.exitCode=1;});
