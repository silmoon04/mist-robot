# Geraldine conversation preview

The local preview has three short scenes using the selected MIST drawings and the three existing synthetic recordings. Choose restrained or expressive timing, interrupt a response, or pause to inspect a cel. Open **Review a moment** to save Keep / Revise notes and export them as JSON.

From the spider-robot project directory:

```powershell
python brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/serve.py --port 9064
```

Open <http://127.0.0.1:9064/>. Ctrl+C stops this preview server. The page needs no model backend, microphone, account, or external assets. It starts silent; Play starts the bundled recording. Space pauses/resumes and I interrupts when focus is outside a form control.

The portable ZIP keeps `character-preview/` beside `site/`. After extracting it, use:

```powershell
python character-preview/serve.py --port 9064
```

## Faces and drawings

There are 13 named expression presets: attentive, considering, skeptical, amused, concerned, quiet-listening, friendly-curiosity, wry-teasing, reassuring, quietly-pleased, laughing, doubtful, and eager-delight. They reuse six eye families and three mouth families, each with 12 registered drawings. That is 108 component cels, rather than 13 separately redrawn speech systems.

Playback uses 15 frames per second. Family changes use the original 400 ms closed-eye transition. Speech uses the mouth family assigned to the expression; a concerned or dry expression retains that family while talking. The adapter closes the speech mouth during silence and cancellation, including presets with an open idle mouth.

The recordings are unchanged. Two have provider word bounds with estimated pronunciation timing inside each word. The third uses audio energy and a simple open/rest target. These fixtures support timing and interruption review; they do not establish measured phoneme alignment or perfect lip sync.

## Review

Watch the ordinary answer, try interrupting the dry reaction, then watch the reassuring scene through its inserted delivery gap. Compare the two timing profiles. Use Keep / Revise at a particular moment and write what felt wrong or right. Notes stay in this browser and can be exported; export them before clearing browser storage.

The inspector shows scene time, audible clip time, sampled mouth target, rendered cel, source/provenance, and interruption events. The complete recording transcript is labelled as such when playback is interrupted; it is not a claim that every displayed word was heard.

`INTEGRATION.md` describes the adapter and the remaining live-runtime work. `ACCEPTANCE.md` summarizes the results; `qa/` contains deterministic checks and browser observations, with their limits stated separately. `input-verification.json` compares local source bytes with the saved checkpoint. The published site and live robot defaults are unchanged by this preview.

## Checks

These commands run from the spider-robot project directory and need Node.js for the JavaScript checks:

```powershell
python brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/check_inputs.py
node brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/adapter/check.mjs
node brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/qa/acceptance.mjs
node brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/qa/scene-acceptance.mjs
node brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/speech-review/test-render-timeline.mjs
node --test brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/preview/transport.test.mjs brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/preview/playback.test.mjs
```

The source check also verifies the inspected shared runtime files, so run it from the original project. Portable release hashes are recorded in `release-manifest.json`.
