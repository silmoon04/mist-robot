import {createFaceState, requestPreset, sampleFace, stopFace, canonicalViseme, FRAME_MS} from './source/state.mjs';
import {AtlasRenderer, fetchJson, validateManifest} from './source/player.mjs';

export const VERSION = '1.0.0';
export const EXPRESSION_MAP = Object.freeze({neutral:'attentive', listening:'quiet-listening', thinking:'considering', happy:'amused', sad:'concerned', alert:'attentive', curious:'friendly-curiosity', reassuring:'reassuring'});
const DEFAULT_MANIFEST = new URL('../../site/asset-manifest.json', import.meta.url);
const rest = (source = 'silence') => ({active:false,viseme:'rest',amount:0,source,time:0,epoch:null,sequence:null,turn_id:null});
const tagged = epoch => Number.isInteger(epoch) && epoch >= 0;
const unsupported = () => ({supported:false,reason:'This adapter only implements the Geraldine face and speech cels.',token:null});

function resolveAssets(manifest, base) {
  const copy = structuredClone(manifest);
  for (const asset of [...Object.values(copy.eyes),...Object.values(copy.mouths)]) {
    asset.file = new URL(asset.file, base).href;
    for (const frame of asset.frames) for (const item of [frame,frame.left,frame.right].filter(Boolean)) if (item.file) item.file = new URL(item.file,base).href;
  }
  copy.extraAssets = (copy.extraAssets || []).map(file => new URL(file,base).href);
  return copy;
}

export function createGeraldineAdapter(canvas, options = {}) {
  const now = options.now || (() => performance.now());
  let manifest, renderer, faceState, loaded = false, destroyed = false, error = null;
  let epoch = tagged(options.epoch) ? options.epoch : 0, generation = 0;
  let intent = EXPRESSION_MAP[options.expression] || options.expression || 'attentive';
  let state = 'available', reaction = null, speech = null, sampled = rest(), pose = null, lastFrame = null, withinSpeechDuration = false;
  let speechView = {active:true,playing:false,positionMs:0,cues:[]};
  let history = [], lastTime = -Infinity;
  const validId = id => manifest?.presets.some(preset => preset.id === id);
  const stamp = () => Number(now()) || 0;
  function close(source) {
    generation++; speech = null; sampled = rest(source); history = []; lastFrame = null; withinSpeechDuration = false;
    speechView = {active:true,playing:false,positionMs:0,cues:[]};
  }
  function acceptEpoch(value) {
    if (value === undefined || value === null) return true;
    if (!tagged(value) || value < epoch) return false;
    if (value > epoch) {
      epoch = value; close('epoch'); reaction = null;
      if (faceState) requestPreset(faceState,intent,stamp(),speechView,{quiet:options.reducedMotion});
    }
    return true;
  }
  function choose(id, at) {
    if (faceState) requestPreset(faceState,id,at,speechView,{quiet:options.reducedMotion,bridgeFamily:manifest.closedBridge?.family || 'attentive'});
  }
  function readSpeech() {
    withinSpeechDuration = false;
    if (!speech) return rest(sampled.source);
    const attached = speech, serial = generation;
    let cue;
    try {
      if (typeof attached.sample === 'function') cue = attached.sample();
      else {
        const time = Number(attached.clock?.());
        if (!Number.isFinite(time) || time < 0 || time >= attached.duration) cue = {...rest(),time:Number.isFinite(time)?time:0};
        else {
          const event = attached.events.findLast(event => event.time <= time && (event.end === undefined || time < event.end));
          cue = event ? {...event,active:true,time,source:event.source || 'timed_cues',epoch:attached.epoch} : {...rest('missing_cues'),time};
        }
      }
    } catch (failure) { error = `Speech sampler failed: ${failure.message || failure}`; cue = rest('sample_error'); }
    if (destroyed || generation !== serial || attached !== speech) return rest('canceled');
    if (!cue || typeof cue !== 'object') return rest('missing_sample');
    if (cue.epoch != null && (!tagged(cue.epoch) || cue.epoch < epoch)) return rest('stale_epoch');
    let inBounds = true;
    if (typeof attached.sample === 'function' && Number.isFinite(attached.duration)) {
      try {
        const time = typeof attached.clock === 'function' ? attached.clock() : cue.time;
        inBounds = Number.isFinite(time) && time >= 0 && time < attached.duration;
      } catch (failure) { error = `Speech clock failed: ${failure.message || failure}`; inBounds = false; }
      if (destroyed || generation !== serial || attached !== speech) return rest('canceled');
    }
    if (tagged(cue.epoch) && cue.epoch > epoch) {
      epoch = cue.epoch; reaction = null; choose(intent,stamp());
    }
    withinSpeechDuration = inBounds;
    const viseme = canonicalViseme(cue.viseme);
    const amount = cue.amount === undefined ? (viseme === 'rest' ? 0 : 1) : Number.isFinite(cue.amount) ? Math.max(0,Math.min(1,cue.amount)) : 0;
    return {active:cue.active === true,viseme,amount,source:cue.source || 'unavailable',time:Number.isFinite(cue.time)?cue.time:0,epoch:cue.epoch ?? null,sequence:cue.sequence ?? null,turn_id:cue.turn_id ?? null};
  }
  function makeSpeechView(cue) {
    const articulating = withinSpeechDuration && cue.active && cue.viseme !== 'rest' && cue.amount > 0;
    const positionMs = cue.time * 1000;
    if (!articulating) { history = []; lastTime = positionMs; return {active:true,playing:false,positionMs,cues:[]}; }
    if (positionMs < lastTime) history = [];
    if (!history.length || history.at(-1).viseme !== cue.viseme) {
      if (history.length) history.at(-1).endMs = positionMs;
      history.push({startMs:positionMs,endMs:Infinity,viseme:cue.viseme});
    }
    lastTime = positionMs;
    history = history.filter(item => item.endMs >= positionMs - 1000);
    return {active:true,playing:true,positionMs,cues:history};
  }
  const api = {
    get loaded() { return loaded; }, get manifest() { return manifest; }, get expression() { return faceState?.targetId || intent; },
    ready:null,
    update(nowMs = stamp()) {
      if (destroyed || !loaded || !Number.isFinite(nowMs)) return api.snapshot();
      const frame = Math.floor((nowMs + 0.000001) / FRAME_MS);
      if (frame === lastFrame) return api.snapshot();
      lastFrame = frame;
      sampled = readSpeech();
      if (destroyed) return api.snapshot();
      speechView = makeSpeechView(sampled);
      if (reaction && nowMs >= reaction.untilMs) { reaction = null; choose(intent,nowMs); }
      pose = sampleFace(faceState,nowMs,{speech:speechView,quiet:options.reducedMotion});
      // A speech rest must close even a preset with an open expressive idle cel.
      if (!withinSpeechDuration || !sampled.active || sampled.viseme === 'rest' || sampled.amount <= 0) pose = {...pose,mouthFrame:'rest',speaking:false};
      renderer.draw(canvas,pose);
      return api.snapshot();
    },
    snapshot() {
      return {version:VERSION,renderer:'geraldine-native-atlas',loaded,destroyed,state,expression:api.expression,intent,epoch,generation,requestCount:faceState?.requestCount || 0,pose:pose?{...pose}:null,viseme:pose?.mouthFrame || 'rest',speech:{...sampled},reaction:reaction?{...reaction}:null,error};
    },
    startSpeech(config = {}) {
      if (destroyed || !acceptEpoch(config.epoch)) return false;
      close('start');
      speech = {sample:config.sample,clock:config.clock,duration:Number.isFinite(config.duration)?Math.max(0,config.duration):Infinity,epoch:config.epoch,
        events:(Array.isArray(config.events)?config.events:[]).filter(event => Number.isFinite(event.time) && event.time >= 0).map(event=>({...event})).sort((a,b)=>a.time-b.time)};
      return true;
    },
    stopSpeech() { if (destroyed) return false; close('stop'); return true; },
    setExpression(id, config = {}) {
      id = EXPRESSION_MAP[id] || id;
      if (destroyed || !validId(id) || (config.durationMs !== undefined && (!Number.isFinite(config.durationMs) || config.durationMs <= 0 || config.durationMs > 10000)) || !acceptEpoch(config.epoch)) return false;
      const at = stamp();
      if (config.durationMs !== undefined) {
        if (reaction?.id === id) return true;
        reaction = {id,untilMs:at + config.durationMs}; choose(id,at);
      } else { intent = id; if (!reaction) choose(id,at); }
      return true;
    },
    handleEvent(event = {}) {
      if (event.type === 'expression') return api.setExpression(event.expression,event);
      if (event.type === 'reset') return api.reset(event);
      if (destroyed || event.type !== 'state' || typeof event.state !== 'string' || !acceptEpoch(event.epoch)) return false;
      state = event.state; return true;
    },
    reset(config = {}) {
      if (destroyed || !acceptEpoch(config.epoch ?? epoch + 1)) return false;
      close('reset'); reaction = null; state = 'available';
      if (faceState) { stopFace(faceState,stamp()); choose(intent,stamp()); }
      return true;
    },
    destroy() { if (destroyed) return; close('destroy'); destroyed = true; loaded = false; },
    setGaze:unsupported,clearGaze:unsupported,setListeningSignal:unsupported,setActivity:unsupported,clearActivity:unsupported,resetActivities:unsupported,previewActivity:unsupported
  };
  api.ready = (async () => {
    try {
      const url = new URL(options.manifestUrl || DEFAULT_MANIFEST,globalThis.location?.href || DEFAULT_MANIFEST);
      manifest = validateManifest(options.manifest || await fetchJson(url));
      if (destroyed) return false;
      if (!validId(intent)) { error = `Unknown initial expression: ${intent}; using attentive.`; intent = 'attentive'; }
      faceState = createFaceState(manifest.presets,intent,stamp());
      renderer = options.renderer || new AtlasRenderer(resolveAssets(manifest,url));
      await renderer.load?.();
      if (destroyed) return false;
      loaded = true; return true;
    } catch (failure) { error = `Geraldine assets unavailable: ${failure.message || failure}`; loaded = false; return false; }
  })();
  return api;
}
