import math
import unittest
import numpy as np
from kinematics import COXA, LEGS, LIMITS, NEUTRAL, crawl_plan, forward_body, forward_local, inverse_local, inverse_world, nominal_stance, rz, sample_phase, support_margin


class KinematicContract(unittest.TestCase):
    def test_nominal_dimensions_and_ground_height(self):
        known_neutral=np.radians([0,25,60])
        base, feet = nominal_stance(known_neutral)
        self.assertAlmostEqual(base[2], 0.111636086856, places=7)
        xy=0.152536405789+(COXA-.050)/math.sqrt(2)
        np.testing.assert_allclose(feet["FL"], [xy,xy,0.005], atol=1e-7)
        for leg in LEGS:
            np.testing.assert_allclose(inverse_world(leg, feet[leg], base), known_neutral, atol=1e-10)

    def test_positive_pitch_moves_toe_down(self):
        self.assertLess(forward_local([0, 0.1, 0.1])[2], 0)

    def test_translated_rotated_base(self):
        for leg in LEGS:
            base = np.array([0.12, -0.34, 0.27])
            rot = rz(0.43)
            q = np.radians([12, 18, 70])
            toe = base + rot @ forward_body(leg, q)
            np.testing.assert_allclose(inverse_world(leg, toe, base, rot), q, atol=1e-10)

    def test_joint_envelope_round_trip(self):
        rng = np.random.default_rng(3215)
        for _ in range(300):
            margin=.1*(LIMITS[:,1]-LIMITS[:,0])
            q = rng.uniform(LIMITS[:,0]+margin,LIMITS[:,1]-margin)
            np.testing.assert_allclose(inverse_local(forward_local(q)), q, atol=1e-10)

    def test_unreachable_and_limit_rejection(self):
        with self.assertRaises(ValueError):
            inverse_local([0.8, 0, 0])
        with self.assertRaises(ValueError):
            inverse_local(forward_local(np.radians([45, 20, 60])))

    def test_full_crawl_reach_and_support(self):
        base, feet = nominal_stance()
        minimum = math.inf
        for phase in crawl_plan(neutral=np.radians([0,25,60])):
            for t in np.linspace(0, 1, 101):
                b, f = sample_phase(phase, t)
                for leg in LEGS:
                    q = inverse_world(leg, f[leg], b)
                    np.testing.assert_allclose(b + forward_body(leg, q), f[leg], atol=1e-10)
                if phase["kind"] == "swing":
                    minimum = min(minimum, support_margin(b[:2], [v[:2] for k,v in f.items() if k != phase["leg"]]))
        self.assertGreater(minimum, 0.014)
        self.assertAlmostEqual(b[0], 0.030)
        self.assertAlmostEqual(b[1], 0.0)


if __name__ == "__main__":
    unittest.main()
