# Conversation latency diagnosis

The saved browser timings confirmed the reported delay. Four turns without a model tool call produced their first text in 1.89-3.14 seconds. Two turns involving `face` or `get_capabilities` took 8.53 and 8.69 seconds. Their first tool requests arrived at 3.72 and 2.03 seconds, leaving another 4.81 and 6.66 seconds before text. These measurements are inside the persistent model client, before speech generation.

The reproduction command was `python harness/analyze_turn_latency.py results/mist-v2-browser-live/turn_metrics.jsonl --max-first-text 3`. It failed the three-second first-text budget. `browser_baseline.json` preserves the six timing records without conversation text. The records did not contain queue or RPC-acknowledgement timings, so those stages could not be reconstructed retrospectively.

## Changes

The conversation client now reads a small capability snapshot immediately before submitting each turn. The read does not call a model tool, write robot state, or create bus events. It contains runtime constants, validated availability flags and timestamps. User-written observation summaries, source names, objects, hazards and memory text are excluded before the snapshot enters application context. The latest snapshot supersedes older ones. A current-vision question still requires a fresh `observe` call.

An optional expression can travel in a leading `[[face:name]]` marker in the same answer. A bounded streaming parser validates the expression against the 20 display expressions, removes the marker from streamed and final speech text, and emits a display-only event. It cannot encode movement or another action. Plain text is released on the first delta. The `face` tool remains available for explicit tool requests, and all 18 existing robot tools retain their deterministic handlers and interlocks.

The persona now asks ordinary conversation to answer without decorative tool calls. After a Spark greeting exposed a name-confusion bug, the persona and Codex runtime were also made explicit: the assistant is MIST; a named addressee is someone to address, never an identity to adopt. Faulty model outputs are not rewritten into correct answers after generation.

Per-turn telemetry now records lock wait, capability-read time, RPC acknowledgement time, tool execution time, time from the last tool reply to first text, visible output length and reasoning tokens. High-resolution elapsed timing uses `perf_counter`; the first three optimized Astra probes used the earlier Windows clock, whose roughly 15-millisecond resolution rounded small local stages to zero.

## Bounded live results

No live conversation was interrupted and no voice API calls were made by these probes. The tests used isolated run directories and persistent clients within each short sequence.

| Model and configuration | Probe | First text | Full response | Model tools |
| --- | --- | ---: | ---: | --- |
| Astra, low, priority | Ordinary good-news chat | 3.53 s | 3.55 s | None |
| Astra, low, priority | Capability question | 4.50 s | 4.50 s | None |
| Astra, low, priority | Current-vision question | 5.56 s | 5.58 s | `observe` |
| Spark, low, standard | Greeting with happy cue, before identity fix | 2.46 s | 2.51 s | None |
| Spark, low, standard | Current-vision question | 2.93 s | 2.98 s | `observe` |
| Spark, low, standard | Same greeting after identity fix | 2.18 s | 2.23 s | None |
| Spark, low, standard | Follow-up identity question | 1.05 s | 1.12 s | None |

The optimized Astra capability prompt was identical to the earlier seven-second capability prompt, but the sequence and cache state differed. The new 4.50-second result was 36% lower than the earlier 7.08-second result and required one model response instead of a tool round trip. This is an observed small-sample improvement, not a controlled provider benchmark.

The current-vision prompt was identical in the optimized Astra and Spark probes. Both called `observe` and correctly admitted that the feed was unavailable. Spark's 2.98-second completion was 47% lower than Astra's 5.58-second completion in these two samples. Spark's local observation handler took 4.1 milliseconds, its RPC acknowledgement took 2.6 milliseconds, and lock wait was about 12 microseconds. Its remaining 1.76 seconds after the tool reply came from the model path. Faster hardware for these local reads would not remove that delay.

The initial Spark greeting said "I'm Moon", confusing the recipient with the assistant. That error was reported before activation. After the general identity instruction was added, the same greeting addressed Moon and the follow-up answered that its own name was MIST and Moon was the person speaking with it. Both targeted checks passed. The corrected greeting delivered a happy display cue without a separate `face` call. This retest establishes the correction for those prompts; it is not a broad intelligence evaluation.

Spark's installed catalog supports low reasoning but lists no priority tier. Its standard tier was accepted; the offline request audit shows no `service_tier` override in the outgoing model request. The chosen fast-conversation configuration is therefore `gpt-5.3-codex-spark`, `low`, `default`, while the independent executive remains `gpt-6-astra`, `low`, `priority`. The backend now rejects a priority request for a model whose catalog does not advertise it.

The three Astra probes used 148 reported output tokens. The first two Spark probes used 203, and the two identity retests used 229. Spark exceeded the approximate 50-token target despite short spoken answers. The protocol's output count includes hidden reasoning: in the retest, 71 of 94 tokens and 110 of 135 tokens were reasoning tokens. There is no verified hard assistant-output cap in this CLI. No more live probes were run after the targeted identity check.

## Verification and remaining limits

Eleven Codex contract tests, six streaming-format tests and eighteen robot-tool tests cover the new behavior. The pure snapshot tests verify freshness, exclusion of untrusted text and absence of state or bus writes. The parser tests cover every split point of a valid prefix, leading whitespace, malformed and oversized markers, unknown expressions and immediate release of ordinary text. The exact-CLI loopback audits continue to show 18 model tools for conversation and zero tools in executive mode, with legacy notifications suppressed.

The browser team separately owns duplicate speech requests, playback recovery and end-to-end timestamps. The model timings above do not include speech API generation, audio buffering or actual playback. The live model can still choose a tool unnecessarily or answer poorly; those are model behaviors, not guarantees provided by these samples. The deterministic motion checks, missing-observation behavior and tool allowlist remain in force.

Evidence in this directory includes `astra_optimized_live`, `spark_live`, `spark_identity_retest`, `spark_manual_review.json`, `tool_exposure_after_optimization.json` and `spark_tool_exposure.json`. The initial failed Spark output is preserved unchanged.
