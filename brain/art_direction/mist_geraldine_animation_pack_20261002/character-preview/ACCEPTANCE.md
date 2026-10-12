# Local acceptance, 4 October 2026

Preview 1.0.1 and adapter interface 1.0.0 are ready for local character review and a logic-owner handoff. The independent reviewer found no blocking defects. Human style approval and integration with the live brain remain pending.

| Evidence | Result | What it establishes |
| --- | --- | --- |
| Adapter worker checks | 42 groups pass | Finite speech duration, normalization, provenance, cancellation and reset |
| Independent sampled-runtime checks | 72/72 | Closed speech on silence, stop/reset and invalid amount across all 13 presets |
| Independent boundary checks | 5/5 | Expired callback rendering and reentrant cancellation |
| Independent scene/cel checks | 9/9 | Authored traversal, native crop ownership and transport cleanup |
| App-used playback/transport tests | 26/26 | Actual lifecycle logic, replay, paused recovery, early resume and scene ending |
| Speech sampler checks | 51 | Cue validation, identity, gaps, replacement and original WAV hashes |
| Scheduling-to-render fixtures | 8 | Closure at the next injected 15 fps render call |
| Independent browser review | 20/20 | Desktop/phone UI, original-page playback, notes and scoped failure fixtures |
| Reused input comparisons | 23/23 | 14 native media files, seven source interfaces and two exact module copies |

The original page was tested at desktop and 851 by 393 landscape. It preserves reassuring intent across the inserted packet gap and freezes clip position at 1.1 seconds until playback resumes. Real AudioContext suspension/resume and pagehide cleanup were observed through a QA-only fixture importing the unchanged app. A separate fixture deliberately failed a WAV request and verified the visible error and disabled playback. The normal page made only local requests.

The native transition lasts 400 ms. The next 15 fps render can add about 67 ms before browser event-loop delay. Observed recovery examples completed at 410 and 425 ms; these are scheduling observations, not acoustic measurements. The reviewer did not hear browser audio. Two recordings use estimated phoneme timing within word bounds, and one uses audio-energy targets. No perfect lip-sync or listening-quality score is claimed.

One minor inspector issue remains: an authored interruption records its request and application with the same visible label. Cancellation itself is correct. `qa/defects.md` records the exact replay and the resolved earlier defects.

The portable ZIP includes the selected native assets, preview, adapter, interface notes, fixtures, receipts and screenshots. `release-manifest.json` records each payload hash. `release-check-results.json` beside the ZIP records its fresh extracted launch and served native bytes. The local source check is separate from public deployment verification.

Review the three scenes, compare timing profiles, and use Keep / Revise notes to record a specific moment. Final face selection and live-default approval are still human choices.
