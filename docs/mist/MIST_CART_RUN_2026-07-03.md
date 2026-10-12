# MIST cart run — 2026-07-03

> **Final actual orders are now captured in [MIST_ACTUAL_INVENTORY.md](MIST_ACTUAL_INVENTORY.md).** Earlier cart audits in this file are historical decision notes.

Goal: use the existing MIST docs plus live Chrome shopping to add missing build parts to the user's carts. Do not purchase.

Source docs:
- `MIST_MASTER_BASKET.md`
- `MIST_BUDGET_V2.md`
- Claude chat attachment: `<LOCAL_HOME>\.codex\attachments\64807b4b-a685-4bcb-b5d3-47bbc871de96\pasted-text.txt`

Working target:
- Default to the budget-safe 12-servo MIST configuration unless the live cart is already committed to 18 servos.
- Keep all safety lines: fuses, XT90-S loop key, smoke stopper, LiPo bag, low-voltage alarm, 25V caps.
- Do not buy or check out.

Live status:
- Chrome connected.
- Subagent research in progress.
- AliExpress cart tab claimed, but browser policy blocked automation on `https://www.aliexpress.com/p/shoppingcart/index.html`.
- Cart not modified. Do not attempt cart mutation via workaround.

## Consolidated cart action plan

Chrome could not mutate the cart. Manual actions below are the source of truth for this run.

### Target configuration

Use the **12-servo budget MIST** configuration unless explicitly choosing the full 18-servo build:
- 12-servo budget: 4 legs x 2 DOF + 4 wheel servos, coxa joints deferred.
- Later upgrade: add one more 6-pack plus extra cables/caps.
- Safety/power system stays the same as the 18-servo build.

### Remove / replace from the Claude cart

| Existing cart item | Action | Reason |
|---|---|---|
| 12-pack ST-3215-C018 | Replace with 2x 6-pack for budget config | 6-pack pricing was cheaper per servo in `MIST_BUDGET_V2.md`; 12-pack only makes sense if it reprices better live. |
| Existing 6-pack STS3215 | Keep, but budget target is total qty 2 six-packs | Must be 12V / 30KG / ST-3215-C018. |
| Servo Driver with ESP32 Expansion Board | Remove | Replaced by Bus Servo Adapter (A) + ESP32 DevKitC. |
| 300W 20A buck converters x3 | Remove | Leftover from 7.4V plan; 12V servos run on raw 3S. |
| XT60 to 4mm banana charge lead | Remove | B6neo output is native XT60; not needed. |
| 4700uF 16V capacitors | Remove | Replace with 25V caps for 12.6V full 3S pack. |

### Add on AliExpress

| Item | Budget qty | Full 18-servo qty | Search / listing clue |
|---|---:|---:|---|
| ST-3215-C018 12V 30KG 6-pack | 2 total | 3 total | `STS3215 12V 30KG 6PCS ST-3215-C018`; screenshot exact option text. |
| FE-URT-1 USB servo adapter | 1 | 1 | Add if not bundled with servo pack; needed for ID/register testing. |
| Bus Servo Adapter (A) | 1 | 1 | Must be serial bus Adapter (A), not PWM/I2C board. |
| ESP32 DevKitC / WROOM-32 CH340 | 1 | 1 | USB-C or micro-USB is fine if you have a matching data cable. |
| 5V 5A UBEC, 2-6S / 7-26V input | 2 | 2 | Change current qty 1 to qty 2. |
| XT30 pigtail pairs, 16AWG | 8-10 pairs | 10 pairs | For fused leg branches and spares. |
| 5.5x2.1mm male DC barrel pigtail | 2 | 2 | Adapter/control board power input. |
| XT90-S anti-spark loop key, preferably with XT60 pigtails | 1 | 1 | Physical kill switch. |
| Blade fuse assortment incl. 15A and 30A | 1 | 1 | Need 4x 15A branch fuses + 30A main/spares. |
| LiPo low-voltage alarm, 1-8S adjustable | 1 | 1 | Running safety. |
| 5264 3-pin Feetech servo cables | 9 minimum / 12 safer | 12 | Search `5264 3 pin servo cable Feetech 20cm 30cm`. |
| 4700uF 25V electrolytic capacitors | 5-6 | 8 | Replace the 16V caps. |
| XT60 M/F pigtail pairs, 14AWG | 3 pairs | 3 pairs | Smoke stopper/adapters/spares. |
| 63/37 solder + rosin flux + desolder wick | 1 set | 1 set | Required unless buying locally/Amazon. |
| Wire stripper + flush cutters | 1 each | 1 each | Required unless already owned. |
| 20mm hook-loop battery straps | 3 | 3 | Battery/phone retention. |
| Blue threadlocker + zip ties | 1 each | 1 each | Vibration/cable retention. |
| Safety glasses | 1 | 1 | Required. |
| USB-C data cable + micro-USB data cable | 1 each if not owned | same | Must be data-capable, not charge-only. |

Keep from existing AliExpress cart:
- B6neo 2 charger, only if store is SkyRC-branded.
- XT60 to 8-channel XT30 PDB.
- 5-pack inline blade fuse holders.
- Fireproof LiPo bag.
- 12AWG / 14AWG / 16AWG silicone wire, with 16AWG qty 2 if cheap.
- VL53L0X ToF sensor.
- XT60BE-M connectors.
- Heat-shrink kit.
- Acrylic mirrors.

### UK / Amazon / local

| Item | Qty | Status |
|---|---:|---|
| 3S LiPo with XT60, preferably 2-pack 2200mAh 30C+ / 50C | 2 packs preferred | Required; AliExpress lithium shipping is not the plan. |
| Existing 100W USB-C PD brick + 5A e-marked cable | 1 | Required for B6neo PD input unless using DC PSU. |
| PETG 1kg | 1 now | Required for first frame/leg prints. |
| TPU 95A 1kg | 1 | Required for tires/feet; not deferrable. |
| H4 55/60W bulb + holder | 1 minimum, 2 safer | Required smoke stopper. |
| Temp-controlled soldering iron | 1 | Required unless already owned. |
| Multimeter with continuity + DC voltage | 1 | Newly flagged required blocker. |
| Cheap metric hex key/driver set | 1 | Required. |
| Digital calipers 150mm | 1 | Required for CAD/measuring. |
| Printer / borrowed printer access | 1 | Required unless outsourced. |

### Verification gates before payment

- Servo option text must read **12V / 30KG / ST-3215-C018**.
- Screenshot every servo option page before paying.
- On arrival, FE-URT-1 register check: register 14 = 140 confirms 12V variant.
- UBEC must say 2-6S or 7-26V input and 5V 5A output.
- Capacitors must be 4700uF 25V.
- Bus Servo Adapter must be Adapter (A) serial bus servo adapter.
- Do not enter checkout/payment in this run.

## Cart audit from user-provided AliExpress/Amazon list — 2026-07-04

Verdict: current carts are not ready. Several items are good, but core blockers remain.

AliExpress problems:
- Only 1x 6-pack servo is listed. Budget MIST needs 2x 6-pack total. Full MIST needs 3x 6-pack total.
- XT60 to 4mm banana lead is still present and should be removed.
- UBEC quantity is 1; target quantity is 2.
- Missing XT90-S anti-spark loop/extension disconnect.
- Missing blade fuse assortment with 15A branch fuses and spare 30A fuses.
- Missing XT30 16AWG pigtail pairs.
- Missing 5264 3-pin Feetech servo cables.
- Missing 4700uF 25V capacitors.
- Missing 5.5x2.1mm barrel pigtails.
- Missing XT60 pigtail pairs.
- Wire items need option verification: must be 12AWG, 14AWG, and 16AWG red/black silicone wire, not random thin gauges.
- UBEC option must be 5V 5A with 2-6S / 7-26V input.

AliExpress okay if verified:
- LiPo alarm, FE-URT-1, one 6-pack servo, PDB, heat-shrink, ESP32, Bus Servo Adapter A, VL53L0X, LiPo bag, acrylic mirrors, silicone wire, fuse holders.

Amazon problems:
- TPU quantity is 2kg; change to 1kg TPU and add 1kg PETG.
- Smoke stopper quantity is 3; reduce to 1 unless very cheap/bundled.
- Zeee 3S 2200mAh 2-pack at 43.99 is usable but high versus prior budget target.
- UGREEN charger is only worth buying if no suitable USB-C PD brick is already owned. Need a 5A e-marked USB-C cable for best B6neo PD input.
- Missing multimeter.
- Missing solder/flux/wick.
- Missing calipers and metric hex keys/drivers unless already owned.

## Connector gender guidance — 2026-07-05

- Buy XT30 pigtails as male/female pairs when possible: `XT30 pigtail 16AWG male female pair`.
- If forced to choose one gender for leg branches, inspect the PDB output sockets and buy the opposite plug. Most XT30 PDB outputs are female sockets, so the branch lead often needs XT30 male, but listings vary.
- Buy XT60 pigtails as male/female pairs: `XT60 pigtail 14AWG male female pair`.
- RC safety convention: battery/source side should use recessed female contacts; load/device side uses male pins. Never leave exposed live male pins on a battery/source lead.
- The XT90-S screenshot option `XT90S 14awg 10cm` is not preferred for main kill/disconnect. Use a prewired XT90-S extension/loop in 10AWG or 12AWG. Short length: 10-30cm preferred.

## Cart audit from user-provided AliExpress/Amazon list — 2026-07-06

Verdict: better, but not ready. Current cart has most categories covered, but there are duplicates and a few wrong/expensive lines.

Must fix:
- Only 1x 6-pack servo is listed. Budget MIST still needs 2x 6-pack total.
- 5264 servo cable listing has 21.05 shipping; find another listing or defer only if servos include enough cables.
- Remove AliExpress PETG at 21.09 because Amazon PETG is cheaper.
- Remove duplicate XT60 pigtail line unless total selected options are intentionally 3 pairs.
- Remove duplicate heat-shrink line.
- Remove duplicate capacitor line; keep one 25V option, preferably 10pcs Nichicon if total delivered price is acceptable.
- UBEC needs qty 2, and must be 5V 5A or acceptable Hobbywing 3A/5A spare plan.
- Confirm XT90-S extension option is 10AWG and 30cm/50cm, not 14AWG.
- Confirm silicone wire options are exactly 12AWG, 14AWG, 16AWG red/black.
- Amazon PETG qty 2 is acceptable but 1 is enough for first build; no TPU on Amazon list, but AliExpress TPU is present.
- Add/confirm safety glasses and USB-C 5A e-marked cable if not already owned.

## Follow-up connector/servo audit — 2026-07-06

- User added 3x 6-pack STS3215. This is correct for full MIST: 4 legs x 3 joints = 12, plus 4 wheel servos = 16, plus 2 spares = 18.
- B6neo can use existing 100W/120W chargers only if they support USB-C PD 20V/5A and the cable is 5A e-marked. Proprietary phone 120W is not automatically equivalent.
- XT30 pigtails: need 8-10 male/female pairs total. If selected variant is 5 pairs, qty 2 is correct. If selected variant is 1 pair, qty 2 is not enough.
- XT60 pigtails: need around 3 pairs total. A 5-pair 14AWG set is acceptable for adapters/smoke-stopper; main battery trunk should still use 12AWG/10AWG where possible.
- UBEC: listing is acceptable only if selected option is 5V 5A and qty 2, with input 2-6S / 7-26V.
- XT90-S extension listing is acceptable if option is 10AWG, 30cm or 50cm.
- First AliExpress link could not be identified from web tooling. If it is 5264 STS3215 servo cables, accept only if it says 3P/5264 for Feetech STS3215 and provides at least 10-12 cables at sensible shipping.

## Charger/tooling decision — 2026-07-06

- User has Anker 317 100W charger. Official Anker spec is 20V/5A 100W max and the UK product page says the included USB-C cable is 5A/100W with E-Marker. This is suitable for B6neo PD input; no extra 100W charger needed if using that cable.
- Still need a real LiPo balance charger. A USB-C laptop charger cannot connect directly to a 3S LiPo. B6neo is still the recommended cheap charger because it has balance/storage/discharge modes and can run from the existing Anker 317.
- Buy soldering iron, flux/wick, and safety glasses. Recommended source: Amazon/UK for iron and glasses; Amazon or reputable AliExpress for 63/37 solder, rosin flux, and wick.
- HANDSKIT 90W Amazon soldering kit `B07SLRRYMC` is acceptable for XT60/XT30/XT90 and wire work. It includes lead-free solder and rosin flux, but still prefer separate 63/37 0.8mm solder for easier beginner joints. Desoldering pump is included; wick is still useful but not a hard blocker.
- Amazon charger search audit from pasted results: recommended default is SKYRC B6Neo `B0CCT2WGNS` at 37.52. If out of stock, SKYRC B6 Neo2 `B0GDK65S7G` at 42.43 is acceptable. Budget alternative is ISDT 608PD at 26.99, but B6Neo remains the simpler documented path.

## AliExpress bundle picks — 2026-07-06

Best useful filler items from the bundle list:
- Work safety anti-splash goggles, about 1.00-1.60: buy if no safety glasses.
- Desoldering braid/wick, about 0.80: buy.
- 100pcs standard blade fuses incl. 15A/30A, about 1.80: buy if standard blade, not mini.
- XT30 male/female 16AWG pigtail set, about 1.60: buy as needed to reach 8-10 pairs total.
- 5pcs 4700uF 25V caps, about 1.60: buy two packs for full build if caps not already covered.
- Wire stripper/cutter 10-22AWG, about 4.40: buy if not already covered by better tool.
- DELIXI metric Allen/hex key set, about 5.00: buy if no metric hex keys.
- Cable ties / reusable cable organizer ties, about 0.80-1.00: buy.
- A3/A4 cutting mat, about 1.80-2.40: useful, but not a hot soldering surface.
- 5kg/1g kitchen scale, about 5.20-5.40: useful. Do not also buy pocket scale.

Skip from bundle list:
- 18650 chargers/power bank boards, pocket scale if buying kitchen scale, second multimeter if Amazon meter is kept, Imax B3 Pro charger, SG90/PWM servo tester, blue-light/sunglasses as safety glasses, random PD/charger modules, non-contact AC voltage pen, lock pick set, car cleaning items.

## Mechanical joint hardware note — 2026-07-06

- STS3215 servos normally include 25T horns and some mounting/horn screws, but do not rely on included screws as the only mechanical stock.
- For printed MIST joints, buy/keep: M2 screw/nut assortment, M3 socket/button-head screw assortment, M3 nyloc nuts, M3 washers, blue threadlocker, metric hex keys.
- Optional but recommended after first fit test: M3 heat-set inserts and an insert tip; not required before printing the first prototype leg.
- Do not buy PWM/Futaba servo plug kits or generic SG90/MG996R servo horns for the STS3215 bus servos.
- Do not buy bearings before CAD dimensions are fixed. If the printed joint needs a passive pivot later, choose bearing size after measuring the printed boss/shaft.
- Wheel hubs/tires are printed: PETG for hubs, TPU for tires. Use the STS3215 horn as the bolt pattern into the printed wheel hub; buy spare STS3215-compatible horns only if the servo packs do not include enough.

## Triple-check cart state — 2026-07-06

Bundle order placed:
- Useful/covered: screwdriver bit set, 0.8mm 20g rosin-core solder, A4 cutting mat, magnetic pickup tool, cable organizer, safety goggles, desoldering braid, pocket scale, SZ308 multimeter, 10kg kitchen scale, washer assortment, XT30 5-pair pigtails, 2x 5pcs 4700uF 25V caps, wire stripper/cutters.
- Not counted for MIST servo bus: 25pcs generic RC/PWM servo extension leads. STS3215 needs 5264 3-pin Feetech/ST/SC servo cables.

AliExpress cart remaining:
- Remove 6337 63/37 solder at 19.56: too expensive and redundant after bundle solder + Amazon soldering kit.
- FE-URT-1 cart line selected as `urt-1` is correct, despite title showing servo.
- Keep 5264 3PIN cable listing if it is 6pcs 300/900mm for ST/SC/CF and shipping free. Six cables is usable but not enough alone; servo packs may include cables, otherwise need 6 more.
- XT90-S selected `WHITE` must be checked: keep only if it is 10AWG cable, 30cm or 50cm. Do not buy 100cm.
- Low-voltage alarm, PDB, STS3215 6-pack, Bus Servo Adapter A, ESP32, 2pcs 5A UBEC, LiPo bag, silicone wires, heat shrink are good.
- Inline fuse holders selected as `5PCS 18 AWG` are not ideal. Prefer 12AWG holders. Existing title says 12AWG but selected SKU says 18AWG, so replace if possible.
- XT30 total after bundle is 5 pairs. Full build target is 8-10 pairs; add one more 5-pair set unless existing cart still has another 5-pair set.
- Missing/not confirmed: standard blade fuses assortment with 15A/30A; M2/M3 screws/nuts/nylocs; metric hex key set; battery straps/phone retention; USB-C/micro-USB data cables if not owned; safety glasses already covered by bundle.

Amazon cart:
- Keep B6Neo, HANDSKIT soldering kit, TPU, multimeter only if not relying on bundle SZ308, Loctite, smoke stopper, PETG, HOOVO 3S 2-pack.
- Multimeter is duplicated with bundle SZ308; keep Amazon meter only if wanting a safer/faster better meter, otherwise remove.
- Loctite duplicates Ali threadlocker only if Ali line remains; keep Amazon Loctite and remove cheap Ali threadlocker if present.

## Fastener/mechanical count clarification — 2026-07-06

MIST full build fastener targets:
- M2 servo body screws: minimum 64 for 16 installed servos, 72 if mounting/testing all 18, practical target 100 pcs. Useful sizes: M2x6 and M2x8.
- M3 structure/hub screws: practical target 100-150 mixed lengths. Useful sizes: M3x6, M3x8, M3x10, M3x12, M3x16.
- M3 nyloc nuts: target 50-100.
- M3 washers: target 100+; user ordered mixed washer box, should cover washers if enough M3 included.
- M2 nuts/washers are useful but less critical than M2 screws and M3 nylocs/washers.
- Do not buy bearings until CAD dimensions are fixed.
- 5264 cable qty 3 likely means 3 x 6pcs = 18 cables if using the 6pcs listing; this is enough.
- Separate ESP32 devkit CP2102 is still recommended even though user owns an ESP32 camera board, because the camera board should stay vision-only and does not have easy spare pins/USB for the servo bus.

## Actual orders recorded — 2026-07-06

Source of truth moved to `MIST_ACTUAL_INVENTORY.md`.

High-level ordered state:
- Full 18-servo build covered: 3x 6-pack STS3215 12V 30kg ordered.
- Control covered: FE-URT-1, Bus Servo Adapter A, ESP32 CP2102 Type-C ordered.
- Power/safety mostly covered: SKYRC B6Neo, HOOVO 3S 2200mAh 2-pack, smoke stopper, LiPo bag, low-voltage alarm, XT90-S, XT60 PDB, XT30/XT60 pigtails, UBECs, 25V caps, fuse holders, blade fuses ordered.
- Tools/materials covered: HANDSKIT soldering kit, 63/37 solder, wick, wire stripper, multimeter, calipers, goggles, PETG 1kg, TPU 0.5kg ordered.

Still not proven from actual orders:
- 12AWG / 14AWG / 16AWG red-black silicone wire.
- M2/M3 machine screws, M3 nyloc nuts, and known-good metric hex keys.
- Battery/phone straps.
- Data-capable USB cables for ESP32/FE-URT-1 if not already owned.
- TPU quantity beyond the first 0.5kg if tire iterations consume material.
