"""Small, opt-in JEV connection-lifetime diagnostic. No speech or quality scoring.

Run only after the speech benchmark has finished. Twelve requests maximum:
two keepalive settings x two repetitions x cold/immediate/8-second-idle.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import httpx

try:
    from .jev_comparison_20260929 import API_URL, MODEL, validate_answers
    from .jev_turn_policy_20260930 import QUESTION, TurnSnapshot
except ImportError:
    from jev_comparison_20260929 import API_URL, MODEL, validate_answers
    from jev_turn_policy_20260930 import QUESTION, TurnSnapshot


HERE = Path(__file__).resolve().parent
DEFAULT_ENV = Path.home() / "Downloads/03_Programming_Projects/misc/.env"
DEFAULT_OUTPUT_PARENT = HERE.parents[1] / "results" / "flux-scribe-jev-20260930"
TIMEOUT_S = 2.0
IDLE_S = 8.0
EXPIRIES_S = (5.0, 60.0)
REPETITIONS = 2
STATE = TurnSnapshot(endpoint_id="connection-probe", epoch=0, revision=0,
                     transcript="Can you help me with this?", event="candidate_endpoint",
                     local_turn_ready=True).provider_state()


def load_exact_key(path: Path) -> str:
    """Load the exact JEV_API_KEY assignment from the requested file only."""
    values = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip().removeprefix("export ").strip() == "JEV_API_KEY":
            values.append(value.strip().strip("\"'"))
    if len(values) != 1 or not values[0]:
        raise ValueError("Expected exactly one nonempty JEV_API_KEY in the specified env file")
    return values[0]


def connection_evidence(events: list[dict]) -> dict:
    names = [event["name"] for event in events]
    tcp = any(name.startswith("connection.connect_tcp.") for name in names)
    tls = any(name.startswith("connection.start_tls.") for name in names)
    pool = any(name.startswith("connection_pool.") for name in names)
    return {
        "tcp_connect_observed": tcp,
        "tls_handshake_observed": tls,
        "reuse_inference": ("new_connection_observed" if tcp or tls else
                            "possible_reuse_no_connect_event" if events else
                            "unknown_no_trace_events"),
        "pool_event_observed": pool,
    }


async def one_request(client: httpx.AsyncClient, key: str, *, expiry_s: float,
                      repetition: int, phase: str, idle_actual_s: float | None) -> dict:
    started = time.perf_counter()
    events: list[dict] = []

    async def trace(name: str, _info: dict) -> None:
        # httpcore may pass request headers, host, exception, etc. in _info.
        # Preserve only event name and monotonic relative timestamp.
        events.append({"name": name, "at_ms": round((time.perf_counter() - started) * 1000, 3)})

    body = json.dumps({"state": STATE, "model": MODEL, "questions": QUESTION},
                      ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    row = {"expiry_s": expiry_s, "repetition": repetition, "phase": phase,
           "idle_before_s": idle_actual_s, "started_utc": datetime.now(timezone.utc).isoformat(),
           "deadline_ms": int(TIMEOUT_S * 1000), "status": "error", "http_status": None,
           "error_type": None, "usage_known": False, "input_tokens": None,
           "wall_latency_ms": None, "trace_events": events}
    try:
        response = await asyncio.wait_for(client.post(
            API_URL, content=body,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            extensions={"trace": trace}), timeout=TIMEOUT_S)
        row["http_status"] = response.status_code
        if response.status_code >= 400:
            row["error_type"] = "http_error"
        else:
            validated = validate_answers(QUESTION, response.json())
            row["status"] = "ok"
            row["input_tokens"] = validated["usage"]["input_tokens"]
            row["usage_known"] = row["input_tokens"] is not None
    except (asyncio.TimeoutError, httpx.TimeoutException):
        row["error_type"] = "total_deadline_or_http_timeout"
    except httpx.RequestError:
        row["error_type"] = "network_error"
    except (ValueError, UnicodeError):
        row["error_type"] = "response_validation_error"
    finally:
        row["wall_latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
        row.update(connection_evidence(events))
    return row


async def run(key: str, output: Path, *, idle_s: float = IDLE_S) -> list[dict]:
    if idle_s != IDLE_S:
        raise ValueError("Probe protocol fixes the idle interval at eight seconds")
    # Exclusive creation prevents accidental overwrite of earlier evidence.
    output.mkdir(parents=True, exist_ok=False)
    sources = (Path(__file__), HERE / "jev_async_client_20260930.py",
               HERE / "jev_comparison_20260929.py", HERE / "jev_turn_policy_20260930.py")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": MODEL, "endpoint": API_URL, "deadline_ms": 2000,
        "keepalive_expiries_s": EXPIRIES_S, "idle_s": IDLE_S,
        "repetitions": REPETITIONS, "request_cap": 12,
        "state_sha256": hashlib.sha256(json.dumps(STATE, sort_keys=True).encode()).hexdigest(),
        "question_sha256": hashlib.sha256(json.dumps(QUESTION, sort_keys=True).encode()).hexdigest(),
        "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        "limitations": [
            "Connection reuse is inferred from httpcore trace events; missing events do not prove reuse.",
            "A fresh client begins each triplet; this isolates connection lifetime but is not the full speech path.",
            "Serial scheduling and network/provider variability limit causal interpretation.",
            "Timeout or cancellation leaves provider usage unknown unless a validated response arrived.",
            "This measures text API latency, not duplex timing, semantic quality, or naturalness.",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    rows = []
    for repetition in range(1, REPETITIONS + 1):
        for expiry_s in (EXPIRIES_S if repetition == 1 else EXPIRIES_S[::-1]):
            async with httpx.AsyncClient(timeout=TIMEOUT_S, follow_redirects=False,
                    limits=httpx.Limits(max_connections=4, max_keepalive_connections=4,
                                         keepalive_expiry=expiry_s)) as client:
                for phase in ("fresh_client", "immediate_repeat", "after_idle"):
                    idle_actual = None
                    if phase == "after_idle":
                        idle_started = time.perf_counter()
                        await asyncio.sleep(IDLE_S)
                        idle_actual = round(time.perf_counter() - idle_started, 3)
                    rows.append(await one_request(client, key, expiry_s=expiry_s,
                                                  repetition=repetition, phase=phase,
                                                  idle_actual_s=idle_actual))
                    (output / "attempts.json").write_text(
                        json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--output", type=Path, required=True,
                        help="Fresh, nonexistent result directory")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output directory already exists; choose a fresh path")
    key = load_exact_key(args.env)
    rows = asyncio.run(run(key, args.output))
    print(json.dumps({"output": str(args.output), "requests": len(rows),
                      "successes": sum(row["status"] == "ok" for row in rows),
                      "timeouts": sum(row["error_type"] == "total_deadline_or_http_timeout" for row in rows)}))


if __name__ == "__main__":
    main()
