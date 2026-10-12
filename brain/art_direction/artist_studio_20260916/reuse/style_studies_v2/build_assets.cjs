const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sharp=require('<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=__dirname,sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const styles=[{id:'original',label:'Current',description:'Existing MIST contours.'},{id:'pen',label:'Gesture ink',description:'Tilted loops, tapered lines and drawn mouth shapes.'},{id:'brush',label:'Dry brush',description:'Painted sweeps, bristle gaps and tapered marks.'},{id:'cel',label:'Cartoon cel',description:'Bean shapes, crescent lids and expressive silhouettes.'}];
(async()=>{
 const selection=JSON.parse(fs.readFileSync(path.join(root,'selection.json')));
 const basis='Main conversation faces, plus expressive alternatives. The current defaults and seven selected faces account for 387 of 391 recorded expression transitions across 33 saved studio traces. Those traces include fixtures and test sessions, so this is not an organic popularity ranking. Deadpan, Sleepy and Delighted add expressive range and appeared in earlier Luna conversation tests.';
 const assets={},sources={},report={passed:true,faces:10,generatedVariants:30,originals:10,files:[],checks:['All expected crops contain visible cyan artwork and clear margins.','Mouthless expressions have no unexpected ink in the lower face.','Only rectangular extraction; generated source pixels are not repainted.'],limitations:['Static style proposals, not animation frames or production replacements.','Numeric crop checks do not establish drawing style or emotional clarity. See visual_review.json.']};
 for(const f of selection.faces){assets[f.id]={};const bytes=fs.readFileSync(path.join(root,f.original));assets[f.id].original={file:f.original,sha256:sha(bytes)};}
 for(const style of styles.filter(s=>s.id!=='original')){
  const source=`source/${style.id}.png`,bytes=fs.readFileSync(path.join(root,source)),meta=await sharp(bytes).metadata();
  sources[style.id]={file:source,sha256:sha(bytes),width:meta.width,height:meta.height,columns:2,rows:5,tool:'Built-in ImageGen',prompt:`prompts/${style.id}.txt`};
  fs.mkdirSync(path.join(root,'variants',style.id),{recursive:true});
  for(const f of selection.faces){
   const col=f.index%2,row=Math.floor(f.index/2),left=Math.round(col*meta.width/2),top=Math.round(row*meta.height/5);
   const width=Math.round((col+1)*meta.width/2)-left,height=Math.round((row+1)*meta.height/5)-top;
   const output=await sharp(bytes).extract({left,top,width,height}).png().toBuffer(),file=`variants/${style.id}/${f.id}.png`;
   fs.writeFileSync(path.join(root,file),output);assets[f.id][style.id]={file,sha256:sha(output),source,sourceRect:[left,top,width,height]};
   const {data,info}=await sharp(output).removeAlpha().raw().toBuffer({resolveWithObject:true});let l=width,r=-1,t=height,b=-1,count=0,mouthPixels=0;
   for(let y=0;y<height;y++)for(let x=0;x<width;x++){const p=(y*width+x)*info.channels;if(data[p+1]>100&&data[p+1]-data[p]>40&&data[p+2]>100){l=Math.min(l,x);r=Math.max(r,x);t=Math.min(t,y);b=Math.max(b,y);count++;if(y>height*.64)mouthPixels++;}}
   const margin=Math.min(l,width-1-r,t,height-1-b);
   if(count<250||margin<8)throw Error('Missing or cropped face: '+file);
   if(['35_sad_10_manual','12_happy_09_manual'].includes(f.id)&&mouthPixels>20)throw Error('Unexpected mouth in '+file);
   report.files.push({file,width,height,visiblePixels:count,minimumMargin:margin,mouthPixels,sha256:sha(output)});
  }
 }
 const manifest={version:2,created:'2026-09-28',basis,faces:selection.faces,styles,assets,sources,kind:'static drawing style exploration',liveAssetsChanged:false};
 fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
 report.manifestSha256=sha(fs.readFileSync(path.join(root,'manifest.json')));
 fs.writeFileSync(path.join(root,'asset_review.json'),JSON.stringify(report,null,2)+'\n');
 const composite=[];
 for(const f of selection.faces)for(const [j,s]of styles.entries()){
  const img=await sharp(path.join(root,assets[f.id][s.id].file)).resize(256,154,{fit:'contain',background:'#101c20'}).flatten({background:'#101c20'}).png().toBuffer();
  composite.push({input:img,left:j*264,top:f.index*162});
 }
 await sharp({create:{width:1048,height:1612,channels:3,background:'#e8ecea'}}).composite(composite).png().toFile(path.join(root,'comparison.png'));
 console.log(JSON.stringify({faces:10,newVariants:30,checksPassed:true}));
})().catch(e=>{console.error(e);process.exitCode=1;});
