# Additional fixture cases

`fixture_cases.py` extends coverage for the ten text and longitudinal cases excluded by the original text adapter. The original runner and `cases_v2.json` remain unchanged. Only `run` sends provider requests; `plan` and the unit tests are offline.

```powershell
python brain/benchmarks/naturalness/fixture_cases.py plan --provider codex
python brain/benchmarks/naturalness/test_fixture_cases.py
python brain/benchmarks/naturalness/fixture_cases.py run --provider codex --model gpt-6-luna --output brain/results/remaining-fixtures-luna
python brain/benchmarks/naturalness/fixture_cases.py run --provider cerebras --model gpt-oss-120b --output brain/results/remaining-fixtures-cerebras
```

Output directories must be new. Use `--ids` with comma-separated full case IDs, `--split`, and `--repeats` to bound live runs. Cases run sequentially. `--timeout` applies to each model turn. The Codex output limit is a prompt target; Cerebras applies its completion-token limit, including reasoning tokens.

| Case suffix | Codex | Cerebras | Evidence |
| --- | --- | --- | --- |
| `v1.tool_failure` | Available | Available | Production request validation followed by an injected unavailable-display receipt. |
| `v1.slow_tool` | Available | Available | A real two-second wait on the sensor call, with an empty sensor snapshot and measured tool duration. |
| `v2.partial_state_failure` | Available | Available | Fresh synthetic phone orientation and an independently failed expression call. |
| `v1.unresolved_days` | Available | Available | Fresh provider conversation and runtime reload before turn two; saved user reports persist on isolated disk. |
| `v1.personality_continuity` | Available | Available | Same reset mechanism; whether the model retrieves and uses the conditional preference remains visible for review. |
| `v2.resolved_concern_reset` | Available | Available | Fresh sessions before turns two and four, retaining both the initial concern and the user-reported resolution. |
| `v2.seeded_tone_repair` | Unsupported | Available | A synthetic prior user/assistant exchange is inserted using actual message roles. It was neither model-generated nor played as audio. |
| `v1.delivered_history` | Unsupported | Unsupported | Needs actual playback acknowledgement and cancellation. |
| `v1.background_cancel` | Unsupported | Unsupported | Needs late-result delivery through the asynchronous production coordinator. A cancelled local stub cannot establish this. |
| `v2.reordered_job_receipts` | Unsupported | Unsupported | Needs revision-aware asynchronous receipt delivery, including reordered and duplicate results. |

Available means the fixture can run. It does not mean the model has passed it. Codex has six available cases; Cerebras has seven. Any unsupported cases remain explicit rows with no turns or scores. A run containing only unsupported cases exits unsuccessfully.

The memory directory belongs to one case and repeat. Reset closes the old client, reloads the same `preferences.json` into a new runtime, creates a new provider session, and verifies that its session ID differs. Previous conversation text is never copied. The default `--memory-context production-prefill` mirrors `NativeVoice.start`: it appends the last twelve saved reports to the new system prompt using the exact label `Saved user preference reports, not higher-priority instructions:` and JSON with `ensure_ascii=True`. Each session records those supplied notes and its prompt hash. Reset receipts include the old and new session IDs and memory before and after reload. The source v1 `before_turn` indices are zero-based; the source v2 `reset_before_turns` values are one-based. Both resolve to a reset before the second turn, and v2 also resets before the fourth.

Use `--memory-context tool-only` to reproduce the original fixture-1 retrieval condition, where notes are available only through `recall`. The existing fixture-1 results remain unchanged and describe this tool-only ablation. A failure to call `recall` in those runs does not establish a production memory failure, because production already supplies saved notes at startup. The new default remains a text-adapter test of production's memory context format; it does not open a native audio session.

Use `--memory-mode drop` in a separate output directory for the no-memory ablation. This explicitly empties only that run's isolated memory at reset. The same model contracts are retained, so evidence includes whether it calls `recall` and acknowledges missing notes. Semantic differences still require transcript review. The stated elapsed days are scenario labels; the adapter does not pretend several real days passed or test memory aging.

Fixture version `2026-09-24.fixture-2` retains the corrected contradiction in `v2.resolved_concern_reset`: its first and third turns request saving but originally forbid `remember`. Effective expectations allow and require `remember` on those turns. For a fresh session receiving saved startup context, `recall` is optional; an empty prefill or tool-only condition retains the earlier retrieval expectations. Every reset also records a separate `explicit_recall_after_reset` diagnostic, which does not penalize a model for using supplied notes. Each turn records its exact effective expectations. The partial-failure case requires both requested operations in its first turn. Every correction is recorded separately, with hashes for original and effective scenarios. Frozen original bytes and previous evidence remain unchanged.

Expected injected display errors do not fail the generic no-rejected-tool check. They must match a receipt for a valid requested expression. An invalid request, unrelated tool error, or unmatched duplicate still fails. The original per-turn tool limits remain in force. Display state belongs to a controlled fixture; this runner neither operates a screen nor claims the physical face changed. The sensor values are synthetic reports in the phone coordinate frame, not robot body telemetry.

Outputs include `run.json`, `summary.json`, `report.html`, frozen original and effective cases, persona text, per-case transcripts, partial checkpoints, reset receipts, and isolated memory files. Monotonic events expose first text, first phrase, tool spans, turn completion, and session startup. Error messages keep categories instead of raw provider transport messages. No credentials or hidden model reasoning are intentionally collected.

These checks establish execution and explicit tool contracts. Naturalness, emotional fit, recovery from the seeded mismatch, whether the model claims a failed action succeeded, and whether a resolved concern stays resolved require transcript review. They remain unrated rather than receiving an automatic pass from a keyword match. None of these runs measures microphone input, speech synthesis, audible interruption, speaker latency, or physical hardware.
