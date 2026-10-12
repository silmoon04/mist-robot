# Streaming speech recognition

Talk mode can send speech to a separate loopback WebSocket service while the person is speaking. The service keeps the Deepgram credential on the server and forwards mono PCM16 audio to Nova-3. It supplies partial text during recognition and one final result after the existing local VAD ends the utterance. This is a streaming transcription path, not a native end-to-end speech model.

`ui/streaming_stt.py` provides `WarmDeepgramSTT`. `begin_utterance(sample_rate, on_event=...)` opens or reuses an upstream connection; `send_pcm(bytes)` accepts ordered signed 16-bit little-endian mono PCM; `finalize()` drains final transcript segments; `cancel()` discards an unfinished utterance. The sample-rate parameter must describe the actual samples. The client must not relabel 48 kHz data as 16 kHz or prepend WAV headers to raw chunks.

Normal `ui/server.py` startup now manages the local proxy in `ui/stt_proxy.py` within the same Python process. The default console and proxy ports are 8776 and 8788, both on loopback. `--port` and `--stt-port` set a different pair; the allowed origins derive from the actual console port, and `/api/config` advertises the proxy URL. Only one browser can own recognition at a time. The proxy limits frame size, utterance duration and session duration. The permanent Deepgram key is never returned to the browser.

```powershell
python ui/server.py --port 8776 --stt-port 8788 --run-dir results/mist-v2-browser-live
```

The streaming dependency is pinned in `ui/requirements-stt.txt` to the validated `websockets` 13.1 API. Install it in the console's Python environment with `python -m pip install -r ui/requirements-stt.txt` when it is not already present. `--stt-mode off` remains available without the streaming dependency.

The managed launcher reserves both ports before constructing the model client or starting queued jobs. A conflict or startup failure releases its own reservations and leaves existing services alone. Windows HTTP binding uses exclusive ownership to prevent a second console from sharing a listener. The recognition engine is created only when an allowed browser connects; its provider connection remains lazy until speech begins.

Ctrl+C closes managed recognition and the console together. Shutdown rejects new connections and prevents an engine still being constructed from publishing a session afterward. The runtime closes only its own sockets, browser streams, background worker and model client. `--stt-mode external` explicitly uses a separately launched proxy without taking ownership; `--stt-mode off` disables streaming and retains batch recognition. Stub and watch launches default to off.

The separate `python ui/stt_proxy.py` entry point remains available. Pair it with `--stt-mode external` on the console, and pass matching `--origin` values when using a non-default console port. The running processes present before this lifecycle change remain separate and have not been restarted by this update.

The browser sends a `start` message containing `utterance_id` and `sample_rate`, then ordered binary PCM frames, then `end` with the same ID. The proxy acknowledges `started`, emits `partial` messages, and returns `final` only after a finalized result timestamp reaches the submitted audio's end. `cancel` and connection close discard pending work. IDs prevent delayed results from entering a later utterance. A finalized provider segment is not necessarily a finalized user utterance.

The AudioWorklet capture path retains its existing VAD and pre-roll. Streaming callbacks start only after speech is confirmed, and send the buffered pre-roll once before continuing with live frames. Idle microphone frames are not uploaded. The browser buffers a bounded amount of initial audio while the provider connection is opening, then preserves its order. Existing complete-WAV recognition remains the fallback when streaming is unavailable.

Deepgram is configured with interim results, `smart_format=false`, punctuation, and explicit `Finalize` messages. Local VAD owns the boundary, so another provider pause detector or one-second utterance-gap wait is not added. Smart formatting can delay results while waiting for an incomplete entity; disabling it removes that potential wait. [Deepgram formatting documentation](https://developers.deepgram.com/docs/smart-format)

`Finalize` is not treated as an unconditional acknowledgement of all audio sent. A saved-clip test produced a `from_finalize` result covering only the first 0.8 seconds of a 3.67-second upload. The backend rejected the truncated transcript. It accumulates finalized segments by timestamp and uses bounded draining until their latest end reaches the submitted audio's end; interim text is never silently promoted into a final answer. This timing check does not establish that every word was recognized correctly. [Deepgram finalization documentation](https://developers.deepgram.com/docs/finalize)

The provider connection is reused between utterances and receives KeepAlive messages during short gaps. It opens when an utterance starts rather than maintaining an indefinitely idle preconnection before any audio exists. The backend closes idle upstream connections after 45 seconds and reconnects for later speech. Audio timestamps count audio samples, not wall time during gaps. [Deepgram KeepAlive documentation](https://developers.deepgram.com/docs/audio-keep-alive)

Use `python harness/test_streaming_stt.py`, `python harness/test_stt_proxy.py` and `python harness/test_service_lifecycle.py` for local fixtures without audio-provider calls. The lifecycle suite uses ephemeral ports and fake engines to check startup failure, exclusive ownership, matched origins, lazy construction and clean shutdown. `harness/probe_streaming_stt.py` replays a supplied saved WAV through the proxy at real-time cadence and makes one real transcription submission. It does not capture a microphone or call a language model or text-to-speech service.
