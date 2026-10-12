# Streaming STT latency check

The real-time replay returned the complete expected words and produced a final transcript **0.373 seconds after the last PCM frame**. Partial text arrived **1.118 seconds after audio began**, while the 3.68-second clip was still being sent. This was a real Deepgram Nova-3 request through the new loopback WebSocket proxy, using a saved synthetic WAV rather than a microphone.

| Measurement | Result |
| --- | ---: |
| Saved PCM audio duration | 3.680 s |
| Format | 48 kHz, mono, signed PCM16 |
| Cold provider connection | 0.354 s |
| Local start through audio-ready acknowledgement | 0.359 s |
| Audio start to first partial | 1.118 s |
| Last audio frame to final transcript | 0.373 s |
| Total wall time, including the real-time audio replay | 4.413 s |
| Provider finalized audio coverage | 3.68000016 s |
| Confidence | 0.9995117 |

Expected and returned text were both: "Hello. I'm MIST. My wheels are ready, and I'm listening." Normalizing punctuation and case gives zero word errors across the ten reference words.

The earlier completed-WAV HTTP check took **6.390 seconds after its request began**, with the same expected phrase and a reported 3.68-second duration. The new 0.373-second measure starts after the streaming audio finishes. Recognition now overlaps speech capture; it no longer begins only after capture ends. These are different transport/settings trials, not repeated statistical estimates. The streaming trial used explicit local-VAD finalization and disabled smart formatting. It does not isolate the contribution of each setting.

## The failure that informed the implementation

The first additional probe rapidly uploaded a 3.67-second WAV over WebSocket and immediately sent `Finalize`. Deepgram returned a `from_finalize` segment covering only the first 0.8 seconds, then later interim segments. The implementation rejected that truncated eight-character result and timed out at 8.65 seconds. The failed trace is preserved in `streaming_stt_probe/results.jsonl`.

The successful path sends PCM at speaking cadence. The backend also accumulates finalized segments by timestamp and performs bounded draining until their duration covers the input. An early `from_finalize` flag alone cannot commit the utterance. Interim text is not promoted into a final answer after a timeout. The regression test reproduces an early partial final acknowledgement and verifies that the remaining final segment is included.

## Activated backend

The independent sidecar started successfully as PID **50852**, listening only on **127.0.0.1:8788**. The existing console process **50488** was not killed or restarted. Default allowed browser origins are the localhost variants on port 8776. The sidecar holds the Deepgram key, allows one browser connection, limits each utterance to 30 seconds and each session to 900 seconds, and rejects oversized frames.

The provider connection is retained between utterances and closed after 45 seconds of inactivity. Warm reuse was verified by local fake-provider tests; a second live warm utterance was not added after the allotted two audio probes. The measured successful provider connection above was cold.

Browser integration is owned separately by the Talk-mode work. It sends VAD-confirmed pre-roll and speech frames, buffers initial audio while waiting for the `started` acknowledgement, consumes partial/final events, and can fall back to the existing completed-WAV route. The sidecar alone does not capture a microphone or call the conversation model.

Metrics are written to `brain/results/mist-v2-browser-live/stt_streaming_metrics.jsonl`. They contain timing, duration, confidence, transcript length and generic errors; they omit transcripts, audio, headers and credentials. Sidecar startup logs and its PID are in that run's `stt-sidecar` directory.

## Scope and verification

The additional validation used **two audio submissions totaling 7.35 seconds**: the failed rapid-upload trial and the successful paced trial. Both used Nova-3. There were **zero LLM calls, zero TTS calls, and no ambient microphone capture**. Submitted audio duration is reported rather than an inferred invoice amount; account billing was not queried.

Six engine tests and seven fake-provider proxy tests pass. They cover segment accumulation, duplicate-segment handling, missing finalization flags, rejection of premature completion, timeout/cancellation isolation, origin and connection limits, malformed input, safe metrics and warm reuse. Browser capture and transport tests are maintained by the integration work.

This is streaming speech recognition feeding the existing conversation and speech components. It is not a native end-to-end full-duplex voice model. The 0.373-second figure excludes the configured local VAD pause, conversation-model latency and speech playback. Acoustic echo cancellation and real-microphone barge-in behavior are not established by a saved-audio replay.

Evidence: `streaming_stt_paced_probe/result.json`, the preserved first trial, and `deepgram_capture_check.json`. The successful source WAV SHA-256 is `57e4040d70f68a51bafc1ed0ae48448c4d78c088890ebf487e2682e2e0057c3c`.

Protocol references: [Deepgram streaming format](https://developers.deepgram.com/docs/determining-your-audio-format-for-live-streaming-audio), [segment and endpoint semantics](https://developers.deepgram.com/docs/understand-endpointing-interim-results), [Finalize](https://developers.deepgram.com/docs/finalize), [KeepAlive](https://developers.deepgram.com/docs/audio-keep-alive), and [smart-format delays](https://developers.deepgram.com/docs/smart-format).
