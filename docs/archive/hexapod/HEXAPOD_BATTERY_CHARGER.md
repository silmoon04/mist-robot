All disputed facts confirmed. Everything both sides argue rests on verified numbers: STS3215 = 2.5 A stall/servo (→45 A rail), 19.5 kg·cm @ 7.4 V; Overlander pack in stock at £44.99, 343 g, XT60 available. Both models actually agree on chemistry; the only real dispute is capacity choice and regulator sizing. Here is the definitive answer.

---

# DEFINITIVE Battery Answer — Hexapod (18× STS3215, ~2.5 kg, flat-7.4 V rail)

## 1. Verdict (one line)

**Buy the Overlander Supersport Pro 3350 mAh 3S 35C LiPo with an XT60 connector (£34.99).** Go **3S, XT60, 35C**; take **3350 mAh over 5000 mAh** because on a ~2.5 kg walker the 115 g and the higher CG matter more than 10 extra minutes of runtime. **This changes the original recommendation** (which led with the 5000) — see §6.

## 2. The product (+ backup)

**BUY — Overlander Supersport Pro 3350mAh 11.1V 3S 35C LiPo (select XT60):**
- **£34.99–35.99** · **228 g** · 137 × 43 × 17 mm · 37.2 Wh · JST-XH balance lead · in stock at Overlander (UK manufacturer, ships LiPo domestically — solves your AliExpress problem).
- https://overlander.co.uk/product/3350mah-11-1v-3s-35c-supersport-pro-lipo-battery/
- Connector is per-order — **explicitly pick XT60** in the dropdown (options are Bare/Deans/EC3/EC5/Traxxas/XT60/XT90/XT90S).

**BACKUP / if you decide runtime beats CG — Overlander Supersport Pro 5000mAh 3S 35C (XT60):**
- **VERIFIED LIVE:** £44.99–45.98 · **343 g** · 138 × 42 × 27 mm · 55.5 Wh · 35C/65C burst · **in stock** · XT60 offered.
- https://overlander.co.uk/product/5000mah-11-1v-3s-35c-supersport-pro-lipo-battery/
- Amazon UK mirror (sold by Overlander, ~£45, Prime): https://www.amazon.co.uk/Overlander-Batteries-5000mAh-Supersport-Models-connector/dp/B0FXMY7X42
- Other UK stock: Kings Lynn Model Shop, Howes Models.

Buy **one of each** if budget allows: 3350 flies on the robot, 5000 is a bench/long-run hot-swap. Both charge on your B6neo with no new leads.

## 3. Why this chemistry / capacity / C (the numbers)

- **3S, not 2S — settled, both models agree.** The rail is a *flat 7.4 V buck output*. 3S runs 12.6 V→9.9 V, always **above** 7.4 V, so the regulator only ever **steps down** — a plain, common buck. 2S (8.4 V→6.0 V) falls **below** 7.4 V for most of discharge, forcing a rare/hot **40 A+ buck-boost**. GPT-5.5 conceded this outright ("for flat 7.4 V, 3S buck is electrically easier"). Confirmed.
- **C-rating is a non-issue — buy for capacity, not C.** Verified stall is **2.5 A/servo → 45 A** worst-case at the rail. At 90% buck efficiency that's ~**37 A pack-side** near cutoff. The 3350's 35C = **117 A continuous / 217 A burst**; the 5000's = 175 A/325 A. Either is **~3–5× the absolute worst case** and ~15× the ~8 A walking draw. C-rating never binds. (GPT-5.5 agreed here too.)
- **XT60 — correct.** Rated ~30 A continuous / 60 A burst: covers walking (~8 A) and the brief 37 A stall transient with margin, and matches every UK pack + your B6neo. Fit an **XT90-S anti-spark as the main switch** if you want spark-free connects on a 3S pack.
- **Runtime — GPT-5.5's math is the honest one; adopt it.** Usable ~80% × ~90% buck ≈ **72% delivered**. So **3350 ≈ 27 Wh usable ≈ 20 min** walking, **5000 ≈ 40 Wh ≈ 30 min** — *only if* real walking rail power is ~80 W. **The "30 min" is unproven until you measure walking current with an inline wattmeter.** Plan on **~15–20 min real** and treat longer as a bonus.
- **Weight / CG — the deciding factor.** 343 g (5000) is **~14% of a 2.5 kg walker**; 228 g (3350) is ~9%, saving **115 g** with nearly the same Wh-per-gram. The servo trade study already pins this build at **≤2.3–2.5 kg with almost no torque margin** and flags the top-mounted phone as a tip-over/CG risk. On a torque-starved walker, **shedding 115 g high in the stack is worth more than 10 min of runtime.** That's why the 3350 wins here.

## 4. Regulator requirement this implies (the real risk — both models flag it)

The battery is the easy part. **The failure point is the regulator, and the cart's "300 W / 20 A" buck is disqualified.**
- Need at the rail: **7.4 V flat, ≥40 A continuous, brief 45 A stall, input up to 12.6 V.**
- 45 A × 7.4 V = **333 W output**. A "20 A" buck = **148 W** — less than half. Even a nominal "300 W" part = 40.5 A *ideal* with **zero thermal headroom**, below the stall case. **Buy/build a genuine ≥40 A regulator and bench-test it at 40 A before it ever drives legs.**
- **Zero overvoltage headroom at 7.4 V** (servo max = 7.4 V). A buck overshoot / bad trim-pot / transient is now a servo-kill event. **Set the pot to 7.4 V under load, verify with a scope/meter, and never let raw 3S (12.6 V) reach the servos.** (GPT-5.5's "drop to 6 V for margin" is rejected — the trade study proved 6 V costs ~19% torque this build can't spare; 7.4 V stays, tightly regulated.)
- **Star/per-leg power injection**, not one daisy-chain through 5264 connectors at 45 A.
- **Firmware must current-limit / stagger the gait** so 18 servos never stall simultaneously — keeps XT60, buck, and pack inside rating.

## 5. Accessories still to get (LiPo bag already owned)

- **Positive strap** (hook-loop cinch or strap-plate) to mount the pack **low and central** over the body centroid — non-negotiable on a marginal walker.
- **Per-cell low-voltage alarm** (JST-XH plug-in "buzzer", ~£3–5, HobbyRC/Amazon UK). **Get this** — GPT-5.5 is right that a pack-level buck cutoff hides an imbalanced cell. Balance-lead per-cell monitoring on the robot, not just total voltage.
- **Balance-lead extension / strain relief** so the JST-XH isn't tugged as the body moves.
- **Inline wattmeter (≥50 A)** to actually measure walking current and settle the runtime question.
- **XT60 (or XT90-S) main kill switch** reachable while the robot moves.
- **Charging:** balance-charge only on the SKYRC B6neo (1–6S, no new leads); it needs USB-C PD or a DC PSU to hit full current. **Cutoff 3.3–3.5 V/cell; store at ~3.8 V/cell; never charge unattended; charge in the bag.** Verify XT60 polarity before first connect (5 Ah reversed = dead short).

## 6. Resolved disagreements

- **Chemistry (3S vs 2S):** No real dispute — both models land on **3S** for the flat-7.4 V rail. **Settled: 3S.**
- **Capacity (5000 vs 3350):** The two disagreed. Original led with 5000 for runtime; GPT-5.5 argued 3350/lighter is "more defensible for this walker." **Resolved in favour of the 3350** — the servo trade study independently caps this build near its torque limit and flags CG/tip-over, so **115 g high in the stack outweighs ~10 min runtime.** 5000 kept as backup.
- **Rail voltage (7.4 V vs drop to 6 V):** GPT-5.5 floated 6 V for headroom. **Rejected** — the prior study verified 6 V = ~15.8 kg·cm (~81% torque), a loss this walker can't afford. **Stay at a tightly-regulated flat 7.4 V.**
- **Regulator adequacy:** Both agree the "300 W/20 A" buck is **inadequate**. **Settled — spec ≥40 A and bench-test.**
- **Runtime figure:** GPT-5.5's ~72%-delivered math is more honest than the original's "30 min." **Adopt ~15–20 min real; measure to confirm.**

Sources: [Overlander 5000 3S](https://overlander.co.uk/product/5000mah-11-1v-3s-35c-supersport-pro-lipo-battery/) · [Overlander 3350 3S](https://overlander.co.uk/product/3350mah-11-1v-3s-35c-supersport-pro-lipo-battery/) · [Amazon UK 5000 (Overlander)](https://www.amazon.co.uk/Overlander-Batteries-5000mAh-Supersport-Models-connector/dp/B0FXMY7X42) · [Seeed STS3215 C001 spec](https://www.seeedstudio.com/STS3215-19kg-cm-7-4V-Serial-Servo-p-6338.html) · SKYRC B6neo (1–6S balance charger).

---

# Appendix — draft synthesis + GPT-5.5 adversary

## Synthesis

Recommendation saved to `battery_rec.md`. Contents below.

# Hexapod Battery Recommendation (18x STS3215, ~2.5 kg, flat-7.4V rail)

## 1. Chosen spec
**3S LiPo / 5000 mAh / 35C / XT60 connector.**

- **3S, not 2S** because the servo rail is a *flat 7.4 V buck output*. A 3S pack stays **12.6 V (full) -> ~9.9 V (empty)** — always **above** 7.4 V, so a simple **step-DOWN buck** holds the rail rock-solid across the whole discharge. A 2S pack (8.4 V -> 6.0 V) sags **below** 7.4 V for most of its range, forcing a rarer/hotter/pricier **40 A+ buck-BOOST**.
- **35C is plenty** (not the constraint): 35C x 5 Ah = **175 A continuous / 325 A burst** vs a ~35 A pack-side worst-case stall and ~8 A walking draw. Buy for capacity/robustness, not C.
- **XT60** matches the SKYRC B6neo ecosystem and every UK RC pack; rated ~30 A continuous / ~60 A burst — covers walking easily and the brief stall near its limit.

## 2. THE product to buy (+ backup)

**BUY: Overlander Supersport Pro 5000mAh 11.1V 3S 35C LiPo (XT60)**
- Shop: **Overlander** (overlander.co.uk, UK manufacturer/retailer) — in stock
- Price: **GBP 44.99-45.98** (XT60 variant)
- Weight: **343 g** · Dims: **138 x 42 x 27 mm** · 55.5 Wh · JST-XH balance lead · 10 AWG
- URL: https://overlander.co.uk/product/5000mah-11-1v-3s-35c-supersport-pro-lipo-battery/
- **Confirm XT60 is selected at checkout** (connector is per-order).

**BACKUP (same pack, stock redundancy / Prime): Amazon.co.uk, sold by Overlander**
- Price: **~GBP 45** (mirrors RRP — verify the specific listing before buying)
- URL: https://www.amazon.co.uk/Overlander-Batteries-5000mAh-Supersport-Models-connector/dp/B0FXMY7X42
- Other UK stockists: King's Lynn Model Shop, Howes Models, RCModelz.

## 3. Lighter option (weight/CG-sensitive)

**Overlander Supersport Pro 3350mAh 11.1V 3S 35C LiPo (XT60)**
- Shop: Overlander — in stock · Price: **GBP 34.99-35.99**
- Weight: **228 g (~115 g lighter)** · Dims: **137 x 43 x 17 mm** · 37.2 Wh
- URL: https://overlander.co.uk/product/3350mah-11-1v-3s-35c-supersport-pro-lipo-battery/
- Trade: ~20 min walking vs ~30 min for the 5000. C-rating (117 A cont / 217 A burst) still ~3x worst-case draw. Same simple step-down buck path. Pick if the ~2.5 kg mass ceiling / top-heaviness matters more than runtime — or keep it as a hot-swap spare.

**Runtime (usable ~80%):** 5000 mAh ≈ **30 min continuous walking** (~8 A pack), hours idle. 3350 mAh ≈ **20 min walking**.

## 4. Fit to the regulate-to-7.4V plan

- The **buck regulator MUST accept >=12.6 V input** (3S full charge) and deliver **>=40 A continuous** at 7.4 V, with margin. Undersizing the *regulator* (not the battery) is the most likely failure point.
- With 3S, the regulator only ever **steps DOWN** 12.6 V -> 9.9 V input to a flat **7.4 V** out — no boost stage needed. (If you ever went 2S/8.4 V, the regulator would have to **buck-boost** because input crosses 7.4 V — avoid.)
- **Never connect the pack directly to the servos.** Raw 3S (12.6 V) and raw 2S (8.4 V) both exceed the STS3215 7.4 V rating and would destroy them. The regulated flat-7.4 V rail is mandatory at all times.
- Set the regulator/BMS **low-voltage cutoff at 3.3-3.5 V/cell = 9.9-10.5 V pack**.
- Buck runs hot at the ~35 A stall — heatsink/ventilate it and size for continuous walking current (~8 A pack). Assume ~90% efficiency (real runtime may be 10-20% lower).
- Firmware should current-limit / stagger the gait so all 18 servos never stall simultaneously (keeps XT60 and buck within rating).

## 5. Accessories & safety

- **Strap the pack LOW and CENTRAL** over the body centroid with a positive strap — 343 g is ~14% of all-up mass; an unrestrained pack can tip the hexapod mid-gait. This matters more than the grams.
- **Balance-charge only**, via the JST-XH lead on your **SKYRC B6neo** (charges 1-6S; no new leads needed). The B6neo needs USB-C PD or a DC PSU to hit full charge current for a 5000 mAh pack.
- **Cutoff 3.3-3.5 V/cell; never below 3.0 V.** Store at storage voltage (~3.8 V/cell).
- **Charge and store in the LiPo safety bag; never charge unattended.**
- Verify **XT60 polarity** (female on the pack lead) before first connection — a reversed XT60 is a dead short on a 5 Ah pack.

## GPT-5.5 adversary (verbatim)

GPT-5.5's full output verbatim:

---

The core electrical trade is now clear: a flat 7.4 V rail makes 3S easier for the converter, but it does not prove a 3S 5000 pack is the right robot choice. The weak point is regulator/fault handling, not the pack C-rating.

Read [battery_rec.md](</mnt/data?>) and nearby notes. Verdict: **3S is only "better" if you insist on a flat 7.4 V rail. It is not proven better for the robot.** The recommendation underplays regulator, thermal, CG, and cutoff risk.

**Main refutation**

- **C-rating is not the problem.** ST3215-7.4V is listed at **2.5 A locked-rotor current**, so 18 servos can demand about **45 A at the rail**. A 3S 5000 mAh 35C pack's advertised **175 A** is far above that. But C-ratings are marketing-adjacent; the real bottleneck is the **regulator, wiring, fuse, connectors, and heat**, not the cells.
- **3S reduces input current, but raises consequences.** 45 A at 7.4 V is **333 W output**. At 90% efficiency, pack current is roughly **29 A full / 33 A nominal / 37 A near 9.9 V cutoff**. A 2S buck-boost doing the same rail needs roughly **44-62 A input** across discharge. So yes, for *flat 7.4 V*, 3S buck is electrically easier than 2S buck-boost. That does not make the 3S 5000 pack the right robot battery.
- **The likely "300 W / 20 A" regulator cannot meet the stated need.** If the named regulator is the cart's cheap 300 W / 20 A buck from `synthesis2.md`, it may accept 12.6 V, but it is not a 40 A continuous 7.4 V servo supply. **20 A at 7.4 V is 148 W.** Even "300 W" is only **40.5 A ideal at 7.4 V**, with zero thermal margin, and below the **333 W / 45 A stall** case. This is the most serious hole.
- **Runtime math is hand-wavy.** 3S 5000 is **55.5 Wh nominal**. Usable 80% and 90% regulator efficiency gives about **40 Wh delivered to the rail**. At 7.4 V:
  - 10.8 A rail average = about **30 min**
  - 15 A rail average = about **22 min**
  - 20 A rail average = about **16 min**
  The recommendation's "30 min" only holds if the real walking rail power is around **80 W**. That needs measuring.
- **Weight/CG is not a footnote.** 343 g is about **14% of a 2.5 kg walker**. The 2S 5000 class is usually materially lighter, and the 3S 3350 option has similar Wh to a 2S 5000 but much less mass. On a marginal 18-servo walker, carrying a 3S 5000 for runtime may be the wrong trade unless it is mounted low and central.
- **Flat 7.4 V has no servo voltage headroom.** The ST3215-7.4V variant is specified for **4.0-7.4 V**, with **19.5 kg.cm** and **2.5 A locked-rotor current** listed by Waveshare. A cheap buck overshoot, bad trim pot, or transient above 7.4 V is now a servo-risk event. A regulated **6.0 V rail from 2S** is a cleaner conservative path if the torque is sufficient.
- **Per-cell cutoff is incomplete.** A pack-level 9.9-10.5 V cutoff can hide an imbalanced 3S pack. You need **per-cell monitoring via balance lead** on the robot, not only total voltage at the buck input. A buck/boost rail will mask pack sag until the LiPo is abused.
- **Charging note is mostly OK, but incomplete.** SKYRC says B6neo-class chargers support **LiPo 1-6S**, balance charge/storage modes, and balance current. It still needs the correct **DC or USB-C PD power source**, correct main charge lead, and the JST-XH balance lead connected. Do not treat XT60 alone as "the charging ecosystem."
- **UK price sanity:** I could not cleanly verify the live Overlander/Amazon pages from this environment. As a sanity check, **~£45 for a branded UK 3S 5000 35C** is plausible, not obviously a bargain. The **£35 3S 3350** looks more defensible for this walker. A 2S route may save pack cost and mass, but only if you avoid a high-current 7.4 V buck-boost.

Sources checked: Waveshare ST3215 specs for 7.4 V operating range and 2.5 A locked-rotor current: https://www.waveshare.com/st3215-servo.htm. SKYRC B6neo specs for LiPo 1-6S, balance charge/storage, and input/charge limits: https://www.skyrc.com/b6neo.

**MOST-LIKELY-TO-BITE**

1. **Regulator cannot deliver 7.4 V at 40-45 A continuous/transient without overheating or sagging.**
2. **Flat 7.4 V leaves no overvoltage margin for 7.4 V servos.**
3. **No per-cell cutoff/alarm on the robot; buck hides LiPo abuse.**
4. **343 g pack mounted high shifts CG and worsens gait/thermal margin.**
5. **Runtime estimate assumes low measured walking current that is not proven.**
6. **Balance lead/charge workflow/strain relief not specified enough for a moving hexapod.**