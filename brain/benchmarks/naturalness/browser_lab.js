import {Playback} from '/duplex/playback.js?v=20260922-fps15-th';
import {ExpressionPolicy} from '/duplex/expression_policy.js?v=20260922-fps15-holds';
import {replyExpression} from '/duplex/delivery.js?v=20260922-expression-policy';

export const LAB_CAPTURE_VERSION = '2026-09-24-continuous-recorder-v2';
const FRAME_MS = 1000 / 15;
const PCM_RATE = 16000;
const sleep = ms => new Promise(resolve => setTimeout(resolve, Math.max(0, ms)));
const round = value => Number.isFinite(value) ? Math.round(value * 1000) / 1000 : null;

export async function drainPlayback({isPlaying,isGenerating=()=>false,lastActivityMs=()=>null,now,wait,check=()=>{},maxMs=20000,settleMs=200}) {
  const started = now();
  const pending = () => isPlaying() || isGenerating();
  if (!pending() && (lastActivityMs()===null || started-lastActivityMs()>=settleMs)) {
    return {extended:false,duration_ms:0,timed_out:false,settled:true};
  }
  let idleSince = null;
  while (now()-started < maxMs) {
    check();
    if (pending()) idleSince = null;
    else if (idleSince === null) idleSince = now();
    else if (lastActivityMs()!==null) idleSince = Math.max(idleSince,lastActivityMs());
    if (idleSince !== null && now()-idleSince >= settleMs) {
      return {extended:true,duration_ms:round(now()-started),timed_out:false,settled:true};
    }
    await wait(Math.min(20,maxMs-(now()-started)));
  }
  check();
  return {extended:true,duration_ms:round(now()-started),timed_out:true,settled:false,
    playback_pending:isPlaying(),generation_pending:isGenerating()};
}

export function observeGeneration(generation,event,at) {
  if (event.type==='transcript_delta' && event.role==='assistant') {
    generation.pending=true;generation.last_activity_ms=at;
  } else if (event.type==='transcript_done' && event.role==='assistant') {
    generation.pending=false;generation.completed_ms=at;generation.last_activity_ms=at;
  } else if ((event.type==='transcript_done' && event.role==='user' && event.text?.trim() &&
      !(event.backchannel===true && event.floor_preserved===true)) ||
      (event.type==='state' && ['thinking','checking'].includes(event.state))) {
    generation.pending=true;generation.last_activity_ms=at;
  } else if (event.type==='audio') generation.last_activity_ms=at;
}

// The resampler retains its fractional position across render quanta. A
// low-pass node filters the captured graph before downsampling in the worklet.
export class StreamingResampler {
  constructor(inputRate,outputRate=16000) {
    this.step=inputRate/outputRate;this.position=0;this.consumed=0;this.previous=0;
  }
  push(samples) {
    const start=this.consumed,end=start+samples.length,result=[];
    if (!samples.length) return result;
    while (this.position <= end-1) {
      const left=Math.floor(this.position),fraction=this.position-left;
      const a=left<start?this.previous:samples[left-start];
      const b=fraction===0?a:samples[left+1-start];
      result.push(a+(b-a)*fraction);this.position+=this.step;
    }
    this.previous=samples[samples.length-1];this.consumed=end;
    return result;
  }
}

export function mixPcm16(echo,input=null,offset=0) {
  const output=new Uint8Array(echo.length*2),out=new DataView(output.buffer);
  const user=input?new DataView(input.buffer,input.byteOffset,input.byteLength):null;
  let echoPower=0,userPower=0,mixedPower=0,clipped=0,consumed=0;
  for (let index=0;index<echo.length;index++) {
    const userAt=offset+index*2;
    const near=user && userAt+2<=input.byteLength?user.getInt16(userAt,true)/32768:0;
    if (user && userAt+2<=input.byteLength) consumed+=2;
    const raw=echo[index]+near,sample=Math.max(-1,Math.min(32767/32768,raw));
    if (raw!==sample) clipped++;
    out.setInt16(index*2,Math.round(sample*32768),true);
    echoPower+=echo[index]**2;userPower+=near**2;mixedPower+=sample**2;
  }
  return {pcm:output,consumed,clipped,echo_rms:Math.sqrt(echoPower/echo.length),
    input_rms:Math.sqrt(userPower/echo.length),mixed_rms:Math.sqrt(mixedPower/echo.length)};
}

export const ECHO_WORKLET_SOURCE = `${StreamingResampler.toString()}
class MistLabEcho extends AudioWorkletProcessor {
  constructor() { super(); this.resampler=new StreamingResampler(sampleRate); this.packet=new Float32Array(320); this.used=0; this.packetStart=0; }
  process(inputs,outputs) {
    const size=outputs[0][0].length;
    const samples=inputs[0]?.[0] || new Float32Array(size);
    const before=this.resampler.position;
    const values=this.resampler.push(samples);
    for(let index=0;index<values.length;index++) {
      if(this.used===0) this.packetStart=(before+index*this.resampler.step)/sampleRate;
      this.packet[this.used++]=values[index];
      if(this.used===320) {
        this.port.postMessage({samples:this.packet.buffer,stream_start_s:this.packetStart,process_context_s:currentTime},[this.packet.buffer]);
        this.packet=new Float32Array(320);this.used=0;
      }
    }
    for(const output of outputs[0]) output.fill(0);
    return true;
  }
}
registerProcessor('mist-lab-echo',MistLabEcho);`;

const echoContexts=new WeakSet();
async function createDigitalEcho(context,tee,settings,send,record,result,isOpen) {
  if (!context.audioWorklet || !globalThis.AudioWorkletNode) throw Error('Digital echo requires AudioWorklet');
  const gain=Number(settings.gain),delayMs=Number(settings.delay_ms);
  if (!Number.isFinite(gain) || gain<0 || gain>1 || !Number.isFinite(delayMs) || delayMs<0 || delayMs>2000) {
    throw Error('Digital echo requires gain 0..1 and delay_ms 0..2000');
  }
  if (!echoContexts.has(context)) {
    const url=URL.createObjectURL(new Blob([ECHO_WORKLET_SOURCE],{type:'text/javascript'}));
    try {await context.audioWorklet.addModule(url);echoContexts.add(context);} finally {URL.revokeObjectURL(url);}
  }
  const source=context.createMediaStreamSource(tee.stream),delay=context.createDelay(2),level=context.createGain();
  const filter=context.createBiquadFilter(),node=new AudioWorkletNode(context,'mist-lab-echo',{
    numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[1],channelCount:1,channelCountMode:'explicit'});
  delay.delayTime.value=delayMs/1000;level.gain.value=gain;filter.type='lowpass';filter.frequency.value=7000;filter.Q.value=.707;
  const frames=result.echo_frames=[];
  const metadata=result.digital_echo={enabled:true,gain,nominal_delay_ms:delayMs,input_sample_rate:context.sampleRate,
    uplink_sample_rate:16000,lowpass_hz:7000,source:'actual_web_audio_media_stream_tee',
    delay_scope:'render_graph_plus_media_stream_and_worklet_buffering',physical_microphone:false,browser_aec:false,
    packets:0,non_silent_echo_packets:0,clipped_samples:0,max_echo_rms:0};
  let active=null,stopped=false;
  node.port.onmessage=event => {
    if (stopped || !isOpen()) return;
    try {
      const at=record.now(),echo=new Float32Array(event.data.samples);
      const mixed=mixPcm16(echo,active?.pcm,active?.offset || 0);
      send({type:'mic',pcm:btoa(String.fromCharCode(...mixed.pcm))},false);
      metadata.packets++;metadata.clipped_samples+=mixed.clipped;
      metadata.max_echo_rms=Math.max(metadata.max_echo_rms,mixed.echo_rms);
      if (mixed.echo_rms>.0001) metadata.non_silent_echo_packets++;
      frames.push([at,round(event.data.process_context_s),round(mixed.echo_rms),round(mixed.input_rms),round(mixed.mixed_rms),mixed.clipped]);
      if (active) {
        const {input}=active;
        if (input.start_ms===null) {
          input.start_ms=at;
          input.playback_active_at_start=active.isPlaying();
          record('input_started',{step:input.step,file:input.file,playback_active:input.playback_active_at_start,
            role:input.role,digital_echo:true,requested_start_ms:input.requested_start_ms});
        }
        const due=input.start_ms+active.offset/32;
        input.packets.push([at,mixed.consumed,round(Math.max(0,at-due))]);active.offset+=mixed.consumed;
        if (active.offset>=active.pcm.length) {
          active.done=true;active.sent_end_ms=at+mixed.consumed/32;active=null;
        }
      }
    } catch (error) {record('echo_uplink_error',{message:error.message});metadata.error=error.message;if (active) active.error=error.message;}
  };
  source.connect(delay).connect(level).connect(filter).connect(node).connect(context.destination);
  // The processor writes only zeros to its output. This branch captures and
  // submits echo without playing a second copy through the speaker.
  record('digital_echo_started',metadata);
  return {
    play(pcm,input,isPlaying) {
      if (active) throw Error('Digital echo mixer already has an input');
      active={pcm,input,isPlaying,offset:0,done:false,sent_end_ms:null};return active;
    },
    stop() {
      stopped=true;node.port.onmessage=null;
      for(const item of [source,delay,level,filter,node]) item.disconnect();
      record('digital_echo_stopped',{packets:metadata.packets,non_silent_echo_packets:metadata.non_silent_echo_packets,
        clipped_samples:metadata.clipped_samples,max_echo_rms:metadata.max_echo_rms});
      if (!metadata.non_silent_echo_packets) result.errors.push({phase:'echo_capture',message:'No non-silent rendered echo reached the uplink'});
    },
    get error() {return metadata.error;},
  };
}

// Parse the container without AudioContext decoding or implicit resampling.
export function parseFixtureWav(buffer) {
  const data = new DataView(buffer);
  const tag = offset => String.fromCharCode(...new Uint8Array(buffer, offset, 4));
  if (buffer.byteLength < 44 || tag(0) !== 'RIFF' || tag(8) !== 'WAVE') throw Error('Expected a RIFF WAV fixture');
  let format = null, pcm = null;
  for (let offset = 12; offset + 8 <= data.byteLength;) {
    const size = data.getUint32(offset + 4, true), start = offset + 8;
    if (start + size > data.byteLength) throw Error('Truncated WAV chunk');
    if (tag(offset) === 'fmt ') {
      if (size < 16) throw Error('Invalid WAV format chunk');
      format = {encoding:data.getUint16(start,true),channels:data.getUint16(start+2,true),
        sample_rate:data.getUint32(start+4,true),bits:data.getUint16(start+14,true)};
    }
    if (tag(offset) === 'data') pcm = new Uint8Array(buffer.slice(start, start + size));
    offset = start + size + size % 2;
  }
  if (!format || !pcm || !pcm.length || pcm.length % 2) throw Error('Missing or invalid WAV PCM');
  if (format.encoding !== 1 || format.channels !== 1 || format.sample_rate !== PCM_RATE || format.bits !== 16) {
    throw Error('Fixture must be PCM16 mono at 16000 Hz');
  }
  return {...format, pcm, duration_ms:pcm.length / 32};
}

export function startedQueuedPlayback(observations,segments) {
  const queued=new Set(segments.map(segment => `${segment.event.epoch}:${segment.event.seq}`));
  return observations.playback_starts.filter(start => queued.has(`${start.epoch}:${start.sequence}`));
}

export function observePlaybackCancellation(observations,player,nextEpoch,at) {
  if (nextEpoch<player.epoch) return null;
  const starts=startedQueuedPlayback(observations,player.segments);
  if (!starts.length) return null;
  const event={type:'playback_cancelled',t_ms:at,reason:'audio_reset',epoch:player.epoch,next_epoch:nextEpoch,
    started_sequences:[...new Set(starts.map(start => start.sequence))],last_started_ms:starts.at(-1).t_ms};
  (observations.playback_cancellations ??= []).push(event);
  return event;
}

export function resolveTrigger(step, observations, anchorMs) {
  const kind = step.trigger || 'immediate';
  if (kind === 'ready') return observations.ready_ms;
  if (kind === 'immediate') return anchorMs;
  if (kind === 'after_input') return observations.last_input_end_ms ?? null;
  const starts = observations.playback_starts.filter(item => item.t_ms >= anchorMs);
  if (kind === 'after_playback') {
    const fresh = starts.filter(item => !observations.excluded_playback_keys?.has(`${item.epoch}:${item.sequence}`));
    return fresh[Math.max(1, step.playback_index || 1) - 1]?.t_ms ?? null;
  }
  if (kind === 'after_idle') {
    const endings=[...observations.playback_idles,...(observations.playback_cancellations || [])].sort((a,b) => a.t_ms-b.t_ms);
    if (observations.action_had_playback && observations.playback_starts.some(start => start.t_ms<=anchorMs)) {
      return endings.find(item => item.t_ms>=anchorMs)?.t_ms ?? null;
    }
    if (!starts.length) return null;
    return endings.find(item => item.t_ms >= starts[0].t_ms)?.t_ms ?? null;
  }
  throw Error(`Unknown step trigger: ${kind}`);
}

export function compactFace(snapshot) {
  const keys = ['expression','speaking','viseme','amount','speechTime','audioActive','alignmentSource',
    'syncSource','renderer','drawnReady','drawnError','drawnAnimation','drawnMouthFamily','drawnTransition',
    'drawnIdentity','handdrawn','bounds'];
  return Object.fromEntries(keys.filter(key => snapshot[key] !== undefined).map(key => [key, snapshot[key]]));
}

export function summarizeCapture(result) {
  const starts = result.events.filter(event => event.type === 'playback_started');
  const resets = result.events.filter(event => event.type === 'audio_reset');
  const schedule = result.events.filter(event => event.type === 'source_scheduled');
  const frameGaps = result.frames.slice(1).map((frame, index) => frame.t_ms - result.frames[index].t_ms);
  return {
    timing_kind:'software_output_estimate_not_acoustic',
    next_playback_scope:'nearest_playback_after_input_end_without_response_attribution',
    first_playback_ms:starts[0]?.t_ms ?? null,
    last_playback_start_ms:starts.at(-1)?.t_ms ?? null,
    first_scheduled_output_ms:schedule[0]?.estimated_output_start_ms ?? null,
    last_scheduled_output_end_ms:schedule.at(-1)?.estimated_output_end_ms ?? null,
    scheduled_sources:schedule.length, playback_starts:starts.length, audio_resets:resets.length,
    max_frame_gap_ms:frameGaps.length ? round(Math.max(...frameGaps)) : null,
    input_turns:result.inputs.map(input => {
      const response = starts.find(event => event.t_ms >= input.end_ms);
      const reset = resets.find(event => event.t_ms >= input.start_ms);
      return {step:input.step, file:input.file, start_ms:input.start_ms, end_ms:input.end_ms,
        playback_active_at_start:input.playback_active_at_start,
        next_playback_after_input_end_ms:response ? round(response.t_ms - input.end_ms) : null,
        reset_after_input_start_ms:reset ? round(reset.t_ms - input.start_ms) : null,
        max_packet_lateness_ms:input.packets.length ? round(Math.max(...input.packets.map(packet => packet[2]))) : null};
    }),
  };
}

async function fetchChecked(url, options = {}, timeoutMs = 30000) {
  const controller = new AbortController();
  const cancel = () => controller.abort(options.signal.reason);
  options.signal?.addEventListener('abort', cancel, {once:true});
  if (options.signal?.aborted) cancel();
  const timer = setTimeout(() => controller.abort(Error(`HTTP timeout: ${url}`)), timeoutMs);
  try {
    const response = await fetch(url, {...options, signal:controller.signal});
    if (!response.ok) throw Error(`${url}: HTTP ${response.status} ${(await response.text()).slice(0,200)}`);
    return response;
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', cancel);
  }
}

const post = (url, body, signal) => fetchChecked(url, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal});

// This proxy only adds a recording connection. Playback still owns scheduling,
// speaker connection, stop behavior, and the face's output clock.
export function recordingContext(context, destination, record, getPlayer, getPacket) {
  let sourceId = 0;
  return new Proxy(context, {
    get(target, key) {
      if (key === 'createBufferSource') return () => {
        const source = target.createBufferSource(), id = ++sourceId, packet = getPacket();
        source.connect(destination);
        const nativeStart = source.start.bind(source), nativeStop = source.stop.bind(source);
        source.start = (...args) => {
          nativeStart(...args);
          const at = Number(args[0]) || target.currentTime, player = getPlayer();
          const outputTime = player?.outputTime() ?? target.currentTime;
          const duration = source.buffer?.duration || 0;
          record('source_scheduled', {source_id:id,epoch:packet?.epoch,sequence:packet?.seq,
            context_start_s:at,duration_s:duration,
            estimated_output_start_ms:round(record.now() + (at-outputTime)*1000),
            estimated_output_end_ms:round(record.now() + (at+duration-outputTime)*1000),
            timing_kind:'software_output_estimate_not_acoustic'});
        };
        source.stop = (...args) => {
          nativeStop(...args);
          record('source_stop_called', {source_id:id,context_stop_s:args[0] ?? target.currentTime,
            epoch:packet?.epoch,sequence:packet?.seq,timing_kind:'software_command_not_acoustic'});
        };
        source.addEventListener('ended', () => record('source_ended', {source_id:id,epoch:packet?.epoch,sequence:packet?.seq}));
        return source;
      };
      const value = Reflect.get(target, key, target);
      return typeof value === 'function' ? value.bind(target) : value;
    },
  });
}

export function startRecordingClock(context,destination,record) {
  const source=context.createConstantSource();
  source.offset.value=0;source.connect(destination);
  const metadata={source:'constant_zero_to_recording_tee',value:0,speaker_connected:false,
    started_ms:record.now(),started_context_s:context.currentTime,stopped_ms:null,stopped_context_s:null};
  source.start();
  record('recording_clock_started',metadata);
  let stopped=false;
  return {metadata,stop() {
    if (stopped) return;
    stopped=true;metadata.stopped_ms=record.now();metadata.stopped_context_s=context.currentTime;
    source.stop();source.disconnect();
    record('recording_clock_stopped',{stopped_ms:metadata.stopped_ms,stopped_context_s:metadata.stopped_context_s});
  }};
}

export function createRecorder(stream, kind, record) {
  if (!globalThis.MediaRecorder) return {kind,unavailable:'MediaRecorder is unavailable'};
  const types = kind === 'face_video' ? ['video/webm;codecs=vp9,opus','video/webm;codecs=vp8,opus','video/webm','video/mp4'] :
    ['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/mp4'];
  const mimeType = types.find(type => MediaRecorder.isTypeSupported(type));
  if (!mimeType) return {kind,unavailable:'No supported recording format'};
  const chunks = [], recorder = new MediaRecorder(stream, {mimeType});
  let error = null, resolveStopped, didStop = false, encoderStartedMs=null, stoppedEventMs=null;
  const chunkTimes=[];
  const stopped = new Promise(resolve => {resolveStopped = resolve;});
  recorder.ondataavailable = event => {
    if (event.data.size) {
      chunks.push(event.data);
      chunkTimes.push({observed_ms:record.now(),timecode_ms:Number.isFinite(event.timecode)?event.timecode:null,bytes:event.data.size});
    }
  };
  recorder.onstart = () => {encoderStartedMs=record.now();record('recording_encoder_started',{kind,clock_id:'browser_performance'});};
  recorder.onerror = event => {error = event.error?.message || 'MediaRecorder failed';record('recording_error',{kind,message:error});};
  recorder.onstop = () => {didStop = true;stoppedEventMs=record.now();resolveStopped();};
  const startedMs = record.now();
  recorder.start(1000);
  record('recording_started', {kind,mime_type:mimeType,clock_id:'browser_performance'});
  return {kind,async stop() {
    const stopRequestedMs=record.now();
    if (recorder.state !== 'inactive') recorder.stop();
    let stopTimer;
    try {
      await Promise.race([stopped,new Promise(resolve => {stopTimer=setTimeout(() => {
        if (!didStop) error='Recorder stop timed out';resolve();
      },5000);})]);
    } finally {clearTimeout(stopTimer);}
    const blob = new Blob(chunks, {type:mimeType});
    record('recording_stopped', {kind,bytes:blob.size,error,stop_requested_ms:stopRequestedMs,clock_id:'browser_performance'});
    return {kind,mime_type:mimeType,start_ms:startedMs,end_ms:stopRequestedMs,clock_id:'browser_performance',
      encoder_started_ms:encoderStartedMs,stop_event_ms:stoppedEventMs,encoder_flush_ms:stoppedEventMs===null?null:round(stoppedEventMs-stopRequestedMs),
      chunks:chunkTimes,bytes:blob.size,error,blob};
  }};
}

async function installLab() {
  const $ = id => document.getElementById(id);
  let context = null, running = false, controller = null;
  const state = {status:'loading',capture_version:LAB_CAPTURE_VERSION,case_id:null,results:[],fixtures:[]};
  const status = text => { $('status').textContent = text; window.labStatus = state.status; };
  const requestedIds = (new URLSearchParams(location.search).get('ids') || '').split(',').filter(Boolean);
  const selected = () => $('case').value;
  const download = (blob, filename) => {
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob); link.download = filename; link.textContent = filename;
    const line = document.createElement('p');line.append(link);$('downloads').append(line);
  };
  const setRunning = value => {
    running = value;
    $('run').disabled = value; $('run-all').disabled = value; $('case').disabled = value; $('stop').disabled = !value;
  };
  const fail = error => {state.status = 'failed';status(error.message || String(error));};

  async function runCase(fixture, map) {
    const origin = performance.now();
    const result = {schema_version:1,capture_version:LAB_CAPTURE_VERSION,case_id:fixture.id,status:'running',started_at:new Date().toISOString(),
      performance_time_origin_ms:performance.timeOrigin,performance_origin_ms:origin,
      timing_kind:'software_output_estimate_not_acoustic',fixture,events:[],frames:[],inputs:[],errors:[],recording:[],
      environment:{user_agent:navigator.userAgent,visibility:document.visibilityState,device_pixel_ratio:devicePixelRatio,
        sample_rate:context.sampleRate,base_latency_s:context.baseLatency ?? null,output_latency_s:context.outputLatency ?? null,
        microphone_opened:false,acoustic_capture:false,input_processing:'prebuilt_pcm16_16khz_no_browser_aec',
        face_fps:15,renderer_versions:{original:window.MistFaceRuntime?.version,drawn:window.MistDrawnFaceRuntime?.version,
          handdrawn:window.MistHanddrawnRuntime?.version}}};
    const record = (type, values = {}) => {const event = {t_ms:round(performance.now()-origin),type,...values};result.events.push(event);return event;};
    record.now = () => round(performance.now()-origin);
    controller = new AbortController();
    const signal = controller.signal;
    const deadline = setTimeout(() => controller.abort(Error('Case deadline exceeded')), fixture.timeout_ms || 120000);
    const check = () => {if (signal.aborted) throw signal.reason || Error('Run stopped');};
    const observations = {ready_ms:null,playback_starts:[],playback_idles:[],playback_cancellations:[]};
    const generation = {pending:false,last_activity_ms:null,completed_ms:null};
    let socket = null, player = null, face = null, echo = null, recordingClock = null, sampleTimer = null, expressionTimer = null, closing = false;
    let receivedFatal = null, currentPacket = null, ready = false, frameDue = 0, lastFaceId = null, lastGaze = null;
    let pendingCaption = '', conversationState = 'available', actionAnchor = 0, connectionActivity = null;
    const transcript = {assistant:'',user:''}, recorders = [], recordings = [], videoStreams = [], backgroundJobs = new Map();
    const tee = context.createMediaStreamDestination();
    const policy = new ExpressionPolicy(map, {transitionMs:matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : (window.MistDrawnFaceRuntime?.timing?.transitionMs ?? 260)});
    const send = (event, trace = true) => {
      if (socket?.readyState !== WebSocket.OPEN) throw Error('Voice socket is not open');
      socket.send(JSON.stringify(event));
      if (trace) record('client_sent', {event});
    };
    const render = () => {
      const shot = policy.setState(player?.sample()?.active ? 'speaking' : conversationState);
      if (shot.faceId !== lastFaceId) {lastFaceId = shot.faceId;face.setExpression(shot.faceId);}
      const gaze = JSON.stringify(shot.gaze);
      if (gaze !== lastGaze) {lastGaze = gaze;if (shot.gaze) face.setGaze(...shot.gaze);else face.clearGaze();}
      $('face').setAttribute('aria-label', `MIST face: ${shot.expression}`);
      return shot;
    };
    const setState = value => {conversationState = value;face.handleEvent?.({type:'state',state:value});render();};
    const waitFor = async (predicate, timeoutMs, label) => {
      const until = performance.now() + timeoutMs;
      while (true) {
        check();if (receivedFatal || echo?.error) throw Error(receivedFatal || echo.error);
        const value = predicate();if (value !== null && value !== false && value !== undefined) return value;
        if (performance.now() > until) throw Error(`${label} timed out after ${timeoutMs} ms`);
        await sleep(10);
      }
    };
    const waitUntil = async target => {while (record.now() < target) {check();if (receivedFatal || echo?.error) throw Error(receivedFatal || echo.error);await sleep(Math.min(20,target-record.now()));}};
    const capturePng = label => {
      try {if (face?.loaded && face.canvas) result[`${label}_frame`] = {t_ms:record.now(),png:face.canvas.toDataURL('image/png')};}
      catch (error) {record('frame_capture_unavailable',{message:error.message});}
    };
    const onVisibility = () => record('visibility_changed',{visibility:document.visibilityState});
    const onContext = () => record('audio_context_state',{state:context.state});
    document.addEventListener('visibilitychange',onVisibility);context.addEventListener('statechange',onContext);
    try {
      status(`Preparing ${fixture.id}`);state.case_id = fixture.id;
      await post('/lab/begin',{case_id:fixture.id},signal);
      check();
      face = (window.MistHanddrawnRuntime || window.MistDrawnFaceRuntime || window.MistFaceRuntime).create($('face'), {
        data:window.MIST_DATA,atlasUrl:'/drawn/atlas.json',manifestUrl:'/studio/handdrawn_v6/manifest.json'});
      const readyFace = await Promise.race([face.ready,sleep(20000).then(() => false)]);
      check();record('face_ready',{ready:!!readyFace,renderer:face.snapshot().renderer,error:face.error?.message ?? null});
      if (!readyFace) result.errors.push({phase:'face',message:face.error?.message || 'Production face did not load'});
      const contextProxy = recordingContext(context,tee,record,() => player,() => currentPacket);
      player = new Playback(contextProxy,face,() => {
        record('playback_lag_cleared');policy.interrupt();setState('listening');send({type:'barge_in'});
      },() => {
        observations.playback_idles.push(record('playback_idle',{clock_source:player.clockSource}));
        if (ready && !closing) send({type:'playback_state',playing:false});
        if (ready) setState('listening');
      },event => {
        const item = record('playback_started',{epoch:event.epoch,sequence:event.seq,
          queue_ms:round(Math.max(0,player.end-player.outputTime())*1000),clock_source:player.clockSource,
          alignment_source:event.alignment_source || 'audio_energy',timing_kind:'software_output_estimate_not_acoustic'});
        observations.playback_starts.push(item);
        if (!closing) send({type:'playback_state',playing:true});
        policy.request({expression:replyExpression(pendingCaption)},{source:'automatic'});render();
        $('caption').textContent = pendingCaption.slice(-300);
      });
      recordingClock=startRecordingClock(context,tee,record);
      result.recording_clock=recordingClock.metadata;
      result.media_alignment={status:'unverified_pending_media_audit',continuous_silence_source:true,
        contract:'Compare decoded audio/video PTS and duration against each recorder interval before aligning browser markers'};
      recorders.push(createRecorder(tee.stream,'audio',record));
      if (face.loaded && face.canvas?.captureStream) {
        try {
          const videoStream = face.canvas.captureStream(15);
          videoStreams.push(videoStream);
          for (const track of tee.stream.getAudioTracks()) videoStream.addTrack(track);
          recorders.push(createRecorder(videoStream,'face_video',record));
          result.video_capture = {source:'production_canvas',fps:15,width:face.canvas.width,height:face.canvas.height};
        } catch (error) {recorders.push({kind:'face_video',unavailable:error.message});}
      } else recorders.push({kind:'face_video',unavailable:'Loaded production canvas capture is unavailable'});
      render();capturePng('first');
      expressionTimer = setInterval(render,50);
      frameDue = performance.now();
      const sampleFrame = () => {
        const at = performance.now(), cue = player.sample();
        result.frames.push({t_ms:round(at-origin),sample_late_ms:round(Math.max(0,at-frameDue)),
          context_time_s:round(context.currentTime),output_time_s:round(player.outputTime()),clock_source:player.clockSource,
          audio_active:cue.active,queue_ms:round(Math.max(0,player.end-player.outputTime())*1000),
          audio_sequence:cue.sequence ?? null,face:compactFace(face.snapshot(at)),policy:policy.snapshot()});
        frameDue += FRAME_MS;
        if (frameDue < at-FRAME_MS) frameDue = at+FRAME_MS;
        sampleTimer = setTimeout(sampleFrame,Math.max(0,frameDue-performance.now()));
      };
      sampleFrame();
      connectionActivity = face.setActivity?.('connecting',{owner:'transport'}).token;
      socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/voice`);
      socket.onopen = () => record('socket_open');
      socket.onerror = () => {record('socket_error');receivedFatal = 'Voice socket error';};
      socket.onclose = event => {
        record('socket_closed',{code:event.code,reason:event.reason,clean:event.wasClean});
        if (!closing) receivedFatal = `Voice socket closed (${event.code})`;
      };
      socket.onmessage = message => {
        try {
          const event = JSON.parse(message.data), clean = {...event};
          if (clean.pcm !== undefined) {clean.pcm_bytes = Math.floor(clean.pcm.length*3/4)-(clean.pcm.endsWith('==')?2:clean.pcm.endsWith('=')?1:0);delete clean.pcm;}
          record(event.type,{...clean,direction:'server'});
          if (closing) {record('late_event_during_close',{event_type:event.type});return;}
          observeGeneration(generation,event,record.now());
          face.handleEvent?.(event);
          if (event.type === 'ready') {
            face.clearActivity?.(connectionActivity);connectionActivity = null;
            ready = true;observations.ready_ms = record.now();setState('listening');
          }
          else if (event.type === 'audio') {currentPacket = event;player.append(event);currentPacket = null;}
          else if (event.type === 'audio_reset') {
            if (event.epoch < player.epoch) {record('stale_reset_ignored',{epoch:event.epoch});return;}
            const cancelled=observePlaybackCancellation(observations,player,event.epoch,record.now());
            if (cancelled) record('playback_cancelled',cancelled);
            generation.pending=false;generation.last_activity_ms=record.now();
            player.reset(event.epoch);policy.interrupt();setState('listening');
            send({type:'playback_state',playing:false});pendingCaption = '';transcript.assistant = '';$('caption').textContent = '';
          } else if (event.type === 'transcript_delta') {
            transcript[event.role] = (transcript[event.role] || '') + event.text;
            if (event.role === 'assistant') pendingCaption = transcript.assistant;
          } else if (event.type === 'transcript_done') {
            transcript[event.role] = '';if (event.role === 'assistant') pendingCaption = event.text;
          } else if (event.type === 'face') {
            if (event.epoch !== player.epoch) {record('stale_face_ignored',{epoch:event.epoch});return;}
            const command = {expression:event.expression};
            for (const key of ['variant','duration_ms']) if (event[key] !== undefined) command[key] = event[key];
            record('expression_result',{result:policy.request(command,{source:event.source === 'manual' ? 'manual' : 'model'})});render();
          } else if (event.type === 'state') setState(event.state);
          else if (event.type === 'tool') {
            if (event.name === 'stop_robot') {policy.request({expression:'alert'},{source:'model'});render();}
            if (event.result?.status === 'preview_only' && event.result.action === 'phone_pan') {
              face.setGaze(Math.max(-1,Math.min(1,event.result.angle_rad/Math.PI)),0);
            }
          }
          else if (event.type === 'brain_job') backgroundJobs.set(event.job_id,event.status);
          else if (event.type === 'error') {
            result.errors.push({phase:'server',message:event.message,fatal:!!event.fatal});
            if (event.fatal) receivedFatal = event.message || 'Fatal server error';
          }
        } catch (error) {record('client_receive_error',{message:error.message});receivedFatal = error.message;}
      };
      await waitFor(() => ready,fixture.startup_timeout_ms || 30000,'Voice ready');
      if (fixture.digital_echo) {
        echo = await createDigitalEcho(context,tee,fixture.digital_echo,send,record,result,
          () => ready && !closing && socket?.readyState===WebSocket.OPEN);
        result.environment.input_processing='rendered_digital_echo_plus_fixture_pcm_no_browser_aec';
      }
      record('case_ready');status(`Running ${fixture.id}`);
      const wavCache = new Map();
      for (const [index,step] of fixture.steps.entries()) {
        check();
        let wav = null;
        if (step.file) {
          if (!wavCache.has(step.file)) {
            const path = step.file.split('/').map(encodeURIComponent).join('/');
            wavCache.set(step.file,parseFixtureWav(await (await fetchChecked(`/lab/fixture/${path}`,{signal})).arrayBuffer()));
          }
          wav = wavCache.get(step.file);
        }
        const trigger = await waitFor(() => resolveTrigger(step,observations,actionAnchor),step.trigger_timeout_ms || 30000,`Step ${index} ${step.trigger || 'immediate'}`);
        const target = trigger + (step.delay_ms || 0);
        await waitUntil(target);check();
        actionAnchor = record.now();
        observations.action_had_playback = startedQueuedPlayback(observations,player.segments).length>0;
        observations.excluded_playback_keys = new Set([
          ...observations.playback_starts.map(item => `${item.epoch}:${item.sequence}`),
          ...player.segments.map(item => `${item.event.epoch}:${item.event.seq}`),
        ]);
        record('step_started',{step:index,step_type:step.type || 'audio',trigger:step.trigger || 'immediate',
          trigger_ms:trigger,target_ms:target,late_ms:round(Math.max(0,actionAnchor-target))});
        if (step.type === 'seed_text') {
          generation.pending=true;generation.last_activity_ms=record.now();
          record('context_setup',{step:index,kind:'seed_text',text:step.text});
          await post('/lab/seed',{case_id:fixture.id,text:step.text},signal);
        } else if (step.type === 'background') {
          send({type:'start_background',question:step.question || step.text});
        } else if (step.type === 'pause') {
          await waitUntil(record.now() + (step.duration_ms || 0));
        } else {
          if (!wav) throw Error(`Step ${index} has no WAV file`);
          if (step.role && !['user','synthetic_noise'].includes(step.role)) throw Error(`Unsupported input role: ${step.role}`);
          const input = {step:index,file:step.file,role:step.role || 'user',start_ms:echo?null:record.now(),requested_start_ms:record.now(),duration_ms:wav.duration_ms,
            playback_active_at_start:player.sample().active,packets:[]};
          result.inputs.push(input);
          if (echo) {
            const mixedInput=echo.play(wav.pcm,input,() => player.sample().active);
            await waitFor(() => mixedInput.done,wav.duration_ms+5000,`Step ${index} echo-mixed input`);
            await waitUntil(mixedInput.sent_end_ms);
          } else {
            record('input_started',{step:index,file:step.file,role:input.role,playback_active:input.playback_active_at_start});
            for (let offset = 0; offset < wav.pcm.length; offset += 640) {
              const due = input.start_ms + offset / 32;
              await waitUntil(due);check();
              const packet = wav.pcm.subarray(offset,Math.min(offset+640,wav.pcm.length));
              send({type:'mic',pcm:btoa(String.fromCharCode(...packet))},false);
              input.packets.push([record.now(),packet.length,round(Math.max(0,record.now()-due))]);
            }
            await waitUntil(input.start_ms + wav.duration_ms);
          }
          input.end_ms = record.now();observations.last_input_end_ms = input.end_ms;
          record('input_ended',{step:index,file:step.file,role:input.role,packets:input.packets.length});
        }
        record('step_ended',{step:index});
      }
      record('tail_started',{duration_ms:fixture.tail_ms ?? 8000});
      await waitUntil(record.now() + (fixture.tail_ms ?? 8000));
      result.tail_end_ms=record.now();
      const drainMax=Math.max(0,Math.min(20000,fixture.post_tail_drain_ms ?? 20000));
      record('playback_drain_check',{max_ms:drainMax,settle_ms:2000,generation_pending:generation.pending,
        queue_ms:round(Math.max(0,player.end-player.outputTime())*1000)});
      result.playback_drain=await drainPlayback({isPlaying:() => player.playing,isGenerating:() => generation.pending,
        lastActivityMs:() => generation.last_activity_ms,now:record.now,wait:sleep,settleMs:2000,
        check:() => {check();if (receivedFatal || echo?.error) throw Error(receivedFatal || echo.error);},maxMs:drainMax});
      result.capture_truncated=result.playback_drain.timed_out || !result.playback_drain.settled;
      if (result.playback_drain.extended) record('playback_drain_finished',result.playback_drain);
      if (result.capture_truncated) {
        result.errors.push({phase:'capture',message:`Generation/playback did not finish and settle within the ${drainMax} ms post-tail drain`});
        record('playback_drain_timeout',{generation_pending:generation.pending,queue_ms:round(Math.max(0,player.end-player.outputTime())*1000)});
      }
      check();result.status = 'complete';
    } catch (error) {
      if (result.status !== 'unsupported') result.status = signal.aborted && signal.reason?.message === 'Stopped by user' ? 'aborted' : 'failed';
      result.errors.push({phase:'case',message:error.message || String(error)});
      record('case_error',{message:error.message || String(error)});
    } finally {
      clearTimeout(deadline);clearTimeout(sampleTimer);clearInterval(expressionTimer);
      closing = true;capturePng('last');
      echo?.stop();
      result.observation_end_ms = record.now();
      result.remaining = {queue_ms:player ? round(Math.max(0,player.end-player.outputTime())*1000) : null,
        playback_active:player?.sample()?.active ?? false,generation_pending:generation.pending,
        generation_completed_ms:generation.completed_ms,background_jobs:[...backgroundJobs.entries()]};
      result.capture_truncated ??= !!player?.playing || generation.pending;
      record('capture_boundary',{status:result.status,...result.remaining});
      player?.reset();ready = false;
      if (socket && socket.readyState !== WebSocket.CLOSED) {
        socket.close(1000,'Case finished');
        const end = performance.now()+5000;
        while (socket.readyState !== WebSocket.CLOSED && performance.now()<end) await sleep(20);
        if (socket.readyState !== WebSocket.CLOSED) result.errors.push({phase:'cleanup',message:'WebSocket close timed out'});
      }
      for (const recorder of recorders) {
        if (recorder.unavailable) {result.recording.push(recorder);continue;}
        try {recordings.push(await recorder.stop());}
        catch (error) {result.recording.push({kind:recorder.kind,error:error.message});}
      }
      recordingClock?.stop();
      for (const recording of recordings) {
        const {blob,...metadata} = recording;
        const format = blob.type.includes('mp4') ? 'mp4' : blob.type.includes('ogg') ? 'ogg' : 'webm';
        download(blob,`${fixture.id}.${recording.kind}.${format}`);
        try {
          const response = await fetchChecked(`/lab/audio?case=${encodeURIComponent(fixture.id)}&format=${format}&kind=${recording.kind}`,
            {method:'POST',headers:{'Content-Type':blob.type},body:blob});
          metadata.upload = await response.json();
        } catch (error) {metadata.upload_error = error.message;result.errors.push({phase:'upload',message:error.message});}
        result.recording.push(metadata);
        if (recording.error || !recording.bytes) result.errors.push({phase:'recording',message:recording.error || `${recording.kind} recording is empty`});
      }
      videoStreams.forEach(stream => stream.getVideoTracks().forEach(track => track.stop()));
      tee.stream.getTracks().forEach(track => track.stop());tee.disconnect();
      face?.destroy();
      document.removeEventListener('visibilitychange',onVisibility);context.removeEventListener('statechange',onContext);
      result.ended_at = new Date().toISOString();result.duration_ms = record.now();
      result.metrics = summarizeCapture(result);
      try {await post('/lab/result',result);result.uploaded = true;}
      catch (error) {result.uploaded = false;result.errors.push({phase:'result_upload',message:error.message});}
      download(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}),`${fixture.id}.browser.json`);
    }
    return result;
  }

  let map;
  async function run(ids) {
    if (running) throw Error('A benchmark run is already active');
    context ??= new AudioContext();
    await context.resume();
    if (context.state !== 'running') throw Error('AudioContext needs a click on the run button');
    const requested = Array.isArray(ids) ? ids : [ids || selected()];
    const cases = requested.map(id => state.fixtures.find(item => item.id === id));
    if (cases.some(item => !item)) throw Error('Unknown fixture ID');
    setRunning(true);state.status = 'running';window.labStatus = 'running';
    try {
      for (const fixture of cases) {
        const result = await runCase(fixture,map);state.results.push(result);
        $('results').textContent += `${fixture.id}: ${result.status}; ${result.metrics.playback_starts} playback starts; ${result.errors.length} errors; uploaded=${result.uploaded}\n`;
        if (result.status === 'aborted' || result.errors.some(error => error.phase === 'cleanup')) break;
      }
      state.status = state.results.slice(-cases.length).some(result => result.status !== 'complete' || !result.uploaded || result.errors.length) ? 'completed_with_errors' : 'complete';
      status(`Run ${state.status.replaceAll('_',' ')}`);
      return state.results;
    } finally {setRunning(false);controller = null;}
  }
  const launch = ids => {
    window.labPromise = run(ids);
    window.labPromise.catch(fail);
    return window.labPromise;
  };
  window.mistLab = {run:launch,stop:() => controller?.abort(Error('Stopped by user')),state,results:state.results};
  $('stop').onclick = window.mistLab.stop;
  $('run').onclick = () => launch([selected()]);
  $('run-all').onclick = () => launch(requestedIds.length ? requestedIds : state.fixtures.map(item => item.id));
  try {
    const setup = await (await post('/lab/setup',{})).json();
    state.fixtures = setup.fixtures;
    if (!Array.isArray(state.fixtures) || !state.fixtures.length) throw Error('No fixtures were returned');
    map = await (await fetchChecked('/face-map.json')).json();
    $('case').replaceChildren(...state.fixtures.map(fixture => new Option(fixture.id,fixture.id)));
    if (requestedIds.length) {
      if (requestedIds.some(id => !state.fixtures.some(fixture => fixture.id === id))) throw Error('URL contains an unknown fixture ID');
      $('case').value = requestedIds[0];$('run-all').textContent = `Run ${requestedIds.length} URL-selected cases`;
    }
    setRunning(false);state.status = 'ready';status(`${state.fixtures.length} fixtures ready`);
  } catch (error) {fail(error);}
}

if (typeof document !== 'undefined') installLab();
