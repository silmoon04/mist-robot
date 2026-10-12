Expression policy integration, 22 September 2026

Historical integration checkpoint. The later Luna testing pass changed the default backing and background models and added request checks. See [LUNA_REVIEW_20260922.md](LUNA_REVIEW_20260922.md) for the current configuration and final verification. The measurements below belong to this earlier checkpoint.

The expression-control agent owns static/expression_policy.js, expression_policy.py,
face_map.json, persona.txt, delivery.js, runtime.py, app.js, server.py, native.py and their
tests. It has not edited playback.js or either face renderer.

Implemented browser API, now wired into app.js:

    import {ExpressionPolicy} from './expression_policy.js';
    const policy = new ExpressionPolicy(map, {now: () => performance.now()});
    policy.request({expression: 'happy', variant: 0, duration_ms: 2200});
    policy.setState('thinking');
    policy.setState('listening');
    policy.setState('speaking');
    policy.interrupt();
    policy.snapshot();

snapshot returns expression, faceId, state, gaze, mouthMode, source and expiry.
State changes preserve an active expression. Mouth movement is controlled only by audible
playback. A barge-in clears the old expression and speech state immediately. Call snapshot
from the render loop or a 50 ms timer so expiry and cooldown queues resolve.

Face events should preserve optional variant and duration_ms from a successful tool result.
Ignore refused set_expression receipts. UI requests may pass {source: 'manual'} to bypass
the ordinary cooldown, but still have finite duration. Leave model requests as source model.

State is evaluated against player.sample().active, so early model state changes do not
replace speaking while output is audible. Model and manual expressions use finite holds.
Repeated calls do not restart a transition or extend its hold. Conflicting rapid calls
coalesce for 450 ms. A queue left behind for over 1200 ms is discarded.

NativeVoice captures an expression revision at backing-turn start. It rejects an expression
call if that revision is no longer current. Conversation.emit also rejects obsolete or
refused receipts. Face events carry the PCM epoch; the browser rejects a face event that
does not match the player epoch after a local stop. Explicit and natural interruptions
invalidate the revision before the old tool can finish.

All 40 source faces are named in face_map.json. 18_misc_2_02 was missing from the old map;
it is now the uncertain preset. Source faces 12 and 35 have no mouth. While audio is audible,
the policy temporarily selects a mouth-bearing variation of the same emotion. It restores
the requested face when quiet if the hold is still active. This keeps the original drawings.

Checks passed 38,327 assertions across 14 deterministic scenarios, 1560 directed face
selections and 10,000 mixed events. They test selection and state, not visual quality.
Eight Python tests cover the tool boundary and native/server integration. In the interruption
test a barge-in occurs during tool dispatch: the old call and a later old-turn call are both
refused, and the new-turn call reaches the browser with its variation, duration and epoch.
The app-handler test uses the real Playback class with a controlled output clock. It passes
queued versus audible speech, thinking/listening messages during speech, mouthless fallback
and restoration, stale epochs, invalid faces, finite expiry and disconnect. The existing
33 duplex tests and delivery tests pass too.

Actual gpt-6-luna, low/default probes ran with only a validating set_expression stub.
The production voice model was not changed. The first 16-case run passed 15 cases.
The 37-case follow-up passed all 21 explicit preset selections plus 15 conversation cases.
The final 19-case run passed 18. Prompt and tool-description changes fixed the original
invalid-name case, and the model rejected invalid variation 999 and a compound invented
name. One new request for an unavailable ecstatic preset was still interpreted as a related
valid expression. That semantic substitution is a remaining model-quality failure; the
validator cannot reject it because the substituted call itself is valid. All failures are
preserved. Do not claim perfect instruction following or that these tests prove speech quality.

Reports are in brain/results/expression_probe_20260922,
brain/results/expression_probe_20260922_refined and brain/results/expression_probe_20260922_final.
The final median first tool call was about 1.81 seconds, excluding model startup. No voice
generation or hardware calls were made by these probes.

Files are stable for the parent to restart and review the voice app. Run:

    node brain/harness/test_expression_policy.mjs
    node brain/harness/test_expression_app.mjs
    python brain/harness/test_expression_policy.py

The production native model default remains gpt-5.3-codex-spark. It was absent from the local
models_cache.json examined for the probe; gpt-6-luna was present. No production setting was
changed. The parent should account for that existing model-availability issue when starting
a fresh native session.
