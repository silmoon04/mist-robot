# Expectation runner review

Reviewed `expectation_bench.py`, its tests, the current 32-case dataset, and the production clients/runtime it uses. No provider calls or production changes. Six existing expectation-runner tests pass. Additional temporary fake-client probes reproduced the failures below; these are runner tests, not model results.

## Blockers before comparing runs

1. **Codex architectures fail before the first turn.** `run_case` reads `client.prompt`, which exists on CerebrasClient. CodexClient stores the supplied production prompt in `_system_prompt` and has no `prompt` attribute. The CLI accepts the Luna architecture, but each sample fails with AttributeError. A fake using the actual Codex field contract reproduced this without contacting a provider. Return the actual frozen prompt from `production_client`, or resolve the two supported client contracts explicitly. Test both provider shapes; the current fake always supplies `.prompt` and misses this defect.

2. **Unexpected turn failures lose executed actions, and cleanup failures escape the runner.** If `ask` raises after a tool executes, `run_case` records only the outer error and never appends the in-progress turn. A local probe executed `set_expression`, emitted its event, then raised TimeoutError: the saved sample had zero turns and zero receipts. If `client.close` raises, the exception escapes `finally`, no `sample.json` is written, and the outer run stops without appending that sample. A cleanup probe reproduced this with an otherwise successful turn. Preserve the attempted turn's events, receipts, before/after state and failure before cleanup; catch cleanup errors separately and always write the final sample. Distinguish attempted turns from successful completed turns: the current counter increments even when `result.errors` is nonempty.

3. **The frozen suite can disagree with the suite actually executed.** `run` calls `checked_suite(args.suite)` to obtain parsed cases and a digest, then separately reads the path to create `cases.frozen.json`. A file change between those reads produces a manifest hash and executed cases from one version with a different frozen dataset. The dataset is being edited in parallel, so this is relevant now. Freeze the same bytes that were parsed and hashed, or verify the later bytes match before any provider call. This finding is from the code path; no existing result has been established as mismatched.

## Evidence boundaries that currently look sound

- Only each user utterance reaches `ask`; review criteria, desired behavior and counterexamples remain outside model input. The production persona and tool schema come from `CascadeVoice.make_client`.
- A fresh temporary runtime and client are created per case, with the same client retained for successive turns. Current production adapters retain their generated history. RuntimeBridge labels background work as a stub.
- All required expression arguments in the current text dataset were exercised through the real isolated RuntimeBridge without rejection. No impossible expression fixture was found.
- The dataset currently contains 22 text cases and ten non-text contracts. Non-text modes are explicitly unsupported. Voice, rendered expressions and semantic scores remain unknown; a completed request is not labelled a quality pass.
- Current Codex and Cerebras adapters emit only public text deltas. The runner should still filter `assistantMessageEvent.type == text_delta` explicitly, because its present catch-all would persist a future reasoning delta and count it as first text. This is a defensive contract gap, not evidence that these runs leaked reasoning.

The timings describe local text generation, not audio. `total_ms` presently also includes state inspection and objective grading after `ask` returns. If used for provider latency comparisons, capture request completion before that local work and label the separate measurement. This runner does not implement an interleaved paired comparison; separate architecture runs should not be presented as one without a matched schedule and preserved configuration.

The visible development/validation split is correctly described as authored material, not an unseen test set. Later changes informed by these cases must be recorded as such.

## Fix verification

Rechecked the revised runner and ran all ten expectation-runner tests successfully, without provider calls. The three original blockers are resolved:

- Codex clients now use their `_system_prompt` fallback, so the `.prompt` interface mismatch no longer stops a case.
- A raised `ask` preserves the attempted turn, captured public prefix, executed receipts, tools and before/after state. Attempted and completed counts are separate. Cleanup errors mark the sample failed while retaining its final saved evidence.
- Suite bytes are read, checked against the parsed suite's digest, then those same bytes are written to the frozen file. A mutation between parsing and that read raises before any provider call.
- Generation duration is captured immediately after `ask`, before state inspection and grading, resolving the timing-label concern.

One metadata qualification remains for future Codex comparisons: `_system_prompt` is the production base prompt, but `CodexClient.new_session` appends response-length and tool-isolation instructions before sending `baseInstructions`. The saved file therefore needs to be labelled as the base prompt, or the client should expose the full effective instructions for capture. The frozen adapter source and configured token target retain how this suffix is constructed, so this does not block the current Cerebras run; it should not be described as the byte-exact full Codex request prompt.

The earlier defensive recommendation to filter only explicit public `text_delta` events is still open. Current adapters already filter their emitted text, so this is not an observed reasoning disclosure. No new execution blocker was found. The four planned dataset additions were not yet present at this recheck; the reviewed dataset still had 32 cases, including 22 text cases.
