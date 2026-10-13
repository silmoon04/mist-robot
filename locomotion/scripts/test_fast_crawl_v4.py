"""Static invariants for the bounded extension of the selected fast crawl."""
import unittest
import numpy as np
from locomotion.scripts.dev_fast_crawl_probe_v4 import check_prior, make_cases
from experimental_fast_crawl_v3 import WideRecoveryFastCrawl
from experimental_fast_crawl_v4 import SpeedCeilingCrawl


class SpeedCeilingTests(unittest.TestCase):
    def test_current_profile_remains_bit_identical(self):
        old, new = WideRecoveryFastCrawl(cycle_s=1.2), SpeedCeilingCrawl(cycle_s=1.2)
        for phase in np.arange(129)/128.:
            for command in ([.025, 0., 0.], [0., .025, .06], [0., 0., 0.]):
                t = 6.4+phase*1.2
                np.testing.assert_array_equal(old.targets(t, command), new.targets(t, command))
                np.testing.assert_array_equal(old.position_targets(t, command, phone_mass_kg=.155),
                                              new.position_targets(t, command, phone_mass_kg=.155))
        check_prior()

    def test_cap_formula_and_cycle_extension_are_explicit(self):
        for cycle in (1.2, 1., .8):
            gait = SpeedCeilingCrawl(cycle_s=cycle)
            ceiling = .035/(.8*cycle*1.15)
            self.assertEqual(gait.shift_m, .005*cycle/3.2)
            self.assertEqual(gait.uncapped_translation_m_s(), ceiling)
            self.assertTrue(all(abs(r-1.) < 1e-12 for r in gait.stride_cap_ratios([ceiling, 0., 0.]).values()))
            self.assertTrue(all(abs(r-.5) < 1e-12 for r in gait.stride_cap_ratios([2*ceiling, 0., 0.]).values()))
        for cycle in (0., .6, 1.1, 3.2):
            with self.assertRaises(ValueError):
                SpeedCeilingCrawl(cycle_s=cycle)
        with self.assertRaises(ValueError):
            SpeedCeilingCrawl(cycle_s=.8, shift_m=.005)
        with self.assertRaises(ValueError):
            SpeedCeilingCrawl(recovery_start=.84)

    def test_case_budget_and_saved_seed_pairing(self):
        cases = make_cases()
        self.assertEqual(len(cases), 8)
        self.assertEqual(sum(c["payload"] == .155 for c in cases), 6)
        self.assertTrue(all(c["steps"] == 480 and c["command_name"] == "forward" for c in cases))
        self.assertEqual(len({c["seed"] for c in cases if c["payload"] == .155}), 1)


if __name__ == "__main__":
    unittest.main()
