# All actuators inside the body: preliminary architecture

Status: mechanical study, not a CAD freeze or a build release. The concealed-shin revision is paused. Its saved source remains `cad/concealed_wheel_drive_20260907/concealed_leg.py`, SHA256 `a717b4e4ed3662e816ea590d721e46b66b9dbf48977d819d765eb56bc1a2607c`; its last FL report has 168 valid solids, 10 positive contacts and one kernel warning. No process owned by this task is still running that build.

**Keeping every actuator inside the body is possible in principle.** The question is how much mechanism must occupy the body and joint roots. Two interpretations remain under study: every motor housing rigidly fixed to the chassis, or a fully enclosed internal motor plate that turns with the first joint. Neither permits a motor on an exposed hip, knee, shin or wheel. The motor count remains twelve C018 positioning servos plus four continuous wheel motors.

| Option | Motor housings | Power channels crossing first joint | Mechanism and practical cost | Preliminary position |
|---|---|---:|---|---|
| A. Strict fixed motors, serial belt outputs | All sixteen fixed to chassis | Three independent downstream channels per leg | Three concentric feeds, passive right-angle pickups, and three hip-axis outputs; two femur belts and a wheel route through the knee. Load coupling is strong. | A real baseline, but the most demanding root transmission. |
| B. Strict fixed motors with physical spatial differential | All sixteen fixed to chassis | Differential handles first-axis/hip motion; independent knee and wheel feeds remain | Published three-DOF joint-drive precedent exists. Adds a genuine spatial differential and nested knee/wheel feeds. Axis signs and knee mapping must be taken from its actual gear topology. | Best strict-fixed mechanism to examine next; no claim that it fits this body. |
| C. Fully enclosed three-motor internal plate | First-axis servo fixed; H/K/wheel housings rotate on an internal first-joint plate | No motor-power feedthrough across first axis | All three downstream motors, their mounts, connectors and cables need a collision-free swept envelope inside the shell. Removes the complicated first-axis feedthrough. | Mechanically simpler if the user's internal-plate interpretation permits it and the full sweep fits. |
| D. Enclosed H/K plate, fixed wheel motor | First-axis and wheel motors fixed; H/K housings on internal plate | One continuous wheel-power channel | Two C018 housings and their differential fit the swept plate; the long FIT0493 can remain vertical and fixed. One concentric wheel shaft plus a bevel pickup crosses first axis. | Most useful compromise to package first while the interpretation is pending. |
| E. Coaxial five-bar leg plus wheel channel | Depends on first-axis arrangement | Still needs wheel and any out-of-plane feeds | Two base-driven upper links replace the serial planar chain. This changes kinematics, workspace and singularities; it does not by itself solve yaw/roll or wheel drive. | A separate leg redesign, not a shortcut or a direct replacement for three-DOF wheeled legs. |

The first axis can be yaw or roll, but that is a real behavior choice. Yaw controls conventional wheel heading. A roll-first leg can have upright, parallel wheel planes in its drive pose, but steering would require an explicit skid/differential-drive or other steering plan. Rolling the hip tilts the wheel; it is not equivalent to yaw steering. A fixed-motor spatial differential published for abduction/thigh motion is a precedent for roll-first architecture. Reorienting it for yaw requires a new mechanism and packaging check.

## Physical route for a serial belt leg

Let `y` be first-joint yaw, `h` hip pitch, `k` knee angle relative to femur and `w` wheel angle relative to tibia. Pitch and wheel axes remain parallel within the yaw frame. Let `betaH`, `betaK`, `betaW` denote the three independently driven hip-axis members, measured relative to that yaw frame.

1. `betaH = h` drives the femur through a supported hip trunnion.
2. `betaK = h+k` drives an equal-pulley open belt along the femur. Its distal pulley is attached to the tibia-driving knee member.
3. `betaW = h+k+w` drives a second, independent equal-pulley belt along the femur. At the knee it enters an independent wheel-drive member, then continues to the wheel.

For an open belt on a carrier at angle `c`, the exact ideal relation is `(thetaOut-c) = (rIn/rOut)*(thetaIn-c)`. Equal pulleys therefore give `thetaOut=thetaIn`. For two equal pulleys with fixed center distance `C`, pitch length is `2*C + 2*pi*r`; rotating the complete link changes neither `C` nor belt length. This is why joint-concentric transfer shafts matter. Moving a motor somewhere near a joint does not establish constant belt length.

The hip needs three independent angular outputs, but it need not have three long nested tubes. One short hip-driving trunnion can stop on one side; a separate knee tube and wheel core shaft can occupy the opposite side, with a real gap between the independent trunnions. That reduces nested depth to two. It still requires independent bearing seats, positive torque locks and axial retention. Two solid shafts must never be drawn through each other.

Bearing availability depends on the support topology. A provisional two-channel arrangement can use an 8 mm OD / 6 mm ID steel knee tube around a 5 mm wheel shaft, with the tube on 608 bearings and the core supported independently at axial stations beyond the tube ends. The recovered assortment lists 685 bearings (5 x 11 x 5 mm), not 625. A 685 cannot fit inside the tube's 6 mm bore, but it can support the protruding core outside the tube. That approach trades radial compactness for a longer axial stack and needs a real route to drive both members without colliding with the opposite hip trunnion.

For a 40 mm uniform tube at 2.75 Nm and assumed steel shear modulus77 GPa, polar moment is274.9 mm4, nominal torsional shear40.0 MPa and twist0.298 degrees. The 5 mm core at0.172 Nm twists0.083 degrees over the same length. These torsion-only values do not clear combined bending, fatigue, bearing fit or tube collapse. A cross-pin through the outer tube would obstruct the independently rotating inner shaft. A keyway through a 1 mm wall is also not a valid torque lock. External clamping, shallow flats, splines or bonded/brazed flanges need a measured design that retains circular bearing lands and does not crush the tube onto its core. The nominal0.5 mm radial gap is an initial clearance allowance, not verified dynamic separation.

Strict three-channel feedthroughs, or designs that put core bearings inside the surrounding tube, likely require larger or new bearings, precision tubes and machined lands. No blanket stock-only feasibility claim is made. Substituting thin plastic journals solely to narrow the drawing would reintroduce friction, deflection and backlash.

## What crosses a strict fixed-motor yaw joint

For a 1:1 bevel pickup on the yaw carrier, choose signs so that `beta_i = alpha_i-y`, where `alpha_i` is the chassis-referenced vertical feed angle. Then the body motor/output coordinates before motor reductions must be:

```text
alphaH = y+h
alphaK = y+h+k
alphaW = y+h+k+w
mY=rY*y, mH=rH*alphaH, mK=rK*alphaK, mW=rW*alphaW
```

The motor-speed matrix and the virtual-work torque map come from this physical pickup. With ideal 1:1 pickups and motor/output reductions `r`:

```text
muW = tauW/rW
muK = (tauK-tauW)/rK
muH = (tauH-tauK)/rH
muY = (tauY-tauH)/rY
```

Thus strict remote drive can load the yaw actuator even when the foot produces little direct yaw moment. Reversing a bevel mesh changes signs, not the requirement to derive its reactions. Software pose compensation does not remove these torque paths. Losses, pretension, shaft friction and rotating inertia are additional.

Three bevel pairs cannot simply be stacked at different heights while all their horizontal outputs are drawn on one hip axis. Different pickup heights produce different horizontal axes. The packaging must include the corresponding parallel-axis transfer stages, or a specifically designed concentric crown/bevel arrangement. A three-color axis line is not a mechanism.

Passive differential angle-adders could mechanically form `y+h`, then `y+h+k`, then `y+h+k+w` from relative motor coordinates and recover a diagonal ideal motor map. Those adders require real gears, bearings, reaction members and return load paths. This is an alternative cost in body volume, losses and backlash, not free cancellation.

## Strict-fixed spatial differential: verified precedent and proposed wheel extension

The published Type I mechanism supplies a more concrete strict-fixed starting point than three independent pickups. With its selected ratios `[rB1,rB2,rG1,rG2]=[1,1,2,2]`, the full actuator-to-joint mapping is:

```text
q0 = (a0-a1)/2
h  = (a0+a1)/4
k  = (a2-a1)/2
```

The quarter-sum for `h` includes the mechanism's actual reduction; using the bare differential half-sum here would double the predicted speed and misstate torque. The exact ratio-dependent matrix and source equation references are in `primary_sources.md`.

An additional wheel feed could duplicate the *physical A2 transmission path* with its own shaft and the same ratios. The existing absolute tibia angle is `t=h+k=q0/2+a2/2`. An identical independent path would produce `chi=q0/2+a3/2`, hence `w=chi-t=(a3-a2)/2`. This is our proposed extra channel, not a wheel mechanism demonstrated in the paper.

```text
[q0]   [ 1/2  -1/2    0    0 ] [a0]
[ h] = [ 1/4   1/4    0    0 ] [a1]
[ k]   [   0  -1/2  1/2    0 ] [a2]
[ w]   [   0     0 -1/2  1/2 ] [a3]

mu0 = tau0/2 + tauH/4
mu1 = -tau0/2 + tauH/4 - tauK/2
mu2 = tauK/2 - tauW/2
mu3 = tauW/2
```

These efforts are on the paper's actuator-coordinate shafts before any additional, explicitly selected gearing. A literal duplicate path also halves continuous wheel speed: a3 at350 rpm gives175 rpm wheel speed with a2 held. Recovering350 rpm needs a different physical wheel ratio or an added speed-up stage and a fresh loss/rating check. This option must prove that its extra independent feed can coexist with the original knee channel; the algebra alone does not create shaft space or a torque lock.

## Enclosed internal plate and the hybrid

If all downstream motors turn with an internal yaw plate, no actuator power must cross that yaw joint. The simple serial arrangement is:

```text
mY=rY*y
mH=rH*h
mK=rK*(h+k)
mW=rW*(h+k+w)
muY=tauY/rY
muH=(tauH-tauK)/rH
muK=(tauK-tauW)/rK
muW=tauW/rW
```

The yaw plate still carries the real downstream motor masses, torque reactions and cable loops. Its *entire swept envelope* must remain inside the body and clear the other three plates, phones, battery, cooling structure and service access.

In the hybrid, the wheel motor stays fixed to the chassis and its one 1:1 bevel pickup crosses yaw. Replace only its coordinate with `mW=rW*(y+h+k+w)`. The yaw torque becomes `muY=(tauY-tauW)/rY`. Hip/knee coupling remains until a physical differential changes it.

For an enclosed pitch-pair differential, two driven side members `alpha,beta` and a femur-driving carrier can give `h=(alpha+beta)/2`. If the alpha member also drives absolute tibia orientation through the equal belt, then `k=(alpha-beta)/2`. This physically implements `alpha=h+k`, `beta=h-k`. With a fixed-body wheel feed crossing yaw:

```text
mA=gA*(h+k), mB=gB*(h-k), mW=gW*(y+h+k+w)
muA=(tauH+tauK-2*tauW)/(2*gA)
muB=(tauH-tauK)/(2*gB)
muW=tauW/gW
muY=(tauY-tauW)/rY
```

This can redistribute peak motor load, at the cost of mixed speed/travel requirements. It does not increase actuator power. The physical spatial differential in the cited paper mixes first-axis and thigh motion; it must not be conflated with this proposed pitch/knee differential.

## Wheel continuation through the knee

| Route | Parts at knee and tibia | Width and load consequence |
|---|---|---|
| Belt throughout | Knee-drive pulley, independent incoming wheel pulley and outgoing wheel pulley on the same knee axis; then a wheel pulley | Normally three pulley bands at the knee. Two incoming femur belts and the outgoing tibia belt require separate axial spaces, flanges, hubs, bearings and retainers. A 9 mm belt does not imply a 9 mm pulley package. |
| Knee turn plus shaft | Incoming wheel pulley at knee drives a bevel pair into a supported longitudinal tibia shaft; a second pair turns to the axle | Four bevel gears plus shaft, bearings and thrust retention. Can narrow the shin and avoid a third pulley band, but adds mesh losses, backlash, lubrication and gear-rating limits. Knee-carrier phase includes knee rotation. |

For two 1:1 knee/foot miter pairs with sign product+1, the tibia-mounted knee pickup sees `chi-(h+k)`. Its longitudinal shaft spin and the wheel-relative spin are therefore equal up to commissioned offsets. The same `chi=h+k+w` input law survives. Omitting the rotating tibia carrier term would make the wheel turn when the knee moves. A chassis-fixed wheel motor crossing yaw adds its yaw pickup separately; it can then have three miter pairs in the complete wheel path, not just the two in the leg.

The verified KHK nominal gear geometry is available for the second route, but its small hardened gear reference rating, 1 A wheel-current limit, impact/backdrive protection and lubricant/speed assumptions remain gates. A current limit does not protect against an externally imposed wheel shock. No flexible rotary shaft is selected; bidirectional torque, bend radius, torsional windup and fatigue would need manufacturer validation.

## Load path and assembly conditions

The body frame must carry first-joint and hip bearing blocks. Motor shafts transmit drive torque; they are not the structural journals for robot weight or belt pretension. Each nested member needs two appropriate supports or an explicit equivalent bearing arrangement. Bearing inner-race spacers and matched shoulders must take shaft clamp force without clamping shields or printed material. Axial assembly must permit every bearing, sleeve and torque lock to be inserted and reached with tools.

The earlier yaw/hip 20T printed-pinion web, thin printed knee-adapter ligament and narrow spacer-neck defects are not solved merely by moving their housings inside the body. New transmission modules need their own torque interfaces and material/gear-rating checks; those old parts are not approved for reuse.

Knee and wheel belt pretension loads are in addition to transmitted tension difference. At pulley radius15.28 mm, 2.75 Nm needs about180 N tension difference; 0.172 Nm wheel torque needs about11.3 N. Initial tension and dynamic factors can dominate the small wheel number. Compact nested journals must be checked against combined belt, gear and body loads.

For the first body envelope study, reserve a distinct motor volume, first-axis bearing/feedthrough volume, hip output corridor, belt planes and cable/cooling access in every quadrant. Motor case volume alone is not a fit proof. No numeric root-station location or transmission-body diameter is frozen in this note.

## Evidence and limits

Stanford Doggo is a useful planar precedent: two body-panel motors drive independent coaxial members through belts, and its leg is a two-DOF five-bar. Its own project documentation reports problems with pulley/shaft play and increasing friction under belt tension. It does not demonstrate this three-DOF, continuously driven wheeled leg. [Project mechanical design](https://github.com/Nate711/StanfordDoggoProject/blob/master/README.md#mechanical-design), [2019 paper](https://arxiv.org/abs/1905.04254).

Wang et al. report a physical differential leg with three torso-fixed actuators, mixing abduction/thigh coordinates and adding a separate knee route. It is a direct precedent for strict body-fixed joint actuation, but it contains no wheel channel and does not establish this body package. [Published paper](https://doi.org/10.1109/TRO.2025.3543262). The detailed source note is `primary_sources.md`.

Next decision: compare the strict spatial-differential option with the enclosed-H/K, fixed-wheel hybrid using the packaging and motor-load screens. Do not freeze a new leg CAD model until the motor-housing interpretation, actual feedthrough geometry, channel widths and swept body clearance agree.

Companion files: `architecture_routes.svg` / `.png` show the route concepts; `coupling_contracts.py` writes machine-readable ideal matrices and checks virtual work. Its five candidate maps passed 100 deterministic random power checks each to floating-point precision. This validates the algebra only. It is not a collision, strength, efficiency or packaging test.
