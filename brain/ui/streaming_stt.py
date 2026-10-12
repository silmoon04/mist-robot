"""Warm Deepgram WebSocket recognition with server-held credentials.

Supports a complete PCM WAV today and ordered PCM chunks for live capture.
Local VAD owns utterance boundaries; Finalize flushes without reconnecting.
"""
from __future__ import annotations

import io
import json
import threading
import time
import urllib.parse
import uuid
import wave
from dataclasses import dataclass, field

from websockets.sync.client import connect


class StreamingSTTError(RuntimeError):
    pass


@dataclass
class _Utterance:
    id: str
    started: float
    audio_start: float
    sample_rate: int
    callback: object = None
    samples: int = 0
    segments: dict = field(default_factory=dict)
    interim: str = ""
    final_requested: float | None = None
    first_partial: float | None = None
    first_final: float | None = None
    processed_end: float = 0.0
    saw_final: bool = False
    finalized: bool = False
    error: str | None = None
    event_trace: list = field(default_factory=list)
    finalize_requests: int = 0
    done: threading.Event = field(default_factory=threading.Event)

    def text(self):
        return " ".join(self.segments[key][0] for key in sorted(self.segments)).strip()


class WarmDeepgramSTT:
    """One ordered utterance at a time, with one persistent upstream receiver."""

    def __init__(self, key, *, keyterms=("MIST", "Moon"), language="en-GB",
                 idle_timeout=45.0, max_audio_seconds=30.0, connector=connect):
        self._key = key
        self.keyterms = tuple(keyterms)
        self.language = language
        self.idle_timeout = idle_timeout
        self.max_audio_seconds = max_audio_seconds
        self._connector = connector
        self._lock = threading.RLock()
        self._utterance_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._socket = None
        self._sample_rate = None
        self._generation = 0
        self._audio_seconds = 0.0
        self._active = None
        self._last_send = 0.0
        self._last_activity = 0.0
        self._connection_metrics = {}
        self.last_diagnostic = {}

    def _url(self, sample_rate):
        params = [("model", "nova-3"), ("language", self.language),
                  ("encoding", "linear16"), ("sample_rate", str(sample_rate)), ("channels", "1"),
                  ("interim_results", "true"), ("endpointing", "false"),
                  ("smart_format", "false"), ("punctuate", "true")]
        params += [("keyterm", term) for term in self.keyterms]
        return "wss://api.deepgram.com/v1/listen?" + urllib.parse.urlencode(params)

    def _ensure_connection(self, sample_rate):
        with self._lock:
            if self._socket is not None and self._sample_rate == sample_rate:
                return {"connection_reused": True, "connect_s": 0.0}
        self._close_socket()
        key = self._key() if callable(self._key) else self._key
        if not isinstance(key, str) or not key:
            raise StreamingSTTError("Deepgram credentials are unavailable")
        started = time.perf_counter()
        try:
            socket = self._connector(self._url(sample_rate), additional_headers={"Authorization": "Token " + key},
                                     compression=None, open_timeout=6, close_timeout=1, max_size=1_000_000)
        except Exception as error:
            # Upstream exceptions can contain handshake headers. Do not expose them.
            status = getattr(error, "status_code", None)
            detail = f" (HTTP {status})" if isinstance(status, int) else ""
            raise StreamingSTTError("Deepgram streaming connection failed" + detail) from None
        with self._lock:
            self._socket = socket
            self._sample_rate = sample_rate
            self._audio_seconds = 0.0
            self._generation += 1
            generation = self._generation
            self._last_send = self._last_activity = time.perf_counter()
        threading.Thread(target=self._receive, args=(socket, generation), daemon=True,
                         name="mist-streaming-stt").start()
        return {"connection_reused": False, "connect_s": time.perf_counter() - started}

    def begin_utterance(self, sample_rate: int, *, on_event=None) -> str:
        if sample_rate not in (8000, 16000, 22050, 24000, 32000, 44100, 48000):
            raise StreamingSTTError("Unsupported PCM sample rate")
        if not self._utterance_lock.acquire(blocking=False):
            raise StreamingSTTError("Speech recognition is already processing an utterance")
        started = time.perf_counter()
        try:
            connection = self._ensure_connection(sample_rate)
            with self._lock:
                utterance = _Utterance(str(uuid.uuid4()), started, self._audio_seconds, sample_rate, on_event)
                self._active = utterance
                self._connection_metrics = connection
                self._last_activity = time.perf_counter()
            return utterance.id
        except Exception:
            self._utterance_lock.release()
            raise

    def send_pcm(self, pcm: bytes):
        if not isinstance(pcm, bytes) or len(pcm) % 2:
            raise StreamingSTTError("Audio chunks must contain signed 16-bit little-endian mono PCM")
        if len(pcm) > 192_000:
            raise StreamingSTTError("Audio chunk is too large")
        if not pcm:
            return
        with self._lock:
            utterance = self._active
            if utterance is None or utterance.final_requested is not None:
                raise StreamingSTTError("No accepting speech utterance")
            if (utterance.samples + len(pcm) // 2) / utterance.sample_rate > self.max_audio_seconds:
                raise StreamingSTTError("Speech utterance exceeds the duration limit")
            utterance.samples += len(pcm) // 2
            self._audio_seconds += len(pcm) / (2 * utterance.sample_rate)
        self._send(pcm)

    def _send(self, message):
        with self._send_lock:
            socket = self._socket
            if socket is None:
                raise StreamingSTTError("Speech recognition connection is closed")
            try:
                socket.send(message)
            except Exception:
                raise StreamingSTTError("Speech recognition connection was interrupted") from None
            self._last_send = time.perf_counter()

    def _receive(self, socket, generation):
        try:
            while generation == self._generation:
                try:
                    raw = socket.recv(timeout=0.5)
                except TimeoutError:
                    now = time.perf_counter()
                    with self._lock:
                        active = self._active is not None
                    if not active and now - self._last_activity > self.idle_timeout:
                        break
                    if now - self._last_send >= 4:
                        self._send(json.dumps({"type": "KeepAlive"}))
                    continue
                event = json.loads(raw)
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "Error":
                    raise StreamingSTTError("Deepgram could not process the audio")
                if event.get("type") == "Results":
                    self._handle_result(event, generation)
        except Exception:
            with self._lock:
                if generation == self._generation and self._active is not None:
                    self._active.error = "Speech recognition connection ended before final transcription"
                    self._active.done.set()
        finally:
            with self._lock:
                if generation == self._generation:
                    self._socket = None
                    self._generation += 1
            try:
                socket.close()
            except Exception:
                pass

    def _handle_result(self, event, generation=None):
        callback = None
        preview = None
        with self._lock:
            if generation is not None and generation != self._generation:
                return
            active = self._active
            if active is None or active.done.is_set():
                return
            start = float(event.get("start", 0))
            duration = float(event.get("duration", 0))
            end = start + duration
            if end < active.audio_start - 0.025:
                return
            alternatives = event.get("channel", {}).get("alternatives", [])
            alternative = alternatives[0] if alternatives else {}
            text = alternative.get("transcript", "").strip()
            now = time.perf_counter()
            final = bool(event.get("is_final"))
            if len(active.event_trace) < 20:
                active.event_trace.append({"elapsed_s": now - active.started, "start_s": start,
                    "duration_s": duration, "is_final": final, "from_finalize": bool(event.get("from_finalize")),
                    "speech_final": bool(event.get("speech_final")), "transcript_characters": len(text)})
            if text and active.first_partial is None:
                active.first_partial = now
            if final:
                active.saw_final = True
                active.first_final = now if active.first_final is None else active.first_final
                active.processed_end = max(active.processed_end, end)
                if text:
                    active.segments[(start, duration)] = (text, alternative.get("confidence"))
                active.interim = ""
            else:
                active.interim = text
            preview = {"type": "stt_partial", "utterance_id": active.id,
                       "text": " ".join(part for part in (active.text(), active.interim) if part),
                       "segment_final": final}
            callback = active.callback
            self._maybe_complete(active)
        if callback is not None:
            try:
                callback(preview)
            except Exception:
                pass

    def _maybe_complete(self, active):
        expected_end = active.audio_start + active.samples / active.sample_rate
        if (active.final_requested is not None and active.saw_final
                and active.processed_end >= expected_end - 0.03):
            active.finalized = True
            active.done.set()

    def finalize(self, timeout=8.0) -> dict:
        with self._lock:
            active = self._active
            if active is None:
                raise StreamingSTTError("No speech utterance to finalize")
            active.final_requested = time.perf_counter()
        try:
            self._send(json.dumps({"type": "Finalize"}))
            active.finalize_requests += 1
            with self._lock:
                self._maybe_complete(active)
            deadline = time.perf_counter() + timeout
            while not active.done.wait(min(0.25, max(0, deadline - time.perf_counter()))):
                if time.perf_counter() >= deadline:
                    raise StreamingSTTError("Speech recognition did not finalize in time")
                # Finalize can cover only audio already processed by the service.
                # Drain queued audio until final segment timestamps cover the input.
                self._send(json.dumps({"type": "Finalize"}))
                active.finalize_requests += 1
            if active.error or not active.finalized:
                raise StreamingSTTError(active.error or "Speech recognition returned no final transcript")
            finished = time.perf_counter()
            confidence = [value[1] for value in active.segments.values() if isinstance(value[1], (int, float))]
            return {"transcript": active.text(), "confidence": sum(confidence) / len(confidence) if confidence else None,
                    "audio_seconds": active.samples / active.sample_rate, "api_latency_s": finished - active.started,
                    "provider_processed_audio_seconds": max(0, active.processed_end - active.audio_start),
                    "final": True, "utterance_id": active.id, "transport": "deepgram_websocket",
                    "model": "nova-3", "sample_rate": active.sample_rate,
                    "timings": {**self._connection_metrics,
                        "first_partial_s": active.first_partial - active.started if active.first_partial else None,
                        "first_final_s": active.first_final - active.started if active.first_final else None,
                        "finalize_to_final_s": finished - active.final_requested,
                        "finalize_requests": active.finalize_requests,
                        "recognition_total_s": finished - active.started},
                    "provider_events": active.event_trace}
        except Exception as error:
            self.last_diagnostic = {"error": str(error), "submitted_audio_seconds": active.samples / active.sample_rate,
                                    "elapsed_s": time.perf_counter() - active.started,
                                    "provider_events": active.event_trace}
            self._close_socket()
            raise
        finally:
            with self._lock:
                self._active = None
                self._last_activity = time.perf_counter()
            self._utterance_lock.release()

    def transcribe_wav(self, raw: bytes, *, timeout=8.0, on_event=None) -> dict:
        try:
            with wave.open(io.BytesIO(raw), "rb") as audio:
                if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getcomptype() != "NONE":
                    raise StreamingSTTError("Streaming recognition requires mono PCM16 WAV")
                rate = audio.getframerate()
                if audio.getnframes() / rate > self.max_audio_seconds:
                    raise StreamingSTTError("Speech utterance exceeds the duration limit")
                pcm = audio.readframes(audio.getnframes())
        except (wave.Error, EOFError):
            raise StreamingSTTError("Audio is not a supported PCM WAV") from None
        if not pcm:
            raise StreamingSTTError("Audio is empty")
        self.begin_utterance(rate, on_event=on_event)
        try:
            for offset in range(0, len(pcm), rate // 5 * 2):
                self.send_pcm(pcm[offset:offset + rate // 5 * 2])
        except Exception:
            self.cancel()
            raise
        return self.finalize(timeout=timeout)

    def cancel(self):
        with self._lock:
            active = self._active
            if active is not None:
                active.error = "Speech recognition was cancelled"
                active.done.set()
        self._close_socket()
        if active is not None and active.final_requested is None:
            with self._lock:
                self._active = None
            self._utterance_lock.release()

    def _close_socket(self):
        with self._lock:
            socket, self._socket = self._socket, None
            self._generation += 1
        if socket is not None:
            try:
                socket.send(json.dumps({"type": "CloseStream"}))
            except Exception:
                pass
            try:
                socket.close()
            except Exception:
                pass

    def close(self):
        self.cancel()
