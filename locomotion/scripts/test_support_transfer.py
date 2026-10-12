"""Static solver and failed-worker receipt checks; no physics simulation."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from locomotion.scripts import dev_support_transfer_probe as probe
from experimental_support_transfer import solve_convex_qp, PlanningError, periodic_basis, PlannedSupportTransferCrawl
from experimental_stride_gain import TranslationGainClearanceCrawl
from locomotion.acceptance import COMMANDS


def synthetic_support_case(case):
    if case["variant"] == "clearance_shift005_gain115":
        raise PlanningError("synthetic explicit optimizer failure")
    return {"case": case, "tracking_screen_passed": False, "steady": {"sample_count": 42}}


class SupportTransferTests(unittest.TestCase):
    def test_constrained_qp_and_explicit_infeasibility(self):
        solution, receipt = solve_convex_qp(np.eye(2), [[1., 0.], [0., 1.], [1., 1.]], [1., 2., 4.])
        np.testing.assert_allclose(solution, [2., 2.], atol=1e-8)
        self.assertLess(receipt["primal_violation_fraction"], 1e-8)
        with self.assertRaises(PlanningError):
            solve_convex_qp(np.eye(1), [[1.], [-1.]], [1., 1.])

    def test_basis_partition_and_periodic_derivatives(self):
        for phase in np.arange(65)/64.:
            self.assertAlmostEqual(periodic_basis(phase).sum(), 1.)
            for derivative in (1, 2):
                self.assertAlmostEqual(periodic_basis(phase, derivative).sum(), 0.)
                np.testing.assert_allclose(periodic_basis(phase, derivative), periodic_basis(phase+1., derivative), atol=1e-12)

    def test_gain_and_attitude_contract_stay_inherited(self):
        gait = PlannedSupportTransferCrawl(phone_mass_kg=.155)
        reference = TranslationGainClearanceCrawl(shift_m=0., translational_stride_gain=1.15)
        command = np.asarray(COMMANDS["backward"])
        copy = command.copy()
        for phase in np.arange(17)/16.:
            t = 6.4+phase*3.2
            # Zero coefficients isolate and verify the frame transformation,
            # before checking the support plan in the independent audit.
            gait.plans[tuple(command)] = {"coefficients_mm": np.zeros((2, 32)), "solver": {}}
            np.testing.assert_allclose(gait.targets(t, command, [.04, -.03]), reference.targets(t, command, [.04, -.03]), atol=1e-13)
        np.testing.assert_array_equal(command, copy)
        np.testing.assert_array_equal(gait.effective_geometric_command(COMMANDS["clockwise"]), COMMANDS["clockwise"])
        self.assertEqual(gait.cycle_s, reference.cycle_s)
        self.assertEqual(gait.lift_m, reference.lift_m)
        self.assertEqual(gait.offset, reference.offset)

    def test_wrapper_retains_later_success_after_explicit_worker_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/"support.json"
            argv = ["dev_support_transfer_probe.py", "--workers", "1", "--output", str(output)]
            shared = probe.original_probe.collect_cases
            with patch.object(probe.sys, "argv", argv), patch.object(probe, "run_case", synthetic_support_case), \
                    patch.object(probe.original_probe, "collect_cases", wraps=shared) as collector, redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as stopped:
                    probe.main()
            self.assertEqual(stopped.exception.code, 1)
            collector.assert_called_once()
            self.assertIs(collector.call_args.kwargs["runner"], synthetic_support_case)
            receipt = json.loads(output.read_text())
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual([r["case"] for r in receipt["results"]], receipt["ordered_cases"])
            self.assertEqual(receipt["results"][0]["status"], "execution_error")
            self.assertEqual(receipt["results"][1]["status"], "completed")
            self.assertEqual(receipt["ordered_cases"][0]["seed"], receipt["ordered_cases"][1]["seed"])
            self.assertTrue(all(c["seed"] >= 2**50 for c in receipt["ordered_cases"]))


if __name__ == "__main__":
    unittest.main()
