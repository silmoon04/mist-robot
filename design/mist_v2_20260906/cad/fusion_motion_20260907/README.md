# Native Fusion motion helper

This helper adds native as-built yaw, hip, knee and wheel joints, plus explicit rigid groups for each physical link. **Its native 17-component test fixture passed on 2026-09-07:** all 16 joint direction/axis/restoration checks and 96 component/world-datum checks passed, including combined upstream motion. A test F3D was exported and the existing MIST body remained unchanged. The full 657-part assembly, nested occurrence hierarchy and multi-part rigid groups have not been validated by this fixture. See `NATIVE_VERIFICATION.md` for the exact evidence and limits.

`motion.py` imports Autodesk only when the native entry point runs. Its geometry and angle-mapping functions can be tested with ordinary Python. `API_EVIDENCE.md` records the official Autodesk documentation and installed primary declarations used to check the calls.

The final proximal integration pass is recorded in `INTEGRATION_REVIEW.md`. `reviewed_groups.py` supplies an explicit map for the retained part identities and the rotating proximal shaft. The current 657-part recipe passes plan creation with 16 main revolutes, 33 rigid groups and 16 fixed-phase rotor attachments. `current_integration.json` points to the exact plan, source snapshots and assignment audit.

## Integration

Call this after `body_native.build_body(...)` and the selected leg builder return, before the existing native export/report step:

```python
from pathlib import Path
import sys
sys.path.insert(0, str(CAD / 'fusion_motion_20260907'))
import motion

motion_report = motion.rig_build_results(
    design, params, body, legs,
    output_directory=out / 'motion',
    group_overrides=explicit_groups,  # Optional if every leg part has rigid_group.
)
```

`rig_build_results` returns a serializable native report and writes `motion_plan.json` and `native_motion_report.json`. A native failure writes the partial report and raises. The motion integration does not modify leg geometry. The proximal `fusion_run.py` wrapper supplies the reviewed map before and after feature replay; the root agent separately corrected native placement and root-renaming behavior during live validation.

The existing builder result contract is supported:

```python
body = {'spec': body_spec, 'components': {'part_name': native_component, ...}}
leg = {'spec': leg_spec, 'components': {'part_name': native_component, ...}}
legs = [leg_FL, leg_FR, leg_RL, leg_RR]
```

A `part_occurrences` map can replace `components`. The helper resolves each component through `root.allOccurrencesByComponent(...)`, requiring exactly one occurrence and retaining its root assembly context. It does not identify parts by display name. Reused components with several occurrences require a more specific binding adapter and currently fail clearly.

For fully explicit integration, the lower-level calls are:

```python
plan = motion.build_motion_plan(params, body['spec'], [r['spec'] for r in legs],
                                group_overrides=explicit_groups)
occurrences = motion.resolve_occurrences(design.rootComponent, body, legs)
report = motion.apply_motion_plan(design, plan, occurrences,
                                  out / 'native_motion_report.json')
```

The occurrence dictionary keys are `body/PART_NAME` and `FL/PART_NAME`, etc. Every key must appear exactly once in the plan. A changed plan hash or duplicate occurrence binding fails before creating constraints.

## Required physical grouping

Every leg part must have `rigid_group`, or an explicit override keyed by `FL/PART_NAME`. Supported structural values are `body`, `yaw`/`pod`, `femur`, `tibia` and `wheel`. Body recipe parts always belong to the chassis group. For example:

```python
explicit_groups = {
    'FL/Y06_yaw_output_40T': 'yaw',
    'FL/H06_output_40T': 'femur',
    'FL/W05_FIT0493_motor_CASE': 'tibia',
    # Include all remaining parts unless they already have rigid_group.
}
```

Those examples illustrate why the helper refuses to treat `part.link` as a complete motion assignment. The old static recipe uses some links as placement frames: its yaw output gear is tagged body, hip output gear pod, and wheel motor case wheel. Simply grouping those tags would make parts move incorrectly. The fitted recipe's actual assignments must be supplied before native integration; no provisional blanket mapping is hidden in the helper.

A separate group ending in `_rotor`, such as `knee_input_rotor`, is supported. Its housing frame is taken from `motion_housing_link`, then `mass_group`, then `link`. This keeps the new femur-mounted knee rotor attached to the femur when its geometry placement frame differs. All members must agree on that frame. The helper creates a separate rigid group and an explicitly named **fixed-phase preview attachment** to the housing. This makes those parts travel with their housing while holding their assembled phase. It does not create gear or belt mates, animate belt circulation, or certify the torque path. The original transmission equations remain metadata. Bearing envelopes stay with their declared group; inner and outer race rotation is not separately modeled.

Each leg spec also supplies:

- `leg_name` and `pose_deg` containing yaw, hip, knee and heading.
- `joint_centers_world_mm` containing yaw, hip, knee and wheel.
- `parts` containing unique names and explicit grouping as above.

Yaw uses world +Z. Hip, knee and wheel use local -Y rotated by the leg's actual heading. Wheel rotation has no position limits. The other limits come from `params['geometry']['joint_limits_deg']` without widening them.

## Native behavior and angle convention

The helper creates rigid groups in `design.rootComponent` using full-path leaf occurrences and `includeChildren=False`. It clears `isGrounded` and `isGroundToParent` on those members and their ancestor occurrences, then pins one chassis representative. All changed grounding flags are recorded. Use it in the new design created by the existing rebuild script, not as a general-purpose modifier of a user's unrelated assembly.

Joint datums are native fixed sketch points in each parent link's representative component. A parametric offset plane has its normal aligned with the intended joint axis; the as-built joint uses standard Z in that geometry frame. The sketch point is passed as a root-context proxy, so its position follows the parent link. This replaced the original custom-line definition after a live test showed rotation about the sketch normal rather than the requested custom line. The helper never uses direct-modeling-only raw construction-point or transient-line APIs. A requested axis that is not normal to a supported principal plane of the representative component fails explicitly.

New as-built joints represent the assembled pose; their angles cannot safely be treated as absolute physical coordinates. The helper captures Fusion's initial angle `r0`, drives **0.1° (0.001745329252 rad)** and compares the child transform relative to its parent. That increment matches the setter resolution observed in the native diagnostic. The original strict angle, axis and centre tolerances remain unchanged. The original pose is restored and checked before limits are applied. The mapping is:

`fusion_angle = r0 + measured_sign * radians(physical_q - built_physical_q)`

Both transformed endpoints are sorted before setting minimum and maximum. Thus a hip built at 58° receives physical bounds -40° to 125° as relative offsets -98° to +67°, with Fusion's measured sign and initial offset included. The native report records `built_physical_deg`, `initial_fusion_value_rad`, measured sign, probe checks and final radian limits for every joint. Wheel limits are explicitly disabled.

Autodesk's inspected API does not document which occurrence rotates positively. The helper therefore measures the sign on each run rather than inferring it from `rotationAxisVector`. In the passing fixture, yaw signs were +1 and hip/knee/wheel signs were -1 on all four legs. These observations are not hard-coded. A failed probe or restoration still raises.

`rotationValue` produces a transient Drive Joints pose in the tested Fusion build. The diagnostic found that Compute All resets it to the as-built value. `refresh_joint_drive()` therefore runs doEvents and viewport refresh before measuring a driven pose, without calling Compute All. Recompute occurs after the original values are restored. The fixture follows the same rule for its combined +5° yaw, +4° hip and -3° knee check. This does not make the driven pose a persistent design parameter.

## Checks completed and still pending

`python static_api_check.py` passes **50 installed primary API member/signature checks** without importing Autodesk's native DLLs. The check follows inherited declarations, including `BaseComponent`. It caught and removed unsupported `GeometricConstraints.addFixed` and as-built health properties during development; the final helper uses documented `SketchEntity.isFixed` and native validity/suppression state.

`python -m unittest test_motion -v` passes **16 offline tests** covering physical/as-built offset mapping, reversed rotation signs, rotated-parent probe math, wrong-axis-centre rejection, wheel limits, explicit rotor grouping and housing frames, missing/ambiguous groups and occurrence bindings, and failure reporting when Autodesk is unavailable.

`python -m unittest test_motion test_integration -v` passes **22 tests** in total. The six added checks cover all 657 real recipe parts, the wheel's 1:1 rotating group, separation of input and output gears, rejection of unreviewed retained-part changes, and repeated wrapper loads after a source change with identical size and timestamp.

The native fixture adds evidence beyond these offline checks: 16 native revolutes, successful direction/axis/centre probes, restoration, and correct downstream world datums after upstream motion. It has 17 root-level component occurrences and no multi-part rigid groups. Nested assemblies, rotor attachments, full ranges, collision, wiring clearance and physical strength remain separate validation. `full_motion_verified` remains false because neither the fixture nor the small probes establishes those properties.
