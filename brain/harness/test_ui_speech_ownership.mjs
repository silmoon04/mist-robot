import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const htmlArgument = process.argv.indexOf('--html');
const htmlPath = htmlArgument < 0
  ? new URL('../ui/static/index.html', import.meta.url)
  : process.argv[htmlArgument + 1];
assert.ok(htmlPath, '--html requires a file path');
const html = fs.readFileSync(htmlPath, 'utf8');
const scripts = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]
  .filter(([, attributes]) => !/\bsrc\s*=/.test(attributes))
  .map(([, , source]) => source);
assert.equal(scripts.length, 1, 'Exercise the complete console inline script');

class Element {
  constructor(tagName = 'div') {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.style = {};
    this.dataset = {};
    this.listeners = new Map();
    this.className = '';
    this.value = '';
    this.scrollTop = 0;
    this.clientHeight = 500;
    this._text = '';
    this._html = '';
    this.classList = {
      add: (...names) => { this.className = [...new Set([...this.classes(), ...names])].join(' '); },
      remove: (...names) => { this.className = this.classes().filter(name => !names.includes(name)).join(' '); },
      contains: name => this.classes().includes(name),
    };
  }
  classes() { return this.className.split(/\s+/).filter(Boolean); }
  get options() { return this.descendants().filter(child => child.tagName === 'OPTION'); }
  get scrollHeight() { return this.children.length * 30; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  set textContent(value) { this._text = String(value ?? ''); this._html = ''; this.children = []; }
  get innerHTML() {
    return this._html || this.textContent.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  }
  set innerHTML(value) { this._html = String(value); this._text = ''; this.children = []; }
  appendChild(child) { this.children.push(child); child.parentNode = this; return child; }
  append(...children) {
    for (const child of children) {
      if (typeof child === 'string') { const text = new Element(); text.textContent = child; this.appendChild(text); }
      else this.appendChild(child);
    }
  }
  replaceChildren(...children) { this.children = []; this._text = ''; this._html = ''; this.append(...children); }
  descendants() { return this.children.flatMap(child => [child, ...child.descendants()]); }
  addEventListener(name, callback) { this.listeners.set(name, callback); }
  removeAttribute(name) { delete this[name]; }
  setAttribute(name, value) { this[name] = String(value); }
  focus() {}
}

const flush = () => new Promise(resolve => setImmediate(resolve));
const config = {
  type: 'hello', mode: 'chat', backend: 'fixture', model: 'offline', busy: false,
  soul: 'mist-v2', face_map: {}, jobs: [], jobs_available: true,
  voices: [], personas: [], deepgram_available: false,
  speech: {elevenlabs_available: true, elevenlabs_voice_label: 'fixture'},
};

async function createTab() {
  const elements = new Map();
  for (const [, tag, attributes, id] of html.matchAll(/<([a-z][\w-]*)\b([^>]*\bid="([^"]+)"[^>]*)>/gi)) {
    const element = new Element(tag);
    element.id = id;
    element.hidden = /\bhidden\b/.test(attributes);
    element.checked = /\bchecked\b/.test(attributes);
    element.value = attributes.match(/\bvalue="([^"]*)"/)?.[1] ?? '';
    elements.set(id, element);
  }
  for (const [, attributes, content] of html.matchAll(/<select\b([^>]*)>([\s\S]*?)<\/select>/gi)) {
    const select = elements.get(attributes.match(/\bid="([^"]+)"/)?.[1]);
    if (!select) continue;
    for (const [, optionAttributes, label] of content.matchAll(/<option\b([^>]*)>([\s\S]*?)<\/option>/gi)) {
      const option = new Element('option');
      option.value = optionAttributes.match(/\bvalue="([^"]*)"/)?.[1] ?? label;
      option.textContent = label;
      select.appendChild(option);
      if (select.options.length === 1 || /\bselected\b/.test(optionAttributes)) select.value = option.value;
    }
  }
  const body = new Element('body');
  const document = {
    body,
    getElementById(id) { assert.ok(elements.has(id), `Unknown DOM id: ${id}`); return elements.get(id); },
    createElement: tag => new Element(tag),
  };
  const sayRequests = [], speechCalls = [], eventSources = [], fetchCalls = [];
  let talkOptions=null;
  const audio = new Element('audio');
  const face = {setExpression() {}, setGaze() {}, clearGaze() {}, stopSpeech() {}};
  const player = {
    audio, stop() {}, applyRate() {},
    play(reply, options) { speechCalls.push({reply, options}); return Promise.resolve(); },
    resume() { throw new Error('The ownership fixture must use the reply playback path'); },
  };
  const context = {
    console, document, URL, Blob, AbortController, navigator: {},
    setTimeout, clearTimeout,
    localStorage: {getItem() { return null; }, setItem() {}},
    MistFaceRuntime: {create: () => face},
    MistSpeechPlayer: {create: () => player},
    MistTalkCapture: {create: () => ({start:async()=>true,stop:async()=>{}})},
    MistTalkRecognition: {create: options=>({captureFactory:options.captureFactory,transcribe:options.batchTranscribe})},
    MistTalkSession: {create: options=>{talkOptions=options;let active=false;return {
      start:async()=>{active=true;options.onState({status:'listening',active});return true;},
      stop:async()=>{active=false;options.onState({status:'idle',active});},
      getState:()=>({status:active?'listening':'idle',active})};}},
    EventSource: class {
      constructor(url) { assert.equal(url, '/api/events'); eventSources.push(this); }
    },
    fetch(url, options) {
      fetchCalls.push({url, options});
      if (url === '/api/config') return Promise.resolve({ok: true, json: async () => config});
      if (url === '/api/say') return new Promise((resolve, reject) => sayRequests.push({options, resolve, reject}));
      if (url === '/api/interrupt') return Promise.resolve({ok:true,status:200});
      throw new Error(`Unexpected network request in offline regression: ${url}`);
    },
  };
  context.window = context;
  vm.createContext(context);
  vm.runInContext(scripts[0], context, {filename: String(htmlPath)});
  await flush();
  assert.equal(eventSources.length, 1, 'The real console boot must connect its event stream');
  assert.equal(elements.get('ttsMode').value, 'elevenlabs', 'Fixture must enable provider speech');
  context.handle({...config});
  return {
    elements, speechCalls, sayRequests, fetchCalls,
    getTalkOptions:()=>talkOptions,
    event(event) { context.handle(event); },
    async send(text, status = 202, echoFirst = false) {
      elements.get('input').value = text;
      elements.get('send').onclick();
      const request = sayRequests.at(-1);
      assert.equal(JSON.parse(request.options.body).text, text, 'Send the text through the actual button handler');
      if (echoFirst) context.handle({type: 'chat_user', text});
      request.resolve({ok: status >= 200 && status < 300, status});
      await flush();
      if (!echoFirst) context.handle({type: 'chat_user', text});
      return request;
    },
    finish(reply = 'Fixture reply.', extra = {}) { context.handle({type: 'turn_end', reply, ...extra}); },
    reconnect(busy = false) {
      const source = eventSources[0];
      source.onerror();
      source.onopen();
      source.onmessage({data: JSON.stringify({...config, busy})});
      assert.equal(elements.get('connTxt').textContent, 'live');
    },
    buttons(label) { return elements.get('log').descendants().filter(element => element.tagName === 'BUTTON' && element.textContent === label); },
  };
}

test('fresh tab displays a completion without automatically requesting speech', async () => {
  const tab = await createTab();
  tab.finish('A reply initiated in another tab.');
  assert.match(tab.elements.get('log').textContent, /A reply initiated in another tab\./);
  assert.equal(tab.speechCalls.length, 0, 'A spectator turn_end must not synthesize speech');
});

test('restored history and reconnect snapshots render once without speech', async () => {
  const tab=await createTab();
  const history=[{role:'user',text:'Earlier question'},{role:'assistant',text:'Earlier answer'}];
  tab.event({...config,history});
  const initial=tab.elements.get('log').children.length;
  tab.event({...config,history});
  assert.equal(tab.elements.get('log').children.length,initial);
  assert.match(tab.elements.get('log').textContent,/Earlier answer/);
  assert.equal(tab.speechCalls.length,0);
});

test('a foreign request id cannot consume or speak an owned reply', async () => {
  const tab=await createTab();
  const request=await tab.send('Local with identity');
  const id=JSON.parse(request.options.body).request_id;
  tab.finish('Foreign replay',{request_id:'other-request'});
  assert.equal(tab.speechCalls.length,0);
  tab.finish('Local completion',{request_id:id});
  assert.equal(tab.speechCalls.length,1);
});

test('a correlated completion can confirm acceptance before the HTTP acknowledgement', async () => {
  const tab=await createTab();
  tab.elements.get('input').value='Immediate correlated reply';
  tab.elements.get('send').onclick();
  const request=tab.sayRequests.at(-1);
  const body=JSON.parse(request.options.body);
  tab.event({type:'chat_user',text:body.text,request_id:body.request_id});
  tab.finish('Immediate answer',{request_id:body.request_id});
  assert.equal(tab.speechCalls.length,1);
  request.resolve({ok:true,status:202});await flush();
  tab.finish('Immediate answer',{request_id:body.request_id});
  assert.equal(tab.speechCalls.length,1);
});

test('Talk barge-in clears old reply ownership before a late completion', async()=>{
  const tab=await createTab();
  tab.event({...config,deepgram_available:true,talk_available:true});
  await tab.elements.get('btnTalk').onclick();
  const request=await tab.send('Old spoken turn');
  tab.getTalkOptions().stopSpeech();
  tab.finish('Late old voice',{request_id:JSON.parse(request.options.body).request_id});
  assert.equal(tab.speechCalls.length,0);
  await tab.elements.get('btnTalk').onclick();
});

test('Stop reply prevents a late uncancelled completion from speaking',async()=>{
  const tab=await createTab();
  await tab.send('Stop this voice');
  tab.elements.get('btnStop').onclick();
  tab.finish('Late completion without a cancelled flag');
  assert.equal(tab.speechCalls.length,0);
});

for (const echoFirst of [false, true]) {
  test(`accepted local send speaks once when its echo arrives ${echoFirst ? 'before' : 'after'} the HTTP response`, async () => {
    const tab = await createTab();
    await tab.send('Local question', 202, echoFirst);
    tab.event({type: 'text_delta', delta: 'Partial'});
    tab.finish('Complete local reply.');
    assert.equal(tab.speechCalls.length, 1);
    assert.equal(tab.speechCalls[0].reply, 'Complete local reply.');
    assert.equal(tab.speechCalls[0].options.provider, 'elevenlabs');
  });
}

test('an accepted request without its matching echo does not own a completion', async () => {
  const tab = await createTab();
  tab.elements.get('input').value = 'Local question';
  tab.elements.get('send').onclick();
  tab.sayRequests[0].resolve({ok: true, status: 202});
  await flush();
  tab.event({type: 'chat_user', text: 'A different tab question'});
  tab.finish();
  assert.equal(tab.speechCalls.length, 0);
});

test('a delayed HTTP acceptance cannot revive ownership after completion', async () => {
  const tab = await createTab();
  tab.elements.get('input').value = 'Question with a delayed HTTP response';
  tab.elements.get('send').onclick();
  tab.event({type: 'chat_user', text: 'Question with a delayed HTTP response'});
  tab.finish('Completion before HTTP acceptance.');
  assert.equal(tab.speechCalls.length, 0, 'A matching echo alone cannot authorize automatic speech');
  tab.sayRequests[0].resolve({ok: true, status: 202});
  await flush();
  tab.finish('An unowned later completion.');
  assert.equal(tab.speechCalls.length, 0, 'A late response must not authorize an unrelated completion');
});

for (const failure of [409, 500, 'network']) {
  test(`a ${failure} send failure cannot authorize later speech`, async () => {
    const tab = await createTab();
    tab.elements.get('input').value = 'Rejected local question';
    tab.elements.get('send').onclick();
    tab.event({type: 'chat_user', text: 'Rejected local question'});
    const request = tab.sayRequests[0];
    if (failure === 'network') request.reject(new Error('Offline fixture disconnect'));
    else request.resolve({ok: false, status: failure});
    await flush();
    tab.finish('Another client completed a turn.');
    assert.equal(tab.speechCalls.length, 0);
  });
}

test('duplicate completion and reconnect replay do not repeat automatic speech', async () => {
  const tab = await createTab();
  await tab.send('Local question');
  tab.finish();
  assert.equal(tab.speechCalls.length, 1);
  tab.finish();
  assert.equal(tab.speechCalls.length, 1, 'A duplicate completion must consume no second speech request');
  tab.reconnect();
  tab.finish();
  assert.equal(tab.speechCalls.length, 1, 'Reconnecting must not restore consumed ownership');
});

test('reconnect during an owned turn preserves one playback and a later local turn can speak', async () => {
  const tab = await createTab();
  await tab.send('Repeated question');
  tab.reconnect(true);
  tab.finish('Repeated reply.');
  assert.equal(tab.speechCalls.length, 1);
  await tab.send('Repeated question');
  tab.finish('Repeated reply.');
  assert.equal(tab.speechCalls.length, 2, 'Separate accepted turns may legitimately have the same text');
});

test('a cancelled completion clears local speech ownership', async () => {
  const tab = await createTab();
  await tab.send('Please stop this reply');
  tab.finish('Partial cancelled reply.', {cancelled: true});
  tab.finish('A later unowned completion.');
  assert.equal(tab.speechCalls.length, 0);
});

test('a spectator can explicitly play a completed reply', async () => {
  const tab = await createTab();
  tab.finish('Manually playable reply.');
  assert.equal(tab.speechCalls.length, 0);
  const buttons = tab.buttons('Play reply');
  assert.equal(buttons.length, 1, 'Completed replies need an explicit Play reply control');
  buttons[0].onclick();
  assert.equal(tab.speechCalls.length, 1);
  assert.equal(tab.speechCalls[0].reply, 'Manually playable reply.');
  assert.deepEqual(tab.fetchCalls.map(call => call.url), ['/api/config'], 'No model or speech provider network calls occur in this fixture');
});
