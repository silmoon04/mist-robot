# Native proximal candidate

The Fusion Scripts launcher `MIST_Proximal_20260907` is installed. It calls `fusion_run.py`, which creates a new document and replays the proximal recipe using `native_replay.py`. The earlier `MIST_Rebuild_20260906` launcher and its candidate are preserved separately.

**This native run has not been executed.** Fusion is still at Autodesk sign-in. Syntax checks pass for the entry point and replay wrapper; the separate motion helper has its own installed-API and offline math/contract checks. None of these checks is a native build or motion-clearance pass.

Before making the new document, the runner validates the physical rigid-group plan. Missing or ambiguous groups stop the run rather than silently attaching gears or the wheel motor housing to the wrong link. The runner then creates native feature components, adds sixteen as-built joints, applies the assembled-angle offsets, checks Compute All and one-pose interference, and exports F3D/STEP plus reports under `cad/native_proximal_runs/<timestamp>`.

The native motion helper probes and restores each joint to verify its axis, centre and sign. It keeps internal rotors in explicitly fixed-phase preview groups; gear and belt mates are not modeled. Component material and colour attributes are metadata. Native Fusion physical material assignment and mass-property agreement have not been established; use the separate CAD mass audit until those are checked.

Any script failure writes `build_report.json` and raises. Successful native execution would establish only the recorded checks. It would not release the gears, shaft interfaces, printed structures, wiring, full travel or walking/stair performance. Generator dimensions remain inputs to the recipe; editing the recorded user parameters alone does not regenerate every placement.
