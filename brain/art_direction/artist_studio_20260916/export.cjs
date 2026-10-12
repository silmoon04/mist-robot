const fs=require('fs'),path=require('path'),scene=require('./scene.js');
const root=__dirname,out=path.join(root,'frame_assets');fs.mkdirSync(out,{recursive:true});
const slug=s=>s.replaceAll(' + ','_').replaceAll(' ','_');const clips=[];
function clip(id,label,frames,settings,reuse,core=true){clips.push({id,label,frames,fps:24,seconds:frames/24,settings,reuse,core});}
for(const s of scene.states.filter(s=>s.kind==='State'))for(const [i,option] of s.options.entries())clip(s.id+'_'+slug(option),s.name+' / '+option,s.frames,{state:s.id,option,mode:'state'},s.eyes+' + '+s.mouth,i===0);
for(const s of scene.states.filter(s=>s.talk))clip('speech_'+s.id,'Speech / '+s.name,48,{state:s.id,mode:'speech'},s.eyes+' + shared mouth cycle');
for(const [i,family] of scene.families.entries()){
 clip('blink_'+family,'Blink / '+family,6,{state:'available',family,mode:'blink',mouth:false},`B${String(i*2+1).padStart(2,'0')} + B${String(i*2+2).padStart(2,'0')} + open eyes`);
 clip('enter_'+family,'Transition / '+family,8,{state:'available',family,mode:'transition',mouth:false},'Shared closed-lid bridge; eyes only');
}
for(const s of scene.states.filter(s=>s.kind==='Reaction'))clip('reaction_'+s.id,'Reaction / '+s.name,12,{state:s.id},s.eyes+' + '+s.mouth+' + accent');
if(clips.filter(c=>c.core).reduce((n,c)=>n+c.frames,0)!==516)throw Error('Core frame mismatch');
if(clips.reduce((n,c)=>n+c.frames,0)!==828)throw Error('All frame mismatch');
for(const c of clips){const folder=path.join(out,c.id);fs.mkdirSync(folder,{recursive:true});for(let i=0;i<c.frames;i++)fs.writeFileSync(path.join(folder,String(i).padStart(4,'0')+'.svg'),scene.render({...c.settings,frame:i,background:false}));}
const rows=[];function part(id,group,name,note,unit='eye pair'){rows.push({id,group,name,note,unit});}
for(const [i,name] of ['Round / available','Attentive / listening','Focused / thinking','Happy','Soft / concerned','Heavy / sleepy','Angled / skeptical','Wide / surprise'].entries())part('E'+String(i+1).padStart(2,'0'),'Eyes',name,'Left and right eyes on separate layers.');
for(const [i,name] of ['Rest','Smile','Concern','Smirk','Lips together / MBP','Open / AA','Wide / EE','Round / OO'].entries())part('M'+String(i+1).padStart(2,'0'),'Mouths',name,'Shared anchor; no baked glow.','mouth');
for(const [i,family] of scene.families.entries())for(const [j,state] of ['Half closed','Closed'].entries())part('B'+String(i*2+j+1).padStart(2,'0'),'Blinks',family+' / '+state,'Keep this family recognizable through the blink.');
for(const [i,name] of ['Surprise anticipation','Surprise overshoot','Happy squeeze','Sleepy droop'].entries())part('A'+String(i+1).padStart(2,'0'),'Reactions',name,'A brief accent. No speaking required.');
for(const [i,name] of ['Available B','Available C','Focused B','Focused C'].entries())part('R'+String(i+1).padStart(2,'0'),'Redraws',name,'Small contour variation; position stays fixed.');
const data={status:'Existing MIST assets and renderer. Artist drawing scope is a separate proposal.',states:scene.states,families:scene.families,parts:rows,clips,counts:{drawings:rows.length,eye_pairs:rows.filter(r=>r.unit==='eye pair').length,mouths:8,individual_parts:64,core_frames:516,all_frames:828,core_clips:23,all_clips:28},fps:24};
fs.writeFileSync(path.join(root,'plan.json'),JSON.stringify(data,null,2));fs.writeFileSync(path.join(root,'data.js'),'window.MIST_PLAN='+JSON.stringify(data)+';');console.log(JSON.stringify(data.counts));
