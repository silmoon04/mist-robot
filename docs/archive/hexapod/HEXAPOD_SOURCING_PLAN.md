I have everything I need to produce the definitive, reconciled plan. The Castle CC BEC 2.0 is only 14/15A (peak 20A) — not a 25A-class part, so it's a worse UK fallback than the Hobbywing. The reconciliation is clear: Hobbywing 25A HV is the right part but OOS at the two named UK shops (in stock at CML Distribution UK / HeliDirect), so the budget split-BEC path is the pragmatic default.

---

# DEFINITIVE SOURCING PLAN — 18× STS3215 Hexapod (London E11, GBP)

Reconciled with adversarial web-checks. **The GPT-5.5 pass produced no output (timed out at 400s), so I ran independent web verification on the load-bearing claims instead.** One material error was found and fixed (see §5).

---

## 1. ADD ON ALIEXPRESS — one consolidated order (ideally the servo cart)

| Item | Search term | ~£ |
|---|---|---|
| 5V 3A UBEC (aux logic rail) | `5V 3A UBEC BEC` | 2–4 |
| XT60 power distribution board | `XT60 PDB power distribution board` (high-copper) | 3–6 |
| Inline blade fuse holders ×~6 (per-leg) | `inline ATC ATO fuse holder 16AWG` (10-pk) | 4–7 |
| 1–8S LiPo low-voltage alarm | `1-8S lipo low voltage alarm buzzer` | 1–2 |
| XT60 Y-splitters | `XT60 Y splitter parallel harness` | 3–5 |
| Spare 5264 3-pin bus cables | `5264 3pin servo bus cable double head` | 4–8 |
| Ratcheting crimp tool (SN-28B) | `SN-28B ratcheting crimping tool` | 8–14 |
| Dupont/JST connector + pin kit | `Dupont JST XH connector kit assortment` | 6–12 |
| M2×6 socket screws ×100 | `M2x6 stainless socket head screw` | 2–4 |
| M3 screw + nyloc + washer kit (500–800pc) | `M3 screw assortment box nyloc washer` | 6–12 |
| M3 heat-set inserts ×100 + iron tip | `M3 brass heat set insert soldering tip kit` | 4–9 |
| MPU6050 IMU (buy 2–3) | `GY-521 MPU6050` | ~1 ea |
| VL53L0X ToF sensor | `VL53L0X time of flight module` | 1.5–2.5 |
| PET braided sleeving (assorted roll) | `PET expandable braided sleeving assorted` | 3–6 |

**Buy the higher-copper/higher-spec variant** for anything power-carrying (PDB, fuse holders, Y-splitters, UBEC) — AliExpress current ratings are optimistic. Sensors/fasteners/connectors: cheapest is fine.

**Subtotal ≈ £50–100** (one order, free ship, 1–3 wk — overlaps printing).

---

## 2. BUY IN THE UK

| Item | Shop | Product | £ | Delivery | Verdict |
|---|---|---|---|---|---|
| XT90-S anti-spark loop key | HobbyRC UK | Genuine gold XT90-S (2× female) | ~5.15 (~4.90 @10+) | Royal Mail | **Specialist** (genuine resistor) |
| Inline watt-meter ≥50A | Amazon / FlyingTech | 100–150A 0–60V inline analyser | 15–20 | Prime next-day | **Prime** — pay for accuracy |
| Charger power source | FlyingTech | SkyRC PSA100 20V/5A 100W XT60 | **19.99 ✓verified** | Same/next-day | **Specialist** (mains-safe, matches B6neo) |
| Blue threadlocker | Amazon | Genuine Loctite 243 10ml | ~9–10.5 | Prime | **Prime** — must be genuine |
| Soldering station (PID) | Kunkune UK | YIHUA 937D+ 75W PID | ~39 | Free >£25 | **Specialist** (holds temp on 12/14AWG + XT tabs) |
| Digital calipers 150mm | Amazon | Preciva/Kynup 0.01mm stainless | 9–13 | Prime | **Prime** — cheapest + fast |
| Precision hex driver set | Amazon | Ball-end metric set (Wera 950/9 if splurging) | 4–15 | Prime | **Prime** |
| PETG 1kg | SUNLU UK / eSUN-UK | Matte/HS PETG | ~10–15/kg | Free 3–7d | **Specialist** |
| TPU 95A 1kg | SUNLU UK | TPU 95A 1kg | **~17.99 ✓verified** | Free | **Specialist** (beats Amazon/3DJake) |
| Zip ties | Amazon / Screwfix | Assorted cable-tie pack | 3–5 | Prime / C&C | **Local** |

*Correction vs original plan: SUNLU TPU is now ~£17.99, not £13.49 — the sub-£14 price is gone. Still the cheapest UK route.*

**Bundle into 4 orders:** (a) SUNLU-direct: PETG + TPU. (b) Amazon Prime: watt-meter, Loctite, calipers, hex set, zip ties (+ crimper/inserts if you skip AliExpress). (c) Kunkune: soldering station (add solder/flux to clear £25). (d) HobbyRC + FlyingTech: XT90-S + PSA100.

**Subtotal ≈ £130–180** (excludes regulator).

---

## 3. THE ≥40A 7.4V SERVO-RAIL REGULATOR — the pick

**No single cheap module gives a genuine flat 40A @ 7.4V.** "40/50A" waterproof bucks quote *input* amps; "600W" CC/CV modules do ~15A out. Correct answer: **split the bus — two 7.4V BECs, each feeding 9 servos** (independent halves, ~40–50A total, per-unit thermal margin, graceful degradation, no ORing diodes).

| Tier | Product | Price | Reconciled status |
|---|---|---|---|
| **DEFAULT (budget, recommended)** | 2× HiModel 20A SBEC (7.4V jumper, 20A cont/25A pk) | ~£28 (AliExpress, ~£14 ea) | Buy this. Adds to the consolidated AliExpress order. Verify heatsinking. |
| **Best (if you can wait)** | 2× Hobbywing UBEC 25A HV (alu case, 25A cont/50A pk, 7.4V selectable) | ~£130 | **⚠ OOS at 3DXR AND FlyingTech.** In stock at **CML Distribution UK** and **HeliDirect** — order there or wait for restock. |
| **UK-instant fallback** | Castle CC BEC 2.0 / BEC Pro | £58/ea @ Nexus | Only 14–15A continuous (20A *peak*) — you'd need 3× for margin. Worse value than Hobbywing; use only if you must buy same-day in the UK. |

**Never hard-parallel BEC outputs onto one rail** (voltage mismatch → one unit current-hogs and fails). If you truly need a single common rail, parallel two 25A HV units through Schottky ORing diodes, set to ~7.8–7.9V pre-diode. The split-bus avoids all of this.

**12.6V→7.4V dropout is a non-issue** (ample buck headroom across the whole 3S curve).

### 40A validation (run on ANY unit before trusting it)
1. Set output to exactly **7.4V** no-load.
2. Apply **~40A** load (≈0.185Ω bank / DC load) at 7.4V.
3. Hold **10–15 min** — reject if V sags <7.0V or any part >80°C.
4. Pulse to **45A** — confirm no shutdown/overshoot.
5. Confirm the added fan holds steady-state temp.
6. During the real walk test, watch the inline ≥50A watt-meter — **real continuous draw is likely 8–15A**, far below 40A, validating the 2×20A split. Size for walking, not the 45A momentary stall (LiPo + 4700µF caps absorb it).

---

## 4. SUBTOTALS

- **AliExpress (one order):** ≈ **£50–100** + **regulator £28** (2× HiModel, default) = **~£78–128**
- **UK (tools + filament + specialist):** ≈ **£130–180**
- **If upgrading to 2× Hobbywing 25A HV:** add ~£100 over the budget BECs → regulator ~£130.
- **All-in for missing items:** ≈ **£210–410** depending on regulator tier and tool quality (excludes already-chosen £35 Overlander battery and existing cart items).

---

## 5. RESOLVED DISAGREEMENTS (from web-check, since GPT-5.5 produced nothing)

1. **Hobbywing 25A HV is OOS at BOTH named UK shops (3DXR £64.99 *and* FlyingTech £66.00).** The original plan implied it was orderable at 3DXR — it is not. **Resolution: the budget 2× HiModel 20A SBEC (~£28) becomes the DEFAULT pick;** Hobbywing demoted to "best if you can wait / order from CML Distribution or HeliDirect."
2. **Castle CC BEC 2.0 is not a viable ≥25A UK substitute** — it is 14–15A continuous (20A peak only), £58/unit. Rejected as anything but a same-day fallback.
3. **SUNLU TPU price corrected** £13.49 → **~£17.99** (verified current); still cheapest UK route.
4. **Confirmed verified:** SkyRC PSA100 **£19.99** at FlyingTech; XT90-S genuine at HobbyRC; both PSA100 and TPU sourcing stand.

**Bottom line:** proceed with the 2× HiModel split-bus regulator (add to the AliExpress cart now), run the 40A validation on delivery, and only chase the Hobbywing upgrade if validation shows you want the alu-case thermal margin.

Sources: [FlyingTech PSA100](https://www.flyingtech.co.uk/product/skyrc-psa100-20v-5a-100w-power-supply-adapter-with-xt60/) · [FlyingTech Hobbywing 25A HV (OOS)](https://www.flyingtech.co.uk/product/hobbywing-25a-3-18s-hv-ubec-with-5-2-6-7-4-8-4-output/) · [3DXR Hobbywing](https://www.3dxr.co.uk/collections/hobbywing) · [CML Distribution UK](https://www.cmldistribution.co.uk/product/HW30606000/hobbywing-ubec-25a-hv) · [HobbyRC XT90-S](https://www.hobbyrc.co.uk/xt90-female-anti-spark-connector-2x-female) · [SUNLU TPU UK](https://uk.store.sunlu.com/collections/tpu) · [Nexus Models Castle BEC](https://nexusmodels.co.uk/collections/voltage-regulators-bec)