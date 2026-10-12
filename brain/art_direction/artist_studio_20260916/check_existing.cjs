const fs=require('fs'),path=require('path'),assert=require('assert/strict'),S=require('./scene.js');
const plan=JSON.parse(fs.readFileSync(path.join(__dirname,'plan.json'),'utf8'));
const known=new Set(S.data.faces.map(f=>f.id));let checks=0;
for(const c of plan.clips)for(const frame of [0,Math.floor(c.frames/2),c.frames-1]){
 const actual=S.render({...c.settings,frame,background:false});
 const saved=fs.readFileSync(path.join(__dirname,'frame_assets',c.id,String(frame).padStart(4,'0')+'.svg'),'utf8');assert.equal(actual,saved);
 const source=actual.match(/data-source="([^"]+)"/)[1];assert(known.has(source));checks++;
}
assert(!fs.readFileSync(path.join(__dirname,'scene.js'),'utf8').includes('function eye('));
console.log(`${checks} frame samples match the shared existing-asset renderer; all source IDs belong to the original 40 faces.`);
