# MIST console

Run commands from the `brain` directory. The default Fast conversation profile uses the installed Codex client with GPT-5.3 Codex Spark, low reasoning and its verified standard service tier. Independent background tasks use GPT-6 Astra, low reasoning and Fast (`priority`). Spark does not advertise a priority tier. The Astra catalog's Fast description does not establish a measured twofold speedup.

```powershell
python ui/server.py --port 8776 --run-dir results/mist-v2-browser-live
```

On the next authorized launch, that single command starts the console and its streaming-recognition proxy. The default ports are 8776 and 8788. Both listeners belong to the same Python process; Ctrl+C closes its browser connections, recognition engine, background worker and model client. A port conflict fails startup before a model client is created. The launcher never kills or silently adopts an existing process.

Managed recognition uses the already-tested `websockets` 13.1 dependency. In another Python environment, install it with `python -m pip install -r ui/requirements-stt.txt`. Batch-only mode does not import that dependency.

The currently running console and separately launched proxy are unchanged by this code update. Do not start another copy alongside them. The managed lifecycle applies when the console is next launched through the updated command.

For a different port pair:

```powershell
python ui/server.py --port 9000 --stt-port 9001 --run-dir results/mist-custom
```

The proxy's allowed origins and the browser's WebSocket URL follow those settings. `--stt-port 0` selects an available proxy port and advertises the selected URL. `--stt-mode off` uses batch recognition only. `--stub` and watch mode default to streaming off; tests can explicitly request a managed proxy with a fake engine.

Open [the console](http://127.0.0.1:8776/) or [the face studio](http://127.0.0.1:8776/face/). The console stays on loopback. It does not connect to motors or a camera. The simulated motion tools enforce the recovered 50 C servo cutoff independently of model instructions.

Codex must already be signed in. The provider validates the requested model, reasoning level and service tier during startup. See [CODEX_PROVIDER.md](CODEX_PROVIDER.md) for the installed-client requirements and tool-exposure audit. Model errors remain errors; no other backend silently substitutes an answer. The Conversation profile selector can switch to Astra conversation while retaining recent messages. The CLI equivalent is `--profile astra`. Use `--executive-model`, `--executive-thinking` and `--executive-service-tier` to configure background work separately.

The Gemini option remains available through Pi:

```powershell
python ui/server.py --backend pi --model gemini-flash-lite-latest --thinking off --port 8776 --run-dir results/mist-gemini
```

The existing repository `.env` supplies provider keys. Values are never returned by `/api/config`. The console defaults to the existing ElevenLabs voice **MIST (refined)**, `24AMj4dc02cYAwoUnqzN`, with Responsive (`eleven_flash_v2_5`). The Voice quality selector retains Quality (`eleven_multilingual_v2`). To use the existing cloned MIST voice instead, configure `MIST_ELEVENLABS_VOICE_ID=VjMZm85XGZ6JjZZlCGeJ` in the launch environment. This selects an existing voice; it does not create a clone. Deepgram and the browser voice remain selectable alternatives. Browser speech has no dependable playback clock, so that fallback preserves the expression without claiming synchronized mouth motion.

The conversation uses the `mist-v2` persona. It answers briefly, uses saved notes and the current conversation, checks observations before present-tense vision claims, and distinguishes simulated actions from physical ones. Persona switching creates a fresh conversation. Notes and job receipts persist in the selected run directory.

`conversation.json` persists the last forty user and assistant messages. Startup and profile changes restore up to 12,000 characters as quoted prior-conversation data. These messages are context, not proof that actions happened. The native Codex thread is ephemeral and is replaced on restart. New session clears the restored conversation; jobs and saved notes remain.

## Talk mode

Click **Talk** once and allow the browser's microphone prompt. MIST listens for an utterance, waits for 650 ms of silence and sends its transcript automatically. Confirmed speech streams to the local recognition proxy while you speak; a complete-WAV fallback is used if the proxy is unavailable. Enter and the manual mic button are not required. **Stop talk** stops capture, discards pending audio and prevents a late transcript from sending. The visible indicator changes between opening the microphone, listening, hearing speech, transcribing and sending.

Listening resumes after the utterance has been transcribed and accepted, so it can continue during the model reply and voice playback. Speaking again stops local playback and interrupts an active reply before submitting the new utterance. Browser echo cancellation, noise suppression and gain control are requested; stronger, sustained input is required during playback. This is local activity detection with separate recognition, text-model and TTS stages, not a native full-duplex speech model. Acoustic echo rejection on the user's microphone and speakers has not been measured. Sustained room noise can also trigger basic activity detection; headphones can help if speaker pickup causes interruptions.

Capture keeps 200 ms of lead-in audio and a 650 ms silence tail, rejects voiced segments shorter than 250 ms and caps an utterance at twenty seconds. Only one transcription/submission handoff is active at a time; new samples during that handoff are dropped rather than queued indefinitely. Stop, microphone disconnection, processor failure and a lost console connection release the microphone. Talk never starts automatically on page load or reconnect.

Normal console startup manages recognition automatically. If deliberately running the proxy separately, start it with the console's exact origins and mark it external in the console command:

```powershell
python ui/stt_proxy.py --port 8788 --origin http://127.0.0.1:8776 --origin http://localhost:8776 --metrics-path results/mist-v2-browser-live/stt_streaming_metrics.jsonl
python ui/server.py --stt-mode external --stt-port 8788 --port 8776 --run-dir results/mist-v2-browser-live
```

Those two commands run in separate terminals. External mode does not start, probe or shut down the separately owned proxy. Its port must be fixed, and the operator must match its origins to the selected console port. This preserves explicit ownership instead of treating an occupied port as permission to attach or replace it.

The proxy keeps the Deepgram key on the server, accepts the console's localhost origins and reuses the provider connection between utterances. The browser sends actual-rate PCM16 only after local activity confirmation, preserving lead-in audio while the connection opens. Frames are paced and bounded. Stop or cancellation closes the stream and never triggers a fallback upload; service failure can fall back once to the complete WAV. See [STREAMING_STT.md](STREAMING_STT.md) for the protocol and dependency details.

The saved-audio browser fixture is reproducible without opening a microphone or calling providers:

```powershell
python harness/ui_talk_fixture.py --port 8779
python harness/ui_talk_fixture.py --port 8779 --streaming
```

Run either fixture command separately. Its visible label identifies the saved virtual microphone. Click Talk there to exercise endpointing, transcription, automatic sending and saved reply playback. The streaming variant uses a fake provider through the real local proxy. The optional interruption button injects another saved utterance during playback. Capture and session lifecycle checks are included in `harness/run_offline_tests.py`.

## Background tasks

Type a research or writing request and choose **Background task**, or ask MIST to research it during conversation. The tool and button feed the same ticket queue. A maximum of two independent executive workers can run while the conversation model stays available. Executive model sessions receive no robot, shell, file, web or collaboration tools. The deterministic worker fetches source excerpts and passes them to the model as untrusted data.

Each task shows queued, running, completed, failed or cancelled state. Results retain source URLs, retrieval times, evidence coverage and limitations. **Read result** speaks a completed brief on demand. Ask MIST about the result to retrieve it through `check_inbox` during conversation. Nothing is sent to external messaging services.

**Cancel task** immediately records cancellation and suppresses late publication. A network fetch already in progress may finish before the worker notices cancellation. Interrupted running jobs become failed after restart and write one failure receipt to the inbox. Queued jobs remain available for the next run. **Stop reply** stops speech and interrupts a Codex conversation turn, including a stop requested before its model call starts. It is not a physical emergency stop.

The server owns the background worker by default. Do not run `executive/worker.py` against the same run directory at the same time. Use `--no-executive` when managing that older standalone worker yourself; the integrated task controls are unavailable in that mode. A fresh foreign `worker.alive` file blocks competing worker startup. After a crash, let its twenty-second heartbeat window expire before relaunching.

## Speech and face timing

The main console uses the shared SVG face renderer directly. It preserves the original forty expressions, eases changes through one visible mouth, blinks and moves its gaze while idle, and respects reduced-motion settings. An expression change does not terminate speech.

Updated tabs automatically generate audio only for messages they submitted, and show restored history silently. The server also requires speech protocol 2, an explicit reply/preview/manual purpose and a request id before calling the provider. Obsolete pages receive a reload message. Concurrent requests with the same id and content share one generation, and later retries reuse a bounded cached clip; conflicting content is rejected. This server guard is necessary because updating the page source does not replace JavaScript already running in another tab.

The audio cache holds at most sixteen clips and sixteen MiB for ten minutes. The server remembers up to 4,096 request ids, including successful ids recovered from the usage log. Remembered ids whose audio has expired or been evicted return 410 without regenerating audio. A new explicit Play reply request uses a new id. If browser autoplay policy blocks a generated clip, Play reply retries that same retained audio from a user gesture without another HTTP or TTS request. The previous empty audio-priming function was removed; the persistent audio element and the explicit playback gesture follow the browser's policy.

ElevenLabs returns character timestamps. The server converts those into approximate mouth shapes, checks the generated WAV duration and closes the mouth in detected quiet intervals. During playback, the renderer reads the audio element's `currentTime`; speed changes and pauses therefore use the same clock. Stop, completion and provider errors reset the speech layer. A generation counter and request abort prevent an older voice response from replacing a newer reply.

`/api/speech` returns WAV bytes as base64, measured duration, timestamped events, alignment provenance and usage. `/api/tts` preserves the older Deepgram WAV endpoint. The optional Deepgram round trip measures whether generated words remain intelligible; it does not measure voice likeness or perceptual lip sync. No physical microphone loop was performed in the saved validation run.

Each local conversation request has an id. Server metrics retain acceptance, queue and backend stage timings; voice metrics retain request headers, first response byte, body completion and local processing. The browser's `#latencyStatus` element exposes the last twenty traces in its `data-traces` attribute, from Send through actual audio playback. These traces contain timing and usage metadata, not message text.

## Checks and evidence

```powershell
python harness/run_offline_tests.py
```

This runs robot interlocks, model-client contracts, UI and background-job lifecycle checks, face geometry, speech request races and provider response parsing without paid API calls. For an offline interactive fixture:

```powershell
python ui/server.py --stub --port 8777 --run-dir results/mist-offline
```

The UI clearly labels that mode **OFFLINE FIXTURE**. Its canned model and executive answers are not evidence of live intelligence. Selecting a configured speech provider can still call its API, so choose Mute when keeping a fixture session fully offline.

Live browser measurements and screenshots are under `design/mist_v2_20260906/brain_v2_20260907` in the repository root. `turn_metrics.jsonl` and `speech_metrics.jsonl` in each run directory record latency and reported usage. Codex subscription turns and speech providers do not expose a dollar price here; unknown cost remains null.
