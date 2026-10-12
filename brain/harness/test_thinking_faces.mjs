import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const policySource=await readFile(new URL('../duplex/static/expression_policy.js',import.meta.url),'utf8');
const {ExpressionPolicy,THINKING_FACE_TIMING}=await import('data:text/javascript;base64,'+Buffer.from(policySource).toString('base64'));
const map=JSON.parse(await readFile(new URL('../duplex/face_map.json',import.meta.url),'utf8'));
const sourceIds=new Set(Object.keys(map.faces));
let assertions=0,scenarios=0;
const eq=(actual,expected,message)=>{assertions++;assert.deepEqual(actual,expected,message);};
function setup(options={}) {
  let time=0;
  const policy=new ExpressionPolicy(map,{...options,now:()=>time});
  return {policy,at(value){time=value;return policy.snapshot();},get time(){return time;}};
}
function scenario(_name,run){run();scenarios++;}

scenario('Sustained thinking cycles three original faces with full holds and no adjacent repeat', () => {
  const f=setup({transitionMs:600}), expected=['20_neutral_06_manual','40_neutral_03_manual','39_neutral_02_manual'];
  const firstAt=THINKING_FACE_TIMING.delayMs, interval=600+THINKING_FACE_TIMING.holdMs;
  f.policy.setState('thinking');
  eq(f.at(firstAt-1).faceId,map.expressions.neutral.primary,'brief waits keep the ordinary face');
  for(let i=0;i<9;i++) {
    const at=firstAt+i*interval, shot=f.at(at);
    eq(shot.faceId,expected[i%3]);
    eq(sourceIds.has(shot.faceId),true);
    eq(shot.source,'state');eq(shot.expiresAt,null);eq(shot.mouthMode,'rest');
    eq(f.policy.setState(i%2?'thinking':'checking').faceId,shot.faceId,'thinking/checking events share one wait');
    eq(f.at(at+interval-1).faceId,shot.faceId,'the hold includes the face entrance');
  }
  const resumed=f.at(60000).faceId;
  eq(resumed,expected[0],'a hidden-tab gap advances once instead of replaying missed changes');
  eq(f.at(60001).faceId,resumed);
});

scenario('Separate thinking turns continue the face rotation after speech and interruptions', () => {
  const f=setup(), selected=[];
  for(let i=0;i<9;i++) {
    f.at(i*1000);f.policy.setState('thinking');
    selected.push(f.at(i*1000+THINKING_FACE_TIMING.delayMs).faceId);
    const idle=i%2?f.policy.interrupt():f.policy.setState('speaking');
    eq(idle.gaze,null);eq(idle.source,'state');
    eq(idle.faceId,i%2?map.expressions.listening.primary:map.expressions.neutral.primary);
  }
  eq(new Set(selected).size,3);
  eq(selected.every((id,i)=>i===0||id!==selected[i-1]),true);
  for(const id of new Set(selected))eq(selected.filter(value=>value===id).length,3,'each face has an equal share of turns');
  f.policy.setState('available');
  f.policy.setState('thinking');f.at(f.time+THINKING_FACE_TIMING.delayMs-1);
  eq(f.policy.snapshot().faceId,map.expressions.neutral.primary,'a new short wait never inherits the previous thinking pose');
});

scenario('Thinking rotation waits for model, manual and system expression holds', () => {
  for(const source of ['model','manual','system']) {
    const f=setup({transitionMs:600});
    f.policy.request({expression:'thinking',duration_ms:6000},{source});
    f.policy.setState('thinking');
    for(const at of [650,4200,6599]) {
      const shot=f.at(at);
      eq(shot.faceId,map.expressions.thinking.primary);eq(shot.source,source);
    }
    eq(f.at(6600).faceId,'20_neutral_06_manual','default variation begins only after the requested hold');
    eq(f.policy.snapshot().source,'state');
    f.policy.request({expression:'happy',duration_ms:6000},{source});
    eq(f.at(11000).faceId,map.expressions.happy.primary,'a new deliberate face can interrupt the rotation');
    eq(f.policy.setState('speaking').expression,'happy');
    eq(f.policy.snapshot().mouthMode,'audio');
  }
});

scenario('An automatic reply cue cannot pin the default thinking face', () => {
  const f=setup();
  f.policy.request({expression:'happy',duration_ms:6000},{source:'automatic'});
  f.policy.setState('thinking');
  eq(f.at(THINKING_FACE_TIMING.delayMs-1).faceId,map.expressions.happy.primary);
  const shot=f.at(THINKING_FACE_TIMING.delayMs);
  eq(shot.faceId,'20_neutral_06_manual');eq(shot.source,'state');eq(shot.expiresAt,null);
  eq(f.at(THINKING_FACE_TIMING.delayMs+THINKING_FACE_TIMING.holdMs).faceId,'40_neutral_03_manual');
  const speaking=f.policy.setState('speaking');
  eq(speaking.faceId,map.expressions.happy.primary);eq(speaking.source,'automatic');
  eq(speaking.mouthMode,'audio');eq(speaking.gaze,null);
});

console.log(`PASS: ${assertions} assertions, ${scenarios} thinking-face scenarios.`);
