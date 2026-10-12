# Deposition parser independent review

The reviewed parser passes for the frozen numeric CuraEngine profile. The two input-validation findings raised during review were fixed by the parent and checked again. No unresolved finding affects that profile.

The existing eight-check suite passed without rewriting its receipt. Independent endpoint and midpoint quadrature matched COM and inertia for eight segments under a full 3D rotation and translation. The rectangular bead correction also matched a single cuboid formula.

| Archived R2 femur quantity | Result |
| --- | ---: |
| Parsed deposited volume | 24860.3055 mm3 |
| Rounded CuraEngine volume | 24860 mm3 |
| Difference | 0.001229% |
| Robot part PLA | 27.190685 g |
| Excluded support PLA | 3.577744 g |
| Excluded SKIRT adhesion PLA | 0.058349 g |

The parser handles E resets, absolute and relative coordinates, and retraction debt consistently with the recorded linear profile. G90 and G91 clear the M82/M83 override, matching the [Marlin M82 documentation](https://marlinfw.org/docs/gcode/M082.html). G92 changes the logical coordinate offset while preserving the physical position. See [Marlin G92](https://marlinfw.org/docs/gcode/G092.html).

Mass converts filament volume in mm3 to kg using density_g_cm3 * 1e-6. Segment moments integrate the midpoint displacement plus the segment direction outer product divided by 12. Converting kg mm2 to kg m2 contributes another factor of 1e-6. Both conversions and the layer-centre Z correction are correct.

The runner returns gcode_to_source_transform; pass that value as the parser argument gcode_to_source. The translated-tray check retained its original STL minima of approximately [0.0174, 0.0043, 0.0067] mm. The matrix inverse composition and restored deposition bounds passed.

Resolved findings: travel G2/G3/G5 now fails explicitly, and malformed or non-finite homogeneous transforms are rejected. The source hashes in parser_review.json identify the exact reviewed implementation.

Limitations:

- This review does not establish correctness for arbitrary printer G-code, startup homing or externally changed firmware state.
- Deposited E is commanded filament. Actual filament diameter, density, extrusion calibration, pressure and shrinkage require measurement.
- The mass model distributes fresh material uniformly along each deposited segment and treats moving retraction recovery as a non-depositing prefix.
- The line model and optional rectangular bead correction approximate mass distribution; neither reconstructs bead overlap or proves printed strength.
- A variable or different initial layer height would require a corresponding per-layer centre correction. The frozen profile uses 0.2 mm for both.

The archived R2 files, smoke archive, parser, tests and existing test receipt were preserved. Only the three parser_review outputs were written.
