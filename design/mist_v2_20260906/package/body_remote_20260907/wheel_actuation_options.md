# Wheel actuation options with body-mounted motors

Checked 7 September 2026. **The ordered ST-3215-C018 genuinely supports continuous velocity operation, but a 2–3× speed-up cannot meet 200 wheel rpm.** Its manufacturer no-load speed is 45 rpm at 12 V. The existing simulation already uses 45 rpm; the 70–100 rpm figure was an unverified hypothesis, not a simulation defect. No ratio, material, controller or CAD changes were made from that hypothesis. FIT0493 remains the current fallback.

## What the exact C018 supports

The controlling source is Feetech's **ST-3215-C018 specification, edition A/0, dated 20 July 2023**, available from the [manufacturer](https://www.feetechrc.com/Data/feetechrc/upload/file/20240507/6385067068652648096680943.pdf) and the [saved local PDF](../../references/C018_manufacturer_spec.pdf). The [current manufacturer product page](https://www.feetech.cn/525603.html) also identifies this exact variant and continuous rotation. Do not substitute a faster STS-family variant's specifications.

Page 5 identifies **mode 1 as closed-loop speed motor operation**, and mode 2 as open-loop speed motor operation. Page 4 specifies no mechanical rotation limit. These support indefinite rotation commanded by speed, rather than repeated finite position moves. The separate ±7-turn position mode is not the wheel-mode evidence. Mode1's description says it regulates speed as load changes; available torque, speed and protection limits still apply. No device mode was written or tested during this research.

| Exact C018 parameter | Published value |
| --- | --- |
| Supply | 12 V nominal;4–14 V permitted |
| No-load speed | 45 rpm ±10% at 12 V,0.222 s/60° |
| No-load / idle current | 180 mA /30 mA, both±10% |
| Rated torque / current | 10kgf·cm = 0.9807 N·m /900 mA |
| Separate stall torque / current | 30kgf·cm = 2.942 N·m /2.7 A, both±10% |
| Body / mass | 45.2×24.7×35 mm /55±1 g |
| Interface | TTL half-duplex serial; speed/current/temperature feedback |

Pages3–5 provide these figures. They do **not** specify S1 continuous duty, a continuous speed-torque curve, winding temperature at rated load, or allowable output-shaft radial load. In particular, the rated torque cannot be combined with the no-load speed to invent an operating point.

The default protection descriptions include overcurrent above 2 A for 2 s and torque disable above 70°C. These are shutdown conditions, not continuous operating ratings. The A/0 environmental range is −10..60°C. The page 6 endurance protocol alternates 60° movements with 0.5 s pauses at one-fifth stall torque. That intermittent test does not validate uninterrupted wheel rotation inside the new body enclosure. Treat thermal performance and actual feedback/protection behaviour as unverified.

## The requested 2–3× speed-up screen

Let `R = wheel speed / servo speed`, so R>1 is a **speed increase**, and let η denote the efficiency of the entire external transmission. Then `wheel rpm = R × servo rpm` and `required servo torque = wheel torque × R / η`. The table uses 85% efficiency only to show the torque requirement; it is not measured belt or remote-drive performance. Wheel size is 85 mm.

| Speed-up R | Nominal unloaded wheel-speed ceiling at 12 V | Corresponding unloaded ground speed | Servo torque needed for 0.17 N·m wheel torque at η=0.85 |
| --- | ---: | ---: | ---: |
| 2 | 90 rpm | 0.401 m/s | 0.400 N·m |
| 2.5 | 112.5 rpm | 0.501 m/s | 0.500 N·m |
| 3 | 135 rpm | 0.601 m/s | 0.600 N·m |

Those torque demands resemble the original 0.4–0.6 N·m hypothesis, but the available **speed does not**. Loaded speeds at those torques are not published, and must not be assumed equal to the unloaded ceilings. Even the positive 10% no-load tolerance gives only 148.5 rpm at 3×. Therefore the 2–3× proposal is rejected for the 200 rpm target without needing a stall-derived performance prediction.

The table assumes a fixed leg pose. A body-fixed drive through moving joints also needs the correct carrier/feedthrough speed compensation; that does not provide a steady-state speed gain. No higher-ratio mechanism was designed after the hypothesis was rejected. The root task retains 4.5–5× and low-voltage tradeoffs outside the default design.

Belt preload and shaft reactions remain unverified. Torque rating alone does not establish that the servo output bearings can carry a tensioned drive pulley. A revived design would need actual pulley radii, belt tension and a supported shaft interface before radial load could be accepted. This note selects no new belt, pulley or shaft dimensions.

## Cost and electronics

The [inventory record](../../../../docs/mist/MIST_ACTUAL_INVENTORY.md) lists 18 ordered 12V30kg servos and an original target of 16 installed, including four wheel servos, plus two spares. Reusing those units avoids another motor purchase if they are available and match the ordered variant. The original unit purchase price is not established by that inventory entry; no new £15 price is inferred from ownership.

A current [RobotShop UK C018 listing](https://uk.robotshop.com/products/feetech-12v-30kgcm-magnetic-encoding-servo-sts3215) displays **£24.32 including tax**, with restocking expected but no usable ETA. That is not an in-stock purchasing recommendation. The existing FIT0493 project allowance is **£25.61 including VAT** per motor. Bought anew, the verified C018 listing does not offer a large bare-motor price saving; owned-stock reuse is the stronger cost argument.

C018 includes its motor drive and velocity controller, so it can reuse the purchased servo bus interface rather than adding a separate wheel H-bridge and external encoder speed loop. That does not remove the controller, bus wiring, power distribution or transmission costs. Actual mode settings, update behaviour, current limits and uninterrupted-duty heating have not been commissioned. FIT0493 and the Cytron comparison both require a brushed-DC driver and encoder processing.

## One credible Cytron comparison

The exact current fast encoder model is **SPG30E-GR30**. Its [manufacturer page](https://www.cytron.io/p-12v-37mm-dc-geared-motor-with-encoder-spg30e-gr30) gives 12 V,333 rpm no-load, and a **rated point of 266 rpm at 0.1118 N·m and 400 mA**. The separate stall figures are 0.4413 N·m and 1.2 A. The [detailed Cytron note](cytron_wheel_motor_note.md) includes the checked drawing and supply search.

That rated point represents approximately 3.11 W. The requested 200 rpm at 0.17 N·m requires 3.56 W before transmission losses. Gearing the rated point down to 200 rpm gives only **0.1487 N·m ideally**, or 0.1264 N·m at the illustrative 85% efficiency. Thus it does not establish the required operating point. A higher-current working point is not justified by the stall specification.

Cytron displayed US$19 and out of stock. No live UK price near £15 price, stock or delivered lead was verified. The current drawing gives a 37 mm gearbox diameter, 69 mm body length and approximately 90 mm to the output tip, excluding wire clearance; exact mass remains unverified. It is larger than the 25 mm-class FIT0493. The older SPG30E-20K is discontinued, and its 225 rpm headline was unloaded; its rated point was 170 rpm at 0.128 N·m.

**Decision:** retain FIT0493 as the known fallback while its current-limited model and thermal duty remain conditional. C018 wheel mode is a real capability but does not rescue the 2–3× speed-up hypothesis. The checked Cytron variant does not establish the target performance or a verified £15 UK replacement. No motor was bought, provider contacted, bench test run, or ratio/material changed.
