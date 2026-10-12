# MIST CAD check pipeline - what Claude can verify and how to export for it

How the model-checking loop works: model the current manufacturing design in
Autodesk Fusion, export named components/parts, then run numeric fit, integrity,
render, slicer, and physics checks against the export. The first historical run
was done 2026-07-06 against a concept `MIST.stl`; that file is not present in
this workspace and its dimensions are superseded. Start the current CAD path at
[`MIST_FUSION_360_GUIDE.md`](MIST_FUSION_360_GUIDE.md).

## What Claude can do (and what it uses)

| Check | How | Trust level |
|---|---|---|
| Dimensions, bounding boxes, per-part sizes | `trimesh` (Python) — exact numbers from the geometry | High — this is measurement, not vision |
| Part count, watertightness, inverted normals, duplicate shells | `trimesh` integrity checks | High |
| Volume → printed-weight estimates | watertight volumes × material density × infill factor | Medium (infill factor is an estimate) |
| Fit checks vs real components | place datasheet-sized boxes (servo, phone, battery, boards) against pockets numerically; cross-sections through pockets | High *if* the export has real scale and separated parts |
| "Does it look right" | render PNGs (matplotlib/Blender) and read them | Medium — good for shape/topology/proportions, NOT for measurements |
| Print-readiness | integrity checks now; slicer dry-run via PrusaSlicer console CLI if installed; Blender headless (`blender --background --python`) if installed | High once tools installed |
| Physics: mass budget, joint torque, current, runtime | plain maths from measured geometry + component datasheets | High for sanity-checking, not a substitute for the single-leg load test |

The older text referenced `mist_3d/tools/analyze_mesh.py`, `render_views.py`,
`build_printable.py`, `variants/`, and `printable_v1/`. Those artifacts are not
present in this workspace as of 2026-07-12. Do not claim that regeneration or
automated mesh checking is available until the tools are restored. Fusion's
own Measure, Properties/CoM, Section Analysis, Interference, 3MF export, and the
existing slicer previews remain available for the manual loop.

## Export rules (this is the part that matters)

1. **Model at real size in millimetres.** In Fusion, set Browser → Document Settings → Units to millimetres, and enter unit-bearing expressions. Never repair an arbitrary-scale model by guessing one overall dimension.
2. **Preserve component identity.** Create, name, and activate components before geometry. Export each printable component separately; do not collapse the moving assembly into one unnamed mesh.
3. **Prefer 3MF for the slicer, STEP for editable/audit exchange, and F3D/F3Z for native archival.** 3MF stores units; STL is unitless and should be a compatibility fallback. GLB/OBJ remain useful for named visual review when a downstream checker supports them.
4. **Use the guide naming scheme** (`base_link`, `FL_hiproll`, `FL_femur`, `FL_tibia`, `FL_wheel`, and matching q1/q2/q3/wheel joints). Names are free documentation and make every report readable.
5. **Add real-size envelope components** for the Mi 9 SE, STS3215 body/ears/horn/cables, battery, ESP32, PDB, UBEC, fuses, caps, connectors, tool access, and service loops. Hide them from manufacturing exports, not from design validation.
6. **Export closed printable solids.** Concept surfaces and duplicate shells are acceptable only as visual references. Run Fusion Compute All, then inspect the exported 3MF in the slicer before release.

## Findings from the first check (MIST.stl, 2026-07-06, assuming x100 scale)

- Robot ~256 x 348 x 365mm; barrel body ~196mm dia x 238mm tall; ground clearance ~66mm. Barrel fits the Neptune 4 Pro bed (225 x 225 x 265) as one piece, barely — consider splitting anyway.
- **Screen panel is 134 x 90mm — the Mi 9 SE (147.5 x 70.5) does not fit in either orientation.** Needs +14mm width (landscape) or a redesign around a cutout/bezel.
- Front leg segments 49 x 70 x 157mm — STS3215 body fits the cross-section. Plausible.
- No obvious wheels found near the ground (foot-like boxes only). MIST spec has 4 wheel servos — the concept model and the build plan disagree; resolve in the next modelling pass.
- 108 bodies, duplicated shells, inverted normals, not watertight — fine as historical concept evidence, not sliceable. Rebuild manufacturing parts in the current Fusion master, one component/interface at a time.

## Feasibility numbers v1 (rough, at x100 scale — redo when masses are real)

- Mass budget: 16 servos ~960g + battery ~180g + phone 155g + electronics/harness ~200g + printed parts ~800-1400g (the 196 x 238 barrel alone is ~600-900g in PETG) → **~2.3-2.9kg total**.
- Femur torque, walking worst case (diagonal support, ~1.2-1.4kg on one leg): at 80mm foot offset ≈ 10-11 kg·cm; at 120mm ≈ 14-17 kg·cm, vs 30 kg·cm stall. Continuous holding should stay ≤ ~10 kg·cm (~1/3 stall) — so it works *only if* feet stay under the body and idle = park-on-wheels/torque-off. The tall barrel raises the centre of mass, which worsens both lever arms and tipping.
- Current: normal walking bursts ~4-7A total; one leg's worst-case stall 4 x 2.7A = 10.8A < 15A branch fuse; normal trunk load well under the 30A main. The fuse plan is consistent with the model.
- Runtime: 2.2Ah / ~4A average ≈ 30 min mixed use.
- Biggest single lever on the design: **cut body mass**. Every 100g saved is ~0.8 kg·cm less femur torque at 80mm offset.

## Historical variant explorer (2026-07-06; tooling absent)

The missing `mist_3d/tools/generate_variants.py` and `render_variants.py` were
reported to have generated named-part GLBs under `mist_3d/variants/`. Their
2026-07-06 output is useful as historical design evidence only: sprawled
variants reportedly reached 88–99% of servo stall, while tucked variants were
torque-cheap but narrow. The old `v5_balanced` result used a 170 mm barrel and
other geometry that is not the July 12 CAD baseline. Do not call it the current
working model or quote its figures as a fresh reproducible result.

## Historical printable kit v1 (2026-07-06; artifacts absent)

The missing `mist_3d/tools/build_printable.py` and
`mist_3d/printable_v1/` were reported to contain a ten-part printable concept.
Neither the claimed `VERIFY` block nor the generated assembly can be inspected
in this workspace. Its reported ~1.74 kg printed mass, ~3.2 kg total mass, and
51% transient femur load are historical clues, not reproduced checks. Rebuild
the manufacturing geometry from the Fusion master and use measured servo
interfaces. Retain the useful failure lessons: check hip height, pod-to-shell
clearance, and wheel-to-shin clearance across the entire joint range.

## Blender headless (when installed)

Blender isn't currently on this PC. Installing it unlocks the best version of this loop: Claude can run `blender --background MIST.blend --python script.py` to export named parts, take real rendered screenshots, measure objects, and even apply fixes — directly from the .blend, no manual exporting.
