# Thinking study QA

Final animation, source-art, and speech integration checks pass on runtime `a2507a412b5c2e91620bedfcb6c2d2bddb39601e884d4320a14e992c6ad70601`, manifest `5506f3df35c90060c840496f31bfb295c283889494f72bc0898f948c03219efc`, and studio renderer `22084e744e8d11ed0484b273b8f82ee3af8c9e9e11070c6290a3e535f6d48ce3`.

One separate file-preservation guard remains red because the production renderer's container-positioning check changed after both approved baselines. The studio renderer subsequently received the same change. This does not change face art, animation, or audio, and the new bytes passed the source-art integration check. See `qa_external_edit.md` for the exact diff and provenance limits. QA has neither reverted this change nor replaced the recorded baseline.

## Final results

- All 88 cels pass source and manifest hash checks, transparency, nonempty content, and safety margins. The two reused props are byte-identical to the approved v6 assets. All six loop seams stay within the alpha-difference review threshold; there are no image warnings.
- The final contact sheet was visually inspected. The book opens and turns a page; the terminal changes short input lines; the note moves its pen and content; cards rearrange while keeping a coherent silhouette. No replacement eyes, mouths, or facial parts are present in the prop pack.
- All six studies pass notice/work/held consideration/resumption, continuous loop gaze, indefinite pending work, and explicit exit checks across 813 choreography samples.
- Eighteen speech starts and all six replacements during active speech keep a stable quiet action cel without stopping or quantizing audio.
- Original face integration passes 815 sampled states against the retained verified v5 renderer: 2,043 source paths and 459 original raster cel draws. All forty expressions, their blinks, and sampled transitions preserve source geometry. Props only move or uniformly scale the whole face.
- The original audio clock is unquantized at 120 Hz callbacks, while painting stays at 15 fps. Consonant lip closure and stopped audio update immediately.
- All 36 ordered study replacements reject a stale completion token.

Reports: `qa_choreography_report.json`, `qa_integration_report.json`, and `qa_assets_report.json`. The last report explicitly separates `assetValidationPassed: true` from `protectedFilesUnchanged: false` and retains an overall failure for the unchanged-file assertion.

## Earlier failure: activity changes during speech

This was reproduced on runtime `5c666f1431368793fd149cb947f98c9584ffc631ff429a8067619cc74dd665f6` and is fixed in the final runtime. `setActivity()` now selects quiet active cel 4 when speech is already active.

`setActivity()` resets `frozenCel` to null even when speech is already active. The next study dims its prop and quiets its gaze, but after entrance it resumes changing active cels throughout the speech. This conflicts with the same runtime's normal speech behavior, which holds the current action cel still.

Reproduce with `node brain/art_direction/artist_studio_20260916/reuse/thinking_v7/qa_choreography.cjs`. All six replacement cases fail: start a study, start speech, wait for quieting, then select another study while speech continues. The new study displays two to four loop cels instead of remaining on one quiet cel. Initialize a suitable active-loop cel when starting a study during speech, or freeze it when the new entrance settles.

The tests otherwise cover real active-cel changes, held consideration, indefinite pending work, explicit exits, continuous gaze across loop boundaries, and 18 speech starts during entrance/work/near-loop-end. No audio is stopped or quantized. The entrance-speech cel now correctly stays within the active range.

Browser feel and saved-recording playback are handled by the root reviewer. These independent tests use deterministic audio and recording canvas contexts; no microphone or paid provider call was made.
