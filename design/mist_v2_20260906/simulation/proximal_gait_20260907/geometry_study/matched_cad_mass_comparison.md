# Matched CAD mass distribution: static comparison

The matched 657-part CAD input weighs **7.10816 kg**, up from the earlier **6.34106 kg** sensitivity model: **+12.10%**. The change is substantially larger within particular moving links. Each femur assembly grows from **226.53 g to 569.79 g**, while each yaw carriage shrinks from **376.86 g to 188.57 g**. The heavier femur COM moves closer to its hip axis, so joint inertia does not increase in proportion to femur mass.

At neutral, the complete leg's inertia about its yaw axis approximately doubles; about its hip axis it rises **16.49%**, and about its knee axis **7.10%**. The whole robot COM moves **2.448 mm lower**. This is not simply a uniformly heavier robot or a raised-COM problem.

This report uses [parameters_cad_inertials.json](../../proximal_cad_20260907/parameters_cad_inertials.json), the earlier same-mass parameter snapshot, the frozen `runtime_cad/model.py`, and the corrected full-link COM helper. [matched_cad_mass_comparison.json](matched_cad_mass_comparison.json) contains all 17 old/new masses, local COM vectors, full inertia tensors, pose definitions, contact forces, signed torques, per-leg joint mass matrices and source hashes. [compare_matched_cad.py](compare_matched_cad.py) reproduces the analysis without connecting to a physics engine or taking any simulation steps.

## Where the mass moved

| Group | Earlier total | Matched CAD total | Change |
|---|---:|---:|---:|
| Base | 2.497145 kg | 2.449207 kg | −0.047938 kg |
| Four yaw links | 1.507437 kg | 0.754273 kg | −0.753164 kg |
| Four femur links | 0.906109 kg | 2.279173 kg | +1.373064 kg |
| Four tibia links | 1.092197 kg | 1.275263 kg | +0.183067 kg |
| Four wheel links | 0.338175 kg | 0.350243 kg | +0.012068 kg |
| **Total** | **6.341062 kg** | **7.108160 kg** | **+0.767098 kg** |

Representative local COM coordinates are shown for FL; the other sides retain their appropriate mirrored lateral coordinates.

| Link | Earlier local COM, mm | Matched local COM, mm |
|---|---|---|
| Base | (3.323, 0.0015, 33.209) | (3.388, 0.0015, 30.414) |
| FL yaw | (17.500, 15.000, 0) | (50.378, −29.095, 3.048) |
| FL femur | (0, 0, −62.527) | (0, 27.557, −41.688) |
| FL tibia | (0, 0, −95.518) | (0, 38.756, −79.660) |
| FL wheel | (0, 0, 0) | (0, 2.231, 0) |

Femur and tibia COMs move toward their proximal joints but acquire substantial lateral offsets. The yaw carriage COM moves farther from its yaw axis even though its mass nearly halves. These changes affect yaw inertia and the COM response to a body shift. Wheel COMs lie on the spin axis, so the nominal zero wheel-angle choice introduces no relevant COM error for this CAD input.

The CAD file's **`link_mass_properties` is authoritative**. Its retained scalar component fields are compatibility inputs and must not be summed as the new robot mass. Doing so would incorrectly recover approximately 3.954 kg. This comparison uses the 657-part matched input only; earlier individual motor-offset notes are not substituted for its per-link properties.

## Inertia about the actual joint axes

The following neutral-pose values include each joint's descendant rigid links, with the other joints and wheel rotation held fixed. They include the parallel-axis contribution from each link COM. The body and other legs are excluded from this local calculation. Values are in kg·m² and are the diagonal entries of the saved per-leg joint mass matrix.

| FL joint axis | Earlier | Matched CAD | Change |
|---|---:|---:|---:|
| Yaw, all four moving links | 0.00721183 | 0.01465687 | +103.23% |
| Hip, femur + tibia + wheel | 0.01351697 | 0.01574572 | +16.49% |
| Knee, tibia + wheel | 0.00438827 | 0.00470000 | +7.10% |

Considering the femur alone, its inertia about the actual hip-pitch axis changes from **0.00121747 to 0.00219264 kg·m² (+80.10%)**. The components are:

| Femur contribution | Earlier | Matched CAD |
|---|---:|---:|
| Pitch inertia about its own COM | 0.000331834 | 0.001202421 |
| Parallel-axis term to the hip | 0.000885631 | 0.000990223 |
| **Total about hip-pitch axis** | **0.001217465** | **0.002192644** |

The COM moves from 62.527 mm to 41.688 mm down the femur, partly offsetting its 151.53% mass increase. The complete hip-axis inertia rises less than the femur-only value because it also includes the distal links, whose contributions change less. Conversely, lateral offsets and carriage redistribution increase yaw inertia substantially. The neutral yaw–hip joint-mass cross term also changes from −0.00201078 to −0.00478332 kg·m², so simultaneous motion cannot be represented by independently scaling three diagonal inertias.

These values describe rigid-link kinetic energy about fixed parent axes. They are not a free-base effective inertia measurement, and they omit independent motor/gear rotor inertia. They quantify a changed dynamic burden without proving which contribution causes a closed-loop failure.

## COM and static holding loads

At the same neutral joint angles, whole-robot body-frame COM changes from **(1.309, 0.0006, −29.203) mm** to **(1.168, 0.0005, −31.651) mm**. With the body origin at 232.5 mm, COM height is therefore 203.297 mm versus 200.849 mm. The nearly symmetric XY position remains close to the body centre.

The torque calculation uses `required joint torque = gravity torque − contact Jacobianᵀ × vertical reactions`, then applies the existing 2:1 reduction and 0.85 efficiency to obtain servo-shaft torque. Four-foot reactions use a minimum-norm equilibrium split because four-contact static force sharing is indeterminate without compliance. Three-contact reactions are uniquely determined under the stated vertical-force assumptions.

| Neutral FL quantity | Earlier | Matched CAD |
|---|---:|---:|
| Vertical contact reaction | 15.673 N | 17.554 N |
| Leg-gravity hip joint torque | +0.369833 Nm | +0.507576 Nm |
| Leg-gravity knee joint torque | −0.163257 Nm | −0.161970 Nm |
| Net supported hip shaft torque | −0.335609 Nm | −0.320983 Nm |
| Net supported knee shaft torque | +0.441988 Nm | +0.507327 Nm |

The neutral hip shaft load magnitude **slightly decreases**, despite the heavier femur. In this pose, the larger leg-gravity moment offsets part of the ground-reaction moment. The knee shaft load increases. It would therefore be incorrect to say every static joint torque rises by 12.10%, or by the femur's mass increase. At the selected 243.5 mm body height, the same four-foot comparison gives a maximum shaft load of 0.39935 Nm versus 0.45839 Nm.

## Selected RL support poses

The selected geometric references use 80 mm stride, 40 mm commanded lift, 243.5 mm body height, and a 30 mm desired support-triangle inset. The comparison first places both mass models at exactly the earlier model's body and joint pose. It then replans the matched model's body position to restore the intended COM inset.

| Pose and model | Support margin | Maximum absolute shaft torque |
|---|---:|---:|
| RL support start, earlier mass | 30.000 mm | 1.02250 Nm |
| Same pose, matched CAD mass | 25.180 mm | 1.09864 Nm |
| Replanned support start, matched CAD mass | 30.000 mm | 1.13678 Nm |
| RL mid-swing, earlier mass | 30.000 mm | 0.98171 Nm |
| Same mid-swing pose, matched CAD mass | 25.035 mm | 1.04903 Nm |
| Replanned mid-swing, matched CAD mass | 30.000 mm | 1.08054 Nm |

The maximum in these sampled three-foot poses is the RR hip shaft. At the earlier support-start pose, the matched model's COM moves **5.497 mm laterally** within the body frame, cutting support margin by 4.820 mm. Recovering the intended 30 mm inset changes body Y from **−42.616 to −53.184 mm**, requiring approximately **10.6 mm more lateral shift**. At mid-swing, the corresponding extra lateral shift is approximately 11.2 mm.

This illustrates three separate changes relevant to control: a different response of whole-robot COM to body movement, larger yaw inertia/cross-coupling, and altered gravity/contact moments. Static peaks remain below the assumed 1.33493 Nm actuator peak in these few poses, but this does not establish adequate peak margin during acceleration or adequate continuous RMS over a gait.

## Scope

The calculations use level-body poses, vertical ground reactions, zero acceleration and locked wheel rotation. There are no horizontal friction forces, impacts, backlash engagement, thermal dynamics or controller-saturation dynamics here. All force solutions have nonnegative normal reactions. The full tensor and parallel-axis treatment is used for inertia; only gravity and contact moments enter the static torque calculation.

The matched mass input itself remains an estimate based on solid printed volume, purchased-part envelopes and stated allowances. Collision links remain simplified primitives. The separate matched-CAD physics runs, including their clearance, drift, saturation and support failures, remain the evidence for actual simulated motion. This static analysis explains why transferring the earlier controller result by total weight alone is insufficient; it does not attribute the dynamic failure to inertia alone or turn any failed run into a pass.
