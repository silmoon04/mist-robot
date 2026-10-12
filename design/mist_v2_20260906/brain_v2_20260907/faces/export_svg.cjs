const fs=require('node:fs');
const path=require('node:path');
const {pathData}=require('../../../../brain/ui/static/face_runtime.js');
const frames=JSON.parse(fs.readFileSync(path.join(__dirname,'settled_frames.json'),'utf8'));
const folder=path.join(__dirname,'editable_svg');fs.mkdirSync(folder,{recursive:true});
for(const frame of frames){
  const paths=frame.layers.map((l,i)=>`<path id="${l.role}-${i}" data-part="${l.part}" d="${pathData(l.points,l.mode==='fill')}" fill="${l.mode==='fill'?'#5eeadd':'none'}" stroke="${l.mode==='stroke'?'#5eeadd':'none'}" stroke-width="${l.width}" stroke-linecap="round" stroke-linejoin="round" opacity="${l.opacity}"/>`).join('\n');
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 64" width="800" height="512"><title>MIST ${frame.expression}</title><defs><filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation=".55"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><rect id="background" width="100" height="64" fill="#07090c"/><g id="face" filter="url(#glow)">\n${paths}\n</g></svg>`;
  fs.writeFileSync(path.join(folder,frame.expression+'.svg'),svg);
}
console.log('Wrote '+frames.length+' editable SVG expressions to '+folder);
