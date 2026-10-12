# MIST brain integration, 7 September 2026

The console now runs GPT-6 Astra with low reasoning through the installed Codex client, uses the existing MIST (refined) ElevenLabs voice, and delivers independent background research while chat continues. Main-page speech uses the audio playback clock. Motion remains simulated with the deterministic 50 C cutoff.

The browser run used Codex CLI 0.153.4. The requested Fast tier was accepted as `priority`. Its installed catalog says "2x speed, increased usage"; this run did not compare Fast and standard tiers, so it does not claim a measured twofold speedup. See `codex_tool_exposure_audit.json` and the provider report for the exact outgoing tool registry proof.

## Live browser results

| Operation | First reaction | Model total | Result |
|---|---:|---:|---|
| Short greeting | 2.344 s | 2.375 s | Natural one-sentence reply; ElevenLabs synthesis took 0.836 s |
| Arithmetic while research ran | 1.891 s | 1.906 s | Correct answer, 391, while the background job was still active |
| Happy expression and twenty-word reply | 3.719 s | 8.547 s | Real `face(happy)` receipt, followed by speech; synthesis took 1.051 s |

The background research task completed in 7.469 seconds, including search, three successful page fetches, model startup and a 4.672-second model summary. It retained the official Python queue documentation, Real Python and a Python 3.6 documentation mirror as separate sources. The UI displayed the result, source links and retrieval limitations. A second research request was cancelled from the browser and remained cancelled.

The three conversation turns reported 10,905 input tokens and 151 output tokens. The research summary reported 2,793 input tokens and 71 output tokens. These are provider-client usage observations, not an account bill. The independent backend validation suite is separate and is documented by its own agent; do not count its twelve paid turns as part of these three browser turns.

No browser console errors were observed. The final renderer was reloaded in the studio, and a sustained silent mouth preview remained `data-speaking=true` after switching to happy 14. Stop reset it to false. The main console reached real ElevenLabs `playing` state, and Stop reply left audio paused, the speech status quiet and the face speech layer stopped. Timing correctness is also tested against a held and advancing media clock in the actual player module.

The requested 390 by 844 viewport override did not take effect in the browser integration: measured document dimensions remained 1280 by 720. Phone layout is therefore not claimed as tested. `browser-reloaded.png` records the actual desktop viewport after reload.

## Voice usage and limits

Four short clips were generated in total: two dedicated alignment checks and two browser replies. They used the existing **MIST (refined)** voice, `24AMj4dc02cYAwoUnqzN`, with `eleven_multilingual_v2`.

| Measurement | Observed total |
|---|---:|
| Input characters | 257 |
| Generated audio | 13.7926 s |
| Provider-billed characters reported in headers | 128 |
| TTS API time across all four requests | 5.6837 s |
| Audio sent to Deepgram for word checks | 6.7802 s |
| Deepgram word scores | 0.90 and 1.00 |

The lower word score was the robot's name, MIST, being transcribed as "missed". Both dedicated clips returned ordered character timestamps and passed pause-closure checks. Mouth shapes are spelling approximations rather than provider phoneme labels. Word fidelity does not establish voice likeness or perceptual lip-sync quality. No new voice was cloned. No dollar amount is inferred from character usage or subscription tokens.

## Bugs reproduced and fixed

The original speech request race was reproduced with two overlapping requests: the actual UI played `newer` and then incorrectly played `older`. The player now aborts the prior request and checks request ownership before changing audio. Its regression test also covers cancellation during fetch, playback completion, provider errors and a paused media clock.

The face agent reproduced collapsing mouth thickness and insufficient edge clearance in the legacy renderer. Its repaired renderer passes 31,050 sampled states across forty faces, eleven mouth shapes and all 1,600 expression pairs. The tests require at most one visible mouth during transitions and verify pause and completion behavior. The full visual comparison and Aseprite export are in the `faces` directory.

Review also identified three lifecycle faults. A server restart could show an interrupted task as failed without writing a failure to the robot's inbox; a delayed scheduler pass could start queued work after shutdown; and a stop between accepting chat and starting its model call could be lost. All three now have regression coverage. Restart writes one failure receipt, the scheduler checks its stop flag inside its lock, and each accepted conversation turn owns a cancellation latch.

The final full offline runner passed: fifteen robot-tool checks, nine Codex client tests, the existing grounding and benchmark checks, the HTTP job lifecycle tests, face-map and geometry checks, speech-player races and speech-provider parsing. Targeted UI checks passed again after the final shutdown ownership cleanup. No further provider calls were needed for that cleanup.

## Reproduce

From `brain`:

```powershell
python ui/server.py --port 8776 --run-dir results/mist-v2-browser-live
python harness/run_offline_tests.py
```

Open the console at `http://127.0.0.1:8776/`. Use Background task to submit research, then send a normal chat message while its card says running. Cancel task records a terminal cancellation. The face studio is at `/face/`. Provider setup and the Gemini alternative are documented in `brain/docs/MIST_CONSOLE.md`.

Evidence: `integration_evidence.json`, `browser-turn-metrics.jsonl`, `browser-speech-metrics.jsonl`, `browser-jobs.json`, `browser-desktop.png`, `browser-happy.png`, `browser-expression-during-speech.png`, and `voice/voice_check.json`. The screenshots are from local browser interaction, not generated mockups. The expression-during-speech screenshot uses the studio's labelled silent preview; it is not a recording of live ElevenLabs audio.
