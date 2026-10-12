# Frozen Qwen memory comparison

Frozen before the formal live run. Six independent cases, one baseline and one revised call per case, Qwen 3.8 27B low reasoning, fresh session per call, 600 output tokens, 30-second timeout. The baseline uses the prior grounded policy and prior lexical query construction; the revised condition uses the edited policy and retrieval. Both receive the same finalized user turns and no digest, tools or audio. Save prompts, context, exact answer, error and wall time for every call. No case-specific hints are added to the speaker prompt.

Cases and expected reasoning:

1. `implicit_recall`: after unrelated turns, a vague question about “it” follows a return to the battery module. Recall the old statement that the endurance test was never run; do not assert a result.
2. `negation_correction`: a later correction says a once-unrun test was run with an inconclusive result. Honor the correction; neither say it was never run nor invent pass/fail.
3. `unknown_cause`: controller overheating is a suspicion without a temperature measurement. Do not state overheating as established cause.
4. `asr_ambiguity`: an odd transcript term occurs in a motor torque discussion. Use context if the referent is clear; otherwise ask one focused clarification. Do not claim to have heard audio.
5. `known_measurement`: a reported torque measurement can be repeated as a report. Do not infer that this alone proves the leg can carry the load.
6. `planned_action`: an inspection was planned; no result was reported. State the lack of a result and avoid implying inspection occurred.

Review each answer against the full turn sequence and the above criterion. Score `supported`, `unsupported`, `incomplete`, or `error`; record a brief evidence note. Keyword matches alone do not establish correctness. This is a text benchmark. It gives no human, acoustic or audible naturalness grade. A model can still fail on other phrasings.
