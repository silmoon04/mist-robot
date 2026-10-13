"""Isolate common shift change and verify saved-reference case matching."""
import unittest
import numpy as np
from locomotion.scripts import dev_fast_crawl_probe_v2 as probe
from experimental_fast_crawl import FastClearanceCrawl
from experimental_fast_crawl_v2 import CadenceShiftFastCrawl
from experimental_support_transfer import feet_from_angles, inherited_shift_reference


class CadenceShiftTests(unittest.TestCase):
    def test_five_mm_reference_is_identical(self):
        old = FastClearanceCrawl(cycle_s=1.2)
        new = CadenceShiftFastCrawl(cycle_s=1.2, shift_m=.005)
        for phase in np.arange(65)/64.:
            t = 6.4+phase*1.2
            np.testing.assert_array_equal(old.targets(t, [.025, 0., 0.]), new.targets(t, [.025, 0., 0.]))

    def test_scaled_shift_changes_only_common_horizontal_reference(self):
        old = FastClearanceCrawl(cycle_s=1.2)
        new = CadenceShiftFastCrawl(cycle_s=1.2)
        for phase in np.arange(65)/64.:
            t = 6.4+phase*1.2
            delta = inherited_shift_reference(old, t)["shift_m"]-inherited_shift_reference(new, t)["shift_m"]
            feet_delta = feet_from_angles(new.targets(t, [.025, 0., 0.]))-feet_from_angles(old.targets(t, [.025, 0., 0.]))
            np.testing.assert_allclose(feet_delta, np.tile(np.r_[delta, 0.], (4, 1)), atol=2e-15)
        self.assertEqual(new.lift_m, old.lift_m)
        self.assertEqual(new.translational_stride_gain, old.translational_stride_gain)

    def test_reference_receipt_guard(self):
        probe.check_prior()
        import json
        saved = json.loads(probe.REFERENCE_PATH.read_text())["results"]
        case = next(row["case"].copy() for row in saved if row["case"]["variant"] == "fast120_v025_s180")
        case["variant"] += "_shift1875"
        self.assertEqual(probe.reference_for_case(case)["case"]["seed"], case["seed"])
        case["seed"] += 1
        with self.assertRaisesRegex(RuntimeError, "seed"):
            probe.reference_for_case(case)


if __name__ == "__main__":
    unittest.main()
