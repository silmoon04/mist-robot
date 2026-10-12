# MIST available parts

This short inventory combines the order record with the latest physical audit.
Anything listed under **Confirm before final design** still needs a count,
label check, or measurement before release.

## Actuation

- **18 Feetech STS3215 serial-bus servos** are present: 16 for the robot and 2
  spares. The ordered variant is **ST-3215-C018, 12 V, 30 kg·cm peak stall**.
  Use **10 kg·cm as rated torque** and about **2.7 A as stall current at 12 V**.
  The reference body envelope is `45.2 × 24.7 × 35 mm`, about `55 g` each.
- **1 FE-URT-1 USB adapter** is present for bench servo setup and testing. It is
  not intended to stay on the robot.
- The intended stock is **18 Feetech 5264 three-pin bus leads**, but these were
  not found in the latest audit. Generic PWM servo extensions do not fit this
  role.

## Compute and control

- **1 ESP32 DevKitC / WROOM-32 board** is recorded as the low-level controller.
- **1 Bus Servo Adapter A** is recorded as the ESP32-to-servo interface. It is
  not a regulator or main servo-current path; its board limit is about `5 A`.
- **1 Xiaomi Mi 9 SE phone** is assigned for cameras, interface, and additional
  processing. Its nominal bare envelope is
  `147.5 × 70.5 × 7.45 mm` and `155 g`; allow separately for its case, cable,
  padding, and removal path.

The existing `brain/` folder contains an agent harness, voice and tool
interfaces, movement skills, safety checks, and expressive face assets.

## Sensing and interaction

- The phone provides cameras plus IMU, compass, and GPS sensors.
- **1 VL53L0X time-of-flight distance sensor** is recorded; the exact breakout
  board size still needs measuring.
- **5 cm acrylic mirror triangles** are recorded for optional face details.

## Power

- **2 HOOVO 3S LiPo packs** are confirmed present. Each is `2200 mAh`, `11.1 V`
  nominal, `12.6 V` full, `50 C` listing, with XT60; mount one pack at a time.
  The reference pack envelope is about `104 × 34.5 × 24.5 mm` and `174 g`.
- **1 SKYRC B6Neo balance charger**, **1 compatible 100 W USB-C PD supply**, a
  LiPo bag, low-voltage alarm, and smoke stopper are recorded. The B6Neo and
  smoke stopper were physically confirmed.
- **1 XT60-to-8×XT30 distribution board**, **1 XT90-S anti-spark lead**, about
  **4 small 5 V / 5 A UBEC modules**, **5 inline fuse holders**, a blade-fuse
  assortment, and **10 × 4700 µF / 25 V capacitors** are recorded.
- Recorded connector stock includes **10 XT30 pairs** and **5 XT60 pairs**.
- Keep the servo rail on raw 3S and the ESP32/sensors on regulated 5 V, with the
  required common ground. The simple stall bounds are `10.8 A` for one
  four-servo leg and `43.2 A` for all 16 installed servos; these are protection
  bounds, not normal running-current predictions.

## Fabrication and materials

- **1 Elegoo Neptune 4 Pro** is owned. Its usable build volume is approximately
  `225 × 225 × 265 mm`, with a direct-drive extruder suitable for TPU.
- Material records show about **3 kg PLA**, **1 kg PETG**, and **0.5 kg TPU
  95A**. PLA is for prototypes, PETG for structural parts, and TPU for tyres,
  pads, or strain relief. One PETG spool may not cover the whole robot.

## Mechanical and electrical hardware

- M2 screws in several lengths and an **M2-M10 washer assortment** are present,
  although the useful M2 machine-screw count still needs checking.
- Recorded wiring stock includes silicone wire, XT pigtails, heat shrink,
  solder, cable ties, and temporary mounting tape.
- Bench equipment includes a soldering iron, wire stripper, calipers, scales,
  and a multimeter body. The multimeter needs its battery before it can be used.
- M3 machine screws, M3 nyloc nuts, and final battery/phone straps are not yet
  confirmed. Self-tapping screws and tape are only suitable for prototypes.

## Confirm before final design

1. Count the servos, confirm every label is the 12 V C018 variant, and measure
   their mounting and output interfaces.
2. Find and fit-test the 5264 leads; record their pin order and length.
3. Measure the phone, battery, boards, sensors, plugs, and cable-bend space.
4. Verify voltage, polarity, wire gauge, fuse format, connector ratings, and USB
   data operation.
5. Count the M2 hardware and obtain the required M3 hardware and proper straps.
6. Record any bearings by type and size. No reliable bearing stock list exists,
   so the design must not assume one.
