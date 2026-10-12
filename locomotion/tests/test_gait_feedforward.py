"""Check planned support loads and servo position feedforward."""
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gait import CrawlController, ry, rz
from model import LEGS, MOUNTS, NEUTRAL
from kinematics import LIMITS, forward


class PositionFeedforwardTests(unittest.TestCase):
    def setUp(self):
        self.gait = CrawlController()

    def test_static_support_conserves_weight(self):
        expected = (self.gait.model_mass_without_phone + .155) * 9.81
        force = self.gait.estimate_support_forces(0, [0, 0, 0])
        np.testing.assert_allclose(force, np.full(4, expected/4), atol=1e-10)
        for time in np.linspace(0, self.gait.cycle_s, 41):
            force = self.gait.estimate_support_forces(time, [.012, 0, 0])
            self.assertGreaterEqual(force.min(), 0)
            self.assertAlmostEqual(force.sum(), expected, places=9)
            weights = self.gait.support_weights(time, [.012, 0, 0])
            self.assertEqual(np.count_nonzero(force[weights == 0]), 0)

    def test_nominal_stance_bias_has_expected_sign_and_size(self):
        result = self.gait.position_targets(0, [0, 0, 0]).reshape(4, 3)
        expected = NEUTRAL + [0, .02034340409894312, -.03955530796985383]
        np.testing.assert_allclose(result, np.tile(expected, (4, 1)), atol=1e-10)
        self.assertGreater(self.gait.model_mass_without_phone, 2.4)

    def test_position_limits_and_payload_validation(self):
        for time in np.linspace(0, self.gait.cycle_s, 33):
            for command in ([.012, 0, 0], [-.012, 0, 0], [0, .012, 0], [0, -.012, 0]):
                q = self.gait.position_targets(time, command, phone_mass_kg=0).reshape(4, 3)
                self.assertTrue(np.all(q >= LIMITS[:, 0]))
                self.assertTrue(np.all(q <= LIMITS[:, 1]))
                self.assertLessEqual(np.max(np.abs(self.gait.last_position_bias)), .1200000001)
        for value in (-.1, float('nan')):
            with self.assertRaises(ValueError):
                self.gait.position_targets(0, [0, 0, 0], phone_mass_kg=value)

    def test_attitude_rotation_reduces_world_foot_height_error(self):
        nominal = np.asarray([self.gait.nominal[leg] for leg in LEGS])
        for roll, pitch in ((.1, 0), (-.1, 0), (0, .1), (0, -.1)):
            cr, sr = np.cos(roll), np.sin(roll)
            rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
            rotation = ry(pitch) @ rx
            uncorrected = (rotation @ nominal.T).T[:, 2] - nominal[:, 2]
            q = self.gait.targets(0, [.012, 0, 0], attitude=[roll, pitch]).reshape(4, 3)
            corrected = np.asarray([np.asarray(MOUNTS[leg]['xyz']) + rz(MOUNTS[leg]['yaw']) @ forward(angles)
                                    for leg, angles in zip(LEGS, q)])
            error = (rotation @ corrected.T).T[:, 2] - nominal[:, 2]
            self.assertLess(np.mean(np.abs(error)), .6 * np.mean(np.abs(uncorrected)))

    @unittest.skipUnless(importlib.util.find_spec('pybullet'), 'PyBullet is not installed')
    def test_four_directions_at_converged_timestep(self):
        from mist_env import MistEnv

        class PositionController:
            def __init__(self):
                self.geometric = CrawlController()
                self.cycle_s = self.geometric.cycle_s

            def targets(self, time_s, command, attitude=None):
                return self.geometric.position_targets(time_s, command, attitude, .155)

            def position_targets(self, time_s, command, attitude=None, phone_mass_kg=.155):
                return self.geometric.position_targets(time_s, command, attitude, phone_mass_kg)

        for command in ([.012, 0, 0], [-.012, 0, 0], [0, .012, 0], [0, -.012, 0]):
            with self.subTest(command=command):
                env = MistEnv(command=command, randomize=False, payload=.155, max_steps=400, pushes=False)
                env.dt, env.substeps = 1/1000, 20
                env.gait = PositionController()
                try:
                    _, initial = env.reset(seed=42)
                    start = np.asarray(initial['position'])
                    for _ in range(400):
                        _, _, terminated, _, info = env.step(np.zeros(12))
                        self.assertFalse(terminated)
                    direction = np.asarray(command[:2]) / np.linalg.norm(command[:2])
                    progress = (np.asarray(info['position']) - start)[:2] @ direction
                    self.assertGreater(progress, .02)
                    self.assertEqual(info['ik_rejections'], 0)
                finally:
                    env.close()


if __name__ == '__main__':
    unittest.main()
