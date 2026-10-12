const fs=require('node:fs'),path=require('node:path');
const sharp=require('<LOCAL_HOME>/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=__dirname;
const faces=[['39_neutral_02_manual','Calm','Default available and speaking face'],['25_neutral_2_03_manual','Listening','Default listening face'],['20_neutral_06_manual','Curious','Thinking rotation; two evaluation selections'],['40_neutral_03_manual','Quiet thought','Thinking rotation'],['09_happy_03_manual','Happy','Primary happy face; three evaluation selections'],['37_misc_06_manual','Playful','Primary smug face; one evaluation selection'],['35_sad_10_manual','Deadpan','Primary deadpan face; one evaluation selection'],['16_misc_16_manual','Sleepy','Primary sleepy face; one evaluation selection'],['12_happy_09_manual','Delighted','Happy alternative; one evaluation selection'],['32_sad_07_manual','Sad','Primary sad face; one evaluation selection']].map(([id,label,basis],index)=>({id,label,basis,index,original:'originals/'+id+'.png'}));
(async()=>{
 const layers=[];
 for(const f of faces){
  const src=path.join(root,'../faces',f.id+'.png');
  fs.copyFileSync(src,path.join(root,f.original));
  const image=await sharp(src).resize(512,307,{fit:'contain',background:'#101c20'}).flatten({background:'#101c20'}).png().toBuffer();
  layers.push({input:image,left:(f.index%2)*512,top:Math.round(Math.floor(f.index/2)*1536/5)});
 }
 await sharp({create:{width:1024,height:1536,channels:3,background:'#101c20'}}).composite(layers).png().toFile(path.join(root,'reference.png'));
 fs.writeFileSync(path.join(root,'selection.json'),JSON.stringify({basis:'Everyday runtime defaults plus successful face selections in 18 synthetic Luna conversations (86 turns), not a measured user-usage ranking.',sources:['brain/duplex/static/expression_policy.js','brain/duplex/face_map.json','brain/results/luna_conversations_20260922/refined/*/transcript.json'],faces},null,2)+'\n');
 console.log('Prepared ten original faces and the 2-column / 5-row reference.');
})().catch(e=>{console.error(e);process.exitCode=1;});
