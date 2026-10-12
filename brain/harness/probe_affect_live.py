"""Probe the real qwen-affect trial over its loopback text WebSocket.

Run live_studio separately with --port 9054 and a dedicated --run-dir.
This captures server packets and outgoing PCM, not microphone or browser playback.
The server's public /trial/export endpoint owns trace redaction.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import uuid
import wave

import aiohttp


DEFAULT_OUT = Path(__file__).resolve().parents[1] / "results/dual-model-harness-20260924/live-smoke"
PROMPTS = (
    "Please show a curious face while you answer in one sentence: what is a hinge?",
    "I worked all weekend on an exhibition model, and its stand collapsed before anyone saw it. Please respond briefly.",
    "Keep the current face unchanged. Please say one brief encouraging sentence about trying the print again.",
)
TERMINAL_AFFECT = {"finished", "failed", "skipped_busy"}
TERMINAL_SESSIONS = {"ended", "interrupted", "failed", "aborted", "cancelled", "completed"}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def wave_file(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(pcm)


def trace_timing(export: dict) -> list[dict]:
    """Keep a compact timeline while preserving the full redacted export."""
    selected = {
        "affect_decision", "face", "tool", "transcript_done", "latency",
        "error", "state", "ready", "speech_style",
    }
    timeline = []
    for row in export.get("events", []):
        event = row.get("event", {})
        kind = event.get("type")
        if kind in selected:
            item = {
                "id": row.get("id"),
                "elapsed_ms": row.get("elapsed_ms"),
                "source": row.get("source"),
                "type": kind,
            }
            if kind == "affect_decision":
                item.update(phase=event.get("phase"), outcome=event.get("outcome"),
                            elapsed_affect_ms=event.get("elapsed_ms"),
                            trace=event.get("trace"), decision=event.get("decision"))
            elif kind == "face":
                item.update(source_face=event.get("source"), expression=event.get("expression"),
                            variant=event.get("variant"), persistent=event.get("persistent"))
            elif kind == "tool":
                item.update(name=event.get("name"), result=event.get("result"))
            elif kind == "transcript_done":
                item.update(role=event.get("role"), text=event.get("text"))
            elif kind == "latency":
                item["tts"] = event.get("tts")
            elif kind == "speech_style":
                item.update(delivery=event.get("delivery"), stability=event.get("stability"),
                            model=event.get("model"))
            elif kind == "error":
                item["fatal"] = event.get("fatal", False)
            timeline.append(item)
        elif kind == "debug_model" and event.get("phase") in {
            "thinking_started", "thinking_finished", "model_failed", "text_delta"
        }:
            timeline.append({
                "id": row.get("id"), "elapsed_ms": row.get("elapsed_ms"),
                "source": row.get("source"), "type": "debug_model",
                "phase": event.get("phase"),
                "duration_ms": event.get("duration_ms"),
                "timings": event.get("timings"),
            })
        elif event.get("event") in {
            "tts_connected", "tts_phrase", "tts_complete", "tts_failure"
        }:
            timeline.append({
                "id": row.get("id"), "elapsed_ms": row.get("elapsed_ms"),
                "source": row.get("source"), "type": event.get("event"),
                "backend": event.get("backend"), "first_byte_s": event.get("first_byte_s"),
                "output_s": event.get("output_s"),
            })
    return timeline


async def request_json(http: aiohttp.ClientSession, method: str, url: str, **kwargs) -> dict:
    async with http.request(method, url, **kwargs) as response:
        if response.status != 200:
            raise RuntimeError(f"{method} {url.split('/')[-1]} returned HTTP {response.status}")
        return await response.json()


async def receive_packet(ws: aiohttp.ClientWebSocketResponse, timeout: float) -> dict:
    message = await asyncio.wait_for(ws.receive(), timeout)
    if message.type != aiohttp.WSMsgType.TEXT:
        raise RuntimeError(f"WebSocket closed or returned non-text packet: {message.type.name}")
    packet = json.loads(message.data)
    if not isinstance(packet, dict):
        raise RuntimeError("WebSocket packet was not an object")
    return packet


async def run(args: argparse.Namespace) -> dict:
    args.out.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{args.port}"
    headers = {"Origin": base}
    report = {
        "architecture": "qwen-affect",
        "input_mode": "typed_websocket",
        "port": args.port,
        "prompts": list(PROMPTS),
        "limitations": [
            "Real TrialConversation, speaker provider, affect reader, and ElevenLabs WebSocket are used.",
            "Typed input bypasses microphone and acoustic endpointing.",
            "Captured PCM is a server packet receipt; browser playback and human hearing were not tested.",
            "Synthetic playback_state=false is sent after each captured reply to clear server playback bookkeeping.",
        ],
        "turns": [],
        "status": "incomplete",
    }
    trace_id = None
    audio = bytearray()
    client_events: list[dict] = []
    try:
        timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_connect=10)
        async with aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True), timeout=timeout
        ) as http:
            await request_json(http, "POST", base + "/trial/bootstrap", headers=headers, json={})
            catalog = await request_json(http, "GET", base + "/trial/catalog")
            architecture = next(
                (item for item in catalog.get("architectures", []) if item.get("id") == "qwen-affect"),
                None,
            )
            if architecture is None or not architecture.get("available"):
                report["availability"] = {
                    "listed": architecture is not None,
                    "available": bool(architecture and architecture.get("available")),
                    "missing_variable_names": architecture.get("missing", []) if architecture else [],
                }
                raise RuntimeError("qwen-affect is unavailable in the live catalog")
            report["availability"] = {"listed": True, "available": True}
            async with http.ws_connect(
                base + "/trial/voice?architecture=qwen-affect", headers=headers,
                heartbeat=20, max_msg_size=4 * 1024 * 1024,
            ) as ws:
                startup_deadline = time.monotonic() + args.startup_timeout
                while time.monotonic() < startup_deadline:
                    packet = await receive_packet(ws, min(5, startup_deadline - time.monotonic()))
                    kind = packet.get("type")
                    client_events.append({"type": kind, "at_monotonic": time.monotonic()})
                    if kind == "studio_session":
                        trace_id = packet.get("trace_id")
                        report["trace_id"] = trace_id
                    elif kind == "ready":
                        report["ready"] = {
                            "typed_input_supported": packet.get("typed_input_supported"),
                            "provider": packet.get("provider"),
                            "speech_backend": packet.get("speech_backend"),
                            "startup": packet.get("startup"),
                        }
                        break
                    elif kind == "error" and packet.get("fatal"):
                        raise RuntimeError("TrialConversation startup returned a fatal error")
                else:
                    raise TimeoutError("TrialConversation did not become ready")

                for number, prompt in enumerate(PROMPTS, 1):
                    turn = {
                        "number": number,
                        "prompt": prompt,
                        "user_done": False,
                        "assistant_done": False,
                        "affect_terminal": False,
                        "tts_complete": False,
                        "audio_chunks": 0,
                        "audio_bytes": 0,
                        "faces": [],
                        "tools": [],
                        "errors": [],
                    }
                    report["turns"].append(turn)
                    turn_audio = bytearray()
                    sent = time.monotonic()
                    turn["sent_monotonic"] = sent
                    await ws.send_json({"type": "text", "text": prompt})
                    deadline = sent + args.turn_timeout
                    last_audio = sent
                    while time.monotonic() < deadline:
                        complete = (
                            turn["assistant_done"] and turn["affect_terminal"]
                            and turn["tts_complete"]
                        )
                        if complete and time.monotonic() - last_audio >= 0.6:
                            break
                        remaining = min(1.0, deadline - time.monotonic())
                        if remaining <= 0:
                            break
                        try:
                            packet = await receive_packet(ws, remaining)
                        except asyncio.TimeoutError:
                            continue
                        kind = packet.get("type")
                        now = time.monotonic()
                        client_events.append({"turn": number, "type": kind,
                                              "at_ms_since_send": round((now - sent) * 1000, 1)})
                        if kind == "audio":
                            raw = base64.b64decode(packet.get("pcm", ""), validate=True)
                            if packet.get("sample_rate") != 24000 or len(raw) % 2:
                                turn["errors"].append("invalid_audio_packet")
                            else:
                                audio.extend(raw)
                                turn_audio.extend(raw)
                                turn["audio_chunks"] += 1
                                turn["audio_bytes"] += len(raw)
                                last_audio = now
                        elif kind == "transcript_done":
                            if packet.get("role") == "user":
                                turn["user_done"] = True
                                turn["user_done_ms"] = round((now - sent) * 1000, 1)
                            elif packet.get("role") == "assistant":
                                turn["assistant_done"] = True
                                turn["assistant_done_ms"] = round((now - sent) * 1000, 1)
                                turn["assistant_text"] = packet.get("text", "")
                        elif kind == "affect_decision":
                            if packet.get("phase") in TERMINAL_AFFECT:
                                turn["affect_terminal"] = True
                                turn["affect_outcome"] = packet.get("outcome")
                                turn["affect_status"] = packet.get("trace", {}).get("status")
                                turn["affect_elapsed_ms"] = packet.get("elapsed_ms")
                                turn["affect_finished_ms"] = round((now - sent) * 1000, 1)
                        elif kind == "latency" and "tts" in packet:
                            turn["tts_complete"] = True
                            turn["tts"] = packet["tts"]
                        elif kind == "face":
                            turn["faces"].append({
                                "source": packet.get("source"),
                                "expression": packet.get("expression"),
                                "variant": packet.get("variant"),
                                "persistent": packet.get("persistent"),
                                "at_ms_since_send": round((now - sent) * 1000, 1),
                            })
                        elif kind == "tool":
                            turn["tools"].append({
                                "name": packet.get("name"),
                                "status": packet.get("result", {}).get("status"),
                            })
                        elif kind == "error":
                            turn["errors"].append("server_error")
                            if packet.get("fatal"):
                                raise RuntimeError("Fatal error during turn")
                    turn["deadline_reached"] = time.monotonic() >= deadline
                    turn["audio_seconds"] = round(len(turn_audio) / 48000, 3)
                    if turn_audio:
                        wave_file(args.out / f"turn-{number}.wav", turn_audio)
                        turn["audio_sha256"] = hashlib.sha256(turn_audio).hexdigest()
                    if not turn["assistant_done"]:
                        raise TimeoutError(f"Assistant did not complete turn {number}")
                    await ws.send_json({"type": "playback_state", "playing": False})
                await ws.close()

            if trace_id:
                for _ in range(20):
                    sessions = await request_json(http, "GET", base + "/trial/sessions")
                    session = next(
                        (item for item in sessions.get("sessions", [])
                         if item.get("trace_id") == trace_id), None
                    )
                    if session and session.get("status") in TERMINAL_SESSIONS:
                        report["session_status"] = session.get("status")
                        report["session_reason"] = session.get("reason")
                        break
                    await asyncio.sleep(0.5)
                export = await request_json(
                    http, "GET", base + "/trial/export", params={"session": trace_id}
                )
                write_json(args.out / "public-trace.json", export)
                write_json(args.out / "timeline.json", trace_timing(export))
                report["trace_events"] = len(export.get("events", []))
                report["session_status"] = export.get("session", {}).get("status")
                report["session_reason"] = export.get("session", {}).get("reason")
        if audio:
            wave_file(args.out / "all-turns.wav", audio)
            report["audio"] = {
                "pcm_bytes": len(audio),
                "duration_s": round(len(audio) / 48000, 3),
                "pcm_sha256": hashlib.sha256(audio).hexdigest(),
            }
        report["status"] = "completed" if len(report["turns"]) == len(PROMPTS) else "incomplete"
    except Exception as error:
        report["status"] = "failed"
        report["failure_type"] = type(error).__name__
        report["failure_note"] = str(error)[:180]
    finally:
        if audio and not (args.out / "all-turns.wav").exists():
            wave_file(args.out / "all-turns.wav", audio)
            report["audio"] = {
                "pcm_bytes": len(audio),
                "duration_s": round(len(audio) / 48000, 3),
                "pcm_sha256": hashlib.sha256(audio).hexdigest(),
            }
        if trace_id and not (args.out / "public-trace.json").exists():
            try:
                async with aiohttp.ClientSession(
                    cookie_jar=aiohttp.CookieJar(unsafe=True),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as recovery_http:
                    await request_json(
                        recovery_http, "POST", base + "/trial/bootstrap",
                        headers=headers, json={},
                    )
                    export = await request_json(
                        recovery_http, "GET", base + "/trial/export",
                        params={"session": trace_id},
                    )
                    write_json(args.out / "public-trace.json", export)
                    write_json(args.out / "timeline.json", trace_timing(export))
                    report["trace_events"] = len(export.get("events", []))
                    report["session_status"] = export.get("session", {}).get("status")
                    report["session_reason"] = export.get("session", {}).get("reason")
            except Exception as recovery_error:
                report["trace_recovery_error_type"] = type(recovery_error).__name__
        write_json(args.out / "probe-summary.json", report)
        write_json(args.out / "client-event-timing.json", client_events)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9054)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--startup-timeout", type=float, default=45)
    parser.add_argument("--turn-timeout", type=float, default=65)
    args = parser.parse_args()
    if args.out is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.out = DEFAULT_OUT / f"probe-{stamp}-{uuid.uuid4().hex[:6]}"
    result = asyncio.run(run(args))
    print(json.dumps({
        "status": result["status"],
        "out": str(args.out),
        "trace_id": result.get("trace_id"),
        "turns": len(result["turns"]),
        "audio_bytes": result.get("audio", {}).get("pcm_bytes", 0),
        "failure_type": result.get("failure_type"),
    }))
    if result["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
