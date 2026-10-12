"""Run with: python -m unittest test_refine_from_feedback -v"""

import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest

import refine_from_feedback as gate


def feedback(*rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=gate.FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def measured(**overrides):
    row = {
        "feature_id": "bearing_OD22_040", "interface": "bearing_OD22",
        "nominal_mm": "22", "cad_mm": "22.40", "measured_part_mm": "22.08",
        "measured_hardware_mm": "21.99", "fit_result": "slip",
        "print_material": "PETG", "layer_mm": "0.20", "wall_count": "4",
        "xy_compensation_mm": "0", "notes": "Vertical bore; measured twice.",
    }
    row.update(overrides)
    return row


class FeedbackGateTests(unittest.TestCase):
    def test_empty_and_template_inputs_cannot_generate_request(self):
        inputs = [
            b"", feedback(), feedback({}),
            feedback({"feature_id": "bearing_OD22_040", "nominal_mm": "22", "cad_mm": "22.40"}),
            feedback(measured(fit_result="not_tested", measured_part_mm="", measured_hardware_mm="")),
        ]
        for content in inputs:
            with self.subTest(content=content), self.assertRaises(gate.FeedbackError):
                gate.make_request(content, "feedback.csv")

    def test_slip_request_retains_exact_submitted_fields_and_measurements(self):
        row = measured(measured_part_mm="22.0812345", notes="  My actual measurement  ")
        request = gate.make_request(feedback(row), "feedback.csv")
        proposed = request["interface_requests"][0]
        self.assertEqual(proposed["candidate_cad_mm"], [22.35, 22.4, 22.45])
        self.assertEqual(proposed["selection_method"], "confirmed_slip")
        self.assertEqual(proposed["basis"]["measured_part_mm"], 22.0812345)
        self.assertEqual(proposed["basis"]["measured_hardware_mm"], 21.99)
        self.assertEqual(proposed["feedback"][0]["submitted_fields"], row)
        self.assertFalse(request["production_release"])

    def test_partial_tested_invalid_and_nonfinite_measurements_fail(self):
        overrides = [
            {"measured_part_mm": ""}, {"measured_hardware_mm": ""},
            {"measured_part_mm": "0"}, {"measured_hardware_mm": "-1"},
            {"measured_part_mm": "nan"}, {"measured_hardware_mm": "inf"},
            {"print_material": ""}, {"layer_mm": ""}, {"wall_count": "2.5"},
            {"wall_count": "0"}, {"xy_compensation_mm": ""},
            {"xy_compensation_mm": "nan"}, {"fit_result": "good"},
            {"fit_result": ""},
        ]
        for bad in overrides:
            with self.subTest(bad=bad), self.assertRaises(gate.FeedbackError):
                gate.make_request(feedback(measured(**bad)), "feedback.csv")

    def test_separate_interfaces_and_print_profiles_keep_local_corrections(self):
        rows = [
            measured(fit_result="tight", measured_part_mm="21.90"),
            measured(feature_id="shaft_clearance_ID8_040", interface="shaft_clearance_ID8",
                     nominal_mm="8", cad_mm="8.4", measured_part_mm="8.1", measured_hardware_mm="8", fit_result="loose"),
            measured(print_material="PLA", measured_part_mm="22.3", fit_result="loose"),
        ]
        groups = gate.make_request(feedback(*rows), "feedback.csv")["interface_requests"]
        self.assertEqual(len(groups), 3)
        self.assertEqual([group["center_cad_mm"] for group in groups], [22.5, 8.3, 22.1])
        self.assertEqual([group["basis"]["measured_part_mm"] for group in groups], [21.9, 8.1, 22.3])

    def test_heat_insert_uses_pilot_nominal_and_does_not_confirm_cold_slip(self):
        row = measured(feature_id="heat_insert_M3_040", interface="heat_insert_M3",
                       nominal_mm="4", cad_mm="4.4", measured_part_mm="4.2", measured_hardware_mm="4.6")
        proposed = gate.make_request(feedback(row), "feedback.csv")["interface_requests"][0]
        self.assertEqual(proposed["selection_method"], "empirical_dimension_correction")
        self.assertEqual(proposed["candidate_cad_mm"], [4.15, 4.2, 4.25])
        self.assertIn("Heat insertion and pull-out", proposed["validation_pending"])
        self.assertEqual(proposed["basis"]["measured_hardware_mm"], 4.6)

    def test_slip_selection_is_explicit_and_preserves_other_test_rows(self):
        rows = [
            measured(feature_id="too_tight", cad_mm="22.25", fit_result="tight"),
            measured(feature_id="wide_slip", cad_mm="22.70"),
            measured(feature_id="close_slip", cad_mm="22.40"),
        ]
        proposed = gate.make_request(feedback(*rows), "feedback.csv")["interface_requests"][0]
        self.assertEqual(proposed["selected_feature_id"], "close_slip")
        self.assertEqual(len(proposed["feedback"]), 3)

    def test_unmeasured_rows_are_skipped_when_measured_rows_exist(self):
        request = gate.make_request(feedback({}, {"feature_id": "blank_template"},
                                            measured(fit_result="not_tested"), measured()), "feedback.csv")
        self.assertEqual(request["measurement_rows_used"], 1)
        self.assertEqual([row["reason"] for row in request["ignored_rows"]],
                         ["blank", "unmeasured_template", "not_tested"])

    def test_invalid_cli_input_never_creates_or_overwrites_request(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "feedback.csv"
            output = Path(directory) / "request.json"
            source.write_bytes(feedback())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(gate.main([str(source), "--out", str(output)]), 2)
            self.assertFalse(output.exists())
            output.write_text("existing measured request", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(gate.main([str(source), "--out", str(output)]), 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "existing measured request")

    def test_valid_cli_writes_json_only_and_input_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "feedback.csv"
            output = Path(directory) / "request.json"
            source.write_bytes(feedback(measured()))
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(gate.main([str(source), "--out", str(output)]), 0)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(json.loads(output.read_text())["measurement_rows_used"], 1)
            original = source.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(gate.main([str(source), "--out", str(source)]), 2)
            self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
