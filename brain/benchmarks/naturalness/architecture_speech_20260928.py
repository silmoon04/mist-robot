"""Cached-PCM adapter for the 2026-09-28 MIST speech architecture bench.

This module keeps the production TrialConversation, CascadeVoice, STT, speaker,
affect reader, and TTS intact. It only exposes a benchmark context injection,
cached WAV validation, and real-time PCM packetization. Running it as a server
starts an isolated live_studio-compatible service; it never selects port 9053.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import sys
import time
import wave
from datetime import datetime, timezone

BRAIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BRAIN))
from duplex import live_studio

SAMPLE_RATE = 16_000
FRAME_MS = 20
FRAME_BYTES = SAMPLE_RATE * 2 * FRAME_MS // 1000
FIXTURE_DIR = BRAIN / "results" / "e2e_20260924" / "fixtures_v2"
OUTPUT_DIR = BRAIN / "results" / "architecture-cost-20260928" / "speech"


def load_cached_wav(path: Path) -> tuple[bytes, dict]:
    """Return mono PCM16 bytes and a hash/duration record; perform no network IO."""
    raw = path.read_bytes()
    with wave.open(str(path), "rb") as wav:
        actual = (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype())
        expected = (1, 2, SAMPLE_RATE, "NONE")
        if actual != expected or wav.getnframes() <= 0:
            raise ValueError(f"Unsupported or empty cached WAV: {path.name}")
        pcm = wav.readframes(wav.getnframes())
        if len(pcm) != wav.getnframes() * 2:
            raise ValueError(f"Truncated cached WAV: {path.name}")
    return pcm, {
        "file": path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "sample_rate": SAMPLE_RATE,
        "duration_ms": round(len(pcm) / (SAMPLE_RATE * 2) * 1000, 3),
        "bytes": len(pcm),
        "synthetic": True,
    }


def pcm_frames(pcm: bytes):
    """Yield 20 ms payloads and their due offsets, without padding the last frame."""
    if len(pcm) % 2:
        raise ValueError("PCM16 payload has an odd byte length")
    for offset in range(0, len(pcm), FRAME_BYTES):
        chunk = pcm[offset:offset + FRAME_BYTES]
        yield offset // 2, chunk


async def send_cached_pcm(ws, pcm: bytes, *, clock=time.perf_counter, sleep=asyncio.sleep,
                          on_sample=None) -> dict:
    """Send cached PCM as ordinary production mic packets at original real-time cadence."""
    if len(pcm) % 2 or not pcm:
        raise ValueError("PCM16 payload must be nonempty and sample-aligned")
    started = clock()
    sent = []
    for sample_offset, chunk in pcm_frames(pcm):
        due = started + sample_offset / SAMPLE_RATE
        delay = due - clock()
        if delay > 0:
            await sleep(delay)
        await ws.send_json({"type": "mic", "pcm": base64.b64encode(chunk).decode("ascii")})
        event = {"sample_offset": sample_offset, "t_ms": round((clock() - started) * 1000, 3),
                 "payload_bytes": len(chunk)}
        sent.append(event)
        if on_sample:
            on_sample(event)
    last_sample_ms = (len(pcm) // 2 - 1) / SAMPLE_RATE * 1000
    return {
        "first_packet_ms": sent[0]["t_ms"],
        "last_packet_sent_ms": sent[-1]["t_ms"],
        "input_last_sample_ms": round(last_sample_ms, 3),
        "packet_count": len(sent),
        "packet_ms": FRAME_MS,
        "schedule_lateness_ms_max": round(max(
            max(0.0, event["t_ms"] - event["sample_offset"] / SAMPLE_RATE * 1000)
            for event in sent), 3),
    }


def sample_metrics(events: list[dict]) -> dict:
    """Summarize browser-client receive events on one monotonic millisecond clock."""
    def first(pred):
        return next((e["t_ms"] for e in events if pred(e)), None)
    user_final = first(lambda e: e.get("type") == "transcript_done" and e.get("role") == "user")
    model_text = first(lambda e: e.get("type") == "transcript_delta" and e.get("role") == "assistant"
                       and bool(str(e.get("text", "")).strip()))
    tts_audio = first(lambda e: e.get("type") == "audio")
    tts_done = first(lambda e: e.get("event") == "tts_complete" or e.get("type") == "tts_complete")
    cancel = first(lambda e: e.get("type") in ("audio_reset", "playback_cancelled")
                   or e.get("event") in ("playback_interrupt", "interrupted_generation_discarded"))
    anchor = next((e.get("input_last_sample_ms") for e in events
                   if e.get("input_last_sample_ms") is not None), None)
    return {
        "user_transcript_final_ms": user_final,
        "first_model_text_ms": model_text,
        "first_tts_audio_packet_ms": tts_audio,
        "tts_complete_ms": tts_done,
        "cancel_ms": cancel,
        "stage_durations_from_input_last_sample_ms": {
            "user_transcript_final": _delta(user_final, anchor),
            "first_model_text": _delta(model_text, anchor),
            "first_tts_audio_packet": _delta(tts_audio, anchor),
            "tts_complete": _delta(tts_done, anchor),
            "cancel": _delta(cancel, anchor),
        },
        "playback_or_heard_onset_ms": None,
    }


def _delta(value, anchor):
    return round(value - anchor, 3) if value is not None and anchor is not None else None


class CachedBenchTrialConversation(live_studio.TrialConversation):
    """Adds only a test-only context injection needed to seed interrupt scenarios."""
    async def handle(self, packet):
        if packet.get("type") == "bench_context":
            text = packet.get("text")
            if not isinstance(text, str) or not text.strip() or len(text) > 1000:
                raise ValueError("Benchmark context must be 1 to 1000 characters")
            await self.voice.context(text.strip())
            self.journal.record({"type": "bench_context_queued", "text": text.strip(),
                                 "playback_verified": False}, "benchmark_adapter")
            return
        await super().handle(packet)

    async def emit(self, event):
        if isinstance(event, dict):
            event = dict(event)
            if event.get("type") in ("transcript_delta", "transcript_done"):
                if event.get("role") == "assistant":
                    event["benchmark_turn_id"] = getattr(self, "_bench_output_turn_id", None)
                    event["benchmark_parent_user_turn_id"] = getattr(self, "_bench_parent_user_turn_id", None)
                elif event.get("role") == "user":
                    event["benchmark_turn_id"] = getattr(self, "_bench_user_turn_id", None)
            elif event.get("type") == "audio":
                event["benchmark_turn_id"] = getattr(self, "_bench_output_turn_id", None)
                event["benchmark_parent_user_turn_id"] = getattr(self, "_bench_parent_user_turn_id", None)
        await super().emit(event)

    async def realtime_event(self, event):
        turn = event.get("turn", {}) if isinstance(event, dict) else {}
        if event.get("type") == "turn.created":
            if turn.get("role") == "user":
                self._bench_user_turn_id = turn.get("id")
            elif turn.get("role") == "assistant":
                self._bench_output_turn_id = turn.get("id")
                self._bench_parent_user_turn_id = getattr(self, "_bench_user_turn_id", None)
        await super().realtime_event(event)


CASES = {
    "ordinary_question": {"case_id": "mist.naturalness.v1.audio_phrase_seam",
        "file": "audio_phrase_seam-1.wav", "seed": None, "delay_after_seed_audio_ms": None},
    "incomplete_pause": {"case_id": "mist.naturalness.v1.audio_long_pause",
        "file": "audio_long_pause-1.wav", "seed": None, "delay_after_seed_audio_ms": None},
    "backchannel": {"case_id": "mist.naturalness.v1.audio_backchannel_yes",
        "file": "audio_backchannel_yes-1.wav",
        "seed": "The bracket has three checks. First the screw clearance, then the fit, then the cable path.",
        "delay_after_seed_audio_ms": 900},
    "stop": {"case_id": "mist.naturalness.v1.audio_stop", "file": "audio_stop-1.wav",
        "seed": "Let me explain the bracket in three steps. The first thing to check is whether the screw clears the edge, then we can look at how the washer sits on the bracket.",
        "delay_after_seed_audio_ms": 800},
}

ARMS = ("cerebras-balanced", "bench-qwen-responsive", "qwen-affect")
EXTRA_ARMS_BY_CASE = {"ordinary_question": ("qwen-none",), "incomplete_pause": ("qwen-none",)}


async def _read_events(ws, events, audio_chunks, clock, stop_event, playback=None):
    while not stop_event.is_set():
        message = await ws.receive()
        if message.type.name in ("CLOSED", "CLOSE", "ERROR"):
            return
        if message.type.name != "TEXT":
            continue
        packet = json.loads(message.data)
        now = (clock() - events[0]["_clock_start"]) * 1000 if events else 0
        packet["t_ms"] = round(now, 3)
        if packet.get("type") == "audio" and isinstance(packet.get("pcm"), str):
            try:
                chunk = base64.b64decode(packet["pcm"], validate=True)
                audio_chunks.setdefault((packet.get("benchmark_turn_id"), packet.get("epoch", 0)), []).append(
                    (packet.get("sample_rate", 24000), packet.get("seq"), chunk))
            except (ValueError, TypeError):
                packet["audio_capture_error"] = "invalid_pcm_payload"
            packet.pop("pcm", None)
            packet["pcm_bytes"] = len(chunk) if "chunk" in locals() else None
        events.append(packet)
        if playback:
            await playback.observe(packet, clock())


async def _poll_trace(http, base, trace_id, server_events, stop_event):
    import aiohttp
    cursor = 0
    while not stop_event.is_set():
        try:
            async with http.get(base + "/trial/events", params={"session": trace_id,
                                                                  "after": cursor, "limit": 200}) as response:
                if response.status == 200:
                    page = await response.json()
                    for row in page.get("events", []):
                        cursor = max(cursor, int(row.get("id", cursor)))
                        event = row.get("event")
                        if isinstance(event, dict) and (event.get("event") == "tts_complete"
                                or event.get("event") == "tts_failure"
                                or event.get("type") in ("turn.created", "turn.done", "floor_backchannel_kept")):
                            server_events.append({"elapsed_ms": row.get("elapsed_ms"),
                                                  "source": row.get("source"), "event": event})
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            pass
        await asyncio.sleep(.1)


class SoftwarePlaybackClock:
    """Model client queue duration only; it is not a playback or hearing measurement."""
    def __init__(self, ws, events, buffer_ms):
        self.ws, self.events = ws, events
        self.buffer_s = max(0, buffer_ms) / 1000
        self.active = False
        self.queue_end = 0.0
        self.timer = None

    async def observe(self, packet, received_at):
        kind = packet.get("type")
        if kind == "audio_reset":
            self.queue_end = received_at
            if self.timer:
                self.timer.cancel(); self.timer = None
            if self.active:
                await self.ws.send_json({"type": "playback_state", "playing": False})
                self.active = False
                self.events.append({"type": "software_playback_state", "playing": False,
                                    "reason": "server_audio_reset", "timing_basis": "PCM_duration_simulation"})
        elif kind == "audio":
            try:
                sample_rate = int(packet.get("sample_rate", 0))
                payload_bytes = int(packet.get("pcm_bytes", 0))
                if sample_rate <= 0 or payload_bytes <= 0:
                    return
                if not self.active:
                    await self.ws.send_json({"type": "playback_state", "playing": True})
                    self.active = True
                    self.events.append({"type": "software_playback_state", "playing": True,
                                        "reason": "first_received_pcm", "timing_basis": "PCM_duration_simulation"})
                self.queue_end = max(self.queue_end, received_at) + payload_bytes / (sample_rate * 2)
                if self.timer:
                    self.timer.cancel()
                self.timer = asyncio.create_task(self._finish_after_queue())
            except (ValueError, TypeError):
                return

    async def _finish_after_queue(self):
        try:
            while self.active:
                deadline = self.queue_end + self.buffer_s
                await asyncio.sleep(max(0, deadline - time.perf_counter()))
                if time.perf_counter() + .002 < self.queue_end + self.buffer_s:
                    continue
                await self.ws.send_json({"type": "playback_state", "playing": False})
                self.active = False
                self.events.append({"type": "software_playback_state", "playing": False,
                                    "reason": "PCM_duration_queue_drained", "timing_basis": "PCM_duration_simulation"})
        except (asyncio.CancelledError, ConnectionError, RuntimeError):
            return

    async def close(self):
        if self.timer:
            self.timer.cancel()
            await asyncio.gather(self.timer, return_exceptions=True)


async def run_one(http, base, arm, case_name, case, output, *, timeout_s=40):
    import aiohttp
    pcm, input_info = load_cached_wav(FIXTURE_DIR / "audio" / case["file"])
    started = time.perf_counter()
    row = {"architecture_id": arm, "scenario": case_name, "case_id": case["case_id"],
           "status": "running", "input": input_info, "clock_id": "client_perf_counter",
           "events": [], "limitations": [
               "Server packet times do not measure browser scheduling or acoustic playback.",
               "Listening quality is unrated until a human listens to the retained TTS PCM.",
           ]}
    row["events"].append({"_clock_start": started, "type": "clock_anchor", "t_ms": 0})
    socket = None
    audio_chunks = {}
    stop_reader = asyncio.Event()
    stop_trace = asyncio.Event()
    reader = None
    trace_reader = None
    playback = None
    server_events = []
    try:
        async with http.ws_connect(base + f"/trial/voice?architecture={arm}", headers={"Origin": base}, heartbeat=20,
                                   max_msg_size=4 * 1024 * 1024) as ws:
            socket = ws
            buffer_ms = 120 if arm in ("bench-qwen-responsive", "qwen-affect") else 200
            playback = SoftwarePlaybackClock(ws, row["events"], buffer_ms)
            row["playback_clock"] = {"kind": "software_PCM_duration_simulation",
                                     "buffer_ms": buffer_ms,
                                     "physical_or_browser_playback_measured": False}
            reader = asyncio.create_task(_read_events(ws, row["events"], audio_chunks,
                                                      time.perf_counter, stop_reader, playback))
            deadline = time.perf_counter() + 35
            while time.perf_counter() < deadline:
                if any(e.get("type") == "ready" for e in row["events"]):
                    break
                if any(e.get("fatal") for e in row["events"]):
                    raise RuntimeError("TrialConversation reported a fatal startup event")
                await asyncio.sleep(.02)
            else:
                raise TimeoutError("production TrialConversation did not become ready")
            row["ready_ms"] = round((time.perf_counter() - started) * 1000, 3)
            row["trace_id"] = next((e.get("trace_id") for e in row["events"]
                                    if e.get("type") == "studio_session"), None)
            if not row["trace_id"]:
                raise RuntimeError("TrialConversation did not provide a trace identity")
            trace_reader = asyncio.create_task(_poll_trace(http, base, row["trace_id"],
                                                            server_events, stop_trace))
            if case.get("seed"):
                await ws.send_json({"type": "bench_context", "text": case["seed"]})
                row["seed_requested_ms"] = round((time.perf_counter() - started) * 1000, 3)
                # Trigger from first returned audio packet. This is a server transport
                # anchor and must not be described as actual playback onset.
                while time.perf_counter() < started + timeout_s:
                    if any(e.get("type") == "audio" for e in row["events"]):
                        break
                    await asyncio.sleep(.01)
                else:
                    raise TimeoutError("seeded assistant speech produced no returned TTS packet")
                first_seed_audio = next(e["t_ms"] for e in row["events"] if e.get("type") == "audio")
                row["seed_first_tts_packet_ms"] = first_seed_audio
                await asyncio.sleep(case["delay_after_seed_audio_ms"] / 1000)
            row["input_start_ms"] = round((time.perf_counter() - started) * 1000, 3)
            row["seed_turn_id"] = next((e.get("benchmark_turn_id") for e in row["events"]
                                        if e.get("type") == "audio" and e.get("benchmark_turn_id")), None)
            timing = await send_cached_pcm(ws, pcm, on_sample=None)
            row["input_timing"] = timing
            # Declared last sample availability is the end of the final PCM sample,
            # derived from the input's start and sample count, not socket send return.
            row["input_last_sample_ms"] = round(row["input_start_ms"] + timing["input_last_sample_ms"], 3)
            row["events"].append({"type": "input_last_sample", "t_ms": row["input_last_sample_ms"],
                                  "input_last_sample_ms": row["input_last_sample_ms"]})
            # Wait for floor decision and fully drained TTS. Backchannel and stop
            # are explicitly allowed to finish with no new assistant transcript.
            end = time.perf_counter() + timeout_s
            outcome = "bounded_timeout"
            while time.perf_counter() < end:
                input_user = next((e for e in row["events"] if e.get("type") == "transcript_done"
                    and e.get("role") == "user" and e.get("t_ms", -1) >= row["input_start_ms"]), None)
                user_id = input_user.get("benchmark_turn_id") if input_user else None
                correlated_text = [e for e in row["events"] if e.get("type") == "transcript_delta"
                    and e.get("role") == "assistant" and user_id
                    and e.get("benchmark_parent_user_turn_id") == user_id]
                correlated_done = next((e for e in row["events"] if e.get("type") == "transcript_done"
                    and e.get("role") == "assistant" and user_id
                    and e.get("benchmark_parent_user_turn_id") == user_id), None)
                correlated_audio = [e for e in row["events"] if e.get("type") == "audio" and user_id
                    and e.get("benchmark_parent_user_turn_id") == user_id]
                latencies = [e.get("tts", {}) for e in row["events"] if e.get("type") == "latency"
                             and isinstance(e.get("tts"), dict)]
                tts_finished = _tts_sequences_finished(correlated_audio, latencies)
                backchannel_kept = any(e.get("type") == "debug_model"
                    and e.get("phase") == "floor_backchannel_kept" for e in row["events"])
                reset = any(e.get("type") == "audio_reset" and e.get("t_ms", -1) >= row["input_start_ms"]
                            for e in row["events"])
                user_committed = input_user is not None
                if case_name == "backchannel" and backchannel_kept and not reset:
                    # Let the already queued explanation finish so the outcome checks
                    # continuation, while remaining a non-response case.
                    seed_audio = [e for e in row["events"]
                        if e.get("type") == "audio" and e.get("benchmark_turn_id") == row.get("seed_turn_id")]
                    seed_tts_done = _tts_sequences_finished(seed_audio, latencies)
                    if seed_tts_done and not playback.active:
                        outcome = "floor_backchannel_kept_continuing_playback"
                        break
                elif case_name == "stop" and reset and (user_committed or not playback.active):
                    outcome = "server_speech_cancelled_no_reply_required"
                    break
                elif case_name in ("ordinary_question", "incomplete_pause") and correlated_done:
                    if _normal_turn_drained(correlated_done, correlated_audio, latencies, playback.active):
                        outcome = "assistant_turn_complete"
                        break
                await asyncio.sleep(.025)
            row["outcome"] = outcome
            row["status"] = "complete" if outcome != "bounded_timeout" else "timeout"
            row["active_user_turn_id"] = input_user.get("benchmark_turn_id") if input_user else None
            row["metrics"] = _correlated_metrics(row["events"], row["active_user_turn_id"],
                                                 row["input_start_ms"], row["input_last_sample_ms"])
            reset_at = next((e["t_ms"] for e in row["events"] if e.get("type") == "audio_reset"
                             and e.get("t_ms", -1) >= row["input_start_ms"]), None)
            row["server_cancel_reset_ms"] = reset_at
            row["server_cancel_from_input_start_ms"] = (None if reset_at is None else
                round(reset_at - row["input_start_ms"], 3))
            row["server_trace_events"] = server_events
    except Exception as exc:
        row["status"] = "failed"
        row["failure"] = type(exc).__name__
        row["failure_message"] = str(exc)[:240]
    finally:
        if socket and not socket.closed:
            await socket.close()
        stop_reader.set()
        if reader:
            reader.cancel()
            await asyncio.gather(reader, return_exceptions=True)
        stop_trace.set()
        if trace_reader:
            trace_reader.cancel()
            await asyncio.gather(trace_reader, return_exceptions=True)
        if playback:
            await playback.close()
        row["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
        row["output_audio"] = []
        for (turn_id, epoch), chunks in sorted(audio_chunks.items(), key=lambda item: str(item[0])):
            rates = {rate for rate, _, _ in chunks}
            if len(rates) == 1:
                turn_slug = hashlib.sha256(str(turn_id).encode()).hexdigest()[:8] if turn_id else "unknown"
                audio_path = output / f"{case_name}__{arm}__turn-{turn_slug}__epoch-{epoch}.wav"
                with wave.open(str(audio_path), "wb") as wav:
                    wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(next(iter(rates)))
                    wav.writeframes(b"".join(block for _, _, block in sorted(chunks, key=lambda x: x[1] or 0)))
                row["output_audio"].append({"file": audio_path.name, "sha256": hashlib.sha256(audio_path.read_bytes()).hexdigest(),
                                            "sample_rate": next(iter(rates)), "bytes": audio_path.stat().st_size,
                                            "benchmark_turn_id": turn_id, "epoch": epoch})
        # Drop the private local clock object before serialization.
        for event in row["events"]:
            event.pop("_clock_start", None)
        (output / f"{case_name}__{arm}.json").write_text(
            json.dumps(row, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        return row


def _correlated_metrics(events, user_turn_id, input_start_ms, input_last_sample_ms):
    def first(predicate):
        return next((e for e in events if predicate(e)), None)
    user = first(lambda e: e.get("type") == "transcript_done" and e.get("role") == "user"
                 and e.get("benchmark_turn_id") == user_turn_id) if user_turn_id else None
    model = first(lambda e: e.get("type") == "transcript_delta" and e.get("role") == "assistant"
                  and e.get("benchmark_parent_user_turn_id") == user_turn_id
                  and bool(str(e.get("text", "")).strip())) if user_turn_id else None
    audio = first(lambda e: e.get("type") == "audio"
                  and e.get("benchmark_parent_user_turn_id") == user_turn_id) if user_turn_id else None
    complete = first(lambda e: e.get("type") == "transcript_done" and e.get("role") == "assistant"
                      and e.get("benchmark_parent_user_turn_id") == user_turn_id) if user_turn_id else None
    cancel = first(lambda e: e.get("type") == "audio_reset" and e.get("t_ms", -1) >= input_start_ms)
    seqs = {(e.get("epoch"), e.get("seq")) for e in events if e.get("type") == "audio"
            and e.get("benchmark_parent_user_turn_id") == user_turn_id} if user_turn_id else set()
    tts = first(lambda e: e.get("type") == "latency" and isinstance(e.get("tts"), dict)
                 and (e["tts"].get("epoch"), e["tts"].get("sequence")) in seqs)
    values = {"accepted_user_transcript": user, "first_assistant_text": model,
              "first_tts_audio_packet": audio, "assistant_turn_done": complete, "server_cancel_reset": cancel}
    stamps = {key: None if event is None else event.get("t_ms") for key, event in values.items()}
    stamps["tts_complete"] = None if tts is None else tts.get("t_ms")
    return {
        "correlation": "benchmark_parent_user_turn_id; seed output is excluded",
        "active_user_turn_id": user_turn_id,
        "events_ms": stamps,
        "signed_durations_from_input_last_sample_ms": {
            key: None if value is None else round(value - input_last_sample_ms, 3)
            for key, value in stamps.items()},
        "events_before_input_last_sample_retained": True,
        "tts_provider_metric": None if tts is None else tts.get("tts"),
        "browser_playback_ms": None, "physical_playback_ms": None, "heard_onset_ms": None,
    }


def _tts_sequences_finished(audio_events, latency_metrics):
    sequences = {(e.get("epoch"), e.get("seq")) for e in audio_events}
    return bool(sequences) and sequences.issubset({(m.get("epoch"), m.get("sequence"))
                                                   for m in latency_metrics})


def _normal_turn_drained(assistant_done, correlated_audio, latency_metrics, playback_active):
    """A final text event alone is insufficient: require returned audio, TTS final, and queue drain."""
    return bool(assistant_done and correlated_audio and
                _tts_sequences_finished(correlated_audio, latency_metrics) and not playback_active)


async def run_batch(base: str, output: Path):
    import aiohttp
    output.mkdir(parents=True, exist_ok=False)
    timeout = aiohttp.ClientTimeout(total=None, connect=10, sock_connect=10)
    rows = []
    catalog = {}
    async with aiohttp.ClientSession(timeout=timeout, cookie_jar=aiohttp.CookieJar(unsafe=True)) as http:
        async with http.post(base + "/trial/bootstrap", headers={"Origin": base}) as response:
            response.raise_for_status()
        async with http.get(base + "/trial/catalog") as response:
            response.raise_for_status()
            catalog = {a["id"]: a for a in (await response.json()).get("architectures", [])}
        # Alternating architecture order within each fixture limits simple order bias.
        for case_index, (case_name, case) in enumerate(CASES.items()):
            arms = ARMS[case_index % len(ARMS):] + ARMS[:case_index % len(ARMS)]
            arms += EXTRA_ARMS_BY_CASE.get(case_name, ())
            for arm in arms:
                try:
                    row = await run_one(http, base, arm, case_name, case, output)
                finally:
                    async with http.post(base + "/trial/disconnect", headers={"Origin": base}) as response:
                        response.raise_for_status()
                if row.get("trace_id"):
                    async with http.get(base + "/trial/export", params={"session": row["trace_id"]}) as response:
                        if response.status == 200:
                            trace = await response.json()
                            row["server_clock_id"] = "trial_trace_elapsed_ms"
                            row["server_trace_events"] = [{"elapsed_ms": item.get("elapsed_ms"),
                                "source": item.get("source"), "event": item.get("event")}
                                for item in trace.get("events", []) if isinstance(item.get("event"), dict)
                                and (item["event"].get("event") == "tts_complete"
                                     or item["event"].get("type") in ("audio_delivery", "latency", "debug_model"))]
                            tts_done = next((item for item in reversed(row["server_trace_events"])
                                if item.get("event", {}).get("event") == "tts_complete"), None)
                            row["tts_complete_server_elapsed_ms"] = None if not tts_done else tts_done.get("elapsed_ms")
                            (output / f"{case_name}__{arm}.json").write_text(
                                json.dumps(row, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
                rows.append(row)
    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if len(rows) == 14 and all(r["status"] == "complete" for r in rows) else "partial_or_failed",
        "trial_count": len(rows), "planned_trial_count": 14,
        "server_origin": base, "input_mode": "cached_synthetic_pcm_replayed_at_20ms_cadence",
        "service": "production_live_studio_TrialConversation_and_CascadeVoice",
        "provider_requests": "Deepgram Nova-3 STT, Cerebras model, ElevenLabs streaming TTS; Qwen affect reader on qwen-affect arm",
        "architecture_catalog_snapshots": {arm: catalog.get(arm) for arm in sorted(
            {r["architecture_id"] for r in rows})},
        "measurement_scope": "client_receive_and_server_packet; no browser_or_physical_playback",
        "human_listening": "unrated", "samples": [{"architecture_id": r["architecture_id"],
            "scenario": r["scenario"], "status": r["status"], "duration_ms": r["duration_ms"]} for r in rows],
    }
    (output / "run.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def configure_isolated_studio():
    """Patch only the live_studio class factory and add the responsive Qwen arm."""
    live_studio.TrialConversation = CachedBenchTrialConversation
    if not any(a["id"] == "bench-qwen-responsive" for a in live_studio.ARCHITECTURES):
        source = next(a for a in live_studio.ARCHITECTURES if a["id"] == "qwen-affect")
        arm = dict(source, id="bench-qwen-responsive", label="Qwen low, responsive, no reader",
                   conversation_policy="responsive", endpoint_ms=500)
        for key in ("affect_model", "affect_reasoning"):
            arm.pop(key, None)
        arm["description"] = "Qwen low with the qwen-affect responsive settings and no separate expression reader."
        live_studio.ARCHITECTURES.append(arm)


def serve(port: int, run_dir: Path):
    if port == 9053:
        raise ValueError("The speech benchmark must not bind port 9053")
    configure_isolated_studio()
    args = argparse.Namespace(port=port, run_dir=str(run_dir))
    app = live_studio.create_studio(args)
    from aiohttp import web
    print(json.dumps({"event": "speech_bench_server_start", "port": port,
                      "run_dir": str(run_dir), "adapter": Path(__file__).name}), flush=True)
    web.run_app(app, host="127.0.0.1", port=port)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:9054")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR / "capture")
    parser.add_argument("--port", type=int, default=9054)
    parser.add_argument("--run-dir", type=Path, default=OUTPUT_DIR / "server-state")
    args = parser.parse_args()
    if args.serve:
        serve(args.port, args.run_dir)
    elif args.run:
        result = asyncio.run(run_batch(args.base_url, args.output))
        print(json.dumps(result, indent=2))
    else:
        parser.error("Use --serve to start the isolated TrialConversation service")


if __name__ == "__main__":
    main()
