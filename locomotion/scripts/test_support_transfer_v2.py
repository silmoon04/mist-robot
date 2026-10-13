"""Exercise pre-reset payload construction and the v2 failed-worker receipt."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from locomotion.scripts import dev_support_transfer_probe_v2 as probe
from locomotion.acceptance import COMMANDS
from locomotion.model import load_config


def synthetic_support_case(case):
    if case["variant"] == "clearance_shift005_gain115":
        raise RuntimeError("synthetic v2 worker failure")
    return {"case": case, "tracking_screen_passed": False, "steady": {"sample_count": 42}}


class PayloadBeforeResetEnv:
    """No simulator calls; mirror the delayed creation of known payload."""
    def __init__(self, **kwargs):
        self.cfg = load_config()
        self.declared_payload = kwargs["payload"]

    def reset(self, **kwargs):
        self.phone_mass = float(self.declared_payload)
        return None, {}


class SupportV2Tests(unittest.TestCase):
    def test_declared_payload_constructs_controller_before_reset(self):
        import locomotion.mist_env as env_module
        case = {"variant": "planned_support_gain115", "payload": .155,
                "randomize": False, "save_trace": True, "command_name": "backward"}
        observed = {}
        def pure_case_runner(declared):
            env = env_module.MistEnv(payload=declared["payload"])
            self.assertFalse(hasattr(env, "phone_mass"))
            self.assertEqual(env.gait.phone_mass_kg, declared["payload"])
            env.reset(seed=2**50)
            self.assertEqual(env.gait.phone_mass_kg, env.phone_mass)
            observed["gait"] = env.gait
            return {"case": declared, "initial_info": {"command": COMMANDS["backward"]}}
        with patch.object(env_module, "MistEnv", PayloadBeforeResetEnv), \
                patch.object(probe.original_probe, "run_case", pure_case_runner):
            result = probe.run_case(case)
        self.assertIn("support_plan", result)
        self.assertEqual(observed["gait"].phone_mass_kg, .155)

    def test_reset_rejects_realized_payload_mismatch(self):
        import locomotion.mist_env as env_module
        class WrongPayloadEnv(PayloadBeforeResetEnv):
            def reset(self, **kwargs):
                self.phone_mass = .154
                return None, {}
        case = {"variant": "planned_support_gain115", "payload": .155,
                "randomize": False, "save_trace": True, "command_name": "backward"}
        def pure_case_runner(declared):
            env = env_module.MistEnv(payload=declared["payload"])
            env.reset()
        with patch.object(env_module, "MistEnv", WrongPayloadEnv), \
                patch.object(probe.original_probe, "run_case", pure_case_runner):
            with self.assertRaisesRegex(RuntimeError, "Realized known payload"):
                probe.run_case(case)

    def test_wrapper_retains_later_success_after_worker_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/"support.json"
            argv = ["dev_support_transfer_probe_v2.py", "--workers", "1", "--output", str(output)]
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
            self.assertIn("static_geometry_evidence", receipt)


if __name__ == "__main__":
    unittest.main()
