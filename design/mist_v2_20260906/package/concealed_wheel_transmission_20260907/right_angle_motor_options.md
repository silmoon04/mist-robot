# Compact right-angle wheel motor comparison

Checked 7 September 2026. The retained design uses an 85 × 24 mm wheel and FIT0493 motor, approximately 61 mm × 25 mm, longitudinally in the upper tibia. The supplied working estimate is about 0.172 N·m at the 1 A winding-current cap; 1.177 N·m is stall torque, not the working design point. No purchase or supplier contact was made. This note contains two alternatives and does not change the CAD selection.

DFRobot FIT0489-D is the strongest documented alternative within the component-price target. Its rated load exceeds the current torque estimate, but it is slower, larger and explicitly self-locking. Adafruit 3802 is a much cheaper compact comparison, but its torque and drawing evidence are insufficient to replace the current drive. Neither is a verified drop-in improvement.

## 1. DFRobot FIT0489-D, 150:1 metal worm gearmotor

| Parameter | Manufacturer specification |
| --- | --- |
| Rated / operating voltage | 12 V / 6–15 V |
| Rated torque | 2.2 kgf·cm = 0.2158 N·m |
| Rated speed / current | 32 rpm / 180 mA |
| No-load speed / current | 40 rpm / 35 mA |
| Stall torque / current | 8 kgf·cm = 0.7845 N·m / 1 A |
| Gearbox | Metal, 150:1 worm, perpendicular output |
| Mass | 167 g |
| Continuous-duty evidence | Rated operating point published; no explicit S1 duty or thermal/endurance curve found |

Source: [DFRobot FIT0489-D](https://www.dfrobot.com/product-1484.html). The manufacturer mislabels the 32 rpm entry as torque; it is interpreted as rated speed from its unit and sequence. Its separate 8 kgf·cm headline is the stall value. The 1 A cap would coincide with this motor's stall current, so it cannot serve as its continuous current target.

**UK-facing purchase route:** [TME DF-FIT0489-D](https://www.tme.eu/gb/details/df-fit0489-d/dc-motors/dfrobot/fit0489-d/) showed **£14.41 excluding / £17.29 including VAT**, **63 in TME stock**, minimum one. Delivery costs are additional; UK-held inventory was not established. [DigiKey UK](https://www.digikey.co.uk/en/products/detail/dfrobot/FIT0489-D/7087173) showed £13.91 excluding / £16.69 including VAT and 62 in stock, but its displayed £22 delivery below £65 makes a single motor exceed £25 through that route.

**Drawing:** the [manufacturer PDF hosted by DigiKey](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/2554/FIT0489-D_Web.pdf), page 2, was rendered and visually inspected. The same family drawing is [linked on DFRobot's product page](https://dfimg.dfrobot.com/enshop/image/data/FIT0489/Dimension_0x0.png.webp). It gives:

- Gearbox front outline 32 × 46 mm; motor barrel diameter 24.4 mm and length 30.8 mm. Terminal projection is 4.2 mm, yielding a calculated longitudinal envelope of 81 mm including terminals, or 76.8 mm excluding them.
- A side-view depth callout of 25.2 mm and a separate 18.5 mm shaft/bearing projection. Use the drawing's reference planes before combining these; 18.5 mm is not all usable coupling length.
- Output shaft diameter 6 mm, D-flat dimension 5.4 mm, flat length 12 mm.
- Four M3 × 0.5 mounting threads, marked effective depth 12 mm, on an 18 × 33 mm rectangular pattern. The rows are 6 mm and 7 mm from the gearbox ends. The output axis is centred across the 32 mm width and 15 mm below the top gearbox edge.

This body is longer and wider than the supplied FIT0493 envelope. The output-shaft bearing and gearbox radial-load capacity were not rated in the inspected documents; the wheel should remain supported by the designed wheel bearings unless the supplier confirms direct cantilever loading.

At the stated rated point, an 85 mm wheel would give `π × 0.085 × 32/60 = 0.142 m/s` and `0.2158/0.0425 = 5.08 N` tangential force, before other losses. Torque is approximately 25% above the supplied 0.172 N·m estimate. This comparison does not establish how long either motor can sustain its point inside a concealed housing.

**Worm-drive consequence:** DFRobot explicitly describes the output as self-locking. Electrical polarity reversal drives it in both directions; that does not imply that the wheel can backdrive the motor. No forward/reverse efficiency map or backdrive threshold was published. In this wheel application, self-locking changes unpowered rolling and obstacle-impact behaviour: wheel torque is reacted through the gearbox and mount rather than freely spinning the motor. A switch would need a deliberate decision about rolling drag, external push/impact loads and controller behaviour. Self-locking is not treated as a wheel-drive advantage here.

## 2. Adafruit 3802, TT all-metal gear train, 90:1

[Adafruit's product page](https://www.adafruit.com/product/3802) specifies steel gears and a perpendicular TT output. It reports one bench-tested sample, rather than a guaranteed performance curve:

| Supply | No-load speed / current | Measured stall current |
| --- | --- | --- |
| 3 V | 60 rpm / 80 mA | 0.5 A |
| 4.5 V | 90 rpm / 90 mA | 0.8 A |
| 6 V | 120 rpm / 100 mA | 1.0 A |

No reliable rated torque, stall torque or continuous current was established. The gear-train input mechanism, backdriving torque and reverse efficiency are not specified, so no non-worm or freely backdrivable claim is made.

**UK stock:** [The Pi Hut ADA3802](https://thepihut.com/products/tt-motor-all-metal-gearbox-1-90-gear-ratio) showed **£5.80 including VAT** and **13 units left**, delivery extra. Its body dimensions are **69.5 × 22 × 20.7 mm excluding shaft**, mass **39.4 g**. It has no encoder. At 120 rpm the 85 mm wheel's calculated unloaded speed is 0.534 m/s; this is not a loaded operating point.

**Drawing and data limitations:** Adafruit links a [four-page gearbox datasheet](https://cdn-shop.adafruit.com/product-files/3802/C11454_datasheet_TT1___90_metal.pdf). The page-2 drawing was rendered and inspected: it labels 64.40 mm length, 22.40 mm face height, 18.60 mm gearbox thickness, 8.70 mm output projection and a 5.40 mm shaft feature with 3.70 mm flat dimension. Those figures differ from the storefront body envelope; they must not be silently combined into a frozen motor model. The storefront specifies an M2.5 × 12.5 mm shaft-retention screw. A supplier drawing matched to the delivered revision or physical measurement is needed for the final wheel adapter.

The same datasheet labels a 60 rpm no-load speed and 105 rpm rated-load speed at DC 6 V, which is internally inconsistent. Its life-test page also lacks a clear, credible continuous output-torque rating. Therefore the linked file does not justify using this motor at 0.172 N·m. This is an inexpensive bench-test option, not a validated replacement.

## Decision for the present CAD freeze

Retain the supplied FIT0493 with the independently checked right-angle transmission for the current CAD freeze. FIT0489-D becomes a plausible alternative only if approximately 0.14 m/s rated wheel speed, its larger mounting envelope and self-locking wheel behaviour are acceptable, followed by a thermal/duty check in the enclosure. Adafruit 3802 requires measured torque, current and delivered-part geometry before it can support a mechanical selection.

Before approving either replacement, obtain the rated-load duty and ambient conditions, permissible gearbox radial/axial loading, speed/torque/current curve, reverse/backdrive characteristics and the drawing for the exact delivered revision. These are missing comparison inputs; no request was sent.
