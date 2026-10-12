# MIST visual build guide

This is the visual companion to `MIST_BUILD_PHASES.md`.

For Phase 6 and all manufacturing CAD, use
[`MIST_FUSION_360_GUIDE.md`](MIST_FUSION_360_GUIDE.md) plus
[`MIST_FUSION_MASTER_DIMENSIONS.md`](MIST_FUSION_MASTER_DIMENSIONS.md). They
supersede dimensions or Fusion UI shown inside generated images.

The generated panels are orientation aids. The callout notes below are the source of truth. If tiny image text or a generated connector detail disagrees with `MIST_BUILD_PHASES.md`, `MIST_FIELD_GUIDE.md`, or this caption text, follow the text.

Use this guide beside the bench. Do not jump ahead: each panel assumes the previous phase's hard gate passed.

## Visual index

| Phase | Panel | Main decision |
|---:|---|---|
| 0 | Missing parts | Do not start final harness or final chassis until blockers are resolved. |
| 1 | Package intake | Count, photograph, and label everything while disputes are still possible. |
| 2 | Safe bench | Make the bench safe before LiPo power or soldering. |
| 3 | Battery/charger | Prove LiPo balance-charge/storage workflow first. |
| 4 | Electronics dry checks | Verify UBEC 5V and USB data before servos. |
| 5 | Servo intake | Test, assign ID, and label one servo at a time. |
| 6 | CAD/print coupons | Fit-test coupons before full parts. |
| 7 | Joint/wheel module | Validate one joint and one wheel off the robot. |
| 8 | Trunk/logic harness | Build the main power spine with no servo branches yet. |
| 9 | One leg branch | Build one fused branch and signal tap before duplicating. |
| 10 | Single leg test | Static scan through stopper; motion only with stopper bypassed. |
| 11 | Firmware integration | ESP32 controls safely with torque-off/default guards. |
| 12 | Full assembly | Assemble four legs with strain relief and separated voltage domains. |
| 13 | Stand test | Fuses out, static scan, then one branch at a time. |
| 14 | Floor tests | Low speed, kill path proven, no payload. |
| 15 | Reliability loop | Log, inspect, recharge safely, revise. |

## Phase 0 - Missing-part check

![Phase 0 missing parts](images/phase-00-missing-parts.png)

Comments:

- The panel is a pre-build stop sign, not an assembly step.
- Available/ordered items include pigtails, XT90-S, fuses, capacitors, heat shrink, soldering kit, washers, and self-tappers.
- Remaining blockers stay real until physically confirmed: 12/14/16AWG silicone wire, M2/M3 machine screws, M3 nyloc nuts, useful metric hex keys, battery/phone straps, and known data-capable USB cables.
- Pigtails are not a substitute for raw silicone wire. They help, but a clean robot harness still needs wire lengths you can cut to route.
- Self-tappers and washers are partial mechanical coverage. Final frame joints should use real machine screws and locking nuts or heat-set inserts where the printed part allows it.
- Do not floor-test if the LiPo is held by tape only.

Hard gate: consciously resolve or defer every blocker before Phase 1 turns into real assembly.

## Phase 1 - Package intake

![Phase 1 package intake](images/phase-01-package-intake.png)

Comments:

- Open one package at a time. Photograph the package label, item, SKU, option, and any printed voltage/current marking.
- Count the expensive items immediately: 18 servos total, 2 LiPo packs, FE-URT-1, Bus Servo Adapter A, ESP32 CP2102, B6Neo, PDB, UBECs, and 5264 cable packs.
- Label bags for `XT30`, `XT60`, `5264`, `fuses`, `caps`, `fasteners`, `servo horns`, and `servo screws`.
- Confirm every STS3215 says 12V / 30kg / ST-3215-C018 or an equivalent 12V 30kg variant. If a pack looks like a 7.4V variant, stop and document it before applying 3S voltage.
- Inspect LiPos for swelling, crushed corners, damaged insulation, or wrong connector. A damaged pack is not a test item.
- Check that 5264 leads actually fit STS3215 ports. Generic PWM servo extensions do not count for the servo bus.

Hard gate: every expensive item is counted, photographed, and either accepted or marked suspect.

## Phase 2 - Safe bench setup

![Phase 2 safe bench](images/phase-02-safe-bench.png)

Comments:

- Charging/storage area and soldering area are separate. The PVC cutting mat is for cutting and layout, not for hot soldering.
- LiPos sit in the LiPo bag when charging or stored on the bench.
- Remove rings and metal watch straps before handling batteries or live power leads.
- Keep one battery connected at a time.
- Never strip both battery leads at once. Finish and insulate one lead before touching the other.
- Park multimeter probes in `COM` and `V/ohm`, not the current socket.
- Keep the smoke stopper and XT90-S/key path reachable before any powered harness test.
- Practice tinning and heat-shrinking scrap wire before any real connector.

Hard gate: no LiPo-powered wiring until the smoke stopper is present and the meter/iron basics are proven.

## Phase 3 - Battery and charger commissioning

![Phase 3 battery charger](images/phase-03-battery-charger.png)

Comments:

- Use the B6Neo with the Anker 317 100W USB-C PD charger and a 5A e-marked cable.
- Charger settings for the HOOVO packs: LiPo, 3S, 12.6V full target, balance charge, 2.2A max for first charge.
- Never use LiHV or NiMH mode for these packs.
- Before first charge, meter the XT60 main lead and confirm the charger sees all 3 cells through the balance lead.
- First charge stays supervised, in the LiPo bag, on a non-flammable surface.
- Storage-charge packs if you are not building within a few days.
- Remove the LiPo alarm after use; it slowly drains the pack in storage.

Hard gate: each pack has sane per-cell voltages and the charger workflow is understood before it powers servos.

## Phase 4 - Tool and electronics dry checks

![Phase 4 electronics dry check](images/phase-04-electronics-dry-check.png)

Comments:

- Verify each UBEC output before connecting logic. Accept roughly 4.9-5.2V.
- The ESP32 first test is USB-only: data cable, COM port, blink or serial print.
- Use one ESP32 power source at a time by default. If laptop USB and UBEC 5V must both be connected, use a verified power-blocked USB data lead or a cheap sacrificial USB hub.
- The Bus Servo Adapter A dry check is pin identification and common-ground planning. Do not connect servos yet.
- The adapter does not get trusted as a high-current servo power path.

Hard gate: a tested 5V UBEC, known data cable, and known ESP32 COM port exist before servo work.

## Phase 5 - Servo intake, IDs, and register log

![Phase 5 servo ID registers](images/phase-05-servo-id-registers.png)

Comments:

- Connect exactly one factory-default servo at a time. Multiple default-ID servos on the same bus will collide.
- Use FE-URT-1 for intake, ID assignment, register dump, and first motion tests.
- USB powers the adapter logic only. The servo still needs external servo power.
- Log each servo's default registers before changing anything.
- Assign IDs according to the MIST map: front-left 1-4, front-right 5-8, rear-right 9-12, rear-left 13-16, then 17-18 as spares.
- Only the four wheel-role servos get wheel/continuous mode. Mode persists after power cycle, so verify and label immediately.
- Do not attach horns during first intake sweeps.
- Any servo whose protection/registers look like a 7.4V variant stays off raw 3S until resolved.

Hard gate: all 18 servos respond, move smoothly, have unique IDs, and are physically labelled.

## Phase 6 - CAD measurement and print coupons

![Phase 6 CAD print coupons](images/phase-06-cad-print-coupons.png)

Comments:

- Measure the real servo body, mounting ears, horn spline/holes, cable exit, and screw locations. Do not trust listing dimensions.
- Print coupons before full parts: servo pocket, screw boss, washer clearance, horn/hub fit, cable tunnel, and wheel/tire interface.
- PLA is for fast prototypes and disposable fit checks.
- PETG is for load-bearing structure, servo pockets, brackets, and hubs.
- TPU is for tires/feet after PETG workflow is stable.
- Reprint at least one critical fit coupon in PETG before printing a full structural part. PLA clearances do not transfer perfectly.

Hard gate: one PETG servo pocket and one horn/wheel coupon fit correctly before full legs are printed.

## Phase 7 - Single joint and wheel module

![Phase 7 joint and wheel module](images/phase-07-joint-wheel-module.png)

Comments:

- Center every servo at position 2048 before fitting a horn or link.
- Build one joint module first. Check full range by hand and then under low-power command.
- No binding is acceptable. If the linkage binds, fix the print/CAD instead of masking it in software.
- Build one wheel module off the robot. Wheel mode is only for wheel-role servos.
- Cable exit must not pinch through the joint's travel.
- This phase proves the mechanical unit, not the full leg harness.

Hard gate: one joint and one wheel move smoothly off-load with correct mode and no cable pinch.

## Phase 8 - Harness stage 1: trunk, PDB, and logic

![Phase 8 harness trunk logic](images/phase-08-harness-trunk-logic.png)

Comments:

- This is the main spine only: LiPo -> XT90-S -> main fuse -> smoke stopper for static first-power -> PDB.
- Leave PDB branch outputs empty in Phase 8. No leg branches and no servos yet.
- Measure raw battery voltage at the PDB before adding any logic load.
- UBEC input comes from raw 3S. UBEC output is measured before it touches the ESP32.
- Label the UBEC output as 5V.
- XT60/XT30 stay raw 3S only. Do not build adapters that put raw battery voltage onto a 5V connector family.
- Bus Servo Adapter A is dry-checked/planned here; it is not carrying servo current.

Hard gate: polarity, continuity, raw pack voltage, and verified 5V UBEC output all pass through the static smoke-stopper check.

## Phase 9 - Harness stage 2: one leg branch

![Phase 9 one leg branch](images/phase-09-one-leg-branch.png)

Comments:

- Build one branch only before duplicating anything.
- Branch path: PDB XT30 output -> branch fuse -> 16AWG red/black leg branch -> leg-root junction.
- The 4700uF capacitor goes across positive and ground in parallel. It is never inline.
- Observe capacitor polarity. Reversed electrolytic capacitors fail violently.
- The leg-root power tap sends V+ and GND to the servo chain.
- The controller/adapter side sends signal plus common ground only. V+ from the adapter side is isolated.
- A brief continuity beep across + and GND can happen once the capacitor is installed; it should fade. A sustained beep is a short.

Hard gate: one branch has correct polarity, correct fuse, correct cap orientation, and no sustained short before any servo is connected.

## Phase 10 - Single-leg assembly and test

![Phase 10 single leg test](images/phase-10-single-leg-test.png)

Comments:

- Assemble one 3-joint leg plus one wheel on a stand, not on the full robot.
- Center each joint servo at 2048 before fitting horns/links.
- Static ID scan may use the smoke stopper.
- Any motion/load test must bypass the smoke stopper. The stopper causes voltage drop under servo current and creates false failures.
- Servo power comes from the fused leg branch, not from the Bus Servo Adapter A.
- Adapter/controller side provides signal and common ground.
- Start with tiny jog commands and wheel spin off-load.
- Watch cable movement at every joint. Flex should happen in cable loops, not at connector exits.
- Check cable, connector, fuse holder, and servo warmth after short tests.

Hard gate: one full leg moves through safe ranges without bus dropouts, binding, abnormal heat, or warm leg-root cables.

## Phase 11 - Firmware integration

![Phase 11 firmware integration](images/phase-11-firmware-integration.png)

Comments:

- Firmware starts with torque disabled by default.
- The ESP32 is powered from verified 5V logic power, while servos are powered from the separate raw 3S rail.
- USB is for data/debug. Do not power servos from USB or through the ESP32.
- Common ground is mandatory between ESP32, adapter, UBEC, and servo rail.
- Use safe UART pins on the ESP32. Avoid strapping pins and flash pins.
- First firmware functions: bus scan, ID inventory, neutral command, wheel command, telemetry read, torque-off/deadman.
- EEPROM writes happen only in setup tools, not in the control loop.
- Add current/temperature/voltage guards before any multi-servo movement.

Hard gate: firmware can scan expected IDs, torque off reliably, command neutral slowly, read telemetry, and stop on guard conditions.

## Phase 12 - Full mechanical assembly

![Phase 12 full mechanical assembly](images/phase-12-full-mechanical-assembly.png)

Comments:

- Assemble the chassis only after one leg passed Phase 10.
- The battery needs real straps. Tape is not retention.
- Keep XT90-S/key access reachable from outside the body.
- Raw 3S flow is battery -> XT90-S -> main fuse -> PDB -> four fused leg branches.
- UBEC 5V feeds logic only: ESP32, sensors, camera, and similar low-voltage electronics.
- Bus Servo Adapter A carries signal/common reference, not leg servo current.
- Put a capacitor at each leg root across V+ and GND.
- Add strain relief before tightening cable routes. Leave service loops where joints move.
- Use threadlocker only after fit and range are proven.

Hard gate: all four legs are installed, cables are restrained, voltage domains are separated, and no connector can be pulled tight at full joint travel.

## Phase 13 - Full robot stand test

![Phase 13 full robot stand test](images/phase-13-full-robot-stand-test.png)

Comments:

- Put the robot on stands so wheels and legs cannot load the floor.
- Start with all branch fuses out and the robot unpowered.
- Meter rails before inserting fuses.
- Static first-power and ID scan can use the smoke stopper.
- Bypass the smoke stopper before motion.
- Insert one leg branch fuse at a time and verify that leg before adding the next.
- Confirm all 16 installed IDs: 1-4, 5-8, 9-12, 13-16.
- Test neutral pose, then no-load wheel pulses.
- Watch heat at servos, XT30s, fuse holders, capacitors, and cable exits.

Hard gate: all 16 servos work together on stands without dropouts, abnormal current/temperature, or connector heating.

## Phase 14 - First floor tests

![Phase 14 first floor tests](images/phase-14-first-floor-tests.png)

Comments:

- First floor tests are low-speed and no-payload.
- Prove the kill path before motion. The XT90-S/key or battery disconnect must be reachable.
- Start with deadman/torque-off behaviour.
- Then test wheel pulses, crouch/stand, and one-leg lift. A straight roll is
  permitted only after the wheel-heading architecture gate in
  `MIST_BUILD_PHASES.md` Phase 14 is closed (documented scrub acceptance,
  parallel/adjustable pods, omni contact, or steering). Fixed radial wheels
  must not receive a generic skid-steer translation command.
- Keep the top deck empty except required electronics. Do not add phone/payload until base movement is stable.
- Check heat at servos, XT30 connectors, fuse holders, leg-root capacitors, and UBEC after each short run.
- Stop on drift, binding, reboot, missed IDs, repeated guard trips, warm connectors, or battery movement.

Hard gate: the robot can move slowly and stop cleanly, with stable power and no hot spots.

## Phase 15 - Reliability loop

![Phase 15 reliability loop](images/phase-15-reliability-loop.png)

Comments:

- Reliability is a loop: run, log, inspect, revise, repeat.
- Charge or storage-charge LiPos in the LiPo bag, not loose on the bench.
- Record runtime, recharge mAh, cell spread, servo temperatures, current/load peaks, resets, missed IDs, and mechanical faults.
- Inspect fasteners, horns, connectors, fuse holders, caps, strain relief, tire wear, and battery straps after each session.
- Add threadlocker only after a joint has proven fit and range.
- If a connector warms, a fuse repeats, a servo overheats, or a print deforms, treat it as a redesign trigger.
- Keep one known-good golden kit: one servo, one cable, one adapter path, one branch harness.
- Update CAD and wiring notes as soon as a change works.

Hard gate: there is no final hard gate. Keep the robot in this phase until failures become boring and explainable.

## Integration map

![MIST integration map](images/integration-map.png)

Read this as the wiring authority:

- Raw 3S path: LiPo -> XT90-S anti-spark/key -> main 30A fuse -> XT60-to-8x-XT30 PDB -> four fused leg branches.
- Leg branches: each branch has its own fuse, local capacitor across V+/GND, and power injection at the leg root.
- Logic path: UBEC converts raw 3S to 5V for ESP32, sensors, camera, and other low-voltage electronics only.
- Signal path: ESP32 UART -> Bus Servo Adapter A -> STS servo signal bus.
- Ground path: raw power ground, UBEC ground, ESP32 ground, adapter ground, and servo ground must share a common reference.
- Adapter rule: the adapter provides signal/reference. Do not rely on it as the current path for the leg servos.
- Voltage-domain rule: XT60/XT30 are raw 3S in this build. UBEC output is 5V and must be labelled separately.
- Servo ID groups: front-left 1-4, front-right 5-8, rear-right 9-12, rear-left 13-16, spares 17-18.

## Image review notes

- The phase set was storyboarded by subsystem: intake/safety, electronics/harness, mechanical/firmware, and stand/floor/reliability.
- The wiring-critical panels were regenerated after review: Phase 8, Phase 9, Phase 10, Phase 11, Phase 12, Phase 13, and the integration map.
- The biggest correction was smoke-stopper use: it appears only for static first-power/ID-scan checks, never as the path for real motion or load tests.
- The second correction was adapter current: Bus Servo Adapter A is shown as a signal/common-ground interface, while servo current comes from fused raw-3S leg branches.
- The third correction was voltage-domain separation: raw 3S, 5V logic, TTL signal, and common ground are treated as separate layers.
