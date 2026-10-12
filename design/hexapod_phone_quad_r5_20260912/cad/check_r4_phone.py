"""Read-only verification of the frozen R4 phone against its full assembly."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import unittest

import build
import check_phone_pan_samples as pan_samples
import geom as g
import phone
import servo_contract as hardware
from test_phone_geometry import PhoneGeometry, solids

CAD = Path(__file__).resolve().parent
OUT = CAD / "output"
EXPECTED_MANIFEST = "6cac852c196e29e2da100816a7d3b96f545e62dba92c3009a46417eb7d9bc449"
MEASUREMENTS = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R4Phone(PhoneGeometry):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.full_parts, cls.poses, cls.joints = build.load_assembly()
        cls.parts = [p for p in cls.full_parts
                     if p["name"].startswith("phone_") or p["material"] == "phone"]
        cls.coupons = phone.build_coupons()
        cls.world = [(p, build.shape_at(p["shape"], cls.poses[p["link"]]))
                     for p in cls.full_parts if not p.get("allowance_only")]
        cls.world_bounds = [(p, shape, g.bounds(shape)) for p, shape in cls.world]

    def test_parts_are_valid_connected_solids(self):
        for part in self.parts + self.coupons:
            with self.subTest(part=part["name"]):
                self.assertTrue(g.valid(part["shape"]))
                self.assertGreater(g.volume(part["shape"]), 0)
                expected = 2 if part["material"] == "servo" else 1
                self.assertEqual(solids(part["shape"]), expected)

    def test_frozen_phone_bounds_and_profile(self):
        self.assertEqual((phone.PHONE_WIDTH, phone.PHONE_HEIGHT, phone.PHONE_THICKNESS),
                         (147.5, 70.5, 7.45))
        self.assertAlmostEqual(phone.CASE_X[0], -35.115)
        self.assertAlmostEqual(phone.CASE_X[1], 10.115)
        self.assertEqual(hardware.REFERENCE_REAR_PROFILE_Z, -32.4)
        self.assertAlmostEqual(hardware.PORT_CLEARANCE_OUTER_Z + phone.PAN_Z, 62.1)
        low, high = g.bounds(phone.servo_exterior())
        self.assertAlmostEqual(low[0], -35.115, delta=.005)
        self.assertAlmostEqual(high[0], 10.115, delta=.005)
        self.assertAlmostEqual(low[2], 64.9, delta=.001)
        self.assertAlmostEqual(high[2], 101.4, delta=.001)
        device = next(p for p in self.parts if p["material"] == "phone")
        MEASUREMENTS["phone_local_bounds_mm"] = g.bounds(device["shape"])
        MEASUREMENTS["servo_world_bounds_mm"] = [low, high]
        MEASUREMENTS["provisional_plug_clearance_low_z_mm"] = 62.1

    def test_supplier_shoulder_support_and_axial_stops(self):
        saddle, cap = phone._fixed_clamp()
        servo = phone.servo_exterior()
        up = g.common_volume(g.translate(servo, (0, 0, .3)), cap["shape"])
        down = g.common_volume(g.translate(servo, (0, 0, -.3)), saddle["shape"])
        self.assertGreater(up, 5)
        self.assertGreater(down, 5)
        coverage = []
        for sign in (-1, 1):
            for z0 in (69.001, 97.901):
                patch = g.box(10, 1, .099, center=(0, sign * 11.15, z0 + .0495))
                fraction = g.common_volume(servo, patch) / g.volume(patch)
                self.assertGreater(fraction, .9)
                coverage.append(fraction)
        MEASUREMENTS["shoulder_support"] = {
            "lower_z_mm": 69, "upper_lip_z_mm": [98, 100.5],
            "sample_material_coverage": coverage,
            "upward_0p3mm_contact_volume_mm3": up,
            "downward_0p3mm_contact_volume_mm3": down,
        }

    def test_actual_cover_passage_and_pdb_rotation(self):
        route = phone.pan_port_passage(50, 69.1)
        reserve = g.translate(hardware.plugged_profile_reserve(), (0, 0, phone.PAN_Z))
        checked = []
        for part, shape in self.world:
            if part["link"] != "base" or part["name"] == "phone_pan_STS3215_envelope":
                continue
            for region in (route, reserve):
                if pan_samples._aabb_overlaps(g.bounds(shape), g.bounds(region)):
                    self.assertLess(g.common_volume(shape, region), .001, part["name"])
            checked.append(part["name"])
        self.assertIn("hex_faceted_cover", checked)
        pdb = next(shape for part, shape in self.world if part["name"] == "power_distribution_envelope")
        lo, hi = g.bounds(pdb)
        self.assertAlmostEqual(hi[0] - lo[0], 45 * math.sqrt(2), places=5)
        self.assertAlmostEqual(hi[1] - lo[1], 45 * math.sqrt(2), places=5)
        MEASUREMENTS["actual_cover_route"] = {
            "bounds_mm": g.bounds(route), "base_parts_checked": len(checked),
            "pdb_world_bounds_mm": [lo, hi], "pdb_rotation_deg": 45,
        }

    def test_full_nominal_hardware_static(self):
        result = build.overlaps(self.full_parts, self.poses)
        MEASUREMENTS["full_nominal_static"] = result
        self.assertEqual(result["positive_intersections"], [])

    def test_full_assembly_24_pan_angles(self):
        original = pan_samples.ANGLES_DEG
        try:
            pan_samples.ANGLES_DEG = tuple(range(0, 360, 15))
            result = pan_samples.run_phone_samples(self.cfg, self.full_parts, self.poses)
        finally:
            pan_samples.ANGLES_DEG = original
        MEASUREMENTS["full_assembly_pan"] = {
            key: result[key] for key in (
                "status", "angles_deg", "sample_count", "moving_part_count",
                "stationary_part_count", "candidate_boolean_pair_count", "failures", "thresholds")
        }
        self.assertEqual(result["failures"], [])

    def test_assembly_order_driver_access(self):
        checks = []

        def clear(tool, description, include):
            tool_box = g.bounds(tool)
            for part, shape, shape_box in self.world_bounds:
                if not include(part) or not pan_samples._aabb_overlaps(tool_box, shape_box):
                    continue
                self.assertLess(g.common_volume(shape, tool), .001,
                                description + ": " + part["name"])
            checks.append(description)

        # Fasten the fixed case first, then its horn and hub, then the cradle.
        before_hub = lambda p: p["link"] != "phone_pan"
        before_cradle = lambda p: not p["name"].startswith("phone_cradle_") and p["material"] != "phone"
        for x, y in phone.MOUNT_XY:
            clear(g.cylinder(3, 70, base=(x, y, 70.001)),
                  f"Body fixing before hub at {x},{y}", before_hub)
        for x, y in ((-25, -19), (-25, 19), (5, -19), (5, 19)):
            clear(g.cylinder(3, 60, base=(x, y, 90.801)),
                  f"Pan cap before hub at {x},{y}", before_hub)
        for x, y in ((7, 0), (-7, 0), (0, 7), (0, -7)):
            clear(g.cylinder(3, 55, base=(x, y, phone.PAN_Z + 8.001)),
                  f"Main horn at {x},{y}", before_cradle)
        without_phone = lambda p: p["material"] != "phone"
        for x, y in phone.HUB_BOLT_XY:
            clear(g.cylinder(3, 115, base=(x, y, phone.PAN_Z + 13.501)),
                  f"Cradle foot at {x},{y}", without_phone)
        for y in (-24, 24):
            for z in (24, 34):
                clear(g.cylinder(3, 49.499, base=(-60, y, phone.PAN_Z + z), axis=(1, 0, 0)),
                      f"Rear frame at {y},{z}", without_phone)
        for y in (-78.25, 78.25):
            for z in (25.5, 92.5):
                clear(g.cylinder(3, 45, base=(11.001, y, phone.PAN_Z + z), axis=(1, 0, 0)),
                      f"Phone corner at {y},{z}", lambda p: True)
        MEASUREMENTS["driver_access"] = {
            "diameter_mm": 6, "checked_paths": checks,
            "assembly_order": "Tighten body and case-cap screws before installing the horn and hub, then attach the cradle, insert the phone and close its clips",
        }


def main():
    manifest_path = OUT / "assembly_manifest.json"
    if sha(manifest_path) != EXPECTED_MANIFEST:
        raise RuntimeError("The production manifest differs from the requested frozen R4")
    manifest = json.loads(manifest_path.read_text())
    inputs = {str(CAD / name): digest for name, digest in manifest["source_hashes"].items()}
    inputs[str(CAD.parent / "settings.json")] = sha(CAD.parent / "settings.json")
    inputs[str(manifest_path)] = EXPECTED_MANIFEST
    inputs[str(Path(__file__))] = sha(Path(__file__))
    inputs[str(CAD / "test_phone_geometry.py")] = sha(CAD / "test_phone_geometry.py")
    inputs[str(CAD / "check_phone_pan_samples.py")] = sha(CAD / "check_phone_pan_samples.py")
    if not all(sha(path) == digest for path, digest in inputs.items()):
        raise RuntimeError("A source file does not match the frozen R4 manifest")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(R4Phone)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    unchanged = all(sha(path) == digest for path, digest in inputs.items())
    report = {
        "status": "pass" if result.wasSuccessful() and unchanged else "fail",
        "revision": manifest["revision"], "manifest_sha256": EXPECTED_MANIFEST,
        "tests_run": result.testsRun, "inputs_unchanged": unchanged,
        "input_hashes": inputs, "measurements": MEASUREMENTS,
        "failures": [(str(test), error) for test, error in result.failures + result.errors],
        "mesh_report": "r4_phone_mesh_check.json",
        "limitations": [
            "The 24 pan samples do not prove clearance at every intermediate angle.",
            "Plug projection and flexible-wire clearance still use the explicitly provisional measured-profile mapping.",
            "Geometry contact and tool-access checks do not establish physical fit, clamp strength or loaded walking.",
        ],
    }
    (OUT / "r4_phone_check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    text = [f"R4 phone verification: {report['status'].upper()}",
            f"Manifest SHA256: {EXPECTED_MANIFEST}",
            f"Tests run: {result.testsRun}. Inputs unchanged: {unchanged}.",
            "Bare landscape phone: 147.5 mm across, 70.5 mm upright, 7.45 mm thick.",
            "Current production body cover and 45 degree PDB arrangement are included.",
            "The full assembly is checked at 24 pan angles, with all other links at the frozen nominal pose.",
            "Tool checks use a 6 mm diameter driver and the stated assembly order.",
            "Independent exported mesh details are in r4_phone_mesh_check.json and its text companion."]
    if "full_nominal_static" in MEASUREMENTS:
        static = MEASUREMENTS["full_nominal_static"]
        text.append(f"Full nominal static: {static['boolean_pairs']} Boolean pairs, {len(static['positive_intersections'])} intersections.")
    if "full_assembly_pan" in MEASUREMENTS:
        pan = MEASUREMENTS["full_assembly_pan"]
        text.append(f"Full pan sweep: {pan['candidate_boolean_pair_count']} Boolean pairs, {len(pan['failures'])} intersections.")
    text.extend(report["limitations"])
    if report["failures"]:
        text.extend(["Failures:"] + [name + "\n" + error for name, error in report["failures"]])
    (OUT / "r4_phone_check.txt").write_text("\n".join(text) + "\n", encoding="utf-8")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
