/* Optional PCM streaming transport. Capture owns microphone access and VAD. */
(function(root) {
  'use strict';

  const packetMs = 100, maxAudioMs = 20000, connectTimeoutMs = 1000;
  const startTimeoutMs = 3000, resultTimeoutMs = 8000;
  const rates = new Set([8000, 16000, 22050, 24000, 32000, 44100, 48000]);
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  function create({url = 'ws://127.0.0.1:8788/stt', onPartial = () => {}, onStatus = () => {},
                   socketFactory = address => new root.WebSocket(address),
                   uuidFactory = () => root.crypto?.randomUUID?.()} = {}) {
    let current = null, connection = null, epoch = 0;
    const now = () => root.performance?.now?.() ?? Date.now();
    const live = run => current === run && !run.settled && run.epoch === epoch;
    const matches = (run, meta) => !!run && meta?.utteranceId === run.id;
    const observe = (callback, value) => { try { callback(value); } catch (_) {} };
    function status(run, value, details = {}) {
      observe(onStatus, {status: value, utteranceId: run?.id ?? null, ...details});
    }
    function clearTimer(owner, key) {
      if (owner[key] !== null) root.clearTimeout(owner[key]);
      owner[key] = null;
    }
    function closeConnection(conn) {
      if (!conn) return;
      if (connection === conn) connection = null;
      clearTimer(conn, 'timer');
      conn.socket.onopen = conn.socket.onmessage = conn.socket.onerror = conn.socket.onclose = null;
      try { conn.socket.close(); } catch (_) {}
    }
    function clearSignals(run, keepCapture = false) {
      run.signals = run.signals.filter(([signal, listener]) => {
        if (keepCapture && signal === run.captureSignal) return true;
        signal.removeEventListener('abort', listener);
        return false;
      });
    }
    function settle(run, value, state, reason, cancelWire = false) {
      if (!live(run)) return;
      run.settled = true;
      epoch++;
      for (const key of ['startTimer', 'pumpTimer', 'resultTimer']) clearTimer(run, key);
      clearSignals(run, value !== null);
      run.queue = []; run.queuedSamples = 0; run.headOffset = 0;
      if (cancelWire) {
        if (run.startSent && run.connection?.socket.readyState === 1) {
          try { run.connection.socket.send(JSON.stringify({type: 'cancel', utterance_id: run.wireId})); }
          catch (_) {}
        }
        closeConnection(run.connection);
      }
      run.resolve(value);
      status(run, state, reason ? {reason} : {});
    }
    function fail(run, reason) { settle(run, null, 'fallback', reason, true); }
    function bindSignal(run, signal) {
      if (!signal || !live(run)) return;
      if (signal.aborted) { settle(run, null, 'cancelled', 'aborted', true); return; }
      if (run.signals.some(([existing]) => existing === signal)) return;
      const listener = () => {
        if (current === run && run.settled) stop();
        else settle(run, null, 'cancelled', 'aborted', true);
      };
      run.signals.push([signal, listener]);
      signal.addEventListener('abort', listener, {once: true});
    }
    function schedulePump(run, delay = 0) {
      if (!live(run) || !run.acknowledged || run.pumpTimer !== null) return;
      run.pumpTimer = root.setTimeout(() => {
        run.pumpTimer = null;
        pump(run);
      }, delay);
    }
    function takePacket(run, samples) {
      const packet = new Uint8Array(samples * 2);
      let offset = 0;
      while (offset < packet.length) {
        const head = run.queue[0];
        const count = Math.min(head.length - run.headOffset, packet.length - offset);
        packet.set(head.subarray(run.headOffset, run.headOffset + count), offset);
        offset += count; run.headOffset += count;
        if (run.headOffset === head.length) { run.queue.shift(); run.headOffset = 0; }
      }
      run.queuedSamples -= samples;
      return packet.buffer;
    }
    function sendEnd(run) {
      if (!live(run) || run.endSent || !run.ended || run.queuedSamples) return;
      if (run.connection.socket.bufferedAmount > 0) { schedulePump(run, 50); return; }
      run.endSent = true;
      try { run.connection.socket.send(JSON.stringify({type: 'end', utterance_id: run.wireId})); }
      catch (_) { fail(run, 'send-failed'); return; }
      if (live(run)) status(run, 'waiting');
    }
    function pump(run) {
      if (!live(run) || !run.acknowledged || run.endSent) return;
      const socket = run.connection.socket;
      if (connection !== run.connection || socket.readyState !== 1) { fail(run, 'connection-closed'); return; }
      if (socket.bufferedAmount > run.sampleRate) { fail(run, 'backpressure'); return; }
      if (!run.queuedSamples) { sendEnd(run); return; }
      if (run.queuedSamples < run.packetSamples && !run.ended) return;
      const delay = run.nextSendAt - now();
      if (delay > 0) { schedulePump(run, delay); return; }
      if (socket.bufferedAmount > run.packetSamples * 4) { schedulePump(run, 50); return; }
      const samples = Math.min(run.packetSamples, run.queuedSamples);
      const packet = takePacket(run, samples);
      try { socket.send(packet); }
      catch (_) { fail(run, 'send-failed'); return; }
      if (!live(run)) return;
      // Schedule from the actual send time so a delayed timer cannot cause a burst.
      run.nextSendAt = now() + samples * 1000 / run.sampleRate;
      if (run.queuedSamples) schedulePump(run, run.nextSendAt - now());
      else sendEnd(run);
    }
    function begin(run) {
      if (!live(run) || run.startSent || run.connection.socket.readyState !== 1) return;
      run.startSent = true;
      run.startTimer = root.setTimeout(() => fail(run, 'start-timeout'), startTimeoutMs);
      try {
        run.connection.socket.send(JSON.stringify({type: 'start', utterance_id: run.wireId,
          sample_rate: run.sampleRate}));
      } catch (_) { fail(run, 'send-failed'); return; }
      if (live(run) && !run.acknowledged) status(run, 'starting');
    }
    function receive(conn, event) {
      const run = current;
      if (connection !== conn || !run || !live(run) || run.connection !== conn) return;
      let message;
      try { message = JSON.parse(event.data); }
      catch (_) { fail(run, 'invalid-response'); return; }
      if (!message || message.utterance_id !== run.wireId) return;
      if (message.type === 'started') {
        if (!run.startSent || run.acknowledged) return;
        if (message.sample_rate !== undefined && message.sample_rate !== run.sampleRate) {
          fail(run, 'sample-rate-mismatch'); return;
        }
        clearTimer(run, 'startTimer');
        run.acknowledged = true;
        status(run, 'streaming');
        schedulePump(run);
      } else if (message.type === 'partial') {
        if (run.acknowledged && typeof message.text === 'string') {
          observe(onPartial, {utteranceId: run.id, text: message.text});
        }
      } else if (message.type === 'final') {
        if (!run.endSent) return;
        if (typeof message.transcript !== 'string') { fail(run, 'invalid-response'); return; }
        const confidence = Number.isFinite(message.confidence) && message.confidence >= 0 &&
          message.confidence <= 1 ? message.confidence : null;
        settle(run, {...message, transcript: message.transcript.trim(), confidence,
          utteranceId: run.id}, 'complete');
      } else if (message.type === 'error') fail(run, 'service-error');
      else if (message.type === 'cancelled') settle(run, null, 'cancelled', 'service-cancelled', true);
    }
    function connect(run) {
      let conn = connection;
      if (conn && conn.socket.readyState !== 1) { closeConnection(conn); conn = null; }
      if (!conn) {
        let socket;
        try { socket = socketFactory(url); }
        catch (_) { fail(run, 'service-unavailable'); return; }
        conn = {socket, timer: null};
        connection = conn;
        run.connection = conn;
        socket.binaryType = 'arraybuffer';
        socket.onopen = () => {
          if (connection !== conn) return;
          clearTimer(conn, 'timer');
          if (current?.connection === conn) begin(current);
        };
        socket.onmessage = event => receive(conn, event);
        socket.onerror = () => {
          if (connection !== conn) return;
          if (current?.connection === conn && live(current)) fail(current, 'service-unavailable');
          else closeConnection(conn);
        };
        socket.onclose = () => {
          if (connection !== conn) return;
          if (current?.connection === conn && live(current)) fail(current, 'connection-closed');
          else closeConnection(conn);
        };
        if (socket.readyState !== 1) {
          conn.timer = root.setTimeout(() => {
            if (connection !== conn) return;
            if (current?.connection === conn && live(current)) fail(current, 'service-unavailable');
            else closeConnection(conn);
          }, connectTimeoutMs);
        }
      }
      run.connection = conn;
      begin(run);
    }
    function start(meta = {}) {
      const previous = current;
      if (previous && live(previous)) {
        settle(previous, null, 'cancelled', 'replaced', true);
        if (current !== previous) return false;
      }
      if (previous) clearSignals(previous);
      let wireId;
      try { wireId = uuidFactory(); } catch (_) {}
      const run = {id: meta.utteranceId, wireId, sampleRate: meta.sampleRate, epoch: ++epoch,
        connection, captureSignal: meta.signal, settled: false, acknowledged: false, startSent: false,
        ended: false, endSent: false, queue: [], queuedSamples: 0, acceptedSamples: 0, headOffset: 0,
        packetSamples: Math.round(meta.sampleRate * packetMs / 1000), nextSendAt: 0,
        signals: [], startTimer: null, pumpTimer: null, resultTimer: null};
      run.promise = new Promise(resolve => { run.resolve = resolve; });
      current = run;
      if (typeof run.id !== 'string' || !run.id.length || run.id.length > 256) {
        fail(run, 'invalid-utterance-id'); return false;
      }
      if (typeof wireId !== 'string' || !uuidPattern.test(wireId)) {
        fail(run, 'uuid-unavailable'); return false;
      }
      if (!rates.has(run.sampleRate)) { fail(run, 'unsupported-sample-rate'); return false; }
      bindSignal(run, meta.signal);
      if (!live(run)) return false;
      status(run, 'connecting');
      if (live(run)) connect(run);
      return live(run);
    }
    function push(samples, meta = {}) {
      const run = current;
      if (!matches(run, meta) || !live(run) || run.ended) return false;
      if (meta.sampleRate !== run.sampleRate) { fail(run, 'sample-rate-changed'); return false; }
      if (Object.prototype.toString.call(samples) !== '[object Float32Array]') {
        fail(run, 'invalid-audio'); return false;
      }
      if (run.acceptedSamples + samples.length > run.sampleRate * maxAudioMs / 1000) {
        fail(run, 'audio-too-long'); return false;
      }
      if (!samples.length) return true;
      const bytes = new ArrayBuffer(samples.length * 2), view = new DataView(bytes);
      for (let i = 0; i < samples.length; i++) {
        const value = Number.isFinite(samples[i]) ? Math.max(-1, Math.min(1, samples[i])) : 0;
        view.setInt16(i * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
      }
      run.queue.push(new Uint8Array(bytes));
      run.queuedSamples += samples.length;
      run.acceptedSamples += samples.length;
      schedulePump(run);
      return true;
    }
    function end(meta = {}) {
      const run = current;
      if (!matches(run, meta) || !live(run)) return false;
      bindSignal(run, meta.signal);
      if (!live(run)) return false;
      if (run.ended) return true;
      run.ended = true;
      run.resultTimer = root.setTimeout(() => fail(run, 'result-timeout'), resultTimeoutMs);
      if (!run.acceptedSamples) { fail(run, 'empty-audio'); return false; }
      status(run, 'draining');
      schedulePump(run);
      return live(run);
    }
    function result(meta = {}) {
      const run = current;
      if (!matches(run, meta)) return Promise.resolve(null);
      if (meta.signal?.aborted || run.captureSignal?.aborted) {
        if (run.settled) stop();
        else settle(run, null, 'cancelled', 'aborted', true);
        return Promise.resolve(null);
      }
      bindSignal(run, meta.signal);
      if (live(run) && !run.ended) end(meta);
      return run.promise;
    }
    function cancel(meta = {}) {
      const run = current;
      if (!run || (meta.utteranceId !== undefined && !matches(run, meta))) return false;
      if (run.settled) {
        clearSignals(run);
        closeConnection(run.connection);
        current = null;
        epoch++;
        status(run, 'cancelled', {reason: 'cancelled'});
        return true;
      }
      settle(run, null, 'cancelled', 'cancelled', true);
      return true;
    }
    function stop() {
      const run = current;
      if (run && live(run)) {
        settle(run, null, 'stopped', 'stopped', true);
        if (current === run) current = null;
      }
      else {
        epoch++;
        closeConnection(connection);
        if (run) clearSignals(run);
        current = null;
        status(run, 'stopped');
      }
    }
    return {start, push, end, cancel, result, stop};
  }

  root.MistSTTStream = Object.freeze({create});
})(typeof globalThis !== 'undefined' ? globalThis : this);
