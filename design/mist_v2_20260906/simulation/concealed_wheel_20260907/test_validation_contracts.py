"""Cheap input/decision regressions; no dynamics or hardware are executed."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SIM))
import model
import validate_concealed as validation


class ValidationContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((SIM.parent / "cad/leg_proximal_20260907/output_candidate/leg_geometry_report.json").read_text())
        cls.params = json.loads(Path(cls.report["parameters_path"]).read_text())
        cls.params["wheel_transmission"] = {"topology": "longitudinal_upper_tibia_shaft_miter_1to1", "ratio": 1, "efficiency_assumption": .9}

    def test_electrical_caps_and_servo_assumptions_cannot_increase(self):
        validation.verify_actuator_contract(self.params)
        for section, field, value in [("wheel_motor", "current_limit_a", 2), ("servo", "continuous_fraction_of_stall", .5), ("transmission", "efficiency", [.95, .95, .95]), ("wheel_transmission", "efficiency_assumption", 1)]:
            with self.subTest(section=section, field=field):
                changed = copy.deepcopy(self.params)
                changed[section][field] = value
                with self.assertRaisesRegex(ValueError, "Protected"):
                    validation.verify_actuator_contract(changed)

    def test_miter_loss_scales_torque_but_preserves_current_and_speed(self):
        original = copy.deepcopy(self.params)
        derived = validation.effective_wheel_parameters(original)
        motor = derived["wheel_motor"]
        voltage = derived["servo"]["simulation_voltage_v"] / motor["nominal_voltage_v"]
        stall = motor["stall_torque_nm"] * voltage
        cap = stall * (motor["current_limit_a"] - motor["no_load_current_a"]) / (motor["stall_current_a"] * voltage - motor["no_load_current_a"])
        self.assertAlmostEqual(stall, .873772515)
        self.assertAlmostEqual(cap, .1561938099941962)
        self.assertAlmostEqual(motor["no_load_speed_rpm"] * voltage, 288.75)
        for field in ["current_limit_a", "stall_current_a", "no_load_current_a", "nominal_voltage_v"]:
            self.assertEqual(motor[field], original["wheel_motor"][field])
        self.assertEqual(original, self.params)
        with self.assertRaisesRegex(ValueError, "twice"):
            validation.effective_wheel_parameters(derived)

    def test_real_single_leg_export_is_rejected(self):
        path = SIM.parent / "cad/concealed_wheel_drive_20260907/output_cased_first/leg_geometry_report.json"
        with self.assertRaisesRegex(ValueError, "four-leg"):
            validation.basic_preflight(path)

    def test_earlier_130mm_tibia_cannot_reuse_old_mass(self):
        path = SIM.parent / "cad/leg_proximal_20260907/output_candidate/leg_geometry_report.json"
        with self.assertRaises(ValueError):
            validation.basic_preflight(path)

    def test_frame_origin_must_match_fk_even_if_two_copies_agree(self):
        validation.verify_frames(self.report, self.params, model)
        changed = copy.deepcopy(self.report)
        changed["specifications"]["FL"]["frames_world_mm"]["femur"][0][3] += 10000
        changed["link_mass_properties"]["FL_femur"]["frame_local_to_world_mm"][0][3] += 10000
        with self.assertRaisesRegex(ValueError, "origin differs"):
            validation.verify_frames(changed, self.params, model)

    def test_base_inertial_frame_cannot_shift(self):
        changed = copy.deepcopy(self.report)
        changed["link_mass_properties"]["base_link"]["frame_local_to_world_mm"][0][3] = 1
        with self.assertRaisesRegex(ValueError, "hip-plane"):
            validation.verify_frames(changed, self.params, model)

    def test_stale_parameter_bytes_rejected(self):
        tests_dir = HERE / "temporary_contract_tests"
        tests_dir.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tests_dir) as temp:
            temp = Path(temp)
            parameter_path = temp / "synthetic_parameters.json"
            parameter_path.write_text("{}")
            minimal = {"specifications": {name: {} for name in ["FL", "FR", "RL", "RR", "body"]},
                       "exports_complete": True, "shape_checks": [],
                       "interference": {"positive_volume_interferences": [], "boolean_failures": []},
                       "physical_mass_properties": {"units": {"mass": "kg", "com": "m", "inertia": "kg m^2", "cad_transforms": "mm"}},
                       "parameters_path": str(parameter_path), "parameters_sha256": hashlib.sha256(b"old bytes").hexdigest()}
            report_path = temp / "synthetic_report.json"
            report_path.write_text(json.dumps(minimal))
            with self.assertRaisesRegex(ValueError, "parameter bytes changed"):
                validation.basic_preflight(report_path)

    def test_exact_gate_boundary_and_missing_reserve(self):
        passed = {"status": "PASS_IN_MODEL"}
        fixture = {"status": "PASS_IN_MODEL", "continuous_torque_reserve_fraction": .20,
                   "hold_max_foot_error_m": .010, "active_hold_saturated_steps": 0,
                   "active_all_run_travel_violations": 0}
        self.assertTrue(validation.gait_gate(passed, passed, fixture)["allowed"])
        for field, value in [("continuous_torque_reserve_fraction", .19999), ("hold_max_foot_error_m", .01001), ("active_hold_saturated_steps", 1), ("active_all_run_travel_violations", 1)]:
            changed = {**fixture, field: value}
            self.assertFalse(validation.gait_gate(passed, passed, changed)["allowed"])
        self.assertFalse(validation.gait_gate(passed, {"status": "FAIL_IN_MODEL"}, fixture)["allowed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
