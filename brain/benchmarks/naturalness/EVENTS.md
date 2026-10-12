# Event and evidence format

`runner.py score path/to/run.json --output new/report-directory` recalculates metrics from a normalized run. Every run has a manifest and samples. A sample is one full scenario repetition, including its conversation turns.

```json
{
  "manifest": {
    "schema_version": 1,
    "run_id": "example",
    "suite_sha256": "hash-of-frozen-cases",
    "adapter": "phone-audio-v1",
    "selected_case_ids": ["example-case"],
    "repeats": 1,
    "config": {"device": "Mi 9 SE", "conditions": "quiet room"}
  },
  "samples": [{
    "case_id": "example-case",
    "repeat": 1,
    "category": "interruption",
    "split": "dev",
    "status": "completed",
    "turns": [],
    "events": [
      {"name": "user_interrupt_onset", "t_ms": 1200, "clock_id": "capture", "turn_id": "2", "interruption_id": "i1"},
      {"name": "playback_stopped", "t_ms": 1390, "clock_id": "capture", "turn_id": "2", "interruption_id": "i1"}
    ],
    "checks": [],
    "outcomes": {"missed_interruption": false}
  }]
}
```

The example is a schema illustration, not a recorded result. An actual run should state how the ground-truth event was obtained, clock uncertainty, fixture hash, device, model versions, prompt and policy hashes, network conditions, cold/warm state, and any missing evidence.

Event names used by the scorer:

- `user_audio_end`, `asr_final`, `turn_committed`, `first_text`, `first_phrase`, `first_tool`, `turn_completed`.
- `tool_requested`, `tool_started`, `tool_finished`, with `tool_call_id`.
- `playback_started`, `first_useful_audio`, `user_interrupt_onset`, `playback_stopped`. Repeated cutoffs need `interruption_id`.
- `expression_requested`, `expression_applied`, with `expression_id` when repeated.

`first_useful_audio` needs a human annotation or a frozen, scenario-specific rule identifying the useful content, plus the corresponding playback time. The first PCM packet, the first spoken filler, and the first text token are different observations.

Use separate clock IDs for an unsynchronized browser, server, and external recording. A clock name must identify an actual common time base, not merely relabel unrelated numbers so they can be subtracted. Browser output timestamps are software estimates; external loopback or microphone recordings are stronger evidence for physical onset and audiovisual offsets.

For a text adapter, `turn_committed` means submission of the text prompt. It does not measure audio endpointing. `tool_started` is the first observed application dispatch; the model's earlier internal decision is unavailable. Omit `tool_requested` if it was not observed. Normalized events never substitute for the retained raw trace.

Explicit outcome fields are `false_interruption`, `missed_interruption`, `task_success`, `appropriate_expression`, `history_correct`, and `tool_correct`. Use true/false only when the case provides enough observed evidence; omit or null means unknown. A backchannel case measures false interruption; a takeover case measures missed interruption. Do not populate both merely to fill the report.

Statuses distinguish `completed`, `failed`, `timeout`, and `unsupported`. Completion means the harness finished the case, not that the model succeeded. Checks have `name`, `passed` (true/false/null), and `critical`. Keep state protection, model choice, and human ratings separate.

To add media to a blinded review, set `audio_path` to an existing local recording. Set `audio_scope` to `conversation` only if it contains the whole interaction with the actual pauses and overlap. Response-only audio can support a voice-quality rating but cannot establish turn timing. Expression ratings require a synchronized video or a separate live review; this text/audio page does not enable them.
