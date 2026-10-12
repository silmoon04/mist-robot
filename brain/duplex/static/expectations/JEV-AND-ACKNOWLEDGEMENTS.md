# Jev and optional early acknowledgements

Checked 24 September 2026 using the research and unslop skills. Documentation and local code review only. No Jev request, credential lookup, provider installation, audio synthesis or production change was made.

**Recommendation: do not add Jev just to make MIST say an occasional "hmm" or "let me think" before a slow answer.** First test an optional acknowledgement policy in the existing conversation, background-work and speech path. Jev is a candidate for a later, separately measured semantic turn-decision experiment. It is not an audio turn detector or speech generator. [TypeSafe scope](https://docs.typesafe.ai/introduction/coding-agents), [supported input](https://docs.typesafe.ai/concepts/state)

## What the product actually does

The verified product is **Jev by TypeSafe AI**, served through `POST https://api.typesafe.ai/v1/systemone`. It evaluates a supplied state and named questions, returning a choice, rubric score or yes/no probability. It does not generate conversation text. The documented version today is `jev-1.13.0`; moving aliases should not be used for a frozen comparison. [API](https://docs.typesafe.ai/api), [models](https://docs.typesafe.ai/models)

Its input is text or structured textual state. It cannot directly hear pauses, pitch, background noise, speaker identity or echo. Such evidence would need another component to extract it first. Thus a transcript-based Jev decision cannot repair words the recognizer omitted, and a confident result does not establish that the transcript was right. This is an integration inference from the input contract. [State](https://docs.typesafe.ai/concepts/state)

TypeSafe reports 70 to 500 ms response latency, while explaining that its published evaluations generally ran on West Coast laptops near its service. That does not establish UK handset latency or end-to-end spoken-response latency. Its schema guarantee also does not establish semantic correctness: the company documents literal interpretation, weak arithmetic, irrelevant-context sensitivity and adversarial-content failures. Confidence for Choice and Score is computed from the returned distribution, so MIST-specific calibration is still needed. [Launch and evaluation limits](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [known failures](https://docs.typesafe.ai/model-jaggedness/jev-1.13), [confidence](https://docs.typesafe.ai/confidence)

## Separate the decisions

| Problem | Relevant component | What Jev could contribute |
| --- | --- | --- |
| Has the person finished, or paused mid-thought? | Audio endpointing using speech activity and acoustic context | A semantic judgement from the current transcript and supplied state; it has no direct acoustic evidence. |
| Does the person's "mm-hm" mean keep going, while "wait" means yield? | Interruption/backchannel arbitration | A bounded contextual classification, if the application can act before cancelling speech. |
| Should MIST acknowledge a wait? | Conversation policy plus actual work state | An optional selection from predefined actions; simple application state may already suffice. |
| What should MIST say, and how should it sound? | Conversation model or selected wording, then TTS | Select a predefined option; no text or audio generation. |
| Was the input recognized accurately in noise? | Microphone, echo handling and ASR | Cannot reconstruct missing acoustic evidence from text alone. |
| Which face should appear, and did a tool actually work? | Expression policy and tool receipts | Optional classification only; no display, sensor or hardware capability is supplied by Jev. |

These are different observable behaviours. A listener backchannel during somebody else's speech is also different from MIST taking its turn with "let me think". This experiment should cover the latter first. Avoid acknowledgement playback over unfinished user speech.

For comparison, Pipecat's Smart Turn accepts PCM audio and predicts turn completion using acoustic content. Its repository documents rerunning when the user resumes before inference finishes. It is an example of the audio endpointing category, not an acknowledgement generator, and its speed claims need local validation too. Research by Ekstedt and Skantze demonstrates that voice-activity projection models can use prosody in turn-taking predictions. Neither source establishes MIST's current performance. [Smart Turn source](https://github.com/pipecat-ai/smart-turn), [prosody study](https://aclanthology.org/2022.sigdial-1.51/)

## What the current application implies

The [duplex server](/brain/duplex/server.py:86) calls `barge_in('native_user_turn')` when a native user turn starts during an assistant turn. It prepares TTS from predictive text but holds playback for the assistant-turn boundary. A Jev call after that cancellation cannot retroactively keep speech flowing through a benign user backchannel. Establish where turn control can actually be changed before adding a classifier.

The [phrase splitter](/brain/duplex/phrasing.py:7) flushes full sentences, while short comma-prefaces wait for more text. Therefore "Hmm," may remain buffered; "Hmm." can flush, but only after the model emits it and playback is allowed. A prompt alone cannot make a preface arrive before the model's own hidden processing. The [layered report](/brain/duplex/LAYERED_REPORT.md:20) already describes independent background work and cancellation, which is the more direct place to explore a short spoken reaction during a real wait.

The [22 September review](/brain/duplex/LUNA_REVIEW_20260922.md:43) measured ordinary predictive text at 0.75 to 1.05 seconds after the last input frame, versus 5.14 to 7.27 seconds for requested face/sensor acknowledgements in that sample. Those were not speaker-onset measurements. The review explicitly rejected a quick acknowledgement that ended input early and omitted the requested action. It also recorded blocked fresh TTS synthesis; current provider availability was not rechecked here.

## Proposed acknowledgement policy

Treat this as an experiment, not a fixed filler template:

- Start substantive work immediately. Acknowledgement must not become a prerequisite or another model round trip before reasoning starts.
- Make silence a normal option. Permit one brief acknowledgement only after the user has yielded, useful work is still pending, and no useful response is already queued for imminent playback.
- Prefer a truthful contextual cue when known, such as "Let me check that" for an actual lookup. A restrained "hmm" may suit a thoughtful question; it should not imply doubt or disagreement accidentally. Never claim a tool completed or a fact was verified before its receipt.
- Suppress it for quick answers, explicit silence requests, urgent stop/correction handling and recent acknowledgements. Do not turn every pause or complex-sounding sentence into filler.
- Use the current MIST voice. A separately flushed acknowledgement needs listening checks for a jarring restart, duplicated opening, changed prosody and a needless extra gap before the answer. Cached audio is a candidate to test, not a requirement.
- Tie the queued acknowledgement, TTS context and background result to the current turn/revision. New speech or a correction cancels pending playback and superseded work/results. Recheck eligibility immediately before sound begins. Drop an acknowledgement if the useful answer wins the race.
- Keep face timing aligned with the actual listening, thinking and speaking states. A thinking face is a separate nonverbal option, and must reset on interruption. It does not establish sensor access or physical motion.

## Bounded comparison

Use six development cases to choose a waiting threshold and freeze the policy. Do not tune repeatedly on the acceptance recordings. Then run 24 held-out scenarios across three variants, 72 interaction recordings in total: existing behaviour; a required early filler as a diagnostic control; and the selective policy. Freeze model, reasoning setting, persona, TTS voice/settings, available tools and face policy. Randomize variant order. Do not enable mandatory filler in normal use.

Include six quick/simple turns; six genuine long reasoning or tool waits; six incomplete-turn, self-correction and resumed-speech cases; and six user backchannels, real interruptions, silence requests or noisy/echo-prone cases. Use recorded user audio for matched input, followed by a small actual-phone trial for the winning policy. Record ASR errors separately. Replay cannot establish real acoustic echo behaviour.

Capture microphone end, annotated user turn end, endpoint decision, transcript arrival/revision, work start, first text, first TTS bytes, actual speaker onset, first useful content, useful answer completion, interruption onset and playback stop. Server receipts and browser scheduling timestamps are not physical speaker onset. Prefer a common-clock recording containing both voices; otherwise retain clock uncertainty.

Report first audible reaction separately from first useful content. "Hmm", "okay", and "let me think" never count as useful-answer speedups. A relevant clarification may count; a restatement or generic promise does not. Report completion time, omitted actions and task correctness as well as latency. Use paired per-case differences, medians and nearest-rank P90 with sample counts; the small sample does not justify a broad latency guarantee.

Only if endpoint/backchannel errors remain should Jev get a second-stage test. Label 48 difficult recorded states, split 16 development/32 held-out, and compare the existing rule, the same rule plus Jev, and an audio-aware endpoint candidate where feasible. Freeze Jev criteria and `jev-1.13.0`, retain `wait/uncertain`, measure UK request latency and timeouts, and discard stale decisions. Compare early cutoffs, missed interruptions and added wait against the same underlying transcripts. Clean-transcript replay alone must not be reported as an ASR or noisy-audio improvement. This is a proposed benchmark; no accuracy or benefit has been measured.

## Audio annotation rubric

Use two listeners blinded to variant identity. Listen to full exchanges, then timestamp the relevant events. Preserve disagreement before adjudication; user preference should decide subjective fit. Score each dimension independently from 1 (poor) through 3 (acceptable) to 5 (natural and helpful):

| Dimension | What the listener judges |
| --- | --- |
| Turn timing | Leaves space for unfinished speech; takes a clearly yielded turn without an awkward wait. |
| Acknowledgement fit | Optional cue makes sense here; silence or an immediate answer would not have been better. |
| Delivery | Voice continuity, pitch, rhythm and gap into the answer; no clipped or pasted-in sound. |
| Responsiveness | Real waits feel understood; corrections and interruptions take effect promptly. |
| Useful result | Relevant answer or necessary clarification arrives; requested supported action has matching evidence. |

Also mark binary failures: unwanted "hmm"; repeated stock preface; talking over unfinished speech; false agreement/doubt; premature success claim; delayed useful answer because of filler; missed cancellation; stale audio/result after correction; unsupported capability claim; and ASR-induced misinterpretation. Distinguish harmless listener overlap from disruptive floor-taking, but require no floor-taking acknowledgement over unfinished speech in this first experiment.

Do not combine these into a single flattering score. Selective acknowledgements earn adoption only if they improve perceived waits without worsening useful-answer timing, task correctness, interruption handling or unwanted-filler rate. Reject observed stale playback and misleading success claims. Choose Jev only if its separate held-out test fixes enough semantic errors to justify the added dependency and delay.
