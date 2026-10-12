# Face and voice reader

The optional `qwen-affect` and `oss-affect` studio profiles use the existing Qwen speaker and a separate affect reader. The default architecture is unchanged. The reader selects a face and a delivery profile; it has no application tools and cannot generate spoken words.

At the end of a user turn, the application starts both model requests. The reader receives bounded conversation records, the current persistent face, and any current face constraint. Unverified generated assistant text is excluded. The speaker continues without waiting for the reader.

A reader proposal must pass the face schema and cite exact supplied text for a change or a non-neutral delivery. This verifies the source of the quote, not the quality of its emotional interpretation. The application applies an accepted proposal only before the speaker starts its output turn and while the user revision, expression revision and face serial still match. A new user turn, manual replacement or intervening model face request invalidates it. One reader request may be in flight at a time. Busy, late and rejected results are recorded and discarded.

The application owns persistence. A face request without `duration_ms` stays until another accepted choice replaces it. Listening, thinking and speech do not reset it. A timed flash returns to the previous persistent face. While that flash is active, the reader may suggest delivery but cannot replace the face. The browser acknowledges the return to the base face with its epoch, expression revision and face serial; stale acknowledgments do not release the hold. Audio resets also restore the base.

Delivery starts at `neutral` for each new user turn. A timely proposal can select another profile before the first provider frame is sent. Flash varies stability only. The `qwen-expressive` profile uses Eleven v4 Turbo's Text-to-Dialogue WebSocket and adds one controlled delivery tag at the beginning of the reply. All phrases share one voice, context and delivery. Speech does not wait for the reader. Mouth cues remain tied to the playback clock and provider alignment, with audio-energy fallback when timings are missing.

The reader prompt is `affect-director-v2.1`. Cerebras receives a strict JSON Schema so a delivery word cannot become an unlisted face name. Local validation still checks the face variant, current override and exact evidence quotes. The prompt chooses face and voice separately, keeps faces across replies, and avoids routine grins, theatrical sadness, anger at corrections, or acting out every thinking/tool state. Evidence must come from the public conversation. Proposed assistant text can inform delivery but cannot be cited as something already heard. Unclear context keeps the current face and neutral delivery.

| Delivery | v4 Turbo control | When it fits |
| --- | --- | --- |
| neutral | No tag | Ordinary conversation and technical explanations |
| warm | `[warmly]` | Friendly acknowledgement |
| gentle | `[gently]` | Restrained empathy |
| bright | `[excited]` | Genuine good news or shared success |
| serious | `[seriously]` | Measured gravity |
| curious | `[curiously]` | Interested inquiry supported by context |
| amused | `[amused]` | Invited or shared humour |
| reassuring | `[reassuringly]` | Steady support without promising an outcome |
| urgent | `[calmly]` | A clear priority or stop instruction, without panic |

These tags request delivery; they do not guarantee an emotion. The reader cannot send arbitrary tags, edit speech, alter voice identity, or add laughs and fillers. The speaker still owns phrasing. Unsupported `style` and speaker-boost controls are omitted for v4 Turbo. Numeric stability is not presented as a named emotion control. Changes that arrive after synthesis starts are discarded instead of restarting audio or changing its delivery mid-sentence.

The trial Voice selector is independent of architecture. It offers MIST (refined), Jessica, Laura and Callum as session-local choices and keeps MIST as the default. The chosen identity is stored in the trace. Listening-cue cache lookup uses the same voice identity, so a missing alternate-voice clip cannot play in MIST's voice.

The trace records `affect_decision` with elapsed time, evidence, outcome and revision context, plus `speech_style` with the setting actually sent to ElevenLabs. Public trace export excludes credentials and hidden model reasoning.

## Verification

The controller tests exercise non-blocking submission, one-request concurrency, closure and rejected proposals. Studio tests cover ownership changes, speech deadlines, delivery reset, unheard history, temporary faces and stale browser acknowledgments. Browser tests exercise persistence through delayed speech, interruption and state changes, with all 40 existing faces.

The live smoke probe uses real text input, Cerebras and ElevenLabs through the trial WebSocket. It does not test microphone recognition, audible browser playback or human quality. The text comparison also cannot establish those properties. Provider voice samples establish synthesis and timing support; listening judgments remain separate.

Experiment files and rerunnable probes are in `brain/results/dual-model-harness-20260924/`, `brain/benchmarks/naturalness/affect_comparison.py`, `brain/harness/probe_affect_live.py` and `brain/harness/probe_affect_prosody.py`. `brain/harness/build_affect_review.py` publishes selected reports and samples at `/duplex/affect/index.html`.
