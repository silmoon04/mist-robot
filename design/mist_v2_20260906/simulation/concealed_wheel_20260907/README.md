# Concealed-wheel validation

This folder validates a new full CAD inventory for the 139.5 mm femur, 140 mm tibia and wheel motor housed at upper-tibia stations 20–81 mm. It does not reuse the earlier 7.108 kg mass estimate. The full report's 17-link masses, centres of mass and tensors are authoritative.

`validate_concealed.py` first requires a completed four-leg/body export, clean shape and interference checks, matching frozen parameter bytes, declared SI mass properties, matching CAD/URDF joint frames and the existing actuator limits. `protected_actuator_contract.json` preserves electrical, servo, transmission and controller assumptions; it contains no reusable body or limb mass.

The runtime and all inputs are frozen before execution. A derived wheel-axis envelope applies the declared 1:1 miter transmission's assumed 0.9 efficiency to torque, while retaining the motor's speed and current limits. The original motor fields remain in provenance so this conversion cannot be applied twice. The new shaft/input gear's independent spin inertia and gyroscopic effects remain omitted; their mass and pose inertia are included in the CAD links.

The prescribed checks are stand, drive and a suspended three-contact-equivalent load fixture. The fixture applies a virtual vertical force at the axle's contact line, with the body fixed above the floor. It is not a gait. It records full-rate hold RMS, tracking, saturation and shaft travel. This corrects the older fixture's force-at-COM and sparsely sampled RMS assumptions without rewriting those earlier results.

One slow gait runs only if stand and drive pass, and the fixture has at least 20% continuous-torque reserve, at most 10 mm hold error, no hold saturation and no shaft travel violation. This is a predeclared simulation screening policy, not a measured thermal or reliability guarantee. A rejected gate is recorded rather than followed by a gait sweep.

The optional, separately authorized hypothetical gearing check changes only the simulated hip/knee reduction from 2:1 to 3:1, retains the original shaft travel span and intersects joint limits with the resulting output range. It checks one static kinematic reference and one corrected load fixture. Output speed follows the new ratio through the existing actuator model. The original 2:1 CAD remains unchanged, and its mass is explicitly retained as a hypothetical assumption; no 3:1 gear geometry, clearance or manufacturing release is implied.

Eight inexpensive contract regressions passed before any new dynamics run. They cover real partial/older report rejection, stale parameter bytes, the reproduced frame-origin bug, actuator-limit protection, wheel torque conversion and the gait gate boundaries. Evidence is in `contract_test_result.json`; independent review notes are under `review/`.

Run the wrapper only after the leg exporter supplies its frozen full report. Use a fresh `--name` each time; existing evidence is never overwritten. New case folders contain the source CAD snapshot, reconciled and derived parameters, frozen runtime, motion traces, fixture trace, gate decision and final validation summary. The actual wheel/cover CAD collision meshes, gear load rating, printed Z strength, temperature behavior and hardware commissioning remain separate checks.
