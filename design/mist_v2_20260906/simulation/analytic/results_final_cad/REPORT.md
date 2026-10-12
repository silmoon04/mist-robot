# MIST leg engineering screen

These results size a candidate mechanism. They do not establish that a robot can climb stairs or sustain the calculated loads.

The shared mass estimate totals **3.954 kg**, including both phones and four wheel motors. The selected 140/130 mm leg has nominal hip and knee angles 58.06 and -84.96 degrees.

For the preferred proximal reduction and 1:1 remote belt, motor angles are `u = [ry*yaw, rh*hip, rk*(hip+knee)]`. Virtual work gives `tau_motor = [tau_yaw/ry, (tau_hip-tau_knee)/rh, tau_knee/rk]` before losses. An unequal remote pulley instead gives `u_k=hip+rk*knee`, and changes the proximal torque subtraction to `tau_hip-tau_knee/rk`. These equations must match the actual belt routing.

## Shared nominal posture at 2:1

The following rows include moving-leg gravity and vertical support force. Utilization greater than 1 exceeds the stated sizing allowance. Speed is a local upper estimate, even where the continuous limit fails.

| Supply | Load case | Hip motor Nm | Knee motor Nm | Continuous utilization | Peak utilization | Radial speed m/s |
|---|---|---:|---:|---:|---:|---:|
| 9.9 V | four_static | 0.475 | 0.259 | 0.65 | 0.36 | 0.265 |
| 9.9 V | crawl_three_static | 0.701 | 0.371 | 0.96 | 0.53 | 0.251 |
| 9.9 V | pair_static | 1.153 | 0.594 | 1.58 | 0.86 | 0.224 |
| 9.9 V | pair_dynamic_1p5 | 1.831 | 0.930 | 2.51 | 1.37 | 0.147 |
| 9.9 V | single_dynamic_1p5 | 3.864 | 1.936 | 5.31 | 2.89 | 0.000 |
| 12.0 V | four_static | 0.475 | 0.259 | 0.54 | 0.29 | 0.328 |
| 12.0 V | crawl_three_static | 0.701 | 0.371 | 0.79 | 0.43 | 0.314 |
| 12.0 V | pair_static | 1.153 | 0.594 | 1.31 | 0.71 | 0.287 |
| 12.0 V | pair_dynamic_1p5 | 1.831 | 0.930 | 2.07 | 1.13 | 0.246 |
| 12.0 V | single_dynamic_1p5 | 3.864 | 1.936 | 4.38 | 2.39 | 0.000 |

## Ratio and length trade

The sweep checks three normalized postures, three-contact static support, and two-contact support with a 1.5 normal-force multiplier and off-axis loading. Reductions span 1:1 to 3:1 independently on all three channels. A passing row covers those samples only. Shorter links in this comparison have lower body clearance.

| Links mm | Supply | Ratios yaw/hip/knee | Sampled load pass | Peak utilization | Crawl continuous utilization | Minimum radial speed m/s |
|---|---|---|---|---:|---:|---:|
| 110/70 | 9.9 V | 1.5/3/1.5 | True | 0.88 | 0.59 | 0.120 |
| 110/70 | 12.0 V | 1/2.5/1 | True | 0.96 | 0.59 | 0.180 |
| 140/130 | 9.9 V | 1.5/3/2 | False | 1.12 | 0.75 | 0.136 |
| 140/130 | 12.0 V | 1.5/3/1.5 | True | 0.94 | 0.62 | 0.201 |
| 160/150 | 9.9 V | 1.5/3/2 | False | 1.28 | 0.86 | 0.135 |
| 160/150 | 12.0 V | 1.5/3/2 | False | 1.05 | 0.71 | 0.198 |

For 140/130 mm links at 9.9 V, the selected best torque case within this sweep reaches its modeled peak allowance at 3.581 kg. That is a boundary with no extra margin. Reducing body mass changes this limit while the model holds moving-link masses fixed. The current estimated mass exceeds it. The CSV includes each ratio's exact mass envelope.

## Stair geometry and error budget

The stair screen assumes 180 mm rise, 270 mm tread, and the shared wheel radius. It searches hip heights from 120 to 320 mm above the lower floor and pitch-axis reaches from 40 to 150 mm. A pair of reachable endpoints says nothing about tread placement or stability.

- 110/70 mm: 0 of 246 sampled pairs reach both heights within joint and servo travel, and 0 also allow the requested toe clearance at the same radial coordinate.
- 140/130 mm: 25 of 246 sampled pairs reach both heights within joint and servo travel, and 11 also allow the requested toe clearance at the same radial coordinate.
- 160/150 mm: 49 of 246 sampled pairs reach both heights within joint and servo travel, and 31 also allow the requested toe clearance at the same radial coordinate.

At the nominal pose, the backlash-only corner bound is 2.32 mm. Shared full-width servo backlash is divided by the external reduction, then combined with downstream backlash at its own output. The assumed stiffness adds 4.05 mm of load-dependent endpoint deflection in the two-contact dynamic load case. These are separate terms; fabrication error, bearing clearance, belt tension, printed part flex, deadband and tracking error are not included in the backlash number.

A yaw axis about vertical has zero torque from a purely vertical endpoint force. Tangential contact force, steering scrub, drive reaction and inertia create yaw demand. The nominal CSV includes an off-axis load case so yaw is not sized from gravity alone.

## Limits and next measurements

- Total mass includes both phones and all four complete leg mass estimates.
- Sweep masses change body payload while moving-link masses stay fixed; no CAD mass prediction.
- Foot support uses equal load sharing then stated dynamic multiplier. Link gravity is subtracted once because total mass already includes it.
- Sweep checks all four sign combinations of radial and tangential force, each 25% normal. Nominal CSV shows positive forces only. Unequal COM sharing requires contact dynamics.
- Linear voltage and torque-speed scaling, efficiency, backlash, stiffness, continuous/peak ratings and controller response are unmeasured.
- The speed estimate is a local kinematic upper bound at a fixed force. It omits acceleration, reflected servo inertia, control lag, drive/brake reaction moments and impact.
- Stair screen only checks paired endpoint inverse kinematics and motor travel. It does not check a continuous collision-free path, body clearance, tread placement, tipping, stair edge contact, or actuator loads during traversal.
- Workspace extrema contain geometrically reachable samples which may collide with body or another leg.
- Motor span is centered at a calibrated home, per shared parameters; whole joint box cannot be obtained at arbitrary high ratios in single-turn position mode.

Measure loaded servo speed, temperature and current over the intended duty cycle; full reversal backlash; force-versus-deflection of the complete leg; actual component masses; wheel traction and motor current; physical travel and body interference. Re-run the shared parameter file after the coupon and bench measurements.

Reproduce with `python analytic.py`; run `python -m unittest discover -s . -p 'test_*.py'` from this directory. The CSV files preserve every load case and sweep row. `summary.json` records the exact shared parameter SHA-256.
