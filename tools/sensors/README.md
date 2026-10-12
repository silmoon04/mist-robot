# Phone → robot sensor streaming (Mi 9 SE) — ✅ WORKING

Live IMU + magnetometer (+GPS) from the Mi 9 SE via **SensorServer**, a WebSocket
server that runs *on the phone*. Verified streaming 2026-06-30 (148 msgs / 6 s).

## App
**SensorServer v7.2.1** — `github.umer0586.sensorserver` (open-source, GPL-3.0).
APK: https://github.com/UmerCodez/SensorServer/releases  (sideload via `adb install`)

### One-time phone setup
1. **MIUI unlock for ADB:** Developer Options → enable **"Install via USB"** *and*
   **"USB debugging (Security settings)"**. These need a **SIM + Mi account signed in**.
   Without them MIUI blocks `adb install` *and* `adb shell input tap`.
2. In SensorServer → ☰ → **Settings** → turn **ON "Listen on 0.0.0.0"**
   (binds all interfaces: `127.0.0.1` for the USB tunnel **and** the WiFi IP for the robot).
   WebSocket port = **8080**.
3. Main screen → tap **START**.

## Path A — read from the PC over USB (no WiFi, no firewall)
```
adb forward tcp:8080 tcp:8080
pip install websocket-client
python tools/sensors/sensor_ws_reader.py          # from repo root; connects to ws://127.0.0.1:8080
```

## Path B — read from the robot (ESP32) over WiFi
"Listen on 0.0.0.0" also serves the phone's WiFi IP. Put the ESP32 + phone on the
same 2.4 GHz WiFi, then connect to `ws://<phone-wifi-ip>:8080/...`.
(ESP32 WebSocket-client sketch: TODO — ask and I'll add `esp32_sensor_ws.ino`.)

## WebSocket API
- Multi-sensor: `ws://HOST:8080/sensors/connect?types=["android.sensor.accelerometer","android.sensor.gyroscope","android.sensor.magnetic_field"]`
- Each message (JSON): `{"type":"android.sensor.X","values":[x,y,z],"accuracy":n,"timestamp":<ns>}`
- Single sensor: `/sensor/connect?type=android.sensor.accelerometer`
- GPS: separate endpoint `/gps`

## Verified reading (phone flat on desk, stationary)
```
ACC ≈ [-0.85, 0.48, 9.83] m/s²   (Z≈g  → screen up, not moving)
GYR ≈ [ 0.00, 0.00, 0.00] rad/s  (not rotating)
MAG ≈ [ 143, -66, -18 ] µT       (magnetic field / heading)
```
