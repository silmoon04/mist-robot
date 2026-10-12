const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sharp = require('<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root = __dirname;
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');

(async () => {
  const catalog = JSON.parse(fs.readFileSync(path.join(root, 'catalog.json')));
  const manifest = {version:1,created:'2026-09-29',kind:'Three-pose acting studies',liveAssetsChanged:false,groups:[]};
  const report = {passed:true,groups:0,examples:0,poses:0,files:[],limitations:['Crop checks do not establish acting quality. See visual_review.json.','Only three key poses per example; no generated in-between frames or voice integration.']};
  const contact = [];
  for (const [groupIndex, sourceGroup] of catalog.groups.entries()) {
    const group = {...sourceGroup, examples:[]};
    group.sheet = `source/${group.id}.png`;
    const bytes = fs.readFileSync(path.join(root,group.sheet));
    const meta = await sharp(bytes).metadata();
    group.sourceSha256 = sha(bytes);
    group.sourceWidth = meta.width;
    group.sourceHeight = meta.height;
    group.prompt = `prompts/${group.id}.txt`;
    fs.mkdirSync(path.join(root,'poses',group.id),{recursive:true});
    for (const [row,sourceExample] of sourceGroup.examples.entries()) {
      const {durations,...details} = sourceExample;
      const example = {...details,poses:[]};
      for (let col=0;col<3;col++) {
        const left=Math.round(col*meta.width/3),top=Math.round(row*meta.height/3);
        const width=Math.round((col+1)*meta.width/3)-left,height=Math.round((row+1)*meta.height/3)-top;
        const crop=await sharp(bytes).extract({left,top,width,height}).png().toBuffer();
        const file=`poses/${group.id}/${example.id}_${col}.png`;
        fs.writeFileSync(path.join(root,file),crop);
        const {data,info}=await sharp(crop).removeAlpha().raw().toBuffer({resolveWithObject:true});
        let count=0,minX=width,maxX=-1,minY=height,maxY=-1;
        for(let y=0;y<height;y++)for(let x=0;x<width;x++){
          const p=(y*width+x)*info.channels;
          if(data[p+1]>110&&data[p+1]-data[p]>35&&data[p+2]>110){count++;minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
        }
        const margin=Math.min(minX,minY,width-1-maxX,height-1-maxY);
        if(count<200||margin<10)throw Error(`Missing or clipped pose: ${file}`);
        const record={label:['Setup','Change','Settle'][col],file,durationMs:durations[col],sha256:sha(crop),sourceRect:[left,top,width,height]};
        example.poses.push(record);
        report.files.push({file,width,height,visiblePixels:count,minimumMargin:margin,sha256:record.sha256});
        report.poses++;
      }
      group.examples.push(example);
      report.examples++;
    }
    manifest.groups.push(group);
    report.groups++;
    const thumb=await sharp(bytes).resize(768,512,{fit:'contain',background:'#101c20'}).png().toBuffer();
    contact.push({input:thumb,left:(groupIndex%2)*780,top:Math.floor(groupIndex/2)*524});
  }
  if(report.groups!==6||report.examples!==18||report.poses!==54)throw Error('Incomplete collection');
  fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
  report.manifestSha256=sha(fs.readFileSync(path.join(root,'manifest.json')));
  fs.writeFileSync(path.join(root,'asset_review.json'),JSON.stringify(report,null,2)+'\n');
  await sharp({create:{width:1548,height:1560,channels:3,background:'#e8ecea'}}).composite(contact).png().toFile(path.join(root,'overview.png'));
  console.log(JSON.stringify({groups:report.groups,examples:report.examples,poses:report.poses,passed:true}));
})().catch(error=>{console.error(error);process.exitCode=1;});
