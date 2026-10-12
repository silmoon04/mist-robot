# MIST engineering simulation

The current candidate rolls and changes height in this model. It does **not** pass the stair tests. The baseline 2:1 hip drive also misses the minimum foot clearance during a slow crawl. A 3.5:1 hip variant improves clearance and load response, but its physical transmission, usable servo travel, temperature and accuracy still need bench verification.

The shared [parameters.json](parameters.json) is the geometry and assumption contract. It uses 140/130 mm links, 85 mm wheels, three proximal STS3215 servos per leg, and a conditional DFRobot FIT0493 wheel motor. The total is **3.95376294555 kg**. Shell and face-frame masses use the new CAD's solid PETG volume; they have not been weighed or confirmed by a slicer. Both phones are included. Other component masses remain estimates.

## Executed results

All results below use the same final CAD mass and COM, 9.9 V assumed loaded rail, 1 ms physics steps, and 100 contact-solver iterations. `PASS_IN_MODEL` means the listed case criteria passed under these inputs. It does not establish manufactured-robot performance.

| Test | Recorded result | Implication |
|---|---|---|
| Baseline stand, 8 s | Pass; maximum tilt 0.192 degrees, joint RMS error 2.63 degrees | Holds the estimated mass, settling about 6.82 mm below the commanded height |
| Fixed-base single-leg swing | Pass; joint RMS error 0.86 degrees | Tests unloaded movement with the body supported |
| Body-height adjustment | Pass; joint RMS error 2.73 degrees | Tracks a slow plus/minus 25 mm height command |
| Aligned-wheel drive, 8 s | Pass; 5.235 m forward, 26.0 mm lateral drift, maximum tilt 0.425 degrees | Uses a 0.9 m/s command after a two-second ramp; motor curve and tire grip remain assumptions |
| Baseline crawl, 26 s | **Fail**; front-left wheel clears only 12.80 mm against a 15 mm requirement | All four legs cycle and the robot moves 31.1 mm, but commanded lift is not achieved reliably |
| Hip 3.5:1 crawl variant, 26 s | Pass; actual clearance 30.36–36.60 mm, maximum tilt 2.29 degrees | Moves only 34.4 mm with 18.3 mm lateral drift. This is a slow gait experiment, not fast or accurate walking |
| 180 mm step ascent | **Fail**; maximum tilt 100.48 degrees | Raising the body 47.5 mm before lifting does not make the scripted transition stable |
| 180 mm step descent | **Fail**; unreachable targets, non-wheel support and excessive sustained motor load | Does not complete the edge traversal |
| Obstacle stop | Pass; minimum wheel-to-wall gap 177.6 mm, zero obstacle contacts | Uses the world's exact distance as an ideal range-sensor surrogate; no perception or avoidance planner was tested |

Each case folder in [outputs](outputs) contains `report.json`, `parameters_used.json`, `trajectory.json` and `scene.json`. Reports include source and parameter SHA-256 hashes. [outputs/summary.json](outputs/summary.json) aggregates the eight final cases. The earlier 3.884 kg runs are preserved in [outputs_baseline_preCAD](outputs_baseline_preCAD), and their variants in [variants_baseline_preCAD](variants_baseline_preCAD). Do not mix those numbers with the final mass.

[variants/hip_3p5](variants/hip_3p5) repeats crawl and drive with ratios 2/3.5/2. [variants/adverse](variants/adverse) repeats drive with 60 ms delay, slower response, twice the assumed servo backlash, half transmission stiffness and friction coefficient 0.35. That run stays upright, but it has higher tracking error and contact loads. It covers one sensitivity case, not the uncertainty space.

The supported-body [load tests](load_tests/summary.json) apply an external vertical force to one suspended wheel. At 12.93 N, the 2:1 hip holds with 9.55 mm endpoint error and its hip RMS torque is only just below the assumed continuous allowance. At 29.09 N, it reaches the torque cap and yields by 148 mm. A 3.5:1 hip reduces that error to 15.86 mm, but fails the sustained-load acceptance criteria. This force is held for seconds; it should not be presented as a permitted short peak or a validated gait.

## Geometry and transmission

World coordinates are +X forward, +Y left and +Z up. The `base_link` origin is the hip yaw mount plane, **35 mm above the body bottom**. COM coordinates use this origin. The cylinder is 220 mm high; lid and handle bring the body assembly to 260 mm overall.

The four mounts lie at radius 103 mm and azimuths +45, -45, +135 and -135 degrees. Each leg has yaw about +Z, then hip and knee rotation about local -Y. A 35 mm radial offset and a mirrored 30 mm transverse carriage offset produce about 206 mm wheel track when the wheel planes face forward. The offset must exist mechanically. Changing a simulated stance parameter cannot supply lateral track while the real wheel planes remain constrained elsewhere.

For separate proximal reductions followed by a 1:1 belt along the femur:

```text
s = [ry*qyaw, rh*qhip, rk*(qhip+qknee)]
tau_motor = [tau_yaw/ry, (tau_hip-tau_knee)/rh, tau_knee/rk] / efficiency
```

The remote knee motor drives the absolute tibia angle. Sizing the proximal hip from `tau_hip/rh` alone underestimates its load. If reduction instead comes from unequal pulleys along the moving femur, the equation changes to `s_knee=qhip+N*qknee`. The analytic model compares both arrangements.

The simulated motor travel is measured **relative to a calibrated shaft position at the neutral pose**, not relative to the mathematical zero of `A*q`. Neutral hip is 58.0615 degrees and knee is -84.9565 degrees. With a 350-degree usable motor span, 3.5:1 gives only 100 degrees of hip travel, approximately 8.06 to 108.06 degrees when centered there. The stair endpoint screen needs about 111.84 degrees. Re-centering around an 80-degree hip could cover roughly 30 to 130 degrees, but that is a different commissioning range, and it has not been used to claim stair success. No raw hardware ticks are generated here.

## Analytic sizing

[analytic/results_final_cad/REPORT.md](analytic/results_final_cad/REPORT.md) and its CSV files contain the final **9,000-case** ratio, mass and link-length sweep. [analytic/results](analytic/results) retains the earlier mass snapshot.

At 9.9 V, 140/130 mm links and the current mass, no tested combination with every reduction at or below 3:1 meets all sampled peak loads. The best corresponding mass boundary is about **3.581 kg**, with no extra design margin. The 110/70 mm geometry has better torque margins but no feasible paired stair endpoints in the sampled household-step screen. The 160/150 mm geometry improves reach while increasing torque demand.

The 140/130 mm leg can reach selected upper and lower endpoints for a 180 mm rise only after changing body height and approaching its travel limits. Reach alone does not establish a stable, collision-free step. The rigid-body runs retain those failures.

The nominal backlash sensitivity is about **2.32 mm** at the wheel, before tracking error, print tolerances and structural flex. The assumed elastic transmission term adds about 4 mm under the high-load case. These calculations use unmeasured backlash and stiffness. They are values to replace after the coupon and leg-rig tests, not a prediction of manufactured accuracy.

## What is modeled

`model.py` generates [generated/mist_candidate.urdf](generated/mist_candidate.urdf) from the shared parameters. Four articulated legs, gravity, mass/inertia, cylindrical wheel contact, friction, wheel motor torque/speed/current caps, self collision outside selected adjacent pairs, and reaction forces run in PyBullet. Servo torques are applied each step through `TORQUE_CONTROL`; the robot base is free except in explicitly labeled fixture tests. Contact checks reject non-wheel support. Support-polygon checks use loaded contacts with upward-facing normals, so a wall cannot silently become a floor contact.

The actuator approximation includes sampled commands, latency, a speed limit, response filtering, deadband, command-reversal play, reduced stiffness for transmission compliance, friction, voltage scaling, peak limits and continuous RMS checks. The series-stiffness and command-play approximation **does not model load-side backlash gap engagement under an external force reversal**. There is no separately integrated belt elastic mode or identified rotor/reflected-gearbox inertia.

The current URDF uses simple boxes and cylinders. It is not a collision mesh exported from the final Fusion assembly. Beam flexibility, layer-direction strength, insert pull-out, belt tooth load, fatigue, bearing contact, wiring, thermal saturation, tire deformation and stair noses are outside this rigid model. Use the mechanical review and coupon tests for those gates. All readings of actual servo performance, material properties and floor grip still need hardware measurements.

The earlier browser simulator already contains useful statics and Rapier contacts. Its wheel colliders are spheres and robot-to-robot contacts are disabled globally in that layer. Those choices weaken wheel-heading and assembly-clearance checks. The new simulator is an additional engineering test runner; it does not overwrite the existing browser simulator or its evidence.

## Reproduce

An isolated Python 3.12 environment is installed at `.venv`. PyBullet 3.2.7 was compiled successfully on this Windows machine. From this directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest test_simulation -v
.\.venv\Scripts\python.exe -m unittest discover -s analytic -p 'test_*.py'
.\.venv\Scripts\python.exe analytic/analytic.py --output analytic/results_final_cad
.\.venv\Scripts\python.exe run_sim.py --case all
.\.venv\Scripts\python.exe refresh_summary.py
.\.venv\Scripts\python.exe run_variants.py
.\.venv\Scripts\python.exe load_test.py
```

There are six integration/mechanics tests and nine analytic tests. They verify URDF versus analytic FK, IK, mass reconciliation, all four drive headings, base-link versus inertial-frame conversion, virtual work, torque caps, command delay, support polygons, gravity and error calculations. They do not assert that the robot passes a movement scenario.

To create an environment elsewhere, use Python 3.12, `python -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. Windows may need a C++ compiler to build PyBullet. Once installed, the runs are offline and use no hardware or network interfaces.

The replay format is `trajectory.json` with `joint_names` and `frames`. Each frame includes seconds `t`, `base_position`, `base_quaternion_xyzw`, the 16 joint coordinates `q`, 12 desired leg coordinates `target_q`, contact forces, COM, tilt and slip. `base_position` is the URDF base-link frame. `scene.json` contains exact world boxes as `{name, size, position, quaternion_xyzw}`. A pose replay should load these boxes to show the step or obstacle correctly.

The [PyBullet quickstart guide](https://raw.githubusercontent.com/bulletphysics/bullet3/master/docs/pybullet_quickstartguide.pdf) documents torque-control semantics and the need for accurate mass/inertia and identification. Motor inputs and current limits are traceable through the [wheel study](../wheel_motor_study.md), the [Feetech C018 manufacturer specification](https://cdn.robotshop.com/media/F/Fit/RB-Fit-155/pdf/feetech_12v_30kg_cm_magnetic_encoding_servo_sts321_specification_pdf.pdf), and the [DFRobot manufacturer-linked motor drawing](https://raw.githubusercontent.com/Arduinolibrary/DFRobot_12V_DC_Motor_350RPM_with_Encoder/master/Dimension.png). Electrical endpoints are supplier data; the linear curve, derating, control behavior and friction are engineering assumptions.
