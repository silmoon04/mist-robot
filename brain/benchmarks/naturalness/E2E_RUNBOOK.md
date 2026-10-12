# Voice benchmark

The input pack contains 26 synthetic speech scenarios. It covers acknowledgements, corrections, stop requests, pauses, reading, emotional changes, expressions, soft speech, noise and digital echo. The browser sends the recorded input through the real voice connection and records the production audio player and face canvas.

The measurements distinguish three kinds of evidence:

- Browser E2E: recorded input, recognition, reply, ElevenLabs synthesis, scheduled playback and rendered face. Playback time is a browser output-clock estimate. The captured audio is digital output.
- Component replay: controlled delayed, cancelled and reordered background results through the production coordinator. Transports are recording doubles.
- Human assessment: listening and face ratings. These remain unrated until someone actually reviews the recordings.

## Run the same inputs

From the repository root, start a new isolated server. Every run needs a new output directory. The existing input WAVs are reused without another synthesis request.

```powershell
python brain/benchmarks/naturalness/lab_server.py --port 9044 --run-dir brain/results/my_voice_comparison/native_full --fixtures brain/results/e2e_20260924/fixtures_v2
```

Open `http://127.0.0.1:9044/lab` and click **Run all cases**. Keep the tab visible. The lab does not open the microphone. It uses a fresh robot state for each case and no actuator connection. The server stores input hashes, source snapshots, browser traces, audio and face video. Treat its run directory as private: server diagnostics and local session state are not a public report.

For the experimental text pipeline:

```powershell
python brain/benchmarks/naturalness/lab_server.py --port 9045 --run-dir brain/results/my_voice_comparison/cascade_selective --fixtures brain/results/e2e_20260924/fixtures_v2 --backend cascade --provider cerebras --model gpt-oss-120b --floor selective
```

This uses Deepgram Nova-3 recognition, Cerebras for replies, ElevenLabs for speech and a separate Luna background worker. Recognition stays active during playback. The `selective` floor policy is a lexical experiment: short acknowledgements may preserve playback. It is not a semantic turn-taking model. Use `--floor cancel_all` to compare immediate yielding on detected speech. Use `--provider codex --model gpt-6-luna` to compare the foreground model with the same STT/TTS path.

Use `--endpoint-ms 700` to compare with the default 300 ms setting in a fresh `cascade_endpoint700` directory. It does not add semantic turn completion. Run the same case several times in alternating condition order before treating a difference as reliable. Browser URL selections accept repeated IDs; each capture receives a new sequence folder.

Native Codex voice uses its own realtime speaking model. Its Luna backing model handles delegated tools; calling the whole native path “Luna voice” would be inaccurate.

Use `?ids=mist.naturalness.v1.audio_phrase_seam,mist.naturalness.v1.audio_abbreviation` on `/lab` for a subset. Inputs scheduled during a reply are triggered relative to actual browser playback, not a fixed offset from the API request.

## Analyse

```powershell
python brain/benchmarks/naturalness/e2e_metrics.py --group native=brain/results/my_voice_comparison/native_full --group cerebras=brain/results/my_voice_comparison/cascade_selective --output brain/results/my_comparison.json
python brain/benchmarks/naturalness/async_fixture_cases.py --output brain/results/my_async_replay
python brain/benchmarks/naturalness/audio_capture_audit.py brain/results/my_voice_comparison/native_full brain/results/my_voice_comparison/cascade_selective --contact-sheet
python brain/benchmarks/naturalness/e2e_report.py --source brain/results/my_voice_comparison --output brain/results/my_voice_report
```

To include the input players and downloadable input pack in a new report, copy `brain/results/e2e_20260924/fixtures_v2` into the new comparison directory as `fixtures_v2`. The report discovers the named conditions `native_full`, `native_rerun`, `native_capture_fix`, `cascade_selective`, `cascade_cancel_all`, `cascade_luna` and `cascade_endpoint700`. Audio, video and input files are published through an allowlist; private server state and logs are excluded.

Blind listening includes only continuous-clock recordings with a matching media audit. **Play reply** seeks within the original file to just before speech. It does not trim or combine the files. Within-reply pacing is a listening question; reaction latency comes from the separate browser measurements.

The first-response comparison uses only a single input without seeded or overlapping output. It separates startup, user transcript finalization, first reply text, first received audio and first scheduled playback. A nearby audio packet is not automatically a response to the latest user turn. Reset counts are observations, not a quality score: “yeah” and “stop talking” need different behavior.

For memory across resets, use `fixture_cases.py run --memory-context production-prefill`. This matches the app's saved-context startup behavior. The `tool-only` condition is a separate retrieval experiment. Neither condition simulates real days passing.

## Interpretation

Keep failed runs and capture timeouts. Fixing a fixture or measurement requires a new run; do not replace the original evidence. A completed schedule means inputs and capture completed, not that the conversation was good.

The current synthetic pack uses one English input voice. The noise case is a non-speech surrogate, not a recorded cough. Digital echo bypasses the microphone and browser echo cancellation. Sarcasm, varied accents, acoustic echo, actual speaker cutoff and human emotional fit need additional recordings or listening review. Generated assistant text does not prove which words a person heard before an interruption.

When comparing models, keep input, prompt, tools, floor policy, TTS settings and playback buffering fixed where possible. Report remaining differences. Repeat cases in balanced order before making a reliability or percentile claim. The first native/cascade batch is a pilot, not a statistically powered model ranking.
