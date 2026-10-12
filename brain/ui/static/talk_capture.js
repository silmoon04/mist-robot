/* Local microphone capture, utterance boundaries, and complete PCM WAV clips. */
(function(root) {
  'use strict';

  const defaults = Object.freeze({
    preRollMs: 200, silenceMs: 650, minSpeechMs: 250, maxDurationMs: 20000,
    startMs: 90, bargeInMs: 220, startRms: 0.012, stopRms: 0.007,
    bargeInRms: 0.03, initialNoiseFloor: 0.003
  });
  let utteranceSequence = 0;
  const utterancePrefix = Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);

  function encodeWav(samples, sampleRate) {
    const bytes = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(bytes);
    const word = (offset, value) => {
      for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i));
    };
    word(0, 'RIFF'); view.setUint32(4, bytes.byteLength - 8, true); word(8, 'WAVE');
    word(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
    view.setUint16(22, 1, true); view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); view.setUint16(32, 2, true);
    view.setUint16(34, 16, true); word(36, 'data');
    view.setUint32(40, samples.length * 2, true);
    for (let i = 0; i < samples.length; i++) {
      const value = Number.isFinite(samples[i]) ? Math.max(-1, Math.min(1, samples[i])) : 0;
      view.setInt16(44 + i * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
    }
    return new root.Blob([bytes], {type: 'audio/wav'});
  }

  function createDetector({sampleRate, onUtterance = () => {}, onSpeechStart = () => {},
                           onActivity = () => {}, onStreamStart, onStreamData, onStreamEnd,
                           onStreamCancel, onStreamError = () => {}, config = {}}) {
    if (!Number.isFinite(sampleRate) || sampleRate < 8000 || sampleRate > 192000) {
      throw new Error('Unsupported microphone sample rate.');
    }
    const options = {...defaults, ...config};
    const count = milliseconds => Math.round(milliseconds * sampleRate / 1000);
    const frameSize = count(10), preRollLimit = count(options.preRollMs);
    const maxSamples = count(options.maxDurationMs), minSpeech = count(options.minSpeechMs);
    let frame = new Float32Array(frameSize), frameOffset = 0, framePlayback = false;
    let history = [], historySamples = 0, candidate = null, blocked = false;
    let noiseFloor = options.initialNoiseFloor, revision = 0;
    const streaming = [onStreamStart, onStreamData, onStreamEnd, onStreamCancel].some(value => typeof value === 'function');

    function metadataFor(value, reason) {
      return {utteranceId: value.utteranceId, sampleRate,
        durationMs: value.totalSamples * 1000 / sampleRate,
        speechMs: value.speechSamples * 1000 / sampleRate,
        preRollMs: value.preRollSamples * 1000 / sampleRate,
        trailingSilenceMs: value.silenceSamples * 1000 / sampleRate,
        bargeIn: value.bargeIn, ...(reason ? {reason} : {})};
    }
    function reportStreamError(error) {
      try { onStreamError(error); } catch (_) {}
    }
    function cancelStream(value, reason) {
      if (!value?.streamStarted || value.streamClosed) return;
      value.streamClosed = true;
      try { onStreamCancel?.(metadataFor(value, reason)); }
      catch (error) { reportStreamError(error); }
    }
    function streamAvailable(value, mine) {
      return candidate === value && revision === mine && !blocked && !value.streamClosed;
    }
    function streamFrames(value) {
      if (!streaming || value.streamClosed || value.streamPumping) return;
      const mine = revision;
      value.streamPumping = true;
      try {
        if (!value.streamStarted) {
          value.streamStarted = true;
          onStreamStart?.(metadataFor(value));
        }
        const available = value.chunks.length;
        while (streamAvailable(value, mine) && value.streamIndex < available) {
          // Copies let a transport transfer its buffer without damaging the fallback WAV.
          const samples = value.chunks[value.streamIndex++].slice();
          onStreamData?.(samples, {sampleRate, utteranceId: value.utteranceId});
        }
      } catch (error) {
        cancelStream(value, 'callback-error');
        reportStreamError(error);
      } finally { value.streamPumping = false; }
    }

    function remember(samples) {
      history.push(samples);
      historySamples += samples.length;
      while (historySamples > preRollLimit && history.length) {
        const extra = historySamples - preRollLimit;
        if (history[0].length <= extra) historySamples -= history.shift().length;
        else { history[0] = history[0].slice(extra); historySamples -= extra; }
      }
    }
    function clearCandidate(reason = 'reset', notify = true) {
      const previous = candidate;
      candidate = null;
      history = []; historySamples = 0;
      cancelStream(previous, reason);
      if (previous?.confirmed && notify) onActivity(false);
    }
    function finish(reason) {
      const completed = candidate, mine = revision;
      onActivity(false);
      if (candidate !== completed || revision !== mine || blocked) return;
      if (completed.speechSamples < minSpeech) { clearCandidate('too-short', false); return; }
      const metadata = metadataFor(completed, reason);
      if (completed.streamStarted && !completed.streamClosed) {
        completed.streamClosed = true;
        try { onStreamEnd?.(metadataFor(completed, reason)); }
        catch (error) { reportStreamError(error); }
        if (candidate !== completed || revision !== mine || blocked) return;
      }
      clearCandidate('finished', false);
      const samples = new Float32Array(completed.totalSamples);
      let offset = 0;
      for (const chunk of completed.chunks) { samples.set(chunk, offset); offset += chunk.length; }
      onUtterance({samples, metadata});
    }
    function process(samples, playback) {
      if (blocked) return;
      let sum = 0;
      for (const value of samples) sum += value * value;
      const rms = Math.sqrt(sum / samples.length);
      const bargeIn = playback || !!candidate?.bargeIn;
      const startThreshold = Math.max(bargeIn ? options.bargeInRms : options.startRms,
        noiseFloor * (bargeIn ? 6 : 3.5));

      if (!candidate) {
        if (rms < startThreshold) {
          // Learn quiet surroundings. Playback and candidate speech cannot raise the floor.
          if (!playback) {
            const rate = rms < noiseFloor ? 0.05 : 0.01;
            noiseFloor = Math.max(0.0005, Math.min(0.02, noiseFloor + rate * (rms - noiseFloor)));
          }
          remember(samples);
          return;
        }
        candidate = {chunks: history, totalSamples: historySamples, preRollSamples: historySamples,
          speechSamples: 0, confirmationSamples: 0, silenceSamples: 0, confirmed: false, bargeIn,
          streamStarted: false, streamClosed: false, streamIndex: 0, streamPumping: false};
        history = []; historySamples = 0;
      }

      if (playback && !candidate.bargeIn && !candidate.confirmed) {
        candidate.bargeIn = true;
        candidate.confirmationSamples = 0;
      }
      if (!candidate.confirmed && rms < startThreshold) {
        const abandoned = candidate.chunks;
        clearCandidate();
        for (const chunk of abandoned) remember(chunk);
        remember(samples);
        return;
      }

      const retained = samples.subarray(0, Math.min(samples.length, maxSamples - candidate.totalSamples));
      candidate.chunks.push(retained);
      candidate.totalSamples += retained.length;
      const stopThreshold = Math.max(options.stopRms, noiseFloor * 2);
      if (rms >= (candidate.confirmed ? stopThreshold : startThreshold)) {
        candidate.speechSamples += retained.length;
        candidate.confirmationSamples += retained.length;
        candidate.silenceSamples = 0;
      } else candidate.silenceSamples += retained.length;

      if (!candidate.confirmed && candidate.confirmationSamples >= count(candidate.bargeIn ? options.bargeInMs : options.startMs)) {
        const confirmed = candidate, mine = revision;
        candidate.confirmed = true;
        candidate.utteranceId = 'talk-' + utterancePrefix + '-' + (++utteranceSequence);
        onActivity(true);
        if (candidate !== confirmed || revision !== mine || blocked) return;
        onSpeechStart({utteranceId: candidate.utteranceId, bargeIn: candidate.bargeIn, sampleRate, noiseFloor,
          thresholdRms: startThreshold, confirmationMs: candidate.confirmationSamples * 1000 / sampleRate});
        if (candidate !== confirmed || revision !== mine || blocked) return;
      }
      const active = candidate, mine = revision;
      if (candidate.confirmed) streamFrames(candidate);
      if (candidate !== active || revision !== mine || blocked) return;
      if (candidate.totalSamples >= maxSamples) finish('max-duration');
      else if (candidate.silenceSamples >= count(options.silenceMs)) finish('silence');
    }
    function push(samples, playback = false) {
      if (blocked || !samples?.length) return;
      const mine = revision;
      for (let offset = 0; offset < samples.length;) {
        if (blocked || revision !== mine) break;
        const size = Math.min(samples.length - offset, frameSize - frameOffset);
        for (let i = 0; i < size; i++) {
          const value = samples[offset + i];
          frame[frameOffset + i] = Number.isFinite(value) ? value : 0;
        }
        frameOffset += size; offset += size; framePlayback = framePlayback || playback;
        if (frameOffset === frameSize) {
          const completed = frame, wasPlayback = framePlayback;
          frame = new Float32Array(frameSize); frameOffset = 0; framePlayback = false;
          process(completed, wasPlayback);
        }
      }
    }
    function reset(reason = 'reset') {
      revision++;
      frame = new Float32Array(frameSize); frameOffset = 0; framePlayback = false;
      clearCandidate(reason);
    }
    return {push, reset, setBlocked(value, reason = 'blocked') { blocked = !!value; reset(reason); },
      getState: () => ({speaking: !!candidate?.confirmed, noiseFloor, blocked})};
  }

  function create({onUtterance = async () => {}, onSpeechStart = () => {}, onState = () => {},
                   onError = () => {}, isPlaybackActive = () => false, getUserMedia,
                   onStreamStart, onStreamData, onStreamEnd, onStreamCancel,
                   audioContextFactory, workletUrl = '/static/talk_capture_worklet.js', config = {}} = {}) {
    let current = null, status = 'idle', delivery = null;
    const supportedSetting = (session, key) => {
      const value = session?.settings?.[key];
      return typeof value === 'boolean' ? value : null;
    };
    function getState() {
      return {status, active: !!current?.ready, pending: !!current?.pending,
        sampleRate: current?.context?.sampleRate ?? null,
        noiseFloor: current?.detector?.getState().noiseFloor ?? defaults.initialNoiseFloor,
        echoCancellation: supportedSetting(current, 'echoCancellation'),
        noiseSuppression: supportedSetting(current, 'noiseSuppression'),
        autoGainControl: supportedSetting(current, 'autoGainControl')};
    }
    function emit(next) { status = next; onState(getState()); }
    function stopTracks(stream) {
      for (const track of stream?.getTracks?.() ?? []) {
        try { track.stop(); } catch (_) {}
      }
    }
    function release(session) {
      if (session.closed) return session.cleanup ?? Promise.resolve();
      session.closed = true;
      session.abort.abort();
      session.detector?.setBlocked(true, 'stopped');
      if (session.node) {
        session.node.port.onmessage = null;
        session.node.onprocessorerror = null;
        try { session.node.port.postMessage({type: 'stop'}); } catch (_) {}
        try { session.node.port.close(); } catch (_) {}
      }
      for (const [track, ended] of session.trackListeners) track.removeEventListener?.('ended', ended);
      for (const node of [session.source, session.node, session.sink]) {
        try { node?.disconnect(); } catch (_) {}
      }
      stopTracks(session.stream);
      try { session.cleanup = Promise.resolve(session.context?.close()).catch(() => {}); }
      catch (_) { session.cleanup = Promise.resolve(); }
      return session.cleanup;
    }
    async function stop() {
      const previous = current;
      current = null;
      emit('idle');
      if (previous) await release(previous);
    }
    function fail(session, error) {
      if (current !== session) return release(session);
      current = null;
      emit('error');
      onError(error instanceof Error ? error : new Error(String(error)));
      return release(session);
    }
    async function deliver(session, value) {
      if (current !== session || delivery) return;
      const mine = {};
      delivery = mine;
      session.pending = true;
      try {
        session.detector.setBlocked(true);
        emit('processing');
        if (current !== session || session.abort.signal.aborted) return;
        const metadata = {...value.metadata, signal: session.abort.signal,
          echoCancellation: supportedSetting(session, 'echoCancellation')};
        await onUtterance(encodeWav(value.samples, value.metadata.sampleRate), metadata);
      } catch (error) {
        if (current === session && !session.abort.signal.aborted) onError(error);
      } finally {
        session.pending = false;
        if (delivery === mine) {
          delivery = null;
          if (current) {
            current.pending = false;
            current.detector?.setBlocked(false);
            if (current.ready) emit('listening');
          }
        }
      }
    }
    async function activate(session) {
      try {
        if (current !== session || session.closed) return false;
        const media = getUserMedia ?? root.navigator?.mediaDevices?.getUserMedia?.bind(root.navigator.mediaDevices);
        const Context = root.AudioContext || root.webkitAudioContext;
        if (!media || (!audioContextFactory && !Context) || !root.AudioWorkletNode) {
          throw new Error('Talk needs microphone access and AudioWorklet support in this browser.');
        }
        session.context = audioContextFactory ? audioContextFactory() : new Context({latencyHint: 'interactive'});
        if (!session.context.audioWorklet) throw new Error('AudioWorklet is unavailable. Open MIST on localhost or HTTPS.');
        const resumed = session.context.resume();
        const streamReady = Promise.resolve(media({audio: {channelCount: 1, echoCancellation: true,
          noiseSuppression: true, autoGainControl: true}, video: false})).then(stream => {
          if (current !== session || session.closed) { stopTracks(stream); return; }
          session.stream = stream;
          for (const track of stream.getTracks()) {
            const ended = () => { void fail(session, new Error('The microphone disconnected. Start Talk to reconnect.')); };
            track.addEventListener?.('ended', ended);
            session.trackListeners.push([track, ended]);
          }
          session.settings = stream.getAudioTracks?.()[0]?.getSettings?.() ?? {};
        });
        await Promise.all([resumed, streamReady]);
        if (current !== session || session.closed) { await release(session); return false; }
        await session.context.audioWorklet.addModule(workletUrl);
        if (current !== session || session.closed) { await release(session); return false; }
        session.detector = createDetector({sampleRate: session.context.sampleRate, config,
          onActivity: speaking => { if (current === session && !session.pending) emit(speaking ? 'speaking' : 'listening'); },
          onSpeechStart: metadata => { if (current === session) onSpeechStart(metadata); },
          onStreamStart: onStreamStart && (metadata => { if (current === session) onStreamStart({...metadata,
            signal: session.abort.signal, echoCancellation: supportedSetting(session, 'echoCancellation')}); }),
          onStreamData: onStreamData && ((samples, metadata) => { if (current === session) onStreamData(samples, metadata); }),
          onStreamEnd: onStreamEnd && (metadata => { if (current === session) onStreamEnd({...metadata,
            signal: session.abort.signal, echoCancellation: supportedSetting(session, 'echoCancellation')}); }),
          onStreamCancel: onStreamCancel && (metadata => onStreamCancel({...metadata,
            signal: session.abort.signal, echoCancellation: supportedSetting(session, 'echoCancellation')})),
          onStreamError: error => { if (current === session) onError(error); },
          onUtterance: value => { void deliver(session, value); }});
        session.pending = !!delivery;
        session.detector.setBlocked(session.pending);
        session.source = session.context.createMediaStreamSource(session.stream);
        session.node = new root.AudioWorkletNode(session.context, 'mist-talk-capture', {
          numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1], channelCount: 1,
          channelCountMode: 'explicit', processorOptions: {batchMs: 20}
        });
        session.node.onprocessorerror = () => { void fail(session, new Error('Microphone processing stopped. Start Talk to retry.')); };
        session.node.port.onmessage = event => {
          if (current !== session || !session.ready || session.pending) return;
          if (event.data?.type === 'pcm') session.detector.push(event.data.samples, !!isPlaybackActive());
        };
        session.sink = session.context.createGain();
        session.sink.gain.value = 0;
        session.source.connect(session.node);
        session.node.connect(session.sink);
        session.sink.connect(session.context.destination);
        session.ready = true;
        emit(session.pending ? 'processing' : 'listening');
        return true;
      } catch (error) {
        if (current === session) await fail(session, error);
        else await release(session);
        return false;
      }
    }
    function start() {
      if (current) return current.startPromise ?? Promise.resolve(current.ready);
      const session = {abort: new root.AbortController(), trackListeners: [], ready: false, pending: false, closed: false};
      current = session;
      emit('starting');
      session.startPromise = activate(session);
      return session.startPromise;
    }
    return {start, stop, getState};
  }

  root.MistTalkCapture = {create, createDetector, encodeWav, defaults};
  if (typeof module !== 'undefined' && module.exports) module.exports = root.MistTalkCapture;
})(typeof window !== 'undefined' ? window : globalThis);
