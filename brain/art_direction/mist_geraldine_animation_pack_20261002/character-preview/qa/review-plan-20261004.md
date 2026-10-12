# Integration acceptance plan, 4 October 2026

The original expected-outcomes oracle remains the acceptance basis. Prior QA files were copied to `history/20261004/` before replacement. This plan was prepared while the adapter and preview owners were fixing clock reset ordering, bounded interruption recovery, paused blink settling and sampled finite duration. No final candidate tests had run when it was written.

## Mechanical checks

- Rerun the existing sampled-runtime and complete-scene checks after the owner declares the candidate ready. These tests do not exercise the actual browser dispatcher.
- Add sampled finite-duration boundary cases: just before duration, at duration, after duration, and duration zero. Cover a sampler that keeps returning active AA, the current sampled interface, and cancellation during a callback.
- Add clock-reset cases for a half-finished transition and finite reaction. Compare clean and repeated resets using the same scene/render clock contract.
- Check interruption during speech and a temporary reaction. Expect zero audio sources, immediate closed speech, a bounded return to listening, preserved ongoing intent, and stale epoch rejection.
- Keep source ownership and native cel checks separate from appearance judgment.

## Actual browser checks

- Fresh desktop load, three scene options, all local requests and useful missing-asset failure from an isolated fixture.
- Replay each scene through the real UI, then rapid replay and timing-profile changes. Inspect the event transcript and source/loop counts.
- Pause while speaking and during an eye transition. Inspect immediate closure and a settled face after the documented recovery bound; resume once and finish normally.
- Observe the authored packet gap and resumed speech in Waiting together. The ongoing reassuring intent must survive the gap.
- Interrupt during a finite reaction and during ordinary speech. Inspect the recovery before and after the documented deadline, including a pause during recovery.
- Resume during the first 400 ms after pausing. A recovery deadline must not detach the resumed sampler while audio keeps running.
- Finish the expressive question scene while its final acknowledgement is returning to the ongoing intent. The stopped scene must settle the remaining native transition and then release its loop.
- Suspend the real Web Audio context through a scoped test hook, inspect the visible state and source cleanup, resume with the UI, and remove the test hook by reloading.
- Check desktop and 851 by 393 layout, visible focus, keyboard playback/interruption, reduced-motion emulation, and the normal view with its inspector closed.
- Save a uniquely labeled synthetic review note, reload, export it through the UI and verify scene ID, position, profile, version and exact text.
- Navigate away after active playback and inspect teardown instrumentation for cleared interval/audio sources.

## Evidence boundaries

Browser observations, deterministic scheduling tests and screenshots are separate evidence. A screenshot establishes one visible pose and layout; it does not establish the motion between frames. No listening or acoustic synchronization score will be claimed because the reviewer cannot hear the browser audio. Visual family continuity is a reviewer observation, while final taste and live default approval remain with the user.
