# Hand-drawn activity API

The phone keeps all 40 original MIST expressions, including their original eye shapes, corrected blink frames and transitions. Speaking uses the existing emotion-specific mouth frames and playback clock. An activity adds a symbol and uniformly moves or scales the whole face to make room. It does not redraw eyes, start a tool or grant access to an account. The five generated eye studies are inactive and are not loaded by the runtime.

```js
const face = MistHanddrawnRuntime.create(element, {
  data: MIST_DATA,
  atlasUrl: '/drawn/atlas.json',
  manifestUrl: '/studio/handdrawn_v6/manifest.json'
});
await face.ready;

const activity = face.setActivity('reading', {owner: 'read:42'});
try {
  await readFiles();
} finally {
  face.clearActivity(activity.token);
}
```

`setActivity` returns `{accepted, token, id}`. Keep the token. A delayed completion for an old operation cannot clear a newer activity. Unknown IDs return `accepted: false` without replacing the current activity. Repeating the same ID and owner does not replay its entrance; pass `restart: true` for a deliberate replay.

`clearActivity(token)` plays the exit. `clearActivity(token, {immediate: true})` removes the symbol immediately. `resetActivities()` clears all event ownership on disconnect. The symbol loops until a matching completion or cancellation. Its timing never implies success.

| ID | Use while |
| --- | --- |
| `coding` | Editing or executing code |
| `reading` | Reading files or retrieved content |
| `writing` | Composing text or saving a note |
| `email` | An actual mail operation is running |
| `searching` | A search request is running |
| `planning` | Reasoning or planning |
| `calculating` | Performing a calculation |
| `connecting` | Opening a transport connection |
| `checking` | Inspecting reported results or sensor values |

The live page exposes the same activity controls as `window.MistActivity.setActivity`, `clearActivity` and `snapshot`. It does not accept activity requests from arbitrary cross-origin messages.

## Current automatic events

The existing voice WebSocket sends `debug_tool` start and finish events from `NativeVoice`, and `brain_job` status events from the background worker. The page forwards them to `face.handleEvent(event)`.

- Conversation `thinking` selects planning; `checking` selects checking.
- Background `brain_job` with status `running` selects planning; its completion, failure or cancellation clears that job's activity.
- `debug_tool` maps `get_sensor_snapshot` to checking, `recall` to reading, and `remember` to writing. Start and finish are matched by `call_id`.
- Opening the voice WebSocket selects connecting. The actual ready event, connection error or disconnect ends it.
- A tool can temporarily replace a background activity. When it finishes, a still-running background activity resumes. Stale completions do not erase newer work.

Email, code execution, search and calculation are available visual activities for future tool adapters. This change does not add those tools. Use their explicit activity IDs only when the corresponding operation really runs. No ticks or joined connection states are generated from elapsed time.

## Playback and inspection

Activity artwork is held at 15 fps. Four entrance drawings lead into a four-drawing loop; four exit drawings fade out. The individual drawings have deliberate holds, so they do not all flash at 15 changes per second. The original MIST renderer owns all eye shapes, blinks, gaze and face transitions. The entire face uses one uniform scale and translation while an activity needs space; eyes and mouth keep their original relationship.

Use `face.startSpeech(settings)` and `stopSpeech()` through the existing `Playback` adapter. Do not drive the mouth from text arrival, animation ticks or activity state. These calls still use the original audio output clock and emotion-specific mouth selection.

`inspect({activityFrame: 4, layers: 'activity'})` holds an activity cel. Layers are `all`, `eyes`, `mouth` or `activity`. Call `inspect({})` to follow animation again. Use the linked original expression inspector for individual blink cels. `snapshot().handdrawn` reports original eye-slot identities, the whole-face transform, and the activity file, frame, phase, token and owner. It reports visual state, not tool results.

The inspector's saved voice recordings exercise the existing audio-energy mouth timing. They are not new synthesized voice calls or measured phoneme alignment.

If the manifest, an activity cel or the original mouth atlas fails to load, the original renderer remains available. `face.ready` returns false and `face.error` reports the problem. Only the nine activity assets are required or downloaded; the inactive eye studies cannot replace a face.
