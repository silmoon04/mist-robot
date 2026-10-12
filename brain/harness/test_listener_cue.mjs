import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const source=await readFile(new URL('../duplex/static/listener_cue.js',import.meta.url),'utf8');
const {newListenerCue}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));

const realSetTimeout=globalThis.setTimeout,realClearTimeout=globalThis.clearTimeout,realNow=Date.now;
let timerId=0,now=1000;
const timers=new Map();
globalThis.setTimeout=(fn)=>{timers.set(++timerId,fn);return timerId;};
globalThis.clearTimeout=id=>timers.delete(id);
Date.now=()=>now;

function fixture(){
  const sources=[],speech=[],events=[];let stopped=0,disconnected=0;
  const context={currentTime:0,state:'running',destination:{},outputLatency:0,baseLatency:0,
    createBuffer(channels,length,rate){assert.equal(channels,1);return{duration:length/rate,getChannelData(){return new Float32Array(length);}};},
    createBufferSource(){const node={buffer:null,onended:null,connect(){},disconnect(){disconnected++;},start(at){this.startAt=at;},stop(){stopped++;}};sources.push(node);return node;},
    createGain(){return{gain:{value:1},connect(){},disconnect(){disconnected++;}};}};
  const face={startSpeech(value){speech.push(value);},stopSpeech(){speech.push('stopped');}};
  const cue=newListenerCue(context,face,event=>events.push(event));
  return {cue,context,face,sources,speech,events,get stopped(){return stopped;},get disconnected(){return disconnected;}};
}
function pcm(seconds=.12,rate=24000){const bytes=Buffer.alloc(Math.round(seconds*rate)*2);for(let i=0;i<bytes.length;i+=2)bytes.writeInt16LE(5000,i);return bytes.toString('base64');}
function cue(overrides={}){return{type:'listener_cue',cue_id:'cue-1',utterance_id:'u-1',transcript_revision:1,
  pcm:pcm(),sample_rate:24000,duration_ms:120,mouth_cues:[{time:0,viseme:'MBP',amount:.7},{time:.05,viseme:'AA',amount:.8}],
  text:'Mm-hmm.',epoch:0,valid_for_ms:350,...overrides};}
function open(target,id='u-1',revision=1){assert.equal(target.cue.observe({type:'user_transcript',utterance_id:id,revision,text:'I was saying…',final:false}),true);}
function step(target,timeSeconds,elapsedMs=16){target.context.currentTime=timeSeconds;now+=elapsedMs;const pending=[...timers.values()];timers.clear();for(const fn of pending)fn();}
function phases(target,id='cue-1'){return target.events.filter(event=>event.cue_id===id).map(event=>event.phase);}

try{
  {
    const f=fixture();open(f);const stale=cue({transcript_revision:0});
    assert.equal(f.cue.play(stale),false);assert.equal(f.sources.length,0);
    assert.equal(f.events.at(-1).phase,'skipped');assert.equal(f.events.at(-1).reason,'stale_user_transcript');
    assert.equal(f.cue.play(cue(),{normalPlaying:true}),false);assert.equal(f.sources.length,0);
    assert.equal(f.events.at(-1).reason,'assistant_playing');
    assert.equal(f.cue.play(cue(),{enabled:false}),false);assert.equal(f.sources.length,0);
    assert.equal(f.events.at(-1).reason,'disabled');
    f.cue.reset();assert.equal(f.speech.length,0,'reset without an owned cue must not stop normal speech');
  }
  {
    const f=fixture();open(f);
    assert.equal(f.cue.play(cue()),true);assert.equal(f.sources.length,1);
    assert.equal(f.sources[0].startAt,.02,'cached audio starts with only a 20 ms reserve');
    assert.equal(f.sources[0].buffer.duration,.12,'the independent source holds only the bounded decoded cue');
    assert.equal(f.cue.sample().active,false,'scheduled audio is not speaking before its output start');
    step(f,.02);assert.deepEqual(phases(f),['started']);assert.equal(f.speech.length,1);
    const speech=f.speech[0];assert.equal(typeof speech.sample,'function');
    assert.equal(speech.sample().active,true);assert.equal(speech.sample().viseme,'MBP');
    step(f,.071);assert.equal(speech.sample().viseme,'AA','cached mouth cues follow the independent output clock');
    assert.deepEqual(phases(f),['started']);
    step(f,.141);assert.deepEqual(phases(f),['started','ended']);assert.equal(f.cue.sample().active,false);
    assert.equal(f.speech.at(-1),'stopped');
  }
  {
    const f=fixture();open(f);assert.equal(f.cue.play(cue()),true);
    f.cue.observe({type:'user_transcript',utterance_id:'u-1',revision:2,text:'Actually, wait.',final:false});
    assert.deepEqual(phases(f),['cancelled']);assert.equal(f.events.at(-1).reason,'new_user_transcript');
    assert.equal(f.stopped,1);assert.equal(f.cue.sample().active,false);
    assert.equal(f.cue.play(cue(),{normalPlaying:false}),false,'the invalidated partial revision cannot revive its cue');
    assert.equal(f.events.at(-1).reason,'stale_user_transcript');
    assert.equal(f.cue.observe({type:'audio_reset',epoch:1}),true);
    open(f,'u-1',2);assert.equal(f.cue.play(cue({transcript_revision:2,epoch:0})),false);
    assert.equal(f.events.at(-1).reason,'stale_audio_epoch');
  }
  {
    const f=fixture();open(f);assert.equal(f.cue.play(cue()),true);step(f,.02);
    f.cue.observe({type:'user_transcript',utterance_id:'u-1',revision:2,text:'More words',final:false});
    assert.deepEqual(phases(f),['started'],'same-floor transcript revision must let a started syllable finish');
    f.cue.observe({type:'user_transcript',utterance_id:'u-1',revision:2,text:'More words',final:true});
    assert.deepEqual(phases(f),['started'],'same-floor finalization must not clip a started syllable');
    step(f,.141);assert.deepEqual(phases(f),['started','ended']);
    assert.equal(f.cue.play(cue({cue_id:'late',transcript_revision:2})),false,'finished user floors cannot receive late cues');
    assert.equal(f.events.at(-1).reason,'stale_user_transcript');
  }
  {
    const f=fixture();open(f);assert.equal(f.cue.play(cue()),true);step(f,.02);
    assert.equal(f.cue.play(cue({cue_id:'second'})),false,'there is no cue queue');
    assert.deepEqual(phases(f,'second'),['skipped']);assert.equal(f.cue.sample().active,true);
    f.cue.observe({type:'user_transcript',utterance_id:'u-2',revision:0,text:'New thought',final:false});
    assert.deepEqual(phases(f),['started','cancelled'],'a new floor stops even an active cached cue');
    assert.equal(f.cue.sample().active,false);assert.equal(f.speech.at(-1),'stopped');
  }
  {
    const f=fixture();open(f);assert.equal(f.cue.play(cue()),true);
    f.cue.observe({type:'listener_cue_cancel',reason:'assistant_reply'});
    assert.deepEqual(phases(f),['cancelled']);assert.equal(f.speech.length,0,'queued cancellation must not stop the normal face timeline');
    assert.equal(f.stopped,1);
  }
  {
    const f=fixture();open(f);assert.equal(f.cue.play(cue()),true);step(f,.02);
    assert.equal(f.cue.play(cue({cue_id:'disabled'}),{enabled:false}),false);
    assert.deepEqual(phases(f),['started','cancelled']);assert.equal(f.speech.at(-1),'stopped');
  }
  {
    const f=fixture();open(f);assert.equal(f.cue.play(cue()),true);step(f,.02);
    assert.equal(f.cue.play(cue({cue_id:'assistant'}),{normalPlaying:true}),false);
    assert.deepEqual(phases(f),['started','cancelled']);assert.equal(f.events.at(-1).reason,'assistant_playing');
    assert.equal(f.cue.sample().active,false);
  }
  {
    const f=fixture();open(f);assert.equal(f.cue.play(cue()),true);
    f.context.state='suspended';step(f,.01,400);
    assert.deepEqual(phases(f),['skipped'],'a cue that misses its short start window never plays later');
    assert.equal(f.events.at(-1).reason,'expired_before_start');assert.equal(f.speech.length,0);
  }
  {
    const f=fixture();open(f);assert.equal(f.cue.play(cue()),true);
    f.context.state='suspended';now+=400;
    // Simulate a backgrounded tab: the timer did not run during suspension.
    f.context.state='running';step(f,.02,0);
    assert.deepEqual(phases(f),['skipped'],'resume must check TTL before starting scheduled audio');
    assert.equal(f.events.at(-1).reason,'expired_before_start');assert.equal(f.speech.length,0);
    assert.equal(f.cue.sample().active,false);
  }
  {
    const f=fixture();open(f);assert.equal(f.cue.play(cue({valid_for_ms:351})),false);
    assert.equal(f.events.at(-1).reason,'expired_cue');
    assert.equal(f.cue.play(cue({cue_id:'bad-duration',duration_ms:1600})),false);
    assert.equal(f.events.at(-1).reason,'invalid_duration');
  }
  console.log('Listener cue scheduling, mouth timing, transcript revisions and cancellation passed.');
} finally {
  globalThis.setTimeout=realSetTimeout;globalThis.clearTimeout=realClearTimeout;Date.now=realNow;
}
