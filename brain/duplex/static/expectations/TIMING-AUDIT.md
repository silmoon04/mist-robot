# Conversation timing audit

Trace `8199b0128136401f9ccbfbba95f0d224`; status `active`. Source SHA-256 `8fda62cd2acb1f80c655833daba3e85c8b793c2372bfaf3021d59b4bf99a92ff`.

All intervals below use the same explicit server receipt clock. Playback means a browser notification, not measured speaker onset. Missing playback and useful-answer annotations are not assigned zero latency.

## Coverage

{"events": 15141, "user_commits": 31, "generation_attempts": 32, "user_generations": 31, "application_report_generations": 1, "completed_generations": 30, "discarded_generations": 2, "with_playback_receipt": 30, "face_commands": 10, "browser_expression_reports": 82, "incomplete_hold_events": 0, "backchannels_preserved": 1}

## Longest waits after user commitment

| Request | Commit → model start | Commit → public text | Commit → playback receipt | Evidence |
|---|---:|---:|---:|---|
| Try again. | 0 ms | 13134 ms | 13691 ms | #12099 → #12100 → #12176 → #12238 |
| Twice hard one. | 0 ms | 9002 ms | 9404 ms | #13512 → #13513 → #13574 → #13614 |
| Based on the day today? | 3878 ms | 6970 ms | 7891 ms | #3633 → #3655 → #3671 → #3737 |
| Make me eight different phases one after the other after the countdown is done. | 0 ms | 5936 ms | 7500 ms | #9645 → #9646 → #9682 → #9790 |
| You don't know what day is today. Can you now check? | 0 ms | 3794 ms | 4296 ms | #4307 → #4308 → #4339 → #4384 |
| You should make some faces when you say the. | 0 ms | 2631 ms | 3231 ms | #7677 → #7678 → #7710 → #7769 |

The JSON retains every generation, interruptions, queue delay and model HTTP-header timings. It does not equate a server thinking state with a visible thinking animation.

Public text means the first nonblank turn.delta published by the model protocol. This is neither a caption-render timestamp nor the onset of speech. Browser speech activity samples during these waits are retained in the JSON; they are sampled observations, not continuous acoustic measurements.

## User-turn latency distributions

| Stage | Observed / all attempts | Missing | Median | P90 |
|---|---:|---:|---:|---:|
| commit_to_model_start | 31 / 31 | 0 | 0 ms | 0 ms |
| model_start_to_nonblank_text | 29 / 31 | 2 | 1214 ms | 4222 ms |
| commit_to_nonblank_text | 29 / 31 | 2 | 1214 ms | 6143 ms |
| commit_to_playback_receipt | 29 / 31 | 2 | 1759 ms | 7578 ms |
| commit_to_public_text | 29 / 31 | 2 | 1215 ms | 6143 ms |
| public_text_to_playback_receipt | 29 / 31 | 2 | 531 ms | 931 ms |
| model_start_to_playback_receipt | 29 / 31 | 2 | 1758 ms | 4937 ms |
| nonblank_text_to_audio_delivery | 29 / 31 | 2 | 359 ms | 746 ms |
| audio_delivery_to_playback_receipt | 29 / 31 | 2 | 174 ms | 188 ms |
| last_asr_final_to_commit | 31 / 31 | 0 | 1 ms | 690 ms |

Missing observations, including interrupted generations, stay in the denominator. These are descriptive values from one conversation, not a controlled model comparison.

## Nearby user turns

- #1913 'Can you tell me' → #1986 'anything funny?': 2430 ms between commitments. Intervening generated answer: #1935 'Yes, go ahead.'. Playback receipts: #1954. Resets: #1962.
- #3601 'So can you guess what model is the latest?' → #3633 'Based on the day today?': 2274 ms between commitments. Intervening generated answer: none. Playback receipts: none. Resets: none.
- #8673 'I mean, you should probably change the face yourself.' → #8708 'And not have a timer for the face itself.': 3294 ms between commitments. Intervening generated answer: none. Playback receipts: none. Resets: none.

These are temporal candidates, not automatic judgments of intent. No incomplete-clause hold was recorded in this trace.

## Face commands and browser state

| Command | Requested hold | Browser application | Next reported state | State lifetime | Displaced before associated playback? |
|---|---:|---|---|---:|---|
| #1508 happy | 2800 ms | #1516 | #1528 smug | 466 ms | yes, by 744 ms |
| #1512 curious | 2600 ms | missing | missing  | unavailable | not established |
| #1520 smug | 1800 ms | #1528 | #1688 neutral | 2400 ms | not established |
| #7696 sad | 2200 ms | #7700 | #7841 neutral | 2831 ms | not established |
| #10802 curious | 400 ms | #10806 | #10849 neutral | 1042 ms | yes, by 384 ms |
| #12142 curious | 3000 ms | #12146 | #12166 neutral | 3611 ms | yes, by 2815 ms |
| #13170 happy | 400 ms | #13174 | #13204 neutral | 1031 ms | yes, by 313 ms |
| #13551 angry | 400 ms | #13555 | #13564 neutral | 1017 ms | yes, by 2062 ms |
| #13890 angry | 400 ms | #13894 | #14007 neutral | 1031 ms | not established |
| #14304 sad | 400 ms | #14308 | #14334 neutral | 1024 ms | yes, by 246 ms |

Browser expression records describe selected state. They do not prove that a full raster face remained visibly settled for that duration. Matching uses expression name/pinned state because the browser records do not carry originating command IDs.
- #1508 happy was followed by another face command after 4 ms, before its requested hold elapsed.
- #1512 curious was followed by another face command after 3 ms, before its requested hold elapsed.

## Background acknowledgement versus result response

- Job `d5ae313514e3`: started #5283; terminal #5403 (complete); queued #5622. Initial response playback #5349 arrived 2846 ms after user commitment. The separate report response #5700 arrived after 11485 ms.
  The job finished in 2074 ms; it waited 4511 ms before delivery was queued. Last browser idle receipt → queue was 1 ms. Queue → report playback receipt was 3590 ms. No useful-answer/audio onset was annotated; these are not interchangeable with that metric.
  Initial generated response: "Kicked it off. It can peek at the same sensor feed I do, so we'll see if anything's hiding there.". Separate generated report: "Same result as my own read. No timestamp, no clock anywhere in the feed. Unless you tell me, I'm flying blind on the date.". Generated wording does not prove all those words were heard.

## Mouth while speech is inactive

There are 505 browser speech samples, including 296 with audio_active=false. 0 of those request a speech viseme other than rest or none. This does not establish whether the idle/listening artwork itself has an open mouth.
At #12583, the user asks 'Why do you keep your mouth open?'. In the preceding ten seconds, 9/10 sampled speech states were inactive. The JSON records their IDs; no actual mouth raster or screen frames are available.

## Signals needed to settle the remaining questions

- Final voiced microphone sample on an attributable clock; ASR-final receipt is not speech end.
- Recorded speaker audio/acoustic onset and cutoff; the trace removes PCM payloads.
- Renderer frame/asset IDs and mouth geometry/openness for idle, listening, thinking and transitions.
- Activity-overlay state/frame telemetry to verify whether thinking is visibly communicated.
- A face command ID propagated through renderer acceptance, transition completion and expiry reason.
- Human or scenario-rule annotations for useful answer onset, intended continuation and perceived expression.

The export is marked active. Counts describe the captured interval only; an active export does not establish an unfinished model generation.

No provider calls, browser changes or production fixes were performed by this analyzer.
