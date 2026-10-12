# Hexapod pre-flight — critical pre-order audit, wiring plan & test protocol

Generated 2026-07-02 by a 36-agent adversarial audit (6 specialist auditors re-deriving the math from manufacturer datasheets, every critical/high finding independently re-verified, then a completeness critic). 25 critical/high findings survived verification; 0 were refuted.

**Read Part 1 before paying for anything.**

---
# Part 1 — Critical Pre-Order Check & Corrected Buy List

**Read this before paying for anything.** Every number below traces to a manufacturer datasheet (Feetech STS3215-C001 spec, Waveshare Servo Driver with ESP32 docs, SkyRC, Hobbywing) — not the project docs, which were caught wrong in several places (battery weight, "hours idle", the 40A bench test, the M3-tap advice). The two most expensive mistakes available this week are (a) ordering the wrong STS3215 variant (£258.72 at stake) and (b) buying no-name "20A" SBECs for the #1-risk line item.

---

## 1. What can go wrong — severity-ranked

| # | Sev | Problem | The one-line math | Fix (before ordering) |
|---|-----|---------|-------------------|------------------------|
| 1 | 🔴 CRIT | **Servo variant trap on the two biggest cart lines.** STS3215 sells as C001 (7.4V/1:345/19.5 kg·cm), C044 (7.4V/1:191), C046 (7.4V/1:147) and C018 (12V/30 kg·cm) behind one option dropdown. | C044 on your 7.4V rail = 19.5 × 191/345 = **10.8 kg·cm (−45%)**; C046 = 8.3 kg·cm (−57%); C018 keeps ~94% torque but runs at 27.7 rpm vs 52 rpm (**53% speed**). Exposure: £162.93 + £95.79 = **£258.72**. | Confirm the *selected option text* reads **"7.4V 19.5kg" / 1:345 / TTL** on all 18 units, and that the 6-pack option **explicitly includes the FE-URT-1** (photos lie). Screenshot both option texts for dispute evidence. |
| 2 | 🔴 CRIT | **The "two isolated 7.4V rails" plan is physically impossible as drawn.** Every 5264 bus cable carries V+ (pinout GND/V+/Signal), and the Waveshare board's DC jack IS the servo-bus V+ plane (board max **5A**). | 18 × 2.5A stall = **45A ≫ 5A** board limit; any leg cable plugged into the board ties that rail's V+ to the board's jack net → SBEC-A and SBEC-B hard-paralleled through the PCB, even with the jack unplugged. | Pull/cut the **middle (V+) pin from all six board-to-leg 5264 cables** (Signal+GND only through the board — GND must stay continuous). Inject 7.4V at each leg root. Feed the board's jack from rail A only (7.4V is inside its 6–12.6V spec). Buy spare 5264 housings so cut cables aren't irreversible. |
| 3 | 🔴 CRIT | **A "20A" SBEC is below its own 9-servo group stall.** Feetech spec 5-5: stall = 2.5A ±10%/servo @7.4V; protection only trips after 2s (spec 7-11). | 9 × 2.5A = **22.5A** (24.75A at tolerance) > 20A for up to **2s** → rail folds back, half the robot browns out mid-fall. | Replace the "2× 20A SBEC" search-term line with a named part: **2× Hobbywing UBEC 25A HV** (25A cont / 50A peak, 3–18S in, DIP-set 7.4V, 74g). Real price: **~£62–65 each UK** (Wheelspin £61.74 / 3DXR £64.99) or ~£105/pair on AliExpress — not the £30–35 the docs guessed. |
| 4 | 🔴 CRIT | **Continuous torque is 5 kg·cm, not 19.5.** 19.5 is *stall*; rated is 5 kg·cm @ 650 mA (spec 5-8/5-9, Kt = 7.8 kg·cm/A). | Tripod stand at 14 cm reach: (2.4/3) kg × 14 cm = **11.2 kg·cm = 2.24× rated**, 1.44A vs 0.65A rated. 2-leg events: 16.8 kg·cm → 2.15A > 2.0A default trip if sustained 2s. | No new part — a **design rule**: gait keeps the foot under the knee (~7 cm femur moment arm → 5.6 kg·cm ≈ 1.1× rated, viable only via gait duty-cycling), torque-off "sit" pose as default idle, configure protection registers day 1. |
| 5 | 🔴 CRIT | **Mass busts the torque envelope before the phone goes on.** Docs' "~200g electronics" is 2–3× too low. | 990g servos + 228g pack + **440–630g** electronics/harness + 550–900g frame + 100–200g fasteners + 30–50g sensors = **2,338–2,998g** vs ~2.3 kg (SF≥1.8) / ~2.5 kg tolerable. SF-2.0 envelope: mass × reach ≤ 29.25 kg·cm → at 2.4 kg, reach ≤ 12.2 cm. | Commit now: phone **off-board** (155g, teleop over WiFi), printed frame budget **≤650g**, tibia ~10 cm and mid-stance reach ≤11–12 cm, battery stays the 228g 3350 (the 343g figure in the docs is the *rejected* 5000 pack). No servo-class change needed if you do all of the above. |
| 6 | 🟠 HIGH | **One mis-set DIP/jumper feeds 18 servos 8.4–12V.** Hobbywing: switch 1 ON alone = 8.4V; HiModel: 7.4/8.4/9/12V jumper. Servo protection trips at >8.0V and *stays* tripped on a regulated rail; 7.5–8.0V is a silent over-stress band. | 8.4/7.4 = **+13.5%**; 12/7.4 = **+62%**; rated input is 4–7.4V (spec 5-7). | **Step 0 of bring-up:** with SBEC powered off, set 7.4V; power on with NO servos; multimeter each output, accept only 7.2–7.5V; then tape/glue the switches. Leave servo register 14 at its factory 8.0V ceiling. |
| 7 | 🟠 HIGH | **Nothing in the basket can legally power the brain.** Waveshare jack minimum is 6V; your 5V UBEC is 1.0V short — and no 5.5×2.1mm pigtail exists anywhere in the cart. | 5.0V < 6.0V min; jack net = servo V+ net, so feeding it 12V would put 12V on 7.4V-max servos. | Add a **5.5×2.1mm male DC barrel pigtail** (~£1–2); feed the jack from rail A at 7.4V. 5V UBECs power *sensors only* (camera, OLED, IMU, ToF). All grounds common — "isolated" means separate +V nets only, never separate grounds. |
| 8 | 🟠 HIGH | **The Waveshare board has ZERO spare GPIO** — official schematic shows no expansion header. The SH1106 eyes need 5 signal pins; the board exposes 0; its I2C is consumed by the onboard OLED with no header. | SH1106 SPI needs SCK/MOSI/CS/DC/RST + 3V3/GND; exposed pins = **0**. | Add a **plain ESP32 dev board (CH340, £4–8)** as the sensor/eyes node — promote from "recommended" to REQUIRED. It hosts SH1106 + VL53L0X (+ optionally MPU6050) and talks to the driver ESP32 over UART/ESP-NOW. |
| 9 | 🟠 HIGH | **Connector-system mismatch.** The servo bus is Molex 5264 (2.50mm SPOX); JST-XH and Dupont physically do not mate with it. The Dupont/JST kit covers sensors only. | 0 of the planned kit's housings fit the servo sockets. | Add a **5264 3P housing + 5263 terminal kit** (£3–5) OR decide now to solder+heatshrink the 6 power-injection taps into pre-made cables (easier for a first-time crimper). Never buy anything labelled "JST-XH servo cable" for the bus. |
| 10 | 🟠 HIGH | **Cable count = zero spares, and hub runs are too short.** Bus tree: 1 driver + 18 servos = 19 nodes → exactly 18 cables needed; 18 included 15cm cables = 0 spares; driver-to-hip runs need 20–30cm. | 19 nodes − 1 = 18 runs; 18 included − 18 needed = **0 spares**; hub run ≈ 200–270mm > 150mm supplied. | Quantify the cable line: **6× 30cm + 6× 20cm + 4 spares** pre-made 5264 cables (~£5–8). Confirm each servo listing states "with cable". |
| 11 | 🟠 HIGH | **Nothing can plug into the PDB.** 8 XT30 outputs, zero XT30 mates in the basket. And the 6 leg branches must NOT hang off the PDB anyway — it carries raw 3S (12.6V > 7.4V servo max). | PDB loads = 2 SBEC inputs + 1 UBEC input = **3 XT30 males minimum**. SBEC feed worst case ≈ 15.7A vs XT30's 15A cont — at the limit, OK for bursts. | Add **10× XT30 pigtail pairs, 16AWG** (£3–6). Leg fuses/branches go on the SBEC *outputs*. Check the listing photo for pigtail gender (source = female convention). |
| 12 | 🟠 HIGH | **The harness cannot be built with what's listed.** No solder, flux, strippers, cutters, spare XT60s, battery strap, data cables or safety glasses anywhere — and you own only a multimeter. | Soldering iron + 0 solder = **0 joints**. Gap ≈ £20–35 total. | Add the consumables bundle (list in §3, items A13–A18). |
| 13 | 🟠 HIGH | **SBEC dropout near empty pack.** Including fuse/connector/wire resistance (~35–40 mΩ loop), a stall burst near 3.3V/cell pulls SBEC input to ~8.3V — only **0.9V** above the 7.4V output, inside cheap-buck dropout. | At 3.5V/cell alarm: Vin ≈ 9.0V → 1.6V differential — borderline, not comfortable. | Buy SBECs verified to **regulate 7.4V from a ~9V input at load** (the Hobbywing 25A HV qualifies; a generic "min input 6V" spec does NOT prove this). Set the LiPo alarm to **3.5V/cell = hard walk-stop**; exclude 3.3V capacity from runtime math. |
| 14 | 🟠 HIGH | **The docs' "bench-test at 40A for 10–15 min" is physically impossible**, and 20A continuous from a 30g shrink-wrap SBEC is thermally impossible in still air. | 40A test needs 4.7–7.0 Ah vs **2.68 Ah usable** in the pack (dies at ~5.7 min); 16.4W loss into a 0.007 m² case = **ΔT ≈ 107–238°C** still-air. | Rewrite: one SBEC at a time, ~20A for 5–8 min, **with the 30mm fan + aluminium plate fitted as they will fly** (forced air → ΔT 33–48°C: passes). Dummy load: 3× 1Ω 100W resistors (22.2A, ~£12) or 4× H4 bulbs (~24.6A). Promote the 30mm 5V fan to REQUIRED. |
| 15 | 🟡 MED | **XT90-S loop key mates with nothing** — the whole system is XT60. | XT90 ≠ XT60 mechanically; 0 adapters in basket. | Buy a pre-made **XT90-S loop key with XT60 pigtails**, or one XT60M→XT90F + one XT90M→XT60F adapter pair (~£4–6). |
| 16 | 🟡 MED | **Per-leg fuses must be 10A, not 5A.** | Leg stall = 3 × 2.5A = 7.5A = **150% of a 5A blade** → nuisance-blows in tens of seconds; on 10A it's 75% → holds. 30A main is correct — keep it, mounted within 10cm of the battery XT60. | Standardise **10A per leg**; buy spares of 10A and 30A in the fuse assortment. |
| 17 | 🟡 MED | **Do NOT buy an M3 tap — the earlier advice was wrong.** The SO-101 reference design fastens STS3215s with M2x6 through the case's 8 holes; the included self-tappers are M2-class. | If the holes were M3-tap pilots (2.5mm), an M2 screw (Ø2.0mm) would have zero engagement — yet thousands of SO-101 arms hold together. | Keep the M2x6 kit; use included self-tappers first. If your CAD uses all 8 holes/servo: 18 × 8 = 144 > 100-pc kit → buy a **second M2 kit (£2–4)**. Message both servo sellers to confirm per-unit contents (horn + screw bag + 15cm cable) — free, no order delay. |
| 18 | 🟡 MED | **First power-up trusts an untested LiPo→SBEC chain that can source 117A.** | 35C × 3.35 Ah = 117A available; a 30A blade at 200% takes 0.15–5s — long enough to vaporise a 28AWG pigtail. | Build a **smoke stopper** (H4 55W bulb inline on XT60 pigtails, ~£5): limits any dead short to ~5A. Optional but strongly recommended: 30V/10A CC-CV bench PSU (£35–45, UK Amazon for returns) — also serves as the FE-URT-1 servo-ID supply and the B6neo DC input. |

---

## 2. Corrections to the current AliExpress cart (£354.14 as line-summed)

**VERIFY before paying (no cost, highest stakes):**

- **12-pack STS3215 (£162.93) + 6-pack w/ FE-URT-1 (£95.79):** open both listings; the selected option must literally say **7.4V / 19.5kg (.cm) / 1:345 / TTL serial** — not 12V/30kg, not "1:191/1:147 high speed". Confirm the 6-pack option *includes* the FE-URT-1 board. Screenshot both. Also message both sellers: "does each servo ship with disc horn, horn screw, mounting screws, and 15cm cable?"
- **2× 5V 5A UBEC (£4.59):** listing must state input **2–6S / DC 7–26V** (some £2 units are 2S-max). Role change: these power the *sensor node only* — never the Waveshare board (its jack needs ≥6V).
- **SkyRC B6neo (£26.99):** "B6neo 2" matches no SkyRC model name (lineup: B6neo / B6neo+ / B6nex). If the store is no-name, treat as clone risk and buy from a SkyRC-branded store. Charging works from your owned 100W PD charger: 1C = 3.35A × 12.6V ÷ 0.9 ≈ 47W < 80W PD ceiling. Use the **5A e-marked USB-C cable** that came with the 100W charger (a 3A cable silently caps at 60W).
- **XT60→8ch XT30 PDB (£14.39):** keep, but note only **3 loads** connect to it (2× SBEC in + 1× UBEC in). It carries raw 12.6V — leg branches never attach here. Check output pigtail gender in the photos.
- **Silicone wire kit (£7.33):** verify it contains *true* 14AWG (cheap kits under-gauge). Usage plan: 12AWG battery→PDB, 14AWG SBEC output trunks, 16AWG per-leg branches.
- **4700µF 16V caps (£1.42):** fine on the 7.4V rails (46% of rating). If any cap ends up on the raw battery side, that's 12.6/16 = 79% — buy 2× **4700µF 25V** (~£1.50) for those positions. Allocation: 2–3 per SBEC output + 1 per leg root.

**CHANGE:**

- **"2× 20A SBEC 7.4V" (still-to-add line):** replace the search term with a named part — **2× Hobbywing UBEC 25A HV**. UK: £61.74 each (Wheelspin) / £64.99 (3DXR); AliExpress ~£53 each (beware fakes — buy from the official Hobbywing store). This is the single biggest budget correction: **~£105–130, not £60–70**.
- **XT60→4mm charge lead (£2.00):** unnecessary for charging — the B6neo's charge output is a native XT60 and the pack plugs straight in. Keep it *only* if you buy the bench PSU (it becomes the PSU→charger DC-input lead); otherwise remove.

**DO NOT BUY (traps from earlier drafts):**

- ❌ M3 tap / tapped-M3 servo mounting (wrong — M2x6 is the reference-design fastener)
- ❌ 18–24 spare 25T horns (servos ship with horns per every distributor channel; only add *if* a seller confirms bare packs)
- ❌ Second battery now (bench work draws 0.5–2A; add a second 3350 after first walk, never a 5000 — its +115g costs torque where it hurts most)
- ❌ XT60 Y-splitters (the PDB does the fan-out; no remaining use case)
- ❌ Anything labelled "JST-XH servo cable" for the bus

---

## 3. Additions — exact items, quantities, search terms, prices

**A. Power (the load-bearing fixes)**

| # | Item | Qty | Search term | Price |
|---|------|-----|-------------|-------|
| A1 | Hobbywing UBEC 25A HV (set DIP to 7.4V) | 2 | `Hobbywing UBEC 25A HV 3-18S` (official store) | £105–130 |
| A2 | 5.5×2.1mm male DC barrel pigtail, 18AWG | 2 | `5.5x2.1mm male DC pigtail cable 18AWG` | £1–2 |
| A3 | XT30 pigtail pairs, 16AWG | 10 pr | `XT30 pigtail 16AWG male female pair` | £3–6 |
| A4 | XT90-S loop key with XT60 pigtails (or XT60↔XT90 adapter pair) | 1 | `XT90-S anti spark loop key XT60` | £4–6 |
| A5 | Inline mini-blade fuse holder, 16AWG | 6 | `inline mini blade fuse holder 16AWG waterproof` | £4–6 |
| A6 | Blade fuse assortment incl. ≥6× 10A + ≥2× 30A spares | 1 kit | `mini blade fuse assortment 5A 10A 30A` | £3–5 |
| A7 | LiPo alarm, 1–8S, settable per-cell display buzzer | 1 | `lipo battery voltage alarm 1-8S adjustable` | £2–3 |
| A8 | 30mm 5V fan (SBEC cooling — REQUIRED) | 2 | `30mm 5V brushless fan 3010` | £2–5 |
| A9 | H4 55/60W bulb + holder (smoke stopper) | 2+1 | `H4 halogen bulb holder socket` | £5 |
| A10 | 4700µF **25V** caps (battery-side positions only) | 2 | `4700uF 25V electrolytic capacitor` | £1.50 |

**B. Servo bus & connectors**

| # | Item | Qty | Search term | Price |
|---|------|-----|-------------|-------|
| A11 | Pre-made 5264 3-pin bus cables: 6× 30cm + 6× 20cm + 4 spares | 16 | `5264 3 pin servo cable double head Feetech 30cm` | £5–8 |
| A12 | Molex 5264 3P housings + 5263 terminals kit | 20 sets | `5264 connector 3P housing 2.5mm terminal kit` | £3–5 |

**C. Build consumables & tools (currently zero joints possible)**

| # | Item | Qty | Search term | Price |
|---|------|-----|-------------|-------|
| A13 | 63/37 solder 0.8mm (100g) + rosin flux + desolder wick | 1 ea | `63/37 solder wire 0.8mm 100g rosin flux paste desoldering wick` | £4–8 |
| A14 | Self-adjusting wire strippers + flush cutters | 1 ea | `self adjusting wire stripper` / `flush cutter electronics` | £5–10 |
| A15 | Spare XT60 male/female pairs with pigtails | 3 pr | `XT60 connector pigtail 14AWG pair` | £3–6 |
| A16 | 20mm hook-loop battery strap | 2 | `RC lipo battery strap 20mm 250mm` | £2–4 |
| A17 | USB-C **data** cable + micro-USB **data** cable (board/FE-URT-1 revisions differ) | 1 ea | `USB C data cable short` / `micro USB data cable` | £1–3 |
| A18 | Safety glasses | 1 | `safety glasses clear` | £2–5 |
| A19 | SN-28B crimp tool (already planned — keep) | 1 | `iWiss SN-28B` | £6–9 |
| A20 | Dupont/JST-XH kit (sensor wiring ONLY — does not fit the servo bus) | 1 | `dupont JST XH connector kit assortment` | £5–8 |
| A21 | Anti-static wrist strap | 1 | `anti static wrist strap` | £2 |
| A22 | Resistor assortment (rail-sense dividers: 2× 100k/33k into ESP32 ADC) | 1 | `metal film resistor assortment kit` | £2 |

**D. Fasteners, mechanics, electronics (planned — now quantified)**

| # | Item | Qty | Search term | Price |
|---|------|-----|-------------|-------|
| A23 | M2x6 machine screw kit (second kit if CAD uses 8 holes/servo: 144 > 100) | 1–2 | `M2 screw nut assortment kit` | £2–4 |
| A24 | M3 screw kit + M3 heat-set inserts + insert iron tip | 1 ea | `M3 heat set insert kit` / `heat set insert soldering tip` | £8–12 |
| A25 | Digital calipers 150mm + hex driver set | 1 ea | `digital caliper 150mm` / `hex screwdriver set 0.9-3mm` | £9–15 |
| A26 | Inline watt-meter, 130A XT60 | 1 | `RC watt meter 130A power analyzer XT60` | £8–12 |
| A27 | ESP32 dev board, CH340 (sensor/eyes node — REQUIRED) | 1 | `ESP32 DevKitC WROOM-32 CH340 38pin` | £4–8 |
| A28 | Threadlocker (blue), braided sleeving, zip ties | 1 ea | `threadlocker 243 blue` / `braided cable sleeve 6mm` | £5–8 |

**AliExpress additions subtotal: ≈ £200–245** (of which ~£105–130 is the UBEC pair — the corrected #1-risk item).

**E. UK buys**

| Item | Price | Note |
|------|-------|------|
| Overlander 3350mAh 3S 35C, **XT60 selected in dropdown** | £35 | 228g — confirmed correct pick over the 5000 |
| Creality Ender 3 V3 SE | £149 | |
| PETG 2× 1kg + TPU 95A 1kg | £35–45 | Print rules: 4–6 walls, ≥40% infill on femur/tibia, layers along the beam axis |
| Temp-controlled soldering iron (Pinecil / KSGER T12 class) | £25–40 | |
| *(Optional but recommended)* 30V/10A CC-CV bench PSU | £35–45 | UK Amazon for returns; doubles as FE-URT-1 servo-ID supply + B6neo DC input |
| *(Optional)* 3× 1Ω 100W aluminium-shell resistors (SBEC dummy load) | ~£12 | Skip if using the H4-bulb load |
| *(Alt. UBEC source)* 2× Hobbywing UBEC 25A HV from Wheelspin/3DXR | £124–130 | Faster + genuine-guaranteed vs AliExpress ~£105 |

---

## 4. Final ordering checklist

### ☐ AliExpress — cart fixes (do these on the open cart, before paying)
- [ ] 12-pack option text = **7.4V / 19.5kg / 1:345** — screenshot taken
- [ ] 6-pack option text = same variant **and FE-URT-1 explicitly included** — screenshot taken
- [ ] Both servo sellers messaged: horn + screws + 15cm cable per unit?
- [ ] 5V UBEC listing states 2–6S / DC 7–26V input
- [ ] B6neo store is SkyRC-branded (name "B6neo 2" = clone flag)
- [ ] PDB output pigtail gender checked in listing photos
- [ ] Wire kit confirmed true 14AWG
- [ ] XT60→4mm lead: removed (or consciously kept as future PSU lead)
- [ ] "2× 20A SBEC" search-term line **deleted** — replaced by A1 below

**Cart after fixes: ≈ £352**

### ☐ AliExpress — additions (same order, one shipping window)
- [ ] A1 — 2× Hobbywing UBEC 25A HV (£105–130) ← *the* critical buy
- [ ] A2 — 2× 5.5×2.1mm DC pigtails (£1–2)
- [ ] A3 — 10× XT30 pigtail pairs 16AWG (£3–6)
- [ ] A4 — XT90-S loop key w/ XT60 pigtails (£4–6)
- [ ] A5/A6 — 6× fuse holders + assortment w/ 10A & 30A spares (£7–11)
- [ ] A7 — settable LiPo alarm, will be set 3.5V/cell, unplugged when off (£2–3)
- [ ] A8 — 2× 30mm 5V fans, REQUIRED not optional (£2–5)
- [ ] A9 — H4 bulbs + holder, smoke stopper (£5)
- [ ] A10 — 2× 4700µF 25V (£1.50)
- [ ] A11 — 5264 cables: 6×30cm + 6×20cm + 4 spares (£5–8)
- [ ] A12 — 5264/5263 connector kit (£3–5)
- [ ] A13–A18 — solder/flux/wick, strippers+cutters, 3× XT60 pairs, battery strap, USB-C + micro-USB data cables, safety glasses (£17–36)
- [ ] A19–A22 — SN-28B, Dupont/JST kit (sensors only), wrist strap, resistor assortment (£15–21)
- [ ] A23–A26 — M2 kit(s), M3 + inserts + iron tip, calipers + hex drivers, 130A watt-meter (£27–43)
- [ ] A27 — ESP32 dev board CH340, REQUIRED (£4–8)
- [ ] A28 — threadlocker + sleeving + zip ties (£5–8)

**Additions subtotal: ≈ £200–245**

### ☐ UK buys
- [ ] Overlander 3350 3S 35C — **XT60 selected in dropdown** (£35)
- [ ] Ender 3 V3 SE (£149)
- [ ] PETG ×2 + TPU 95A ×1 (£35–45)
- [ ] Temp-controlled soldering iron (£25–40)
- [ ] *Optional:* bench PSU (£35–45) + dummy-load resistors (£12)

**UK subtotal: ≈ £245–270 (+£47–57 optional)**

### Running total
| Block | GBP |
|---|---|
| AliExpress cart (after fixes) | ~£352 |
| AliExpress additions | ~£200–245 |
| UK buys (core) | ~£245–270 |
| **Grand total** | **~£800–870** |
| Optional (bench PSU + resistor load) | +£47–57 |

### ☐ Before ANY servo sees power (costs nothing, ordered here so it's not forgotten)
- [ ] **Step 0:** SBECs powered off → DIP set 7.4V → power on with NO servos → multimeter each output, accept 7.2–7.5V only → tape/glue the switches
- [ ] V+ (middle) pin pulled from all six board-to-leg 5264 cables; multimeter continuity on V+ across every rail boundary reads **open**
- [ ] Board jack fed from rail A only — never 12V, never the raw pack
- [ ] Bank A = legs 1,3,5 / Bank B = legs 2,4,6 (a dead bank leaves a standing tripod instead of a sideways fall)
- [ ] Smoke stopper inline for every first connection of a new subcircuit
- [ ] During FE-URT-1 ID session: read protection registers on all 18 (expect addr 19 = 44, addr 13 = 70°C, addr 14 = 80, addr 35 = 200, addr 36 = 80); fix outliers; then hand-stall one servo and confirm torque drops within ~2s

---

# Part 2 — Connection & wiring plan

This is the wiring plan that survives the audit. The two non-negotiable rules that drive everything below:

1. **The Waveshare board's DC jack IS the servo-bus V+.** Its 6–12.6 V jack feeds the V+ pin of every servo port directly, and the board is rated **5 A max** — it can never carry leg current, and any 3-wire cable plugged into it joins that cable's V+ to the jack net.
2. **Rail A and Rail B must never share a V+ conductor anywhere** — not through the board, not through a leg-to-leg jumper. GND, by contrast, must be common **everywhere**.

---

## 1. Power tree

```
 Overlander 3S 3350 mAh 35C LiPo (12.6 V full / 10.5 V walk-stop / 9.9 V floor)
 [XT60 female on pack]        [JST-XH balance lead -> LV alarm, set 3.5 V/cell,
        |                      UNPLUG alarm whenever robot is off]
        | 12 AWG silicone
        v
 [XT90-S ANTI-SPARK LOOP KEY]        <-- needs XT60M->XT90F + XT90M->XT60F
        |                                adapter pair (~GBP 4-6) or a pre-made
        | 12 AWG                         XT90-S loop key with XT60 pigtails --
        v                                XT90 does NOT mate with XT60
 [30 A blade fuse, inline holder]    <-- mount within ~10 cm of the battery XT60
        |
        | 12 AWG
        v
 [Inline watt-meter, XT60, 130 A]    <-- your only ammeter; leave it in the trunk
        |
        v
 =====[PDB: XT60 in -> 8x XT30 out]=====   RAW 12.6 V BUS — nothing servo-side
   |XT30        |XT30            |XT30      connects here. If you put any cap on
   |(x2 chans   |(x2 chans       |          this side, it must be 25 V, not 16 V.
   | paralleled,| paralleled,    |
   | optional)  | optional)      | 16 AWG XT30-male pigtails (buy ~10 pairs,
   | 16 AWG     | 16 AWG         |          16 AWG, ~GBP 3-6 — NOT in cart yet)
   v            v                v
 [SBEC A]     [SBEC B]        [5V 5A UBEC]  (input must say 2-6S / DC 7-26 V)
 Hobbywing    Hobbywing          |
 UBEC 25A HV  UBEC 25A HV        +--5 V--> plain ESP32 dev board (sensor node)
 DIP = 7.4V   DIP = 7.4V         +--5 V--> ESP32-WROVER cam
 (set OFF-    (set OFF-          +--5 V--> SH1106 OLED, MPU6050, VL53L0X, 30 mm fan
  line, tape   line, tape           (second UBEC = spare)
  switches)    switches)
   |            |
   | 14 AWG trunk, <=30 cm       At each SBEC output screw terminal:
   |            |                2-3x 4700 uF 16 V caps (observe polarity!)
   v            v
 [RAIL A      [RAIL B
  manifold]    manifold]
  | | |        | | |
 [10A][10A][10A]  [10A][10A][10A]   <-- 6x inline blade-fuse holders, 10 A fuses
  | | |        | | |                    (5 A will nuisance-blow on a leg stall)
  16 AWG branches, each ending at a leg-root injection point
  with 1x 4700 uF 16 V cap at the root (12-15 caps total)
  v v v        v v v
 Leg1 Leg3 Leg5   Leg2 Leg4 Leg6    <-- MIX the tripods: A = legs 1,3,5;
                                        B = legs 2,4,6. A dead rail then leaves
                                        a standing tripod, not a one-sided flop.
   |
 RAIL A ONLY also feeds:
   +--14/16 AWG--> [5.5x2.1 mm male barrel pigtail] --> Waveshare board DC jack
                   (7.4 V is inside the board's 6-12.6 V window; NEVER feed the
                   jack 12 V or raw battery — the jack voltage lands on servo V+.
                   Barrel is CENTER-POSITIVE: multimeter it before first plug-in.
                   Pigtail ~GBP 1-2 — NOT in cart yet.)
```

**Load check on each edge:** battery trunk worst case ~35–43 A for ≤2 s (12 AWG + 30 A blade fuse rides it out, no nuisance blow); each SBEC input 13–16 A worst case (single XT30 = at its 15 A rating, hence the optional two-channel parallel); each SBEC output 22.5 A worst / ~6 A walking (25 A continuous rating covers it); each leg branch 7.5 A worst (16 AWG + 10 A fuse fine).

---

## 2. Signal topology

```
                    Mi 9 SE phone  (2.4 GHz hotspot = the single AP)
                    /            \
        WiFi (commands,           WiFi (MJPEG stream,
        <10 kbps, 500 ms          ~3 Mbps, independent)
        deadman)                     \
       /                              \
 [Waveshare Servo Driver ESP32]     [ESP32-WROVER cam]  (5 V from UBEC)
  - runs the ENTIRE 50 Hz IK/gait
    loop locally
  - servo UART: GPIO18 RX / GPIO19 TX,
    fixed 1,000,000 baud, half-duplex      [plain ESP32 dev board]  (5 V from UBEC)
  - NO spare GPIO exposed  <---UART or      - SH1106 OLED "eyes" via SPI (5-6 pins)
    (onboard I2C eaten by    ESP-NOW--->    - VL53L0X (I2C 0x29)
    its own 0.91" OLED)                     - MPU6050 (I2C 0x68) unless you later
                                              solder-tap the Waveshare I2C pads
   |port1              |port2
   | 30 cm 5264,       | 30 cm 5264,      ALL six inter-leg and board-to-leg
   | V+ PIN REMOVED    | V+ PIN REMOVED   cables: GND + Signal ONLY (middle
   v                   v                  V+ pin de-pinned). Power enters each
 Leg1 coxa           Leg2 coxa            leg ONLY at its root injection point.
   | 20 cm, full 3-wire |
   v                   v                  WITHIN a leg, full 3-wire is correct —
 Leg1 femur          Leg2 femur           that's how bus power reaches the femur
   | 20 cm, full 3-wire |                 and tibia from the root.
   v                   v
 Leg1 tibia          Leg2 tibia
   | 30 cm jumper,     | 30 cm jumper,
   | V+ REMOVED        | V+ REMOVED
   v                   v
 Leg3 coxa -> ... -> Leg5 (rail A chain)   Leg4 -> ... -> Leg6 (rail B chain)
```

- One 1 Mbps bus handles all 18 servos at 50 Hz with margin (sync-write ≈ 1.3 ms; sync-write + 6-servo rotating telemetry ≈ 5.7 ms per 20 ms tick). Do **not** split the data bus or buy a second driver.
- Bus tree = 19 nodes = exactly **18 cables**. Servos ship with one 15 cm cable each, which covers the 12 intra-leg hops only. **Buy: ~6× 30 cm + 6× 20 cm + 4 spares pre-made 5264 cables (~GBP 5–8)** — the spares get sacrificed for V+ de-pinning practice.
- Cable budget for V+ removal: 8 cables get the middle pin pulled (2 board→coxa + 4 leg→leg jumpers + 2 spares).
- I2C on the sensor node is conflict-free: MPU6050 0x68, VL53L0X 0x29, (Waveshare onboard OLED 0x3C). Keep I2C leads <20 cm at 100–400 kHz.
- Firmware deadman goes in from day 1: no valid command packet for 500 ms → freeze stance / crouch + torque-off. Poll all 18 IDs at ~10 Hz; a missed reply = a walked-out connector → halt and crouch.

---

## 3. Grounding rules

1. **One common ground for everything**: battery negative, PDB, both SBEC outputs, 5V UBEC output, Waveshare board, sensor-node ESP32, camera, every servo. The half-duplex TTL bus garbles or dies without a shared reference.
2. **"Isolated rails" means separate +V nets only. Never separate grounds.** You cut/de-pin only the **middle (V+) pin** of boundary cables — GND and Signal stay continuous end-to-end.
3. Grounds naturally common up through the PDB input side and the bus cables — that's fine and expected. Only V+ sharing between Rail A and Rail B (including through the board's copper) is forbidden.
4. Star-point mentality: the PDB is your ground hub; keep the 14 AWG trunk grounds back to it short, and don't daisy-chain leg power grounds leg-to-leg (power GND enters at each leg root alongside its V+).
5. Before every first power-up: **multimeter continuity, V+ between Rail A and Rail B must read OPEN; GND between any two points must read ~0 Ω.**

---

## 4. Assembly & wiring order (numbered — do it in this order)

**Tools referenced:** temp-controlled soldering iron + 63/37 0.8 mm solder + flux, wire strippers, flush cutters, SN-28B crimper, pin extractor (or a sewing needle), heat-shrink + lighter/iron, multimeter, safety glasses.

1. **Practice soldering first** (iron, solder, scrap of 16 AWG + a spare XT60 pair). Ten joints on scrap before any real joint. Wear the safety glasses; flux spits.
2. **Build the smoke stopper** (iron, heat-shrink): XT60 male pigtail + H4 55 W car bulb in series + XT60 female pigtail (~GBP 5). This limits any wiring mistake to ~4–5 A instead of the pack's 117 A. Use it for the *first* connection of every new subcircuit below.
3. **Set both SBEC DIP switches to 7.4 V — powered OFF, before anything else** (fingers only). On the Hobbywing 25A HV, switch 1 ON alone forces 8.4 V, which locks all 18 servos into over-voltage protection. After setting, don't touch until step 7.
4. **Battery trunk** (iron, strippers, heat-shrink): fuse holder → loop-key adapters → watt-meter → PDB, all 12 AWG. **Classic mistake:** never strip/solder both battery leads at once — one lead fully finished and insulated before the other is touched. A 3S dead short vaporises tools.
5. **SBEC + UBEC input pigtails** (iron or SN-28B): XT30 male pigtails in 16 AWG onto both SBEC inputs and the UBEC input. Check the PDB listing's actual output gender first. Optional but cheap: two paralleled XT30 channels per SBEC input.
6. **No-load voltage verification** (multimeter — this is step 0 of bring-up): battery → smoke stopper → PDB → one SBEC at a time, **nothing on the outputs**. Accept only **7.2–7.5 V**. Then the UBEC: accept 4.9–5.2 V. Then hot-glue/tape the DIP switches and jumpers. *Never change a DIP switch with the SBEC powered.*
7. **Barrel pigtail** (iron, multimeter): wire the 5.5×2.1 mm pigtail to Rail A. **Verify centre pin = +7.4 V with the multimeter before it ever meets the Waveshare board.** Reversed barrel polarity is the #1 board-killer.
8. **Servo ID + register session** (FE-URT-1, PC, one servo at a time — all ship as ID 1): power the FE-URT-1's servo terminal from Rail A (via smoke stopper the first time). Assign IDs 1–18, and on each servo *read* the protection registers (addr 19 expect 44, addr 28 expect ~500, addr 35 expect 200, addr 13 expect 70, addr 14 expect 80 — leave 14 at 8.0 V). Fix outliers (unlock addr 55, write, re-lock). Then stall-test ONE servo by hand: torque should drop to ~20 % within ~2 s.
9. **Rail manifolds** (iron, SN-28B, heat-shrink): per rail — 14 AWG trunk from SBEC output, three 10 A blade-fuse holders, 16 AWG branches, 5264 tails at the leg roots (crimp 5263 terminals with the SN-28B, or solder-splice into pre-made cables — easier for a first-timer). Solder the 4700 µF caps at the SBEC screw terminals and leg roots. **Electrolytic caps are polarised — stripe = negative; a reversed cap vents violently.**
10. **De-pin V+ on the 8 boundary cables** (pin extractor): lift the plastic latch on the 5264 housing, withdraw the **middle** pin, tape it back along the cable (reversible). Practice on the 2 sacrificial spares first.
11. **Full continuity audit** (multimeter, battery disconnected): V+ Rail A↔Rail B = OPEN; V+ Rail A↔board jack net = continuous (that's intended); V+ Rail B↔board = OPEN; GND everywhere = continuous; no V+↔GND short on either rail.
12. **First integrated power-up** (smoke stopper inline, watt-meter visible, loop key in reach): Rail A + board + ONE leg only, torque-off. Then torque-on, jog one joint from the Waveshare web UI (192.168.4.1). Then add legs one at a time. Only after all six behave does the smoke stopper come out.
13. **Firmware safety before first stand:** 500 ms deadman → crouch + torque-off; 10 Hz all-ID poll watchdog; torque-off belly-rest as the default idle pose (standing torqued burns ~32 W — half of walking — "hours idle" only exists torque-off).
14. **After final assembly:** hot-glue/tape-wrap every inter-servo 5264 (they have no positive lock and walk out under gait vibration), strain-relieve at every joint crossing, strap the battery, zip-tie the harness.

---

## 5. Connector & pinout reference

| Connector | Where | Pinout / polarity | Ratings & gotchas |
|---|---|---|---|
| **Molex 5264-3P** (2.50 mm) | Servo bus, all 18 servos + board ports | **Pin 1 = GND, Pin 2 = V+ (middle), Pin 3 = Signal.** Pin 1 marked by triangle/chamfer on housing | 3 A/pin — why leg power must inject at roots, not chain leg-to-leg. Terminals = Molex **5263** (SN-28B crimps them). **JST-XH and Dupont do NOT mate with this** — the Dupont/JST kit is for sensors only |
| Servo wire colours | Feetech pigtails | Typically **black = GND, red = V+, white/yellow = Signal** — but clone cables vary; confirm against the pin-1 mark with the multimeter before trusting colour | Each servo has two internally-paralleled ports (daisy-chain pass-through, including V+) |
| **XT60** (yellow) | Battery, fuse, watt-meter, PDB in | **Female (socket) = power source; male (pins) = load.** "+"/"−" moulded into the shell — match them, the housings only mate one way | 30 A cont. Battery ships female |
| **XT30** (small) | PDB outputs → SBEC/UBEC inputs | Same convention: female = source (PDB side), male = load pigtail | **15 A cont / 30 A burst** — SBEC input worst case is 13–16 A, hence optional channel-paralleling |
| **XT90-S** (green end) | Anti-spark loop key in battery trunk | Anti-spark resistor is in the "S" version only — don't substitute plain XT90 | Mechanically incompatible with XT60: needs the adapter pair from §1 |
| **5.5×2.1 mm barrel** | Waveshare DC jack | **Centre = positive.** Verify with multimeter before first insertion | Jack net = servo-bus V+ = board logic supply. Feed 7.4 V from Rail A only; 12 V here reaches every servo |
| **JST-XH 4-pin balance** | Pack → charger / LV alarm | Pin 1 = pack negative, then cell taps in order | Alarm draws 3–10 mA continuously from cells 1–2 — **unplug it when the robot is off** or it kills the pack in days |

**Still-missing wiring parts this plan consumes (add before checkout):** 5.5×2.1 mm male barrel pigtail (GBP 1–2) · ~10× XT30 male pigtail pairs 16 AWG (GBP 3–6) · XT60↔XT90 adapter pair (GBP 4–6) · Molex 5264 housing + 5263 terminal kit (GBP 3–5) + pin extractor · 5264 cables 6× 30 cm + 6× 20 cm + 4 spares (GBP 5–8) · H4 bulb + holder (GBP 5) · 6× inline blade-fuse holders + 10 A fuses · solder/flux/strippers/flush cutters/heat-shrink (GBP 20–35) · plain ESP32 dev board (GBP 4–8, required — the Waveshare board has zero spare GPIO).

---

# Part 3 — Bench test & benchmark protocol (before final wiring)

Run these tests **in this order**. Each test gates the next: do not skip forward, because every stage assumes the previous one passed. Total bench time is roughly two evenings plus one charge cycle. Your only owned test gear is a multimeter — the list below adds ~£25–35 of cheap kit that makes the difference between "it smoked and I don't know why" and a controlled bring-up.

## Minimum test kit (buy with the main order)

| Item | Why | Cost |
|---|---|---|
| Multimeter (owned) | Every polarity/voltage/continuity check below | £0 |
| Inline watt-meter, 130A XT60 (already on to-add list) | Current/energy measurement for SBEC soak, first power-up, runtime benchmark | ~£8 |
| 4x H4 60/55W halogen car bulbs + 2 bulb holders | SBEC dummy load (~24.6A with both filaments wired) AND one bulb doubles as the smoke-stopper | ~£12 |
| 1x extra XT60 male + female pigtail pair (16AWG) | Build the smoke-stopper lead (bulb in series with the supply) | ~£2 |
| Settable LiPo low-voltage alarm (1–8S, per-cell display) | Set 3.5V/cell; walk-stop indicator during runtime test | ~£3 |
| 2x 5A blade fuses | Temporarily replace the 30A main fuse during commissioning (300x margin → 30x) | ~£1 |
| USB data cable matching the FE-URT-1 connector (check the listing photo — micro-USB vs USB-C varies by revision) | ID assignment; a charge-only cable will waste an evening | ~£2 |
| Windows PC | Feetech FD software is Windows-only, free from feetechrc.com/software.html | £0 |
| Safety glasses + fireproof LiPo bag (bag already in cart) | All powered tests | ~£3 |
| *Optional but strongly recommended:* 30V/10A CC-CV bench PSU | Current-limited first power of every subcircuit; doubles as B6neo DC input and FE-URT-1 servo supply | £35–45 |

No IR thermometer needed: the STS3215 reports its own internal temperature over the bus — you will use that telemetry as your thermometer from test T7 onward.

---

## T0 — Unbox inspection (nothing powered)

**Purpose:** catch wrong-variant servos and missing accessories while the AliExpress dispute window is open.

**Procedure:**
1. Count 18 servos. Check the label/listing on **every unit** reads the 7.4V variant: **"7.4V / 19.5kg.cm / 1:345"** (C001-class), *not* 12V/30kg (C018) and *not* the fast-gear 1:191 / 1:147 versions (those deliver only ~10.8 / ~8.3 kg·cm — build-killers). Screenshot the option text you ordered against what arrived.
2. Confirm per-servo contents: 1x disc horn (or horn bag), horn screw (M3x6), mounting screw bag, 1x ~15cm 3-pin cable. Confirm the FE-URT-1 is physically in the 6-pack box.
3. Spin each output shaft gently by hand through its travel — it should feel like smooth, heavy gear drag, identical across all 18. Note any gritty/clicking unit.
4. Check the SBECs' voltage selector (DIP switch or jumper) position **as shipped** — do not assume 7.4V.

**PASS:** 18/18 servos labelled 7.4V 19.5kg 1:345; FE-URT-1 present; ≥1 horn + cable per servo.
**FAIL:** open an AliExpress dispute immediately with photos. Do not "make do" with a 12V or fast-gear unit mixed into the fleet.

---

## T1 — Battery + charger verification (first charge)

**Purpose:** prove the B6neo charges at 1C from your USB-C PD brick, and baseline the pack.

**Setup:** B6neo fed from your 100W PD charger **using the 5A e-marked USB-C cable that came with it** (a generic 3A cable silently caps input at 60W — still enough, but know why). Pack in the fireproof bag on a hard surface, balance lead connected, you present the whole time.

**Procedure:**
1. Measure pack voltage per cell via the charger's display (or multimeter on the balance lead: each cell 3.7–3.85V as shipped).
2. Balance-charge LiPo mode, 3S, **3.3A (1C)**. Charge power needed is 12.6V x 3.35A / 0.9 ≈ **47W**, well inside the 80W PD ceiling.
3. Record time and final per-cell voltages.

**PASS:** charger negotiates PD and sustains ~3.3A; all three cells finish at 4.19–4.20V within ±0.01V of each other; full charge from storage in ≤90 min.
**FAIL:** cells won't balance within 0.03V after a long CV tail → pack fault, return it. Charger won't negotiate >60W → swap cable. Charger doesn't match SkyRC B6neo spec behaviour at all → clone; dispute.

---

## T2 — Dead checks: PDB, fuses, polarity (multimeter only, no battery)

**Purpose:** every downstream test trusts this wiring. Nothing expensive touches power until this passes.

**Procedure (battery NOT connected at any point):**
1. **Fuse holders:** continuity across the 30A main holder with fuse seated (<0.5Ω, effectively beep); open with fuse removed.
2. **PDB polarity:** continuity from XT60 input **+** pin to each of the 8 XT30 output **+** pins; same for −. Then confirm **no** continuity (+ to −) anywhere: resistance should read >1MΩ / open on every port pair.
3. **Every lead you crimp or solder** (SBEC input pigtails, smoke-stopper, barrel-jack pigtail for the Waveshare board): polarity check against the connector datasheet gender/pin convention, then a firm tug test on each joint.
4. **Barrel pigtail:** centre pin = **+** (Waveshare jack is centre-positive). Verify with continuity before it ever meets the board.

**PASS:** 0 polarity errors, 0 short-circuit beeps, every crimp survives a tug.
**FAIL:** re-make the joint. Never "note it and fix later" — a reversed XT30 pigtail is the single most likely way to kill a £62 SBEC.

---

## T3 — SBEC output set + no-load verify (step 0 of all powered work)

**Purpose:** both regulators can be mis-set to 8.4V+ with one switch — above the servos' 7.4V rated ceiling and (at 8.4V+) into fleet-wide protection lockout. This is the highest-value 5 minutes in the whole protocol.

**Setup:** one SBEC at a time. Input from battery **through the 30A fuse and watt-meter**, with a **5A fuse temporarily substituted** in the main holder. **No servos, no load connected.**

**Procedure:**
1. With the SBEC **unpowered**, set the DIP/jumper to 7.4V (Hobbywing 25A HV: switch 2 ON, switches 1 and 3 OFF — switch 1 ON alone forces 8.4V regardless of the others).
2. Power up. Multimeter on the output.
3. Repeat for the second unit.
4. Tape or hot-glue the switches in place. Label each unit "RAIL A" / "RAIL B".

**PASS:** output **7.2–7.5V** on both units. Anything from 7.5–8.0V is the silent danger band (over servo rating, below the 8.0V protection trip) — that's a FAIL too.
**FAIL:** re-check switch positions powered-off; if a unit can't be brought into 7.2–7.5V, return it. Do not proceed with one good rail.

---

## T4 — SBEC load soak (one unit at a time)

**Purpose:** prove each regulator holds voltage at real current before 9 servos depend on it. Note: the old "bench-test at 40A" instruction in the docs is not executable — 40A through one unit is 2x overload, and a 10–15 min hold would need 4.7–7Ah from a 2.68Ah-usable pack. The correct test is per-unit.

**Setup:** dummy load = **4x H4 bulbs with both filaments wired, in parallel** (~6.15A each at 7.4V → **~24.6A total**; use 2–3 bulbs ≈ 12–18A if you bought the 25A Hobbywings and want margin, all 4 if testing to the rating). Alternative: 3x 1Ω 100W aluminium resistors in parallel (0.33Ω → 22.2A, 55W each — bolt to a metal plate). SBEC mounted on an aluminium plate **with the 30mm fan fitted as it will fly**. Watt-meter between battery and SBEC input. Full 30A fuse back in.

**Procedure:**
1. Connect load, power up, start a timer.
2. Log every minute: output voltage (multimeter), input current/watts (watt-meter).
3. Soak **5–8 min** (the 3350 pack sustains ~14.8A input for ~10.9 min — stop at 3.7V/cell).
4. Finger-test the case at the end (brief touch).
5. Repeat for unit 2 on a recharged or partially rested pack.

**PASS:** output **≥7.2V for the entire soak** at ≥20A load; case touchable for 2+ seconds (≲60°C); no shutdown, no oscillation/flicker of the bulbs.
**FAIL:** voltage folds back or unit thermally cuts → it cannot survive a 9-servo stall event (22.5A for 2s); return/replace with a genuine 25A-continuous unit. If it only fails without the fan, the fan is now officially REQUIRED, not optional.

---

## T5 — UBEC test (5V logic/accessory rail)

**Purpose:** verify the cheap 5V 5A UBEC before the camera/OLED/sensors trust it. Reminder: this rail does **not** feed the Waveshare board (its jack needs 6–12.6V and comes from Rail A).

**Setup:** UBEC input from the battery via the PDB. Load: one H4 bulb single 55W filament ≈ 2.5–3A at 5V, or the ESP32-WROVER cam board streaming (its worst-case draw ~0.5A) plus the bulb.

**Procedure:** power up, measure output at no load, then under ~3A load for 5 min.

**PASS:** **4.9–5.2V** at no load AND under 3A; no visible flicker.
**FAIL:** sags below 4.75V under load → it's a 2S-max mini-BEC mislabelled 5A; use the second (spare) unit, and if both fail, buy a Hobbywing UBEC-10A class part before flying sensors on it.

---

## T6 — Servo ID assignment + individual test of all 18 (FE-URT-1)

**Purpose:** all servos ship as ID 1, so they must be commissioned **one at a time**; this is also the moment to verify protection registers on every unit — the free insurance that stops a stalled servo cooking itself.

**Setup:** FE-URT-1 on the Windows PC (FD software installed). Servo power into the FE-URT-1's power terminals from **Rail A's now-tested SBEC** (or bench PSU at 7.4V, 1A limit, if bought). Keep the 5A fuse in the main holder for this whole session. One servo connected at a time, **no horn fitted, no load**.

**Procedure per servo (about 3 min each; do all 18 in one or two sittings):**
1. Connect, scan, confirm it answers at its current ID.
2. Assign new ID (1–18; write it on masking tape on the servo body immediately — decide your leg-numbering map first, e.g. leg 1 coxa/femur/tibia = 1/2/3).
3. Jog it through full travel from the software; watch for smooth motion, no grinding.
4. Read current: no-load running should be ~**150mA**, static idle ~**21mA**.
5. **Read the protection registers and verify factory defaults** (unlock EEPROM addr 55 only if you need to fix an outlier, re-lock after): addr 13 = 70 (°C), addr 14 = 80 (8.0V — leave it, do NOT raise), addr 19 = 44 (unload on overload+current+temp), addr 28 ≈ 500, addr 34 = 20, addr 35 = 200 (2s), addr 36 = 80 (%).
6. On **one** sacrificial servo only: fit a horn, command a position, grip the horn firmly by hand for >2s. Confirm torque drops to ~20% within ~2s and recovers on the next position command.

**PASS:** 18/18 respond, jog smoothly, draw ≤200mA no-load; registers match defaults (or were corrected); stall test unloads in ≤2.5s.
**FAIL:** a servo that draws >300mA no-load, grinds, or won't take an ID → photograph, set aside, dispute. A register dump showing addr 14 = 140 (14.0V) means you received a 12V-variant unit — that's a T0-level FAIL, dispute the pack.

---

## T7 — Harness V+ isolation check (multimeter, before any multi-rail power)

**Purpose:** the single most dangerous latent fault in this build — Rail A and Rail B being invisibly joined through the bus cables' V+ pins or the Waveshare board's common V+ plane. Every 3-pin cable carries power, and the board's DC jack IS the servo-port V+.

**Setup:** full harness assembled per the wiring plan (V+ pin lifted/de-pinned on all six board-to-leg cables and any A↔B jumper; power injected at leg roots only). **Battery disconnected.**

**Procedure:**
1. Continuity from Rail A's SBEC output **+** to Rail B's SBEC output **+**: must read **OPEN** (>1MΩ).
2. Continuity from the Waveshare barrel jack **+** to Rail B **+**: **OPEN**.
3. Continuity from the Waveshare barrel jack **+** to Rail A **+**: **CLOSED** (that's the leg-root injection + board feed sharing Rail A — correct).
4. Ground continuity: battery −, Rail A −, Rail B −, board GND, every leg GND — **all CLOSED** (common ground is mandatory or the serial bus will garble).

**PASS:** exactly the pattern above: A+↔B+ open, all grounds common.
**FAIL:** any A+↔B+ beep → find the un-lifted V+ pin (it's in a 3-pin cable crossing a rail boundary, or both banks plugged into the board's two internally-connected ports). Fix before ANY power. This fault doesn't announce itself — it silently overloads one SBEC through 3A-rated connector pins.

---

## T8 — First power-up, current-limited (smoke stopper)

**Purpose:** the first time the full harness goes live, a stray wire strand faces a pack that can source 117A; the 30A fuse takes seconds to act. An H4 bulb in series limits any dead short to ~4–5A and glows as a visual alarm.

**Setup:** smoke-stopper lead (XT60 male → H4 bulb 55W filament → XT60 female) between battery and the main fuse. Watt-meter inline. All servos connected, **torque off** (no commands). Loop key/disconnect within arm's reach.

**Procedure:**
1. Connect. The bulb may flash briefly (capacitor inrush into the 4700µF bank) then go **dark**.
2. Check rails: Rail A and Rail B each 7.2–7.5V *(note: through the bulb the pack side sags — check rail voltage, not pack)*; 5V rail 4.9–5.2V; Waveshare board boots (its ESP32_DEV hotspot appears).
3. Idle current on the watt-meter: 18 torque-off servos ≈ 18 x 21mA + board + sensors ≈ **0.5–0.8A total**.
4. Enable torque on ONE servo via the web UI; jog it. Bulb stays dark.
5. Remove the smoke stopper, connect directly, repeat steps 2–3.

**PASS:** bulb dark at idle; idle draw ≤1.0A; both rails in band with servos attached.
**FAIL (bulb glows steadily):** dead or partial short — disconnect within 5 seconds, go back to T2/T7 with the multimeter. The bulb just saved you the cost of a harness.

---

## T9 — Single-leg testbed benchmark (torque / current / temperature)

**Purpose:** verify one fully-built leg against the numbers the whole design rests on, before printing/assembling five more. This is where the "19.5 kg·cm" marketing meets the 5 kg·cm continuous reality.

**Setup:** one complete leg (coxa+femur+tibia) bolted to a clamped plate or weighted base. Rail A power via leg-root injection, 10A blade fuse in that leg's holder. Watt-meter on the rail. A known mass: a 800g water bottle (800ml) strapped at the foot.

**Procedure:**
1. Command the leg to a **foot-under-knee stance** (femur moment arm ≈ 7cm). Load with the 800g mass. This simulates one tripod-stance leg of a 2.4kg robot: 0.8kg x 7cm = **5.6 kg·cm** on the femur.
2. Hold 10 minutes. Poll femur servo telemetry every 60s: current and temperature registers.
3. Repeat briefly (60s only) at an extended ~10–11cm reach to see the overload region approach — watch current climb toward 1.3–1.4A.
4. Run a continuous step cycle (lift/place, ~1Hz) for 10 min at the 7cm geometry; log peak current and end temperature.

**PASS (10-min hold at 7cm):** femur current **0.6–0.85A** (theory: 5.6/7.8 + idle ≈ 0.74A); temperature **<55°C** and plateauing (cutoff is 70°C); no protection trips; no visible flex/cracking at the printed servo pockets.
**FAIL:** current >1.0A at the 7cm pose → your moment arm is longer than you think or the frame binds — fix geometry before printing more legs. Temperature still climbing past 60°C at 10 min → the bracket needs vent openings (≥50% case exposure) before you commit to six. Protection trip during the step cycle → re-check registers (T6) and geometry.

---

## T10 — Full 18-servo bus integrity test

**Purpose:** prove the single 1Mbps bus runs the whole fleet with telemetry before writing gait code against it.

**Setup:** all 18 servos ID'd, all six legs connected in the final harness topology, robot **on a stand with feet off the ground** (no load). Both rails live.

**Procedure:**
1. Scan the bus from the Waveshare firmware: enumerate IDs 1–18.
2. Sync-write a neutral pose to all 18 simultaneously (SyncWrite 0x83). All servos must move together.
3. Run a telemetry sweep loop: read position/current/temp from all 18 continuously for 5 minutes; count missed replies. (Full sweep costs ~14ms, so a 20Hz poll is comfortable.)
4. While polling, wiggle each leg's cabling gently at every connector — a marginal 5264 crimp shows up as a burst of missed replies from all IDs downstream of it.
5. Sync-write a slow all-leg wave motion for 5 min; watch rail voltages on the multimeter.

**PASS:** 18/18 found; **0 missed replies** during static polling; ≤0.1% missed during the wiggle test with no repeatable dropout point; rails stay ≥7.2V during unloaded motion.
**FAIL:** repeatable dropout at one connector → re-crimp/replace that cable and hot-glue-secure it (do this for all inter-servo connectors at final assembly anyway). Whole-bus garbling → a ground path is missing somewhere (back to T7 step 4).

---

## T11 — Runtime benchmark (the last test before real walking)

**Purpose:** replace the docs' guesses with your measured number. Expectations from corrected math: **~30 min walking (~48W rail), ~48 min standing torque-on (~32W), 5+ hours in torque-off sit (~5W)** on the 3350mAh pack.

**Setup:** full robot, fresh-charged pack, watt-meter inline, low-voltage alarm plugged in and **set to 3.5V/cell**, soft surface, open floor.

**Procedure:**
1. Log watt-meter Wh and A at: torque-off sit (2 min), stand torque-on (5 min), continuous slow tripod walk (10 min).
2. Extrapolate runtime to the 3.5V/cell alarm from measured average watts: usable energy ≈ 26.8Wh at the rail.
3. Continue walking until the alarm sounds; note actual elapsed powered time.
4. **Unplug the alarm** when done (it drains cells 1–2 at 3–10mA continuously and will wreck the pack in days if left on).
5. Poll all 18 servo temperatures immediately after the walk.

**PASS:** measured walking draw **35–65W rail-side**; alarm-to-alarm powered time **≥25 min** mixed use; hottest servo **<65°C** at end of run; pack cells within 0.05V of each other after recharge.
**FAIL:** draw >70W walking → gait geometry is over-reaching (feet too far out — pull them under the knees, see T9); a servo >65°C → its bracket needs ventilation or that joint's geometry is overloaded; runtime <15 min → measure standing draw and check you implemented the torque-off idle pose in firmware — standing torque-on is half your power bill.

---

**Golden rules across all tests:** one new variable per power-up; the loop key or smoke-stopper within reach whenever the pack is connected; log every number (voltage, current, temperature, minutes) — week-one measurements are what you'll tune the gait, fusing, and runtime claims against.

---

# Part 4 — Gaps the panel almost missed

Eight late findings, each resolved to a concrete action. Everything load-bearing below was re-checked against primary sources on 2026-07-02; where a number could NOT be independently verified it is explicitly flagged. New buy lines introduced here: **A29 (spare servos)** and **A30 (nothing — A22 is deleted, see 4.5)**.

---

## 4.1 Part 0: the mechanical plan (the missing chapter)

**Confirmed by fresh web check: no open-source hexapod exists designed around the STS3215.** The closest projects are [PCrnjak/3D-printed-Hexapod](https://github.com/PCrnjak/3D-printed-Hexapod) (18 micro servos), [rookidroid/hexapod](https://github.com/rookidroid/hexapod) (18× MG92B PWM servos, ESP32 or Pico, GPL-3.0), [Aecerts_Hexapod_V1](https://github.com/Ryan-Mirch/Aecerts_Hexapod_V1) (RC-size PWM servos, self-described "messy WIP"), and [ArachnoBot](https://github.com/robs-tech-workbench/hexapod_spiderbot_model). None have STS3215 pockets. You will be re-modelling servo pockets no matter what. Plan for it.

**The plan:**

1. **Geometry donor + code donor: rookidroid/hexapod.** It is the only candidate that is ESP32-native, GPL-3.0 licensed, includes firmware with a web calibration UI, and has a complete 18-DOF leg layout. You keep its leg geometry and linkage proportions and re-model every servo pocket from MG92B size to STS3215 size. Keep Aecerts V1 open in a second tab as a reference for how full-size-servo brackets look.
2. **Measure, don't trust.** Nominal STS3215 case is ~45 × 25 × 35 mm with M2 mounting holes, but the Waveshare wiki blocked automated verification of exact dimensions — so the rule is: **when the servo box arrives (T0 day), measure one servo with the calipers (A-list item) and model the pocket from YOUR numbers**, with 0.2–0.3 mm clearance per face for PETG shrinkage.
3. **CAD tool: Onshape Free** (browser-based, zero install, free tier requires public documents — fine for a hobby robot) or Fusion 360 Personal (free hobby licence, 10-editable-document cap). If you have never CADed: Onshape's own learning path takes ~6–10 hours; budget week 1 evenings for it. This is not optional — there is no downloadable frame.
4. **Leg dimension targets** (already implied by the torque math elsewhere in this doc — keep them): coxa offset ~4–5 cm, femur ~7 cm effective arm, tibia ~10 cm, mid-stance foot reach ≤ 11–12 cm from the coxa axis. Longer legs = more torque demand; the 2.24× stall-margin math in Part 1 assumed a 7 cm femur arm.
5. **Idler-side support:** every joint must be bridged across BOTH faces of the servo — output horn on one side, an idler on the case back on the other. Feetech multi-packs typically include horns + screws; **at T0, inventory what's actually in the box** and if there is no back-side idler hardware, design a printed boss riding a printed pin (acceptable at this torque) or add M3 bearing + shoulder bolt to the UK order.
6. **Print budget (arithmetic):** one leg ≈ 3 brackets + femur + tibia ≈ 150–250 g PETG ≈ 10–15 h at 0.2 mm layers. 6 legs + 2 chassis plates ≈ 60–80 h total, ~1.2–1.6 kg of filament including supports and failed prints — buy 2× 1 kg PETG spools, not 1. The ≤650 g frame budget from Part 1 is the *installed* weight, not the *printed* weight.
7. **Printer commissioning is a week-1 task** (parcels are still shipping): bed level → PETG temperature tower (230–250 °C) → print ONE test servo pocket (1–2 h print) → check fit when servos arrive.
8. **Hard rule: print one complete leg, pass T9 with it, THEN print the other five.** A pocket error found after 6 legs costs 50+ hours; found after 1 leg it costs 10.

## 4.2 The software plan (nobody has written the 50 Hz loop)

Verified: the stock firmware at [github.com/waveshare/Servo-Driver-with-ESP32](https://github.com/waveshare/Servo-Driver-with-ESP32) is literally described as "the Web app example" — a WiFi jog demo bundling Waveshare's SCServo library. There is no gait engine, no IK, no watchdog. You are writing those. Milestone ladder:

- **Toolchain (week 1, before any hardware):** Arduino IDE 2.x + ESP32 board package + clone the Waveshare repo (its bundled SCServo library is your serial-bus driver — SyncWrite is protocol instruction 131 = 0x83, confirmed in the [STS register map](https://raw.githubusercontent.com/Mickael-Roger/python-st3215/main/st3215/values.py)).
- **M0** — flash the stock web demo, jog ONE servo from the phone browser. (This is also the dependency for T8 step 4.)
- **M1** — SyncWrite (0x83) a neutral pose to all 18 IDs at 1 Mbps; verify all 18 respond to a ping sweep.
- **M2** — single-leg IK (port the math from [mithi/hexapod-kinematics-library](https://github.com/mithi/hexapod-kinematics-library) — it is a clean, tested kinematics-only codebase; rookidroid's firmware shows the same math already living on an ESP32).
- **M3** — open-loop tripod gait, robot on a stand.
- **M4** — safety layer: 500 ms command deadman, 10 Hz 18-ID poll watchdog, torque-off crouch idle. **M4 ships before the robot ever stands on the floor.**
- **M5** — phone teleop: the ESP32 serves a WebSocket + joystick page (extend the stock web app); SensorServer remains inbound-sensing only.
- **IMU decision, resolved:** balance control is **deferred to phase 2**. Phase 1 gait is open-loop and needs no IMU. When phase 2 comes, the sensor-node ESP32 streams filtered pitch/roll over UART to the driver board at 50 Hz (one `P,<pitch>,<roll>\n` line per tick ≈ 20 bytes ≈ 2 ms at 115200 baud — latency is a non-issue). Do not let IMU plumbing block walking.

## 4.3 Spare servos — line A29

Arithmetic: 12 + 6 = 18 servos ordered for 18 joints = **zero spares** protecting a £162.93 + £95.79 = **£258.72 fleet** and the whole schedule. Unit price £162.93 ÷ 12 = **£13.58**.

**A29: add 2× STS3215, same 7.4 V / 19.5 kg·cm / 1:345 option text, same seller, same order ≈ £27.16.** Same batch matters: mixed firmware revisions have different register defaults (see 4.8). Designate spare #1 as the sacrificial unit for T6's hand-stall test and T9's thermal-abuse soak so the flight 18 are never deliberately stressed. Bonus: two spares double as a source of spare horns, screws, and 15 cm cables.

## 4.4 One topology, stated once (resolving the Part 1 / Part 2 contradiction)

**Standard is the Part 2 daisy-chain** — it matches the board's two physical ports: port 1 → leg 1 → leg 3 → leg 5, port 2 → leg 2 → leg 4 → leg 6. Part 1 risk #2 and T7's wording "all six board-to-leg cables" is hereby corrected everywhere to: **"the six rail-boundary cables"**.

- **De-pin count (final): 2 board→coxa + 4 leg-to-leg jumpers = 6 live cables get the middle V+ pin lifted, plus 2 spares de-pinned first as practice. Total 8.** Signal and GND pass through every cable; V+ never crosses a rail boundary — each leg's servos get power ONLY from their own leg's fused injection point.
- **Cable allocation (A11 = 6× 30 cm + 6× 20 cm + 4 spares; packs include 12× 15 cm):** 30 cm → board→coxa runs (2 used, 4 spare); 20 cm → the 4 leg-to-leg jumpers (4 used, 2 spare); included 15 cm → all 12 intra-leg coxa→femur and femur→tibia hops. Nothing is jobless, and the two spare 20 cm cables are the de-pin practice pair.
- **Grounding rule 4, clarified:** it applies to **power** grounds only — never return leg *power* current through another leg; every injection point's GND goes to the PDB star. The **signal-cable** GND pin daisy-chaining leg-to-leg is not only fine, it is required (it's the serial reference). Two different grounds, two different rules.

## 4.5 Brain-death and rail monitoring (and deleting A22)

The "dead rail leaves a standing tripod" claim is only true if Rail B dies. If **Rail A** dies, the board dies with it, and Rail B's 9 servos hold their last torque command with no deadman alive to release them. Resolutions:

1. **Free rail monitoring already exists — use the servos.** Verified against the STS register map: **register 62 = present input voltage** (RAM, read-only, units of 0.1 V), alongside 63 = temperature and 69/70 = present current ([source](https://raw.githubusercontent.com/Mickael-Roger/python-st3215/main/st3215/values.py)). Every servo is a voltmeter on its own rail. Fold reg 62 into the existing 10 Hz watchdog poll: **any servo on either bank reading < 68 (= 6.8 V) → torque-off ALL 18 + crouch + halt gait.** At healthy 7.4 V the register reads ≈ 74. This costs zero parts and zero pins.
2. **A22 rail-sense dividers: DELETE.** Part 1 risk #8 already established the driver board has no spare GPIO, and item 1 above makes the dividers redundant. (If you later want pack-level pre-fuse voltage on the sensor node, its ESP32 has free ADC pins — but the LiPo low-voltage alarm already covers that.)
3. **Rail-A brain death itself:** the honest mitigation at this budget is procedural, not electronic — **the XT90-S loop key lives within arm's reach during every powered session, and the standing rule is "anything unexplained → pull the key first, diagnose second."** Optionally add a 2-diode OR (two 5 A Schottky, e.g. SS54, ~£1) feeding the board from both rails — but the ~0.35 V Schottky drop puts board input at ~7.05 V, and the board's minimum input spec could not be verified this session (Waveshare wiki blocked automated fetch), so **bench-test the diode-OR at T8 before trusting it**, or skip it.
4. **Add one test, T7b (2 min): brain-death drill.** Robot on the stand, gait running, pull Rail A's blade fuse. Observe: Rail B servos freeze holding torque, web UI dies. Recover with the loop key. Now you have *seen* the failure mode before the robot is on the floor.

## 4.6 The first three weeks (sequencing against real lead times)

AliExpress lines land in 1–4 weeks, staggered per seller; UK lines land in days. Hidden deadline, verified: **AliExpress buyer protection runs 15 days after the order is marked received** ([AliExpress help](https://www.aliexpress.com/buyerprotection/how_do_i_open_a_dispute.html)) — so servo inspection cannot wait for the rest of the harness.

| When | Do | Needs only |
|---|---|---|
| **Week 1** (UK parcels) | Printer commissioning + PETG temp tower + test pocket print; Onshape leg CAD started; soldering practice on scrap wire (30+ joints before any real one); install FD software + USB-serial driver on Windows; T1 first balance charge → **immediately to storage mode** (see 4.7) | Printer, filament, iron, laptop, LiPo, B6neo |
| **Servo box arrival day** | **T0 same day**: count 18 (+2 spares), variant label photos archived; measure one case with calipers → finalise CAD pockets | Calipers, camera |
| **Within 15-day window** | **T6 full register dump + ID assignment on all 20 units** — T6 needs ONLY the FE-URT-1 + a 7.4 V source. If the SBECs haven't landed, power it from the **storage-charged LiPo (2 × 3.85 V = 7.7 V)** through the 30 A inline fuse. Do NOT wait for the PDB. A 12 V unit masquerading as 7.4 V must be caught while a dispute is still possible. | FE-URT-1, LiPo, fuse, laptop |
| **SBEC arrival week** | T3/T4 bench tests same week; T7 harness build | SBECs, PDB, connectors |
| **Anytime, parallel** | Print leg 1 → T9 | Printer only |

Blocked-by map: T0/T6 ← servo parcel. T3/T4 ← SBEC parcel. T7 ← PDB + connector + crimp-tool parcels. T9 ← leg print + one servo. T1 ← nothing (UK). The failure mode this table prevents: boxes pile up for three weeks, the dispute window lapses, everything gets attempted in one chaotic weekend.

## 4.7 LiPo standing orders (permanent, not just T1)

Verified: the B6neo has a dedicated **storage mode targeting 3.85 V/cell** and does 200 W on DC / **80 W max on USB-C PD (12–20 V, 5 A, PD 3.0)** — your 100 W PD brick is fine ([SkyRC](https://www.skyrc.com/b6neo), [manual PDF](https://www.skyrc.com/download/100198%20B6neo%20Instruction%20Manual%20V1.1_240318.pdf)). Standing orders, in force forever:

1. **Every charge attended**, in the fireproof bag, on ceramic/concrete/tile — never the workbench where flux and solder scraps live. Smoke alarm in the room. (T1's rules were the permanent rules all along.)
2. **Storage-charge whenever the pack won't be used within 3 days**: B6neo storage mode → 3.85 V/cell = 7.70 V pack. This applies **immediately after T1**, because the harness parts won't have arrived. A LiPo parked at 4.20 V/cell for weeks degrades measurably and puffs sooner.
3. **Retire, never recharge**, any pack that has: puffed, dropped below 3.0 V/cell, or taken a hard mechanical hit (dropped robot counts). With the plan's 3.3 V/cell floor, an over-discharge in testing is a *likely* event — decide now, not then.
4. **UK disposal:** discharge to storage or below (B6neo discharge mode), tape the connector, take it to the council Household Waste Recycling Centre battery point. Never the bin, and skip the salt-water-bucket folklore — it corrodes the tabs without reliably discharging the cells.

## 4.8 T6 beginner on-ramp, and trusting the datasheet over this document

The register structure was re-verified this session against a published STS3215 driver's memory map ([python-st3215 values.py](https://raw.githubusercontent.com/Mickael-Roger/python-st3215/main/st3215/values.py)): **ID = addr 5, baud = addr 6 (EEPROM), lock = addr 55, present voltage = 62, present temp = 63, present current = 69/70, SyncWrite = 0x83.** The *protection defaults* Part 1 quotes (13=70, 14=80, 19=44, 28≈500, 34=20, 35=200, 36=80) could **not** be independently confirmed this session — so the standing rule for T6 is: **download the [Feetech STS3215 datasheet/memory table](https://files.seeedstudio.com/products/Feetech/108090023_STS3215-C001_Datasheet.pdf) first, and where it disagrees with Part 1's table, the datasheet wins.** A value that differs from Part 1 but matches the datasheet is not an outlier — Part 1 is what gets corrected.

- **Software:** get FD from the official page, [feetechrc.com/software.html](https://www.feetechrc.com/software.html) (FD1.9.8.x series; UI is part-Chinese — the [Hackster STS3215 setup guide](https://www.hackster.io/ian-hong/feetech-serial-bus-servo-sts3215-setup-guide-fd16aa) is the illustrated walkthrough to follow click-by-click). Open-source fallbacks if FD fights you: [FT_SCServo_Debug_Qt](https://github.com/Kotakku/FT_SCServo_Debug_Qt) or [Feetech-tuna](https://github.com/iotdesignshop/Feetech-tuna).
- **FE-URT-1 wiring, the classic mistake pre-empted:** servo 7.4 V goes to the board's **screw terminal** (V+ / GND), never onto the USB side; the servo plugs into the 3-pin bus header; USB-C to the laptop. Photograph your working setup at servo #1 and match it for #2–20.
- **First-servo dry run (spare #1, not a flight unit):** scan at 1 Mbps → factory servo answers at ID 1 → unlock addr 55 (write 0) → change **ONLY addr 5** to the new ID → re-lock addr 55 (write 1) → power-cycle → re-scan and confirm. **Never touch addr 6 (baud) — it isn't needed for anything in this build.**
- **"Scan finds nothing" triage, in order:** (1) COM port / driver — check Windows Device Manager; (2) servo power — is the screw terminal actually at 7.4 V (multimeter); (3) wrong baud — scan every baud the tool offers (8 codes: 1 M down to 38400).
- **Recovery note (mistakes are not fatal):** an accidental baud write soft-locks nothing — the servo still answers at its new baud, and a full baud-sweep scan finds it again. The only truly destructive act at T6 is applying 7.4 V to the signal pins, which the wiring photo rule exists to prevent.
- **Budget correction:** first servo gets **20 minutes**, not 3. Servos 2–20 get 3 minutes each once the routine is boring. 20 min + 19 × 3 min ≈ 77 minutes for the fleet.
