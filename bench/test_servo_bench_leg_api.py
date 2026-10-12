import unittest
import math

from bench import servo_bench
from bench.leg_calibration import default_config


class ServoBenchLegApiTests(unittest.TestCase):
    def test_ik_payload_exposes_remote_knee_servo_angle(self):
        payload = servo_bench.leg_ik_payload({
            "x_mm": 120,
            "y_mm": 0,
            "z_mm": -120,
            "knee_sign": -1,
        })
        self.assertTrue(payload["reachable"])
        self.assertAlmostEqual(
            payload["servo_deg"]["knee_driver"],
            payload["joints_deg"]["hip"] + payload["joints_deg"]["knee"],
            places=5,
        )
        self.assertIn("requested", payload["ticks"]["hip"])
        self.assertFalse(payload["motion_enabled"])
        self.assertTrue(payload["linkage_check"]["within_limits"])

    def test_ik_payload_refuses_unreachable_target(self):
        payload = servo_bench.leg_ik_payload({
            "x_mm": 500,
            "y_mm": 0,
            "z_mm": -20,
        })
        self.assertFalse(payload["reachable"])
        self.assertIn("beyond full extension", payload["reason"])

    def test_disconnected_hardware_check_is_structured(self):
        result = servo_bench.leg_hardware_check()
        self.assertFalse(result["pass"])
        self.assertFalse(result["safe_to_calibrate"])
        self.assertIn("not connected", result["reason"])

    def test_ping_only_snapshot_is_not_reported_as_torque_enabled(self):
        original_open = servo_bench.BUS.ser
        original_ping = servo_bench.BUS.ping
        original_read = servo_bench.BUS.read
        try:
            class OpenPort:
                is_open = True

            servo_bench.BUS.ser = OpenPort()
            servo_bench.BUS.ping = lambda sid: sid == 1
            servo_bench.BUS.read = lambda *args: None
            result = servo_bench.leg_hardware_check()
            joined = " | ".join(result["warnings"])
            self.assertIn("Probable duplicate factory ID 1", joined)
            self.assertIn("registers are unreadable", joined)
            self.assertNotIn("torque is enabled", joined)
        finally:
            servo_bench.BUS.ser = original_open
            servo_bench.BUS.ping = original_ping
            servo_bench.BUS.read = original_read

    def test_coupled_linkage_guard_rejects_near_straight_knee(self):
        config = default_config()
        result = servo_bench.linkage_guard(
            config,
            (0.0, math.radians(60.0), math.radians(-20.0)),
        )
        self.assertFalse(result["within_limits"])
        self.assertEqual(result["q3_safe_min_deg"], -115.0)
        self.assertEqual(result["q3_safe_max_deg"], -55.0)
        self.assertEqual(result["q3_cad_min_deg"], -120.0)
        self.assertEqual(result["q3_cad_max_deg"], -50.0)

    def test_sync_write_packet_matches_feetech_broadcast_shape(self):
        packet = servo_bench.Bus.sync_write_packet(41, [
            (1, bytes([2, 0x34, 0x12])),
            (2, bytes([3, 0x78, 0x56])),
        ])
        self.assertEqual(packet[:7], bytes([0xFF, 0xFF, 0xFE, 12, 0x83, 41, 3]))
        self.assertEqual(packet[7:-1], bytes([1, 2, 0x34, 0x12, 2, 3, 0x78, 0x56]))
        self.assertEqual(packet[-1], servo_bench.checksum(packet[2:-1]))

    def test_motion_goal_rows_write_official_seven_byte_sts_block(self):
        rows = servo_bench.MotionController._goal_rows([1], {1: 0x1234})
        self.assertEqual(rows, [(1, bytes([
            servo_bench.MOTION_ACCELERATION,
            0x34, 0x12,
            0, 0,
            servo_bench.MOTION_SPEED & 0xFF,
            (servo_bench.MOTION_SPEED >> 8) & 0xFF,
        ]))])

    def test_workspace_projection_clamps_unreachable_cursor_to_valid_pose(self):
        projected = servo_bench.project_leg_target({
            "x_mm": 500.0,
            "y_mm": 0.0,
            "z_mm": -5.0,
        })
        self.assertTrue(projected["projected"])
        self.assertGreater(projected["projection_distance_mm"], 100.0)
        self.assertTrue(projected["ik"]["reachable"])
        self.assertTrue(projected["ik"]["within_calibrated_limits"])

    def test_motion_speed_profile_is_bounded_and_reports_ramp_rate(self):
        normal = servo_bench.motion_profile(70)
        self.assertEqual(normal["max_step_ticks"], 44)
        self.assertEqual(normal["speed"], 730)
        self.assertEqual(normal["acceleration"], 15)
        self.assertAlmostEqual(normal["estimated_deg_s"], 116.015625)
        self.assertEqual(servo_bench.motion_profile(999)["speed_percent"], 100)

    def test_public_workspace_has_rom_ranges_and_closed_envelope_points(self):
        workspace = servo_bench.public_workspace_payload()
        self.assertEqual(set(workspace["ranges_deg"]), {
            "roll", "hip", "knee_driver_absolute", "knee_relative",
        })
        self.assertGreater(len(workspace["envelope"]), 50)


if __name__ == "__main__":
    unittest.main()
