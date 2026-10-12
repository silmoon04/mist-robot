from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from expression_capture_audit import analyze


class ExpressionAuditTests(unittest.TestCase):
    def frame(self, stamp, expression, active=True):
        return {"t_ms": stamp, "audio_active": active, "policy": {"expression": expression},
                "face": {"expression": expression + "_face", "drawnMouthFamily": {"active": expression + "_mouth"}}}

    def test_sad_expiry_and_cleanup_exclusion(self):
        report = analyze({"observation_end_ms": 400,
                          "events": [{"type": "face", "t_ms": 0, "expression": "sad", "duration_ms": 100}],
                          "frames": [self.frame(20, "sad"), self.frame(80, "sad"), self.frame(130, "sad", False),
                                     self.frame(250, "neutral"), self.frame(410, "neutral")]})
        self.assertEqual(report["active_sample_count"], 3)
        row = report["command_coverage_observations"][0]
        self.assertEqual(row["matching_active_samples"], 2)
        self.assertEqual(row["different_active_samples"], 1)
        self.assertEqual(row["first_different_active_sample_ms"], 250)

    def test_explicit_next_command_ends_coverage_window(self):
        report = analyze({"events": [{"type": "face", "t_ms": 0, "expression": "sad"},
                                      {"type": "face", "t_ms": 100, "expression": "neutral"}],
                          "frames": [self.frame(50, "sad"), self.frame(200, "neutral")]})
        self.assertEqual(report["command_coverage_observations"][0]["different_active_samples"], 0)
        self.assertEqual(report["command_coverage_observations"][1]["matching_active_samples"], 1)


if __name__ == "__main__":
    unittest.main()
