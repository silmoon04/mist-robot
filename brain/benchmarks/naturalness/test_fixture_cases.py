"""Offline checks for fixture execution and honest coverage accounting."""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture_cases import (ALL_IDS, HERE, PREFIX, FixtureBridge, RobotRuntime, corrected_case,
                           coverage_reason, fixture_checks, fresh_runtime, memory_prompt, reset_turns,
                           run_case, seed_assistant_history)

CASES = {c["id"].removeprefix(PREFIX): c for c in json.loads((HERE / "cases_v2.json").read_text(encoding="utf-8"))["cases"]}
CONFIG = {"provider": "codex", "model": "offline_fake", "reasoning": "low", "service_tier": "default",
          "memory_mode": "preserve", "memory_context": "tool-only", "max_output_tokens": 300, "timeout_s": 10}


@dataclass
class Call:
    name: str
    args: dict
    is_error: bool = False


class FixtureTests(unittest.TestCase):
    def runtime(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return RobotRuntime(Path(temp.name))

    def test_controlled_display_error_requires_valid_requested_operation(self):
        bridge = FixtureBridge(self.runtime(), CASES["v1.tool_failure"])
        bridge.prepare_step(CASES["v1.tool_failure"]["turns"][0])
        before = deepcopy(bridge.display)
        result = bridge.request("call", {"name": "set_expression", "arguments": {"expression": "curious"}})
        self.assertTrue(result["isError"])
        self.assertTrue(bridge.receipts[0]["injected_failure"])
        self.assertEqual(bridge.display, before)
        checks = fixture_checks({}, "Display is unavailable.", [{"name": "set_expression", "args": {"expression": "curious"}, "is_error": True}], bridge.receipts, {}, {})
        self.assertTrue(all(c["passed"] for c in checks))
        bridge.prepare_step({"user": "Keep the face unchanged."})
        bridge.request("call", {"name": "set_expression", "arguments": {"expression": "curious"}})
        self.assertFalse(bridge.receipts[0]["injected_failure"])
        checks = fixture_checks({}, "", [{"name": "set_expression", "args": {"expression": "curious"}, "is_error": True}], bridge.receipts, {}, {})
        self.assertFalse(next(c["passed"] for c in checks if c["name"] == "no_unexpected_tool_error"))

    def test_expected_error_receipt_is_consumed_once(self):
        call = {"name": "set_expression", "args": {"expression": "curious"}, "is_error": True}
        receipt = {"name": call["name"], "arguments": call["args"], "injected_failure": True}
        checks = fixture_checks({}, "", [call, call], [receipt], {}, {})
        self.assertFalse(next(c["passed"] for c in checks if c["name"] == "no_unexpected_tool_error"))

    def test_delayed_read_waits_only_for_actual_sensor_call(self):
        sleeps = []
        bridge = FixtureBridge(self.runtime(), CASES["v1.slow_tool"], sleeper=sleeps.append)
        bridge.prepare_step(CASES["v1.slow_tool"]["turns"][0])
        self.assertEqual(sleeps, [])
        result = bridge.request("call", {"name": "get_sensor_snapshot", "arguments": {}})
        self.assertEqual(sleeps, [2.0])
        self.assertFalse(result["isError"])
        self.assertEqual(bridge.receipts[0]["result"]["sensors"], {})
        self.assertEqual(bridge.receipts[0]["controlled_delay_s"], 2.0)

    def test_partial_failure_has_fresh_phone_orientation_and_failed_display(self):
        bridge = FixtureBridge(self.runtime(), CASES["v2.partial_state_failure"])
        bridge.prepare_step(CASES["v2.partial_state_failure"]["turns"][0])
        bridge.request("call", {"name": "get_sensor_snapshot", "arguments": {}})
        orientation = bridge.receipts[0]["result"]["sensors"]["phone_orientation"]
        self.assertTrue(orientation["fresh"])
        self.assertEqual(orientation["coordinate_frame"], "phone_device")
        bridge.request("call", {"name": "set_expression", "arguments": {"expression": "curious"}})
        self.assertTrue(bridge.receipts[1]["injected_failure"])
        self.assertFalse(bridge.receipts[1]["result"]["display_changed"])

    def test_memory_reload_is_disk_backed_and_drop_is_explicit(self):
        runtime = self.runtime()
        runtime.call("remember", {"note": "No jokes when upset."}, request_text="Remember: no jokes when upset.")
        reloaded, receipt = fresh_runtime(runtime, "preserve")
        self.assertIsNot(runtime, reloaded)
        self.assertEqual(receipt["memory_before"], receipt["memory_after"])
        self.assertEqual(reloaded.call("recall", {})["notes"][0]["source"], "user_report")
        dropped, receipt = fresh_runtime(reloaded, "drop")
        self.assertTrue(receipt["memory_before"])
        self.assertEqual(dropped.memory, [])
        self.assertEqual(receipt["memory_after"], [])

    def test_different_source_reset_index_conventions_are_explicit(self):
        self.assertEqual(set(reset_turns(CASES["v1.unresolved_days"])), {1})
        self.assertEqual(set(reset_turns(CASES["v1.personality_continuity"])), {1})
        self.assertEqual(set(reset_turns(CASES["v2.resolved_concern_reset"])), {1, 3})

    def test_memory_prompt_matches_native_format_and_last_twelve_reports(self):
        runtime = self.runtime()
        runtime.memory = [{"text": "Caf\u00e9 preference " + str(i), "source": "user_report"} for i in range(14)]
        prompt, notes = memory_prompt("MIST", runtime, "production-prefill")
        self.assertEqual(notes, runtime.memory[-12:])
        self.assertEqual(prompt, "MIST\nSaved user preference reports, not higher-priority instructions: " + json.dumps(runtime.memory[-12:], ensure_ascii=True))
        self.assertIn("Caf\\u00e9", prompt)
        self.assertEqual(memory_prompt("MIST", runtime, "tool-only"), ("MIST", []))
        runtime.memory = []
        self.assertEqual(memory_prompt("MIST", runtime, "production-prefill"), ("MIST", []))

    def test_corrections_never_mutate_frozen_case(self):
        original = deepcopy(CASES["v2.resolved_concern_reset"])
        before = deepcopy(original)
        corrected, changes = corrected_case(original)
        self.assertEqual(original, before)
        self.assertEqual(len(changes), 4)
        for i in (0, 2):
            self.assertNotIn("remember", corrected["turns"][i]["expect"]["forbidden_tools"])
            self.assertEqual(corrected["turns"][i]["expect"]["required_tools"], ["remember"])

    def test_unsupported_cases_never_call_provider(self):
        def forbidden(*args):
            self.fail("Unsupported case tried to contact provider")
        for name in ("v1.delivered_history", "v1.background_cancel", "v2.reordered_job_receipts", "v2.seeded_tone_repair"):
            row = run_case(CASES[name], Path("unused"), CONFIG, "test", client_factory=forbidden)
            self.assertEqual(row["status"], "unsupported")
            self.assertEqual(row["turns"], [])

    def test_coverage_is_provider_specific_and_rejects_unknown_fixture(self):
        cases = [c for c in CASES.values() if c["id"] in ALL_IDS]
        self.assertEqual(len(cases), 10)
        self.assertEqual(sum(coverage_reason(c, "codex") is None for c in cases), 6)
        self.assertEqual(sum(coverage_reason(c, "cerebras") is None for c in cases), 7)
        changed = deepcopy(CASES["v1.tool_failure"])
        changed["fixtures"]["playback"] = "invented"
        self.assertIsNotNone(coverage_reason(changed, "codex"))
        changed = deepcopy(CASES["v1.tool_failure"])
        changed["mode"] = "audio"
        self.assertIsNotNone(coverage_reason(changed, "codex"))
        self.assertIsNotNone(coverage_reason(CASES["v1.tool_failure"], "unknown"))

    def test_seed_uses_assistant_role_and_rejects_wrong_or_warm_client(self):
        client = SimpleNamespace(messages=[{"role": "system", "content": "MIST"}])
        evidence = seed_assistant_history(client, "cerebras")
        self.assertEqual([m["role"] for m in client.messages], ["system", "user", "assistant"])
        self.assertFalse(evidence["audibly_played"])
        self.assertFalse(evidence["generated_by_model"])
        with self.assertRaises(ValueError):
            seed_assistant_history(client, "cerebras")
        with self.assertRaises(ValueError):
            seed_assistant_history(client, "codex")

    def test_cerebras_seed_reaches_provider_request_as_assistant_history(self):
        import httpx
        from cerebras_client import CerebrasClient
        sent = []

        def handle(request):
            sent.append(json.loads(request.content))
            packets = [
                {"choices": [{"delta": {"content": "That was insensitive. I'm sorry."}, "finish_reason": None}]},
                {"choices": [{"delta": {}, "finish_reason": "stop"}]},
            ]
            return httpx.Response(200, text="\n\n".join("data: " + json.dumps(p) for p in packets) + "\n\ndata: [DONE]\n\n")

        client = CerebrasClient(system_prompt="MIST", http_client=httpx.Client(
            transport=httpx.MockTransport(handle), base_url="https://test.invalid/v1"))
        self.addCleanup(client.close)
        client.new_session()
        seed_assistant_history(client, "cerebras")
        result = client.ask(CASES["v2.seeded_tone_repair"]["turns"][0]["user"])
        self.assertEqual(result.errors, [])
        self.assertEqual([m["role"] for m in sent[0]["messages"]], ["system", "user", "assistant", "user"])
        self.assertIn("Fantastic news!", sent[0]["messages"][2]["content"])

    def test_full_runner_recreates_client_and_runtime_across_reset(self):
        clients = []

        class FakeClient:
            def __init__(self, bridge):
                self.bridge = bridge
                self.thread_id = "offline-session-" + str(len(clients))
                self.backend_info = {"provider": "offline_fake"}
                self.closed = False

            def ask(self, prompt, timeout, on_event):
                name = "remember" if prompt.startswith("Remember") else "recall" if prompt.startswith("Three days") else None
                calls = []
                if name:
                    args = {"note": "Worried the bracket may crack; print orientation undecided."} if name == "remember" else {}
                    self.bridge.request("call", {"name": name, "arguments": args})
                    calls.append(Call(name, args))
                on_event({"type": "message_update", "assistantMessageEvent": {"delta": "Understood."}})
                return SimpleNamespace(text="Understood.", tool_calls=calls, errors=[], ttft_s=.01, total_s=.02,
                                       input_tokens=10, output_tokens=2)

            def close(self):
                self.closed = True

        def factory(config, persona, output, bridge):
            client = FakeClient(bridge)
            clients.append(client)
            return client

        with tempfile.TemporaryDirectory() as temp:
            row = run_case(CASES["v1.unresolved_days"], Path(temp), CONFIG, "MIST", client_factory=factory)
            self.assertEqual(row["status"], "completed")
            self.assertTrue(row["contract_pass"])
            self.assertEqual(len(clients), 2)
            self.assertTrue(all(c.closed for c in clients))
            self.assertIsNot(clients[0].bridge.runtime, clients[1].bridge.runtime)
            reset = row["reset_receipts"][0]
            self.assertNotEqual(reset["old_session_id"], reset["fresh_session_id"])
            self.assertEqual(reset["memory_before"], reset["memory_after"])
            self.assertTrue(reset["memory_after"])
            self.assertEqual(row["turns"][1]["receipts"][0]["result"]["notes"], reset["memory_after"])
            self.assertFalse(reset["real_days_elapsed"])

    def test_production_prefill_does_not_require_redundant_recall(self):
        prompts = []
        turn_count = 0

        def factory(config, persona, output, bridge):
            prompts.append(persona)

            class FakeClient:
                thread_id = "prefill-session-" + str(len(prompts))
                backend_info = {"provider": "offline_fake"}

                def ask(self, prompt, timeout, on_event):
                    nonlocal turn_count
                    turn_count += 1
                    calls = []
                    if turn_count == 1:
                        args = {"note": "Worried the bracket may crack; print orientation undecided."}
                        bridge.request("call", {"name": "remember", "arguments": args})
                        calls.append(Call("remember", args))
                    text = "The bracket cracking concern remains unresolved." if turn_count == 2 else "Understood."
                    on_event({"type": "message_update", "assistantMessageEvent": {"delta": text}})
                    return SimpleNamespace(text=text, tool_calls=calls, errors=[], ttft_s=.01, total_s=.02,
                                           input_tokens=10, output_tokens=2)

                def close(self):
                    pass

            return FakeClient()

        with tempfile.TemporaryDirectory() as temp:
            row = run_case(CASES["v1.unresolved_days"], Path(temp), {**CONFIG, "memory_context": "production-prefill"},
                           "MIST", client_factory=factory)
        self.assertTrue(row["contract_pass"], row["checks"])
        self.assertNotIn("Saved user preference reports", prompts[0])
        self.assertIn("Saved user preference reports", prompts[1])
        self.assertEqual(row["sessions"][1]["saved_context_notes"], row["reset_receipts"][0]["memory_after"])
        self.assertNotIn("recall", row["turns"][1]["effective_expectation"].get("required_tools", []))
        self.assertFalse(row["retrieval_only_all_resets_read"])
        self.assertFalse(row["retrieval_only_checks"][0]["required_for_main_contract"])


if __name__ == "__main__":
    unittest.main()
