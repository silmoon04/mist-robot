"""Convert measured MPU6050 or Android frames to the policy's chassis observations."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

import numpy as np

G = 9.80665


class SensorError(ValueError):
    pass


def vector(value, name):
    if not isinstance(value, (tuple, list, np.ndarray)) or len(value) != 3 or any(isinstance(x, (bool, np.bool_)) for x in value):
        raise SensorError(f"{name} requires three finite numbers")
    out = np.asarray(value, dtype=float)
    if out.shape != (3,) or not np.isfinite(out).all():
        raise SensorError(f"{name} requires three finite numbers")
    return out


def rotation(value):
    result = np.asarray(value, dtype=float)
    if result.shape != (3, 3) or not np.isfinite(result).all() or not np.allclose(result.T @ result, np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(result), 1.0, atol=1e-6):
        raise SensorError("mount R must be a proper 3x3 rotation mapping sensor axes to body axes")
    return result


def rz(angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])


class GravityEstimator:
    """Gyro integration with gated accelerometer correction; no magnetometer or yaw claim."""
    def __init__(self, correction_tau_s=0.5):
        self.gravity = None
        self.at = None
        self.tau = correction_tau_s

    def reset(self):
        self.gravity = self.at = None

    def update(self, stamp_s, accel_m_s2, gyro_rad_s):
        accel, gyro = vector(accel_m_s2, "accel"), vector(gyro_rad_s, "gyro")
        if not math.isfinite(stamp_s):
            raise SensorError("invalid sensor timestamp")
        norm = np.linalg.norm(accel)
        trust = .8 * G <= norm <= 1.2 * G
        if self.gravity is None:
            if not trust:
                raise SensorError("initial gravity needs a near-stationary accelerometer sample")
            self.gravity, self.at = -accel / norm, stamp_s
            return self.gravity.copy()
        dt = stamp_s - self.at
        if dt > .1:
            self.reset()
            raise SensorError("sensor gap; estimator reset, next stationary sample may recover observations only")
        if dt <= 0:
            raise SensorError("sensor timestamp repeated, out of order or gap exceeds 100 ms; reset estimator")
        angle = np.linalg.norm(gyro) * dt
        if angle > 0:
            axis = -gyro / np.linalg.norm(gyro)
            k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
            self.gravity = (np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)) @ self.gravity
        if trust:
            gain = dt / (self.tau + dt)
            self.gravity = (1 - gain) * self.gravity + gain * (-accel / norm)
        self.gravity /= np.linalg.norm(self.gravity)
        self.at = stamp_s
        return self.gravity.copy()


class BodyIMU:
    def __init__(self, mount, gyro_bias_rad_s=(0, 0, 0), max_age_s=.1):
        self.mount = rotation(mount)
        self.bias = vector(gyro_bias_rad_s, "gyro bias")
        self.max_age = max_age_s
        self.estimator = GravityEstimator()
        self.latest = None
        self.arrived = None
        self.clock_offset = None

    def reset(self):
        self.estimator.reset()
        self.latest=self.arrived=self.clock_offset=None

    def ingest(self, packet, received_at=None):
        if not isinstance(packet, dict):
            raise SensorError("MPU packet must be a JSON object")
        if packet.get("kind") != "imu" or packet.get("source") != "mpu6050" or packet.get("valid") is not True:
            raise SensorError("valid MPU6050 packet required")
        gyro_sensor = vector(packet.get("gyro_rad_s"), "gyro") - self.bias
        accel_sensor = vector(packet.get("accel_m_s2"), "accel")
        stamp = packet.get("t_ms")
        if type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp < 0:
            raise SensorError("invalid MPU timestamp")
        arrival = time.monotonic() if received_at is None else received_at
        # A reset is deliberate after a receive gap; duplicates within a live stream fail.
        if self.arrived is not None and arrival-self.arrived > self.max_age:
            self.estimator.reset()
            self.clock_offset=None
        try:
            gravity = self.estimator.update(stamp / 1000.0, accel_sensor, gyro_sensor)
        except SensorError:
            self.latest=None
            raise
        offset=arrival-stamp/1000.0
        self.clock_offset=offset if self.clock_offset is None else min(self.clock_offset,offset)
        self.latest = {"gravity_body": (self.mount @ gravity).tolist(),
                       "gyro_body": (self.mount @ gyro_sensor).tolist(), "source": "mpu6050", "measurement_time_s":stamp/1000., "arrival_time_s":arrival, "frame":"body", "units":"unit down vector; rad/s", "valid":True}
        self.arrived = time.monotonic() if received_at is None else received_at
        return self.latest

    def observation(self, now=None):
        now = time.monotonic() if now is None else now
        if self.latest is None or not 0 <= now - (self.latest["measurement_time_s"]+self.clock_offset) <= self.max_age:
            raise SensorError("MPU6050 observation missing or stale")
        return dict(self.latest, sample_age_s=now-(self.latest["measurement_time_s"]+self.clock_offset))


class PhoneIMU:
    """Android SensorServer input; mount at pan zero is measured independently of screen orientation."""
    def __init__(self, mount_at_pan_zero, gyro_bias_rad_s=(0, 0, 0), pan_locked=True, max_age_s=.1):
        self.mount = rotation(mount_at_pan_zero)
        self.bias = vector(gyro_bias_rad_s, "gyro bias")
        self.pan_locked, self.max_age = bool(pan_locked), max_age_s
        self.pan = None
        self.samples = {}
        self.estimator = GravityEstimator()
        self.last_estimated_stamp = None
        self.clock_offset=None

    def reset(self):
        self.clock_offset=None
        self.samples.clear()
        self.estimator.reset()
        self.last_estimated_stamp=None

    def set_pan(self, angle_rad, rate_rad_s, received_at=None):
        if not all(type(x) in (int, float) and math.isfinite(x) for x in (angle_rad, rate_rad_s)):
            raise SensorError("pan angle and rate must be finite measured radians")
        self.pan = (angle_rad, rate_rad_s, time.monotonic() if received_at is None else received_at)

    def ingest(self, packet, received_at=None):
        if not isinstance(packet, dict):
            raise SensorError("Android packet must be a JSON object")
        kind = packet.get("type")
        if kind not in ("android.sensor.gravity", "android.sensor.gyroscope", "android.sensor.accelerometer"):
            raise SensorError("unsupported Android sensor type")
        values = vector(packet.get("values"), "Android values")
        stamp = packet.get("timestamp")
        if type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp <= 0:
            raise SensorError("Android sensor timestamp must be monotonic nanoseconds")
        if kind in self.samples and stamp <= self.samples[kind][1]:
            raise SensorError("Android sensor timestamp repeated or out of order")
        arrival=time.monotonic() if received_at is None else received_at
        offset=arrival-stamp/1e9
        self.clock_offset=offset if self.clock_offset is None else min(self.clock_offset,offset)
        self.samples[kind] = (values, stamp, arrival)

    def _fresh(self, kind, now):
        sample = self.samples.get(kind)
        if sample is None or not 0 <= now - (sample[1]/1e9+self.clock_offset) <= self.max_age:
            raise SensorError(f"{kind} missing or stale")
        return sample

    def observation(self, now=None):
        now = time.monotonic() if now is None else now
        gyro, stamp, _ = self._fresh("android.sensor.gyroscope", now)
        gyro = gyro - self.bias
        sample = self.samples.get("android.sensor.gravity")
        if sample and 0 <= now - (sample[1]/1e9+self.clock_offset) <= self.max_age:
            if abs(stamp - sample[1]) > min(.02,self.max_age) * 1e9:
                raise SensorError("phone gravity and gyro sensor timestamps differ excessively")
            norm = np.linalg.norm(sample[0])
            if not .8 * G <= norm <= 1.2 * G:
                raise SensorError("phone gravity magnitude is implausible")
            gravity = -sample[0] / norm
        else:
            accel, accel_stamp, _ = self._fresh("android.sensor.accelerometer", now)
            if abs(stamp - accel_stamp) > min(.02,self.max_age) * 1e9:
                raise SensorError("phone accel and gyro timestamps differ excessively")
            if self.last_estimated_stamp != stamp:
                self.estimator.update(stamp / 1e9, accel, gyro)
                self.last_estimated_stamp = stamp
            gravity = self.estimator.gravity
        pan_angle = pan_rate = 0.
        if not self.pan_locked:
            raise SensorError("moving-pan observations require timestamp-aligned mount measurements; locked pan only")
            if self.pan is None or not 0 <= now - self.pan[2] <= self.max_age:
                raise SensorError("moving phone mount requires fresh measured pan angle and rate")
            pan_angle, pan_rate, _ = self.pan
        transform = rz(pan_angle) @ self.mount
        return {"gravity_body": (transform @ gravity).tolist(),
                "gyro_body": ((transform @ gyro) - [0., 0., pan_rate]).tolist(), "source": "phone", "frame":"body", "units":"unit down vector; rad/s", "valid":True, "measurement_time_s":stamp/1e9, "sample_age_s":now-(stamp/1e9+self.clock_offset)}


def select_observation(source, mpu=None, phone=None, now=None):
    if source == "mpu6050" and mpu is not None:
        return mpu.observation(now)
    if source == "phone" and phone is not None:
        return phone.observation(now)
    if source == "auto":
        for sensor in (mpu, phone):
            if sensor is not None:
                try:
                    return sensor.observation(now)
                except SensorError:
                    pass
        raise SensorError("no fresh configured MPU6050 or phone stream")
    raise SensorError("no sensor selected; learned-policy body observations are unavailable")


def load_mount(path):
    data = json.loads(Path(path).read_text())
    if data.get("verified_on_robot") is not True:
        raise SensorError("mount rotations and gyro bias must be measured on the robot first")
    for name in ("mpu6050", "phone"):
        rotation(data[name]["R_body_from_sensor_at_pan_zero"])
        vector(data[name]["gyro_bias_rad_s"], "gyro bias")
    return data


def main():
    parser = argparse.ArgumentParser(description="Read sensor observations without issuing any motor command")
    parser.add_argument("--source", choices=("phone", "mpu6050"), required=True)
    parser.add_argument("--mount", required=True)
    parser.add_argument("--url", default='ws://127.0.0.1:8080/sensors/connect?types=["android.sensor.accelerometer","android.sensor.gyroscope"]')
    parser.add_argument("--serial")
    args = parser.parse_args()
    profile = load_mount(args.mount)[args.source]
    if args.source == "phone":
        import websocket
        if profile.get("pan_locked") is not True:
            parser.error("CLI phone monitor needs locked pan; moving-pan caller must supply set_pan measurements")
        sensor = PhoneIMU(profile["R_body_from_sensor_at_pan_zero"], profile["gyro_bias_rad_s"], pan_locked=True)
        stream = websocket.create_connection(args.url, timeout=.15)
        def receive():
            return json.loads(stream.recv())
    else:
        import serial
        if not args.serial:
            parser.error("MPU6050 requires the ESP32 --serial port")
        sensor = BodyIMU(profile["R_body_from_sensor_at_pan_zero"], profile["gyro_bias_rad_s"])
        stream = serial.Serial(args.serial, 460800, timeout=.15)
        def receive():
            line = stream.readline()
            if not line:
                raise SensorError("sensor serial timeout")
            packet = json.loads(line)
            if packet.get("kind") != "imu":
                return None
            return packet
    try:
        while True:
            try:
                packet = receive()
                if packet is None:
                    continue
                sensor.ingest(packet)
                print(json.dumps(sensor.observation(), allow_nan=False), flush=True)
            except (SensorError, ValueError, TimeoutError) as exc:
                print(json.dumps({"valid": False, "error": str(exc)}), flush=True)
    finally:
        stream.close()


if __name__ == "__main__":
    main()
