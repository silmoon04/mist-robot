import os
import tempfile
import unittest

from bench.leg_calibration import (
    CalibrationStore,
    calibration_ready,
    default_config,
    validate_config,
)


class LegCalibrationTests(unittest.TestCase):
    def test_default_geometry_matches_physical_test_leg(self):
        config = default_config()
        self.assertEqual(config["geometry"], {
            "hip_offset_mm": 32.0,
            "femur_mm": 110.0,
            "tibia_mm": 70.0,
        })
        self.assertFalse(calibration_ready(config))
        self.assertEqual(config["linkage"]["driver_mm"], 40.0)
        self.assertEqual(config["linkage"]["follower_mm"], 40.0)
        self.assertEqual(config["roles"]["hip"]["reference_angle_deg"], 90.0)

    def test_store_captures_without_losing_other_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "calibration.json")
            store = CalibrationStore(path)
            store.capture("hip", "center_tick", 2011)
            store.set_sign("hip", -1)
            config = store.load()
            self.assertEqual(config["roles"]["hip"]["center_tick"], 2011)
            self.assertEqual(config["roles"]["hip"]["sign"], -1)
            self.assertIsNone(config["roles"]["roll"]["center_tick"])

    def test_duplicate_ids_are_rejected(self):
        config = default_config()
        config["roles"]["hip"]["id"] = 1
        with self.assertRaisesRegex(ValueError, "distinct servo IDs"):
            validate_config(config)

    def test_calibration_ready_requires_both_limits(self):
        config = default_config()
        for role in config["roles"].values():
            role.update(center_tick=2048, sign=1, min_tick=1500, max_tick=2500)
        self.assertTrue(calibration_ready(config))

    def test_physical_endpoints_are_sorted_into_raw_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            store = CalibrationStore(os.path.join(directory, "calibration.json"))
            store.capture_endpoint("hip", "a", 2800)
            halfway = store.load()["roles"]["hip"]
            self.assertIsNone(halfway["min_tick"])
            store.capture_endpoint("hip", "b", 1200)
            role = store.load()["roles"]["hip"]
            self.assertEqual(role["min_tick"], 1200)
            self.assertEqual(role["max_tick"], 2800)


if __name__ == "__main__":
    unittest.main()
