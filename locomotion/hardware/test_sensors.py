"""Sensor replay checks cover units, frame transforms, freshness and missing inputs."""
import math
import unittest

import numpy as np

from locomotion.hardware.sensors import BodyIMU, G, GravityEstimator, PhoneIMU, SensorError, rotation, select_observation


def phone_packet(kind, values, stamp=1_000_000_000):
    return {"type": "android.sensor." + kind, "values": values, "timestamp": stamp}


def mpu_packet(stamp=0, gyro=(0, 0, 0)):
    return {"kind": "imu", "source": "mpu6050", "valid": True, "t_ms": stamp,
            "accel_m_s2": [0, 0, G], "gyro_rad_s": gyro}


class SensorTests(unittest.TestCase):
    def test_proper_rotation_required(self):
        for value in (np.diag([1, 1, -1]), np.eye(3) * 2, np.zeros((2, 2))):
            with self.assertRaises(SensorError):
                rotation(value)

    def test_mpu_level_units_and_staleness(self):
        sensor = BodyIMU(np.eye(3))
        sensor.ingest(mpu_packet(), received_at=10)
        self.assertEqual(sensor.observation(10.01)["gravity_body"], [0, 0, -1])
        with self.assertRaises(SensorError):
            sensor.observation(10.2)

    def test_mpu_mount_and_bias(self):
        r = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
        sensor = BodyIMU(r, gyro_bias_rad_s=[.1, 0, 0])
        sensor.ingest(mpu_packet(gyro=[.5, 0, 0]), received_at=1)
        np.testing.assert_allclose(sensor.observation(1)["gyro_body"], [0, .4, 0])

    def test_mpu_missing_invalid_or_out_of_order_rejected(self):
        sensor = BodyIMU(np.eye(3))
        with self.assertRaises(SensorError):
            sensor.observation()
        packet = mpu_packet()
        packet["valid"] = False
        with self.assertRaises(SensorError):
            sensor.ingest(packet)
        sensor.ingest(mpu_packet(10), received_at=1)
        with self.assertRaises(SensorError):
            sensor.ingest(mpu_packet(9), received_at=1)

    def test_gravity_integration_sign_and_acceleration_gate(self):
        estimator = GravityEstimator()
        estimator.update(0., [0, 0, G], [0, 0, 0])
        gravity = estimator.update(.05, [0, 0, 2 * G], [math.pi / 2, 0, 0])
        self.assertLess(gravity[1], 0)
        self.assertAlmostEqual(float(np.linalg.norm(gravity)), 1.)
        with self.assertRaises(SensorError):
            estimator.update(.5, [0, 0, G], [0, 0, 0])

    def test_phone_android_gravity_is_inverted_and_axes_are_mounted(self):
        # Portrait axes remain device axes even when screen content rotates.
        mount = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
        sensor = PhoneIMU(mount)
        sensor.ingest(phone_packet("gravity", [0, G, 0]), 1)
        sensor.ingest(phone_packet("gyroscope", [0, .5, 0]), 1)
        out = sensor.observation(1.01)
        np.testing.assert_allclose(out["gravity_body"], [0, 0, -1])
        np.testing.assert_allclose(out["gyro_body"], [0, 0, .5])

    def test_phone_pan_rate_is_subtracted_and_pan_must_be_fresh(self):
        sensor = PhoneIMU(np.eye(3), pan_locked=False)
        sensor.ingest(phone_packet("gravity", [G, 0, 0]), 1)
        sensor.ingest(phone_packet("gyroscope", [0, 0, .4]), 1)
        with self.assertRaises(SensorError):
            sensor.observation(1)
        sensor.set_pan(math.pi / 2, .4, 1)
        with self.assertRaisesRegex(SensorError, 'locked pan only'):
            sensor.observation(1)

    def test_phone_fallback_accel_estimator_can_be_read_twice(self):
        sensor = PhoneIMU(np.eye(3))
        sensor.ingest(phone_packet("accelerometer", [0, 0, G]), 1)
        sensor.ingest(phone_packet("gyroscope", [0, 0, 0]), 1)
        self.assertEqual(sensor.observation(1)["gravity_body"], sensor.observation(1.01)["gravity_body"])
        self.assertAlmostEqual(sensor.observation(1.01)["sample_age_s"], .01)

    def test_phone_repeated_sensor_timestamp_and_missing_pair_rejected(self):
        sensor = PhoneIMU(np.eye(3))
        packet = phone_packet("gravity", [0, 0, G])
        sensor.ingest(packet, 1)
        with self.assertRaises(SensorError):
            sensor.ingest(packet, 1)
        with self.assertRaises(SensorError):
            sensor.observation(1)

    def test_auto_selects_fresh_stream_and_none_refuses_policy_observation(self):
        mpu = BodyIMU(np.eye(3))
        phone = PhoneIMU(np.eye(3))
        mpu.ingest(mpu_packet(), 1)
        phone.ingest(phone_packet("gravity", [0, 0, G]), 1.2)
        phone.ingest(phone_packet("gyroscope", [0, 0, 0]), 1.2)
        self.assertEqual(select_observation("auto", mpu, phone, 1.01)["source"], "mpu6050")
        self.assertEqual(select_observation("auto", mpu, phone, 1.21)["source"], "phone")
        for source in ("none", "auto"):
            with self.assertRaises(SensorError):
                select_observation(source, now=2)


if __name__ == "__main__":
    unittest.main()
