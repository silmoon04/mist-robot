"""Check refinement provenance and coupon geometry using temporary feedback."""

from __future__ import annotations

import contextlib
import copy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

import build_refined_bed as builder
import refine_from_feedback as gate


def measured(interface="bearing_OD22", nominal=22, cad=22.4, **overrides):
    row = {
        "feature_id": f"synthetic_{interface}",
        "interface": interface,
        "nominal_mm": str(nominal),
        "cad_mm": str(cad),
        "measured_part_mm": str(cad - 0.3),
        "measured_hardware_mm": str(nominal),
        "fit_result": "slip",
        "print_material": "PETG",
        "layer_mm": "0.20",
        "wall_count": "4",
        "xy_compensation_mm": "0",
        "notes": "Synthetic test data; never use for a production part.",
    }
    row.update(overrides)
    return row


def feedback(*rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=gate.FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def add_bounds(op):
    """Bounds of added stock, independent of the CAD kernel."""
    if op["kind"] == "box":
        low = [op["x"], op["y"], op["z"]]
        high = [low[i] + op[key] for i, key in enumerate(("sx", "sy", "sz"))]
    elif op["kind"] in ("cylinder", "cone"):
        radius = max(op["diameter"], op.get("bottom_diameter", 0)) / 2
        low = [op["x"] - radius, op["y"] - radius, op["z"]]
        high = [op["x"] + radius, op["y"] + radius, op["z"] + op["height"]]
    elif op["kind"] == "polygon":
        low = [min(p[0] for p in op["points"]), min(p[1] for p in op["points"]), op["z"]]
        high = [max(p[0] for p in op["points"]), max(p[1] for p in op["points"]), op["z"] + op["height"]]
    else:
        raise AssertionError(f"Unknown stock geometry: {op['kind']}")
    return low, high


class RefinedBedTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "synthetic_feedback.csv"
        self.request_path = self.directory / "request.json"
        self.output = self.directory / "synthetic_bed2"

    def write_request(self, *rows):
        self.source.write_bytes(feedback(*(rows or [measured()])))
        request = gate.make_request(self.source.read_bytes(), str(self.source.resolve()))
        self.write_json(request)
        return request

    def write_json(self, request):
        self.request_path.write_text(json.dumps(request, indent=2), encoding="utf-8")

    def assert_cli_refuses_without_output(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = builder.main([str(self.request_path), "--out", str(self.output)])
        self.assertEqual(result, 2, stderr.getvalue())
        self.assertFalse(self.output.exists())
        self.assertTrue(stderr.getvalue().strip())

    def test_valid_source_request_loads_without_changing_measurements(self):
        request = self.write_request(measured(measured_part_mm="22.0812345"))
        loaded = builder.load_validated_request(self.request_path)
        self.assertEqual(loaded, request)
        self.assertEqual(loaded["interface_requests"][0]["basis"]["measured_part_mm"], 22.0812345)
        self.assertEqual(loaded["source"]["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_timestamp_is_the_only_ignored_recomputed_field(self):
        request = self.write_request()
        request["generated_at_utc"] = "2026-09-06T00:00:00+00:00"
        self.write_json(request)
        self.assertEqual(builder.load_validated_request(self.request_path), request)

    def test_tampered_metadata_candidates_and_measurements_are_rejected(self):
        original = self.write_request()
        mutations = [
            lambda r: r.update(schema_version=2),
            lambda r: r.update(schema_version=True),
            lambda r: r.update(purpose="production_leg"),
            lambda r: r.update(status="approved"),
            lambda r: r.update(production_release=True),
            lambda r: r.update(production_release=0),
            lambda r: r.update(measurement_rows_used=9),
            lambda r: r.update(measurement_rows_used=True),
            lambda r: r["source"].update(sha256="0" * 64),
            lambda r: r["rules"].update(error_model="unmeasured global correction"),
            lambda r: r["interface_requests"][0].update(candidate_cad_mm=[22.2, 22.25, 22.3]),
            lambda r: r["interface_requests"][0]["print_profile"].update(wall_count=4.0),
            lambda r: r["interface_requests"][0]["basis"].update(measured_part_mm=22.3),
            lambda r: r["interface_requests"][0]["feedback"][0].update(measured_part_mm=22.3),
            lambda r: r.update(extra_unverified_parameter=1),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                changed = copy.deepcopy(original)
                mutate(changed)
                self.write_json(changed)
                with self.assertRaises(ValueError):
                    builder.load_validated_request(self.request_path)
                self.assert_cli_refuses_without_output()

    def test_changed_source_and_rehashed_changed_source_are_rejected(self):
        request = self.write_request()
        self.source.write_bytes(feedback(measured(measured_part_mm="22.3")))
        with self.assertRaises(ValueError):
            builder.load_validated_request(self.request_path)
        self.assert_cli_refuses_without_output()
        request["source"]["sha256"] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.write_json(request)
        with self.assertRaises(ValueError):
            builder.load_validated_request(self.request_path)
        self.assert_cli_refuses_without_output()

    def test_empty_or_unmeasured_source_cannot_be_used_even_with_matching_hash(self):
        for content in (b"", feedback(), feedback(measured(fit_result="not_tested"))):
            with self.subTest(content=content):
                request = self.write_request()
                self.source.write_bytes(content)
                request["source"]["sha256"] = hashlib.sha256(content).hexdigest()
                self.write_json(request)
                with self.assertRaises(ValueError):
                    builder.load_validated_request(self.request_path)
                self.assert_cli_refuses_without_output()

    def test_missing_source_and_relative_source_path_cannot_create_output(self):
        request = self.write_request()
        request["source"]["path"] = "synthetic_feedback.csv"
        self.write_json(request)
        with self.assertRaises(ValueError):
            builder.load_validated_request(self.request_path)
        self.assert_cli_refuses_without_output()
        self.write_request()
        self.source.unlink()
        self.assert_cli_refuses_without_output()

    def test_invalid_json_and_invalid_top_level_cannot_create_output(self):
        for text in ("{", "null", "[]", "{}"):
            with self.subTest(text=text):
                self.request_path.write_text(text, encoding="utf-8")
                self.assert_cli_refuses_without_output()

    def test_clamp_requires_review_before_geometry(self):
        self.write_request(measured("clamp_ID8", 8, 8.3))
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = builder.main([str(self.request_path), "--out", str(self.output)])
        self.assertEqual(result, 2)
        self.assertFalse(self.output.exists())
        self.assertIn("review", stderr.getvalue().lower())

    def test_unsupported_interfaces_and_more_than_three_groups_are_rejected(self):
        cases = [
            [measured("bearing_OD99", 99, 99.4)],
            [measured("shaft_clearance_ID9", 9, 9.3)],
            [measured("bolt_clearance_M5", 5, 5.4)],
            [measured("bearing_OD8", 8, 8.4), measured("bearing_OD10", 10, 10.4),
             measured("bearing_OD11", 11, 11.4), measured("bearing_OD13", 13, 13.4)],
        ]
        for rows in cases:
            with self.subTest(interfaces=[row["interface"] for row in rows]):
                self.write_request(*rows)
                self.assert_cli_refuses_without_output()

    def test_different_print_profiles_cannot_share_one_bed(self):
        self.write_request(measured(), measured("shaft_clearance_ID8", 8, 8.3, print_material="PLA"))
        self.assert_cli_refuses_without_output()

    def test_existing_output_is_preserved(self):
        self.write_request()
        self.output.mkdir()
        existing = self.output / "preserve.txt"
        existing.write_bytes(b"prior output")
        with contextlib.redirect_stderr(io.StringIO()):
            result = builder.main([str(self.request_path), "--out", str(self.output)])
        self.assertEqual(result, 2)
        self.assertEqual(existing.read_bytes(), b"prior output")
        self.assertEqual(list(self.output.iterdir()), [existing])

    def test_every_supported_bearing_retains_full_seat_geometry(self):
        for od, width in ((8, 4), (10, 4), (11, 5), (13, 5), (14, 5), (19, 6), (22, 7)):
            with self.subTest(outer_diameter=od):
                request = self.write_request(measured(f"bearing_OD{od}", od, od + 0.4))
                recipe = builder.make_refined_recipe(builder.load_validated_request(self.request_path))
                self.assertFalse(recipe["production_release"])
                self.assertEqual(recipe["purpose"], "second_fit_bed")
                self.assertEqual(recipe["units"], "mm")
                self.assertEqual(len(recipe["features"]), 3)
                self.assertEqual([f["cad_mm"] for f in recipe["features"]],
                                 request["interface_requests"][0]["candidate_cad_mm"])
                parts = {part["name"]: part for part in recipe["parts"]}
                for feature in recipe["features"]:
                    self.assertEqual(feature["bearing_width_mm"], width)
                    self.assertEqual(feature["boss_outer_mm"], od + 8)
                    self.assertAlmostEqual(feature["seat_depth_mm"], width + 0.2)
                    self.assertEqual(feature["floor_mm"], 1.2)
                    self.assertEqual(feature["print_axis"], "Z")
                    self.assertEqual(feature["source_feature_id"], f"synthetic_bearing_OD{od}")
                    self.assertEqual(feature["source_row"], 2)
                    ops = parts[feature["part"]]["ops"]
                    stock = [o for o in ops if o["op"] == "add" and o["kind"] == "cylinder"
                             and math.isclose(o["x"], feature["x_mm"])
                             and math.isclose(o["y"], feature["y_mm"])]
                    self.assertTrue(any(math.isclose(o["diameter"], od + 8)
                                        and math.isclose(o["height"], width + 1.4) for o in stock))
                    seats = [o for o in ops if o["op"] == "cut" and o["kind"] == "cylinder"
                             and math.isclose(o["x"], feature["x_mm"])
                             and math.isclose(o["y"], feature["y_mm"])
                             and math.isclose(o["diameter"], feature["cad_mm"])]
                    self.assertTrue(any(math.isclose(o["z"], 1.2) and o["height"] >= width + 0.2
                                        for o in seats))

    def test_shaft_bolt_and_wire_coupons_keep_the_original_wall_depth(self):
        cases = [(f"shaft_clearance_ID{size}", size, size + 0.3, 2) for size in range(3, 9)]
        cases += [("bolt_clearance_M3", 3, 3.4, 4), ("bolt_clearance_M4", 4, 4.4, 4),
                  ("wire_slot", 6, 6.2, 2)]
        for interface, nominal, cad, thickness in cases:
            with self.subTest(interface=interface):
                request = self.write_request(measured(interface, nominal, cad))
                recipe = builder.make_refined_recipe(request)
                ops = recipe["parts"][0]["ops"]
                stock = [op for op in ops if op["op"] == "add"]
                self.assertEqual(len(stock), 1)
                self.assertEqual(stock[0]["sz"], thickness)
                self.assertEqual([f["cad_mm"] for f in recipe["features"]],
                                 request["interface_requests"][0]["candidate_cad_mm"])
                for feature in recipe["features"]:
                    self.assertEqual(feature["print_axis"], "Z")
                    self.assertEqual(feature["wall_depth_mm"], thickness)
                    if interface == "wire_slot":
                        cuts = [o for o in ops if o["op"] == "cut" and o["kind"] == "box"
                                and math.isclose(o["sx"], feature["cad_mm"])
                                and math.isclose(o["x"] + o["sx"] / 2, feature["x_mm"])]
                        self.assertTrue(any(o["z"] < 0 and o["sz"] > thickness and o["sy"] == 7
                                            for o in cuts))
                    else:
                        cuts = [o for o in ops if o["op"] == "cut" and o["kind"] == "cylinder"
                                and math.isclose(o["x"], feature["x_mm"])
                                and math.isclose(o["diameter"], feature["cad_mm"])]
                        self.assertTrue(any(o["z"] < 0 and o["height"] > thickness for o in cuts))

    def test_nut_and_insert_coupons_keep_full_pockets_and_blind_floors(self):
        cases = [("nut_trap_M3", 5.5, 5.8, 6, 2.8), ("nut_trap_M4", 7, 7.3, 6, 3.6),
                 ("heat_insert_M3", 4.6, 4.8, 8, 6), ("heat_insert_M4", 5.6, 5.8, 10, 8)]
        for interface, nominal, cad, height, depth in cases:
            with self.subTest(interface=interface):
                request = self.write_request(measured(interface, nominal, cad,
                                                      measured_part_mm=str(nominal)))
                recipe = builder.make_refined_recipe(request)
                ops = recipe["parts"][0]["ops"]
                for feature in recipe["features"]:
                    self.assertEqual(feature["print_axis"], "Z")
                    if interface.startswith("nut"):
                        self.assertEqual(feature["plate_height_mm"], height)
                        self.assertEqual(feature["pocket_depth_mm"], depth)
                        self.assertTrue(any(o["op"] == "add" and o["kind"] == "box"
                                            and o["sz"] == height for o in ops))
                        pockets = [o for o in ops if o["op"] == "cut" and o["kind"] == "polygon"
                                   and math.isclose(sum(p[0] for p in o["points"]) / 6, feature["x_mm"])]
                        self.assertEqual(len(pockets), 1)
                        pocket = pockets[0]
                        self.assertAlmostEqual(pocket["z"], height - depth)
                        self.assertGreaterEqual(pocket["height"], depth)
                        self.assertAlmostEqual(max(p[0] for p in pocket["points"])
                                               - min(p[0] for p in pocket["points"]), feature["cad_mm"])
                    else:
                        self.assertEqual(feature["boss_height_mm"], height)
                        self.assertEqual(feature["boss_outer_mm"], 10)
                        self.assertEqual(feature["hole_depth_mm"], depth)
                        self.assertIsNone(feature["hardware_length_mm"])
                        self.assertIn("Heat insertion and pull-out", feature["validation_pending"])
                        cylinders = [o for o in ops if o["kind"] == "cylinder"
                                     and math.isclose(o["x"], feature["x_mm"])
                                     and math.isclose(o["y"], feature["y_mm"])]
                        self.assertTrue(any(o["op"] == "add" and o["diameter"] == 10
                                            and o["height"] == height for o in cylinders))
                        self.assertTrue(any(o["op"] == "cut" and math.isclose(o["diameter"], feature["cad_mm"])
                                            and math.isclose(o["z"], height - depth)
                                            and o["height"] >= depth for o in cylinders))

    def test_servo_width_gauges_retain_eight_mm_height_and_three_mm_walls(self):
        request = self.write_request(measured("servo_body_width", 25.23, 25.43))
        recipe = builder.make_refined_recipe(request)
        walls = [o for o in recipe["parts"][0]["ops"]
                 if o["op"] == "add" and o["kind"] == "box" and o["sx"] == 3 and o["sy"] == 20]
        self.assertEqual(len(walls), 6)
        self.assertTrue(all(o["z"] == 0 and o["sz"] == 8 for o in walls))
        for feature in recipe["features"]:
            self.assertEqual(feature["gauge_height_mm"], 8)
            self.assertEqual(feature["wall_mm"], 3)
            left = feature["x_mm"] - feature["cad_mm"] / 2 - 3
            right = feature["x_mm"] + feature["cad_mm"] / 2
            self.assertTrue(any(math.isclose(o["x"], left) for o in walls))
            self.assertTrue(any(math.isclose(o["x"], right) for o in walls))

    def test_three_group_recipe_stays_on_bed_and_keeps_individual_candidates(self):
        request = self.write_request(measured(), measured("servo_body_width", 25.23, 25.43),
                                     measured("heat_insert_M3", 4.6, 4.8,
                                              measured_part_mm="4.6", measured_hardware_mm="4.6"))
        recipe = builder.make_refined_recipe(builder.load_validated_request(self.request_path))
        self.assertEqual(recipe["bed_limit_mm"], [210, 210])
        self.assertEqual(len(recipe["features"]), 9)
        for group in request["interface_requests"]:
            actual = [f["cad_mm"] for f in recipe["features"] if f["interface"] == group["interface"]]
            self.assertEqual(actual, group["candidate_cad_mm"])
        for part in recipe["parts"]:
            for op in part["ops"]:
                if op["op"] != "add":
                    continue
                low, high = add_bounds(op)
                self.assertTrue(all(math.isfinite(v) for v in low + high))
                self.assertGreaterEqual(min(low), -1e-6)
                self.assertLessEqual(high[0], 210 + 1e-6)
                self.assertLessEqual(high[1], 210 + 1e-6)
        placements = recipe["placements"]
        for index, first in enumerate(placements):
            self.assertGreater(first["width_mm"], 0)
            self.assertGreater(first["height_mm"], 0)
            self.assertLessEqual(first["x_mm"] + first["width_mm"], 210 + 1e-6)
            self.assertLessEqual(first["y_mm"] + first["height_mm"], 210 + 1e-6)
            for second in placements[:index]:
                overlaps_x = min(first["x_mm"] + first["width_mm"], second["x_mm"] + second["width_mm"]) > max(first["x_mm"], second["x_mm"])
                overlaps_y = min(first["y_mm"] + first["height_mm"], second["y_mm"] + second["height_mm"]) > max(first["y_mm"], second["y_mm"])
                self.assertFalse(overlaps_x and overlaps_y)

    @unittest.skipUnless(os.environ.get("MIST_RUN_CAD_TESTS") == "1", "CAD integration is opt-in")
    def test_cad_export_for_three_groups_is_valid_and_physical_feedback_stays_blank(self):
        self.write_request(measured(), measured("servo_body_width", 25.23, 25.43),
                           measured("heat_insert_M3", 4.6, 4.8, measured_part_mm="4.6"))
        root = Path(__file__).resolve().parent
        python = Path(os.environ.get("MIST_CAD_PYTHON", str(root / ".venv_stable" / "Scripts" / "python.exe")))
        self.assertTrue(python.is_file(), f"CAD interpreter is missing: {python}")
        result = subprocess.run([str(python), str(root / "build_refined_bed.py"), str(self.request_path),
                                 "--out", str(self.output)], cwd=root, capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ("MIST_BED2_ALL_PARTS.step", "MIST_BED2_ALL_PARTS.stl", "MIST_BED2_ALL_PARTS.3mf",
                     "coupon_recipe.json", "feature_manifest.json", "feedback_BED2.csv", "validation.json"):
            self.assertGreater((self.output / name).stat().st_size, 0, name)
        validation = json.loads((self.output / "validation.json").read_text(encoding="utf-8"))
        self.assertEqual(validation["status"], "geometry_checks_passed_physical_fit_pending")
        self.assertIs(validation["production_release"], False)
        self.assertEqual(validation["part_count"], 3)
        self.assertEqual(validation["feature_count"], 9)
        self.assertEqual(validation["request_sha256"], hashlib.sha256(self.request_path.read_bytes()).hexdigest())
        low, high = validation["bounds_mm"]
        self.assertGreaterEqual(min(low), -1e-5)
        self.assertLessEqual(max(high[:2]), 210)
        self.assertEqual(len(validation["checks"]), 3)
        for check in validation["checks"]:
            self.assertTrue(check["brep_valid"])
            self.assertEqual(check["solid_count"], 1)
            self.assertTrue(check["watertight"])
            self.assertTrue(check["winding_consistent"])
            self.assertGreater(check["volume_mm3"], 0)
            self.assertGreater(check["triangles"], 0)
            self.assertGreater((self.output / f"{check['part']}.stl").stat().st_size, 84)
        with zipfile.ZipFile(self.output / "MIST_BED2_ALL_PARTS.3mf") as archive:
            self.assertIsNone(archive.testzip())
            model = ET.fromstring(archive.read("3D/3dmodel.model"))
            self.assertEqual(model.attrib["unit"], "millimeter")
            self.assertEqual(len(model.findall(".//{*}object")), 3)
            self.assertEqual(len(model.findall(".//{*}item")), 3)
        with (self.output / "feedback_BED2.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(row["fit_result"] == "not_tested" for row in rows))
        self.assertTrue(all(not row["measured_part_mm"] and not row["measured_hardware_mm"] for row in rows))


if __name__ == "__main__":
    unittest.main()
