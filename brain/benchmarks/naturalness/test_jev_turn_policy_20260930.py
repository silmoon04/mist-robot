import asyncio
import threading
import time

import pytest

from jev_turn_policy_20260930 import JEVTurnPolicy, TurnSnapshot


def snap(**changes):
    base = dict(endpoint_id="e1", epoch=2, revision=1, transcript="I think",
                event="candidate_endpoint", local_turn_ready=True)
    base.update(changes)
    return TurnSnapshot(**base)


def answer(choice="wait", *, usage=None):
    return {"status": "ok", "response": {"answers": {"turn_intent": {"choice": choice}},
                                      "usage": usage or {"input_tokens": 22, "output_tokens": 3}},
            "wall_latency_ms": 12}


class FakeClient:
    def __init__(self, response=None, delay=0):
        self.response = response or answer()
        self.delay = delay
        self.calls = []

    def decide(self, state, questions):
        self.calls.append((state, questions))
        time.sleep(self.delay)
        return self.response


@pytest.mark.asyncio
async def test_payload_contains_history_and_trusted_state_without_per_partial_calls():
    client = FakeClient(answer("take_turn"))
    policy = JEVTurnPolicy(client)
    s = snap(transcript="Can you help?", short_history=(("user", "Earlier question"),
                                                     ("assistant", "Sure")),
             assistant_is_speaking=True)
    task = policy.submit(s)
    assert task is policy.submit(s)
    result = await task
    assert result.decision == "take_turn" and result.source == "jev"
    assert result.usage == {"input_tokens": 22, "output_tokens": 3}
    assert len(client.calls) == 1
    state = client.calls[0][0]
    assert state["latest_user_transcript"] == "Can you help?"
    assert state["short_history"][-1] == {"role": "assistant", "text": "Sure"}
    assert state["assistant_is_speaking"] and state["local_turn_ready"]
    policy.close()


@pytest.mark.asyncio
async def test_wait_grace_is_bounded_and_resumed_speech_invalidates():
    policy = JEVTurnPolicy(FakeClient(answer("wait")), grace_ms=80)
    result = await policy.submit(snap())
    assert result.decision == "wait" and result.hold_until is not None
    assert 0 < result.hold_until - time.monotonic() <= .081
    policy.update_current(snap(revision=2, transcript="I think we should", speech_active=True))
    assert not policy._applicable(snap())
    policy.close()


@pytest.mark.asyncio
async def test_timeout_uses_local_endpoint_and_retains_late_usage():
    finished = threading.Event()

    class Slow(FakeClient):
        def decide(self, state, questions):
            self.calls.append((state, questions))
            time.sleep(.08)
            finished.set()
            return answer("wait", usage={"input_tokens": 40})

    client = Slow()
    policy = JEVTurnPolicy(client, deadline_ms=10)
    result = await policy.submit(snap())
    assert result.decision == "take_turn" and result.source == "deadline_fallback"
    assert result.hold_until is None
    assert finished.wait(.2)
    assert policy.outcomes[(2, "e1")]["response"]["usage"]["input_tokens"] == 40
    policy.close()


@pytest.mark.asyncio
async def test_stale_revision_epoch_and_local_state_cannot_apply():
    client = FakeClient(answer("yield"), delay=.03)
    policy = JEVTurnPolicy(client)
    task = policy.submit(snap())
    await asyncio.sleep(.005)
    policy.update_current(snap(revision=2, transcript="I think, actually"))
    result = await task
    assert not result.applicable and result.decision == "uncertain" and result.source == "stale"
    for changed in (snap(epoch=3), snap(assistant_is_speaking=True),
                    snap(local_turn_ready=False), snap(speech_active=True)):
        policy.update_current(changed)
        assert not policy._applicable(snap())
    policy.close()


@pytest.mark.asyncio
async def test_unknown_choice_error_and_busy_remote_fallback():
    policy = JEVTurnPolicy(FakeClient(answer("unknown")))
    result = await policy.submit(snap())
    assert result.decision == "take_turn" and result.source == "invalid_choice_fallback"
    policy.close()

    slow = FakeClient(answer("yield"), delay=.08)
    policy = JEVTurnPolicy(slow, deadline_ms=10)
    await policy.submit(snap())
    result = await policy.submit(snap(endpoint_id="e2", revision=2))
    assert result.decision == "take_turn" and result.source == "busy_fallback"
    assert len(slow.calls) == 1
    policy.close()


@pytest.mark.asyncio
async def test_reliable_local_stop_bypasses_jev_and_quoted_stop_does_not():
    client = FakeClient(answer("wait"))
    policy = JEVTurnPolicy(client)
    direct = await policy.submit(snap(transcript="Stop now", explicit_local_stop=True))
    assert direct.decision == "yield" and direct.source == "local_explicit_stop"
    quoted = await policy.submit(snap(endpoint_id="e2", revision=2,
                                      transcript='She said "stop talking" yesterday'))
    assert quoted.decision == "wait" and quoted.source == "jev"
    assert len(client.calls) == 1
    policy.close()


@pytest.mark.asyncio
async def test_overlap_requires_stability_and_backchannel_is_incoming_only():
    client = FakeClient(answer("keep_speaking"))
    policy = JEVTurnPolicy(client)
    unstable = await policy.submit(snap(event="stable_overlap", overlap_stable=False,
                                        assistant_is_speaking=True, local_turn_ready=False))
    assert unstable.source == "unstable_overlap"
    stable = await policy.submit(snap(endpoint_id="e2", event="stable_overlap",
                                      overlap_stable=True, transcript="Mm-hm",
                                      assistant_is_speaking=True, local_turn_ready=False))
    assert stable.decision == "keep_speaking"
    assert "outgoing" in client.calls[0][1]["turn_intent"]["instructions"]
    policy.close()


@pytest.mark.asyncio
async def test_semantic_answer_cannot_override_trusted_local_readiness_or_speaking():
    policy = JEVTurnPolicy(FakeClient(answer("take_turn")))
    result = await policy.submit(snap(local_turn_ready=False, user_floor_held=True))
    assert result.decision == "wait" and result.source == "local_state_fallback"
    policy.close()

    policy = JEVTurnPolicy(FakeClient(answer("keep_speaking")))
    result = await policy.submit(snap(assistant_is_speaking=False))
    assert result.decision == "take_turn" and result.source == "local_state_fallback"
    policy.close()


@pytest.mark.asyncio
async def test_drain_captures_late_usage_before_trial_close():
    policy = JEVTurnPolicy(FakeClient(answer("wait", usage={"input_tokens": 91}), delay=.05),
                           deadline_ms=5)
    first = await policy.submit(snap())
    assert first.source == "deadline_fallback" and first.usage is None
    assert await policy.aclose(timeout_s=.2)
    assert policy.outcomes[(2, "e1")]["response"]["usage"]["input_tokens"] == 91


@pytest.mark.asyncio
async def test_drain_reports_unresolved_request_instead_of_hiding_it():
    policy = JEVTurnPolicy(FakeClient(delay=.08), deadline_ms=5)
    await policy.submit(snap())
    assert not await policy.aclose(timeout_s=.005)
    await asyncio.sleep(.1)
    assert (2, "e1") in policy.outcomes
