"""Offline tests of controlled fixtures against the actual production policy."""
import asyncio
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from async_fixture_cases import Harness, SCENARIOS, VERSION, run_scenario, run_suite


class AsyncFixtureTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_and_cleanup_serialized_actual_brain_completions(self):
        for case in ("cancel_running_late_result", "replacement_waits_for_cleanup", "cancelled_job_reentry_after_replacement"):
            with self.subTest(case=case):
                row = await run_scenario(case)
                self.assertTrue(row["passed"], row["checks"])
                self.assertFalse(row["audio_e2e"])
                self.assertTrue(any(e["name"] == "controlled_analyst_returned" for e in row["events"]))
                if case == "cancel_running_late_result":
                    self.assertTrue(any(e["name"] == "controlled_analyst_ignored_cancellation" for e in row["events"]))
                    returned=next(e for e in row["events"] if e["name"] == "controlled_analyst_returned")
                    self.assertEqual(returned["status_before_return"], "cancelled")
                else:
                    self.assertTrue(next(c for c in row["checks"] if c["name"] == "no_replacement_started_during_cleanup")["passed"])

    async def test_real_coordinator_respects_every_delivery_guard(self):
        for case in ("late_result_while_user_speaks", "guard_playback", "guard_pending_audio", "guard_assistant_turn", "guard_native_delegation"):
            with self.subTest(case=case):
                row = await run_scenario(case)
                self.assertTrue(row["passed"], row["checks"])
                self.assertEqual(len(row["contexts"]), 1)
                self.assertGreaterEqual(row["delivery_delays"][0]["completion_to_context_ms"], 400)

    async def test_revision_and_duplicate_result_policy(self):
        changed = await run_scenario("changed_topic_revision")
        self.assertTrue(changed["passed"], changed["checks"])
        self.assertEqual(changed["contexts"], [])
        self.assertLess(changed["jobs"][0]["revision"], changed["final_user_revision"])
        duplicate = await run_scenario("duplicate_completion")
        self.assertTrue(duplicate["passed"], duplicate["checks"])
        self.assertEqual(len(duplicate["contexts"]), 1)

    async def test_completed_cancel_blocks_pending_delivery(self):
        row = await run_scenario("cancel_completed_before_delivery")
        check = next(c for c in row["checks"] if c["name"] == "cancel_completed_result_prevents_context")
        self.assertTrue(row["passed"], row["checks"])
        self.assertEqual(check["passed"], len(row["contexts"]) == 0)
        self.assertEqual(row["passed"], all(c["passed"] for c in row["checks"]))
        self.assertTrue(any(c["name"] == "cancel_after_complete_before_context" and c["status_before_cancel"] == "complete" for c in row["conditions"]))

    async def test_completed_cancel_is_idempotent_and_allows_replacement(self):
        async with Harness() as h:
            await h.user_turn("Compare options")
            await h.c.handle({"type": "playback_state", "playing": True})
            job = await h.start_job("Compare options")
            await h.finish(job, "Result waiting behind playback.")
            self.assertEqual(job["status"], "complete")
            self.assertFalse(job["announced"])
            await h.cancel(job)
            self.assertEqual(job["status"], "cancelled")
            self.assertNotIn("summary", job)
            await h.cancel(job)
            cancellation_events = [e for e in h.recorder.events if e.get("event", {}).get("type") == "brain_job"
                                   and e["event"].get("status") == "cancelled"]
            self.assertEqual(len(cancellation_events), 1)
            replacement = await h.start_job("Compare replacement options")
            self.assertNotEqual(replacement["job_id"], job["job_id"])
            self.assertEqual(replacement["status"], "running")

    async def test_cancel_invalidates_queued_result_without_claiming_playback(self):
        async with Harness() as h:
            await h.user_turn("Compare options")
            job = await h.start_job("Compare options")
            await h.finish(job, "Result queued as context, playback unverified.")
            await h.wait_for(lambda: len(h.delivered_ids) == 1)
            self.assertTrue(job["announced"])
            await h.cancel(job)
            self.assertEqual(job["status"], "cancelled")
            self.assertNotIn("summary", job)
            self.assertTrue(job["announced"], "Preserve that queueing happened; it is not proof of playback.")
            self.assertFalse(h.c.voice.contexts[0]["audio_played"])
            self.assertFalse(job["cancellation"]["remote_stop_verified"])
            await h.observe()
            self.assertEqual(h.delivered_ids, [job["job_id"]])

    async def test_harness_closes_production_tasks(self):
        async with Harness() as h:
            await h.user_turn("Compare options")
            await h.start_job("Compare options")
            result_task = h.c.result_task
            pending = list(h.c.brain.tasks.values())
            self.assertFalse(result_task.done())
        self.assertTrue(result_task.done())
        self.assertTrue(all(task.done() for task in pending))
        self.assertTrue(h.c.brain.closed)

    async def test_unknown_case_cannot_silently_pass(self):
        with self.assertRaises(ValueError):
            await run_scenario("invented")
        with self.assertRaises(ValueError):
            await run_suite([])
        self.assertEqual(len(SCENARIOS), 11)
        self.assertEqual(VERSION, "2026-09-24.async-component-2")
        with self.assertRaises(ValueError):
            await run_scenario("reordered_old_last")


if __name__ == "__main__":
    unittest.main()
