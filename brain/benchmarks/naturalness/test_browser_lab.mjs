import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const source = (await readFile(new URL('./browser_lab.js',import.meta.url),'utf8')).replace(/^import .*;\r?\n/gm,'');
const {parseFixtureWav,resolveTrigger,compactFace,summarizeCapture,recordingContext,
  drainPlayback,observeGeneration,StreamingResampler,mixPcm16,ECHO_WORKLET_SOURCE,
  observePlaybackCancellation,startedQueuedPlayback,LAB_CAPTURE_VERSION,startRecordingClock,createRecorder} =
  await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const playbackSource = await readFile(new URL('../../duplex/static/playback.js',import.meta.url),'utf8');
const {Playback} = await import('data:text/javascript;base64,'+Buffer.from(playbackSource).toString('base64'));

function wav({channels=1,rate=16000,bits=16,extra=false} = {}) {
  const offset = extra ? 54 : 44, buffer = Buffer.alloc(offset+640);
  buffer.write('RIFF');buffer.writeUInt32LE(buffer.length-8,4);buffer.write('WAVE',8);
  buffer.write('fmt ',12);buffer.writeUInt32LE(16,16);buffer.writeUInt16LE(1,20);buffer.writeUInt16LE(channels,22);
  buffer.writeUInt32LE(rate,24);buffer.writeUInt32LE(rate*channels*bits/8,28);buffer.writeUInt16LE(channels*bits/8,32);buffer.writeUInt16LE(bits,34);
  if (extra) {buffer.write('JUNK',36);buffer.writeUInt32LE(1,40);buffer.writeUInt8(7,44);}
  buffer.write('data',offset-8);buffer.writeUInt32LE(640,offset-4);
  for(let index=offset;index<buffer.length;index+=2) buffer.writeInt16LE(1234,index);
  return buffer.buffer.slice(buffer.byteOffset,buffer.byteOffset+buffer.byteLength);
}

assert.equal(parseFixtureWav(wav()).duration_ms,20);
assert.equal(parseFixtureWav(wav({extra:true})).pcm.length,640,'WAV parser must honor padded metadata chunks');
assert.throws(() => parseFixtureWav(wav({channels:2})),/PCM16 mono/);
assert.throws(() => parseFixtureWav(wav({rate:24000})),/PCM16 mono/);
assert.throws(() => parseFixtureWav(wav().slice(0,100)),/Truncated/);

const seen = {ready_ms:25,last_input_end_ms:400,playback_starts:[
  {t_ms:100,epoch:0,sequence:0},{t_ms:210,epoch:0,sequence:0},{t_ms:500,epoch:1,sequence:1}],
  playback_idles:[{t_ms:350},{t_ms:700}],excluded_playback_keys:new Set(['0:0'])};
assert.equal(resolveTrigger({trigger:'ready'},seen,0),25);
assert.equal(resolveTrigger({trigger:'after_playback'},seen,200),500,'Old response restart cannot satisfy new-response trigger');
assert.equal(resolveTrigger({trigger:'after_playback',playback_index:2},seen,200),null);
assert.equal(resolveTrigger({trigger:'after_input'},seen,200),400);
assert.equal(resolveTrigger({trigger:'after_idle'},seen,400),700);
assert.equal(resolveTrigger({trigger:'after_idle'},{...seen,action_had_playback:true},200),350,'Backchannel can wait for the current response to drain');
assert.equal(resolveTrigger({trigger:'after_idle'},{...seen,playback_starts:[]},200),null,'Silence must not fabricate a completed response');
assert.equal(resolveTrigger({trigger:'after_playback'},{...seen,excluded_playback_keys:new Set()},0),100,'Seeded speech can trigger interruption');
assert.throws(() => resolveTrigger({trigger:'guess'},seen,0),/Unknown/);
assert.equal(LAB_CAPTURE_VERSION,'2026-09-24-continuous-recorder-v2');
const cancelled={playback_starts:[{t_ms:100,epoch:0,sequence:0}],playback_idles:[],playback_cancellations:[],action_had_playback:true};
const queuedPlayer={epoch:0,segments:[{event:{epoch:0,seq:0}}]};
assert.equal(startedQueuedPlayback(cancelled,queuedPlayer.segments).length,1);
assert.equal(resolveTrigger({trigger:'after_idle'},cancelled,200),null);
const resetEnd=observePlaybackCancellation(cancelled,queuedPlayer,1,250);
assert.equal(resetEnd.type,'playback_cancelled');assert.equal(resetEnd.reason,'audio_reset');
assert.equal(resolveTrigger({trigger:'after_idle'},cancelled,200),250,'A reset that cancels started speech completes the after_idle boundary');
assert.equal(cancelled.playback_idles.length,0,'Cancellation must not fabricate a natural playback idle callback');
assert.equal(resolveTrigger({trigger:'after_idle'},cancelled,300),null,'A reset before this action cannot satisfy its idle trigger');
const unstarted={playback_starts:[],playback_idles:[],action_had_playback:true};
assert.equal(observePlaybackCancellation(unstarted,queuedPlayer,1,250),null);
assert.equal(resolveTrigger({trigger:'after_idle'},unstarted,200),null,'Queued audio cancelled before its first output start is not completed speech');
assert.equal(observePlaybackCancellation(cancelled,{epoch:1,segments:[{event:{epoch:1,seq:0}}]},2,300),null,'An old epoch start cannot qualify a new epoch queue');
assert.equal(observePlaybackCancellation(cancelled,{epoch:1,segments:[]},2,300),null,'Reset of an empty queue is not a new completion');
assert.equal(observePlaybackCancellation(cancelled,{...queuedPlayer,epoch:1},0,300),null,'Stale reset does not end playback');
const responseCancelled={playback_starts:[{t_ms:500,epoch:1,sequence:1}],playback_idles:[],action_had_playback:false};
observePlaybackCancellation(responseCancelled,{epoch:1,segments:[{event:{epoch:1,seq:1}}]},2,600);
assert.equal(resolveTrigger({trigger:'after_idle'},responseCancelled,400),600,'A response that starts after the input can also end by cancellation');

const shot = compactFace({expression:'sad',viseme:'AA',layers:[{points:['large']}],handdrawn:{activity:{id:'reading'}},renderer:'handdrawn'});
assert.equal(shot.layers,undefined);assert.equal(shot.handdrawn.activity.id,'reading');
const empty = summarizeCapture({events:[],frames:[],inputs:[]});
assert.equal(empty.first_playback_ms,null);assert.equal(empty.last_scheduled_output_end_ms,null);
const summary = summarizeCapture({events:[{type:'playback_started',t_ms:100},{type:'audio_reset',t_ms:140}],
  frames:[{t_ms:0},{t_ms:80}],inputs:[{step:0,file:'x.wav',start_ms:120,end_ms:200,packets:[[120,640,7]],playback_active_at_start:true}]});
assert.equal(summary.input_turns[0].next_playback_after_input_end_ms,null,'An old response must not be scored as a new one');
assert.equal(summary.input_turns[0].reset_after_input_start_ms,20);
assert.equal(summary.max_frame_gap_ms,80);
assert.equal(summary.next_playback_scope,'nearest_playback_after_input_end_without_response_attribution');

let time=0;
const drain=await drainPlayback({isPlaying:() => time<2600,now:() => time,wait:async ms => {time+=ms;}});
assert.deepEqual(drain,{extended:true,duration_ms:2800,timed_out:false,settled:true},'A queued 2.6-second tail gets captured with its resting face');
time=0;
const timeout=await drainPlayback({isPlaying:() => true,now:() => time,wait:async ms => {time+=ms;}});
assert.equal(timeout.duration_ms,20000);assert.equal(timeout.timed_out,true,'Continuing output must have a bounded, explicit truncation');
assert.equal((await drainPlayback({isPlaying:() => false,now:() => 0,wait:async () => assert.fail('Silent capture must not extend')})).extended,false);
time=0;
const resumed=await drainPlayback({isPlaying:() => time<100 || (time>=200 && time<400),now:() => time,wait:async ms => {time+=ms;}});
assert.equal(resumed.duration_ms,600,'A short queue gap during drain must not truncate newly arriving audio');
await assert.rejects(() => drainPlayback({isPlaying:() => true,now:() => 0,wait:async () => {},check:() => {throw Error('cancel');}}),/cancel/);
time=0;
const sentenceGap=await drainPlayback({isPlaying:() => time<100 || (time>=1700 && time<2300),
  isGenerating:() => time<2100,now:() => time,wait:async ms => {time+=ms;},settleMs:2000});
assert.equal(sentenceGap.duration_ms,4300,'A 1.6-second queue gap cannot stop capture while the assistant is generating');
time=0;
const generationTimeout=await drainPlayback({isPlaying:() => false,isGenerating:() => true,
  now:() => time,wait:async ms => {time+=ms;}});
assert.equal(generationTimeout.timed_out,true);assert.equal(generationTimeout.generation_pending,true);
assert.equal(generationTimeout.playback_pending,false);
time=0;
const unsettled=await drainPlayback({isPlaying:() => time<300,now:() => time,wait:async ms => {time+=ms;},maxMs:400});
assert.equal(unsettled.timed_out,true);assert.equal(unsettled.playback_pending,false,'A drain deadline during the quiet window remains an explicit timeout');
time=0;
const recentOutput=await drainPlayback({isPlaying:() => false,lastActivityMs:() => -50,
  now:() => time,wait:async ms => {time+=ms;}});
assert.equal(recentOutput.extended,true,'Recent final audio still needs a stable drain boundary');
const generation={pending:false,last_activity_ms:null,completed_ms:null};
observeGeneration(generation,{type:'state',state:'thinking'},10);assert.equal(generation.pending,true);
observeGeneration(generation,{type:'transcript_delta',role:'assistant',text:'First sentence.'},20);
observeGeneration(generation,{type:'audio'},30);assert.equal(generation.pending,true,'An audio packet is not a generation completion');
observeGeneration(generation,{type:'transcript_done',role:'assistant',text:'Done.'},40);assert.equal(generation.pending,false);
observeGeneration(generation,{type:'audio'},50);assert.equal(generation.pending,false,'Final TTS packets after model completion must not invent another generation');
assert.equal(generation.last_activity_ms,50);assert.equal(generation.completed_ms,40);
const preservedBackchannel={type:'transcript_done',role:'user',text:'yeah',backchannel:true,floor_preserved:true};
observeGeneration(generation,preservedBackchannel,60);
assert.deepEqual(generation,{pending:false,last_activity_ms:50,completed_ms:40},'A preserved backchannel after assistant completion must not create a pending reply');
observeGeneration(generation,{type:'transcript_delta',role:'assistant',text:'Next sentence.'},70);
observeGeneration(generation,preservedBackchannel,80);
assert.deepEqual(generation,{pending:true,last_activity_ms:70,completed_ms:40},'A preserved backchannel must not clear assistant generation already in progress');
observeGeneration(generation,{type:'transcript_done',role:'assistant',text:'Done.'},90);
observeGeneration(generation,{...preservedBackchannel,floor_preserved:false},100);
assert.equal(generation.pending,true,'A non-preserved user turn still requires a reply');
observeGeneration(generation,{type:'transcript_done',role:'assistant',text:'Done.'},110);
observeGeneration(generation,{type:'transcript_done',role:'user',text:'Explain that again.'},120);
assert.equal(generation.pending,true,'An ordinary user transcript still marks generation pending');

for (const rate of [44100,48000]) {
  const resampler=new StreamingResampler(rate),received=[];
  for (let offset=0;offset<rate;offset+=128) received.push(...resampler.push(new Float32Array(Math.min(128,rate-offset)).fill(.125)));
  assert.equal(received.length,16000,`One second of ${rate} Hz render quanta becomes one second at 16 kHz`);
  assert(received.every(sample => Math.abs(sample-.125)<1e-7),'Render-quantum boundaries must retain continuous amplitude');
}
const near=new Uint8Array(6),nearView=new DataView(near.buffer);
nearView.setInt16(0,20000,true);nearView.setInt16(2,-20000,true);nearView.setInt16(4,1234,true);
const mixed=mixPcm16(new Float32Array([.75,-.75,0,0]),near);
const mixedView=new DataView(mixed.pcm.buffer);
assert.equal(mixedView.getInt16(0,true),32767);assert.equal(mixedView.getInt16(2,true),-32768);
assert.equal(mixedView.getInt16(4,true),1234);assert.equal(mixedView.getInt16(6,true),0);
assert.equal(mixed.clipped,2);assert.equal(mixed.consumed,6,'Final fixture packet is zero-padded without inventing input samples');

let Processor;
class FakeWorkletProcessor {
  constructor() {this.messages=[];this.port={postMessage:event => this.messages.push(event)};}
}
new Function('AudioWorkletProcessor','sampleRate','currentTime','registerProcessor',ECHO_WORKLET_SOURCE)(
  FakeWorkletProcessor,48000,0,(name,implementation) => {assert.equal(name,'mist-lab-echo');Processor=implementation;});
const processor=new Processor();
for (let offset=0;offset<48000;offset+=128) {
  const input=new Float32Array(Math.min(128,48000-offset)).fill(.125),output=new Float32Array(input.length).fill(1);
  assert.equal(processor.process([[input]],[[output]]),true);
  assert(output.every(value => value===0),'The capture branch must never duplicate speech at the speaker');
}
assert.equal(processor.messages.length,50,'Worklet emits 50 uplink packets per second');
for (const packet of processor.messages) {
  const samples=new Float32Array(packet.samples);assert.equal(samples.length,320);assert(samples.every(value => value===.125));
}

// Exercise the real Playback with the recording proxy to catch double speaker
// routing or instrumentation that changes the native schedule.
const destination = {}, recording = {}, made = [], zeroSources = [], events = [];
const context = {currentTime:0,state:'running',destination,
  createConstantSource() {
    const source={offset:{value:1},connections:[],stops:0,connect(target){this.connections.push(target);},
      start(){this.started=true;},stop(){this.stops++;},disconnect(){this.disconnected=true;}};
    zeroSources.push(source);return source;
  },
  createBuffer(channels,length,rate) {return {duration:length/rate,getChannelData:() => new Float32Array(length)};},
  createBufferSource() {
    const source = {connections:[],connect(target) {this.connections.push(target);},disconnect() {},
      start(at) {this.started=at;},stop() {this.stopped=true;},addEventListener() {}};
    made.push(source);return source;
  }};
const record = (type,values) => events.push({type,...values});record.now = () => 50;
const recordingClock=startRecordingClock(context,recording,record);
assert.equal(zeroSources[0].offset.value,0,'Recording clock must generate exactly zero-valued samples');
assert.deepEqual(zeroSources[0].connections,[recording],'Silence source must connect only to the recording destination');
assert.equal(zeroSources[0].started,true,'Recording track is activated before voice playback exists');
const packet = {epoch:0,seq:0,sample_rate:16000,pcm:Buffer.alloc(640).toString('base64')};
let player;
const proxy = recordingContext(context,recording,record,() => player,() => packet);
const actualObservations={playback_starts:[],playback_idles:[],action_had_playback:true};
player = new Playback(proxy,{startSpeech(){},stopSpeech(){}},() => {},
  () => actualObservations.playback_idles.push({t_ms:context.currentTime*1000}),
  event => actualObservations.playback_starts.push({t_ms:context.currentTime*1000,epoch:event.epoch,sequence:event.seq}));
player.append(packet);
assert.equal(made.length,1);
assert.deepEqual(made[0].connections,[recording,destination],'One recording path and exactly one speaker path');
assert.equal(made[0].started,.2,'Production startup buffer is unchanged');
const scheduleEvent=events.find(event => event.type==='source_scheduled');
assert.equal(scheduleEvent.estimated_output_start_ms,250);
assert.equal(scheduleEvent.estimated_output_end_ms,270);
assert.equal(scheduleEvent.timing_kind,'software_output_estimate_not_acoustic');
context.currentTime=.21;clearTimeout(player.timer);player.tick();
assert.equal(actualObservations.playback_starts.length,1);
assert(observePlaybackCancellation(actualObservations,player,1,215));
player.reset(1);
assert.equal(made[0].stopped,true);
assert.equal(events.at(-1).type,'source_stop_called');
assert.equal(actualObservations.playback_idles.length,0,'Production reset does not invoke onIdle');
assert.equal(resolveTrigger({trigger:'after_idle'},actualObservations,210),215,'Observed cancellation must bridge the production reset callback gap');
assert.equal(zeroSources[0].stops,0,'Playback reset must leave the recording silence clock running');
recordingClock.stop();recordingClock.stop();
assert.equal(zeroSources[0].stops,1);assert.equal(zeroSources[0].disconnected,true);
assert.equal(recordingClock.metadata.stopped_context_s,.21);

const realMediaRecorder=globalThis.MediaRecorder;
let recorderTime=100;
class FakeMediaRecorder {
  static isTypeSupported(){return true;}
  constructor(){this.state='inactive';}
  start(){this.state='recording';this.onstart?.();}
  stop(){
    this.state='inactive';recorderTime+=75;
    this.ondataavailable?.({data:new Blob(['test bytes']),timecode:0});this.onstop?.();
  }
}
try {
  globalThis.MediaRecorder=FakeMediaRecorder;
  const metadataEvents=[],clockRecord=(type,values) => metadataEvents.push({type,...values});
  clockRecord.now=() => recorderTime;
  const recorder=createRecorder({},'audio',clockRecord);
  recorderTime=1100;
  const capture=await recorder.stop();
  assert.equal(capture.start_ms,100);assert.equal(capture.end_ms,1100,'Recorded interval ends at the stop request, not after encoder flush');
  assert.equal(capture.stop_event_ms,1175);assert.equal(capture.encoder_flush_ms,75);
  assert.equal(capture.clock_id,'browser_performance');assert.equal(capture.chunks[0].timecode_ms,0);
  assert.equal(metadataEvents.find(event => event.type==='recording_started').clock_id,'browser_performance');
} finally {
  if (realMediaRecorder===undefined) delete globalThis.MediaRecorder;
  else globalThis.MediaRecorder=realMediaRecorder;
}
console.log('browser lab: WAV validation, adaptive triggers and reset cancellation, bounded drain, continuous recording clock and encoder metadata, real Playback routing, echo resampling/mixing and 20 ms worklet packets passed');
