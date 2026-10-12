# Scene direction

These three scenes are authored simulations for character review. All user and context captions are labelled synthetic. Assistant captions resolve `audio.textRef` by `audio.clipId` against `../../site/speech-clips.json`; preserve that field verbatim, including its spacing. In the interrupted scene the caption is the full source recording transcript, not a claim that every word was heard. Label it accordingly.

The restrained profile is a provisional starting point. The user still chooses how warm, dry or expressive MIST should feel. These fixtures do not record approval or change the live default.

## Runner contract

`atMs` and `durationMs` use scene milliseconds. Process events in array order, including ties. Audio begins at `audio.startMs`. `textRef` is a reference descriptor, not an expression to evaluate. Resolve clip IDs explicitly. Assistant text comes only from the referenced recording; no new speech is authored here.

Scene playback and user pause share a scene clock. User pause freezes scene and audio clocks. Each packet gap pauses audio at `atClipMs`, holds that audible position for `durationMs` of scene time, then resumes. Subsequent clip positions subtract all completed gap durations. Do not seek past, mute over or splice out the gap. Patience pauses at 1100 ms, inside its existing 1060 to 1300 ms rest cue interval. This models a delivery gap; it does not reproduce a captured network incident.

`state` records turn activity: listening, thinking or speaking. The waiting beats use thinking with a synthetic context caption. `intent` selects the persistent face for a conversational beat. `reaction` temporarily selects a face for the duration named in the active timing profile, then returns to the current intent. A newer intent or interruption supersedes the old reaction return. Neither silence nor the packet gap changes intent. In patience, reassuring remains selected across 5100 to 6000 ms, while speech returns rest.

`interrupt` stops native playback immediately and cancels pending speech and reaction returns for that scene epoch. It reaches quiet-listening through the existing 400 ms preset transition; the mouth closes by the next rendered frame. The authored scene continues only its synthetic listening context. A manual interruption must prevent future authored events from reviving canceled speech or emotional reactions. Scene replay creates a fresh epoch; stale callbacks cannot act in it.

## Performance notes

Use the same native atlases, audio, cue data, scene times and preset sequence for both profiles. Only the finite reaction holds differ. The 600/1000 ms wry reaction precedes the second-attempt recording. The 400/800 ms pleased acknowledgement follows the hinge answer and the recovered patience answer. This comparison isolates hold timing without changing the answer or staging a different emotional reading. `review-moments.json` holds the reasons and candidate palette for QA; keep that detail behind the inspector.

Use pack idle eye mode throughout, even during a finite reaction. Its deterministic blinks and closed-eye family changes give the eyes enough activity. Do not use the repeating 1800 ms reaction tour: it moves through every look cel and makes a brief conversational response feel performed. A gaze shift, if selected by the existing idle scheduler, must use the native look-left/look-right/settle cells. Keep the registered shapes intact; no rotation, stretching or generated outlines.

Hinge considers once, then holds attentive through the whole answer. Second attempt offers a brief wry look, returns to listening intent, then speaks reassuringly. The interruption makes listening the new intent. Patience acknowledges the problem with concerned, keeps it through the deliberate wait, and changes to reassuring when the synthetic user reports progress. There are no expression changes tied to individual words.

## Review limits and edge cases

The first two recordings use recovered provider word bounds with estimated phoneme timing. Patience uses measured audio energy and generic open shapes. Keep those source labels in the inspector. Scene checks establish timing consistency, not acoustic alignment quality or a listening score.

QA should inspect a reaction return during a newer intent, replay during a pending return, interruption during a packet gap, user pause during that gap, repeated interruption, and a manual interruption before scheduled audio starts. The last case must cancel that future start. Compare the exact same clip and gap offsets across profiles. Check the full-recording transcript label after interruption so unheard words are not presented as completed speech.

Run `node brain/art_direction/mist_geraldine_animation_pack_20261002/character-preview/direction/validate.mjs` from the project root for fixture checks.
