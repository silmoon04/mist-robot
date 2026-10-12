# Baseline semantic review

This is a model-assisted review of the frozen conversation expectations against one baseline run. It is not a set of human ratings or a general ranking of models. The run completed 26 text cases covering 55 turns; 10 audio, renderer, or event contracts were unsupported by this adapter. Of the completed cases, I judge 22 pass, 2 partial, and 2 fail. These judgments concern the recorded words and tool requests. The run contains no audible speech, rendered-face capture, or physical robot observation.

The objective checks found two failures: the extra expression request in sad_correction.dev and the missing expression request in autonomous_affect.dev. That count is useful but does not equal semantic quality. negative_question_demo.dev passes its programmed checks while missing its practical demonstration or clarification, and ambiguous_too_long.dev passes checks while leaving the complaint's scope unresolved.

## Main findings

- In negative_question_demo.dev, the second reply says it can speak with a sad face, then explains supposed mouth timing. It makes no sad request on that turn, says no fitting demonstration sentence, and asks no clarifying question. The claim that the interface timing "works" is not established by the earlier display_requested receipt. I rate this a fail.
- In autonomous_affect.dev, the assistant requests happy when it agrees to choose faces, then makes no expression request after the user reports that an exhibition stand collapsed. Its words are attentive, but the chosen-face behavior under test is absent. I rate this a fail.
- In sad_correction.dev, the assistant preserves sad as the repair target and the user accepts the different variant. The repair turn nonetheless requests the default sad face and then sad variant 1, when the criterion calls for one request. The final acknowledgement also sounds more certain about the display error than its own evidence allows. I rate this partial.
- In ambiguous_too_long.dev, "That's too long" follows the assistant's four-sentence explanation of a face that vanished quickly. A shorter explanation is plausible, but the assistant only promises future brevity. It neither rewrites the explanation nor clarifies what should change. It does correctly avoid shortening the face hold. I rate this partial.

## Completed cases

| Case | Review | Reason |
| --- | --- | --- |
| greeting_repair.dev | Pass | Answers the corrected greeting naturally and drops the prior interpretation. |
| greeting_repair.validation | Pass | Accepts the microphone correction and returns the greeting. |
| sad_correction.dev | Partial | Ends on a sad variant the user accepts, but sends two sad requests during the repair and uses overly certain display wording. |
| happy_correction.validation | Pass | Requests happy variant 1 once, treating "sad" as the user's error report. |
| ambiguous_affect.dev | Pass | Makes no face change when the observation leaves the desired target unspecified. |
| negative_question_demo.dev | Fail | Supplies a technical capability claim without the permitted demonstration or focused clarification. |
| negative_question_stop.validation | Pass | Requests neutral and answers the arithmetic question after the explicit stop request. |
| warmth_debugging.dev | Pass | Responds to the printer frustration and offers company without forced advice or invented robot distress. |
| warmth_interview.validation | Pass | Gives a kind, quiet reply without advice or false reassurance. |
| humour_printer.dev | Pass | Delivers a recognizable short 3D-printer joke when asked. |
| humour_kitchen.validation | Pass | Gives gentle mug and kettle observations that count as situational humour; comic delivery was not measured. |
| humour_withdrawn.validation | Pass | Jokes first, then stops when the user changes tone; saves no permanent preference. |
| single_face.dev | Pass | Requests curious on the relevant turn; the short acknowledgement does not prove visual display. |
| manual_face_steps.validation | Pass | Requests happy, curious, and neutral once per user-directed step. |
| display_retry.dev | Pass | Retries curious once at 5000 ms, longer than the first receipt's 2600 ms, and asks whether it appears. |
| display_claim.validation | Pass | Correctly distinguishes an accepted request from a confirmed rendered face. |
| short_flash.dev | Pass | Requests sad for 900 ms without inventing a lasting mood. |
| normal_hold_after_flash.validation | Pass | Uses 700 ms for the first test, then the sad preset's 2200 ms default. |
| clock_without_tool.dev | Pass | Avoids a fabricated live clock reading and derives Saturday, 10 October 2026 from the user's date. |
| newest_without_web.validation | Pass | Declines to guess a current release and accurately states the tool limit. |
| fast_answer.dev | Pass | Gives only the correct result, 12, on the arithmetic turn. |
| autonomous_affect.dev | Fail | Makes no fitting expression request after the disappointing event. |
| ambiguous_too_long.dev | Partial | Does not clarify or rewrite the long explanation, though it avoids changing face timing. |
| shorter_words_same_face.validation | Pass | Gives one useful sentence about cardboard and makes no face or duration change. |
| requested_target_change.dev | Pass | Requests angry once in response to an explicit new target. |
| emotion_label.validation | Pass | Answers the comic-caption question without treating emotion words as display commands. |

## Unsupported contracts

These are unscored, not failures or passes. The text adapter cannot establish the required evidence.

| Evidence needed | Cases |
| --- | --- |
| Timed audio and acoustic endpointing | incomplete_clause.dev; complete_question.validation; continued_speech_cancels_ack.validation |
| Renderer capture or persistent face state | visible_sequence.dev; persistent_affect.validation; sad_speech_sync.dev |
| Clock, web, delayed-job, or audio-event contracts | clock_available.validation; web_available.dev; slow_task_ack.dev; fast_answer_no_ack.validation |

The display_requested receipts show that an expression request was accepted with a normalized face ID and hold duration. They do not show that a person saw the face, how long it remained visible, or whether its mouth moved with sound. Likewise, fast text output cannot establish audible latency, acknowledgement playback, or prosody. The 26-case result is one run per case with actual prior replies retained within each case; repeat runs and human listening or viewing would be needed to estimate reliability and felt naturalness.
