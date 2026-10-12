# Cytron wheel motor check

Checked 7 September 2026. Target: a body-mounted encoder gearmotor near 200 wheel rpm and 0.17 N·m working torque, with an approximately £15 UK component price. Supplied comparator: FIT0493, £25.61 including VAT, 98 g, 350 rpm no-load, 1.177 N·m stall; approximately 0.172 N·m estimated at the 1 A winding-current cap. No purchase, supplier contact or bench test was made.

**No buyable UK SPG30E variant meeting that price and operating-point target was verified.** The real current fast variant below is a technical comparison, not a £15 UK purchasing recommendation. It does not reach the requested rated power even before remote-transmission losses.

## One current variant: SPG30E-GR30

[Cytron's exact encoder product page](https://www.cytron.io/p-12v-37mm-dc-geared-motor-with-encoder-spg30e-gr30) identifies **SPG30E-GR30**, distinct from the non-encoder SPG30-GR30. Its table states:

| Parameter | Value |
| --- | --- |
| Gear ratio | 30:1 |
| Rated voltage | 12 V |
| No-load speed / current | 333 rpm / 120 mA |
| Rated load speed | 266 rpm |
| Rated load torque | 1.14 kgf·cm = 0.1118 N·m |
| Rated current | 400 mA |
| Stall torque / current | 4.5 kgf·cm = 0.4413 N·m / 1.2 A |
| Encoder | Incremental, advertised 16 PPR; 3.3–5 V supply |
| Harness | Non-detachable wires with 2.54 mm female headers |

Cytron displayed **US$19.00** and **out of stock** for this exact encoder variant. No UK seller price, VAT-inclusive total, stock or delivery date was verified. A dollar conversion would not establish a delivered UK price. The linked current encoder datasheet folder returned 404 during this check; the product page and dimensional image were available. No explicit continuous-duty class, thermal-rise limit or endurance test was established from them.

## Actual current geometry

The [Cytron encoder-motor dimension drawing](https://static.cytron.io/image/catalog/products/V-SPG30/v-spg30-dimension-spg30e-v2.png), linked from the current product page, was visually inspected. For GR30 it gives gearbox length L = 22 mm and motor/encoder section length 47 mm. Thus the calculated body length is 69 mm; adding the 21 mm front boss/shaft projection gives approximately 90 mm to the output tip, excluding wire clearance.

The gearbox diameter is 37 mm and motor/encoder section diameter 35 mm. The output is a 6 mm D-shaft, 5.5 mm across the flat, with 15 mm shaft projection beyond the boss and 12 mm flat length. The locating boss is 12 mm diameter. The drawing marks M3 mounting holes on a 31 mm pattern diameter, and a 7 mm offset between output and body axes. Confirm mounting-thread depth from the actual delivered revision; do not transfer the older SPG30E-20K's thread-depth data automatically.

**Exact mass was not verified.** Do not reuse an older SPG30E weight or infer that its mass matches the 98 g FIT0493. The current 37 mm diameter and approximately 90 mm overall envelope already require a larger body mounting allowance than the supplied 25 mm-class FIT0493.

## Operating-point comparison

At the published rated point, GR30 output power is calculated as:

`0.1118 × 2π × 266/60 = 3.11 W`

The requested wheel point requires:

`0.17 × 2π × 200/60 = 3.56 W`

A passive reduction from 266 to 200 rpm would ideally multiply torque by 1.33, yielding only **0.1487 N·m**. At an illustrative 85% transmission efficiency it becomes **0.1264 N·m**. That efficiency is an assumption, not a measured remote-drive value. Consequently the published rated point misses 0.17 N·m at 200 rpm before considering the enclosure, cable/belt/gearing losses or shock margin.

Alternatively, ideal reduction to 0.17 N·m would put wheel speed near 175 rpm; at 85% efficiency, near 149 rpm. These are transmission calculations at the rated motor point, not a complete motor curve. Do not extrapolate a safe 1 A working point from the 1.2 A stall current, and do not compare the 0.4413 N·m stall value against a continuous target.

The supplied FIT0493 estimate and Cytron's rated point have different evidence bases. The former comes from the main task's current-limited model; the latter is a manufacturer operating point without explicit continuous-duty conditions. Neither substitutes for a thermal/duty check in the actual body enclosure.

## Encoder and driver requirements

The motor needs a bidirectional brushed-DC H-bridge for a 12 V supply. As an implementation choice, a 2 A-class channel provides margin over the published 1.2 A stall current, with current limiting set to the validated operating envelope. Driver current capacity is not permission to operate the motor at that current continuously.

The encoder needs its own 3.3–5 V supply and compatible logic input levels, plus two-channel pulse acquisition for speed/direction feedback. Cytron labels the current encoder 16 PPR; confirm whether that means cycles per motor revolution or counted quadrature edges before assigning counts per output revolution. The older SPG30E 7-PPR/3-PPR documentation must not be combined with this new GR30 encoder. No built-in speed controller is claimed.

## Why the older near-200 rpm listing was not selected

[Cytron T-SPG30E-20K](https://www.cytron.io/p-12v-225rpm-1.3kgfcm-brushed-dc-geared-motor-with-encoder) is a real product, but Cytron marks it **discontinued**. Its 225 rpm figure is no-load; its rated point is 170 ± 17 rpm at 0.128 N·m and less than 570 mA. It would still miss 0.17 N·m at 200 rpm at that point. No live UK stock/price was found. The surviving [RobotShop-hosted 20K manufacturer drawing](https://cdn.robotshop.com/media/c/cyt/rb-cyt-81/pdf/schema-spg30e-20k_r2.pdf) does not prove current sale availability.

The suffix is a gear-ratio identifier, not an rpm promise. No SPG30E-200K or similarly slow variant was substituted to obtain a convenient torque or price. Searches at RobotShop UK, The Pi Hut and Pimoroni did not establish the requested exact, buyable UK motor. The current GR30's US$19 display also does not substantiate an approximately £15 UK cost saving.

## Result for the design decision

Keep GR30 as a rejected rated-point comparison for the present 200 rpm / 0.17 N·m target. Selecting it would require lower wheel performance, a separately justified higher-duty operating point, or a different motor. Its mass, actual UK landed price and delivered lead remain open; do not freeze them into the BOM as 98 g or £15.
