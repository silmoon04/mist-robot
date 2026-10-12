# Animation refinement

User request: replace the FV, LNT and TH mouth shapes with clean drawings, smooth transitions between all 40 faces, use 15 fps, and verify that the model can select and change faces correctly.

Acceptance checks:

- Both neutral and smile families receive new FV, LNT and TH artwork. No inward notch, tongue-like tab, teeth or detached interior feature. Preserve the other mouth drawings and exact original resting faces.
- New source PNG bytes remain unchanged. The atlas records source files, crop bounds, registration and a consistent scale. Rebuilding the atlas must retain the replacement selection.
- Current production and inspector animations use a 15 fps drawing cadence, with 1/15-second stepping. Audio continues on its own playback clock. Do not accelerate the blink by treating every key pose as one frame.
- Face changes preserve one visible eye per side and one mouth. Switching during an existing transition starts from the visible pose. All directed face pairs retain exact endpoints, stable registration and bounded geometry.
- Speaking mouths sample current audible playback. Pause, silence and interruption cannot leave a free-running mouth or revive old cues. Provider-aligned live audio remains unavailable while ElevenLabs reports its existing payment issue.
- A small model-facing face API exposes names, variants and holds. Models choose expressions; they do not schedule mouth frames or send a call for every animation tick. Verify actual Luna calls through the guarded runtime with held-out inputs.
- Independent tests cover transition geometry, 15 fps phase sampling, replacement source integrity and source-face identity. Inspect the browser at normal size and slowed playback before packaging.

The final report will separate generated poses, rendering checks, real model calls and saved-audio review. None alone establishes perfect animation quality or fresh live voice synchronization.
