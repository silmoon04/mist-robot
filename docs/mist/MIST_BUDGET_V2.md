# MIST BUDGET V2 — verified savings ledger + basket configurations

> **Current purchased inventory is now in [MIST_ACTUAL_INVENTORY.md](MIST_ACTUAL_INVENTORY.md).** This file is retained as the savings/pricing history and is no longer the live cart state.

**Date:** 3 July 2026. **Baseline:** ~£605 (excl. printer) per `MIST_MASTER_BASKET.md`.
Every saving below was web-verified and then adversarially judged by an independent GPT-5.5 panel. REFUTED ideas were removed before this file; verdicts shown are SURVIVES (bank it) or UNCERTAIN (check on the day, don't budget on it).

Already-agreed baseline cuts (applied inside the configurations, not re-listed in the ledger):
Zeee 3S 2200 2-pack ~£28 instead of Overlander (−£7, gains a 2nd pack) · basic 60W iron £12–15 (−£20) · one PETG spool now (−£13) · skip SN-28B + Dupont kit + logic analyzer + sleeving (−£25–30) · cheap hex keys (−£5) · optional 12-servo config (−£83, coxa joints deferred).

---

## 1) Savings ledger — ranked by £ saved

| # | £ saves | Verdict | Idea | Verified price + source | Exactly what to do |
|---|---|---|---|---|---|
| F3 | **£44–47** | 🟢 SURVIVES 3/3 | Ender 3 V3 SE open-box instead of £149 new *(printer line — outside the £605 basket, inside project spend)* | **£102.48** Amazon Resale, ASIN B09WR8L93B, confirmed live 3 Jul (amazon.co.uk/s?k=creality+ender&i=warehouse-deals); corroborated by eBay UK SOLD £105.00+£5.88 on 1 Jul (ebay.co.uk/itm/398006866216) | Buy the warehouse unit if the condition note doesn't say "missing parts". Identical model (CR-Touch + direct extruder) with full 30-day Amazon returns. Run self-test + auto-level inside the return window. Only "1+ used offers" — it can vanish; eBay used ~£105–111 delivered is the fallback. May ship with EU plug → £2 UK kettle lead. |
| F2 | **£20–55** (rebate, weeks later) | 🟢 SURVIVES 3/3 | Route the AliExpress order through TopCashback (15% all members) | 15% on item price **excl. VAT/delivery**, confirmed live 3 Jul (topcashback.co.uk/aliexpress-uk). Quidco shows 20% but it's **Premium-members-only and capped at £35/order** (quidco.com/merchant/ali-express) | Click through the portal before checkout. **Critical rule (verified):** any promo code not listed on TopCashback voids the cashback — see F8 for the split that fixes this. Treat as a delayed rebate, not cash off at the till; tracking can fail. |
| F4 | **£15–30** (incremental over baseline coupon allowance) | 🟢 SURVIVES 3/3 | Order inside the live Summer Savings window — **ends 7 July 2026, 23:59 PST** | Tiers confirmed at alitools.io/en/promo-codes + news.astools.app + 2 more aggregators: **AFJCD55 = $55 off $449 / AFJCD40 = $40 off $329 / AFJCD25 = $25 off $209**; UK series **AEUKSS55 = £55 off £449, AEUKSS40 = £40 off £329, AEUKSS25 = £25 off £209, AEUKSS15 = £15 off £120** | One code per checkout, existing users OK. Test the code in-cart **before** paying (codes are "selected products" — a few lines may not count toward the threshold). A £330–449 AliExpress checkout captures £40; ≥£449 captures £55. |
| F9 | **£17.41** | 🟢 SURVIVES 3/3 | Buy 18 servos as **3× 6-packs** instead of 12-pack + 6-pack | Own cart lines: 12-pack £182.99 (£15.25/servo) vs 6-pack £82.79 (**£13.80/servo**); rate corroborated by WowRobo tiers $13.99–15.99/pc for the identical C018 (shop.wowrobo.com) | 3 × £82.79 = **£248.37** vs £265.78. At order time confirm qty 3 holds £82.79 each in-cart (AliExpress sometimes caps discounted qty) and all three show **12V / 30kg / ST-3215-C018** variant text. Screenshot it. If it reprices, fall back to 12+6. |
| F10 | **£11–17** | 🟢 SURVIVES 3/3 | Replace the £21.89 Waveshare "Servo Driver with ESP32" with the **Bus Servo Adapter (A)** driven by the A20 ESP32 DevKitC already in the basket | Pi Hut **£4.80** confirmed but sold out (thepihut.com/products/serial-bus-servo-driver-board); Botland EU €4.50 in stock; Amazon UK B0CJ6TP3TP exists (~£10.90, price not fully verified); also on Waveshare's official AliExpress store (item 1005006054189812) | Delete the £21.89 board; add the adapter (~£5–11 — cheapest is riding it on the AliExpress order). Jumper to A, wire ESP32 TX/RX/GND (Waveshare wiki: "RX-RX, TX-TX"), SCServo library on Serial1 @1,000,000 baud — Waveshare's own documented path, not a hack. Same 9–12.6V input, same barrel jack, servo power never routed through the board anyway. You lose the tiny status OLED + out-of-box web demo; v1 firmware was custom regardless. |
| F7 | **£5–25** (incremental over eBay-used route) | 🟢 SURVIVES 2/3 | Collect a used Ender locally (Gumtree/FBM) from E11 — test before paying | Live Gumtree ads re-verified 3 Jul: **£50 Ender 3 Pro "fully working" Isle of Dogs**, £120 direct-drive Pro in Leytonstone (E11), £90 Maida Vale (gumtree.com/search?q=ender+3&search_location=E11) | Only if you choose used-over-new for the printer. Bring a pre-sliced Benchy on microSD and require it printing before cash changes hands; check bed heats, belts, Mean Well/Creality PSU sticker. Haggle anchor: eBay sold ~£47–74. Honest cost: base/Pro models are manual-levelling — a real beginner skill tax vs the V3 SE. |
| F8 | **£10–22** (overlaps F2+F4 — do NOT add all three) | 🟡 UNCERTAIN (mechanics valid) | Split the AliExpress order in two so code and cashback don't kill each other | Voiding rule verified verbatim on TopCashback; tiers verified (see F4). Adversarial math: split ≈ £52–62 total capture vs £40–55 naive single-order | Checkout A (~£300: servos + adapter) through TopCashback with **no external code**; Checkout B (the rest) carries the best AEUKSS tier it reaches. Same-store items stay in one checkout to keep combined shipping. This is the execution recipe for F2+F4, not extra free money. |
| F13 | £5–15 | 🟡 UNCERTAIN | Missed July 7? Next real windows | Corroborated calendar: **Choice Day runs 1st–7th of every month**; late-Aug clearance ~Aug 18–27. The cited "Anniversary Aug 13–18" was contradicted by two independent calendars (anniversary is March) | Rule: never pay no-coupon prices on a 3-figure AliExpress order — the next window is always ≤3 weeks away. Use for the deferred 6-pack/second wave. Exact codes only publish days before each event. |
| F1 | £0 expected (up to ~£105 lottery) | 🟡 UNCERTAIN | Free hedge: eBay saved-search alerts for a private-seller **12V** STS3215 dump | Cited May 2026 sold precedents (£3.40–5.27/servo) could NOT be independently re-verified (eBay bot-wall); all observed dumps were the **7.4V** variant — zero 12V precedent | Costs nothing: save searches "STS3215 12V", "ST-3215 30kg", UK-located, alerts on, between now and order day. Gate: photo of case label showing **12V + 30KG/ST-3215-C018** before paying; on arrival, FE-URT-1 register read (reg 14 = 140 is CORRECT) + sweep + <1A no-load. Never off-platform payment. If nothing appears by order day, buy as planned — zero delay. |
| F5 | £0 today (~£25 if restocked) | 🟡 UNCERTAIN | WowRobo sells the exact C018 at $13.99/pc (10+) — **currently sold out, all variants** | Re-verified 3 Jul: $15.99/1, $14.99/5, $13.99/10, all "sold out"; UK shipping not shown (shop.wowrobo.com/products/feetech-sts3215-servo-12v-30kg-high-torque-servo-for-so-arm100) | Watch item only. Check once on order day; take it only if in stock AND landed cost (price + shipping + 20% UK import VAT) beats £248.37. Do not wait on it. Their $15.99 single price answers the "spares" question. |
| F16 | ~~£13–14.39~~ | 🔴 EFFECTIVELY KILLED (1 REFUTED + 2 UNCERTAIN) | Delete the £14.39 PDB, solder a 12AWG star junction instead | Deletion arithmetic confirmed, electrically sound — but the panel ruled the two multi-wire high-current splices (7 conductors per polarity) **a beginner soldering trap in a first-soldering build** | **Don't do it.** Keep the PDB. If you want a nibble: a comparable XT60→8×XT30 PDB lists ~£10.05 on AliExpress — swap saves ~£4 with zero skill cost. |

---

## 2) Three basket configurations (running totals)

Shared assumptions: F9 six-pack pricing, F10 adapter swap, all baseline cuts applied, PDB kept (F16 rejected), all safety lines intact.

### Config A — "Full 18-servo, all trims" → **~£480 at checkout (~£468 effective)**

| Block | Contents | £ |
|---|---|---|
| Servos | 3× 6-pack ST-3215-C018 12V/30kg (F9) | 248.37 |
| Control | Bus Servo Adapter (A) ~£6 (F10) — Waveshare ESP32 board deleted | 6.00 |
| Cart rest | B6neo 27.49 · PDB 14.39 · 2× UBEC 9.38 · fuse holders 4.69 · LiPo bag 3.63 · 12/14/16AWG 7.30 · VL53L0X 2.69 · XT60BE-M 1.51 · heat-shrink 1.38 · mirrors 0.77 | 73.23 |
| Additions (trimmed) | A1–A10, A13–A23 with cheap hex (£4) — SN-28B, Dupont, logic analyzer, sleeving skipped | ~111 |
| UK | Zeee 2-pack 28 · PETG ×1 13 · TPU 20 · basic iron 13 · H4 bulbs 7 | ~81 |
| **Subtotal** | | **~£519.60** |
| July code (F4) | AliExpress portion ≈ £438.60 → AEUKSS40 (−£40); nudge cart to £449 → AEUKSS55 (−£55) | **−40 to −55** |
| **At checkout** | | **≈ £465–480** |
| Cashback route (F8 split, instead of full code) | pay ~£505, get ~£37 back later | effective **≈ £468** |

Simplest path: single checkout + AEUKSS40 = **£479.60**. Max-capture path: F8 split ≈ £468 effective (rebate arrives weeks later). **vs £605 baseline: −£125 to −£140, same robot, same safety.**

### Config B — "12-servo budget" → **~£394 at checkout (~£390 effective)**

12 servos = 4 legs × 2 DOF + 4 wheels; coxa joints deferred (already-agreed −£83 route). Upgrade later = one more £82.79 6-pack.

| Block | £ |
|---|---|
| Servos: 2× 6-pack = £165.58 (F9 pricing beats half-a-12-pack) | 165.58 |
| Adapter (F10) + cart rest (as Config A) | 79.23 |
| Additions trimmed (3 fewer 5264 cables/caps) | ~108 |
| UK block | ~81 |
| **Subtotal** | **~£433.81** |
| AliExpress portion ≈ £352.81 → AEUKSS40 | **−40** |
| **At checkout** | **≈ £394** |

Second wave (Aug window, F13): 6-pack £82.79 + 4 caps/cables ~£90 − ~£8 code ≈ **£82 later** when you want the full 18.

### Config C — "12-servo + borrow/used everything" → **~£378 at checkout (~£365 effective)**

Config B, plus: cheap £4 calipers, skip breadboard (−4), use owned USB data cables (−3), velcro/zip instead of straps (−2), single M3 kit (−3). Watt-meter and ALL safety lines kept.

| Block | £ |
|---|---|
| Cart (as Config B) | 244.81 |
| Additions minimal | ~92 |
| UK block | ~81 |
| **Subtotal** | **~£417.81** |
| AliExpress ≈ £336.81 → AEUKSS40 | **−40** |
| **At checkout** | **≈ £378** |
| + F1 lottery IF a 12V dump ever appears (no precedent) | −£105 → ~£273 |

**Printer (outside the basket, all configs):** Amazon Resale V3 SE **£102.48** (F3, best beginner pick — auto-level + returns) or Gumtree collect-and-test **£50–120** (F7, manual levelling tax). vs £149 new.

---

## 3) DO-NOT-CUT list (safety + insurance — non-negotiable in every config)

1. **30A main + 4× 15A branch blade fuses and the 5 inline holders** — the only thing between a wiring fault and a 117A pack.
2. **XT90-S anti-spark loop key** — physical kill switch + no connector arcing.
3. **H4 bulb smoke stopper** (~£7) — limits any first-power-up short to ~5A.
4. **Fireproof LiPo bag** + **low-voltage alarm** — charging and running insurance.
5. **4700µF 25V caps** — 16V caps at 12.6V are at 79% of rating; do not "save" £2 here.
6. **Safety glasses.**
7. **Genuine-store SkyRC B6neo only** — clone chargers are a fire risk.
8. **TPU tires** — required for MIST wheel mode, not deferrable.
9. **Dispute-window insurance:** screenshot variant text at order; unbox check (T0) + FE-URT-1 register read on ALL servos **within AliExpress's 15-day dispute window**. This is why FE-URT-1 ships in wave 1.
10. **Cashback discipline:** never enter a code that isn't listed on TopCashback into a portal-tracked checkout — it silently voids the whole rebate.
11. **Used-servo variant gate (F1):** label photo showing 12V + 30KG before paying; eBay on-platform payment only.

---

## 4) Order timing playbook

**Now → 7 July (the window is live, deadline 7 Jul 23:59 PST):**
1. Fix the cart: 3× 6-pack (verify qty-3 price + variant text), delete Waveshare ESP32 board, add Bus Servo Adapter (A), keep PDB, apply baseline trims.
2. Set the free eBay saved searches (F1). Check WowRobo stock once (F5).
3. Pick a route:
   - **Simple:** one checkout, test AEUKSS40/55 in-cart before paying.
   - **Max capture (F8):** Checkout A (~£300, servos + adapter) via TopCashback, in-app store coupons only, NO external code → ~£37 rebate later. Checkout B (rest) with the best AEUKSS tier. Keep each store's items in one checkout.
4. Buy the UK block (battery, filament, iron, bulbs) any day — no window applies.
5. Printer: grab the £102.48 Amazon Resale V3 SE if still there (30-day returns), else Gumtree £50-collect-and-test, else eBay used ~£105.

**If the window is missed (or for Config B's second wave):**
- Choice Day runs the **1st–7th of every month**; late-August clearance ~**Aug 18–27**. (Ignore the "Aug 13–18 anniversary" framing — contradicted by two calendars; AliExpress anniversary is March.) Never pay no-coupon prices on a 3-figure order — the next window is ≤3 weeks away.

**On arrival (dispute-window clock starts):** T0 variant check + register read every servo (reg 14 = 140 is correct for 12V — don't "fix" it), sweep test, no-load current <1A, wheel-mode spin test — all before printing legs 2–4.
