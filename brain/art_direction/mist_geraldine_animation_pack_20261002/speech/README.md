# Speech cues

The portable demo contains three existing synthetic MIST (refined) recordings.
The WAV files are copied byte for byte. Two clips use saved provider caption
onsets to bound words, then estimate pronunciation shapes within those bounds.
The patience clip follows audio energy because its original timing events were
not saved. No new synthesis calls were made.

`site/speech-clips.json` supplies each clip's text, native audio path, duration,
and `cues` with `time`, `viseme`, and `amount`. Use the audio element's playback
time to select the latest cue. Close the mouth when playback pauses or ends.

## Optional runtime use

`brain/duplex/phoneme_cues.py` is an opt-in layer. The live TTS import and runtime
configuration are unchanged. A caller can use it where the existing TTS code
already produces cues, after removing delivery tags and converting provider
timestamps to the reply clock:

```python
from duplex.phoneme_cues import phoneme_mouth_cues

cues, alignment_source = phoneme_mouth_cues(
    raw,
    aligned_message,
    audio_offset=audio_offset,
)
```

Keep the existing `duplex.lipsync.slice_cues` packet slicing and the existing
browser playback clock. This helper processes the current PCM chunk immediately
and has no utterance buffer, network call, or async wait. Supply `final=True`
only when an unterminated last word is known to be complete. A leading fragment
at a nonzero audio offset also keeps character cues unless its boundary is
present or the caller explicitly supplies `leading_word_complete=True`.

The bundled vocabulary has 319 English words and their original CMU dictionary
variants. Unknown words and missing dictionary data keep the existing character
shapes. Invalid or missing provider alignment uses energy cues. The default
pronunciation is the first dictionary entry; it does not infer sentence meaning.
For example, `read` defaults to the past-tense pronunciation. Select a known
reading with `overrides={"read": "R IY1 D"}`, or supply a complete CMU-style
dictionary through `pronunciations`. Different accents can need overrides.

Phones choose shapes, including the initial `FV` in `phone`, final `FV` in
`enough`, and silent letters in `knight`. Vowel and consonant duration weights
estimate positions within measured word bounds. Those positions are **not
measured phoneme timestamps**. A 20 ms PCM RMS window controls whether a shape
opens; written spaces and punctuation do not establish acoustic silence.

## Recording evidence and limits

The hinge and second-attempt WAVs come from the fixed typed-input live harness
in `brain/results/dual-model-harness-20260924/live-smoke/`.
Their native PCM hashes match the original probe summary. The recorded session
names the MIST refined voice ID, `24AMj4dc02cYAwoUnqzN`, and Flash model. The
harness prompts are synthetic constants and bypass microphone capture.

The saved `caption_cues` contain actual provider-aligned prefix growth onsets.
The first letter's onset and following separator's onset bound a complete word.
Original character duration arrays were not retained. Newly observed characters
at a packet's zero-time boundary can have a clipped onset. The builder marks
those onsets and excludes that word spelling from dictionary upgrades in the
clip. It never fills missing words from the authored reply or repaired captions.

Base64 payload padding was redacted in the archive. The known native PCM byte
count bounds the remaining packet-offset uncertainty to 83.333 microseconds for
the hinge clip and 41.667 microseconds for the second-attempt clip. Caption cue
rounding contributes another half microsecond. The demo uses interval midpoints
and records both bounds in `recovered-caption-onsets.json`. Reconstructed word
bounds and estimated positions inside words are explicitly labeled in the site
manifest.

The patience WAV comes from the fixed-text voice-quality benchmark in
`brain/results/brain-quality-20260929/voice-after/`. Its metadata confirms the
same MIST voice, successful synthesis, and full aggregate character-alignment
coverage. That benchmark discarded the character and cue events, so the demo
uses `audio_energy`, a generic `AA` shape, and measured silence. The coverage
count does not recreate timing.

The evidence supports native audio identity, finite ordered cues, dictionary
lookup, silence gating, and provider timing provenance. It does not establish a
human listening score or perceptual lip-sync quality.

## Rebuild and check

Run from the repository root:

```powershell
python brain/harness/test_geraldine_phoneme_cues.py
python brain/art_direction/mist_geraldine_animation_pack_20261002/speech/build_speech_clips.py
```

The builder copies the three native WAVs, reconstructs bounded provider onsets,
runs the focused tests, measures local 100 ms chunk processing, and writes
`qa/speech-cues.json`. It requires the existing local source recordings. The
portable site itself only needs the bundled WAVs and `speech-clips.json`.

The CMU subset can be rebuilt with `vendor_cmudict_subset.py`. It fetches only
the pinned official data and license. `cmudict-subset.json` records commit
`74790861f652b15e4ac49015a90074ad62a27690`, the full source dictionary hash, and
the selected vocabulary. `CMUDICT-LICENSE.txt` preserves the CMU data license.
There is no new Python package dependency.

Sources: [CMU dictionary data and license](https://github.com/cmusphinx/cmudict/tree/74790861f652b15e4ac49015a90074ad62a27690),
[ElevenLabs character timing](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps),
and [ElevenLabs forced-alignment response](https://elevenlabs.io/docs/api-reference/forced-alignment/create).
The implementation uses the existing recording events and does not call forced
alignment.
