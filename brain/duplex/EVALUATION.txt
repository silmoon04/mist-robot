Historical initial evaluation. The connection-recovery and faster-start implementation is documented in FIX_REPORT.md and FIX_REPORT.json.

# MIST voice evaluation, 14 September 2026

The native voice and masking path works with the supplied MIST voice. This is a tested development harness; the handset and physical robot were not connected.

The final social cases measured 2.17 to 2.92 seconds from the last uploaded synthetic microphone frame to the first converted audio packet (median 2.53). The final tool cases measured 5.06 to 5.81 seconds (median 5.38). These are client-side packet measurements, before the browser's small playback buffer; they are not physical microphone-to-speaker measurements. Earlier fixture runs used sleep-based pacing that stretched input, so those latency values are not mixed into the final summary.

Converter first-byte time across the final social/tool samples had median 0.71 seconds and range 0.64 to 1.58. This excludes native voice processing and input chunk accumulation. It must not be advertised as total conversation latency.

The interruption test cut off a story, requested blue teacup, and received that correction. Zero old-generation audio packets arrived after the reset acknowledgement. The local clock reported reset within one clock tick, which is not evidence of zero physical latency. Browser playback cancellation and stale-packet rejection passed separate tests.

All offline test commands passed. The existing face checker covers forty faces, 1,600 expression pairs and 31,050 states; twenty expression controls were exercised in an 851 by 393 landscape browser viewport. The mouth follows converted PCM playback. A synthetic converted recording was transcribed again to check broad intelligibility, with differences from the native transcript retained in the raw evidence.

The conversation passes covered greeting, correction, tired-user companionship, a requested joke, sensor availability, phone-pan preview, stop, memory, recall, quiet waiting and returning. Prompt changes reduced unnecessary questions and corrected the pan/USB explanation. The final prompt still cannot guarantee a particular style on every response. The owner should judge the recorded sample and actual conversation on the phone.

## Representative observed replies

- greeting: That’s wonderful. I’m really glad you got them done. How did the assembly go?
- correction: Fair correction. Printed, not walking. I’ll keep it grounded.
- tired: Got it. No advice. I’m here with you.
- humor: I’m basically a very confident paperweight right now.
- sensors: I’ve only got stale phone-motion data, so, no current readings, no camera or valid body sensors reporting.
- pan: Alright, thirty degrees left is prepared as a preview; motors aren't connected.
- stop: Preview stopped.

## Remaining work

- Observed social latency is seconds, not a claimed subsecond response.
- Tool-backed turns remain slower than ordinary voice conversation.
- Provider probes included one startup timeout and one early conversion failure; the latter failed silent with original audio muted.
- A later slow conversion motivated the 3-second live deadline and clearing pending old speech on a new user turn.
- Small audio chunks can introduce seams. Converted speech was checked with ASR, not certified by a human listening panel.
- Quiet waiting can keep the native transcript turn open until the next utterance.
- Saved preference wording can reflect model or recognition errors; exact stored text is shown in the transcript.
- Room echo cancellation, Mi 9 SE microphone/speaker behavior, wireless transport and live sensors need handset testing.
- No calibrated servo transport, camera producer or body-attitude fusion is enabled.

The original text/STT/TTS console is preserved. The new mode reuses its face assets and Codex transport but keeps physical robot actuation unavailable. See README.md for launch, pairing, phone routing and the optional SensorServer adapter. EVALUATION.json contains hashes of the exact evidence and current implementation.
