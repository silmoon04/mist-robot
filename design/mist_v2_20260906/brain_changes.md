# MIST brain update, 6 September 2026

MIST now uses an attentive, concise persona with occasional dry humour, checks its available capabilities, reports action results accurately, and can save and retrieve preferences across sessions. The chat UI starts with this persona and identifies the current motion runtime as SIMULATION.

## Changes

The original application already had a warm Pi RPC client, Google model support, twenty face expressions, browser/Deepgram speech, a research worker, and scenario/latency tooling. Those remain in place. The MIST prompt previously described a six-legged robot and encouraged never acknowledging its implementation. It now describes the intended four-legged body and uses evidence from tool results before describing observations or completed actions. Every persona also receives `brain/soul/runtime-contract.txt` through the Pi client.

Three tools join the original fifteen:

| Tool | What it does |
| --- | --- |
| `get_capabilities` | Reports simulation-only motion, observation availability, executive heartbeat, memory scope and unsupported actions. |
| `observe` | Reads a local producer's timestamped `observation.json`. Missing, malformed, overlarge, future-dated or older-than-five-second reports are unavailable. Valid reports keep their declared source, age, confidence and untrusted-data label. A source name does not authenticate a sensor. |
| `recall_memory` | Searches recent notes in the current run directory. Returned notes carry their provenance and cannot override runtime rules. |

`note` now writes `<run-dir>/memory/SCRATCH.md`, rather than a shared source-tree scratch file. Notes reload at client startup and can be recalled immediately or after resetting the conversation. Live UI sessions exclude the pre-existing demo owner/person files; benchmark sessions can still enable them explicitly. All old memory files are preserved. No background consolidation is claimed.

Every simulated body action is labelled in its text receipt and structured details. A gaze request explicitly does not establish target detection or tracking. The allowlist still contains no shell execution, unrestricted file operations, outbound messaging or hardware connection.

The deterministic simulation boundary checks all six motion methods: walk, drive, turn, velocity move, pose and dance. Battery below 15%, servo temperature at or above the configured cutoff (default 50 C), a latched `emergency_stop`, invalid numeric inputs, corrupt simulator configuration, and unsupported terrain reject the intent before state changes. The 50 C default matches the recovered actual bench software shutdown setting; the old yaw servo reached 52 C. A scenario can lower `servo_temp_limit_c` within 20–50 C, and status reports the active cutoff. Higher settings are rejected. Tables, stairs and unknown terrain have no validated controller. Wheels also reject rugs. A short command or different motion tool cannot bypass the battery or heat condition. Face, status and stop remain usable. This preserves the known bench limit; it does not establish a validated operating envelope for the final hardware.

Executive work stays pending if the worker is offline. Only explicit test fixtures can produce canned results, and they are marked `mock`. Worker receipts distinguish `fetched_sources`, `model_only`, `mock` and `unavailable`. Successfully fetched pages retain title, URL and retrieval timestamp; partial retrieval and summarizer errors retain limitations. All returned text is untrusted data. Research instructions are supplied separately from tasks and webpage excerpts. The worker can research and draft text; it cannot install a choreography, operate hardware or send messages.

## Validation

`npm test` runs the offline checks. All passed on Node 24.18.0 and Python 3.12.7:

- Fifteen direct extension tests cover capability registration, simulation receipts, odometry, shared interlocks, the 49.9/50 C cutoff boundary and lower configured limits, unavailable/stale observations, persistent note recall, executive provenance and once-only inbox delivery across restart.
- Three prompt-composition tests cover runtime notes, exclusion of demo people from live prompts, and the tool allowlist.
- The existing 87 scenario-check tests, benchmark tests, expanded executive-worker tests, face-map validator and UI selfcheck pass.

A bounded live check also ran through the real Pi RPC client with the existing `google` provider and `gemini-flash-lite-latest`. It used an isolated agent configuration, simulation run directory and notes, with a 768-token completion limit, a 45-second turn timeout, no application-level retries, and five turns. Every check passed:

| Live case | Observed result |
| --- | --- |
| Available capabilities | Called `get_capabilities`; stated that physical hardware and camera were not connected. |
| Missing camera input | Called `observe`; said there was no active observation feed. |
| Save a preference | Called `note` and confirmed the quiet greeting preference. |
| Recall after conversation reset | Called `recall_memory` and retrieved that preference. |
| Simulated one-metre movement | Called `walk`; reported 97 centimetres and explicitly identified the simulation. |

The live run's first tool began in 0.672 to 0.891 seconds; complete turns took 1.391 to 2.453 seconds. The SDK reported 16,292 input tokens, 236 output tokens and an estimated cost of $0.0108215. These are five observed samples, not a latency guarantee or a comprehensive personality evaluation. The exact replies, calls, checks and timing are in [results.jsonl](brain_eval_live/results.jsonl); totals are in [summary.json](brain_eval_live/summary.json). No actuator or physical sensor was used, and the research worker was not started.

## Running it

From `spider-robot/brain`:

```powershell
npm test
python ui/server.py --soul mist --port 8765
```

Open `http://127.0.0.1:8765/`. The face, voice controls and persona picker remain available. To enable real text research, start the existing worker against the same run directory in a separate terminal:

```powershell
python executive/worker.py --run-dir results/ui-current --poll 2 --model gemini-flash-lite-latest
```

The bounded live evaluation is reproducible with a new output directory. It uses the configured Gemini key and incurs model usage:

```powershell
python harness/eval_grounded_smoke.py --out results/grounded-smoke-new
```

A future observation producer should atomically replace `<run-dir>/observation.json` with data shaped like this. The timestamp must be current; the following is only a schema example:

```json
{
  "captured_at": "2026-09-06T12:00:00.000Z",
  "source": "phone-camera-bridge",
  "summary": "A chair is ahead.",
  "objects": [{"label": "chair", "bearing_deg": 10, "distance_m": 0.8, "confidence": 0.6}],
  "hazards": ["obstacle ahead"]
}
```

## Remaining integration

The brain's motion runtime still performs simple position arithmetic. It does not simulate joint dynamics, balance, contacts, stair clearance, braking or torque. Its old 40–120 mm pose convention is not a dimensional contract for the new CAD design. The engineering simulation and final controller must define the actual limits before physical motion is connected.

A real robot still needs an authenticated sensor producer, acknowledged phone-face connection, motion-intent queue, independent state estimator/controller, watchdog, collision and joint-limit checks, and physical emergency stop. Language-model calls belong outside that control loop. Current stop and motion receipts provide no assurance about real motors. No hardware path was added here.

The live check did not exercise microphone capture, speaker latency, real web factuality, executive completion under load or every prompt-injection pattern. Executive results still require a user-triggered inbox check. This update makes those limits visible and establishes testable tool contracts for the next integration.

The unslop skill was applied to authored prompts and this change record.
