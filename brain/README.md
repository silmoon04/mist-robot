# MIST brain

The native voice refinement is available in [duplex/README.md](duplex/README.md). It connects Codex V3 voice to ElevenLabs Voice Changer with the MIST (refined) voice, a landscape phone face, sensor snapshots and bounded R5 previews. Run `npm run duplex`; the prior console below remains available. See the new mode's evaluation record for measured latency and physical-phone limits.

The September 2026 update makes MIST the default chat persona, adds explicit capability checks, timestamped observation input, and persistent note recall. The console always labels the current motion runtime as SIMULATION. Start it with `python ui/server.py --soul mist`; run all offline checks with `npm test` (Node 24 and Python 3.12 were used).

The detailed change record is [brain_changes.md](../design/mist_v2_20260906/brain_changes.md). Its runtime contract supersedes historical motion and memory descriptions below. `docs/SPECS.md` remains the July interface snapshot. The current tool list has 18 tools: the original 15 plus `get_capabilities`, `observe` and `recall_memory`.

Live chat excludes the demo owner/person files. Notes now persist in `<run-dir>/memory/SCRATCH.md`, reload at client startup, and can be searched in the same or later session. Historical `brain/memory/SCRATCH.md` is preserved. There is no overnight memory consolidation.

Body tool receipts identify simulation explicitly. Every motion method checks the same heat, battery, terrain and emergency-stop conditions before changing state. Servo temperature at or above 50 C, battery below 15%, an asserted `emergency_stop`, corrupt simulator input, and terrain other than floor/rug block motion. The 50 C cutoff matches the recovered bench software shutdown setting; the old yaw servo reached 52 C. A scenario can set `servo_temp_limit_c` between 20 and 50 C to test a lower cutoff. `get_status` exposes the active limit. Wheels also refuse rugs. These are simulator interlocks; real control needs an independent controller and physical emergency stop.

`observe` reads `<run-dir>/observation.json`. A producer writes `captured_at` (ISO UTC), `source`, optional `summary`, `objects` (`label`, `bearing_deg`, `distance_m`, `confidence`), and `hazards`. Reports older than five seconds, invalid reports and future timestamps are unavailable. Returned data retains its reported source and is explicitly untrusted. No camera producer is connected by this update.

Executive tickets remain pending when the worker is offline. Explicit `executive_results` fixtures are labelled `mock`; no default answer is fabricated. Worker results carry `grounding`, successfully fetched `sources` with retrieval times, fetch `coverage`, and `limitations`. See the change record for the bounded live evaluation and remaining integration work.

## Existing application and commands

The L1 "voice brain" of the wheel-leg quadruped (4 legs x 3 DOF + wheel hubs at the
feet: 16 active ST-3215 bus servos of the 18 bought — the "HEX-1" name and the two
spares are leftovers from the cancelled six-leg design), running on
[Pi](https://github.com/earendil-works/pi)
(`@earendil-works/pi-coding-agent`, pinned locally in `package.json`), with the robot's
tool belt implemented as a Pi extension, a chat UI, a background executive worker, and a
Python benchmark harness that batters it with scenarios, latency measurements, long
conversations, and a Deepgram voice round-trip. See `docs/ARCHITECTURE.md` for diagrams.

```
brain/
├── soul/                  # system-prompt personas (A/B testable)
│   ├── butter-nihilist.md    #   v1 persona (short, dry, nihilist, hexapod-era body)
│   ├── butter-nihilist-v2.md #   v2 persona (same voice, wheel-leg quad body truth)
│   ├── mist.md             #   softer, eerie Pantheon-MIST flavor
│   └── minimal.md          #   control prompt (rules only, no character)
├── skills/                # skill library (dances, gaits, gestures) as JSON
├── memory/                # MEMORY.md + PEOPLE/ — loaded into the system prompt
│   └── SCRATCH.md         # written by the robot via note() at runtime
├── extensions/
│   └── robot-tools.ts     # Pi extension: 15 robot tools + simulated L0 spine
├── executive/
│   └── worker.py          # background L2 brain: tickets.jsonl -> web+Gemini -> inbox.jsonl
├── ui/
│   ├── server.py           # stdlib chat UI server (chat mode + --watch spectate mode)
│   └── static/index.html   # single-file browser page (face iframe + chat + sim panel)
├── face_assets/
│   ├── app/                 # SVG face animator (index.html, app_data.js, faces[40])
│   └── face_map.json        # 20 tool expressions -> primary/alt SVG face ids
├── harness/
│   ├── pi_client.py       # warm `pi --mode rpc` client, latency + usage capture
│   ├── scenarios.py       # 64 scenarios / 88 turns across 15 categories + check DSL
│   ├── run_suite.py       # scenario matrix runner (models × souls)
│   ├── bench.py            # repeatable benchmark runner -> results/<run-id>/{manifest,results,summary,report}
│   ├── compare_runs.py     # markdown diff across two+ bench runs (pass-rate/latency/cost/flips)
│   ├── check_face_map.py   # offline validator for face_assets/face_map.json
│   ├── test_checks.py      # offline unit tests for the scenario DSL
│   ├── test_bench.py       # offline unit tests for bench.py/compare_runs.py
│   ├── test_executive.py   # offline unit tests for executive/worker.py
│   ├── long_convo.py      # 38-turn single-session memory/latency test
│   ├── voice_check.py     # Deepgram TTS -> STT fidelity round trip
│   └── debug_timeline.py  # raw RPC event dump for one prompt
├── docs/
│   ├── SPECS.md            # binding interface contract for this repo
│   └── ARCHITECTURE.md     # diagrams + data-flow docs
├── results/               # run outputs (JSONL) — one dir per run
└── voice/                 # generated .wav samples
```

## The tool belt (extension)

`walk drive turn move pose dance face look_at stop list_skills load_skill note
ask_executive check_inbox get_status get_capabilities observe recall_memory`

`walk` is legs (any terrain, slow, expressive); `drive` is wheels (fast, quiet,
energy-cheap, flat hard ground only — refuses on rug). The extension simulates the
spine: it tracks position/heading/pose/face/locomotion mode, blocks motion when
battery is below 15% or a servo reaches the configured cutoff (default 50 C),
refuses `drive` on a rug surface, and fails unknown dances so
the model must consult `list_skills`, runs a real ticket/inbox executive bus (with a
sim-canned fallback when no worker is alive), and appends **every tool call to
`bus.jsonl`**. This is an audit log, not an actuator command queue; a real controller
needs a separate validated motion-intent interface.

Test knobs are injected per scenario via `sim_state.json` in the run dir
(`battery_pct`, `servo_temp_max_c`, `hot_servo`, `surface`, `executive_delay_ms`,
`executive_results`, `walk_scale`, …). The harness (or `ui/server.py`'s `/api/sim`
route) writes it; the extension reads it fresh on every tool call.

## Running

Keys go in `spider-robot/.env` (`GEMINI_API_KEY`, `DEEPGRAM_API_KEY`) — the harness
loads it automatically.

```powershell
cd brain

# full suite, one model
python harness/run_suite.py --models gemini-flash-lite-latest:off --pace 5

# compare models / thinking levels / personas
python harness/run_suite.py --models gemini-2.5-flash:off,gemini-flash-lite-latest:off
python harness/run_suite.py --models gemini-flash-lite-latest:off --soul mist

# one category or one scenario
python harness/run_suite.py --models gemini-flash-lite-latest:off --only safety
python harness/run_suite.py --models gemini-flash-lite-latest:off --only cmd_walk_simple

# 38-turn long conversation (memory recall probes at turns 10/21/34/37)
python harness/long_convo.py gemini-flash-lite-latest:off --pace 5

# voice round trip (writes .wav files you can listen to)
python harness/voice_check.py --lines 3
python harness/voice_check.py --from-results results/<run>/results.jsonl

# debug one prompt: full RPC event timeline
python harness/debug_timeline.py gemini-flash-lite-latest:off "walk two meters"
```

`--pace 5` matters on the free-tier Gemini key (RPM limits). The runner also
auto-retries turns that die with 429/503/fetch errors.

## Chat UI

Stdlib-only web server (`ui/server.py`) + a single-file browser page
(`ui/static/index.html`): left pane is the SVG face (`face_assets/app/`) in an
iframe, right pane is the chat log, with a collapsible sim panel (battery,
servo temp, surface, executive delay). Header controls: **persona picker** (live
switch between `soul/*.md`), **speech engine** (Browser / Deepgram / Mute),
**voice picker** (33 Deepgram Aura voices, grouped warm/bright/dry, with a ▶
preview), and a connection dot. The composer has a **🎤 push-to-talk mic** —
click to record, click to stop; it transcribes with Deepgram and (with `auto` on)
sends. That is the "talk to it in real life" path.

```powershell
# live chat, one warm PiClient
python ui/server.py --model gemini-flash-lite-latest --thinking off `
  --soul butter-nihilist-v2 --port 8765

# start on a specific voice (else the persona's default is used)
python ui/server.py --soul mist --voice aura-2-cora-en

# spectate a benchmark run instead of chatting (no PiClient, no network)
python ui/server.py --watch results/<run-id>

# offline smoke test: stub client, ephemeral port, exits 0/1
python ui/server.py --selfcheck
```

Then open `http://127.0.0.1:8765/`. Everything streams over one `/api/events`
SSE connection; `/api/say` accepts one turn at a time (409 if busy), `/api/sim`
patches `sim_state.json` live, `/api/session/new` resets the conversation.
Voice/persona/mic routes: `/api/voices` (GET registry), `/api/tts` (POST
`{text, voice}` → Aura wav), `/api/stt` (POST mic audio → transcript, nova-3),
`/api/personas` (GET list) and `/api/persona` (POST `{soul}` → rebuilds the warm
brain under a new soul). All Deepgram routes need `DEEPGRAM_API_KEY` in `.env`.
When Deepgram plays, a Web Audio `AnalyserNode` reads the actual audio and drives
the mouth from its live amplitude — so each voice's own cadence, pauses and vowel
length match (not a fixed text estimate). MIST gets a warm voice, butter-nihilist
a dry one, and you can taste-test the rest live.

## Benchmarks

`harness/bench.py` is a repeatable driver over the same scenario matrix as
`run_suite.py`, writing a full `results/<run-id>/` bundle
(`manifest.json`, `results.jsonl`, `summary.json`, `report.md`) instead of just
stdout.

```powershell
# print the run matrix (configs x scenarios x turns) and exit — no network
python harness/bench.py --models gemini-flash-lite-latest:off --souls butter-nihilist-v2 --plan

# actually run it
python harness/bench.py --models gemini-flash-lite-latest:off `
  --souls butter-nihilist-v2,butter-nihilist --only safety --pace 5 `
  --timeout 90 --repeat 1 --run-id demo-run

# compare two or more runs: pass-rate table, by-category deltas, latency,
# cost, and a pass<->fail "flips" section
python harness/compare_runs.py results/runA results/runB --out compare.md
```

`Ctrl-C` mid-run still writes a partial `summary.json` (`"aborted": true`).
`--only` filters by scenario id substring or exact category name.

## Executive worker

`executive/worker.py` is the background L2 brain: it polls a run dir's
`tickets.jsonl` (written by the `ask_executive` tool), researches or answers
each new ticket, and appends results to `inbox.jsonl` for `check_inbox` to
pick up, touching `worker.alive` every pass as a heartbeat.

```powershell
# real research (DuckDuckGo HTML search -> fetch -> Gemini summary) + general Q&A
python executive/worker.py --run-dir results/ui-current --poll 2 `
  --model gemini-flash-lite-latest

# offline, zero network, deterministic canned briefs
python executive/worker.py --run-dir results/ui-current --once --mock
```

Point it at the same `--run-dir` a running `ui/server.py` chat session uses to
get real `ask_executive` / `check_inbox` round trips instead of the
extension's sim-canned fallback (which only kicks in when no worker has
touched `worker.alive` in the last 20 s).

## Face map

`face_assets/face_map.json` maps all 20 tool-level expressions to a primary
SVG face id (plus 1-3 alts) out of the 40 faces in `face_assets/app/app_data.js`.
`harness/check_face_map.py` validates it offline against both `app_data.js`
and the `EXPRESSIONS` array parsed straight out of `extensions/robot-tools.ts`:

```powershell
python harness/check_face_map.py
```

## Souls

- `soul/butter-nihilist.md` — v1, hexapod-era body truth (6 legs, kept for A/B
  benchmarking; do not edit).
- `soul/butter-nihilist-v2.md` — v2, current default: wheel-leg quad body
  truth (legs vs wheels decision rule, face-first reactions, energy
  self-awareness), same dry-nihilist voice.
- `soul/mist.md` / `soul/minimal.md` — alternate flavor / control prompt for
  A/B runs.

Pick a soul with `--soul <name>` on `run_suite.py` / `ui/server.py`, or
`--souls a,b` (comma list) on `bench.py`.

## Interactive driving

You can talk to the robot brain directly in Pi's TUI:

```powershell
$env:GEMINI_API_KEY = "<key>"; $env:ROBOT_BRAIN_DIR = (Resolve-Path .)
./node_modules/.bin/pi --provider google --model gemini-flash-lite-latest `
  --no-context-files --no-builtin-tools -e ./extensions/robot-tools.ts `
  --system-prompt (Get-Content -Raw soul/butter-nihilist-v2.md)
```

## What a result row contains

Per turn: reply text, ordered tool calls with args and error flags, `ttft_s`
(first spoken token), `ttf_tool_s` (first motor intent — the number that makes the
robot *feel* alive), `total_s`, LLM round-trips, input/output/cached tokens, cost,
and every check with pass/fail + detail. Persona checks (no markdown, ≤80 words,
no emoji) run on every reply automatically.

## Known model notes (July 2026, free tier)

- `gemini-flash-lite-latest` — fastest and most consistent (~2.3 s to first tool call).
- `gemini-2.5-flash` — solid, ~2.7 s.
- `gemini-3.1-flash-lite` — works, more latency variance.
- `gemini-3.5-flash` / `gemini-flash-latest` — frequent 503 "high demand" at test time.
- `gemini-3-pro` / `3.1-pro` — **quota 0 on free tier**; needs paid billing for smart mode.
- `:off` thinking is clamped to `minimal` on Gemini 3.x models.
