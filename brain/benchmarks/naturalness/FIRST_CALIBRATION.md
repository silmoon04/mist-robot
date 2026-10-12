# First calibration, 23 September 2026

The benchmark has 72 scenarios. The first live run exercised four dev scenarios, twice in each of two identical arms: tea and contextual correction, a bad day without advice, phone-versus-body orientation, and exact face requests. This produced 16 scenario samples and 40 real Luna turns. Both arms used Luna with low reasoning and the same production persona, tools and output limits. Each pair ran serially in balanced AB/BA order. It was an A/A repeatability check, not a candidate improvement.

All samples completed. Four tool-delivery checks failed on the second exact-face turn. Luna selected `curious` correctly for “Now curious, no special variation.” The production request guard rejected the request as an unavailable preset, and the reply then reported that curious was unavailable. This is an application failure with a misleading resulting answer, not evidence that Luna selected the wrong preset. The original run and receipts are retained; production code was not changed during this benchmark task.

| Median measurement | Arm A | Arm B |
| --- | --- | --- |
| First visible text after prompt submission | 1.43 s | 1.33 s |
| First complete phrase after prompt submission | 1.53 s | 1.49 s |
| First tool request after prompt submission | 1.55 s | 1.91 s |

Text/phrase measurements have 20 observed turns per arm; tool-request measurements have six observations per arm. These are backend timings, not speaker latency. The summaries include completed samples with noncritical tool-delivery failures; their checks remain visible and no overall quality verdict is produced. A later speed comparison should examine the affected task outcomes before accepting an improvement.

Only four distinct scenarios were sampled. Repeated turns are correlated, and the tail estimates are too small to treat as stable. Differences between these identical arms establish the need for repetitions, not the superiority of either configuration.

The blind page contains actual transcripts and pending ratings. No human score, voice-quality result, or Jev decision was generated or inferred. The review page was checked in a browser: navigation, unavailable audio ratings and JSON download worked. The browser test left human ratings empty. A screenshot is saved at `output/playwright/mist-benchmark-review.png`.

All nine existing offline contract groups passed. The benchmark's 79 unit tests passed after final review fixes. Tests cover missing events, clock and turn separation, tool correlation, stale/missing identities, planned missing samples, clustered comparisons, blinding, incomplete review rejection and ratings validation. Those are tests of the evaluation machinery, not 79 human conversation trials.

Next evidence to collect: recorded timed-audio fixtures, a playback-aware browser/device adapter, independent listener ratings, and real session-reset cases. Add Jev as a separate evaluated condition after its native interruption integration is established. Keep the present baseline unchanged for comparison.
