import asyncio

import httpx
import pytest

from jev_connection_probe_20260930 import connection_evidence, one_request, QUESTION


def test_connection_evidence_does_not_claim_reuse_without_positive_evidence():
    assert connection_evidence([])["reuse_inference"] == "unknown_no_trace_events"
    assert connection_evidence([{"name": "connection.connect_tcp.started"}])[
        "reuse_inference"] == "new_connection_observed"
    assert connection_evidence([{"name": "http11.send_request_headers.started"}])[
        "reuse_inference"] == "possible_reuse_no_connect_event"


@pytest.mark.asyncio
async def test_probe_discards_response_text_and_marks_timeout_usage_unknown():
    async def handler(_request):
        await asyncio.sleep(10)
        raise AssertionError("deadline should cancel the transport")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        # Keep the test fast while retaining the production two-second deadline.
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr("jev_connection_probe_20260930.TIMEOUT_S", 0.01)
            row = await one_request(client, "secret", expiry_s=5, repetition=1,
                                    phase="fresh_client", idle_actual_s=None)
    assert row["error_type"] == "total_deadline_or_http_timeout"
    assert row["usage_known"] is False and row["input_tokens"] is None
    assert "secret" not in str(row)
    assert "questions" not in str(row)
    assert QUESTION
