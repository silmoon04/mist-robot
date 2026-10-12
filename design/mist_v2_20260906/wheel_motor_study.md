# MIST wheel drive study, 6 September 2026

The best documented small purchased motor found is the **DFRobot FIT0493, 12 V, 350 rpm, 25 mm gearbox, 98 g, with encoder**. Its UK price is about **GBP 25.61 including VAT per motor**, before the driver. It can plausibly give a 3–4 kg MIST roughly 1 m/s on 70 mm wheels, subject to the loaded motor tests below. The requested GBP 15 price is not met by this choice.

There is also a useful route using parts already ordered: drive each wheel from an STS3215 through a **7.5:1 external speed increase**. That converts the servo's surplus wheel torque into useful rolling speed. It needs a two-stage transmission and introduces considerable angular play at the wheel. Keep it as a cost comparison for a single wheel rig before committing four sets of parts.

This document is a design screen, not a claim of continuous motor capability or a completed stair test. The companion `wheel_motor_calculations.py` regenerates `wheel_motor_envelopes.json`, containing 1,620 analytic cases across mass, voltage, wheel diameter, contact count and motor choice.

## Design inputs

The ordered inventory records 18 Feetech ST-3215-C018 servos, two HOOVO 3S 2200 mAh packs, bus adapter, ESP32, UBECs, distribution board and wiring accessories. The old complete-robot estimate is approximately 3.22 kg, with some later inventory estimates closer to 3.55 kg. This study therefore screens 3, 3.5 and 4 kg. A second mounted phone, remote joint transmissions, shafts and bearings must be included in the next measured mass budget. One battery is mounted at a time. See `docs/mist/MIST_ACTUAL_INVENTORY.md` and `docs/mist/MIST_MATERIAL_DIMENSIONS_MASS.md`.

The original master wheel is 70 mm OD. The new simulation also considers 85 and 100 mm. Increasing 70 to 85 mm raises both the speed at a given rpm and the torque needed for a given ground force by 21.4%. Keep the tire's loaded radius as a separate measured value; soft TPU deflection changes it.

Working targets are 1 m/s rolling speed and 1 m/s² acceleration on level ground, with a low body pose, four loaded wheels and aligned wheel headings. These are screening requirements, not yet validated robot performance. A 175 mm stair riser requires articulated leg placement. None of these wheel sizes makes an ordinary stair into a rolling ramp.

The old radial hip-roll/pitch/knee chain cannot be assumed to satisfy the aligned-heading condition. Its wheel axle stays tangential in horizontal projection at each fixed leg azimuth, so the four wheels scrub if commanded to drive straight without suitable leg motion. The new hip-yaw design must demonstrate a reachable, collision-free steering pose for all four wheels. Test lateral slip explicitly; an isotropic sliding contact can conceal this error in a simulation.

## Candidate comparison

All speeds below are no-load unless marked otherwise. Stall figures are not operating ratings. UK prices and stock were checked on 6 September 2026; shipping is separate and no purchases were made.

| Option | Maker speed, torque and mass | Price evidence | Design verdict |
|---|---|---|---|
| Owned Feetech ST-3215-C018, direct wheel | 45 rpm at 12 V; 0.981 N·m rated torque; 2.942 N·m stall; 55 g | Already ordered | Strong enough, but only 0.165 m/s with 70 mm tire before load. Useful first motion baseline. |
| Same servo, external 7.5:1 speed increase | Calculated 337.5 rpm; 0.111 N·m output from rated torque at assumed 85% efficiency; servo plus estimated 30–60 g transmission | No new motor, driver or encoder; belts/pulleys/bearings still need inventory match | Plausible low-cost rolling drive. More parts and more wheel play; lower slope margin. |
| Waveshare DCGM-N20-12V-EN-200RPM | 200 rpm; 0.118 N·m locked-rotor torque; up to 1.1 A locked current; 18 g listed | [Waveshare direct](https://www.waveshare.com/product/modules/motors-servos/dcgm-n20-12v-en-200rpm.htm), US$6.99 before UK landed costs | Cheap and light, but too little power and speed margin for this whole robot. |
| Pololu #5214, N20 HPCB 12 V 75:1 encoder | 450 rpm; 0.098 N·m stall at 0.75 A; 11 g | [Maker specifications](https://www.pololu.com/product/5214/specs); UK delivered price not verified | Useful documented fast N20 reference. The torque screen rejects it for the requested acceleration and slopes. |
| **DFRobot FIT0493, 25 mm** | **350 rpm; 1.177 N·m stall at 5.5 A; 98 g** | [DigiKey UK](https://www.digikey.co.uk/en/products/detail/dfrobot/FIT0493/7087166), GBP 21.34 ex VAT / **25.608 inc VAT**, 53 stock. [RobotShop UK](https://uk.robotshop.com/products/12v-dc-motor-12kg-cm-350rpm-encoder), GBP 26.77 inc VAT, two stock | Best purchased balance of distal mass, speed and price found. Needs external driver. |
| Pololu #4843, 25D HP 20.4:1 encoder | 500 rpm; 0.726 N·m extrapolated stall at 5 A; 98 g | [Maker product](https://www.pololu.com/product/4843), US$56.95 before UK landed costs | Faster documented reference with better characterized curves, but expensive. |
| DFRobot FIT0186, 37 mm | 251 rpm; 1.765 N·m stall at 7 A; 205 g | [DigiKey UK](https://www.digikey.co.uk/en/products/detail/dfrobot/FIT0186/6588528), GBP 12.14 ex VAT / 14.568 inc VAT, 929 stock | Meets bare-motor price. Adds 428 g across four legs versus FIT0493 and is slower. Reject for a light, responsive leg unless price dominates. |
| Waveshare DCGM-3865-12V-EN-240RPM | 240 rpm no load; **rated 0.392 N·m at 125 rpm**, at most 1 A; 167 g listed | [Waveshare direct](https://www.waveshare.com/product/robotics/motors-servos/motors/dcgm-3865-12v-en-240rpm.htm), US$9.99; UK delivered price not verified | More useful torque documentation but only 0.46 m/s at the rated point on 70 mm wheels. |

The STS figures are for the ordered C018 variant, from the [Feetech manufacturer specification hosted by RobotShop](https://cdn.robotshop.com/media/F/Fit/RB-Fit-155/pdf/feetech_12v_30kg_cm_magnetic_encoding_servo_sts321_specification_pdf.pdf). The specification permits 4–14 V. Other STS3215 variants must not inherit these numbers.

The current [FIT0493 maker page](https://www.dfrobot.com/product-1462.html) lists a maximum-efficiency point of 0.196 N·m at 285 rpm and 0.65 A, plus 0.23 A no-load current. It does not give a continuous thermal duty. The quoted torque and rpm imply 5.85 W, whereas the page says 5.0 W; its listed maximum-power point also has inconsistent power. An older distributor PDF gives a different no-load current. Keep those source values separate from the endpoint-linear estimate, and characterize the actual motor before trusting a thermal model. The [FIT0186 maker wiki](https://wiki.dfrobot.com/fit0186/) identifies its 18 kg·cm figure as stall torque, even though a distributor labels that number as rated torque.

## Torque and speed calculation

For equal load across `n` driven contacts:

```text
wheel torque = m [a + g(sin(slope) + Crr cos(slope))] r / n
wheel speed = rpm × 2πr / 60
rpm(V, torque) ≈ rpm0(12 V) [V/12 − torque/stall_torque(12 V)]
current(torque) ≈ I0 + (Istall − I0) torque/stall_torque
```

The script uses `Crr = 0.03` as a provisional smooth-floor rolling-resistance coefficient. This is an assumption, not a TPU measurement. Carpet, tread deformation, misaligned wheels and turning scrub can cost much more. Rotor, pulley and wheel inertia are omitted from this first calculation, so retain at least 25% acceleration torque margin until inertia and steering losses are added. Uneven load sharing must use each wheel's actual normal force and requested traction.

At 4 kg and four contacts, 1 m/s² acceleration needs **0.0453 N·m per 70 mm wheel**, or **0.0550 N·m per 85 mm wheel**. Steady motion on a 15° slope needs 0.0988 and 0.1199 N·m respectively. With only two driven contacts, those slope torques double. This is why a motor that moves the robot on a floor can still fail during a stair transition.

No candidate's stall torque is used as continuous torque. For the Pololu motors, the manufacturer advises operation at roughly 25% or less of stall current; this is a general motor-life guideline, not a guaranteed thermal rating. Its 25D gearbox has a separate 0.392 N·m continuous-load mechanical recommendation, which does not override a lower motor thermal limit. [Pololu 25D operating guidance](https://www.pololu.com/product/4843).

| Drive | Provisional wheel torque ceiling used in the screen | Basis |
|---|---:|---|
| STS direct | 0.841 N·m | Conservative linear current estimate capped at the maker's 0.9 A rated current; below 0.981 N·m maker rated torque |
| STS with 7.5× speed increase | 0.0953 N·m | Same current limit, multiplied by 0.85/7.5 |
| Pololu fast N20 | 0.0157 N·m | 0.1875 A, 25% of 0.75 A nominal stall current |
| Waveshare N20 200 rpm | 0.0206 N·m | Screening assumption of 25% stall current, not a Waveshare continuous rating |
| Pololu 25D HP | 0.1467 N·m | 1.25 A, 25% of 5 A nominal stall current |
| FIT0493 | 0.1719 N·m | Analyst-selected 1 A current ceiling with current maker endpoint data; conditional on measurement |

For a **4 kg robot at 10.5 V**, flat floor and 1 m/s² acceleration, the script predicts:

| Drive | 70 mm wheel speed | 85 mm wheel speed | Torque screen |
|---|---:|---:|---|
| STS direct | 0.142 m/s | 0.172 m/s | Pass; slow |
| STS, 7.5× speed increase | 0.914 m/s | 1.067 m/s | Pass; 85 mm case has 1.73× provisional torque margin |
| Pololu 75:1 N20 | Not sustained | Not sustained | Fail; required current exceeds provisional limit |
| Waveshare 200 rpm N20 | Not sustained | Not sustained | Fail |
| Pololu 25D HP | 1.489 m/s | 1.779 m/s | Pass in this analytic model |
| FIT0493 | 1.073 m/s | 1.290 m/s | Pass in this analytic model |

These figures are motor predictions, not achieved driving speeds. At 85 mm and 4 kg, the 15° four-contact slope screen passes the two 25 mm motors but fails the 7.5× STS drive's conservative continuous current limit. It fails both 25 mm motors at two contacts under the same provisional limits. Terrain speed must therefore depend on posture, contact state, measured current and temperature. Gear ratio, motor temperature and unit variation can reduce these figures further.

## Packaging, shaft support and mass

FIT0493's maker-linked drawing gives a **25 mm diameter, 21 mm long gearbox**, 24.4 mm motor diameter, and **61 mm from gearbox face to encoder rear**. Its output shaft projects 12 mm, making **73 mm total**, before cable bend space. The shaft is 4 mm diameter with a 3.5 mm dimension across the flat; the flat is 8 mm long. The pilot is 7 mm diameter. Use these as supplier geometry, then measure the delivered part. [Manufacturer-linked drawing](https://raw.githubusercontent.com/Arduinolibrary/DFRobot_12V_DC_Motor_350RPM_with_Encoder/master/Dimension.png).

The Pololu reference is 25D × 65 mm plus its 12.5 mm shaft. A FIT0493 cartridge can share the broad tibia envelope, but its fasteners, pilot, shaft engagement and rear clearance need separate parameters. Do not treat the two motors as a blind interchange. [Pololu #4843 dimensions](https://www.pololu.com/product/4843/specs).

Use a short wheel axle supported by two bearings and a clamped hub. Transfer only torque from the motor shaft through a compliant coupling or a small belt stage. The bearings and tibia carry the foot impact, side loads and overturning moment. Do not use the motor's 4 mm output shaft as a cantilever foot spindle. Leave the motor removable without splitting the entire leg, and shield the encoder/cable connector from the floor.

The user's recent bearing order is not dimensionally verified. Small 5 or 6 mm bore bearings may save substantial mass versus using 608 bearings everywhere. Design the cartridge from measured bore, OD and width, with retention shoulders and screws; do not infer a fit from the phrase skateboard bearings. A bearing bore and a 3D-printed sliding pin need different coupon tolerances.

Budget **125–155 g per purchased 25 mm drive**, excluding the tire and hub: 98 g motor, 5–10 g driver/connectors, 12–20 g carrier and 10–25 g axle/support bearings. An initial 140 g simulation allowance is reasonable. A 60 g wheel/hub therefore makes approximately 200 g at the distal end. These estimates must be replaced by sliced and weighed components. Place the motor toward the knee where a short belt can reduce distal inertia, but add belt loss, support mass and backlash before claiming a benefit.

For the owned-servo route, two belt stages can produce 7.5× speed increase: **60 teeth driving 16, followed by 32 driving 16**. At an illustrative 3 mm pitch, pitch diameters are 57.3, 15.3, 30.6 and 15.3 mm. These are ratio examples; they do not prove that the user's belts have matching pitch, width, tooth form or length. Keep purchased small pulleys where available. Print larger pulleys flat so belt tension is carried mainly within the layer plane, use steel shafts and bearings, and clamp the hub rather than relying on a printed set-screw thread. Provide tension adjustment, adequate small-pulley wrap and guards.

That speed increase also multiplies output angular play. An assumed 1–2° servo reversal deadband becomes 7.5–15° at the wheel before the new belt/pulley errors, corresponding to approximately 4.6–9.2 mm tread displacement at 70 mm OD. This is a sensitivity example, not a measured C018 backlash. The servo encoder is upstream of the added transmission. A separate wheel encoder is needed if centimeter-scale stopping/reversal error is unacceptable. The speed-up assembly is estimated at 85–115 g before tire/hub; prove its layout and stiffness before choosing it on mass alone.

## Driver, battery and wiring

The existing 3S battery reaches 12.6 V when full. C018's rated input range includes this. For a nominal 12 V DC motor, use voltage feed-forward to cap effective drive near 12 V, including a maximum duty of about 95.2% at 12.6 V, and use active current regulation. PWM still applies battery-amplitude pulses; the driver needs voltage headroom for regeneration and wiring transients. A 2S supply gives only about 62% of the nominal 12 V no-load speed at 7.4 V. A 5 V logic rail is unsuitable as the wheel drive supply. The JSON includes lower-voltage cases to show the penalty; they do not authorize sharing a UBEC with four wheel motors.

**Pololu #4035 DRV8874** is a credible one-motor driver module. It provides adjustable active current limiting and current feedback, accepts 4.5–37 V, and has a maker-tested 2.1 A continuous board rating in open room-temperature air. It weighs 0.9 g before headers and wiring. The chip's peak rating is not the carrier's continuous rating. Start the FIT0493 rig at a verified 1 A hardware limit; enclosed-tibia thermal performance remains to be tested. [Pololu driver documentation](https://www.pololu.com/product/4035).

UK purchase evidence: [RobotShop](https://uk.robotshop.com/products/pololu-drv8874-single-brushed-dc-motor-driver-carrier) lists GBP 11.02 inc VAT with one in stock; [DigiKey Marketplace](https://www.digikey.co.uk/en/products/detail/pololu/4035/26714680) lists GBP 8.79 ex VAT / 10.548 inc VAT, shipping from Pololu, with a separate delivery charge possible. FIT0493 plus that driver is therefore about **GBP 36.16–36.63 per wheel before mounts, bearings and shipping**, or GBP 145–147 for four motor/driver sets. Encoders and motor cables are included with the motor. Ordinary DigiKey UK delivery was shown as GBP 22 below GBP 65; Marketplace shipping has separate terms.

The cheaper [Adafruit DRV8871 at The Pi Hut](https://thepihut.com/products/adafruit-drv8871-dc-motor-driver-breakout-board-3-6a-max) was GBP 7.30 but sold out. It also lacks the same direct current-feedback interface. Do not substitute a common 10.8 V driver board onto the raw 3S rail. No PCB design is needed for this stage.

Wire each DC driver from an appropriate fused raw-battery branch with a common logic ground. Twist the motor pair, keep it away from encoder lines, strain-relieve both ends, and route through the measured leg motion envelope. Confirm the encoder's supply and output voltage before connecting to ESP32 inputs. Its vendor pulse-count convention must be measured with one marked wheel revolution; x1 pulse counts and x4 quadrature counts are not interchangeable. Put velocity control on the local controller, with bounded commands and a command timeout.

Four FIT0493 motors have a combined **22 A stall specification** before any joint servo load. A branch fuse is too slow to protect a stalled miniature motor. Hardware current limiting, stall detection and local command timeout belong in the drive control. Include driver voltage drop, measured pack sag, phone power and the joint branch currents in the full power model. Compare loaded 12.0, 11.1 and 10.5 V in testing; 10.5 V is a sag scenario, not a recommendation to deeply discharge the pack.

## Stair behavior and physical acceptance

For stairs, the leg places the wheel beyond the edge and carries the vertical lift. The wheel supplies tread traction and controlled braking. The body must stay inside the remaining support polygon, and the controller must account for unloaded contacts. A parked wheel with motor power removed is not a brake. Power-on holding torque, controlled descent and the response to power loss need separate tests. At a stair lip, temporary contact forces can be much higher than the equal-load rolling calculation.

Even with sufficient motor torque, a 15° steady slope with the assumed rolling resistance requires a friction coefficient of at least `tan(15°) + 0.03`, about 0.298 before any acceleration or margin. Measure the actual TPU tire against the intended floor and stair finish, including dust and unequal contact loading. Motor power does not compensate for insufficient friction.

Before a motor choice is frozen, test one complete wheel cartridge with a guarded drum or spring-scale rig:

1. Measure actual wheel OD under load, assembly mass, wheel/shaft runout, gearbox play and the encoder count convention. Verify current limiting independently before a loaded run.
2. Record no-load and loaded rpm/current at 12.0, 11.1 and 10.5 V. Test 0.05, 0.10 and 0.15 N·m for the purchased candidate, starting at the lightest load. Do not apply a deliberate sustained stall.
3. Log motor-case, driver and nearby PETG temperature while cycling representative starts, stops and low-speed holds, followed by a sustained rolling-load run. Extend until temperature approaches a stable trend. The test temperature limits must come from the component/print limits and a measured case-to-winding allowance; a cool case alone does not prove safe windings.
4. Test forward/reverse motion and braking under the intended current limit. Log latency, stopping distance, output reversal error and supply-voltage rise. Repeat with the real encoder cable and joint actuators moving nearby.
5. For the STS alternative, repeat with the complete 7.5× transmission. Confirm that wheel mode reaches the expected speed continuously, measure added loss, belt tooth skipping, reflected play, bearing heat and tire-position error. The 45 rpm servo specification alone does not prove the assembled drive.
6. Use the measured motor curve, inertia, current limit, backlash and thermal derating in the robot simulation before speed increases or stair trials. First tests on the assembled leg should keep the body supported and use the actual installed wheel mass.

Choose FIT0493 if the motor budget can grow and a simple local velocity loop is preferred. Choose an owned-STS speed-up prototype if avoiding four new motors matters more than assembly simplicity. Reject the light N20 choice for this 3–4 kg target unless the required acceleration, grade and contact-force envelope are reduced and measured to match it.
