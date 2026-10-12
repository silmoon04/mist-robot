# Candidate CAD mass reconciliation

Accounted mass: **6.341 kg**. This uses the actual exported candidate volumes and nominal/assumed hardware values. It is neither a scale measurement nor a slicer estimate.

| Group | Accounted mass |
|---|---:|
| FL | 1152.1 g |
| FR | 1152.1 g |
| RL | 1152.1 g |
| RR | 1152.1 g |
| body | 1282.6 g |
| Electronics, harness and unmatched hardware allowance | 450.0 g |

The per-part JSON keeps every mass source. Bearings are deliberately represented by a solid steel annulus estimate, which can exceed actual ball-bearing mass. Fully solid PETG volumes also exceed many sliced parts. Unmodeled couplings, nuts, wires and covers can add mass. These opposing uncertainties cannot be collapsed into a claimed finished weight.

A mass-only parameter snapshot is produced only when its accounting agrees with the CAD grouping. It retains simple link COM/inertia and collision geometry, so it is a sensitivity experiment rather than a reconstructed dynamic CAD model. Earlier3.95376kg simulation results remain attached to their original parameters.

Missing mass assignments: none among exported parts; unfinished physical parts still require a BOM.
