"""Loopback PCM speech proxy. Provider credentials stay in this process."""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import threading
import time
import uuid
from pathlib import Path

from websockets.exceptions import ConnectionClosed
from websockets.sync.server import serve

try:
    from .streaming_stt import WarmDeepgramSTT
except ImportError:
    from streaming_stt import WarmDeepgramSTT

DEFAULT_ORIGINS = ("http://127.0.0.1:8776", "http://localhost:8776")
SAMPLE_RATES = {8000, 16000, 22050, 24000, 32000, 44100, 48000}
TIMING_FIELDS = {"connection_reused", "connect_s", "first_partial_s", "first_final_s",
                 "finalize_to_final_s", "recognition_total_s", "finalize_requests"}


def _key_from_server():
    value = os.environ.get("DEEPGRAM_API_KEY")
    if value:
        return value
    try:
        lines = (Path(__file__).resolve().parents[2] / ".env").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        name, separator, value = line.strip().partition("=")
        if separator and name.strip() == "DEEPGRAM_API_KEY":
            return value.strip().strip("\"'") or None
    return None


def _valid_id(value):
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        return str(uuid.UUID(value)) == value.lower()
    except ValueError:
        return False


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0 else None


class _BrowserSession:
    def __init__(self, owner, socket, engine):
        self.owner, self.socket, self.engine = owner, socket, engine
        self.lock = threading.RLock()
        self.send_lock = threading.Lock()
        self.created = time.monotonic()
        self.active = None
        self.pending = None
        self.worker = None
        self.epoch = 0
        self.closed = False
        self.seen = set()

    def send(self, value, epoch=None):
        with self.send_lock:
            active = self.active
            if self.closed or (epoch is not None and (active is None or active["epoch"] != epoch)):
                return False
            if value.get("type") == "partial" and (active is None or active["phase"] not in {"accepting", "finalizing"}):
                return False
            try:
                self.socket.send(json.dumps(value, allow_nan=False))
                return True
            except (ConnectionClosed, OSError):
                return False

    def error(self, message, utterance_id=None):
        self.owner.record({"type": "error", "message": message, "utterance_id": utterance_id})
        self.send({"type": "error", "message": message, "utterance_id": utterance_id})

    def cancel(self, utterance_id=None, acknowledge=True):
        with self.lock:
            active_id = self.active["id"] if self.active else None
            pending_id = self.pending["utterance_id"] if self.pending else None
            if utterance_id is not None and utterance_id not in (active_id, pending_id):
                return False
            if utterance_id == pending_id and pending_id is not None:
                self.pending = None
            else:
                self.epoch += 1
                self.active = None
                if utterance_id is None:
                    self.pending = None
        try:
            self.engine.cancel()
        except Exception:
            pass
        if acknowledge:
            self.send({"type": "cancelled", "utterance_id": utterance_id or active_id or pending_id})
        return True

    def begin(self, request):
        utterance_id = request["utterance_id"]
        with self.lock:
            if self.closed:
                return
            self.epoch += 1
            epoch = self.epoch
            self.active = {"id": utterance_id, "epoch": epoch, "rate": request["sample_rate"],
                           "started": time.monotonic(), "bytes": 0, "phase": "starting"}

        def partial(event):
            with self.lock:
                if not self.active or self.active["epoch"] != epoch or self.active["phase"] == "starting":
                    return
            text = event.get("text") if isinstance(event, dict) else None
            if isinstance(text, str):
                self.send({"type": "partial", "text": text[:32768], "utterance_id": utterance_id}, epoch)

        try:
            self.engine.begin_utterance(request["sample_rate"], on_event=partial)
        except Exception:
            with self.lock:
                if self.active and self.active["epoch"] == epoch:
                    self.active = None
            self.error("Speech recognition could not start", utterance_id)
            return
        with self.lock:
            valid = not self.closed and self.active is not None and self.active["epoch"] == epoch
        if not valid:
            self.cancel(acknowledge=False)
            return
        self.send({"type": "started", "utterance_id": utterance_id, "sample_rate": request["sample_rate"]}, epoch)
        with self.lock:
            if self.active and self.active["epoch"] == epoch:
                self.active["phase"] = "accepting"

    def finish(self, epoch, utterance_id):
        try:
            result = self.engine.finalize(timeout=self.owner.finalize_timeout)
            text = result.get("transcript")
            if not isinstance(text, str) or result.get("final") is not True:
                raise ValueError("missing final result")
            confidence = _number(result.get("confidence"))
            timings = {name: value if isinstance(value, bool) else _number(value)
                       for name, value in result.get("timings", {}).items() if name in TIMING_FIELDS}
            event = {"type": "final", "utterance_id": utterance_id, "transcript": text[:32768],
                     "confidence": confidence if confidence is not None and confidence <= 1 else None,
                     "audio_seconds": _number(result.get("audio_seconds")),
                     "provider_processed_audio_seconds": _number(result.get("provider_processed_audio_seconds")),
                     "api_latency_s": _number(result.get("api_latency_s")), "timings": timings,
                     "final": True, "transport": "deepgram_websocket", "model": "nova-3"}
            with self.lock:
                if self.active is not None and self.active["epoch"] == epoch:
                    self.active["phase"] = "finished"
            if self.send(event, epoch):
                self.owner.record(event)
        except Exception:
            with self.lock:
                current = self.active is not None and self.active["epoch"] == epoch and not self.closed
            if current:
                self.error("Speech recognition did not return a final transcript", utterance_id)
        finally:
            with self.lock:
                if self.active is not None and self.active["epoch"] == epoch:
                    self.active = None

    def control(self, request):
        if not isinstance(request, dict):
            self.error("Invalid speech control message")
            return
        kind, utterance_id = request.get("type"), request.get("utterance_id")
        if not isinstance(kind, str) or kind not in {"start", "end", "cancel"} or not _valid_id(utterance_id):
            self.error("Invalid speech control message")
            return
        if kind == "cancel":
            if not self.cancel(utterance_id):
                self.error("No matching speech utterance", utterance_id)
            return
        if kind == "start":
            rate = request.get("sample_rate")
            if type(rate) is not int or rate not in SAMPLE_RATES:
                self.error("Unsupported PCM sample rate", utterance_id)
                return
            with self.lock:
                if (self.active is not None and self.active["phase"] != "finished") or self.pending is not None or utterance_id in self.seen or len(self.seen) >= 1024:
                    self.error("A speech utterance is already active or the id was used", utterance_id)
                    return
                self.seen.add(utterance_id)
                if self.worker is not None and self.worker.is_alive():
                    self.pending = request
                    return
            self.begin(request)
            return
        with self.lock:
            active = self.active
            if active is None or active["id"] != utterance_id or active["phase"] != "accepting":
                self.error("No matching accepting speech utterance", utterance_id)
                return
            if not active["bytes"]:
                self.error("No audio was received", utterance_id)
                self.cancel(utterance_id, acknowledge=False)
                return
            active["phase"] = "finalizing"
            self.worker = threading.Thread(target=self.finish, args=(active["epoch"], utterance_id), daemon=True,
                                           name="mist-stt-finalize")
            self.worker.start()

    def pcm(self, value):
        with self.lock:
            active = self.active
            if active is None or active["phase"] != "accepting":
                self.error("Audio arrived before started or after end", active["id"] if active else None)
                return
            utterance_id = active["id"]
            if len(value) % 2 or len(value) > self.owner.max_frame_bytes:
                self.error("Invalid PCM16 audio chunk", utterance_id)
                self.cancel(utterance_id, acknowledge=False)
                return
            if active["bytes"] + len(value) > active["rate"] * 2 * self.owner.max_utterance_seconds:
                self.error("Speech utterance exceeds the duration limit", utterance_id)
                self.cancel(utterance_id, acknowledge=False)
                return
            active["bytes"] += len(value)
        try:
            self.engine.send_pcm(value)
        except Exception:
            self.error("Speech audio could not be processed", utterance_id)
            self.cancel(utterance_id, acknowledge=False)

    def run(self):
        try:
            while not self.closed:
                now = time.monotonic()
                if now - self.created >= self.owner.max_session_seconds:
                    self.error("Speech session reached its time limit", self.active["id"] if self.active else None)
                    break
                with self.lock:
                    active = self.active
                    pending = self.pending if self.worker is None or not self.worker.is_alive() else None
                    if pending:
                        self.pending = None
                if active and active["phase"] in {"starting", "accepting"} and now - active["started"] >= self.owner.max_utterance_seconds:
                    self.cancel(active["id"], acknowledge=False)
                    self.error("Speech utterance reached its time limit", active["id"])
                if pending:
                    self.begin(pending)
                try:
                    value = self.socket.recv(timeout=0.1)
                except TimeoutError:
                    continue
                if isinstance(value, bytes):
                    self.pcm(value)
                else:
                    try:
                        request = json.loads(value)
                    except (json.JSONDecodeError, ValueError):
                        self.error("Invalid speech control message")
                        continue
                    self.control(request)
        except (ConnectionClosed, OSError):
            pass
        finally:
            self.close()

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
        self.cancel(acknowledge=False)
        try:
            self.engine.close()
        except Exception:
            pass
        try:
            self.socket.close()
        except Exception:
            pass
        worker = self.worker
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=self.owner.finalize_timeout + 1)


class STTProxyServer:
    def __init__(self, *, host, port, origins, engine_factory, key_provider, max_session_seconds,
                 max_utterance_seconds, finalize_timeout, max_frame_bytes, metrics_path):
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Speech proxy must bind to loopback")
        if not origins or any(not isinstance(origin, str) or not origin.startswith(("http://127.0.0.1:", "http://localhost:")) for origin in origins):
            raise ValueError("Explicit loopback browser origins are required")
        self.max_session_seconds = min(float(max_session_seconds), 900.0)
        self.max_utterance_seconds = min(float(max_utterance_seconds), 30.0)
        self.finalize_timeout = min(float(finalize_timeout), 8.0)
        self.max_frame_bytes = min(int(max_frame_bytes), 192_000)
        limits = (self.max_session_seconds, self.max_utterance_seconds, self.finalize_timeout, self.max_frame_bytes)
        if any(not math.isfinite(value) or value <= 0 for value in limits):
            raise ValueError("Speech proxy limits must be positive")
        self.metrics_path = Path(metrics_path) if metrics_path else None
        self.metrics_lock = threading.Lock()
        self.engine_factory = engine_factory or (lambda: WarmDeepgramSTT(key_provider or _key_from_server,
                                                                       max_audio_seconds=self.max_utterance_seconds))
        self.gate = threading.Lock()
        self.session = None
        self.state_lock = threading.Lock()
        self.stopping = False
        self.browser_socket = None
        logger = logging.getLogger("mist.stt_proxy.websocket")
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
        self.server = serve(self.handle, host, port, origins=tuple(origins), compression=None,
                            open_timeout=3, close_timeout=1, max_size=self.max_frame_bytes,
                            process_request=self.handshake, server_header=None, logger=logger)
        self.address = self.server.socket.getsockname()
        self.port = self.address[1]

    def handshake(self, connection, request):
        with self.state_lock:
            if self.stopping:
                return connection.respond(503, "Speech recognition is stopping\n")
        if request.path not in {"/", "/stt"}:
            return connection.respond(404, "Speech endpoint not found\n")
        if self.gate.locked():
            return connection.respond(503, "Speech recognition already has an active browser\n")
        return None

    def handle(self, socket):
        if not self.gate.acquire(blocking=False):
            socket.close(code=1013, reason="Speech recognition already has an active browser")
            return
        try:
            with self.state_lock:
                stopping = self.stopping
                if not stopping:
                    self.browser_socket = socket
            if stopping:
                socket.close(code=1001, reason="Speech recognition is stopping")
                return
            try:
                engine = self.engine_factory()
            except Exception:
                socket.send(json.dumps({"type": "error", "message": "Speech recognition is unavailable", "utterance_id": None}))
                return
            with self.state_lock:
                stopping = self.stopping
                if not stopping:
                    session = _BrowserSession(self, socket, engine)
                    self.session = session
            if stopping:
                try:
                    engine.close()
                except Exception:
                    pass
                try:
                    socket.close(code=1001, reason="Speech recognition is stopping")
                except Exception:
                    pass
                return
            session.run()
        finally:
            with self.state_lock:
                self.session = None
                if self.browser_socket is socket:
                    self.browser_socket = None
            self.gate.release()

    def record(self, event):
        if self.metrics_path is None:
            return
        record = {"at": time.time(), "model": "nova-3", "transport": "deepgram_websocket",
                  "utterance_id": event.get("utterance_id"), "type": event["type"]}
        if event["type"] == "final":
            record.update({name: event.get(name) for name in ("audio_seconds", "provider_processed_audio_seconds", "timings", "confidence")})
            record["transcript_characters"] = len(event.get("transcript", ""))
        else:
            record["error"] = event.get("message", "Speech recognition failed")
        try:
            with self.metrics_lock:
                self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
                with self.metrics_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record, allow_nan=False) + "\n")
        except OSError:
            pass

    def serve_forever(self):
        self.server.serve_forever()

    def shutdown(self):
        with self.state_lock:
            self.stopping = True
            session = self.session
            browser = self.browser_socket
        self.server.shutdown()
        if session is not None:
            session.close()
        elif browser is not None:
            try:
                browser.close(code=1001, reason="Speech recognition is stopping")
            except Exception:
                pass


def create_proxy_server(*, host="127.0.0.1", port=8788, origins=DEFAULT_ORIGINS, engine_factory=None,
                        key_provider=None, max_session_seconds=900.0, max_utterance_seconds=30.0,
                        finalize_timeout=8.0, max_frame_bytes=192_000, metrics_path=None):
    return STTProxyServer(host=host, port=port, origins=origins, engine_factory=engine_factory,
                          key_provider=key_provider, max_session_seconds=max_session_seconds,
                          max_utterance_seconds=max_utterance_seconds, finalize_timeout=finalize_timeout,
                          max_frame_bytes=max_frame_bytes, metrics_path=metrics_path)


def main():
    parser = argparse.ArgumentParser(description="MIST loopback streaming speech proxy")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--origin", action="append", help="Allowed browser Origin; repeat to allow several")
    parser.add_argument("--metrics-path", type=Path)
    args = parser.parse_args()
    proxy = create_proxy_server(port=args.port, origins=args.origin or DEFAULT_ORIGINS, metrics_path=args.metrics_path)
    print(f"MIST speech proxy listening on 127.0.0.1:{proxy.port}", flush=True)
    try:
        proxy.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        proxy.shutdown()


if __name__ == "__main__":
    main()
