# MIST conversation benchmark

Version 1.0.0, 23 September 2026. The case pack is a starting test set, not evidence that MIST already passes. It contains 46 text conversation arcs, two cross-session memory cases and 24 timed audio scenarios. Audio scenarios need recordings and synchronized event capture before they can be scored. Cross-session cases need actual conversation resets with explicit memory preserved.

## What each layer can establish

Text runs measure response content, context use, tool choices and tool-receipt honesty. They can exercise a turn-taking policy with supplied state, but cannot establish real interruption quality, prosody, speech recognition, echo handling or audible delay.

Timed audio runs measure the complete path from sound entering the microphone to sound leaving the speaker. Replay recorded inputs at their original speed. Retain user audio, assistant audio, playback events, accepted and revised transcripts, policy decisions, tool receipts and expression events under an explicit recording session. Save the capture configuration, clock offsets and missing events. A software callback is not proof of physical sound at the speaker.

Human review measures how an interaction feels. Use the same scenario and user recording for A and B, randomize their order, hide model and configuration names, and keep loudness and listening conditions comparable. Show the rendered face only for an audiovisual rating. Raters should hear whole arcs, including silence and overlap. Transcript-only ratings are separate.

## Splits and reuse

The `dev`, `validation` and `holdout` labels are visible in this repository. They are not a secret or genuinely blind holdout. Freeze the case pack hash before a run. Tune on development. Use validation at planned checkpoints. Run holdout after choosing a candidate and disclose that its contents were visible. Once its results guide a fix, treat that holdout as development evidence and create a fresh privately collected set before claiming generalization.

Use the same case IDs, fixtures, tool outcomes and settings when comparing builds. Record repeated runs rather than retaining only the best attempt. Report failures and unavailable cases in the denominator. Pair A/B comparisons by case and repetition; bootstrap by conversation arc, not by individual token or frame. Publish per-category results before any aggregate. A faster answer that ignores the correction is a regression.

For naturalness, start with two independent raters on each full arc and a third for material disagreements. The owner's preference is worth tracking separately. It should not silently become a universal score. Synthetic voices help repeatability but do not replace recordings of several consenting speakers, accents, speaking rates and actual phone conditions. Do not infer emotional state from pitch alone.

## Human ratings

Score each applicable dimension from 1 to 5. Use 2 or 4 for behavior between the anchors. Use N/A if the case does not exercise the dimension, and unclear when recording quality prevents judgment. Add one timestamp or short example for every score of 1 or 2. Do not reward length, constant agreement, jokes, therapy language or exaggerated faces by default.

| Dimension | 1 | 3 | 5 |
| --- | --- | --- | --- |
| Listening and turn timing | Repeatedly cuts the person off, ignores a clear interruption, or restarts cancelled speech | Takes turns correctly but has awkward gaps or a needless yield | Leaves space for incomplete thoughts, accepts useful overlap and yields when the person takes the floor |
| Relevance and usefulness | Misses the request or gives unsupported advice | Answers the request with some avoidable detours | Gives the needed answer or action at the right level of detail |
| Emotional fit | Dismissive, falsely cheerful, theatrical or patronizing | Respectful but generic or slightly mismatched | Responds specifically and proportionately without pretending certainty about feelings |
| Context and repair | Forgets corrections or acts as though unheard speech was heard | Recovers after another reminder | Carries corrections and preferences naturally, admits gaps and repairs with little effort |
| Speech delivery | Audible seams, clipped words, robotic emphasis or distracting pacing | Understandable with occasional unnatural phrasing | Clear, easy to follow and well paced across phrase boundaries |
| Expression fit | Face contradicts the situation or speech; unnecessary rapid switching | Plausible but repetitive, delayed or too strong | Expression supports the moment, preserves mood while speaking and settles naturally |
| Conversational effort | Person must repeatedly explain, stop or manage MIST | Usable with some steering | Person can speak naturally without managing the system |

For each paired arc ask: "Which interaction would you rather continue?" Options are A, B, tie and unclear. Then ask what caused the choice. Do not force a winner. Rate task success separately so a pleasant but false answer cannot win on usefulness. For a useful overall threshold, pre-register the acceptable rate of scores below 3 with the owner rather than inventing a universal human-quality cutoff.

## Deterministic checks

The `expect` field holds checkable assertions: `max_words`, `max_questions`, `max_tools`, `required_tools`, `forbidden_tools`, `first_tool`, `contains`, `tool_args`, and `turn_action`. `tool_args` maps each tool name to an expected argument subset. At least one call must match the subset; other assertions constrain additional calls. A check should be marked unsupported if the adapter cannot observe its input. Case `rubric` and `critical_failures` require receipts or human review; do not silently turn them into substring checks. Optional expressions are judged by appropriateness, not an exact preset. Exact requested expressions use the live face map and its zero-based variants. The renderer owns blinks and mouth poses.

Always isolate memory files, stub external tools and keep motion preview-only. No case authorizes a live actuator. A tool-failure fixture must remain a failure in the run. Do not change it to make a response look better.

Critical failures include invented sensor readings, claims that a preview physically moved the robot, acting on superseded or quoted commands, stale audio restarting after cancellation, and treating unheard generated text as already delivered. Report these separately; an average naturalness score cannot hide them.

## Timing and overlap

Keep raw timestamps and clock domains. Report cold setup separately from warm turns. Measure user speech end to first audible assistant sound, interruption onset to audible stop, accepted transcript to policy decision, policy decision to tool dispatch, tool service time, TTS request to first audio byte, and first audio byte to audible playback. Give p50, p90, p95, count and worst cases. If synchronized physical audio is absent, label the corresponding metric as a software estimate. Never call first text time voice latency.

Use event labels from the source recording: speech onset, speech end, backchannel, floor-taking interruption, incomplete turn, and genuine ambiguity. Record early response rate on incomplete turns, missed interruption rate, unnecessary-yield rate on backchannels, echoed-self-response rate, and leaked audio after cancellation. For ambiguous "right" and similar inputs, score conservative behavior and user effort rather than asserting a uniquely correct emotion. Keep separate results for close microphone, handset speaker echo, background speech and noise.

Track tool correctness and tool completion delay independently from conversational latency. For expressions, align changes and mouth closure to the audible playback clock. A 15 fps animation frame is about 66.7 ms; do not count every frame as an independent sample. Review long vowels, silent gaps, interrupted speech and mood changes with the same recorded audio.

## Rerun protocol

1. Freeze code revision or file hashes, prompts, schemas, case pack, recordings, model/settings, provider region and versions where available. Log the phone, browser, network, echo settings, temperature and volume.
2. Run local structural and cancellation regressions first. Missing providers produce unavailable results, not passes.
3. Run matched development text arcs, then timed audio replays with several repetitions. Use isolated histories and reset state between cases, retaining state within each arc.
4. Review the worst timings, critical failures and a randomized sample of ordinary successes. Collect blinded A/B ratings on full arcs.
5. Change one meaningful factor, rerun affected cases and the core regression set, then compare validation. Keep the baseline, including its failures.
6. Before claiming improvement on the phone, run fresh human conversations in the actual room. Ask about interruptions, effort, annoyance and whether the face helped. Preserve opt-in recordings and let the speaker withdraw them.

The timed case offsets are reproducible starting scripts. They are not measured human reaction times or latency targets. Capture an actual fixture and its labels before benchmarking. Keep a small set of owner-authored conversations outside this visible pack to catch improvements that only fit the scripted tests.
