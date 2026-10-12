# R7 remote and ESP32 commissioning bridge

Run the remote from the repository root:

```sh
python -m locomotion.hardware.bridge
```

Open `http://127.0.0.1:8130`. The default remote previews 12 joint targets, six crawl commands and local leg inverse kinematics. It opens no motor connection. The pose drawing shows each leg's pitch plane; use the simulation remote for 3D contact and balance. `q` always means 12 radians in FL, FR, RL, RR order, each with yaw, hip, knee. The crawl command is `[vx_m_s, vy_m_s, yaw_rad_s]`.

The current robot has three direct-drive joints per leg. `bench/leg_calibration.json` records the older 32/110/70 mm four-bar test mechanism, whose remote knee follows `q2 + q3`. Those ticks, signs, IDs and equations do not calibrate R7. R7 uses 82/90/105 mm geometry, yaw about +Z and both pitch joints about +Y. Zero pitch points outward along local +X; positive pitch moves toward -Z. Its CAD bounds are yaw -55..55°, hip -30..65°, knee 5..115°. Printed contact, cable travel and load limits still need measurement.

## Hardware profile

The shipped firmware has `PROFILE_CONFIGURED=false`; it refuses arming and writes no bus commands. Every calibration field in `calibration.example.json` is unset. Before creating a hardware profile, restrain the robot, remove foot load, identify one servo at a time, then measure every R7 reference angle, corresponding tick, direction and safe end with margin. Keep the full range within one non-wrapping 0..4095 revolution. A raw centre tick is associated with `reference_rad`, which does not have to be zero. Horn reinstallations require recalibration.

Copy the example to `calibration.local.json`, fill all 12 records and confirm `measured`, `verified_on_robot` and `estop_nc_verified` only after those checks. The stock bridge deliberately has no ID-writing or EEPROM feature. Assign IDs separately through the existing bench tool with only one unconfigured servo connected.

```sh
python -m locomotion.hardware.bridge --calibration locomotion/hardware/calibration.local.json \
  --write-header locomotion/hardware/esp32/include/calibration_profile.h
python -m pip install platformio pyserial==3.5
cd locomotion/hardware/esp32
pio run
```

The profile generator embeds the canonical JSON SHA256 in the firmware. The host refuses a different firmware hash. `pio run` builds without uploading. No firmware was flashed and no physical motor command was sent during development. After a separately controlled board bring-up, the host command is:

```sh
python -m locomotion.hardware.bridge --calibration locomotion/hardware/calibration.local.json \
  --serial /dev/ttyUSB0
```

The serial port belongs to the ESP32 USB bridge. It is not the FE-URT adapter or the Waveshare adapter's direct USB connection. Replace the sample device name with the actual ESP32 port. Hardware arming also requires the remote's unloaded-fixture confirmation. It reads the 12 actual positions, preloads those targets and enables torque at that pose. The host never jumps to a generic neutral on arm.

## Wiring

The recorded parts are an ESP32 WROOM-32 board, Waveshare Bus Servo Adapter A, C018 servos, raw 3S LiPo, a 5 V UBEC and a power distribution board. Older inventory totals of 16 installed motors refer to the earlier wheel concept. Current R7 legs need 12 motors; a phone pan adds one.

| Connection | Wiring |
| --- | --- |
| ESP32 UART2 RX | GPIO16 to Adapter A header RX |
| ESP32 UART2 TX | GPIO17 to Adapter A header TX |
| Signal reference | ESP32 GND to adapter GND and servo power ground |
| Adapter mode | Jumper A for MCU UART; B is its separate USB mode |
| Servo bus | Feetech 5264 three-pin leads, GND/Vcc/TTL; verify the actual connector orientation |
| ESP32 power | Verified regulated 5 V to board 5V/GND, or USB power during bring-up |
| Stop input | GPIO27 with pull-up, normally closed stop contact to GND; opening the loop trips |
| Owned MPU6050 | SDA to GPIO21, SCL to GPIO22, common GND, verified 3.3 V compatible supply and pull-ups |

Adapter A unusually names its UART header from the host perspective, so [Waveshare's wiring instructions](https://docs.waveshare.com/Bus_Servo_Adapter_A/Product-Wiring-Example) specify RX-RX and TX-TX. Check the exact board markings before connecting. GPIO16/17 are usable on WROOM boards; some WROVER boards reserve them for PSRAM. Verify the owned clone and pin count against [Espressif's board guide](https://docs.espressif.com/projects/esp-idf/en/v5.0.3/esp32/hw-reference/esp32/get-started-devkitc.html). Select one ESP32 supply source; avoid simultaneous external 5 V and USB 5 V unless properly isolated.

The [Adapter A FAQ](https://docs.waveshare.com/Bus_Servo_Adapter_A/FAQ) specifies 5 A maximum and no voltage regulator. Distribute servo V+ externally through appropriately sized, protected branches; do not pass the complete robot's servo current through this adapter or the ESP32. Where V+ is supplied by a separate branch, isolate unintended positive-rail paths in the bus harness while preserving common signal ground and TTL continuity. Inspect that harness before power is applied. Wire the stop contact to GPIO27 and use an independent means to interrupt servo power. A software torque-off packet cannot stop a disconnected or damaged bus.

## Controller behaviour

The ESP32 receives newline-delimited JSON at 460800 baud over USB and controls the servo bus at 1 Mbps. It uses the official [Feetech Arduino library](https://github.com/ftservo/FTServo_Arduino), pinned to `64922cda46e56b21b8c1d9e830d936a1941645ae`. Its STS interface supplies synchronized position writes and a 56..70 register block for position, speed, load, voltage, temperature and raw current. Library errors and servo status bits are checked.

Commands use increasing sequence IDs. Stale frames, unsafe telemetry, invalid targets, opened stop loop, missing heartbeat and expired commissioning window latch a fault and send broadcast torque off. The host stops if the browser heartbeat is absent for 300 ms. The ESP32 independently uses the same 300 ms watchdog and a 60 second arm window. Targets are bounded by calibrated ticks and 0.5 rad/s with a two-tick rounding allowance. The heartbeat holds the last valid target; it does not manufacture new gait commands. Page blur, hide and close request a stop.

Commissioning guards are 20% torque limit, 50°C trip, 9.0..12.6 V rail, and raw current magnitude at most 120. Servo speed and acceleration are fixed to conservative raw values 200 and 4. These are selected commissioning settings. Raw current stays labelled as raw because its scale has not been confirmed on the owned C018 units. Compare its readings with a current measurement before selecting a deployed limit. Broadcast writes have no per-motor acknowledgement; telemetry does not prove a broken servo obeyed torque-off.

The [manufacturer C018 specification](https://cdn.robotshop.com/media/F/Fit/RB-Fit-155/pdf/feetech_12v_30kg_cm_magnetic_encoding_servo_sts321_specification_pdf.pdf) gives 12 V nominal, 4..14 V operating range, 0.981 N·m rated torque at 0.9 A, 2.942 N·m stall at 2.7 A, 55±1 g mass, 12-bit position feedback and at most 0.5° backlash. Its cyclic-life load is one-fifth stall, about 0.588 N·m. Neither stall nor this selected initial load proves unlimited continuous thermal operation. R7's old 0.8 N·m and 0.5 rad/s URDF values were analysis bounds. Measure voltage-dependent speed, tracking, delay, backlash and thermal behaviour before replacing the simulation actuator assumptions.

## Sensors and learned-policy deployment

The user confirmed the owned MPU6050 and Mi 9 SE. The fixed MPU can provide chassis sensing with the phone absent; the phone can be used alone or as an additional stream. `esp32dev` leaves MPU I2C disabled. `pio run -e esp32dev_mpu6050` builds the optional driver on GPIO21/22. It checks WHO_AM_I at 0x68 or 0x69, configures ±2 g and ±250°/s ranges and emits sensor-frame acceleration in m/s² and angular rate in rad/s at up to 50 Hz. Readout follows the [TDK register map](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Register-Map1.pdf). Its 16384 LSB/g and 131 LSB/(°/s) conversions match those configured ranges. Check the actual breakout supply and pull-up voltages before connecting; the ESP32 signal pins require 3.3 V compatible levels.

`sensors.py` converts either source to the policy's first six values: `gravity_body` is a unit vector pointing down, and `gyro_body` is chassis angular rate in rad/s. MPU gravity uses gyro integration with accelerometer correction only when measured acceleration stays near gravity. This estimator has no absolute yaw measurement. Measure stationary gyro bias and each sensor-to-body rotation, then fill `sensor_mount.local.json` from the example. The loader refuses its unverified identity defaults.

Android accelerometer and gravity readings at rest point opposite the policy's down vector. The phone adapter reverses and normalizes that vector, maps gyro through the same measured mounting rotation and rejects stale or out-of-order samples. Android's sensor axes remain tied to the device's natural orientation when the screen content rotates, as described in the [Android sensor guide](https://developer.android.com/develop/sensors-and-location/sensors/sensors_overview). Rotating screen UI cannot calibrate the mount. For a moving pan, call `PhoneIMU.set_pan(angle_rad, rate_rad_s)` with fresh measured pan state; the adapter rotates the sensor frame and subtracts pan angular rate about body +Z. The pan-zero mounting transform must include the actual upright landscape phone orientation.

The repository already records native SensorServer on the phone. Use that path without a browser permission or HTTPS dependency:

```sh
python -m pip install websocket-client==1.9.0 pyserial==3.5
adb forward tcp:8080 tcp:8080
python -m locomotion.hardware.sensors --source phone \
  --mount locomotion/hardware/sensor_mount.local.json
```

Enable SensorServer and select the recorded gyro/accelerometer streams. If its gravity sensor is available, include `android.sensor.gravity` in the `--url` query. Direct Wi-Fi can use the phone's private address instead of the USB tunnel; measure transport delay and keep phone pan locked for the CLI monitor. For the optional ESP32 MPU profile:

```sh
python -m locomotion.hardware.sensors --source mpu6050 --serial /dev/ttyUSB0 \
  --mount locomotion/hardware/sensor_mount.local.json
```

These monitors issue no motor commands. Use only one reader per ESP32 USB port. `SerialLink.imu_packet` also exposes the latest raw MPU frame to a combined host application. Source selection supports `mpu6050`, `phone`, `auto` and `none`; `auto` prefers a fresh fixed MPU, then phone. `none` refuses to fabricate policy observations. Both sources reject arrival age over 100 ms. Arrival freshness does not establish end-to-end latency because the phone and laptop clocks have not been synchronized. A source change during deployed control needs a validated transition; the monitor's fallback is not a tested control failover.

The `gait` endpoint refuses physical execution. A real learned policy still needs fresh chassis measurements, synchronized joint state, the training observation order and normalization, bounded inference time and a measured actuator model. The sensor driver and replay tests do not establish physical mounting, bias, vibration behaviour or latency. Finish supported stance/load commissioning before implementing that host runner. Use servo current and load as imperfect contact hints only after measuring their behaviour. A distance sensor is not a foot contact sensor.

The protocol operations are `status`, `arm`, `heartbeat`, `ticks`, `disarm`, `estop` and `clear`; only the host accepts radians, gait and IK. Only `arm` accepts a profile hash. The firmware `ticks` command carries 12 raw positions and never changes servo IDs or mode. `status` returns the profile hash, last sequence, fault, stop state and raw telemetry. Browser requests also need a per-session token and the server binds only to loopback.

## Checks

```sh
python -m unittest locomotion.hardware.test_bridge locomotion.hardware.test_sensors -v
cd locomotion/hardware/esp32
pio run -e esp32dev -e esp32dev_mpu6050
```

Tests cover incompatible calibration rejection, reference/sign conversions, duplicate IDs, tick and CAD limits, finite inputs, timeout faults, held-pose arming, physical gait refusal and direct R7 IK. Sensor replay tests cover frame rotations, gravity sign, gyro bias, missing streams, timestamps, pan compensation and source selection. Both firmware profiles built successfully with the real library API and ESP32 toolchain. These checks do not verify wiring, actual motor responses, watchdog timing on the board, printed load capacity or real walking.

Arm and clear requests must include the latest `intent_generation` from status. Disarm, STOP and watchdog trips invalidate previous arm requests, including requests pending when a page closes. Duplicate arms are rejected. Firmware also checks its own arm generation. Host and firmware each spend cumulative per-joint slew credit at 0.5 rad/s, with one initial two-tick quantization allowance; packets do not renew that allowance. Dry-run gait targets use the same position feedforward controller and nominal phone mass as simulation.

The bridge still does not assemble the 47-value actor observation or execute a learned policy through calibrated joints. It owns serial access and exposes commissioning/raw sensor telemetry. Do not run a second serial monitor on the same port. Deployment still needs fresh joint telemetry, shared observation construction, phase/residual handling, sensor stop behavior, verified geometry/calibration and restrained loaded tests. No software test substitutes for those measurements.
