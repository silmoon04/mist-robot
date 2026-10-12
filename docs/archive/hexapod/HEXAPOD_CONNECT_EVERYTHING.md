# Hexapod — "Connect Everything" addendum (the parts beginners forget)

Companion to `HEXAPOD_BOM_ANALYSIS.md`. This is the **connective glue**: the connectors, termination consumables, charging/power-safety bits, programming/bring-up gear, motion hardware, and tools that don't show up in a servo+battery BOM but stall the build when missing. Priorities: **CRITICAL** (build stops without it) / **RECOMMENDED** / **OPTIONAL**. £ = rough AliExpress GBP. Sources: cross-model (GPT-5.5) gap pass + the main analysis.

> ⚠️ **The single most-overlooked item:** the **SKYRC B6neo charger is DC-input only** — it has **no mains plug**. Without a separate **DC power brick** it cannot charge anything. Buy one (see §B). This alone strands a lot of first-time buyers.

---

## A. Electrical connectors & termination (wire it together)

| Item | Why needed | AliExpress search | £ | Priority |
|---|---|---:|---|---|
| **Dupont jumper kit (M-F, F-F, M-M, 10–20cm)** | I2C wiring for MPU6050 / VL53L0X / OLED to the ESP32 (SDA/SCL/3V3/GND) and bench jumpers | `dupont jumper wire male female 120pcs` | 2–4 | CRITICAL |
| **JST-XH / PH2.0 connector + crimp-pin kit** | Make clean detachable sensor/power pigtails instead of soldering everything | `JST XH PH2.0 connector kit crimp pins` | 4–8 | RECOMMENDED |
| **Ratcheting crimp tool (SN-2549 / SN-28B)** | You can buy connectors but you **cannot terminate them** without this. #1 silent blocker | `SN-2549 crimping tool dupont JST` | 8–14 | CRITICAL |
| **Wire ferrules + ferrule crimper** | Screw terminals on the PDB / buck need ferrules, not tinned/bare strands (loosen + arc) | `wire ferrule kit crimper 0.25-6mm` | 7–12 | RECOMMENDED |
| **Spare XT60 pairs + XT60 pigtails** | Power wiring always needs more connectors than planned (buck in/out, PDB taps) | `XT60 connector male female pigtail 14awg` | 3–6 | CRITICAL |
| **Bullet connectors 3.5/4mm (optional)** | Quick servo-power branch disconnects if you don't solder | `3.5mm bullet connector silicone wire` | 2–4 | OPTIONAL |
| **Solder (leaded 0.8mm) + flux + wick** | XT60s, bus injection points, repairs; flux makes power joints reliable | `solder wire 0.8mm 63/37` · `rosin flux paste` · `desoldering wick` | 4–8 | CRITICAL |
| **Heat-shrink gun (or rely on the iron)** | You already have heat-shrink tubing; needs even heat to seal | `mini hot air heat shrink gun` | 6–12 | RECOMMENDED |
| **Helping-hands / PCB holder** | Third hand for soldering 18 servo cables + XT60s | `helping hands soldering pcb holder` | 5–10 | RECOMMENDED |
| **Flush cutters + wire strippers** | Clean cuts/strips on silicone wire and zip ties | `flush cutter` · `self adjusting wire stripper` | 5–10 | RECOMMENDED |
| **Spare multimeter probes / alligator clips** | You have a multimeter; clips free your hands for live checks | `multimeter alligator clip test lead` | 2–5 | OPTIONAL |

## B. Battery, charging & power safety

| Item | Why needed | AliExpress search | £ | Priority |
|---|---|---:|---|---|
| **DC power brick for the B6neo (≥12V, 5–10A / 100W+)** | The charger has **no AC input** — useless without this. A laptop-style 19–24V 5A PSU works | `15V 24V 6A power adapter XT60 charger PSU` | 8–16 | CRITICAL |
| **2S balance-lead extension (JST-XH)** | Reaches the charger's balance port without flexing the pack leads | `JST-XH 2S balance lead extension 30cm` | 1–3 | RECOMMENDED |
| **Battery strap / hook-loop with buckle** | Velcro alone won't hold a pack against gait vibration — needs real retention | `RC battery strap hook loop 20mm` | 2–4 | CRITICAL |
| **LiPo voltage checker (BB plug)** | Quick per-cell check before/after flights of walking | `1-8S lipo battery voltage checker BB` | 1–3 | RECOMMENDED |
| **2S LiPo low-voltage alarm buzzer** | Backstop against over-discharge / brownout mid-walk (firmware cutoff is primary) | `2S 3S lipo low voltage buzzer alarm` | 1–3 | CRITICAL |
| **Main kill switch (20A+) / XT90-S loop key** | Instant power cut for a jammed 18-servo robot; loop key also tames inrush | `XT90S anti spark loop key` · `20A DC rocker switch` | 3–8 | CRITICAL |
| **Spare blade fuses, 5–30A assortment** | One short stops the build; you'll blow a few while tuning | `mini blade fuse assortment 5A 10A 15A 20A 30A` | 2–5 | CRITICAL |
| **Reverse-polarity / TVS spike protection (optional)** | Cheap insurance against a wrong-way battery or motor spikes | `MOSFET reverse polarity module` · `SMBJ TVS diode 12V` | 2–7 | OPTIONAL |

## C. Programming, flashing & bring-up

| Item | Why needed | AliExpress search | £ | Priority |
|---|---|---:|---|---|
| **USB *data* cable for the ESP32 board** (check USB-C vs micro) | A charge-only cable wastes hours — no COM port. Match the Waveshare board's connector | `USB-C data cable short` / `micro USB data cable` | 1–3 | CRITICAL |
| **CH340 / CP210x driver** (free software) | Windows needs the USB-serial driver before the board/FE-URT-1 enumerate | *(download — WCH / Silabs)* | 0 | CRITICAL |
| **Current-limited bench PSU (CC-CV) — or use a buck carefully** | Safe **first power-up** at low current limit catches a wiring fault before it cooks parts | `adjustable bench power supply 30V 5A` | 25–45 | RECOMMENDED |
| **Spare ESP32 dev board (CH340)** | Known-good controller to isolate "is it the board or my wiring?" | `ESP32 WROOM dev board CH340 38pin` | 4–8 | RECOMMENDED |
| **Breadboard + sensor bring-up** | Test MPU6050/ToF/OLED on the bench before they go on the robot | `breadboard 830 jumper kit` | 3–6 | OPTIONAL |
| **Cable/servo labels** | 18 servos + cables need IDs that match your servo map | `heat shrink cable marker numbers` | 3–8 | RECOMMENDED |

## D. Mechanical & motion hardware *(from the cross-model gap pass)*

| Item | Why | Search | £ | Priority |
|---|---|---|---:|---|
| M2×6 socket screws ×100 | Servo body mounting (included screws unreliable) | `M2 x 6mm socket head screws 100pcs` | 2–4 | CRITICAL |
| M3 screw assortment kit | Chassis/brackets/printed joints | `M3 socket head screw assortment kit` | 6–10 | CRITICAL |
| M3 nyloc nuts ×100 | Vibration-proof joints | `M3 nylon lock nut 100pcs` | 2–4 | CRITICAL |
| M3 washers ×200 | Stop screw heads chewing PETG/PLA | `M3 flat washer stainless 200pcs` | 2–4 | CRITICAL |
| M3 brass heat-set inserts + iron tip | Durable threads in printed parts | `M3 brass heat set insert` · `heat set tip M3` | 7–14 | CRITICAL |
| **Exact horn screws (M3×6) + spare STS3215 horns** | A lost/stripped horn screw disables a whole leg | `M3 x 6 servo horn screw` · `Feetech STS3215 horn 25T` | 6–12 | CRITICAL/REC |
| M3 shoulder bolts (precision pivots) | Tighter leg pivots than printed holes | `M3 shoulder screw 3mm shaft` | 5–10 | RECOMMENDED |
| M3 standoffs (nylon/alu) | Stack controller / PDB / phone plate | `M3 nylon standoff spacer kit` | 4–8 | RECOMMENDED |
| Mini bearings (size to CAD) | Smooth idler pivots — **measure CAD first** | `MR83ZZ` / `F623ZZ flanged bearing` | 4–8 | RECOMMENDED |
| TPU 95A filament | Grippy shock-absorbing feet | `TPU 95A filament 1.75mm` | 12–18 | CRITICAL |
| PETG filament | Structural parts tougher/hotter-tolerant than PLA | `PETG filament 1.75mm 1kg` | 10–16 | CRITICAL |
| **Real phone clamp/strap (not tape)** | Phone must be mechanically retained against vibration | `phone holder tripod clamp screw mount` | 4–8 | CRITICAL |
| Anti-vibration damper pads (M3) | Protect phone camera/IMU from servo buzz | `rubber anti vibration damper M3` | 3–7 | RECOMMENDED |
| Zip ties (small/med) + releasable | Cable routing + serviceable leg bundles | `nylon cable ties assorted` · `reusable cable ties` | 2–5 | CRITICAL |
| PTFE/silicone lube (pivots, not gears) | Bushings/pivots | `PTFE silicone grease plastic gear` | 3–6 | RECOMMENDED |

## E. Thermal, protection & cable management *(from the gap pass)*

| Item | Why | Search | £ | Priority |
|---|---|---|---:|---|
| Heatsink kit + thermal adhesive | Stops the buck/regulator thermal-shutting at 15–20A | `aluminum heatsink assortment thermal tape` | 2–5 | RECOMMENDED |
| 30/40mm 5V fan | Active cooling for an enclosed buck/controller | `5V 30mm cooling fan` | 2–5 | OPTIONAL |
| Cable glands / rubber grommets | Protect wires through printed chassis holes | `rubber grommet assortment cable` | 3–6 | RECOMMENDED |
| Strain-relief clamps (M3) | Keep leg motion loads off solder joints | `nylon cable clamp strain relief M3` | 3–6 | CRITICAL |
| PET braided sleeving 4/6/8mm | Abrasion protection on moving leg bundles | `PET braided cable sleeving 4 6 8mm` | 4–8 | CRITICAL |
| Kapton + foam tape | Board insulation / vibration isolation | `Kapton tape 10mm` · `3M foam tape` | 3–8 | RECOMMENDED |

## F. Tools you likely lack *(from the gap pass)*

| Item | Why | Search | £ | Priority |
|---|---|---|---:|---|
| **Precision hex driver set (1.5/2/2.5/3mm)** | Tiny socket screws strip with bad keys | `precision hex screwdriver set metric` | 8–18 | CRITICAL |
| **Digital calipers** | Bearing/hole/horn/insert sizes can't be guessed | `digital caliper 150mm` | 8–15 | CRITICAL |
| **Temp-controlled soldering iron (T12)** | XT60s, inserts, repairs | `T12 soldering iron kit temperature controlled` | 20–35 | CRITICAL |
| Bench vise / small clamp | Hold parts while assembling | `mini bench vise clamp` | 8–15 | RECOMMENDED |
| Deburring tool / pin vise + bits / M2-M3 taps | Clean and size printed holes/threads | `deburring tool` · `pin vise drill set` · `M2 M3 tap set` | 12–25 | RECOMMENDED |
| Safety glasses | Cutting/soldering/LiPo handling | `safety glasses anti splash` | 2–5 | CRITICAL |

---

## TOP 15 most-forgotten (ranked by how badly absence stalls the build)

1. **Feetech FE-URT-1** — without it, assigning unique IDs to 18 servos is painful/blocked.
2. **Correct Feetech STS/SCS 3-pin bus cables** — PWM extensions don't solve serial-bus wiring.
3. **B6neo DC power brick** — the charger is useless without an external DC PSU.
4. **USB *data* cable for the ESP32** — charge-only cables waste hours during flashing.
5. **Current-limited bench PSU / CC-CV supply** — first power-up from LiPo can destroy parts fast.
6. **Main kill switch / XT90-S loop key** — a jammed 18-servo robot needs an instant cut.
7. **XT60 pigtails + spare XT60 pairs** — power wiring always needs more connectors than expected.
8. **Dupont/JST crimp tool + pins/housings** — beginners buy connectors but can't terminate them.
9. **Spare blade fuses (multiple ratings)** — one short can halt the whole build.
10. **Battery strap / real mechanical retention** — Velcro alone fails under gait vibration.
11. **Blue threadlocker (243)** — walking robots loosen screws constantly.
12. **Exact horn screws + spare horns** — one missing/stripped horn screw disables a leg.
13. **M3 washers + nyloc nuts** — printed joints need load spreading + vibration resistance.
14. **Braided sleeving + grommets + strain-relief clamps** — moving leg wires fail at exits/joints.
15. **Calipers** — bearing/bushing/screw/horn/insert sizes can't be guessed reliably.
