"""Replay recorded microphone input; measure server transport, never speaker latency.

Annotations: {"turns": [{"turn_id": "u1", "start_ms": 0, "end_ms": 900}]}.
The WAV contains the entire input timeline, including pauses and interruptions.
No microphone, input synthesis, browser playback acknowledgements, or fallback voice
is used. The existing server may use its configured paid speech/model providers.

Start a dedicated server with a fresh directory and an unused port before replay:
python brain/duplex/server.py --enable-fixtures --run-dir <fresh-dir> --port 8796
Pass --base-url http://127.0.0.1:8796 explicitly. The fixtures flag is required,
but does not prove state isolation; the fresh run directory is also necessary.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
import wave

HERE = Path(__file__).resolve().parent
RATE, FRAME_SAMPLES, FRAME_BYTES = 16000, 320, 640
LIMITATIONS = [
    "Server packet arrival is not speaker playback or perceived latency.",
    "No microphone, room echo, acoustic overlap, or browser face rendering is measured.",
    "No playback acknowledgements are sent; background-result delivery may stay blocked.",
    "Native turn IDs cannot reliably be joined to annotated fixture turns; response latencies remain unknown.",
    "Saved output is packet-order PCM per epoch, not a recording of audible playback or gaps.",
    "The fixture has fixed timing; it does not react to when the assistant actually speaks.",
    "The existing server keeps its normal tools and state; this adapter does not isolate memory or preview actions.",
    "The fixtures-enabled preflight is a guard, not proof of isolation; use a dedicated server with a fresh run directory.",
]


class ReplayFailure(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def load_fixture(path):
    try:
        with wave.open(str(path), "rb") as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, RATE, "NONE"):
                raise ReplayFailure("unsupported_wav_format")
            count = wav.getnframes()
            pcm = wav.readframes(count)
            if not count or len(pcm) != count * 2:
                raise ReplayFailure("empty_or_truncated_wav")
    except (wave.Error, EOFError) as exc:
        raise ReplayFailure("invalid_wav") from exc
    return pcm


def load_annotations(path, duration_ms):
    value = json.loads(path.read_text(encoding="utf-8"))
    rows = value.get("turns") if isinstance(value, dict) else value
    if not isinstance(rows, list) or not rows:
        raise ReplayFailure("invalid_annotations")
    seen, previous_end = set(), -1
    for row in rows:
        if not isinstance(row, dict):
            raise ReplayFailure("invalid_annotations")
        tid, start, end = row.get("turn_id"), row.get("start_ms"), row.get("end_ms")
        numbers = all(isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) for x in (start, end))
        if (not isinstance(tid, str) or not tid or tid in seen or not numbers
                or not 0 <= start < end <= duration_ms or start < previous_end):
            raise ReplayFailure("invalid_annotations")
        seen.add(tid)
        previous_end = end
    return rows


def frames(pcm):
    """Each 20 ms packet is due when those microphone samples would be available."""
    for index, offset in enumerate(range(0, len(pcm), FRAME_BYTES)):
        block = pcm[offset:offset + FRAME_BYTES]
        yield index, (index + 1) * .02, block.ljust(FRAME_BYTES, b"\0"), len(block) // 2


def redact(value, secret):
    if isinstance(value, str):
        return value.replace(secret, "[REDACTED]") if secret else value
    if isinstance(value, list):
        return [redact(item, secret) for item in value]
    if isinstance(value, dict):
        return {key: redact(item, secret) for key, item in value.items()}
    return value


class Capture:
    def __init__(self, output, case_id, annotations, clock=time.perf_counter):
        self.output, self.case_id, self.annotations, self.clock = output, case_id, annotations, clock
        self.started = clock()
        self.fixture_started = None
        self.events, self.raw, self.audio, self.rates, self.sent = [], [], {}, {}, []
        self.first_audio = None
        self.emitted_annotations = set()

    def now(self):
        return (self.clock() - self.started) * 1000

    def record(self, name, turn_id="transport", **metadata):
        event = {"event": name, "event_id": f"event-{len(self.events) + 1}", "t_ms": self.now(),
                 "turn_id": turn_id, "clock_id": "replay_perf_counter", "case_id": self.case_id, "metadata": metadata}
        self.events.append(event)
        return event

    def server_event(self, event):
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise ReplayFailure("invalid_server_event")
        clean = dict(event)
        name = event["type"]
        # Native turn IDs are retained, but are never guessed to match a fixture turn.
        native_id = event.get("turn_id")
        tid = "server:" + str(native_id) if native_id is not None else "uncorrelated_server"
        if name == "audio":
            epoch, rate = event.get("epoch"), event.get("sample_rate")
            if type(epoch) is not int or epoch < 0 or type(rate) is not int or not 8000 <= rate <= 96000:
                raise ReplayFailure("unsupported_output_audio")
            try:
                pcm = base64.b64decode(event["pcm"], validate=True)
            except (KeyError, ValueError, TypeError) as exc:
                raise ReplayFailure("invalid_output_pcm") from exc
            if len(pcm) % 2 or (epoch in self.rates and self.rates[epoch] != rate):
                raise ReplayFailure("invalid_output_pcm")
            self.rates[epoch] = rate
            self.audio.setdefault(epoch, bytearray()).extend(pcm)
            clean.pop("pcm", None)
            clean.update(pcm_bytes=len(pcm), pcm_sha256=digest(pcm))
            if pcm and self.first_audio is None:
                self.first_audio = self.now()
            name = "audio_packet_received"
        row = self.record("server_" + name, tid, correlation="unknown", payload=clean)
        self.raw.append({"event_id": row["event_id"], "received_t_ms": row["t_ms"], "payload": clean})

    def packet_sent(self, index, due, samples, actual):
        self.sent.append({"packet_index": index, "fixture_end_ms": due * 1000,
                          "input_samples": samples, "sent_t_ms": actual,
                          "schedule_lateness_ms": actual - self.fixture_started - due * 1000})
        for annotation in self.annotations:
            for boundary in ("start", "end"):
                key = (annotation["turn_id"], boundary)
                offset = annotation[boundary + "_ms"]
                reached = offset <= due * 1000 if boundary == "end" else offset < due * 1000
                if key not in self.emitted_annotations and reached:
                    self.emitted_annotations.add(key)
                    self.record("user_audio_" + boundary, annotation["turn_id"],
                                source="annotated_input_packet_send", fixture_offset_ms=offset,
                                containing_packet_index=index, resolution_ms=20,
                                server_turn_correlation="unknown")

    def write_audio(self):
        files = []
        for epoch, pcm in sorted(self.audio.items()):
            name = f"received-epoch-{epoch}.wav"
            path = self.output / name
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self.rates[epoch])
                wav.writeframes(pcm)
            files.append({"path": name, "epoch": epoch, "sample_rate": self.rates[epoch],
                          "pcm_bytes": len(pcm), "sha256": digest(path.read_bytes())})
        return files


async def paced_upload(ws, pcm, capture, sleep=asyncio.sleep):
    capture.fixture_started = capture.now()
    start = capture.clock()
    capture.record("fixture_started")
    for index, due, block, samples in frames(pcm):
        await sleep(max(0, start + due - capture.clock()))
        await ws.send_json({"type": "mic", "pcm": base64.b64encode(block).decode("ascii")})
        capture.packet_sent(index, due, samples, capture.now())
    capture.record("fixture_finished", padding_samples=(-len(pcm) // 2) % FRAME_SAMPLES)


async def preflight(http, base, headers):
    """Reject ordinary production servers before pairing or opening native voice."""
    async with http.get(base + "/config", headers=headers) as response:
        if response.status != 200:
            raise ReplayFailure("fixture_preflight_unavailable")
        config = await response.json()
        if not isinstance(config, dict) or config.get("fixtures_enabled") is not True:
            raise ReplayFailure("fixtures_not_enabled")


async def transport(args, pcm, capture, secret):
    try:
        import aiohttp
    except ImportError as exc:
        raise ReplayFailure("aiohttp_unavailable") from exc
    base = args.base_url.rstrip("/")
    headers = {"Origin": base}
    ready = asyncio.Event()
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True),
                                     timeout=aiohttp.ClientTimeout(total=args.startup_timeout)) as http:
        await preflight(http, base, headers)
        capture.record("fixture_preflight_passed", isolation_verified=False)
        capture.record("pair_requested")
        async with http.post(base + "/pair", headers=headers, json={"code": secret}) as response:
            if response.status != 200:
                raise ReplayFailure("pair_rejected")
        capture.record("paired")
        async with http.ws_connect(base + "/voice", headers=headers, heartbeat=15) as ws:
            async def reader():
                async for message in ws:
                    if message.type == aiohttp.WSMsgType.TEXT:
                        event = redact(json.loads(message.data), secret)
                        capture.server_event(event)
                        if event["type"] == "ready":
                            ready.set()
                        if event["type"] == "error":
                            raise ReplayFailure("server_error")
                        if event["type"] == "voice_warning":
                            raise ReplayFailure("voice_unavailable")
                    elif message.type == aiohttp.WSMsgType.ERROR:
                        raise ReplayFailure("websocket_error")
                raise ReplayFailure("websocket_closed")
            reader_task = asyncio.create_task(reader())
            upload_task = None
            waiter = asyncio.create_task(ready.wait())
            try:
                done, _ = await asyncio.wait([reader_task, waiter], timeout=args.startup_timeout,
                                             return_when=asyncio.FIRST_COMPLETED)
                if reader_task in done:
                    await reader_task
                if waiter not in done:
                    raise ReplayFailure("startup_timeout")
                capture.record("startup_ready")
                async def upload_and_tail():
                    await paced_upload(ws, pcm, capture)
                    await asyncio.sleep(args.tail_seconds)
                upload_task = asyncio.create_task(upload_and_tail())
                done, _ = await asyncio.wait([reader_task, upload_task], return_when=asyncio.FIRST_COMPLETED)
                if reader_task in done:
                    await reader_task
                await upload_task
            finally:
                for task in (reader_task, waiter, upload_task):
                    if task is not None:
                        task.cancel()
                await asyncio.gather(*(t for t in (reader_task, waiter, upload_task) if t is not None), return_exceptions=True)


async def run(args):
    pcm = load_fixture(args.fixture)
    annotations = load_annotations(args.annotations, len(pcm) / 32)
    suite_bytes = args.suite.read_bytes()
    suite = json.loads(suite_bytes)
    case = next((c for c in suite["cases"] if c["id"] == args.case_id), None)
    if case is None:
        raise ReplayFailure("unknown_case_id")
    parsed = urlsplit(args.base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ReplayFailure("invalid_base_url")
    args.output.mkdir(parents=True, exist_ok=False)
    capture = Capture(args.output, args.case_id, annotations)
    secret = os.environ.get(args.pair_code_env, "")
    failure = None
    try:
        if not secret:
            raise ReplayFailure("pair_code_env_missing")
        await transport(args, pcm, capture, secret)
    except ReplayFailure as exc:
        failure = exc.code
    except asyncio.TimeoutError:
        failure = "transport_timeout"
    except (OSError, ValueError):
        failure = "transport_or_protocol_error"
    except Exception as exc:
        # Provider/client exceptions can contain URLs or headers; record type only.
        failure = "transport_exception:" + type(exc).__name__
    audio = capture.write_audio()
    startup = next((e["t_ms"] for e in capture.events if e["event"] == "startup_ready"), None)
    sample = {"case_id": args.case_id, "repeat": args.repeat, "category": case["category"], "split": case["split"],
              "status": "failed" if failure else "completed", "measurement_scope": "server_transport_only",
              "evidence_mode": "audio_transport", "events": capture.events, "checks": [], "outcomes": {},
              "errors": [{"code": failure}] if failure else [], "limitations": LIMITATIONS,
              "transport_metrics": {"startup_ready_ms": startup,
                  "first_audio_packet_ms": None if capture.first_audio is None or capture.fixture_started is None else capture.first_audio - capture.fixture_started,
                  "first_audio_packet_origin": "fixture_started; not response or speaker latency",
                  "per_turn_response_latency_ms": None, "turn_correlation": "unknown"},
              "audio_files": audio}
    run_data = {"manifest": {"schema_version": 1, "run_id": args.output.name,
                "created_utc": datetime.now(timezone.utc).isoformat(), "adapter": "existing-duplex-audio-replay",
                "suite_sha256": digest(suite_bytes), "selected_case_ids": [args.case_id], "repeats": 1,
                "measurement_scope": "server_transport_only", "human_quality": "unrated",
                "input_sha256": digest(args.fixture.read_bytes()), "annotations_sha256": digest(args.annotations.read_bytes()),
                "input_filename": args.fixture.name,
                "config": {"base_url": args.base_url, "packet_ms": 20, "tail_seconds": args.tail_seconds,
                           "input_sample_rate": RATE, "native_turn_mapping": "unknown", "speaker_playback": False},
                "source_hashes": {"audio_replay.py": digest(Path(__file__).read_bytes())}}, "samples": [sample]}
    save(args.output / "run.json", run_data)
    save(args.output / "server-events.json", capture.raw)
    save(args.output / "input-packets.json", capture.sent)
    save(args.output / "annotations.json", annotations)
    (args.output / "cases.frozen.json").write_bytes(suite_bytes)
    print(json.dumps({"status": sample["status"], "failure_code": failure, "output": str(args.output),
                      "measurement_scope": "server_transport_only"}))
    return 1 if failure else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--suite", type=Path, default=HERE / "cases.json")
    parser.add_argument("--base-url", required=True, help="Dedicated fixtures-enabled server, e.g. http://127.0.0.1:8796; use a fresh run directory.")
    parser.add_argument("--pair-code-env", default="MIST_PAIR_CODE")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--startup-timeout", type=float, default=45)
    parser.add_argument("--tail-seconds", type=float, default=15)
    args = parser.parse_args()
    if args.repeat < 1 or not math.isfinite(args.startup_timeout) or args.startup_timeout <= 0 or not math.isfinite(args.tail_seconds) or args.tail_seconds < 0:
        parser.error("repeat and startup timeout must be positive; tail seconds must be nonnegative")
    try:
        return asyncio.run(run(args))
    except (ReplayFailure, FileExistsError, OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "failure_code": getattr(exc, "code", type(exc).__name__)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
