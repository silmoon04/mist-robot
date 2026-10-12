# R5 revision requirements

This revision starts from the checked R4 quadruped. Preserve the R4 package and geometry as a separate baseline.

1. Turn each hip servo case180 degrees so its tail faces inward toward the yaw joint. Rearrange the supported coxa to preserve real case, cable, fastener and yaw clearances. Increase coxa length only as required by that packaging.
2. Replace the curved lower leg with a straight knee-to-toe structural member. Keep the105 mm joint-to-toe length and opposite-side shaft support. Prefer one main printed member with a short removable bearing cheek if assembly needs it.
3. Preserve the four-leg architecture, inward knee servo cases, bare landscape Mi9SE upright pan mount, thirteen STS3215 C018servos, direct drive, owned component envelopes and PLA print strategy.
4. Check the new load paths, part printing orientation, actual screw/nut assembly, full static and sampled motion clearances. Recalculate fastener positions, sliced mass/COM/inertia, URDF and bounded nominal movement with the new coxa length.
5. Export current Fusion, STEP, oriented print parts, affected fit specimens, viewer and indexed package. Superseded checks must not be presented as evidence for R5.
6. Retain physical fit and load qualification gates. The existing brain app and hardware calibration are separate commissioning work; this revision does not actuate hardware.

Status: R5 geometry and the digital checks are complete. The selected coxa is 70 mm; the final yaw operating limit is 19 degrees each side of neutral. R4 remains available separately.

The nominal assembly, sampled full-body motion and 312 integer-yaw distance checks pass. The minimum recorded clearance is 1.573865 mm against a 1.5 mm target. All 34 production and 32 fit/fixture meshes pass, and three plates reload with 15, 5 and 12 objects. Native Fusion has 14 links, 133 closed solids and 13 verified motions, with actual native yaw limits matching the manifest.

The deposition-based assembled estimate is 2.756962 kg. The final 64-second nominal crawl, half-stiffness case and full-solid case pass; both feedback-dead-zone sensitivity cases fail walking. The ordinary analytical strength screens pass conditionally, with the post's margin about 1.19. Independent lateral and shock bounds, measured PLA behavior and loaded hardware operation remain unqualified.

The release is for controlled fit and fixture printing. Use the R5 femur auxiliary cheek and deck as well as the five selected revision-plate parts; the plate is not the complete change set. Physical calibration, thermal endurance, phone-network integration and reliable hardware walking remain subsequent tasks.

For future revisions, check complete-body movement and minimum gaps before binding the expensive native, slicing and physics outputs. Preserve failed diagnostic ranges and earlier releases. An isolated bracket check does not establish assembled-body clearance.
