# MIST debug and expression inspection

Two new routes are linked from Conversation controls: /debug and /expressions.

The live debug page shows a bounded server timeline with native model phases, tool arguments/results, application handler durations, background jobs and their read-tool calls, TTS phrase and connection events, browser playback starts and queue depth, microphone frame/RMS summaries, and expression changes. Filter by category or text, pause updates, expand event details, clear the local view, or export its filtered trace. Debug data requires the same pairing cookie as the conversation. Server restarts have a distinct trace identifier so old cursor values do not mix two timelines.

The server retains 2,000 events in memory and pages without skipping retained records. Raw PCM and known authentication fields are excluded. Audio delivery is sampled per reply at half-second intervals; microphone and queue summaries arrive once per second. Conversation text and tool arguments remain available for debugging, so exports should be treated as conversation records. No hidden model reasoning is collected.

Timing labels distinguish the native connection, model turn, application tool execution, TTS first byte, and transcript completion to playback. The last interval excludes native speech-end detection. Browser and server performance clocks are separate; server event time records arrival, not synchronized wire latency.

The expression inspector uses the actual MIST renderer and data: 40 face variants, 20 named presets and 11 visemes. It includes a looping gallery and focused view, all-viseme speech, the production AA/rest pattern, a single held mouth shape, idle motion, blink inspection and expression transitions. Gaze, mouth amount, transition duration, playback speed, glow and bounds are adjustable. Pause, scrub or step by 1/60 second. Backward seeks rebuild and replay the renderer so its transition state can be inspected consistently. Export the current clean SVG or its JSON geometry from the page.

The inspector makes no model or microphone calls. The all-viseme sweep is a synthetic diagnostic, not a claim that live speech has phoneme alignment. It does not edit production face assets.

## Verification

A real synthetic conversation produced native connection timing, a sensor-tool call, model activity, TTS timing, playback and expression records. A real background analysis produced its separate sensor-tool start/end and timing events. The browser reported no JavaScript errors. Category filtering and narrow-screen layout were inspected.

All 40 gallery variants loaded. A held AA mouth on the happy face at frame 12 (200 ms) produced byte-identical geometry after stepping forward and back. The face renderer's existing 31,050-state verification passed. Five new diagnostic contracts verify bounds, redaction, paging, audio sampling and pairing; existing application, TTS, background and playback tests also passed. Export functions are present; no real microphone recording or phone-acoustics validation was performed.

Evidence and check logs: brain/results/debug_views_20260914. DEBUG_REPORT.json includes the exact implementation hashes used for the source archive.
