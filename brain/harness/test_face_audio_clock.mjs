import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const box={console};box.window=box;box.globalThis=box;
vm.createContext(box);
for(const name of ['../face_assets/app/app_data.js','../ui/static/face_runtime.js']){
  vm.runInContext(await readFile(new URL(name,import.meta.url),'utf8'),box);
}
let audio={viseme:'rest',amount:0,time:0,active:false,source:'silence'};
const face=box.MistFaceRuntime.create(null,{data:box.MIST_DATA,autoStart:false,now:()=>1000});
face.startSpeech({sample:()=>audio,duration:Infinity,clock:()=>999});
assert.equal(face.snapshot(1000).viseme,'rest');
audio={viseme:'FV',amount:.4,time:.13,active:true,source:'elevenlabs_characters_audio_gated'};
const state=face.snapshot(5000);
assert.equal(state.viseme,'FV');assert.equal(state.speechTime,.13);
assert.equal(state.amount,.4);assert.equal(state.audioActive,true);
assert.equal(state.alignmentSource,'elevenlabs_characters_audio_gated');
audio={...audio,viseme:'TH'};
assert.equal(face.snapshot(5000).viseme,'TH','the original renderer retains dental cues through its LNT shape fallback');
audio={...audio,active:false};assert.equal(face.snapshot(5000).viseme,'rest');
face.stopSpeech();assert.equal(face.snapshot(5000).speaking,false);
face.startSpeech({events:[{time:0,viseme:'MBP'},{time:.1,viseme:'OO'}],duration:1,clock:()=>.2});
assert.equal(face.snapshot(5000).viseme,'OO','recorded alignment event arrays remain compatible');
face.startSpeech({events:[{time:0,viseme:'TH'}],duration:1,clock:()=>.2});
assert.equal(face.snapshot(5000).viseme,'TH','recorded dental cues must not become a rest mouth');
face.destroy();
console.log('PASS: live mouth cues follow audio sample callback, expose amplitude/timing provenance, stop cleanly, and preserve recorded event-array playback.');
