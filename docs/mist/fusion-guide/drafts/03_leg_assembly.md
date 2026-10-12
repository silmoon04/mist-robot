# Build one real MIST leg, then assemble all four

This chapter builds the mechanical chain that the concept posters only suggest:

`base_link → q1 hip roll → d1 offset → q2 hip pitch → femur → q3 knee → tibia → driven wheel`

The result is one editable, motion-tested leg module and three associative copies attached at MIST's four actual body azimuths. The dimensions in [`MIST_FUSION_MASTER_DIMENSIONS.md`](../../MIST_FUSION_MASTER_DIMENSIONS.md), the parameter CSV in this guide, and `sim/js/kin.js` are authoritative. The AI posters are composition references only.

> **Poster correction.** The Step 4 poster shows two plain links and a foot, the Step 5 poster shows four mounts at 90-degree intervals, and the Step 6 poster gives generic hip/knee limits. MIST instead has three articulated axes plus a driven wheel, four non-equally-spaced mounts, and the limits listed below. Do not trace the poster holes or type its dimensions into Fusion.

## What this chapter freezes, and what it deliberately leaves open

By the end of the chapter, freeze these facts:

- world frame: `+X` forward toward the phone face, `+Y` left, `+Z` up;
- leg-local mount frame: `Xm` radial outward, `Ym` tangential counter-clockwise, `Zm` up;
- q1 axis point: radius `mount_r = body_dia/2 + mount_standoff = 100 mm`, height `leg_mount_h = 35 mm` above the barrel bottom;
- q1 axis: `+Xm`, radial and horizontal;
- q2 axis point: `d1 = 32 mm` farther outward along q1's axis;
- q2, q3, and the Layout A wheel axes: parallel to `-Ym` in the zero-roll pose;
- `femur = 110 mm` from q2 to q3, measured axis-to-axis;
- `tibia = 70 mm` from q3 to wheel axle, measured axis-to-axis;
- `wheel_dia = 70 mm` at the tire outside diameter;
- the four mount azimuths: FL `+25°`, FR `-25°`, RL `+109°`, RR `-109°`.

Do **not** freeze these without hardware or a design decision:

- servo ear holes, horn bolt circle, spline/horn recess, output-stack thickness, auxiliary support, cable exit, and fastener lengths;
- bearing sizes, wheel width, hub stem length, or a Layout B belt and pulley standard;
- the final wheel-heading strategy;
- final mechanical stops or cable-safe joint limits.

The first pass is therefore a kinematically exact blockout with measured envelopes. The second pass turns the envelopes into printable, double-supported brackets after the real STS3215, horn, screws, bearings, and coupons are available.

## Read the chain before drawing it

| Joint | Parent → child | Axis point | Positive axis | Zero definition | Analysis ROM |
|---|---|---|---|---|---:|
| `q1` hip roll | `base_link/root_mount → hiproll` | `R=mount_r`, `Z=leg_mount_h` | radial `+Xm` | leg plane vertical | `-60°…+60°` |
| offset `d1` | within `hiproll` | q1 to q2, outward | along `+Xm` | not a joint | `32 mm` |
| `q2` hip pitch | `hiproll → femur` | q1 point + `d1` | rolled `-Ym` | femur straight down | `-35°…+110°` |
| `q3` knee | `femur → tibia` | q2 + `femur` | parallel to q2 | tibia aligned with femur | `-135°…+135°` |
| wheel | `tibia → wheel` | q3 + `tibia` | Layout A: parallel to q3 | arbitrary spoke index | unlimited in CAD |

Positive q2 rotates a straight-down femur toward radial outward. MIST's current spider-like inverse-kinematics branch uses a negative q3 value: the knee bows out and the tibia returns toward the wheel. Do not mirror a leg to obtain the other side; rotating the same module to a different mount frame preserves this convention.

For a useful visual check, the current neutral reference (`stance_r=176 mm`, barrel-bottom clearance `148 mm`) evaluates to approximately:

`q1 = 0°`, `q2 = +40.52°`, `q3 = -63.63°`

That value is derived from the current geometry and `sim/js/kin.js`. It is a CAD pose check, not a servo calibration or a promise that the bracket clears there.

## Hard design gate: decide what “driving” means

At zero roll, the current kinematic model makes each wheel axle tangential and each ordinary wheel's rolling line radial. Its four rolling-line headings are therefore `+25°`, `-25°`, `+109°`, and `-109°`. They are not parallel.

That arrangement cannot behave like conventional four-wheel skid steering without lateral tire slip. Even straight motion asks some wheels to scrub. Moving the wheel servo from the axle to the knee in Layout B does **not** change this fact; it only changes how torque reaches the same axle.

| Direction | What it preserves | What it costs |
|---|---|---|
| Accept fixed radial wheels and scrub | simplest common leg; q3 and wheel axes stay parallel; current Layout A/B study remains closest | tire wear, wasted power, unpredictable floor loads, poorer odometry; must be proven slowly on the real floor |
| Make four wheel rolling lines parallel to `+X` in the neutral pose | familiar forward drive and skid-turn model | wheel axle is no longer simply knee-parallel; needs per-corner yaw adapters, an adjustable pod, or a distal redesign; common-carrier symmetry may be lost |
| Use omni wheels | tolerates lateral velocity while keeping the leg-plane axle | different wheel, traction, vibration, noise, print/BOM, and floor-contact behavior |
| Add a passive caster/swivel | wheel may self-align | a driven caster is mechanically awkward, heading can flutter or reverse, and it is poor as a precise leg endpoint |
| Add powered steering | heading becomes controllable | four more axes, actuators, cables, mass, current, software, and collision envelopes |
| Keep a bolted, adjustable wheel pod for v1 trials | lets physical tests choose before a permanent carrier is printed | more fasteners and another interface that must not slip under wheel torque |

**Gate W:** do not print four final wheel carriers, cut a permanent horn recess, or claim skid steering until one option is selected. The safest CAD move now is a removable wheel pod with a repeatable datum and enough yaw adjustment to test radial and parallel headings.

## 1. Prepare the current Fusion file

These paths are for Autodesk Fusion `v2704.1.23` as checked on 12 July 2026. If a command is not visible in a compact toolbar, press `S`, type its current name, and launch it from the Toolbox.

1. Open the guide's **Hybrid Design** in **Parametric Modeling Mode**.
2. Activate the top/default component before creating assembly relationships. Joints, contact sets, and motion studies belong at assembly level.
3. Open `Modify > Change Parameters` and confirm the imported values in [`../mist-fusion-parameters.csv`](../mist-fusion-parameters.csv), especially `mount_r`, `d1`, `femur`, `tibia`, the four azimuth parameters, and `q1_min` through `q3_max`.
4. In the Browser, right-click `base_link` and choose **Pin**. Current Fusion renamed the old top-level **Ground** action to **Pin**. **Ground To Parent** is a different child-to-parent relationship and is not the command wanted here.
5. Save a named version before assembly work, for example `MIST_leg_chain_axes_v01`.

For every new internal part, use `Design > Solid > Assemble > New Component`, set `Type: Part`, `Part Type: Standard`, clear **External**, enter the name, and check **Activate**. Creating the component before its sketches keeps its parametric history reusable. If **External** is unavailable, verify that the file is a Hybrid Design rather than a pure Assembly Design.

Do not use `Extrude > Operation: New Component` for this reusable leg. Current Autodesk guidance warns that this shortcut can leave the sketch/history in the default component, which makes later reuse and copying harder to understand.

## 2. Build the four body mount datums

The mount skeleton is more important than the cosmetic shell. It prevents a later body edit from silently rotating a joint axis.

### 2.1 Make the mount-height sketch

1. Activate `base_link`.
2. Choose `Design > Solid > Construct > Offset Plane`.
3. Select the barrel-bottom datum plane, not a filleted shell face.
4. Enter `leg_mount_h` as the offset and rename the result `PL_leg_mount_height`.
5. Start a sketch on `PL_leg_mount_height`; rename it `SK_mount_azimuths`.
6. Project the body origin with `Create > Project/Include > Project` if it is not already selectable.
7. Draw a centre-point circle at the body axis. Toggle it to **Construction** and dimension its radius as `mount_r`.
8. Draw a horizontal construction line from the centre along world `+X`; this is the zero-azimuth reference toward the phone.
9. Draw four construction rays from the same centre to the circle. Constrain every outer endpoint coincident with the construction circle.
10. With `Sketch > Sketch Dimension`, set the signed ray angles as follows. Use dimensions or symmetry expressions, not eyeballed positions.

| Point | Expression | World interpretation |
|---|---:|---|
| `P_FL_q1` | `front_az` | forward-left, `+25°` CCW from `+X` |
| `P_FR_q1` | `-front_az` | forward-right, `-25°` |
| `P_RL_q1` | `rear_az` | rear-left, `+109°` |
| `P_RR_q1` | `-rear_az` | rear-right, `-109°` |

11. Add a sketch point at each ray endpoint and rename the point/ray through the sketch feature names where practical.
12. Fully constrain the sketch, then finish it.

The angular gaps are not four equal quadrants. Around the ring they are `50°`, `84°`, `142°`, and `84°`. A four-instance Circular Pattern or two Mirrors produces the poster robot, not MIST.

### 2.2 Create explicit base joint origins

For each of the four sketch points:

1. Choose `Design > Solid > Assemble > Joint Origin`.
2. Set **Mode: Simple** and select the named sketch point.
3. In **Alignment**, choose **Reorient**.
4. Set the joint origin's `Z Axis` along that point's radial sketch ray, outward from the body centre.
5. Set its `X Axis` straight down, parallel to world `-Z`. This makes the origin right-handed and gives every leg the same zero-roll reference.
6. Click OK and rename the origin `JO_FL_mount`, `JO_FR_mount`, `JO_RL_mount`, or `JO_RR_mount`.

Use the joint-origin coordinate glyph, not only the dot, as the check. At every mount:

- origin Z arrow: radial outward;
- origin X arrow: down;
- q1 point: exactly on `mount_r` and `leg_mount_h`;
- no arrow is copied from a global axis by accident.

To make the glyphs legible, use the Navigation bar at the bottom of the canvas: `Display Settings > Object Visibility > Joint Origins` or `Joint Origin Axes`.

**Gate M:** from Top view, the four origin Z arrows must lie on the four radial rays; from Front/Right views, all origin points must be on the same mount-height plane.

## 3. Create a reusable leg module as rigid links

Create an organisational parent called `LEG_MASTER`, then create these internal components under it. The parent has no printable body.

| Working component | What is rigidly inside it | Export/final name for the FL instance |
|---|---|---|
| `root_mount` | stationary q1 servo case reference, ear bracket, chassis interface, optional opposite-side support | `FL_root_mount` or merge to `base_link` by a fixed joint |
| `hiproll` | q1 metal horn reference and moving cradle; `d1` bridge; q2 servo case and its fixed bracket | `FL_hiproll` |
| `femur_link` | q2 horn/clevis, 110 mm femur beam, q3 servo case and bracket | `FL_femur` |
| `tibia_link` | q3 horn/clevis, 70 mm tibia beam, Layout A wheel-servo case/carrier | `FL_tibia` |
| `wheel_link` | metal wheel horn, PETG hub, TPU tire | `FL_wheel` |

The `root_mount` is a Fusion/printing convenience, not a fourth leg degree of freedom. It attaches to `base_link` with a rigid placement joint. Keeping it separate lets **Duplicate With Joints** copy the q1 servo pocket and bracket to the other three mount datums. At URDF/export time it can remain a fixed link or be merged into `base_link`.

### Bodies are not links

Fusion joints act between **components**, not between bodies. A single `Leg` body containing all beams, clevises, servo cases, and wheels cannot articulate. Conversely, do not split a rigid beam, bracket, and its captive servo body into independent moving components unless they are joined rigidly.

If detailed purchased hardware is nested as separate reference components, select only hardware that moves with the same link and use `Assemble > Rigid Group`. Never include components from both sides of q1, q2, q3, or the wheel in one Rigid Group.

### Put servo parts on the physically correct side of each joint

The servo case and its mounting ears are stationary relative to the **parent** link. The output horn is stationary relative to the **child** link:

| Axis | Servo case belongs with | Horn/output belongs with |
|---|---|---|
| q1 | `root_mount` | `hiproll` |
| q2 | `hiproll` | `femur_link` |
| q3 | `femur_link` | `tibia_link` |
| wheel | `tibia_link` | `wheel_link` |

Do not import a servo as one rigid component that spans both sides of a revolute joint. Either split the visual reference into `servo_case_ref` and `servo_horn_ref`, or place copied reference bodies in their respective link components.

## 4. Model the one-leg geometry

Work at the FL mount first, but dimension the module in its own local frame. Activate only the component being edited. Show neighbouring components as translucent references; do not accidentally extrude into them.

### 4.1 Make a measured STS3215 envelope

Until the servos arrive, the only locked case envelope is `servo_l × servo_w × servo_h = 45.2 × 24.7 × 35 mm`. Create a simple case body and add clearly named provisional bodies for:

- mounting ears and ear holes;
- output boss/shaft axis;
- metal horn outside diameter, thickness, bolt circle, and centre screw;
- opposite-case/auxiliary support feature;
- both bus sockets, plug insertion space, and the cable bend envelope.

Prefix uncertain bodies or dimensions with `VERIFY_`. The case box proves packaging; it does not prove a printable pocket. Do not infer ear holes or horn geometry from the AI render.

The print kit contains 0.3 mm and 0.5 mm servo-pocket coupons. They are calibration choices, not proof that either clearance fits the actual unit. In this guide, `pocket_clearance_per_side` means clearance on **each side**:

`pocket_width = measured_servo_width + 2 * pocket_clearance_per_side`

Keep that distinct from `pin_radial_clearance`, which is a **radial** gap:

`free_bore_dia = measured_pin_dia + 2 * pin_radial_clearance + hole_diameter_comp`

The last term is a separately coupon-tuned printer process correction, not desired fit.

### 4.2 Build the q1 root and hip-roll cradle

1. In `root_mount`, place the q1 servo output axis at `JO_FL_mount`.
2. Orient its output axis along local `+Xm`—the base joint origin's Z axis—not vertically and not tangentially.
3. Create the stationary ear bracket around the servo envelope. Leave tool access to every mounting screw and space to unplug the bus connector without removing the barrel.
4. In `hiproll`, place the q1 horn at the same axis.
5. Create a moving U-cradle or two-cheek bracket around the servo. One cheek connects to the metal horn; the other provides a coaxial auxiliary pivot/bearing or supported idler.
6. Extend the moving structure outward along the q1 axis until the q2 axis is exactly `d1` from q1.
7. Place the q2 servo case in the `hiproll` component with its output axis along local `-Ym`.

`d1` is an **axis-to-axis offset along q1**, not a vertical link and not the thickness of the q1 bracket. At 32 mm, packaging is tight relative to a 24.7 mm servo body. Prove room for the horn stack, bracket cheeks, washers, support, and cable before decorating the part.

### 4.3 Use a servo-supported clevis, not a printed pin pretending to be a servo

Use the same load-path pattern at q1, q2, q3, and preferably the wheel:

1. The real metal horn transmits torque on one side.
2. A printed moving tongue or hub bolts to that horn.
3. Two structural cheeks place the moving link in double shear.
4. The far cheek uses a coaxial bearing, bushing, shoulder screw, or the servo's verified auxiliary support feature.
5. A small controlled axial gap plus washers prevents rub.
6. The output and support axes must be genuinely coaxial; forcing a misaligned far support will preload the servo and make it run hot.

The print kit's 7 mm clevis / 6 mm tongue / M3 pin coupon is a useful passive-hinge experiment. It is **not** the final geometry for an actuated STS3215 joint. Keep the metal horn and the servo output axis in the real load path.

Every bracket needs:

- a removable horn-centre-screw path;
- captive-nut, nyloc, or heat-set-insert access as chosen later;
- enough material around holes after print shrinkage;
- a cable slot and a service loop that cannot reach the horn;
- clearance at the entire ROM, not only the home pose;
- a print orientation that does not put the primary bending load across a weak layer seam.

### 4.4 Model the femur

1. Activate `femur_link`.
2. Make a side-profile sketch in the q2–q3 leg plane.
3. Place the q2 and q3 axis centres first and dimension their separation as `femur`.
4. Build the beam around that construction line using `beam_w` and `beam_t`. Keep the **axis centres** 110 mm apart after end caps, fillets, and pockets are added.
5. At q2, add the horn-attached tongue/hub and the opposite support feature.
6. At q3, place the q3 servo case and fixed double-support bracket. Its output axis must be parallel to q2.
7. Cut cable passages only after a swept cable envelope exists. A tunnel through the narrowest beam section can erase the stiffness gained by `beam_w` and `beam_t`.

The AI poster's “90 mm upper link with Ø12 holes” is not a usable shortcut. The actuator axis is defined by the measured servo output and support, not by a generic through-hole.

### 4.5 Model the tibia and Layout A wheel carrier

1. Activate `tibia_link`.
2. Place its q3 origin at the proximal end and its wheel-axis origin exactly `tibia` away.
3. Build the beam around the 70 mm axis-to-axis construction line.
4. At q3, add the horn-attached tongue/hub and far-side support.
5. At the distal end, place the Layout A wheel-servo case. Its output axis is parallel to q3 in the current kinematic baseline.
6. Make the direct wheel carrier a **removable pod** attached to a repeatable planar datum on the tibia. Keep its final bolt pattern provisional until fasteners and wheel-heading strategy are selected.
7. Push the wheel hub outboard on a parameterised stem far enough that the 70 mm tire does not touch the tibia, servo case, screw heads, or cable. A previous printable concept had a real wheel/shin collision.
8. Add an opposite-side wheel support if packaging permits. A wheel hanging only from the servo horn sends ground impacts and bending load into the servo output bearing.

Increasing the hub stem improves shin clearance but increases bending moment on the servo, support, and printed carrier. The correct value is the shortest stem that clears the complete moving envelope plus print and assembly tolerance.

### 4.6 Model the wheel as its own component

1. Activate `wheel_link`.
2. Sketch the 70 mm tire outside diameter on a plane normal to the axle.
3. Make a PETG hub and TPU tire as separate bodies within the same rigid component, or as nested components held in one Rigid Group.
4. Keep wheel width provisional; the old print kit mentions 30 mm, but the current master dimensions do not lock it.
5. Model the real metal horn and its measured fasteners. Do not print an invented spline.
6. Add a visible spoke/index mark to make wheel rotation and sign obvious in Fusion.

The old `fit_wheel_slice_76` coupon is a 76 mm legacy interface test. It must not overwrite the current `wheel_dia = 70 mm` baseline.

## 5. Reserve the Layout B corridor now

Layout A is the v1 recommendation: all four leg actuators are direct, so there is no transmission to tension or tune. Layout B moves only the wheel servo to the knee and uses one belt along the rigid tibia to a bearing-supported axle. The belt crosses no moving joint, which makes it the least difficult later upgrade.

| Study result | Layout A, all direct | Layout B, wheel at knee |
|---|---:|---:|
| Optimised femur/tibia | 111/70 mm | 82/91 mm |
| Optimised `d1` | 32 mm | 31 mm |
| Optimised front/rear azimuth | 25°/109° | 25°/119° |
| Mass | 3223 g | 3263 g |
| Crawl peak servo | 42% stall | 35% stall |
| Hip swing torque | 0.125 N·m | 0.128 N·m |
| Runtime estimate | 38 min | 41 min |

The counter-intuitive swing result matters: moving the wheel servo to the knee does not automatically reduce every hip load because the knee can have a longer gravity arm in the sprawled pose. Layout B also has a different optimised geometry. Reserving a corridor in the 110/70 Layout A leg makes a retrofit physically possible; it does **not** turn that leg into the optimised Layout B result.

### Create non-printing keep-outs

1. Under `LEG_MASTER`, create an internal component named `REF_layout_B_keepouts`.
2. Create a servo envelope adjacent to q3 called `KEEP_B_wheel_servo`.
3. Create a straight swept/rectangular volume from the knee pulley region to the wheel axle called `KEEP_B_belt_run`.
4. Add `KEEP_B_axle_bearing` and `KEEP_B_tensioner_sweep` cylinders/volumes.
5. Give all keep-outs a bright translucent appearance and place `REF_` / `KEEP_` at the start of every name.
6. Do not include the component when exporting printable bodies.

The keep-out sizes remain provisional until belt pitch/width, pulley tooth counts, bearing, shaft, tension method, guards, and allowable belt twist are selected. The corridor still enforces useful rules now:

- no cross-rib, fastener, horn screw, or cable tunnel blocks the knee-to-axle line;
- there is a flat mounting land near q3 for a future wheel servo;
- the axle region can accept a bearing-supported free axle rather than only a servo spline;
- the direct wheel pod can be removed without cutting the tibia;
- a guard and tension adjustment have somewhere to exist.

Do not hollow the whole tibia into a belt tunnel. That trades a future mechanism for a current structural weakness. Reserve an **external or locally guarded corridor** first, then calculate the final section after belt selection.

**Gate B:** hide `REF_layout_B_keepouts`, verify Layout A assembly; show it, run `Inspect > Interference` against the tibia and hardware, and confirm no unintended physical body occupies the reserved route.

## 6. Create and orient the joint origins on the leg

Use `Design > Solid > Assemble > Joint Origin`. The point says **where** a joint is; the coordinate triad says **which way it rotates and what zero means**. Create both sides of each interface explicitly.

| Origin | Component | Location | Origin `Z Axis` | Origin `X Axis` at zero |
|---|---|---|---|---|
| `JO_mount_root` | `root_mount` | q1-axis pod-placement datum, coincident with `JO_q1_parent` | radial outward | down |
| `JO_q1_parent` | `root_mount` | q1 output centre | radial outward `+Xm` | down |
| `JO_q1_child` | `hiproll` | q1 horn centre | radial outward `+Xm` | down |
| `JO_q2_parent` | `hiproll` | q2 output centre | `-Ym` | down |
| `JO_q2_child` | `femur_link` | q2 horn centre | `-Ym` | femur distal direction at q2=0 |
| `JO_q3_parent` | `femur_link` | q3 output centre | parallel to q2 | femur distal direction |
| `JO_q3_child` | `tibia_link` | q3 horn centre | parallel to q2 | tibia distal direction at q3=0 |
| `JO_wheel_parent` | `tibia_link` | wheel-servo output centre | parallel to q3 for Layout A | a chosen visible radial/index direction |
| `JO_wheel_child` | `wheel_link` | horn/axle centre | same as parent | same visible index direction |

For a circular edge or hole whose centre is hard to select, hover over the face/hole, hold `Ctrl` on Windows, then select the obscured snap point. Use **Reorient** to select the intended Z and X directions. Use **Flip** only when the triad needs reversing; do not compensate for a wrong origin with an arbitrary joint angle.

The q2, q3, and wheel axes are **parallel**, not coincident. q3 sits one femur length from q2; the axle sits one tibia length from q3.

**Gate A:** show only Joint Origin Axes and link centreline sketches. All parent/child origin pairs must be coincident when the module is in its zero pose, and each pair's Z and X arrows must agree.

## 7. Add the five assembly relationships

Current Autodesk guidance recommends the normal **Joint** command with **Duplicate With Joints**. Use As-Built Joint only when already-positioned imported geometry makes repositioning undesirable and you accept a less direct duplication workflow.

### 7.1 Rigidly place the root at FL

1. Activate the top/default component.
2. Choose `Design > Solid > Assemble > Joint`.
3. On **Position**, set Component 1 to `root_mount` and select `JO_mount_root`.
4. Set Component 2 to `base_link` and select `JO_FL_mount`.
5. Use **Flip** only if the root points into the barrel.
6. On **Motion**, choose **Rigid**.
7. Click OK and rename the relationship `FL_mount_fixed`.

The base is pinned; the root is fixed to it by a real relationship. Do not Pin each leg part. Pinning all of them masks missing or incorrect joints.

### 7.2 Add q1, q2, q3, and wheel

For each row below, use `Design > Solid > Assemble > Joint`, select the child origin as Component 1 and the parent origin as Component 2, then choose **Motion: Revolute** and **Rotate: Z Axis**.

| Name | Component 1 / Component 2 | Minimum | Maximum | Rest for frame audit |
|---|---|---:|---:|---:|
| `FL_q1_roll` | `hiproll` / `root_mount` | `q1_min` | `q1_max` | `0 deg` |
| `FL_q2_hip` | `femur_link` / `hiproll` | `q2_min` | `q2_max` | `0 deg` |
| `FL_q3_knee` | `tibia_link` / `femur_link` | `q3_min` | `q3_max` | `0 deg` |
| `FL_wheel` | `wheel_link` / `tibia_link` | unchecked | unchecked | `0 deg` |

In the **Motion > Joint Motion Limits** section, enable Minimum and Maximum and enter the parameter expressions. The wheel remains an unlimited Revolute joint because Fusion has no separate “continuous” joint type. Unchecked limits mean continuous for the CAD model; firmware must still impose speed, current, temperature, and mode safety.

Use **Preview Motion** to check each axis. Then stop and verify the sign:

- positive q1 follows the right-hand rule about radial `+Xm`;
- positive q2 moves a down-pointing femur radially outward;
- q3 zero makes tibia and femur collinear; MIST's current neutral branch uses negative q3;
- positive wheel rotation agrees with the visible wheel index and the sign convention intended for firmware.

If a sign is wrong, reorient/flip the joint origins. Do not silently reverse one limit pair or add `180°` until the animation looks plausible; that creates a CAD/URDF/firmware mismatch.

### CAD zero, home, limit rest, and servo centre are different things

- **CAD zero** defines the kinematic frames above.
- **Joint Rest** is a Fusion assembly setting; it is not written to the servo.
- **Home Position** is the pose Fusion returns to. After driving the leg to the validated neutral reference, right-click a joint and use **Set as Home Position** only if that behavior is useful for the assembly.
- **STS3215 position 2048** is the electrical/mechanical centring step before the horn is fitted.

Because q2's requested range is asymmetric (`-35°…+110°`), servo centre 2048 does not automatically equal the middle of the CAD reference range or q2=0. Choose horn indexing and the firmware centre offset deliberately after the physical bracket range is known.

Joint limits in Fusion are an analysis aid, not a physical stop and not a firmware guard. Final protection needs all three: collision-safe printed geometry, firmware min/max calibration per servo ID, and a mechanical/cable arrangement that cannot destroy itself on a bad command.

## 8. Prove one leg before copying it

Use the current commands, not the poster's old paths:

- `Design > Solid > Assemble > Drive Joints`, or right-click a joint and choose **Drive Joints**;
- right-click a joint and choose **Animate Joint** to view that joint alone;
- use **Animate Joint Relationships** to include other relationships;
- `Design > Solid > Inspect > Interference` checks overlaps only at the current pose;
- Section Analysis reveals the inside but does not report collision.

Test at least these poses, computing Interference after each important move:

| Pose | q1 | q2 | q3 | Purpose |
|---|---:|---:|---:|---|
| datum | 0° | 0° | 0° | origin and axis sign |
| neutral reference | 0° | +40.52° | -63.63° | current stance geometry |
| roll inward | `q1_min` | neutral | neutral | barrel, root bracket, cable |
| roll outward | `q1_max` | neutral | neutral | bracket cheek and cable |
| hip minimum | 0° | `q2_min` | a safe q3 | shell and femur clearance |
| hip maximum | 0° | `q2_max` | a safe q3 | horn, clevis, cable |
| knee minimum | 0° | a safe q2 | `q3_min` | femur/tibia fold and wheel/shin |
| knee maximum | 0° | a safe q2 | `q3_max` | opposite fold and hard-stop risk |

Do not assume that every combination of three independent extrema is a useful reachable pose. Do sample combined corners that the controller could command, especially those that bring the wheel toward the body. Record which collision sets are intentional, such as a washer touching its support face, and which require a design change.

Selective Contact Sets can prevent specified parts passing through one another during drag tests, but they cost computation. Use them for the servo/bracket, femur/tibia, and wheel/shin pairs under investigation, not as a permanent all-component substitute for joint limits and static Interference checks.

**One-leg gate:** the module must have exactly four intended rotational degrees of freedom; all other pieces move rigidly with their link; q1/q2/q3 signs match the frame table; no wheel, servo case, horn, support, fastener, cable envelope, or Layout B keep-out collides in the accepted pose set.

## 9. Duplicate the proven module with its joints

Do not use Mirror, `Create > Pattern > Circular Pattern`, or ordinary body copies. The current **Duplicate With Joints** command preserves associative component geometry and duplicates enclosed joints while placing each instance through an open joint.

1. Leave the original module mounted at FL.
2. Activate the top/default component.
3. Choose `Design > Solid > Assemble > Duplicate With Joints`.
4. In the Browser, select `root_mount`, `hiproll`, `femur_link`, `tibia_link`, and `wheel_link`. Use **Add** in the dialog until all five are selected. Selecting `LEG_MASTER` alone is acceptable only if the dialog shows the same relationships.
5. Inspect the relationship table before placing anything:
   - `FL_mount_fixed` must be **open** because `base_link` is not selected;
   - q1, q2, q3, and wheel must be **enclosed** because both components of each joint are selected.
6. Select `FL_mount_fixed` as the placement relationship.
7. Set **Origin Mode: Simple**.
8. Select `JO_FR_mount`, `JO_RL_mount`, and `JO_RR_mount` in the canvas, one at a time. Do not select an adjacent shell vertex or servo face.
9. Expand **More** and inspect every placed instance. Use **Flip** only if a whole pod points into the body.
10. Click OK.

Fusion adds a Copy Component and a Joint feature for each instance. Component instances remain associative: changing shared component geometry changes every instance. The duplicated joints are independent: editing one joint's origin, limit, or rest does not edit the other three. This is why the limit fields use shared parameter expressions and why every copy still gets a motion audit.

If q1 is shown as open instead of the rigid mount, the selection omitted `root_mount`. Cancel, correct the selection, and retry. If q2/q3/wheel are shown as open, one or more moving links were omitted. Do not continue with a partially duplicated chain.

## 10. Name occurrences and relationships without destroying reuse

Associative Fusion instances normally share a component definition name and differ by occurrence suffixes such as `:1`, `:2`, and `:3`. **Paste New** would make independent components that can be renamed freely, but then later geometry fixes would not propagate.

During design iteration, keep associativity and maintain this explicit occurrence map in the design notes/properties:

| Leg | Azimuth | Required occurrence contents | Required joint names |
|---|---:|---|---|
| FL | `+front_az` | root, hiproll, femur, tibia, wheel instance at `JO_FL_mount` | `FL_mount_fixed`, `FL_q1_roll`, `FL_q2_hip`, `FL_q3_knee`, `FL_wheel` |
| FR | `-front_az` | same at `JO_FR_mount` | `FR_mount_fixed`, `FR_q1_roll`, `FR_q2_hip`, `FR_q3_knee`, `FR_wheel` |
| RL | `+rear_az` | same at `JO_RL_mount` | `RL_mount_fixed`, `RL_q1_roll`, `RL_q2_hip`, `RL_q3_knee`, `RL_wheel` |
| RR | `-rear_az` | same at `JO_RR_mount` | `RR_mount_fixed`, `RR_q1_roll`, `RR_q2_hip`, `RR_q3_knee`, `RR_wheel` |

Rename the independent joint relationships in `Browser > Relationships > Joints`. Keep the canonical link names `{FL,FR,RL,RR}_hiproll`, `_femur`, `_tibia`, and `_wheel` in the export plan even if the live associative Browser uses shared definitions plus occurrence numbers.

When geometry is frozen for URDF/export, choose one of two deliberate routes:

- preserve shared instances and configure the exporter with the occurrence-to-leg map; or
- save a separate export snapshot, use independent copies there, and rename every link explicitly.

Do not break associativity in the working design merely to make the Browser prettier.

## 11. Audit the four-leg assembly

Drive and inspect all four copies. The duplicate feature does not prove that every destination origin was oriented correctly.

1. Return all legs to the datum pose. From Top view, q1 axes must point along their radial mount rays.
2. Drive all legs to approximately `(0°, +40.52°, -63.63°)`. The projected wheel-ground contact points should lie near the 176 mm stance circle before bracket offsets and wheel-heading alternatives are introduced.
3. Drive each q1 positive by a small equal angle. Confirm the same local motion occurs on all four legs; “same” means relative to each local mount frame, not the same world-left direction.
4. Drive each q2 positive. Every femur must swing radially outward from its own mount.
5. Drive each q3 negative into the selected spider branch. Every knee must bow consistently.
6. Run Interference on neighbouring front pods, neighbouring rear pods, shell/root brackets, wheel/tibia, and cable envelopes.
7. Show `REF_layout_B_keepouts` and repeat the check.
8. Confirm the body has only one Pin and every leg is constrained by relationships, not by hidden Capture Position/Move features.

**Four-leg gate:** there are four distinct mount origins at `+25°`, `-25°`, `+109°`, and `-109°`; all four modules have the same local chain and signs; all sixteen driven axes exist; no joint copy is missing; and the wheel-heading decision remains visibly flagged until resolved.

## 12. Parameter-change impact map

Change one parameter, regenerate, drive the pose set, run Interference, and update the simulator before accepting it. A green Fusion timeline only means features rebuilt; it does not mean the robot is still stable, strong, or driveable.

| Parameter change | Likely benefit | Coupled cost/checks |
|---|---|---|
| `mount_standoff ↑` | more shell/bracket clearance | wider body envelope, longer root bracket, more bending, longer cables, changed q1-axis radius and IK |
| `d1 ↑` | more room between q1 and q2; stance widens for the same angles | more distal mass and q1 load, larger overall width, changed reach/support polygon, possible neighbour collision |
| `d1 ↓` | compact pod and lower moment arm | servo/horn/clevis stack may no longer fit; body collision at roll |
| `femur ↑` | more reach and possible stand height | more mass, swing inertia, torque, flex, cable length, wheel sweep, print leverage; neutral q2/q3 changes |
| `tibia ↑` | more reach and axle clearance; longer Layout B belt route | more knee moment, flex and belt sensitivity; wheel sweeps closer to body in folded poses |
| `wheel_dia ↑` | obstacle rollover and axle ground clearance | more torque for the same tractive force, higher speed per rpm, larger collision envelope, changed stance/body-height geometry |
| `beam_w` or `beam_t ↑` | stiffness and more room for inserts | mass, servo-pocket crowding, print time; stiffness gain depends strongly on which dimension is aligned with bending |
| `front_az` / `rear_az` | changes support polygon and pod spacing | changes wheel headings, neighbour clearance, wiring routes and stability; rebuild all four explicit origins |
| `pocket_clearance_per_side ↑` | easier insertion and PETG tolerance | servo case can rattle or shift; ear fasteners take more locating load |
| `pin_radial_clearance ↑` | freer passive support/pin; bore grows by twice the edit before process compensation | backlash, impact, poor coaxial support; radial meaning differs from per-side rectangular clearance |
| q1/q2/q3 ROM widened | larger theoretical workspace | more collision/cable/horn exposure and possibly unreachable/unsafe combinations; firmware limits must change too |
| hub stem ↑ | wheel clears shin and fasteners | larger servo/bearing bending moment and wheel wobble |
| Layout B corridor enlarged | more pulley/belt choice | less room for tibia structure, cable, and direct wheel carrier |

When changing femur, tibia, `d1`, wheel size, azimuths, or mass placement, rerun the MIST simulator/optimisation checks. Fusion is the geometry authority for what fits; it is not the authority for torque, stability, current, or runtime.

## Troubleshooting

### A joint rotates around the right point but the wrong line

The joint origin point is correct but its axis is not. Edit both joint origins, use **Reorient**, set the Z axis to the required shaft direction, then keep `Rotate: Z Axis`. Do not repair it with a Move feature.

### The child jumps far away when Joint starts

The normal Joint command repositions Component 1 onto Component 2. Confirm the two selected origins are the matching parent/child pair and that their X/Z directions agree. Use As-Built Joint only if the parts were intentionally positioned and Duplicate With Joints is no longer the immediate workflow.

### The whole robot moves when a leg is dragged

`base_link` is not pinned, or the rigid mount relationship is missing. Pin only `base_link`; do not Pin every child.

### A whole leg is rigid

Look for a Rigid Group that crosses a revolute interface, a Pin on a child, a rigid joint where Revolute was intended, or a nested component that contains all links as bodies. Suppress one suspect relationship at a time and retest.

### Duplicate With Joints cannot place the module

The selection has no open joint. Include `root_mount` and all moving links, exclude `base_link`, and choose the resulting open `*_mount_fixed` relationship. Autodesk's command needs at least one selected component attached to an unselected destination component.

### A duplicate moves correctly but later limit edits do not propagate

This is expected. Duplicate geometry is associative; duplicate joints are independent. Reference shared q-limit user parameters, then audit all joint instances.

### The servo fits the CAD pocket but the joint binds

The body envelope is not the load-bearing axis stack. Check real horn thickness, output-boss stand-off, washers, opposite support coaxiality, case clamping, print shrinkage, and screw-head interference. Test the PETG coupon before a full link.

### The wheel clears at neutral but cuts through the tibia when folded

The hub was checked in one pose only. Drive q2/q3 through the accepted combined range, compute Interference at samples, and shorten/re-angle the carrier or move the wheel farther outboard. Re-check the added bending moment.

## Current Autodesk references used for this workflow

- [Components and current internal/external component model](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-COMPONENTS.htm)
- [Create new components](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/GUID-5966BF6B-4135-49B3-B5BF-29A6577C9E72.htm)
- [Create a Joint](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-CREATE-JOINT.htm)
- [Create a Joint Origin](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-CREATE-JOINT-ORIGIN.htm)
- [Joint Motion Limits](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/GUID-543C82D9-F1E8-42B3-9C34-31BB108AFAA3.htm)
- [Edit and drive joints](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/GUID-C0DCB65B-87F6-43AC-8A62-CC68B27EEB6E.htm)
- [Duplicate components with their joints](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-DUPLICATE-WITH-JOINTS.htm)
- [Pin versus Ground To Parent](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-GROUND-TO-PARENT.htm)
- [Contact Sets](https://help.autodesk.com/cloudhelp/ENU/Fusion-Assemble/files/ASM-CONTACT-SETS.htm)
- [Interference](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/GUID-A6629113-B137-4EDE-B3B2-C9F1F3BA83D1.htm)

## Visual-editor notes for the polished guide

- From [`2ee53a2c…png`](../../../../mist_3d/mist_fusion_guide/2ee53a2c-b6a6-414f-bd26-0ddb6c07c57e.png), the one-leg silhouette and exploded stack can orient a beginner, but crop out or visibly strike through the 90/70 mm links, Ø12 holes, and foot block. Overlay q1/q2/q3/wheel labels and the real 110/70 axis distances.
- From [`2dc4e473…png`](../../../../mist_3d/mist_fusion_guide/2dc4e473-bd40-4c91-8d6c-b93aed0190e5.png), use the Browser-organisation idea only. The 4×90° top view should appear solely in a “do not copy this pattern” comparison beside the corrected +25/-25/+109/-109 mount diagram.
- From [`d9363efa…png`](../../../../mist_3d/mist_fusion_guide/d9363efa-0ea2-4767-89ec-a16e4b8b0fc9.png), the hero render and collision concept are usable. Replace the generic two-joint limit table, old `Inspect > Drive Joint` path, and generic Ground wording with current Fusion screenshots and this chapter's q1/q2/q3/wheel table.
- A new vector diagram should show parent/child ownership of each servo case and horn. That relationship is difficult to infer from a beauty render and prevents a common beginner assembly mistake.
