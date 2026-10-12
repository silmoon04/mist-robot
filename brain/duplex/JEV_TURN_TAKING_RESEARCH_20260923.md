# Jev for MIST turn taking

Checked 23 September 2026. Documentation research only; no live Jev calls, package installation, key lookup, or production changes.

## Assessment

Jev is a plausible semantic decision layer for deciding whether to continue speaking, yield to an interruption, or wait for more input. It does not supply duplex audio, speech recognition, speech generation, or persistent conversation memory. TypeSafe explicitly says Jev does not generate text or hold a conversation. Keep the conversation model and ElevenLabs voice. [Official scope](https://docs.typesafe.ai/introduction/coding-agents)

## Verified interface

- Input is text only: a string or structured JSON state, including message history. Audio, video, and images are unsupported. Transcripts and precomputed acoustic/timing features must come from other components. [State](https://docs.typesafe.ai/concepts/state)
- The documented request evaluates the supplied state; it has no conversation/session identifier or history-management API. MIST should own persistent history and submit a relevant snapshot each time. This is an integration conclusion from the request contract, rather than a claim about provider data retention. [API reference](https://docs.typesafe.ai/api)
- `POST https://api.typesafe.ai/v1/systemone` uses a Bearer API key. Requests contain `state`, `model`, and named `questions`; answers retain those question IDs. Choice returns a permitted option, the option probability distribution, and confidence. Noul returns a yes/no probability. Score supplies a rubric-based value. [API reference](https://docs.typesafe.ai/api)
- Questions sharing one state run independently in one call. A question cannot consume another answer from that same call. Batch intent, completeness, and backchannel judgments, then combine them in code; use another request only for real dependencies. Question IDs are not model instructions. [Primitives](https://docs.typesafe.ai/primitives)
- Confidence is computed from the probability distribution, not an independent verification of correctness. Thresholds need calibration on MIST conversations. [Confidence](https://docs.typesafe.ai/confidence)
- Current documentation lists `jev-1.13.0`, a 64k combined request limit, and a 32k limit for state plus the longest question. Aliases can move; pin the tested model. Published limits are explicitly subject to change. [Models](https://docs.typesafe.ai/models)
- A key comes from the TypeSafe console. The September 15 launch describes early access; actual access for this user is unverified. [Quick start](https://docs.typesafe.ai/introduction/quickstart), [launch announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- TypeSafe reports 70–500 ms end-to-end responses and notes its published evaluations were generally run from West Coast laptops near its service. This is a vendor claim, not a MIST or UK-phone measurement, latency guarantee, or total speech-response time. [Launch announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev)

## Proposed MIST integration

Use bounded decisions such as `backchannel`, `take_turn`, `explicit_stop`, `continuing_thought`, `unrelated`, and `uncertain`. Supply the latest partial/final transcript, recent turns, a compact older summary, current task, whether MIST is speaking, what it has actually said, queued speech, and interruption history. Compute elapsed-time comparisons in code. TypeSafe documents weaknesses with arithmetic, indirect questions, irrelevant context, and literal interpretation; write precise criteria with boundary examples. [Known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13)

These labels are proposed behavior, not tested Jev capability:

| Input while MIST speaks | Intended action |
| --- | --- |
| Brief “yeah” or “mm-hm” | Continue; register acknowledgement. |
| “Wait, I meant the other one” | Yield and process the correction. |
| “Um... because...” | Leave room for the user to finish. |
| “Stop talking” | Stop playback promptly through local control. |
| Quoted “stop”, laughter, echo, or ambiguous partial text | Use context and acoustic evidence; avoid unconditional cancellation. |

Keep explicit stop controls local. Use a short deadline, discard stale decisions by transcript/session revision, and preserve a deterministic fallback. One pending semantic check should not queue behind obsolete partial transcripts. Measure speech detection, transcript arrival, Jev response, playback stop, and next audible speech separately.

History should distinguish generated, queued, played, interrupted, and dropped assistant speech. Playback acknowledgements should commit only what the user could have heard, with any uncertainty retained. Background-tool results stay separate until delivered. This prevents a later response from assuming an interrupted explanation was fully heard.

The root agent's local inspection reports that `server.py` cancels TTS on each native user turn before semantic classification. The inspected native schema exposes no verified switch disabling automatic interruption; `clientManagedHandoffs` relates to tool delivery. A prompt cannot establish control over that mechanism. First probe whether native listening and generation can continue during backchannels. If not, use independent streaming STT, Jev turn arbitration, the Luna talker, and existing ElevenLabs playback; retain the background analyst.

## Acceptance checks before enabling

Replay labelled cases with acknowledgements, real interruptions, negation, quoted stop words, long pauses, corrections, laughter, speaker echo, ASR revisions, and consecutive interruptions. Compare premature stops, missed interruptions, response delays, resume coherence, and history accuracy against the present behavior. Test on the actual phone speaker/microphone. Typed outputs alone establish neither correct turn taking nor natural duplex conversation.
