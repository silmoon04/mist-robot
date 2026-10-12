# Motion guide and drawing reuse

Use a 24 fps authoring timeline for the initial review clips. The browser can render at 60 fps. These are different things: displaying 60 frames per second does not require 60 hand drawings per second. Most frames hold a drawing or move it slightly in code.

Separate eye_L, eye_R and mouth, with optional accents on their own layer. Eyes carry the emotion while the speech mouth comes and goes. Do not animate every expression-to-expression pair. Twelve layouts have 132 directed pairs; three reusable transition recipes cover most of them.

## Blink: six timeline frames, two extra drawings per family

At 24 fps, show OPEN, HALF, CLOSED, CLOSED, HALF, OPEN, one frame each: 250 ms total. OPEN is an existing base eye pair; HALF and CLOSED are the two new blink drawings. Reuse HALF on the return initially. If the return feels mechanical in the pilot, scope a separate reopening breakdown later; it is not included in the 38 drawings.

Families: E01/E02/E08/E09 start with open-family B01/B02; E03/E10 with happy-family B03/B04; E04/E07 with focused-family B05/B06; E05/E06 with downcast-family B07/B08. These groupings require the artist's visual check. If a family does not preserve a pose's silhouette, add a specific blink pair explicitly rather than silently expanding the brief.

Schedule a blink after roughly 3 to 6 seconds of idle time as a starting range; do not loop it every quarter second. Sleepy can hold CLOSED longer using the same drawing. A rare double blink replays the same clip with a short open hold, adding no new drawings. Keep the mouth independent. Consider a one-authoring-frame stagger between eyes for an occasional asymmetric blink, not for every blink.

## Three transition recipes

T01 Same-family change: about 6 timeline frames, 250 ms. Ease the position, tilt and width from source to destination. Use vector interpolation only when path structure is compatible. For painted/raster assets, move/deform a rig or choose a deliberate drawing swap; do not assume automatic path morphing exists. No new hand drawings in the initial budget.

T02 Blink bridge: eight frames, about 333 ms. Frames 0-1 show the source; frame 2 source HALF; frames 3-4 source CLOSED; frame 5 destination HALF; frames 6-7 destination. Swap the open contours while lids are shut. Family closure silhouettes need to be compatible at the cut. Cross to the destination mouth through its closed/rest shape rather than dissolving two complete mouths. Reuses blink drawings.

T03 Accent then settle: eight frames, about 333 ms. Frames 0-1 use the anticipation eye pair; frames 2-3 use the overshoot; frames 4-7 hold the final expression. Neutral-to-surprise can use A01, A02, then E08. Happy, thoughtful and sleepy accents can use A03, A04 or A06 followed by their base. A05 gives a playful asymmetrical beat. Keep accents brief and triggered by meaning, not by every response.

## State behavior

Available: F01. One subtle gaze shift or tiny scale/breath change over several seconds. A still pose is a valid idle state. Closed M01. Do not cycle emotions just to show the app is alive.

Listening: F02. Change promptly when user speech is detected; use a small gaze settle. The mouth remains closed. Avoid constant nodding or interruption-like movements during a long explanation.

Thinking: F03. Hold E04 + M01; look slightly upward and to one side. After a delay, one short A04 squint is enough. Reuse the same components for a slow 2 to 4 second gaze shift if a wait is long. Do not use the round speech mouth as a waiting indicator. Thinking while MIST is still talking should not erase its current speech pose.

Speaking: keep the current eye expression and switch ONLY the mouth as audio actually plays. M06 AA and M01 rest are sufficient for the present amplitude-based path. M05 lips together, M07 wide and M08 round are prepared for a later timing/viseme mapping pass. Do not promise lip-sync from eight drawings alone: phoneme timing must be generated and connected in code. M02/M03/M04 return as emotional rest mouths after speech.

Interrupted: cancel queued mouth movement with the audio. Settle to the current closed mouth within about 100 to 150 ms, then listening eyes. Do not replay an old blink or reopen a cancelled talking mouth. Thinking/work completion waits for the current conversational state; it should not override a person who is still speaking.

Error: use F06 or F07 plus clear status text. Do not rely on an angry face to explain an error. On disconnect, stop speaking animation and hold a calm resting face.

Reduced motion: static selected face, no contour cycling or gaze/breath loop. Keep necessary speaking/rest changes, without exaggerated bounces. An explicit preview can still show the animations for review.

## Subtle line variation

R01/R02 redraw E01, R03/R04 redraw E03, R05/R06 redraw E04. Together with each base, that makes three contour versions for each of those poses. Try a short A-B-A-C passage at 6 to 8 drawing changes per second during an accent, then settle. Avoid a perpetual rapid three-frame loop. The timing and redraw choice need a runtime extension; this is not present production behavior.

## Review clips to assemble, not draw from scratch

| Clip | Timeline duration | Use |
| --- | --- | --- |
| idle_available | 96 frames / 4 s | Neutral, one gaze shift, one blink |
| listening_hold | 72 frames / 3 s | Listening without talking |
| thinking_hold | 96 frames / 4 s | Closed mouth, offset gaze, one squint |
| blink_four_families | 4 x 6 frames / 1 s combined | Show each family separately |
| neutral_to_thinking | 8 frames / 0.333 s | Blink bridge |
| neutral_to_happy | 8 frames / 0.333 s | Small happy accent |
| neutral_to_surprise | 8 frames / 0.333 s | Anticipate, overshoot, settle |
| happy_to_concerned | 8 frames / 0.333 s | A difficult eye/mouth change |
| speech_neutral, speech_happy, speech_concerned | 72 frames / 3 s each | Same mouth sequence over three eye poses |
| speech_interrupt | 24 frames / 1 s | Talking ends, mouth closes, listening wins |

Those review clips contain 560 timeline exposures altogether if all are supplied. That does NOT mean 560 new drawings: they reuse the 38 components, held frames and transforms. The authored timing is a starting proposal; runtime events ultimately decide when listening, speaking or interruption occurs.
