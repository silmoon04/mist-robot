# Affect director comparison

## Result

The corrected one-pass run completed six cases across three arms. It shows that either reader can return grounded face and delivery proposals, but this small text-only sample does not show that a two-model system consistently feels smarter. Several reader proposals were rejected by validation. The Qwen speaker paired with GPT-OSS also timed out on two cases. No reader proposal was applied to the face or voice renderer.

| Arm | Speaker first-text median | First-phrase median | Reader result | Reader completed before phrase |
| --- | ---: | ---: | --- | ---: |
| Qwen speaker only | 4,207 ms (6 replies) | 4,209 ms (6 replies) | — | — |
| Qwen reader + Qwen speaker | 1,615 ms (6 replies) | 1,616 ms (6 replies) | 4 accepted, 1 face override, 1 inconsistent proposal rejected | 3/6 |
| GPT-OSS reader + Qwen speaker | 4,137 ms (4 replies) | 4,138 ms (4 replies) | 5 accepted, 1 proposal rejected for missing evidence | 4/4 replies with a phrase |

These timings use one local monotonic clock. They measure first nonblank text, the first boundary from production `next_phrase`, and reader completion. They do not measure audible onset or TTS readiness. The runs happened in two bounded invocations with the same frozen source and prompt hashes: one three-arm smoke case, then five cases. Arm order was randomized within each invocation. No prompt tuning or model-call retries followed the smoke case.

## Case observations

On the disappointment case, Qwen's raw proposal was a sad face and gentle delivery, grounded in the user's words. Validation accepted it. GPT-OSS proposed the same face and delivery but supplied no evidence, so validation rejected it and returned the unchanged neutral fallback. The Qwen speaker replied sympathetically in all three arms. This is one grounded affect proposal; it does not show that the sad face or gentle delivery would feel right when seen or heard.

On the explicit curious-face request, every speaker arm issued one persistent `set_expression` request. GPT-OSS proposed to hold its state. Qwen proposed to set curious, but the explicit face override caused validation to reject that change and return the current neutral state. The runtime receipt records a persistent curious request from the speaker; it does not prove the renderer showed it.

On the prior neutral-face preference, both raw reader outputs proposed keeping neutral and cited the earlier request. The single-speaker arm also issued a neutral expression call; the paired speaker arms did not. The speaker outputs varied, so this run cannot attribute the call difference to adding a reader.

On the sad-face correction, all three speakers issued one sad-face request. Qwen's reader held the existing sad preset. GPT-OSS proposed sad variant 1 with gentle delivery, based on the earlier request and the correction. That schema-valid choice may be more theatrical than the requested sad preset. Because the reader proposal was not applied, the experiment did not enact a speaker/reader conflict. A production design still needs one renderer owner.

The negative question, “Can you not talk with a sad face, though?”, lacked the earlier face demonstration described in the case metadata; that metadata was kept out of model inputs. Qwen proposed changing neutral to neutral, and validation rejected the inconsistent change. GPT-OSS held neutral. Both completed speaker replies assumed the user meant that the face could stay sad during speech. The text also permits a request to avoid speaking with a sad face, so one focused clarification would fit better. This case cannot judge whether the reader inferred the intended prior face.

For a factual answer after “Keep the sad face until I change it,” both readers proposed holding sad with neutral delivery. Their timing differed: Qwen finished after the first phrase boundary; GPT-OSS finished before it. Both Qwen speakers that completed the turn answered “Fifty-six.” The GPT-OSS-paired Qwen speaker timed out, so that arm has no reply for this case.

## Timing, failures, and limits

The reader started at user-turn dispatch with an empty proposed phrase. It did not wait for the speaker and did not block speaker output. Qwen finished before the first phrase boundary on 3 of 6 cases. GPT-OSS did so on all 4 cases where the speaker produced a phrase. The GPT-OSS-paired Qwen speaker ended in `ReadTimeout` on the negative-question and factual-answer cases; both missing replies stay in the denominator of six. The reader still completed those requests, and its outputs and errors are retained.

An independent review of the separate three-turn live Qwen probe found that the reader completed after speech started on the two turns that needed a new delivery decision. The reader therefore could not change those turns' TTS style. That probe did not verify browser playback or what the person heard; details are in [SEMANTIC-REVIEW.md](SEMANTIC-REVIEW.md).

This experiment does not rank naturalness, measure prosody, prove face visibility, or test renderer persistence. It covers six authored cases with one run per arm. The late-result fixture did not deliver a second live user turn, so stale-revision handling was not measured. The initial failed attempt remains preserved in the sibling `comparison` folder; the corrected run writes each run's speaker text, reader result, timing, and provider errors to an atomic `raw.json` before aggregation.

## Artifacts

- `comparison.json` contains the six-case result, tool receipts, source hashes, reader traces, and errors.
- `index.html` shows validated and raw reader decisions, speaker output, provider errors, and measured timings.
- `smoke.json` and `remaining.json` preserve both bounded invocations. Each arm result links to its per-run `raw.json`.
- `harness-source-frozen.py` and `prompt-frozen.txt` contain the runner and speaker prompt used for the corrected run.
- `four-case-primary.json` is a compact view; the main comparison retains all six completed cases.
