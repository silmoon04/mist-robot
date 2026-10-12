"""Check faster-preview isolation and score-command consistency without physics."""
import unittest
import numpy as np
from locomotion.scripts.dev_fast_crawl_probe import PROFILES, requested_command, check_prior
from experimental_fast_crawl import FastClearanceCrawl, preview_config
from experimental_stride_gain import TranslationGainClearanceCrawl
from locomotion.model import load_config


class FastCrawlTests(unittest.TestCase):
    def test_runtime_config_changes_only_target_slew(self):
        source = load_config()
        fast = preview_config(3.)
        self.assertEqual(fast["actuator"]["command_speed_rad_s"], 3.)
        fast["actuator"]["command_speed_rad_s"] = 1.8
        self.assertEqual(fast, source)
        self.assertEqual(load_config(), source)
        check_prior()

    def test_reference_geometry_is_identical(self):
        candidate = FastClearanceCrawl()
        reference = TranslationGainClearanceCrawl(shift_m=.005, translational_stride_gain=1.15)
        for phase in np.arange(33)/32.:
            t = 6.4+phase*3.2
            np.testing.assert_array_equal(candidate.targets(t, [.01, 0., 0.], [.03, -.02]), reference.targets(t, [.01, 0., 0.], [.03, -.02]))

    def test_fast_profiles_keep_uncapped_cardinal_strides_and_original_yaw(self):
        for profile in PROFILES.values():
            gait = FastClearanceCrawl(cycle_s=profile["cycle_s"])
            for name in ("forward", "backward", "left", "right", "clockwise", "counterclockwise"):
                command = requested_command(name, profile)
                self.assertTrue(all(value == 1. for value in gait.stride_cap_ratios(command).values()))
                self.assertEqual(gait.effective_geometric_command(command)[2], command[2])
                for phase in np.arange(65)/64.:
                    q = gait.targets(6.4+phase*gait.cycle_s, command, [.03, -.02])
                    self.assertTrue(np.isfinite(q).all())


if __name__ == "__main__":
    unittest.main()
