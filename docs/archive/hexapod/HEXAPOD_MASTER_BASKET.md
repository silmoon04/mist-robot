# Hexapod — master basket & build list (live)

Single source of truth for everything. Status: ✅ in AliExpress cart (ticked) · 🛒 to add (AliExpress one‑click) · 🇬🇧 UK/specialist · 🔧 already own · ⚠️ care needed.

## ✅ In the AliExpress cart now (all ticked)
| Item | £ |
|---|---|
| 12‑pack STS3215 servos | 162.93 |
| 6‑pack STS3215 + FE‑URT‑1 programmer | 95.79 |
| Waveshare Servo Driver with ESP32 (the brain) | 21.99 |
| 5V 5A UBEC ×2 (logic rail + spare) | 4.59 |
| VL53L0X ToF sensor | 2.69 |
| XT60 → 8‑channel XT30 PDB (100A) | 14.39 |
| SKYRC B6neo 2 charger | 26.99 |
| XT60→4mm charge lead (spare) | 2.00 |
| Fireproof LiPo bag | 3.64 |
| 4700µF 16V caps | 1.42 |
| Silicone wire 14/16/12 AWG | 7.33 |
| 30A inline fuse holder + blade fuses | 4.69 |
| XT60BE‑M connector | 1.51 |
| Heat‑shrink kit · mirrors (eyes) | 4.18 |
**Cart subtotal ≈ £374**

## 🛒 To add on AliExpress (one‑click each — cheapest here since it's one order)
| Item | Search | ~£ |
|---|---|---|
| 5264 3‑pin bus cables (daisy‑chain spares) | `5264 3pin servo cable double head` | 5–8 |
| Per‑leg blade‑fuse holders ×6 | `inline blade fuse holder 16awg` | 4–7 |
| LiPo low‑voltage alarm | `1-8S lipo low voltage alarm buzzer` | 1–2 |
| XT60 Y‑splitters | `XT60 parallel Y splitter` | FREE/3 |
| Ratcheting crimp tool (SN‑28B) | `SN-28B crimping tool` | 8–14 |
| Dupont/JST connector + pin kit | `dupont JST XH connector kit` | 6–12 |
| M2×6 screws + M3 screw/nyloc/washer kit | `M2x6 screw` / `M3 screw nut washer kit` | 8–16 |
| M3 heat‑set inserts + iron tip | `M3 heat set insert soldering tip` | 5–12 |
| Digital calipers 150mm | `digital caliper 150mm` | 6–10 |
| Precision hex driver set | `precision hex screwdriver set metric` | 6–12 |
| Inline watt‑meter (130A, XT60) | `RC watt meter 150A XT60` | 6–9 |
| Threadlocker 243 · PET sleeving · zip ties | (search each) | 8–12 |
| **⚠️ 2× 20A SBEC → 7.4V servo rail** | `20A SBEC 7.4V switching` | ~28 |
| *(optional)* half breadboard for bench tests | `breadboard 400 tie` | 2 |

## 🇬🇧 UK / specialist (not AliExpress)
| Item | Where | £ |
|---|---|---|
| **3S 3350mAh LiPo, XT60** (lithium won't ship from AliExpress) | Overlander | 35 |
| **3D printer — Creality Ender 3 V3 SE** | 123‑3D | 149 |
| **PETG 1kg + TPU 95A 1kg** | ELEGOO (Amazon) / SUNLU | ~13 + ~18 |
| XT90‑S anti‑spark loop key | HobbyRC | ~5 |
| Soldering iron (temp‑controlled) — *or cheaper AliExpress T12* | Kunkune | ~39 |

## 🔧 Already own — do NOT buy
18× STS3215 are being bought above · **MPU6050** (removed the duplicate) · **Mi 9 SE phone** (accelerometer, GPS, gyro, screen, camera — high‑level sensing + teleop) · **ESP32‑WROVER camera** (forward FPV) · **multimeter** · **100W + 120W USB‑C PD chargers** (these power the B6neo — no PSU needed).

## ⚠️ What could go wrong / what to add or test (cheap)
1. **The ≥40A 7.4V regulator is the #1 risk.** The 2× 20A SBEC split‑bus (9 servos each) must be **bench‑tested at 40A** before it ever drives legs (fan + heatsink). This is the part most likely to fail.
2. **Never feed servos raw 3S (12.6V) or 2S (8.4V)** — regulate to a flat 7.4V. At 6V they lose ~19% torque (see the explorer).
3. **ID the servos 1–18 one at a time** with the FE‑URT‑1 before daisy‑chaining, or the bus collides.
4. **Per‑leg power injection + branch fuses + common ground** — don't run 45A through one daisy‑chain end or the driver board.
5. **Stay in the torque envelope:** ≤~2.4 kg all‑up, ≤14 cm foot reach, ~≤12 cm tibia (the explorer shows the safety factor live).
6. **Measure the chassis before printing** — body's longest flat side ≤~200 mm to fit the Ender bed, or split it.
7. **Cheap test gear worth having:** a **CC‑CV bench PSU (~£25–45)** for a safe first power‑up (limits current so a wiring fault doesn't cook parts) + the inline watt‑meter above + **Feetech FD software (free)** via the FE‑URT‑1 to test/ID servos. A **£8 logic analyzer** helps debug the serial bus if needed.
