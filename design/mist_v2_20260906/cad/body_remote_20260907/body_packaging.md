# Body packaging checkpoint: all actuator cases inside MIST

Status: **inspectable preliminary packaging, not a mechanism fit or CAD freeze**. Saved at the root agent's checkpoint request before running a new packing search. No native CAD, Fusion MCP call, or existing assembly mutation was performed for this checkpoint.

The explicit user requirement is that every motor case stays inside the body and the legs stay slim. Whether an internal motor carrier may rotate while remaining enclosed is still unanswered. Therefore neither chassis-fixed stators nor rotating internal carriers is selected here.

The native assembly remains the earlier **267-solid body plus FL/RR proximal sections**, as reported by the root agent. The mirror continuation is paused. Its last saved failure is `../fusion_live_20260907/mirror_fixture_runs/20260907T131309668284Z/report.json`, referenced by `last_mirror_fixture.json`; it failed on a null pattern-elements collection and recorded main-body reactivation and an unchanged fingerprint. The null-handling correction was prepared, but this checkpoint does not claim a subsequent mirror pass.

## Current conclusion

**The 180 mm barrel is not ruled out by the motor case volumes.** The root's explicit case-only example fits 16 actual-size motor cases and the three device envelopes with no pair intersections. It excludes all drive hardware, mounting, connectors, cooling and access, so it does not establish that 16 working drive channels fit.

The original body internals cannot be retained unchanged with that example. The old phone deck and phone location intersect the lower STS layer, and the four old core-post positions intersect the diagonal wheel-motor columns. A new internal frame and a relocated brain-phone tray are required. A 190 or 200 mm barrel may provide useful clearance, but no increase is yet justified as mandatory by a complete transmission layout.

## Coordinate frame and hardware envelopes

All coordinates below are millimetres from the **body bottom**, before the existing -35 mm assembly offset to the hip-yaw plane. +X is the face, +Y is left, and +Z is up.

| Item | Envelope used | Source/limit |
|---|---|---|
| Main shell | 180 mm outside diameter, 220 mm straight body height | Existing 33-part `cad/body_native.py` recipe. |
| Shell interior | 87.6 mm nominal radius | 2.4 mm shell wall; excludes rims, posts, brackets and manufacturing clearance. |
| Lid/handle | Overall height 260 mm | This is not a full-diameter extra 40 mm equipment compartment. |
| C018 positioning servo, 12 units | Case footprint 45.23 × 24.73 mm; nominal axial case envelope 35 mm | OEM drawing and saved hardware envelope. Output-to-auxiliary projection span is 36.5 mm. |
| C018 axis location | 12.5 mm from the short end; case centre 10.115 mm from the output axis | Case cannot be modelled as centred on its shaft. |
| C018 horn | 19.95 mm OD, 4.5 mm total accessory envelope, 2.5 mm peripheral flange | Mounted axial stop is not established by summing the full horn thickness onto the case. Main shaft, horn, pinion, retention screw and tool access need separate space. |
| FIT0493 wheel motor, 4 units | Up to 25 mm diameter × 61 mm housing length | 98 g nominal complete unit. A 12 mm output shaft protrudes beyond the gear-case face; wiring and connector exit are additional. |
| Installed battery | 104 × 34.5 × 24.5 mm, 174 g nominal | One HOOVO 3S 2200 mAh pack. Cable and strap envelope not included. |
| Brain phone | 155 × 75 × 10 mm placeholder | Exact second-device model, case, plug and buttons remain unmeasured. |
| Face phone | 147.5 × 70.5 × 7.45 mm Mi 9 SE reference | Device assignment and delivered case/connector details still need confirmation. |

The 12 C018 cases alone weigh approximately 660 g, and four nominal FIT0493 units approximately 392 g. These totals exclude reductions, bearings, shafts, frames and the rest of the robot. They are not a new robot mass estimate.

## Verified root case-only example

The files `root_case_envelope_check.py` and `root_case_envelope_check.json` belong to the root agent and are preserved unchanged. They use the saved device bounds from `../leg_proximal_20260907/output_candidate/leg_geometry_report.json`.

| Group | Positions | Orientation and extent |
|---|---|---|
| 12 STS cases | At all combinations x=±25, y=±15, with layer centres z=52.5, 92.5, 132.5 | Long dimension along X, width along Y, shaft axis along Z; 45.23 × 24.73 × 35. |
| Four wheel cases | At all combinations x=±50, y=±50, centre z=65.5 | Vertical cylinders, Ø25, z=35…96. |
| Battery | x=-77…27, y=-17.25…17.25, z=8.25…32.75 | Original low horizontal envelope. |
| Brain phone | x=-37.5…37.5, y=-77.5…77.5, z=175…185 | Original horizontal orientation moved up 111 mm. |
| Face phone | x=70.05…77.5, y=-35.25…35.25, z=66.25…213.75 | Original vertical front position. |

The root check reports **171 case/device pairs, zero intersections**, and all cases inside the nominal barrel. Minimum radial shell gap is **1.504 mm**, at a brain-phone corner. The wheel cases have **4.389 mm** radial shell clearance. Expanding their radius from 12.5 to 15.5 mm for a provisional 3 mm clamp would leave only **1.389 mm** to the nominal inner shell, before cable, airflow and frame space.

The STS layers have only **5 mm axial gaps** between their 35 mm case envelopes. That is not a demonstrated horn, gear, bearing and tool-access allowance. As a sensitivity, a provisional 14 mm-tall local horn/input-pinion keepout above each case would extend 9 mm into the next case layer at its own output-shaft location. This is an illustrative drive-space conflict, not a measured mounted-horn stack. Shafts facing down instead would push the first layer's drive hardware toward the battery region.

The example proves that a claim of simple volume impossibility would be wrong. It does not yet provide a workable transmission.

## Exact obstacles in the existing body

| Existing feature | Position/envelope | Packaging consequence |
|---|---|---|
| Brain-phone deck B04 | z=61…64; nominal disc radius 83 | Its central x=-32…32, y=-35…35 region is uncut solid in the current recipe and intersects all four lower STS cases in the root example. |
| Original brain phone | x=±37.5, y=±77.5, z=64…74 | Intersects the first STS layer over z=64…70. Moving the phone without redesigning its old deck is insufficient. |
| Four B03 core-post lines | x=±48, y=±60, OD10; segments z=5…61 and 64…104 | Each corresponding diagonal Ø25 wheel case at x=±50, y=±50 is only 10.198 mm from the post centre. The radii sum to 17.5 mm, with overlapping z ranges. The old posts therefore conflict with those motor columns. |
| Upper core ring B05 | r=74…86.6, z=104…108, with front cutout | This is an additional obstruction for future outer gear/shaft bays. The root's bare wheel cases end at z=96, so this row is not claimed as a collision in that example. |
| Face cassette B13 | Bounding reserve x=66.9…78.25, y=±38.05, z=64.5…215.5 | Contains frame ribs, phone and insertion space. Treat it as reserved until exact shape/access routing is considered. |
| Face bezel B14 | x=84…99, y=±47, z=96…182 | Front cosmetic protrusion; it is not extra available motor volume. |
| Lid rim B10 | Inner radius 84.8 over part of z=216…224 | The full 87.6 mm interior radius cannot be assumed near the top. |
| Shallow lid B11 | Inner roof rises from about z=232.4 at r=82.6 to z=239.5 near the centre | Extra lid volume is tapered. Full-width motor or phone trays cannot simply occupy the entire height to 260. |

The face phone's lower edge is at z=66.25. A provisional connector/bend reserve of **x=60…84, y=±11, z=38…66** was identified for review; it is not a measured plug envelope. It can conflict with a front cardinal wheel-motor column even when the bare phone and bare motor case do not touch. The existing cassette has an opening near x=74.2, y=±8.5, z≈53.5…73.5, but that does not prove a complete cable bend route.

## Inspectable alternative: lower cardinal pairs

This is a concrete seed derived from actual case dimensions. **It has not had a complete pairwise, mount, connector or transmission check.** It leaves a central region instead of filling it with the root example's STS blocks.

For each cardinal angle 0°, 90°, 180° and 270°, use local radial R, tangential T and vertical Z coordinates:

| Components | Proposed centre coordinates | Local envelope |
|---|---|---|
| Two lower H/K STS per cardinal sector, 8 total | R=52.615, T=±15.5, Z=26.25 | 45.23 radial × 24.73 tangential × 36.5 vertical; includes the drawing's projection span as a guard rather than only the 35 mm case. |
| One upper yaw STS per cardinal sector, 4 total | R=49, T=0, Z=81.25 | Rotate the footprint: 24.73 radial × 45.23 tangential × 36.5 vertical. |
| Four fixed wheel-motor cases | Global x=±50, y=±50, centre Z=80.5 | Vertical Ø25 cases, z=50…111. |
| Provisional wheel shaft/coupler space | Same motor axes | Shaft z=111…123; a candidate Ø12 coupling reserve z=115…135. Exact coupling, overlap, retention and supports are not selected. |
| Upper horizontal brain-phone alternative | x=±37.5, y=±77.5; initially use z=175…185 | A lower z=155…165 tray may be explored after shaft/gear space is fixed. Neither tray has a new supporting frame here. |

The lower cases occupy radial R=30…75.23 and tangential extrema ±27.865. Their outermost rectangular corners are about **80.2 mm** from the body centre, leaving roughly 7.4 mm to the nominal inner shell. Opposing case centres within one sector are 31 mm apart, leaving **6.27 mm** between their 24.73 mm widths. Adjacent cardinal packages have a 2.135 mm separation along each separating coordinate at their closest corners. These are elementary case-box checks, not a tolerance-qualified assembly.

The upper front yaw case ends at x=61.365, below the face cassette's reserved inner x=66.9 boundary, whereas a radial-long case at the same station would reach x=71.615 and enter that reserve. This is why actual orientation matters.

A **vertical central battery** could be placed at x=±17.25, y=±12.25, z=8…112, with a provisional 52 × 52 mm central service region. It cannot be combined unchanged with the root example's central STS blocks; those occupy the same region. The cardinal-pair seed leaves more of that region open. Battery holder, connector, fuse and lift-out path remain unallocated.

Lower H/K horn access from above is likely blocked by the upper yaw layer at the same cardinal station. A credible assembly sequence would install and test the lower modules first, then add a removable upper yaw tray and phone tray. This is a proposed service strategy, not an established unobstructed tool path. Radial extraction and gear access still need exact swept tooling envelopes.

## Phone alternatives under consideration

1. **High horizontal brain phone:** retain its 155 × 75 footprint and move it above the actuator rows. The root's z=175…185 placement is the only case-only example checked programmatically so far. Its 1.504 mm corner gap is narrow for a continuous surrounding cradle. A holder could support edges without wrapping every corner, but that needs a design. At 190 mm outside diameter the same bare phone gains 5 mm of radial clearance.
2. **Vertical rear brain phone:** an untested placement is x=-77.5…-67.5, y=±37.5, z=55…210. It frees the middle height but competes with rear motor sweeps, cooling and a rear disconnect/connector route. Its lower connector can approach the original horizontal battery. This is not selected over the high tray.
3. **Low horizontal battery:** retain the verified reference x=-77…27, y=±17.25, z=8.25…32.75 where mechanisms allow it. It keeps mass lower, but conflicts with many downward shaft/gear routes from the centre motor block.
4. **Vertical removable battery:** the central placement above trades higher pack centre of mass for a clear peripheral actuator layout. It requires removal of the upper tray for service and an explicit connector pocket. The 52 mm service square is a reservation proposal, not a measured battery tray.

## Internal carrier alternatives and current sweep status

No numerical full- or limited-yaw sweep optimization has been executed in this subtask. The following are dimensional screens and candidate parameters for the next bounded experiment. They must not be reported as a collision-free internal carrier.

### Enclosed H/K carrier with wheel motor fixed to chassis

Two C018 cases can use a **45.23 × 35 mm horizontal footprint with 24.73 mm vertical thickness**, placing the servo output axes horizontally. Their bare footprint corner radius is **28.59 mm** about the footprint centre. Two vertically stacked cases plus a 3 mm separation occupy **52.46 mm** in height before base plates, caps and gears.

Adding a provisional 3 mm radial carrier allowance gives a **31.59 mm** case/support sweep radius. Four concentric carrier axes on R=52 at diagonal angles would then have:

- Outer swept radius about **83.59 mm**, nominally inside the 87.6 mm shell radius.
- Adjacent axis spacing **73.54 mm**; subtracting two 31.59 mm radii leaves about **10.36 mm**.
- A central circular gap only about **20.41 mm** in radius, before battery/frame clearance.

Those circle figures exclude the face phone. For the front-left axis at about (36.77,36.77), the face-cassette reserve begins at x=66.9 and covers that Y position. The centre-to-reserve distance is about **30.13 mm**, less than the provisional 31.59 mm sweep radius. Thus the simple symmetric full-circle seed already intrudes into the cassette reserve by roughly **1.46 mm**, even before a phone clearance allowance. This is a conflict of the conservative circular envelope, not proof that an actual limited box sweep is impossible.

The case circle also does not reserve the horn and input drive. For illustration only, an output-side envelope extending to tangential 29.5 mm and radial 23.615 mm would reach about **37.79 mm** radius before its own frame clearance. This shows how a nominally small horn/gear region can dominate sweep. No particular gear, offset or 37.79 mm design is frozen.

This hybrid removes H/K motor power feeds across the yaw joint while retaining one continuous wheel feed. It still needs the actual differential/coaxial output block and a wheel-feed bearing/pickup. The leg agent proposes an opposing short H trunnion and a nested K-tube/W-core arrangement, rather than drawing three solid shafts through one another. No complete station diameter or axial depth has been supplied yet.

### Three downstream motors on an enclosed carrier

Adding the FIT0493 to the carrier requires its Ø25 × 61 case, 12 mm output shaft, coupling, support bearings, wiring and heat path. Laying its long axis in the carrier plane expands the footprint. Stacking it vertically above H/K can preserve a small case-only footprint but does **not** solve the output route: the wheel shaft cannot pass through the STS cases below it. A side shaft corridor then enlarges the swept package. Neither orientation has been checked as a complete mechanism.

### Limited-angle, inboard-offset carriers

A full 360° cylinder is not a mandatory requirement for a joint with limited travel. Candidate experiments may use yaw limits ±55°, ±65° and the previous geometric ±100°, with actual 45.23 × 35 mm case rectangles offset inward from carrier axes. Root-proposed initial axis/offset examples include R=70 with a 33 mm inboard offset. The toy disc arithmetic is not retained as a fit result here; actual boxes, gear blocks, cables and neighboring independent carrier sweeps must replace it.

Reduced yaw cannot be accepted silently. The previous, different 139.5/130 mm stair screen used a rear support yaw near -98° in one feasible static event. It does not prove that the new robot requires that angle, but it prevents treating ±55° or ±65° as already sufficient for the existing plan. A new gait/stair path would need checking.

## Space not yet reserved or verified

The following remain **explicitly unreserved**, rather than being hidden inside an assumed percentage of empty volume:

- Fixed-motor spatial differential bodies, gears, bearings and reaction mounts, or the H/K carrier differential blocks.
- Supported yaw output stations and their complete path to the wall/leg root. The previous external R103 mm yaw station cannot be reused as an internal motor-centre assumption.
- Independent K/W tube/core supports and positive torque locks. The proposed 8 OD/6 ID tube with 5 mm core needs separate external bearing stations; a bearing cannot be invented inside its 6 mm bore.
- All servo input gears, any additional output reductions and their axial stacks. The old module-1 20T horn interface was rejected; it is not a valid compact placeholder.
- Wheel-motor output couplers, encoder/cable exits, continuous feed shafts and right-angle transfers.
- Mounting plates, case clamps, preload pads, structural ties, fastener heads, insertion directions and driver-tool access.
- Phone and battery holders, board outlines, capacitors, disconnect, fuse, cable bend radii and strain relief.
- Distinct power/USB/bus routing and sufficient space to disconnect a module before extracting it.
- Air inlet/outlet passages, heat-spreading clamps and service clearances around hot cases.
- Swept cable loops and carrier-to-carrier/phone/shell clearances for any rotating internal option.

The old 33-part body provides useful boundary geometry, but its posts, decks and clamshell access layout are not automatically suitable for these new internals.

## Cooling and assembly constraints to carry forward

Cooling cannot be inferred from cases fitting. The prior wheel-motor estimate used roughly **5–7 W per motor** as an unmeasured total-loss sensitivity, or 20–28 W for four units. Servo losses are additional and have not been identified; the historical yaw servo reached 52°C and the bench cutoff was 50°C. These facts require explicit case-temperature monitoring and a real airflow/heat-spreading design, not a claimed continuous rating.

A passive-air arithmetic screen for a nominal 180 × 220 mm cylinder gives about 0.124 m² side area. At an assumed 5 W/m²/K film coefficient, 28 W alone corresponds to roughly 45 K air-to-surface rise if that entire side were an effective heat exchanger. It is not: the shell is polymer, thermal contact is imperfect, and phones/gears obstruct flow. This is a reason to reserve a metal heat path and forced-air option, not a thermal prediction of the robot.

Candidate fixed-layout assembly order: lower deck and H/K modules; lower gears/shafts with direct screw access; power distribution and low battery or central battery guide; upper yaw/wheel modules; serviceable harness loops; removable brain-phone tray; face cassette; shells/lid. That sequence remains a planning constraint. It must be replaced by a checked tool/part insertion sequence once the drive stations are dimensioned.

## Next bounded experiment proposed for the root agent

Use the actual boxes above, preserve the face-cassette reserve, and compare: (1) the root fixed-case seed with local drive/connector keepouts, (2) the lower cardinal-pair layout with upper phone tray, and (3) two H/K cases on limited-yaw carriers with fixed wheel motors. Test 180, 190 and 200 mm shells before assuming enlargement. Any larger diameter should be justified by a named collision or service margin. The first result should report cases, mechanisms, service paths and moving envelopes separately.

This checkpoint intentionally stops before claiming a fit for all 16 drive channels. It records the available positions, exact existing blockers and the remaining mechanism space so the next experiment can be specific.
