'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),vm=require('node:vm'),crypto=require('node:crypto');
const here=__dirname,source=fs.readFileSync(path.join(here,'runtime.js'),'utf8');
const manifest=JSON.parse(fs.readFileSync(path.join(here,'manifest.json'),'utf8'));
const report={passed:false,runtimeSha256:crypto.createHash('sha256').update(source).digest('hex'),checks:[],failures:[]};
function fixture(){
  const deferred=[],errors=[];let destroyed=0,updates=0,hook=null;
  const sandbox={module:{exports:{}},URL,performance:{now:()=>0},location:{href:'http://localhost/preview/'},Image:class{constructor(){this.naturalWidth=this.naturalHeight=256;}decode(){return new Promise((resolve,reject)=>deferred.push({resolve,reject,image:this}));}}};
  vm.runInNewContext(source,sandbox);
  const data={faces:[{id:'test',slots:{eye_L:{part:'circle'},eye_R:{part:'circle'},mouth:{y:46}}}]};
  const drawnRuntime={create(_container,options){hook=options.eyeLayer;return {expression:'test',ready:Promise.resolve(true),loaded:true,update(){updates++;return {drawnReady:true,drawnAnimation:{time:0}};},snapshot(){return {drawnReady:true,renderer:'drawn'};},destroy(){destroyed++;}};}};
  const api=sandbox.module.exports.create(null,{data,drawnRuntime,manifest,autoStart:false,now:()=>0,onError:error=>errors.push(error.message)});
  return {api,deferred,errors,stats:()=>({destroyed,updates,eyeReady:hook.ready}),sandbox,data,drawnRuntime};
}
async function test(name,fn){try{await fn();report.checks.push(name);}catch(error){report.failures.push({name,error:error.message});}}
(async()=>{
  await test('Destroy during frame loading cannot revive the overlay or emit a stale failure',async()=>{
    const f=fixture();assert.equal(f.deferred.length,108);assert(f.deferred.every(item=>!item.image.src.includes('/eye_')));f.api.destroy();for(const pending of f.deferred)pending.resolve();
    assert.equal(await f.api.ready,false);assert.equal(f.stats().eyeReady,false);assert.equal(f.stats().updates,0);assert.equal(f.stats().destroyed,1);
    assert.equal(f.errors.length,0,'Destroyed instances must not report a loading failure');
  });
  await test('A failed frame leaves the old renderer active and allows a later retry',async()=>{
    const f=fixture();f.deferred[0].reject(new Error('one frame failed'));for(const pending of f.deferred.slice(1))pending.resolve();
    assert.equal(await f.api.ready,false);assert.equal(f.stats().eyeReady,false);assert.equal(f.errors.length,1);assert.equal(f.api.snapshot().renderer,'drawn');
    const retry=f.sandbox.module.exports.create(null,{data:f.data,drawnRuntime:f.drawnRuntime,manifest,autoStart:false,now:()=>0});
    assert.equal(f.deferred.length,109,'Only the rejected image should be fetched again');f.deferred[108].resolve();assert.equal(await retry.ready,true);retry.destroy();f.api.destroy();
  });
  await test('Incomplete frame dimensions fail cleanly without using the overlay',async()=>{
    const f=fixture();f.deferred[0].image.naturalWidth=128;for(const pending of f.deferred)pending.resolve();
    assert.equal(await f.api.ready,false);assert.equal(f.stats().eyeReady,false);assert.match(f.errors[0],/Unregistered/);f.api.destroy();
  });
  report.passed=report.failures.length===0;fs.writeFileSync(path.join(here,'qa_async_report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(!report.passed)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
