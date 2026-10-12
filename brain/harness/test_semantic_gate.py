import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from duplex.semantic_gate import GateSnapshot, decide, validate_compaction


class SemanticGateTests(unittest.TestCase):
    def snap(self, **kw):
        base = dict(utterance_id="u1", revision=2, captured_at=10, epoch=3,
                    assistant_speaking=False, user_floor_held=True, pause_ms=600)
        return GateSnapshot(**(base | kw))

    def run_gate(self, snapshot=None, advisory=None, **kw):
        now = kw.pop("now", 10.1)
        return decide(snapshot or self.snap(), advisory or {"intent":"listener_cue", "route":"speaker", "confidence":.9},
                      now=now, current_utterance_id="u1", current_revision=2,
                      current_epoch=3, **kw)

    def test_fresh_listener_candidate_is_only_advisory_eligible_when_local_timing_allows(self):
        self.assertTrue(self.run_gate().eligible)
        self.assertFalse(self.run_gate(self.snap(pause_ms=100)).eligible)
        self.assertFalse(self.run_gate(self.snap(speech_active=True)).eligible)
        self.assertFalse(self.run_gate(self.snap(assistant_speaking=True)).eligible)

    def test_revision_epoch_ttl_and_confidence_fail_closed(self):
        self.assertEqual(self.run_gate(self.snap(revision=1)).reason, "stale_revision")
        self.assertEqual(self.run_gate(self.snap(epoch=4)).reason, "stale_revision")
        self.assertEqual(self.run_gate(now=11).reason, "expired_snapshot")
        self.assertEqual(self.run_gate(advisory={"intent":"take_turn", "route":"speaker", "confidence":.2}).reason,
                         "low_confidence")

    def test_local_quiet_veto_precedes_semantic_hint(self):
        d = self.run_gate(self.snap(quiet_requested=True), {"intent":"listener_cue", "route":"speaker", "confidence":1})
        self.assertFalse(d.eligible)
        self.assertEqual(d.reason, "local_listener_ineligible")
        # A quiet preference suppresses MIST's optional cue, while explicit
        # user turns and corrections still reach the speaker route.
        d = self.run_gate(self.snap(quiet_requested=True, host_turn_ready=True),
                          {"intent":"take_turn", "route":"speaker", "confidence":1})
        self.assertTrue(d.eligible)

    def test_fresh_correction_can_yield_without_waiting_for_floor_transfer_flag(self):
        d = self.run_gate(self.snap(assistant_speaking=True, speech_active=False, user_floor_held=False),
                          {"intent":"yield", "route":"speaker", "confidence":.95})
        self.assertTrue(d.eligible)
        self.assertEqual(d.reason, "accepted")

    def test_take_turn_waits_for_host_finalization_and_no_active_speech(self):
        advisory={"intent":"take_turn", "route":"speaker", "confidence":.95}
        self.assertFalse(self.run_gate(self.snap(host_turn_ready=False), advisory).eligible)
        self.assertFalse(self.run_gate(self.snap(host_turn_ready=True, speech_active=True), advisory).eligible)
        self.assertTrue(self.run_gate(self.snap(host_turn_ready=True), advisory).eligible)

    def test_explicit_stop_is_immediate_local_control(self):
        d = self.run_gate(self.snap(revision=0, epoch=999), None, current_trusted_local_stop=True)
        self.assertTrue(d.local_stop)
        self.assertEqual(d.reason, "local_explicit_stop")

    def test_expression_is_bounded_and_sticky_requires_expression(self):
        d = self.run_gate(advisory={"intent":"take_turn", "route":"speaker", "confidence":.9,
                                    "expression":"warm", "sticky":True})
        self.assertEqual((d.expression, d.sticky), ("warm", True))
        d = self.run_gate(advisory={"intent":"take_turn", "route":"speaker", "confidence":.9,
                                    "expression":"x"*49, "sticky":True})
        self.assertIsNone(d.expression)
        self.assertFalse(d.sticky)

    def test_compaction_preserves_order_pinned_and_atomic_receipt_groups(self):
        rows = [{"id": x, "text": x} for x in "abcdef"]
        kept = validate_compaction(rows, ["e", "a", "b", "c"], pinned_ids={"a"}, groups=[["b", "c"]])
        self.assertEqual([r["id"] for r in kept], ["a", "b", "c", "e"])
        with self.assertRaises(ValueError):
            validate_compaction(rows, ["a", "b"], pinned_ids={"a"}, groups=[["b", "c"]])
        with self.assertRaises(ValueError):
            validate_compaction(rows, ["b", "c"], pinned_ids={"a"}, groups=[])


if __name__ == "__main__":
    unittest.main()
