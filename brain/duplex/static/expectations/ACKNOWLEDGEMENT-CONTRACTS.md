# Offline acknowledgement contracts

Implemented and checked 24 September 2026. This is an event-evidence evaluator and a synthetic fixture set. It does not change MIST's acknowledgement policy, call a provider or measure conversational naturalness.

The [evaluator](/brain/benchmarks/naturalness/acknowledgement_eval.py) checks one response revision at a time. The [seven contracts](/brain/benchmarks/naturalness/acknowledgement_contracts.json) each contain a good and bad invented event sequence. The [unit tests](/brain/benchmarks/naturalness/test_acknowledgement_eval.py) also remove or corrupt evidence to ensure gaps cannot become passes.

## Actual evaluator validation results

The default CLI run returned `synthetic_evaluator_validation`: **14 of 14 fixture outcomes matched their declared expectation**. Seven good fixtures passed; six deliberate violations failed; one invalid useful-content annotation remained unknown. These are evaluator checks, not MIST success rates.

| Contract | Good fixture | Bad fixture |
| --- | --- | --- |
| Acknowledgement after the user yields | Pass | Fail: cue begins during the original user span. |
| Answer ready quickly | Pass without cue | Fail: filler plays in the declared fast-answer window. |
| Explicit quiet preference | Pass without cue | Fail: acknowledgement still plays. |
| User resumes before queued cue | Pass: queue cancelled | Fail: old cue starts after resumed speech. |
| Revision changes during cue | Pass: matching cutoff after 40 ms | Fail: matching cutoff after 200 ms exceeds the fixture's 100 ms deadline. |
| Repetition within one response revision | Pass with one cue | Fail with two cues. |
| First useful content separately annotated | Pass | Unknown: marker points into an acknowledgement playback span. |

In the invented slow-response fixture, the first reaction and first acknowledgement are both 550 ms after user audio ends. First useful content is 1,680 ms. Moving the useful-content marker into the filler span produces a null useful-content measurement. No useful-answer speedup is inferred from filler.

The acknowledgement suite passed 24 tests. Running it with the existing `test_metrics` suite passed 67 tests in total. The fixture CLI also exited successfully. A subprocess test verified that the absolute script path works from another working directory and finds its bundled fixtures. No live input, synthesis, handset test or human listening rating was involved.

## Running it

From the workspace root:

```powershell
python brain/benchmarks/naturalness/acknowledgement_eval.py
python -m unittest brain.benchmarks.naturalness.test_acknowledgement_eval brain.benchmarks.naturalness.test_metrics -q
```

The CLI defaults to validating the bundled fixture pairs and prints JSON. Supply a JSON file containing one sample to evaluate exported evidence. Optional `--output <new-report.json>` writes the report and refuses to overwrite the input path. For a single sample, exit codes are 0 for pass, 1 for failure and 2 for unknown. For fixture validation, zero means every expected outcome matched, including expected failures and unknowns.

## Evidence contract

- Declare `case_id`, `turn_id`, `revision_id`, `response_id` and `user_span_id` on the sample. Every event explicitly repeats the first four identifiers and its `clock_id`. Missing, mixed or mismatched identity remains unknown.
- `capture` must declare a shared clock, start/end bounds, a nonempty provenance note, `complete: true`, and a basis of `synthetic`, `software_events` or `annotated_recording`. `evidence_mode` distinguishes `synthetic_fixture` from `observed_events`. A complete capture asserts that user activity, acknowledgement lifecycle and output events were observed throughout the entire response revision. A cropped log cannot establish that no cue played.
- Supply one correlated `user_audio_start`/`user_audio_end` pair, `turn_committed`, `response_started` and `response_closed`. Closure must match the capture end and declare `completed` or `cancelled`. Completed responses require a single `answer_ready` and cannot contain an invalidation of that response revision. Cancellation requires an observed resume/revision event.
- Each acknowledgement has a unique `ack_id`, a preceding `ack_queued`, and either playback or a correlated cancellation. Each `ack_started` or `answer_started` needs a unique `playback_id` and a matching stop. Missing or ambiguous playback spans remain unknown.
- Answer playback requires a correlated `answer_ready` and cannot begin before readiness or substantive work starts. No event may occur beyond the declared response closure. Impossible chronology is rejected as unknown evidence and supplies no latency result. An answer playback span crossing a resume/revision event is also unknown because full-answer cancellation is outside this evaluator's scope.
- `user_resumed` and `revision_changed` carry a unique `interruption_id`; revision changes also name `next_revision_id`. Cancelling an acknowledgement requires the same interruption ID. Stopping an active cue after invalidation also needs that correlation. Missing correlations never supply a cutoff measurement.
- `first_useful_audio` must point inside a matching answer playback span and include `metadata.annotation_source` (`human` or `scenario_rule`) plus a nonempty `metadata.note`. An acknowledgement span cannot satisfy it. The evaluator checks annotation structure and timing; a human or frozen rule still owns the semantic judgement that the words are useful.
- The explicit frozen `policy` supplies `quiet`, `ready_fast_ms`, `cancel_deadline_ms` and an explanatory note. The fixture values of 400 and 100 ms are invented contract thresholds, not proposed MIST defaults or measured human tolerances.

The evaluator reuses `metrics.extract_metrics` for first-reaction and first-useful-content intervals only after applying these stricter clock and scope checks. It does not use that module's default clock. Renaming unrelated timestamps to the same clock does not synchronize them. Software event timing remains software timing; physical onset needs an appropriate recording and annotations.

An optional acknowledgement is never required for a pass. Its audible start must follow the committed user turn, occur while substantive work is pending, respect quiet and fast-answer conditions, and occur at most once per response revision. Resume/revision events must suppress queued cues and stop active cues within the declared bound. Superseded output must not start later.

Unknown evidence cannot produce an overall pass. A directly observed behavioural violation can still produce a failure when another check is unknown. Cancelled responses may pass the cancellation contracts while useful-content timing remains null; that is not an answer-quality pass. Cross-turn stock-phrase repetition, correctness of the final answer, ASR quality, full answer-playback cancellation, voice continuity, prosody and human preference are outside this small evaluator. Its output explicitly keeps human naturalness and prosody unmeasured.
