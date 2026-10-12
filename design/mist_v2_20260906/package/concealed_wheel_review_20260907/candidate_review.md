# Independent concealed-drive candidate review

Reviewed the saved OEM checkpoint, not an invented final assembly. Source: `cad/concealed_wheel_drive_20260907/concealed_leg.py`, checkpoint reported by its author as SHA-256 beginning `a717b4e4`. Geometry: `output_oem_checkpoint/leg_geometry_report.json`, SHA-256 `676360badb1427c509544576d50ba5be773c31f2e159f17666cbae79d82dbc92`. The separate audit JSON records the complete report hash and mass comparison.

The motor has moved from the foot into the upper tibia, and the casing has the continuous faceted shape requested. That is a useful visual improvement. The present checkpoint cannot yet be assembled and operated as drawn: it has ten positive interferences, incomplete motor mounting, incomplete shaft/hub torque and thrust retention, an unclosed thermal-duty limit and a larger mass budget. A final full-body report has not yet been supplied for this review.

## What is established

- The actual manufacturer file `references/KHK_SM1_20/SM1-20_On.stp` is available and verified as one valid solid, volume 2332.532 mm3, 6 mm bore and 16 mm hub. Its SHA-256 is `c4aebaa418f6955130f9bf4f4a798dc478b181fea47327865db2d7aedb386a98`. The former lack-of-local-bytes limitation is resolved.
- CW07/CW08 now use that STEP reference. The source distinguishes plain SM1-20 geometry from the proposed hardened SM1-20H material variant. Having the geometry does not establish the grade, purchase or holding interface.
- The source records a native Fusion result for seven coupled gear-phase samples using `output_phase = 9 - input_phase`. The author reports the phase-9 OEM pair as zero-overlap and warning-free in the checkpoint. This review did not rerun native Fusion; those samples are not a continuous contact-pattern or load test.
- All 168 FL checkpoint solids are valid, with zero shape-check issues. The ten positive intersections and one warning are retained in the report; they are not discarded as expected contacts.
- The 98 g motor case occupies u20 to 81 mm, with its shaft at u81 to 93, inside the planned shin. The old W05/W06/W07/W08/W09 foot-drive parts are absent.
- The tibia is now 140 mm. Opposed longitudinal bearing-cup openings resolve the previously reported insertion obstruction: the upper bearing enters from the knee end, and the lower one from the foot end. Their overlapping shoulders form one shared 2 mm web inside CW09.
- The outer wheel bearing moves to Y42 to 48; the back of the OEM output gear is at Y40. The rear service pocket is extended to Y53.4, beyond the Y52.4 cover face, so it is an opening rather than the former internal recess.

## Blockers to physical assembly and operation

| Issue | Concrete evidence | Required resolution |
|---|---|---|
| Moving or separate parts still intersect | Frame/motor case 82.10 mm3; frame/rear cover 303.48; old main cheek/front cover 286.32; femur/frame 30.45; knee belt/rear cover 33.56; wheel hub/frame 72.59; wheel hub/shaft bearing 4.99; wheel hub/OEM driver 3.46; keeper/rear cover 1.02; OEM output/rear cover 1.12. | Correct the actual solids and rerun the same revision. The warning belongs to the output-gear/rear-cover contact; it must remain visible until resolved. |
| Motor and heat assembly has no defined frame mount | Thermal-source screws join motor clamps to the heat spine. The source has no demonstrated clamp/spine fixing to the tibia frame. Frame ties are at u50/u90; clamp stations are u35/u70. | Add a real bracket/fastener load path for motor torque, weight and vibration. The drive coupling and cosmetic cover must not be the only support. |
| Torque connections remain incomplete | The imported miter gears have plain bores. CW03 is a round-bore coupling envelope without its clamp/D features. The wheel hub's clearance bore has no defined torque lock. | Specify the actual coupling and gear/shaft/wheel-hub connections, with machining, fasteners, engagement and retention. A coincident bore and shaft is not a torque path. |
| Axial retention remains incomplete | Both longitudinal bearing cups lack complete keepers, and the smooth shaft has no finished axial locating stack. The two bearing centres are only 8 mm apart. The driver back face is about 0.5 mm beyond the lower bearing end. | Close the thrust path through inner and outer races, shoulders/spacers and retainers; reserve the required shim/mesh adjustment. Recheck overhang, pin/flat stress concentrations and assembly access. |
| Wheel-axle retention is unfinished | The new outer bearing ends at Y48, where the current axle also ends. Only the positive outer-race keeper is defined; its fastening and the opposite support remain incomplete. | Specify end screws/washers or another retention arrangement. A flush shaft end has no external collar land, but an explicitly designed end-tap arrangement could use the central service opening. |
| Cover and clamp fastening remains caller work | The thermal recipe lists split bolts/nuts, spine bolts and eight cover screws as hardware to integrate. Cover holes alone do not show mating inserts/nuts or usable engagement. | Include their actual geometry and tool paths. Demonstrate cover and motor removal with the knee adapter and shaft assembly present. |
| Thermal operation is not qualified | At assumed h=5 W/m2K, the recipe predicts 49.1 to 68.7 K sink rise for 5 to 7 W, before contact resistance. At 25 C ambient that is roughly 74 to 94 C. | Measure enclosure-fitted temperature/airflow and set a supported current/duty envelope. The proposed 60 C case cutoff is not evidence that the thermal design stays below it. |
| Actuator reserve is already inadequate | The concealed checkpoint adds approximately 197 g per leg. Its own nominal COM calculation gives 0.8415 N m knee demand under three equivalent contacts, 115.6% of the assumed 0.7281 N m continuous cap. | Reconcile the final mass/COMs and close a mass, ratio, speed/range and load-policy trade. A prettier enclosure does not establish functional completion. |

The supplied gear study also limits the material choice: its plain SM1-20 surface-durability reference, 0.084 N m, is below the approximately 0.172 N m working estimate. The hardened SM1-20H reference is conditional on its catalogue speed/lubrication assumptions, and unrestricted motor stall exceeds the cited bending reference. Keep those restrictions with the selected purchased grade and actual operating speed. The local STEP resolves geometry availability, not this operating limit.

## Concealment, cooling and service

The current skin is approximately 47.2 mm wide in the leg plane, tapering to 34 mm, and spans Y-24.4 to +52.4, or 76.8 mm across the leg. This is wider than the earlier 65 to 70 mm target. The small rear bearing/bolt opening is mechanically different from an exposed motor block, but all four principal views still need inspection with the body present. Keep the full motor body within the skin; the remaining frame/motor clash means the current fitted envelope is not yet real clearance.

The encoder exit is at the proximal u20 end. A removable side panel must expose the motor clamps and coupling, and permit enough withdrawal to disengage the actual motor shaft. The new service opening can expose the axle keeper, but motor and gear replacement still require a complete disassembly sequence. Do not infer tool access from a circular bore alone.

The proposed heat path is explicit: motor case, aluminium split clamps, heat spine/fins and baffled rear vents. The 24.6/25.2 mm clamp bores have plausible nominal closing clearance around the 24.4/25 mm cases and a 0.6 mm split gap; preload, case distortion and thermal contact remain unmeasured. The fasteners and frame attachment must be present before this becomes a supported heat path.

The fin channels are only 1.2 mm wide. Their cross-section falls to 138.84 mm2 at reliefs, below the 225.28 mm2 vent-group throat figure. Both numbers are geometry, not measured airflow. Leg angle, fouling, pressure loss and contact resistance remain outside the estimate. Even h=8 at 7 W predicts approximately 68 C sink temperature at 25 C ambient. A duty estimate based on averaged heat does not permit a sustained stall.

## Mass and new tibia geometry

The FL checkpoint is 1,540.874 g, versus 1,343.893 g in the old candidate. Four identical replacements with the old body/allowances project approximately 7.896 kg, an increase of about 0.788 kg. This is not the final full-body mass. The checkpoint's covers and cooling alone are 127.17 g per leg, and the fixed 98 g motor is simply relocated.

`mass_and_reserve_review.md` ranks the actual printed families and separates the 1.536 kg of selected phones, battery, servos and wheel motors. The updated 140 mm nominal COM calculation gives a hypothetical 5.466 kg uniform mass target for 20% continuous reserve, compared with the current 7.896 kg projection. Holding the moving limbs unchanged leaves only 0.324 kg for the base, less than the phones and battery alone. These are static screens, not achievable-BOM or motion guarantees. Old 130 mm load files must not be relabeled as validation of this candidate.

The rendered checkpoint was independently inspected in `checkpoint_visual/leg_view.png`. The foot motor block is gone and the motor is hidden behind the faceted casing. Visible penetrating frame/tie features and the wider casing reflect the recorded unresolved intersections, so this view is evidence of the new layout rather than an assembly-clearance pass.

The next review should use a frozen complete source/output set containing the corrected solids, real mounting and retention parts, complete mass allocation and the chosen motion samples. Until then, this checkpoint is useful CAD evidence and a clear list of work remaining, not a first-leg structural print release.
