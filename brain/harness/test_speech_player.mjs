import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const pending=[],played=[],states=[],errors=[],mouth=[],timings=[],requests=[];
const audio={currentTime:0,pause(){},removeAttribute(){this.src='';},load(){},
  play(){played.push(this.src);this.onplaying?.();return Promise.resolve();}};
const face={stopSpeech(){mouth.push('stopped');},startSpeech(value){mouth.push(value);}};
let url=0;
const context={AbortController,Blob,Uint8Array,console,atob,URL:{createObjectURL:()=>`audio-${++url}`,revokeObjectURL(){}},
  fetch:(url,options)=>{requests.push(JSON.parse(options.body));return new Promise(resolve=>pending.push(resolve));}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(new URL('../ui/static/speech_player.js',import.meta.url),'utf8'),context);
const player=context.MistSpeechPlayer.create({face,audio,onState:s=>states.push(s),onError:e=>errors.push(e),onTiming:e=>timings.push(e)});
const payload={audio_base64:'AAAA',mime_type:'audio/wav',duration_s:3,events:[{time:0,viseme:'AA'}]};
const reply=()=>({ok:true,json:async()=>payload});
const older=player.play('older');const newer=player.play('newer');
pending[1](reply());await newer;
pending[0](reply());await older;
assert.deepEqual(played,['audio-1'],'Stale response must not play.');
assert.equal(requests[0].client_protocol,2);
assert.equal(requests[0].purpose,'manual');
assert.ok(requests[0].request_id);
assert.deepEqual(timings.slice(-4).map(event=>event.stage),
  ['tts_response_headers','tts_response_body','audio_play_attempt','audio_playing']);
const speaking=mouth.at(-1); audio.currentTime=1.125;
assert.equal(speaking.clock(),1.125,'Mouth must follow audio media clock.');
audio.currentTime=1.125;
assert.equal(speaking.clock(),1.125,'Paused clock must not advance.');
player.stop();assert.equal(audio.src,'');assert.equal(mouth.at(-1),'stopped');
const cancelled=player.play('cancel during fetch');player.stop();pending[2](reply());await cancelled;
assert.equal(played.length,1,'Cancelled request must not restart.');
const completed=player.play('finish');pending[3](reply());await completed;audio.onended();
assert.equal(mouth.at(-1),'stopped');assert.equal(states.at(-1),'idle');
const failure=player.play('failure');pending[4]({ok:false,json:async()=>({error:'Voice unavailable'})});await failure;
assert.deepEqual(errors,['Voice unavailable']);
assert.equal(mouth.at(-1),'stopped');
const blockedStates=[],blockedErrors=[];
let fetchCount=0,attempts=0;
const blockedAudio={...audio,currentTime:0,src:'',play(){
  attempts++;
  if(attempts===1){const error=new Error("play() failed because the user didn't interact with the document first");error.name='NotAllowedError';return Promise.reject(error);}
  this.onplaying?.();return Promise.resolve();
}};
const blockedPlayer=context.MistSpeechPlayer.create({face,audio:blockedAudio,
  fetch:async()=>{fetchCount++;return reply();},
  onState:s=>blockedStates.push(s),onError:e=>blockedErrors.push(e)});
await blockedPlayer.play('Retain this generated clip');
assert.equal(blockedPlayer.speech,payload,'Autoplay rejection must retain the generated clip.');
assert.equal(blockedStates.at(-1),'blocked');
assert.deepEqual(blockedErrors,[],'Autoplay policy must not appear as a raw chat error.');
assert.ok(blockedAudio.src);
await blockedPlayer.resume();
assert.equal(fetchCount,1,'Gesture retry must reuse audio without another TTS request.');
assert.equal(attempts,2);assert.equal(blockedStates.at(-1),'playing');
blockedPlayer.stop();
assert.equal(blockedPlayer.speech,null);
assert.equal(await blockedPlayer.resume(),false,'Stopped clips must not resume.');
console.log('PASS: speech ownership, cancellation, media clock, timing stages, completion, provider error, retained autoplay retry without regeneration.');
