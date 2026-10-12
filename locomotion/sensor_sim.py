"""Synthetic IMU samples delivered on the physics clock."""
from __future__ import annotations

from collections import deque
from copy import deepcopy
import math

import numpy as np

try:
    from .hardware.sensors import rotation, vector
except ImportError:
    from hardware.sensors import rotation, vector


# These are simulation assumptions until measured on the fitted robot.
# Phone 10 Hz pairs consume 20 messages/s; the repository historically recorded
# about 25 aggregate SensorServer messages/s, not 25 Hz for each sensor.
SENSOR_PROFILES = {
    "mpu6050": {
        "sample_rate_hz": 50.0,
        "transport_delay_s": 0.005,
        "gravity_noise_std": 0.004,
        "gyro_noise_std_rad_s": 0.012,
        "dropout_probability": 0.0,
        "gyro_bias_rad_s": [0.0, 0.0, 0.0],
        "max_age_s": 0.1,
        "R_body_from_sensor_at_pan_zero": np.eye(3).tolist(),
        "pan_locked": True,
    },
    "phone": {
        "sample_rate_hz": 10.0,
        "transport_delay_s": 0.06,
        "gravity_noise_std": 0.008,
        "gyro_noise_std_rad_s": 0.02,
        "dropout_probability": 0.0,
        "gyro_bias_rad_s": [0.0, 0.0, 0.0],
        "max_age_s": 0.2,
        "R_body_from_sensor_at_pan_zero": np.eye(3).tolist(),
        "pan_locked": True,
    },
}


def attitude_from_gravity(gravity_body):
    """Recover roll and pitch from body-down gravity; yaw is unobserved."""
    x, y, z = vector(gravity_body, "gravity")
    if np.linalg.norm([x, y, z]) < 1e-12:
        raise ValueError("gravity direction must be nonzero")
    return np.array([math.atan2(-y, -z), math.atan2(x, math.hypot(y, z))])


class SimulatedIMU:
    """Hold the latest delivered reading without substituting current truth.

    Noise and residual gyro bias are applied in sensor axes, then transformed
    using the same sensor-to-body mount convention as hardware/sensors.py.
    Projected gravity represents an estimated down direction, not raw specific
    force. Accelerometer transients and estimator drift are not modelled here.
    """

    def __init__(self, mode="mpu6050", profile=None, rng=None):
        if mode not in ("mpu6050", "phone", "none"):
            raise ValueError("sensor mode must be mpu6050, phone or none")
        if mode == "none" and profile:
            raise ValueError("open-loop mode has no sensor profile")
        self.mode = mode
        self.rng = np.random.default_rng() if rng is None else rng
        self.profile = deepcopy(SENSOR_PROFILES.get(mode, {}))
        if profile:
            unknown = set(profile) - set(self.profile)
            if unknown:
                raise ValueError(f"unknown sensor profile settings: {sorted(unknown)}")
            self.profile.update(deepcopy(profile))
        if mode != "none":
            for name in ("sample_rate_hz", "transport_delay_s", "gravity_noise_std",
                         "gyro_noise_std_rad_s", "dropout_probability", "max_age_s"):
                value = self.profile[name]
                if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f"{name} must be finite")
                if value < 0 or (name in ("sample_rate_hz", "max_age_s") and value == 0):
                    raise ValueError(f"invalid {name}")
            if self.profile["dropout_probability"] > 1:
                raise ValueError("dropout probability must be between zero and one")
            if self.profile["pan_locked"] is not True:
                raise ValueError("simulation locomotion requires locked sensor pan")
            self.mount = rotation(self.profile["R_body_from_sensor_at_pan_zero"])
            self.bias = vector(self.profile["gyro_bias_rad_s"], "gyro bias")
            self.period = 1.0 / self.profile["sample_rate_hz"]
        self.reset()

    def reset(self):
        self._clock = None
        self._next_sample = 0.0
        self._pending = deque()
        self._latest = None
        self.generated_samples = self.dropped_samples = 0

    def advance(self, time_s, rotation_body_to_world=None, omega_world=None):
        """Generate at most one sample per physics tick and deliver due packets.

        Rates finer than the caller's physics ticks are limited by those ticks.
        Sample timestamps record the actual physics tick, avoiding backfilled
        readings that pretend current truth was measured in the past.
        """
        if isinstance(time_s, (bool, np.bool_)) or not math.isfinite(time_s) or time_s < 0:
            raise ValueError("sensor time must be finite, nonnegative physics time")
        if self._clock is not None and time_s < self._clock:
            raise ValueError("sensor physics time cannot move backwards")
        self._clock = float(time_s)
        if self.mode == "none":
            return
        if time_s + 1e-12 >= self._next_sample:
            body_rotation = rotation(rotation_body_to_world)
            omega = vector(omega_world, "world gyro")
            self.generated_samples += 1
            self._next_sample = (math.floor((time_s + 1e-12) / self.period) + 1) * self.period
            if self.rng.random() < self.profile["dropout_probability"]:
                self.dropped_samples += 1
            else:
                gravity_sensor = self.mount.T @ (body_rotation.T @ [0.0, 0.0, -1.0])
                gyro_sensor = self.mount.T @ (body_rotation.T @ omega)
                gravity_sensor += self.rng.normal(0.0, self.profile["gravity_noise_std"], 3)
                gravity_sensor /= np.linalg.norm(gravity_sensor)
                gyro_sensor += self.bias + self.rng.normal(0.0, self.profile["gyro_noise_std_rad_s"], 3)
                ready_at = time_s + self.profile["transport_delay_s"]
                self._pending.append((ready_at, time_s, self.mount @ gravity_sensor, self.mount @ gyro_sensor))
        while self._pending and self._pending[0][0] <= time_s + 1e-12:
            self._latest = self._pending.popleft()

    def observation(self):
        """Return copies of the delivered body vectors, or neutral at startup."""
        if self._latest is None:
            return np.zeros(3), np.zeros(3)
        return self._latest[2].copy(), self._latest[3].copy()

    def status(self):
        sample_age = None if self._latest is None else self._clock - self._latest[1]
        received_age = None if self._latest is None else self._clock - self._latest[0]
        return {
            "mode": self.mode,
            "open_loop": self.mode == "none",
            "frame": "body", "units": "unit down vector; rad/s",
            "measurement_time_s":None if self._latest is None else self._latest[1],
            "arrival_time_s":None if self._latest is None else self._latest[0],
            "valid":self.mode != "none" and sample_age is not None and sample_age <= self.profile["max_age_s"],
            "ready": self.mode != "none" and self._latest is not None,
            "stale": self.mode != "none" and (sample_age is None or sample_age > self.profile["max_age_s"]),
            "sample_age_s": sample_age,
            "received_age_s": received_age,
            "generated_samples": self.generated_samples,
            "dropped_samples": self.dropped_samples,
            "profile": deepcopy(self.profile),
        }
