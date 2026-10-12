"""Offline coverage for warm STT, finalization and cancellation isolation."""
import io
import json
import queue
import sys
import threading
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui.streaming_stt import StreamingSTTError, WarmDeepgramSTT


def wav(seconds=0.2, rate=16000, channels=1):
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(b"\0\0" * int(rate * seconds) * channels)
    return output.getvalue()


class SocketFixture:
    def __init__(self, rate=16000, omit_finalize_flag=False, never_finish=False, lagging_finalize=False):
        self.rate = rate
        self.omit_finalize_flag = omit_finalize_flag
        self.never_finish = never_finish
        self.lagging_finalize = lagging_finalize
        self.finalize_count = 0
        self.frames = queue.Queue()
        self.total_bytes = 0
        self.segment_start = 0
        self.closed = False
        self.commands = []

    def result(self, text, start, duration, final, **extra):
        return {"type": "Results", "start": start, "duration": duration,
                "is_final": final, "channel": {"alternatives": [{"transcript": text, "confidence": 0.99}]}, **extra}

    def send(self, value):
        if self.closed:
            raise OSError("fixture closed")
        if isinstance(value, bytes):
            self.total_bytes += len(value)
            self.frames.put(json.dumps(self.result("Hello", self.segment_start, 0.05, False)))
            return
        command = json.loads(value)["type"]
        self.commands.append(command)
        if command == "Finalize" and not self.never_finish:
            self.finalize_count += 1
            end = self.total_bytes / (self.rate * 2)
            if self.lagging_finalize:
                if self.finalize_count == 1:
                    self.frames.put(json.dumps(self.result("Hello", self.segment_start, 0.08, True, from_finalize=True)))
                    self.segment_start += 0.08
                else:
                    self.frames.put(json.dumps(self.result("MIST.", self.segment_start, end - self.segment_start, True, from_finalize=True)))
                    self.segment_start = end
                return
            middle = (self.segment_start + end) / 2
            first = self.result("Hello", self.segment_start, middle - self.segment_start, True)
            self.frames.put(json.dumps(first))
            self.frames.put(json.dumps(first))  # duplicate finalized segment
            self.frames.put(json.dumps(self.result("MIST.", middle, end - middle, True,
                                                   from_finalize=not self.omit_finalize_flag, speech_final=True)))
            self.segment_start = end

    def recv(self, timeout):
        try:
            value = self.frames.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError from None
        if value is None:
            raise OSError("closed")
        return value

    def close(self):
        self.closed = True
        self.frames.put(None)


class StreamingSTTTests(unittest.TestCase):
    def client(self, **socket_options):
        sockets = []
        def connector(uri, **kwargs):
            self.assertTrue(uri.startswith("wss://api.deepgram.com/v1/listen?"))
            self.assertIn("smart_format=false", uri)
            socket = SocketFixture(**socket_options)
            sockets.append(socket)
            return socket
        client = WarmDeepgramSTT("fixture-key", connector=connector)
        self.addCleanup(client.close)
        return client, sockets

    def test_two_utterances_share_connection_and_merge_final_segments_once(self):
        client, sockets = self.client()
        events = []
        first = client.transcribe_wav(wav(), on_event=events.append)
        second = client.transcribe_wav(wav())
        self.assertEqual(first["transcript"], "Hello MIST.")
        self.assertEqual(second["transcript"], "Hello MIST.")
        self.assertFalse(first["timings"]["connection_reused"])
        self.assertTrue(second["timings"]["connection_reused"])
        self.assertEqual(len(sockets), 1)
        self.assertTrue(any(not event["segment_final"] for event in events))
        self.assertEqual(first["audio_seconds"], 0.2)

    def test_final_audio_coverage_works_when_from_finalize_is_absent(self):
        client, _ = self.client(omit_finalize_flag=True)
        result = client.transcribe_wav(wav(), timeout=0.5)
        self.assertTrue(result["final"])
        self.assertEqual(result["transcript"], "Hello MIST.")

    def test_early_finalize_ack_cannot_commit_a_truncated_utterance(self):
        client, _ = self.client(lagging_finalize=True)
        result = client.transcribe_wav(wav(), timeout=1)
        self.assertEqual(result["transcript"], "Hello MIST.")
        self.assertEqual(result["timings"]["finalize_requests"], 2)
        self.assertGreaterEqual(result["timings"]["finalize_to_final_s"], 0.2)

    def test_timeout_closes_connection_and_does_not_promote_interim_to_final(self):
        client, sockets = self.client(never_finish=True)
        with self.assertRaisesRegex(StreamingSTTError, "did not finalize"):
            client.transcribe_wav(wav(), timeout=0.02)
        self.assertTrue(sockets[0].closed)
        self.assertIsNone(client._active)

    def test_stale_connection_results_cannot_enter_a_new_utterance(self):
        client, _ = self.client()
        client.begin_utterance(16000)
        stale_generation = client._generation
        client.cancel()
        client.begin_utterance(16000)
        client._handle_result(SocketFixture().result("old private words", 0, 0.2, True), stale_generation)
        self.assertEqual(client._active.text(), "")
        client.cancel()

    def test_cancel_releases_capture_and_bad_wav_never_opens_connection(self):
        client, sockets = self.client()
        for bad in (b"not wav", wav(channels=2)):
            with self.assertRaises(StreamingSTTError):
                client.transcribe_wav(bad)
        self.assertEqual(sockets, [])
        client.begin_utterance(16000)
        with self.assertRaises(StreamingSTTError):
            client.begin_utterance(16000)
        client.cancel()
        self.assertEqual(client.transcribe_wav(wav())["transcript"], "Hello MIST.")


if __name__ == "__main__":
    unittest.main()
