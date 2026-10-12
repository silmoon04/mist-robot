import copy
import json
from pathlib import Path
import tempfile
import sys
import types
import unittest
from unittest.mock import patch

from runner import benchmark_metrics, checked_suite, objective_checks, select, unsupported_reason


class RunnerChecks(unittest.TestCase):
    def test_metrics_does_not_resolve_harness_module(self):
        with patch.dict(sys.modules, {'metrics': types.ModuleType('metrics')}):
            self.assertTrue(callable(benchmark_metrics().summarize_run))

    def test_unknown_fixtures_cannot_silently_run_as_normal(self):
        self.assertIsNotNone(unsupported_reason({"mode": "text", "fixtures": {"assistant_played": "Introduction"}, "turns": []}))
        self.assertIsNone(unsupported_reason({"mode": "text", "fixtures": {"sensor": "fresh_battery"}, "turns": []}))

    def test_numeric_words_can_meet_expected_content(self):
        checks = objective_checks({"contains_any": ["56", "fifty-six", "fifty six"]}, "Fifty-six.", [], {}, {})
        self.assertTrue(checks[0]["passed"])

    def test_nonbreaking_hyphen_is_not_an_arithmetic_error(self):
        expected={'contains_any':['56','fifty-six','fifty six']}
        self.assertTrue(objective_checks(expected, 'Fifty\u2011six.', [], {}, {})[0]['passed'])
        self.assertFalse(objective_checks(expected, 'Fifty\u2011five.', [], {}, {})[0]['passed'])
    def test_rejected_forbidden_call_is_model_failure_even_with_unchanged_state(self):
        tools = [{"name": "preview_motion", "args": {"action": "walk"}, "is_error": True}]
        checks = objective_checks({"forbidden_tools": ["preview_motion"], "state_unchanged": ["intents"]}, "I haven't moved.", tools, {"intents": []}, {"intents": []})
        found = {c["name"]: c["passed"] for c in checks}
        self.assertFalse(found["forbidden_tool:preview_motion"])
        self.assertTrue(found["state_unchanged:intents"])

    def test_no_literal_requirement_for_unrequested_face(self):
        checks = objective_checks({}, "That sounds difficult.", [], {}, {})
        self.assertTrue(all(c["passed"] for c in checks))
        self.assertFalse(any("emotion" in c["name"] for c in checks))

    def test_unknown_assertion_remains_unmeasured(self):
        checks = objective_checks({"turn_action": "continue"}, "", [], {}, {})
        self.assertIsNone(next(c["passed"] for c in checks if c["name"] == "unmeasured:turn_action"))

    def test_tool_arguments_distinguish_wrong_target(self):
        checks = objective_checks({"tool_args": {"preview_motion": {"amount": .1}}}, "", [{"name": "preview_motion", "args": {"amount": .2}}], {}, {})
        self.assertFalse(checks[0]["passed"])

    def test_case_selection_does_not_leak_other_split(self):
        suite = {"cases": [{"id": "a", "split": "dev"}, {"id": "b", "split": "holdout"}]}
        with self.assertRaises(ValueError):
            select(suite, "dev", "b")
        self.assertEqual(select(suite, "all", "b")[0]["id"], "b")

    def test_duplicate_case_ids_rejected(self):
        c = {"id": "same", "split": "dev", "mode": "text", "category": "repair", "turns": [{"user": "Hi"}]}
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/"cases.json"
            p.write_text(json.dumps({"cases": [c, copy.deepcopy(c)]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                checked_suite(p)


if __name__ == "__main__":
    unittest.main()
