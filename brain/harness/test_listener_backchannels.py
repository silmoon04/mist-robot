import unittest

from brain.duplex.listener_backchannels import ListenerBackchannelPolicy


WORDS = "I have been thinking about what you said earlier and it is still on my mind"
OPEN = "I have been thinking about what you said earlier and it is still on my mind, because"


class ListenerBackchannelPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = ListenerBackchannelPolicy()

    def observe(self, now, *, text=OPEN, floor="floor-1", voiced=False,
                pause=450, finalized=False, **flags):
        return self.policy.evaluate(
            now,
            floor_id=floor,
            transcript=text,
            speech_active=voiced,
            pause_ms=pause,
            finalized=finalized,
            **flags,
        )

    def test_sustained_held_clause_gets_one_short_lived_noncommittal_candidate(self):
        self.observe(0.0, voiced=True)
        early = self.observe(4.8, voiced=False)
        self.assertFalse(early.emit)
        self.assertEqual(early.reason, "floor_not_sustained")

        ready = self.observe(5.1)
        self.assertTrue(ready.emit)
        self.assertEqual(ready.cue, "mhm")
        self.assertEqual(ready.urgency, "low")
        self.assertTrue(ready.cancel_if_user_resumes)
        self.assertEqual(ready.trigger, "sustained_floor+short_pause+unfinished_nonquestion_partial")
        self.assertEqual(self.observe(5.15), ready)  # no duplicate reservation

    def test_quick_or_brief_pauses_do_not_create_cues(self):
        self.observe(0.0, voiced=True)
        self.assertEqual(self.observe(5.0, pause=200).reason, "pause_too_short")
        self.assertEqual(self.observe(5.0, pause=1500).reason, "pause_too_long")
        self.assertEqual(self.observe(5.0, text="We went to the market yesterday").reason,
                         "too_few_words")

    def test_complete_clause_without_a_continuation_cue_stays_quiet(self):
        self.observe(0.0, voiced=True)
        result = self.observe(
            6.0,
            text="I have been thinking about what you said earlier and it is still on my mind",
        )
        self.assertFalse(result.emit)
        self.assertEqual(result.reason, "no_continuation_signal")

    def test_comma_boundary_and_open_clause_are_both_allowed(self):
        self.observe(0.0, voiced=True)
        result = self.observe(5.1, text="I was thinking about what you said, and it reminded me of")
        self.assertTrue(result.emit)

    def test_question_and_completed_or_finalized_turns_are_suppressed(self):
        self.observe(0.0, voiced=True)
        for text in (
            "I have been thinking about what you said earlier, because what do you think?",
            "I have been thinking about what you said earlier and it is still on my mind.",
        ):
            result = self.observe(5.2, text=text)
            self.assertFalse(result.emit, text)
            self.assertEqual(result.reason, "question_or_question_boundary")
        self.assertEqual(self.observe(5.2, finalized=True).reason, "turn_finalized")

    def test_embedded_wh_auxiliary_statement_can_qualify_at_a_continuation_pause(self):
        self.observe(0.0, voiced=True)
        text = "I have been learning what is changing in the project and why the deadline matters, because"
        result = self.observe(5.1, text=text)
        self.assertTrue(result.emit, result.reason)

    def test_unpunctuated_direct_and_tag_questions_remain_suppressed(self):
        cases = (
            "What do you think about what is changing today",
            "Do you think we should move ahead with this plan",
            "I have thought about the plan, and we should move ahead, don't you think",
        )
        for text in cases:
            with self.subTest(text=text):
                policy = ListenerBackchannelPolicy()
                policy.evaluate(0.0, floor_id="f", transcript=text,
                                speech_active=True, pause_ms=0)
                result = policy.evaluate(6.0, floor_id="f", transcript=text,
                                         speech_active=False, pause_ms=450)
                self.assertEqual(result.reason, "question_or_question_boundary")

    def test_user_can_explicitly_request_quiet_or_speaking_practice(self):
        self.observe(0.0, voiced=True)
        self.assertEqual(self.observe(5.2, quiet_requested=True).reason, "user_requested_quiet")
        self.assertEqual(self.observe(5.2, speaking_practice=True).reason, "user_requested_quiet")
        self.assertEqual(
            self.observe(5.2, text="Please let me practice this speech before we talk about it").reason,
            "user_requested_quiet",
        )

    def test_distress_bad_news_and_caller_marked_sensitive_context_are_suppressed(self):
        cases = (
            "My mother died last night and I have not told the family yet, because",
            "I got laid off yesterday and I am still trying to work out what comes next, so",
            "I am scared and I need help figuring out what to do next, because",
        )
        for text in cases:
            policy = ListenerBackchannelPolicy()
            policy.evaluate(0, floor_id="f", transcript=text, speech_active=True, pause_ms=0)
            result = policy.evaluate(8, floor_id="f", transcript=text, speech_active=False, pause_ms=450)
            self.assertEqual(result.reason, "sensitive_or_distress_context", text)
        policy = ListenerBackchannelPolicy()
        policy.evaluate(0, floor_id="f", transcript=OPEN, speech_active=True, pause_ms=0)
        self.assertEqual(policy.evaluate(8, floor_id="f", transcript=OPEN, speech_active=False,
                                         pause_ms=450, sensitive=True).reason,
                         "sensitive_or_distress_context")

    def test_voiced_audio_vetoes_even_if_stt_says_pause_is_ready(self):
        self.observe(0, voiced=True)
        result = self.observe(6, voiced=True)
        self.assertEqual(result.reason, "voiced_audio_active")

    def test_partial_revision_resume_and_expiry_invalidate_before_playback(self):
        self.observe(0, voiced=True)
        candidate = self.observe(5.2)
        self.assertTrue(candidate.emit)
        self.assertFalse(self.policy.is_valid(
            candidate, 5.3, floor_id="floor-1", transcript=OPEN + " we should",
        ))
        resumed = self.observe(5.3, text=OPEN + " we should", voiced=True)
        self.assertEqual(resumed.reason, "voiced_audio_active")
        self.assertFalse(self.policy.is_valid(
            candidate, 5.56, floor_id="floor-1", transcript=OPEN,
        ))
        self.assertFalse(self.policy.playback_started(candidate, 5.56))

    def test_quiet_or_sensitive_context_change_invalidates_an_issued_candidate(self):
        self.observe(0, voiced=True)
        candidate = self.observe(5.2)
        quiet = self.observe(5.25, quiet_requested=True)
        self.assertEqual(quiet.reason, "user_requested_quiet")
        self.assertFalse(self.policy.is_valid(
            candidate, 5.26, floor_id="floor-1", transcript=OPEN,
            quiet_requested=True,
        ))

        policy = ListenerBackchannelPolicy()
        policy.evaluate(0, floor_id="floor-1", transcript=OPEN, speech_active=True, pause_ms=0)
        candidate = policy.evaluate(5.2, floor_id="floor-1", transcript=OPEN,
                                    speech_active=False, pause_ms=450)
        self.assertTrue(candidate.emit)
        self.assertFalse(policy.is_valid(candidate, 5.25, floor_id="floor-1",
                                         transcript=OPEN, sensitive=True))

    def test_floor_change_and_user_resumption_reject_stale_candidate(self):
        self.observe(0, voiced=True)
        candidate = self.observe(5.2)
        self.assertFalse(self.policy.is_valid(
            candidate, 5.25, floor_id="floor-2", transcript=OPEN,
        ))
        self.assertFalse(self.policy.is_valid(
            candidate, 5.25, floor_id="floor-1", transcript=OPEN, voiced_now=True,
        ))

    def test_actual_playback_consumes_one_per_floor_and_starts_global_cooldown(self):
        self.observe(0, voiced=True)
        candidate = self.observe(5.2)
        self.assertTrue(self.policy.playback_started(candidate, 5.25))
        self.assertFalse(self.policy.playback_started(candidate, 5.26))
        self.observe(7.0, floor="floor-2", voiced=True)  # speech-start establishes the new floor
        self.assertEqual(self.observe(13.0, floor="floor-2").reason, "global_cooldown")
        self.assertTrue(self.observe(23.3, floor="floor-2").emit)

    def test_cancelled_or_failed_candidate_does_not_burn_floor_or_cooldown(self):
        self.observe(0, voiced=True)
        candidate = self.observe(5.2)
        self.assertTrue(self.policy.cancel(candidate))
        retry = self.observe(5.3)
        self.assertTrue(retry.emit)
        self.assertTrue(self.policy.cancel(retry))
        self.assertTrue(self.observe(5.4).emit)

    def test_negative_acknowledgement_text_is_never_selected(self):
        self.observe(0, voiced=True)
        self.assertEqual(self.observe(5.2).cue, "mhm")


if __name__ == "__main__":
    unittest.main()
