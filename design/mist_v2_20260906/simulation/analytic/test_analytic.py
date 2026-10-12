import unittest
import numpy as np

from analytic import MODES, directional_speed, fk, ik_planar, jacobian, mass_limit, motor_torque, transmission


class MechanicsTests(unittest.TestCase):
    def test_jacobian_matches_finite_difference_with_yaw_offsets(self):
        q = np.array([.4, .8, -1.1])
        lengths, offsets = (.14, .13), (.035, .030)
        numeric = np.column_stack([(fk(q + np.eye(3)[i] * 1e-6, lengths, offsets) - fk(q - np.eye(3)[i] * 1e-6, lengths, offsets)) / 2e-6 for i in range(3)])
        np.testing.assert_allclose(jacobian(q, lengths, offsets), numeric, rtol=1e-8, atol=1e-10)

    def test_transmissions_preserve_virtual_work(self):
        qdot, tq = np.array([.3, -.4, .9]), np.array([.2, 1.7, -.8])
        for mode in MODES:
            A = transmission(mode, (1.5, 2, 3))
            tm = motor_torque(tq, A, (1, 1, 1))
            self.assertAlmostEqual(float(tq @ qdot), float(tm @ (A @ qdot)), places=12)

    def test_absolute_tibia_cancels_hip_knee_motion(self):
        A = transmission("absolute_tibia", (2, 2, 2))
        np.testing.assert_allclose(A @ [0, 1, -1], [0, 2, 0])
        np.testing.assert_allclose(motor_torque([0, .176886, -2.299522], A, [1, 1, 1]), [0, 1.238204, -1.149761])

    def test_unequal_remote_pulley_does_not_equal_proximal_reduction(self):
        A = transmission("unequal_remote_pulleys", (2, 2, 3))
        np.testing.assert_allclose(A @ [0, 1, -1], [0, 2, -2])
        np.testing.assert_allclose(motor_torque([0, 3, 6], A, [1, 1, 1]), [0, .5, 2])

    def test_ik_recovers_known_targets_and_rejects_impossible(self):
        for target in ((.06, .19), (.12, .10), (.15, -.02)):
            q = ik_planar(*target, (.14, .13))
            self.assertIsNotNone(q)
            np.testing.assert_allclose(fk(q, (.14, .13)), [target[0], 0, -target[1]], atol=1e-12)
        self.assertIsNone(ik_planar(.30, .20, (.14, .13)))

    def test_vertical_gravity_creates_no_yaw_torque(self):
        J = jacobian([.7, 1.1, -1.4], (.14, .13), (.035, .03))
        self.assertAlmostEqual(float((J.T @ [0, 0, 25])[0]), 0.0)

    def test_backlash_mapping_has_correlated_hip_knee_error(self):
        A = transmission("absolute_tibia", (2, 2, 2))
        dq = np.linalg.solve(A, [0, .02, 0])
        np.testing.assert_allclose(dq, [0, .01, -.01])

    def test_mass_envelope_handles_opposing_motor_loads(self):
        self.assertAlmostEqual(mass_limit([1, -2, 0], [-.5, .5, .1], 1), .75)
        self.assertEqual(mass_limit([1, 0], [0, 2], 1), 0)

    def test_stationary_motor_must_still_hold_load(self):
        p = {"servo": {"nominal_voltage_v": 12, "stall_torque_nm": 2.94, "no_load_speed_rpm": 45, "continuous_fraction_of_stall": .3, "peak_fraction_of_stall": .55}}
        self.assertEqual(directional_speed(np.eye(3), np.eye(3), [3, 0, 0], 12, p, (0, 1, 0)), 0)


if __name__ == "__main__":
    unittest.main()
