"""Offline prompt composition checks; no model or network is required."""
import tempfile
import unittest
from pathlib import Path

from pi_client import ROBOT_TOOLS, build_system_prompt


class GroundingTests(unittest.TestCase):
    def test_live_prompt_uses_runtime_notes_without_demo_people(self):
        with tempfile.TemporaryDirectory(prefix="mist-prompt-") as temp:
            run_dir = Path(temp)
            memory = run_dir / "memory"
            memory.mkdir()
            (memory / "SCRATCH.md").write_text("Owner prefers quiet greetings.", encoding="utf-8")
            prompt = build_system_prompt("mist", with_memory=False, run_dir=run_dir)
            self.assertIn("Owner prefers quiet greetings.", prompt)
            self.assertNotIn("Owner is Moon", prompt)
            self.assertNotIn("Roomba's gothic cousin", prompt)
            self.assertIn("No physical motion controller is connected", prompt)
            self.assertIn("three joint axes per leg", prompt)

    def test_legacy_personas_receive_current_runtime_contract_last(self):
        prompt = build_system_prompt("butter-nihilist", with_memory=True)
        self.assertIn("DEMO MEMORY DATA", prompt)
        contract_at = prompt.index("Runtime facts and constraints.")
        self.assertGreater(contract_at, prompt.index("DEMO MEMORY DATA"))
        self.assertIn("fetched_sources", prompt[contract_at:])
        self.assertIn("No overnight consolidation runs", prompt[contract_at:])

    def test_rpc_allowlist_contains_observation_and_recall_without_shell_tools(self):
        self.assertEqual(len(ROBOT_TOOLS), 18)
        self.assertTrue({"get_capabilities", "observe", "recall_memory"}.issubset(ROBOT_TOOLS))
        self.assertFalse({"bash", "read", "write", "exec"}.intersection(ROBOT_TOOLS))


if __name__ == "__main__":
    unittest.main()
