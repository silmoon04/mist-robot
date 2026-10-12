# Live qwen-affect smoke, 24 September 2026

This probe connected to an isolated live_studio process on port 9054 through the real TrialConversation route. It bootstrapped a session, selected qwen-affect, sent three typed turns, and captured the public server trace and outgoing ElevenLabs PCM. The session ended cleanly with reason disconnected. No error events occurred. The speaker and affect reader each returned HTTP 200 responses on all their provider requests.

| Turn | Speaker first text after user commit | Affect result after user commit | Timing and action | First audio packet | PCM |
| --- | ---: | ---: | --- | ---: | ---: |
| Explicit curious face and hinge answer | 3346.0 ms | 2039.5 ms | Accepted neutral/no-change decision applied 1306.5 ms before speech. Speaker's curious tool request returned display_requested with persistent=true. | 5123.7 ms | 6.233 s |
| Exhibition stand collapsed | 1434.7 ms | 1502.7 ms | Reader proposed sad plus gentle delivery, but arrived 68.0 ms after speech started. Guard returned speech_already_started; no director face packet was emitted. | 2051.0 ms | 2.119 s |
| Keep current face unchanged | 554.5 ms | 559.7 ms | Reader proposed no face change plus warm delivery, but arrived 5.2 ms after speech started. Guard returned speech_already_started. No face tool or face packet followed. | 984.8 ms | 4.301 s |

The speaker finished its model turns in 3375, 1438, and 578 ms. The affect reader's provider totals were 2025.2, 1492.1, and 546.4 ms, with first-token times of 1962.2, 1458.9, and 545.2 ms. The three TTS speech_style receipts all selected neutral delivery and stability 0.5. ElevenLabs completed all three replies and the server sent 129 audio packets, 607,376 PCM bytes or 12.654 seconds at 24 kHz mono.

The wiring works: the real speaker, reader, expression tool, and ElevenLabs stream all ran in one TrialConversation. The meaningful emotional suggestion missed the speech boundary in this sample and was correctly discarded. The early accepted decision on turn 1 proposed no affect change because the user explicitly requested the face. These three turns therefore do not demonstrate a timely applied non-neutral delivery or autonomous face change.

The input was typed through the trial WebSocket. The audio files contain PCM packets received by the probe; no browser playback or human hearing was tested. The curious face receipt establishes an accepted request, not visible rendering. The probe sent playback_state=false after each complete reply only to clear server bookkeeping.

Evidence: public-trace.json contains the server-redacted 282-event export; timeline.json extracts relevant receipts and timings; probe-summary.json records each turn; turn-1.wav, turn-2.wav, turn-3.wav and all-turns.wav contain the outgoing PCM. The server's separate run directory and process identity were recorded under live-smoke/server-20260924T164417Z.
