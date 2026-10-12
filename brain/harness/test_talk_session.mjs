import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';

const context={AbortController,Blob,console};
vm.createContext(context);
vm.runInContext(fs.readFileSync(new URL('../ui/static/talk_session.js',import.meta.url),'utf8'),context);
const {create}=context.MistTalkSession;
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const clip=()=>new Blob(['spoken words'],{type:'audio/webm'});
function gate(){
  let resolve,reject;
  const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});
  return {promise,resolve,reject};
}

function fixture(options={}){
  const captures=[],states=[],errors=[],transcripts=[],transcriptions=[],submissions=[],events=[];
  let playback=false,busy=false;
  const session=create({
    captureFactory(callbacks){
      const capture={callbacks,starts:0,stops:0,
        start(){
          this.starts++;
          events.push('capture-start');
          if(options.open) return options.open(this);
          callbacks.onState({status:'listening',active:true});
          return true;
        },
        stop(){this.stops++;events.push('capture-stop');callbacks.onState({status:'idle',active:false});},
      };
      captures.push(capture);
      return capture;
    },
    transcribe(blob,meta){
      transcriptions.push({blob,meta});events.push('transcribe');
      return options.transcribe ? options.transcribe(blob,meta) : Promise.resolve('  Hello MIST.  ');
    },
    submit(text,meta){
      submissions.push({text,meta});events.push('submit');
      return options.submit ? options.submit(text,meta) : Promise.resolve(true);
    },
    interrupt(meta){events.push('interrupt');return options.interrupt?.(meta);},
    stopSpeech(){events.push('stop-speech');options.stopSpeech?.();},
    isReplyBusy:()=>busy,
    isPlaybackActive:()=>playback,
    onState(value){states.push(value);return options.onState?.(value);},
    onTranscript(text,meta){transcripts.push({text,meta});return options.onTranscript?.(text,meta);},
    onError(message){errors.push(message);return options.onError?.(message);},
  });
  return {session,captures,states,errors,transcripts,transcriptions,submissions,events,
    get capture(){return captures.at(-1);},
    set busy(value){busy=value;},set playback(value){playback=value;},
    utterance(blob=clip(),meta={}){return this.capture.callbacks.onUtterance(blob,meta);},
    speech(meta={}){return this.capture.callbacks.onSpeechStart(meta);},
  };
}

test('capture starts only explicitly, starts once, and forwards live playback state',async()=>{
  const opening=gate();
  const f=fixture({open:()=>opening.promise});
  assert.equal(f.captures.length,0);
  assert.equal(f.session.getState().status,'idle');
  const first=f.session.start();
  assert.equal(f.capture.starts,1,'Capture start must run before start() yields.');
  assert.equal(f.session.start(),first);
  assert.equal(f.session.getState().status,'starting');
  f.playback=true;
  assert.equal(f.capture.callbacks.isPlaybackActive(),true);
  opening.resolve(true);
  assert.equal(await first,true);
  const snapshot=f.session.getState();snapshot.status='changed';
  assert.equal(f.session.getState().status,'listening');
  await f.session.stop();
  assert.equal(f.capture.callbacks.isPlaybackActive(),false);
  assert.equal(f.session.getState().active,false);
  assert.equal(f.transcriptions.length,0);
});

test('capture callback waits for acceptance and releases while reply remains busy',async()=>{
  const accepted=gate();
  const f=fixture({submit:()=>accepted.promise});
  await f.session.start();
  await f.speech();
  const task=f.utterance(clip(),{durationMs:1500,speechMs:800,bargeIn:false});
  let settled=false;task.then(()=>{settled=true;});
  await flush();
  assert.equal(f.session.getState().status,'submitting');
  assert.equal(settled,false);
  assert.equal(f.submissions[0].text,'Hello MIST.');
  assert.equal(f.transcriptions[0].meta.durationMs,1500);
  assert.equal(f.transcriptions[0].meta.speechMs,800);
  f.busy=true;
  accepted.resolve(true);
  assert.equal(await task,true);
  assert.equal(f.session.getState().status,'listening');
  assert.equal(f.session.getState().active,true);
  assert.equal(f.capture.stops,0);
  await f.session.stop();
});

test('stop aborts STT and settles the callback even when the provider ignores abort',async()=>{
  const transcription=gate();
  const f=fixture({transcribe:()=>transcription.promise});
  await f.session.start();
  const oldCapture=f.capture;
  const task=f.utterance();
  await flush();
  const signal=f.transcriptions[0].meta.signal;
  await f.session.stop();
  assert.equal(signal.aborted,true);
  assert.equal(await task,false);
  assert.ok(oldCapture.stops>0);
  transcription.resolve('Do not send this.');
  await flush();
  oldCapture.callbacks.onState({status:'speaking',active:true});
  assert.equal(await oldCapture.callbacks.onUtterance(clip()),false);
  assert.equal(f.session.getState().status,'idle');
  assert.equal(f.transcripts.length,0);
  assert.equal(f.submissions.length,0);
  assert.deepEqual(f.errors,[]);
});

test('stop aborts pending acceptance without publishing a late completion',async()=>{
  const accepted=gate();
  const f=fixture({submit:()=>accepted.promise});
  await f.session.start();
  const task=f.utterance();
  await flush();
  assert.equal(f.submissions.length,1);
  await f.session.stop();
  assert.equal(f.submissions[0].meta.signal.aborted,true);
  assert.equal(await task,false);
  const states=f.states.length;
  accepted.resolve(true);
  await flush();
  assert.equal(f.states.length,states);
  assert.equal(f.session.getState().status,'idle');
});

test('identical callbacks share one task and overlapping utterances cannot submit',async()=>{
  const transcription=gate();
  const f=fixture({transcribe:()=>transcription.promise});
  await f.session.start();
  const blob=clip();
  const first=f.utterance(blob);
  assert.equal(f.utterance(blob),first);
  assert.equal(await f.utterance(),false);
  await flush();
  assert.equal(f.transcriptions.length,1);
  transcription.resolve('One turn.');
  assert.equal(await first,true);
  assert.equal(await f.utterance(blob),true);
  assert.equal(f.submissions.length,1);
  assert.equal(await f.utterance(),true);
  assert.equal(f.submissions.length,2);
  await f.session.stop();
});

test('empty audio and empty transcripts never become chat turns',async()=>{
  const f=fixture({transcribe:async()=> ' \n\t '});
  await f.session.start();
  assert.equal(await f.utterance(new Blob([])),false);
  assert.equal(f.transcriptions.length,0);
  assert.equal(await f.utterance(),false);
  assert.equal(f.transcripts.length,0);
  assert.equal(f.submissions.length,0);
  assert.equal(f.session.getState().status,'listening');
  await f.session.stop();
});

test('a rejected old transcription cannot unlock or overwrite a restarted session',async()=>{
  const old=gate(),fresh=gate();
  let calls=0;
  const f=fixture({transcribe:()=>++calls===1 ? old.promise : fresh.promise});
  await f.session.start();
  const oldCapture=f.capture;
  const oldTask=f.utterance();
  await flush();
  await f.session.stop();
  await f.session.start();
  const freshTask=f.utterance();
  await flush();
  old.reject(new Error('Late provider error.'));
  assert.equal(await oldTask,false);
  await flush();
  oldCapture.callbacks.onError('Late microphone error.');
  assert.equal(f.session.getState().status,'transcribing');
  assert.equal(await f.utterance(),false);
  assert.equal(f.transcriptions.length,2);
  assert.deepEqual(f.errors,[]);
  fresh.resolve('New session only.');
  assert.equal(await freshTask,true);
  assert.deepEqual(f.submissions.map(value=>value.text),['New session only.']);
  await f.session.stop();
});

test('barge-in stops playback immediately and waits for interruption without closing capture',async()=>{
  const interrupted=gate();
  const f=fixture({interrupt:()=>interrupted.promise});
  f.busy=true;f.playback=true;
  await f.session.start();
  const speech=f.speech({bargeIn:true});
  assert.deepEqual(f.events.slice(-2),['stop-speech','interrupt']);
  assert.equal(f.capture.stops,0);
  const task=f.utterance(clip(),{bargeIn:true});
  await flush();
  assert.equal(f.transcriptions.length,1,'Capture can finish while interruption is pending.');
  assert.equal(f.submissions.length,0);
  assert.equal(f.capture.stops,0);
  f.busy=false;
  interrupted.resolve();
  assert.equal(await speech,true);
  assert.equal(await task,true);
  assert.equal(f.events.filter(value=>value==='interrupt').length,1);
  assert.equal(f.submissions.length,1);
  await f.session.stop();
});

test('stopping while interruption is pending prevents the transcript from submitting',async()=>{
  const interrupted=gate();let signal;
  const f=fixture({interrupt:meta=>{signal=meta.signal;return interrupted.promise;}});
  f.busy=true;
  await f.session.start();
  const speech=f.speech({bargeIn:true});
  const task=f.utterance();
  await flush();
  await f.session.stop();
  assert.equal(signal.aborted,true);
  assert.equal(await speech,false);
  assert.equal(await task,false);
  interrupted.reject(new Error('Late interruption error.'));
  await flush();
  assert.equal(f.submissions.length,0);
  assert.deepEqual(f.errors,[]);
});

test('failed interruption drops that turn and capture can accept another utterance',async()=>{
  const f=fixture({interrupt:async()=>{throw new Error('Could not interrupt.');}});
  f.busy=true;
  await f.session.start();
  assert.equal(await f.speech(),false);
  assert.equal(await f.utterance(),false);
  assert.equal(f.submissions.length,0);
  assert.deepEqual(f.errors,['Could not interrupt.']);
  f.busy=false;
  await f.speech();
  assert.equal(await f.utterance(),true);
  assert.equal(f.capture.stops,0);
  await f.session.stop();
});

test('a reply becoming busy during transcription is interrupted before submission',async()=>{
  const transcription=gate(),interrupted=gate();
  const f=fixture({transcribe:()=>transcription.promise,interrupt:()=>interrupted.promise});
  await f.session.start();
  await f.speech();
  const task=f.utterance();
  await flush();
  f.busy=true;
  transcription.resolve('Speak next.');
  await flush();
  assert.equal(f.events.filter(value=>value==='interrupt').length,1);
  assert.equal(f.submissions.length,0);
  interrupted.resolve();
  assert.equal(await task,true);
  await f.session.stop();
});

test('a new reply during STT is interrupted even after speech-start interrupted an earlier reply',async()=>{
  const transcription=gate(),replacement=gate();
  let interruptions=0;
  const f=fixture({transcribe:()=>transcription.promise,interrupt:()=>{
    if(++interruptions===1){f.busy=false;return Promise.resolve();}
    return replacement.promise;
  }});
  f.busy=true;
  await f.session.start();
  await f.speech();
  assert.equal(interruptions,1);
  const task=f.utterance();
  await flush();
  f.busy=true;
  transcription.resolve('Interrupt the replacement too.');
  await flush();
  assert.equal(interruptions,2);
  assert.equal(f.submissions.length,0);
  f.busy=false;
  replacement.resolve();
  assert.equal(await task,true);
  assert.equal(f.submissions.length,1);
  await f.session.stop();
});

test('STT and submit failures release the slot, while failed Blob callbacks stay deduplicated',async()=>{
  for(const stage of ['transcribe','submit']){
    let fail=true;
    const f=fixture({[stage]:()=>{
      if(fail) throw new Error(`${stage} failed.`);
      return stage==='transcribe' ? 'Recovered.' : true;
    }});
    await f.session.start();
    const blob=clip();
    assert.equal(await f.utterance(blob),false);
    assert.deepEqual(f.errors,[`${stage} failed.`]);
    assert.equal(f.session.getState().status,'listening');
    fail=false;
    assert.equal(await f.utterance(blob),false);
    assert.equal(await f.utterance(),true);
    await f.session.stop();
  }
});

test('throwing or rejecting UI observers do not break submission, cleanup or restart',async()=>{
  for(const observer of ['onState','onTranscript']){
    for(const asynchronous of [false,true]){
      const f=fixture({[observer]:()=>{
        const error=new Error(`${observer} failed.`);
        if(asynchronous) return Promise.reject(error);
        throw error;
      },onError:()=>{throw new Error('Error observer failed.');}});
      await f.session.start();
      assert.equal(await f.utterance(),true);
      await f.session.stop();
      await f.session.start();
      assert.equal(await f.utterance(),true);
      await f.session.stop();
      await flush();
      assert.equal(f.session.getState().status,'idle');
      assert.equal(f.submissions.length,2);
      assert.ok(f.errors.includes(`${observer} failed.`));
    }
  }
});

test('capture errors stop the session and cannot automatically reopen the microphone',async()=>{
  const f=fixture();
  await f.session.start();
  f.capture.callbacks.onError(new Error('Microphone disconnected.'));
  assert.equal(f.session.getState().status,'error');
  assert.equal(f.session.getState().active,false);
  assert.equal(await f.utterance(),false);
  await flush();
  assert.equal(f.captures.length,1);
  assert.ok(f.capture.stops>0);
  assert.deepEqual(f.errors,['Microphone disconnected.']);
  assert.equal(await f.session.start(),true);
  assert.equal(f.captures.length,2);
  await f.session.stop();
});

test('startup rejection closes capture and remains stopped until an explicit start',async()=>{
  const f=fixture({open:async()=>{throw new Error('Microphone permission denied.');}});
  assert.equal(await f.session.start(),false);
  assert.equal(f.session.getState().active,false);
  assert.equal(f.session.getState().status,'error');
  assert.deepEqual(f.errors,['Microphone permission denied.']);
  assert.ok(f.capture.stops>0);
  await flush();
  assert.equal(f.captures.length,1);
});

test('stop during microphone startup settles promptly and late startup cannot restore listening',async()=>{
  const opening=gate();
  const f=fixture({open:()=>opening.promise});
  const started=f.session.start();
  const oldCapture=f.capture;
  await f.session.stop();
  assert.equal(await started,false);
  opening.resolve(true);
  await flush();
  oldCapture.callbacks.onState({status:'listening',active:true});
  assert.equal(f.session.getState().status,'idle');
  assert.equal(f.session.getState().active,false);
  assert.ok(oldCapture.stops>0);
  assert.equal(f.captures.length,1);
});

test('the capture signal cancels an utterance without ending the Talk session',async()=>{
  const transcription=gate();
  const f=fixture({transcribe:()=>transcription.promise});
  await f.session.start();
  const controller=new AbortController();
  const task=f.utterance(clip(),{signal:controller.signal});
  await flush();
  controller.abort();
  assert.equal(await task,false);
  assert.equal(f.transcriptions[0].meta.signal.aborted,true);
  assert.equal(f.session.getState().status,'listening');
  assert.equal(f.session.getState().active,true);
  transcription.resolve('Cancelled capture.');
  await flush();
  assert.equal(f.submissions.length,0);
  assert.equal(await f.utterance(clip(),{signal:controller.signal}),false);
  await f.session.stop();
});

test('a transcript observer stopping Talk prevents submission',async()=>{
  let session;
  const f=fixture({onTranscript:()=>session.stop()});
  session=f.session;
  await session.start();
  assert.equal(await f.utterance(),false);
  assert.equal(f.submissions.length,0);
  assert.equal(session.getState().status,'idle');
});

test('a capture error cannot overwrite a replacement started by a state observer',async()=>{
  let session,restart=false;
  const f=fixture({onState:value=>{
    if(value.status==='idle' && restart){restart=false;return session.start();}
  }});
  session=f.session;
  await session.start();
  restart=true;
  f.capture.callbacks.onError(new Error('Old capture failed.'));
  await flush();
  assert.equal(f.captures.length,2);
  assert.equal(session.getState().status,'listening');
  assert.equal(session.getState().active,true);
  assert.deepEqual(f.errors,[]);
  assert.equal(await f.utterance(),true);
  await session.stop();
});
