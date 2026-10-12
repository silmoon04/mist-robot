# Stair feasibility screen

The 139.5 mm femur, 130 mm tibia and 85 mm wheel geometry is **not ruled out by a 180 mm stair rise**. This screen found a connected, densely sampled first-front-leg lift and touchdown, plus feasible poses for the other necessary crossing events. It has **not found or verified a complete four-leg ascent/descent sequence**. The earlier scripted dynamics failures remain failures; these static candidates do not override them.

The stair is provisional: 180 mm rise, 270 mm tread, square noses, rigid surfaces, unlimited lateral tread width. A second and third riser are included, so an upper wheel cannot simply occupy the space of the next step. Actual stair dimensions, noses, tyre grip and side clearance need measurement.

![Static stair candidates](stair_candidates.png)

## Fixed assumptions

`parameters_snapshot.json` and `model_snapshot.py` freeze the source before search. Total mass is 6.341061857 kg. All three reductions remain 2:1 at 85% efficiency. At the existing 9.9 V assumption, continuous motor torque is 0.7281437625 N m and peak is 1.33493023125 N m. No rating or joint limit was increased to obtain a pass.

The knee servo housing moves with the femur. The motor coupling is `s = diag(2,2,2) q`, so output torque and motor torque are related by `tau_joint = A.T @ (eta * tau_motor)`. The frozen mass model places the 55 g knee servo 40 mm along the femur centre line. The later CAD mount has a substantial transverse offset; its matched mass properties and collision geometry have not been substituted here. This is the requested same-mass architecture screen.

For each pose, the code computes whole-robot centre of mass, nonnegative vertical support forces and joint gravity torque by virtual work. Contact forces satisfy force and moment balance. Required motor torque is `solve(A.T, dU/dq - J_contact_z * Fz) / eta`. The pitched calculation includes wheel camber, the actual lowest cylinder contact point and its offset from the axle. Gravity can then require yaw torque as well as hip/knee torque.

The original joint ranges and the original ±175° motor travel relative to the saved neutral pose are enforced. This retains the commissioning assumption even though the C018 supports multi-turn operation. Guarded searches add 2° from joint stops, 5° from motor-travel bounds, 15 mm from the support-polygon edge and 10% below the existing continuous torque assumption. These are design reserves, not measured error bounds.

## Concrete candidates

| Event | Body hip-plane position x/y/z (mm) | Body pitch | Largest motor torque | Support margin | Status |
|---|---:|---:|---:|---:|---|
| First front wheel over the nose | -156.2 / 8.8 / 297.7 | level | 0.6343 N m | 16.6 mm | Guarded static pose |
| Second front wheel over the nose | -86.6 / 19.7 / 286.5 | level | 0.6515 N m | 43.6 mm | Guarded static pose |
| Both front wheels on the upper tread | -139.5 / 18.0 / 282.4 | level | 0.6553 N m | 116.7 mm | Guarded static pose |
| First rear wheel over the nose | 65.5 / -70.5 / 272.2 | 3.17° nose-down | 0.6553 N m | 55.8 mm | Guarded static pose |
| Last rear wheel over the nose | 159.9 / 7.1 / 460.4 | level | 0.6553 N m | 20.9 mm | Guarded static pose |

Each JSON file stores feet, contacts, joint angles, motor offsets, forces and torques. These rows are independently solved poses with different footholds. They cannot be concatenated into a gait. In particular, their loaded feet cannot move sideways between rows without a separate unloading/repositioning plan.

`first_leg_candidate.json` and `first_leg_trace.csv` contain a connected first-front-leg candidate. Its other three wheel contacts stay fixed. The front-left wheel lifts at x=-65 mm, moves forward at axle height 245 mm, and touches the upper tread at x=85 mm. Across 815 dense samples, the minimum support margin is 15.0999 mm and the largest motor torque is 0.654601 N m. All original limits and guarded reserves pass at those samples. The body moves about 1 mm forward and a few millimetres sideways while staying near 298 mm hip-plane height.

An illustrative 14-second schedule uses 6 seconds to lift, 6 to cross, and 2 to lower. Its largest finite-difference motor speed is 1.622 rad/s; the static torque-plus-speed calculation stays inside the existing motor envelope. The schedule is deliberately slow, has unsmoothed phase transitions, and contains no acceleration or actuator integration. It is not a demonstrated stair speed. Reversing this same path gives a geometric/static lowering candidate for this one leg. It does not establish forward-facing descent of the whole robot, and no electrical braking or regeneration behavior has been tested.

## Clearance and pitch checks

Wheel rims are sampled as actual 85×24 mm cylinders, including both sidewalls. The 128-segment rim error is below 0.013 mm; a 0.06 mm numerical pad is used away from intended support contact. Each 24×18 mm link has a conservative 15 mm radius capsule, sampled at intervals no larger than 5 mm with another 2.5 mm pad. Intended tyre/tread contact naturally has zero clearance. Positive airborne wheel clearance at the nose is required separately.

The pitched rear search includes the full body-height envelope, deck tabs, phone cassette, 99 mm front bezel, rear connector guard, yaw carriage envelopes and three successive risers. These dimensions come from `cad/body_native.py`; they remain coarse envelopes, not full moving CAD collision meshes. Wheel camber changes both contact height and contact x/y location, which are included in support and torque calculations. Positive pitch means nose-up; the passing rear event uses -3.1703°.

The guarded level-body rear search failed from five starts. Its best point required about 0.680 N m and fell short of several added angular reserves. That did not justify longer links or a new ratio. A bounded ±5° pitch search found the guarded rear event above on its second start. The first positive-pitch start failed and remains in the saved trial history.

## Failures and verification

The initial last-rear search mistakenly retained the lower-support body-height bound of 309 mm even after all three support feet were on the upper tread. Its best reported attempt had objective 0.0225995, motor torque 0.810371 N m and violated joint limits. Raising the search bound to 489 mm only for that no-lower-support event found a valid pose. This changed a search bound, not a robot joint or torque limit. The first bounded result was overwritten during exploration; these values are recovered from the captured terminal output rather than presented as a complete original trace.

`first_leg_path.json` preserves an initial endpoint failure caused by applying the airborne numerical clearance pad at intended touchdown. The next path fixed the contact definition, but dense interpolation found small violations of the added guard bands between coarse samples. `verification_before_path_guard_refinement.json` and `first_leg_dense_trace_before_refinement.json` preserve those failures. The final path adds numerical reserve inside the same guard bands; all 815 interpolated samples then pass. `verification.json` names the exact path and records hashes.

Independent numerical checks give maximum gravity-gradient error 1.36e-10 N m, pitched axle-Jacobian error 2.64e-11 m/rad, wheel camber derivative error 3.56e-12 m/rad, mass closure error 1.11e-16 kg and static force/moment equation residual about 7.1e-15 in their respective units. These test the implementation identities, not the physical assumptions.

## What this changes in the design decision

There is no demonstrated geometric need to lengthen the links or increase a reduction solely because the old scripted step test failed. Coordinated body translation, lateral weight transfer, modest pitch and wheel placement deserve a full planner test first. The first-leg path and rear-event pose provide concrete targets for that test.

Full ascent and descent still require a connected contact sequence, support-force control, proper load transfer at touchdown, free-base dynamics, acceleration and speed limits, actuator delay and compliance, wheel scrub/friction, exact leg/body self-collision, wiring and the matched CAD mass properties. The 2° reserve does not simulate backlash or loaded deflection. No claim is made about fast stairs, obstacle perception, fall recovery, physical servo temperatures or print strength. No hardware was operated.

To reproduce locally, run `python search.py --case first_front_crossing --guarded`, `python pitch_search.py --degrees 5`, `python first_leg_path.py`, `python verify.py`, then `python present.py` from this directory. Repeated pose/path searches write new timestamped files; reports name their source. The model and parameter snapshots remain fixed.
