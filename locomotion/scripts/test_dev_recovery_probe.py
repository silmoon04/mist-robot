"""Exercise recovery-wrapper receipts through the shared process collector."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from locomotion.scripts import dev_recovery_probe as recovery


def synthetic_recovery_case(case):
    if case["variant"] == "shift005":
        raise ValueError("synthetic recovery failure")
    return {"case": case, "tracking_screen_passed": False,
            "steady": {"sample_count": 42}}


class RecoveryCollectionTests(unittest.TestCase):
    def test_wrapper_keeps_later_success_after_first_worker_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "recovery.json"
            argv = ["dev_recovery_probe.py", "--workers", "1", "--output", str(output)]
            shared_collector = recovery.original_probe.collect_cases
            with patch.object(recovery.sys, "argv", argv), \
                    patch.object(recovery, "run_case", synthetic_recovery_case), \
                    patch.object(recovery.original_probe, "collect_cases", wraps=shared_collector) as collector, \
                    redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as stopped:
                    recovery.main()
            self.assertEqual(stopped.exception.code, 1)
            collector.assert_called_once()
            self.assertIs(collector.call_args.kwargs["runner"], synthetic_recovery_case)
            receipt = json.loads(output.read_text())
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual([row["case"] for row in receipt["results"]], receipt["ordered_cases"])
            failed, completed = receipt["results"]
            self.assertEqual(failed["status"], "execution_error")
            self.assertEqual(failed["case"]["variant"], "shift005")
            self.assertIn("ValueError: synthetic recovery failure", failed["execution_error"])
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["case"]["variant"], "shift005_matched")
            self.assertEqual(completed["steady"]["sample_count"], 42)


if __name__ == "__main__":
    unittest.main()
