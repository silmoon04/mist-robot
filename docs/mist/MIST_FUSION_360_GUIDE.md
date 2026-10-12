# MIST in Autodesk Fusion — complete beginner guide

**Current baseline:** MIST v1, Layout A (all direct), checked against Autodesk
Fusion `v2704.1.23` on 2026-07-12.

This is the entry point for creating the MIST mechanical design from a blank
Fusion file. Use the [polished interactive guide](MIST_FUSION_360_GUIDE.html) for
the best reading experience, parameter visualizer, searchable chapters, image
zoom, and persistent build gates. The detailed source chapters are linked below
for plain Markdown reading and review.

> **Important:** this guide is deliberately not a recipe for blindly copying
> the six AI posters. They show a Ø220 body, equal 90° leg spacing, passive feet,
> two-joint legs, and invented Fusion dialogs. Current MIST is Ø180, mounts at
> `+25°`, `-25°`, `+109°`, `-109°`, and has q1 roll, q2 hip, q3 knee, plus one
> driven wheel per leg. Every poster is labelled concept-only in the guide.

## Read this first

Source precedence is strict:

1. A physical part measured with calipers and a material-matched coupon.
2. [MIST Fusion master dimensions](MIST_FUSION_MASTER_DIMENSIONS.md).
3. `sim/js/kin.js` for the coordinate frame and joint-axis convention.
4. Current inventory, material, print-test, and build-phase docs.
5. Older CAD/variant reports for lessons, not current dimensions.
6. AI images for appearance only.

The guide uses three parameter classes:

- **Locked baseline** — current MIST geometry. Changing it is a project-level
  redesign, not casual visual tuning.
- **Measure on arrival** — hardware envelope/interface values that must be
  replaced from the actual item.
- **Provisional/calibration** — explicit starting choices such as shell wall or
  pocket clearance, which need coupons and validation.

## What you will build

The beginner route uses a single **Hybrid Design** in **Parametric Modeling
Mode**. The dependency chain is one-way:

```text
named user parameters
    ↓
small skeleton sketches and origin-based datums
    ↓
components and component-owned geometry
    ↓
joint origins at real servo axes
    ↓
revolute joints, limits, and four associative leg instances
    ↓
pose, interference, cable, mass, print, and release checks
```

This is intentional. A separate Part + Assembly architecture is cleaner for a
team or reusable product family, but a parent Assembly parameter table cannot
simply drive every external child file. The one-file Hybrid route removes that
reference-management problem while a beginner learns the geometry.

## Canonical quick reference

| Item | Current value | Meaning |
|---|---:|---|
| Barrel | Ø180 × 260 mm | Cylinder only; dome/handle are not dimensioned yet |
| q1 axis | R100, Z35 mm | Body axis to hip-roll axis; Z from barrel bottom |
| q1→q2 offset | 32 mm | Radially outward |
| Femur | 110 mm | q2 axis to q3 axis |
| Tibia | 70 mm | q3 axis to wheel axle, not to ground |
| Wheel | Ø70 mm | Tire outside diameter |
| Mount rays | ±25°, ±109° | Measured CCW from +X forward |
| Beam | 20 × 14 mm | Printed link cross-section baseline |
| Neutral pose | body bottom 148 mm; stance R176 mm | Pose reference, not part geometry |
| ROM | q1 ±60°; q2 −35°…+110°; q3 ±135° | Verify signs from each local joint frame |
| STS3215 body | 45.2 × 24.7 × 35 mm | Body only; ears, horn, shaft, cable still need measurement |

Download/import the companion
[parameter CSV](fusion-guide/mist-fusion-parameters.csv), but first export one
small parameter set from your own Fusion build and compare its header. Autodesk
supports parameter CSV import/export; the exact accepted header should be
verified against the installed build before importing a large table.

## Detailed chapters

1. [Truth, current Fusion UI, components, parameter table, and skeleton](fusion-guide/drafts/01_ui_parameters.md)
2. [Hardware envelopes and the complete `base_link`/body workflow](fusion-guide/drafts/02_body_envelopes.md)
3. [One real MIST leg and the four-leg assembly](fusion-guide/drafts/03_leg_assembly.md)
4. [Motion, collision, cables, mass, printing, export, and release](fusion-guide/drafts/04_validation_export.md)
5. [Parameter effects, equations, clearances, sensitivities, and A–E tradeoffs](fusion-guide/drafts/05_parameter_tradeoffs.md)

Supporting records:

- [Research and version verification](fusion-guide/RESEARCH_AND_VERIFICATION.md)
- [Guide completion/verification state](fusion-guide/PROGRESS.md)
- [AI/Autodesk asset builder](../../tools/docs/build_fusion_guide_assets.py)

## Beginner milestone ladder

Do not model the entire robot before proving the interfaces. Stop at each gate.

1. **File gate:** saved Hybrid Design, Parametric Modeling Mode, millimetres,
   +X forward/+Y left/+Z up.
2. **Parameter gate:** all locked parameters and derived expressions recompute
   with no Timeline warnings.
3. **Skeleton gate:** three small fully constrained sketches define top layout,
   leg kinematics, and height envelope.
4. **Measurement gate:** actual servo body, ears, axis, horn, cable exits,
   battery, phone/case/USB, and board connectors are recorded.
5. **Coupon gate:** pocket, horn, hole, pin, insert, cable, and wheel-interface
   coupons pass in the intended material and orientation.
6. **One-joint gate:** a real centred servo, horn, idler/bearing support,
   fasteners, and printed bracket move without bind or case twist.
7. **One-leg gate:** q1/q2/q3/wheel components move through limits; cable sweep,
   fasteners, body, wheel, and tibia remain clear.
8. **Four-leg gate:** associative occurrences sit at the four explicit rays;
   no 4×90° circular pattern or mirrored geometry was substituted.
9. **Packaging gate:** battery is retained and removable; fuses/key/connectors
   are reachable; the unresolved four-branch bus junction still has reserved
   service space.
10. **Release gate:** representative and extreme poses pass targeted
    Interference checks; section views, mass/CoM, 3MF units, drawings, and slicer
    previews have been reviewed.

## Two unresolved decisions you must not hide

### Fixed-wheel heading

The current wheel axes follow the knee axes, so each conventional wheel rolls
approximately radial to its physical mount. Four fixed radial headings at
`±25°/±109°` cannot perform ordinary no-slip translation and yaw. Select one:

- accept low-speed skid/scrub on compliant TPU (simple, inefficient, more wear);
- use omni/caster-style contact (less scrub, less lateral grip/control);
- add a steering degree of freedom (best kinematics, more servo/mass/control);
- make pod azimuth mechanically adjustable (useful prototype, weaker interface).

Changing a simulated “drive stance” cannot rotate a fixed chassis pod. Keep the
azimuth sketches and mount interfaces editable until this decision is tested.

### Servo-bus branching

The body needs four serviceable leg-root signal/common-ground paths plus raw-3S
power injection. Current docs also consume the coxa servo’s second connector for
the onward daisy chain, and the BOM has no proven 1→4 hub/Y-splice. Reserve the
junction volume and connector access; do not freeze cable slots around an
unresolved schematic.

## Clearance language used in this guide

Never write “0.3 mm clearance” without its geometry:

```text
diametral_gap = hole_diameter - pin_diameter
radial_gap = diametral_gap / 2
pocket_width = measured_part_width + 2 × side_gap
```

The existing 5.0 mm peg coupon with 5.1–5.6 mm holes labels **diametral** gaps of
0.1–0.6 mm. The parameter CSV treats `pocket_clearance_per_side` and
`pin_radial_clearance` as one-sided/radial gaps, then keeps
`hole_diameter_comp` separate as printer-process correction. Coupons override
all starting values.

## How parameter changes spread

| Change | Direct effect | Less obvious cost |
|---|---|---|
| Increase `body_dia` | More interior and wider shell | q1 radius moves by half the change; mass/yaw inertia/print split/phone curvature change |
| Increase `body_h` | More vertical packaging | shell centre rises; tipping and cable length worsen; ground clearance does not increase |
| Increase `d1` | More hip packaging and stance width | bracket leverage, inertia, collision envelope, and real mass rise |
| Increase `femur` | More reach/height | bending grows roughly with length³; knee/distal mass has more leverage |
| Increase `tibia` | More ground reach | wheel and servo leverage, collision sweep, and cable length rise |
| Increase `wheel_dia` | More axle/obstacle clearance and speed | less tractive force for a given torque, more inertia, larger sweep |
| Increase `beam_t` in bending direction | Much higher stiffness | mass/print time/joint width rise; layer orientation can dominate |
| Increase `stance_r` | Larger static support polygon | reach and torque rise; stride headroom disappears |
| Move a wheel servo inward | Lower distal inertia | belt/pulley/bearing/tensioner/backlash/maintenance are added |

Concrete simulator sensitivities around the rounded baseline:

- Femur `110→120 mm`: modeled flex `0.582→0.735 mm`.
- Beam thickness `14→16 mm`: about `+26 g`, flex `0.582→0.393 mm`.
- Stance radius `176→196 mm`: static tip angle `24.9→26.7°`, but pose-battery
  worst torque `21.1→29.9%` and the 86% reach-headroom gate fails.

These are model sensitivities, not physical certification. Print anisotropy,
fastener slip, backlash, cable forces, impacts, and tire compliance are not fully
represented.

## Concept-art index

All originals remain unmodified under `mist_3d/mist_fusion_guide/`:

| Sheet | Safe use | Main correction |
|---|---|---|
| [01 — setup/reference](../../mist_3d/mist_fusion_guide/c9f98018-dc76-4914-9e09-42f10d75449e.png) | Target appearance crop | Ø220 and its parameter table are not MIST values |
| [02 — body/lid](../../mist_3d/mist_fusion_guide/688908d9-0bdb-4bbb-b650-f1a0a5254c78.png) | Revolve/shell concept | Shell/lid/handle dimensions are provisional |
| [03 — front module](../../mist_3d/mist_fusion_guide/23794522-88e1-4b32-8522-f36c110bb668.png) | Composition only | Use a tangent datum and the real portrait phone envelope |
| [04 — leg](../../mist_3d/mist_fusion_guide/2ee53a2c-b6a6-414f-bd26-0ddb6c07c57e.png) | Anatomy warning | It omits q1 and the wheel and gives conflicting link sizes |
| [05 — assembly](../../mist_3d/mist_fusion_guide/2dc4e473-bd40-4c91-8d6c-b93aed0190e5.png) | Component concept | 90° circular placement is wrong |
| [06 — motion](../../mist_3d/mist_fusion_guide/d9363efa-0ea2-4767-89ec-a16e4b8b0fc9.png) | Motion intent | Synthetic UI, obsolete Ground wording, incorrect limits/tool paths |
