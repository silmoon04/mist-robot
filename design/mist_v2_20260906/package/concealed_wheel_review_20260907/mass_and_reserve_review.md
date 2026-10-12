# Mass ranking and assumed torque reserve

This compares the preserved 7.108160 kg proximal candidate with the available OEM concealed-drive checkpoint. It includes a new nominal-pose calculation from the checkpoint's actual part COMs, plus the older loaded-fixture comparison. These mass and quasi-static sensitivities do not certify dynamic motion or stairs; the final corrected geometry will need another calculation.

## Keep the fixed component mass separate

| Selected-layout component | Mass |
|---|---:|
| Two 155 g phones | 0.310 kg |
| One battery | 0.174 kg |
| Twelve 55 g servos | 0.660 kg |
| Four 98 g wheel motors | 0.392 kg |
| **Subtotal** | **1.536 kg** |
| Current electronics, harness and extras allowances | 0.450 kg |

The subtotal is fixed for the current selected layout; it is not a claim that the conditional wheel motors have been purchased. The other hardware includes bearings, shafts, gears, pulleys, tires, clamps and fasteners. Its values mix nominal manufacturer masses with solid-envelope estimates. Weighing real bearings and hardware may correct overestimates, but an unmeasured correction is not a design saving.

## Actual printed mass ranking

The old candidate contains 2.829003 kg of printed material, using the declared solid material volumes. The largest families are:

| Part or family | Robot total | Geometry classification and useful change |
|---|---:|---|
| Four PF02 sliding carriages | 617.77 g | Integrated plate, deep bridges and motor cradle. Large 6 mm walls are the main target, rather than the small 4 mm sliding plate. |
| Four drive-side femur cheeks | 186.23 g | 6 mm cheek plus added fixed rails and crossmembers. Add bounded windows and edge ribs while retaining bolt and bearing nodes. |
| Structural lower body deck | 167.02 g | 5 mm plate with broad root tabs and two openings. A ribbed deck can remove central area while keeping root-bolt spread and core-post lands. |
| Four fixed yaw mount bridges | 140.32 g | Plate plus servo cradle and local housing structure. Shorter load paths and ribbed walls can help; the root and yaw-bearing supports remain structural. |
| Four old outer tibia cheeks | 132.74 g | Cheek plus knee face adapter. The concealed revision replaces them; do not count their removal twice. |
| Four old foot motor cradles | 128.77 g | Removed in the concealed revision. New motor support still needs a real load path. |
| Four main tibia cheeks | 116.90 g | 6 mm webs with holes and bearing interfaces. Midspan windows/edge rails can reduce mass. |
| Four wheel hubs | 110.70 g | Already have spokes and a hollow rim. Refine rim/web dimensions; this is not a solid wheel disk. |
| Four hip servo saddles | 100.82 g | Thick floors and sidewalls. Use hard-stop clamp lands and ribbed floors. |
| Rear upper barrel half | 95.18 g | Already a 2.4 mm hollow wall. Reducing infill does not remove this mass. |
| Four hip-only coxa parts | 90.17 g | Short offset carrier with a tall hip-drive support. Preserve moment transfer into the yaw stack. |
| Shallow lid | 81.84 g | Already a revolved approximately 2.5 mm skin with rim details, not a filled dome. |
| Front upper barrel half | 72.60 g | Already a hollow cosmetic wall. |
| Phone/electronics deck | 72.97 g | Mostly a 3 mm disk with openings and locating rails. Open-web support beneath the actual equipment is preferable to a uniform solid disk. |

These numbers come from the saved geometry report, not a slicer estimate. The thin walls and ribs are already physical solids in the CAD. Assigning an arbitrary low infill percentage to all parts would incorrectly reduce their walls, gear teeth and bearing seats as well as bulk regions.

For PF02, raw positive-box primitives identify where the bulk lies: two 6 x 54.125 x 58 mm bridge walls, a 66 x 54.125 x 6 mm cross panel, two 6 x 41 x 51.23 mm servo walls and a 36.73 x 6 x 51.23 mm rear wall. Their raw volumes overlap, so they are not additive part masses. They explain why merely shaving the 4 mm slider plate will not solve the 154.44 g per-carriage mass.

Use large windows bounded by continuous edge members and diagonal webs in those deep walls, with full material around bearing cups, rail-clamp bolts, the adjuster and the motor reaction nodes. For scale, opening a 38 x 42 mm central window in one 6 mm bridge wall removes about 12.2 g of solid PETG before adding a diagonal rib. Two such windows are useful, but they do not save 100 g each. Keep through-fasteners and metal compression lands. A 6-to-2.4 mm uniform thinning of a flat panel leaves only 6.4% of its original out-of-plane second moment; ribs or return flanges are required.

The body can also lose material without changing the reference outline. Keep the lower deck's root tabs and post lands, and remove non-load-bearing central areas between ribs. Preserve the upper shell/lid rims and handle feet while reducing cosmetic wall area or thickness only where print stiffness permits. Those body walls are already hollow; large savings need a new section, not a density label. The lid handle remains cosmetic and must not become the robot lifting handle.

## What the concealed checkpoint adds

The available `output_oem_checkpoint` is one FL leg, with 168 valid solids, ten positive interferences and one Boolean warning. Its mass is 1,540.874 g, versus 1,343.893 g for the old FL leg: **+196.981 g**. Printed mass rises from approximately 507.60 to 557.02 g, about **+49.42 g**; the remaining **+147.56 g** is hardware. The old foot motor and cradle are absent, and the 98 g motor is counted once at its new location.

Replicating that exact leg four times while leaving the body and supplemental allowances unchanged projects approximately **7.896 kg**, **0.788 kg above** the old candidate. This is explicitly a four-identical-leg projection, not a completed new full-body mass report. Final geometry and fasteners can change it.

The new covers and heat path contribute 127.17 g per leg: 76.86 g of printed covers and 50.31 g of aluminium clamps/spine/fins. Both covers are already hollow, approximately 2.1 to 2.4 mm shells; they are not filled 77 mm-wide blocks. Thinning their walls modestly can recover tens of grams, but cannot remove the added shaft, bearings and gears. Removing cooling metal without replacing its thermal function is not a valid mass fix.

## Define the 20% reserve explicitly

Here, 20% reserve means motor demand no greater than 80% of the assumed torque cap. The caps are 0.7281438 N m continuous and 1.3349302 N m peak, giving targets of 0.5825150 and 1.0679442 N m.

The saved three-contact-equivalent fixture applies 23.2437 N upward to a suspended wheel, equivalent to Mg/3 for the 7.108160 kg robot. Its loaded knee RMS is 0.727899 N m, almost the full continuous allowance. Uniformly scaling all masses and their gravity contributions gives:

`M_target = 7.108160 * 0.582515 / 0.727899 = 5.688439 kg`

That means **1.419721 kg reduction** from the old robot. If hardware mass were unchanged, this would require removing about **50% of all old printed material**, including the parts already modeled as thin shells. It cannot be achieved by shaving the new shin covers alone.

Retaining the old limb masses/COMs and changing base mass alone gives an affine static reconstruction at the saved loaded posture:

`hip_motor_torque = -0.117536*M + 0.305802`

`knee_motor_torque = +0.116285*M - 0.098698`

At the old mass these closely reproduce the saved mean torques. The knee target gives approximately **5.858 kg total**, requiring **1.250 kg removed from the base**. That leaves about 1.199 kg for the base. The two phones, battery, four yaw servos and current 450 g body allowances already total 1.154 kg, leaving roughly 45 g for the body/root structure. Base-only slimming is therefore not a credible route with those assumptions.

The distinction matters: distal weight partly counteracts the upward contact-force knee moment in this folded stance. Removing distal mass or relocating a motor changes both sides of the balance. The 140 mm tibia changes it again. The following checkpoint calculation uses its new COMs rather than reusing those old coefficients.

## Updated 140 mm checkpoint calculation

`static_reserve.py` sums the actual part gravitational moments at each candidate's nominal CAD pose. Both put the wheel 60 mm forward and 190 mm below the hip. The old hip/knee angles are 58.043/-84.717 degrees; the checkpoint uses 62.157/-89.062 degrees. The motor-to-joint gain is the same assumed 2 x 0.85 = 1.7.

| Nominal-pose quantity | Previous candidate | OEM checkpoint |
|---|---:|---:|
| Total mass used | 7.108160 kg | 7.896084 kg, projected from FL |
| Hip input torque, three contacts | -0.521791 N m | -0.481332 N m |
| Knee input torque, three contacts | +0.702640 N m | +0.841481 N m |
| Uniform mass target for 20% continuous reserve | 5.893 kg | **5.466 kg** |
| Base-only mass target for 20% continuous reserve | 6.038 kg | **5.771 kg** |
| Uniform mass target for the unrun two-contact x1.5 peak screen | 4.465 kg | **4.125 kg** |

The new knee demand is 115.6% of the assumed continuous cap even before motion. Its new affine equations for three equivalent contacts are:

`hip_motor_torque = -0.115411765*M + 0.429968640`

`knee_motor_torque = +0.121856303*M - 0.120706323`

The checkpoint's moving limbs already total 5.446877 kg. Its 5.770907 kg base-only bound leaves only 0.324029 kg for the base, less than the two phones and battery alone at 0.484 kg. Base-only slimming is therefore impossible under these assumptions. The uniform 5.466 kg target requires a hypothetical 2.430 kg reduction that also scales motors and hardware; it is not yet an achievable BOM. The old approximately 5.7 kg figure remains evidence for the old loaded fixture, not the target for this new geometry.

These nominal calculations omit compliance, inertia, uneven support and measured servo behaviour. They also use incomplete geometry containing ten assembly interferences. The final mass allocation and corrected COMs must replace the checkpoint before a release decision.

## A more demanding load is a different target

An unrun same-pose counterfactual with two contacts and a 1.5 load multiplier raises the wheel-force term by 2.25, while retaining limb self-weight. At 80% of the assumed peak cap, the resulting mass bounds are approximately **4.310 kg if all masses scale uniformly**, or **4.459 kg algebraically if only base mass changes**. The latter is impossible with unchanged limbs already totaling about 4.659 kg.

At 5.7 kg under uniform scaling, that counterfactual gives a knee demand of roughly 1.412 N m, exceeding even the full 1.335 N m peak cap. It is not a dynamic test or a stair calculation. It demonstrates why the 5.7 kg continuous-reserve target must not be advertised as reserve for every manoeuvre.

The current concealed checkpoint is visually closer to MIST, but it moves the mass budget in the wrong direction. Before functional release, the design needs a closed trade between complete-system mass, reduction ratio, speed/range and permitted contact/load policy. This review makes no geometry change and does not select a new ratio or motor.

Sources and reproducibility: `baseline_mass_ranking.json`, `oem_checkpoint_audit.json`, `oem_checkpoint_static_reserve.json`, `mass_ranking.py`, `audit_candidate.py` and `static_reserve.py` record the source report hashes and calculations. The actual loaded fixture is `simulation/proximal_cad_20260907/load_three_contacts.json`. Its results belong to the old geometry; the new COM calculation is a separate nominal-pose screen.
