import math
import random
import unittest

from bench.leg_kinematics import (
    LegGeometry,
    fk_tip_mm,
    ik_tip_mm,
    joints_from_servo_angles,
    radians_from_tick,
    servo_angles_from_joints,
    tick_target,
)


class LegKinematicsTests(unittest.TestCase):
    def setUp(self):
        self.geometry = LegGeometry(32.0, 110.0, 70.0)

    def assertVectorAlmostEqual(self, actual, expected, places=8):
        self.assertEqual(len(actual), len(expected))
        for got, wanted in zip(actual, expected):
            self.assertAlmostEqual(got, wanted, places=places)

    def test_neutral_tip_is_straight_down(self):
        self.assertVectorAlmostEqual(
            fk_tip_mm(self.geometry, (0.0, 0.0, 0.0)),
            (32.0, 0.0, -180.0),
        )

    def test_remote_knee_mapping_uses_absolute_tibia_angle(self):
        joints = tuple(math.radians(v) for v in (12.0, 30.0, -55.0))
        servo = servo_angles_from_joints(joints)
        self.assertAlmostEqual(math.degrees(servo["roll"]), 12.0)
        self.assertAlmostEqual(math.degrees(servo["hip"]), 30.0)
        self.assertAlmostEqual(math.degrees(servo["knee_driver"]), -25.0)
        self.assertVectorAlmostEqual(joints_from_servo_angles(servo), joints)

    def test_spider_branch_round_trip(self):
        random.seed(3215)
        for _ in range(1000):
            joints = (
                math.radians(random.uniform(-50.0, 50.0)),
                math.radians(random.uniform(-20.0, 95.0)),
                math.radians(random.uniform(-125.0, -5.0)),
            )
            target = fk_tip_mm(self.geometry, joints)
            result = ik_tip_mm(self.geometry, target, knee_sign=-1)
            self.assertTrue(result.reachable, result.reason)
            self.assertIsNotNone(result.joints_rad)
            self.assertLess(result.fk_error_mm, 1e-8)
            self.assertVectorAlmostEqual(result.joints_rad, joints, places=8)

    def test_other_knee_branch_reaches_same_tip(self):
        target = fk_tip_mm(
            self.geometry,
            tuple(math.radians(v) for v in (8.0, 40.0, -70.0)),
        )
        result = ik_tip_mm(self.geometry, target, knee_sign=1)
        self.assertTrue(result.reachable)
        solved = fk_tip_mm(self.geometry, result.joints_rad)
        self.assertVectorAlmostEqual(solved, target)

    def test_unreachable_target_is_not_clipped(self):
        result = ik_tip_mm(self.geometry, (500.0, 0.0, -20.0))
        self.assertFalse(result.reachable)
        self.assertIsNone(result.joints_rad)
        self.assertIn("beyond full extension", result.reason)

    def test_tick_conversion_round_trip(self):
        calibration = {
            "center_tick": 2020,
            "sign": -1,
            "min_tick": 1200,
            "max_tick": 2800,
        }
        target = tick_target("hip", math.radians(30.0), calibration)
        self.assertTrue(target.within_limits)
        recovered = radians_from_tick(target.requested_tick, calibration)
        self.assertAlmostEqual(recovered, math.radians(30.0), delta=0.5 / 4096 * 2 * math.pi)

    def test_hip_reference_tick_represents_horizontal_femur(self):
        calibration = {
            "center_tick": 2048,
            "reference_angle_deg": 90.0,
            "sign": 1,
            "min_tick": 1000,
            "max_tick": 3000,
        }
        self.assertAlmostEqual(radians_from_tick(2048, calibration), math.pi / 2)
        target = tick_target("hip", math.pi / 2, calibration)
        self.assertEqual(target.requested_tick, 2048)

    def test_tick_conversion_reports_limit_violation_without_clamping(self):
        calibration = {
            "center_tick": 2048,
            "sign": 1,
            "min_tick": 1900,
            "max_tick": 2200,
        }
        target = tick_target("roll", math.radians(90.0), calibration)
        self.assertFalse(target.within_limits)
        self.assertEqual(target.requested_tick, 3072)


if __name__ == "__main__":
    unittest.main()
