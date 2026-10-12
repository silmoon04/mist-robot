# Hands-free Talk mode

The console was restarted when the task began: port 8776 had no listener, and a hidden Python process was launched with the saved run directory. The API verified Spark low reasoning for chat, Astra for background work, speech protocol 2 and eight restored conversation messages. No microphone was opened during that restart.

Talk is an explicit button. It requests microphone capture only after a click and then submits completed utterances without Enter or Send. The indicator shows when capture is active, and Stop talk aborts pending recognition/submission, closes the audio context and releases media tracks. Normal listening resumes after each accepted utterance while the model and voice can continue asynchronously.

The capture path uses an AudioWorklet to collect mono PCM in 20 ms batches. Local activity detection retains 200 ms of pre-roll and waits for 650 ms of trailing silence. It requires 250 ms of voiced audio, caps a clip at twenty seconds and uses stronger input sustained for 220 ms to detect interruption during playback. Each resulting clip is a complete PCM16 WAV at the actual capture sample rate.

The session controller serializes recognition and submission. Duplicate Blob callbacks share one operation, overlapping utterances during that operation are dropped, and stale results cannot submit after Stop or overwrite a restarted session. A new spoken utterance stops local playback and requests interruption of an active model reply. The final pre-submit check also catches a replacement reply that began while transcription was pending. Reply ownership is cleared when interruption starts, so a late old `turn_end` cannot restart its voice. The existing player also rejects stale audio responses after cancellation.

## Streaming activation

The first batch-recognition sample took 6.3896 seconds, so a separate loopback proxy was added on port 8788 without replacing the original console process. Production origins are restricted to the console on port 8776, and the Deepgram key remains in the proxy. Confirmed microphone frames stream in paced PCM16 packets while the person speaks. Startup buffering preserves the lead-in, and cancellation invalidates old results. The original WAV route remains a service-failure fallback; stopping does not invoke that fallback.

The real paced saved-audio provider probe recognized the full 3.68-second clip with zero word errors. It produced an intermediate transcript 1.118 seconds into the audio and a final transcript 0.373 seconds after the last PCM packet. The total included realtime audio delivery, so it must not be described as four seconds of waiting after the person stopped. These numbers are one diagnostic sample, not a latency guarantee. `STREAMING_STT_REPORT.md` and `streaming_stt_paced_probe/result.json` retain the provider evidence, including rejection of an earlier truncated result.

The browser integration was then checked with saved virtual microphone audio and a fake provider through the actual proxy protocol. It completed one stream start and one final, submitted one chat turn and played one saved reply. HTTP batch-transcription calls remained zero. The UI reported `recognition=streaming` and returned to Listening; Stop talk returned it to Mic off. `streaming_browser_counts.json`, `streaming_browser_proof.json` and `streaming_browser.png` record that check. No additional provider calls were used for browser verification.

One fixture failure was caught before accepting the browser result: the test attempted to overwrite a method on the client's frozen export, so its fake-proxy override did not apply. The corrected fixture replaces the export object and disables real microphone construction before configuring the saved stream. The corrected run, not the earlier fallback run, supplies the zero-HTTP-call proof.

## Browser and provider evidence

The browser fixture replaced `getUserMedia` with a stream generated from an existing synthetic WAV. Its injector was verified before clicking Talk. It did not request an operating-system microphone permission or capture room audio.

One Talk click produced one endpointed WAV, one fixture transcription, one automatically submitted chat turn and one saved reply playback. No Enter or Send click was used. Listening resumed afterwards. A second saved utterance was injected during saved voice playback: its metadata reported `bargeIn=true`, and it produced one additional transcription and chat turn. Totals were two transcriptions, two chat turns and three saved speech requests, including the deliberately triggered preview. Stop talk returned the button to unpressed and the indicator to Mic off. The browser recorded no console errors.

The first capture was 3.68 seconds of mono PCM at 48 kHz. One Deepgram batch check returned every expected word, with word similarity 1.00 and confidence 1.00. API time was 6.3896 seconds. This cold sample demonstrated correct audio boundaries but motivated the streaming path described above. No paid language-model or TTS calls were made for this check.

The latest `captured_utterance.wav` and JSON are from the later interruption capture, which was 3.67 seconds. The earlier 3.68-second recognition result is recorded in `deepgram_capture_check.json`; the fixture overwrote its original WAV during the second capture. Both inputs came from the same saved synthetic phrase.

## Validation and limits

Thirty-nine capture tests cover sample rates, exact lead-in/tail retention, stream/WAV equivalence, interruption qualification, bounded duration, worklet batching, permission races, pending delivery and resource release. Twenty session tests cover asynchronous recognition/submission, duplicate utterances, interruption ordering, aborts and stale callbacks. Thirty-seven client tests cover the paced WebSocket protocol; seven adapter checks cover successful recognition, fallback and cancellation. Six provider-engine and seven proxy tests exercise final coverage and protocol isolation. The UI ownership tests additionally cover a late old completion after Talk interruption and after Stop reply. The full offline runner is recorded in `offline_checks.txt`.

The browser requests echo cancellation, noise suppression and automatic gain control. Those requests do not prove acoustic cancellation on the user's hardware. This is not a native full-duplex speech model: it uses local activity detection and separate recognition, text-model and TTS stages. Real microphone/speaker echo performance has not been tested, and sustained background noise may be mistaken for speech.

During feature activation, automatic approval review rejected a combined process-tree restart command with the reason `blocked by policy`. That command did not execute. The already-running server supported the necessary recognition, chat and interruption routes, so the completed Talk client was activated through static files without stopping it again. `rejected_restart_command.txt` preserves the exact rejected command. Later backend transport activation is coordinated separately by the root task.
