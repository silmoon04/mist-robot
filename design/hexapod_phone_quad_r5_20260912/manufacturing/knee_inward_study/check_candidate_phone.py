"""Validate the isolated corrected-C018 phone candidate without production edits."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import trimesh

STUDY = Path(__file__).resolve().parent
CAD = STUDY.parents[1] / "cad"
sys.path.insert(0, str(CAD))
sys.path.insert(0, str(STUDY))

import candidate_phone as phone
import geom as g
import servo_contract as hardware
from test_phone_geometry import PhoneGeometry, solids


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CorrectedPhone(PhoneGeometry):
    @classmethod
    def setUpClass(cls):
        cls.parts = phone.build_phone()
        cls.coupons = phone.build_coupons()

    def test_parts_are_valid_connected_solids(self):
        for part in self.parts + self.coupons:
            with self.subTest(part=part["name"]):
                self.assertTrue(g.valid(part["shape"]))
                self.assertGreater(g.volume(part["shape"]), 0)
                if part["printable"]:
                    self.assertEqual(solids(part["shape"]), 1)
                elif part["material"] == "servo":
                    # The case and output shaft are separate physical solids.
                    self.assertEqual(solids(part["shape"]), 2)
                else:
                    self.assertEqual(solids(part["shape"]), 1)

    def test_corrected_case_dimensions_and_shared_datum(self):
        self.assertAlmostEqual(phone.CASE_X[0], -35.115)
        self.assertAlmostEqual(phone.CASE_X[1], 10.115)
        self.assertEqual(phone.PAN_Z, 98)
        low, high = g.bounds(phone.servo_exterior())
        self.assertAlmostEqual(low[0], -35.115, delta=.005)
        self.assertAlmostEqual(high[0], 10.115, delta=.005)
        self.assertAlmostEqual(high[1] - low[1], 24.73, delta=.01)
        self.assertAlmostEqual(low[2], 64.9, delta=.001)
        self.assertAlmostEqual(high[2], 101.4, delta=.001)
        servo = next(p for p in self.parts if p["material"] == "servo")
        self.assertEqual(servo["mass_kg"], .055)

    def test_three_mm_outer_walls(self):
        saddle, cap = phone._fixed_clamp()
        for part, z in ((saddle, 80), (cap, 94)):
            regions = [
                g.box(3, 4, 1, center=(-37.065, 0, z)),
                g.box(3, 4, 1, center=(12.065, 0, z)),
                g.box(4, 3, 1, center=(-30, -14.315, z)),
                g.box(4, 3, 1, center=(-30, 14.315, z)),
            ]
            for region in regions:
                self.assertAlmostEqual(g.common_volume(part["shape"], region), 12, places=5)

    def test_supplier_shoulders_react_both_axial_directions(self):
        saddle, cap = phone._fixed_clamp()
        servo = phone.servo_exterior()
        self.assertGreater(g.common_volume(g.translate(servo, (0, 0, .3)), cap["shape"]), 5)
        self.assertGreater(g.common_volume(g.translate(servo, (0, 0, -.3)), saddle["shape"]), 5)
        for sign in (-1, 1):
            for z0 in (69.001, 97.901):
                patch = g.box(10, 1, .099, center=(0, sign * 11.15, z0 + .0495))
                self.assertGreater(g.common_volume(servo, patch) / g.volume(patch), .9)

    def test_downward_port_passage_and_cover_contract(self):
        saddle, cap = phone._fixed_clamp()
        route = phone.pan_port_passage(60, 69.1)
        reserve = g.translate(hardware.plugged_profile_reserve(), (0, 0, phone.PAN_Z))
        for part in (saddle, cap):
            self.assertLess(g.common_volume(part["shape"], route), .001)
            self.assertLess(g.common_volume(part["shape"], reserve), .001)
        # This witness plate checks the specified opening, not the production cover.
        cover_witness = g.box(100, 80, 2, center=(0, 0, 61))
        self.assertGreater(g.common_volume(cover_witness, route), 100)
        opened = g.cut(cover_witness, route)
        self.assertLess(g.common_volume(opened, route), .001)

    def test_printable_candidate_meshes(self):
        with tempfile.TemporaryDirectory(prefix="corrected_c018_pan_") as temp:
            for part in self.parts + self.coupons:
                if not part["printable"]:
                    continue
                path = g.export_stl(part["shape"], Path(temp) / (part["name"] + ".stl"))
                mesh = trimesh.load_mesh(path, process=True)
                with self.subTest(part=part["name"]):
                    self.assertTrue(mesh.is_watertight)
                    self.assertTrue(mesh.is_winding_consistent)
                    self.assertGreater(mesh.volume, 0)


def main():
    protected = {str(p): sha(p) for p in (CAD / "phone.py", CAD / "body.py", CAD / "leg.py")}
    study_sources = {p.name: sha(p) for p in (STUDY / "candidate_phone.py", STUDY / "servo_contract.py", Path(__file__))}
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CorrectedPhone)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "status": "pass" if result.wasSuccessful() else "fail",
        "scope": "Isolated corrected-C018 pan candidate; production geometry unchanged",
        "tests_run": result.testsRun,
        "failures": [(str(test), error) for test, error in result.failures + result.errors],
        "source_hashes": study_sources,
        "study_sources_unchanged": all(sha(STUDY / name) == digest for name, digest in study_sources.items()),
        "supplier_step_sha256": sha(STUDY / "ST3215-3D_supplier" / "ST3215.step"),
        "production_unchanged": all(sha(Path(path)) == digest for path, digest in protected.items()),
        "production_source_hashes": protected,
        "case_x_mm": list(phone.CASE_X),
        "pan_origin_mm": [0, 0, phone.PAN_Z],
        "lower_shoulder_z_mm": 69,
        "upper_lip_z_mm": [98, 100.5],
        "minimum_wall_mm": 3.05,
        "cover_window_x_mm": list(phone.PAN_PORT_WINDOW_X),
        "cover_window_y_mm": list(phone.PAN_PORT_WINDOW_Y),
        "cable_limit": "Shell aperture plus allowance, not measured plug dimensions or a complete insertion proof",
    }
    (STUDY / "candidate_phone_check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not result.wasSuccessful() or not report["production_unchanged"] or not report["study_sources_unchanged"]:
        return 1
    out = STUDY / "candidate_phone_output"
    parts = phone.build_phone()
    g.export_step([g.translate(p["shape"], (0, 0, phone.PAN_Z)) if p["link"] == "phone_pan" else p["shape"]
                   for p in parts], out / "corrected_C018_phone_candidate.step")
    for part in parts:
        if part["printable"]:
            oriented = g.transform(part["shape"], rpy_deg=part["print_rotation"])
            low, high = g.bounds(oriented)
            g.export_stl(g.translate(oriented, tuple(-v for v in low)), out / "print_stl" / (part["name"] + ".stl"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
