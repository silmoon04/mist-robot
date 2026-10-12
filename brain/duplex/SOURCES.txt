# Implementation sources

The [shared conversation](https://chatgpt.com/share/6aa72ea9-d49c-83eb-996c-6db77e97dec9) was fetched successfully and its conversation payload extracted. Its main requirement is to preserve the native voice performance while replacing voice identity. It also distinguishes speech conversion from text-to-speech and warns that conversion latency needs measurement. Its suggestion to capture desktop audio was unnecessary here because the installed native Codex WebRTC route worked directly.

The protocol was checked against schemas emitted by the installed Codex desktop executable, version 0.154.0-alpha.6.2, and the official [Codex realtime protocol source](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/src/protocol/v2/realtime.rs). A real WebSocket probe returned an API-key requirement; a real WebRTC probe using the app-server's own account state connected, accepted synthetic speech and produced output audio. The implementation does not extract or reuse an OAuth token outside the installed app-server.

[ElevenLabs Voice Changer](https://elevenlabs.io/docs/api-reference/speech-to-speech/stream) accepts a finite audio upload and returns streamed converted audio. Its raw `pcm_s16le_16` input is mono 16 kHz PCM16; the selected output is 24 kHz PCM. The implementation uses `eleven_multilingual_sts_v2`. The supplied voice ID returned HTTP 200 with the name MIST (refined). Its persistent account settings were not changed; the request supplies voice settings locally.

The [ElevenLabs realtime TTS interface](https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/realtime-tts) and [Speech Engine upstream interface](https://elevenlabs.io/docs/api-reference/speech-engine/speech-engine-upstream) were reviewed. They synthesize from text, so neither was substituted for the requested native-audio conversion path.

The existing SensorServer integration is documented in `tools/sensors/README.md` and its [upstream project](https://github.com/umer0586/SensorServer). The new adapter retains Android's monotonic timestamp distinction and identifies reports as phone-frame data. No connected phone was available for a new hardware sensor test.

All vendor documentation and live probes were inspected on 14 September 2026. Provider access, experimental protocol fields and latency can change. Source snapshots and raw synthetic-test records remain in `brain/results/voice_refinement_20260914`; they are evidence, not instructions or guaranteed service behavior.
