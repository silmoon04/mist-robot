# MIST field guide - electronics for a programmer

Companion to `MIST_BUILD_PHASES.md` and `MIST_ACTUAL_INVENTORY.md`. Those two docs are strong on *process* (gates, one-change-at-a-time, evidence). This doc covers what they assume you already know: the *why* behind the rules, the beginner traps they don't spell out, and a symptom-based debugging playbook.

Visual companion: `MIST_VISUAL_BUILD_GUIDE.md`.

Read sections 1-3 once before parts arrive. Use section 7 (debugging playbook) as a lookup table when something misbehaves.

Technical claims in this guide were adversarially reviewed on 2026-07-06 by an independent GPT-5.5 panel (52 claims checked against the Feetech/Waveshare/Espressif documentation; 3 refuted, 1 downgraded). The corrections are folded in.

## 1. Remaining gaps and already-folded corrections

These are things the phase/inventory docs either still need to emphasize or have recently folded in. They stay here because they are common beginner traps.

| # | Gap | Impact | Fix |
|---:|---|---|---|
| 1 | **RESOLVED 2026-07-06 — printer exists.** An Elegoo Neptune 4 Pro is at home with ~3kg PLA; PETG/TPU are in the post. The remaining gap is *material*, not machine: PLA creeps under sustained load and softens near servo operating temperatures (glass transition ~55-60°C, servos run 50-70°C under load). | A PLA servo pocket or structural bracket that works on day one slowly deforms, then binds/loosens weeks later. | Prototype freely in PLA (coupons, fit tests, throwaway brackets — cheap iteration is exactly what 3kg of PLA is for). Reprint anything servo-adjacent or load-bearing in PETG, and re-verify critical fits with one PETG coupon first — clearances don't transfer exactly between materials. |
| 2 | **Servo-centering must be repeated anywhere horns/links are fitted.** Phase 7 has the rule, and Phases 10/12 now repeat it for leg and full-robot assembly. | If you attach a horn at a random position, your leg's mechanical neutral lands near a travel limit. Everything after that needs software hacks to compensate. | Before fitting any horn: power the servo, command position 2048, hold it there, then attach the horn/link at the intended neutral geometry. |
| 3 | **RESOLVED in `MIST_BUILD_PHASES.md` — smoke-stopper use is static-only.** A bulb-type stopper drops voltage in proportion to current; jogging servos through it causes false resets/dropouts. | False failures, wasted debugging, possible brownout-corrupted flash writes. | Use the stopper for the first *static* power-up + ID scan of each new wiring stage only. Bypass it (direct connection, fuses in) for any test involving motion. |
| 4 | **Fuses protect wires, not servos.** Nothing in the docs says this. A stalled STS3215 draws roughly 2.5-3A — a 15A branch fuse will never see it. Four servos stalling on one branch still may not blow it quickly. | Expecting the fuse to save a stalled/binding servo. It won't. Only the servo's own overload/over-temp protection and your firmware guard do that. | Mental model correction (section 3). Firmware current/temp guard (Phase 11 F8) is the *servo's* protection; fuses are the *harness's*. |
| 5 | **Daisy-chain cable current limit.** Power enters each leg at the root, but the femur/tibia/wheel servos downstream get their current *through* the thin 5264 cables and through each upstream servo's PCB. Three downstream servos stalling ≈ 8-9A through one thin cable. | Warm/melting bus cables during prolonged stalls or binds. | Know the limit; keep stalls short (firmware guard); during Phase 10 load tests, feel the leg-root cable. If it warms, add a second power injection point mid-leg. |
| 6 | **ESP32 dual-power rule missing.** During development the ESP32 will often have laptop USB *and* UBEC 5V connected at once. Espressif's official DevKitC guidance treats the power inputs as mutually exclusive; the genuine V4 schematic does have a Schottky diode blocking backfeed into USB, but clones may omit it. | Backfeeding your laptop's USB port — expensive. | Safest default: one power source at a time (unplug the UBEC lead to flash, or use a power-blocked/data-only USB connection). If you do dual-power, first verify your specific board has the diode — and keep a cheap sacrificial USB hub between laptop and robot regardless. |
| 7 | **Continuity tests will "fail" once capacitors are installed.** Phases 8/9 say "positive should not beep to negative" — but a 4700uF cap across the rail *will* beep for a moment while the meter charges it, then fade. | Panic, or worse: dismissing a real short as "the cap thing". | Brief beep that dies + resistance climbing to high values = cap charging = normal. Sustained solid beep / stable near-0Ω = real short. Added to playbook. |
| 8 | **B6Neo LiHV trap.** The charger supports LiHV (4.35V/cell). Selecting LiHV for a normal LiPo overcharges it — fire risk. Also NiMH mode on a LiPo has no voltage cutoff. | Battery fire during your very first charge. | First-use walkthrough in section 4. Always: type = LiPo, cells = 3S (12.6V), current = 2.2A, balance mode. |
| 9 | **Servo EEPROM has limited write cycles.** ID, baud, mode, limits live in EEPROM (~100k writes typical for this class). A firmware bug that writes mode or limits in a loop kills the servo silently over hours. | Dead/corrupt servo, mysterious. | Only write EEPROM registers in setup tools, never in the control loop. Goal position/speed are RAM — those are fine to spam. |
| 10 | **Multimeter current-jack trap.** If the meter's probes are left in the current (A) socket and you then measure "voltage" across the battery, the meter *is* a dead short. | Blown meter fuse at best; melted probe/spark at worst. | Habit: always park probes in the V/Ω socket. Never measure the servo rail current in series with a cheap meter — use B6Neo recharge mAh or servo telemetry instead. |
| 11 | **Wheel-mode register persists.** Setting an STS3215 to wheel mode is an EEPROM write — it survives power cycles. Set it on the wrong servo and your "tibia" spins instead of positioning. | Confusing behaviour that survives reboots; possible leg damage. | Only set mode on the four wheel-role servos, immediately label them, and verify mode by register read during Phase 5. |
| 12 | **RESOLVED in `MIST_BUILD_PHASES.md` — 12V-variant electrical cross-check is part of Phase 5.** Phase 1 checks the printed label; Phase 5 reads voltage-protection/register defaults as supporting evidence. | A mislabelled 7.4V servo run at 12.6V dies. | Per the Feetech datasheets the 12V STS3215-C018 protects above ~14V, the 7.4V C001 above ~7.4V. It's a writable config register, so treat it as supporting evidence, not proof of the hardware variant — but any servo whose protection reads ~7.4V stays off the 12V rail until its identity is resolved. |
| 13 | **Voltage-domain discipline is implicit, never stated.** The #1 beginner robot killer is 12V touching a 5V input. | Instant dead ESP32/sensor. | Rule: one connector family per voltage. XT60/XT30 = raw 12V only. Never build an adapter that puts raw battery voltage on a connector that 5V devices use. Label the UBEC output lead "5V" with tape. |
| 14 | **Filament is hygroscopic.** PETG and especially TPU absorb moisture in days; wet filament strings, bubbles, and prints weak parts. | "My printer is broken" — it's the filament. | Keep spools sealed with desiccant until use; if prints get stringy/popping, dry the spool (~60-65°C PETG / ~50°C TPU for 4-6h) — in a filament dryer or dehydrator, never a household oven (ovens overshoot and deform spools). |
| 15 | **No jewellery rule.** Rings/metal watch straps across a 3S pack's terminals will weld/burn before any fuse reacts. | Burned finger, damaged pack. | Rings and metal watch off whenever a battery is on the bench. |

Smaller adds, also worth doing: clear safety glasses if the ordered goggles are tinted; a ceramic tile + small bucket of dry sand at the charge/test station; hot glue or tape retention on 5264 connectors *after* a leg passes tests (friction-fit connectors walk out under vibration); M3 brass heat-set inserts (cheap, far stronger than self-tappers in PETG bosses — install with a spare/dedicated iron tip, not your leaded solder tip); a cheap ferrule kit if any screw terminal ever feels loose (ferrules beat bare twisted wire in screw terminals); identify mystery SKU `JP-1086 hei` when it arrives.

## 2. How electricity breaks things — the four failure modes

Everything that kills parts in this build is one of these:

1. **Reverse polarity** — + and − swapped. Kills electronics in milliseconds. Fuses do NOT protect against this (current flows "correctly" through the fuse, just backwards through the chip). Your defences: keyed connectors (XT60/XT30 can't physically reverse — this is why you never bypass them with bare wire), red/black discipline, and metering every new lead before it powers anything.
2. **Overvoltage** — 12V on a 5V pin. Also milliseconds. Defence: voltage-domain connector discipline (gap #13), and measuring UBEC output before connecting logic (already in Phase 4).
3. **Overcurrent / short** — too much current through too thin a path; the path heats until insulation melts or something ignites. This is the only failure fuses actually address, and they protect *the wire*, not the device. Defence: fuses sized to the wire, smoke stopper on first power, no rings.
4. **Heat over time** — the slow one. A servo holding a heavy pose, a connector with a bad crimp, an undersized wire — all get hot gradually. Nothing trips; things just age and fail. Defence: the finger test as a *warning*, not a thermometer (uncomfortable to hold = assume too hot, likely 50°C+, and check), servo temperature telemetry for the real number, and the Phase 15 run log.

## 3. Mental models (programmer translations)

- **Voltage** is like potential/pressure — it's *applied* to the circuit. **Current** is *drawn* by the load, not pushed by the supply. A 50C 2200mAh pack that "can deliver 110A" will happily deliver 0.2A to an idle ESP32. Big supply ≠ danger to small loads. The danger is only when a load (or a short) *asks* for huge current.
- **Ohm's law is about the wires here.** Every wire is a small resistor (V = I×R). High current through thin wire → voltage sags at the far end and the wire heats as I²R. This is why the trunk is 12AWG and a signal wire can be hair-thin, and why "servos work fine until they all move at once, then the ESP32 reboots" is almost always wire resistance somewhere. The pack is part of that chain too: "50C = 110A" is a marketing-theoretical ceiling, and real packs sag under pulsed servo load through their internal resistance plus every connector and fuse holder in the path.
- **Ground = shared reference frame.** All voltages are *differences* against ground, like pointers being meaningful only within one address space. Two boards without a common ground wire comparing "3.3V signals" are comparing pointers from different processes — garbage. This is the entire reason for the "grounds must be common" rule between ESP32, adapter, and servo rail.
- **A fuse is a rate limiter on infrastructure, not input validation.** It protects the transport (wire) from catastrophic abuse; it does nothing about application-level misbehaviour (a stalled servo cooking itself at 3A under a 15A fuse).
- **A capacitor is a local write buffer.** Servos draw current in sharp spikes (each control cycle, each direction reversal). The 4700uF cap at the leg root serves those spikes locally so the long wire back to the battery doesn't have to, keeping the local voltage stable. This is also why there's an inrush spark at plug-in (buffer cold-filling) — the XT90-S's internal resistor pre-charges the caps gently before the main contacts touch. Always push the XT90-S fully home in one motion, don't let it sit half-inserted.
- **The UBEC is an adapter layer**: it takes anything from ~9-12.6V in and emits regulated 5V. It's a switching regulator (~90% efficient) so it barely warms. Verify its output because a mislabelled or DOA unit emits its input instead — see failure mode 2.
- **The servo bus is a single-threaded message queue.** One wire, half-duplex: the controller broadcasts a packet addressed to an ID, then the addressed servo replies on the same wire. Two servos with the same ID = two threads writing one socket = corrupted replies. That's the real reason behind "never connect multiple factory-ID servos" — they all ship as ID 1.
- **LiPo = raw storage with no memory protection.** Phone batteries have a built-in BMS that prevents overcharge/overdischarge/shorts. Hobby packs have *nothing* — the balance lead is just voltage taps. Every safety rule in Phase 3 exists because **you are the BMS**.

## 4. Battery and charger — first-use walkthrough

The B6Neo arrives ~2026-07-15. First session, in order:

1. Power it from the Anker 317 with the 5A e-marked cable. It should negotiate PD (screen shows input wattage capability).
2. Battery *not* connected yet: explore the menu. Find: task type (Charge / Storage / Discharge), battery type (**LiPo** — never LiHV, never NiMH for these packs), cell count, current.
3. Meter the pack's XT60 first: a healthy stored 3S reads ~11.1-11.7V. Then connect main lead + balance lead to the charger.
4. **Sanity gate: the charger must display 3 cells and a target of 12.6V.** If it shows 2S or 4S or any cell below ~3.3V or cell spread > ~0.1V — stop, mark the pack suspect.
5. Settings for these packs: LiPo, 3S, **2.2A** (1C), Balance Charge. In the LiPo bag, on the tile, in sight, never unattended. First charge of each pack: stay close and touch-check the pack every few minutes (should stay cool/barely warm).
6. After charge: cell spread ≤ ~0.02-0.03V is good. Log it. If the B6Neo offers internal-resistance (IR) readout, log that too — rising IR over months = pack aging; one cell much higher than siblings = pack going bad.
7. Not building for a few days? Run **Storage** mode (~3.85V/cell, ~11.5V pack) before putting it away.

Standing rules: never charge a pack that's still warm from running; never charge below 0°C; alarm set to 3.5V/cell and *removed* after each session (it drains the pack in storage — already noted in Phase 3); disposal is a council battery-recycling point after discharging, not the bin, and the old salt-water trick is obsolete advice.

**If a pack ever hisses, swells while charging, or smells sweet/solventy:** disconnect at the charger if safe, move it (by the bag/tile, not bare hands against the cells) outside onto concrete, and leave it for 30+ minutes. Don't breathe the vapour. Sand smothers; water cools. A pack that did this is dead — never recharge it. But only move a pack while it's *just* hissing/swelling and clearly safe to approach — if it's actually flaming or too hot to get near, don't be a hero: keep your distance, ventilate, get people out, and let it burn out on the tile or call 999.

## 5. Skills you'll be learning live

### Soldering (the HANDSKIT 90W + 63/37)

- **Practice first.** Before any real joint: strip, twist, tin, and join ~20 scrap-wire pairs. Your first ten joints will be bad; make them be bad on scrap. Budget one evening.
- Order of operations for every joint: **slide heat-shrink on FIRST**, well away from the joint → tin both parts → bring together, add heat + a touch of solder → hold dead still while it sets (~2s) → tug test → slide shrink over, shrink it.
- The jig-mate for XT soldering must be an **unpowered spare** — never a connector attached to a battery, the PDB, or any live wiring.
- A good joint is **shiny and concave**, wetted onto both metals. Grey, lumpy, or ball-shaped = cold joint = future intermittent fault (the worst kind). Reflow with fresh solder; the rosin core is the flux.
- Big joints need heat: 12AWG wire and XT90/XT60 cups soak heat away. Use the biggest tip in the kit and ~380-400°C for those; ~330-350°C for small wires. If solder won't flow in 3-4 seconds, the tip is too small/cold — don't sit there cooking the insulation.
- **XT connector trick:** plug the connector you're soldering into its mate first. The mate acts as a jig and stops the pins drifting when the plastic softens.
- Never tin a wire end that goes into a **screw terminal** (e.g. the Bus Servo Adapter A power input). Tinned wire cold-flows under the screw and the joint loosens itself over weeks. Bare twisted wire, screwed firmly, re-check after a day.
- Hygiene: it's leaded solder — fine to use, just wash hands after, don't eat at the bench. The smoke is flux (an asthma sensitiser), not lead — use the fan, don't hover your face over the joint.
- No helping-hands tool in inventory: blu-tack, the cutting mat, and masking tape make an acceptable jig. Don't solder anything held in your fingers.

### Multimeter (ANENG SZ308)

- The three modes you'll live in: **DC voltage** (measure *across* things, in parallel — safe), **continuity beep** (unpowered circuits ONLY), **resistance** (also unpowered only).
- Continuity nuance: the beep threshold is ~30-50Ω. A beep proves *a* path, not a *good* path — for power joints, the tug test matters as much as the beep. And caps make + to − beep briefly (gap #7).
- Autoranging meters show phantom volts (1-2V, drifting) on disconnected floating wires — that's noise pickup, not a real supply. A real rail reads solid and stable.
- Weird readings that make no sense → check the meter's own battery first. Cheap meters ship with half-dead cells and lie when low.
- Probing XT60/XT30 pins is fiddly and one slip shorts + to −. Build a **measurement pigtail** from one spare XT30/XT60 pair: connector on one end, two stripped tails you can clip to safely. Ten minutes of soldering practice that pays off for the whole build.
- Current measurement: don't (gap #10). Everything you need comes from voltage checks, servo telemetry (register-reported current), and B6Neo recharge mAh.

### 3D printing (Neptune 4 Pro)

Full beginner curriculum in `MIST_PRINTING_BOOTCAMP.md` — commissioning, calibration ladder, CAD project ladder, print-failure playbook. Summary points:

- The Neptune 4 Pro is a good machine for this build: direct-drive extruder (TPU-capable), Klipper firmware, ~300°C hotend, ~225×225×265mm bed. Nothing in MIST needs more.
- **Use the PLA-only window well.** Until PETG arrives, everything printable is a prototype: Phase 6 coupons, servo-pocket fit tests, mock brackets, cable-routing dry fits. PLA prints easier than PETG, so it's also the right material to learn the printer on. The one rule: PLA never goes on the final robot where it clamps a servo or carries sustained load — it creeps and softens near servo temperatures.
- When PETG arrives: run a PETG temperature tower, then **reprint one fit coupon in PETG before any final part** — PLA-validated clearances transfer only approximately (different shrinkage/flow).
- PETG loves to weld itself to smooth PEI beds — use glue stick *as a release layer*, and it strings at too-hot/too-fast settings.
- TPU 95A: slow (20-30mm/s), minimal retraction, dry filament. It's the hardest material in this build; print the tires *after* you're comfortable with PETG. The Neptune's direct drive is what makes it feasible at all.
- Layer orientation is strength: a screw boss printed with layers perpendicular to the screw axis splits along layers. Orient parts so loads run *along* layers, and prefer heat-set inserts over self-tappers for anything opened more than twice.

## 6. Subsystem notes the docs skim

### Servo bus deep dive (STS3215)

- Protocol: half-duplex TTL serial, default **1,000,000 baud**, ID 1 from factory. Position range 0-4095 over 360°, **centre = 2048** (some Feetech docs say 2047 — same thing in practice).
- Registers split into **EEPROM** (ID, baud, angle limits, voltage/temp protection, mode — survive power cycles, limited write cycles, guarded by a lock register) and **RAM** (torque enable, goal position/speed/acceleration, all telemetry — vanish at power-off, safe to write constantly). The FD software handles the lock automatically; if you later write EEPROM from your own code, you must unlock (lock register → 0), write, re-lock. Verify addresses against the Feetech STS/SMS memory table for your firmware version rather than trusting any list from memory — and log the full default dump per servo in Phase 5 as the docs already say.
- Telemetry is the killer feature vs PWM servos: each servo reports position, speed, load, **input voltage, temperature, current**. Your battery monitor *is* the servos — no extra voltage divider needed on the ESP32.
- Useful numbers for sanity checks (12V C018 datasheet): no-load moving current ≈ 0.18A; stall ≈ 2.7A; over-temp protection above 70°C. Skin is not a thermometer — trust the telemetry. A servo idling at 45°C+ while unloaded is telling you something (bind, bad unit, or holding torque against gravity).
- Pinout discipline: the 5264 pins are GND / V+ / signal (check the moulding marks against the datasheet). Verify at every adapter tail and home-made lead — V+ landing on the signal pin kills the bus side instantly.
- The Bus Servo Adapter A's own schematic marks its servo power path **6A max** — three stalled servos already exceed that. It's a signal+GND interface; leg current must come from the fused branches (the phases doc's power-injection rule, now with a number attached).
- **FE-URT-1 needs servo power separately from USB.** USB powers only the adapter's logic. If FD scans find nothing, first question is always: is the 12V rail actually present at the servo? (See playbook.)
- Drivers, install before the boards arrive: **CP210x** (Silicon Labs) for the ESP32 DevKitC, and the FE-URT-1 is typically a **CH340** — install both, they don't conflict. Feetech's Windows tool is the FD debug software from their site.
- Bus wiring hygiene: signal quality at 1Mbps is fine over a robot-sized harness *if* grounds are common and connectors are seated. Nearly all "flaky bus" problems are mechanical (crimp, half-seated 5264, cable flexing at a joint), not electrical noise.

### Power architecture nuances

- Wire-gauge rule of thumb for short silicone-insulated runs: 16AWG ≈ 10A, 14AWG ≈ 15-20A, 12AWG ≈ 25-30A continuous. Your branch (15A fuse on 16AWG) is at the edge but fine for burst-y servo loads; the trunk (30A on 12AWG) likewise. This is why the phase doc insists on real silicone wire before final harness — PVC-insulated equivalents derate hard.
- XT gender is named by the **metal contacts**, not the shell. Sources (battery, PDB outputs) should present female sockets; loads present male pins. Keep "power flows out of sockets, into pins" true everywhere and you can never plug live pins into your palm.
- Worst-case math for perspective: 16 servos all stalling at once ≈ 40-48A against a 30A main fuse. Don't read that as "the fuse handles it" — blade fuses are slow at modest overloads and can take a long time to open at 1.5× rating. The fuse is last-resort wire protection; what actually stops a stall is the servo's own protection plus your firmware current/temp guard and torque-off. Normal mixed driving is more like 2-6A total; standing with torque on can exceed driving. Also: the main fuse belongs physically close to the battery — every centimetre of positive lead before the fuse is unprotected wire.
- Runtime estimate: 2200mAh at an average 3-4A ≈ 30-40 min of gentle driving. Torque-off when idle (firmware) roughly doubles real bench-session life and keeps servos cool — one more reason MIST's park-on-wheels stance beats a joints-loaded stand.
- Never disconnect the battery while servos are actively moving if avoidable — command torque-off first, then pull the loop key. (Motors being back-driven can kick voltage around with only caps to absorb it.)

### ESP32 specifics (the part closest to home for you)

- **Strapping pins**: GPIO 0, 2, 5, 12, 15 are sampled at boot. Anything connected to them that pulls them the wrong way = boot failure or flash-mode weirdness. Wire the Bus Servo Adapter A UART to innocent pins — GPIO 16/17 (UART2) is the classic safe choice on your WROOM DevKitC (not on WROVER boards like your camera module, where 16/17 are taken by PSRAM). Also off-limits: GPIO 6-11 (internal flash) and GPIO 1/3 (the USB serial console).
- GPIO 34-39 are **input-only** (can't TX). ADC2 pins are unusable while WiFi is on — if you ever add analog sensors, use ADC1 pins (32-39).
- "Brownout detector was triggered" on the serial monitor = the 3.3V rail sagged. Causes in this build, in order of likelihood: powering servos while ESP32 runs from laptop USB only through a thin cable; UBEC input tapped from a sagging point; thin/long ground path. Fix the power path; don't disable the brownout detector.
- Flashing fails with "Failed to connect" → hold BOOT while esptool retries; if it persists, disconnect the servo-adapter wires during flashing (something on a strapping pin).
- Dual power (USB + UBEC) — see gap #6. The sacrificial-USB-hub habit is cheap insurance for the whole development period.

## 7. Debugging playbook

**The universal algorithm:** change one thing; retest the smallest subsystem that proves the change; keep a **golden kit** (one servo + one cable + FE-URT-1, all verified in Phase 5) as your known-good reference. The swap test tells you which side is broken: move the *suspect servo* to the known-good port/cable (fault follows servo = servo), then the *known-good servo* to the suspect port/cable (fault stays = cable/port). Two swaps, unambiguous answer.

### No COM port on Windows

1. Cable — the #1 cause. Charge-only USB cables look identical. Test the cable on a phone (does the PC see the phone?).
2. Driver — CP210x for ESP32, CH340 for FE-URT-1. Device Manager shows an unknown device / yellow bang until installed.
3. Different USB port (front-panel ports and hubs misbehave; try a rear/direct port to diagnose, then go back to the sacrificial hub).
4. Board — if two known-data cables and two ports fail, the board's USB is likely dead. Dispute-window evidence time.

### Servo doesn't respond to scan

1. **Servo power present?** Meter V+ to GND *at the servo's connector*: expect pack voltage. USB alone never powers servos. No voltage → fuse, connector seating, or upstream wiring.
2. Common ground between adapter/controller and servo rail?
3. One servo at a time on the bench — always.
4. Scan **all baud rates** (FD software supports this) — a servo you (or the factory) set to a nonstandard baud is invisible at 1M.
5. Connector fully seated? 5264s can sit half-in and feel firm.
6. Swap test with the golden kit.
7. Still dead → mark it, photograph it, move on. Don't sink an evening into one servo out of 18 while the return window ticks.

### Multiple servos respond garbled / all claim ID 1

- Two or more servos share an ID (factory default). Disconnect all but one, assign IDs per the Phase 5 map, reconnect one at a time.

### ESP32 resets when servos move

- This is voltage sag reaching the logic rail. In order: UBEC input tapped from a point that sags (it should feed from the PDB directly, not from a leg branch); ground path too thin/long (logic ground should join the power ground at one solid point); running the whole rig through the smoke stopper (gap #3 — bypass it for motion); laptop-USB-only power during servo tests.
- Firmware mitigation that also helps a healthy rig: soft-start — ramp speeds, stagger multi-servo motion starts by a few ms each, don't command 12 servos from stop in the same instant.

### Bus drops IDs when cables move / intermittent missed replies

- Mechanical, ~always: reseat every 5264 in the path; inspect crimps (gently tug each wire *in* its housing — a bad crimp pulls out); look for a cable flexing right at a joint (strain-relieve so flex happens mid-cable, not at the connector).
- After a leg passes its tests, retain connectors (dab of hot glue on the housing-to-socket seam — removable, not on the pins).

### Fuse blows

- **Instantly, with any load** → dead short downstream. Pull the battery. Unplug all loads on that branch; meter + to − resistance: near-0Ω confirms short; unplug things until it clears — the last thing unplugged contains the short (pinched wire, solder bridge, reversed cap).
- **After seconds/minutes of running** → genuine overload or undersized fuse. Check for a binding joint (servo current telemetry per servo finds the culprit fast).
- Same branch blows twice → stop condition (already in the phases doc). Something structural is wrong; bisect with the branch unloaded.

### Smoke stopper glows steady

- Brief flash then dark = caps charging = normal. Steady glow = a load is drawing hard or there's a short. Disconnect loads one at a time, most-recently-changed first. If it glows with *nothing* connected, the short is in the harness section itself.

### One servo runs hot

- All servos warmish = normal under load; **one** outlier = mechanical bind (does the joint move freely with torque off?), over-tight mounting distorting the case, or a bad unit. Compare current telemetry against its siblings in the same pose — the hot one will be drawing visibly more.

### UBEC output wrong

- Reads ~input voltage (12V) → dead regulator, do not connect logic, bin/return it (this is why Phase 4 tests each one).
- Reads 0V → check input polarity and fuse first; UBECs with reversed input are usually dead afterwards even once corrected.
- Reads 5V no-load but ESP32 browns out under WiFi load → check under load: watch the voltage while the ESP32 runs WiFi + servos scanning. Sagging below ~4.8V loaded = weak unit or thin input wiring; you have spares.

### Servo moves the wrong direction / neutral is off

- Do NOT fix per-servo in EEPROM ad hoc. Fix it in one place in firmware: a calibration table (per ID: direction sign, centre offset, min/max ticks). Geometry problems that need big offsets are Phase 15 "when to redesign" territory — software trims that hide bad geometry are called out there for a reason.

### Print doesn't fit the servo

- Measure the *print*, not just the CAD: PETG holes come out ~0.2-0.4mm undersized. Adjust the coupon, reprint the coupon — never "it's close, I'll force it". Forced pockets pre-load the case and show up later as binding and hot servos.

## 8. Firmware architecture suggestions (Phase 11, programmer-to-programmer)

- **Explicit state machine**: `BOOT → IDLE(torque off) → READY → ACTIVE → FAULT`. Every guard (deadman, low voltage, over-temp, over-current, scan-miss) transitions to `FAULT`, which torque-offs and requires explicit reset. No guard should "just print a warning".
- **Two watchdogs, not one.** The command deadman (F7) catches a dead *link*; the ESP32 hardware task watchdog (`esp_task_wdt`) catches your *own code* hanging. A wedged control loop with torque enabled is the scariest failure the deadman can't see. Configure the task watchdog to actually panic/reset — in some setups its default is a logged warning only, which protects nothing.
- **One calibration struct** per servo: `{id, role, direction, centre_offset, min_ticks, max_ticks}` — the only place geometry lives. Enforce min/max in the command path so no caller can drive a joint past mechanical limits, whatever the IK says.
- **Puppeteer mode is your best early tool**: torque off, move the leg by hand, stream position reads. This finds real joint limits and neutral poses empirically, validates the telemetry path, and gives you record-and-replay poses before any IK exists. The docs never mention it; it's the single highest-value trick these serial servos enable.
- **Use sync-write** (one packet commands all servos) for motion; round-robin telemetry reads (one servo per tick) so the control loop never blocks on 16 sequential reads. At 1Mbps you can comfortably run 50Hz command + full telemetry sweep every ~300ms.
- **Log to CSV from day one** (voltage, per-servo temp/current/position, fault events, millis). Your Phase 15 run log then writes itself, and every "it glitched once yesterday" becomes greppable.
- Never write EEPROM registers from the control loop (gap #9).

## 9. Pre-power ritual (print this)

Before every first power-up of anything new or changed:

1. Rings and watch off. Loop key out. Meter probes in the V socket.
2. Visual: red-to-red/black-to-black at every new joint; cap stripes toward GND; no stray strands at solder joints.
3. Continuity, unpowered: + to − not beeping (or brief cap-beep that dies); fuse path beeps; loop-key-out breaks positive.
4. Smoke stopper inline (static tests only). Loads disconnected.
5. Power. Meter the new section's output voltage before connecting the next stage downstream.
6. One change since the last known-good state. If more than one thing changed, you're not debugging, you're guessing.
