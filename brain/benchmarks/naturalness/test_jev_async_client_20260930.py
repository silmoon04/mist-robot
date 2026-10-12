import asyncio
import json

import httpx
import pytest

from jev_async_client_20260930 import AsyncJevClient
from jev_turn_policy_20260930 import JEVTurnPolicy, QUESTION, TurnSnapshot


def snapshot():
    return TurnSnapshot(endpoint_id="e1", epoch=1, revision=1,
                        transcript="Can you help?", event="candidate_endpoint",
                        local_turn_ready=True)


@pytest.mark.asyncio
async def test_async_transport_uses_pinned_contract_and_validates_usage():
    calls = []

    async def handler(request):
        calls.append((json.loads(request.content), request.headers.get("Authorization")))
        response = {"model": "jev-1.13.0", "answers": {"turn_intent": {
            "type": "choice", "choice": "take_turn", "confidence": .9,
            "probabilities": {key: (1.0 if key == "take_turn" else 0.0)
                              for key in QUESTION["turn_intent"]["criteria"]}}},
            "usage": {"input_tokens": 90, "output_tokens": 4}}
        return httpx.Response(200, json=response)

    client = AsyncJevClient("secret", transport=httpx.MockTransport(handler))
    try:
        policy = JEVTurnPolicy(client)
        advice = await policy.submit(snapshot())
        assert advice.decision == "take_turn" and advice.usage["input_tokens"] == 90
        assert calls[0][0] == {"state": snapshot().provider_state(),
                               "model": "jev-1.13.0", "questions": QUESTION}
        assert calls[0][1] == "Bearer secret"
        assert "secret" not in json.dumps(advice.raw)
        assert await policy.aclose()
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_slow_network_is_canceled_at_total_deadline_and_usage_unknown():
    canceled = asyncio.Event()

    async def handler(request):
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            canceled.set()
            raise
        raise AssertionError("slow request should be canceled")

    client = AsyncJevClient("secret", timeout_s=5,
                            transport=httpx.MockTransport(handler))
    try:
        policy = JEVTurnPolicy(client, deadline_ms=20, total_deadline_ms=80)
        advice = await policy.submit(snapshot())
        assert advice.decision == "take_turn" and advice.source == "deadline_fallback"
        assert advice.usage is None
        assert await policy.aclose()
        assert canceled.is_set()
        outcome = policy.outcomes[(1, "e1")]
        assert outcome["status"] == "error" and outcome["error_type"] == "total_deadline"
        assert outcome["usage_known"] is False
    finally:
        await client.aclose()
