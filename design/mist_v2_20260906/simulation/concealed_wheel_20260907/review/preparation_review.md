# Concealed-wheel simulation preparation review

Read-only source review on 2026-09-07. No physics run or hardware operation was performed. The new validation wrapper was not yet present when this initial review was written.

## Required before a matched run

1. Bind the full CAD report to its exact parameter bytes. `reconcile_proximal_cad.py` reads `report.parameters_path` but does not compare the bytes with `report.parameters_sha256`. It checks only inertia units. Require mass `kg`, COM `m`, inertia `kg m^2` and CAD transforms `mm`, complete exports, all 17 nonempty rigid bodies, valid tensors, and agreement between their summed mass and the CAD total. Check parameter and report hashes again after preparation.
2. Verify the new kinematics against all four CAD specifications. The export changes tibia length to 140 mm, while the earlier design parameter file contains 130 mm. Require that length, actual ratios `[2, 2, 2]`, femur-relative knee topology, joint centres, link-frame rotations and wheel axes to agree. Reconciliation currently overwrites a textual 2:1 equation without checking those relationships.
3. Require zero shape errors, Boolean failures and positive-volume interferences before allowing a gait. The old reconciliation function records interference counts but accepts them. A completed export is not proof of interference clearance.
4. Use the 17 CAD inertials as authoritative. `model.total_mass` and `build_urdf` already prioritize them correctly. Do not add the old scalar component mass allowances again. Do not start from the previous 7.108 kg robot and move only a motor COM.
5. Preserve the original wheel-motor electrical data and derive an explicit wheel-axis envelope once. `run_sim.py` does not read `wheel_transmission`; merely adding the new field would leave direct-drive torque in the simulation.

## Correct 1:1 miter approximation

Let `r = motor_speed / wheel_speed` and let `eta` be motoring efficiency. Then `motor_speed = r * wheel_speed` and `wheel_torque = eta * r * motor_torque`.

For the declared `r = 1`, `eta = 0.9`, an equivalent wheel-axis torque-speed envelope uses 90% of the original stall torque and the unchanged no-load speed. Keep stall current, no-load current and the 1 A current limit unchanged. This makes the existing current-to-torque cap scale by 0.9 too. Do not reduce RPM or amperes by the efficiency factor. Do not change the STS joint transmission efficiencies.

Record that this is an assumed symmetric torque-envelope loss. It does not identify bevel friction, load-dependent efficiency, backlash or a thermal rating. The longitudinal input shaft, motor rotor and input gear remain lumped into the tibia; their reflected spin inertia and gyroscopic coupling are omitted.

## Supported-load fixture corrections

- `load_test.trial` applies the upward force at `getLinkState(wheel)[0]`, the wheel COM. The new output gear changes that location. Apply the ideal vertical force on the tire/axle centre line, using the wheel link-frame origin `[4]` or an explicit tire contact point directly below it. Preserve the CAD inertia.
- The existing hold RMS is calculated from one torque sample every 20 simulation steps. Calculate per-servo hold RMS from `ActuatorBank.motor_torque` at the full physics rate over the declared hold interval instead.
- Add motor travel and hold saturation checks. The old fixture status checks only error below 15 mm and torque below the continuous assumption.
- Derive the six-second run from `dt`, or explicitly require 1000 Hz. The existing 6000-step loop silently changes its duration if the physics frequency changes.
- Label this as a fixed-body, one-leg vertical loading fixture. Equal `mass * g / 3` loading does not establish the actual three-contact weight distribution or gait stability.

## Suggested conditional gait gate

Freeze the gate before reading new outputs. One conservative screening policy is:

- Existing stand and drive criteria all pass.
- The three-contact fixture passes all of its corrected criteria.
- The largest per-servo hold RMS is at most 80% of the unchanged continuous limit.
- Hold foot error is at most 10 mm, with zero travel violations and no saturation during the hold.

The current continuous assumption is 0.7281437625 Nm, so the suggested 20% reserve corresponds to 0.58251501 Nm. That reserve is a screening policy, not a measured uncertainty allowance. A failed gate should produce a saved skipped-gait decision; it should not trigger a ratio change, current increase or further sweep.

## Additional evidence and diagnostic risks

`run_sim.py` computes a wheel-axis diagnostic using `getLinkState(...)[1]`, the world COM/principal-inertia orientation. Use link orientation `[5]` for a wheel-local axis. An eccentric COM also requires accounting for rotational velocity when converting COM velocity to axle velocity. This affects lateral-slip diagnostics, not Bullet's underlying contact solution.

Run a copied runtime in an isolated process and record its exact hashes. Copying and hashing a file after its module has already been imported can attribute new source bytes to older executed code. Record original motor parameters and the derived envelope separately so resuming cannot apply the miter loss twice.

Even with matched mass and link frames, the existing URDF uses coarse collision boxes and cylinders. It does not test the new shell, coupling, gear teeth or cable clearance. A simulation pass cannot release this assembly for printing or stairs.
