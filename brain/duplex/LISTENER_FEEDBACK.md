# Live captions and listening acknowledgements

The phone face shows a `You` caption while recognition is in progress. Revised partials replace earlier text. The last final remains until the next recognized words arrive; acoustic speech-start alone does not clear it. The visible band follows the latest two lines. Conversation history still receives only committed turns.

Cascade voice architectures have **Controls → Listening acknowledgements**, enabled by default. The current policy selects a quiet, cached “Mm-hmm.” in the configured MIST voice. A positive “Uh-huh.” clip is also cached, but is not selected by the current policy. Native Codex voice still has its own turn handling; this new acknowledgement channel is unavailable there.

## Timing and turn handling

- Require at least five seconds of the current user floor, eight recognized words, and an unfinished clause.
- Wait for 350–1100 ms without recent voiced PCM or a transcript revision. A completed statement or question does not qualify.
- Send at most one candidate per floor, with at least 18 seconds between attempts. Candidates expire after 350 ms in the browser.
- Cancel a queued cue if the user resumes, recognition changes, normal assistant audio arrives, or the session resets. Let an already-started short cue finish under continuation of the same user floor.
- Requests for quiet, speaking practice, and detected distress suppress cues. “Let me finish” suppresses only the current floor. Explicit practice mode lasts until ended or the control is re-enabled.

The clip is loaded from `brain/results/listener-cues`; normal operation does not synthesize it or call another model. Missing clips cause a recorded skip. The microphone remains active. Cue audio uses a separate player, with mouth timing based on the audio output clock. It does not create an assistant transcript, model turn, tool call, or face-selection command.

This is a conservative timing and text policy, not a semantic listener model. It will miss some natural acknowledgement opportunities and cannot reliably infer all sensitive contexts. Browser echo cancellation and a narrow exact-cue echo check are present, but physical speaker-to-microphone echo and perceived naturalness need testing on the phone.

## Debugging

The trace's audio category includes `listener_feedback`, `listener_cue`, and browser `listener_cue_state` receipts. Decisions record their suppression reason; receipts distinguish scheduled output from started and ended playback. PCM is omitted from public traces. `user_transcript` snapshots have utterance IDs and monotonic revisions. The face debug snapshot exposes the visible user caption and current cue.

## Repeatable checks

```powershell
python -m unittest brain.harness.test_listener_backchannels brain.harness.test_listener_voice brain.harness.test_listener_integration -q
node --test brain/duplex/static/user_transcript_state.test.mjs
node brain/harness/test_listener_cue.mjs
python -m unittest discover -s brain/benchmarks/naturalness -p test_cascade_voice.py -q
```

The isolated browser fixture runs with `python brain/harness/preview_listener_feedback.py --port 9064`. Open `http://127.0.0.1:9064/?architecture=qwen-low&trial=1`, then **Controls → Connect test session**. POST `/replay/start` with `Origin: http://127.0.0.1:9064`. It replays a fictional garden explanation and synthetic PCM activity; no microphone or speech/model provider is opened. It uses the real cached cue and production listener code. Reload the production page afterward because localhost pairing cookies are shared across ports.

Results and screenshots for this change are in `brain/results/listener-feedback-20260928`. Browser receipt latency is a software measurement; it is not physical mouth-to-ear latency.
