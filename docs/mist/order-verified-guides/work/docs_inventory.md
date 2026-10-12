# MIST guide-derived parts inventory

Audit date: 2026-07-30

Purpose: provide the exact parts/groups that the order-image audit and replacement
labelled pictures must represent. This report separates:

- what the current build guides require;
- what the older order ledger says was ordered;
- what the user has now physically confirmed;
- what is still missing, unusable, or visually unverified.

It does **not** prove the current AliExpress order contents. The order page and the
received hardware still need to be matched to this list.

## 1. Source hierarchy and conflicts

1. `MIST Build Guide (standalone).html` is explicitly marked **ARCHIVED
   SNAPSHOT**. Its banner says not to use its dimensions or old floor-test
   sequence.
2. `MIST_VISUAL_BUILD_GUIDE.html` is the current bench-facing HTML authority.
   Its text says the generated panels are orientation aids and the written
   callouts are the source of truth.
3. That HTML points to `MIST_BUILD_PHASES.md` for the exact phase order and
   parts needed at each gate.
4. `MIST_ACTUAL_INVENTORY.md` is the previous record of what was ordered on
   2026-07-06. It is useful order evidence but is not proof that an item arrived
   or that the seller shipped the selected variant.
5. `MIST_FUSION_360_GUIDE.html` supplies provisional physical envelopes for
   visually faithful layout. It repeatedly says to replace them with measurements
   of the received parts.

Consequences for regenerated pictures:

- Do not copy the old generated guide art as product-identification evidence.
- Product appearance should come from the current AliExpress order option image
  and the user's physical photo/video, with the guide name/spec used as a label.
- Do not invent the unresolved final four-leg signal/power tap harness.
- Treat the dimensions below as scale references, not proof of an exact casing,
  connector, wire colour, or board revision.

## 2. Status vocabulary

| Status | Meaning |
|---|---|
| **Confirmed present** | The user explicitly said it is physically present. |
| **Present, verify** | The user has the general item, but exact count/spec/function still needs checking. |
| **Order-ledger only** | Listed in the 2026-07-06 order record; not yet reconfirmed physically in this conversation. |
| **Missing / blocked** | The user explicitly lacks it, cannot find it, or the item is unusable. |
| **Optional / later** | Useful, but not a blocker for the current commissioning step. |
| **Not required** | Absence does not block the documented workflow. |

## 3. Current gap summary

| Item | Guide requirement | Current status | Exact next check |
|---|---|---|---|
| C018 servos | 18 total: 16 installed + 2 spares | **Present, verify** | Count 18 and confirm every label/option is `12V / 30kg / ST-3215-C018` or an explicitly equivalent 12 V 30 kg variant. |
| HOOVO LiPos | 2 packs, one connected/mounted at a time | **Confirmed present** | Two packs are present; inspect each pack and record all three cell voltages. |
| B6Neo | 1 | **Confirmed present** | In use charging a HOOVO pack. Preserve balance-charge/storage-charge workflow. |
| FE-URT-1 | 1 | **Confirmed present** | Confirm its USB connector and the servo-side power/5264 path. |
| Feetech 5264 3-pin leads | 16 for the robot plus 2 spare/bench is the ordered target | **Missing / blocked** | User cannot find them. Locate the expected `3 packs × 6 pcs`, then physically test a plug in a C018 port before counting them. |
| Smoke stopper | 1 | **Confirmed present** | Static first-power/ID-scan use only; bypass it before motion/load. |
| Silicone wire | 12, 14 and 16 AWG red/black in adequate lengths | **Present, verify** | Check the reel/bag labels and colours: 12 AWG 1 m pair, 14 AWG 1 m pair, 16 AWG 1–2 m pair minimum. |
| M2 machine screws | M2×6 and M2×8, about 100 total useful target | **Present, verify** | User has M2×4/5/6/8/10/12/16/20; verify these are machine screws rather than only self-tappers, and count enough ×6/×8. |
| M3 machine hardware | M3×6/8/10/12/16, 100–150 mixed; 50–100 M3 nyloc nuts; M3 washers | **Missing / blocked for final mechanics** | User has no M3. Buy/locate before final chassis/leg assembly. |
| M4 hardware | No current guide requirement | **Not required** | Do not buy merely because it is absent; wait for a measured CAD/interface requirement. |
| USB cables | Known data-capable cable for ESP32 and whatever FE-URT-1 uses | **Present, verify** | User has USB cables; prove Windows data/COM operation. A charging cable is not enough. |
| Multimeter | Working DC voltage + continuity meter | **Missing / blocked while unpowered** | Meter body is present but has no battery. Install the battery specified by its label/manual and prove continuity and DC voltage. The illuminated test screwdriver cannot substitute. |
| Breadboard | Not listed as a build blocker | **Not required** | Servo intake can be done without one. ESP32 integration may use secure direct jumpers/connectors. |
| Battery/phone straps | 20 mm hook-and-loop, 3–4 pieces | **Order status unconfirmed** | Locate and measure. Tape is not acceptable LiPo retention. |

The immediate blockers to a documented one-servo FE-URT test are the missing/unverified
5264 lead, the unusable multimeter, and confirmation of a protected external 3S
power path with the correct fuse. The lack of a breadboard is not a blocker.

## 4. Group A — servo stock and intake bench

### Required stock

| Item | Target quantity | Exact specification / role | Prior order record |
|---|---:|---|---|
| Feetech STS3215 serial-bus servo | 18 | `12V / 30kg / ST-3215-C018`; 16 installed and 2 spares | Three 6-piece packs |
| FE-URT-1 USB servo adapter | 1 | Bench-only ID/register/sweep adapter | 1 |
| Feetech/ST/SC/CF 5264 3-pin lead | 1 for the active intake setup; 18 total stock target | Must physically fit the C018 serial-bus port | Three 6-piece packs, expected 18 |
| PC USB data cable | 1 | Correct plug for FE-URT-1; must carry data | User says USB cables are present, function unproven |
| HOOVO 3S pack | 1 connected | Storage voltage preferred for intake; external servo power | 2 total packs |
| Low-current single-servo fuse | 1 | 5 A or 7.5 A if available | Fuse assortment expected; value not physically confirmed |
| Smoke stopper | 1 | Static first power / ID scan only | Present |
| Working multimeter | 1 | DC voltage, polarity and continuity | Meter body present but unusable without battery |
| Labels/register log | 18 labels | IDs and role recorded immediately | Consumable |

### Correct one-servo arrangement

```text
Windows PC --USB data--> FE-URT-1 --5264 bus--> ONE C018 servo
                                      ^
                                      |
one protected 3S source --5/7.5 A fuse + smoke stopper--> servo V+/GND
```

Rules:

- Connect exactly one factory-default servo at a time.
- USB powers adapter logic; it does not power the servo motor.
- Fit no horn during first intake sweeps.
- Read/log default registers before changing ID or mode.
- Do not connect the C018 directly to ESP32 pins.
- Do not attempt this while the multimeter is unusable.
- The four wheel-role servos alone get continuous/wheel mode.

### ID/role map

| Corner | IDs | Roles |
|---|---|---|
| Front-left (FL) | 1–4 | coxa, femur, tibia, wheel |
| Front-right (FR) | 5–8 | coxa, femur, tibia, wheel |
| Rear-right (RR) | 9–12 | coxa, femur, tibia, wheel |
| Rear-left (RL) | 13–16 | coxa, femur, tibia, wheel |
| Spares | 17–18 | labelled, tested spares |

The Fusion guide still treats rear-ID agreement as a release gate. Regenerated
images must print `RR 9–12` and `RL 13–16` explicitly rather than assuming an
array/corner order.

## 5. Group B — LiPo charging and storage

| Item | Required / ordered quantity | Exact specification | Mounted/connected at once |
|---|---:|---|---:|
| HOOVO LiPo | 2 | 3S, 2200 mAh, 11.1 V nominal, 12.6 V full, 50 C listing, XT60 | 1 |
| SKYRC B6Neo | 1 | LiPo balance/storage charger | Bench only |
| Anker 317 supply | 1 | 100 W USB-C PD | Bench only |
| USB-C input cable | 1 | 5 A e-marked | Bench only |
| LiPo guard bag | 1 | Ordered envelope 185 × 75 × 60 mm | One pack comfortably |
| LiPo alarm/tester | 1 | Adjustable 1S–8S | Remove after use; not left attached in storage |
| Working multimeter | 1 | Main-lead polarity/voltage sanity | Bench only |

First-charge settings in the guide:

- mode: LiPo;
- cell count: 3S;
- full target: 12.6 V;
- balance charge;
- first-charge current: 2.2 A maximum;
- never use LiHV or NiMH mode.

The two batteries should appear together in an inventory picture, but any
connection diagram must show only one pack connected to the charger or robot.

## 6. Group C — raw-3S main trunk

### Required installed path

```text
one HOOVO 3S XT60 pack
  -> XT90-S anti-spark disconnect/key
  -> 30 A main standard-blade fuse in inline holder
  -> XT60-to-8×XT30 PDB
```

For a static first-power check only, the smoke stopper is temporarily inserted
in the protected trunk path before the PDB/load. It is not a permanent robot
component and is bypassed before motion.

| Item | Build quantity | Ordered stock / spec | Current physical status |
|---|---:|---|---|
| HOOVO 3S XT60 pack | 1 mounted | 2 total | Present |
| XT90-S anti-spark extension/disconnect | 1 | 10 AWG listing; short/reachable preferred | Order-ledger only |
| Main inline blade fuse holder | 1 | Part of 5-holder set; 12 AWG listing expected | Order-ledger only |
| Standard ATO/ATC 30 A fuse | 1 installed + spares | Must match holder; not mini blade | Order-ledger only |
| XT60-to-8×XT30 PDB | 1 | `100A max` listing; meter every output before use | Order-ledger only |
| 12 AWG red/black silicone wire | route dependent | Minimum 1 m pair | Present, gauge/length unverified |
| 14 AWG red/black silicone wire | route dependent | Minimum 1 m pair | Present, gauge/length unverified |
| XT60 male/female 14 AWG pigtails | 1–2 pairs used | 5 pairs ordered | Order-ledger only |
| Heat shrink | cut to fit | 127-piece kit ordered | Order-ledger only |

XT60 and XT30 are **raw 3S only** in this build. Do not draw or label either
connector family as a 5 V logic connector.

## 7. Group D — four identical fused leg kits

Build one leg branch, test it, then duplicate it three times.

### Per-leg visual kit

| Per leg | Quantity | Exact role |
|---|---:|---|
| C018 servo | 4 | coxa + femur + tibia + wheel |
| 5264 3-pin Feetech bus lead | 4 | one root/signal-tap path plus three inter-servo daisy-chain links |
| XT30 pigtail/branch connector | 1 pair/path | Raw-3S output from PDB |
| Inline standard-blade fuse holder | 1 | Leg branch protection |
| Standard blade fuse | 1 | 15 A branch fuse |
| 16 AWG red silicone wire | route length | V+ leg branch |
| 16 AWG black silicone wire | route length | GND leg branch |
| Electrolytic capacitor | 1 | 4700 µF, 25 V, across V+ and GND at the leg root |
| Printed PETG leg/link/hub parts | one leg set | Final geometry follows received-part measurements and fit coupons |
| TPU tyre | 1 | Wheel contact material |
| Servo horns/horn screws | 4 sets | Prefer supplied C018-compatible horns; verify count and pattern |

### Four-leg total

| Item | Installed total | Ordered/stock target |
|---|---:|---:|
| C018 servos | 16 | 18 |
| 5264 leads | 16 | 18 expected |
| XT30 branch paths | 4 | 10 pigtail pairs ordered |
| Branch fuse holders | 4 | 5 holders total ordered |
| 15 A standard blade fuses | 4 | assortment plus spares |
| 4700 µF 25 V capacitors | 4 | 10 ordered |
| TPU tyres | 4 | printed |

Power path per leg:

```text
PDB XT30 output
  -> 15 A blade fuse
  -> 16 AWG red/black branch
  -> 4700 µF 25 V capacitor in parallel at leg root
  -> C018 V+ and GND power injection
```

The capacitor is never inline. Its marked negative lead goes to GND.

Signal/common-ground path:

```text
Bus Servo Adapter A
  -> one signal/common-ground tap per leg
  -> coxa -> femur -> tibia -> wheel serial-bus daisy chain
```

The exact adapter-to-four-leg tap remains an unresolved physical interface in
the Fusion guide. A picture may show the logical paths, but must not present an
invented splitter/crimp layout as a finished, verified harness.

For any adapter-to-leg 5264 lead that is signal/reference only, V+ must be
isolated. Do not identify or cut a conductor by wire colour alone. First verify
the actual adapter and servo pinout with continuity and authoritative markings.

## 8. Group E — 5 V logic and servo signal

| Item | Required/mounted | Exact specification / role | Prior order record |
|---|---:|---|---|
| FPV UBEC | 1 mounted, spare recommended | 5 V 5 A output; 2–6S / 7–26 V input listing; verify 4.9–5.2 V | Selected `2PCS 5A UBEC` with order quantity ×2, likely 4 modules; AliExpress semantics must be verified |
| ESP32 DevKitC | 1 | WROOM-32, CP2102, Type-C order option | 1 |
| Bus Servo Adapter A | 1 | ST/SC serial-bus Adapter **A**, not PWM/I2C | 1 |
| DC barrel pigtail set | 1 set | 5.5 × 2.1 mm male/female for adapter bench/input use if required | 5-piece set in ledger; exact male/female count needs order-image verification |
| USB data cable | 1 | Data/debug for ESP32 | Present, function unproven |
| VL53L0X breakout | 1 optional | Proximity sensor; exact board variant varies | 1 |
| Common-ground wiring | as routed | UBEC, ESP32, adapter and raw servo rail share reference | raw wire/jumpers |

Correct domain picture:

```text
RAW 3S from PDB -> UBEC input
VERIFIED 5 V from UBEC -> ESP32 / sensors / camera only
ESP32 UART -> Bus Servo Adapter A -> C018 signal bus
all relevant grounds -> common reference
servo motor current -> fused raw-3S leg branches, not through ESP32 or Adapter A
```

By default use one ESP32 power source at a time. If laptop USB remains connected
while UBEC powers the ESP32, use a verified power-blocked USB data lead or a
sacrificial USB hub as documented.

A breadboard is not required by the guide. Mechanically secure, verified direct
jumpers/connectors are sufficient for bring-up.

## 9. Group F — mechanical hardware and printed material

| Item | Minimum useful target | User status | Notes |
|---|---|---|---|
| M2 machine screws | M2×6 and M2×8, about 100 total | Lengths present, type/count unverified | Extra M2 lengths are useful, but do not assume a self-tapper assortment is machine hardware. |
| M2 nuts | Assortment recommended | Unconfirmed | Earlier basket notes recommend an M2 screw/nut assortment. |
| M3 machine screws | M3×6/8/10/12/16, 100–150 mixed | Missing | Final frame/links/tray/brackets. |
| M3 nyloc nuts | 50–100 | Missing | Vibration-resistant joints. |
| M3 washers | useful stock | Likely included in M2–M10 washer assortment; verify | Spreads load on printed plastic. |
| Metric hex keys/drivers | 1.5, 2.0, 2.5, 3.0 mm | Unconfirmed | The 25-in-1 bit set does not prove useful metric hex coverage. |
| C018-compatible horns | at least 18 | Expected with servos; verify | Do not substitute generic SG90/MG996R horns. |
| Horn/mount screws | one usable set per servo + spares | Expected with servos; verify | Photograph/count separately from frame fasteners. |
| 20 mm hook-and-loop straps | 3–4 | Unconfirmed | Required for LiPo and later phone/payload retention. |
| Blue threadlocker | 1 small bottle | Order-ledger only | Apply only after fit and motion range are proven. |
| M3 heat-set inserts | optional later | Unconfirmed | Recommended only after first fit/coupon strategy is chosen. |
| PETG | At least 1 kg to start; final kit may exceed it | 1 kg ordered | Structural parts, pockets, brackets, hubs. |
| TPU 95A | 0.5 kg to start | 0.5 kg ordered | Tyres/feet; failed iterations may require more. |
| PLA | prototype stock | About 3 kg owned | Coupons/prototypes only, not final loaded/heat-exposed pockets. |

No current guide calls for M4 hardware. Final production dimensions for servo
ears, horn bolt circle, spline, cable exit and screw locations must come from
caliper measurements and fit coupons, not listing drawings.

## 10. Group G — safety, soldering and measurement tools

| Item | Quantity | Blocker level / exact use |
|---|---:|---|
| Working multimeter | 1 | **Hard blocker** for powered wiring: voltage, polarity, continuity, UBEC output |
| Safety goggles | 1 | Required during soldering/cutting; use clear lenses if ordered pair is too dark |
| Soldering iron and stand | 1 | Power-wire/connector assembly |
| 63/37 rosin solder, 0.8 mm | 50 g + 20 g backup ordered | Primary beginner-friendly solder |
| Desoldering braid | 3 mm × 1.5 m | Rework |
| Wire stripper/cutter | 10–22 AWG | Power-wire preparation |
| Heat shrink and safe heat source | kit | Insulate every finished joint |
| Non-flammable hot-work surface | 1 | Tile/metal sheet; PVC cutting mat is not a soldering surface |
| Ventilation/local fume control | 1 setup | Required for solder fumes |
| Digital caliper | 150 mm | Servo, horn, board and printed-fit measurements |
| Scale(s) | 10 kg/1 g and optional 1000 g/0.1 g | Subassembly/final mass |
| Blocks/stand | one stable set | Holds wheels/legs clear for Phase 13 |
| Labels/bags | subsystem set | `XT30`, `XT60`, `5264`, `fuses`, `caps`, `fasteners`, `servo horns`, `servo screws` |

The non-contact AC test screwdriver is not a DC multimeter and cannot establish
polarity, exact voltage, continuity, UBEC output, or a short.

## 11. Optional/later parts that should not be confused with blockers

| Item | Status |
|---|---|
| VL53L0X sensor | Optional sensor; not needed for first servo intake |
| Acrylic mirror stickers | Cosmetic/optical experiment |
| Phone payload/frame | Later; no payload during first floor tests |
| Inline watt meter | Useful for logging, not a documented blocker |
| M3 heat-set inserts | Optional after coupon strategy |
| Extra TPU | May be needed after tyre iterations |
| Breadboard | Not required |
| M4 hardware | Not currently specified |
| Generic 3-pin RC/PWM/Futaba/JR servo extensions | Sensor/bench spares only; **not** C018 bus cables |
| 18650 charger | Not part of the 3S LiPo architecture |
| Non-contact AC test screwdriver | Not a robot measurement tool |

## 12. Connector and cable nomenclature audit

| Guide/order name | What it means here | Do not confuse with | Verification required |
|---|---|---|---|
| `5264`, `5264-3PIN`, `ST/SC/CF servo cable`, `Feetech bus lead` | Three-conductor serial-bus lead that physically fits C018/STS3215 ports | Generic PWM/Futaba/JR servo extension | Fit test, housing/key orientation, continuity, pin markings, actual length |
| `XT30 pigtail pair` | Male + female XT30 with 16 AWG wire, used for raw-3S branches | A 5 V connector | Confirm PDB output gender and opposite branch plug |
| `XT60 pigtail pair` | Male + female XT60 with 14 AWG wire, adapters/spares | B6Neo banana lead or logic connector | Confirm gender/polarity |
| `XT90-S` | Anti-spark XT90 disconnect/extension in the main trunk | Plain XT90 or tiny loop-key drawing | Confirm the shipped connector is `XT90-S`, cable is actually 10/12 AWG, and installed lead is not excessively long |
| `XT60-to-8×XT30 PDB` | One XT60 input, eight XT30 raw-3S outputs | A voltage regulator | Meter polarity and voltage on every output |
| `5.5×2.1 mm barrel pigtail` | Adapter/control-board bench/input lead where required | Proof of voltage | Confirm plug polarity and which board actually uses it |
| `standard blade fuse` / `ATO` / `ATC` | Fuse size expected for the five inline holders | Mini, low-profile mini or micro blade fuse | Physically match holder before power |
| `USB data cable` | USB cable that enumerates FE-URT/ESP32 on Windows | Charge-only cable | Demonstrate COM/USB data, not just charging LED |

The phrase `JST-GH-style` appears in the old order ledger as a visual
approximation for the 5264 lead. It should **not** be promoted to a guaranteed
connector-family identification in the regenerated pictures. Use the seller's
exact order-option wording plus `Feetech 5264 3-pin / STS3215-compatible`, and
keep the physical-fit check as the acceptance criterion.

## 13. Reference physical envelopes for faithful scale

These are provisional guide/CAD envelopes. Rendered product shape should follow
the verified order images and physical photos.

| Item | Reference envelope |
|---|---|
| C018 / STS3215 servo | 45.2 × 24.7 × 35 mm; about 55 g |
| FE-URT-1 | 55.8 × 36.6 × 11.5 mm |
| HOOVO 3S 2200 mAh pack | about 104 × 34.5 × 24.5 mm; about 174 g |
| B6Neo | 70 × 50 × 32 mm; about 82 g |
| Bus Servo Adapter A | about 42 × 33 mm PCB; populated height unknown |
| ESP32 candidate | about 54.8 × 28.6 × 10–13 mm |
| UBEC candidate | about 43 × 21 × 8 mm |
| PDB candidate | about 45 × 45 × 18 mm |
| XT90-S connector | about 25 × 20 × 10 mm; ordered lead length still needs verification |
| Inline fuse holder | about 45 × 20 × 15 mm |
| 4700 µF 25 V capacitor | typically 16 mm diameter × 25–30 mm high |
| XT30 connector body | about 13.5 × 8 × 4.5 mm |
| LiPo bag | 185 × 75 × 60 mm |
| 5264 leads | Ordered listing had 300/900 mm options; actual selected/received lengths unresolved |

## 14. Image-generation inventory contract

The replacement set should depict:

1. **Individual identification sheet:** one verified image tile for every distinct
   ordered product/SKU, with exact order-option text, ordered quantity, and a
   confidence badge (`order verified`, `physical photo verified`, or
   `appearance uncertain`).
2. **Group A:** one-servo FE-URT intake bench, with exactly one C018, one 5264
   lead, USB data and protected external 3S power. No horn fitted.
3. **Group B:** two HOOVO packs as stock, but only one pack connected to B6Neo,
   with balance lead, XT60 main lead, PD input and LiPo bag.
4. **Group C:** raw-3S main trunk, showing XT90-S, one 30 A main holder/fuse,
   PDB, heavy red/black wire and temporary smoke-stopper placement.
5. **Group D:** four repeated leg trays labelled FL/FR/RR/RL. Each tray contains
   four C018s, four 5264 leads, one XT30 branch, one 15 A holder/fuse, one
   4700 µF 25 V capacitor, and red/black 16 AWG.
6. **Group E:** UBEC, ESP32 CP2102 Type-C, Bus Servo Adapter A, barrel pigtail,
   USB data lead and optional VL53L0X, with raw 3S / verified 5 V / signal /
   common-ground layers visually separated.
7. **Group F:** M2 machine screws, missing M3 shopping silhouette, M3 nylocs,
   washers, horns, straps, PETG and TPU. Do not include M4 as a required gap.
8. **Group G:** working multimeter, iron/stand, solder, wick, stripper, goggles,
   non-flammable hot-work surface, ventilation and labels. Mark the illuminated
   screwdriver as `not a multimeter`.
9. **Master together view:** bench-only tools outside the robot boundary; one
   mounted LiPo; 16 installed servos; two tested spares; charger and FE-URT not
   mounted.

Every cable-end depiction must follow the verified seller/physical image. If
the order page cannot establish the exact 5264 housing or selected lead length,
render it as an isolated product-reference tile labelled `verify against
received cable`, not as a definitive final harness.

## 15. Safe first action from the current state

Before testing a servo:

1. Install the correct battery in the ANENG SZ308 and prove continuity plus DC
   voltage on a known safe source.
2. Locate one genuine C018-compatible 5264 lead and prove it fits without force.
3. Identify the FE-URT-1 USB connector and prove the cable carries data.
4. Prepare one protected external 3S servo-power path with a 5 A or 7.5 A fuse
   if available and the smoke stopper.
5. Connect one C018 only, with no horn.
6. Use FE-URT-1 for the first ID/register/small-sweep test.

ESP32 testing comes later through Bus Servo Adapter A with a verified 5 V logic
rail, common ground and a separate fused raw-3S servo rail. The ESP32 and its USB
port must never carry C018 motor current.
