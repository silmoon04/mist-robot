"""Check alternate leg geometry, source audits and measurement provenance."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from design_profile import DEFAULT_PROFILE, audit_measurements, compare_profiles, load_profile, measurement_template, sha256
from kinematics import LegGeometry, NEUTRAL, forward, inverse, jacobian, foot_in_body, inverse_body, validate_angles, validate_limits


class GeometryTests(unittest.TestCase):
    def test_other_dimensions_round_trip_and_jacobian(self):
        geometry = LegGeometry(.1, .12, .14)
        limits = np.radians([[-70, 70], [-20, 60], [5, 110]])
        rng = np.random.default_rng(82)
        for q in rng.uniform(limits[:, 0], limits[:, 1], (60, 3)):
            np.testing.assert_allclose(inverse(forward(q, geometry=geometry), geometry=geometry, limits=limits), q, atol=1e-9)
        q, eps = np.radians([20, 25, 60]), 1e-6
        numeric = np.column_stack([(forward(q + eps * row, geometry=geometry) - forward(q - eps * row, geometry=geometry)) / (2 * eps) for row in np.eye(3)])
        np.testing.assert_allclose(jacobian(q, geometry=geometry), numeric, atol=1e-9)
        mount = {"xyz": [.05, -.02, .03], "yaw": .8}
        np.testing.assert_allclose(inverse_body(foot_in_body(q, mount, geometry=geometry), mount, geometry=geometry, limits=limits), q, atol=1e-9)

    def test_default_and_mapping_geometry_agree(self):
        geometry = {"coxa_m": .082, "femur_m": .09, "tibia_m": .105}
        np.testing.assert_array_equal(forward(NEUTRAL), forward(NEUTRAL, geometry=geometry))

    def test_invalid_dimensions_limits_and_tolerance(self):
        for length in (0, -.1, float("inf"), float("nan"), True, None):
            with self.assertRaises(ValueError):
                LegGeometry(length, .09, .105)
        for limits in ([[0, 1]], [[0, 1], [2, 2], [0, 1]], [[0, 1], [2, 1], [0, 1]], [[0, float("nan")]] * 3):
            with self.assertRaises(ValueError):
                forward(NEUTRAL, limits=limits)
        with self.assertRaises(ValueError):
            validate_angles(NEUTRAL, tolerance=-1)
        limits = np.radians([[-10, 10], [-10, 10], [0, 10]])
        with self.assertRaises(ValueError):
            forward(NEUTRAL, True, limits=limits)
        copy = validate_limits()
        copy[:] = 0
        self.assertGreater(validate_limits()[0, 1], 0)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mist-profile-")
        self.directory = Path(self.temp.name)
        self.baseline = load_profile()
        self.doc = deepcopy(self.baseline.document)
        for entry in self.doc["sources"].values():
            entry["path"] = str((DEFAULT_PROFILE.parent / entry["path"]).resolve())
        self.doc["sources"].pop("config")
        self.path = self.directory / "profile.json"

    def tearDown(self):
        self.temp.cleanup()

    def write_profile(self):
        self.path.write_text(json.dumps(self.doc))
        return self.path

    def modified_source(self, change):
        root = ET.parse(self.doc["sources"]["urdf"]["path"]).getroot()
        change(root)
        destination = self.directory / "source.urdf"
        ET.ElementTree(root).write(destination)
        self.doc["sources"]["urdf"] = {"path": str(destination), "sha256": sha256(destination)}

    def test_baseline_reports_mass_transforms_and_pending_status(self):
        report = self.baseline.report
        self.assertEqual(report["audit_status"], "consistent")
        self.assertEqual(report["calibration_status"], "pending")
        self.assertEqual(report["joints"][1]["xyz_m"], [.082, 0, 0])
        self.assertAlmostEqual(report["source_total_mass_kg"], .4469585695946898)
        self.assertIn("no audited toe frame", report["toe_note"])
        self.assertEqual(compare_profiles(self.baseline, self.baseline)["source_total_mass_delta_kg"], 0)

    def test_mismatch_hash_geometry_limits_and_mass_rejected(self):
        for change, message in ((lambda d: d["sources"]["urdf"].update(sha256="0" * 64), "SHA-256"),
                                (lambda d: d["geometry"].update(coxa_m=.084), "origin"),
                                (lambda d: d["geometry"].update(tibia_m=.11), "manifest lengths"),
                                (lambda d: d["geometry"]["limits_deg"][0].__setitem__(0, -54), "limits"),
                                (lambda d: d["declared_link_masses_kg"].update(coxa=.5), "mass")):
            saved = deepcopy(self.doc)
            change(self.doc)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                load_profile(self.write_profile())
            self.doc = saved

    def test_unsupported_axis_rotation_and_mimic_rejected(self):
        for change, message in ((lambda r: r.find("joint[@name='hip']/axis").set("xyz", "1 0 0"), "axis"),
                                (lambda r: r.find("joint[@name='knee']/origin").set("rpy", "0 0 .1"), "rotation"),
                                (lambda r: ET.SubElement(r.find("joint[@name='knee']"), "mimic", joint="hip"), "mechanism")):
            saved = deepcopy(self.doc)
            self.modified_source(change)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                load_profile(self.write_profile())
            self.doc = saved

    def test_four_bar_extra_actuator_and_broken_chain_rejected(self):
        self.doc["transmission"] = "four_bar"
        with self.assertRaisesRegex(ValueError, "four-bar"):
            load_profile(self.write_profile())
        self.doc["transmission"] = "direct"
        self.modified_source(lambda r: r.find("joint[@name='knee']/parent").set("link", "coxa"))
        with self.assertRaisesRegex(ValueError, "serial"):
            load_profile(self.write_profile())
        saved = deepcopy(self.doc)
        self.modified_source(lambda r: ET.SubElement(r, "joint", name="extra", type="revolute"))
        with self.assertRaisesRegex(ValueError, "exactly"):
            load_profile(self.write_profile())
        self.doc = saved

    def test_fixed_toe_support_and_mismatch(self):
        self.doc["sources"].pop("manifest")
        self.doc["toe_reference"].update(basis="urdf_fixed_joint", joint="toe_fixed")
        def add_toe(root):
            link = ET.SubElement(root, "link", name="toe")
            ET.SubElement(ET.SubElement(link, "inertial"), "mass", value="0")
            joint = ET.SubElement(root, "joint", name="toe_fixed", type="fixed")
            ET.SubElement(joint, "parent", link="tibia")
            ET.SubElement(joint, "child", link="toe")
            ET.SubElement(joint, "origin", xyz=".105 0 0", rpy="0 0 0")
        self.modified_source(add_toe)
        self.doc["declared_link_masses_kg"]["toe"] = 0
        self.doc["sources"]["manifest"] = deepcopy(self.baseline.document["sources"]["manifest"])
        self.doc["sources"]["manifest"]["path"] = str((DEFAULT_PROFILE.parent / self.doc["sources"]["manifest"]["path"]).resolve())
        self.doc["toe_reference"]["basis"] = "cad_manifest_lengths"
        with self.assertRaisesRegex(ValueError, "select and audit"):
            load_profile(self.write_profile())
        self.doc["toe_reference"]["basis"] = "urdf_fixed_joint"
        self.doc["sources"].pop("manifest")
        profile = load_profile(self.write_profile())
        self.assertIn("source URDF", profile.report["toe_note"])
        self.modified_source(lambda r: r.find("joint[@name='toe_fixed']/origin").set("xyz", ".106 0 0"))
        with self.assertRaisesRegex(ValueError, "toe origin"):
            load_profile(self.write_profile())

    def test_other_design_requires_matching_source_and_manifest(self):
        self.doc["profile_id"] = "longer_coxa_analysis"
        self.doc["geometry"]["coxa_m"] = .095
        self.modified_source(lambda r: r.find("joint[@name='hip']/origin").set("xyz", ".095 0 0"))
        manifest = json.loads(Path(self.doc["sources"]["manifest"]["path"]).read_text())
        manifest["lengths_mm"][0] = 95
        manifest_path = self.directory / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))
        self.doc["sources"]["manifest"] = {"path": str(manifest_path), "sha256": sha256(manifest_path)}
        profile = load_profile(self.write_profile())
        self.assertAlmostEqual(compare_profiles(profile, self.baseline)["length_delta_m"]["coxa_m"], .013)
        self.assertIn("model export", profile.report["adaptation_required"])

    def test_measurement_template_pending_and_false_measured_status(self):
        record = measurement_template(self.baseline)
        path = self.directory / "measured.json"
        path.write_text(json.dumps(record))
        report = audit_measurements(path, self.baseline)
        self.assertEqual(report["status"], "pending")
        self.assertTrue(report["missing_fields"])
        self.assertIsNone(report["geometry_delta_m"]["coxa_m"])
        record["status"] = "measured"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "requires all"):
            audit_measurements(path, self.baseline)

    def test_record_complete_provenance_and_evidence_hash(self):
        record = measurement_template(self.baseline)
        record["status"] = "measured"
        values = record["measurements"]
        values.update(geometry_m={"coxa_m": .083, "femur_m": .09, "tibia_m": .105},
                      link_masses_kg=dict(self.baseline.report["source_link_masses_kg"]),
                      actuator={"continuous_torque_nm": .7, "no_load_speed_rad_s": 4.1, "latency_s": .025},
                      joint_zero_offset_rad=[0, .01, -.01], joint_direction=[1, 1, 1], body_com_m=[.001, 0, .04])
        evidence = self.directory / "bench.csv"
        evidence.write_text("sample,torque_nm\n1,0.7\n")
        record["provenance"] = {"measured_at_utc": "2026-10-12T12:00:00Z", "operator": "test operator", "instrument": "load cell and scale", "procedure": "test fixture procedure",
                                "conditions": {"supply_voltage_v": 12, "ambient_temperature_c": 24, "duration_s": 300, "load_description": "loaded test fixture"},
                                "evidence": [{"path": "bench.csv", "sha256": sha256(evidence)}]}
        path = self.directory / "measured.json"
        path.write_text(json.dumps(record))
        report = audit_measurements(path, self.baseline)
        self.assertEqual(report["missing_fields"], [])
        self.assertAlmostEqual(report["geometry_delta_m"]["coxa_m"], .001)
        self.assertAlmostEqual(report["actuator_comparison"]["continuous_torque_nm"]["delta"], .112)
        evidence.write_text("changed evidence")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            audit_measurements(path, self.baseline)

    def test_measurement_record_for_wrong_profile_and_invalid_value_rejected(self):
        record = measurement_template(self.baseline)
        path = self.directory / "measured.json"
        record["profile_sha256"] = "0" * 64
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "profile_sha256"):
            audit_measurements(path, self.baseline)
        record["profile_sha256"] = self.baseline.report["profile_sha256"]
        record["measurements"]["actuator"]["continuous_torque_nm"] = -.1
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "positive"):
            audit_measurements(path, self.baseline)

    def test_cli_audit_and_no_overwrite(self):
        command = [sys.executable, str(HERE / "design_profile.py")]
        result = subprocess.run(command + ["audit", "--baseline", str(DEFAULT_PROFILE)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["baseline_comparison"]["length_delta_m"]["coxa_m"], 0)
        output = self.directory / "pending.json"
        result = subprocess.run(command + ["template", "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        previous = output.read_bytes()
        result = subprocess.run(command + ["template", "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
