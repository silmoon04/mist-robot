const fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(__dirname,'../../../..'),out=__dirname;
const ctx={window:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'brain/face_assets/app/app_data.js'),'utf8'),ctx);
const data=ctx.window.MIST_DATA,R=require(path.join(root,'brain/ui/static/face_runtime.js'));
const audit=JSON.parse(fs.readFileSync(path.join(out,'audit.json'),'utf8'));
function svg(layers,box='0 0 100 64') {return `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="512" viewBox="${box}">${layers.map(l=>`<path data-role="${l.role}" data-part="${l.part}" d="${R.pathData(l.points,l.mode==='fill')}" fill="${l.mode==='fill'?'#5eeadd':'none'}" stroke="${l.mode==='stroke'?'#5eeadd':'none'}" stroke-width="${l.width||0}" stroke-linecap="round" stroke-linejoin="round" opacity="${l.opacity??1}"/>`).join('')}</svg>`;}
function save(name,layers,box){const p=path.join(out,name+'.svg');fs.mkdirSync(path.dirname(p),{recursive:true});fs.writeFileSync(p,svg(layers,box));}
function native(id,p,role='part'){return{part:id,role,points:p.points.map(([x,y])=>[x+50,y+32]),mode:p.kind,width:p.width||0,opacity:1};}
for(let i=0;i<audit.candidates.length;i++){
 const c=audit.candidates[i],a=data.parts[c.a],b=data.parts[c.b];
 const mean=p=>[0,1].map(axis=>p.reduce((v,q)=>v+q[axis],0)/p.length);
 const ma=mean(a.points),mb=mean(b.points),rad=c.rotation*Math.PI/180;
 const points=a.points.map(([x,y])=>{x=(x-ma[0])*(c.mirror?-1:1);y-=ma[1];return[50+Math.cos(rad)*x-Math.sin(rad)*y,32+Math.sin(rad)*x+Math.cos(rad)*y];});
 const layers=[{...native(c.a,a),points}, {...native(c.b,b),points:b.points.map(([x,y])=>[50+x-mb[0],32+y-mb[1]]),opacity:.65}];
 let s=svg(layers);const at=s.indexOf('<path',s.indexOf('<path')+1);s=s.slice(0,at)+s.slice(at).replaceAll('#5eeadd','#f396b9');
 fs.mkdirSync(path.join(out,'comparisons'),{recursive:true});fs.writeFileSync(path.join(out,'comparisons',i+'.svg'),s);
}
const clips=[];
for(const g of audit.groups)save('parts/'+g.id,[native(g.id,data.parts[g.id])]);
for(const [base,id] of Object.entries(data.blinks))save('parts/'+id,[native(id,data.parts[id])]);
for(const f of data.faces){
 const renderer=R.create(null,{data,expression:f.id,autoStart:false,reducedMotion:true,now:()=>0});
 const snap=renderer.snapshot(0);save('faces/'+f.id,snap.layers);
 for(const l of snap.layers)save('instances/'+f.id+'/'+l.role,[l]);
 renderer.destroy();
}
for(const name of Object.keys(data.visemes)){
 let t=0;const renderer=R.create(null,{data,expression:data.faces[0].id,autoStart:false,reducedMotion:true,now:()=>t});
 renderer.startSpeech({events:[{time:0,viseme:name}],duration:2,clock:()=>t/1000});t=250;
 save('speech/'+name,renderer.snapshot(t).layers.filter(l=>l.role==='mouth'));renderer.destroy();
}
for(const g of audit.groups.filter(g=>g.blink)){
 const p=data.parts[g.id],closed=data.parts[g.blink];
 // Artist timing reference: discrete source contours, 125 ms per frame. No new artwork.
 const open=native(g.id,p,'eye'),lid=native(g.blink,closed,'eye');
 const h=p.points.map(([x,y],i)=>[x+50,(y+closed.points[i][1])/2+32]);
 const frames=[[open],[{...open,points:h}],[lid],[{...open,points:h}]];
 frames.forEach((l,i)=>save(`clips/blink_${g.id}/${String(i).padStart(3,'0')}`,l));
 clips.push({id:'blink_'+g.id,name:g.id,type:'blink',frames:4,fps:8,source:[g.id,g.blink],note:'Four-frame study; hold open between blinks. Half-lid is a procedural guide.'});
}
for(const [id,name] of [['thinking_lookup','Look up'],['thinking_scan','Search'],['thinking_focus','Focus']]){
 const fid=id==='thinking_focus'?'40_neutral_03_manual':'39_neutral_02_manual';
 for(let i=0;i<24;i++){
  let t=0;const r=R.create(null,{data,expression:fid,autoStart:false,reducedMotion:false,now:()=>t});
  let x=0,y=-.7;
  if(id==='thinking_scan'){x=Math.sin(i/24*Math.PI*2)*.9;y=-.25;}
  if(id==='thinking_lookup'){x=i<12?-.65:.3;y=-.7;}
  if(id==='thinking_focus'){x=.35*Math.sin(i/24*Math.PI*2);y=-.35;}
  r.setGaze(x,y);t=i*125;save(`clips/${id}/${String(i).padStart(3,'0')}`,r.snapshot(t).layers);r.destroy();
 }
 clips.push({id,name,type:'thinking',frames:24,fps:8,source:[fid],note:'Existing face; gaze and timing only. Zero new drawings.'});
}
let t=0;const speech=R.create(null,{data,expression:'09_happy_03_manual',autoStart:false,reducedMotion:true,now:()=>t});
const order=['rest','MBP','AA','AA','EH','EE','FV','OO','OH','LNT','S','rest','MBP','AA','EH','SMILE','SMILE','OO','LNT','EE','FV','MBP','rest','rest'];
// Explicit held visemes make a useful 8 fps shape study; this is not an audio alignment test.
for(let i=0;i<order.length;i++){
 const r=R.create(null,{data,expression:'09_happy_03_manual',autoStart:false,reducedMotion:true,now:()=>0});
 r.startSpeech({events:[{time:0,viseme:order[i]}],duration:2,clock:()=>.25});
 save(`clips/speech_shapes/${String(i).padStart(3,'0')}`,r.snapshot(250).layers);r.destroy();
}
speech.destroy();clips.push({id:'speech_shapes',name:'Speech shapes',type:'speech',frames:24,fps:8,source:Object.keys(data.visemes),note:'Shape and timing study without audio; live speech needs audio timestamps.'});
const archived=JSON.parse(fs.readFileSync(path.join(root,'design/mist_v2_20260906/brain_v2_20260907/faces/animation_frames.json'),'utf8'));
// Preserve archived timings and every layer; left/right are inferred from geometry because the archive labels both eyes "eyes".
for(let i=0;i<archived.frames.length;i++){
 const f=archived.frames[i];save(`archive/${String(i).padStart(3,'0')}`,f.layers);
 for(let j=0;j<f.layers.length;j++){
  const l=f.layers[j];const center=l.points.reduce((s,p)=>s+p[0],0)/l.points.length;
  save(`archive_layers/${String(i).padStart(3,'0')}/${j}_${l.role==='eyes'?(center<50?'eye_L':'eye_R'):l.role}`,[l]);
 }
}
fs.writeFileSync(path.join(out,'clips.json'),JSON.stringify(clips,null,2));
fs.writeFileSync(path.join(out,'clips.js'),'window.REUSE_CLIPS='+JSON.stringify(clips)+';');
console.log(JSON.stringify({parts:audit.groups.length,faces:data.faces.length,clips:clips.length,frames:clips.reduce((n,c)=>n+c.frames,0),archivedFrames:archived.frames.length}));
