The live app now uses generated face frames and one continuous audio playback timeline.

The old player restarted `startSpeech` for every 100 ms PCM packet, used a wall-clock timer for each packet, and only selected AA or rest. The TTS server discarded ElevenLabs character timing data. The replacement preserves those timings when splitting provider audio into browser packets, carries the active cue across packet boundaries, and gates mouth motion with measured audio silence.

The player supplies a live sample callback to the face renderer. Mouth state follows the browser's speaker-output timestamp where available. The fallback subtracts reported output and base latency from the AudioContext clock. The mouth stays at rest during startup buffering, suspension, underrun gaps, and after cancellation. An audio source's `onended` event no longer removes animation before its final samples reach the output device.

The ElevenLabs WebSocket requests `sync_alignment=true`. Both documented camelCase fields and snake_case variants are parsed. Character labels are mapped to approximate mouth shapes; they are not phoneme labels. Missing or invalid alignment uses an `audio_energy` fallback. Debug events report the alignment and clock source used.

Verified without external API calls:

- `node brain/harness/test_duplex_playback.mjs`: 100 contiguous packets, one mouth timeline, cue boundaries, output-latency fallback, audible tail, output timestamps, suspension, underrun, interruption, stale callbacks, silence, and unaligned fallback.
- `node brain/harness/test_face_audio_clock.mjs`: the actual face runtime follows live samples, exposes amount and timing provenance, stops cleanly, and retains recorded event-array support.
- `python brain/harness/test_lipsync.py`: 4 tests for exact character boundaries, 100 ms packet carry-over, silence gating, invalid timing fallback, and provider-chunk clock resets.
- `python brain/harness/test_streaming_tts.py`: 13 tests passed, including exact PCM byte preservation and attached alignment across browser packet boundaries.
- `python brain/harness/test_duplex.py`: 33 existing session, interruption, pairing, and robot-preview tests passed.
- `node --check brain/duplex/static/app.js`: passed.

These checks verify scheduling and cue transport. They do not measure audiovisual offset at a physical phone speaker, Bluetooth latency, subjective speech naturalness, or phoneme accuracy. No paid API call or live microphone session was opened for this check.

Sources checked on 2026-09-22:

- [ElevenLabs multi-context WebSocket documentation](https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-multi-stream-input) documents `sync_alignment`.
- [Official ElevenLabs SDK alignment model](https://raw.githubusercontent.com/elevenlabs/elevenlabs-python/main/src/elevenlabs/types/alignment.py) specifies that character times are relative to the returned provider chunk.
