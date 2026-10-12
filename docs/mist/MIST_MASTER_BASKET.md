# MIST wheeled-quad — master basket (supersedes ../archive/hexapod/HEXAPOD_MASTER_BASKET.md)

> **Actual orders now tracked in [MIST_ACTUAL_INVENTORY.md](MIST_ACTUAL_INVENTORY.md) (2026-07-06).** The older cart/pricing tables below are planning history, not the current inventory. Current ordered state: 18 servos, FE-URT-1, Bus Servo Adapter A, ESP32 CP2102, B6Neo, 2x 3S LiPos, PDB, XT30/XT60 pigtails, XT90-S, 5264 cables, UBECs, caps, fuses, soldering tools, PETG, and TPU are ordered. Still not proven in actual orders: 12/14/16AWG silicone wire, M2/M3 machine screws/nuts/nylocs, metric hex keys, battery straps, and data cables.

> **Build order after packages arrive:** follow [MIST_BUILD_PHASES.md](MIST_BUILD_PHASES.md).

> **Pricing superseded by [MIST_BUDGET_V2.md](MIST_BUDGET_V2.md) (2026-07-03):** verified cheaper configs (~£394–480), incl. 3× 6-pack servo pricing, and the Waveshare ESP32 driver board **replaced** by Bus Servo Adapter (A) + the ESP32 devkit already in the basket. Sale-code window ends **7 July**. Architecture/wiring below still applies (the adapter takes the driver board's place in the power tree; servo bus on ESP32 Serial1 @ 1M baud).

Build: **MIST-style wheel-leg quad** — 4 legs × 3 DOF + 4 wheel servos (STS3215 wheel mode) = **16 servos + 2 spares = 18 bought**. Big top deck for phone/payload. Single raw-3S 12V rail (the 12V C018 servos are rated 6–12.6V → **no SBECs, no regulators**).

Current power-domain architecture (one raw servo rail plus regulated logic
rails; follow `MIST_BUILD_PHASES.md` for the executable harness sequence):
```
3S LiPo (XT60) → XT90-S loop key → 30A main blade fuse → optional watt-meter / smoke-stopper test lead
  → PDB (XT60 in / 8× XT30 out), all at raw pack voltage 9.9–12.6V:
      ├─ 4× leg branches, 16AWG, 15A blade fuse each, 4700µF 25V cap at each leg root
      │    (serviceable leg-root injection topology is still a continuity-verified build gate)
      ├─ 5V 5A UBEC → sensor-node ESP32 VIN/5V, ESP32-cam, and 5V-rated sensors
      │                  └─ sensor-node ESP32 regulated 3V3 → SH1106 OLED (NOT 5V)
      └─ 5.5×2.1mm barrel pigtail → Bus Servo Adapter A DC jack (6–12.6V spec — in range)
Bus Servo Adapter A is signal/common-ground only for installed leg servos; it
must not carry branch current. Do not de-pin or make an XT30→5264 injection tap
until every conductor and port is continuity-identified and the serviceable
1→4 signal/common-ground topology is approved. All grounds remain common.
```
Per-leg fuse math: 4 servos/leg × ~2.7A stall @12V ≈ 10.8A → **15A blade** (10A nuisance-blows). Main stays 30A.

## Historical AliExpress cart audit — superseded by actual orders

Do not use this section as current inventory. Use `MIST_ACTUAL_INVENTORY.md` for what has actually been ordered.

## Historical AliExpress cart — verdicts from before ordering
| Item | £ | Verdict |
|---|---|---|
| ST-3215-C018 12V 30KG **12-pack** | 182.99 | ✅ KEEP — variant text must read **12V / 30kg / ST-3215-C018** (screenshot it) |
| STS3215 12V 30KG **6-pack** | 82.79 | ✅ KEEP — but this one probably does **NOT** include the FE-URT-1 (old 7.4V 6-pack at £95.79 did). Verify; if absent add A1. Same variant-text check + screenshot |
| SKYRC B6neo 2 (DC 300W / PD 80W) | 27.49 | ⚠️ KEEP only if the store is SkyRC-branded (clone risk). PD 80W ↔ your 100W brick = fine, use the 5A e-marked cable |
| Waveshare Servo Driver with ESP32 | 21.89 | Historical only — replaced by Bus Servo Adapter A + ESP32 CP2102 in actual orders |
| XT60→8ch XT30 PDB 100A | 14.39 | ✅ KEEP — now the actual leg distributor (12V rail = servo voltage) |
| 5V 5A UBEC | 4.69 | ✅ KEEP, **change qty to 2** (one spare). Listing must say input 2–6S / DC 7–26V |
| 5-pack 30A inline fuse holders (12AWG, blade) | 4.69 | ✅ KEEP — 1× main (30A) + 4× legs (fit **15A** blades from A5) |
| Fireproof LiPo bag | 3.63 | ✅ KEEP |
| **300W 20A buck converter ×3** | 3.23 | ❌ **REMOVE** — leftover from the 7.4V plan; 12V servos run on raw 3S, nothing to regulate. (Also the part the original audit debunked as really ~120–150W) |
| 12AWG silicone wire 1m | 3.19 | ✅ KEEP (battery trunk) |
| VL53L0X ToF | 2.69 | ✅ KEEP |
| 14AWG wire 1m | 2.40 | ✅ KEEP (PDB→branch trunks) |
| **XT60→4mm banana charge lead** | 1.99 | ❌ **REMOVE** — B6neo's charge output is native XT60; the pack plugs straight in |
| 16AWG wire 1m | 1.71 | ✅ KEEP (leg branches) — consider qty 2 |
| XT60BE-M male ×2 | 1.51 | ✅ KEEP (smoke-stopper / adapter building) |
| **4700µF 16V caps** | 1.41 | ❌ **REPLACE with 25V** (A8) — 12.6V on a 16V cap = 79% of rating, too close |
| Heat-shrink kit | 1.38 | ✅ KEEP |
| Acrylic mirrors (eyes) | 0.77 | ✅ KEEP |

**Cart after fixes ≈ £360.**

## 🛒 AliExpress additions (same order = one shipping window)
| # | Item | Qty | Search term | ~£ |
|---|---|---|---|---|
| A1 | FE-URT-1 USB servo adapter (**only if 6-pack lacks it**) | 1 | `FE-URT-1 Feetech servo driver USB` | 7–10 |
| A2 | XT30 pigtail pairs 16AWG | 10 pr | `XT30 pigtail 16AWG male female pair` | 3–6 |
| A3 | 5.5×2.1mm male DC barrel pigtail 18AWG | 2 | `5.5x2.1mm male DC pigtail cable` | 1–2 |
| A4 | XT90-S anti-spark loop key **with XT60 pigtails** (or XT60↔XT90 adapter pair) | 1 | `XT90-S anti spark loop key XT60` | 4–6 |
| A5 | Blade fuse assortment — must include ≥6× **15A** + spare 30A | 1 | `blade fuse assortment 5A 10A 15A 20A 30A` | 3–5 |
| A6 | LiPo low-voltage alarm 1–8S, settable, per-cell display | 1 | `lipo voltage alarm 1-8S adjustable buzzer` | 2–3 |
| A7 | 5264 3-pin servo cables: 4× 30cm + 4× 20cm + 4 spares | 12 | `5264 3 pin servo cable double head Feetech 30cm` | 5–7 |
| A8 | 4700µF **25V** electrolytic caps | 8 | `4700uF 25V electrolytic capacitor` | 3–4 |
| A9 | Solder 63/37 0.8mm 100g + rosin flux + desolder wick | 1 ea | `63/37 solder 0.8mm 100g` etc. | 5–8 |
| A10 | Self-adjusting wire strippers + flush cutters | 1 ea | `self adjusting wire stripper` / `flush cutter` | 5–10 |
| A11 | SN-28B crimp tool | 1 | `iWiss SN-28B crimping tool` | 6–9 |
| A12 | Dupont/JST-XH connector kit (sensor wiring only — does NOT fit the servo bus) | 1 | `dupont JST XH connector kit` | 5–8 |
| A13 | Spare XT60 M/F pigtail pairs 14AWG | 3 pr | `XT60 pigtail 14AWG pair` | 3–6 |
| A14 | 20mm hook-loop battery/phone straps | 3 | `lipo battery strap 20mm 250mm` | 3–5 |
| A15 | USB-C **data** cable + micro-USB **data** cable | 1 ea | (match FE-URT-1/board port — check photos) | 2–3 |
| A16 | M2 screw/nut kit + M3 screw kit | 1 ea | `M2 screw nut assortment` / `M3 screw kit` | 5–8 |
| A17 | Digital calipers 150mm (CAD is measured, not downloaded) | 1 | `digital caliper 150mm` | 6–10 |
| A18 | Precision hex driver set 0.9–3mm | 1 | `precision hex screwdriver set metric` | 6–12 |
| A19 | Inline watt-meter XT60 130A | 1 | `RC watt meter 130A XT60` | 8–12 |
| A20 | ESP32 dev board CH340 (sensor/eyes node — the Waveshare board has zero spare GPIO) | 1 | `ESP32 DevKitC WROOM-32 CH340` | 4–8 |
| A21 | Half breadboard + M-F jumper wires (sensor-node bench) | 1 | `breadboard 400 jumper wire kit` | 3–4 |
| A22 | Threadlocker blue + zip ties + braided sleeve | 1 ea | `threadlocker 243` etc. | 5–8 |
| A23 | Safety glasses | 1 | `safety glasses clear` | 2–3 |
| A24 | *(optional)* 8ch 24MHz logic analyzer (bus debug) | 1 | `24MHz 8 channel logic analyzer` | 8 |
| A25 | *(optional)* anti-static wrist strap | 1 | `anti static wrist strap` | 2 |

**Additions ≈ £100–140 (core) / +£10 optional.**

## 🇬🇧 UK / Amazon
| Item | ~£ | Note |
|---|---|---|
| Overlander 3S 3350mAh 35C, XT60 (overlander.co.uk) | 35 | Default. Wheeler bonus: a ~5200mAh (~380g) pack later = multi-hour rolling; weight only hurts leg maneuvers |
| PETG 1kg ×2 (ELEGOO/SUNLU, Amazon) | 26 | Frame + wheel hubs |
| TPU 95A 1kg (Amazon) | 18–22 | **Tires** + foot pads — required for MIST, not deferrable |
| H4 55/60W bulbs ×2 + holder (Amazon/Halfords) | 6–8 | Smoke stopper (limits any short to ~5A vs the pack's ~117A) |
| Temp-controlled soldering iron (Pinecil ~£30 AliExpress or T12 station Amazon) | 30–40 | |
| *(skipped)* bench PSU £35–45 | 0 | Smoke stopper + 5A-fuse trick + storage-charged pack cover commissioning |
| *(deferred)* M3 heat-set inserts | 0 | Self-tappers into PETG bosses first |

## Totals
| Block | £ |
|---|---|
| AliExpress cart after fixes | ~360 |
| AliExpress additions | ~100–140 |
| UK/Amazon | ~120–135 |
| **Everything (excl. printer)** | **~£580–635** |
| Ender 3 V3 SE | +149 |

## What carries over from ../archive/hexapod/HEXAPOD_PREFLIGHT.md
- All of Part 3's test protocol (T0 unbox variant check within the 15-day dispute window; T6 ID/register session — 12V variant reads register 14 = 140, that's CORRECT for this variant, don't "fix" it; T8 smoke-stopper first power-up; T9 single-leg testbed **before printing legs 2–4**; wheel-mode spin test added: command wheel servo in speed mode, verify smooth continuous rotation + current <1A unloaded).
- Historical de-pin proposal: four board→coxa leads. Do not execute it until
  every pin is continuity-identified against authoritative pinouts and the
  unresolved serviceable 1→4 signal/common-ground harness is approved. The
  adapter must not become the servo-current path.
- SBEC sections (T3/T4) are obsolete — skip them.
- No open-source STS3215 wheel-leg design exists: CAD from your own caliper measurements (servos are dual-axis — use the rear stub as the joint idler). Print 1 leg + 1 wheel → T9 → then the rest.
- The earlier “wheel speed commands = skid steer” assumption is not yet valid.
  Fixed radial wheel headings at ±25°/±109° scrub even in nominal translation.
  Close the wheel-architecture gate (explicit low-speed scrub, parallel or
  adjustable pods, omni contact, or steering) before defining v1 drive mapping.
