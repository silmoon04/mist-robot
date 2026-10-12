# One overnight run of R7 leg parts

Open R7_Overnight_Leg_Parts.3mf as models in Cura and import/select Tree_Undersides_R7_PLA_028.curaprofile. The 3MF is a geometry plate, not a Cura project: it does not select the profile automatically. A combined STL is included as a fallback. Keep 100 percent scale and the supplied orientations.

CuraEngine estimates 9 h 50 min and 147.7 g PLA. Heating and actual printer firmware can change the duration. All eight parts print together in one run. The model footprints have at least 12 mm separation, and the generated motion fits the printer envelope.

The profile uses the existing Neptune 4 Pro, 0.4 mm nozzle and PLA process: 0.28 mm layers, five walls, 25 percent gyroid, 210 C nozzle, 60 C bed, slow overhangs and bridges, and build-plate tree supports. No machine-ready G-code is supplied. Keep the printer's usual monitoring and confirm the first layer; the files cannot guarantee an unattended print.

## Included

1. Coxa upper bracket with hip saddle.
2. Matching longer lower yaw arm.
3. Femur main bracket with knee saddle.
4. Femur auxiliary cheek with integral annular stand-off.
5. Straight tibia and foot.
6. Tibia auxiliary cheek with integral annular stand-off.
7. Hip case cap.
8. Knee case cap.

The original R7 geometry is unchanged. Only arrangement on the bed and rotations around print Z changed. Mesh, spacing, source hashes, profile values, engine envelope and sampled support-intrusion checks passed. The larger batch was sliced again; this is not just a sum of previous time estimates. Accessible support in the open coxa screwdriver scallop still needs removal.

## What to keep from earlier prints

| Earlier item | What to do |
| --- | --- |
| Flat case cap from the first/second fit set | Reuse it for the yaw servo. The matching-cap export has exactly the same STL hash as the R7 yaw cap. The batch supplies the two additional caps needed for the other servos. |
| Four nominal 11.6 mm yaw spacers | Keep a matching set. The nominal geometry is still OD5.8, ID3.4, length11.6. Your measured 11.4-ish height may include printing error. Confirm a uniform set and free rotation during assembly; do not mix short/long comparison samples. |
| Existing nose-up saddle/clamp | Keep it. Its fitted case pocket and mounting pattern remain useful, but its nut-seat depth differs from R7. Do not approve it for loaded use from case fit alone: verify full nut engagement with the available M3x30 screws. It is omitted from tonight's batch pending that check. |
| Old lower yaw arm | The earlier arm is approximately 47 mm long; R7 is 59 mm long and has wider washer recesses. Use the new arm for this leg. |
| Short horn cheeks and the M30 fixture bridge | Keep them as the alignment/rotation test fixture. They do not replace the complete femur or tibia and their integrated bridges. |
| 4 mm phone-pan spacers | Keep them for the phone-mount stage, subject to its final stack. |
| Gauge spacers and alternative clearance samples | Keep them identified as test pieces. Do not use them interchangeably with yaw spacers. |

The large ribbed base from plate 01 is a temporary bench fixture. It is not the final robot body and is excluded here. A securely mounted existing board or fitting fixture can avoid printing that base; the eventual robot body will carry the leg. A complete leg still needs a satisfactory yaw-servo saddle, whether the existing one proves suitable or its replacement becomes necessary.

## Hip pivot and balance

The current R7 hip pivot is already at the outward end of the servo, with the case extending toward the body. This is the direction indicated by the marked older-model image. It is not necessary to flip R7 back again.

The shaft lies 12.5 mm from the case centre. Holding the case centre in place while reversing its direction moves the pivot by 25 mm. It does not automatically move the whole motor farther outward. If the foot also moves outward by 25 mm under the same vertical force F, bending at the yaw support increases by F times 0.025 metres. For example, 5 N gives 0.125 Nm extra bending. This is not torque about the vertical yaw axis. If the foot position stays fixed and the joint angles change instead, that foot-force lever at the coxa stays fixed too.

Three-foot support is compatible with this geometry in principle, but the centre of mass must be placed inside the support triangle for a static margin. A centred rectangular four-foot stance puts the centre on a triangle edge when one corner is lifted, so a weight shift is normally needed. Two small feet give a very narrow static support region and require much more careful balance control. Even with ideal equal sharing, average load per supporting leg is 50 percent higher on two feet than on three. Neither a successful unloaded leg animation nor the hip flip proves two-foot balance or adequate loaded torque.

The contact-force and support-region reasoning follows MIT's Underactuated Robotics notes: https://underactuated.mit.edu/humanoids.html

## Scope

These are functional robot leg parts intended to carry forward, not another coupon plate. They remain the first complete physical leg prototype. The R7 conservative strength screens still flag bridge load qualification, so zero future revisions cannot be promised. Begin with restrained, unloaded articulation and use the R7 assembly guide. The auxiliary horn fixings use M3x12 with two 0.5 mm flat washers; longest screws remain M3x30. Washer thickness still needs confirmation. The supplied assembly guide is copied from the R7 release.
