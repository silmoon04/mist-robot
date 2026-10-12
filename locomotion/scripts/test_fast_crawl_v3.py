"""Check the final recovery variable without executing physics."""
import unittest
import numpy as np
from locomotion.scripts.dev_fast_crawl_probe_v3 import check_prior
from experimental_fast_crawl_v2 import CadenceShiftFastCrawl
from experimental_fast_crawl_v3 import WideRecoveryFastCrawl, wider_along
from experimental_clearance_recovery import clearance_along
from experimental_support_transfer import feet_from_angles


class WiderRecoveryTests(unittest.TestCase):
    def test_reference_is_identical_and_vertical_targets_stay_exact(self):
        old = CadenceShiftFastCrawl(cycle_s=1.2)
        reference = WideRecoveryFastCrawl(cycle_s=1.2, recovery_start=.84)
        candidate = WideRecoveryFastCrawl(cycle_s=1.2)
        for phase in np.arange(129)/128.:
            t = 6.4+phase*1.2
            np.testing.assert_array_equal(old.targets(t, [.025, 0., 0.]), reference.targets(t, [.025, 0., 0.]))
            np.testing.assert_allclose(feet_from_angles(old.targets(t, [.025, 0., 0.]))[:, 2],
                                       feet_from_angles(candidate.targets(t, [.025, 0., 0.]))[:, 2], atol=1e-15)
        check_prior()

    def test_recovery_is_C1_and_peak_horizontal_rate_is_lower(self):
        for boundary in (.82, .96):
            left = np.array(wider_along(boundary-1e-9))
            right = np.array(wider_along(boundary+1e-9))
            np.testing.assert_allclose(left, right, atol=2e-6)
        phases = np.linspace(0., 1., 10001)
        wide = max(wider_along(p)[1] for p in phases)
        old = max(clearance_along(p)[1] for p in phases)
        self.assertAlmostEqual(wide/old, 0.84472049689441, places=10)


if __name__ == "__main__":
    unittest.main()
