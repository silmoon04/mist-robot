import math
import unittest
from control_uncertainty import describe_case, feedback_deadband


class ControlUncertainty(unittest.TestCase):
    def test_zero_deadband_preserves_the_existing_controller(self):
        for error in [-2,-.01,0,.01,2]:
            self.assertEqual(feedback_deadband(error,0),error)

    def test_feedback_stays_zero_inside_the_declared_gap(self):
        width=math.radians(.5)
        for error in [-width,-width/2,0,width/2,width]:
            self.assertEqual(feedback_deadband(error,width),0)

    def test_outer_slope_and_direction_are_preserved(self):
        width=math.radians(.5)
        self.assertAlmostEqual(feedback_deadband(math.radians(1.5),width),math.radians(1))
        self.assertAlmostEqual(feedback_deadband(math.radians(-1.5),width),math.radians(-1))

    def test_invalid_or_nonfinite_cases_are_rejected(self):
        for width in [-1,float("nan")]:
            with self.assertRaises(ValueError):feedback_deadband(.1,width)
        with self.assertRaises(ValueError):describe_case(0,.1,.5)
        with self.assertRaises(ValueError):describe_case(.5,.1,3)

    def test_proxy_cannot_claim_material_or_backlash_validation(self):
        case=describe_case(.5,.1,1)
        self.assertEqual(case["feedback_deadband_full_width_deg"],2)
        self.assertFalse(case["structural_flexibility_simulated"])
        self.assertFalse(case["mechanical_backlash_simulated"])
        self.assertFalse(case["material_properties_measured"])


if __name__=="__main__":unittest.main()
