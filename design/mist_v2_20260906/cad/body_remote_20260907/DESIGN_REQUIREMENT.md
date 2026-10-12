# All actuators inside the MIST body

The user's clarified preference is to keep every motor inside the body, transferring motion through slim legs. This includes twelve positional joint servos and four continuous wheel motors in the current actuator count. A motor hidden under a shin cover does not satisfy that preference. Slim legs and a faithful MIST silhouette drive the transmission design.

One distinction is being clarified: must every motor housing be rigidly fixed to the chassis, or may an internal motor carrier turn with the hip if it remains completely inside the casing at every pose? Rigid fixation was our stronger initial interpretation. The latter option may eliminate several transmission stages without changing the visible legs, and is being studied alongside strict fixation while the user's answer is pending.

This architecture is mechanically possible in principle. Its fit inside the current180mm body, torque margin, useful travel and practical manufacturing route have not yet been established. The concealed-shin revision is paused; its components, native CAD and failed load results remain useful evidence.

## What must be demonstrated before new full CAD

- A spatial layout for the actual motor envelopes, reduction stages, independent bearings, phones, battery, cooling and service access. Motor volume alone does not establish fit.
- A continuous mechanical path through the chosen yaw or roll joint, the hip and knee, and the continuously rotating wheel. Belts must not twist or change length merely because an upstream joint moves.
- Correct motor/joint angle and torque mappings. Changing motor commands can compensate geometric coupling, but cannot remove the corresponding mechanical loads. A differential that changes load sharing must have a real gear/belt/link mechanism.
- Joint travel within the existing350-degree positional-servo span. Commissioning offsets may move that span; they do not widen it. The wheel motor can rotate continuously.
- Separate accounting for motor relocation and genuine mass removal. Moving a motor into the body reduces moving-leg mass but does not remove its weight from the robot. New shafts, bearings, pulleys and tensioners must be counted.
- Stiffness, accumulated lost motion, positive torque connections and belt pretension supported by calculations and a small mechanical test. The servo's internal angle sensor does not measure flex or backlash downstream of the transmission.
- An assembly sequence that can be executed with the intended printing and workshop resources. Identify bought or machined shaft/hub interfaces rather than depicting an unconnected plain bore as a completed drive.

## Evidence informing the direction

[Stanford Doggo's original engineering account](https://github.com/Nate711/StanfordDoggoProject/blob/master/README.md#mechanical-design) describes body-panel motors driving coaxial leg shafts through belts. It also reports the practical penalties of pulley/shaft play, extra tension and friction. That is useful precedent for concentrating actuators in the body; its planar five-bar leg does not directly establish this three-joint, wheel-driven MIST arrangement.

The preceding concealed-shin study projected7.896kg before its final mounting hardware. Its provisional suspended three-contact test required0.9068Nm knee shaft RMS against the assumed0.7281Nm continuous limit. A hypothetical3:1 reduction improved that to0.5845Nm with19.73% reserve, narrowly short of the chosen20% screening margin. These are results for the preceding geometry and must not be presented as a new body-fixed design verdict.

The current native Fusion assembly has267solids: the33-part body and117-part proximal sections onFL andRR. Those sections are preserved rather than extended under the rejected motor-placement architecture. Fusion access is working. No purchase or physical robot actuation has been performed.
