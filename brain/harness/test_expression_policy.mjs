import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const policySource = await readFile(new URL('../duplex/static/expression_policy.js', import.meta.url), 'utf8');
const deliverySource = await readFile(new URL('../duplex/static/delivery.js', import.meta.url), 'utf8');
const load = source => import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const {ExpressionPolicy, normalizeExpression, EXPRESSION_LIMITS} = await load(policySource);
const {replyExpression} = await load(deliverySource);
const map = JSON.parse(await readFile(new URL('../duplex/face_map.json', import.meta.url), 'utf8'));
const dataSource = await readFile(new URL('../face_assets/app/app_data.js', import.meta.url), 'utf8');
const data = JSON.parse(dataSource.replace(/^window\.MIST_DATA = /, '').trim().replace(/;$/, ''));
const sourceIds = new Set(data.faces.map(face => face.id));
const reached = new Set(), report = {passed:false, scenarios:[], limits:[]};
let assertions = 0;
const eq = (actual, expected, message) => {assertions++; assert.deepEqual(actual, expected, message);};
function setup(options={}) {
  let time = 0;
  const policy = new ExpressionPolicy(map, {...options,now:() => time});
  return {policy, at(value) {time=value; return policy.snapshot();}, get time() {return time;}};
}
function scenario(name, run) {run(); report.scenarios.push(name);}

scenario('Every source face is reachable through a named preset and a valid variant', () => {
  for (const [expression,preset] of Object.entries(map.expressions)) {
    const all = [preset.primary,...preset.alts];
    for (const [variant,id] of all.entries()) {
      const f = setup();
      eq(f.policy.request({expression,variant}).status,'applied');
      eq(f.policy.snapshot().faceId,id);
      eq(sourceIds.has(id),true);
      reached.add(id);
    }
  }
  eq([...reached].sort(),[...sourceIds].sort());
  eq(Object.keys(map.faces).sort(),[...sourceIds].sort());
});

scenario('All 1560 directed face changes preserve the chosen face and reject no valid call', () => {
  const representatives = Object.entries(map.faces).map(([id,face]) => [id,face.calls[0]]);
  for (const [fromId,from] of representatives) for (const [toId,to] of representatives) {
    if (fromId === toId) continue;
    const f = setup();
    f.policy.request(from);
    eq(f.policy.snapshot().faceId,fromId);
    f.at(EXPRESSION_LIMITS.cooldownMs);
    eq(f.policy.request(to).status,'applied');
    eq(f.policy.snapshot().faceId,toId);
  }
});

scenario('A compliment holds its expression through thinking, speech and listening', () => {
  const f = setup();
  f.policy.request({expression:'happy',duration_ms:2800});
  for (const state of ['thinking','checking','speaking','listening']) {
    const shot = f.policy.setState(state);
    eq(shot.expression,'happy');
    eq(shot.mouthMode,state === 'speaking' ? 'audio' : 'rest');
  }
  eq(f.at(2800).expression,'neutral');
});

scenario('Quiet listening uses the calm resting face without displacing persistent affect', () => {
  const f=setup();
  const quiet=f.policy.setState('listening');
  eq(quiet.expression,'neutral');
  eq(quiet.faceId,map.expressions.neutral.primary);
  eq(quiet.mouthMode,'rest');
  f.policy.request({expression:'curious',persistent:true});
  eq(f.policy.setState('thinking').expression,'curious');
  eq(f.policy.setState('listening').expression,'curious');
  eq(f.policy.snapshot().mouthMode,'rest');
  eq(f.policy.setState('speaking').mouthMode,'audio');
  eq(f.policy.setState('listening').faceId,map.expressions.curious.primary);
});

scenario('Question and uncertainty use restrained cues; apology and distress stay neutral', () => {
  const cases = [
    ['Good question. I will check.','curious'],["I'm not sure yet.",'uncertain'],
    ["I don't have enough information to tell.",'uncertain'],["I can't tell from that reading.",'uncertain'],
    ["That's wonderful. You did it.",'happy'],['Nice work. It fits.','happy'],
    ["I'm sorry, I read that wrong.",'neutral'],['Fair correction. Printed, not walking.','neutral'],
    ['That sounds hard. We can sit here.','neutral'],['No rush.','neutral'],
    ['She said "That worked" yesterday.','neutral'],['That did not work.','neutral'],
    ['The happy preset has three variants.','neutral'],['Do not act angry.','neutral'],
    [null,'neutral'],[42,'neutral'],['','neutral'],
  ];
  for (const [text,expected] of cases) eq(replyExpression(text),expected,text);
});

scenario('Tool waiting never replaces an explicit face or starts a speaking mouth', () => {
  const f = setup();
  f.policy.request({expression:'curious'});
  const waiting = f.policy.setState('checking');
  eq(waiting.expression,'curious');
  eq(waiting.mouthMode,'rest');
  eq(waiting.gaze,[-0.35,-0.2]);
  eq(f.policy.setState('speaking').gaze,null);
  eq(f.policy.snapshot().expression,'curious');
});

scenario('Mouthless faces 12 and 35 use a related speaking variant and restore when quiet', () => {
  for (const id of ['12_happy_09_manual','35_sad_10_manual']) {
    const f=setup(), command=map.faces[id].calls[0];
    f.policy.request({...command,duration_ms:5000});
    eq(f.policy.snapshot().faceId,id);
    const speaking=f.policy.setState('speaking');
    eq(speaking.requestedFaceId,id);
    eq(speaking.speechFallback,true);
    eq(Boolean(map.faces[speaking.faceId].parts.mouth),true);
    eq(speaking.expression,command.expression);
    eq(f.policy.setState('listening').faceId,id);
    f.at(5000);
    eq(f.policy.snapshot().expression,'neutral');
  }
});

scenario('Barge-in retains the persistent face, cancels queued reactions and refuses late old-turn cues', () => {
  const f = setup();
  f.policy.request({expression:'happy'});
  f.at(100);
  f.policy.request({expression:'smug'});
  const oldGeneration = f.policy.generation;
  f.policy.setState('speaking');
  const interrupted = f.policy.interrupt();
  eq(interrupted.expression,'happy');
  eq(interrupted.mouthMode,'rest');
  eq(interrupted.queued,null);
  eq(f.policy.request({expression:'angry'},{generation:oldGeneration}).reason,'stale_generation');
  eq(f.at(1000).expression,'happy');
  eq(f.policy.request({expression:'neutral'}).status,'applied');
});

scenario('A hundred identical calls do not restart a transition or extend its hold', () => {
  const f = setup();
  f.policy.request({expression:'happy',duration_ms:1800});
  for (let t=1;t<=1000;t+=10) {
    f.at(t);
    eq(f.policy.request({expression:'happy',duration_ms:6000}).status,'unchanged');
  }
  eq(f.policy.counters.applied,1);
  eq(f.at(1800).expression,'neutral');
});

scenario('Rapid conflicting calls coalesce to the latest choice at the cooldown boundary', () => {
  const f = setup();
  f.policy.request({expression:'happy'});
  for (const [at,expression] of [[50,'sad'],[100,'proud'],[200,'uncertain'],[300,'curious']]) {
    f.at(at); eq(f.policy.request({expression}).status,'queued');
    eq(f.policy.snapshot().expression,'happy');
  }
  eq(f.at(449).expression,'happy');
  eq(f.at(450).expression,'curious');
  eq(f.policy.counters.applied,2);
});

scenario('Changing back to the current face cancels an older queued change', () => {
  const f = setup();
  f.policy.request({expression:'happy'});
  f.at(100); f.policy.request({expression:'sad'});
  f.at(200); f.policy.request({expression:'happy'});
  eq(f.at(450).expression,'happy');
  eq(f.policy.snapshot().queued,null);
});

scenario('Automatic wording cues cannot replace a deliberate model or manual expression', () => {
  const f = setup();
  f.policy.request({expression:'uncertain'});
  f.at(500);
  eq(f.policy.request({expression:'happy'},{source:'automatic'}).reason,'explicit_expression_active');
  eq(f.policy.snapshot().expression,'uncertain');
  eq(f.policy.request({expression:'angry'},{source:'manual'}).status,'applied');
  eq(f.policy.snapshot().expression,'angry');
  f.policy.reset();
  f.policy.request({expression:'happy'},{source:'automatic'});
  f.policy.request({expression:'happy'},{source:'model'});
  eq(f.policy.snapshot().source,'model');
});

scenario('Hidden-tab delays discard obsolete queued changes', () => {
  const f = setup();
  f.policy.request({expression:'happy',duration_ms:600});
  f.at(100); f.policy.request({expression:'panic',duration_ms:500});
  eq(f.at(2000).expression,'neutral');
  eq(f.policy.snapshot().queued,null);
});

scenario('A hold starts after application and entrance; cooldown waiting does not consume it', () => {
  const f=setup({transitionMs:600});
  f.policy.request({expression:'happy',duration_ms:400});
  eq(f.policy.snapshot().appliedAt,0);
  eq(f.policy.snapshot().holdStartsAt,600);
  eq(f.policy.snapshot().expiresAt,1000);
  eq(f.at(999).expression,'happy');
  eq(f.at(1000).expression,'neutral');
  f.policy.reset();f.at(2000);
  f.policy.request({expression:'happy'});
  f.at(2100);eq(f.policy.request({expression:'curious',duration_ms:400}).status,'queued');
  eq(f.at(2450).expression,'curious');
  eq(f.policy.snapshot().appliedAt,2450);
  eq(f.policy.snapshot().holdStartsAt,3050);
  eq(f.policy.snapshot().expiresAt,3450);
  eq(f.at(3449).expression,'curious');
  eq(f.at(3450).expression,'happy');
});

scenario('Entrance allowance does not extend duplicate calls and interruption still clears immediately', () => {
  const f=setup({transitionMs:600});
  f.policy.request({expression:'happy',duration_ms:400});
  for(const at of [50,300,600,900]){
    f.at(at);eq(f.policy.request({expression:'happy',duration_ms:6000}).status,'unchanged');
    eq(f.policy.snapshot().expiresAt,1000);
  }
  eq(f.at(1000).expression,'neutral');
  f.policy.request({expression:'curious',duration_ms:400});
  f.at(1100);const shot=f.policy.interrupt();
  eq(shot.expression,'neutral');eq(shot.expiresAt,null);eq(shot.holdStartsAt,null);
  for(const duration of [-1,Infinity,NaN,'600',true,1601]){
    assertions++;assert.throws(()=>setup({transitionMs:duration}),/transition duration/);
  }
  const immediate=setup({transitionMs:0});
  immediate.policy.request({expression:'happy',duration_ms:400});
  eq(immediate.policy.snapshot().holdStartsAt,0);
  eq(immediate.at(400).expression,'neutral');
});

scenario('Durations are finite, invalid payloads are refused, and the face remains unchanged', () => {
  const f = setup();
  f.policy.request({expression:'curious'});
  const invalid = [null,[],{},'happy',{expression:'__proto__'},{expression:4},
    {expression:'happy',variant:-1},{expression:'happy',variant:30},{expression:'happy',variant:0.5},
    {expression:'happy',variant:true},{expression:'happy',variant:null},{expression:'happy',variant:'1'},
    {expression:'happy',duration_ms:Infinity},{expression:'happy',duration_ms:NaN},
    {expression:'happy',duration_ms:null},{expression:'happy',duration_ms:1.2},
    {expression:'happy',duration_ms:'1000'},{expression:'happy',duration_ms:true},
    {expression:'happy',face_id:'something_else'},{expression:'happy',speech:'say this'},
  ];
  for (const command of invalid) {
    eq(f.policy.request(command).status,'refused');
    eq(f.policy.snapshot().expression,'curious');
  }
  eq(normalizeExpression(map,{expression:'happy',duration_ms:-500}).duration_ms,400);
  eq(normalizeExpression(map,{expression:'happy',duration_ms:1e9}).duration_ms,6000);
  eq(f.policy.setState('do_robot_motion').status,'refused');
  eq(f.policy.request({expression:'happy'},{source:'untrusted'}).status,'ignored');
});

scenario('10,000 deterministic mixed events keep valid faces, finite holds and interruption boundaries', () => {
  const f = setup();
  const names = Object.keys(map.expressions);
  let seed = 314159265;
  const rand = () => (seed=(1664525*seed+1013904223)>>>0)/4294967296;
  let time = 0;
  for (let i=0;i<10000;i++) {
    time+=Math.floor(rand()*240);f.at(time);
    const kind=Math.floor(rand()*6);
    if (kind<3) f.policy.request({expression:names[Math.floor(rand()*names.length)]});
    else if (kind===3) f.policy.setState(['listening','thinking','checking','speaking'][Math.floor(rand()*4)]);
    else if (kind===4) {const shot=f.policy.interrupt();eq(shot.state,'listening');eq(shot.queued,null);}
    else f.policy.request({expression:'invalid'});
    const shot=f.policy.snapshot();
    eq(sourceIds.has(shot.faceId),true);
    eq(shot.expiresAt===null || (Number.isFinite(shot.expiresAt) && shot.expiresAt<=time+6000),true);
    eq(shot.mouthMode==='audio',shot.state==='speaking');
  }
});

report.passed=true;
report.checkedAt=new Date().toISOString();
report.assertions=assertions;
report.sourceSha256=createHash('sha256').update(policySource).digest('hex');
report.faceCount=sourceIds.size;
report.presetCount=Object.keys(map.expressions).length;
report.directedFaceChanges=1560;
report.fuzzEvents=10000;
report.limits=[
  'These checks validate expression selection, state precedence and timing policy. They do not judge rendered animation quality.',
  'Conversation cases are deterministic text and tool traces. No live smaller model, microphone or paid voice provider was used.',
  'State speaking must be supplied from actual audible playback; model text arrival must not start it.',
];
await writeFile(new URL('../duplex/expression_policy_checks.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(`PASS: ${assertions} assertions, ${report.scenarios.length} scenarios, all ${sourceIds.size} faces, ${report.directedFaceChanges} directed choices and ${report.fuzzEvents} mixed events.`);
