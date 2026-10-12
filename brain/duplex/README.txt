# MIST native voice

## Debugging and visual inspection

Open `/debug` in the same paired browser to inspect the current server's event timeline. It includes native model phases, tool arguments/results and handler times, background job/tool events, TTS connection and phrase timings, browser playback starts and queue length, expression changes, and microphone frame/RMS summaries. No raw PCM or authentication fields are retained in the trace. The journal holds at most 2,000 events in memory; the page loads them in bounded batches and can filter, pause or export its visible trace. Transcripts and tool arguments may appear in an export. Application tool time is separate from model decision time, and transcript-completion-to-playback time excludes the earlier native end-of-turn detection interval.

Open `/studio/drawn/transitions.html` for the current shared production renderer. It covers all 40 faces, transitions between any pair, frame stepping and saved MIST voice recordings. `/studio/drawn/` shows all 40 together. The renderer preserves the original resting artwork and uses reusable drawn blink and mouth poses for motion. There are 21 named expression presets with variants. The older `/expressions` inspector remains available for the procedural artwork. The inspectors make no model calls and open no microphone.

The current drawn animation uses 15 fps, 600 ms expression transitions and 400 ms blinks. Speech reads the current output clock; silence and lip closure can update immediately. FV, LNT and TH use new smooth ImageGen silhouettes in both mouth families. Faces 20 and 40 retain their small resting mouths but use a readable minimum width during speech. See [FACE_CONTROL.md](FACE_CONTROL.md) for the model-facing selection rules and complete preset/variant table.

An expression's requested duration is its visible hold after the entrance animation. Waiting in the short expression queue does not consume that hold. Duplicate calls do not extend it, and interruptions can still replace it immediately.

Both pages are linked from Conversation controls. See DEBUG_REPORT.md for checks and measurement limits.

The Luna conversation tests are viewable at `/duplex/luna-tests.html`. The page retains earlier failures alongside subsequent runs. It distinguishes model choices from application checks that reject an inappropriate call. The dated reports under `brain/results/luna_*` retain transcripts and measured timings.

This mode connects the phone's microphone to native Codex V3 voice over WebRTC. By default, response text streams to ElevenLabs Flash v2.5 through one multi-context TTS WebSocket, using `24AMj4dc02cYAwoUnqzN`, MIST (refined). The browser plays the resulting PCM audio. Native Codex audio is discarded. The existing face geometry, animator and bounded robot tools are reused.

The current architecture and tests are recorded in [LAYERED_REPORT.md](LAYERED_REPORT.md). STREAMING_TTS_REPORT records the preceding TTS trial, while QUALITY_REPORT and FIX_REPORT preserve earlier Voice Changer experiments. The initial native connection still avoids duplicate automatic Codex startup context.

## Conversation and background reasoning

Native voice continues listening and producing replies. GPT-6 Luna with low reasoning handles immediate application requests. A separate Luna analyst can work on a longer question through `start_background_task`, which returns a job receipt without waiting for the answer. This analyst has its own ephemeral model session and read-only sensor/preference tools. It cannot command motion or change preferences. One analysis runs at a time, with a 45-second reasoning limit and bounded output. Ending the conversation cancels outstanding work and closes its model process.

The models communicate through a private result mailbox. `background_task_status` retrieves a result; `cancel_background_task` cancels it. A completion is supplied to the conversation model only when playback, user speech and active tool delegation are idle, and the user's turn has not changed. Otherwise it stays available for a later question, avoiding an unsolicited answer to an old topic. Cancellation prevents a late result from being published. The controls also offer Think in background and Cancel analysis, allowing typed work to start while MIST is already speaking.

The speech path now prefers complete sentences and clauses of at least six words and 32 characters. Short prefaces, abbreviations and decimal values stay together. A 140-character whole-word fallback bounds unpunctuated text. Every phrase in a reply keeps the same ElevenLabs synthesis context. This is conservative punctuation-based grouping, not a grammatical parser; it cannot guarantee perfect intonation at every boundary.

The prompt asks for a short useful opening, varied rhythm, restrained warmth and natural clause punctuation. The face can choose a small happy or curious reaction from clear opening phrases at playback start. It changes at most once automatically per reply, and explicit expression choices retain priority. No spoken emotion tags, new voice identity or pitch shifting were added.

The microphone stays active during playback. Native user-turn detection cancels the current TTS context and clears queued browser audio; subsequent audio from that context cannot revive it. This is a duplex application built around native voice input and turn detection, a tool model, and a separate streaming synthesizer. It is not a single end-to-end speech model, and room echo handling still depends on browser capture and the actual device.

Visible replies use the native turn's accepted transcript and matching turn ID. Predictive fragments still prepare speech but are not shown as a completed or continuing answer after interruption. Interrupted text is cleared before the next reply.

Model tool requests carry the current user's transcript. Conservative English checks reject explicit unavailable face variants, temporary preferences that were not requested for storage, and conversational phrases such as "walk me through" being used as motion commands. These checks do not interpret every language or ambiguous request. The runtime also validates arguments, units and limits. Superseded non-stop calls are rejected before dispatch; stop bypasses the ordinary tool budget. The local UI's explicit controls keep their direct command path.

Native V3 emits predictive response text before its assistant-turn event. The bridge now prepares TTS from those early fragments, preserving the first words, but holds playback until the native turn boundary. An utterance retains one synthesis context across fragments. Complete sentences flush buffered text, and end-of-turn flushing handles very short replies. Tokens split inside words are reassembled before being sent. Contexts are closed after each reply or interruption; the WebSocket is reused. An interrupted or partially delivered reply is never automatically replayed after a failure.

The retained audio-to-audio experiment can be selected explicitly with `--speech-backend voice-changer`. The default is `--speech-backend streaming-tts`. Selecting Voice Changer restores its extra conversion delay and independent audio passages; the following Voice Changer details apply only to that optional mode.

The backing tool model defaults to `gpt-6-luna` with low reasoning. Native voice handles the live conversation and delegates sensor, memory and robot-preview requests to that model. The app uses the installed Codex app-server and its signed-in account; it does not extract or copy login tokens. The WebSocket-only native transport was tested and requires API-key authentication, so this implementation uses the WebRTC transport instead.

## Start

From the repository root:

```powershell
python -m pip install -r brain/duplex/requirements.txt
python brain/duplex/server.py
```

Open `http://127.0.0.1:8790/`, enter the pairing code printed by the server, and press Start conversation. The microphone opens only after that click. End conversation closes the microphone, realtime call and converter. The browser must permit audio playback and microphone access.

The server uses `ELEVENLABS_API_KEY` from the existing repository `.env`. `MIST_CODEX_BINARY` can explicitly select a native Codex executable. Otherwise, the installed desktop executable is discovered under the local OpenAI Codex directory. The executable used for the 22 September Luna tests is version `0.155.0-alpha.16`; this realtime protocol is experimental. No API key is sent to the browser. ElevenLabs synthesis consumes the account's normal credits.

`MIST_BRAIN_MODEL` selects another locally available backing model. `MIST_BACKGROUND_MODEL` independently selects the analyst. Both default to Luna; explicit environment overrides remain supported. The native voice model is selected by the installed Codex voice service; it is separate from the backing tool model.

## Use the phone

The phone runs the web face, microphone, speaker and optional sensor capture. The computer runs Codex and the conversion bridge. This is not an on-device language model.

With a USB-connected, authorized Android phone, run:

```powershell
adb reverse tcp:8790 tcp:8790
```

Then open `http://localhost:8790/` in the phone browser and pair it using the server code. Localhost provides the secure browser context required for microphone access without a certificate interstitial. The Mi 9 SE was not connected during this implementation; real handset audio, echo cancellation and sensor delivery remain acceptance tests.

For wireless use, serve with a trusted certificate and key:

```powershell
python brain/duplex/server.py --host 0.0.0.0 --port 8790 --cert YOUR_TRUSTED_CERT.pem --key YOUR_PRIVATE_KEY.pem
```

The certificate must match the phone's URL and be trusted by that phone. The server refuses unencrypted non-loopback listening. Do not expose this development server publicly. The same-origin check, short-lived process pairing code and HttpOnly session cookie protect the local voice connection. One screen owns an active conversation at a time.

## Sensors and robot tools

The motion-sensor checkbox sends bounded phone-frame acceleration and angular-rate samples. It never treats the rotating phone's orientation as the robot body's attitude. Values include units, receipt times, source labels and freshness. Sensor values update the display; they do not trigger unsolicited spoken announcements. The model reads a snapshot when needed.

The optional adapter supports the existing SensorServer application:

```powershell
adb forward tcp:8080 tcp:8080
python brain/duplex/server.py --sensor-url 'ws://127.0.0.1:8080/sensors/connect?types=["android.sensor.accelerometer","android.sensor.gyroscope","android.sensor.magnetic_field"]'
```

It preserves separate accelerometer, gyroscope and magnetometer streams, checks ordering and relative timestamp drift, and labels the first sample's absolute age as unknown. Android nanoseconds since boot are not Unix timestamps. There is no camera producer or calibrated body-attitude fusion in this mode.

The seven tools are `get_sensor_snapshot`, `preview_motion`, `pan_phone`, `stop_robot`, `set_expression`, `remember` and `recall`. Motion remains preview-only, with R5 limits and a two-second intent expiry. There is no serial, ESP32 or motor transport. Stop clears and latches the preview path; it does not acknowledge a physical emergency stop. Resume is an explicit interface action. Phone pan requires an explicit USB-disconnected state. Actual controller integration needs measured calibration, a watchdog, independent stops and acknowledgements before hardware enablement.

## Conversation behavior

The prompt favors brief, specific replies, at most one follow-up question, less enthusiasm for routine events and no forced jokes. It distinguishes companionship from unwanted advice, handles corrections directly and avoids narrating sensor schemas. Explicit preferences are stored in the selected run directory and supplied to the next session as reported context.

All 21 named expression presets and 40 underlying face variants remain available. The face's mouth follows the converted playback clock and signal amplitude, including silent-mouth frames. This is amplitude-based animation, not a phoneme recognizer. Expressions requested through a tool are displayed; a few conversational cues are inferred from transcript text and are not emotion detection.

An explicitly requested expression stays until the next interaction, so it does not disappear before the converted voice confirms it. The status returns to Listening after queued audio finishes. A provider failure ends playback without substituting the original voice; a fresh connection starts a new playback generation.

Capture continues during playback with browser echo cancellation, noise suppression and gain control requested. A native user-turn event clears queued playback and invalidates conversion generations. The browser no longer cancels audio based only on microphone volume, which cannot distinguish the user from speaker echo. Stop speaking remains immediate. Old converted chunks cannot revive an interrupted playback generation. The original Codex voice is not an error fallback. Simultaneous capture and playback are supported; reliable recognition in a noisy room and human-quality conversational overlap remain handset acceptance tests.

In the optional Voice Changer mode, finite audio uploads use a 1.8-second cap and acoustic pause boundaries. This mode retains a 3.6-second conversion deadline and retries only before audio is emitted. It is not a continuous audio-input WebSocket and can still produce seams between passages.

Both modes reserve 200 ms in the browser at startup or after an underrun, then schedule PCM packets contiguously. TTS can generate a whole sentence faster than it is spoken, so future audio is allowed to queue up to 30 seconds before the runaway-buffer guard clears it. This is a memory bound, not a target delay: playback starts after the 200 ms reserve, and interruption clears the queue immediately. No pitch shifting, resampling in the browser, or gain boost is applied to the 24 kHz TTS PCM.

Thinking uses a closed line mouth and a slight upward, sideways gaze. The thinking and tool-checking states explicitly select it and keep it until a response arrives. Listening retains the attentive expression; actual audible playback drives the speaking mouth. An explicitly selected expression takes precedence. Versioned frontend URLs ensure a refreshed screen loads these changes instead of cached scripts or mappings.

The overlay caption waits for audio playback to start instead of displaying the reply as soon as the native transcript arrives. The detailed transcript remains immediate. This is a presentation improvement, separate from the measured reduction in audio buffering. Provider diagnostics record timings, exception types and retry counts in `<run-dir>/voice_diagnostics.jsonl`, without audio, transcripts or credentials.

## Tests and limits

```powershell
python brain/harness/test_duplex.py
python brain/harness/test_voice_recovery.py
python brain/harness/test_streaming_tts.py
node brain/harness/test_duplex_playback.mjs
node brain/harness/check_face_runtime.cjs
```

The Python tests cover freshness, units, timestamp ordering, untrusted fields, preview limits, stop latching, persistence, pairing/origin checks, conversion ordering and cancellation. The playback test covers immediate stop, stale generations and backlog. The shared renderer checks forty faces and their transitions.

Live tests require `--enable-fixtures` and the existing Deepgram key. This enables a visible test panel and a paired synthetic-input event. It never opens a real microphone. Fixture audio is generated by Deepgram, streamed into native Codex voice at real time, converted by ElevenLabs and saved only by the explicit evaluation harness. Normal runtime keeps bounded recent events in memory and saves explicit preferences, not microphone audio.

```powershell
python brain/duplex/server.py --enable-fixtures
python brain/harness/eval_duplex_live.py --code SERVER_CODE --limit 11 --out brain/results/YOUR_EVALUATION
python brain/harness/eval_duplex_interrupt.py --code SERVER_CODE --out brain/results/YOUR_INTERRUPTION_TEST
```

This is a working development harness, not a completed physical-robot controller or a guarantee of human-perceived conversational quality. The recorded evaluations distinguish conversion time, input pacing, model/tool delay, interruptions and recognition. Real room echo, Mi 9 SE loudspeaker feedback, thermal behavior, wireless latency and the owner's subjective voice preference must be checked on the handset.
