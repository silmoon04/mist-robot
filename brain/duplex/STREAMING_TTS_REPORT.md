# MIST streaming TTS trial

Streaming TTS is now the default. Native Codex V3 still receives the microphone and handles conversation and tool delegation. Its response text is synthesized by ElevenLabs Flash v2.5 using MIST (refined), voice ID 24AMj4dc02cYAwoUnqzN. Native audio is discarded. The backing Spark model is unchanged.

One provider WebSocket stays open for the conversation. Each reply uses one synthesis context, preserving state across text fragments. Complete sentences and final turns flush pending text. The microphone remains active during playback. A new native user turn closes the old speech context, invalidates queued audio, and lets the correction use a fresh context. Manual Stop speaking clears playback immediately.

The first implementation revealed a specific missing-speech bug: native transcript fragments can precede the assistant-turn event. The bridge now prepares those fragments immediately and holds their audio until the native boundary. This keeps the first words without speaking prematurely over the user. Native event handlers are serialized, split words are reassembled, and late audio or errors from canceled contexts cannot affect the next reply.

The browser buffers 200 ms at startup, then schedules PCM packets contiguously. A ten-second sentence generated in a burst passes the playback regression test; it does not trigger the old backlog reset. The 30-second maximum queue is a resource bound, not an intentional playback delay. No pitch shifting or gain boost is applied.

## Measured results

Six direct TTS probes covered a two-word reply, gentle reassurance, excitement, a question, a precise instruction, and a longer story. Their first audio arrived 140-265 ms after input began on an already connected socket. All six were recovered correctly by independent speech recognition and had zero clipped samples. Basic pitch estimates varied across the samples, but these are not a listening-quality score.

Three complete native conversations returned their first playable audio 1.75-1.84 seconds after the final synthetic microphone frame. Browser buffering adds 200 ms, giving roughly two seconds to audible speech. Independent recognition of the recorded audio confirmed the first and last words of all three replies. Earlier attempts lost prefixes; those results remain in the evidence alongside the fixed run.

Both native-turn interruption and explicit-stop tests discarded all old-generation audio and produced the new blue teacup reply. Independent recognition confirmed the correction was present in the audio. The interruption harness includes synthetic-input generation time, so its dispatch-to-reset interval is not a real microphone interruption latency measurement.

Sensor and phone-pan tools returned real application receipts and spoken replies without speech errors. They remained slow: first audio arrived about 7.4 and 8.4 seconds after input ended. Both were called twice by the native/backing path. This trial does not claim that tool latency is solved.

The browser test played a short synthetic reply, showed its caption at playback start, returned to Listening, and reported no console errors. All 33 application contracts, 11 streaming TTS contracts, six legacy recovery contracts, playback checks and 31,050 renderer states passed.

## Limits and reproduction

This is a duplex application with separate native input and TTS output, not a single end-to-end speech model. Native turn detection remains the main ordinary-conversation delay. Real room echo, phone loudspeaker interaction and subjective quality still need the owner's listening trial. No real microphone was opened by these tests, and no physical robot commands were enabled.

Start normally with python brain/duplex/server.py. The default backend is streaming-tts. The previous audio-to-audio experiment remains selectable with --speech-backend voice-changer. Evidence and recordings are under brain/results/tts_websocket_20260914. The JSON companion records timings, checks and implementation hashes.

API references:
https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-multi-stream-input
https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/multi-context-web-socket
