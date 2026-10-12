# Voice trials

Run `python brain/duplex/live_studio.py` from the repository, then open
<http://127.0.0.1:9053/try>. The server binds to loopback. The test page pairs this
browser locally; provider keys remain on the server.

Choose an architecture and press **Start conversation** inside the face view.
Allow microphone access. The microphone continues sending audio during playback.
Switching closes the previous connection before loading the next face view. Start
the next conversation yourself. Each connection has fresh model history and
preferences, so comparisons do not silently inherit the previous model's answers.

| Choice | Foreground | Turn taking |
| --- | --- | --- |
| Cerebras, more pause time | Deepgram Nova-3 → GPT-OSS-120B | 700 ms recognition endpoint; selective interruption |
| Cerebras, shorter pauses | Deepgram Nova-3 → GPT-OSS-120B | 300 ms endpoint; selective interruption |
| Cerebras, immediate interruption | Deepgram Nova-3 → GPT-OSS-120B | 300 ms endpoint; stops at detected speech |
| Luna, separate speech recognition | Deepgram Nova-3 → GPT-6 Luna | 300 ms endpoint; selective interruption |
| Codex native voice, Luna tools | Native voice V3 with Luna handling delegated tools | Native turn detection |

All choices use ElevenLabs streaming TTS with the MIST voice, the existing face
assets, output-clock mouth cues, and a separate Luna background worker. Native
voice's text is also rendered by ElevenLabs; original native audio is muted.
Selective interruption is a lexical policy, not a model that understands every
social cue. It waits for recognised words before deciding whether to yield.

Try the same requests on each option:

- “Show me sad variation two, then tell me what sensor readings you have.”
- Ask for a short explanation. Say “mm-hm” during it, then interrupt with “wait,
  I meant the other leg.”
- “Think in the background about how to test a leg.” Keep talking while it works.
- Ask for a movement preview, correct a direction, then ask it to stop.

Robot actions remain previews. Phone reports are sensor inputs, not proof of a
connected motor controller, robot body attitude or camera.

In **Controls**, **Connect test session** opens the same voice path without a
physical microphone. **Speak test phrase** synthesises input and feeds actual
speech recognition. Cascade choices also accept typed messages; those skip speech
recognition and must not be compared with microphone latency as if they included it.

## Saved evidence

The trace panel shows public model output, recognised transcripts, tool arguments
and results, expression requests, browser expression changes, audio delivery
metadata, playback estimates, background work and failures. Expand an event for
its full stored JSON. Select a previous session, compare configurations or export
the conversation. Selecting historical evidence does not stop a live conversation.

Files live under `brain/results/live-studio/traces/<trace_id>/`. Records survive
browser reloads and server restarts. A session left open by a server crash is marked
interrupted when the server restarts. Traces contain conversation text, so treat
them as personal local files. API keys, authentication fields, raw microphone/voice
PCM and private model reasoning are excluded from these exports.

Writes are batched off the voice loop, normally for up to 50 ms. Disconnect drains
the queue. Abruptly killing the process can lose the last queued events; saved
earlier events remain readable.

The server receipt clock, model/provider durations and browser playback clock are
distinct. Playback markers measure browser software scheduling, not physical sound
at a listener's ear. Generated reply text does not prove the user heard it. Human
naturalness, echo cancellation and the phone's speaker/microphone still need direct
listening tests.

## Checks

Run the focused storage, integration and session-option tests:

```powershell
python brain/harness/test_trial_traces.py
python brain/harness/test_live_studio.py
python brain/harness/test_session_voice_options.py
```

The integration tests substitute providers to exercise cancellation, fresh state,
tool-to-face logging, saved history and request validation. They do not establish
live provider quality. Keep live smoke evidence separate from these checks.
