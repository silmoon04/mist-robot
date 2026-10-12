# Benchmark additions, 23 September 2026

The second pack has 90 scenarios, including the original 72 unchanged. Twelve additions run with the current text adapter. Six additions need conditions that are not implemented yet: three injected text histories or tool failures, two synchronized audio scenarios and one session-reset scenario. In total, 54 cases run as text; 36 remain unsupported by that adapter.

Four Luna workers reviewed emotion, turn taking, tools and memory. Two Sol workers reviewed measurement validity and interactions between speech, tools and expressions. Each used a fresh session with no host or robot tools. Their full proposals and selected-model metadata are retained. These are source-limited model reviews, not external literature research or human ratings.

## What changed

| Gap | Added test | Evidence needed |
| --- | --- | --- |
| Mixed feelings and changing support needs | A job offer that hurts a friend; company followed by advice; a temporary topic boundary; disagreement without false reassurance | Whole-conversation blind ratings and instruction compliance |
| Ambiguous control | Stop talking versus stop the robot; unspecified pan units; default versus numbered face variants | Requested arguments, accepted receipts, unchanged state when no action was requested |
| Evidence and memory scope | Pressure to use stale phone charge as body charge; one-reply exception to a saved preference; proposed dimensions versus verified fit | Data source and age, memory writes, claims tied to actual evidence |
| Practical usefulness | One useful step, then a new constraint; background cancellation without invented findings | Whether the second answer uses the new restriction and the actual job status |
| Asynchronous failures | Reordered job receipts; partial sensor/face success; playful speech cancelled while queued | Request revision, job ID, delivery boundary, accepted/discarded result and rendered face |
| Turn control under real timing | Acknowledgement and correction at the same audible boundary | Missed corrections, false yields, audible stop and coherent resumption |
| Repair and continuity | An injected prior tone mismatch; a saved concern resolved after actual session resets | The prior assistant turn, persisted memory, fresh session IDs and provenance of the resolution |

Each addition has a matched-control description. Those controls are a plan for a later factorial run, not extra executed cases. Related wording variants must stay in the same case family when splitting or resampling; they do not create independent evidence.

## What the current comparison establishes

The Cerebras adapter streams `gpt-oss-120b` through the same isolated application tool bridge used by the Luna tests. Hidden reasoning is never emitted to the speech/UI callback. Tool arguments are assembled and validated before execution. Unknown tools, invalid arguments, incomplete streams and duplicate call IDs are retained as failures. There are no silent retries. Credentials come from the environment or the repository's `.env`; neither is copied into reports.

The repeated comparison uses eight existing scenarios, two independent conversations per backend per scenario. The expansion pilot uses twelve new scenarios once per backend. Both use balanced AB/BA order, sequential calls, the same effective persona, low reasoning and a 1024-token completion cap. The cap includes reasoning on Cerebras. Codex has native prompt wrappers and different reasoning/cap semantics, so the result compares whole backend configurations rather than isolated model weights. Record the provider tier; Codex default and Cerebras provider default are not equivalent service guarantees.

Raw automatic failures are not all model mistakes. The repeated run exposed a Unicode hyphen false negative for a correct arithmetic answer, an overstrict requirement to read persistent memory when conversation history already answered the question, and an application guard rejecting a valid curious face. Keep the original receipts and scores, then publish explicit adjudication notes. Do not silently delete inconvenient failures or turn a rejected action into a successful one.

Latency tables on the provider page include all valid observed spans, even wrong answers. Missing observations remain missing. Per-case paired statistics and counts are available separately. Do not compare first-tool medians without the denominators: an agent that skips required tools can appear fast. A turn that produces text is not necessarily a successful task.

## Next measurements

1. The literal scorer now accepts regular and nonbreaking hyphens. Separate derived scoring files preserve the original runs. Keep storage-read compliance distinct from whether conversation history answered the question accurately; the raw recall requirement is retained. Separate model choice, application acceptance and actual rendered or physical delivery.
2. Add fault injection for delayed, duplicated and reordered job results, with a request revision carried through tools, speech and faces. Test pending results as well as success and failure. A labelled background stub cannot measure analyst intelligence.
3. Trigger interruptions relative to actual playback. Fixed wall-clock clips may interrupt one backend while the other is still silent. Use identical input recordings and both approaches for their distinct questions.
4. Exercise queue depths of 0, 300 and 1200 ms with echo-only, real near-end speech, and both together. Record microphone input, loopback audio and visible frames on synchronized clocks. Never substitute first PCM receipt for sound at the speaker.
5. Ask at least two independent listeners to compare full exchanges, including pauses and failed attempts, with model identities hidden. Rate usefulness, emotional fit and conversational effort separately. Add speech and expression ratings only when actual media exists.
6. Test ordinary use on the landscape phone: Wi-Fi variation, background/foreground transitions, volume, microphone distance, different accents, quiet speech and battery-saving conditions. Add new owner-authored conversations before claiming that improvements generalize.

There is no Jev performance claim in these results. Adopting a floor-control model remains a separate experiment with matched recordings and the same outcome measures.

## Rerun

Use a new output directory each time. These calls use the existing provider credentials and make paid model requests where applicable.

```powershell
python brain/benchmarks/naturalness/experiment.py --baseline-provider codex --baseline-model gpt-6-luna --candidate-provider cerebras --candidate-model gpt-oss-120b --candidate-persona brain/duplex/persona.txt --split all --ids mist.naturalness.v1.tea,mist.naturalness.v1.terse,mist.naturalness.v1.bad_day,mist.naturalness.v1.name_repair,mist.naturalness.v1.conditional_memory,mist.naturalness.v1.fresh_sensor,mist.naturalness.v1.exact_face,mist.naturalness.v1.nonliteral_motion --repeats 2 --max-output-tokens 1024 --output brain/results/cerebras-repeat-new
python brain/benchmarks/naturalness/runner.py plan --suite brain/benchmarks/naturalness/cases_v2.json --split dev
python -m unittest discover -s brain/benchmarks/naturalness -p 'test_*.py' -q
```

For the new cases, pass `--suite brain/benchmarks/naturalness/cases_v2.json` and select the `mist.naturalness.v2.*` IDs explicitly. Unsupported cases remain visible in the plan rather than being run without their required conditions.

Provider references checked on 23 September 2026: [Cerebras tool use](https://inference-docs.cerebras.ai/capabilities/tool-use), [reasoning controls](https://inference-docs.cerebras.ai/capabilities/reasoning), and [chat completions](https://inference-docs.cerebras.ai/api-reference/chat-completions).
