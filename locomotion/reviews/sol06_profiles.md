# Sol06 independent profile review

Reviewed `design_profile.py`, `profiles/`, `kinematics.py`, profile tests, and the model/gait boundary. No core files were changed.

## Findings

### P2: Matching alternate tibia dimensions bypass the R7 exporter guard

`model.py:230` compares configured lengths to the selected CAD manifest, but does not compare all three lengths to the R7 constants. Reproduction: copy the manifest to a temporary file, set its `lengths_mm[2]` to 140, set a copied config's `geometry.tibia_m` to `.14`, and call `export_models(temp_output, config=config)`. Export succeeds. The source lacks a toe frame, so its joint-origin checks cannot catch this change. `_toe()` still emits `xyz="0.105 0 0"`; default FK and the gait still use 105 mm. The initial profile README overstated the exporter guards; Sol02 has since corrected that wording. The export mismatch remains reproducible and needs a core guard fix.

Add an explicit comparison of configured coxa/femur/tibia lengths with the R7 kinematics constants before export. Test a coordinated config/manifest length change, particularly tibia. Loading an alternate profile alone does not cause this problem: profiles are audit-only and do not change config.

### P3: Accepted yaw limits can describe a valid pose that IK rejects

`kinematics.py:106` always returns `atan2(y, x)` in the principal yaw interval. Limits `[200, 250]` degrees are accepted; FK of `[225, 25, 60]` degrees is valid, but checked IK returns yaw `-135` degrees and rejects the pose. This is not the documented inward radial branch limitation: the radial reach is positive. Either select a `2*pi` equivalent yaw within the supplied limits or explicitly restrict/document the supported yaw interval. The current R7 interval is unaffected. Hip periodicity deserves the same policy.

## Verification

- `work/py311/bin/python -m unittest discover -s outputs/mist-robot/locomotion/tests -p 'test_design_profiles.py' -v`: 13 passed.
- `work/py311/bin/python -m unittest discover -s outputs/mist-robot/locomotion/tests -p 'test_model.py' -v`: 12 passed, including PyBullet FK agreement for all legs.
- Independent numerical checks used three geometries, both knee signs, and 600 sampled poses on the outward radial branch. FK/IK target error was at most `1.11e-16` m. Central-difference Jacobian error was at most `5.93e-11` m/rad.
- Fully extended and fully folded geometric reach boundaries round-tripped within `2.31e-18` m with limit checks disabled.
- Temporary files reproduced both findings without changing source files or config.

## Checks without findings

URDF, manifest and config hashes are pinned and rechecked. The source audit checks serial parent/child structure, exact +Z/+Y/+Y axes, zero moving-joint rotations, coxa/femur origins, limits, positive effort/speed, and every declared link mass. Tibia provenance is explicit: the R7 audit uses the pinned manifest because the source has no toe joint. A fixed toe joint can supply its transform instead. Hash changes and geometry/limit/mass mismatches are rejected.

Unsupported transmissions, mimic joints, extra moving joints, general axes, disconnected trees and closed loops are rejected. Four-bar mechanisms and inward radial solutions are documented exclusions, not missing implementations in this family.

Measurement records remain separate from runtime settings. They bind profile/source hashes, require matching fields, check finite and positive/nonnegative values where appropriate, and require full provenance, UTC time, test conditions and hashed evidence for measured status. These checks establish record consistency rather than validate a bench procedure. No arbitrary upper physical bound is claimed. Existing default FK, IK and Jacobian behavior passes the R7 regression tests.
