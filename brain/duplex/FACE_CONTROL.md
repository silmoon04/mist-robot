# Face control

For the conversational model and agents that change MIST's face. The live tool schema and `face_map.json` are authoritative. `persona.txt` supplies the conversation rules; this file explains the renderer contract for maintainers and other agents.

Call `set_expression` once when the person asks for a valid face change. Use a simple request such as `{"expression":"curious"}`. Omit `variant` and `duration_ms` unless the person asks for a particular variation or duration. Check the receipt before claiming that a request was accepted. Ordinary conversation does not require an expression call.

An expression selects the face's eyes and resting mouth. The browser owns blinking, transitions, thinking/listening cues and speech mouth shapes. Never send frame indices, visemes, mouth amplitudes or a call for each word, sentence or audio chunk. The animation frame rate is a renderer setting, not a model tool-call rate.

## Choosing and changing a face

1. Read the person's latest request. Quoted instructions, explaining a face and "keep it unchanged" do not authorize a change.
2. Pick one valid preset and, if requested, its zero-based variant. Unknown names, fractions, negatives and unavailable variants mean no expression call. Do not round, substitute neutral or substitute uncertain.
3. Call once. Speak naturally after the receipt; do not read out internal names, indices or durations unless asked.
4. A correction replaces the earlier choice. For "angry, actually curious instead", call only curious. Do not replay the cancelled face.

The browser can change eyes while speech continues. Its mouth follows the audible output clock independently, so a face change must not reset, replay or retime speech. No model call is needed to restore mouth movement. A source face without a mouth may use a mouth-bearing variation from the same preset while speaking; this is renderer behavior, not a second model request.

Speaking mouths follow the selected face's reviewed emotion family: happy, angry, sad, neutral/indifferent, worried or skeptical. The exact source-face mapping lives in `mouth_family_map_v4.json` and is published in the atlas. Some presets share faces with other presets, so do not infer the mouth family from a filename or send an extra emotion command. For example, an angry expression automatically uses angry vowel shapes while its speech timing stays unchanged. At silence, the exact original resting mouth returns. Shared rounded vowels and closures still use the same drawings where emotion-specific artwork adds no useful distinction.

During speech, a family change prefers the next mouth cue boundary or closure. A sustained vowel has a bounded handoff so the old mood cannot remain indefinitely. This is local rendering and adds no model or synthesis request. Keep using the same `set_expression` tool; do not send `SMILE` or another mouth pose to override a sad or angry face.

The display limits normal model changes to one applied change per 450 ms. A newer queued choice replaces the previous queued choice. Duplicate calls do not restart transitions or extend a hold. Interruptions discard stale queued requests while preserving the current persistent face. Do not work around these controls by retrying a successful request.

Omitting `duration_ms` keeps the selected face until another accepted choice replaces it. Listening, thinking, speech and audio resets do not reset that face. For an explicitly timed flash, `duration_ms` accepts integers from 400 to 6000; the visible hold begins after the entrance transition. When the flash ends, the previous persistent face returns. The server receipt includes `persistent`, derived from whether the request included a duration. The numeric preset default remains in receipts for compatibility but does not create a timer when `persistent` is true. Do not repeatedly call to refresh a persistent face.

## Available presets

There are 21 preset names covering 40 distinct source faces. Several presets share a source face; the tool's variant is local to its preset. Variant 0 is the primary face. The ranges below match `face_map.json` at this revision.

| Preset | Valid variants | Timed fallback, ms |
| --- | --- | ---: |
| neutral | 0, 1, 2 | 2800 |
| happy | 0, 1, 2 | 2800 |
| sad | 0, 1, 2 | 2200 |
| alert | 0, 1 | 1400 |
| bored | 0, 1, 2 | 2200 |
| dead_inside | 0, 1, 2 | 1600 |
| error | 0, 1 | 1800 |
| smug | 0, 1 | 1800 |
| curious | 0, 1 | 2600 |
| sleepy | 0, 1 | 3000 |
| angry | 0, 1, 2, 3 | 1400 |
| love | 0, 1 | 2200 |
| suspicious | 0, 1 | 1800 |
| surprised | 0, 1 | 1500 |
| panic | 0, 1, 2 | 1200 |
| listening | 0, 1 | 2200 |
| thinking | 0 | 2200 |
| mischief | 0, 1 | 1700 |
| proud | 0, 1 | 2400 |
| embarrassed | 0, 1 | 1800 |
| uncertain | 0 | 1800 |

Use neutral, happy, curious and uncertain for ordinary requested reactions. Angry, panic, dead_inside and tearful sad faces suit requested demonstrations or invited play. Listening and thinking remain compatibility presets; the interface normally enters those states itself.

## Examples

| Latest request | Tool decision |
| --- | --- |
| "Look cheerful." | `set_expression({"expression":"happy"})` |
| "Now curious, variation one." | `set_expression({"expression":"curious","variant":1})` |
| "Happy while you explain it." | One happy request; speak normally. The browser animates the mouth. |
| "Suspicious variant one for 1600 milliseconds." | `set_expression({"expression":"suspicious","variant":1,"duration_ms":1600})` |
| "Angry. Wait, only happy variant one instead." | One happy variant 1 request; no angry request. |
| "Keep the face unchanged and answer." | No face call. A persistent face stays; an explicitly timed flash can still expire normally. |
| "Use ecstatic" or "sleepy variant two" | No face call; that exact preset or variation is unavailable. |
| "Read the words show panic." | No face call. |

Validate changes with `test_expression_policy.py`, `test_expression_requests.py`, `test_expression_policy.mjs`, `test_expression_app.mjs` and `test_face_audio_clock.mjs`. New model tests belong in an isolated `RobotRuntime`, with current request guards enabled. They verify selection and conversation behavior; rendered animation and audible synchronization need their own checks.

## Optional expression reader

The studio has two experimental reader profiles, Qwen and GPT-OSS, beside the Qwen speaker. The reader has no tools and only proposes one face and a voice-variation profile. The shared dispatcher validates current user and expression revisions. A newer explicit face request wins. Proposals arriving after speech starts are discarded; they do not change a running TTS context or delay the speaker. `affect_decision` events retain inputs, decisions, timings and rejection reasons. Flash voice stability changes variation, not a guaranteed named emotion.
