# Concealed-wheel wrapper implementation review

Reviewed `validate_concealed.py` and `concealed_fixture.py` on 2026-09-07 before the author's follow-up corrections. No physics was run. The one executable check was an in-memory frame-validation mutation using an existing full CAD report as a static fixture; it did not simulate or reuse that robot's mass for a new case.

## Changes that address the preparation review

- The wrapper requires four legs plus body, finished exports, clean shape/interference checks, all declared units and a matching parameter hash.
- It requires the 139.5 mm femur, 140 mm tibia, 2:1 joint reductions and the declared 1:1 concealed drive.
- The derived wheel envelope multiplies torque by efficiency without changing electrical current fields or reducing no-load speed for a 1:1 drive. It rejects applying the conversion twice.
- The new fixture applies force on the wheel axle line and records active-leg hold torque/error at 1000 Hz. Its travel and hold-saturation checks are consistent with `ActuatorBank`.
- The copied wheel-slip diagnostic uses the link frame and converts COM velocity to axle velocity correctly.
- The dispatch decision requires passing stand/drive/fixture results, 20% continuous-torque reserve and error no greater than 10 mm.

## Findings to resolve before execution

### 1. Link-frame translations are not checked against kinematics

`verify_frames` checks joint centres and frame rotations, then compares each CAD frame with the inertia allocation frame. It never compares the frame origin with the correct FK joint origin.

Reproduction: add 10,000 mm to the X translation of both `specifications.FL.frames_world_mm.femur` and `link_mass_properties.FL_femur.frame_local_to_world_mm`. The function still returns `link_rotations_and_inertial_frames_match: true` and the same maximum joint-centre difference of `5.551115123125783e-17 m`.

Require frame origins at yaw centre, hip pitch centre, knee centre and wheel axle respectively. Also require the base inertial allocation frame to match the body hip-plane origin. A matching error in two copies of a frame cannot establish that the frame is correct.

### 2. Protected actuator limits can change with valid input hashes

`basic_preflight` checks ratios and physics frequency but accepts increased wheel current, servo torque/voltage/continuous fractions, or transmission efficiency. Hashes identify bytes; they do not enforce the instruction to retain actuator limits.

Compare a documented protected subset with a frozen reference or explicit constants before simulation. Include the 1 A wheel current limit, assumed 0.9 miter efficiency, servo electrical endpoints, supply voltage, peak/continuous fractions, joint efficiencies and motor travel limits. This check can use an old parameter file solely as a limits reference without reusing its mass or COM.

### 3. Freeze all inputs before the tests

The current main path rereads the source report and parameter path during reconciliation. Copy the captured parameter bytes and report before importing/running the simulation, then reconcile the captured inputs. Preserve the original report and its hash separately if a prepared report needs an adjusted local parameter path.

The conditional gait controller is read from the older live result folder only after the fixture finishes. Capture and hash its 60 mm / 4 s configuration during preparation. Record the wrapper and package initializer hashes too. Read each source's bytes once when copying and recording its original hash.

The normal fresh CLI import path appears correct: frozen `model.ROOT` resolves to `runtime_snapshot`, and later imports reuse those frozen modules. Add explicit `module.__file__` and `model.ROOT` assertions so an imported/cached module cannot bypass the frozen runtime. `supported_crawl` and its geometry helper prepend the output directory to `sys.path`, making those assertions useful even when ordinary CLI execution works.

### 4. Preserve a failed optional planning attempt

`supported_crawl.run` can raise during COM planning before writing its normal report. The wrapper then exits without a final validation summary or source verification, despite having completed the three prerequisite checks.

Record one failed planning/runtime attempt, retain the completed checks and verify inputs/sources in `finally`. Do not retry, retune or raise limits. This does not require changing gait physics.

## Minor consistency improvement

Read the gate's numeric thresholds from `POLICY` rather than repeating `.20` and `.010` in `gait_gate`. They currently agree, but a later policy edit could otherwise change the recorded policy without changing the decision.

The frozen full concealed-wheel report was not available for this review. Passing these source checks still requires running that exact report through preflight, and a later simulation pass will retain the documented coarse-collision and unmeasured-actuator limitations.

## Follow-up review after corrections

The four findings above are materially addressed in the follow-up version. Frame origins are compared with FK; the base frame is checked; a protected actuator/control contract is enforced; CAD inputs and the controller are captured before reconciliation/execution; runtime module paths and `model.ROOT` are asserted; and optional gait errors are retained before final input verification.

The original shifted-frame test was repeated independently in memory. The unmodified control still passes. The 10 m femur-frame shift is now rejected with `CAD/URDF frame origin differs for FL/femur`. No physics was run.

The additional `[2, 3, 3]` hypothetical branch correctly uses the femur-relative diagonal coupling. For each changed axis it divides the unchanged shaft span by the new ratio around the initial joint angle, intersects the result with existing physical joint limits, and then checks all twelve shaft targets across the sampled reference. It retains the current matched inertials only as a declared assumption; new gear mass and clearance remain undesigned. The branch does not dispatch a gait or alter the actual 2:1 CAD. A `torque_reserve_gate_pass` field describes torque reserve alone and should be read together with the fixture criteria and ROM result.

No new execution-blocking issue was identified in the normal fresh CLI path. This is source and contract review, not an endorsement of a future simulation or hardware outcome.

Reviewed SHA-256 values:

- `validate_concealed.py`: `34b466d0f16e336187abd6d064076eb70d0be0a6fa2aa6c6edcb8c826a6bed5c`
- `concealed_fixture.py`: `e1b8d67e906e993b7d07534f2309f3615c0fe4c18074f376dcf2accf3be316f1`
- `protected_actuator_contract.json`: `f511bb266a8d11162d2196874836935615ee4a122752fd7b16c9878a52defd1a`
