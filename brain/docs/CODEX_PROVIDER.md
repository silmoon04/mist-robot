# Codex provider

MIST can use a persistent Codex app-server process for conversation and a separate, tool-free client for executive jobs. The Gemini/Pi provider remains available for comparison. The default Codex configuration is `gpt-6-astra`, low reasoning, and `priority` service tier. The installed model catalog calls this tier **Fast**, with the description **2x speed, increased usage**. That describes the service tier; it does not establish that this robot application responds twice as fast.

The latency work also verifies a faster conversation configuration: `gpt-5.3-codex-spark`, low reasoning and `default` service, with a separate Astra/low/priority executive. Spark advertises no priority tier. The console owns profile selection; selecting a conversation model must not implicitly change the executive model. See `design/mist_v2_20260906/brain_v2_20260907/latency_diagnosis/LATENCY_DIAGNOSIS.md` for the bounded comparison and the corrected Spark identity failure.

## Run

Use a signed-in native Codex CLI, version 0.153.4 or newer, with model metadata in `CODEX_HOME/models_cache.json`. On Windows the adapter prefers the native desktop `codex.exe`. Set `MIST_CODEX_BINARY` to select a different native executable. The verified CLI version is 0.153.4. Authentication remains in the installed Codex account; the adapter does not read, copy, or print credentials.

From `brain/`:

```powershell
python ui/server.py --backend codex --model gpt-6-astra --thinking low --service-tier fast
```

The adapter accepts `fast` as an alias for `priority`, plus `default` for standard speed. It checks the thread's returned model and priority tier before accepting the session. It never silently replaces the model. `backend_info` records the requested and accepted settings, CLI version, startup duration, tool count, and whether price or token-limit information is available.

## Tool boundary

`harness/codex_tool_bridge.mjs` imports the same 18 robot handlers as the Pi provider. It checks tool names and JSON schemas before invoking a handler. The handlers retain their simulation receipts, persistent notes, executive tickets and deterministic interlocks. No actuator controller is connected.

The Codex process receives `environments: []`, read-only sandboxing, no approval grants, no project instructions, and disabled integrations at startup. Legacy notification commands are cleared with `notify=[]`; disabling feature hooks alone does not disable these commands. Its per-run model catalog preserves the requested model identity while setting `tool_mode: direct`, disabling collaboration, and removing experimental tool capabilities. These overrides matter: Astra's default local metadata enables code mode and collaboration even when some feature flags are false. Orchestrator skills and MCP are also disabled.

The offline protocol audit captures the actual outgoing tool definitions from Codex 0.153.4. It found exactly the 18 registered robot tools for conversation and no tools for executive mode. The audit uses a loopback mock Responses server with an isolated home directory, no credentials and no cloud model calls. It also completes a genuine app-server dynamic-tool callback.

```powershell
python harness/audit_codex_tool_exposure.py --out results/codex-tool-exposure.json
```

Repeat this audit when upgrading Codex or changing tool configuration. Feature flags alone are insufficient evidence of the available tool set. A missing cached model record causes startup to fail so the adapter cannot silently fall back to a wider catalog.

## Client contract

`CodexClient` supports `ask(prompt, timeout=120, on_event=None)`, `new_session()`, `set_sim(overrides)`, `cancel_current_turn()` and `close()`. It returns the existing `pi_client.TurnResult` type and emits the UI's `message_update`, `tool_execution_start`, `tool_execution_end` and `agent_end` events. Raw reasoning or full RPC payloads are not logged; `keep_events` retains only these normalized application events.

The result is a `CodexTurnResult` subclass with a `timings` dictionary. `backend_timing` events expose the same stage measurements. A validated `face_expression` event carries optional display metadata; its leading marker is removed before text reaches the UI or speech synthesis. This event has no hardware acknowledgement and cannot request movement. A pure internal bridge read supplies fresh capability metadata without a model tool round trip or bus/state mutation. Questions about the present visual scene still require `observe`.

One conversation client keeps one subprocess and thread warm across turns. `new_session()` starts a new ephemeral thread in that process and reloads the run's persistent notes. Executive jobs pass `tools=[]` and their own `system_prompt`; they must use an independent client so research does not block the conversation lock.

Cancellation uses the correlated thread and turn IDs. An acknowledged interrupted turn can finish and the client can be reused. A timeout or incomplete transport closes both subprocesses and marks the client unavailable; create a new client before sending another prompt. Tool requests received after cancellation are rejected. At most 16 robot tool calls are dispatched per turn.

## Measurements and limits

`ttft_s` measures the first visible text delta; `ttf_tool_s` measures the first dynamic tool request; `ttf_any_s` is the first of either. `total_s` ends at the turn-completed event. Startup is measured separately. A `ToolCall.t_offset_s` is the tool-request offset. Token usage is the difference in cumulative thread totals, including all tool round trips. `input_tokens` includes cached input; `cache_read_tokens` is its cached subset. The legacy `turns` field counts completed assistant messages and is not a reliable model-round-trip count for this provider.

Codex does not expose a verified hard assistant-output token cap in the inspected protocol. The client asks for a short response and interrupts when visible output exceeds a character bound. Reasoning and tool arguments can consume tokens before that bound. The live evaluation also stops after a fixed number of turns and a reported aggregate output budget. `cost_usd=0` in the shared result is an unavailable legacy placeholder; `backend_info.cost_available=false` is authoritative. Do not treat it as free usage.

The September 7 evaluation used 12 live Astra turns and 687 output tokens. Ten initial turns had a median 5.12-second completion time, with a 2.53-second median first reaction. An earlier five-turn Gemini sample had a 2.00-second completion median and 0.69-second first-reaction median. The scenarios, personas, context history and runs differ, so this is a descriptive comparison rather than a controlled speed benchmark. No standard-tier Astra comparison was run.

The first suite passed nine of ten strict checks. One current-vision answer correctly admitted missing perception but did not refresh `observe`. The persona was corrected, and a targeted live check confirmed a fresh `observe` call. A final live executive check completed with no tools. Full measurements and limitations are in `design/mist_v2_20260906/brain_v2_20260907/CODEX_EVALUATION.md` at the repository root.

## Verification

```powershell
python harness/test_codex_client.py
python harness/run_offline_tests.py
python harness/eval_codex_smoke.py --out results/codex-live-evaluation
```

The last command makes up to ten real model turns. The first two commands use local fixtures; they do not require a Codex account or call a model. The protocol audit requires the installed native Codex CLI and its cached model metadata, but does not use the account.

Protocol references: [OpenAI app-server documentation](https://learn.chatgpt.com/docs/app-server), [0.153.4 tool registration](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/core/src/tools/spec_plan.rs), [tool-mode precedence](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/core/src/tools/mod.rs#L68).
