# Supported crawl experiments

The later fitted 7.108 kg mass/inertia input changes the conclusion: the former fast controller fails clearance/drift, while a slower fallback passes aggregate criteria with transient two-wheel support. Read [the matched CAD report](MATCHED_CAD_REPORT.md) for the current fitted-input result. The initial 6.341 kg study below remains useful sensitivity evidence and must not be presented as validation of the fitted assembly.

The initial contact-dynamics study for the proposed femur-mounted knee motor uses the same 6.341 kg sensitivity mass as the earlier CAD reconciliation. Its knee motor COM remains (0, 0, −40) mm in the femur frame. The fitted cartridge's lateral COM offset is covered by the separate matched mass/inertia runs above; the initial results below do not validate that CAD.

The fastest passing repeated candidate currently saved is `stride80_force_feedback_3s_3cycles`: 80 mm stride, three seconds per leg, order RL → FL → RR → FR, nominal body mount-plane height 243.5 mm, 40 mm commanded lift and a 30 mm planned support-COM inset. The 243.5 mm value includes the loader's initial 1 mm ground clearance plus a 10 mm commanded raise; it is 1 mm above the earlier analytic screen's 242.5 mm body height. Its report checks every swing, every landing and phase-matched cycle progress. The body advances 237.35 mm in 39.50 s, or 6.01 mm/s including settling, and finishes 1.34 mm sideways from its starting line. Peak tilt is 1.75° and the worst individual servo's RMS torque is 0.663 Nm, below the unchanged 0.728 Nm assumption. All sampled states have at least three loaded wheel contacts, the minimum sampled support margin is 18.23 mm, and the smallest peak clearance among the 12 swings is 26.65 mm. Matching cycle-to-cycle advances are 82.37 and 82.63 mm. It is still a slow crawl. The earlier 25.8 mm / 26 s sensitivity was approximately 0.99 mm/s. This is a controller comparison, not a measured hardware speedup.

`supported_60mm_4s_3cycles` is the slower reference without vertical contact-load correction. It advances 183.97 mm in 51.52 s, with 0.27 mm final lateral error and 0.617 Nm maximum individual shaft RMS. During the first cycle it briefly recovers from two-wheel support; that episode is retained in the report (minimum sampled support margin −17.9 mm). A passing 95% contact-coverage criterion does not mean continuously positive quasistatic support.

The earlier 60 mm, three-second candidate (`force_feedback_60mm_3s_3cycles`) has brief two-contact transients: 0.579% of post-settle samples have fewer than three loaded wheels, 0.842% have a negative sampled support margin, and the minimum is −79.9 mm during a body shift. It recovers with small measured tilt in this model. This result satisfies the stated contact-coverage criterion, but is not continuously supported. The selected 80 mm run removes those sampled transients for its tested trajectory; the difference should not be generalized to untested speeds or terrain.

The selected 80 mm three-cycle controller passes the combined sensitivity with tire friction reduced from 0.75 to 0.60 and servo command delay increased from 25 to 40 ms. It advances 239.14 mm in 39.50 s, ends 1.93 mm sideways, peaks at 1.83° tilt and reaches 0.661 Nm worst shaft RMS. This is one combined perturbation, not an exhaustive robustness test or identification of hardware parameters. The earlier 60 mm controller also passes that combined perturbation.

Doubling both assumed servo gearbox backlash and external output backlash on top of that lower-grip/longer-delay input fails. The robot still completes all 12 swings and advances 230.56 mm, but worst shaft RMS rises to 0.735 Nm above the 0.728 Nm assumption and at least one swing misses the 15 mm clearance requirement. The file is `stride80_sensitivity_double_backlash/report.json`. This predicted failure makes loaded reversal/play measurement a necessary next step. The command-play model remains an approximation; it does not prove that a printed transmission will exhibit the same threshold.

The bounded faster screen tested 2.5, 2.0, 1.2 and 0.8 seconds per leg at 60 mm stride. Faster motion remained upright but failed one or more clearance, contact-coverage or lateral-drift limits. The 1.2-second case produced the highest measured forward rate in that initial screen, 7.74 mm/s, while failing clearance and contact criteria. Increasing feedback gain also failed. An additional 100 mm stride at three seconds per leg fails continuous RMS torque (0.791 Nm against 0.728 Nm) despite satisfying the other one-cycle criteria. These failures set the tested frontier; they do not prove that another controller cannot walk faster.

## What the controller changes

Three stance-wheel targets remain fixed in world coordinates. Before each swing, a kinematic plan places the whole robot COM inside the remaining support triangle and accounts for moving limb mass. It keeps that support COM through the swing and interpolates toward the next support pose after touchdown. Bounded position/attitude feedback tracks the plan. Contact gates pause before unloading when the measured COM is outside the requested support margin, and wait for the landing wheel's measured normal force.

Wheel braking compensates tibia pitch and small body roll/pitch. Holding only wheel-joint angle relative to the tibia rolls the wheel as the leg pitches. The new compensation holds its orientation in the world to first order. This is one change among several; the speed comparison does not isolate its contribution.

The faster candidate also computes the three expected vertical support loads. Measured force error changes each stance axle's commanded height through a 0.1 s filter, capped at ±6 mm. It remains a position command through the existing actuator model, not an applied external force.

All joint torques pass through the existing `ActuatorBank`: unchanged voltage, torque-speed envelope, command delay, rate limit, command-play approximation, compliance and efficiency. The servo peak cap remains 1.335 Nm and continuous RMS assumption 0.728 Nm. Each wheel uses the existing 1 A current assumption, which produces a 0.17355 Nm torque cap at the simulated voltage. No base reset, external force, fixed support constraint or torque increase is used after initial placement.

## Evidence and checks

Each completed run has its parameters, controller settings, source snapshots and hashes, URDF, scene and 50 Hz trajectory. Later runs also include all 1000 Hz servo torques in `servo_torques_1000hz.npz`. State, wheel clearance, contact forces and body pose are sampled after the same physics step in the corrected reports. The run's own archived source is the exact implementation used; current scripts may be newer.

Success requires all planned leg steps, each swing clearing at least 15 mm and unloading, every landing showing normal force, no invalid IK requests or shaft travel violations, no coarse self-collision or nonwheel support, tilt below 10°, joint tracking RMS below 8°, individual motor RMS below its assumed limit, at least 80% planned forward displacement, final lateral error under 10 mm, at least 95% three-contact samples and subsequent full cycles advancing at least 60% stride at matching gait phases. Early fall/body-contact termination remains a failure. These are stated simulation acceptance criteria, not product safety or manufacturing certification.

The raw `selected_60mm_4s_3cycles` report contains a discovered metric error: it compares a neutral initial body pose to a shifted support pose at the end of the first four-leg sequence. It therefore reports a false cycle-distance failure. That report is preserved. The corrected `supported_60mm_4s_3cycles` run compares matching phase boundaries and verifies each swing/landing independently. The old `faster_60mm_3p5s_3cycles` run also fails its final lateral-drift limit, so fixing the metric alone would not turn it into a pass.

Independent COM verification is in `geometry_study/link_com_verification.json`. It exposed the missing local inertial rotation in `base_link_pose` before actual CAD inertia tensors were used. Root fixed the shared implementation. Original diagonal-inertia runs remain valid; later CAD runs must select a new frozen runtime with that correction and the exact per-link COM helper.

## Limits

The controller receives ideal body pose, joint position and contact forces directly from the simulator. On the robot, IMU attitude, wheel/servo odometry, contact/load estimation and localization need implementation and error testing. The model uses coarse collision boxes/cylinders rather than the final printable assembly. There is no stair nose, tread deformation, cable collision or structural stress model in these experiments.

Servo bandwidth, command hysteresis, stiffness, friction and thermal duty are unmeasured assumptions. The backlash approximation has no independent load-side gap engagement, separate rotor inertia or belt vibration modes. Whole-run RMS torque is a screening measure, not a winding/driver temperature prediction. Wheel orientation compensation is only justified in the small-tilt regime tested. Off-axis wheel COM planning uses a nominal wheel angle unless an explicit wheel angle is supplied to the analytic helper.

No stair performance, hardware reliability or print release follows from these results. Re-run the selected controller with fitted mass/inertia and collision geometry, then identify servo reversal behavior, temperature/current duty, contact sensing and tire grip on the physical first leg.

## Saved runs

| Run | Mass kg | Cycles | mm/s | Forward mm | Lateral mm | Tilt ° | Shaft RMS Nm | <3 contacts % | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| [com30_40mm_3s](com30_40mm_3s/report.json) | 6.341 | 1 | 2.83 | 43.9 | 6.68 | 5.52 | 0.649 | 6.86 | Fail |
| [com30_60mm_4s](com30_60mm_4s/report.json) | 6.341 | 1 | 3.07 | 59.9 | 1.17 | 5.33 | 0.684 | 0.78 | Pass |
| [faster_60mm_3p5s_3cycles](faster_60mm_3p5s_3cycles/report.json) | 6.341 | 3 | 3.99 | 181.6 | 10.36 | 7.43 | 0.653 | 2.27 | Fail |
| [force_feedback_60mm_2p5s](force_feedback_60mm_2p5s/report.json) | 6.341 | 1 | 4.07 | 55.0 | -12.33 | 3.24 | 0.699 | 4.49 | Fail |
| [force_feedback_60mm_2p5s_posegain1](force_feedback_60mm_2p5s_posegain1/report.json) | 6.341 | 1 | 5.72 | 77.8 | -52.24 | 9.51 | 0.715 | 20.46 | Fail |
| [force_feedback_60mm_2s](force_feedback_60mm_2s/report.json) | 6.341 | 1 | 4.31 | 49.8 | 1.59 | 5.67 | 0.626 | 1.79 | Fail |
| [force_feedback_60mm_2s_lift50](force_feedback_60mm_2s_lift50/report.json) | 6.341 | 1 | 5.31 | 61.2 | -5.74 | 8.76 | 0.642 | 4.38 | Fail |
| [force_feedback_60mm_3s](force_feedback_60mm_3s/report.json) | 6.341 | 1 | 3.54 | 54.9 | 0.46 | 1.22 | 0.706 | 0.00 | Pass |
| [force_feedback_60mm_3s_3cycles](force_feedback_60mm_3s_3cycles/report.json) | 6.341 | 3 | 4.60 | 181.9 | -0.76 | 3.68 | 0.634 | 0.58 | Pass |
| [frontier_60mm_0p8s](frontier_60mm_0p8s/report.json) | 6.341 | 1 | 5.60 | 40.2 | -4.64 | 6.06 | 0.673 | 11.58 | Fail |
| [frontier_60mm_1p2s](frontier_60mm_1p2s/report.json) | 6.341 | 1 | 7.74 | 65.5 | 9.68 | 6.86 | 0.663 | 12.61 | Fail |
| [frontier_60mm_2s](frontier_60mm_2s/report.json) | 6.341 | 1 | 5.01 | 58.2 | -13.45 | 5.48 | 0.670 | 10.85 | Fail |
| [initial_40mm_3s](initial_40mm_3s/report.json) | 6.341 | 1 | 2.81 | 43.5 | 2.25 | 8.55 | 0.699 | 8.29 | Fail |
| [matched_cad_60mm_4s_3cycles](matched_cad_60mm_4s_3cycles/report.json) | 7.108 | 3 | 3.27 | 168.6 | -0.72 | 4.11 | 0.680 | 1.28 | Pass |
| [matched_cad_80mm_3s_3cycles](matched_cad_80mm_3s_3cycles/report.json) | 7.108 | 3 | 6.06 | 239.5 | 11.85 | 6.76 | 0.708 | 0.84 | Fail |
| [selected_60mm_4s_3cycles](selected_60mm_4s_3cycles/report.json) | 6.341 | 3 | 3.58 | 184.2 | -0.08 | 5.33 | 0.617 | 0.28 | Fail |
| [sensitivity_60mm_3s_grip060_delay040](sensitivity_60mm_3s_grip060_delay040/report.json) | 6.341 | 3 | 4.48 | 177.0 | -1.36 | 3.57 | 0.680 | 0.16 | Pass |
| [stride100_force_feedback_3s](stride100_force_feedback_3s/report.json) | 6.341 | 1 | 6.41 | 99.6 | 1.37 | 6.99 | 0.791 | 0.00 | Fail |
| [stride80_force_feedback_3s](stride80_force_feedback_3s/report.json) | 6.341 | 1 | 4.39 | 68.2 | 2.37 | 1.75 | 0.708 | 0.00 | Pass |
| [stride80_force_feedback_3s_3cycles](stride80_force_feedback_3s_3cycles/report.json) | 6.341 | 3 | 6.01 | 237.4 | -1.34 | 1.75 | 0.663 | 0.00 | Pass |
| [stride80_sensitivity_3s_grip060_delay040](stride80_sensitivity_3s_grip060_delay040/report.json) | 6.341 | 3 | 6.05 | 239.1 | -1.93 | 1.83 | 0.661 | 0.00 | Pass |
| [stride80_sensitivity_double_backlash](stride80_sensitivity_double_backlash/report.json) | 6.341 | 3 | 5.84 | 230.6 | -1.06 | 7.49 | 0.735 | 0.00 | Fail |
| [supported_60mm_4s_3cycles](supported_60mm_4s_3cycles/report.json) | 6.341 | 3 | 3.57 | 184.0 | -0.27 | 5.33 | 0.617 | 0.28 | Pass |
| [wider_shift_40mm_3s](wider_shift_40mm_3s/report.json) | 6.341 | 1 | 1.79 | 27.8 | 0.50 | 5.27 | 0.649 | 9.29 | Fail |

Earlier rows use less complete metrics. Check `verified_per_swing_metrics` and `failed_criteria` in summary.json when comparing generations. Raw results are not rewritten.
