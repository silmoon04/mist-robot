# What this conversation asks MIST to do

You expect one coherent conversational character: it understands corrections, does the requested demonstration, controls its own expressions, and gives a small sign of attention during a long wait. The current pieces can work individually while the interaction still fails. This recording shows both reasoning mistakes and missing application controls.

The audit covers all 32 user transcripts and 30 generated assistant replies in the supplied active-session export. It includes discarded generations and the final acknowledgement that correctly received no extra answer. The original export contains no microphone recording, output audio or captured display frames. Timings here use matching server receipt clocks; a browser playback notice is not an acoustic measurement.

## Expectations and evidence

| Expected behaviour | What went wrong | Benchmark requirement |
| --- | --- | --- |
| Recover from recognition errors using context | “Here” was later corrected to a greeting. The sad/angry correction could describe an unwanted result; MIST chose angry without resolving that ambiguity, and the user then explicitly requested sad. | Explicit correction, ambiguous correction and genuine target changes. Accept one focused clarification when the evidence is insufficient. |
| Let the user finish | “Can you tell me” received an answer before “anything funny?” arrived. | Timed incomplete clauses paired with complete questions. Measure false starts and interruption recovery, not just transcript accuracy. |
| Demonstrate faces when asked | Three face requests were issued in roughly 7 ms; the browser skipped curious. | Ordered visible states with enough settled time to inspect each, plus a separate receipt-only tool check. |
| Keep the expression during speech | Several expressions returned to neutral before their associated speech began. A 3000 ms retry ended 2.815 s before playback. | Speech/expression overlap, persistence through pauses and explicit brief-flash controls. Expression duration should not accidentally become a lasting user preference. |
| Understand what “too long” refers to | A complaint after a long explanation became a 400 ms face hold. | Ambiguous brevity complaints, explicit shorter speech, and deliberate shorter display duration. |
| Be warmer without becoming burdensome | Requested emotion became a story about loneliness and being trapped. | Grounded warmth, context-fitting humour and concise repair. Review relevance and emotional fit rather than counting emotion words. |
| Report what is actually known | A face receipt became a claim about the screen; missing clock/search tools became claims about the entire system. | Separate requested, accepted, rendered and observed states. Test both unavailable capabilities and positive controlled fixtures when implemented. |
| Acknowledge a long wait without holding up the answer | Some turns were silent for many seconds; one analyst result waited behind the initial response. | First reaction, first useful content and task completion reported separately. Include fast answers, resumed speech, cancellations, quiet requests and repeated turns. |

The exposed tools currently lack a clock, web search, persistent expression state and an ordered expression scheduler. Those requests are partly application requirements. A stronger model cannot obtain those capabilities merely by reasoning for longer. The text benchmark therefore distinguishes missing capabilities from model errors.

## Where the waits occurred

Across 29 measured user responses, median commitment-to-public-text was 1.215 s and commitment-to-playback-notice was 1.759 s. Two discarded attempts remain missing observations, not zero-duration successes. The respective descriptive P90 values were 6.143 s and 7.578 s; this single conversation does not establish a population tail.

- “Try again”: 13.134 s to public text and 13.691 s to playback notice.
- “Twice hard one”: 9.404 s to playback notice. The transcript itself was unclear.
- “Based on the day today”: 3.878 s passed before the next model generation even started.
- The analyst job completed in 2.074 s. The initial acknowledgement started at 2.846 s, while the later report started at 11.485 s. The completed job waited 4.511 s before its delivery was queued.

These observations put much of the worst delay before public text, with an additional orchestration delay in the analyst example. They do not establish that every delay is model reasoning: queueing, provider request latency and delivery policy also matter. The detailed stage evidence and event IDs are in `TIMING-AUDIT.json`.

## Acknowledgements and Jev

The reasoning task should start immediately. A separate controller can decide whether a brief acknowledgement would help while that task is pending. Making the same reasoning model begin its answer with “let me think” is insufficient: that phrase may arrive only after its reasoning delay.

The controller needs to know whether the user has finished, whether useful speech is ready, whether the user requested quiet, whether a cue was recently used, and whether the turn has been superseded. An acknowledgement must be cancellable both before and during playback. A ready answer should not wait behind an unnecessary sentence about working on it.

“Hmm” is not always neutral. Depending on delivery it can convey thought, doubt, disagreement or disinterest. Compare short nonverbal cues, a brief task-appropriate phrase and silence in blinded listening trials. Mandatory filler is a useful negative control, not the intended product behaviour.

TypeSafe's Jev selects bounded decisions from textual state; it does not generate speech or directly hear prosody. It could help with semantic turn completion or choosing whether to acknowledge, but it is unnecessary merely to produce an early cue. Start by benchmarking a simple selective controller; add a semantic decision model only if it improves the errors that remain. See the [official scope](https://docs.typesafe.ai/introduction/coding-agents) and [state contract](https://docs.typesafe.ai/concepts/state).

## How to use the benchmark

The first unchanged baseline ran all 36 cases with Qwen 3.8 27B at low reasoning. It completed 26 text conversations, totalling 55 turns, with no backend failures. The remaining 10 cases require timed audio, rendered frames or controlled capability fixtures and were recorded as unsupported. There were two failed objective checks: one sad-face retry issued two expression calls, and one request for autonomous affect was not followed by an expression call on the next emotionally relevant turn. Those checks are distinct from semantic review and do not constitute an overall naturalness score.

Median time to first nonblank public text in this isolated text baseline was 982 ms; the maximum was 5129 ms. These start at the model call, exclude microphone processing and audio playback, and come from shorter fresh sessions. They must not be interpreted as a measured improvement over the uploaded voice conversation. All actual replies, receipts, prompt/source snapshots and per-turn timings are retained in `baseline/`.

The draft received one actual Luna review and one actual Sol review. Their feedback reduced coaching, removed unjustified action limits in ordinary conversation, and sharpened the distinction between requests and visible outcomes. Four additional scope/control cases were added after an independent source audit; that addendum did not receive another provider critique. The final suite and review dispositions are saved with their hashes.

A separate Sol review of the completed replies judged 22 text cases as meeting their criteria, two as partial and two as failing. It identified the unsupported explanation of sad speech, missed autonomous face choice, duplicate sad-face repair and unresolved “too long” complaint. These are model-assisted assessments of meaning, not human preferences or a measured naturalness score. The two- and three-turn cases also do not establish resilience over a long conversation; the original trace supplies evidence of that longer context, while controlled long-session replay remains a separate evaluation.

The case set changes the scenarios and includes controls where the correct action is different. It does not prescribe an answer to each sentence from the uploaded chat. Development and validation groups are both visible; neither is an untouched secret holdout. Record whenever either group guides a change, and collect fresh conversations before claiming general improvement.

The text runner creates one fresh model session per case and keeps its actual generated history for subsequent turns. It uses the current voice architecture's foreground prompt, model settings and tool schemas, with isolated application state. Background tool responses are labelled evaluation stubs. Evaluator criteria never enter the candidate prompt. Each run freezes cases, prompt bytes, settings and source files, and retains errors and partial actions.

Text-only runs can establish what was said and requested. They cannot establish audible warmth, ASR quality, full duplex interruption, visible animation, lip sync or physical robot behaviour. Those cases remain unsupported until their required evidence adapter is used. A completed model request is not a semantic pass.

From the repository root, preview the schedule without contacting a model:

```powershell
python brain/benchmarks/naturalness/expectation_bench.py --split all
```

Run a new baseline using an unused output directory:

```powershell
python brain/benchmarks/naturalness/expectation_bench.py --architecture qwen-assist --split all --live --output brain/results/expectations-next-run
```

Reanalyze a fresh exported conversation:

```powershell
python brain/benchmarks/naturalness/expectation_trace_audit.py <LOCAL_HOME>/Downloads/mist-8199b0128136401f9ccbfbba95f0d224.json --output-dir brain/results/expectations-trace-replay
```

For a model or prompt comparison, keep cases, tools, reasoning budget and voice settings matched; interleave repeated A/B runs; report backend failures and missing evidence separately. Review complete conversation trajectories against meaning criteria, not expected phrases. Treat cases as the independent units. A single sample per case is an initial baseline, not a reliable model ranking.

For the voice comparison, record paired interactions and score comprehension, appropriate clarification, warmth, usefulness, unwanted interruption and acknowledgement annoyance without showing the architecture name. Retain disagreement between raters. The event metrics and semantic review can explain a preference; neither replaces listening to it.

No live voice settings, prompts, tools or animation behaviour were changed in this benchmarking pass.
