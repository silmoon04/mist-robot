# Hexapod — final basket list (3S→7.4V path, full build)

Decisions locked: **servo rail = 3S LiPo → regulated to a flat 7.4V**; **user owns none of the tools**; **scope = everything**. This is the authoritative buy-list to get the whole robot. ✅ = already in the AliExpress basket. 🛒 = to add. ⚠️ = better bought in the UK / needs a decision.

## A. Servos & control (the brain)
| Item | Status | Note / search term | ~£ |
|---|---|---|---|
| 18× STS3215 19kg 7.4V (12-pack + 6-pack) | ✅ added | stemedu; confirm 1:345/C001 on both | ~247–259 |
| FE-URT-1 USB programmer | ✅ (bundled w/ 6-pack) | sets servo IDs from a PC | 0 |
| **Waveshare "Servo Driver with ESP32"** | 🛒 | runtime bus-driver + brain; `Waveshare ESP32 servo driver ST3215` | 16–22 |
| Spare 5264 3-pin bus cables (assorted) | 🛒 | `STS3215 5264 servo cable 3pin 100 200 300mm` | 5–10 |
| 1× spare STS3215 (insurance) | 🛒 | max-1 deals limit this; `Feetech STS3215 7.4V 19kg` | 11–16 |

## B. Power (3S → 7.4V rail)
| Item | Status | Note / search term | ~£ |
|---|---|---|---|
| **3S 5000mAh LiPo, XT60** | 🛒 ⚠️ | ⚠️ batteries ship slow/expensive from China — consider a UK pack. `3S 11.1V 5000mAh lipo XT60` | 22–35 |
| **Real ≥40A buck → 7.4V** (servo rail) | 🛒 | the cheap 20A buck is ~120W; need ≥40A & bench-test. `DC DC buck 40A 600W adjustable` | 8–18 |
| 5V 5A UBEC (logic rail) | 🛒 | `5V 5A UBEC BEC` | 3–8 |
| XT60 power distribution board | 🛒 | `XT60 power distribution board PDB` | 4–8 |
| XT90-S anti-spark loop key | 🛒 | main kill + inrush; `XT90S anti spark loop key` | 3–8 |
| Inline watt-meter (130A, XT60) | 🛒 | measure real draw; `RC watt meter 150A XT60` | 6–12 |
| Power injection Y-splitters | 🛒 | per-leg V+; `XT60 / servo power Y splitter` (one is FREE-with-purchase) | 0–4 |
| Main + per-leg blade-fuse holders (16AWG) | 🛒 | `inline blade fuse holder 16awg` | 4–9 |
| Blade-fuse assortment (5–30A) | 🛒 | `mini blade fuse assortment` | 2–5 |
| 2S/3S LiPo low-voltage alarm | 🛒 | brownout backstop; `3S lipo low voltage alarm buzzer` | 1–3 |
| Charger DC source: SKYRC PSA100 100W *or* your USB-C PD charger | 🛒 ⚠️ | B6neo needs DC/PD in; `SKYRC PSA100` (or use an owned 100W PD charger = £0) | 0–24 |
| 4700µF caps · silicone wire 14/16/12AWG · LiPo bag · XT60 charge lead · B6neo 2 | ✅ in basket | keep | — |

## C. Connect / assemble
| Item | Status | Search term | ~£ |
|---|---|---|---|
| Ratcheting crimp tool (SN-2549) | 🛒 | `SN-2549 crimp tool dupont JST` | 8–17 |
| Dupont/JST connector + pin kit | 🛒 | `dupont JST connector kit crimp pins` | 4–10 |
| M2×6 screws ×100 (servo bodies) | 🛒 | `M2 x 6 screw 100pcs` | 2–4 |
| M3 screws + nyloc + washers kit | 🛒 | `M3 screw nut washer assortment` | 6–14 |
| M3 heat-set inserts ×100 + iron tip | 🛒 | `M3 heat set insert 100pcs` | 5–12 |
| Blue threadlocker (243) | 🛒 | `blue threadlocker 243` | 2–6 |
| Heat-shrink kit | ✅/🛒 | had one in original cart; else `heat shrink assortment` | 0–2 |

## D. Tools (you own none)
| Item | Status | Note | ~£ |
|---|---|---|---|
| Temp-controlled soldering iron (T12) | 🛒 ⚠️ | `T12 soldering iron kit` (UK option fine) | 20–35 |
| Digital calipers 150mm | 🛒 | `digital caliper 150mm` | 8–15 |
| Precision hex driver set (1.5/2/2.5/3mm) | 🛒 | `precision hex screwdriver set metric` | 8–18 |

## E. Sensors / additions
| Item | Status | Search term | ~£ |
|---|---|---|---|
| MPU6050 IMU (fast balance loop) | 🛒 | `MPU6050 GY-521` (≈£1) | 1–5 |
| VL53L0X ToF | 🛒 | `VL53L0X` | 3–8 |
| Phone clamp + anti-vibration pads | 🛒 | `phone holder clamp mount` | 4–10 |

## F. Mechanical (everything)
| Item | Status | Note / search term | ~£ |
|---|---|---|---|
| PETG filament (structural) | 🛒 | `PETG filament 1.75mm 1kg` | 10–16 |
| TPU 95A filament (feet) | 🛒 | `TPU 95A filament 1.75mm` | 12–18 |
| PET braided sleeving 4/6/8mm | 🛒 | `PET braided cable sleeve` | 3–8 |
| Nylon zip ties (assorted) | 🛒 | `nylon cable ties assorted` | 2–5 |
| Leg-pivot bearings | ⚠️ later | size to CAD first — don't buy blind | 4–8 |

## Still WRONG in basket (recommend remove)
2× PCA9685 · 250A bus bar · mirror stickers · (any leftover 3S-2200mAh / MG996R / 25T horns / 2nd charger / PWM extension leads).

**Rough added cost (everything, AliExpress-ish): ~£160–250** on top of the ~£250 servos. Biggest UK-better items: the **3S LiPo** and **soldering iron**.
