# MIST Fusion 360 master dimensions — single source of truth for CAD

Created 2026-07-12. Numbers come from `sim/js/config.js` + the Layout A column of
`MIST_ACTUATOR_LAYOUT_STUDY.md` (build v1 = all-direct actuation). The six
concept sheets in `mist_3d/mist_fusion_guide/` are AI art with
**inconsistent, invented dimensions** (including a Ø220 body, 90° leg spacing,
and incomplete leg anatomy) — use them for composition only, never for
measurements or Fusion UI evidence.

Companion: [`MIST_FUSION_360_GUIDE.md`](MIST_FUSION_360_GUIDE.md) explains the
current Hybrid Design workflow, parameter dependencies, component/joint model,
validation gates, image corrections, and the open mechanical decisions.

Enter the "User parameters" table below into Fusion (Modify → Change Parameters)
before sketching anything. Every sketch/feature should reference these names, so
a geometry change from the sim propagates through the whole model.

## 1. Fusion user parameters

| Parameter | Value | Unit | Source / note |
|---|---:|---|---|
| `body_dia` | 180 | mm | sim `body.cylD` (barrel outer ⌀) |
| `body_h` | 260 | mm | sim `body.cylH` (cylinder, excl. dome/handle) |
| `leg_mount_h` | 35 | mm | hip-roll axis height above cylinder bottom |
| `mount_standoff` | 10 | mm | shell surface → hip-roll axis start (axis point sits at R = body_dia/2 + mount_standoff = **100 mm** from body axis) |
| `d1` | 32 | mm | hip-roll axis → hip-pitch axis, along the roll axis (Layout A optimized) |
| `femur` | 110 | mm | Layout A gives 111; optimizer noise is ±few %, round to printable numbers |
| `tibia` | 70 | mm | knee axis → **wheel axle** (not ground) |
| `wheel_dia` | 70 | mm | TPU tire OD; on level ground, contact Z = axle Z − 35 mm |
| `front_az` | 25 | deg | front legs at ±25° from +X (forward) |
| `rear_az` | 109 | deg | rear legs at ±109° |
| `beam_w` | 20 | mm | printed leg beam cross-section width |
| `beam_t` | 14 | mm | printed leg beam cross-section thickness |
| `pocket_clearance_per_side` | 0.25 | mm | gap at each opposing pocket face; pocket = measured part + 2× this value — **coupon-tune** |
| `pin_radial_clearance` | 0.25 | mm | starting radial pin-to-bore gap; bore adds 2× this value before process compensation — **coupon-tune** |
| `hole_diameter_comp` | 0.20 | mm | starting process correction for printed hole undersize, separate from intentional fit — **coupon-tune** |
| `motion_clearance` | 2.0 | mm | starting air gap around swept moving envelopes; validate with cables/fasteners throughout ROM |
| `servo_l` | 45.2 | mm | STS3215 body (Feetech/Kamami datasheet) |
| `servo_w` | 24.7 | mm | |
| `servo_h` | 35 | mm | body only, excl. horn + cable |

Reference pose (not part dimensions): neutral stand = body bottom 148 mm off
ground, feet at stance radius 176 mm. The Layout A study reported 171 mm with
its 111/70 links; the rounded 110/70 CAD should scan roughly 170–171 mm and
record the highest pose that actually passes reach, joint, cable, and collision
checks. Do not treat 171 mm as a guaranteed stand height.

## 2. Frames, joint chain, and axes (matches `sim/js/kin.js` — use the same in Fusion AND URDF)

World frame: **+X forward (phone face), +Y left, +Z up**, ground z = 0.

Per leg at azimuth φ (25/−25/109/−109° CCW from +X), mount frame: Xm = radial
outward, Ym = tangential CCW, Zm = up. Chain:

1. **q1 hip roll** — revolute about **Xm** (radial, horizontal). Axis point: R=100 mm from body axis, 35 mm above cylinder bottom.
2. offset **d1 = 32 mm outward along Xm** → hip-pitch axis point.
3. **q2 hip pitch** — revolute about the rolled −Ym. Zero = femur pointing straight down; +q2 swings the foot outward/forward in the leg plane.
4. **q3 knee** — revolute, axis parallel to hip pitch. Zero = tibia in line with femur. Config default `kneeSign = -1` (spider look: knee bows up/out, tibia dives down to the wheel).
5. **wheel** — continuous joint, axis = knee axis, disc ⌀70 centered on the axle at the tibia end; on level ground the contact point is axle Z minus 35 mm.

ROM limits (put these as Fusion joint limits, from sim `rom`): roll ±60°,
hip −35°…+110°, knee ±135°.

## 3. Component / link naming (do this from day 1 — URDF exporters need it)

One Fusion **component per rigid link**, joints defined exactly on the axes above:

| Link component | Contains |
|---|---|
| `base_link` | chassis plate, barrel, dome, battery/electronics placeholders |
| `{FL,FR,RL,RR}_hiproll` | hip-roll servo output bracket (the d1 segment) |
| `{FL,FR,RL,RR}_femur` | femur beam + knee servo |
| `{FL,FR,RL,RR}_tibia` | tibia beam + wheel servo carrier |
| `{FL,FR,RL,RR}_wheel` | hub + tire |

Joints: `{leg}_q1_roll`, `{leg}_q2_hip`, `{leg}_q3_knee` (revolute with limits),
`{leg}_wheel` (continuous/revolute unlimited). The axis convention permits one
leg design at all four locations without mirrored part geometry. Validate that
assumption in the current assembly, then insert four associative instances at
the explicit azimuths; do not use a four-instance circular pattern.

Servo mounting uses the servo ears and metal horn. A previously referenced
`build_printable.py` and its `VERIFY` block are absent from this workspace.
Treat ear, axis, horn, auxiliary-support, and cable-exit geometry as unknown
until checked with calipers and a printed coupon.

## 4. Masses (represent in Fusion with physical materials or calibrated proxy geometry)

| Item | Mass | How in Fusion |
|---|---:|---|
| STS3215 servo ×16 | 55 g each | assign a calibrated material/density to the envelope or add a hidden mass-proxy body; verify against the scale |
| Wheel (TPU tire + PETG hub) | 60 g | separate hub/tire materials or a calibrated mass-proxy body |
| Printed structural parts | PETG ρ=1.27 g/cm³ | use actual materials, then calibrate effective density/proxy geometry from sliced and weighed coupons; the simulator's `structFactor=0.7` is **not** a 70% infill instruction |
| Shell (barrel+deck+lid) budget | 900 g | design target from sim `body.shellMass` |
| Battery HOOVO 3S 2200 | 174 g | placeholder ~104×34.5×24.5; place at explicit CAD XYZ after measurement. Simulator `batteryH=40` is mass-centre Z, not pack thickness, and `batteryR=0` is currently centred |
| Phone Mi 9 SE + frame | 205 g | box 147.5 × 70.5 × 7.45, front face, center ~170 mm up |
| Electronics (PDB/ESP32/UBEC/fuses/adapter) | 350 g | boxes near chassis plate (~15 mm up) |
| Harness allowance | 150 g | distributed, ~60 mm up |
| **Total target** | **~3223 g** | Layout A optimized total — check Fusion Properties → CoM against this |

Placeholder envelope boxes to model into a `_components` folder (sizes in
`MIST_MATERIAL_DIMENSIONS_MASS.md`): battery, phone, ESP32 DevKitC
(~55×29×13), bus servo adapter (42×33), UBEC (43×21×8), 5 fuse holders
(45×20×15), 4× 4700 µF caps (⌀16×30, one per leg root), VL53L0X (~21×18×3).

## 5. Design rules carried over from earlier findings

- **Leave a belt run + free axle space in the tibia** — Layout B (wheel servo at
  knee) must be a drop-in retrofit (study recommendation).
- Wheel/shin collision was a real bug in printable v1 — push the hub outboard
  on a stem; check interference in Fusion across full ROM.
- Phone window: concept model was 14 mm too narrow for the Mi 9 SE — size the
  cutout from the phone box, portrait orientation (landscape costs 33 mm of
  barrel interior).
- Caps at leg roots, fuses reachable, battery swappable without tools if
  possible; route servo cables through slots in brackets (bus daisy-chain).
- Neptune 4 Pro bed: 225 × 225 × 265 — barrel fits whole but consider splitting.
- PETG for anything touching a servo or carrying load; PLA for fit-check
  coupons only; TPU for tires.
- Tolerances: print a coupon (servo pocket + horn recess + pin) and tune
  the interface-specific clearance/compensation parameters before committing to
  full parts. Never reuse one ambiguous `fit_clearance` for every interface.

## 6. Open gates before freezing production geometry

- **Wheel heading:** conventional fixed wheels whose axes remain parallel to the
  knee axes roll approximately radial to their fixed mount rays. Four headings
  at ±25°/±109° cannot provide ordinary no-slip translation/yaw. Select and test
  low-speed scrub, omni/caster contact, added yaw steering, or adjustable pods.
  A simulator pose cannot rotate a physical chassis mount.
- **Leg-root bus branching:** the current body needs four serviceable
  signal/common-ground branches plus raw-3S power injection, but the existing
  daisy-chain/BOM does not define a proven 1→4 junction. Reserve access and
  envelope space; do not freeze cable slots until the harness is drawn.
- **Servo interfaces:** body dimensions are useful seeds; ears, axis position,
  auxiliary shaft, horn bolt circle/recess, centre-screw access, and both cable
  exits remain measurement gates.
- **Manufacturing interfaces:** shell split, deck/ribs, lid, handle, mount
  fasteners, inserts, wheel width/hub/bearing, and board mounting remain explicit
  provisional choices in the full guide, not hidden AI dimensions.
