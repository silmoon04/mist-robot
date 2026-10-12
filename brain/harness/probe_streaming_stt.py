"""One saved-WAV replay through the loopback STT proxy at speaking speed."""
import argparse
import hashlib
import io
import json
import os
import queue
import sys
import threading
import time
import uuid
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_client import load_env
from ui.streaming_stt import WarmDeepgramSTT
from ui.stt_proxy import create_proxy_server
from websockets.sync.client import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    source_bytes = args.wav.read_bytes()
    with wave.open(io.BytesIO(source_bytes), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("Probe requires mono PCM16 WAV")
        rate = audio.getframerate()
        pcm = audio.readframes(audio.getnframes())
    key = os.environ.get("DEEPGRAM_API_KEY") or load_env().get("DEEPGRAM_API_KEY")
    if not key:
        raise RuntimeError("Deepgram key unavailable")
    engines = []
    def engine():
        transcriber = WarmDeepgramSTT(key, keyterms=("MIST", "HEX-1", "servo", "femur", "tripod", "gait", "crouch", "ominous sway", "disco stomp", "wheel mode", "Moon"))
        engines.append(transcriber)
        return transcriber
    proxy = create_proxy_server(port=0, origins=("http://127.0.0.1:8779",), engine_factory=engine)
    server_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    server_thread.start()
    events = queue.Queue()
    observed = []
    started = time.perf_counter()
    final = None
    error = None
    audio_started = audio_ended = None
    audio_bytes_sent = 0
    utterance_id = str(uuid.uuid4())
    try:
        with connect(f"ws://127.0.0.1:{proxy.port}/stt", origin="http://127.0.0.1:8779", compression=None,
                     open_timeout=3, close_timeout=1) as socket:
            def receive():
                try:
                    for raw in socket:
                        event = json.loads(raw)
                        observed.append((time.perf_counter(), event))
                        events.put(event)
                except Exception:
                    events.put({"type": "error", "message": "Local probe WebSocket closed"})
            receiver = threading.Thread(target=receive, daemon=True)
            receiver.start()
            socket.send(json.dumps({"type": "start", "utterance_id": utterance_id, "sample_rate": rate}))
            deadline = time.perf_counter() + 8
            while time.perf_counter() < deadline:
                event = events.get(timeout=max(0.01, deadline - time.perf_counter()))
                if event.get("type") == "started":
                    break
                if event.get("type") == "error":
                    raise RuntimeError(event.get("message", "STT start failed"))
            else:
                raise TimeoutError("Streaming utterance did not start")
            audio_started = time.perf_counter()
            chunk_size = rate // 10 * 2
            for offset in range(0, len(pcm), chunk_size):
                chunk = pcm[offset:offset + chunk_size]
                due = audio_started + (offset + len(chunk)) / (rate * 2)
                time.sleep(max(0, due - time.perf_counter()))
                socket.send(chunk)
                audio_bytes_sent += len(chunk)
            audio_ended = time.perf_counter()
            socket.send(json.dumps({"type": "end", "utterance_id": utterance_id}))
            deadline = time.perf_counter() + 10
            while time.perf_counter() < deadline:
                event = events.get(timeout=max(0.01, deadline - time.perf_counter()))
                if event.get("type") == "final":
                    final = event
                    break
                if event.get("type") == "error":
                    raise RuntimeError(event.get("message", "STT finalization failed"))
            else:
                raise TimeoutError("Streaming utterance did not finalize")
    except Exception as exc:
        error = str(exc)
    finally:
        proxy.shutdown()
        server_thread.join(timeout=3)
    first_partial = next((when for when, event in observed if event.get("type") == "partial" and event.get("text")), None)
    final_at = next((when for when, event in observed if event.get("type") == "final"), None)
    report = {"source": "saved synthetic WAV, no microphone capture", "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
              "sample_rate": rate, "source_audio_seconds": len(pcm) / (rate * 2),
              "audio_seconds_submitted": audio_bytes_sent / (rate * 2), "audio_submissions": int(audio_bytes_sent > 0),
              "provider_sessions": sum(bool(engine._connection_metrics) for engine in engines), "provider": "deepgram", "model": "nova-3", "transport": "websocket",
              "model_calls": 0, "tts_calls": 0, "cost_usd": None,
              "start_to_audio_ready_s": audio_started - started if audio_started else None,
              "audio_start_to_first_partial_s": first_partial - audio_started if first_partial and audio_started else None,
              "partial_arrived_before_audio_end": bool(first_partial and audio_ended and first_partial < audio_ended),
              "audio_end_to_final_s": final_at - audio_ended if final_at and audio_ended else None,
              "total_wall_s": (final_at or time.perf_counter()) - started,
              "final": final, "error": error,
              "diagnostic": engines[-1].last_diagnostic if error and engines else None}
    (args.out / "result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report), flush=True)
    return 0 if final is not None and error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
