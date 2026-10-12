# Voice connection and latency fix

The user's failure was reproduced on the native voice path: ClientConnectorError occurred while opening an ElevenLabs connection, before any audio was received for that segment. The previous implementation converted that brief transport error into a fatal mute for the whole conversation. The exact same user-visible failure also appeared in the new regression test before the fix.

The fixed path retries before any segment audio has been emitted, using a fresh multipart request body each time. It never retries already played audio. Retries, queueing and transfer share a bounded deadline. If recovery fails, that reply is cleared while native conversation remains available; account and voice-access errors are reported explicitly.

## Verified results

- Nine turns of the user's greeting/today/expression sequence completed without converter shutdowns.
- 2 real connection failures during that replay recovered on retry.
- Three additional turns with the faster startup completed without warnings, and the expression tool still worked.
- Six recovery regressions and the existing twenty-nine Python contracts passed. Browser playback/cancellation/caption-start checks passed.
- Interruption followed the corrected request with no stale-generation audio packets.
- Native connection readiness changed from 19.08 seconds with automatic startup context to 1.87 and 1.41 seconds without it. MIST already provides its own prompt and tool setup; the backing model is unchanged.
- An identical-input, identical-provider-fixture comparison measured 390 ms earlier first audio, from 0.922 to 0.532 seconds. This isolates the buffer change and is not an internet latency guarantee.

The first native-audio segment is now 400 ms instead of 800 ms. Following segments remain up to 1.2 seconds. Browser playout lead-in is 25 ms instead of 45 ms. The overlay waits for playback; the detailed transcript still appears immediately. Caption gating is separate from the actual buffering improvement.

Metadata-only diagnostics are saved in the running server's run directory as voice_diagnostics.jsonl. They contain phases, retry counts, exception classes and timing, without microphone audio, transcript text or credentials.

## Practical limits

- The exact underlying internet connection failure is not determined. The failure boundary and incorrect fatal handling were reproduced.
- A retry or slow provider can still delay a reply. A persistent outage can still interrupt audio.
- Live response timings vary with generated phrasing and tool execution; the controlled 400 ms buffer comparison isolates the code improvement.
- Expression requests still wait for backing-tool work; they are not guaranteed to speak immediately.
- Captions are gated to audio start, not word-aligned forced transcription.
- Tests used synthetic microphone input, not a physical handset or room-echo measurement.

The normal interface remains at http://127.0.0.1:8790/. The existing pairing code was retained. This fix does not change the backing model, servo calibration or hardware connection state. The initial EVALUATION report is historical; FIX_REPORT.json binds the corrected implementation to its regression and live replay evidence.
