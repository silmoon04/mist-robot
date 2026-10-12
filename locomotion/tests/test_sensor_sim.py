import math
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hardware.sensors import rz
from mist_env import MistEnv
from model import NEUTRAL
from sensor_sim import SENSOR_PROFILES, SimulatedIMU, attitude_from_gravity


def quiet_profile(**changes):
    return {"gravity_noise_std": 0.0, "gyro_noise_std_rad_s": 0.0, **changes}


def body_rotation(roll, pitch, yaw=0.0):
    cr, sr, cp, sp = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    return rz(yaw) @ ry @ rx


@pytest.mark.parametrize("mode", ["mpu6050", "phone"])
def test_projection_and_hardware_mount_convention(mode):
    mount = body_rotation(0.2, -0.5, 0.8)
    body = body_rotation(0.3, -0.2, 1.1)
    bias = np.array([0.01, -0.03, 0.02])
    omega = np.array([0.6, -0.8, 1.0])
    imu = SimulatedIMU(mode, quiet_profile(transport_delay_s=0,
                       R_body_from_sensor_at_pan_zero=mount.tolist(), gyro_bias_rad_s=bias.tolist()))
    imu.advance(0.0, body, omega)
    gravity, gyro = imu.observation()
    np.testing.assert_allclose(gravity, body.T @ [0, 0, -1], atol=1e-15)
    np.testing.assert_allclose(gyro, body.T @ omega + mount @ bias, atol=1e-15)
    np.testing.assert_allclose(attitude_from_gravity(gravity), [0.3, -0.2], atol=1e-15)


def test_sampling_delay_holds_previous_packet_without_truth_fallback():
    imu = SimulatedIMU(profile=quiet_profile())
    imu.advance(0, np.eye(3), [1, 2, 3])
    assert not imu.status()["ready"]
    np.testing.assert_array_equal(imu.observation()[1], [0, 0, 0])
    imu.advance(0.004, np.eye(3), [4, 5, 6])
    assert not imu.status()["ready"]
    imu.advance(0.005, np.eye(3), [4, 5, 6])
    np.testing.assert_array_equal(imu.observation()[1], [1, 2, 3])
    imu.advance(0.020, np.eye(3), [7, 8, 9])
    np.testing.assert_array_equal(imu.observation()[1], [1, 2, 3])
    imu.advance(0.025, np.eye(3), [10, 11, 12])
    np.testing.assert_array_equal(imu.observation()[1], [7, 8, 9])
    assert imu.status()["generated_samples"] == 2
    assert imu.status()["sample_age_s"] == pytest.approx(0.005)


def test_dropout_holds_reading_and_reports_staleness():
    imu = SimulatedIMU(profile=quiet_profile(transport_delay_s=0))
    imu.advance(0, np.eye(3), [1, 2, 3])
    imu.profile["dropout_probability"] = 1.0
    for tick in range(1, 151):
        imu.advance(tick / 1000, np.eye(3), [4, 5, 6])
    np.testing.assert_array_equal(imu.observation()[1], [1, 2, 3])
    assert imu.status()["stale"]
    assert imu.status()["dropped_samples"] == 7


def test_seed_reproduces_noise_dropout_and_unit_gravity():
    imus = [SimulatedIMU("phone", {"dropout_probability": 0.35},
                        np.random.default_rng(123)) for _ in range(2)]
    readings = []
    for imu in imus:
        series = []
        for tick in range(1001):
            imu.advance(tick / 1000, body_rotation(0.2, 0.1), [0.5, 0, 0])
            series.append(np.r_[imu.observation()[0], imu.observation()[1]])
        readings.append(series)
    np.testing.assert_array_equal(readings[0], readings[1])
    norms=np.linalg.norm(np.array(readings[0])[:, :3], axis=1)
    assert np.all(np.isclose(norms,0) | np.isclose(norms,1))
    assert imus[0].dropped_samples > 0
    assert imus[0].generated_samples == 11


def test_none_is_explicit_open_loop_and_never_needs_truth():
    imu = SimulatedIMU("none")
    for time_s in (0, 0.1, 1):
        imu.advance(time_s)
        np.testing.assert_array_equal(imu.observation()[0], [0, 0, 0])
        np.testing.assert_array_equal(imu.observation()[1], [0, 0, 0])
    assert imu.status()["open_loop"]
    assert not imu.status()["ready"]


def test_caller_tick_limits_rate_without_backfilled_truth():
    imu = SimulatedIMU(profile=quiet_profile(transport_delay_s=0))
    imu.advance(0, np.eye(3), [1, 0, 0])
    imu.advance(0.5, np.eye(3), [2, 0, 0])
    assert imu.generated_samples == 2
    assert imu.status()["sample_age_s"] == 0


@pytest.mark.parametrize("profile", [
    {"sample_rate_hz": 0}, {"transport_delay_s": -0.1},
    {"gravity_noise_std": float("nan")}, {"dropout_probability": 1.1},
    {"gyro_bias_rad_s": [0, 0]}, {"pan_locked": False}, {"unknown": 1},
    {"R_body_from_sensor_at_pan_zero": np.diag([1, 1, -1]).tolist()},
])
def test_invalid_profiles_rejected(profile):
    with pytest.raises(ValueError):
        SimulatedIMU(profile=profile)


def test_invalid_mode_and_backwards_physics_clock_rejected():
    with pytest.raises(ValueError):
        SimulatedIMU("automatic")
    imu = SimulatedIMU("none")
    imu.advance(1)
    with pytest.raises(ValueError):
        imu.advance(0.5)


def test_observation_copies_cannot_modify_cached_sensor_reading():
    imu = SimulatedIMU(profile=quiet_profile(transport_delay_s=0))
    imu.advance(0, np.eye(3), [1, 2, 3])
    gravity, gyro = imu.observation()
    gravity[:] = gyro[:] = 100
    np.testing.assert_array_equal(imu.observation()[0], [0, 0, -1])
    np.testing.assert_array_equal(imu.observation()[1], [1, 2, 3])


def test_environment_actor_and_attitude_controller_use_same_delayed_sensor():
    env = MistEnv(command=(0, 0, 0), randomize=False, payload=0,
                  sensor_profile=quiet_profile(transport_delay_s=0.08))
    try:
        obs, info = env.reset(seed=17)
        np.testing.assert_array_equal(obs[:6], env._obs()[:6])
        captured = []

        def targets(time_s, command, attitude, phone_mass_kg):
            captured.append(attitude.copy())
            return np.tile(NEUTRAL, 4)

        env.gait.position_targets = targets
        obs_after, *_ = env.step(np.zeros(12))
        np.testing.assert_allclose(captured[0], attitude_from_gravity(obs[:3]), atol=1e-8)
        assert obs_after.shape == (47,)
        assert info["sensor"]["sample_age_s"] >= 0.08 - 1e-12
        assert info["sensor"]["mode"] == "mpu6050"
    finally:
        env.close()


def test_phone_mode_rejects_missing_payload():
    env = MistEnv(randomize=False, payload=0, sensor_mode="phone")
    try:
        with pytest.raises(ValueError, match="present phone payload"):
            env.reset(seed=1)
    finally:
        env.close()


@pytest.mark.parametrize("mode,payload", [("phone", 0.155), ("none", 0)])
def test_environment_phone_or_none_reset_and_shape(mode, payload):
    env = MistEnv(randomize=False, payload=payload, sensor_mode=mode)
    try:
        obs, info = env.reset(seed=1)
        assert obs.shape == (47,)
        assert info["sensor"]["open_loop"] == (mode == "none")
        if mode == "none":
            np.testing.assert_array_equal(obs[:6], [0, 0, 0, 0, 0, 0])
        else:
            assert info["sensor"]["ready"]
    finally:
        env.close()


def test_phone_default_is_conservative_pair_rate_assumption():
    assert SENSOR_PROFILES["mpu6050"]["sample_rate_hz"] == 50
    assert SENSOR_PROFILES["phone"]["sample_rate_hz"] * 2 < 25
