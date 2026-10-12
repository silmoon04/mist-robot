# Mechanical audit and transmission architecture

Audit date: 2026-09-06. Scope: existing Fusion generators, print releases, MIST mechanical documentation, and primary manufacturer references. This file proposes the next architecture; it does not certify a built leg or stair-climbing robot. Existing CAD was inspected through source and release records, without modifying or executing the user's Fusion documents.

The best next candidate is a vertical yaw joint, hip pitch, and a remotely driven knee, with the three C018 servos concentrated at the hip. A separate wheel gearmotor remains at the foot. Start with a 1:1 belt along the femur and put any required extra reduction entirely in the yaw carriage. This keeps the transmission equation understandable, avoids a four-bar toggle, and gives the yaw joint a real steering function.

## What the existing work actually establishes

| Evidence | Established | Limit |
|---|---|---|
| `docs/mist/MIST_FUSION_MASTER_DIMENSIONS.md` | Legacy barrel Ø180 × 260 mm; 110 mm femur, 70 mm tibia, 70 mm wheel; radial hip-roll chain at ±25°/±109° | These dimensions describe the old all-direct layout, not the new remote-drive design. |
| `fusion360/audited_remote_knee_chain.py` | Native BRep 110/40/110/40 parallelogram with explicit pivot stacks | This earlier demonstrator explicitly was not a drop-in for its side-by-side servo bracket. |
| `fusion360/slim_remote_knee_fit.py` | Later assembly has two facing, coaxial C018 outputs, separated by a measured 9.58 mm face gap; 40/110/40/110 parallelogram | Tested relative input range only −30° to +40°. It is a bench mechanism, not a released walking leg. |
| `fusion360/remote_knee_624zz_test_leg_v2/README_PRINT_V2.md` | Three 624ZZ passive pivots, nominal 4 × 13 × 5 mm; 13.40 mm seat entry, 13.55 mm relief, 5.2 mm depth, 21 mm boss OD | Earlier 13.25 mm seats needed hammering in full bosses. A thin coupon fit did not transfer directly to the full part. |
| `fusion360/remote_knee_624zz_fixture_adapter_plate_v3/README_PRINT_V3.md` | Revised fixtures and adapters; edge-only BRep contact caused a non-manifold exported mesh and needed explicit bridges | One Fusion solid is not sufficient evidence that a printable mesh is manifold. |
| `fusion360/REV_F_DESIGN.md` | 25.23 mm servo pocket is reported as physically verified; prior cap did not clamp, nut slots had poor retention, and axial stops were missing | New preload and case-depth choices remain designs to test. `servo_case_depth_low = 32 mm` is explicitly a placeholder. |
| `docs/mist/MIST_ACTUATOR_LAYOUT_STUDY.md` | Earlier simulator compares distal mass and static loads across layouts | Four nonparallel fixed-wheel headings prevented the claimed ordinary no-slip drive behavior. The report itself records this caveat. |

The existing slim mechanism's 4.2 mm link layers and printed inner-race adapters should not be promoted into a loaded leg. Its release specifically requires smooth metal pins for powered or repeated-load work. The new design must model bearings, shafts, shoulders, retainers, fasteners, and accessible assembly paths as parts, rather than reserve them in comments.

## C018 data to use

The manufacturer's ST-3215-C018 specification states the following at 12 V: rated torque 10 kg·cm (0.981 N·m), stall torque 30 kg·cm (2.942 N·m), 45 rpm no-load speed, 0.9 A rated current, 2.7 A stall current, 55 ± 1 g mass, and backlash ≤0.5°. The case is 45.2 × 24.7 × 35 mm. Its encoder resolution is 0.088°; this is not loaded joint accuracy. Input range is 4–14 V. The specified endurance cycle uses one fifth of stall torque. [Feetech C018 specification, pages 3–6](https://cdn.robotshop.com/media/F/Fit/RB-Fit-155/pdf/feetech_12v_30kg_cm_magnetic_encoding_servo_sts321_specification_pdf.pdf).

Use rated torque as the initial repeated-load ceiling. Voltage-dependent torque/speed, heating, assembly friction, and unit variation still require bench identification. A generic percentage of stall should not erase the manufacturer's rated figure. Increasing reduction exchanges output speed for torque; it cannot increase mechanical power. Do not apply stall torque and no-load speed simultaneously in a simulation.

## Steering changes the leg architecture

Replace the legacy radial hip-roll axis with vertical yaw. Hip pitch and knee stay parallel to the wheel axle. This gives each conventional wheel a controllable heading, while leaving three positioning DOFs for walking. It gives up an independently actuated roll axis, so the controller must regulate body attitude through foot heights and placements.

Yaw also turns the leg plane. Parallel wheel headings therefore constrain where the feet can lie laterally. A simulator cannot widen the drive track independently by moving the feet sideways. Retaining the old ±25° front mounts at a 103 mm radius would put those hip axes only about ±43.5 mm from the centreline.

The candidate shared with the simulation task places hip axes at ±45°/±135°, radius 103 mm, and adds a real, mirrored 30 mm transverse coxa offset. With wheel planes parallel to the body, this gives about 206 mm track before any additional hub offset. The CAD needs handed left/right offset carriers. Front and rear leg yaw conventions also need explicit signs. These are proposed geometry values, not validated dimensions.

The 30 mm coxa offset adds a bending moment to the yaw bearing stack. Two vertically separated bearings and a metal shaft should react that moment. The servo horn should transmit drive torque; its internal bearing should not be the only structure carrying the robot.

## Remote-drive choices

| Topology | Benefit | Cost or failure mode | Decision |
|---|---|---|---|
| Direct knee servo | Simple load path, no remote transmission | Distal mass, exposed wiring and joint impacts | Keep as a comparison baseline. |
| Existing parallelogram | Real local prototype and familiar assembly | Three passive pivots, narrow verified ROM, accumulated play, toggle/singularity and buckling checks | Useful bench evidence; do not simply lengthen it for stairs. |
| 1:1 synchronous belt along femur | Constant geometric ratio, broad rotation range, low distal mass | Elastic deflection, pulley tooth/profile quality, belt tension and bearing side load | Preferred new candidate. |
| Unequal pulleys along femur | Knee reduction in one belt stage | Changes actuator coupling; larger knee pulley adds distal mass and collision envelope | Evaluate only with the correct mapping below. |
| Printed spur gear chain down femur | No purchased belt length | Several meshes accumulate backlash; mass and shaft supports along thigh | Inferior first candidate for responsiveness. |
| Cable or tendon | Small pulleys and low moving mass | Pretension, terminations, creep, hysteresis, capstan slip | More development risk than an available timing-belt setup. |

A printable pulley is reasonable for a fit and low-load experiment if its tooth profile matches the real belt. A printed flexible timing belt is not an equivalent replacement for a reinforced purchased belt. Gates distinguishes belt tooth profiles, positioning backlash, pulley size, and load/tension effects; HTD and GT profiles should not be mixed or treated as having identical positioning behavior. Select actual pitch, width, tooth count, and length using the manufacturer's torque tables and corrections. [Gates light power and precision drive manual](https://www.gates.com/content/dam/documents-library/catalogs/light-power-and-precision-manual.pdf).

### Coupling that the controller and simulator must use

Define `h` as femur angle and `k` as knee angle relative to the femur. Tibia absolute angle is `h + k`. Define reduction ratios as motor angle divided by output angle, and use signed angles consistently.

For a 1:1 open belt along the femur and a separate proximal knee reduction `rK`:

```text
sH = rH * h
sK = rK * (h + k)

motor_torque_K = joint_torque_K / rK
motor_torque_H = (joint_torque_H - joint_torque_K) / rH
```

The last two equations follow from virtual work before adding losses. The hip actuator is not loaded as an independent direct-drive hip. Use signed torques, rather than subtracting absolute values. Corresponding motor speed limits apply to `rH*h_dot` and `rK*(h_dot + k_dot)`.

If the reduction is instead achieved by unequal pulleys on the rotating femur, with driven/driver pitch radius ratio `N` and no separate proximal reduction:

```text
sK = h + N * k
```

That is not `N*(h + k)`. A proximal reduction `P` would give `sK = P*(h + N*k)`. Coupling errors here invalidate torque, speed, and backlash predictions together. The same matrix must drive Fusion motion poses, simulated actuation, and the eventual hardware controller.

### Packaging the belt and bearings

Use opposing short trunnions on the common hip axis: one drives the femur, the other drives the knee-input pulley. Stop the shafts before they meet. Each trunnion needs independent support in the yaw carriage. This is easier to manufacture than pretending two solid shafts can occupy the same axis or inventing a tiny hollow shaft with unspecified bearings inside it.

As an initial envelope, reserve about 75 × 90 × 65 mm for the hip-pitch/knee module, plus yaw mounting space, and 24–30 mm overall thigh transmission width for a 9 mm belt, cheeks, bearings, running gaps, and retainers. This is an assembly study envelope. It must be checked against all four neighboring pods and the body before use as a dimension source.

Pulley candidates of 36–48 teeth at 2 mm pitch or 24–32 teeth at 3 mm pitch give pitch diameters around 23–31 mm. These are packaging candidates, not rated selections. At 1.5 N·m and 15 mm pitch radius, belt tension difference is 100 N. At 3 N·m it is 200 N. Installation pretension adds bearing load on top of transmitted load. A small pulley can therefore make the bearing housing and servo-support problem much worse even when its teeth appear to fit.

For equal pulleys, belt pitch length is `2*C + pi*D`, with centre distance `C` and pitch diameter `D`. Choose an available closed belt, then set the geometry from its pitch length. Put an adjustable idler or screw-driven tension block on the rigid femur so tension remains unchanged as the whole leg moves. Avoid moving the knee joint centre to tension the belt unless that altered link length is measured and propagated into the model. Keep toothed contact on a toothed idler; a back-side idler requires the belt maker's minimum bend diameter. Provide flange and cable clearances through the full stroke.

A 1:1 belt crossing from hip axis to knee axis does not need a length-changing path because those axes are fixed in the femur. The wheel motor at the foot avoids the much harder second belt crossing the moving knee.

## Backlash, stiffness, and validation

The actuator's encoder measures upstream of external clearances. Add horn slip, clamp motion, shaft fit, gear clearance, belt deformation, bearing play, and printed structural compliance to the servo contribution.

For a 270 mm extended leg, 0.5° rotation corresponds to about 2.36 mm tangential motion. With a 1:1 remote knee, hip and knee motor errors are coupled: `delta_k = delta_sK/rK - delta_sH/rH`. Joint errors must come from this mapping; assigning three unrelated zero-mean joint noises would conceal important correlations. Bound worst-case errors and separately simulate reversal hysteresis, because random noise does not represent backlash.

Use joint-load reversal tests with the wheel held against a measured force. Record encoder position, physical wheel movement, response delay, overshoot, motor current, and temperature. The first test must distinguish structure movement from servo gearbox play. Calibrating only unloaded angle tracking would miss the problem that made the previous cradle wobble.

## Manufacturing and assembly provisions

Print the long femur and tibia load paths flat in the XY plane. Use broad cheeks, local ribs, generous fillets, and through-bolts so bending loads do not peel a narrow upright layer stack. Treat printed Z-direction strength and creep as separate, lower properties in structural screening. Do not assign bulk isotropic PETG strength to a sliced part.

Bearing outer races seat against a shoulder and are retained by a cap. Inner-race spacers and smooth metal shafts carry clamp load without crushing seals or locking the bearing. Heat-set inserts attach covers and brackets; they are not rotating journals. A shoulder screw is useful only if the smooth shoulder, not its threads, runs in the race. The chosen bearing quantities may exceed the user's approximate ten-per-size stock if every joint uses the same size; the complete assembly BOM must count both supports at every shaft.

The prior assortment identifies 693, 623, 685, 624, 687, 627, 626, and 608 bearings, with seven unique housing diameters. `fusion360/docs/BEARING_KIT_STANDARD_DIMENSIONS.md` records nominal dimensions and first-party NSK links. Those catalog sizes do not prove the contents or quality of the delivered assortment. Measure the installed examples.

Design the assembly order before closing a shell:

1. Fit inserts into accessible printed housings; install bearings and retainers.
2. Install supported trunnions and output pulleys; confirm independent rotation.
3. Install servo horns and centre screws while tools can reach them, then add servo mounts and couplings.
4. Fit femur, knee axle, tibia, and belt; set and record belt tension.
5. Install wheel motor, wheel support, hub, and tire; inspect wheel/shin clearance.
6. Add cable loops and strain relief while the whole stroke remains visible.
7. Cycle the mechanism, then add removable cosmetic covers.

## The two coupon rounds

Use the first bed to test all interface families, with few separate pieces: bearing diameters in shared strips, one real-width selected bearing boss with its retainer, insert bores, screw/nut access, a servo datum/clamp slice, the supplied horn pattern, a short pulley tooth-fit specimen, and a shaft/hub clamp specimen. Keep physically different fits on separate named parameters. The successful thin 13.25 mm ring and failed full-width bearing boss show why one representative full boss belongs on this bed.

Print these in the intended final material, orientation, nozzle, layer height, and compensation settings. A PLA result should not silently become PETG production compensation. Mark every station and record measured hardware size, CAD size, result, and insertion/removal behavior. Include visible references for XY orientation.

The second bed should contain only failed or ambiguous interfaces and one combined joint stack using selected values. The full leg release follows those measured results. A coupon bed cannot establish fatigue strength, servo thermal limits, or reliable stairs; it can prevent predictable fit and access errors before a large print.

## Fusion build path and audit cautions

The repository already demonstrates native BRep creation with `TemporaryBRepManager`, persistence into a component `BaseFeature`, and assembly via `asBuiltJoints`, followed by `.f3d`, STL, and 3MF exports. The wrappers require execution inside Fusion with an empty active design. No callable Fusion tool or external execution bridge was found during this audit. Installed API definitions are available at `<LOCAL_HOME>/AppData/Roaming/Autodesk/Autodesk Fusion 360/API/Python/defs/adsk`.

A new assembly should use one component per physical rigid link, named joint axes, explicit bought-part references, physical materials, and separate printable components. Use native sketch/extrude/revolve/hole features for frequently tuned interfaces. Parameter tables alone do not make generated BaseFeature geometry update when edited: the existing generators must rerun to rebuild shapes. [Autodesk BRepBody API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_BRepBody.htm), [Autodesk AsBuiltJointInput API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_AsBuiltJointInput.htm).

Do not reuse `fusion_build_rev_f.py::_intersection_mm3` unchanged as a clearance proof. It reports zero intersection when a Boolean operation fails or when property access raises an exception. Those outcomes need an explicit unknown/error result. Copy bodies in assembly context or apply occurrence transforms before intersecting them. Check continuous swept motion, cable envelopes, fastener access, and minimum separation as well as nominal solid overlap. Exported parts also need manifold and disconnected-shell checks because the older carriage already demonstrated a BRep-to-mesh failure.

The next concrete CAD decision is the bearing-supported hip module and its accessible belt path. Only after its envelope, transmission mapping, and coupled torque/speed sweep agree should the four pods, body ribs, low central battery tray, phone mounts, and MIST shell be detailed around it.
