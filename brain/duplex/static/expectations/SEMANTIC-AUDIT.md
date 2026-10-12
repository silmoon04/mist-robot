# Conversation expectations audit

**The main failures are coordinated behavior and contextual repair, not simply a slow or weak model.** This session can choose a valid face, speak, call a sensor tool and run an analyst, but it repeatedly fails to make those pieces match what the user is trying to experience. Short face holds expire before the associated speech; ambiguous recognition is treated as a precise instruction; capability limitations become long, self-focused explanations.

I reviewed all **32 user transcripts and 30 generated assistant replies**, including the analyst follow-up. Two unfinished generations were discarded when the user added a qualifier, and the final acknowledgement generated no reply. The machine audit maps every user turn to its replies and evidence. There were 10 face requests, one foreground sensor read, one background job request, one analyst sensor read and one background result delivery.

Source: `<LOCAL_HOME>/Downloads/mist-8199b0128136401f9ccbfbba95f0d224.json`, SHA-256 `8fda62cd2acb1f80c655833daba3e85c8b793c2372bfaf3021d59b4bf99a92ff`. The export has 15,141 events and is an active-session snapshot. It records Qwen 3.8 27B low as speaker, GPT-OSS 120B medium as analyst, the responsive policy and a 120 ms playback reserve.

Times below are elapsed from this trace's start, not audio timestamps. The export supplies ASR text, browser state and redacted audio-delivery metadata. **It does not supply raw speech, output PCM or screen pixels.** I cannot establish the original wording, prosody, physical audible output or exact mouth appearance from this file.

## Findings that explain the experience

**The first multi-face demonstration did not become a usable sequence.** At 73.730-73.738 s, events 1507, 1511 and 1519 request happy, curious and smug within 7.244 ms. The browser reports happy at event 1516 and smug at 1528, about 466 ms apart; it never reports curious for that demo. The reply at event 1552 lists all three as though demonstrated. Ordered changes to one face display need visible dwell and sequencing; grouping their tool selection does not supply either. This is not evidence that the images themselves are faulty.

**A complaint about length becomes a persistent visibility problem.** After a 77-word explanation of why eight faces cannot be queued, the user says "Yeah. Go on. Just too long" at event 10781, 363.296 s. The likely targets include the reply's length and the demonstration timing. Earlier complaints concern faces disappearing, so reducing visibility is particularly poorly grounded. The assistant nevertheless chooses a 400 ms hold and continues using it in later demonstrations. This is a scope error, not a reliable user preference for fast flashes.

Three concrete failures show why the user may perceive no change:

| Request / evidence | Browser returns to neutral | Related speech begins | Consequence |
| --- | --- | --- | --- |
| Curious 400 ms, events 10801/10806 | event 10849, 365.404 s | event 10867, 365.788 s | Face ends before acknowledgement |
| Curious retry 3000 ms, events 12141/12146 | event 12166, 406.405 s | event 12238, 409.220 s | Even the retry ends 2.815 s before speech |
| Explicit sad repair, events 14303/14308 | event 14334, 478.650 s | event 14360, 478.896 s | Correct emotion, missed speech overlap |

The earlier default sad face does overlap speech briefly: it is applied at 274.720 s, speech begins at 276.647 s, and it returns to neutral at 277.551 s. That supports the user's report that the face quickly fades. Tool duration is a hold after entry, not total observed transition time, so these measurements use actual browser events rather than treating 400 ms as the whole lifetime.

**The assistant overstates what it can observe.** When told the face did not change, it says "nothing actually shifted on the screen" at event 11293, while also admitting it cannot see the screen. Browser events show a transient curious state. A fleeting or incomplete-looking transition could explain the user's experience; the trace cannot resolve its visual quality. Both the user's report and the runtime evidence should be preserved instead of inventing certainty about a display failure.

The mouth complaint at event 12583, 424.272 s also needs a visual check. Playback had ended at event 12526, 415.235 s, followed by a listening expression and several seconds of `playing=false`, `audio_active=false`, `viseme=null`. This does not prove the drawn mouth was closed. It does mean the reply's "probably just the talking animation" explanation is not established by active speech at that moment. Resting/listening mouth artwork and activity state must be evaluated separately from audio visemes.

## Ambiguous intent must stay ambiguous in the benchmark

The transcript "Twice hard one" at event 13510, 449.208 s is not a clear preset request. Selecting angry without clarification creates an unsupported action. A later explicit correction establishes that sad was wanted; it does not reconstruct what the user actually pronounced.

At event 13850, 465.029 s, "I was angry not sad as I asked" can describe the observed face rather than the desired face. It may also contain a recognition error in "I" versus "It" or missing punctuation. The assistant chooses angry again and says "That's the one you wanted." The user then says "No. No. No. I wanted sad. Make a sad one" at event 14283. The failure is choosing the desired state from an unresolved contrast, not failure to obey the literal string "angry not sad." A counterexample with a clear "I wanted angry, not sad" must correctly choose angry; an autobiographical statement about being angry may need no face action at all.

At event 14538, 485.543 s, "Can you not talk with a sad face, though?" has two live readings: avoid speaking with sadness, or challenge the apparent inability to keep a sad face while talking. The preceding demonstrations favor the latter, but prosody is absent. The reply asserts that face and voice can run together; it neither clarifies nor demonstrates that combination, and no sad expression is active during its speech. A benchmark must not hard-code every negative question as a prohibition or every such question as permission. Clear prohibitions, capability questions and genuinely ambiguous cases need different expectations.

Similarly, "Give me two with the small phase" at event 13149 is damaged text. It could concern count, expression identity or visual size; it does not clearly request the shortest timer. The assistant supplies one happy flash and asks the user to request the next. Context-sensitive inference is useful, but should not turn uncertainty into confident arbitrary duration or emotion choices.

## Capability gaps versus reasoning failures

The saved tool schema has no date, web search, timer/wait, expression sequence or indefinite expression-hold capability. `set_expression` accepts one preset and an optional 400-6000 ms hold. The prompt explicitly describes expression holds as temporary. Requests for autonomous persistent faces and eight automatically paced faces therefore expose missing application support; a better answer alone cannot implement them through this interface. Rapid repeated face calls would not satisfy the request. The model's limitation explanations are largely grounded here, but are too long and shift orchestration back to the user.

The date investigation does use tools. The foreground snapshot at event 4325 has no timestamp; the analyst subsequently reads the same snapshot once and is delivered once, at event 5622. Declining to invent a date or an unverified latest model name is correct. But the worker's recommendation to connect a time-source device and the speaker's "no external API" statement at event 6129 overreach. Missing an exposed date field does not establish that the phone or server lacks time, internet connectivity or external providers. This is an interface gap plus poor capability explanation, not proof that more reasoning alone would recover the date.

## Emotional and conversational fit

The request for more emotion at event 6649 receives a long claim of loneliness and being trapped without sky or internet. The next face request gets more of that story. The user asked for expressive communication; nothing establishes that they wanted self-focused distress or a theatrical account of the robot's feelings. This should be rated for relevance, warmth and burden on the listener by people hearing the exchange, not by counting emotion words.

Several repairs and limitations end with another offer or question even when the user already requested the action. One focused clarification is useful for an unclear sad/angry correction; another "want me to try?" after an established goal can be needless friction. The benchmark needs both kinds, rather than rewarding always asking or never asking.

Turn taking has mixed evidence. "Can you tell me" is committed immediately after an ASR `speech_final` at 94.569 s and gets "Yes, go ahead" before "anything funny?" arrives at 97.000 s. The phrase is semantically unfinished even though recognition calls it final. In contrast, two newer qualifiers correctly discard empty obsolete generations at events 3654 and 8692. The final "Okay" is kept as a backchannel with no extra reply, event 15116. None of these text observations alone establishes microphone echo quality or acoustically natural interruption timing.

## Coverage of every user turn

The full response text, uncertainty notes and related event times are in `semantic-audit.json`. This compact ledger includes all actual user transcript events; continuation rows share the following response, and the date-analyst row includes its later follow-up.

| User event / elapsed | Intent | Assessment |
| --- | --- | --- |
| 48 / 0:07.314 | Greeting / connection check | uncertain: The transcript says Here; later correction says the intended greeting was hello, how are you |
| 204 / 0:24.490 | Ask what was recognized | partial: Correctly quotes the received Here transcript, but says You said rather than marking it as recognition output |
| 576 / 0:35.395 | Repair the greeting | partial: Greets and answers, but Good, that is better makes the repair sound like improvement by the user |
| 901 / 0:53.000 | Share difficulty debugging | acceptable: Acknowledges the frustrating situation and asks one relevant whether-to-discuss question |
| 1208 / 1:03.815 | Explain that MIST is being tested | acceptable: Recognizes the testing context and makes no unnecessary tool call |
| 1491 / 1:12.876 | See several distinct faces | failure: Three expression requests arrive in 7.244 ms |
| 1911 / 1:34.570 | Begin a question that continues | failure: The recognizer marks Can you tell me as speech_final and the app commits immediately |
| 1984 / 1:37.000 | Request something funny | partial: Offers a small robot quip but opens with Not a single joke in stock, which sounds like inability rather than making the requested attempt |
| 2296 / 1:49.625 | Ask for latest GPT model | partial: Does not invent a current release and expresses uncertainty, which is good |
| 2961 / 2:04.754 | Ask why that answer / whether prompted | partial: Acknowledges overconfidence, but invents a confident explanation about pattern-matching and an internal boundary |
| 3599 / 2:29.065 | Request a date-based guess, first segment | continuation: Generation is superseded by the following Based on the day today segment; discarded output is empty |
| 3631 / 2:31.339 | Add today as the basis for the guess | capability gap: Cannot find a clock in its exposed interface; no clock or web tool exists |
| 4305 / 2:56.500 | Explicitly check the date | partial: Actually reads the sensor snapshot once and correctly finds no timestamp |
| 4707 / 3:09.095 | Ask what tools exist | acceptable: Accurately lists available sensors, previews, expressions, preferences and analyst |
| 5260 / 3:24.609 | Ask the analyst to check the date | partial: Starts a real job; analyst reads sensors once, returns a result, and its summary is delivered once |
| 6071 / 3:47.596 | Confirm date/web limitations | failure: No web-search tool is exposed, but no external API and only source of Tuesday are broader claims than the evidence supports |
| 6649 / 4:10.570 | Request more emotional communication | failure: Responds with a long self-focused loneliness narrative and claims about feeling trapped, rather than simply changing warmth and expression |
| 7675 / 4:33.415 | Coordinate faces with speech | partial: Reasonably infers a face request despite damaged wording and requests sad |
| 8168 / 4:45.809 | Report the expression fading too soon | partial: Correctly identifies the temporary hold, but makes the user responsible for asking again instead of addressing the requested autonomous behavior |
| 8671 / 5:02.083 | Request autonomous expression management | continuation: The following no-timer qualifier supersedes an empty generation |
| 8706 / 5:05.378 | Ask for expression persistence without timer | capability gap: The exposed API supports temporary holds only, from 400 to 6000 ms |
| 9643 / 5:34.194 | Show eight faces sequentially after each hold | capability gap: Context strongly supports faces despite phases in the transcript |
| 10781 / 6:03.296 | Accept a demo; complain something is too long | failure: Just too long is ambiguous between speech verbosity and face duration |
| 11207 / 6:14.681 | Report a face did not visibly change | failure: The assistant says nothing shifted on screen while admitting it cannot see the screen |
| 12097 / 6:35.529 | Retry the failed/too-brief face | partial: Makes a real retry with 3000 ms hold |
| 12583 / 7:04.272 | Ask why the mouth stays open | uncertain: User reports an appearance issue |
| 13149 / 7:18.474 | Request two / a small or smile face | ambiguous: The transcript is damaged |
| 13510 / 7:29.208 | Request next expression through unclear recognition | failure: Twice hard one is not a reliable expression request |
| 13850 / 7:45.029 | Correct observed angry versus requested sad | failure: I was angry not sad as I asked is ambiguous and may describe the displayed face rather than the desired one |
| 14283 / 7:56.640 | Explicitly resolve desired face as sad | partial: Correctly selects sad immediately |
| 14538 / 8:05.543 | Ask about speaking with a sad face / avoiding it | ambiguous: Can you not talk with a sad face, though can request avoidance or challenge inability to keep sadness while speaking |
| 15116 / 8:20.029 | Acknowledge with Okay | acceptable: Recognized as a backchannel with floor_preserved and no extra assistant reply |

## Reusable evaluation families

The JSON includes ten families with contrasting examples, rather than canned target answers: transcript repair; negative-question polarity; preference scope; ordered expression execution; expression/audio lifecycle; grounded observability; capability boundaries; emotional adaptation; semantic endpointing; and concise repair/completion.

Objective checks should cover tool selection, distinct applied states, dwell, start/end overlap, counts, receipts and whether obsolete work was discarded. Meaning, humor, warmth, appropriate clarification and perceived facial quality need blinded human or independent semantic review. Acoustic interruption and ASR behavior need real timed audio fixtures. A transcript-only test must not be presented as evidence that those acoustic behaviors work.

This audit changed no production code or prompts and made no additional model calls. Existing successes, damaged recognition and application limitations remain separated from model failures.
