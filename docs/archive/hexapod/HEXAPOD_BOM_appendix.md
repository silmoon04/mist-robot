# Hexapod BOM — Adversarial + Synthesis Appendix
_Raw working material behind HEXAPOD_BOM_ANALYSIS.md: the draft synthesis, three GPT-5.5 (codex) refutation passes, and the Claude completeness critic._

# Draft synthesis (pre-adversary)

Done. The full analysis is saved to `synthesis.md`. Here is the report verbatim:

# Master Hardware Analysis — 18x Feetech STS3215 (7.4V) Serial-Bus Hexapod

*Lead-systems-engineer synthesis. Verified facts are marked; engineering estimates and guesses are flagged inline.*

---

## 1. Verdict up front

**Your cart was assembled for the wrong kind of servo, and the battery would fry the servos you actually own.** Two hard, build-stopping problems:

1. **PWM-vs-serial-bus mismatch (the big one).** Your STS3215 are **TTL serial-bus** smart servos (Feetech STS protocol: a single half-duplex UART data line, each servo addressed by ID, all 18 daisy-chained on one bus). The cart is built around **2x PCA9685 PWM drivers**, **25x 3-pin PWM extension leads**, **24x 25T hobby horns**, and **1x MG996R** — the entire toolkit for *analog PWM hobby servos*. **A PCA9685 physically cannot command an STS3215** — it emits 50 Hz pulse-width signals, and the STS3215 has no PWM input pin; its signal wire expects structured serial packets. *(Verified — by protocol definition, multiple sources.)* This whole sub-set of the cart is dead weight for your build.

2. **The 3S / 11.1V battery will damage your 7.4V servos.** A 3S LiPo is 11.1V nominal and **12.6V fully charged** — roughly **50–70% over** the 7.4V STS3215's rated ceiling (operating range ~4–7.4V, absolute max ~8.4V). 12.6V is the spec of the *separate 12V STS3215 variant you did not buy*. Over-volting risks cooking the internal driver MOSFETs and motor windings on all 18 servos (~£200 of servos). *(Verified — Feetech/DFRobot/Seeed datasheets + LeRobot "might burn your motors" warning.)* **You need a 2S pack.**

Two secondary issues: the **two B6neo chargers are redundant** (keep one), and several cart items (250A bus bar, 300W buck) are wildly **over-spec** for a ~15–20A robot.

**The good news:** everything *mechanical and algorithmic* you'd learn from the Tazer reference build (3-DOF legs, Pythagoras + cosine-law IK, Bézier C2 gait paths, tripod/ripple gaits, Blender-IK animation pipeline) transfers unchanged. Only the electronics path differs — and the serial-bus path is actually *simpler* (one UART, no per-servo wiring, free position/load/temp/voltage telemetry).

---

## 2. Cart audit table

| # | Item | Verdict | Reason |
|---|------|---------|--------|
| 1 | SKYRC B6neo 2 — 300W charger | **KEEP** | Balance-charges a 2S pack fine; keep this as your single charger (higher headroom). |
| 2 | XT60-F → 4mm banana charge lead | **KEEP** | Standard charger-to-pack lead; works for the 2S pack. |
| 3 | Fireproof LiPo safety bag | **KEEP** | Correct LiPo safety practice; size fits a 2S pack. |
| 4 | 50pcs acrylic mirror stickers | **MAYBE** | Pure cosmetic flair (~0 g). Harmless; add last. |
| 5 | PCA9685 PWM driver ×2 | **REMOVE-WRONG** | PWM/I2C generator — cannot speak the Feetech serial protocol. Cannot drive STS3215 at all. |
| 6 | 4700µF 16V caps (15 total) | **KEEP** | Right idea, right voltage rating. Use ~2× across the servo rail (~10000µF) + one small cap at logic input. You have plenty. |
| 7 | Silicone wire assorted (£1.89) | **KEEP** | Useful for branch wiring; confirm you have a 14AWG-class gauge for the trunk. |
| 8 | Silicone wire assorted (£2.69) | **KEEP** | Same — branch/leg wiring. |
| 9 | Silicone wire assorted (£3.59) | **KEEP** | Same; this set most likely has the heavier gauges for the trunk. |
| 10 | 4-post 250A marine bus bar | **OVER-SPEC** | Built for ~250A boat loads, ~500g+ dead weight; your peak is ~45A. Use a small XT60 PDB / lever-nuts (a few grams). |
| 11 | Inline fuse holder 12AWG 30A | **KEEP** | 30A main fuse is sensible (above ~15–20A continuous, below wire rating). Consider 25A if measured walking draw stays <15A. |
| 12 | Amass XT60BE-M ×2 | **KEEP** | Correct battery connector standard for the 2S pack. |
| 13 | 25pcs 3-pin servo extension leads | **REMOVE-WRONG** | PWM extension leads; wrong wiring/pinout for the half-duplex serial bus. STS3215 daisy-chain with Feetech bus cables. |
| 14 | MG996R analog PWM servo | **REMOVE-WRONG** | A PWM analog servo — does not belong in an all-serial-bus build. Leftover from the PWM assumption. |
| 15 | SKYRC B6neo — 200W charger | **REDUNDANT** | Second charger unnecessary for one 2S pack. Remove or keep only as a spare. |
| 16 | BEAT 3S 2200mAh 11.1V LiPo | **REMOVE-WRONG** | Over-volts the 7.4V servos (12.6V full vs 8.4V max). Also undersized (2200mAh) for 18 servos. Replace with a 2S 5000mAh pack. |
| 17 | 300W 20A buck converter ×3 | **OVER-SPEC** | ~40A capability is ~2× the design-continuous need; heavy/bulky. An 8A/15A-peak UBEC is lighter and sufficient. (Keep one for a 5V logic rail if useful.) |
| 18 | 164pcs heat-shrink assortment | **KEEP** | Genuinely needed for splices/strain relief. No re-buy. |
| 19 | 25T metal disc horns ×24 | **REMOVE-WRONG** | For MG-class PWM servos. STS3215 ship with their own horns; the spline is similar (25T) but you don't need 24 extra. |

**Net removal:** items 5, 13, 14, 15, 16 (wrong/redundant) and downsize 10, 17. Keep the LiPo-safety, fusing, wiring, caps, heat-shrink, and chargers (one).

> Nuance on item 19: the STS3215 output spline is genuinely 25T (MG995/996-compatible), so these horns *physically fit* if you ever want them — they're just not *needed* since each servo ships with horns.

---

## 3. What you MUST add to actually control the servos

The STS3215 bus is **single-wire half-duplex**: the MCU's separate TX/RX must be combined onto one bidirectional line via a tri-state buffer (74HC126/241) or a proper bus-driver board. A bare ESP32 GPIO will not correctly share one wire for TX+RX. Two parts do the job:

| Part | Role | Necessity | Est. £ | Est. g | Notes |
|------|------|-----------|--------|--------|-------|
| **Waveshare "Servo Driver with ESP32"** (ESP32-WROOM + integrated ST/SC bus driver + 0.96" OLED + DC input) | **Brain + bus driver in one.** Drives up to 253 servos over one UART, injects servo power onto the bus, runs Arduino-framework IK/gait, has WiFi/BT/ESP-NOW. Replaces *both* PCA9685s. | **must-have** | 14–22 | ~30–40 | The **exact board class the LeRobot SO-101 uses**. **Feed it 2S/7.4–8.4V, NOT 12V** — its "12V recommended" note is for the 12V servo variant. |
| **Feetech FE-URT-1** USB-to-TTL bus adapter | **One-time commissioning + PC debug.** Set each servo's unique ID (1–18) and baud before daisy-chaining; run Feetech FD / LeRobot tools. | **must-have** | 7–11 | ~13 | Even with the ESP32 board as runtime brain, this is the simplest way to ID 18 servos from a PC. |
| Extra Feetech 3-pin bus cables (PH2.0/5264, assorted lengths) | Daisy-chain 6 legs; servo-supplied leads won't reach. **Not** the cart's PWM leads. | recommended | 6 | ~40 | Connectors at joints are the #1 recurring mechanical failure (SO-101 redesigned joint-3 routing) — strain-relieve and carry spares. |

> **Why not use the ELEGOO ESP32-WROVER cam as the brain?** Its GPIO is consumed by the OV2640 + PSRAM and it's busy streaming MJPEG — essentially no free, safe pins for a servo bus. Keep it vision-only (Section 5).

**Mandatory setup step (easy to miss):** every STS3215 ships as **ID 1**. Assign unique IDs 1–18 *one at a time* with the FE-URT-1 *before* wiring the shared bus, or they collide and nothing responds. Use **SyncWrite** (one broadcast packet sets all 18 targets) for gait, not 18 sequential writes.

---

## 4. Corrected power system

**Topology:** `2S LiPo → XT60 disconnect → 30A inline fuse → anti-spark switch → small XT60 PDB → [servo rail to bus driver] + [5V buck → logic]`. **Common ground across battery / logic / UART is mandatory** — half-duplex serial returns garbage without it.

| Part | Spec | Necessity | Est. £ | Est. g | Notes |
|------|------|-----------|--------|--------|-------|
| **2S LiPo** | 7.4V nom / 8.4V full, **5000mAh, 30–50C**, XT60 | **must-have** | 18–22 | ~260–300 | Correct voltage. 5Ah @ ~10–12A walking ≈ 20–30 min. At 5Ah even 30C = 150A burst, far above ~45A worst case — **no 80C race pack needed.** Buy 2 for hot-swap if budget allows. |
| **Voltage handling** | run direct off 2S, **or** regulate via UBEC | decision | — | — | 2S spans 6.0V to **8.4V (full)** — 8.4V is at/just over the 7.4V-part limit. **Option A (cheapest/lightest):** run direct, never charge to a hot 8.4V. **Option B (safest):** HV-UBEC clamped to 7.4V/6.0V. |
| HV switching UBEC (optional, Option B) | 8A cont / 15A peak, jumper 5.0/6.0/7.4/8.4V | recommended | 10–14 | ~35 | Far lighter than the 300W buck. |
| 5V logic buck/UBEC | 5V 3–5A (a cart buck works) | **must-have** | 0–4 | ~15 | Isolates logic from servo-rail dips → no brownout. **Don't power logic off the servo node.** Add 470–1000µF at its input. |
| Bulk caps | **2× 4700µF 16V** across servo V+ near servos | recommended | 0 (have) | ~30 | You have 15. 16V on 7.4V = >2× derating. |
| Main fuse | **30A** (you have it); 25A if walking <15A | **must-have** | 0 (have) | ~25 | Clears short/multi-stall jam before wires melt. |
| Wire | **14AWG trunk** (~55A), **16–18AWG branches**, silicone | **must-have** | 0 (have) | ~80 | 18AWG handles one leg's 3 servos. |
| Distribution | small **XT60 PDB** or lever-nuts | **must-have** | 4 | ~25 | **Replaces the 250A bus bar** (~500g → a few grams). |
| Switch | **20A+ rocker** or **anti-spark XT90-S** | recommended | 3 | ~20 | Tiny toggles melt at 20A. Anti-spark avoids bulk-cap inrush arc. |
| LiPo low-voltage alarm | 2S–6S buzzer | **must-have** | 1.5 | ~8 | Stops over-discharge / mid-walk brownout. |

**Current budget (per-servo verified; aggregate estimated):** idle ~2.4A total; **walking ~8–15A continuous**; all-18-stall ~45A *sub-second transient*. Design continuous: **~15–20A.** Measure real draw with your multimeter once it walks, then right-size the fuse.

> **Do NOT** reuse the Tazer build's "3S + buck" idea — he abandoned it (buck couldn't supply peak current) and landed on 2S-direct, which is your correct path.

---

## 5. Compute & software path

**Recommended brain: the Waveshare "Servo Driver with ESP32"** as the dedicated motion controller. 18-DOF analytic IK + tripod/wave gait at ~50 Hz is light math. The WROOM ESP32 has **no hardware FPU** but runs published 18-servo gait code fine at 50 Hz. *(Option:* an ESP32-S3 adds an FPU if you later want higher rates — not required.*)* **Avoid an Arduino Mega.**

**Split-brain (optional, HexArth/ZeroBug pattern):** MCU does servo timing + IK + gait; a Pi or the phone does perception/planning over WiFi. Add a Pi only for on-board autonomy beyond the phone.

**ELEGOO ESP32-WROVER cam:** keep as a **vision-only node** on its MJPEG firmware (2.4 GHz is fine). Good FPV eye (~640×480, ~20 fps, ~100–300ms latency) but **not** a real-time obstacle detector. Talks to the MCU over WiFi/ESP-NOW; never runs the servo bus.

**Mi 9 SE phone (on top):** strong high-level brain / teleop screen. Run **SensorServer** → streams its 9-DOF IMU over **WebSocket (JSON)** — *correct the earlier "UDP" memory note* — for orientation/self-leveling; use the AMOLED as the teleop UI; optionally its camera as a better vision source. **WiFi only; never wired to the servo bus.**

**Network caveat:** cam + phone are both 2.4 GHz — put both on the **same AP/hotspot** to avoid contention.

**Firmware/libraries (verified):** bus control via **matthieuvigne/STS_servos**, **workloads/parallax scservo** (SyncWrite — essential), Feetech SCServo lib, or **lerobot/feetech-servo-sdk** (Python). IK/gait engines to adapt: **rasheeddo/hexapod_dev_esp32**, **CoretechR/ZeroBug** (both PWM-written — swap the output layer to STS SyncWrite), and **Waveshare HexArth** (native serial-bus reference).

---

## 6. Additions menu

| Add-on | £ | g | Verdict |
|--------|----|----|---------|
| **MPU6050** (local IMU, I2C) | 2 | 3 | **Recommended** — hundreds of Hz to the MCU for the fast balance loop; phone's 9-DOF is the high-level/redundant sensor. |
| **VL53L0X ToF** ×1–3 | 3 ea | 2 ea | **Recommended** — narrow laser beam beats ultrasonic on a low walker. Struggles in direct sun. |
| Status OLED (SSD1306) | 2 | 5 | **Skip** if buying the Waveshare ESP32 board (has OLED). |
| INA219 power monitor | 2 | 3 | Optional; **default 3.2A shunt can't see servo surge** — use on logic rail or just an ADC divider. |
| WS2812 "eyes" + mirror stickers | 1 | 1 | Optional flair; add after it walks. |
| DFPlayer Mini + speaker | 3 | 12 | Optional; low priority. |
| Foot-contact switches ×6 | 4 | 18 | Optional; 6 flexing wire runs = failure points. Only after gait is solid. |
| BLE gamepad | 22 | 120 | Optional — phone/web UI also works. |

**Phone-on-top weight warning:** 18 servos ≈ **1.0 kg**; + chassis/legs (~0.5–1.0 kg) + 2S pack (~280 g) + electronics (~150 g) = **~2 kg before the phone.** The Mi 9 SE (~165 g) sits **high and on top** — worst place for CG. *(Synthesis estimate:)* a 19 kg·cm tripod hexapod realistically tops out around **1.5–2.0 kg moving mass** before gait/thermals suffer. **Mount the phone low, centered, removable; keep the gait slow.**

---

## 7. Mechanical consumables to buy

*(Fasteners verified from LeRobot SO-101: **M2×6 body, M3×6 horn/brackets**.)*

| Item | Why | £ | g |
|------|-----|----|----|
| **M2×6 screws ×100** | 4 × 18 = 72 to mount servos. | 3 | 60 |
| **M3 screw + nut assortment (300+)** | 18× M3×6 horns + leg/chassis joints. | 7 | 350 |
| M2/M2.5 assortment | Camera/IMU/phone/standoff fixings. | 5 | 150 |
| **M3 heat-set inserts ×50–100** + iron tip | Durable joints in PLA/PETG; pilot ~4.0mm, set vertical/flush. | 5 | 60 |
| **Blue threadlocker (243)** | Gait vibration walks bolts loose. | 2.5 | 25 |
| Mini bearings (size to CAD) ×~20 | Idler side of each leg pivot. **Confirm size first.** | 6 | 40 |
| **TPU 95A** (feet) | Grippy, shock-absorbing tips. | 12 | 600 |
| **PETG** (structural) | Tougher/more heat-tolerant than PLA near warm servos. | 13 | 1000 |
| PET sleeving + zip ties | Bundle/strain-relieve 18 bus cables. | 5 | 120 |

---

## 8. Price & weight roll-up

**Minimum-viable additional spend** (controllable + safe, beyond kept items): Waveshare ESP32 driver £18, FE-URT-1 £9, bus cables £6, 2S 5000mAh £20, LV alarm £1.5, XT60 PDB £4, switch £3, M2/M3 assortments £10, inserts+threadlock £7.5 → **~£79 / ~916 g.** *(Chargers, fusing, caps, wiring, heat-shrink, cam, phone already owned — not re-counted.)*

**Fully-loaded extra:** UBEC £12, 5V buck £0–4, 2nd pack £20, MPU6050 £2, VL53L0X×2 £6, PETG+TPU £25, bearings/sleeving/M2.5 £16, LEDs £1 → **~£82–86 / ~2250 g.** **Fully-loaded total ≈ £161–165.**

**Estimated robot weight:** 18 servos ~1000 g + chassis/legs ~600–1000 g + pack ~280 g + electronics ~200 g + cam ~12 g = **~2.1–2.5 kg without phone; ~2.3–2.7 kg with it.**

**CG/balance:** you're **already near/over the ~1.5–2.0 kg practical ceiling** *before* the phone. Keep prints light (PETG, ~20% infill, ribbed), mount battery + phone **low and centered**, gait slow. (Tazer hit 5 kg vs 3 kg target → that mass directly caused failures.)

---

## 9. Open questions / assumptions to confirm

1. **Exact STS3215 variant** — confirm all 18 are the **7.4V** part (C001 ~5–8.4V / C046 4–7.4V), not the 12V (C047). Decides direct-2S vs UBEC.
2. **Gear-ratio uniformity** — all 18 the same ratio (likely 1:345 for 19 kg·cm) so leg kinematics match.
3. **Direct-2S vs UBEC** — accept the 8.4V ceiling, or clamp to 7.4V? Decide before ordering.
4. **MG996R quantity** — listing was 2/5/10pcs; REMOVE either way, just confirm you're not charged for a 10-pack.
5. **B6neo DC input** — confirm the kept charger has its required mains/DC brick *(guess — unverified for your listing)*.
6. **Bearing sizes** depend on your printed leg-pivot boss — finalize CAD first.
7. **Phone permanent vs removable** — changes your chassis CG design; decide early.

---

**Bottom line:** Pull the **2× PCA9685, 25 PWM leads, 24 horns, MG996R, 3S battery, one charger**; add a **Waveshare ESP32 serial-bus driver + FE-URT-1 + a 2S 5000mAh pack**; keep your fusing/caps/wiring/chargers(one)/safety gear; mind the **~2 kg weight ceiling** with the phone on top. Minimum extra ≈ **£79**; fully-loaded ≈ **£161**.

# GPT-5.5 adversary — electrical / power / compatibility

Read `synthesis.md`. Electrical/power/servo-compatibility attack only.

## Hard Refutations

1. **The voltage conclusion is internally inconsistent.**
   - It says the servos are “7.4V” and 8.4V may be absolute max, then recommends direct 2S while saying “never charge to a hot 8.4V.”
   - That is not a safety control. A 2S LiPo is 8.4V when properly full. Either the exact STS3215 variant is rated for 8.4V, or you must regulate. Do not build around “partially charge the pack.”

2. **The UBEC recommendation is unsafe if it powers all servos.**
   - “8A continuous / 15A peak” is not enough for 18 STS3215 servos.
   - 18 servos can plausibly demand 45A+ during stalls, foot catches, startup twitch, or bad gait tuning.
   - If regulating the servo rail, use a real high-current 7.4V servo BEC/regulator system, or run direct 2S only after confirming 8.4V tolerance.

3. **The controller board must not be treated as power distribution.**
   - A Waveshare/ESP32 serial-servo driver can command the bus.
   - It should not be assumed to carry full 18-servo current through its PCB traces, headers, barrel jack, or screw terminals.
   - Servo power needs a separate fused PDB with multiple injection points.

4. **One long daisy chain is fragile.**
   - Data can be bused, but power should not flow servo-to-servo through thin pigtails.
   - Use per-leg power branches or multiple rail injection points.
   - Long high-current ground return will cause UART errors through ground bounce.

5. **The current budget is too optimistic.**
   - “8-15A walking” may happen on a light, tuned robot.
   - A 2 kg+ hexapod with 18 small serial servos will hit much uglier transients.
   - Design wiring, connectors, fuses, and brownout margins around stall/fault cases, not only walking average.

6. **A single 30A fuse is incomplete protection.**
   - A 30A main fuse protects the battery lead/trunk.
   - It does not protect one thin leg branch, one servo cable, or one shorted connector.
   - Add branch fusing per leg or per power group.

7. **The 30A inline holder itself is suspect.**
   - Cheap blade fuse holders often melt before behaving cleanly at sustained high current.
   - It must be genuine 12AWG or 10AWG, mounted close to the battery, with correct crimping and strain relief.

8. **“14AWG trunk = 55A” is too casual.**
   - Ampacity depends on insulation, length, bundling, temperature, and connector bottlenecks.
   - XT60 is fine. Tiny servo connectors are not.
   - The weak point is likely connector heating and voltage drop, not the copper trunk alone.

9. **Lever-nuts are a bad mobile-robot default.**
   - They are convenient on a bench.
   - A walking robot vibrates, flexes, and lands hard.
   - Prefer soldered PDB pads, proper crimped terminals, XT connectors, or locking screw terminals with strain relief.

10. **The PCA9685 removal is correct, but the replacement warning is incomplete.**
   - You need a Feetech-compatible TTL half-duplex serial bus interface.
   - Not RS485.
   - Not Dynamixel unless explicitly compatible.
   - Not LewanSoul/LX-16A unless the protocol and pinout match.
   - Not “serial servo controller” generically.

11. **ESP32 GPIO direct-to-servo-bus is risky.**
   - The bus is half-duplex TTL.
   - You need direction control/tri-state behavior and voltage tolerance.
   - Many servo signal lines are 5V TTL; ESP32 GPIO is not 5V tolerant. A real bus driver board matters.

12. **The FE-URT-1 is not enough by itself for powered testing.**
   - Do not power high-torque servos from USB.
   - Use external fused 2S/regulated servo power when commissioning.
   - Connect ground between adapter and servo power.

13. **The ID setup warning is correct but underplays the failure mode.**
   - If all 18 servos share ID 1 on one bus, command/response collisions are expected.
   - Commission one servo at a time.
   - Record ID, physical joint, zero offset, direction, min/max angle, and voltage/current limits.

14. **No brownout design is specified.**
   - ESP32s brown out easily when the servo rail sags.
   - Logic must have a separate 5V buck from the battery side, with local capacitance.
   - Camera/ESP32 and servo ground must meet cleanly, not through a high-current servo return path.

15. **Bulk capacitors are not a substitute for current delivery.**
   - 2x 4700uF helps with spikes.
   - It will not fix an undersized regulator, thin branch wiring, bad connectors, or stalled legs.
   - Add caps near each leg power branch, not only at the battery.

16. **No reverse-polarity or misplug protection is discussed.**
   - XT60 handles battery polarity if soldered correctly.
   - 3-pin servo bus connectors can still be miswired.
   - A reversed servo power plug can kill multiple servos instantly.

17. **Low-voltage buzzer alone is not enough.**
   - It screams after sag has already happened.
   - Firmware should read pack voltage and reduce torque/stop gait before brownout.
   - LiPo over-discharge under walking load will damage the pack and cause resets.

18. **The 300W buck dismissal is wrong.**
   - It is not “over-spec” if considered for the servo rail; it may actually be under-real-world peak or thermally fake.
   - Cheap “300W 20A” buck modules often require airflow, heat sinking, and optimistic lab conditions.
   - For logic, it is oversized. For 18 servos, it is not automatically safe.

19. **The 5V logic buck must be specified.**
   - Need 5V 3A minimum for ESP32 + camera + sensors.
   - Prefer 5V 5A with low ripple.
   - Do not hang camera power off the servo bus driver board.

20. **The runtime estimate is optimistic.**
   - 5Ah at 12A is 25 minutes ideal.
   - Usable LiPo capacity under high current is lower.
   - Expect closer to 10-20 minutes depending gait, mass, terrain, and servo temperature.

21. **The phone-on-top decision worsens power safety.**
   - More mass means more current, more stalls, more heat, more brownouts.
   - Treat the phone as a power-budget risk, not just a CG issue.

22. **Servo thermal/current protection is missing.**
   - Smart servos can report temperature/load/voltage.
   - Firmware must actually read and act on it.
   - Add shutdown rules for over-temp, low voltage, overload, and repeated command timeout.

23. **No emergency kill is specified.**
   - A hexapod with 18 powered joints needs an accessible battery disconnect.
   - Software stop is not enough.
   - Use an XT90-S/XT60 arming loop or proper DC-rated switch.

24. **No pre-power checks are specified.**
   - Before plugging in all 18 servos: verify rail voltage, polarity, fuse continuity, idle current, bus comms, and one-servo motion limits.
   - Powering all 18 with unknown IDs and unknown limits is how servos get cooked.

## Missing Electrical Items

| Missing item | AliExpress search term | Rough GBP |
|---|---:|---:|
| Feetech-compatible USB servo programmer | `FE-URT-1 Feetech STS3215 USB servo programmer` | £8-13 |
| Feetech-compatible ESP32 bus controller | `Waveshare ESP32 servo driver ST3215 STS3215` | £16-25 |
| Correct 3-pin STS/SC servo cables | `Feetech STS3215 3 pin servo cable 5264` | £4-8 |
| 2S 5000mAh LiPo XT60 | `2S 7.4V 5000mAh LiPo XT60 30C` | £18-30 |
| Real 5V logic UBEC | `5V 5A UBEC 2S 6S RC` | £3-7 |
| High-current 7.4V servo BEC, only if regulating servos | `7.4V 20A HV servo BEC RC` | £12-25 |
| XT60 PDB | `XT60 power distribution board 60A` | £3-8 |
| Branch fuse block | `6 way mini blade fuse block 12V` | £4-9 |
| Mini blade fuse assortment | `mini blade fuse assortment 5A 10A 15A 20A 30A` | £2-5 |
| Proper waterproof main fuse holder | `12AWG waterproof blade fuse holder 30A` | £2-5 |
| XT90-S anti-spark arming connector | `XT90S anti spark connector male female` | £2-5 |
| XT60 silicone pigtails | `XT60 14AWG silicone wire pigtail` | £3-6 |
| RC watt meter for real current testing | `150A RC watt meter power analyzer XT60` | £8-15 |
| Voltage sense module for firmware cutoff | `0-25V voltage sensor module Arduino` | £1-3 |
| Better current sensor than INA219 | `INA226 current sensor 50A shunt module` | £4-8 |
| LiPo low-voltage alarm | `2S 3S 4S LiPo low voltage alarm buzzer` | £1-3 |
| Low-ESR capacitor board or extra rail caps | `4700uF 16V low ESR capacitor module XT60` | £3-7 |
| Ferrule/crimp kit for screw terminals | `wire ferrule crimping tool kit` | £8-14 |
| Adhesive heat shrink for power joints | `adhesive lined heat shrink tube assortment` | £3-6 |
| Braided cable sleeve for moving legs | `PET braided sleeving 4mm 6mm cable sleeve` | £3-6 |

## MOST-LIKELY-TO-BITE

1. Full 2S at 8.4V into servos whose exact max voltage was never confirmed.
2. Trying to power 18 servos through a controller board or thin daisy-chain cables.
3. Undersized “8A/15A” UBEC on the servo rail.
4. Brownouts from shared servo/logic power and dirty ground return.
5. All servos left at ID 1 on the same bus.
6. Cheap fuse holder, switch, or connector heating before the fuse clears.
7. No branch fusing, so one leg short can melt small wiring.
8. Fake/optimistic LiPo C rating and fake/optimistic buck/BEC current rating.
9. Long TTL bus with bad grounding causing intermittent command/telemetry failures.
10. No firmware limits for voltage, temperature, overload, timeout, and low-pack shutdown.

# GPT-5.5 adversary — completeness / missing parts

The synthesis fixes the obvious PWM/3S errors, but it still is not a complete build BOM. Worse: it underplays the power-distribution problem.

Sources checked: Waveshare says the 7.4V ST3215 variant is **4V-7.4V**, 2.5A locked-rotor, 1Mbps default baud, feedback capable, and warns that many servos need an adequate power solution. The ESP32 driver board has a **5.5×2.1mm DC jack**, 6-12V input, and input voltage must match servo voltage.  
Links: https://www.waveshare.com/st3215-servo.htm and https://www.waveshare.com/wiki/Servo_Driver_with_ESP32

**Hard Corrections**
- The "direct 2S LiPo is acceptable if careful" line is unsafe for a stated **7.4V** STS/ST3215. A full 2S LiPo is **8.4V**. Waveshare lists the 7.4V variant as **4-7.4V**, not 8.4V. Do not run unregulated 2S unless the exact servo label/datasheet explicitly says 8.4V max.
- The suggested **8A/15A UBEC** is underbuilt. Eighteen servos at 2.5A locked-rotor is **45A**. You do not size the rail for ideal walking only.
- Do not feed the whole hexapod through the Waveshare board's barrel jack. A 5.5×2.1mm jack and small PCB traces are not a 20-45A power bus.
- "One UART controls 253 servos" is not a wiring design. Data can daisy-chain; power must be injected in multiple places.
- Generic "Feetech bus cables" is not enough. You need exact ST/SC/STS 3-pin cables, spares, and a way to break out/inject power.
- The synthesis forgot the charger PSU issue. Many B6neo chargers need an external DC supply. Without it, the charger is just a brick.
- The phone/ESP32-CAM plan omits stable 5V power, mounts, USB cables, and strain relief.
- The mechanical BOM is still thin: no horn screw spares, servo-body screw verification, inserts tooling, drill bits, solder tools, crimp tools, or recovery/debug gear.

**Still Missing AliExpress Parts**
| Missing item | AliExpress search term | Rough GBP |
|---|---:|---:|
| High-current regulated servo rail, not tiny UBEC | `7.4V 30A UBEC high current BEC RC servo power supply` | £18-35 |
| Alternative split rails, 3 modules | `DC DC buck converter 8.4V to 7.4V 15A adjustable` | £6-12 each |
| 2S LiFePO4 pack, safer voltage than LiPo | `2S LiFePO4 battery 6.6V 5000mAh XT60` | £25-45 |
| Known-good 2S LiPo only if using regulator | `2S 5000mAh 50C LiPo XT60` | £18-30 |
| XT60 power distribution board | `XT60 power distribution board 6 output high current` | £4-8 |
| XT30/XT60 pigtails for leg branches | `XT30 connector pigtail silicone wire 16AWG 10 pairs` | £4-7 |
| Per-leg fuses, not only one main fuse | `mini blade fuse holder inline 10A 15A 16AWG` | £4-8 |
| Fuse assortment | `automotive mini blade fuse assortment 5A 10A 15A 20A 30A` | £2-5 |
| Anti-spark main connector | `XT90S anti spark connector pair` | £2-5 |
| Main removable kill loop | `XT60 loop key switch RC battery disconnect` | £3-7 |
| DC barrel-to-wire pigtail for Waveshare board only | `5.5x2.1mm DC male pigtail silicone wire` | £1-3 |
| ST/SC/STS servo cables, several lengths | `Feetech STS3215 servo cable 3 pin 100mm 200mm 300mm` | £5-15 |
| Servo bus Y-splitter / extension spares | `SCServo 3 pin Y cable ST3215` | £4-10 |
| Correct crimp housings, if making cables | `Feetech servo 3 pin connector kit SC ST servo` | £5-12 |
| JST/Molex crimp tool | `SN-28B crimping tool JST PH XH Dupont` | £8-16 |
| Ferrules for screw terminals | `wire ferrule assortment crimp tool kit` | £8-15 |
| WAGO-style lever connectors for bench/debug only | `WAGO 221 compact lever connector assortment` | £4-9 |
| 12AWG/14AWG silicone wire, real gauge | `12AWG silicone wire red black 5m` | £8-14 |
| 16AWG silicone branch wire | `16AWG silicone wire red black 5m` | £5-10 |
| Balance lead extension | `2S JST XH balance extension cable` | £2-4 |
| LiPo checker/alarm | `2S 3S 4S LiPo low voltage buzzer alarm` | £1-3 |
| Inline wattmeter | `RC watt meter power analyzer 150A XT60` | £8-15 |
| Bench current limiter / smoke stopper | `XT60 smoke stopper resettable fuse RC` | £5-10 |
| Multimeter if not already owned | `ANENG digital multimeter 9999 counts` | £8-18 |
| USB logic analyzer for UART bus debug | `24MHz 8 channel USB logic analyzer Saleae compatible` | £5-10 |
| FE-URT-1 or compatible bus adapter | `Feetech FE-URT-1 USB TTL servo programmer` | £8-15 |
| USB-C data cables, not charge-only | `USB C data cable short 30cm 1m` | £2-5 |
| B6neo DC PSU, if missing | `24V 10A power supply XT60 for B6 charger` | £15-28 |
| LiPo charging board/safe box | `LiPo battery charging fireproof box bag` | £5-15 |
| Battery straps | `RC battery strap 20mm 250mm lipo strap` | £2-5 |
| M2 servo-body screw kit | `M2 x 6 stainless steel screw 100pcs` | £2-4 |
| M3 horn screw kit | `M3 x 6 button head screw 100pcs` | £2-5 |
| M3 nyloc nuts | `M3 nylon lock nut 100pcs` | £2-4 |
| M3 heat-set inserts | `M3 brass heat set insert 4x5x5 100pcs` | £3-7 |
| Heat-set insert soldering tip | `M3 heat set insert soldering iron tip` | £2-5 |
| 1.5/2/2.5mm hex drivers | `hex screwdriver set 1.5 2.0 2.5 3.0mm RC tools` | £5-12 |
| Threadlocker | `Loctite 243 blue threadlocker 10ml` | £3-7 |
| TPU feet material | `TPU 95A filament 1kg black` | £10-18 |
| PETG structural filament | `PETG filament 1kg black` | £10-16 |
| Braided sleeving | `PET braided cable sleeve 4mm 6mm 10mm` | £3-8 |
| Small zip ties and adhesive mounts | `nylon zip tie adhesive cable mount assortment` | £2-5 |
| ESP32-CAM stable 5V regulator | `5V 3A buck converter UBEC RC` | £2-6 |
| IMU, if doing balance | `MPU6050 GY-521 module` or `BNO055 module` | £2-18 |
| Spare servos | `STS3215 7.4V serial bus servo` | £13-20 each |
| Spare horns/servo arms, exact ST3215 fit | `ST3215 servo horn metal arm` | £4-10 |
| Spare servo cable sockets | `ST3215 servo connector cable kit` | £5-12 |

**MOST-LIKELY-TO-BITE**
1. Unregulated 2S LiPo over-volting "7.4V" servos at 8.4V full charge.
2. Trying to power 18 servos through the Waveshare barrel jack or one daisy-chain.
3. Undersized UBEC/buck causing brownouts, resets, or servo dropouts under foot contact.
4. Wrong 3-pin cable/connectors; generic PWM extensions are not a validated STS bus harness.
5. All servos defaulting to the same ID and colliding on the bus.
6. No wattmeter/current measurement, so fuse/regulator choices are guesses.
7. No charger PSU for the B6neo.
8. No strain relief on moving leg cables.
9. Missing screws/inserts/locknuts causing mechanical loosening before software is even relevant.
10. No spare STS3215, cable, horn, or adapter; one failed joint stops the entire robot.

# GPT-5.5 adversary — waste / redundancy / weight

The synthesis catches the obvious PWM/3S mistakes, but it still leaves several expensive failure paths.

**Factual/engineering problems in `synthesis.md`**

- The voltage advice is internally inconsistent. It says 7.4V servos must not exceed ~7.4V, then recommends direct 2S, which is 8.4V fully charged. For STS3215 variants rated 6-8.4V, direct 2S is fine. For variants capped at 7.4V, it is not. Confirm the exact label before buying power parts.
- The "8A continuous / 15A peak UBEC" recommendation is too small for 18 servos. If you regulate the servo rail, use a real high-current 7.4V BEC/regulator, or run direct 2S after confirming the servos tolerate 8.4V.
- "Waveshare drives 253 servos" is protocol capacity, not power capacity. Do not feed all servo current through a small controller PCB or one daisy-chain.
- The current budget is optimistic. Design wiring/distribution for ugly peaks, not "walking average." A jammed leg can make the neat math irrelevant.
- The weight roll-up is misleading: it counts whole screw assortments and filament spools as robot mass, then also estimates printed part mass separately.
- "Keep the 300W charger" is wasteful. A 2S 5000mAh pack at 1C is only ~42W. The 200W charger is already enough if it has a proper PSU.
- The XT60 charge lead gender must be checked. Wrong XT60 gender can leave live exposed pins.
- The servo-body screw claim is CAD-specific. Do not assume M2x6 from LeRobot applies to your hexapod brackets.
- Phone-on-top is bad mass placement. Use the phone offboard unless absolutely required.

**Cart items to cut or replace**

| Cart item | Attack |
|---|---|
| `2x PCA9685` | Useless for STS3215 serial servos. Remove. |
| `3S 2200mAh LiPo` | Wrong voltage. Remove. Buy 2S. |
| `MG996R` | Wrong control type and mechanically irrelevant. Remove. |
| `25x PWM servo extensions` | Likely wrong connector and too thin for servo power. Remove unless cutting for bench wiring. |
| `24x metal 25T horns` | Duplicated, heavy, hole pattern may not match CAD. Buy only if the exact horn geometry is required. |
| `Second B6neo charger` | Redundant. One charger is enough. |
| `250A marine bus bar` | Bulky, exposed, mechanically awkward. Replace with XT60 PDB/splitter. |
| `300W buck converters x3` | Not a trustworthy servo regulator. Keep at most one for logic testing; use a real UBEC/BEC for 5V. |
| `Acrylic mirror stickers` | Pure dead weight and scratch/crack risk. Remove. |
| Assorted silicone wire | Do not assume it includes usable 14/16AWG. Verify gauge. Many cheap kits are too thin. |

**Missing items the synthesis still under-specifies**

| Missing item | AliExpress search term | Rough GBP |
|---|---:|---:|
| Serial servo controller | `Waveshare ESP32 serial bus servo driver ST3215` | £15-25 |
| USB servo programmer | `FEETECH FE-URT-1 STS3215 USB TTL servo programmer` | £7-12 |
| Correct bus cables | `FEETECH STS3215 3P servo extension cable` | £4-10 |
| Spare connectors | `HY2.0 3P plug cable kit STS3215` or `PH2.0 3P servo cable kit` | £3-7 |
| Crimp tool | `SN-01BM JST PH2.0 crimp tool` | £8-15 |
| 2S battery | `2S 7.4V 5000mAh 30C XT60 LiPo` | £18-30 |
| Charger PSU | `24V 6A power supply XT60 B6 charger` | £10-20 |
| Low-voltage alarm | `2S 3S 4S LiPo low voltage buzzer alarm` | £1-2 |
| Watt meter | `RC 150A watt meter power analyzer XT60` | £5-10 |
| Lightweight distribution | `XT60 power distribution board 6 output` | £3-7 |
| Kill switch | `XT90S anti spark loop key switch` | £3-6 |
| Real logic supply | `5V 5A UBEC RC BEC` | £3-6 |
| Servo rail regulator, only if needed | `7.4V 20A 30A UBEC HV BEC` | £8-18 |
| Heavy wire | `14AWG silicone wire red black 1m` | £2-5 |
| Branch wire | `16AWG 18AWG silicone wire red black` | £2-5 |
| Battery retention | `RC LiPo battery strap non slip pad` | £2-4 |
| Cable labels | `numbered heat shrink cable marker` | £2-4 |
| Cable protection | `PET braided cable sleeve 4mm 6mm` | £2-4 |
| Washers/nylocs | `M3 stainless washer nyloc nut assortment` | £3-6 |
| Electronics standoffs | `M3 nylon standoff screw kit` | £2-5 |
| Spare servo gears/servo | `STS3215 metal gear replacement` / `Feetech STS3215 servo spare` | £4-14 |
| Rubber feet, lighter than TPU spool | `M3 rubber anti slip feet robot` | £2-5 |
| Better IMU than MPU6050 | `ICM-20948 9DOF IMU module` | £4-8 |

**Cheaper/lighter hardening**

- Use one charger, not two.
- Use one 2S pack onboard, not spare packs mounted to the robot.
- Use the phone offboard. Saves ~165g high above the roll center.
- Use XT60 PDB or soldered harness instead of the marine bus bar.
- Use included/lightweight horns unless the CAD requires metal discs.
- Print sparse PETG ribs, not solid PLA blocks.
- Run per-leg power branches; do not rely on a long servo daisy-chain for high current.
- Put the fuse close to the battery, not somewhere convenient downstream.
- Label every servo ID and cable before assembly.

**MOST-LIKELY-TO-BITE**

1. Exact STS3215 voltage variant not confirmed before choosing direct 2S vs regulated 7.4V.
2. Servo current routed through controller PCB, thin extensions, or one long daisy-chain.
3. Undersized/fake buck converter causing brownouts under gait load.
4. All 18 servos still on default ID `1`.
5. Robot too heavy: phone, metal bus bar, metal horns, dense prints.
6. Wrong connector family on "servo extension" leads.
7. Charger missing a suitable DC PSU or using wrong XT60 gender.
8. Fasteners loosening or pulling out of plastic because inserts/threadlocker/washers were skipped.
9. Branch wires unfused and too thin for a short.
10. Heat and torque margin ignored because "19kg-cm" was treated like payload capacity.

# Claude completeness critic

{
  "factual_errors": [
    "VOLTAGE CEILING IS OVERSTATED AS A FACT. The draft repeatedly asserts the 7.4V STS3215 has an 'absolute max ~8.4V' and uses that to bless running 'direct off 2S' up to 8.4V full. Multiple sources cap the 7.4V part at 4-7.4V (Feetech C046 datasheet via indystry.cc) or 6-8V (LeRobot listings) operating, with NO published 8.4V absolute-max for the C001/C046 7.4V variant. 8.4V appears to be conflated from generic 2S-LiPo full-charge voltage and from the separate 6-8.4V SC-series servos. The honest statement is: 8.4V is ABOVE the rated 7.4V ceiling, not 'at/just over.' Sources: indystry.cc/sts3215-best-motors-for-your-next-robot (4-7.4V for C046); feetechrc.com datasheet PDF; LeRobot listing wording '6-8V, 7.4V recommended.'",
    "THE DECISIVE REAL-WORLD FACT THE DRAFT NEVER STATES: the official LeRobot SO-101/SO-ARM100 powers the 7.4V STS3215 from a 5V supply (5V for the 7.4V motors, 12V for the 12V motors). The draft's entire power section steers toward 2S-direct at 7.4-8.4V, i.e. running the servos at or ABOVE their ceiling continuously, when the authoritative deployment of these exact servos deliberately runs them at 5V. This inverts the safety recommendation. Source: huggingface.co/docs/lerobot/so101 and wiki.seeedstudio.com/lerobot_so100m_new ('5V for the STS3215 7.4V motors').",
    "SELF-CONTRADICTION BETWEEN THE BRAIN BOARD AND THE BATTERY PLAN. The draft recommends the Waveshare 'Servo Driver with ESP32' AND tells the user to 'Feed it 2S/7.4-8.4V, NOT 12V.' But that board's input range is 6-12V (verified, Waveshare wiki + Amazon), and it passes the DC input straight to the servo bus with no per-rail regulation. So: (a) it CANNOT supply the 5V that LeRobot uses to safely run 7.4V servos - 5V is below the board's 6V floor; (b) a 2S pack sags toward 6.0V empty, right at the board's minimum, risking brownout; (c) to stay <=7.4V at the servos you must never charge the 2S above ~3.7V/cell, wasting most of the pack. The board+battery pairing as written is internally inconsistent. Source: waveshare.com Servo Driver with ESP32 product/wiki pages, input 'DC 6-12V.'",
    "ALL SERVO CURRENT THROUGH ONE SMALL BOARD IS UNADDRESSED. The draft routes the whole servo rail (walking ~8-15A, stall transients to ~45A) through the Waveshare ESP32 board's DC input and bus connectors. Waveshare's own docs warn 'due to the high power of the servos... consider whether the power supply solution is enough' and the board's PH2.0/screw input and traces are not rated for tens of amps. For an 18-servo hexapod you must inject servo power into the bus EXTERNALLY (power-injection split / Y from the main PDB straight to the leg buses) and use the board mainly for signal. The draft's 'injects servo power onto the bus' line implies the board can be the sole power path, which it cannot at hexapod current. Source: waveshare.com wiki note on high-power/too-many-servos.",
    "STALL-CURRENT NUMBER IS RIGHT BUT MISLABELED. The draft says 'all-18-stall ~45A sub-second transient' as if 45A is only a rare transient. Verified stall current is 2.5A/servo @7.4V (x18 = 45A), and a leg jam or aggressive gait can hold several servos near stall for longer than 'sub-second.' Idle is ~150mA x18 = 2.7A (draft says 2.4A - minor). The fuse/wire sizing is OK, but the framing under-weights sustained multi-servo stall during a stuck-leg event. Source: STS3215 spec, stall current 2.5A @7.4V (multiple listings, DFRobot/RobotShop).",
    "FE-URT-1 PRICE IS A BIT LOW. Draft lists ~£9; actual AliExpress is $13.68 (~£10.8) for the FE-URT-1; the newer FE-URT-2 is pricier. Minor but worth correcting in the roll-up. Source: aliexpress.com/item/32965635099.html ($13.68)."
  ],
  "missing_items": [
    {
      "item": "Dedicated 5V high-current PSU or properly-sized buck for the SERVO rail (the LeRobot-correct way to power 7.4V STS3215)",
      "why": "The single biggest missing decision. LeRobot runs these exact 7.4V servos at 5V. If the user follows that proven path instead of risky 2S-direct, they need a buck that converts 2S(6-8.4V)->5V at 15-20A continuous. The draft's '300W 20A buck' it tells them to remove is actually the RIGHT class of part for this job. At minimum, keep ONE of the cart's buck converters set to ~5-6V for the servo rail rather than discarding all three.",
      "aliexpress_search_term": "DC-DC buck converter 20A 300W adjustable 5V step down robot",
      "est_price_gbp": 0
    },
    {
      "item": "Anti-spark XT60/XT90-S switch or pre-charge resistor",
      "why": "Draft mentions it in a table but never flags that with ~10000uF of bulk caps the inrush WILL arc and pit a plain rocker switch on every power-up. For an 18-servo build this is near-mandatory, not 'recommended.'",
      "aliexpress_search_term": "XT90-S anti-spark connector self-resetting switch",
      "est_price_gbp": 3
    },
    {
      "item": "Power-injection Y-leads / second feed point for the servo bus",
      "why": "45A peak cannot flow through one bus connector or one end of a daisy chain. You must feed servo power into multiple points (e.g. each leg's 3-servo cluster) from the PDB. Draft never lists the splitter/Y-cables needed to do this.",
      "aliexpress_search_term": "PH2.0 3pin servo power injection Y splitter cable Feetech bus",
      "est_price_gbp": 4
    },
    {
      "item": "USB-C / micro-USB cable for FE-URT-1 and ESP32 flashing",
      "why": "Trivial but genuinely needed to ID the 18 servos and flash firmware; easy to forget and stall the build on day one.",
      "aliexpress_search_term": "USB to USB-C data cable short",
      "est_price_gbp": 1.5
    },
    {
      "item": "Wago-style lever connectors / proper PDB if not using XT60 PDB",
      "why": "Draft says 'lever-nuts' as an aside but doesn't list a part. For 6 leg branches off one trunk these are the clean, rated solution vs the removed 250A bus bar.",
      "aliexpress_search_term": "Wago 221 lever nut connector assortment",
      "est_price_gbp": 3.5
    },
    {
      "item": "Spare STS3215 servo (1-2 units)",
      "why": "The #1 recurring failure on these builds is a stripped gear or dead servo mid-bring-up. With 18 in a chain, one dead servo can block the bus. A spare avoids a multi-week reorder stall and is cheap insurance on a ~£200 servo set.",
      "aliexpress_search_term": "Feetech STS3215 7.4V 19kg serial bus servo",
      "est_price_gbp": 12
    },
    {
      "item": "Inline current/voltage meter (watt meter) for the main lead",
      "why": "Draft says 'measure with your multimeter once it walks' but a multimeter can't read 15-45A safely inline. A 60-130A watt-meter on the main lead gives live current/voltage/mAh and right-sizes the fuse and battery properly.",
      "aliexpress_search_term": "130A watt meter power analyzer XT60 RC",
      "est_price_gbp": 6
    }
  ],
  "over_engineering": [
    "The draft is right to cut the 250A bus bar and downsize, but then UNDERSELLS the one part it tells them to remove that they actually need: the 300W 20A buck. If the user takes the LeRobot-safe 5V-servo path, that buck IS the correct servo-rail regulator. Telling them to remove all three is the inverse error of the bus bar - throwing out a right-sized part. Keep at least one.",
    "Recommending BOTH the Waveshare ESP32 board AND the FE-URT-1 as 'must-have' overstates it. The ESP32 board can itself set servo IDs over USB (it exposes the bus and runs Waveshare's web tool / serial passthrough). The FE-URT-1 is convenient but is a 'recommended', not a hard 'must-have' - you can ID servos with the ESP32 board alone. Don't double-spend if budget is tight.",
    "The 2S 5000mAh 30-50C pack is oversized on C-rating if the servos are run at 5V (lower current at the pack) and even at 7.4V: 5Ah x 30C = 150A, ~3x the 45A worst case. A 5000mAh 25C pack is plenty and cheaper/lighter. Draft already notes 'no 80C race pack needed' but still anchors 30-50C; 20-25C is the honest floor.",
    "Weight ceiling warning is good and should be louder, but the draft's own additions menu (BLE gamepad 120g, DFPlayer+speaker, 6 foot switches, multiple ToF) piles ~150-300g of non-essential mass onto a robot it simultaneously says is already over its ~2kg CG ceiling. The menu should be explicitly gated 'NONE of these until it walks' rather than presented as a shopping list.",
    "Two PCA9685 are correctly cut - but the draft could note the user can RESELL or repurpose them (and the MG996R + 24 horns + PWM leads) rather than treating them as pure dead loss; that softens the ~£20+ sunk cost."
  ],
  "smart_upgrades": [
    "TAKE THE LEROBOT 5V-SERVO PATH, NOT 2S-DIRECT. Power the servo bus from a 2S pack through ONE of the cart's buck converters set to ~5-6V (15-20A). This is exactly how the official SO-101 runs these 7.4V servos, keeps them safely under their 7.4V ceiling forever, removes the '8.4V full-charge will cook them' risk entirely, and reuses a part the draft wanted to bin. Net: safer AND ~£0 extra. (If max torque is wanted, regulate to 7.4V flat via UBEC - never let raw 8.4V hit the servos.)",
    "USE A REGULATED SERVO RAIL SO THE WAVESHARE BOARD GETS A VALID 6V+ INPUT WHILE SERVOS GET 5-7.4V. Because the ESP32 board needs >=6V but passes input straight to servos, the clean architecture is: 2S -> board logic gets 6-8.4V for its own brain, but inject SERVO power separately from a 5-7.4V buck into the bus, NOT through the board's input. This resolves the contradiction the draft left open and protects both the board and the servos.",
    "BUY ONE OR TWO SPARE STS3215 NOW. On an 18-servo single-bus chain, one failed/locked servo can stall the whole bring-up for weeks waiting on a reorder. A £12 spare is the highest-leverage cheap insurance on the entire BOM and the draft omits it.",
    "ADD A 130A INLINE WATT-METER (~£6) on the main lead. It reads live current/voltage/mAh that a multimeter can't safely measure at 15-45A, letting the user right-size the fuse, validate the C-rating, and catch a stalling leg before it browns out the logic. Far higher value than the INA219 the draft lists (whose 3.2A shunt, as the draft admits, can't even see servo surge).",
    "MPU6050 at ~£2 is the single best sensor upgrade and the draft already flags it - reinforce it as tier-1: it gives the fast on-board balance/self-level loop the phone IMU (WiFi-latency-bound) cannot. Pair it with running gait slow until the loop is tuned, given the phone-on-top high-CG mass problem.",
    "ANTI-SPARK XT90-S (~£3) instead of a plain switch: with ~10000uF of bulk caps the draft recommends, every power-on arcs. This is a cheap upgrade that prevents a pitted switch and a startling spark, and should be promoted from 'recommended' to 'buy it.'"
  ],
  "citations": [
    "https://indystry.cc/sts3215-best-motors-for-your-next-robot/",
    "https://www.feetechrc.com/Data/feetechrc/upload/file/20200611/6372749961523760249976542.pdf",
    "https://huggingface.co/docs/lerobot/so101",
    "https://wiki.seeedstudio.com/lerobot_so100m_new/",
    "https://www.waveshare.com/wiki/Servo_Driver_with_ESP32",
    "https://www.waveshare.com/servo-driver-with-esp32.htm",
    "https://www.dfrobot.com/product-2961.html",
    "https://www.robotshop.com/products/magnetic-encoding-servo-sts3215-74v-19kgcm",
    "https://www.aliexpress.com/item/32965635099.html",
    "https://www.seeedstudio.com/STS3215-19kg-cm-7-4V-Serial-Servo-p-6338.html",
    "https://www.waveshare.com/wiki/Bus_Servo_Adapter_(A)"
  ]
}