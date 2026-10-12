// Preserve v4 reports while running the unchanged independent identity criteria.
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path');
let source=fs.readFileSync(path.join(__dirname,'identity_after.cjs'),'utf8')
  .replace('const report={version:4,','const report={version:5,')
  .replaceAll("'identity_v4.json'","'identity_v5.json'")
  .replaceAll("'identity_v4.md'","'identity_v5.md'");
if(process.argv.includes('--candidate'))source=source
  .replaceAll("'identity_after.json'","'identity_candidate_v5.json'")
  .replaceAll("'identity_after.md'","'identity_candidate_v5.md'")
  .replace(/^\s*fs.copyFileSync.*$/gm,'');
vm.runInNewContext(source,{require,__dirname,console,Buffer,process,Uint8ClampedArray},{filename:__filename});
