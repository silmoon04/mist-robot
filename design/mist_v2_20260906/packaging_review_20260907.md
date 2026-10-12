# MIST proximal leg packaging review, 7 September 2026

The four-leg package does not yet support a full-range clearance claim. The original 75 x 90 x 65 mm hip allowance nearly touches the barrel in straight drive, and the wider opposed-trunnion draft has a specific neighbouring-servo collision within the configured motor travel. A finished single leg and a body root fixture remain useful build targets; copying this draft around the body would preserve a known conflict.

**Mode correction after this screen:** the manufacturer's C018 A/0 page5 supports multi-turn absolute positioning up to plus/minus seven turns, with the turn count lost on power-off. The travel comparisons here apply to the configured350-degree single-turn assumption, not a physical motor stop. See [servo_contract_20260907.md](servo_contract_20260907.md). The model's broad yaw/hip ranges are design inputs, not exact angles requested by the user. The envelope and solid-clearance checks remain necessary in either mode.

This review used `simulation/parameters.json`, `mechanical_audit.md`, `cad/output/body_recipe.json`, `cad/output/body_geometry_report.json`, `coupons/fit_parameters.json`, `coupons/README.md`, and `assembly_and_wiring.md`. The larger draft dimensions came directly from the leg implementation agent before its final recipe. No CAD, calibration or hardware was changed. The independent, standard-library calculation is `packaging_screen_20260907.py`; its numerical output is `packaging_screen_20260907.json`.

## Geometry and specific conflicts

The yaw axes are at R103 mm and azimuths +45/-45/+135/-135 degrees. Adjacent axes are 145.66 mm apart. Their clearance to the nominal R90 barrel is only 13 mm. The pitch axis moves with yaw, offset 35 mm forward in the leg plane and a handed 30 mm transverse distance.

For a conservative 75 mm radial by 90 mm transverse box centred on that pitch axis:

| Screen | Result |
|---|---:|
| Closest box radius in straight drive | 91.06 mm, only 1.06 mm beyond the barrel |
| Closest radius at FL yaw +100 degrees | 26.44 mm |
| Furthest corner distance from yaw axis | 104.31 mm |
| FL/RL box overlap at yaw +78/-78 degrees | 49.57 mm minimum separation deficit along tested SAT axes |
| Height if the 65 mm box is centred on the current yaw plane | Body-bottom Z2.5 to Z67.5 mm |

The height overlaps the 0 to 5 mm lower deck and the 61 mm phone deck level wherever their horizontal footprints meet. The front lower shell starts at Z82, but the rear shell remains below that level outside its two hip windows and rear connector opening. The rear hip windows cover radial 72 to 126 mm, transverse +/-44 mm and Z6 to Z82 mm in their fixed mounting frames. They cannot be treated as a moving clearance volume. The battery, core posts, phone deck and fasteners occupy the region behind those windows.

These box overlaps reject the reserved-volume layout; they do not prove that every future detailed shape collides. Straight-drive clearance is also too small to absorb covers, cabling, fasteners, runout and actual dimensions without a detailed check.

The implementation draft is wider. Its hip bearings extend from pitch-local Y-45 to -22 mm and remote-input bearings from +35 to +55 mm. Those bearings alone span 100 mm. Its two servo cases occupy Y-74 to -39 and +59 to +94 mm, a 168 mm combined width. Using 45.2 mm along X, 35 mm along Y, case centre X30 mm beyond the pitch axis, and mirroring the complete stack gives:

- The straight-drive cases clear the barrel: minimum radius 118.78 mm for the hip case and 198.67 mm for the remote case.
- The FL and RL remote cases overlap at yaw +22/-22 degrees, with a 45.55 mm minimum separation deficit along the tested separating axes. Both poses are 67 degrees from their respective drive headings, requiring only 134 degrees of yaw motor travel at 2:1. This collision therefore survives the motor-travel filter.
- A sampled RL hip case at yaw +85 degrees also enters the remaining rear shell near (-86.93, +23.29) mm at body-bottom Z35. The wider draft needs actual component and shell intersections, not just a cylinder check.

The screen tests 1-degree body samples and 2-degree pair combinations. It omits gears, housings, cables and moving links, and it assumes the draft's complete handed mirror. Its positive overlap examples are actionable; absence of an overlap in this screen is not final clearance evidence. Re-run against the completed recipe and continuous sweeps before using a range as a hardware limit.

## Reduction and reachable range

With the configured 350-degree usable motor span, the actuator mapping limits motion before mechanical clearance is considered.

| Requested output span | Reduction | Required motor span | Consequence |
|---|---:|---:|---|
| Yaw -100 to +100 degrees | 2 | 400 degrees | Cannot cover the whole requested range with any neutral |
| Hip -40 to +125 degrees | 2 | 330 degrees | Fits only with a suitable neutral and endpoint margins |
| Hip -40 to +125 degrees | 3.5 | 577.5 degrees | Maximum possible hip span is 100 degrees |
| All combinations of hip/knee rectangular limits, expressed as absolute tibia angle | 2 | 600 degrees | Must use a coupled allowed region rather than independent joint intervals |

The calculated straight-drive hip/knee angles are 58.06/-84.96 degrees. If motor travel is centred on that pose, the hip reaches -29.44 to 145.56 degrees at 2:1, or 8.06 to 108.06 degrees at 3.5:1, before intersecting the configured joint limits. A 2:1 hip neutral near 42.5 degrees can cover the nominal -40 to +125 range; retaining the drive pose as motor centre cannot. For the remote 1:1 belt topology, apply the limit to `2*(hip+knee-neutral_sum)`.

A module-1 20/40 tooth spur pair has a 30 mm centre distance and 42 mm driven outside diameter. Keeping the 20-tooth pinion for 3.5:1 gives 20/70 teeth, a 45 mm centre distance and 72 mm driven outside diameter. That adds 15 mm to the driven radius and servo offset. A full gear centred at current pitch Z35 reaches body-bottom Z-1. A sector gear changes that envelope only after its required tooth coverage and end stops are designed. Two stages can reduce individual gear diameters but add supports, backlash and losses. At unchanged motor speed, 3.5:1 gives 57% of the 2:1 output speed. The ratio change is a mechanical redesign, not a parameter-only fix.

## Bearing allocation and the root

The external support minimum is ten bearings per leg: two yaw, two hip trunnion, two independent remote-input trunnion, two knee and two wheel. Four legs need at least 40. Every extra two-bearing intermediate shaft per leg adds another eight; one single-bearing idler per leg adds four.

The proposed 608 yaw, 687 hip and 685 remote pairs consume eight of each size. With approximately ten per size, selecting 687 again for every knee requires sixteen, approximately six short. Selecting 608 again for every wheel produces the same shortfall. Choose shaft size from load and assembly requirements, then count the purchase delta. A 627 is 7 x 22 x 7 mm and a 608 is 8 x 22 x 7 mm; their common housing fit does not make their shafts or inventory interchangeable.

The current fit file reserves 19/22/30 mm boss ODs for 685/687/608 respectively. These exceed the bearing reference cylinders. All candidate seats remain unvalidated. The hip draft has 18 mm bearing-centre separation and the remote input 15 mm; outer-race caps, inner-race spacers, gear hubs and removable shaft retention must fit outside or between these actual faces.

The lower-deck tabs extend radially from 71 to 106 mm. A yaw axis at R103 has only 3 mm of tab beyond its centre; a 30 mm boss reaches R118, overhanging the tab by 12 mm. The two existing 4.4 mm clearance holes lie at R78 and R98 on one radial line. The deck top is Z5 and the yaw plane Z35, requiring a 30 mm rise.

Define the single-leg root as a removable bearing cassette on an extended, reinforced deck tab or bench plate. It needs two separated yaw bearings, a metal shaft, axial retention and a bracket that transfers bending into the deck. Specify the mating datum, actual through-bolt pattern, underside washer/nut and tool clearance, upper support attachment, cable passage and assembly order. The existing two holes are provisional locating geometry. The cosmetic barrel and lid handle do not provide the missing load path. The structural review must size the cassette, span, bolts and deck together.

## Practical design alternatives

1. Keep the yaw servo body-fixed and both pitch actuators on the yaw carriage, but redesign their placement. The opposed axial stack is the source of the 168 mm width. Fold or stagger the cases along X/Z and model the required gears or belts explicitly. This preserves the present absolute-tibia mapping if the drive path remains equivalent. Raising all eight 55 g pitch/remote servos by 50 mm raises the estimated 3.954 kg robot's overall COM by about 5.56 mm before bracket mass. Vertical staggering can solve a case collision while creating a deck or phone collision, so reserve those volumes first.
2. Keep the yaw servo body-fixed and hip servo on its carriage; place the knee motor near the hip end of the femur, with its belt running to the knee. This remains a proximal motor layout and removes the independent knee-input trunnion from the crowded yaw cassette. A femur-mounted drive generally changes the motor mapping to relative knee motion; rederive it from the actual routing and update CAD, simulation and control together. A 55 g motor 40 mm down the femur adds up to 0.022 N m of gravity moment before its mounting/transmission mass. The added moving mass needs accounting, but this is a more direct route to a first assembled leg.
3. Move the complete pods farther out or below the deck. This gives space at the cost of body width, longer root loads or reduced ground clearance. For the old box, a sufficient all-angle cylinder clearance bound is yaw radius at least 194.31 mm before a running gap; merely increasing R103 a little cannot guarantee clearance. A 65 mm-high pod placed wholly below body-bottom Z0 needs its centre below Z-32.5, 67.5 mm lower than the current pitch plane before clearance. Such changes alter the silhouette and all foot/body geometry and should be explicit design variants.

Keep one physical leg as the integration unit. Select its motor placement, finish the real root, gear/belt path and shaft retention, then produce a four-pod clearance map from that exact assembly. The current bearing quantities, full yaw range and optional 3.5 hip ratio cannot all be accepted unchanged. This review does not establish stair ascent, descent, dynamic load capacity or a print release.
