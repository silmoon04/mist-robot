"""Cancelable JEV transport for the isolated speech benchmark.

This is a sibling of the frozen synchronous benchmark client. It shares the
pinned request and response contract without changing previous artifacts.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx

try:
    from .jev_comparison_20260929 import (API_URL, INPUT_USD_PER_MILLION,
                                          MODEL, validate_answers)
except ImportError:
    from jev_comparison_20260929 import (API_URL, INPUT_USD_PER_MILLION,
                                         MODEL, validate_answers)


class AsyncJevClient:
    """One HTTP request per decision, no retries; cancellation closes the request."""

    def __init__(self, api_key: str, *, timeout_s: float = 2,
                 transport: httpx.AsyncBaseTransport | None = None):
        if not api_key or timeout_s <= 0:
            raise ValueError("JEV API key and positive timeout required")
        self._api_key = api_key
        self.timeout_s = timeout_s
        self.transport_name = "httpx_async_pooled_client"
        self._http = httpx.AsyncClient(
            timeout=timeout_s, transport=transport, follow_redirects=False,
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=4))

    async def aclose(self) -> None:
        await self._http.aclose()

    async def decide(self, state: str | dict | list, questions: dict) -> dict[str, Any]:
        if not isinstance(state, (str, dict, list)) or not isinstance(questions, dict) or not questions:
            raise ValueError("state and nonempty questions required")
        body = json.dumps({"state": state, "model": MODEL, "questions": questions},
                          ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = {"Authorization": "Bearer " + self._api_key,
                   "Content-Type": "application/json"}
        started = time.perf_counter()
        row: dict[str, Any] = {"status": "error", "request_model": MODEL, "http_status": None,
                               "wall_latency_ms": None, "error_type": None,
                               "response": None, "usage_known": False,
                               "estimated_input_cost_usd": None, "transport": self.transport_name}
        try:
            response = await self._http.post(API_URL, content=body, headers=headers)
            row["http_status"] = response.status_code
            if response.status_code >= 400:
                row["error_type"] = "http_error"
                return row
            row["response"] = validate_answers(questions, response.json())
            row["status"] = "ok"
            tokens = row["response"]["usage"]["input_tokens"]
            row["usage_known"] = tokens is not None
            if tokens is not None:
                row["estimated_input_cost_usd"] = tokens * INPUT_USD_PER_MILLION / 1_000_000
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException:
            row["error_type"] = "timeout"
        except httpx.RequestError:
            row["error_type"] = "network_error"
        except (ValueError, UnicodeError):
            row["error_type"] = "response_validation_error"
        finally:
            row["wall_latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return row
