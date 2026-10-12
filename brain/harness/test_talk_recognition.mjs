import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const recognition=require('../ui/static/talk_recognition.js');
function fixture(value){
  let captureOptions,streamOptions,batchCalls=0,resolve;
  const delayed=new Promise(r=>resolve=r);
  const stream={start(){},push(){},end(){},cancel(){},stop(){},result:()=>value==='pending'?delayed:Promise.resolve(value)};
  const adapter=recognition.create({captureFactory:options=>{captureOptions=options;return {start(){},stop(){}};},
    streamFactory:options=>{streamOptions=options;return stream;},batchTranscribe:async()=>{batchCalls++;return 'batch answer';}});
  const capture=adapter.captureFactory({onUtterance:()=>{}});
  const controller=new AbortController(),meta={utteranceId:'capture-id',signal:controller.signal};
  const blob=new Blob(['audio']);captureOptions.onUtterance(blob,meta);
  return {adapter,capture,controller,meta,blob,resolve,streamOptions,get batchCalls(){return batchCalls;}};
}
let f=fixture({transcript:' live answer ',confidence:.9});
assert.equal(await f.adapter.transcribe(f.blob,f.meta),'live answer');assert.equal(f.batchCalls,0);
f=fixture(null);assert.equal(await f.adapter.transcribe(f.blob,f.meta),'batch answer');assert.equal(f.batchCalls,1);
f=fixture({transcript:'',confidence:1});assert.equal(await f.adapter.transcribe(f.blob,f.meta),'');assert.equal(f.batchCalls,0);
f=fixture({transcript:'uncertain',confidence:.2});assert.equal(await f.adapter.transcribe(f.blob,f.meta),'');assert.equal(f.batchCalls,0);
f=fixture('pending');let done=f.adapter.transcribe(f.blob,f.meta);f.controller.abort();f.resolve(null);assert.equal(await done,'');assert.equal(f.batchCalls,0);
f=fixture(null);f.streamOptions.onStatus({status:'cancelled',utteranceId:f.meta.utteranceId});assert.equal(await f.adapter.transcribe(f.blob,f.meta),'');assert.equal(f.batchCalls,0);
f=fixture('pending');done=f.adapter.transcribe(f.blob,f.meta);f.capture.stop();f.resolve(null);assert.equal(await done,'');assert.equal(f.batchCalls,0);
console.log('PASS: 7 recognition adapter checks; live results avoid batch, failures fall back once, cancellation never falls back.');
