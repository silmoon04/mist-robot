# Crawl geometry and gravity balance

This is a kinematic and quasistatic screen of the existing 6.341 kg proximal-femur knee sensitivity model. It does not run contact physics, change actuator limits, establish CAD clearance, or claim a walking robot.

The neutral wheel axles are at `(±167.832, ±102.832, −190)` mm in the body frame. Joint angles are hip 58.043° and knee −84.717°, with the existing ±45° yaw angles. The model's complete robot COM is `(1.309, 0.0006, −29.203)` mm in that frame. At a body mount-plane height of 232.5 mm, its COM is 203.3 mm above the floor.

Removing either front wheel from support gives a neutral support margin of **−0.684 mm**. Removing a rear wheel gives only **+0.684 mm**. The three-foot triangle therefore needs a deliberate COM shift before lifting. These values treat wheel contacts as points on a flat floor and body orientation as level.

The screen holds stance wheel targets in world coordinates, projects a nominal forward COM target into an inset support triangle, and solves the body translation with the moving-link COM included. A 30 mm COM margin needs a larger body translation because planted limb mass counteracts body movement. During each swing, the desired COM remains fixed inside the same triangle. Body XY is adjusted slightly to account for the lifted leg's moving mass.

All 36 sampled geometry combinations were reachable: 20/40/60 mm stride, 20/30 mm COM inset, 222.5/232.5/242.5 mm body height, and two orders. Reachability alone does not establish enough actuator torque. For example, the 60 mm stride, 20 mm inset, 222.5 mm height, RL–FL–RR–FR combination requires a 1.371 Nm static shaft peak, above the model's assumed 1.335 Nm peak limit.

The selected **bounded physics candidate** is 40 mm stride, 35 mm commanded swing clearance, 30 mm desired COM inset, 242.5 mm body height, and order RL → FL → RR → FR. Its analytically required peak shaft torque is 1.121 Nm. The worst individual shaft's RMS across uniformly sampled swing phases is 0.671 Nm, compared with the unchanged 0.728 Nm continuous assumption. This RMS excludes the four-foot shift phases, dynamic acceleration, friction and compliance. It is not the complete-cycle thermal result.

| Body height | COM inset | Largest shaft peak | Largest individual swing RMS |
|---|---:|---:|---:|
| 232.5 mm | 20 mm | 1.133 Nm | 0.776 Nm |
| 232.5 mm | 30 mm | 1.117 Nm | 0.691 Nm |
| 242.5 mm | 20 mm | 1.059 Nm | 0.721 Nm |
| 242.5 mm | 30 mm | 1.121 Nm | 0.671 Nm |

The selected candidate's joint range is yaw −70.66° to +79.49°, hip 46.40° to 74.06°, knee −94.46° to −58.62°. Maximum shaft travel relative to the existing neutral is 69.12°. These are sampled geometric ranges, not CAD collision checks.

`selected_reference_knots.json` contains 41 swing knots per leg, including world feet, desired body XYZ and joint angles. Start with all four feet on the floor, shift through a smooth four-foot stance to the first knot's body position, swing while the three stance targets remain fixed, confirm touchdown, then shift to the next support triangle. After the fourth touchdown, recenter the body at `(40, 0, 242.5)` mm. The initial desired swing-start body positions are:

| Active leg | Body X | Body Y | Body Z |
|---|---:|---:|---:|
| RL | 20.045 mm | −42.657 mm | 242.5 mm |
| FL | −9.407 mm | −36.300 mm | 242.5 mm |
| RR | 42.425 mm | 41.046 mm | 242.5 mm |
| FR | 12.759 mm | 38.512 mm | 242.5 mm |

These are world reference coordinates including accumulated forward motion. They are not measured body poses and must not be applied by resetting the physics base. The controller must create the motion through its existing bounded joint actuators and wheel brakes.

A conservative first timing is 2 seconds for each four-foot shift, 2 seconds for each swing, and up to 0.5 seconds for contact settling. This is around 18 seconds per four-leg cycle before initial/final settling. It is a stability test, not a high-speed walking claim. Shortening these phases should be a separate controlled experiment after contact, clearance and per-actuator load criteria pass.

Useful physics criteria include a completed four-leg sequence with every wheel actually clearing 15 mm; at least three real wheel contacts during swing; no non-wheel support; positive measured support margin with a useful 5 mm margin target; less than 10° tilt; no unreachable targets or motor travel violations; every individual actuator's complete-cycle RMS below its unchanged continuous limit; and actual forward body travel of at least 25 mm per commanded 40 mm cycle, with lateral drift below 10 mm and heading drift below 3°. Report transient minimum support margin as well as any fraction meeting the target. A timeout, failed unloading or failed touchdown must remain a failure rather than silently advancing the phase.

`geometry_study.py` exports callable helpers:

- `com(p, q, wheel_angles=None)`: complete robot COM in body coordinates. When `link_mass_properties` is present, all 17 explicit link masses and local COM vectors are transformed through the joint frames. Without that override, the original component mass approximation is retained. Supply wheel angles separately or as the fourth column of `q` when an off-axis wheel COM must rotate; the usual 4×3 planning input assumes zero wheel angles.
- `closest_inset(points, nominal_xy, inset)`: nearest desired world COM inside the inset contact triangle.
- `body_for_com(p, feet_world, initial_body_xy, body_z, desired_com_xy)`: level body position and IK satisfying that COM target.
- `trial(...)`: full sampled geometry and vertical-force gravity balance.

The analytic vertical support reactions assume a flat floor, zero body angular acceleration and no horizontal contact force. Shaft gravity loads use the existing coupling matrix and efficiency. Yaw torque is zero in this ideal vertical-force screen; this does not imply that steering, lateral contact forces or a tilted body need no yaw torque. Actual feedback, backlash, torsional stiffness, contact friction, wheel rotation, dynamic load transfer and full printed geometry remain the physical controller and manufacturing review's responsibility. The JSON field `static_motor_rms_pooled_nm` pools all four motors on each axis and must not be used as an individual actuator's thermal pass criterion. The selected file includes individual values explicitly.

`verify_link_com.py` checks the helper against the frozen PyBullet URDF implementation. Six kinematic fixtures cover the original model and synthetic 17-link overrides with nonzero local COM offsets, nonzero wheel rotations and physically valid full inertia tensors. All analytic COM results agree within 0.019 micrometres; `link_com_verification.json` records the inputs, source hashes and results. These fixtures perform no simulation steps and are not robot mass estimates.

That validation also detects a separate limitation in the frozen `run_sim.base_link_pose`: it subtracts the local COM offset but omits local inertial-frame rotation. When PyBullet diagonalizes a full inertia tensor, the complete inverse inertial transform is needed to recover the URDF base-link pose. The synthetic fixture exposes 22.7–23.6 mm of resulting COM projection error. The existing diagonal-inertia crawl evidence is unaffected; a run using full CAD inertia tensors must use the corrected base transform before its attitude and foot-position feedback can be trusted. The validation script contains the full-transform reference implementation. This review did not edit shared `run_sim.py`.
