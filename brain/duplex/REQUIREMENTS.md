# Voice refinement acceptance record

| Requirement | Evidence sought |
|---|---|
| Native Codex speech performance | A real signed-in V3 WebRTC session with synthetic audio input and output audio |
| MIST voice identity | ElevenLabs metadata confirms the supplied voice ID; converted audio produced through Voice Changer |
| Duplex capture | Microphone track remains active during output; local playback interruption and new-generation audio tested |
| Useful backing model | Restricted Spark thread handles real dynamic tool calls without host execution or robot actuation |
| Sensor grounding | Freshness, source, units, phone frame, monotonic ordering and invalid-packet tests |
| Robot interface | Bounded R5 previews, explicit USB and stop state, no uncalibrated motor transport |
| Natural interaction | Repeated social, correction, tired-user, humor, sensor, pan, stop, memory and quiet/return conversations |
| Expressions | All named expression controls and shared renderer states checked; mouth timing follows converted audio |
| Phone layout | Landscape viewport inspected; handset microphone, speaker and live sensors remain unmeasured |
| Honest latency | Record last synthetic input frame to converted audio, native transcript boundary and converter first byte separately |
| No stale speech | Interrupted generations are discarded; converter and playback backlog are bounded |
| Existing app preserved | Add a new native-voice mode and reuse the current faces; leave the previous text/STT/TTS console available |

Do not call a provider's first-byte time full conversational latency. Do not call a synthetic microphone test a real handset or room-echo test. Keep failures and prompt revisions visible in the evaluation record.
