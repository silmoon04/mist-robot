# Gallery checks

Checked the local v3 gallery at `http://127.0.0.1:9047/mist_motion_v3/` on 29 September 2026. Reloaded after the final cropped layer manifest was written. These checks cover the controls and layout; they do not replace the separate motion review.

## Automated checks

`node --test brain/art_direction/artist_studio_20260916/reuse/mist_motion_v3/test_gallery.cjs`

12 checks pass. The harness drives the actual gallery event handlers, with the real runtime clocks and a small DOM/canvas test double:

- Existing review IDs, selection and notes restore from the unchanged storage key.
- Scrubbing and resuming use cumulative authored pose durations.
- Actual and half-speed playback preserve pose position and independent mouth selection.
- Separate blinks play once, support scrubbing and layer isolation, and return to the chosen action pose.
- Grid blinks occur only in neutral rests, on alternating cycles with per-card offsets.
- Pause and the Blinks toggle stop grid blinks. A slowed blink is omitted when it cannot fit completely inside a rest.
- Reduced-motion preference pauses initial playback; explicit Play works.
- Missing frame durations produce a visible load failure.
- Speed changes retain position inside the unscaled rest.
- Transition scrubbing reaches exact source and target endpoints.
- Download and history links name the corrected pack and retained v2 page.

## Browser checks

- All 18 cards loaded and animated. Pause stopped the grid; inspector opened correctly.
- Pose 7 displayed its 400 ms authored hold, then 800 ms at half speed.
- Independent mouth scrub advanced from pose 7 to 8 without changing the selected eye pose.
- Blink once reached `Blink finished`; blink scrub selected frame 4 of 7. Right-eye isolation worked.
- Review selection changed the count to 1 and Selected only showed one card. The temporary selection was removed; the count returned to 0. No test notes were saved.
- Transition from Attentive listening to Quiet pride reached step 12 of 12; scrub returned to step 1.
- Turning grid blinks off immediately removed blink readouts.
- Desktop had no horizontal overflow.
- At 390 × 844, the grid used two columns without horizontal overflow. Inspector scroll width equalled its client width; controls stayed inside the dialog. The temporary viewport override was reset.
- A later inspection found that scrolling to mouth/blink controls could hide the face. The final inspector now uses two columns on desktop, with a sticky 384 × 240 preview on the left and controls on the right. At 390 × 844 it uses a proportional sticky preview above the controls. Rechecked Blink scrub, Mouth scrub and Next pose: the face stayed visible without covering the active control. The final `gallery-inspector.png` and `gallery-mobile-inspector.png` show this layout.

The first load happened while layer crops were being rewritten and correctly failed on mismatched image dimensions. After the files stabilized and content-hash asset requests were added, both reloads loaded successfully. No new console errors appeared during the completed checks.

Screenshots: `gallery-desktop.png`, `gallery-inspector.png`, `gallery-mobile.png`, `gallery-mobile-inspector.png`.

Temporary QA tabs were closed, the viewport override was reset, and temporary review selection was removed. No test notes were created.

The public ZIP/history navigation and downloaded previews still need the deployment check; the local source server does not serve the public parent routes.
