# Luna verification, 22 September 2026

The tested application is ready for another user trial, subject to the existing ElevenLabs payment block. Luna can select all 40 faces, and the application rejects the tested invalid or unintended requests. Conversation tests prompted several fixes. They do not establish perfect model behavior or fresh audible voice quality.

Open [the test viewer](http://127.0.0.1:8790/duplex/luna-tests.html) for transcripts, tool receipts, timing distributions and independent reviews. Earlier failures remain visible alongside later fixes. The Download evidence link exports the snapshot.

## Coverage

The snapshot contains 444 recorded model inputs or jobs across 22 runs:

| Suite | Records |
| --- | ---: |
| Direct Luna conversations, six runs | 217 |
| Luna face requests, four runs | 148 |
| Luna text timing trials | 28 |
| Native spoken-input and handoff trials | 33 |
| Luna background jobs | 18 |

Cases include casual and terse conversation, typos, language changes, dry humor, low energy, emotional support without unwanted advice, corrections, pronouns, topic changes, exact memory recall, silence, interrupted answers, sensors, unavailable camera data, preview movement, explicit and figurative commands, quoted instructions, all faces and invalid variants. Separate agents reviewed conversation, faces, latency, native delegation, background work and application behavior.

These are counts of inputs/jobs, not independent user studies. Some runs share scenarios, use synthetic speech or exercise a refinement. Rubrics differ, so there is no combined pass percentage. Deterministic checks and historical call replays are separate from the 444.

## Resulting changes

- Both immediate backing tools and background analysis default to GPT-6 Luna, low reasoning, default service tier. Explicit model overrides remain supported. Codex native realtime V3 still handles listening and spoken conversation; it is a separate model.
- The persona better follows requested tone and length, avoids forced humor after a correction, keeps ordinary context without automatically storing it, and stops narrating expression metadata.
- Request checks reject unavailable or mismatched face variants, quoted or negated actions, temporary preferences presented as durable memory, and phrases such as "walk me through" being dispatched as movement. These are conservative English checks, not a general multilingual intent classifier.
- Movement tool descriptions state units and supported limits. Background analysis no longer implies individual-leg control, collision checking, servo self-tests or a live camera that the app does not have.
- Native tool requests use the originating turn and current user text. Superseded requests and missing context are refused before dispatch, including background jobs. Stop remains available independently of the ordinary budget and request callback.
- The visible assistant transcript uses accepted, matching native turns. Interrupted text is cleared. Late fragments and completions cannot overwrite a new answer. Predictive text still prepares TTS at the original time; the captured TTS event sequence is unchanged.

## Verification

All 40 source faces were selected correctly in two real Luna sweeps and through the actual guarded native dispatcher. The final adversarial face sample achieved 15/15 display protections but only 12/15 strict model selections: three model mistakes were blocked. The final five-turn memory follow-up passed all strict and state checks after correcting an overly narrow guard for "And remember...".

Final aggregate: **132 Python tests pass**. The expression policy passes **38,327 assertions** covering 14 scenarios, all 40 faces, 1,560 directed selections and 10,000 mixed events. Actual app-handler, packet playback, output-clock mouth sampling and delivery tests also pass. Independent QA verified stop, stale turns, predictive user prefixes, background requests and the final source hashes. These checks establish application behavior; assertion counts are not additional conversation trials.

The native transcript regression reconstructs all 17 completed captured answers exactly while preserving their TTS input sequence. A separate comparison of 15 completed TTS replies found 14 exact matches with accepted text. The remaining predictive reply added "Okay" before "I'll be quiet until you're ready." No substantive meaning change appeared in this small sample. Fixing visible text does not establish word-perfect synthesized speech. The client regression also verifies that an interrupted partial answer cannot join the next answer and that a late old reset cannot erase new text.

The local service was restarted with these settings. Its configuration reports Luna for both backing roles, low reasoning, default tier, streaming TTS, fixtures disabled and no hardware connected. Browser checks verified the transcript filters, expandable receipts, timing table and the new Luna tests link in conversation controls. The report had no browser errors.

## Timing

| Measurement | Observed result |
| --- | --- |
| Native ordinary reply, last input audio frame to first predictive text | 0.75 to 1.05 seconds in the nine-case refined run |
| Native requested face or sensor acknowledgement, same interval | 5.14 to 7.27 seconds |
| Face tool event after last input audio frame | 2.47 and 2.99 seconds |
| Broad 86-turn Luna run, first complete phrase | 1.49-second median, 3.03-second nearest-rank P90 |
| Final four background jobs, completed answer | 4.02 to 8.31 seconds |

The native figures measure predictive text, not accepted UI text or speaker onset. The separate native speaking layer delegates tools to Luna; its round trip is still the main delay in explicit tool responses. Background jobs return an immediate handle and can run while input continues.

Matched low-reasoning default/priority trials did not show a consistent overall benefit from priority. Shorter backing instructions and a different handoff format also failed to show a consistent quality/speed improvement, so production routing was retained. One rejected trial ended an utterance early, acknowledged without an action, and merged later inputs. Its apparently quick acknowledgement is a failure, not a latency improvement. Small shared-load samples do not establish causal performance guarantees.

## Remaining acceptance work

The configured MIST (refined) voice lookup succeeds, but ElevenLabs reports a past-due subscription and minimal synthesis returns payment_required. No billing settings were changed. Native spoken-input tests therefore recorded TTS text without synthesizing final MIST audio. Final voice quality, exact audible latency, acoustic echo handling and phone lip-sync remain unverified. Saved audio and controlled playback clocks support renderer checks only.

Luna still sometimes makes an inappropriate tool choice; tested application checks contain those cases. Native endpointing and predictive-versus-accepted wording are additional limitations outside the backing model. Physical robot motion remains preview-only. No hardware movement was used in these tests.

## Evidence

- [Conversation summary](../results/luna_conversations_20260922/conversation_summary.json)
- [Face guard review](../results/luna_faces_20260922/GUARD_REVIEW.md)
- [Independent final review](../results/luna_review_20260922/final_review.md)
- [Final Python log](../results/luna_review_20260922/final_regressions.log)
- [Default/priority review](../results/luna_latency_20260922/REVIEW.md)
- [Native handoff comparison](../results/luna_latency_20260922/HANDOFF_REVIEW.md)
- [Accepted background run](../results/luna_background_20260922_capabilities/review.json)
- [Provider blocker](LIVE_SYNC_BLOCKER_20260922.json)

Rebuild the browser snapshot with `python brain/harness/build_luna_review.py`. This reads existing reports; it does not call any model.
