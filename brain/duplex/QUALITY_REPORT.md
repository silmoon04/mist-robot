# MIST playback revision

The 400 ms first upload was too short to preserve context and could finish playing before the next passage arrived. The current bridge uses a consistent 1.8-second cap, preferring pauses after 800 ms of context. A completed short phrase can still flush earlier after silence. The browser adds a 200 ms startup reserve and schedules subsequent audio packets contiguously. A three-second audio burst no longer triggers the old backlog reset.

Microphone capture continues during playback. Volume alone no longer cancels speech: native user-turn events clear the old playback generation, including audio already delivered to the browser. Stop speaking remains immediate. Browser echo cancellation is requested, but this does not establish reliable room echo handling.

Thinking uses a closed line mouth and a slight upward, sideways gaze. Listening and speaking remain distinct. Thinking is explicitly selected while preparing a response or checking a tool, and speech animation follows the playback clock. Updated asset URLs prevent stale cached mappings from concealing the revision. The thinking pose was visually checked in the app browser.

The backing Spark model, native Codex voice path and MIST voice ID are unchanged. Voice Changer accepts finite audio uploads and streams their converted output. ElevenLabs' incremental text WebSocket is a possible alternative for a later comparison, but would synthesize a new performance from text.

## Checks and remaining uncertainty

All 33 offline application contracts, six conversion recovery tests, browser scheduler checks and 31,050 renderer states passed. Three live synthetic conversations returned converted audio without error or warning. First converted packets arrived 2.56, 3.91 and 2.67 seconds after the final synthetic microphone frame. The browser reserve adds another 200 ms when playback starts.

The latest native-turn interruption and explicit-stop trials cleared old audio generations, followed the correction and produced new audio. One initial explicit-stop trial produced the corrected transcript but no converted correction audio within the observation window. That failure remains in the evidence; passing repeats do not establish that it is fixed.

These tests do not establish human-perceived voice quality, seamless conversational overlap, loudspeaker echo rejection or Mi 9 SE performance. Independent conversion requests still have a latency and prosody tradeoff. The current build is ready for another listening trial, not a claim of production voice reliability.

Evidence: brain/results/voice_quality_20260914. The JSON companion records exact implementation hashes, tests and observations. Earlier FIX_REPORT files describe the superseded 400 ms first-segment policy and remain historical records.

API references:
https://elevenlabs.io/docs/api-reference/speech-to-speech/stream
https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/realtime-tts
