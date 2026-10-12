# Blink direction correction

Reviewed 23 September 2026. Final renderer: `9ade474f61fc9a6f3eee260b6bb07ef4adc2a4e6f56cae3a4871acbc531563ff`.

The reported rotation was reproduced on face 09. Its closed lids measured +33.36 and -32.05 degrees, despite nearly level source drawings and face placement. The fit that positions the gap in an open circular eye was also rotating its closed lid. The minimized baseline command is `node brain/harness/test_blink_orientation.cjs --face=09`; the baseline report is retained with the old source hash.

The renderer now separates open-eye geometry from the closing direction. Round eyes close near their shared eye line. Hook and loop eyes use restrained slopes from their original lids. Already-closed arcs retain their curve through a small squeeze. The same direction is used in the closed portion of expression transitions.

Early stroke phases trim the original contour at the eyelid line and keep rounded ends. The visible contour is not rotated to close it. Round eyes retain their main connected curve, avoiding tiny detached fragments near the gap. Narrow and closed phases use the existing drawn cels, with compensation for the angle already present in the source image. Source PNGs, all canonical resting faces, the emotion mouth map and the 15 fps atlas are unchanged.

## Review and corrections

Browser inspection covered round face 09, angry face 02, sad hooks on 31, loop eyes on 27, the already-closed arcs on 35, and the 35-to-09 transition. Two intermediate candidates were rejected: the first rectangular mask cut the lower curve flat; the next left a tiny isolated fragment during reopening. The final emitted paths resolve both, with rounded ends. The final reopening frame was inspected at 8/9 of the 600 ms transition. The browser reported no rendering errors during that review.

Independent checks also found a small reflection error on face 24. Symmetric sampling of the original upper contour corrected it.

## Verification

The owner suite passes all 80 closing directions, 616 held poses, 26 preserved contours, four emitted-path regressions for the round-eye fragments and two actual-draw reflection checks for face 24. The maximum difference from the reviewed direction targets is 0.693 degrees. These targets are visual acceptance choices, not anatomical measurements.

The renderer suite passes 1,600 expression pairs, 20,920 sampled states and 120 rapid retargets. The timing suite preserves 15 actual paints per second, immediate speech closures and the current audio clock. The mouth-family suite retains all 40 mappings and its bounded handoff behavior.

Independent identity checks preserve all 40 faces, 80 eyes, 120 canonical canvas paths and 1,560 directed transition endpoints. Independent orientation checks measure all 80 visible closed lids, including 54 raster lids and 26 preserved vector contours. The targeted round, angry and already-closed arc checks pass.

The final independent motion suite passes 110 closing/reopening contour checks, 80 mirrored-eye checks and 240 transition-bridge checks, including the reported 35-to-09 reopening frame. Its full regression run covers 1,560 directed transitions, 87,680 sampled states, 4,680 speaking-pair cases, 320 interruptions and 14 cancellation cases. Silent and speaking playback paint at 15 fps under both 60 Hz and 120 Hz callbacks. There are no failures or warnings in this final motion report.

The current unversioned reports describe the shipped renderer. V4 reports and intermediate v5 candidate reports are retained as history and should not be read as current certification. Computational checks cover geometry, identity and scheduling. Naturalness remains a visual judgment; the browser review above is separate evidence.
