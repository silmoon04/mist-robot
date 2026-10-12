# Single-leg calibration and inverse kinematics

This procedure is for the assembled three-servo test leg shown in the August 25 photos. The software model uses the dimensions already established in the Fusion design:

| Item | Test value |
|---|---:|
| Hip-roll to hip-pitch offset, `d1` | 32 mm |
| Femur pivot spacing | 110 mm |
| Tibia pivot spacing | 70 mm |
| Driver / follower | 40 / 40 mm |
| Coupler / femur | 110 / 110 mm |
| Remote-knee transmission | Exact 1:1 parallelogram |
| Hip-roll servo ID | 1 |
| Hip-pitch servo ID | 2 |
| Remote-knee driver servo ID | 3 |
| Servo resolution | 4096 ticks per revolution |

Start the bench server:

```powershell
cd 
python bench\servo_bench.py
```

Open [http://localhost:8124/leg.html](http://localhost:8124/leg.html). Use the main [Servo Bench](http://localhost:8124/) page to connect the FE-URT-2 and scan the bus.

## If the scan shows only ID 1

New servos normally share the same factory ID. Several servos answering as ID 1 collide electrically: a ping may occasionally work while position, voltage and temperature reads fail. Do not change the ID while all three are connected, because every servo using ID 1 may accept the same write.

1. Power off the servo rail before changing any plugs.
2. Connect only the hip-roll servo. Leave it as ID 1 and confirm that position and voltage are readable.
3. Power off, connect only the hip-pitch servo, scan for ID 1, and change it to ID 2. Power-cycle and confirm that only ID 2 answers.
4. Power off, connect only the remote-knee servo, scan for ID 1, and change it to ID 3. Power-cycle and confirm that only ID 3 answers.
5. Power off, reconnect all three, then scan again. The required result is exactly IDs 1, 2 and 3 with valid telemetry from each.

If one physically isolated servo only pings intermittently or still has unreadable registers, the problem is not duplicate IDs. Check connector orientation, common ground, battery rail voltage at the servo connector, baud rate, and the FE-URT signal wiring before writing EEPROM.

## What the photos show

The linkage layout is kinematically plausible for a no-load test. The upper and lower long links form the intended parallelogram, the bearings are seated, and the remote knee driver is coupled to the tibia side of the mechanism.

The `q2 + q3` equation is exact only if the printed mechanism is an actual parallelogram. Verify these four items with calipers before trusting coordinated motion:

- The knee-driver servo axis and hip-pitch servo axis are coaxial.
- Driver and distal follower have the same centre-to-centre length.
- Upper coupler and femur have the same centre-to-centre length.
- All four pivot axes are parallel, with spacers keeping the links in parallel planes.

If either pair differs, the driver-to-tibia relation varies through the stroke. The current calculator must then be replaced by a general four-bar closure solve using the measured pivot coordinates. Do not hide that mismatch in a servo centre offset.

It is not ready for a loaded powered test yet:

- The servo retention visible in the photos is still a prototype arrangement. Clamp or bolt each servo case so reaction torque cannot peel tape or flex a thin wall.
- Clamp the hip-roll fixture to a rigid base. Do not hold the assembly in one hand while enabling torque.
- Use metal pins, shoulder screws, or bolts through every powered pivot. Printed axle adapters are suitable for fit checks, not powered load tests.
- Check that every bearing inner race is clamped and every outer race is retained without crushing it. A pivot should rotate through its range without the bearing walking sideways.
- Add washers or printed spacers wherever two link faces can rub. The link planes must remain parallel through the full motion.
- Add strain relief before repeated movement. The loose servo leads can enter the linkage or pull directly on their connectors.
- Inspect the hammered bearing seats for white stress marks or radial cracks. Replace any cracked hub before applying torque.

The 11.78 V pack reading is suitable for this bench test if it is a healthy 3S LiPo. It is about 3.93 V per cell when balanced, so it does not need charging just to calibrate. Verify the three individual cell voltages through the balance connector and use a 3S balance charger. Stop if any cell differs materially from the others, the pack is swollen, or the voltage drops sharply under a small load.

## Why the knee equation is different

The software joint angle `q3` is the tibia angle relative to the femur. Your 1:1 remote linkage makes its servo driver follow the tibia's absolute pitch instead. The physical servo targets are therefore:

```text
roll servo        = q1
hip servo         = q2
knee-driver servo = q2 + q3
```

For example, `q2 = +30°` and `q3 = -55°` require the remote-knee servo to move to `-25°`, not `-55°`. This correction is implemented in `leg_kinematics.py` and is covered by an automated round-trip test.

## Calibration order

1. Remove the foot load and clamp the hip fixture to the bench.
2. Measure the four conditions above and resolve any mismatch or binding. Connect only the control hardware needed for this leg. Confirm IDs 1, 2 and 3 on the Servo Bench page.
3. Press **Torque OFF ALL**. Move every joint by hand and resolve any binding first.
4. Put the mechanism in the printed Fusion reference pose: roll centred, femur horizontal and outward, tibia vertical down, driver and follower vertical up, and coupler parallel to the femur. The logical angles are `q1 = 0°`, `q2 = +90°`, `q3 = -90°`; the knee-driver servo angle is therefore `0°`. If the horns cannot reach that pose, remove them, centre the servos electrically, and reinstall the horns in this reference arrangement.
5. On the leg page, run **Check IDs, rail and torque state**. All three roles must answer, the rail must be 9.0-12.6 V, and torque must be off.
6. Press **Capture printed-reference ticks**. The hip reference is +90°, while roll and knee-driver references are 0°; the stored conversion accounts for those different reference angles.
7. Find each direction one servo at a time. On the Servo Bench page, command only a 16-32 tick step at low speed, observe the direction, return to neutral, and set the sign on the leg page.
8. With torque off, move one role to either physical safe end and capture **Endpoint A**. Move it to the other safe end and capture **Endpoint B**. Do not guess which direction is raw lower: the page sorts the two tick values into numeric minimum and maximum automatically.
9. Calibrate hip roll independently. For hip pitch, keep the knee near the printed-reference bend while moving the whole parallelogram through the intended hip range. For the knee driver, hold the femur near the printed-reference orientation and move the relative linkage input only through its guarded range. Stop before contact and leave margin for printed-part flex.
10. Repeat the endpoint capture for all three roles. Calibration is complete only when all reference ticks, signs and both physical endpoints are present.
11. Use **Start live hardware pose** while moving the torque-off leg by hand. The displayed angles and tip position should move in the same direction as the mechanism.
12. Drag the target ring inside the complete side view. This performs dry-run IK only. A usable result must say `REACHABLE`, show the coupled linkage check as `PASS`, pass every calibrated raw range, and have a very small forward-kinematics check error.

Do not begin with a walking trajectory. The first powered sequence should be one servo at a time, about 16 ticks per step, low speed, with a current limit and a hand on **TORQUE OFF ALL**. Coordinated motion can be added after the signs and linkage equation are confirmed physically.

## Guarded drag motion

The side-view target remains simulation-only until **Guarded physical drag motion** is explicitly armed. Before arming, clamp the yaw base, install metal pivot pins, unload the foot, route the wires outside the swept linkage and clear hands from the mechanism.

1. Tick the physical-safety confirmation and press **Arm drag motion**. The server verifies IDs, mode 0, rail, temperature, current, calibration, raw limits and the coupled linkage pose.
2. The server preloads the current positions with one Feetech SyncWrite packet, applies a temporary 30% torque limit and only then enables torque. Arming holds the measured pose; it does not jump to the cursor.
3. Press and hold inside the side view, then drag. The server independently recomputes IK and refuses any raw or coupled limit failure.
4. Scroll up over the diagram for positive yaw and down for negative yaw. A normal wheel notch changes yaw by about 5 degrees; trackpad deltas scale smoothly. Side-view dragging preserves the yaw angle instead of changing it indirectly through Y/Z.
5. Release the pointer to hold the last valid pose. Wheel yaw remains active while armed and holding. Drag again to continue, then use **Disarm / torque off** when finished. **TORQUE OFF ALL** remains the immediate stop.

The controller sends synchronized 7-byte STS position blocks at 30 Hz. Select the speed before arming: 10% is about 34 degrees per second, the 70% default is about 116 degrees per second, and 100% is about 158 degrees per second. The server maps the same setting to servo speed 190-1000 and acceleration 4-20. It still trips above 800 mA, 50 C or the configured rail range. Browser heartbeat loss for 750 ms, page hide, focus loss, telemetry timeout, communication error or the 60-second maximum arm window also torques the leg off. These are commissioning limits, not validated weight-bearing operating limits.

Dragging outside the calibrated workspace does not disarm the leg. The cursor is projected to the nearest sampled pose satisfying yaw, hip, knee-driver raw limits and the coupled q3 range. The pale dashed cursor marker may continue outside while the amber commanded target stays clamped to the translucent green Cartesian envelope. Low-opacity joint arcs show calibrated angular ROM; dashed blue and amber paths show the current foot-position span from hip-only and knee-only motion.

## Coordinates used by the calculator

- `+X` points away from the body through the hip mount.
- `+Y` is lateral.
- `+Z` points up. A foot below the hip therefore has a negative Z value.
- `q1` is hip roll.
- `q2 = 0` puts the femur straight down; positive `q2` moves it outward in `+X`. The printed assembly reference uses `q2 = +90°`, so its femur is horizontal.
- `q3 = 0` aligns the tibia with the femur. The normal spider branch uses negative `q3`.

At the printed reference, the 40 mm driver is **not parallel to the femur**. Driver and follower point up and remain parallel to each other. Coupler and femur point outward and remain parallel to each other. The tibia points down, collinear but opposite to the follower. That fixed 180° follower-to-tibia offset is included in the linkage drawing; it does not change the incremental servo equation `knee driver = q2 + q3`.

The no-wheel ankle/tibia-tip workspace has a planar radius from 40 mm to 180 mm around the hip-pitch axis. The calculator refuses unreachable targets instead of clipping them, and it reports out-of-limit servo ticks instead of silently clamping them.

Independent servo ranges are necessary but not sufficient for this four-bar. The Fusion build cleared relative input from `-30°` to `+40°` around the printed reference. The first PLA commissioning range keeps 5° away from both CAD edges, so the page enforces `-25°` to `+35°`. Since the reference has `q3 = -90°`, that corresponds to `q3 = -115°` to `-55°`. The page checks this on every IK target and every calibrated live pose. A target that passes all three raw ranges can still be rejected by this coupled check.

## Files

- `leg_kinematics.py`: forward kinematics, inverse kinematics, servo mapping and tick conversion.
- `leg_calibration.py`: validation and atomic calibration storage.
- `leg_calibration.json`: created locally after the first successful capture.
- `leg.html`: calibration, hardware-check, live-pose and IK interface.
- `test_leg_kinematics.py`: numerical and mapping tests.
- `test_leg_calibration.py`: persistence and validation tests.
