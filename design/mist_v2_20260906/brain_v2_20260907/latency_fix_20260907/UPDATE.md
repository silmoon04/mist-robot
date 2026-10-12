# Conversation and voice repair

The active console on port 8776 now uses GPT-5.3 Codex Spark with low reasoning and the verified standard tier for conversation. Background tasks use GPT-6 Astra with low reasoning and Fast (`priority`). Responsive voice uses the existing MIST (refined) voice with ElevenLabs Flash v2.5. The UI retains Astra conversation and the Multilingual v2 Quality voice as selectable options.

The server was checked idle before shutdown, with its two saved jobs completed and cancelled. The run state was copied to `state_before_restart`. Six visible messages, captured by the root task from the existing conversation, were restored into the replacement client as quoted prior-conversation data. The native Codex thread was ephemeral and could not resume after its process exited. Jobs, notes and receipts stayed in the same run directory. `activated_startup.json` and `activated_console.png` verify the running configuration and the six silently restored message rows.

## What explained the failure

Recent real speech logs contained paired generations for the same reply lengths. A thirty-character response was synthesized twice within fourteen milliseconds; a 364-character response was also synthesized twice. Every connected tab previously called TTS for every completed turn, including fresh spectator tabs. A spectator without a prior browser gesture could then hit autoplay policy. The player discarded that already-generated audio and printed the browser's raw error in the chat.

The longer observed conversation turn took 8.703 seconds, with its first tool request at 2.031 seconds and first text at 8.687 seconds. Full-response TTS then took another 2.45 to 2.64 seconds. This explains an approximately eleven-second wait before playback on that case. It does not establish that every response had that delay. The baseline scalar metrics are preserved beside this report; they contain no message text.

## Repairs and checks

The first ownership repair applied to tabs that loaded the updated JavaScript. An accepted request and its echo establish ownership; newer servers also return a request id that disambiguates replays. Those updated tabs show restored history silently and avoid repeat speech after failed sends, cancellations or reconnects. A correlated completion can arrive before the HTTP acknowledgement without losing the reply. This did not stop JavaScript already running in a stale tab, as the later live probe below demonstrated.

An autoplay `NotAllowedError` retains the audio and displays Play reply. Clicking it retries the same clip without another TTS request. Stop still clears retained audio. The empty `primeAudio` function and its misleading unlock comments were removed.

The actual Chrome saved-clip test first showed the blocked state and one local audio request. A user click scheduled playback six seconds later. That same audio element played and completed with the request count still one. Screenshots are `../autoplay-blocked.png` and `../autoplay-resumed.png`. The fixture made no model or speech-provider calls and changed no browser policy.

The complete console was also exercised on an isolated fixture server using its actual Send handler, HTTP route, SSE events, player and a previously generated WAV. Its trace reached real `audio_playing` 237 milliseconds after Send. This measures local fixture transport and playback overhead, not live model speed. The captured stage sequence and screenshot are `offline_ui_browser_trace.json` and `offline_ui_browser.png`.

The backend now supports a bounded, allowlisted expression prefix in its text response, so a display expression can accompany speech without a separate cosmetic tool round trip. The prefix is stripped before text display and synthesis. The server broadcasts it only as display metadata and preserves it across subsequent simulator-state updates. Robot state is not changed by that metadata. Ordinary capability questions can use a fresh deterministic snapshot; a current-vision question still requires a fresh observation call.

Two authorized Flash probes used the same saved phrase and existing voice. Completion times were 1.0278 and 0.3457 seconds versus the historical same-phrase Multilingual result of 0.8668 seconds. Both Flash word scores were 1.00 and both retained character alignment. The small, noncontemporaneous comparison shows variability: the first Flash request was slower. See `../voice/flash_latency_20260907/probe.md` for usage and timing boundaries. No TLS optimization was claimed without a separate measurement.

Spark's first isolated greeting confused the user's and robot's names. Explicit role anchors were added, and the two authorized targeted retests passed: 2.226 and 1.121 seconds. These are isolated model measurements, not an end-to-end live latency distribution. The backend's reports under `../latency_diagnosis` preserve that failure and retest.

## Timing and continuity

The server records acceptance, queue wait, backend acknowledgement, tool execution and model completion. Speech usage records provider headers, first response-body byte, body completion and local processing. The browser records Send, acceptance response, first text, model completion, TTS request, TTS response headers and body, playback attempt, blocked playback and actual playback. Inspect the last twenty traces through `#latencyStatus.dataset.traces`.

Conversation messages now persist in `conversation.json`. A profile change restores recent messages into the new client; New session and persona changes clear that conversation context. Profile changes keep Astra background work and saved notes intact. History hydration never invokes TTS.

The complete offline runner passed after these changes. It includes fifteen UI ownership and replay cases, the retained-autoplay player regression, request-stage ordering, profile/context persistence, metadata separation, provider model selection and the existing grounding, interlock and face tests. `offline_checks.txt` contains the full result.

No paid calls were made during browser replay, activation or startup inspection. The live user's page was not manipulated during the tests. A page already open before the repair needs a normal reload to load the updated client controls; the conversation and saved job results then hydrate silently.

## Server guard follow-up

A subsequent root live probe returned the six-character reply "Ready." in 2.261 seconds from Send to actual playback: 6 ms to acceptance, 1.207 s to first text, 1.257 s to model completion and 1.262 s to the speech request. It also exposed a stale page generating a second copy. Speech usage grew from seven records to nine: one request had no id, followed by the current client's identified request. That short probe does not establish a matched long-response speedup. Its trace is `root_live_send_to_voice.json`.

The server now rejects `/api/speech` requests without protocol 2 before provider access. Current requests must include an explicit purpose and nonempty request id. Concurrent requests for the same id and content wait on one shared generation; later retries use a bounded cache. Different content under the same id is rejected. Expired, evicted, oversized or previously completed ids recovered after restart do not trigger another generation. Explicit preview or manual playback uses a fresh id.

The new regression uses actual HTTP requests and a saved provider fixture. Before the fix, an obsolete and current request caused two generations, while two concurrent same-id requests and a later retry caused three. After the fix, the obsolete request returned 409, the current request returned 200, and the provider was called once. The concurrency test waits until a duplicate is blocked on the unfinished Future before releasing the provider, proving that sharing works while generation is still active. All ten protocol, conflict, concurrency, cache-bound and restart tests passed. No paid provider calls were used for this follow-up.

After another idle check and backup to `state_before_protocol2_restart`, the guarded server was activated on port 8776 with all eight conversation messages retained. A live obsolete-request check returned 409 `client_reload_required`, and speech usage remained at nine records before and after. `protocol2_live_guard.json` records that check and the active Spark/Astra/Flash configuration. `protocol2_offline_checks.txt` contains the complete passing suite.
