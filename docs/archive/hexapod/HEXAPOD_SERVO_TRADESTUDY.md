I have enough verified data to resolve every disputed number. Key resolution: **the "19.5 kg·cm @ 6V" claim in synthesis2.md is wrong** — it's 19.5 kg·cm @ 7.4V (confirmed by Waveshare's own product title, Seeed, DFRobot, RobotShop, OpenELab). All three GPT-5.5 passes are correct on this. The 6V figure that confused the synthesis is a contamination from the 30kg/12V variant's spec sheet. The 30kg variant does carry temperature feedback; the 19kg's temperature telemetry should be treated as unconfirmed until tested on the user's exact units.

Now producing the final answer.

---

# Hexapod STS3215 — Definitive Trade Study (Torque, Voltage, 19 vs 30 kg, Pricing, Completeness)

**Resolution note:** The synthesis claimed "19.5 kg·cm @ 6 V" and built its optimistic torque verdict on it. **This is incorrect and is overturned.** Verified from the vendor's own pages: the owned servo (Feetech ST3215-C001 / STS3215, 7.4 V) is **19.5 kg·cm @ 7.4 V**, operating range **6–7.4 V**, locked-rotor current **2.5 A @ 7.4 V**. Waveshare's product title literally reads *"30 kg·cm @ 12 V / 19.5 kg·cm @ 7.4 V."* The "@ 6 V" number was a contamination from the **30 kg / 12 V** variant's datasheet. All three GPT-5.5 passes are right; the synthesis is wrong here. Every torque conclusion below is recomputed on the correct 7.4 V basis.

Sources: [Waveshare ST3215](https://www.waveshare.com/st3215-servo.htm), [Seeed C001](https://www.seeedstudio.com/STS3215-19kg-cm-7-4V-Serial-Servo-p-6338.html), [DFRobot 7.4 V](https://www.dfrobot.com/product-2961.html), [DFRobot 30 kg/12 V](https://www.dfrobot.com/product-2962.html), [RobotShop 7.4 V](https://www.robotshop.com/products/magnetic-encoding-servo-sts3215-74v-19kgcm), [RobotShop 30 kg](https://www.robotshop.com/products/feetech-12v-30kgcm-magnetic-encoding-servo-sts3215), [WowRobo C018](https://shop.wowrobo.com/products/feetech-sts3215-servo-12v-30kg-high-torque-servo-for-so-arm100).

---

## 1. Straight answers to your four questions

**(1) Are we sure nothing's missing? — No, not yet.** The prior BOM fixed the big PWM/driver/3S mistakes, but three things are still unresolved and one is a hidden error: (a) the **torque/voltage premise was wrong** — 6 V is **~15.8 kg·cm, not 19.5**; (b) the **servo rail regulator is under-specified** — a cheap "300 W / 20 A" buck is a 120 W part by output-current limit and cannot hold the rail under a 30–45 A stall transient; (c) **temperature telemetry on the 19 kg variant is unconfirmed** — your safety firmware leans on it, but vendor pages list it inconsistently (the 30 kg variant clearly has it; the 7.4 V one is ambiguous), so verify on your own units before relying on it. Full consolidated list in §6.

**(2) Cheapest 18 + spares.** Your cheapest path is **£0 — you already own 18.** For *spares only*: 1–2 from a fast UK stockist (RobotShop ~£26 each) or fold a couple into a slow AliExpress 6-pack (~£13–16/unit). If you were buying all 18 fresh, the cheapest *verified* route is bulk AliExpress 6-packs (~£12–15/unit landed, est.) or Seeed at **$19 each @ 10+**. Concrete table in §5.

**(3) 360° or cheaper/limited?** **Keep the 360° magnetic-encoder STS — do not downgrade.** There is **no cheaper "limited-angle" STS3215 SKU** — angle is firmware, not a price tier — so "downgrading" saves nothing. The magnetic encoder buys absolute-position-on-boot, load telemetry, and resolution you actually use, and it's the more reusable asset for future projects. Details in §4.

**(4) Switch to 30 kg?** **No — not on spec, but design so you *can*.** The 30 kg (C018) is a **zero-weight, zero-CAD drop-in** (same 55 g, same 45.2×24.7×35 mm), but switching forces a **full 3S / 12 V power cascade** *and* a rebuy of servos you already own (~£190–290 / ~$370). The honest nuance the synthesis buried: **at 2.5–2.7 kg with phone and 14–18 cm reach, the 19 kg servos do not hold a clean SF 2 even at 7.4 V** — so 30 kg *is* the correct class *if* the robot really lands that heavy/long. Verdict: build with owned servos but **constrain the design around their weakness** (low mass, short stance, slow gait) and lay out chassis + power so a 3S/30 kg swap is not a rebuild. Full trade in §3.

---

## 2. Torque & voltage — resolved

### 2.1 Owned 19 kg servo, corrected derating (linear from 7.4 V, kt ≈ 7.8 kg·cm/A)

| Rail | Stall torque | Stall A/servo | 18× stall | Usable @ SF 1.5 | Usable @ SF 2.0 |
|---|---:|---:|---:|---:|---:|
| 5.0 V | ~13.2 kg·cm | 1.69 A | 30.4 A / 152 W | 8.8 | 6.6 |
| **6.0 V** | **~15.8 kg·cm** | 2.03 A | 36.5 A / 219 W | **10.5** | **7.9** |
| 7.4 V | **19.5 kg·cm** | 2.50 A | 45.0 A / 333 W | 13.0 | 9.8 |
| 30 kg @ 12 V | 30.0 kg·cm | 2.70 A | 48.6 A / 583 W | 20.0 | 15.0 |

**6 V is NOT full torque** — it is ~81% of 7.4 V. Going 6 V → 7.4 V is a real **+23%**, not the "+15%" the synthesis claimed.

### 2.2 Required **femur** torque (= mass-share × horizontal foot reach)

| Mass | Tripod @14 cm | 2-leg transient @14 cm | Tripod @18 cm |
|---:|---:|---:|---:|
| 2.1 kg | 9.8 | 14.7 | 12.6 |
| 2.3 kg | 10.7 | 16.1 | 13.8 |
| 2.5 kg | 11.7 | 17.5 | 15.0 |
| 2.7 kg | 12.6 | 18.9 | 16.2 |

### 2.3 Resulting safety factors (the real verdict)

| Case | 19 kg @ 6 V | 19 kg @ 7.4 V | 30 kg @ 12 V |
|---|---:|---:|---:|
| 2.3 kg, 14 cm, tripod | 1.48 | 1.82 | 2.80 |
| 2.5 kg, 14 cm, tripod | 1.35 | 1.67 | 2.56 |
| 2.7 kg, 14 cm, tripod | 1.25 | 1.55 | 2.38 |
| 2.7 kg, 18 cm, tripod | 0.98 | 1.20 | 1.85 |
| 2.5 kg, 14 cm, **2-leg** | 0.90 | 1.11 | 1.71 |
| 2.7 kg, 18 cm, **2-leg** | 0.65 | 0.80 | 1.23 |

### 2.4 Firm recommendation — rail voltage

**Regulate the servo rail to a flat 7.4 V, not 6 V, and never to 5 V.**
- This reverses the synthesis's "6 V is fine" — once 19.5 kg·cm is correctly pinned at 7.4 V, you need the 7.4 V rail to get usable margin on a 2.3–2.7 kg walker. 6 V leaves 19% on the floor you can't spare.
- 7.4 V is the **top of the rated band**, so it is safe — but it gives **zero ceiling headroom**, which means the regulator must hold 7.4 V *flat* and never let raw 2S (8.4 V) through. **Raw 2S is forbidden** (8.4 V > 7.4 V rating).
- **Add over-temp cutback in firmware regardless** — at 7.4 V near stall, plastic-case servos heat fast, and stall torque is not continuous torque.

### 2.5 Safe build envelope for the owned 19 kg servos (at 7.4 V)

- **Max all-up mass: ~2.3 kg** for a clean tripod SF ≥ 1.8; up to ~2.5 kg tolerable if gait is slow and stance tight. Above 2.5 kg you lose SF 2 even in clean stance.
- **Max foot reach / effective femur lever: ≤ 14 cm.** 18 cm collapses tripod SF toward 1.2 and 2-leg transients below 1.0.
- **Tibia length:** keep the femur-axis-to-foot horizontal projection ≤ ~14 cm at mid-stance — with coxa 4 / femur 7 cm geometry that caps the tibia near **~12 cm** and bars wide, sprawled stances.
- **Gait: slow, statically-stable tripod, low duty near stall, no fast body-drop (regen into the rail), hard software joint limits before first walk.**
- **Add ~10–20 % for ignored leg self-weight + distal servo mass.** Treat SF 2.0, not SF 1.5, as the design check.

---

## 3. 19 kg vs 30 kg — resolved trade

| Axis | 19 kg (C001, owned) | 30 kg (C018) | Resolved |
|---|---|---|---|
| Stall torque | **19.5 @ 7.4 V** (15.8 @ 6 V) | **30 @ 12 V** | 30 kg ≈ 1.5× usable |
| Weight | 55 ± 1 g | 55 ± 1 g | **Zero delta** |
| Size / CAD / horn | 45.2×24.7×35 mm, 25T | identical | **Drop-in** |
| Battery | 2S, regulate to 7.4 V | 12 V → **3S** | 3S cascade = real cost |
| 18× stall current | 45 A | 48.6 A | ~equal |
| 18× stall power | 333 W | 583 W (+75%) | worse runtime/heat |
| Per-unit price (verified) | Seeed $19 @10+; Waveshare ~$16.3 @4+ | WowRobo $15.99; Waveshare ~$20.6 @4+ | ~same per unit |
| **Cost to switch (18)** | **£0 (owned)** | **~£190–290 / ~$370 rebuy + 3S cascade** | sunk-cost rebuy |

**Net verdict: do not switch on spec; design for a future swap.** Weight and CAD fears are non-issues (identical body). The cost is almost entirely (a) **re-buying 18 servos you own** and (b) a **genuine 3S cascade** — new 3S pack, regulation flips to ~12 V handling, 25 V bulk caps (12.6 V on 16 V caps ≈ 1.27× derating), tighter fusing, +75% stall watts hurting runtime. **£ delta:** the *servo* delta is small (~£40–80 / $78 for 18), but the *real* switch cost is the **full rebuy (~£190–290) plus the cascade**, because you already own the 19 kg set.

**The honest caveat the synthesis missed:** if the robot truly lands at **2.5–2.7 kg with the phone and 14–18 cm reach**, the 19 kg class does *not* give SF 2, even at 7.4 V — 30 kg would then be the correct actuator. So: **build with owned servos, keep mass/stance inside §2.5, measure load/temp telemetry, and switch to 30 kg only if data proves torque-starvation.** Lay out the chassis and power harness now so the 3S/30 kg swap is a re-flash and a pack change, not a rebuild.

---

## 4. 360° vs limited-angle — resolved

**Keep the 360° magnetic-encoder STS3215.** No leg joint exceeds ~180°, so the 360° range is unused — but (a) there is **no cheaper limited-angle STS SKU**, so downgrading saves £0; (b) the magnetic encoder gives absolute position on boot (IK knows pose with no homing), load telemetry (foot-contact/stall detection), 12-bit resolution with no wiper wear under constant gait oscillation; (c) it is the **more reusable asset** — future wheels want continuous mode, future arms/pan-tilt want absolute feedback, both of which the STS covers and a pot-based SCS does not. "Less" only wins for a *separate* future low-torque, fixed-range, many-joint build (e.g. SCS0009 micros for a hand/face) — not here, and mixing SCS in now would add a second firmware path for zero gain.

---

## 5. Cheapest 18-servo sourcing (concrete)

*Verified per-unit prices below; AliExpress landed-UK totals are estimates that resolve only at logged-in checkout with shipping + 20% VAT (over ~£135).*

**19 kg (7.4 V) — what you own; £0 to keep:**

| Qty | Cheapest route | Unit | Total (est.) |
|---|---|---:|---:|
| 18 | 3× AliExpress 6-pack | £12–15 | **£220–270** |
| ~21 | 4× AliExpress 6-pack (24, 6 spare) | £12–15 | **£290–360** |
| verified single floor | Seeed @10+ / Waveshare @4+ | $19 / ~$16.3 | — |
| fast UK spare | RobotShop UK | ~£26 | — |

**30 kg (12 V):**

| Qty | Cheapest route | Unit | Total (est.) |
|---|---|---:|---:|
| 18 | AliExpress 6-packs | £12–15 | **£230–290** |
| 18 | Waveshare @4+ | ~$20.6 | **~$371** |
| verified cheapest single | **WowRobo** | **$15.99** | — |

**Caveat:** treat all AliExpress totals as *estimates* until you do a logged-in landed checkout — some 30 kg listings showed backorder/sold-out at check time, and naming is messy (ST/STS, C001/C018, 7.4 V/12 V). **Verify variant labels and 1:345 gear ratio on every unit** so you don't end up with asymmetric legs. **Practical move: keep your 18, buy 1–2 spare servos + spare 5264 bus cables only.**

---

## 6. What could go wrong / still to buy (new beyond prior BOM)

**Corrected premises (must internalize):**
- 6 V ≠ full torque (15.8 not 19.5). Set rail to **7.4 V**.
- Stall torque ≠ continuous torque — design to **SF 2**, not SF 1.5.
- **Servo "load" telemetry is not a calibrated torque sensor** — use for trends/faults, not SF proof.
- **Temperature telemetry on the 19 kg variant is unconfirmed** — verify on your units; if absent, fall back to conservative load-time limits + bench characterization.

**Power rail (biggest open risk):**
- A **2S buck-to-7.4 V dropout problem**: a 2S pack sags toward ~6–7 V near empty and a plain buck can't hold 7.4 V under load exactly when servos pull hardest. Resolve deliberately: **3S → high-current buck regulated to 7.4 V** is the clean fix (raw 3S still forbidden), or a properly-sized 2S buck-boost. Either way size for **30–45 A transient**, not "20 A."
- The cheap "300 W / 20 A" buck is **~120–150 W by output-current limit** — not a hexapod rail. Buy/build a real regulator and **bench-test it at 40 A**.
- **Per-leg / star power injection**, not one daisy-chain carrying full robot current through 5264 connectors.
- Logic 5 V UBEC isolated from servo dips; low-voltage cutoff/alarm tied to firmware; **emergency kill switch reachable while moving**; anti-spark/robust main switch (XT60/XT90-S); 25 V bulk caps **if** 3S.

**Mechanical:**
- **Phone on top is a CG/tip-over problem, not just mass** — mount battery low/central, phone low/removable or off-board.
- **Hard software joint limits before first gait** (360° servo will drive a printed leg into itself).
- **Screw length**: over-long horn/body screws can contact the servo internals and spike current — Waveshare explicitly warns of this.
- Verify output spline + single-bearing load rating against final leg CAD; PETG/ASA structural filament + TPU feet (PLA near warm servos creeps); model wire exit paths through legs; mechanical connector retention.

**Software / bus:**
- All 18 ship as **ID 1** — assign one at a time; record the ID/baud map in a file.
- **SyncWrite** targets (not sequential writes → gait skew); budget telemetry reads so they don't wreck control timing; timeout → torque-off/freeze safely; controlled startup pose; IK rejects unreachable/singular targets; speed/accel limits to avoid current spikes; deadman timeout on phone/WiFi control; brownout must not reboot into uncontrolled gait.

**Still to buy / verify:** real 40 A-rated servo rail regulator (or 12 V distribution if 3S); FE-URT-1 / half-duplex TTL adapter for commissioning; correct 5264/2.54 3-pin bus cables **in multiple lengths + spares + housings/pins/crimper**; 2S pack (or 3S if 30 kg); low-voltage alarm; 50 A inline wattmeter; fasteners (M2 body, M3 horn/bracket), heat-set inserts, threadlocker; **≥1–2 spare servos** (one dead servo blocks the whole bus); charger PSU; bench supply / current-limited smoke-test rig for bring-up; **actual mass budget from CAD/slicer, not estimates.**

---

## 7. Bottom line

**Keep your 18 owned 19 kg STS3215, regulate the servo rail to a flat 7.4 V (not 6 V, never raw 8.4 V), and constrain the build to ≤ ~2.3–2.5 kg, ≤ 14 cm reach, slow tripod gait** — at which it holds a workable margin; do **not** rebuy or go 30 kg on spec (zero-weight drop-in but a sunk-cost rebuy + full 3S cascade), but **design the chassis and power layout so a 3S/30 kg swap is a re-flash, not a rebuild**, and switch only if load/temp telemetry proves you're torque-starved. The synthesis's one load-bearing error — "19.5 kg·cm @ 6 V" — is corrected to **@ 7.4 V**, and the real open risk is the **high-current servo rail regulator**, which is still under-specified.