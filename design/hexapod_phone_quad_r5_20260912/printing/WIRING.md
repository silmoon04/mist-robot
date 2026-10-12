# Wiring and commissioning boundaries

This guide accompanies the R5 inward-hip and straight-tibia revision. Its electrical arrangement is unchanged. Check actual auxiliary-face plugs and lead bends around both inward-facing servo cases and the complete 70 mm coxa. The dedicated hip cap, revised frame, straight tibia and retained pan-cap nut roofs must pass the fit and incremental fixture checks in PRINT_AND_ASSEMBLE.md before loaded commissioning. A rigid-body result does not establish printed-joint strength. Start with PRINT_FIRST.txt and the five revision-check pieces, then validate one supported leg and the dummy-phone fixture before a full run.

Use the final ±19° yaw operating limit for restricted movement checks. The checked nominal fixed-saddle gap is 1.61054 mm. The older ±22° interval fails the minimum-clearance criterion and must not be carried into commissioning. This software limit requires no geometry or wiring change.

This robot uses thirteen **Feetech ST-3215-C018 12 V TTL serial servos**: three per leg and one fixed pan servo. It does not use PWM servo outputs or an eighteen-servo MG996R wiring arrangement. No hardware was connected, commanded or reconfigured while preparing this package.

The [manufacturer C018 specification](https://cdn.robotshop.com/media/F/Fit/RB-Fit-155/pdf/feetech_12v_30kg_cm_magnetic_encoding_servo_sts321_specification_pdf.pdf) identifies 5264 three-pin connections as GND, Vcc and TTL signal, with half-duplex serial communication. Refer to the actual connector orientation and markings when checking polarity; do not infer pin order from wire colour or a mirrored drawing. Nominal operation is 12 V, with a stated 4 to 14 V input range. Rated load and stall current are different: 0.9 A rated, 2.7 A stall per servo. The [hardware contract](../references/hardware_contract.md) records the mechanical and electrical source details.

## Power arrangement

Use the owned HOOVO 3S pack through the physical disconnect and correctly selected fuse to the XT60-to-XT30 distribution board. A fully charged 3S pack is 12.6 V. Fit the pack securely in the low tray with two straps and protect its leads from the legs. Match wire, connector and fuse ratings to the actual harness; the inventory's advertised PDB rating is not a measured current capacity for the assembled cables.

Run separate positive and ground feeds from the distribution point to FL, FR, RL, RR and the pan branch. Each leg branch supplies its three servos. This avoids making the first servo cable carry the whole robot's current. All branches share signal reference ground. Route the TTL signal through the bus interface to the servo branches with short practical connections and strain relief. Verify communication quality with the real harness before enabling motion.

If branches are to be independently isolated, their positive wires must remain separate downstream of the branch fuses or disconnects. Ordinary three-wire bus extension cables between branches would reconnect their positive rails. Use an inspected signal-plus-ground link between separately powered branches, or a purpose-built distribution harness that explicitly separates positive feeds. Do not assume the bus adapter board already performs this isolation. Preserve adequate ground return paths; do not use the signal-reference lead as a motor-current return.

Power the ESP32 and logic from the separate, measured 5 V UBEC output. Connect its ground to the servo bus reference ground. Use the owned Bus Servo Adapter A between the ESP32 UART and the half-duplex TTL servo bus. Inspect the exact board's labels, supply selection and voltage-level circuit before choosing pins or plugging cables in. **Never connect raw 3S voltage to an ESP32 5 V or 3.3 V input.** Do not attach a powered USB host and a UBEC output together without checking the board's backfeed protection or separating the supplies.

The owned FE-URT-1 is available for individual servo identification and setup, but its USB and servo-power behavior must be checked against the delivered board. Capacitors, fuses and disconnect hardware are available in inventory; values, polarity, branch topology and placement still need a physical harness review. The model's PDB, UBEC, ESP32 and bus-interface trays use nominal envelopes and ties. Measure board dimensions, underside components and connector extraction room before fastening them down.

## IDs and direction records

Assign unique servo IDs only through a deliberate individual-servo commissioning procedure. The following is a **proposed new map**, not a description of the existing bench configuration. It does not authorize overwriting saved calibration or old firmware settings. If the new firmware exports a different explicit map, reconcile these records before commissioning.

| Position | Proposed yaw / hip / knee IDs |
|---|---|
| Front left | 1 / 2 / 3 |
| Front right | 4 / 5 / 6 |
| Rear left | 7 / 8 / 9 |
| Rear right | 10 / 11 / 12 |
| Phone pan | 13 |

Record delivered servo identity, ID, neutral count, mounting orientation, direction sign and software limits separately for every joint. A mirrored leg does not imply that the same raw servo position produces the same physical motion. Check each direction with the robot supported and one joint at a time, using the new controller's restricted commissioning mode. The current model's joint ranges are provisional geometric ranges; they are not automatically safe raw servo limits.

Before any powered movement, confirm polarity with a meter, regulated logic voltage, accessible disconnect, no exposed conductors and readable feedback from the intended servo IDs. Keep torque off while checking identification. The full robot has not undergone a physical electrical, thermal, balance or gait test, so all loaded commissioning starts with external support and an immediate way to remove servo power. Do not choose operating current from the sum of stall ratings alone.

## Phone and existing brain interface

Use the Mi9SE battery and Wi-Fi for the existing brain web interface while the pan axis moves. Mount the phone in landscape orientation with the screen upright, 147.5 mm across and 70.5 mm high. Its USB-equipped short edge faces the cradle's side opening. The phone cradle is a mechanical holder; this package does not establish a real phone connection, camera stream or successful session in the brain application. Open the existing web interface through its normal configuration and confirm its actual host address and camera permissions separately.

The pan servo case and its power lead remain fixed to the chassis, so the rotating cradle need not twist a servo lead. A USB cable plugged into the phone would twist, however. Park and disable pan before attaching USB charging through the side opening; the USB exit is beside the phone's short edge, not beneath the cradle. Keep USB disconnected during unrestricted pan; a local angle setting cannot substitute for proving the cable's free sweep. No slip ring is included.

Mount the phone only after the empty cradle sweeps freely and the base is stable. Check that rear-camera views remain clear at all pan angles. Record the real phone case, camera bump, USB overmould and nearby board measurements in `coupon_feedback.csv` before treating their clearances as resolved.
