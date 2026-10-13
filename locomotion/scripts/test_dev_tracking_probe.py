"""Retain development outcomes when a worker fails or collection stops."""
from concurrent.futures import Future
from copy import deepcopy
import unittest
from unittest.mock import patch

from locomotion.scripts import dev_tracking_probe as probe


def synthetic_case(case):
    if case["variant"] == "failed":
        raise ValueError("synthetic worker failure")
    return {"case": case, "measurement": 42}


class CollectionTests(unittest.TestCase):
    def test_process_failure_preserves_later_success_and_order(self):
        cases = [{"variant": "failed"}, {"variant": "completed"}]
        snapshots = []
        results = probe.collect_cases(cases, 1, lambda rows: snapshots.append(deepcopy(rows)),
                                      runner=synthetic_case)
        self.assertEqual([row["case"] for row in results], cases)
        self.assertEqual(results[0]["status"], "execution_error")
        self.assertIn("ValueError: synthetic worker failure", results[0]["execution_error"])
        self.assertEqual(results[1]["status"], "completed")
        self.assertEqual(results[1]["measurement"], 42)
        self.assertEqual(snapshots[-1], results)
        self.assertEqual(len(snapshots), 2)

    def test_interruption_retains_completed_and_marks_missing_cases(self):
        cases = [{"variant": name} for name in ("completed", "running", "queued")]
        completed, running, queued = Future(), Future(), Future()
        completed.set_result({"case": cases[0], "measurement": 42})
        running.set_running_or_notify_cancel()
        snapshots = []
        with patch.object(probe, "ProcessPoolExecutor") as factory, \
                patch.object(probe, "as_completed", side_effect=KeyboardInterrupt):
            pool = factory.return_value
            pool.submit.side_effect = [completed, running, queued]
            with self.assertRaises(KeyboardInterrupt):
                probe.collect_cases(cases, 1, lambda rows: snapshots.append(deepcopy(rows)))
            pool.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
        self.assertEqual([row["case"] for row in snapshots[-1]], cases)
        self.assertEqual([row["status"] for row in snapshots[-1]],
                         ["completed", "uncollected", "cancelled"])
        self.assertEqual(snapshots[-1][0]["measurement"], 42)
        self.assertTrue(queued.cancelled())


if __name__ == "__main__":
    unittest.main()
