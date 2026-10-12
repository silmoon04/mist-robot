import test from 'node:test';
import assert from 'node:assert/strict';
import {SceneTransport,segmentsFor,locate} from './transport.mjs';
const scene={audio:{startMs:2000,packetGaps:[{atClipMs:1100,durationMs:900}]}};
class Context {
  currentTime=0; state='running'; destination={}; created=[];
  async resume(){this.state='running';}
  createBufferSource(){const node={connect(){},disconnect(){this.disconnected=true;},start(...args){this.args=args;},stop(){this.stopped=true;}};this.created.push(node);return node;}
  close(){this.state='closed';}
}
test('Inserted delivery gap preserves every clip sample and freezes audible position',()=>{
  const segments=segmentsFor(scene.audio,3);
  assert.deepEqual(segments,[{scene:2,clip:0,duration:1.1},{scene:4,clip:1.1,duration:1.9}]);
  assert.deepEqual(locate(segments,3.5,3),{position:1.1,active:false,reason:'packet-gap'});
  assert(Math.abs(locate(segments,4,3).position-1.1)<1e-9);
  assert.equal(locate(segments,6,3).position,3);
});
test('Native sources scheduled on the same scene clock, pause releases all nodes',async()=>{
  const context=new Context(),t=new SceneTransport(context);t.configure(scene,{duration:3});await t.play();
  assert.deepEqual(context.created.map(x=>x.args),[[2,0,1.1],[4,1.1,1.9]]);
  context.currentTime=2.5;assert.equal(t.sample().position,.5);t.pause();
  assert.equal(t.nodes.size,0);assert(context.created.every(n=>n.stopped&&n.disconnected));
  context.currentTime=9;assert.equal(t.time(),2.5);assert.equal(t.sample().active,false);
  await t.play();assert.deepEqual(context.created.at(-2).args,[9,.5,.6000000000000001]);
  assert.equal(context.created.at(-1).args[0],10.5);
});
test('Pause in delivery gap resumes remaining wait without skipping words',async()=>{
  const c=new Context(),t=new SceneTransport(c);t.configure(scene,{duration:3});await t.play();c.currentTime=3.5;t.pause();c.currentTime=10;await t.play();
  assert.deepEqual(c.created.at(-1).args,[10.5,1.1,1.9]);assert.equal(t.sample().active,false);
});
test('Interruption freezes clip position, stops nodes, and cannot resume old speech',async()=>{
  const c=new Context(),t=new SceneTransport(c);t.configure(scene,{duration:3});await t.play();c.currentTime=2.7;t.interrupt();
  assert.equal(t.nodes.size,0);const position=t.sample().position;c.currentTime=5;assert.equal(t.sample().position,position);assert.equal(t.sample().active,false);
  t.pause();const count=c.created.length;await t.play();assert.equal(c.created.length,count);t.reset();assert.equal(t.time(),0);assert.equal(t.interrupted,false);
});
test('Reset while resume promise is pending blocks stale source scheduling',async()=>{
  const c=new Context(),t=new SceneTransport(c);let resolve;c.resume=()=>new Promise(r=>resolve=r);t.configure(scene,{duration:3});const start=t.play();t.reset();resolve();await start;assert.equal(t.running,false);assert.equal(c.created.length,0);
});
test('Replay and scene change retire every prior source; teardown closes context',async()=>{
  const c=new Context(),t=new SceneTransport(c);t.configure(scene,{duration:3});await t.play();const old=[...c.created];t.configure({audio:{startMs:0,packetGaps:[]}},{duration:1});assert(old.every(n=>n.stopped));await t.play();assert.equal(t.nodes.size,1);t.destroy();assert.equal(t.nodes.size,0);assert.equal(t.running,false);assert.equal(c.state,'closed');
});
test('Suspended audio cannot return an active speech sample',async()=>{
  const c=new Context(),t=new SceneTransport(c);t.configure(scene,{duration:3});await t.play();c.currentTime=2.7;c.state='suspended';assert.equal(t.sample().active,false);assert.equal(t.sample().reason,'suspended-clock');
});
for(const action of ['pause','interrupt','reset','destroy'])test(`${action} cancels a pending play before it creates a source`,async()=>{
  const c=new Context(),t=new SceneTransport(c);let resolve;
  c.resume=()=>new Promise(r=>resolve=r);t.configure(scene,{duration:3});const pending=t.play();
  assert.equal(t.pending,true);t[action]();assert.equal(t.pending,false);resolve();
  assert.equal(await pending,false);assert.equal(t.running,false);assert.equal(t.nodes.size,0);assert.equal(c.created.length,0);
});
test('An obsolete resume rejection cannot fail a replacement scene',async()=>{
  const c=new Context(),t=new SceneTransport(c);let reject;
  c.resume=()=>new Promise((_,r)=>reject=r);t.configure(scene,{duration:3});const pending=t.play();t.reset();reject(new Error('old resume failed'));
  assert.equal(await pending,false);assert.equal(t.pending,false);assert.equal(c.created.length,0);
});
test('Resume must actually run the context before sources are scheduled',async()=>{
  const c=new Context(),t=new SceneTransport(c);c.state='suspended';c.resume=async()=>{};t.configure(scene,{duration:3});
  assert.equal(await t.play(),false);assert.equal(t.running,false);assert.equal(t.pending,false);assert.equal(c.created.length,0);assert.equal(t.sample().active,false);
});
test('Output timestamp fallback and regression cannot rewind scene time',async()=>{
  const c=new Context(),t=new SceneTransport(c);let output=0;c.getOutputTimestamp=()=>({contextTime:output});t.configure(scene,{duration:3});await t.play();
  c.currentTime=2.7;assert.equal(t.time(),2.7);output=2.5;assert.equal(t.time(),2.7);output=2.9;c.currentTime=3;assert.equal(t.time(),2.9);
  c.getOutputTimestamp=()=>{throw new Error('unavailable');};assert.equal(t.time(),3);t.reset();assert.equal(t.time(),0);
});
