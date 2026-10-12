import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from duplex.context_checkpoint import ContextLedger


def candidate(snapshot, *, summary="Useful shorter context", source_ids=None,
              raw_ids=None, facts=None):
    ids = [m.id for m in snapshot.messages]
    return {"covered_through_revision": snapshot.covered_through_revision,
            "task_revision": snapshot.task_revision,
            "summary": summary, "source_ids": ids if source_ids is None else source_ids,
            "raw_ids": [] if raw_ids is None else raw_ids,
            "facts": [] if facts is None else facts}


class ContextCheckpointTests(unittest.TestCase):
    def test_speech_coaching_keeps_exact_imperfections_and_audio_reference(self):
        ledger = ContextLedger("speech_coaching", ({"role": "system", "content": "voice persona"},))
        ledger.append("u1", "user", "I, um, I went to the st— store.",
                      protected_segments=("um", "st— store"), audio_ref="capture:1",
                      word_timings=(("um", .2, .4),))
        ledger.append("a1", "assistant", "Try saying that again.")
        snapshot = ledger.snapshot()
        with self.assertRaises(ValueError):
            ledger.commit(snapshot, candidate(snapshot, summary="Speaker hesitated", raw_ids=[]))
        cp = ledger.commit(snapshot, candidate(snapshot, raw_ids=["u1"]))
        context = ledger.working_context()
        self.assertEqual(cp.raw_ids, ("u1",))
        self.assertEqual(context["raw"][0]["text"], "I, um, I went to the st— store.")
        self.assertEqual(context["raw"][0]["audio_ref"], "capture:1")
        self.assertEqual(context["raw"][0]["word_timings"], [["um", .2, .4]])
        self.assertEqual(ledger.originals()[0].text, "I, um, I went to the st— store.")
        self.assertIn("filler_words=true", ledger.proposal_input(snapshot)["instruction"])

    def test_speech_profile_pins_user_utterance_without_manual_segment_tag(self):
        ledger = ContextLedger("speech_coaching")
        ledger.append("u1", "user", "Well, uh, I— I forgot.")
        snap = ledger.snapshot()
        with self.assertRaises(ValueError):
            ledger.commit(snap, candidate(snap, raw_ids=[]))

    def test_problem_solving_pins_correction_negation_task_and_receipt_group(self):
        ledger = ContextLedger("problem_solving")
        ledger.append("goal", "user", "Fix the boot loop", marks={"working_task"})
        ledger.append("attempt", "assistant", "Restarted service", receipt_group="call-1")
        ledger.append("receipt", "tool", "Exit 1", receipt_group="call-1")
        ledger.append("no", "user", "Do not flash firmware", marks={"negation"})
        ledger.append("correction", "user", "Actually board B", marks={"correction"})
        snap = ledger.snapshot()
        mandatory = ["goal", "attempt", "receipt", "no", "correction"]
        for omitted in mandatory:
            with self.subTest(omitted=omitted), self.assertRaises(ValueError):
                ledger.commit(snap, candidate(snap, raw_ids=[id for id in mandatory if id != omitted]))
        ledger.commit(snap, candidate(snap, raw_ids=list(reversed(mandatory))))
        self.assertEqual([m["id"] for m in ledger.working_context()["raw"]], mandatory)

    def test_stale_async_proposal_rejected_after_correction_or_mode_change(self):
        for change in ("correction", "mode"):
            with self.subTest(change=change):
                ledger = ContextLedger("ordinary_chat")
                ledger.append("u1", "user", "I prefer tea")
                snap = ledger.snapshot()
                if change == "correction":
                    ledger.append("u2", "user", "Actually coffee", marks={"correction"})
                else:
                    ledger.set_profile("speech_coaching")
                    self.assertIn("filler_words=true", ledger.proposal_input(ledger.snapshot())["instruction"])
                with self.assertRaisesRegex(ValueError, "Stale task"):
                    ledger.commit(snap, candidate(snap))
                self.assertIsNone(ledger.working_context()["checkpoint"])

    def test_new_message_after_snapshot_survives_checkpoint_as_tail(self):
        ledger = ContextLedger("ordinary_chat")
        ledger.append("u1", "user", "I prefer tea")
        snap = ledger.snapshot()
        ledger.append("u2", "user", "It is raining")
        ledger.commit(snap, candidate(snap, facts=[{"text": "Prefers tea", "source_ids": ["u1"]}]))
        context = ledger.working_context(recent_window=1)
        self.assertEqual([m["id"] for m in context["tail"]], ["u2"])
        self.assertEqual(context["recent_ids"], ["u2"])
        self.assertEqual([m.id for m in ledger.originals()], ["u1", "u2"])

    def test_hallucinated_source_and_unattributed_fact_are_rejected(self):
        ledger = ContextLedger("ordinary_chat")
        ledger.append("u1", "user", "I prefer tea")
        snap = ledger.snapshot()
        with self.assertRaises(ValueError):
            ledger.commit(snap, candidate(snap, source_ids=["invented"]))
        with self.assertRaises(ValueError):
            ledger.commit(snap, candidate(snap, facts=[{"text": "Prefers tea", "source_ids": []}]))

    def test_newer_checkpoint_rejects_older_parallel_completion(self):
        ledger = ContextLedger("ordinary_chat")
        ledger.append("u1", "user", "A")
        first = ledger.snapshot()
        second = ledger.snapshot()
        ledger.commit(second, candidate(second))
        with self.assertRaisesRegex(ValueError, "newer checkpoint"):
            ledger.commit(first, candidate(first))

    def test_changed_fact_invalidates_existing_checkpoint_and_restores_originals(self):
        ledger = ContextLedger("ordinary_chat")
        ledger.append("u1", "user", "The board is A")
        snap = ledger.snapshot()
        ledger.commit(snap, candidate(snap))
        ledger.append("u2", "user", "No, the board is B", marks={"negation"})
        view = ledger.working_context()
        self.assertIsNone(view["checkpoint"])
        self.assertEqual([record["id"] for record in view["tail"]], ["u1", "u2"])

    def test_budget_or_idle_trigger_is_batched(self):
        ledger = ContextLedger("ordinary_chat")
        for index in range(3):
            ledger.append(f"u{index}", "user", "A")
        self.assertFalse(ledger.should_checkpoint(estimated_context_tokens=1000,
                         token_budget=100, idle_seconds=100, min_new_messages=4))
        ledger.append("u3", "user", "A")
        self.assertTrue(ledger.should_checkpoint(estimated_context_tokens=1000,
                        token_budget=100, idle_seconds=0, min_new_messages=4))
        self.assertTrue(ledger.should_checkpoint(estimated_context_tokens=10,
                        token_budget=100, idle_seconds=31, min_new_messages=4))
        ledger.commit(ledger.snapshot(), candidate(ledger.snapshot()))
        self.assertFalse(ledger.should_checkpoint(estimated_context_tokens=1000,
                         token_budget=100, idle_seconds=100, min_new_messages=4))


if __name__ == "__main__":
    unittest.main()
