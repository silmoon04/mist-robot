"""Offline contract tests. No existing app or bench process is imported."""
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import r5_preview as r5


class R5PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = r5.build_profile()

    def setUp(self):
        self.request = r5.neutral_request(self.profile)

    def test_all_thirteen_ids_and_new_joint_names(self):
        self.assertEqual([(row["joint_name"], row["proposed_servo_id"])
                          for row in self.profile["joints"]], [
            ("yaw_FL", 1), ("hip_FL", 2), ("knee_FL", 3),
            ("yaw_FR", 4), ("hip_FR", 5), ("knee_FR", 6),
            ("yaw_RL", 7), ("hip_RL", 8), ("knee_RL", 9),
            ("yaw_RR", 10), ("hip_RR", 11), ("knee_RR", 12), ("phone_pan", 13)])

    def test_r5_geometry_and_hip_origins_come_from_manifest(self):
        self.assertEqual(self.profile["design_revision"], "hex_quad_r5_inward_hip_straight_tibia")
        self.assertEqual(self.profile["link_dimensions_mm"],
                         {"coxa_mm": 70.0, "femur_mm": 90.0, "tibia_mm": 105.0})
        hips = [row for row in self.profile["joints"] if row["joint_name"].startswith("hip_")]
        self.assertEqual(len(hips), 4)
        for row in hips:
            self.assertEqual(row["origin_mm"], [70.0, 0.0, 0.0])

    def test_stale_coxa_origin_is_rejected(self):
        manifest = r5.read_json(r5.DEFAULT_MANIFEST)
        manifest["links"]["femur_FL"]["joint"]["origin_mm"] = [50.0, 0.0, 0.0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            r5.write_json(path, manifest)
            with self.assertRaisesRegex(r5.ContractError, "disagrees with link dimensions"):
                r5.build_profile(path)

    def test_nonfinite_link_dimension_is_rejected(self):
        manifest = r5.read_json(r5.DEFAULT_MANIFEST)
        manifest["parameters"]["coxa_mm"] = 10 ** 400
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            r5.write_json(path, manifest)
            with self.assertRaises(r5.ContractError):
                r5.build_profile(path)

    def test_neutral_uses_new_cad_frames(self):
        out = r5.preview(self.request, self.profile)
        angles = {row["joint_name"]: row["angle_deg"] for row in out["targets"]}
        for leg in r5.LEGS:
            self.assertAlmostEqual(angles[f"yaw_{leg}"], 0)
            self.assertAlmostEqual(angles[f"hip_{leg}"], 30)
            self.assertAlmostEqual(angles[f"knee_{leg}"], 75)
        self.assertFalse(out["actuated"])
        self.assertIsNone(out["raw_servo_counts"])
        self.assertIsNone(out["transport_packets"])

    def test_calibration_remains_missing_for_each_joint(self):
        for row in self.profile["joints"]:
            self.assertIsNone(row["calibration"]["reference_tick"])
            self.assertIsNone(row["calibration"]["direction_sign"])
            self.assertFalse(row["calibration"]["mode_and_startup_position_verified"])

    def test_capability_reports_no_hardware(self):
        result = r5.preview({"schema_version": 1, "action": "get_capabilities", "args": {}})
        self.assertFalse(result["profile"]["actuation_supported"])
        self.assertIn("no wheels", result["profile"]["body"])

    def test_stop_does_not_claim_physical_acknowledgement(self):
        result = r5.preview({"schema_version": 1, "action": "stop", "args": {}})
        self.assertFalse(result["physical_stop_confirmed"])

    def test_hardware_mode_is_refused(self):
        with self.assertRaisesRegex(r5.ContractError, "calibration is missing"):
            r5.preview(self.request, self.profile, mode="hardware")

    def test_unrecognized_execution_mode_is_refused(self):
        with self.assertRaisesRegex(r5.ContractError, "Actuation disabled"):
            r5.preview(self.request, mode="live")

    def test_editing_calibration_cannot_enable_actuation(self):
        profile = deepcopy(self.profile)
        for row in profile["joints"]:
            row["calibration"]["reference_tick"] = 2048
            row["calibration"]["direction_sign"] = 1
        with self.assertRaisesRegex(r5.ContractError, "regenerate"):
            r5.preview(self.request, profile)

    def test_changed_id_proposal_is_rejected(self):
        profile = deepcopy(self.profile)
        profile["joints"][12]["proposed_servo_id"] = 1
        with self.assertRaises(r5.ContractError):
            r5.preview(self.request, profile)

    def test_missing_joint_is_rejected(self):
        del self.request["args"]["positions_rad"]["knee_RR"]
        with self.assertRaises(r5.ContractError):
            r5.preview(self.request)

    def test_old_remote_knee_name_is_rejected(self):
        self.request["args"]["positions_rad"]["knee_driver"] = 0
        with self.assertRaises(r5.ContractError):
            r5.preview(self.request)

    def test_yaw_limits_match_19_degrees_and_reject_beyond(self):
        rows = {row["joint_name"]: row for row in self.profile["joints"]}
        for leg in r5.LEGS:
            name = f"yaw_{leg}"
            self.assertEqual(rows[name]["preview_limits_rad"],
                             [-math.radians(19), math.radians(19)])
            for sign in (-1, 1):
                with self.subTest(joint=name, sign=sign):
                    self.request["args"]["positions_rad"][name] = sign * math.radians(19)
                    self.assertTrue(r5.preview(self.request)["geometry_preview_valid"])
                    self.request["args"]["positions_rad"][name] = sign * math.radians(19.00001)
                    with self.assertRaisesRegex(r5.ContractError, f"{name} is outside"):
                        r5.preview(self.request)
            self.request["args"]["positions_rad"][name] = 0

    def test_nonfinite_boolean_string_positions_are_rejected(self):
        for value in [math.nan, math.inf, -math.inf, True, "0.1", 10 ** 400, -(10 ** 400)]:
            with self.subTest(value=value), self.assertRaises(r5.ContractError):
                self.request["args"]["positions_rad"]["yaw_FL"] = value
                r5.preview(self.request)

    def test_degree_value_is_not_silently_treated_as_radians(self):
        self.request["args"]["positions_rad"]["hip_FL"] = 30
        with self.assertRaises(r5.ContractError):
            r5.preview(self.request)

    def test_pan_only_preserves_continuous_joint_principal_angle(self):
        for angle in [-math.pi, 0, math.pi]:
            result = r5.preview({"schema_version": 1, "action": "phone_pan",
                                 "args": {"angle_rad": angle, "usb_connected": False}})
            self.assertEqual(len(result["targets"]), 1)
            self.assertEqual(result["targets"][0]["proposed_servo_id"], 13)
            self.assertEqual(result["targets"][0]["angle_rad"], angle)

    def test_pan_does_not_guess_wrap_count(self):
        with self.assertRaises(r5.ContractError):
            r5.preview({"schema_version": 1, "action": "phone_pan",
                        "args": {"angle_rad": 2 * math.pi, "usb_connected": False}})

    def test_usb_connected_blocks_pan_even_at_neutral(self):
        self.request["args"]["usb_connected"] = True
        with self.assertRaisesRegex(r5.ContractError, "USB"):
            r5.preview(self.request)

    def test_usb_state_cannot_be_omitted_or_coerced(self):
        for value in [None, 0, "false"]:
            with self.subTest(value=value), self.assertRaises(r5.ContractError):
                self.request["args"]["usb_connected"] = value
                r5.preview(self.request)
        del self.request["args"]["usb_connected"]
        with self.assertRaises(r5.ContractError):
            r5.preview(self.request)

    def test_old_brain_bus_log_is_not_a_command(self):
        with self.assertRaises(r5.ContractError):
            r5.preview({"wall": "2026-09-12T12:00:00Z", "tool": "walk",
                        "args": {"distance_m": 1}, "result": "simulated"})

    def test_high_level_motion_and_gaze_have_no_automatic_mapping(self):
        for action in ("drive", "walk", "move", "dance", "pose", "turn", "look_at"):
            with self.subTest(action=action), self.assertRaises(r5.ContractError):
                r5.preview({"schema_version": 1, "action": action, "args": {}})

    def test_additional_execution_field_is_rejected(self):
        self.request["execute_hardware"] = True
        with self.assertRaises(r5.ContractError):
            r5.preview(self.request)

    def test_stale_manifest_hash_is_rejected(self):
        profile = deepcopy(self.profile)
        profile["manifest_sha256"] = "0" * 64
        with self.assertRaises(r5.ContractError):
            r5.preview(self.request, profile)

    def test_wrong_manifest_revision_and_missing_link_are_rejected(self):
        manifest = r5.read_json(r5.DEFAULT_MANIFEST)
        for change in ("revision", "link", "count", "parent"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                altered = deepcopy(manifest)
                if change == "revision":
                    altered["revision"] = "old_robot"
                elif change == "link":
                    del altered["links"]["tibia_RR"]
                elif change == "count":
                    altered["parameters"]["servo_count"] = 16
                else:
                    altered["links"]["tibia_RR"]["joint"]["parent"] = "base"
                path = Path(directory) / "manifest.json"
                r5.write_json(path, altered)
                with self.assertRaises(r5.ContractError):
                    r5.build_profile(path)

    def test_duplicate_keys_and_json_nan_are_rejected(self):
        for raw in [b'{"action":"stop","action":"phone_pan"}', b'{"value":NaN}']:
            with self.subTest(raw=raw), self.assertRaises(r5.ContractError):
                r5.decode_json(raw)

    def test_large_manifest_limit_is_rejected(self):
        manifest = r5.read_json(r5.DEFAULT_MANIFEST)
        manifest["links"]["coxa_FL"]["joint"]["limits_rad"][1] = 10 ** 400
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            r5.write_json(path, manifest)
            with self.assertRaises(r5.ContractError):
                r5.build_profile(path)

    def test_alternate_manifest_has_actual_source_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "other_manifest.json"
            path.write_bytes(r5.DEFAULT_MANIFEST.read_bytes())
            profile = r5.build_profile(path)
            self.assertEqual(profile["manifest_path"], path.resolve().as_posix())
            self.assertEqual(profile["manifest_sha256"], self.profile["manifest_sha256"])

    def test_cli_large_integer_returns_structured_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            self.request["args"]["positions_rad"]["yaw_FL"] = 10 ** 400
            r5.write_json(path, self.request)
            result = subprocess.run([sys.executable, str(r5.HERE / "r5_preview.py"),
                                     "preview", "--request", str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, "")
            self.assertFalse(json.loads(result.stdout)["actuated"])

    def test_cli_hardware_refusal_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "never_written.json"
            result = subprocess.run([sys.executable, str(r5.HERE / "r5_preview.py"),
                                     "neutral", "--mode", "hardware", "--output", str(output)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())
            self.assertFalse(json.loads(result.stdout)["actuated"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
