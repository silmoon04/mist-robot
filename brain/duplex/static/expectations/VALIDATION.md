# Validation, 24 September 2026

The combined runner, trace-audit, acknowledgement and existing timing-metric suites passed **88 tests**:

```powershell
python -m unittest brain.benchmarks.naturalness.test_expectation_bench brain.benchmarks.naturalness.test_expectation_trace_audit brain.benchmarks.naturalness.test_acknowledgement_eval brain.benchmarks.naturalness.test_metrics -q
```

The acknowledgement CLI validated **14 of 14 declared fixture outcomes**. Seven valid examples passed, six deliberate violations failed, and one false useful-content marker remained unknown. These synthetic examples validate the evaluator; they do not measure MIST's behaviour.

The real Qwen baseline completed **26 cases / 55 turns**, with **0 backend failures** and **2 failed objective checks**. Ten non-text contracts were marked unsupported. Meaning is reviewed separately; there are no human listening ratings. A single observation per case is not enough to rank models.

Independent runner review found and reproduced failures in Codex prompt capture, partial-error retention and dataset freezing. All were fixed and retested before the real run. Codex base prompts remain explicitly distinguished from added session instructions; the current Cerebras baseline captures its effective system prompt.

The new local review page was checked through the browser accessibility tree: the case count, result links, filtering and disclosure of acknowledgement criteria rendered and worked. Screenshot capture was interrupted, so no screenshot-based layout verification is claimed.

The existing local service stopped during final verification: port 9053 had no listener. It was restored with the existing `brain.duplex.live_studio` launcher on the same port. The voice page, review page, download pack and result links then returned HTTP 200. No production prompt, voice, tool or expression policy was changed.
