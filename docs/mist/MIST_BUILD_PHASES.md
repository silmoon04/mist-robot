# MIST build phases after parts arrive

Use this as the build order. The goal is not to assemble the whole robot quickly; the goal is to catch bad parts, wrong variants, wiring mistakes, and CAD fit problems while they are still cheap to fix.

This document assumes the actual ordered inventory in `MIST_ACTUAL_INVENTORY.md`:

- 18x STS3215 12V 30kg servos ordered.
- 3S LiPo raw servo rail: 9.9-12.6V.
- 5V UBEC logic rail.
- Bus Servo Adapter A + ESP32 CP2102 controller.
- B6Neo charger + HOOVO 3S XT60 LiPos.
- XT60 PDB, XT30 branches, XT90-S disconnect, fuses, caps, smoke stopper.

Do not follow old 7.4V hexapod SBEC instructions for MIST. This build uses the 12V STS3215 variant on raw 3S LiPo.

Visual companion: `MIST_VISUAL_BUILD_GUIDE.md`. Print/coupon companion:
`MIST_PRINT_TEST_KIT.md`. Complete CAD companion:
`MIST_FUSION_360_GUIDE.md` with `MIST_FUSION_MASTER_DIMENSIONS.md` as the
numeric authority.

## Phase order summary

| Phase | Name | Main output | Hard gate before moving on |
|---:|---|---|---|
| 0 | Missing-part check | Known blockers list | Silicone wire, fasteners, straps, data cables resolved or consciously deferred. |
| 1 | Package intake | Inventory photos and dispute evidence | Every expensive item counted and photographed. |
| 2 | Safe bench setup | Work area ready | No LiPo, soldering, or servo power before this is ready. |
| 3 | Battery and charger commissioning | Known-good LiPo/charger workflow | Cell voltages sane; B6Neo balance/storage modes understood. |
| 4 | Tool and electronics dry checks | Meter, cables, ESP32, UBEC verified | 5V UBEC reads 4.9-5.2V before touching logic. |
| 5 | Servo intake, IDs, register log | 18 labelled servos + test log | Every servo individually responds, moves smoothly, and has sane registers. |
| 6 | CAD measurement and print coupons | Servo pocket/horn/wheel fit proven | One servo pocket fits before printing full legs. |
| 7 | Single joint and wheel module | One joint and one wheel validated | No binding; wheel mode works off-load. |
| 8 | Harness stage 1: trunk/PDB/logic | Safe main power spine | Polarity and voltage pass through smoke stopper. |
| 9 | Harness stage 2: one leg branch | One fused leg power branch | Branch fuse, cap polarity, and voltage verified. |
| 10 | Single-leg assembly | One 3-joint leg + wheel on stand | Current, temperature, bus reliability pass. |
| 11 | Firmware integration | ESP32 controls servos safely | Deadman, torque-off, ID scan, neutral pose all work. |
| 12 | Full mechanical assembly | Full chassis and four legs assembled | Harness strain relief and battery retention done. |
| 13 | Full robot stand test | All 16 active servos work together | No bus dropouts, no overheating, no abnormal current. |
| 14 | First floor tests | Controlled wheel/leg motion | Kill path proven; slow movement stable. |
| 15 | Reliability pass | Tuned, documented robot | Logs, fastener checks, spare plan, and failure notes complete. |

## Phase 0 - Missing-part check before serious assembly

Purpose: prevent getting blocked halfway through wiring or mechanics.

Parts already ordered that matter:

- XT30/XT60 pigtails.
- XT90-S disconnect.
- Fuse holders and blade fuses.
- 4700uF 25V capacitors.
- Heat shrink.
- Soldering iron, 63/37 solder, desolder wick, wire stripper.
- Washers and self-tappers.

Still not proven from actual orders:

| Item | Why it matters | Minimum useful target |
|---|---|---|
| 12AWG red/black silicone wire | Battery trunk and high-current short links. | 1m pair. |
| 14AWG red/black silicone wire | PDB-to-branch/trunk work where 12AWG is bulky. | 1m pair. |
| 16AWG red/black silicone wire | Leg branch wiring and XT30 branch sections. | 1-2m pair. |
| M2 machine screws | Servo case mounting if self-tappers are bad or insufficient. | M2x6 and M2x8, about 100 pcs total. |
| M3 machine screws | Frame, leg links, battery tray, brackets. | M3x6/8/10/12/16 mixed, 100-150 pcs. |
| M3 nyloc nuts | Vibration-resistant frame joints. | 50-100 pcs. |
| Metric hex keys/drivers | Servo/frame screws. | 1.5, 2.0, 2.5, 3.0mm. |
| Battery straps | LiPo and phone/payload retention. Tape is not enough. | 20mm hook-loop straps, 3-4 pcs. |
| USB data cables | ESP32, FE-URT-1, B6Neo/PC. Charge-only cables waste hours. | Known data-capable USB-C and whatever FE-URT-1 uses. |

Hard gate:

- Do not build the final harness without silicone wire.
- Do not assemble the final chassis without proper M2/M3 hardware.
- Do not floor-test with only tape holding the LiPo.

## Phase 1 - Package intake and evidence

Purpose: catch wrong parts while returns/disputes are possible.

Parts needed:

- Phone camera.
- Calipers.
- Multimeter.
- A labelled box or bags for each subsystem.
- `MIST_ACTUAL_INVENTORY.md` open for cross-checking.

Process:

1. Open one package at a time.
2. Photograph the package label, item, SKU/variant label, and included accessories.
3. Count quantities immediately.
4. Put small parts into labelled bags: `XT30`, `XT60`, `5264`, `fuses`, `caps`, `fasteners`, `servo horns`, `servo screws`.
5. For expensive items, photograph the listing/order page next to the physical item if possible.

Specific checks:

| Part | Check |
|---|---|
| STS3215 packs | Must be 12V / 30kg / ST-3215-C018 or equivalent 12V 30kg variant. Count 18 servos. |
| FE-URT-1 | Confirm USB connector type and servo power terminal/header. |
| Bus Servo Adapter A | Confirm it is Adapter A for ST/SC serial bus servos, not a PWM board. |
| ESP32 CP2102 | Confirm it enumerates as a COM port on Windows with a data cable. |
| 5264 cables | Confirm they physically fit STS3215 ports. Generic PWM servo extensions do not count. |
| UBECs | Confirm selected voltage/output label. Do not trust colour or listing title alone. |
| Fuse holders/fuses | Confirm fuse size matches holder size. Standard blade and mini blade are not interchangeable. |
| XT90-S cable | Confirm wire gauge and length. Too long is usable but should be shortened/rebuilt later. |
| LiPo packs | Inspect for swelling, crushed corners, damaged wires, wrong connector. |

Hard gate:

- If any servo pack looks like the wrong voltage/variant, stop and document before powering it.
- If the battery is swollen, punctured, or physically damaged, do not charge it.

## Phase 2 - Safe bench setup

Purpose: make the workspace safe before soldering or LiPo power.

Parts needed:

- Safety goggles.
- LiPo bag.
- B6Neo charger.
- Multimeter.
- Smoke stopper.
- Soldering iron, stand, solder, wick, heat shrink.
- Non-flammable work surface or scrap tile/metal sheet. The PVC cutting mat is for cutting, not hot soldering.
- Small fan or ventilation for solder fumes.

Setup:

1. Put LiPos in the LiPo bag when charging or storing.
2. Keep one battery connected at a time.
3. Keep connector genders obvious: battery/source side should not expose live male pins.
4. Never strip both battery leads at once. Finish and insulate one lead before touching the other.
5. Keep the XT90-S loop key or battery connector reachable during powered tests.
6. Remove rings and metal watch straps before handling LiPos or live power leads.

Required tests:

- Multimeter continuity beep works.
- Multimeter DC voltage reading works on a known source.
- Soldering iron reaches temperature and tins a scrap wire.
- Heat shrink actually shrinks with your heat source.

Hard gate:

- No LiPo-powered wiring until the smoke stopper is physically available and tested for continuity.

## Phase 3 - Battery and charger commissioning

Purpose: learn the charger before it matters and catch bad LiPos.

Parts needed:

- SKYRC B6Neo.
- Anker 317 100W USB-C PD charger and 5A e-marked cable.
- HOOVO 3S 2200mAh XT60 LiPos.
- LiPo bag.
- Multimeter.
- LiPo alarm.

Process:

1. Power the B6Neo from the Anker 317.
2. Confirm the B6Neo sees USB-C PD input.
3. Set the charger workflow to LiPo, 3S, 12.6V target. Never use LiHV or NiMH mode for these packs.
4. Measure pack main XT60 voltage with the multimeter.
5. Plug the balance lead into the B6Neo and read per-cell voltages.
6. Put each pack into storage charge if not using immediately.
7. Do one supervised balance charge at 1C or lower: 2.2A max for a 2200mAh pack.
8. After charge, confirm cells are close. Target difference should be small; if one cell is far off, mark the pack suspect.

Battery rules:

- Full 3S pack is 12.6V.
- Storage voltage is about 3.8V/cell, about 11.4V pack.
- Stop using before cells are deeply discharged. Set the LiPo alarm conservatively.
- Never leave the LiPo alarm plugged in during storage; it slowly drains the pack.

Hard gate:

- Do not use a LiPo for servo testing until the charger can read all 3 cells and the pack passes basic voltage sanity.

## Phase 4 - Tool and electronics dry checks

Purpose: prove low-voltage electronics before connecting servos.

Parts needed:

- ESP32 CP2102 dev board.
- USB data cable.
- Bus Servo Adapter A.
- UBEC.
- Multimeter.
- 3S LiPo or charger/power source.
- Smoke stopper.
- XT30/XT60 pigtails as needed.

UBEC test:

1. Connect UBEC input to a 3S source through a fuse and smoke stopper.
2. Leave UBEC output disconnected.
3. Measure output with the multimeter.
4. Accept 4.9-5.2V.
5. Mark that UBEC as tested with tape.
6. Repeat for each UBEC module.

ESP32 test:

1. Plug ESP32 into Windows.
2. Confirm a COM port appears.
3. Flash a simple blink or serial print sketch.
4. Record board type, COM port, and cable used.

Bus Servo Adapter dry check:

1. Identify power input, GND, TX, RX, and servo bus connector.
2. Do not connect servos yet.
3. Confirm common ground path between ESP32 GND and adapter GND.

Hard gate:

- Do not connect the ESP32 to the UBEC until UBEC output is verified by multimeter.
- Do not connect a servo until the FE-URT-1 process in Phase 5 is ready.
- Use one ESP32 power source at a time by default. If laptop USB and UBEC 5V must both be connected, use a verified power-blocked USB/data lead or a sacrificial USB hub.

## Phase 5 - Servo intake, ID assignment, and register log

Purpose: every servo ships effectively unknown. Commission them one at a time before they are buried in the robot.

Parts needed:

- 18x STS3215 servos.
- FE-URT-1.
- Windows laptop.
- FE-URT/Feetech software or a known STS3215 tool.
- 3S LiPo at storage voltage or a current-limited bench supply if later obtained.
- Smoke stopper.
- 5A or 7.5A fuse if available for single-servo testing.
- Masking tape and marker.
- Multimeter.

Important MIST-specific rule:

- These are intended to be 12V servos. Do not copy old 7.4V hexapod register limits into them.
- A 12V variant may have a higher over-voltage limit than the old 7.4V plan. Read and log defaults first.
- Only change ID and mode/settings you understand. If a register differs from an old 7.4V note but matches the 12V datasheet/listing behaviour, do not "fix" it.
- Variant cross-check: read the voltage-protection register default. The 12V STS3215-C018 protects above ~14V; the 7.4V C001 above ~7.4V. A servo whose protection reads ~7.4V stays off the 12V rail until its identity is resolved, whatever the sticker says.

Suggested ID map:

| ID | Position |
|---:|---|
| 1 | Front-left coxa |
| 2 | Front-left femur |
| 3 | Front-left tibia |
| 4 | Front-left wheel |
| 5 | Front-right coxa |
| 6 | Front-right femur |
| 7 | Front-right tibia |
| 8 | Front-right wheel |
| 9 | Rear-right coxa |
| 10 | Rear-right femur |
| 11 | Rear-right tibia |
| 12 | Rear-right wheel |
| 13 | Rear-left coxa |
| 14 | Rear-left femur |
| 15 | Rear-left tibia |
| 16 | Rear-left wheel |
| 17 | Spare A |
| 18 | Spare B |

> **Tooling compatibility note (resolved 2026-07-13):** this bench map orders
> the rear groups RR then RL. `sim/js/exports.js` now explicitly reorders the
> simulator's internal `FL, FR, RL, RR` arrays at the hardware-export boundary,
> so generated IDs match this table. Still verify leg, joint, sign and neutral on
> an unloaded bench leg before enabling normal torque.

Procedure per servo:

1. Connect exactly one servo to FE-URT-1.
2. Feed servo power from a safe 3S source through fuse/smoke stopper, or a current-limited supply if you have one.
3. Scan at the default baud.
4. Confirm the servo responds.
5. Assign the planned ID.
6. Power-cycle and rescan to confirm the new ID.
7. Jog gently through a small range with no horn fitted.
8. Read and log voltage, temperature, current if the tool exposes them.
9. Read and log protection/register defaults, including mode where available. Do not mass-edit them.
10. Only the four wheel-role servos should be put into wheel/continuous mode; immediately verify and label those roles because the mode persists.
11. Put tape on the servo with its ID and role.

Pass criteria:

- Servo responds reliably.
- ID change survives power cycle.
- Movement is smooth, no grinding, no twitching.
- No-load current is not obviously abnormal compared with the rest.
- Temperature reading is plausible.

Fail criteria:

- No response after cable/baud/power checks.
- Servo cannot retain ID.
- Servo draws much more current than the others with no load.
- Servo clicks, binds, or smells hot.

Hard gate:

- Do not install an unlabelled or untested servo into a printed part.
- Do not connect multiple factory-ID servos at once before assigning IDs, or they can all answer as ID 1.

## Phase 6 - CAD measurement and print coupons

Purpose: prove dimensions before wasting filament on full legs.

Parts needed:

- Digital calipers.
- One tested STS3215 servo.
- Servo horn and screws from the pack.
- PETG.
- 3D printer.
- M2/M3 hardware or the included self-tappers.

Measurements to capture:

- Servo body length, width, height.
- Mounting ear thickness.
- Hole spacing.
- Output shaft centre relative to body edges.
- Back-side idler/stub geometry if present.
- Horn diameter, screw pattern, centre hole.
- Cable exit direction and clearance.

Print coupons:

1. Print a simple servo pocket block.
2. Print a horn/wheel bolt-pattern test piece.
3. Print a screw boss test with your intended M2/M3 screw.
4. Test PETG shrink/clearance.

Material note:

- PLA (on hand, ~3kg) is fine for every coupon and prototype in this phase — iterate freely.
- Final servo pockets and structural parts must be PETG: PLA creeps under sustained load and softens near servo operating temperature.
- Re-verify critical fits with one PETG coupon when PETG arrives; PLA-tuned clearances transfer only approximately.

Design rules:

- Leave about 0.2-0.3mm clearance per face for PETG fit unless your printer proves otherwise.
- Do not clamp the servo case so hard that the case distorts.
- Leave cable exit space.
- Support joints from both sides where practical: output horn side and idler/back side.
- Keep wheel hubs PETG and tires TPU.

Hard gate:

- Do not print four full legs until one servo pocket and one horn/hub test fit correctly.

## Phase 7 - Single joint and wheel module

Purpose: validate mechanical load paths and wheel mode separately from the full robot.

Parts needed:

- One tested servo.
- One printed joint bracket.
- One printed wheel hub.
- One TPU tire or temporary printed wheel.
- M2/M3 hardware.
- FE-URT-1 or ESP32 controller.

Joint test:

1. Install the servo in the bracket.
2. Secure the bare servo in a fixture with the output clear, power it through the current-limited bench path, and command centre (position 2048). Mark the shaft/case reference, torque-disable if supported, then power down and verify with telemetry/mark that the shaft has not moved. Fit the horn at the intended mechanical neutral **only while de-energised**; keep fingers and tools clear before power is restored. Never fit a horn to an uncentred servo, but never use holding torque as the assembly fixture.
3. Move through the expected range slowly.
4. Watch for case flex, screw pull-out, horn rub, and cable pinch.
5. Reverse direction several times.

Wheel test:

1. Fit wheel hub to the horn.
2. Command wheel/continuous rotation mode only on the intended wheel servo.
3. Run at low speed first.
4. Check wobble, hub slip, screw loosening, and tire rubbing.

Pass criteria:

- No binding through usable range.
- Screws stay tight through repeated motion.
- Wheel spins without major wobble.
- Servo case is not used as a structural bearing in a way that twists it.

Hard gate:

- Do not model the whole leg around an unproven horn/hub geometry.
- Do not fit any horn or leg link to a servo that has not been commanded to centre first.

## Phase 8 - Harness stage 1: trunk, PDB, and logic rail

Purpose: build the power system in small testable sections.

Parts needed:

- 3S LiPo.
- XT90-S disconnect.
- 30A fuse holder and 30A fuse.
- XT60 PDB.
- XT60/XT30 pigtails.
- 12AWG/14AWG silicone wire.
- Smoke stopper.
- Multimeter.
- Heat shrink.
- UBEC.
- Bus Servo Adapter A.
- ESP32.

Target topology:

```text
3S LiPo XT60
  -> XT90-S disconnect / loop key
  -> 30A main blade fuse near battery
  -> smoke stopper during first tests
  -> XT60 PDB
      -> 5V UBEC -> ESP32 / sensors / camera
      -> Bus Servo Adapter A power input if used
      -> four fused leg branches later
```

Assembly process:

1. Build only the battery-to-PDB section first.
2. Check every connector polarity before soldering.
3. Solder one lead at a time and heat-shrink immediately.
4. Keep voltage-domain discipline: XT60/XT30 carry raw 3S only; label UBEC output as 5V; never adapt raw battery voltage onto a 5V connector family.
5. With no loads attached, check continuity:
   - Positive should not beep to negative.
   - Fuse holder should beep through the fuse.
   - XT90-S removed should interrupt positive.
6. First power through smoke stopper.
7. Measure PDB output voltage at every XT30 output.
8. Add UBEC input from one PDB output.
9. Measure UBEC output before connecting logic.
10. Connect ESP32 only after UBEC output passes.

Pass criteria:

- No smoke-stopper glow at no-load except maybe a brief cap-charge flash.
- PDB outputs match pack voltage and polarity.
- UBEC output is 4.9-5.2V.
- ESP32 powers normally from UBEC.

Hard gate:

- Do not connect any servo branch until the trunk/PDB/UBEC stage passes.

## Phase 9 - Harness stage 2: one fused leg branch

Purpose: validate one branch before duplicating it four times.

Parts needed:

- XT30 pigtail pair.
- 16AWG silicone wire.
- Inline fuse holder.
- 15A blade fuse for leg branch.
- 4700uF 25V capacitor.
- 5264 servo cable/tail.
- Heat shrink.
- Multimeter.
- Smoke stopper.

Target branch:

```text
PDB XT30 output
  -> 15A blade fuse
  -> 16AWG leg branch
  -> 4700uF 25V cap at leg root
  -> STS3215 V+ and GND injection at leg root
```

Open topology gate: the body ultimately needs four signal/common-ground leg
branches while each four-servo leg also needs a coxa→femur→tibia→wheel daisy
chain and root power injection. The current BOM does not prove a serviceable
1→4 TTL/GND hub, Y-splice, or equivalent. Reserve accessible body volume and do
not freeze connector slots until a pin-by-pin harness drawing shows which coxa
port carries onward bus and where the root injection joins it.

Capacitor rule:

- Electrolytic caps are polarised.
- Stripe on cap is negative.
- Negative goes to battery negative/GND.
- Reversed caps can vent or fail violently.

Signal/data rule:

- Servo bus needs common GND and signal.
- Do not rely on the Bus Servo Adapter A to carry leg current.
- Any adapter-to-leg 5264 signal cable must not become the main power path. Do not cut or depin a conductor from colour or connector position alone. First continuity-identify every pin against authoritative adapter/servo pinouts, approve the complete four-branch harness drawing, label both ends, and verify the modified signal-only lead again before power. Prefer a documented purpose-built signal/GND harness or reversible depinning/insulation over an irreversible mid-wire cut.
- Leg power enters at the fused branch/root.

Tests:

1. Continuity with fuse removed: branch positive open.
2. Continuity with fuse installed: branch positive connected.
3. Positive-to-GND: no sustained beep. A brief beep that fades while resistance rises is normal capacitor charging.
4. Cap polarity visually checked twice.
5. Power through smoke stopper with no servo: branch voltage equals pack voltage.
6. Power one servo torque-off: smoke stopper stays dark after cap charge.

Hard gate:

- Build only one leg branch first. Duplicate the branch only after it passes.

## Phase 10 - Single-leg assembly and test

Purpose: validate mechanical, electrical, and firmware assumptions on one corner.

Parts needed:

- Four servos for one leg: coxa, femur, tibia, wheel.
- Printed leg parts.
- Printed wheel hub and TPU tire.
- One fused leg branch.
- 4700uF cap at leg root.
- 5264 servo cables.
- Bus Servo Adapter A + ESP32 or FE-URT-1.
- Smoke stopper.
- Multimeter.
- Scale or known weight.

Assembly:

1. Assemble one leg only.
2. Before attaching each coxa/femur/tibia horn or link, command that servo to centre position 2048 and fit the linkage at the intended neutral geometry.
3. Route cables before tightening everything.
4. Keep cable loops clear of moving joints.
5. Connect leg power at the root.
6. Connect signal/GND to the bus.
7. Keep the robot/leg clamped or on a stand; do not free-stand yet.

Tests:

1. Static torque-off ID scan through the smoke stopper: confirm all four IDs reply.
2. Bypass the smoke stopper before any jog, wheel, neutral-pose, or load test. A bulb stopper sags the rail during motion.
3. Single-joint jog: move coxa only, then femur only, then tibia only.
4. Wheel spin: run wheel slowly both directions.
5. Neutral pose: command all three joints to neutral.
6. Load test: apply a small known load at the foot and watch current, temperature, and whether the leg-root or daisy-chain cables warm.
7. Cable wiggle test: gently move cables and watch for missed replies.

Pass criteria:

- All four servos respond reliably.
- No joint binds.
- No cable gets pulled at range limits.
- Branch fuse does not nuisance-blow during gentle tests.
- No servo heats quickly at no-load.

Hard gate:

- Do not print/build the other three legs until one leg passes fit, range, cable, and power tests.

## Phase 11 - Firmware integration

Purpose: make the control stack safe before the robot can move under its own power.

Parts needed:

- ESP32 CP2102.
- Bus Servo Adapter A.
- One tested servo first, then one tested leg, then all servos later.
- Arduino/PlatformIO toolchain.
- STS/SCServo library or compatible serial-bus library.
- USB data cable.

Milestones:

| Milestone | Test |
|---|---|
| F0 serial bring-up | ESP32 prints logs over USB. |
| F1 adapter link | ESP32 can ping one servo ID. |
| F2 ID scan | ESP32 scans and reports the expected connected IDs. |
| F3 torque off/on | ESP32 can enable and disable torque safely. |
| F4 neutral pose | One leg moves to a known safe neutral pose slowly. |
| F5 wheel command | Wheel servo spins slowly in both directions. |
| F6 telemetry | Read voltage/temp/current if library supports it. |
| F7 deadman | If command stream stops for 500ms, robot stops/crouches/torque-offs. |
| F8 current/temperature guard | If telemetry is abnormal, stop motion. |

Implementation order:

1. One servo on the bench.
2. One wheel servo on the bench.
3. One assembled leg on a stand.
4. Four legs on a stand.
5. Floor movement.

Firmware safety rules:

- Default boot state: torque off.
- Any unknown command: no motion.
- Any missed bus scan: stop.
- Any low battery condition: stop.
- Any over-temperature condition: stop.
- Speed limits low at first. Increase only after logs look sane.

Hard gate:

- Do not floor-test until deadman and torque-off are implemented.

## Phase 12 - Full mechanical assembly

Purpose: assemble the full robot only after one leg and the harness design are proven.

Parts needed:

- Remaining printed legs and chassis.
- PETG frame parts.
- TPU tires/feet.
- M2/M3 screws, washers, M3 nyloc nuts.
- Loctite 243.
- Battery straps.
- Cable ties / cable organizer.
- Heat shrink.

Assembly order:

1. Assemble chassis without electronics.
2. Repeat the Phase 10 centre-before-horn/link procedure for every remaining leg; do not align horns by eye on unpowered servos.
3. Install servos into each leg.
4. Install legs to chassis.
5. Install PDB and main power trunk.
6. Install battery tray and straps.
7. Install ESP32, Bus Servo Adapter A, UBEC, sensors.
8. Route one leg branch at a time.
9. Add strain relief at every moving joint crossing.
10. Only apply Loctite after a joint has been assembled, tested, and likely will not need immediate changes.

Mechanical checks:

- Full range of each joint without collision.
- Wires do not enter gear/horn paths.
- Battery cannot slide out in any orientation.
- PDB and ESP32 cannot touch conductive screw heads.
- No sharp PETG edges cut wires.
- Servo screws are snug, not case-crushing.

Hard gate:

- Do not install all fuses and power the full robot until every branch has passed polarity and continuity checks.

## Phase 13 - Full robot stand test

Purpose: test the complete electrical system with the feet off the ground.

Parts needed:

- Full assembled robot.
- Stand or blocks so wheels/feet cannot drive off the bench.
- Smoke stopper.
- Multimeter.
- B6Neo-charged LiPo.
- Laptop serial monitor.
- Power-blocked USB/data lead or sacrificial USB hub if laptop USB stays connected while UBEC powers the ESP32.

Test sequence:

1. Remove all leg branch fuses.
2. Power main trunk through smoke stopper for the initial static check only.
3. Confirm ESP32 boots.
4. Insert one leg fuse.
5. Scan IDs for that leg (torque off — this is still low current).
6. Bypass the smoke stopper before any jog/motion step. A bulb stopper drops voltage in proportion to current, so servos moving through it sag the rail and cause false resets/dropouts.
7. Jog that leg gently.
8. Repeat for each leg.
9. With all four branch fuses installed, scan IDs 1-16.
10. Command neutral pose.
11. Spin each wheel slowly, one at a time.
12. Command all wheels at low speed on the stand.
13. Wiggle harness gently while watching for missed replies.
14. Monitor servo temperatures after 5-10 minutes.

Pass criteria:

- All 16 active IDs respond.
- Spares 17/18 remain disconnected or labelled separately.
- No branch behaves differently from the others.
- Smoke stopper does not glow except brief capacitor inrush.
- No connector warms.
- No servo heats quickly while unloaded.

Hard gate:

- Do not put the robot on the floor until stand tests pass with repeatable results.

## Phase 14 - First floor tests

Purpose: verify real motion at low risk.

Parts needed:

- Full robot.
- Charged LiPo.
- LiPo alarm.
- Open floor area.
- Kill/disconnect reachable.
- Laptop/phone control.

Test order:

1. Confirm the wheel-heading architecture gate is closed: documented low-speed scrub test, parallel/adjustable pods, omni contact, or steering. Do not use generic skid-steer commands with unresolved fixed radial wheels.
2. Place robot on a clear floor with the battery strapped, physical disconnect reachable, and a spotter outside the mechanism envelope.
3. Power up with the architecture-specific mapping and conservative speed/current limits.
4. Confirm deadman: stop sending commands and verify motion stops.
5. Command each wheel individually for 0.5 seconds in each direction; verify its labelled corner and sign before combining wheels.
6. Run one 0.5-second, lowest-speed architecture-specific translation test. Expect and record scrub only if that trade-off was explicitly selected.
7. Run an architecture-specific yaw/turn test only if the selected wheel geometry is supposed to support it; do not force fixed radial wheels to imitate ordinary skid steering.
8. Stop and check current, fasteners, tyre movement and temperatures.
9. Crouch/stand transition with no travel.
10. One-leg lift and place, robot supported if needed. Slow mixed wheel-leg motion comes only after all earlier checks pass.

Do not do on first floor test:

- No high-speed wheel runs.
- No stairs.
- No outdoor dirt.
- No phone/payload unless the base robot passes unloaded.
- No long runtime test until current and temperature logs are sane.

Pass criteria:

- Robot obeys stop/kill every time.
- Battery does not move.
- No branch fuse blows.
- No leg drags cable.
- Hottest servo remains comfortably below protection threshold.

Hard gate:

- Do not add payload/camera behaviour until the base drive is boring and repeatable.

## Phase 15 - Reliability, tuning, and documentation

Purpose: turn a working prototype into something you can debug and improve.

Parts needed:

- Notebook or repo log file.
- Multimeter.
- B6Neo charge data.
- Spare fuses.
- Loctite.
- Zip ties/cable ties.

Create a run log:

| Field | Example |
|---|---|
| Date/time | 2026-07-xx |
| Battery | HOOVO pack A |
| Start voltage | 12.4V |
| End voltage | 11.3V |
| Runtime | 12 min |
| Test | wheels-only indoor |
| Faults | none / FL wheel dropout |
| Hottest servo | ID 6, 48C |
| Fix applied | rerouted cable / tightened hub |

Reliability checks after every early run:

- Recheck wheel hub screws.
- Recheck servo mounting screws.
- Inspect 5264 connectors.
- Inspect branch fuse holders.
- Inspect cap solder joints.
- Inspect battery strap.
- Check LiPo cell balance after recharge.

When to apply Loctite:

- After fit is proven.
- On metal-to-metal screws.
- Not on plastic threads unless you know the plastic is compatible.
- Use a small amount. More is not stronger.

When to redesign:

- Servo temperature rises fast at low load.
- Current is much higher than expected for a pose.
- PETG cracks at screw bosses.
- Wheel hub wobbles.
- Wires are tight at joint limits.
- The robot needs software trims that hide bad geometry.

## Integration map

Electrical integration:

```text
3S LiPo
  -> XT90-S disconnect
  -> 30A main fuse
  -> XT60 PDB
      -> 15A fused leg branch FL -> FL servos IDs 1-4
      -> 15A fused leg branch FR -> FR servos IDs 5-8
      -> 15A fused leg branch RR -> RR servos IDs 9-12
      -> 15A fused leg branch RL -> RL servos IDs 13-16
      -> 5V UBEC -> ESP32 / sensors / camera
      -> Bus Servo Adapter A power/common reference as required
```

Signal integration:

```text
ESP32 Serial1
  -> Bus Servo Adapter A
  -> common STS bus signal + GND
  -> four leg signal taps
  -> each leg daisy-chains coxa/femur/tibia/wheel
```

Power-injection rule:

- Servo current comes from fused leg branches, not through the Bus Servo Adapter A.
- Grounds must be common.
- If a 5264 cable is only serving as an adapter-to-leg signal tap, isolate V+ and keep GND/signal.

Software integration:

```text
Boot
  -> torque off
  -> scan expected IDs
  -> verify battery/servo telemetry if available
  -> wait for command
  -> command neutral
  -> enable low-speed control
  -> watchdog/deadman active forever
```

## First-week priority list

If parts arrive in a messy order, use this priority:

1. Batteries/charger safety.
2. Servo variant check.
3. FE-URT-1 single-servo ID/register testing.
4. ESP32 USB/toolchain check.
5. Caliper measurements and print coupons.
6. UBEC voltage checks.
7. One wheel module.
8. One leg branch harness.
9. One complete leg on a stand.
10. Full robot only after the above is boring.

## Stop conditions

Stop immediately if any of these happen:

- Smoke stopper glows bright and stays bright.
- A connector gets warm.
- A capacitor vents, bulges, or is reversed.
- A LiPo swells, smells, or has one bad cell.
- A servo draws much more current than the rest no-load.
- Bus scan drops IDs when cables move.
- ESP32 resets when servos move.
- A fuse blows twice in the same branch.
- A printed part cracks near a servo pocket.

When stopped, change one thing, then retest the smallest subsystem that can prove the fix.
