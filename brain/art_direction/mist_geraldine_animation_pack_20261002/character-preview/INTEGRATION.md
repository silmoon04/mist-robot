# Geraldine adapter 1.0.0

Import `createGeraldineAdapter` from `adapter/geraldine-adapter.mjs`. Await `face.ready`, check that it is true, and drive `face.update(nowMs)` from a monotonic host render clock at least once per 15 fps frame. The adapter does not create an animation loop or audio source. The host owns both and must stop them on teardown.

## Speech and expressions

The implemented sampling seam is:

```javascript
const face = createGeraldineAdapter(canvas, {now: () => performance.now()});
if (!await face.ready) throw new Error(face.snapshot().error);
face.reset({epoch: currentEpoch});
face.setExpression('reassuring', {epoch: currentEpoch});
face.startSpeech({events, duration, clock, sample, epoch: currentEpoch});
// Host render loop: face.update(performance.now()).
// Host interruption: stop audio, face.stopSpeech(), then render the closure.
// New turn: face.reset({epoch: nextEpoch}).
// Disconnect: stop host audio/loop, face.destroy().
```

The inspected live `Playback` calls `startSpeech({events,duration,clock,sample})` and `stopSpeech()`. Clock/cue time is seconds; render time is milliseconds. A callback sample takes precedence over the event list. Samples preserve active, viseme, amount, source, time, epoch, sequence, and turn_id in the snapshot. A finite duration limits articulation. Inactive, rest, zero/invalid amount, missing or failed samples close the rendered speech mouth. Consult `contract/interface.md` for the finite-duration boundary and sampling details.

`setExpression(id)` sets persistent emotional intent. `setExpression(id,{durationMs})` adds a finite reaction and returns to the latest intent. Repeated requests do not restart the transition or extend the same reaction. `handleEvent({type:'state',state})` records conversational state separately, so a listening state or short delivery gap does not replace a concerned expression.

| Runtime name | Pack preset |
| --- | --- |
| neutral / alert | attentive |
| listening | quiet-listening |
| thinking | considering |
| happy | amused |
| sad | concerned |
| curious | friendly-curiosity |
| reassuring | reassuring |

All 13 native preset IDs also work. Unknown IDs return false and retain the previous intent. Ask a model to choose a face at a conversational beat and keep it through the sentence; do not request a new face for every word. `site/face-tool.json` in the selected pack is the existing named catalog.

## Cancellation

`stopSpeech()` retires the attached sampler generation while retaining intent. `reset({epoch})` also establishes a turn boundary and clears reactions. Lower tagged epochs cannot revive speech or expressions. Untagged calls are trusted current-caller input; the adapter cannot identify stale untagged work. The live host must keep its current turn arbitration and reject old callbacks before calling the adapter.

Cancellation becomes visible on the next host render. The preview explicitly renders after pause/reset, so a frozen audio clock cannot leave an open speech mouth waiting for another frame. Preview interruption recovery is a visual transition with its own bounded rendering period; it does not resume the canceled recording.

`destroy()` is irreversible and prevents later drawing, including completion of pending asset loading. It cannot stop audio owned by the host.

## Optional hooks and integration limits

`setGaze`, `clearGaze`, `setListeningSignal`, `setActivity`, `clearActivity`, `resetActivities`, and `previewActivity` return an explicit unsupported receipt. Reduced motion suppresses incidental idle blinks and gaze; native expression transitions and speech cels remain.

This is compatible with the inspected speech-sampling seam. It is not a full replacement for the live UI's activity catalog or state controller. Before integrating, the logic owner must map any remaining live expression names, decide how to handle unsupported hooks, keep the current audio/turn ownership, and test with the actual streamed audio clock. Better timed cues can enter through the sampler's identity-checked `replaceTimedCues` API without changing the renderer.

The local scenes are deterministic authored examples with synthetic recordings. The preview release is 1.0.1; the adapter interface remains 1.0.0. Scheduling tests, visual browser checks, human character preference, and live-device behavior are separate forms of evidence. Human style selection and live integration remain pending. No shared runtime file, production default, or public deployment was changed.

The direction files preserve the original authored proposal. After an interruption, the final preview cancels future state/expression/reaction commands while allowing context captions to continue. It retains the latest emotional intent in a listening state, superseding the earlier review-moment proposal to force quiet-listening. This keeps emotional policy separate from audio cancellation.
