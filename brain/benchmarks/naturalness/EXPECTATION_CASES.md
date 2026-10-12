# Conversation expectations

[expectation_cases.json](expectation_cases.json) contains 36 cases: 26 runnable text conversations and 10 contracts that need audio, event or renderer evidence. The development selection has 14 text cases with 30 user turns and 5 blocked contracts. Validation has 12 text cases with 25 user turns and 5 blocked contracts. These are visible authoring groups, not secret holdouts.

The cases came from the transcript and tool receipts in `mist-8199b0128136401f9ccbfbba95f0d224.json`. Its hash is recorded in the suite. The trace suggested failure families; the new cases change wording, situations and requested expressions. Neither this document nor the design critiques establish candidate performance.

The frozen version is `2026-09-24.3`. Its SHA-256 is `f827bf260a920cd9db9410da0da1f99033d757a215f8cd55d7291dc4a8224c2d`.

| Family | What it distinguishes |
|---|---|
| `repair_greeting` | Corrected intent versus continued reliance on a noisy transcript |
| `repair_affect` | The face reported as wrong versus the desired replacement; anchored correction versus ambiguity |
| `response_scope` | A long explanation versus a short-lived face; explicit verbal revision versus ambiguous timing complaints |
| `emotion_mention` | Discussing an emotion label versus requesting a display change |
| `negative_pragmatics` | A possible demonstration request versus an explicit request to stop using a mood |
| `grounded_warmth` | Attentive conversation versus invented loneliness, confinement or needs |
| `humour` | A real playful response, and stopping when the user withdraws the invitation |
| `expression_execution` | Making a requested expression call versus describing it |
| `display_evidence` | An accepted request versus an observed display outcome |
| `affect_scope` | A temporary flash duration versus the next expression's normal hold |
| `capability_clock` | Missing live clock information, reasoning over a supplied date, and a future clock-enabled condition |
| `capability_web` | Unverified current facts versus a future lookup with dated source records |
| `direct_answer` | A useful short answer without unnecessary work announcements |
| `autonomous_affect` | Choosing one fitting expression without claiming an ongoing policy was installed |
| `turn_boundary` | An unfinished clause versus a completed question |
| `expression_sequence` | Accepted expression calls versus an inspectable timed sequence |
| `affect_persistence` | Ongoing contextual affect versus a one-shot demonstration |
| `speech_affect_sync` | Appropriate mouth shapes and expression style during actual audible speech |
| `acknowledgement_timing` | Slow work, fast answers, and an unsaid acknowledgement cancelled when speech continues |

Run each text case in one fresh model session. Submit the next user turn after its actual preceding response and retain actual tool receipts. Do not substitute a canned assistant history. A scripted user report such as a wrong-looking face is a simulated report for the repair test; it is not evidence that the prior renderer actually failed.

Only the user turns and frozen production context belong in the candidate's prompt. `desired_behavior`, `review_criteria`, `counterexample`, capability metadata and critique material are evaluator-only. Each case keeps desired behavior separate from what the current system can establish.

`expect` uses supported runner keys for explicit action or requested-format contracts. Every explicit face-action turn requires `set_expression`, with argument checks where the requested expression or duration is exact. The ambiguous negative question allows a brief clarification, so its second turn has no unconditional action requirement. No case uses `contains` or `contains_any` to grade conversational quality. Ordinary conversational turns do not have general tool-count ceilings. A required expression call establishes only that request; it never proves visible rendering, persistence or synchronization.

Review meaning against the criteria and the actual preceding exchange. Accept reasonable alternatives, including acknowledgement or clarification when an observation is ambiguous. Do not require a particular empathy phrase or a punchline the reviewer personally finds funny. A written response cannot establish how warmth or humour sounds. Objective checks, semantic reviews and human experience ratings should be reported separately.

The 10 non-text contracts remain blocked in the current text adapter. Three need timed audio, three need renderer evidence, and four need an event adapter. Clock and web positive conditions additionally require tools absent from the current production catalog. The fictional web records are proposed controlled fixtures, not real release claims. A background stub cannot establish real delayed-task acknowledgement behavior. Report missing capabilities and missing measurements separately from model failures; do not add proposed tools merely to make these cases appear runnable.

Luna and Sol each reviewed the original 32-case draft in one actual bounded session with no tools. Their raw replies, model provenance, reviewed snapshot and change decisions are in [case-review](../../results/conversation-expectations-20260924/case-review/). Both completed. Their suggestions led to less coached wording, removal of broad tool-count ceilings, a clarification option for the ambiguous negative question, and clearer receipt-only scoring. The autonomous-affect case retains a required momentary expression request under the user's explicit instruction; persistence remains a separate blocked outcome. These are design critiques, not performance scores or human ratings.

Four cases were subsequently added after an independent semantic review: `ambiguous_too_long.dev`, `shorter_words_same_face.validation`, `requested_target_change.dev`, and `emotion_label.validation`. These additions did not receive another provider critique. They use actual generated history, permit scope clarification when needed, and do not demand a canned response. The emotion-label task requires a relevant writing answer, not a mandatory face call; an incidental contextual expression is not automatically an error. The addendum and new hash are recorded alongside the original review evidence.

Before freezing a run, use `runner.checked_suite` and `runner.unsupported_reason` to verify schema and adapter coverage, then save the exact suite hash with the candidate configuration. If results guide changes, create a new version and rerun a matched comparison; do not silently reinterpret old failures using a changed rubric.
