"""Interlock tests use synthetic calibrations and an in-memory link, never a motor port."""
import copy
import json
import math
from pathlib import Path
import tempfile
import time
import unittest

from locomotion.hardware.bridge import Bridge, Calibration, InterlockError, JOINTS, joint_values


def fixture():
    return {"schema_version": 1, "model": "mist_r7_direct", "verified_on_robot": True,
            "estop_nc_verified": True, "joints": [
                {"name": name, "id": i + 1, "center_tick": 2048,
                 "reference_rad": math.radians((0, 30, 81)[i % 3]), "sign": (-1 if i % 2 else 1),
                 "min_tick": 1024, "max_tick": 3072, "measured": True} for i, name in enumerate(JOINTS)]}


def load(data):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "synthetic.json"
        path.write_text(json.dumps(data))
        return Calibration.load(path)


class FakeLink:
    def __init__(self, calibration):
        self.calibration = calibration
        self.telemetry = {}
        self.imu_packet = {}
        self.received_at = time.monotonic()
        self.calls = []

    def request(self, op, **payload):
        self.calls.append((op, payload))
        return {"profile_hash": self.calibration.digest, "ticks": [2048] * 12, "armed": True}


class CalibrationTests(unittest.TestCase):
    def test_old_four_bar_rejected(self):
        data = fixture()
        data["model"] = "absolute_tibia_1to1"
        with self.assertRaises(InterlockError):
            load(data)

    def test_real_measurements_and_stop_loop_required(self):
        for key in ("verified_on_robot", "estop_nc_verified"):
            data = fixture()
            data[key] = False
            with self.assertRaises(InterlockError):
                load(data)
        data = fixture()
        data["joints"][0]["measured"] = False
        with self.assertRaises(InterlockError):
            load(data)

    def test_non_wrapping_limits_unique_ids_and_integral_ticks(self):
        for field, value in (("id", 2), ("min_tick", 4090), ("center_tick", 2048.0), ("sign", 0)):
            data = fixture()
            data["joints"][0][field] = value
            with self.assertRaises(InterlockError):
                load(data)

    def test_joint_map_round_trip_with_alternating_sign(self):
        calibration = load(fixture())
        q = [math.radians(v) for v in (10, 20, 70) * 4]
        restored = calibration.radians(calibration.ticks(q))
        self.assertLess(max(abs(a - b) for a, b in zip(q, restored)), math.pi / 4096)

    def test_tick_limit_checked_independently_of_cad(self):
        data = fixture()
        data["joints"][0]["max_tick"] = 2050
        calibration = load(data)
        q = [math.radians(v) for v in (20, 30, 81) * 4]
        with self.assertRaises(InterlockError):
            calibration.ticks(q)

    def test_digest_stable_and_changes_with_measurement(self):
        data = fixture()
        a = load(data)
        b = load(copy.deepcopy(data))
        data["joints"][0]["center_tick"] += 1
        self.assertEqual(a.digest, b.digest)
        self.assertNotEqual(a.digest, load(data).digest)
        self.assertIn(a.digest, a.header())

    def test_malformed_and_non_finite_joint_commands_rejected(self):
        for q in ([0] * 3, [float("nan")] * 12, [True] * 12, [float("inf")] * 12, [0] * 12):
            with self.assertRaises(InterlockError):
                joint_values(q)


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.bridge = Bridge()

    def tearDown(self):
        self.bridge.close()

    def test_disarmed_refuses_targets(self):
        with self.assertRaises(InterlockError):
            self.bridge.handle({"op": "q", "q": self.bridge.q})

    def test_timeout_latches_fault(self):
        self.bridge.handle({"op": "arm", "intent_generation": self.bridge.intent_generation})
        self.bridge.last_heartbeat = time.monotonic() - 1
        time.sleep(0.08)
        self.assertFalse(self.bridge.armed)
        self.assertIn("heartbeat", self.bridge.fault)
        with self.assertRaises(InterlockError):
            self.bridge.handle({"op": "arm", "intent_generation": self.bridge.intent_generation})
        self.bridge.handle({"op": "clear", "intent_generation": self.bridge.intent_generation})
        self.bridge.handle({"op": "arm", "intent_generation": self.bridge.intent_generation})
        self.assertTrue(self.bridge.armed)

    def test_physical_gait_blocked_and_hold_starts_from_feedback(self):
        calibration = load(fixture())
        link = FakeLink(calibration)
        bridge = Bridge(calibration, link)
        try:
            with self.assertRaises(InterlockError):
                bridge.handle({"op": "arm", "intent_generation": bridge.intent_generation})
            bridge.handle({"op": "arm", "intent_generation": bridge.intent_generation, "unloaded_fixture_confirmed": True})
            self.assertEqual(calibration.ticks(bridge.q), [2048] * 12)
            with self.assertRaises(InterlockError):
                bridge.handle({"op": "gait", "command": [0.01, 0, 0]})
            q = bridge.q[:]
            q[0] += 0.2
            with self.assertRaises(InterlockError):
                bridge.handle({"op": "q", "q": q})
            self.assertNotIn("ticks", [op for op, _ in link.calls])
        finally:
            bridge.running = False
            bridge.thread.join(timeout=1)

    def test_inverse_kinematics_returns_original_local_tip(self):
        angles = (0.2, 0.3, 1.1)
        yaw, hip, knee = angles
        r = .082 + .09 * math.cos(hip) + .105 * math.cos(hip + knee)
        xyz = [r * math.cos(yaw), r * math.sin(yaw), -.09 * math.sin(hip) - .105 * math.sin(hip + knee)]
        solved = self.bridge.handle({"op": "ik", "xyz_m": xyz})
        self.assertTrue(solved["preview_only"])
        self.assertLess(max(abs(a - b) for a, b in zip(angles, solved["q_leg"])), 1e-10)
        self.assertFalse(self.bridge.armed)


if __name__ == "__main__":
    unittest.main()
