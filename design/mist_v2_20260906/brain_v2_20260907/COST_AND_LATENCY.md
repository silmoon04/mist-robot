# Measured usage and latency

These numbers cover the saved live MIST evaluations. They do not include every token used by the coding agents, and they are not a provider invoice.

## After the user's live feedback

The selected setup now uses Spark low/standard for conversation and Astra low/priority for background work. Seven additional diagnostic turns tested the avoidable round trips and Spark identity correction. One final short live browser probe measured **1.207 s to first displayed text and 2.261 s from Send to audio playback**. It returned `Ready.`; this is a short-reply measurement, not a promise for long answers. The trace is saved at `latency_fix_20260907/root_live_send_to_voice.json`.

Across all recorded automated model probes, the current total is **105,731 input tokens and 1,552 output tokens**, with **at least 61,952 cached input tokens**. The breakdown is in [automated_usage_summary.json](automated_usage_summary.json). User-triggered chats and the coding agents' own work are excluded. Dollar cost remains unavailable.

Two additional Flash voice probes used 130 characters and generated 6.5945 seconds of audio. Their API completion times were 1.0278 and 0.3457 seconds. Both word checks passed. The final live short-reply test exposed a stale-page duplicate generation, which is recorded rather than excluded from the failure history; server-side request guarding and idempotency address that remaining path.

The snapshot after the voice guard was **22% weekly used, 78% remaining**, versus 4% before the expanded work. Further mechanical CAD, gait and stair work continued, and the [later whole-account reading](../usage_mechanical_followup_20260907.json) was **32% used, 68% remaining**. These changes include coding agents and any other concurrent account activity; they cannot be assigned to the brain runtime or converted into a dollar bill. The recorded runtime-probe token total above did not increase during that mechanical follow-up. Spark's separate meters display 0% used at their reported precision, which does not mean the requests consumed no tokens. The [voice-guard snapshot](usage_final_20260907.json) and later file omit the account identifier. No reset credit was used.

After the completed CAD export, matched simulation, revised fit bed and native integration work, the [delivery snapshot](../usage_delivery_20260907.json) reads **44% weekly used, 56% remaining** at 04:20:59 UTC on 7 September. It is still a whole-account reading, including any concurrent tasks. The recorded automated brain-probe total remains 105,731 input and 1,552 output tokens; it does not measure the coding agents' token consumption.

The sections below preserve the earlier Astra-only measurements and usage snapshots.

| Run | Input tokens | Output tokens | Cached input known |
|---|---:|---:|---:|
| Twelve Codex backend validation turns | 60,704 | 687 | 44,160 |
| Three live browser conversation turns | 10,905 | 151 | Not separately recorded |
| Browser background research summary | 2,793 | 71 | Not separately recorded |
| Combined observed requests | **74,402** | **909** | At least 44,160 |

The initial ten Astra validation turns had median total latency 5.12 s and median first reaction 2.53 s. Two targeted follow-ups completed the twelve-turn budget. The installed Codex 0.153.4 accepted `gpt-6-astra`, `low`, and `priority`; its catalog calls that tier Fast and describes 2x speed with increased usage. No matched standard-tier comparison was run, so this is not a measured twofold improvement.

The earlier, smaller Gemini evaluation had medians 2.00 s total and 0.69 s first reaction. Different cases and harness paths prevent a controlled model-ranking claim. The live integrated Astra browser later gave a greeting in 2.375 s and arithmetic during research in 1.906 s. A tool-using expression/speech reply took 8.547 s before 1.051 s of speech synthesis. Background research completed in 7.469 s with actual fetched sources.

Four ElevenLabs clips used 257 submitted characters and produced 13.7926 s of audio. Deepgram transcribed 6.7802 s for the two word checks. These checks measured word intelligibility and timing data; they did not establish perceptual voice likeness. Account-specific dollar cost is unavailable, so it remains unknown.

The Codex weekly account meter was 4% used before the expanded brain work and 15% used after it: an 11-percentage-point change, leaving 85% at that snapshot. Those are whole-account readings. The main mechanical work, coding agents and any other simultaneous account tasks share the same allowance; this delta cannot be assigned precisely to the brain work or the runtime probes. See [before](usage_before.json) and [after](usage_after.json). No reset credit was used.

Detailed request evidence is in [CODEX_EVALUATION.md](CODEX_EVALUATION.md), [INTEGRATION_REPORT.md](INTEGRATION_REPORT.md), `browser-turn-metrics.jsonl`, and the two Codex live-run directories. The former Gemini experiment remains separately recorded at `../brain_eval_live` and is excluded from the totals above.
