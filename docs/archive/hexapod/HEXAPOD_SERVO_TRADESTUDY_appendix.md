# Servo trade-study — adversarial appendix
_Three GPT-5.5 refutation passes behind HEXAPOD_SERVO_TRADESTUDY.md._

# GPT-5.5 — torque/statics

Read `synthesis2.md`. Main verdict: its torque conclusion is too optimistic, mostly because it misidentifies the 19.5 kg·cm rating voltage.

**Hard Corrections**
The biggest error is in the voltage model: 19.5 kg·cm is not a 6 V rating for the 7.4 V ST3215. Waveshare lists the 7.4 V variant as **19.5 kg·cm @ 7.4 V**, operating **4-7.4 V**, locked-rotor **2.5 A**, `kt = 7.8 kg·cm/A`. Stall torque is a zero-speed condition, so back-EMF is zero. The "scale off no-load/back-EMF point" argument in `synthesis2.md` is wrong.

Correct derating for the owned 19 kg / 7.4 V servos:

| Rail | Stall torque | Stall current / servo | 18-servo stall | Usable @ SF 1.5 | Usable @ SF 2.0 |
|---|---:|---:|---:|---:|---:|
| 5.0 V | 13.2 kg·cm | 1.69 A | 30.4 A / 152 W | 8.8 | 6.6 |
| 6.0 V | 15.8 kg·cm | 2.03 A | 36.5 A / 219 W | 10.5 | 7.9 |
| 7.4 V | 19.5 kg·cm | 2.50 A | 45.0 A / 333 W | 13.0 | 9.8 |
| 30 kg @ 12 V | 30.0 kg·cm | 2.70 A | 48.6 A / 583 W | 20.0 | 15.0 |

So 6 V does not "keep nearly all torque." It loses **19% vs 7.4 V**. 5 V loses **32%**.

**Statics Recheck**
Use:

`joint torque kg·cm = supported mass kg × horizontal foot lever arm cm / support legs`

This assumes the lever arm is measured from the femur pitch axis to the foot contact point. If `synthesis2.md` measured from body center, the femur torque is overstated by the coxa offset. If it measured from femur axis, the math is directionally right.

Corrected required femur torque:

| Mass | Reach | Tripod, 3 legs | Bad transient, 2 legs |
|---:|---:|---:|---:|
| 2.3 kg | 14 cm | 10.7 kg·cm | 16.1 kg·cm |
| 2.5 kg | 14 cm | 11.7 kg·cm | 17.5 kg·cm |
| 2.7 kg | 14 cm | 12.6 kg·cm | 18.9 kg·cm |
| 2.5 kg | 18 cm | 15.0 kg·cm | 22.5 kg·cm |
| 2.7 kg | 18 cm | 16.2 kg·cm | 24.3 kg·cm |

Actual safety factors:

| Case | 19 kg @ 6 V | 19 kg @ 7.4 V | 30 kg @ 12 V |
|---|---:|---:|---:|
| 2.5 kg, 14 cm, tripod | 1.36 | 1.67 | 2.57 |
| 2.7 kg, 14 cm, tripod | 1.25 | 1.55 | 2.38 |
| 2.5 kg, 18 cm, tripod | 1.05 | 1.30 | 2.00 |
| 2.7 kg, 18 cm, tripod | 0.98 | 1.20 | 1.85 |
| 2.5 kg, 14 cm, 2-leg | 0.90 | 1.11 | 1.71 |
| 2.7 kg, 18 cm, 2-leg | 0.65 | 0.80 | 1.23 |

This is the real conclusion: **19 kg is acceptable only as a flat-floor, slow-gait, short-reach prototype.** At 2.5-2.7 kg and 14-18 cm reach, it does not have a proper SF2 margin, even at 7.4 V. At 6 V it is marginal even in clean tripod stance. At 5 V it is not credible.

**19 kg vs 30 kg**
Do not frame this as "30 kg not needed." The correct framing is:

- If total mass stays near **2.0-2.2 kg**, reach stays **10-12 cm**, gait is slow, and terrain is flat: owned 19 kg servos can work.
- If the robot is really **2.5-2.7 kg with phone**, or foot reach is **14-18 cm**, or you expect recovery from slips, turns, body lift, uneven loading, or two-leg transients: **30 kg is the correct actuator class**.
- Since the 19 kg servos are already owned, build with them only if the mechanical design is constrained around their weakness: low CG, short stance, low mass, conservative gait, torque/temp cutbacks.
- Design the chassis and power layout so a 30 kg / 3S swap is not a rebuild.

**Power/BOM Corrections**
The prior 8 A continuous / 15 A peak UBEC idea is under-sized for an 18-servo rail if it is the main servo regulator. At 6 V, all-stall is ~36.5 A output. Even normal walking can hit multi-servo peaks. A "300 W / 20 A" buck at 6 V is only **120 W by output-current limit**, not 300 W. Treat cheap buck ratings as thermal fiction unless tested.

Still un-bought or unresolved:
- High-current servo rail solution: either robust 6-7.4 V regulator with real peak current, or a carefully managed direct/regged 2S strategy.
- Waveshare/Feetech-compatible half-duplex bus driver or ESP32 servo driver.
- FE-URT-1 or equivalent commissioning adapter.
- Correct 5264/2.54 3-pin bus cables, plus spares.
- 2S pack if keeping 19 kg; 3S pack if moving to 30 kg.
- Low-voltage alarm or pack voltage telemetry.
- Per-leg/star power injection, not one long daisy-chain carrying all current.
- Fasteners, heat-set inserts, threadlocker, bearings, TPU feet, PETG/structural filament.
- Actual mass budget from CAD/slicer, not estimates.
- Bench torque/current/temperature test jig.

**Missing Failure Modes**
- Servo load telemetry is not a calibrated torque sensor. Use it for trends and fault detection, not safety-factor proof.
- Continuous torque is far below stall torque. SF1.5 on stall is weak for a walker. SF2 is the minimum sane design check; SF3 is better for continuous thermal margin.
- Leg self-weight and distal servo mass were mostly ignored. Add ~10-20% torque margin unless your CAD proves otherwise.
- Fast downward body motion can regenerate into the rail; many buck converters cannot sink current.
- Long bus chains cause voltage drop and comms faults. Inject power by leg or side.
- Screws that are too long can contact the servo body internally and spike current/burn the servo; Waveshare explicitly warns about this.
- Phone-on-top is a CG and tip-over problem, not just a mass problem.
- Foot slip unloads one leg and overloads another; the math must tolerate this.
- 360° servos need hard software joint limits before gait testing.

**Most-Likely-To-Bite**
1. Wrong rail voltage assumption: 6 V is 15.8 kg·cm, not 19.5.
2. Robot ends up 2.5-2.7 kg and fails torque margin at 14-18 cm reach.
3. Servo regulator cannot supply peak current without sagging/resetting the bus.
4. Thermal overload from operating near stall during stance.
5. Long daisy-chain voltage drop and 5264 connector failures.
6. High CG from phone/battery causing tripod tip-over and load spikes.
7. Under-designed printed joints, horn screws, inserts, and output-bearing support.
8. ID collisions / bad commissioning workflow.
9. No hard joint limits, leading to stripped gears.
10. Treating telemetry "load" as proof of available torque.

Sources checked: Waveshare ST3215 product specs and ST3215 wiki/manual pages: https://www.waveshare.com/st3215-servo.htm and https://www.waveshare.com/wiki/ST3215_Servo.

# GPT-5.5 — risk/completeness

The final answer block (lines 859-970) is GPT-5.5's full output. Here it is verbatim.

---

No, I would not treat `synthesis2.md` as "nothing else is missing." It fixes the old PWM/3S mistakes, but it still has a few build-stopping assumptions.

**Hard Spec Corrections**
The big error: the trade study's "19.5 kg.cm @ 6 V" claim is not what Waveshare lists. Waveshare lists the 7.4 V variant as **19.5 kg.cm @ 7.4 V**, operating **4-7.4 V**, locked-rotor current **2.5 A**, and `Kt = 7.8 kg.cm/A` [source](https://www.waveshare.com/st3215-servo.htm). The same page lists the 30 kg version as **30 kg.cm @ 12 V**.

Corrected linear planning numbers for the 19.5 kg.cm / 7.4 V servo:

| Rail | Stall torque | SF 1.5 usable | SF 2.0 usable | 18x stall current |
|---|---:|---:|---:|---:|
| 5.0 V | ~13.2 kg.cm | 8.8 | 6.6 | ~30 A |
| 6.0 V | ~15.8 kg.cm | 10.5 | 7.9 | ~36.5 A |
| 7.4 V | 19.5 kg.cm | 13.0 | 9.8 | 45 A |

So: **6 V is not full rated torque.** It is about **81% of 7.4 V torque**. 7.4 V buys about **23% more torque than 6 V**, not 15-18%.

The required femur-torque table in `synthesis2.md` is arithmetically right for its simplified model:

| Mass | 10 cm | 14 cm | 18 cm |
|---|---:|---:|---:|
| 2.0 kg tripod | 6.7 | 9.3 | 12.0 |
| 2.5 kg tripod | 8.3 | 11.7 | 15.0 |
| 2.7 kg tripod | 9.0 | 12.6 | 16.2 |
| 2.5 kg two-leg | 12.5 | 17.5 | 22.5 |
| 2.7 kg two-leg | 13.5 | 18.9 | 24.3 |

But using **stall torque** with SF 1.5 is optimistic for a walking robot. At 6 V, **2.5 kg at 14 cm already exceeds SF 1.5 usable torque**. At SF 2.0, even **2.0 kg at 14 cm is marginal/failing**. The safe envelope is closer to: low mass, short stance, slow gait, low duty cycle, smooth terrain.

**Power Architecture Risk**
The "regulated flat 6 V from 2S" recommendation is incomplete. A 2S LiPo is 8.4 V full and roughly 6.0 V near empty. A normal buck converter cannot hold 6.0 V once the pack sags near 6 V under load. It will drop out exactly when the servos are pulling hardest.

You need to choose deliberately:

- **2S direct:** electrically simple, high current, but a fully charged 2S is **8.4 V**, above the listed 7.4 V operating voltage.
- **2S buck to 6 V:** avoids overvoltage, loses torque, drops out near low battery, needs a real 40 A transient-capable regulator.
- **3S into high-current buck set to 6-7.4 V:** safest voltage control, but adds converter heat, size, and another failure point. Raw 3S is still forbidden.
- **Buck-boost:** technically cleanest for a flat 6 V rail from 2S, but it must be sized for hundreds of watts transient.

The prior "8 A / 15 A UBEC is enough" is not credible for the servo rail. It may be enough for logic. The servo rail needs to survive **30-45 A transients** and likely **10-20 A real walking current**.

**Telemetry Assumption Risk**
`synthesis2.md` leans hard on temperature/current telemetry. Waveshare's page explicitly lists feedback as **position, load, speed, input voltage**; its wiki also discusses position/load/voltage/mode and default ID setup [source](https://www.waveshare.com/wiki/ST3215_Servo). Do not assume usable current or temperature telemetry until your exact servos and SDK prove it. If temperature is not exposed, thermal protection needs conservative load-time limits, external thermal checks, and bench characterization.

**Still Missing / Under-Specified**
Must not be hand-waved:

- High-current servo power solution, actually rated and tested at 30-45 A transient.
- Power injection harness per leg. Do not daisy-chain full leg/robot current through tiny servo connectors.
- PDB or custom distribution, branch wiring, main fuse, optional branch fuses.
- Anti-spark or robust switch. Small toggles will fail.
- Logic 5 V regulator isolated from servo dips.
- Low-voltage cutoff/alarm tied to firmware behavior, not just a buzzer.
- Emergency kill switch reachable while the robot is moving.
- FE-URT/programmer or equivalent for one-at-a-time ID assignment.
- Enough real ST/SC bus cables in the correct connector/pinout/lengths.
- Spare bus cables, spare connector housings/pins, crimper if making harnesses.
- At least 1-2 spare servos. One dead servo can stall the whole build.
- Fasteners: M2 body screws, M3 horn/bracket screws, washers, locknuts.
- Heat-set inserts, threadlocker, soldering supplies, strain relief, sleeving.
- PETG/ASA structural filament and TPU feet. PLA near warm servos is a risk.
- Bearings/idler supports if the CAD expects dual-shaft support.
- Current meter or inline wattmeter rated for 50 A.
- Bench supply or smoke-test limiter for bring-up.
- Charger PSU if the B6neo listing does not include one.

**Mechanical Failure Modes**
The torque math is only a first-order check. Real failures are more likely here:

- Foot reach may be larger than assumed once the CAD stands at usable ground clearance.
- Femur torque is posture-dependent; bad tibia angles can multiply loads.
- Tripod gait on a high-CG robot creates roll/pitch moments, not equal mass/3 loading.
- Phone on top is bad CG placement. Battery should go low and central.
- Printed brackets can creep, crack at layer lines, or ovalize around screws.
- Servo output spline/horn screw backlash will grow under gait vibration.
- Single-ended leg loads can overload the servo shaft/bearing before gears fail.
- Hard foot strikes and snagged feet produce shock loads above stall torque.
- TPU feet need enough contact patch; hard plastic feet will slip and spike joint torque.
- No hard stops means one bad command can drive through the printed linkage.
- Wire exit paths through legs must be modeled. Otherwise the first walking test pinches cables.
- Connector retention must be mechanical, not just friction.

**Firmware / Control Risks**
The bus and gait software are not a detail:

- All servos default to ID 1; they must be ID'd one at a time.
- Baud rate and ID map must be recorded in a file, not memory.
- Use SyncWrite for targets; sequential writes create gait skew.
- Telemetry reads must be budgeted. Blocking reads from 18 servos can wreck control timing.
- Timeout behavior must torque-off or freeze safely, not continue stale commands.
- Startup pose must be controlled. Power-on torque at the wrong pose can break legs.
- Joint soft limits must exist before the first gait.
- IK must reject unreachable targets and singular postures.
- Speed/acceleration limits must be set; instant target jumps cause current spikes.
- WiFi/phone control needs a deadman timeout.
- Brownout recovery must not reboot into an uncontrolled gait.
- Servo load units need calibration before using them for foot contact or protection.

**Supply-Chain Risks**
The part naming is messy: ST3215 / STS3215, 7.4 V / 12 V, 19.5 kg.cm / 30 kg.cm, different seller suffixes. Mixing variants will create asymmetric legs. Verify labels and gear ratios on all 18.

Current Waveshare pricing shows **$16.99-$21.99 per servo before shipping/tax** [source](https://www.waveshare.com/st3215-servo.htm). The AliExpress landed-UK estimates in the document may still be possible, but they are not "verified" until checkout with VAT, shipping, and stock shown.

**Most-Likely-To-Bite**
1. Wrong torque premise: 6 V is not full rated torque; margins are thinner than claimed.
2. Power rail design: 2S-to-6 V buck dropout or undersized regulator.
3. Overvoltage temptation: raw full 2S at 8.4 V on a 7.4 V-rated servo.
4. Thermal overload: stall torque used as if it were continuous torque.
5. Tiny connector/current path: daisy-chained servo power carrying too much current.
6. Missing soft limits: 360-degree servo drives printed leg into itself.
7. ID/bus bring-up mistakes: 18 servos all on ID 1, bus collisions, bad baud map.
8. High CG and overweight body: phone/battery/printed mass push it past practical gait margin.
9. Printed joint creep/fastener loosening: screws, horns, brackets loosen before electronics fail.
10. Assuming temperature/current telemetry exists before proving it on the exact servos.

# GPT-5.5 — 30kg cascade/pricing

Read `synthesis2.md`. No files changed.

**Core Refutation**
The biggest error is the "19.5 kg.cm @ 6 V" premise. Waveshare lists the owned ST3215-7.4V as **19.5 kg.cm @ 7.4 V**, operating **4-7.4 V**, locked-rotor current **2.5 A**, `kt = 7.8 kg.cm/A`. So the corrected linear planning numbers are:

| Servo rail | 19kg variant stall estimate |
|---|---:|
| 5.0 V | 13.2 kg.cm |
| 6.0 V | 15.8 kg.cm |
| 7.4 V | 19.5 kg.cm |

So 6 V is not "full torque." It is a reasonable conservative rail, but it gives ~81% of headline torque. Going 6 V -> 7.4 V is a **23% torque increase**, not a small rounding error.

**30kg / 12V / 3S Cascade**
The 30kg ST3215 is rated **30 kg.cm @ 12 V**, operating **6-12.6 V**, locked-rotor current **2.7 A**, `kt = 11 kg.cm/A`. A 2S pack can power it, but then it is not a 30kg servo:

| Supply | 30kg variant stall estimate |
|---|---:|
| 6.0 V | 15.0 kg.cm |
| 7.4 V nominal 2S | 18.5 kg.cm |
| 8.4 V full 2S | 21.0 kg.cm |
| 11.1 V nominal 3S | 27.8 kg.cm |
| 12.0 V | 30.0 kg.cm |
| 12.6 V full 3S | 31.5 kg.cm |

So yes: switching for the advertised "30kg" benefit effectively forces a **3S / 12 V power design**. Raw 3S is not a clean 12 V rail: it ranges about 12.6 V full to ~9 V discharged. If you need stable 30 kg.cm, you need a serious high-current buck-boost/regulator, not just "use 3S."

**Corrected Electrical Deltas**
For 18 servos:

| Case | Rail current at stall | Rail power at stall |
|---|---:|---:|
| Owned 19kg @ 6 V | 45.0 A | 270 W |
| Owned 19kg @ 7.4 V | 45.0 A | 333 W |
| 30kg @ 12 V | 48.6 A | 583 W |

The current delta is small. The **power delta is not**: 30kg @ 12 V is +75% vs 19kg @ 7.4 V, and +116% vs 19kg @ 6 V. That hits runtime, wiring heat, connector stress, fuse sizing, cap voltage rating, regulator choice, and battery C-rating.

**Pricing Check**
Verified Waveshare current page pricing:

| Servo | 4+ unit price | 18-unit subtotal before shipping/tax |
|---|---:|---:|
| ST3215-7.4V 19.5kg | $16.31 | $293.58 |
| ST3215 30kg/12V | $20.63 | $371.34 |

So the verified reseller delta is **$77.76 for 18**, before shipping/VAT. Since the user already owns the 19kg servos, the switch cost is not the delta. It is the full rebuy: roughly **$371 + shipping + VAT**, plus power-system changes. The `£185-290` rebuy estimate may be possible only from cheaper marketplace lots; I would not treat it as verified without logged-in landed checkout.

The "+£5-13 for 3S pack" framing is too narrow. If no battery has been bought, the incremental 2S->3S pack cost may be small. If a 2S pack/regulator path has already been bought, the real switch cost includes the wasted 2S-specific parts plus a 3S battery, 12 V-rated distribution, 25 V capacitors, fusing, connectors, and possibly a buck-boost/current-limited rail.

**Torque Margin Corrections**
Using femur torque = mass share × horizontal reach:

| Robot mass | Tripod @14cm | 2-leg transient @14cm | Tripod @18cm |
|---|---:|---:|---:|
| 2.1 kg | 9.8 kg.cm | 14.7 kg.cm | 12.6 kg.cm |
| 2.3 kg | 10.7 kg.cm | 16.1 kg.cm | 13.8 kg.cm |
| 2.5 kg | 11.7 kg.cm | 17.5 kg.cm | 15.0 kg.cm |
| 2.7 kg | 12.6 kg.cm | 18.9 kg.cm | 16.2 kg.cm |

Owned 19kg @ 6 V with SF 1.5 gives only **10.5 kg.cm usable**. That is already marginal at **2.3 kg / 14 cm**. The trade study's "comfortable to 2.3 kg at 6 V" is too optimistic. At 7.4 V, SF 1.5 usable is **13.0 kg.cm**, barely enough for tripod stance at 2.7 kg / 14 cm, but not for 2-leg transients.

**Wrong / Weak Assumptions**
- 30kg on 2S is mostly pointless. At 7.4 V it estimates ~18.5 kg.cm, close to the owned servo at 7.4 V.
- "3S = 12 V" is false for design. Raw 3S is variable and full charge is exactly the 12.6 V max.
- "Same 55 g" is not proven by the Waveshare page I found. Dimensions are verified identical enough for CAD, but mass should be weighed or sourced from Feetech directly.
- 7.4 V regulated is not the same as raw 2S. Raw 2S full charge is 8.4 V and exceeds the owned servo rating.
- The buck regulator is still a major risk. A cheap "300 W / 20 A" module is not a 45 A hexapod rail.
- Thermal shutdown is not optional. Plastic-case servos near stall will cook before the spreadsheet looks scary.
- The torque table ignores distal leg mass, acceleration, impacts, foot snagging, side loads, and chassis flex.
- Bus reliability is underweighted. One bad 5264/2.54 3P connector or ID collision can take down the chain.

**Still Un-Bought / Must Verify**
Battery, charger, 5 V logic UBEC, servo rail regulator or 12 V distribution path, fuses, kill switch, XT60/XT90 connectors, 25 V bulk caps if 3S, wire gauge, power injection harness, 5264/2.54 3P spare cables, half-duplex TTL interface/servo driver, spare horns/screws, heat-set inserts, feet, phone mount, strain relief, and at least one spare servo or a plan for a dead one.

Sources: Waveshare ST3215 product pages for [19.5kg 7.4V pricing/specs](https://www.waveshare.com/st3215-servo.htm?sku=33014), [30kg 12V pricing/specs](https://www.waveshare.com/st3215-servo.htm?sku=22414), and [ST3215 wiki](https://www.waveshare.com/wiki/ST3215_Servo) for voltage, dimensions, ID collision, feedback, and connector notes.

**MOST-LIKELY-TO-BITE**
1. Believing 6 V gives 19.5 kg.cm. It does not.
2. Buying 30kg servos but keeping the 2S plan, losing most of the advertised benefit.
3. Treating raw 3S as a stable safe 12 V rail.
4. Undersized buck/regulator/wiring for 45-50 A servo faults.
5. Thermal overload during slow stance holds.
6. Foot reach creeping past 14 cm and erasing torque margin.
7. Phone/top mass raising CG and overloading one stance leg.
8. ID collisions from factory-default servo ID 1.
9. 5264 cable/connector failures on a daisy-chained bus.
10. No spare servo/cable when one failed part blocks the whole robot.