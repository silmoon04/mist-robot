# Coupon tooling checks, 6 September 2026

The first bed was generated and inspected as seven BRep solids and seven
watertight, consistently wound meshes. The exact per-part bounds and volumes
are in `bed1/validation.json`. The combined model has no intersecting part
volumes and fits in 206 x 202.5 x 10 mm. Numerical labels are actual cuts.

The feedback and request tests passed: 25 tests passed, with the separate CAD
subprocess integration test skipped in that stdlib run. The CAD integration was
then exercised separately using synthetic bearing, servo-width and insert
measurements inside a temporary directory. Its internal geometry checks passed:
three valid single-solid BReps, three watertight meshes, nine candidates, and
STEP/STL/3MF exports with blank physical feedback. The extent was
199.29 x 47.00 x 8.40 mm. The temporary directory was removed afterwards; no
second physical bed or invented feedback remains in this project.

The **strict CAD subprocess exit check failed**. Windows returned 0xC0000005
after the exports had been written and checked, with no Python traceback.
A plain `import cadquery` also reproduced a native error on exit. The same
shutdown problem occurred with the pinned CadQuery 2.6.1 / OCP 7.8.1.1.post1
runtime and with an independent Python 3.13 runtime. A clean PATH did not fix
it. No script masks the exit status or bypasses normal interpreter cleanup.

An upstream report describes the same Windows import-then-shutdown failure:
[CadQuery issue 1911](https://github.com/CadQuery/cadquery/issues/1911).
This is a tooling limitation; a successful file write alone is not presented
as a clean CLI run. Independent mesh checks do not require CadQuery and can
inspect the delivered files normally. Native Fusion execution remains a
separate outstanding check.

The old `coupon.curaprofile` was read as a ZIP. It contains partial Cura quality
changes: Elegoo_layer_030, five walls, 30% cubic infill, 200 mm/s print speed,
30 mm/s first layer, and 0.45 mm inner wall line width. It does not identify a
complete nozzle/material/temperature profile. No PETG compatibility or G-code
release is inferred from that file.
