# MIST actual inventory - orders placed 2026-07-06

This is the current source of truth for what has actually been ordered. It supersedes the older "current cart" tables in `MIST_MASTER_BASKET.md` and the shopping notes in `MIST_CART_RUN_2026-07-03.md`.

Build/run order after parts arrive: `MIST_BUILD_PHASES.md`. Visual bench companion: `MIST_VISUAL_BUILD_GUIDE.md`.

Dimensions, weights, mounted-vs-bench quantities, and CAD placeholder sizes: `MIST_MATERIAL_DIMENSIONS_MASS.md`.

## Build target now covered

- Full MIST wheeled-quad target: 4 legs x 3 joints + 4 wheel servos = 16 installed servos.
- Spares target: 2 spare servos.
- Servo order placed: 3x 6-pack STS3215 12V 30kg = 18 servos total.
- Power architecture remains raw 3S LiPo for servos, 5V UBEC for logic, Bus Servo Adapter A + ESP32 CP2102 for control.

## Amazon orders

| Item | Qty | Order evidence | Status / notes |
|---|---:|---|---|
| Loctite Threadlocker, 1x 5g | 1 | Amazon order #206-4231619-2061956, order placed 2026-07-06, order total GBP 13.74 with smoke stopper | Good. Use on metal screws after fit is proven. |
| VOANZO XT60 XT30 smoke stopper / short tester | 1 | Amazon order #206-4231619-2061956, arriving Wednesday 2026-07-08 per screenshot | Good. Use for every first power-up after wiring changes. |
| SKYRC B6Neo LiPo charger, 1S-6S, 200W DC / 80W PD | 1 | Amazon order #206-1954387-1528338, GBP 37.52, arriving 2026-07-15 to 2026-07-17 | Good. Use Anker 317 100W PD charger and 5A e-marked cable. Still required; a laptop charger alone cannot balance-charge LiPos. |
| JAYO TPU 95A black filament, 1.75mm, 0.5kg | 1 | Amazon order #206-1179200-7821101, order total GBP 64.26 with PETG/iron/battery, arriving 2026-07-07 | Good to start tires/feet. 0.5kg may be tight after failed tire iterations. |
| Creality PETG white filament, 1.75mm, 1kg | 1 | Amazon order #206-1179200-7821101 | Good for first frame, legs, hubs, brackets. |
| HANDSKIT 90W soldering iron kit with LCD, tips, pump, solder, stand, tweezers | 1 | Amazon order #206-1179200-7821101 | Good starter kit. Still prefer the separate 63/37 solder for first power joints. |
| HOOVO 3S LiPo battery 2200mAh 11.1V 50C XT60, 2-pack | 1 pack / 2 batteries | Amazon order #206-1179200-7821101 | Good. Check per-cell voltage on arrival, storage-charge before long storage, charge in LiPo bag. |

## AliExpress orders

| Item | Ordered qty | Counts as | Status / notes |
|---|---:|---|---|
| 6PCS Feetech STS3215 12V 30KG serial bus servos | 3 packs | 18 servos | Correct for full build: 16 installed + 2 spare. On arrival verify 12V / 30kg / ST-3215-C018 label/variant. |
| Feetech FE-URT-1 USB servo adapter | 1 | Servo setup/test adapter | Correct. Use for ID assignment, register reads, sweep tests, and dispute-window verification. |
| Bus Servo Adapter A | 1 | ESP32-to-STS bus interface | Correct. This replaces the older Waveshare ESP32 servo-driver-board plan. |
| ESP32 DevKitC / WROOM-32 CP2102 Type-C | 1 | Main robot/sensor controller | Correct. Keep separate from the ESP32 camera board. |
| VL53L0X ToF range sensor | 1 | Front/proximity sensor | Good optional sensor. |
| FPV RC UBEC, selected option `2PCS 5A UBEC`, order qty x2 | Likely 4 UBEC modules | 5V logic power + spares | More than enough if the option/quantity ships as expected. Verify each output is 5V before connecting ESP32. |
| XT60 to 8-channel XT30 PDB, 100A max | 1 | Main raw-3S power distributor | Good. Check polarity before plugging anything in. |
| XT30 male/female 16AWG pigtail set, 5 pairs | 2 sets | 10 XT30 pairs | Correct for leg branches and spares. |
| XT60 male/female 14AWG pigtail set, 5 male + 5 female | 1 set | 5 XT60 pairs | Good for adapters/spares. Main high-current trunk should still use 12AWG/10AWG where practical. |
| XT90-S anti-spark female-to-XT90 male extension cable, 10AWG listing | 1 | Main physical disconnect / anti-spark loop | Good if the shipped cable is actually 10AWG and not an overly long option. Keep the installed harness short. |
| 5264-3PIN servo extension leads for ST/SC/CF servos, 6pcs listing | 3 packs | Likely 18 STS3215 bus cables | Correct quantity if 3 packs x 6 cables arrive. Verify plug type is 5264/JST-GH-style Feetech STS bus, not generic PWM servo. |
| DC 5.5x2.1mm barrel pigtail, male and female, 5 pcs | 1 set | Adapter/bench power pigtails | Good. Use for Bus Servo Adapter A DC input if needed. |
| 4700uF 25V electrolytic capacitors, 5pcs | 2 packs | 10 caps | Correct. Use near leg roots; observe polarity. |
| 1S-8S LiPo low-voltage alarm / battery tester | 1 | Running battery alarm | Good. Set alarm conservatively and do not run packs flat. |
| 5-pack waterproof inline fuse holders, 12AWG with 30A fuses | 1 pack | Main/branch fuse holders | Good if shipped as 12AWG. Use 30A main fuse and 15A branch fuses. |
| Standard car blade fuse assortment, 50pc set | 1 set | Spare 15A/30A blade fuses | Good if it is standard blade size matching the holders. Verify not mini-only. |
| Fireproof LiPo guard bag, 185x75x60mm | 1 | LiPo charge/storage safety | Good for one 2200mAh pack at a time. |
| Black heat-shrink tube kit, 127 pcs | 1 | Wire insulation | Good. |
| Acrylic mirror stickers, silver triangle 5cm, 50pcs | 1 | Eye/face cosmetic parts | Optional, good. |
| 63/37 rosin solder wire Sn63Pb37, 0.8mm, 50g | 1 | Primary solder | Good. This is the useful solder for beginner wire/connectors. |
| Extra rosin-core solder wire, 0.8mm, 20g | 1 | Backup solder | Fine. Redundant but useful. |
| Flux-coated desoldering braid, 3mm x 1.5m | 1 | Rework | Good. |
| HAND tools bundle: 25-in-1 screwdriver bits | 1 | General tools | Useful, but does not prove metric hex keys are covered. |
| Wire stripper/cutter, 10-22AWG | 1 | Wiring tool | Good. |
| Electronic digital caliper, 150mm | 1 | CAD/measurement | Good. |
| ANENG SZ308 multimeter | 1 | Electrical checks | Good enough for polarity, voltage, continuity, UBEC checks. |
| Safety goggles, black | 1 | Eye protection | Use if lenses are clear enough to solder/inspect safely. If too dark, get clear safety glasses later. |
| A4 PVC cutting mat | 1 | Work surface | Useful for cutting, not a hot soldering surface. |
| Kitchen scale, 10kg / 1g | 1 | Robot/pack weighing | Useful. |
| Precision pocket scale, 1000g / 0.1g | 1 | Small part weighing | Useful but not critical. |
| Stainless flat washer assortment, M2-M10, 180pcs | 1 | Washers | Useful. Does not replace screws/nuts. |
| 240-piece self-tapping wood screw set, M2 flat metal screws | 1 | Prototype screws | Partial mechanical coverage only. Not a replacement for M2/M3 machine screws and M3 nyloc nuts. |
| Generic 25pcs RC servo extension leads, 3-pin male-to-female | 1 set | Sensor/bench spares only | Do not count for STS3215 bus wiring. These are generic PWM/Futaba-style leads. |
| Telescopic magnetic pickup tool | 1 | General tool | Useful. |
| Cable organizer tie roll, 5m black | 1 | Cable retention | Useful. |
| Ultra-strong double-sided tape, 5m x 20mm x 1mm | 1 | Temporary mounting | Useful for prototypes only; do not rely on it for battery retention. |
| 18650 charger, 1 slot | 1 | Extra / not part of MIST | Not needed for the 3S LiPo architecture. |
| Non-contact AC electrician test screwdriver | 1 | Extra / not part of MIST | Not useful for low-voltage DC robot wiring. |
| Unknown SKU `JP-1086 hei` | 1 | Unknown | Not counted until identified. |

## Already owned at home (not in the orders above)

| Item | Status / notes |
|---|---|
| Elegoo Neptune 4 Pro 3D printer | Owned, at home. Direct-drive extruder (TPU-capable), Klipper, ~300C hotend, ~225x225x265mm bed. Covers all MIST printing. |
| PLA filament, ~3kg | Prototyping/fit-coupon material until PETG/TPU arrive. Do not use PLA for final servo pockets or structural parts: it creeps under sustained load and softens near servo operating temperatures. |
| Anker 317 100W USB-C PD charger + 5A e-marked cable | Powers the B6Neo. |

## Coverage summary

| Need | Status | Notes |
|---|---|---|
| 18 STS3215 12V servos | Covered | 3x 6-pack ordered. |
| Servo configuration/test adapter | Covered | FE-URT-1 ordered. |
| ESP32 bus control | Covered | Bus Servo Adapter A + ESP32 CP2102 ordered. |
| 3S battery + real balance charger | Covered | HOOVO 3S 2-pack + SKYRC B6Neo ordered. |
| USB-C charger for B6Neo | Covered if existing Anker 317 and its 5A e-marked cable are used | No extra USB-C charger needed. |
| Smoke stopper | Covered | VOANZO XT60/XT30 unit ordered. |
| PDB and connector pigtails | Covered | XT60 PDB, XT30 pairs, XT60 pairs, XT90-S ordered. |
| Logic 5V power | Covered | 5A UBEC modules ordered; verify 5V output before use. |
| Branch capacitors | Covered | 10x 4700uF 25V ordered. |
| Fuse holders and fuses | Covered with verification | Need matching standard blade size; use 30A main and 15A per-leg branches. |
| STS3215 servo-bus cables | Covered with verification | 3x 6pcs 5264 cable packs should be 18 cables. Verify connector type/length. |
| 3D printer | Covered | Elegoo Neptune 4 Pro already owned (see "Already owned at home"). Commission it with PLA before PETG arrives. |
| PETG/TPU printing material | Mostly covered | PETG 1kg good. TPU 0.5kg is enough to start, but another TPU spool may be needed after tire iterations. ~3kg PLA on hand for prototypes/coupons meanwhile. |
| Soldering/rework/tools | Covered | HANDSKIT iron, 63/37 solder, spare solder, wick, wire stripper, multimeter, goggles ordered. |
| Silicone power wire | Not shown in actual orders | Still missing unless ordered separately: 12AWG, 14AWG, and 16AWG red/black silicone wire for trunk/branches. Pigtails alone are not enough for a clean harness. |
| M2/M3 mechanical fasteners | Partially covered | Washers and self-tappers are ordered. Still not proven: M2 machine screws, M3 machine screws, M3 nyloc nuts. |
| Metric hex keys/drivers | Not proven | 25-in-1 bit set may not include useful 1.5/2/2.5/3mm hex bits. Verify before assembly. |
| Battery/phone straps | Not shown in actual orders | Needed unless ordered separately. Tape is not enough for LiPo retention. |
| USB data cables | Not proven | Need data-capable USB-C for ESP32/B6Neo and the correct cable for FE-URT-1. Charge-only cables cause debugging pain. |
| Inline watt-meter | Not ordered / optional | Useful for current logging, but not a build blocker if using smoke stopper, fuses, multimeter checks, and B6Neo charge data. |

## Arrival checks before building

1. Photograph each STS3215 listing/label/packaging if it shows 12V / 30kg / ST-3215-C018.
2. Use FE-URT-1 to read IDs/registers and sweep each servo during the dispute/return window.
3. Check each LiPo cell voltage before first charge; storage-charge packs if not building immediately.
4. Verify UBEC output with the multimeter before connecting ESP32 or sensors.
5. Check PDB polarity, XT30/XT60 gender, and fuse continuity before connecting the battery.
6. Use the smoke stopper for first power-up of every new harness stage.
7. Confirm the XT90-S cable gauge and length before making it the main disconnect.
8. Do not start final harness wiring until silicone wire and M2/M3 fasteners are confirmed.
