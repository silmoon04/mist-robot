# MIST engineering rebuild

The first fit bed and brain update are delivered. The mechanical work remains an engineering candidate. The user has now restored Fusion access, and the local MCP endpoint is working. Actual native body construction and a small native joint fixture have run successfully; the complete robot is not a released manufacturing design.

## Current steering: all motors inside the body

The user has clarified that all motors, including wheel motors, should be inside the body. A shin-mounted motor remains inconsistent with the desired compact legs. Whether an internal hip carrier may move while remaining completely enclosed is being clarified; rigidly fixed housings were our stronger initial interpretation. Work is shifting to `cad/body_remote_20260907`: packaging, physical transmission channels, coupling/load distribution, backlash and servo travel. The existing180mm body is not yet verified to fit the complete arrangement. Earlier native and simulation studies remain preserved below.

The previous concealed-shin revision is paused. Its OEM checkpoint had168valid parts but ten actual clashes; the provisional three-contact load test exceeded the2:1 knee torque assumption. It must not be shown as a completed functioning robot. The live Fusion document preserves267native solids, comprising the body and two proximal leg sections, with F3D/STEP exports under `cad/fusion_live_20260907/concealed_stages`.

## Previous concealed wheel drive study and delivered hands-free voice

The user rejected the exposed wheel motor/cradle blocks. The active revision in `cad/concealed_wheel_drive_20260907` moves the wheel motor lengthwise into the upper tibia and uses an internal supported shaft and right-angle gear stage. The motor, casing, cooling path and assembly access are being checked together. The older 657-part assembly below is preserved as evidence rather than treated as the requested final appearance.

The [native body evidence](cad/fusion_live_20260907/native_body/verification.json) records 33 native solids, 384 features, assigned appearances and F3D/STEP exports. A real native test exposed ground-to-parent placement resets; the corrected generator releases that default relationship and captures placements before recompute. The [joint fixture](cad/fusion_motion_20260907/NATIVE_VERIFICATION.md) has now exercised sixteen actual Fusion joints and 96 world-transform/datum checks. These are native results, not the previous offline API tests. The complete concealed-drive assembly and its full motion remain separate work.

The console on port 8776 is running with a new Talk control. It uses local speech detection, streaming transcription, automatic submission and interruption handling after one user microphone click. The [streaming Talk report](brain_v2_20260907/talk_mode_20260907/TALK_REPORT.md) records the browser fixture and a real provider probe: final transcript 0.373 seconds after the last saved-audio packet, excluding endpoint delay, model generation and speech synthesis. Spark conversation / Astra background / ElevenLabs Responsive remain in place. No room microphone was activated during testing. The initial console start succeeded; later restart commands were rejected before execution, and the new recognition sidecar runs separately on port 8788.

The actual KHK supplier STEP is now downloaded and imported in Fusion. Its [native tooth-phase check](cad/fusion_live_20260907/vendor_pair_probe/README.md) found an unphased collision and seven clear sampled positions with a 9° output phase and counter-rotation. Offline Boolean warnings and a 0.289% importer volume difference are preserved rather than reported as equivalent geometry or clearance.

## Latest proximal candidate and matched simulation

The [new complete CAD assembly](cad/leg_proximal_20260907/output_candidate/README.md) has 657 valid solids and zero reported intersections above 0.01 mm3 across 215,496 considered pairs in its recorded drive pose. It includes the femur-mounted knee motor, supported belt cartridge and adjustment hardware. The [full STEP](cad/leg_proximal_20260907/output_candidate/MIST_proximal_robot_candidate.step), GLB and [preview](cad/leg_proximal_20260907/output_candidate/whole_robot_view.png) are saved. This iteration is heavier: 7.108 kg under the declared solid-print and hardware-envelope assumptions, with 2.829 kg of printed material. It is not a scale or slicer result.

The new simulator snapshot consumes all seventeen CAD link masses, COMs and full inertia tensors. A corrected conversion from PyBullet's principal-inertia frame preserves the actual body frame. The [CAD reconciliation](simulation/proximal_cad_20260907/reconciliation.json) and [standing/rolling/load checks](simulation/proximal_cad_20260907/validation_summary.json) preserve the source hashes and assumptions.

| Matched CAD check | Result and practical limit |
|---|---|
| Standing | Pass in the model; worst shaft RMS 0.504 N m against the assumed 0.728 N m limit |
| Rolling | Pass in the model; 5.063 m in 8 seconds, worst shaft RMS 0.600 N m |
| Supported single leg at 23.244 N | Nominal pass with 6.59 mm foot error, but knee RMS 0.727899 N m leaves only 0.000245 N m against the assumed limit; no useful measured headroom established |
| 80 mm stride, 3 seconds per leg | Fails: lateral error 11.85 mm and minimum swing peak only 7.87 mm |
| 60 mm stride, 4 seconds per leg | Passes the aggregate model criteria at 3.27 mm/s, with transient support loss in 1.28% of samples; not a continuously supported or physically robust result |

The [matched gait report](simulation/proximal_gait_20260907/MATCHED_CAD_REPORT.md) explains why the earlier passing gait cannot be transferred to this assembly. The moving femur mass and lateral placement substantially increase yaw inertia. This remains a design iteration, with unresolved pinion/web strength, thin adapter/spacer features, clamp/keeper/horn hardware, mass, wiring and full-motion checks. No first-leg load or print release is issued.

The new [Fusion launcher and native replay](cad/leg_proximal_20260907/NATIVE_RUN.md) are installed as `MIST_Proximal_20260907`. Its reviewed plan assigns all 657 parts into 33 rigid groups, sixteen main revolutes and sixteen fixed-phase rotor attachments. Forty-eight API declaration checks and twenty-two offline tests pass. Native execution, material assignment and full motion remain unverified because Fusion is still at sign-in. The earlier launcher and candidate are preserved.

Use the revised first fit bed linked below. The remaining sections retain earlier design snapshots and their outcomes; they are not the current assembly's mass or motion validation.

## Earlier continued engineering, 7 September

The missing leg builder is now implemented. The checked [single-leg, four-leg and whole-robot STEP/GLB exports](cad/leg_output_checked_20260907) contain 577 valid solids and zero positive-volume intersections across 166,176 considered part pairs in the recorded drive pose. STEP round trips and CAD/kinematic joint-centre agreement passed. This remains a candidate mechanism: shaft torque locks, tension adjustment and complete motion/assembly checks remain unfinished. Native Fusion execution is pending sign-in.

The actual leg solids exceed the earlier mass allowances. [The detailed accounting](simulation/cad_mass_20260907/README.md) totals 6.341 kg using solid-print volume, nominal motors, steel bearing-envelope estimates and explicit allowances. This is not a scale or slicer measurement. Its mass-only simulation fails the assumed continuous motor-load budget in stand, drive and crawl; crawl also misses advance and clearance criteria. The 3.95376 kg results below remain attached to their older snapshot. The current fully remote arrangement is not a structural print release and needs mass/transmission redesign.

Two new engineering findings affect the next revision:

- The [C018 mode/drawing correction](servo_contract_20260907.md) confirms multi-turn positioning support. The old 350-degree limit was a single-turn commissioning assumption, not a mechanical limit. Higher ratios still require verified startup position recovery and physical clearances.
- The [knee-drive frame comparison](architecture_trade_study.md) shows why a knee motor attached near the proximal femur can lower hip torque. It changes the mechanical reaction path and requires a different design; changing the software coupling alone cannot provide the benefit.

The [new same-mass physics comparison](simulation/proximal_knee_20260907/README.md) includes that physical motor relocation and its changed reaction frame. At the same 6.341 kg, stand and drive pass the stated motor-load criteria. The supported 20.735 N leg test improves from about 15.8 mm to 6.5 mm foot error. The two-contact dynamic loading and both scripted stair attempts still fail. The minimal crawl advances only 25.8 mm in 26 seconds, so it does not satisfy the requested walking speed. A matching lighter CAD cartridge and feedback gait controller are being developed separately; this sensitivity is not a first-leg print release.

The [feedback crawl study](simulation/proximal_gait_20260907/README.md) now advances 237.35 mm across three full cycles in 39.50 seconds, with 1.34 mm final lateral error. Its 80 mm stride / 3 seconds per leg passes the declared contact, clearance and torque checks, including a lower-grip / longer-delay repeat. That is still only about 6 mm/s walking. Shorter periods and a 100 mm stride fail parts of the bounded test; this is a controller result under the same provisional mass distribution, not a measured speed or the final CAD dynamics.

The [stair feasibility screen](simulation/stair_feasibility_20260907/README.md) finds a densely checked first-front-leg path at a provisional 180 mm rise / 270 mm tread, and a rear crossing event with 3.17 degrees of nose-down body pitch. It uses the existing limits with additional margins. These isolated static paths are not a complete ascent/descent sequence and do not supersede the failed dynamic stair attempts.

[Shaft and printed-section calculations](structural_screen.md) quantify belt pull, bearing reactions and section sensitivity. [The packaging screen](packaging_review_20260907.md) records the first broad-yaw motor conflicts and the root-attachment problem. These remain design checks, not a physical load rating.

The later [manufacturing review](package/proximal_review_20260907/review.md) also identifies a decisive gear problem: the module-1 20T pinion's horn holes leave about 0.079 mm to a tooth root, and its calculated tooth stress exceeds the assumed printed-material allowance. Increasing face width alone cannot fix that attachment. The [metal gear study](package/metal_gears_20260907/metal_gear_recommendation.md) supplies real catalogue alternatives and required machining; none is claimed to be a drop-in horn connection. The 577-part candidate therefore remains unsuitable for a loaded leg print even where its static clearance check passes.

The user clarified that timing belts have not been ordered. The selected [Gates 375-3MGT-09 belt and matched 32-tooth pulley pair](package/belt_selection_20260907/belt_selection_report.md) set 139.5 mm centres. [design_parameters_20260907.json](simulation/design_parameters_20260907.json) carries that geometry; the earlier 140 mm simulation inputs remain unchanged. No belt purchase was made.

## Open the work

- [Interactive review](http://127.0.0.1:8136/review/) shows the original reference, the candidate mechanism, the solid CAD body and recorded physics tests. If the local server has stopped, run `python review/serve.py` from this directory. Browser files and Three.js are local; no CDN is needed after setup.
- [Revised first fit bed, 3MF](coupons/bed1_proximal_20260907/MIST_BED1_PROXIMAL_ALL_PARTS.3mf), [measurement guide](coupons/bed1_proximal_20260907/MEASURE_FIRST.md), [bed preview](coupons/bed1_proximal_20260907/BED1_PROXIMAL_TOP_VIEW.png), and [blank feedback sheet](coupons/bed1_proximal_20260907/feedback_BED1_proximal.csv). The original bed is preserved separately.
- [Body STEP](cad/output/MIST_body_candidate.step), [body preview](cad/output/body_preview.png), and [manufacturing notes](cad/body_manufacturing.md).
- [Simulation report](simulation/README.md), [URDF](simulation/generated/mist_candidate.urdf), [final sizing report](simulation/analytic/results_final_cad/REPORT.md), and [independent engineering review](engineering_review.md).
- [Recovered inventory and threads](history_inventory.md), [mechanism study](mechanical_audit.md), [wheel motor comparison](wheel_motor_study.md), and [assembly/wiring plan](assembly_and_wiring.md).
- [Brain changes and live results](brain_changes.md).

## Earlier 140 mm geometry and 3.95376 kg simulation snapshot

The earlier fixed radial wheel arrangement cannot provide ordinary straight rolling without scrub. The new candidate has hip yaw, hip pitch and a remote knee, with three positioning servos near each hip. The knee transmission drives the absolute tibia angle, so its coupling changes both motor coordinates and hip torque. A simple independent-joint torque calculation is insufficient.

This earlier geometry uses a 180 mm body, 220 mm barrel plus lid/handle to 260 mm, 140/130 mm links, 85 mm wheels and mounts at +45/-45/+135/-135 degrees. A real 30 mm transverse hip offset supplies rolling track while the wheel planes align. Its [parameter file](simulation/parameters.json) has explicit coordinates and provenance for every group of assumptions. The checked CAD above uses a 139.5 mm femur and the later 6.341 kg mass accounting; the table below does not describe that heavier candidate. Older CAD and the physical bench calibration are preserved.

The earlier estimated robot mass was **3.95376 kg**, using the body's solid PETG volume and both phones with provisional leg, gearbox, carrier and harness allowances. Those allowances were superseded by the later CAD accounting above. The original purchased servos have 0.981 N·m rated torque; 2.942 N·m is their stall endpoint. Measured delay, backlash, thermal behavior and transmission stiffness are still missing.

| Executed check | Current outcome |
|---|---|
| Stand and slow body-height change | Pass under the stated model assumptions |
| Aligned rolling | 5.235 m in 8 s with a ramped 0.9 m/s command; not measured hardware speed |
| 2:1 hip crawl | Fails the 15 mm minimum wheel-clearance requirement |
| 3.5:1 hip crawl variant | Clears the requirement but advances only 34.4 mm in 26 s with 18.3 mm lateral drift |
| 180 mm step ascent/descent | Both fail the scripted tests |
| Ideal range-based stop | Stops 177.6 mm before the obstacle with no obstacle contact; no real perception/planner tested |
| Sustained 29.09 N loaded-leg test | 2:1 hip yields 148 mm; 3.5:1 improves deflection but still fails sustained-load acceptance |

The 3.5:1 hip is a bench alternative, not a frozen replacement. It trades speed and usable joint travel for torque. Results are saved with parameter/source hashes; earlier 3.884 kg runs are kept separately. The simulator represents contacts and applied torques, but its backlash model is command hysteresis with reduced stiffness. It does not resolve physical load-side gap engagement, belt elastic modes, print layers, thermal dynamics or final CAD collisions.

## Wheel choice

The best documented purchased candidate found is DFRobot FIT0493, 12 V, 350 rpm, 98 g, with encoder. UK evidence is about GBP 25.61 including VAT, plus GBP 10.55–11.02 for a current-regulating driver. This exceeds the requested approximate GBP 15 motor budget. The [study](wheel_motor_study.md) includes current listings, equations and 1,620 operating cases.

An owned STS3215 with an external 7.5:1 speed increase is a useful lower-purchase-cost experiment. It predicts approximately 1 m/s on the chosen wheel under the calculation's assumptions, but adds transmission mass and multiplies reversal play. It has less slope margin. Small fast N20 motors failed the required torque/current screen. No motors or extra hardware were purchased.

## First fit bed and refinement

Use the revised bed linked above for a first print made after this update. It preserves seven handled objects and the original interfaces, adding the actual proposed carrier/keeper section, a 16 mm bolt circle, sleeve fits, horizontal jack pocket, slider and long X/Y datums. Its verified footprint is 216 x 216 x 22 mm; allow for brim and purge lines on the 225 mm bed. Seven valid solids, STEP roundtrips and independent STL/3MF checks pass. The new 87-row sheet and assembly/scale sheet are blank. The new leg source adopts the profile, but completed-solid matching is still pending. The paragraphs below describe the preserved original bed.

The bed contains seven handled objects within 206 x 202.5 x 10 mm. Twenty-eight full-depth bearing seats cover all eight purchased bearing codes. Other sections test inserts, bolts, nuts, cable slots, servo case width, metal-shaft clamping and a 624 bearing retainer. Labels are engraved. The old upright printed axles are replaced by metal-shaft interfaces in the proposed load paths.

The 3MF contains geometry, not a machine/material profile. Use the intended final carrier material and slicing process; PETG-to-PLA fit transfer is unproven. The complete model volume is 75.346 cm3, not a slicer filament estimate. The clamp/retainer trials need the fasteners listed in the print guide. All 74 physical feedback rows are blank.

The second-bed toolchain is implemented and tested with temporary synthetic inputs. It requires actual recorded measurements and generates a smaller set of relevant fit specimens. After the second physical check, approved interface values must be applied to the corresponding leg/body recipe and its geometry rechecked. No real second bed or fabricated feedback has been produced.

## Native Fusion status

[MIST_Rebuild.py](cad/MIST_Rebuild/MIST_Rebuild.py) creates a new Fusion document, builds the body and four legs, requests Compute All and native interference analysis, and exports F3D/STEP plus a run report. It records failures instead of treating a failed Boolean as zero interference. It never edits the old leg document. A launcher is installed in Fusion's Scripts folder as `MIST_Rebuild_20260906`.

The [coupon builder](coupons/fusion_coupon_bed.py) separately replays the same fit-bed recipe as native sketches, extrusions and lofts. The native helpers have been checked against the installed API. A separate [native motion helper](cad/fusion_motion_20260907/README.md) supplies rigid groups, sixteen as-built joint definitions and correct assembled-angle offsets; it passed 48 API declaration checks and sixteen offline contract/math tests. Its physical grouping must match the selected recipe before integration. **Neither new build has been executed in Fusion**. No F3D success or native full-assembly clearance is claimed.

The sign-in blocker described in the earlier snapshots is resolved. Native MCP work now proceeds through the local adapter, with the actual body and joint-fixture results linked at the top. The recovered artist mesh was historically exported as `mist_3d/MIST.stl`; its current file is missing. The exact original-show reference and recovered historical evidence are recorded in the inventory report.

Offline solids were generated with CadQuery/OpenCascade. Validity, STEP reimport and mesh checks are separate from a reproducible Windows shutdown error in that runtime. The error also occurs after a plain import; strict clean-process-exit validation did not pass. See [tooling details](coupons/TOOLING_CHECKS.md).

## Brain

The expanded brain work is live at [the MIST console](http://127.0.0.1:8776/). Following the user's latency feedback, conversation uses Spark low/standard, with Astra low/priority for independent background work and the refined MIST ElevenLabs voice in Responsive mode. [Latest activation and playback repairs](brain_v2_20260907/latency_fix_20260907/UPDATE.md), [measured cost/latency](brain_v2_20260907/COST_AND_LATENCY.md), and the [450-frame editable Aseprite document](brain_v2_20260907/faces/MIST_expression_study.aseprite) are saved. The face regression covers 31,050 states; all 450 exported frames were visually reviewed. The paragraphs below describe the earlier grounding update, which the new console preserves.

The existing UI now defaults to MIST, uses a four-legged identity, remembers preferences, checks capabilities and observations, and reports simulation receipts honestly. Research-worker results preserve fetched sources and distinguish unavailable, model-only and mocked responses. Motion intents pass deterministic checks; the MIST thermal cutoff now matches the recovered 50 C bench shutdown.

The full offline suite passed after the final thermal change. Five bounded live model turns also passed, including memory recall after a reset and admission of missing camera data. Observed turn times were 1.39–2.45 s. No physical actuator or sensor connection was made. From `spider-robot/brain`, start `python ui/server.py --soul mist --port 8765`.

## Remaining work before the first loaded leg print

1. Resolve the selected proximal reduction, complete its teeth/centres and real horn/shaft coupling, and check all four hip pods against the body and one another across travel.
2. Redesign the mass and transmission against the 6.341 kg accounting, including reflected inertia and a stronger loaded-reversal/thermal characterization plan. Neither CAD accounting nor the earlier 3.95 kg estimate is a measured finished robot.
3. Run the native Fusion builders after sign-in, inspect the document and actual interference/export reports, and correct every material build error.
4. Obtain fit-bed feedback, actual insert dimensions, the second phone identity and target stair dimensions. Belts remain unpurchased; use the selected belt specification when confirming the pulley procurement interface. Generate and verify the second fit bed, then apply the results to the first leg.
5. Finish fastener engagement, bearing allocation, root attachments, tensioning, covers, cable sweep, phone locking, controller pin expansion and assembly access. The wiring plan identifies the extra pin demand of four encoder-equipped DC wheels.
6. Establish a supported, loaded single-leg result before reproducing legs 2–4. Continue gait and stair development with the same physical geometry and measured actuator limits.

The [requirements record](requirements.md) preserves the full requested scope, including faster walking and stairs. These items remain open rather than being redefined as completed by an animation or a geometry export.
