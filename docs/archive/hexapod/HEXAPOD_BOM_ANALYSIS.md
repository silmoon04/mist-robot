# Master Hardware Report — 18× Feetech STS3215 (7.4V) Serial-Bus Hexapod

*Definitive build deliverable. Reconciles the draft synthesis with three GPT-5.5 adversarial passes and one completeness critic. Disputed facts were settled by web research and are cited inline. Verified vs. estimated is flagged throughout.*

> 🔁 **Two corrections from the later servo trade study (`HEXAPOD_SERVO_TRADESTUDY.md`) override this file:** (1) regulate the servo rail to a **flat 7.4 V, NOT 5–6 V** — 19.5 kg·cm is the 7.4 V figure; at 6 V a walker is torque-starved (~15.8 kg·cm). (2) The cheap "300 W / 20 A" buck is really **~120–150 W by output-current limit** and can't hold the rail under a 30–45 A stall — use a **real ≥40 A regulator, likely 3S → buck-to-7.4 V** (a 2 S buck sags below 7.4 V when the pack is low). Build envelope for the owned 19 kg servos: **≤~2.3–2.5 kg, ≤14 cm foot reach, slow tripod gait, design to SF 2.**

---

## 1. TL;DR

- **Your cart was built for the wrong servo class.** STS3215 are **TTL serial-bus** smart servos (one half-duplex UART, daisy-chained, addressed by ID). The cart's **2× PCA9685, 25× PWM leads, 24× 25T horns, and MG996R** are all PWM-hobby-servo parts. **A PCA9685 physically cannot command an STS3215** — wrong protocol entirely. Cut all of them.
- **The 3S/11.1V battery would cook your servos.** The 7.4V STS3215 (C001/C044/C046) is rated **4–7.4V operating** ([Feetech datasheet](https://www.feetechrc.com/Data/feetechrc/upload/file/20200611/6372749961523760249976542.pdf), [indystry.cc](https://indystry.cc/sts3215-best-motors-for-your-next-robot/)). 11.1V nominal / 12.6V full is ~70% over ceiling. Replace with a 2S pack.
- **THE RESOLVED POWER ANSWER (this overturns the draft):** The official LeRobot SO-101 runs these *exact 7.4V servos from a regulated 5V 4A supply* — **not** 7.4V and **never** raw 8.4V ([Seeed wiki](https://wiki.seeedstudio.com/lerobot_so100m_new/), [HF SO-101](https://huggingface.co/docs/lerobot/so101)). The draft's "run direct off 2S up to 8.4V" advice was **wrong and unsafe**. Correct path: **2S LiPo → high-current buck → regulated 5–6V servo rail.** One of the cart's "300W 20A" bucks is the *right part for this job* — keep one, don't bin all three.
- **The one correct controller path:** A **Feetech-protocol serial-bus driver** (Waveshare "Servo Driver with ESP32" or a bare FE-URT-1 + ESP32). But **do not run servo current through that board** — its 6–12V/5.5×2.1mm barrel jack ([Waveshare wiki](https://www.waveshare.com/wiki/Servo_Driver_with_ESP32)) can't carry 45A. **Inject servo power externally; use the board for signal + telemetry only.**
- **Power must be distributed and protected, not daisy-chained.** Data daisy-chains; **power gets injected per-leg from a fused PDB.** Add per-branch fusing, an anti-spark arming connector, and a watt-meter — a multimeter can't safely read 15–45A inline.
- **Weight is already near the ceiling before the phone.** ~2 kg of robot under 19 kg·cm servos; the Mi 9 SE on top is the worst CG location. Mount it low/centered/removable, gait slow, and gate all "nice-to-have" mass until it walks. Everything mechanical/algorithmic from the Tazer reference transfers; only its electronics path (PWM + Mega) does not.

---

## 2. Cart audit (all 19 items)

| # | Item | Verdict | Reason / Replacement |
|---|------|---------|----------------------|
| 1 | SKYRC B6neo 2 — 300W charger | **KEEP (one charger only)** | A 2S 5000mAh pack at 1C is only ~42W — even the 200W is overkill, but keep one. **Confirm it has its required DC PSU brick** (B6neo chargers need an external DC supply; without it the charger is a paperweight). |
| 2 | XT60-F → 4mm banana charge lead | **KEEP** | Standard charger lead. **Verify XT60 gender** — wrong gender leaves live exposed pins. |
| 3 | Fireproof LiPo bag | **KEEP** | Correct safety practice; fits a 2S pack. |
| 4 | 50pcs acrylic mirror stickers | **REMOVE (or defer)** | Pure cosmetic; adds nothing structural, scratch/crack risk. Add last, if ever. |
| 5 | PCA9685 PWM driver ×2 | **REMOVE — WRONG** | I2C→PWM generator. Cannot speak Feetech serial protocol. Replace with a **serial-bus driver** (§3). Resell/repurpose, don't treat as total loss. |
| 6 | 4700µF 16V caps (15 total) | **KEEP** | Right voltage (16V on 7.4V = 2× derating). Use 1 cap per leg-branch injection point + bulk at the rail, not all at the battery. |
| 7–9 | Silicone wire assortments (×3) | **KEEP — but VERIFY GAUGE** | Many cheap kits are too thin. Confirm you actually have **14AWG for the trunk** and **16–18AWG for branches**. If not, buy real-gauge wire (§3). |
| 10 | 4-post 250A marine bus bar | **REMOVE — OVER-SPEC** | ~500g+ for a ~45A-peak robot. Replace with a small **XT60 PDB** (§3). |
| 11 | Inline fuse holder 12AWG 30A | **KEEP (as main fuse only)** | Sensible main-trunk fuse. **Mount close to the battery, verify real 12AWG + crimps.** It does **not** protect leg branches — add per-leg fusing (§3). |
| 12 | Amass XT60BE-M ×2 | **KEEP** | Correct battery connector for the 2S pack. |
| 13 | 25pcs 3-pin PWM extension leads | **REMOVE — WRONG** | PWM pinout/gauge; not a validated STS bus harness. Replace with **Feetech 3-pin bus cables** (§3). (May cut up for bench wiring.) |
| 14 | MG996R analog PWM servo | **REMOVE — WRONG** | PWM analog servo; irrelevant to an all-serial build. Confirm you weren't billed for a 10-pack. |
| 15 | SKYRC B6neo — 200W charger | **REDUNDANT** | One charger suffices. Keep as spare or drop. |
| 16 | BEAT 3S 2200mAh 11.1V LiPo | **REMOVE — WRONG** | Over-volts servos (12.6V full vs 7.4V ceiling) **and** undersized. Replace with **2S 5000mAh 25C** (§3). |
| 17 | 300W 20A buck converter ×3 | **CHANGE — KEEP ONE, cut two** | The draft was wrong to bin all three. **One is your servo-rail regulator** (2S→5–6V). Keep 1 for servo rail; the other 2 are redundant/heavy. Verify it isn't a thermally-optimistic "300W" — needs airflow at 15–20A. |
| 18 | 164pcs heat-shrink assortment | **KEEP** | Needed for splices/strain relief. |
| 19 | 25T metal disc horns ×24 | **REMOVE — not needed** | STS3215 ship with their own horns; spline is 25T-compatible so they *fit* if wanted, but 24 extra is dead weight and hole pattern may not match your CAD. |

**Net cut:** 4, 5, 13, 14, 15, 19, and 2 of the 3 bucks; downsize 10. **Verify before trusting:** 7–9 (gauge), 11 (real 12AWG), 1 (DC PSU), 2 (gender).

---

## 3. MUST-BUY — to make the robot controllable & powered

*Everything here is required for a working, safe robot. £ and g are estimates unless cited.*

| Part | Why | Qty | AliExpress search term | Est £ | Est g |
|------|-----|-----|------------------------|-------|-------|
| **Serial-bus driver — Waveshare "Servo Driver with ESP32"** | Brain + Feetech ST/SC bus driver in one; runs IK/gait, WiFi/BT/ESP-NOW. **Feed its DC jack 6–8.4V for its own logic; do NOT route 45A of servo current through it.** | 1 | `Waveshare ESP32 servo driver ST3215 STS3215` | 16–25 | ~35 |
| **FE-URT-1 USB→TTL bus adapter** | Commissioning: set each servo's unique ID 1–18 + baud from a PC before busing. *Recommended, not strictly must-have* — the Waveshare board can also set IDs over USB. Buy it if budget allows; it's the cleanest way to ID 18 servos. | 1 | `Feetech FE-URT-1 USB servo programmer` | ~11 | ~13 |
| **Feetech 3-pin bus cables** (assorted + spares) | Daisy-chain 6 legs; **exact ST/SC pinout**, not PWM leads. Connector at joint-3 is the #1 recurring failure on these builds — carry spares. | 1 set | `Feetech STS3215 3 pin servo cable 5264 100mm 200mm 300mm` | 5–12 | ~50 |
| **Servo-power injection Y-splitters** | 45A peak **cannot** flow through one bus end. Feed servo V+ into each leg's 3-servo cluster from the PDB. | 1 set | `PH2.0 3pin servo power injection Y splitter Feetech` | ~4 | ~30 |
| **2S LiPo 5000mAh, 25C, XT60** | Correct voltage. 5Ah×25C = 125A burst >> 45A worst case — **no high-C race pack needed** (draft's 30–50C was over-anchored). | 1 | `2S 7.4V 5000mAh 25C LiPo XT60` | 18–28 | ~280 |
| **Servo-rail buck (5–6V, 15–20A)** | **The LeRobot-correct path:** regulate 2S(6–8.4V) down to a safe **5–6V servo rail**, keeping servos under their 7.4V ceiling forever. **Reuse ONE cart buck (£0)**, or buy a proper unit if the cart's is flaky. | 1 | `DC-DC buck 20A 300W adjustable 5V step down` | 0 (own) | ~60 |
| **5V logic UBEC (3–5A, low ripple)** | Separate logic rail so servo-rail sag never browns out the ESP32. **Never hang logic/cam off the servo rail.** | 1 | `5V 5A UBEC RC BEC` | 3–6 | ~15 |
| **XT60 PDB** | Replaces the 250A bus bar (~500g → ~25g). Fan power out to legs + logic. | 1 | `XT60 power distribution board 6 output` | 3–7 | ~25 |
| **Per-leg branch fusing (6× 10–15A inline)** | Main 30A fuse protects the trunk only; one shorted leg cable can melt thin wire before it clears. | 1 set | `inline mini blade fuse holder 10A 15A 16AWG` | 4–9 | ~40 |
| **Blade-fuse assortment** | Tune main + branch values after measuring. | 1 | `mini blade fuse assortment 5A 10A 15A 20A 30A` | 2–5 | ~20 |
| **XT90-S anti-spark arming connector / loop key** | With ~10000µF bulk caps, **every power-on arcs** and pits a plain switch. This is mandatory, not optional. Also serves as the emergency kill. | 1 | `XT90S anti spark loop key switch` | 2–6 | ~25 |
| **Inline watt-meter (130A, XT60)** | A multimeter **cannot safely read 15–45A inline.** This gives live current/voltage/mAh to right-size the fuse, validate C-rating, and catch a stalling leg. Higher value than INA219. | 1 | `RC 150A watt meter power analyzer XT60` | 6–12 | ~40 |
| **2S LiPo low-voltage alarm** | Stops over-discharge/brownout. (Firmware voltage cutoff is the real protection — see §7; this is the backstop.) | 1 | `2S 3S 4S LiPo low voltage buzzer alarm` | 1–3 | ~8 |
| **Real 14AWG + 16AWG silicone wire** *(only if cart kits 7–9 lack the gauge)* | Trunk = 14AWG (~55A class); branches = 16–18AWG. | as needed | `14AWG silicone wire red black 5m` / `16AWG …` | 0–14 | ~80 |
| **USB-C/micro-USB data cable** | To flash the ESP32 and run the FE-URT-1. Easy to forget; stalls day one. | 1 | `USB to USB-C data cable short` | 1–2 | ~20 |
| **1–2 spare STS3215 (7.4V)** | Highest-leverage cheap insurance: one stripped/dead servo blocks the whole bus and can stall bring-up for weeks awaiting reorder. | 1–2 | `Feetech STS3215 7.4V 19kg serial bus servo` | 12–18 ea | ~60 ea |
| **M2×6 servo-body screws ×100** | 4×18 = 72 to mount servos (verify against *your* CAD — SO-101's M2×6 is a guide, not gospel). | 1 | `M2 x 6 stainless screw 100pcs` | 2–4 | ~60 |
| **M3×6 + M3 nyloc nut assortment** | Horns (M3×6) + leg/chassis joints. | 1 | `M3 x 6 button head screw 100pcs` + `M3 nylon lock nut` | 4–9 | ~350 |
| **M3 heat-set inserts ×100 + iron tip** | Durable joints in PLA/PETG. Pilot ~4.0mm. | 1 | `M3 brass heat set insert 100pcs` + `heat set tip` | 5–12 | ~70 |
| **Blue threadlocker (243)** | Gait vibration walks bolts loose. | 1 | `Loctite 243 blue threadlocker 10ml` | 3–7 | ~25 |

**MUST-BUY subtotal (excl. wire if owned, 1 spare servo): ~£90–150 / ~1.2 kg of parts** (most of which is screws/inserts, not robot mass).

---

## 4. RECOMMENDED additions (sensors / IMU / camera / phone)

| Part | Why | Qty | AliExpress search term | Est £ | Est g | Weight note |
|------|-----|-----|------------------------|-------|-------|-------------|
| **MPU6050 IMU** (I2C) | **Tier-1 upgrade.** Hundreds-of-Hz on-board balance/self-level loop the phone IMU (WiFi-latency-bound) cannot do. Pair with slow gait until tuned. | 1 | `MPU6050 GY-521 module` | ~2 | 3 | negligible |
| **ELEGOO ESP32-WROVER cam** (owned) | Keep as **vision-only node** on its MJPEG firmware (2.4 GHz fine). FPV eye (~640×480, ~20fps, 100–300ms latency) — **not** a real-time obstacle detector. Talks to MCU over WiFi/ESP-NOW; never touches the servo bus. | own | — | 0 | ~12 | mount low/forward |
| **Mi 9 SE phone** (owned, on top) | High-level brain / teleop screen. Run **SensorServer → 9-DOF IMU over WebSocket (JSON)** — *corrects the old "UDP" memory note* — for orientation; AMOLED as teleop UI; optionally its camera. **WiFi only, never wired to servos.** | own | — | 0 | ~165 | **worst CG spot — see §8** |
| **VL53L0X ToF ×1–2** | Narrow laser beam beats ultrasonic on a low walker. Struggles in direct sun. | 1–2 | `VL53L0X time of flight sensor` | 3 ea | 2 ea | tiny |
| **Phone mount (low/centered/removable)** | Vibration-isolated cradle near the roll center, NOT a tall tower. | 1 | `phone bike mount vibration damped` | 3–6 | ~40 | keep low |
| **PET braided sleeving + adhesive cable mounts** | Bundle/strain-relieve 18 bus cables on flexing legs. | 1 | `PET braided cable sleeve 4mm 6mm` | 3–8 | ~120 | |
| **Network note** | Cam + phone both 2.4 GHz → put both on the **same AP/hotspot** to avoid contention. | — | — | 0 | 0 | |

**RECOMMENDED subtotal: ~£15–30 / ~+200 g** (excluding owned cam/phone).

---

## 5. OPTIONAL / nice-to-have — *gated: NONE of these until it walks*

| Part | Why | Est £ | Est g | Verdict |
|------|-----|-------|-------|---------|
| Status OLED (SSD1306) | **Skip** — Waveshare board has one. | 2 | 5 | redundant |
| INA226 current sensor (50A) | Better than INA219 (whose 3.2A shunt can't see servo surge), but the watt-meter (§3) already covers this. | 4–8 | 3 | optional |
| WS2812 "eyes" + the mirror stickers | Flair after it walks. | 1 | 5 | cosmetic |
| Foot-contact switches ×6 | 6 flexing wire runs = 6 failure points. Only after gait is solid. | 4 | 18 | defer |
| DFPlayer Mini + speaker | Sound. Low priority. | 3 | 12 | defer |
| BLE gamepad | Phone/web UI works too. **120 g.** | 22 | 120 | skip unless wanted |
| 2nd 2S pack (off-board hot-swap) | Runtime. Keep off the robot — don't mount spare mass. | 18–28 | 280 | optional |

---

## 6. Corrected power architecture

```
2S LiPo (7.4V nom, 8.4V full, 5000mAh 25C)
   │  XT60
   ▼
[XT90-S anti-spark / loop key]  ← emergency disconnect + inrush protection
   │
[30A main blade fuse]  ← mounted AT the battery, real 12–14AWG, crimped
   │
[Inline watt-meter]    ← live A/V/mAh
   │
[XT60 PDB]  ← single distribution node (replaces 250A bus bar)
   ├──────────────► [Servo-rail buck: 2S → 5–6V, 15–20A]  ← THE KEY REGULATOR
   │                     │  (one of the cart's 300W bucks)
   │                     ▼
   │                Servo V+ rail  ── per-leg [10–15A branch fuse] ──► leg cluster
   │                     │            (power INJECTED per leg, NOT daisy-chained)
   │                     │  4700µF cap at each leg injection point
   │                     ▼
   │                18× STS3215 (DATA bus daisy-chained; POWER injected)
   │
   ├──────────────► [5V logic UBEC, 3–5A] ──► Waveshare ESP32 board logic*,
   │                     │                      ESP32-CAM, MPU6050, sensors
   │                     │  470–1000µF at input
   │
   └─ COMMON GROUND across battery / servo rail / logic / UART — MANDATORY
      (half-duplex serial returns garbage without a clean shared ground)
```

\* **The contradiction the draft left open, resolved:** the Waveshare board needs **6–12V** at its jack and **passes input straight to the servo bus** ([Waveshare wiki](https://www.waveshare.com/wiki/Servo_Driver_with_ESP32)). So you **cannot** feed it 5V, and you **cannot** push 45A through it. Two clean options:

- **Option A (LeRobot-proven, safest):** Regulate a separate **5–6V servo rail** from the buck and inject it into the bus **externally** (Y-splitters into each leg). Feed the Waveshare board's own DC jack 6–8.4V for its logic, but **physically separate its servo-power pass-through** so servos only ever see 5–6V. Servos run forever under their 7.4V ceiling.
- **Option B (simpler, higher torque, tighter margin):** Run the servo rail at a **regulated flat 7.4V** via a real high-current HV-BEC (≥20A) — **never** raw unregulated 2S, because 8.4V full-charge exceeds the rated ceiling. More torque than Option A's 5V, but you must trust the regulator under stall.

**Resolved numbers (verified):**
- **Servo operating voltage: 4–7.4V** ([Feetech datasheet](https://www.feetechrc.com/Data/feetechrc/upload/file/20200611/6372749961523760249976542.pdf)). 8.4V = over-spec. **Do not run direct 2S.**
- **Stall current 2.5A/servo @7.4V → 18× = 45A worst case;** no-load 150mA/servo → **~2.7A idle** ([RobotShop / Feetech](https://www.robotshop.com/products/magnetic-encoding-servo-sts3215-74v-19kgcm)).
- **Walking continuous: ~8–15A** *(estimate — measure with the watt-meter once it walks).* A heavy/badly-tuned 2 kg hexapod will spike uglier; **size wiring/fuses/regulator for stall/fault, not the walking average.**
- **Main fuse: 30A** (you have it; drop to 25A if measured walking stays <15A). **Per-leg fuses: 10–15A.**
- **Runtime: ~10–20 min realistic** (5Ah at ~12A average, derated for high-current LiPo sag) — not the optimistic 25–30 min.

---

## 7. Compute & software plan

**Brain: Waveshare "Servo Driver with ESP32" as the dedicated motion controller.** 18-DOF analytic IK + tripod/wave gait at ~50 Hz is light math; the WROOM ESP32 (no hardware FPU) runs it fine. *(An ESP32-S3 adds an FPU if you later want higher rates — not required.)* **Avoid an Arduino Mega.**

**Why not the ESP32-WROVER cam as brain:** its GPIO is consumed by the OV2640 + PSRAM and it's busy streaming MJPEG — no safe free pins for a servo bus. Keep it vision-only.

**Half-duplex bus note (verified concern):** STS3215 share one bidirectional TTL line; you need proper tri-state/direction control and 5V-TTL handling — a real bus-driver board, **not** a bare ESP32 GPIO. The Waveshare board provides this.

**Firmware / libraries:**
- Bus control: **matthieuvigne/STS_servos**, **Feetech SCServo lib**, or **lerobot/feetech-servo-sdk** (Python).
- **Use SyncWrite** — one broadcast packet sets all 18 targets per gait tick. Never 18 sequential writes.
- IK/gait to adapt: **rasheeddo/hexapod_dev_esp32**, **CoretechR/ZeroBug** (both PWM-written — swap the output layer to STS SyncWrite), **Waveshare HexArth** (native serial-bus reference).

**Firmware safety the servos make free (must actually implement):** STS3215 report **position, load, temperature, voltage, current**. Add firmware rules: over-temp shutdown, low-pack-voltage torque-reduce/stop, overload cutoff, and command-timeout failsafe. A buzzer alarms *after* sag; firmware should reduce torque *before* brownout.

**Split-brain (optional):** MCU does servo timing + IK + gait; the **Mi 9 SE** does perception/planning/teleop over WiFi (SensorServer 9-DOF IMU via WebSocket); the **ESP32-CAM** is the FPV eye. Add a Raspberry Pi only if you want on-board autonomy beyond the phone.

---

## 8. Price & weight scenarios

*Additional spend beyond what you already own (servos, cam, phone, charger, fusing, caps, wire, heat-shrink not re-counted).*

| Scenario | What it includes | Added £ | Notes |
|----------|------------------|---------|-------|
| **Minimum-Viable** | Waveshare driver, bus cables + Y-splitters, 2S 5000mAh pack, reuse 1 cart buck (£0), 5V UBEC, XT60 PDB, per-leg + main fusing, XT90-S, LV alarm, watt-meter, M2/M3 + inserts + threadlock. (Skip FE-URT-1 — ID via the board.) | **~£75–110** | Controllable, powered, safe. |
| **Recommended** | + FE-URT-1, MPU6050, 1 spare STS3215, phone mount, sleeving, VL53L0X. | **~£110–165** | The build you should actually target. |
| **Fully-Loaded** | + 2nd 2S pack, INA226, LEDs, 2nd spare servo, foot switches later, BLE gamepad. | **~£175–230** | Gate all extras until it walks. |

**Filament/consumables** (PETG structural ~£12, TPU 95A feet ~£12) are buy-as-you-print, not robot mass — don't double-count spools in the robot weight.

**Estimated total robot mass:**
- 18 servos ~1000 g + 3D-printed chassis/legs ~600–1000 g + 2S pack ~280 g + electronics/wiring ~200 g + cam ~12 g = **~2.1–2.5 kg without phone.**
- + Mi 9 SE ~165 g = **~2.3–2.7 kg with phone.**

**CG / balance (honest warning):** *(estimate)* a 19 kg·cm tripod hexapod realistically tops out around **1.5–2.0 kg of well-distributed moving mass** before gait quality and servo thermals suffer. **You are already at/over that ceiling before the phone — and the phone is the worst possible location (high and on top).** More mass = more current = more stalls = more heat = more brownouts, so the phone is a **power-safety risk, not just a CG one.** Mitigations: print light (PETG, ~20% infill, ribbed), mount **battery and phone low and centered**, keep gait slow, make the phone **removable**, and seriously consider running the phone **off-board** (teleop over WiFi) until the gait is mature.

---

## 9. Build-order checklist (safe bring-up sequence)

1. **Finalize leg CAD first** — it fixes bearing sizes, servo-body screw spec, and horn geometry. Don't buy bearings/horns until the boss dimensions are set.
2. **Bench power before touching servos** — wire battery → XT90-S → fuse → watt-meter → PDB → buck. Power up with **no servos**, confirm **servo rail = 5–6V (or regulated 7.4V), logic = 5V, correct polarity, fuse continuity, common ground.**
3. **ID the servos one at a time** — every STS3215 ships as **ID 1**; on a shared bus they collide and nothing responds. With FE-URT-1 (or the Waveshare board, **one servo connected at a time**), assign **IDs 1–18** and set baud. **Use external regulated servo power for this — never power high-torque servos from USB.**
4. **Log a servo map** — for each: ID, physical joint, zero offset, rotation direction, min/max angle, voltage/current limits. You will need this for IK sign conventions.
5. **Test ONE servo** — confirm comms, motion, and that telemetry (pos/load/temp/voltage) reads back.
6. **Build and test ONE complete leg (3 DOF)** — verify per-leg current on the watt-meter and basic IK before replicating ×6.
7. **Wire all 6 legs** — **data daisy-chained, power injected per-leg** from the PDB via Y-splitters + branch fuses. Strain-relieve every joint connector (joint-3 routing is the known failure point); sleeve and label every cable.
8. **Idle-current check** — power all 18, expect **~2.7A idle**. Anything wildly higher = a fault; stop and investigate.
9. **First gait, robot on a stand (feet off ground)** — run tripod gait, watch temps/load via telemetry. Add MPU6050 balance loop.
10. **Walk on the floor, slowly** — measure real walking current; right-size main + branch fuses to measured draw.
11. **Add sensors/phone/cam last**, re-check CG and current budget after each addition.

---

## 10. Top 10 mistakes to avoid

1. **Powering "7.4V" servos from raw 2S at 8.4V full charge** — over the 4–7.4V rating. Regulate to 5–6V (LeRobot path) or a flat 7.4V; never run unregulated 2S.
2. **Routing 45A of servo current through the Waveshare board's barrel jack or one daisy-chain end.** Inject power per-leg from the PDB; the board is for signal.
3. **Undersizing the servo regulator.** An "8A/15A UBEC" can't feed 18 servos (45A stall). Use a real 15–20A buck/BEC. Treat cheap "300W 20A" ratings as optimistic — needs airflow.
4. **Leaving all 18 servos at default ID 1** → bus collisions, nothing works. ID them one at a time first.
5. **Shared servo+logic power / dirty ground return** → ESP32 brownouts and garbled half-duplex UART. Separate 5V logic rail + clean common ground.
6. **One main fuse only** — a single leg short melts thin branch wire before 30A clears. Add per-leg fusing.
7. **No anti-spark connector** — ~10000µF of caps arcs and pits a plain switch on every power-up.
8. **Trusting fake C-ratings / no current measurement** — buy a watt-meter; a multimeter can't read 15–45A inline. Right-size everything from measured data.
9. **Too heavy, mass too high** — phone-on-top + metal bus bar + metal horns + dense PLA. Tazer's build hit 5 kg vs a 3 kg target, and that mass directly caused his failures. Stay light, mount low, gait slow.
10. **No firmware limits + no spare servo** — the servos report temp/load/voltage; act on them. And keep a spare STS3215, since one dead servo blocks the whole bus and stalls bring-up for weeks.

---

### Resolved-fact appendix (where the inputs disagreed)

- **Servo voltage ceiling:** Draft said "abs max ~8.4V, run direct 2S." **Resolved: WRONG.** 7.4V STS3215 is rated **4–7.4V** ([Feetech datasheet](https://www.feetechrc.com/Data/feetechrc/upload/file/20200611/6372749961523760249976542.pdf), [indystry.cc](https://indystry.cc/sts3215-best-motors-for-your-next-robot/)). The critic and adversaries were correct.
- **Correct power path:** **Resolved: regulated low voltage.** LeRobot powers these exact 7.4V servos from **5V 4A** ([Seeed wiki](https://wiki.seeedstudio.com/lerobot_so100m_new/)). Keep one cart buck as the servo-rail regulator.
- **Waveshare board:** **Resolved: 6–12V, 5.5×2.1mm jack, input passes to bus, explicit high-power warning** ([Waveshare wiki](https://www.waveshare.com/wiki/Servo_Driver_with_ESP32)). Confirms it can't be the 45A power path and can't take 5V — power injected externally.
- **Stall current / fuse basis:** **Resolved: 2.5A/servo @7.4V → 45A worst case; ~150mA idle/servo** ([RobotShop](https://www.robotshop.com/products/magnetic-encoding-servo-sts3215-74v-19kgcm)).
- **C-rating:** Draft anchored 30–50C; **resolved: 25C 5000mAh is plenty** (125A burst >> 45A).
- **Chargers:** redundant — keep one, and **confirm it has its DC PSU brick** (genuinely missing-item risk flagged by adversaries).

**Sources:** [Feetech STS3215 datasheet](https://www.feetechrc.com/Data/feetechrc/upload/file/20200611/6372749961523760249976542.pdf) · [LeRobot SO-101](https://huggingface.co/docs/lerobot/so101) · [Seeed LeRobot wiki](https://wiki.seeedstudio.com/lerobot_so100m_new/) · [Waveshare Servo Driver with ESP32 wiki](https://www.waveshare.com/wiki/Servo_Driver_with_ESP32) · [RobotShop STS3215 7.4V](https://www.robotshop.com/products/magnetic-encoding-servo-sts3215-74v-19kgcm) · [indystry.cc STS3215](https://indystry.cc/sts3215-best-motors-for-your-next-robot/)