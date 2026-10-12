# Thinking animation references

Reviewed 2026-09-24. These notes separate visible observations from proposed MIST behavior. Existing MIST eye shapes should stay intact.

## What I actually inspected

- [EMO reading, starting at 10:03](https://www.youtube.com/watch?v=5wh3EEZZzUE&t=603s): sampled browser frames show a blue newspaper occupying the lower half of the face, with both eyes still visible above it. The eyes are low, broad lids rather than a talking mouth. The prop and face form one little scene. I did not capture a complete page turn or measure its cycle duration.
- [EMO working, starting at 17:05](https://www.youtube.com/watch?v=5wh3EEZZzUE&t=1025s): sampled frames show a keyboard below the eyes and small outlined hands on its upper edge. Across the inspected interval, the eyes change from tall rounded shapes to narrow, slightly inward-sloped lids. The keyboard stays legible while the face changes. Playback was paused at 18:18. This was frame sampling, not a frame-by-frame timing audit.
- [Lordicon animation documentation](https://lordicon.com/docs/animation): the visible Loop example is an outlined speech bubble whose three interior dots change size while the bubble stays still. Two screenshots captured different dot phases. This is a useful example of motion happening inside a stable silhouette. The page describes separate entrance, interaction, morph, and loop behaviors. Interaction motion starts quickly and slows; a repeated interaction may include a delay. Several lower video examples reported that media could not play, so they were not visually assessed.

No reference assets were downloaded or copied into the project. The suggestions below are original staging proposals, not claims about exact source timings.

## Six directions for MIST

| Direction | Entrance and motion | Suggested timing at 15 fps |
| --- | --- | --- |
| Reading | MIST glances down before a short stack of pages rises below the face. A line marker scans two rows, pauses, and returns. An occasional page flip changes the rhythm. Keep the original mouth visible or move the prop aside when speech starts. | 6-frame entrance; 45-frame loop; 12-frame quiet hold inside the loop. |
| Coding | A small terminal arrives below the face. A cursor types a short burst, pauses, then starts a second line. Let the eyes glance toward the active line rather than squashing them into an angry face. | 6-frame entrance; 36-frame loop with two unequal typing bursts and an 8-frame pause. |
| Writing | A pencil follows the end of a growing line, lifts, and returns to a second line. The paper stays still. MIST briefly looks up between lines. | 8-frame entrance; 45-frame loop; 6-frame pencil-lift pause. |
| Searching | A magnifier moves across three small document rows, stops to inspect one, then changes direction. The eyes anticipate the movement by one or two frames. Do not rotate or bounce the entire face. | 7-frame entrance; 48-frame loop with two 7-frame inspection holds. |
| Planning | Three small cards appear one at a time. A dot tries a route between them, pauses, then takes a different route. Eyes alternate between the two candidate paths. A final resolved route should require an actual completion event. | 8-frame entrance; 54-frame loop with a 10-frame comparison pause. |
| Waiting for a connection | Two stable endpoints and a short travelling pulse indicate that something is pending. MIST gives one small side glance, then settles. Keep the loop calm for long waits. Join the endpoints only when the connection succeeds. | 6-frame entrance; 45-frame loop; lower motion after several cycles. |

## Shared staging rules

- Use the face and activity prop as one scene: eyes notice the prop before it moves, then return their attention to the user.
- Give each activity an entrance, a repeatable action, and a short exit. A task change should not replay a large introduction on every tool event.
- Move one focal element at a time. A stationary outline with a moving cursor, dot, page marker, or pencil is easier to read than several icons bobbing together.
- Holds are intentional. A short action followed by a pause will usually feel more thoughtful than a perfectly regular busy loop.
- Keep speaking and listening available. Activity motion must not replace voice-driven mouth shapes or obscure the eyes.
- Success ticks, sent envelopes, resolved paths, and connected plugs belong to verified result events. Their presence in a thinking loop would imply a result that has not happened.
- All frame counts above are proposed preview settings, not measured source timing or proof of naturalness. Review them in motion on the phone before choosing final values.
