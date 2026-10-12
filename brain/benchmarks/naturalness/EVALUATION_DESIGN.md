# Evaluating MIST in conversation

Judge whether MIST participates appropriately and helps the person, not whether it produces the most speech or the fastest acknowledgment. The shared chat supplies useful scenario ideas, not verified claims about available products. Keep a profile of results; do not combine correctness, speed and human ratings into an arbitrary overall naturalness score.

## Five layers

| Layer | Repeatable test | Evidence and limits |
| --- | --- | --- |
| Contracts | Deterministic event replay: stop, cancellation, stale task revisions, duplicate calls, missing sensors, playback history and expression commands. | State changes and receipts establish application behavior, not conversational understanding. |
| Text conversations | Persistent sessions with multi-turn corrections, emotional changes, ambiguous motion language, useful tools and memory. | Score tool choice, task completion, unsupported claims, unwanted advice, repair and relevant recall. Text cannot establish prosody or acoustic interruption skill. |
| Timed audio | Fixed recordings with annotated speech boundaries, pauses, overlap and the same words delivered differently. Repeat on the intended phone, including speaker echo and noise conditions. | Separate ASR, decision, tool, synthesis, packet arrival and device playback times. Replay cannot capture how a person adapts to the response. |
| Human interaction | Blind, randomized A/B sessions with the same task goals and device conditions. Include both ordinary conversation and interruption tasks. | Ask about timing, ease of interruption, tone fit, continuity, usefulness and willingness to continue. Record task success separately from preference. |
| Longitudinal | Revisit corrected preferences, unfinished tasks and deleted memories across dated sessions. | Check relevant recall, supersession, restraint, follow-through and identity consistency. Simulated date changes test logic; they do not establish a week of pleasant use. |

## Measure the useful moment

Record first acknowledgment and **first useful response** separately. A useful response answers, asks a necessary clarification, confirms a meaningful correction, or reports verified progress. An unrelated filler phrase does not qualify. Annotate its onset against the scenario goal; retain reviewer disagreement. Also measure completed-task latency and the proportion of trials with no useful response. Silence can be correct when the person asks to finish or be left quiet.

For turn-taking, report false interruptions during continuations/backchannels, missed genuine interruptions, speech-end to useful-audio onset, interruption-onset to last unwanted audible sample, false restart rate and coherent resume rate. Track stop-speaking separately from cancel-task. Link mouth/expression timing to played audio and the intended conversational stance. An audio packet, scheduled playback and audible sound are different observations; none proves that the user understood it.

## Comparisons that can support a decision

Freeze cases, labels, rubric, configuration and thresholds before comparing. Use paired cases with repeated independent sessions, alternating/randomized AB and BA order within the same time windows. Reset application state between variants; preserve it within each conversation arc. Record model/provider versions, source and prompt hashes, hardware, concurrency, warm/cold startup and failures. Match audio recordings exactly for replay; match goals rather than forcing identical dialogue in live sessions. Report paired differences and uncertainty at the independent session/person level, not by pretending correlated turns are separate participants. Report p50, p90/p95 and sample counts; tail estimates from small samples remain uncertain. Timeouts stay visible as failures/censored outcomes rather than disappearing from latency summaries.

Human reviewers should not see configuration labels or the preferred hypothesis. Counterbalance order, allow ties and "cannot tell", and collect brief reasons linked to moments in the recording. Distinguish the participant's experience from an observer's impression. Disagreement is evidence to inspect, not a reason to select the favorable rating.

Keep development, locked regression and held-out scenario families separate. Changing phrasing alone does not create a new held-out case. Once a failure influences a prompt, move that case into development/regression and replenish the holdout. Retain every run; never select a lucky rerun as the result.

## Ablations and release decisions

- **No Jev:** use the documented baseline turn policy with everything else fixed. Compare backchannel/continuation false stops, genuine-stop misses, stop latency and decision overhead. Record which controller actually owns the floor; two active policies would invalidate the comparison.
- **No backchannels:** disable optional acknowledgments, keeping answers and interruptions intact. Compare useful-response latency, perceived attentiveness, premature agreement, annoyance and unnecessary speech duration.
- **No memory:** disable persistent retrieval/write while retaining current-session context. Compare cross-session task success, relevant recall, false personal claims, needless repetition and user preference. Include cases where memory should remain unused.

Attach each failure to its scenario, trace, transcript/audio time and likely stage. A mistaken happy reaction after a hesitant clause and a correct reaction played late require different fixes. Use critical gates for unauthorized/unrequested actions, stale results, stop behavior, false claims of completion and memory deletion. Predeclare acceptable non-inferiority margins for those outcomes and compare confidence bounds; a speed win cannot compensate for a failed gate. Require no critical failures in the deterministic suite while acknowledging that a finite test cannot prove a zero real-world failure rate. Mark unmeasured, unsupported and underpowered results explicitly. Release a change only when the targeted benefit is supported and the critical behaviors remain acceptable.
