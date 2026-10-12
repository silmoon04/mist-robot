# Parameter impact, trade-offs, and experiment appendix

This appendix explains what each number means, what it is allowed to drive, and
what else must be rechecked when it changes. It is deliberately stricter than a
normal dimension table: a robot can recompute cleanly in Fusion and still be
unreachable, unstable, hard to print, or impossible to assemble.

> **Authority and scope.** The build-CAD baseline is the table in
> [MIST_FUSION_MASTER_DIMENSIONS.md](../../MIST_FUSION_MASTER_DIMENSIONS.md):
> femur 110 mm, tibia 70 mm, wheel diameter 70 mm, and Layout A direct
> actuation. The actuator study used an unrounded 111 mm femur when it generated
> its reported metrics. Both values appear below only where that distinction
> matters. The default sliders in the simulator are generic starting values,
> not the MIST Fusion baseline. Dimensions drawn into AI concept images and the
> older 65/85 mm print-test beams are not dimensional authorities.

## 1. Four kinds of parameter

The most useful beginner habit is to classify a number before changing it.
Numbers in different classes can have the same unit and still mean completely
different things.

| Class | Question it answers | MIST examples | What it may drive | What it must not silently drive |
|---|---|---|---|---|
| **Physical design** | What shape or interface will be manufactured? | body diameter, hip offset, femur axis-to-axis length, wheel outside diameter, beam thickness | sketches, extrudes, holes, joint-origin positions, hardware envelopes | a convenient screenshot pose |
| **Pose** | Where is the already-built mechanism right now? | body-bottom ground clearance, stance radius, body lean, foot lift, joint angle | joint state, IK/FK, support polygon, collision checks for that state | printed link length, hole spacing, mass |
| **Calibration** | How does the model map to the real printer and hardware? | pocket gap per side, printed-hole compensation, horn zero, servo sign, measured ROM | fit-feature expressions, command mapping, usable joint limits | structural dimensions unrelated to the measured error |
| **Mass and placement** | How much does each item weigh, and where is its mass centre? | 55 g servo, 174 g battery, phone mass-centre height, harness allowance | physical properties, centre of mass, ground reactions, torque and power estimates | the visible envelope unless the real package also changed |

Two examples expose the distinction:

- **pose body clearance = 148 mm** means the cylinder bottom is 148 mm above
  the floor in one reference stance. It does not make the cylinder 148 mm tall.
- The simulator's historical **batteryH** field is the battery mass-centre Z
  coordinate relative to the cylinder bottom. It is not the battery's physical
  thickness. In a new UI, call it **battery_com_z**, and keep the measured
  24.5 mm pack thickness in the battery-envelope component.

### 1.1 Naming rule

Prefer names that encode the quantity and its semantics:

| Ambiguous name | Preferred name | Unit | Meaning |
|---|---|---:|---|
| fit_clearance | pocket_clearance_per_side | mm | intentional gap at each opposing pocket wall |
| clearance | pin_radial_clearance | mm | radial gap between a round pin and bore |
| hole_adjust | hole_diameter_comp | mm | extra modeled diameter used to counter measured print undersize |
| bodyH | pose_body_clearance | mm | ground to cylinder bottom in a pose |
| batteryH | battery_com_z | mm | mass-centre height above cylinder bottom |
| femur | femur_axis_length | mm | hip-pitch axis to knee axis |
| tibia | tibia_axis_length | mm | knee axis to wheel axle, not to the floor |

The current Fusion table keeps short names for convenience. Put the full
semantics in each parameter comment, and never use a short name whose meaning
is uncertain.

## 2. One-way dependency chain

The model should flow from measured facts and deliberate choices toward
calculated consequences. Do not create circular relationships such as sizing a
link from a pose that is itself calculated from that link.

~~~mermaid
flowchart LR
    A["Measured hardware<br/>and design intent"] --> B["Physical design parameters"]
    B --> C["Derived dimensions<br/>axes, offsets, envelopes"]
    C --> D["Sketches and features"]
    D --> E["Rigid components<br/>and joint origins"]

    P["Pose targets<br/>height, stance, lift, lean"] --> F["IK / joint state"]
    E --> F
    F --> G["Posed assembly"]

    K["Calibration<br/>fit, zeros, signs, ROM"] --> D
    K --> F

    M["Mass items<br/>mass plus COM position"] --> H["Robot centre of mass"]
    G --> H
    G --> I["Swept clearance<br/>and support polygon"]

    H --> J["Ground reactions and stability"]
    I --> J
    J --> L["Joint torque, current,<br/>sag, flex and tip margin"]
~~~

The practical rule is:

**top-level parameters → small skeleton sketches/datums → component features →
joint origins → poses → validation.**

If a downstream result is wrong, fix the earliest incorrect input. Do not patch
the last feature with an unexplained offset.

## 3. Core equations and their meaning

The equations here are reasoning tools and cross-checks. Fusion should still be
allowed to recompute the exact 3D model, and the simulator should still run the
complete pose battery.

### 3.1 The neutral leg triangle

For an unrolled leg on level ground:

- Body radius: **R_body = body_dia / 2**
- Hip-roll axis radius: **R_roll = R_body + mount_standoff**
- Hip-pitch axis radius: **R_pitch = R_roll + d1**
- Wheel radius: **r_wheel = wheel_dia / 2**
- Horizontal hip-to-axle demand:
  **x = stance_radius - R_pitch**
- Vertical hip-to-axle demand:
  **z = pose_body_clearance + leg_mount_h - r_wheel**
- Straight-line demand:
  **d = sqrt(x² + z²)**

The two-link chain is geometrically reachable only when:

**abs(femur - tibia) ≤ d ≤ femur + tibia**

That test is necessary, not sufficient. Joint limits, servo bodies, the barrel,
neighbouring legs, cables, and the wheel can still invalidate the pose.

For the rounded build baseline:

| Quantity | Calculation | Result |
|---|---|---:|
| R_roll | 180 / 2 + 10 | 100 mm |
| R_pitch | 100 + 32 | 132 mm |
| x | 176 - 132 | 44 mm |
| z | 148 + 35 - 35 | 148 mm |
| d | sqrt(44² + 148²) | 154.4 mm |
| Reach use | 154.4 / (110 + 70) | **85.8%** |

The unrounded 111/70 mm study chain uses 85.3%. This is why the neutral pose has
little reach reserve: it was optimized against an 86% standing-reach limit.
Increasing the body height or moving the feet farther away can reach the limit
quickly even though the sketch still looks plausible.

For a planar two-link cross-check, define:

**c3 = (d² - L1² - L2²) / (2 L1 L2)**

Then **q3 = knee_sign × acos(c3)**, and q2 follows from the target direction
minus the triangle's internal offset. MIST uses the spider-like negative-knee
branch. Use the repository IK for the final values because wheel contact
direction changes with hip roll.

### 3.2 Do not confuse three lengths

| Length | Endpoints | Why it matters |
|---|---|---|
| Femur axis length | hip-pitch axis → knee axis | kinematics, beam mass, bending |
| Tibia axis length | knee axis → wheel axle | kinematics, belt length, beam mass |
| Ground reach | hip-pitch axis → wheel contact | includes wheel radius and pose |

An overall plastic-body length measured with calipers is not automatically an
axis-to-axis length. Dimension the skeleton between joint centres first, then
build material around it.

### 3.3 Printed-link mass

The simulator's analytical beam estimate is:

**m_beam ≈ density × L × W × T × structural_factor + bracket_allowance**

At PETG density 1.27 g/cm³, W = 20 mm, T = 14 mm, structural factor = 0.70,
and an 18 g bracket allowance:

- a 110 mm femur is approximately 45.4 g;
- a 70 mm tibia is approximately 35.4 g.

The **0.70 structural factor is not “70% slicer infill.”** It is a coarse
analytical scalar for effective mass and stiffness. Real wall count, layer
orientation, local ribs, inserts, holes, and infill pattern dominate. After
slicing and printing, replace analytical estimates with slicer and scale
measurements.

### 3.4 Bending sensitivity

The current model treats the femur as a cantilever:

**deflection = F_perpendicular × L³ / (3 E I)**

with:

**I ≈ W × T³ × structural_factor / 12**

First-order consequences:

- deflection grows with **length cubed**;
- increasing thickness in the modeled bending direction is much more effective
  than adding the same percentage of width;
- changing 14 mm thickness to 15 mm ideally multiplies deflection by
  (14/15)³ = 0.813, about a **19% reduction**;
- the model does not represent layer anisotropy, joint slop, tibia bending,
  creep, stress concentrations, or servo-case compliance.

### 3.5 Centre of mass and tip margin

For mass items i:

**COM = sum(m_i × position_i) / sum(m_i)**

On level ground, the static support margin is the shortest in-plane distance
from the COM projection to an edge of the contact polygon. A useful
cross-check for one edge is:

**tip angle ≈ atan(margin / COM_height)**

The exact direction matters. A single “tip angle” is the worst edge, not a
promise that the robot resists every push equally. During a one-leg lift, the
support polygon changes from four contacts to three. During diagonal
two-wheel support it collapses to a line; the actuator study found static
balance impossible for every layout without active balancing.

### 3.6 Torque, wheel radius, voltage sag, and runtime

The gravitational or contact torque about a joint axis is:

**tau = dot(axis, lever_arm × force)**

A rough sensitivity bound for moving a mass radially is:

**delta_tau ≈ mass × g × delta_lever_arm**

Moving one 55 g servo 100 mm closer to an axis can therefore remove up to about
0.054 N·m of gravity torque in the most adverse orientation. The true change
depends on pose and axis direction.

Wheel holding torque scales with radius:

**tau_wheel = rolling_force × wheel_radius**

Therefore a larger wheel improves obstacle rollover and axle clearance but
demands more motor torque for the same tractive force. Diameter and wheel mass
are independent simulator inputs; update both when the real wheel changes.

The power model uses:

**V_rail ≈ V_open_circuit - current × pack_and_harness_resistance**

and:

**runtime_minutes ≈ capacity_Ah × state_of_charge / average_current × 60**

Battery capacity is not a free runtime slider. A different pack also changes
mass, envelope, connector access, centre of mass, and often resistance.

## 4. Clearance semantics: say exactly which gap you mean

“Add 0.25 mm clearance” is incomplete. State whether it is per side, radial,
diametral, one-directional, or a swept 3D separation.

### 4.1 Manufacturing-fit parameters

Use separate parameters:

| Parameter | Provisional value | Exact meaning |
|---|---:|---|
| pocket_clearance_per_side | 0.25 mm | gap at each opposing pocket wall |
| pin_radial_clearance | 0.25 mm starting point | radial pin-to-bore gap; coupon-tune |
| hole_diameter_comp | measured; no canonical value yet | extra modeled bore diameter to counter print undersize |

The repository observes that printed holes can emerge roughly 0.2–0.4 mm
undersize, but this is not a measured compensation for the final PETG profile.
If a guide UI uses 0.20 mm as an example, label it **provisional**.

For a measured rectangular insert:

**pocket_width = insert_max_width + 2 × pocket_clearance_per_side**

For a round pin:

**modeled_hole_diameter = pin_max_diameter + 2 × pin_radial_clearance +
hole_diameter_comp**

The factor of two appears because a radial/per-side clearance occurs on both
sides of a diameter. If a drawing instead specifies a **diametral clearance**,
add it once. Never mix the two conventions.

If the part locates against one datum wall, add clearance only to the free
side. Symmetrically enlarging the pocket would move the controlled datum.

### 4.2 Clearance is not tolerance or compensation

- **Design clearance** is the intentional nominal gap.
- **Tolerance** is the possible variation around a dimension.
- **Process compensation** deliberately offsets the CAD dimension to cancel a
  repeatable printer error.
- **Interference** is a negative clearance used for a press fit.

A conservative one-side check is:

**minimum_actual_gap = nominal_gap - internal_surface_error -
external_surface_error - alignment_error**

The global pocket gap must not be reused for screw tap holes, screw clearance
holes, bearing seats, heat-set inserts, horn splines, or flexible snaps. Each
interface needs its own coupon and acceptance criterion.

### 4.3 Manufacturing fit is not motion clearance

The 0.25 mm fit value is for mating printed features. It is not adequate proof
that a moving servo case, screw head, cable, belt, wheel, or link clears another
part across the full range of motion.

Record motion-clearance results in this form:

**minimum separation = value, between named bodies, over named pose/ROM set,
with named cable and fastener envelopes visible.**

Interpret the sign explicitly:

- negative: interference;
- zero: touching;
- positive: geometric separation in the modeled state.

Then subtract allowances for print error, joint backlash, shaft play, beam
deflection, cable movement, and assembly misalignment. The simulator's
collision screen approximates links as 14 mm-radius capsules; it is useful for
finding gross collisions, not certifying a manufactured gap.

### 4.4 Coupon sequence

1. Measure the real insert or pin at several points.
2. Print a labelled ladder around the proposed value, in the intended
   material, orientation, wall count, layer height, and nozzle/profile.
3. Test cold, then after normal assembly and servo heat exposure where
   relevant.
4. Record loose/sliding/retained/binding, not just “fits.”
5. Promote the winning value into the calibration parameters.
6. Reprint one critical coupon whenever material, nozzle, line width,
   orientation, or profile changes.

## 5. What changes when a parameter changes

### 5.1 Physical-design parameters

| Parameter | First-order effect | Coupled consequences and trade-off | Mandatory recheck |
|---|---|---|---|
| body_dia | body radius changes; hip-roll axis moves by half the diameter change | interior volume, shell mass, phone offset, leg radial demand, print-bed fit | phone opening, deck/ribs, all hip mounts, shell mass, bed envelope |
| body_h | cylinder and internal stack become taller | shell COM rises if material increases; easier vertical packaging, worse tipping and print time | mass property, split strategy, phone/sensor view, top payload |
| leg_mount_h | raises hip axes relative to body bottom | changes the leg triangle for every pose and can move brackets into the shell/deck | neutral and squat IK, body collision, ground clearance |
| mount_standoff | moves hip-roll axis away from shell | more shell/link clearance but a longer, more flexible bracket and larger moment | bracket strength, fasteners, cable bend radius, foot radius |
| d1 | moves hip-pitch axis outward from hip roll | widens packaging and reduces required link reach at fixed feet; can enlarge hip pod | roll-to-pitch bracket, servo overlap, cable routing, real added mass |
| femur_axis_length | increases proximal reach | adds beam mass and lever arm; modeled flex rises with L³; may improve stand height but hurt swing | every pose, knee/body collision, torque, flex, bed orientation |
| tibia_axis_length | increases distal reach | changes knee angle, wheel/body collision, belt length and distal inertia | every pose, wheel clearance, cable/belt route, swing |
| wheel_dia | raises axle above contact and enlarges wheel envelope | better rollover; more holding torque, inertia, tire material and collision risk | tibia/wheel interference, motor torque, effective rolling radius |
| front_az / rear_az | rotates mount and wheel rolling directions | changes support polygon, directional stability, leg overlap and drive scrub | top-view interference, support compass, selected physical wheel-heading scenario |
| beam_w | increases section area and bending inertia linearly | modest stiffness gain for proportional plastic mass; may block servo/cable space | load path, printer orientation, neighbouring bodies |
| beam_t | increases section area linearly and modeled bending inertia cubically | efficient for one bending direction, but thicker does not cure weak layer orientation or joint slop | load direction, layer orientation, fastener edge distance |
| linkage ratio | divides knee-servo torque by ratio | divides actuator-side angular travel by the same ratio; may increase backlash and package size | full ROM, singularities, horn travel, pushrod collision |
| actuator layout A–E | relocates knee/wheel servo mass | changes transmission count, unsprung mass, wiring, backlash and optimization geometry | use the complete layout battery; never change only the dropdown and call it equivalent |

The current simulator does not charge a dedicated mass or stiffness penalty for
making d1 longer. A design that looks better numerically after increasing d1
still needs a real bracket-volume and load-path update.

### 5.2 Pose parameters

| Parameter | Useful effect | Cost or failure mode | Hold constant deliberately |
|---|---|---|---|
| pose_body_clearance | taller body stance | less reach reserve, higher COM, potentially lower tip angle | foot contacts if using IK; joint angles if using FK |
| stance_radius | wider support polygon | greater joint lever arm, torque, reach use, leg overlap | body height and mass |
| body_x / body_y | shifts COM toward the active support polygon | unloads one side and overloads another; can tip or bind | feet and height |
| feet_azimuth_twist | changes foot direction around each mount | wheel scrub and neighbour collision | mount azimuths |
| foot_lift | creates swing clearance | changes support from four feet to three and adds dynamic demand | support-shift strategy |
| step_x | creates stride | changes IK, leg interference and wheel gap | stance radius and body pose |
| slope / heading | tests gravity direction | normal load shifts, grip and wheel holding torque change | geometry, pose, friction assumption |

When changing link length, choose one of three explorer hold modes:

1. **Fixed foot contacts (IK):** body and feet stay in the world; joint angles
   change. This is what the simulator's one-variable tests below use.
2. **Fixed joint angles (FK):** the assembly pose remains the same; feet move.
   This is often what a Fusion joint screenshot does.
3. **Fixed reach ratio:** the UI rescales pose targets to preserve geometric
   headroom. This is useful for comparing families, but it is not the same task.

Never compare results from different hold modes without labelling them.

### 5.3 Calibration parameters

| Parameter | If increased or changed | Recheck |
|---|---|---|
| pocket_clearance_per_side | easier assembly, less preload; more positional slop | axis alignment, screw clamp, heat cycling |
| pin_radial_clearance | freer rotation; more backlash and impact motion | loaded play and hole wear |
| hole_diameter_comp | larger printed bores without changing intentional fit | coupon result; do not double-count slicer XY compensation |
| servo_zero_offset | changes real neutral pose without changing CAD | all joints on stands, symmetric feet, hard-stop margin |
| servo_sign | reverses command direction | single-joint low-speed test before multi-joint motion |
| usable ROM | changes reachable workspace | collision sweep and cable strain at both ends |
| effective_wheel_radius | maps rotation to ground travel | straight-line distance and odometry, left/right mismatch |
| measured hardware envelope | can move holes, pockets, cable exits and axes | every referencing feature; Compute All and inspect downstream warnings |

Calibration values are test results, not stylistic preferences. Record printer,
material, date, coupon ID, and measurement method beside them.

### 5.4 Mass and placement parameters

| Change | Main consequence | Hidden coupling |
|---|---|---|
| more shell mass | higher total support loads and servo demand | where the material was added matters as much as how much |
| phone higher | higher COM and lower tip angle | front offset also makes stability directional |
| battery lower/central | generally improves stability | must preserve removal path, strap access and cable bend radius |
| battery rearward | can counter the front phone | can worsen rearward slope/push margin |
| heavier wheel or foot servo | more distal/swing inertia and impact energy | static standing may hide the dynamic penalty |
| extra top payload | increases total load and COM height | affects one-leg and crawl cases more than four-foot stand |
| larger battery capacity | potentially longer runtime | mass, envelope and resistance must be updated together |
| more harness resistance | more voltage sag and less available torque/speed | connector heat and fuse-holder quality are physical, not just electrical inputs |

Every mass row needs **mass, count, X/Y/Z centre, source, confidence, and
measurement status**. A visible placeholder with no assigned mass is not a mass
model. Represent non-geometric mass with calibrated density or a named,
positioned proxy body; a mass value with no correct position is not a
centre-of-mass model.

## 6. Quantified one-variable sensitivity examples

These numbers were recomputed through the repository's pure evaluation pipeline
using the exact Layout A study geometry: femur 111 mm, tibia 70 mm, d1 32 mm,
front/rear azimuth 25°/109°, stance radius 176 mm, and body-bottom clearance
148 mm. The baseline flat four-foot stand is:

- mass 3223.2 g;
- COM approximately X = +27.6 mm, Z = 183.0 mm;
- worst servo 12.28% of stall torque at the 9.9 V brown-out rating;
- minimum tip angle 24.89° and geometric support margin 84.93 mm;
- modeled femur deflection 0.426 mm;
- 2.78 A total and 11.71 V rail in this static case.

Each row changes only the named input while keeping the foot contacts and body
target fixed through IK. These are **local sensitivities**, not approved design
variants.

| One change | Mass | Worst servo | Min tip | Femur flex | What the result teaches |
|---|---:|---:|---:|---:|---|
| baseline | 3223 g | 12.28% | 24.89° | 0.426 mm | reference only; crawl is much harder |
| femur +10 mm | 3233 g | 12.98% | 25.08° | 0.571 mm | only +10 g modeled mass, but flex rises **34%** because length is powerful |
| tibia +10 mm | 3233 g | 12.42% | 24.92° | 0.472 mm | same analytical mass increment; different knee geometry and much smaller femur-flex increase |
| d1 +10 mm | 3223 g | 11.84% | 25.06° | 0.402 mm | fixed feet require less radial reach, but the model omits the larger real hip bracket |
| wheel diameter +10 mm, mass held fixed | 3223 g | 12.13% | 24.78° | 0.447 mm | axle height and joint angles change; a real larger wheel would also gain mass/inertia |
| stance radius +10 mm | 3223 g | **15.75%** | **25.83°** | 0.447 mm | wider is more tip-resistant but raises worst-servo use by 3.46 percentage points |
| body clearance +10 mm | 3223 g | 12.66% | **23.94°** | 0.376 mm | this stand loads the beam slightly more axially, yet the higher COM loses about 0.95° tip margin |
| beam thickness 14 → 15 mm | 3236 g | 12.28% | 24.95° | **0.347 mm** | about +12.9 g robot mass for an 18% modeled flex reduction |
| phone COM +50 mm | 3223 g | 12.28% | **24.52°** | 0.426 mm | flat-ground joint load is unchanged, but COM rises 3.18 mm and stability worsens |
| shell mass +200 g | 3423 g | **13.59%** | **23.84°** | 0.458 mm | mass and its cylinder-midheight placement both matter |
| +250 g payload at +300 mm above cylinder bottom | 3473 g | **13.92%** | **22.31°** | 0.466 mm | COM rises to 202.1 mm; a high payload must be tested in one-leg and crawl poses |

Do not extrapolate these rows linearly. For example, the +10 mm stance step
locally changes worst utilization by about +0.35 percentage points per
millimetre, but that slope will change as the knee straightens and the reach or
ROM boundary approaches.

Most importantly, the reference stand is not the sizing case. The Layout A
crawl sequence peaks at 42% in the actuator study. A parameter that improves
the symmetric stand can still make a three-leg crawl phase worse.

## 7. Layout A–E trade-off map

Each column in the actuator study was re-optimized over link lengths, d1,
azimuths, stance, and height. The table therefore compares **complete optimized
systems**, not a clean one-variable relocation experiment.

| Layout | Mechanism | Optimized femur/tibia | Mass | Crawl peak | Swing hip torque | Tallest stand | Max modeled slope | Runtime | Build implication |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **A: all direct** | knee servo at knee; wheel servo at foot | 111/70 mm | **3223 g** | 42% | 0.125 N·m | **171 mm** | 22.5° | 38 min | simplest; no transmissions, but 110 g of servos at/below each knee |
| **B: wheel at knee** | direct knee plus belt along rigid tibia | 82/91 mm | 3263 g | 35% | 0.128 N·m | 163 mm | 27.5° | 41 min | easiest remote-drive upgrade; free axle, bearing/bushing, pulley and tensioner |
| **C: knee at hip** | 1.5:1 pushrod/four-bar; wheel still at foot | 73/85 mm | 3260 g | **34%** | **0.049 N·m** | 148 mm | 22.5° | **48 min** | strong swing improvement; linkage backlash, ROM reduction and hip packaging |
| **D: knee at hip, wheel at knee** | linkage plus rigid-tibia belt | 70/101 mm | 3321 g | 38% | 0.085 N·m | 161 mm | 22.5° | 45 min | light below-knee structure, but two mechanisms to tune per leg |
| **E: all at hip** | linkage plus two-stage wheel transmission crossing knee | 70/96 mm | 3364 g | 35% | 0.053 N·m | 156 mm | **30°** | 44 min | best wiring/proximal mass, hardest moving-joint transmission and largest hip pod |

The packaging choice also moved the optimized geometry:

| Layout | d1 | Front/rear mount azimuth | Reference stance/body clearance |
|---|---:|---:|---:|
| A | 32 mm | 25° / 109° | 176 / 148 mm |
| B | 31 mm | 25° / 119° | 169 / 140 mm |
| C | 37 mm | 25° / 114° | 157 / 132 mm |
| D | 42 mm | 25° / 111° | 168 / 132 mm |
| E | 59 mm | 25° / 124° | 183 / 130 mm |

This is why changing only the actuator-location selector while retaining A's
geometry is an experiment, not a reproduction of B, C, D, or E. In their own
optimized stands, all five layouts use only 7–12% of worst-case stall torque;
the crawl and suspended-swing cases expose the meaningful differences.

Nuances that prevent the table being misread:

- **A remains the v1 recommendation.** Its dominant risk is bracket and
  interface quality, so removing four or eight transmission mechanisms is more
  valuable than optimizing gait dynamics before the first reliable leg exists.
- Reserve a belt corridor and free-axle/bearing space in the tibia so **B can
  be a drop-in v2 experiment**. Its belt spans a rigid link and crosses no
  joint.
- Knee-mounting the wheel servo does not guarantee lower hip torque in every
  stance. In the optimized B sprawl, the knee is farther from the hip than the
  foot's gravity arm, so swing hip torque is slightly higher than A.
- A/C/E differ by about 2.5× in swing hip torque. That matters for gait
  acceleration, smoothness and impacts even when four-foot standing values look
  similar.
- A's 70 mm tibia and 25° front azimuth sit at the optimizer's searched lower
  bounds. The result means “best found inside this search,” not “smaller has
  been proven worse.”
- The study text describes a 35% design constraint for its optimization pose
  battery, but crawl was evaluated later and reaches 42% for A. That is below
  the simulator's 55% transient peak threshold, not below the 35% target.
- Slope results above roughly 25° are ordering evidence, not guaranteed field
  capability; belt/linkage friction, tire squirm and floor variation are not
  fully represented.

## 8. Safe parameter-experiment workflow

### 8.1 Digital loop

1. **Version the baseline.** Save a named Fusion version and export the matching
   simulator config. Record whether the femur is the 110 mm build value or the
   111 mm study-reproduction value.
2. **Write one question.** Example: “Can 10 mm more stance radius buy at least
   0.5° tip margin without exceeding 30% continuous servo use in any pose?”
3. **Classify the input.** Physical design, pose, calibration, or mass. If two
   classes must change, make two recorded steps.
4. **Choose the hold mode.** Fixed foot contacts, fixed joint angles, or fixed
   reach ratio.
5. **Change one independent value.** Let expressions update derived values.
   Do not manually edit the same derived dimension in several sketches.
6. **Compute All in Fusion.** Resolve every yellow warning and red error before
   interpreting the geometry. Inspect the earliest broken reference first.
7. **Inspect geometry in named scenarios.** Neutral stand, low squat, tallest
   intended stand, one-leg lift, crawl extremes, the selected physical
   wheel-heading scenario, and both ROM ends. A simulated “drive stance” does
   not rotate fixed chassis pods.
   Show servo bodies, horn screws, wheel, cables, belt, and hardware envelopes.
8. **Run interference and section checks.** Record the minimum named separation,
   not just “no collision visible.”
9. **Refresh physical properties.** Materials, calibrated effective densities,
   and positioned mass-proxy bodies must match the candidate. Inspect COM in
   front, side and top views.
10. **Run the simulator battery.** Reach/ROM, support polygon, per-foot load,
    torque, current, rail voltage, deflection, friction and transient gait.
11. **Compare deltas against the frozen baseline.** A green absolute value can
    still be a large regression.
12. **Decide: keep, revise, or revert.** Save the decision and evidence before
    the next experiment.

### 8.2 Physical loop

Move from cheap, passive tests toward powered tests:

1. dimension or fit coupon;
2. unpowered interface assembly;
3. one adjustable link or joint on the pose grid;
4. one complete unpowered leg through hand-checked ROM;
5. one powered joint at low speed with no load;
6. one powered leg secured on stands;
7. full robot on stands;
8. low-speed, no-payload floor test;
9. payload and gait tests only after earlier gates pass.

Before powered motion, prove torque-off/deadman behavior and keep the disconnect
reachable. Stop for binding, unexpected direction, drift, reset, missed servo,
abnormal current, hot connector/servo, loose horn, cracked print, cable strain,
or battery movement. A parameter experiment is not permission to bypass the
normal electrical and mechanical safety gates.

### 8.3 What to record

| Field | Example |
|---|---|
| Experiment ID | P-STANCE-003 |
| Baseline | Fusion version, config filename/hash, material profile |
| Question and success criterion | +0.5° tip, no pose over threshold |
| Parameter class | pose |
| Input before → after | stance 176 → 186 mm |
| Hold mode | fixed foot contacts, body height fixed |
| Predicted deltas | +0.94° tip, +3.46 pp worst-servo in stand |
| Fusion result | Compute All clean; min wheel/tibia gap by pose |
| Simulator result | scenario-by-scenario table, worst frame named |
| Physical result | coupon/leg/stand measurements, current and temperature |
| Decision | reject, revise, or promote with reason |

## 9. Interactive web parameter explorer: proposed contract

The explorer should teach causality, not merely expose many sliders.

### 9.1 Input groups

| Group | Inputs |
|---|---|
| Baseline | Layout A–E preset; 110 mm build or 111 mm study reproduction; config version/date |
| Physical design | body diameter/height, mount height/standoff, d1, femur/tibia axis lengths, wheel diameter/mass, azimuths, beam section/material, linkage ratio |
| Pose | body clearance, stance radius, body X/Y, foot azimuth twist, four lift and step values, stand/suspended mode |
| Calibration | pocket gap per side, pin radial gap, hole diameter compensation, measured hardware envelope, joint zero/sign, usable ROM, effective wheel radius |
| Mass table | repeatable rows with name, count, mass, X/Y/Z COM, source, confidence, measured/provisional state |
| Environment/power | slope and heading, friction coefficient, state of charge, capacity, pack/harness resistance, voltage cutoff |
| Scenario set | neutral, squat, one-leg, 10° slope, crawl, drive, tallest, suspended swing |
| Comparison semantics | hold feet, hold joints, or hold reach ratio; one-variable or linked-change mode |

Each input should show:

- value and unit;
- source/authority;
- safe-to-edit versus calculated/locked status;
- provisional/measured badge;
- affected downstream systems;
- valid UI exploration range, explicitly labelled **not an approved CAD range**.

### 9.2 Outputs

| Output | Minimum useful detail |
|---|---|
| Leg triangle | dimensioned side view, axle/contact distinction, reach use and joint angles |
| Top layout | mount rays, feet, rolling directions, neighbouring-leg/wheel overlap |
| Clearance view | named closest body pair, signed minimum gap, pose/frame where it occurs |
| Mass view | item markers, COM, uncertainty/provisional badges |
| Support view | contact polygon, gravity projection, margin and directional tip compass |
| Load view | per-foot normal force, per-joint torque, continuous and transient thresholds |
| Structure view | modeled femur flex plus formula and limitations |
| Power view | per-leg and total current, open-circuit/rail voltage, sag, fuse margins, runtime estimate |
| Scenario matrix | pass/warn/fail for every scenario; worst scenario and animation frame named |
| Delta panel | before/after absolute value, delta, percentage, and dependency explanation |
| Sensitivity panel | one-at-a-time tornado chart or local derivative with nonlinear warning |
| Export | versioned JSON, human-readable parameter table, Fusion-entry table, experiment record |

The most valuable output is a “**why did this change?**” trace. For example:

**stance radius +10 → horizontal reach +10 → knee straighter → joint lever arm
changes → worst servo 12.28% to 15.75%; support polygon widens → tip angle
24.89° to 25.83°.**

### 9.3 Suggested screen layout

- **Left:** grouped inputs with search, source badges, and a visible hold-mode
  selector.
- **Centre:** synchronized side/top/3D views with dimension, COM, support and
  clearance overlays.
- **Right:** verdicts, deltas, the dependency explanation, and the current
  limiting scenario.
- **Bottom:** scenario matrix and a sweep chart; selecting a failed cell moves
  the views to that pose/frame.

### 9.4 Data shape

~~~json
{
  "schemaVersion": 1,
  "authority": {
    "baseline": "MIST Fusion master dimensions",
    "date": "2026-07-12",
    "geometryVariant": "build-110"
  },
  "design": {
    "layout": "A",
    "bodyDiaMm": 180,
    "legMountHMm": 35,
    "mountStandoffMm": 10,
    "d1Mm": 32,
    "femurAxisMm": 110,
    "tibiaAxisMm": 70,
    "wheelDiaMm": 70
  },
  "pose": {
    "bodyClearanceMm": 148,
    "stanceRadiusMm": 176,
    "holdMode": "fixedFootContacts"
  },
  "calibration": {
    "pocketClearancePerSideMm": 0.25,
    "pinRadialClearanceMm": 0.25,
    "holeDiameterCompMm": null,
    "status": "coupon-required"
  },
  "massItems": [
    {
      "name": "battery",
      "count": 1,
      "massG": 174,
      "comMmFromBodyBottom": [0, 0, 40],
      "status": "provisional"
    }
  ],
  "scenarios": ["neutral", "squat", "oneLeg", "slope10", "crawl", "drive"]
}
~~~

The output object should include the normalized inputs, all derived values,
scenario results, limiting scenario/frame, signed clearances, warnings, and a
calculation/model version. This makes a screenshot reproducible instead of
turning it into untraceable evidence.

### 9.5 Interaction rules

- Never silently change a second independent input. Offer a linked change,
  explain it, and require the user to accept it.
- Calculated fields are read-only and display their expression.
- Changing a physical-design input shows **Fusion rebuild / likely reprint**.
- Changing a pose input shows **no part geometry change**.
- Changing a calibration input shows the coupon or bench result it depends on.
- Changing mass without position, or position without mass, produces an
  incomplete-model warning.
- A slider crossing reach, ROM, collision, current, or stability boundaries
  should stop hiding the invalid geometry; keep it visible and explain why it
  failed.
- Preserve keyboard operation, do not rely on red/green alone, and show units
  on every control and readout.
- Allow baseline pinning and URL/config sharing so two people compare the same
  state.

## 10. Goal-to-parameter decision guide

| Goal | Change first | Then inspect | Avoid the tempting shortcut |
|---|---|---|---|
| stand taller | pose_body_clearance within current reach/ROM | tip margin, squat reserve, cable reach | lengthening both links before testing pose headroom |
| resist tipping | lower/central mass, then modest stance increase | torque, leg overlap, directional margin | judging stability from stance width alone |
| clear the body | pose and swept ROM first; then standoff/d1 if physical | bracket bending, packaging, mass | hiding collision by suppressing hardware envelopes |
| reduce flex | print orientation and load path, then beam thickness/ribs | mass, servo/cable clearance, real load test | treating structural_factor as slicer infill |
| improve fit | calibration coupon | datum shift, backlash, clamp load | scaling the whole part |
| carry more payload | add mass at real position | one-leg/crawl, tip, current, mount strength | adding only capacity/runtime in the power model |
| smoother/faster leg swing | reduce distal mass; consider Layout B after v1 | transmission loss, backlash, belt tension, wiring | jumping directly to Layout E |
| roll over larger obstacles | wheel diameter and real wheel mass together | torque, tibia collision, stance/axle geometry | changing diameter while holding mass and inertia fictional |

The correct outcome of a parameter study is often “keep the simpler part and
change the pose.” That is a valid design improvement: fewer reprints, fewer
new failure modes, and an easier baseline to calibrate.

## 11. Known baseline cautions

- AI concept images are aesthetic references only. Crop out invented dimensions
  or mark them **concept — not to scale**.
- The old adjustable 65/85 mm beam baseline and 76 mm wheel coupon predate the
  110/70 mm and 70 mm Fusion authority. They can teach fit and mechanism
  concepts but do not validate the final geometry.
- Servo body dimensions are provisional until the ordered C018 hardware,
  ears, shaft, horn, cable exit, and fastener interfaces are measured.
- Battery, electronics, and harness positions remain provisional until the real
  assembly is laid out and weighed.
- The simulator's generic slider bounds are exploration limits. The Layout A
  result is one optimized candidate inside bounded searches, not a proof of a
  global optimum.
- A clean Fusion timeline proves only that dependencies recomputed. It does not
  prove printed fit, load capacity, stable gait, or safe wiring.

Related local authorities:

- [MIST Fusion master dimensions](../../MIST_FUSION_MASTER_DIMENSIONS.md)
- [MIST actuator-layout study](../../MIST_ACTUATOR_LAYOUT_STUDY.md)
- [MIST material dimensions and mass](../../MIST_MATERIAL_DIMENSIONS_MASS.md)
- [MIST print-test kit](../../MIST_PRINT_TEST_KIT.md)
- [MIST simulator README](../../../../sim/README.md)
