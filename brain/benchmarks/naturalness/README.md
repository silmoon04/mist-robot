# MIST conversation benchmark

This suite separates what MIST says, what it does, when it does it, and how the exchange feels. It does not combine those into a single naturalness score.

The cases draw on [the shared design conversation](https://chatgpt.com/share/6ab449d2-b774-83eb-99cc-1d681877ce6a) and failures in the existing MIST tests. The shared chat is design input, not verification of its vendor or model claims. Its extracted messages are saved in `reference/shared_messages.json`.

## Run it

For the Cerebras comparison and the expanded 90-case pack, see [EXPANSION.md](EXPANSION.md). `experiment.py` supports `--baseline-provider codex` and `--candidate-provider cerebras` with `--candidate-model gpt-oss-120b`. The original 72-case pack remains the default for repeatability; pass `--suite brain/benchmarks/naturalness/cases_v2.json` to use the expanded pack. The current literal scorer normalizes regular and nonbreaking hyphens. `rescore_checks.py` can produce separate derived check records for frozen older runs without replacing their raw scores.

Use these commands from the repository root. `validate`, `plan`, `contracts`, `score`, `compare`, and `review` make no model calls. `run` uses the signed-in Codex model through the existing isolated application adapter. It never opens a microphone or drives motors.

```powershell
python brain/benchmarks/naturalness/runner.py validate
python brain/benchmarks/naturalness/runner.py plan --split dev
python brain/benchmarks/naturalness/runner.py contracts --output brain/results/naturalness-contracts-new
python brain/benchmarks/naturalness/runner.py run --split dev --repeats 3 --output brain/results/naturalness-baseline-new
```

Output directories must be new so a failed run or older baseline cannot be overwritten. Each conversation uses a fresh session and temporary application state. Turns within that conversation share context. Background-task calls use the existing labelled stub; this adapter cannot establish real background reasoning performance. Production prompts, preferences, and model settings stay unchanged.

For a candidate, pass `--persona path/to/candidate.txt`, `--model`, `--reasoning`, or `--service-tier`. Keep the scenarios, fixtures, output limit, concurrency, and hardware conditions matched. Change one factor at a time. The run freezes its cases and effective persona, records source hashes and configuration, retains failures, and writes a report after completion. `run.json` is checkpointed after each case.

```powershell
python brain/benchmarks/naturalness/runner.py compare --baseline brain/results/naturalness-baseline-new/run.json --candidate brain/results/naturalness-candidate-new/run.json --output brain/results/naturalness-comparison.json
python brain/benchmarks/naturalness/runner.py review --baseline brain/results/naturalness-baseline-new/run.json --candidate brain/results/naturalness-candidate-new/run.json --output brain/results/naturalness-review-new
```

Prefer the paired `experiment.py` runner for a controlled comparison. It alternates configurations within case/repetition blocks. Two complete runs taken at different times remain vulnerable to different service load. Identical settings in both arms form an A/A repeatability check; they do not demonstrate improvement.

```powershell
python brain/benchmarks/naturalness/experiment.py --candidate-persona brain/duplex/persona.txt --ids mist.naturalness.v1.tea,mist.naturalness.v1.bad_day,mist.naturalness.v1.sensor_frame,mist.naturalness.v1.exact_face --repeats 3 --output brain/results/naturalness-aa-new
python brain/benchmarks/naturalness/ratings.py --key brain/results/naturalness-review-new/answer_key.json --ratings path/to/reviewer1.json path/to/reviewer2.json --output brain/results/naturalness-human-ratings.json
```

Keep only one export per reviewer per review pack. The ratings aggregator detects duplicate files but cannot prove that separate files came from different people. It reports missing ratings and separate dimensions, not a fabricated overall preference score.

## What to compare

| Layer | Evidence | Can establish |
| --- | --- | --- |
| Application contracts | Offline production tests | Cancellation, stale results, bounded actions, timing transport and renderer invariants |
| Text conversations | Real model replies and tool receipts | Context, repair, requested tools, grounded claims, text latency |
| Timed speech replay | Recorded input, event trace and output audio | Recognition, overlap behavior and transport timing; speaker timing needs playback evidence |
| Blind human review | Paired whole conversations | Emotional fit, usefulness, effort, voice and expression quality when present |
| Repeated use | Sessions on separate days | Corrected preferences, unfinished commitments, stable character and memory boundaries |

The text adapter reports timed-audio, device, or longitudinal cases as unsupported. They remain visible in coverage. A scripted time jump is not a week of actual use. A refusal of an incorrect tool call can protect the application while still being a model-choice failure.

The current pack has 72 cases: 46 text, 24 timed audio and two longitudinal. Of the 46 text cases, 42 work with the current text adapter. Four require explicit delayed/error/background/delivery-history fixtures and remain unsupported until those adapters exist. A generic reply to their user text would not exercise their intended condition.

Read `RUBRIC.md` for anchored ratings and `EVALUATION_DESIGN.md` for the trial design. Holdout labels are visible to the developers and are not a secret test set. Once a holdout result informs a fix, disclose that use and collect fresh cases for a new generalization claim.

## Timing

Record the end of the user's speech, transcript availability, committed turn, first text, first complete phrase, first useful audible response, each tool request and result, playback start/stop, and visible expression changes separately. A filler word must not win the meaningful-response metric.

All metric pairs need a matching case, turn, and clock. Concurrent tools need call IDs. Multiple interruptions need interruption IDs. Do not subtract a browser clock from a server clock without measured synchronization and uncertainty. Negative or missing spans remain unmeasured; they are never clamped to zero.

Reports contain medians, P90, P95, counts, missing observations, failures, and category breakdowns. Small samples carry a warning about tail estimates. Paired comparisons use matching cases and repetitions, with conversation-level resampling. Timing changes alone do not produce an overall winner.

`score` accepts the normalized run format in `EVENTS.md`, so audio capture, a future Jev adapter, or a phone test can reuse the scorer without masquerading as the text path.

## Human review

The review page randomizes A/B positions, hides model/configuration names, and exports ratings. Keep `answer_key.json` private; share only `review.html` and its optional media folder. Give reviewers complete exchanges rather than the best isolated replies. Preserve pauses and overlaps. Transcript-only comparisons cannot rate voice, physical timing, or facial expression.

Use at least two independent listeners for early comparisons, plus the owner's preference as a separately reported result. Ties and uncertainty are valid answers. A short timestamped reason for a preference is more actionable than a bare score. Model judges can help find issues, but should be calibrated against these human ratings and must not decide that an unheard recording sounds natural.

## Iteration rule

1. Freeze the baseline, case version, settings, and review rubric.
2. Run an A/A sample to estimate variation and expose measurement errors.
3. Identify a specific failure, such as stopping on acknowledgements or speaking before a correction finishes.
4. Change one component and run matched A/B repetitions. Retain unsuccessful and timed-out runs.
5. Review whole conversations blindly, then check relevant categories and critical failures.
6. Accept the change only if it improves the intended behavior without a material regression. Increase the sample if the result is uncertain.

Useful ablations are no Jev versus Jev, no backchannels versus selective backchannels, no retrieved memory versus retrieved memory, and current versus revised expression policy. Use the same input recordings and conditions. More visible activity is not itself an improvement.

## Current limits

For recorded input, `audio_replay.py --help` describes the server transport adapter. Start a dedicated fixture-enabled server with a fresh run directory, then provide a 16 kHz mono PCM16 WAV and annotated user spans. On this computer, ports 8738 through 9037 are currently reserved by Windows; use an available port such as 9041 after checking it.

```powershell
python brain/duplex/server.py --enable-fixtures --run-dir brain/results/naturalness-audio-server-new --port 9041
# In another terminal, set MIST_PAIR_CODE to that server's printed code.
python brain/benchmarks/naturalness/audio_replay.py --base-url http://127.0.0.1:9041 --case-id mist.naturalness.v1.audio_backchannel_yes --fixture path/to/input.wav --annotations path/to/turns.json --output brain/results/naturalness-audio-new
```

This replays fixed input timing, receives output packets and saves traces. It does not run a real browser speaker, adapt interruption timing to when MIST actually starts speaking, or establish per-turn audible latency. Native-to-fixture turn correlation currently remains unknown. It sends no invented playback acknowledgements; this also limits background-result delivery tests. Those capabilities need a browser/device adapter before the corresponding cases can pass.

The suite and test tooling are implemented separately from adopting Jev. There is no claim that Jev improves MIST yet. Audio-only cases require recorded fixtures and live capture; human ratings require actual reviewers. The last saved provider failure in the older harness is not treated as current provider status. No new synthesis availability claim follows from an offline test.
