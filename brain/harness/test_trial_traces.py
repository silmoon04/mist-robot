"""Exercise durable paging, trace recovery and persistence-time redaction."""
import concurrent.futures
import json
import logging
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from duplex.trial_traces import BufferedJournal, MAX_PAGE, TraceStore, TraceWriteError


class TrialTraceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = TraceStore(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_reopen_preserves_events_and_marks_unfinished_interrupted(self):
        journal = self.store.start({"model": "luna", "floor": "hold"})
        journal.record({"type": "transcript_done", "text": "Hello"})
        before = journal.since(0)["events"]
        reopened = TraceStore(self.root).get(journal.trace_id)
        self.assertEqual(reopened.since(0)["events"], before)
        self.assertEqual(reopened.metadata["status"], "interrupted")
        self.assertEqual(reopened.metadata["event_count"], 1)
        self.assertIsNotNone(reopened.metadata["ended_at"])
        manifest = json.loads((self.root / journal.trace_id / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "interrupted")

    def test_pagination_retains_more_than_2000_events_after_restart(self):
        journal = self.store.start({})
        for index in range(2205):
            journal.record({"type": "frame", "frame": index})
        journal.finish()
        reopened = TraceStore(self.root).get(journal.trace_id)
        ids, cursor = [], 0
        while cursor < reopened.sequence:
            page = reopened.since(cursor, limit=999999)
            self.assertLessEqual(len(page["events"]), MAX_PAGE)
            ids.extend(row["id"] for row in page["events"])
            cursor = page["cursor"]
        self.assertEqual(ids, list(range(1, 2206)))
        self.assertEqual(reopened.since(0)["oldest"], 1)
        self.assertIsNone(reopened.since(0)["capacity"])
        self.assertEqual(reopened.since(999999)["events"], [])

    def test_full_transcript_and_tool_outputs_not_truncated(self):
        journal = self.store.start({})
        text = "A normal line of dialogue. " * 1200
        tools = [{"index": i, "text": text} for i in range(80)]
        journal.record({"type": "tool", "args": {"question": text}, "result": tools})
        event = journal.export()["events"][0]["event"]
        self.assertEqual(event["args"]["question"], text)
        self.assertEqual(event["result"], tools)

    def test_audio_delta_payload_is_removed_but_spoken_transcript_remains(self):
        journal = self.store.start({})
        journal.record({'type':'response.output_audio.delta','delta':'BASE64-AUDIO'})
        journal.record({'type':'response.audio_transcript.delta','delta':'Hello there'})
        exported = journal.export()
        self.assertNotIn('BASE64-AUDIO', json.dumps(exported))
        self.assertEqual(exported['events'][1]['event']['delta'], 'Hello there')

    def test_redacts_before_writing_config_events_and_reason(self):
        credential = "my-private-provider-secret"
        store = TraceStore(self.root, secrets=[credential])
        journal = store.start({"model": "luna", "api_key": "unknown-api-secret", "url": f"https://example.test/?access_token={credential}"})
        journal.record({"type": "tool", "authorization": "unknown-auth-secret", "tokens": 32,
                        "args": {"query": "normal question"}, "result": {"text": f"failure contained {credential}",
                        "password": "unknown-password", "headers": [["Authorization", "hidden-header-secret"]]}})
        journal.finish(reason=f"A call failed with {credential}")
        persisted = "\n".join(path.read_text(encoding="utf-8") for path in (self.root / journal.trace_id).iterdir())
        for secret in (credential, "unknown-api-secret", "unknown-auth-secret", "unknown-password", "hidden-header-secret"):
            self.assertNotIn(secret, persisted)
        self.assertIn("normal question", persisted)
        self.assertEqual(journal.since(0)["events"][0]["event"]["tokens"], 32)

    def test_private_reasoning_removed_but_observable_reply_retained(self):
        journal = self.store.start({"reasoning_effort": "low"})
        journal.record({"type": "response.reasoning.delta", "delta": "private-reasoning-text", "turn_id": "t1"}, "provider")
        journal.record({"type": "provider", "item": {"type": "reasoning", "summary": [{"text": "private-summary"}]}})
        journal.record({"type": "tool", "reasoning_content": "private-reasoning-field", "result": {"text": "Observable output"}})
        journal.record({"type": "transcript_done", "text": "I am thinking about your question."})
        serialized = json.dumps(journal.export())
        for secret in ("private-reasoning-text", "private-summary", "private-reasoning-field"):
            self.assertNotIn(secret, serialized)
        self.assertIn("Observable output", serialized)
        self.assertIn("I am thinking about your question.", serialized)
        self.assertEqual(journal.metadata["config"]["reasoning_effort"], "low")

    def test_all_audio_metadata_packets_retained_without_pcm(self):
        journal = self.store.start({})
        for index in range(101):
            journal.record({"type": "audio", "epoch": 1, "seq": 0, "pcm": "PRIVATEPCMBLOB",
                            "sample_rate": 24000, "mouth_cues": [{"time": index/100, "viseme": "AA"}]})
        events = [row["event"] for row in journal.export()["events"]]
        self.assertEqual(len(events), 101)
        self.assertTrue(all(event["type"] == "audio_delivery" for event in events))
        self.assertTrue(all("pcm" not in event and event["encoded_bytes"] == 14 for event in events))
        self.assertEqual(events[-1]["mouth_cues"][0]["time"], 1)
        self.assertNotIn("PRIVATEPCMBLOB", (self.root / journal.trace_id / "events.jsonl").read_text())

    def test_binary_and_data_uri_payloads_not_stored(self):
        journal = self.store.start({})
        journal.record({"type": "mic", "data": "hidden-audio-payload", "blob": b"hidden-binary", "text": "data:audio/wav;base64,QUJDREVGRw=="})
        journal.record({"type": "tool", "result": b"hidden-binary"})
        output = json.dumps(journal.export())
        self.assertNotIn("hidden-audio-payload", output)
        self.assertNotIn("hidden-binary", output)
        self.assertNotIn("QUJDREVGRw", output)

    def test_private_channel_and_nested_provider_reasoning_method(self):
        journal = self.store.start({})
        journal.record({"type": "response.output_text.delta", "channel": "analysis", "delta": "hidden-channel-content"})
        journal.record({"method": "item/reasoning/textDelta", "params": {"delta": "hidden-method-content", "itemId": "r1"}})
        journal.record({"method": "item/agentMessage/delta", "params": {"delta": "Normal observable reply"}})
        output = json.dumps(journal.export())
        self.assertNotIn("hidden-channel-content", output)
        self.assertNotIn("hidden-method-content", output)
        self.assertIn("Normal observable reply", output)

    def test_invalid_trace_paths_return_none_and_cannot_escape_root(self):
        for trace_id in ("../other", "..", "C:/Windows", "/tmp/session", "a"*31, "a"*33, "a"*32+"/child", "A"*32, None):
            with self.subTest(trace_id=trace_id):
                self.assertIsNone(self.store.get(trace_id))
        self.assertIsNone(self.store.get("0"*32))

    def test_corrupt_trailing_bytes_preserved_with_valid_prefix_readable(self):
        journal = self.store.start({})
        journal.record({"type": "text", "text": "first"})
        path = self.root / journal.trace_id / "events.jsonl"
        with path.open("ab") as handle:
            handle.write(b'{"id":2,"event":{"text":"half')
        original = path.read_bytes()
        recovered = TraceStore(self.root).get(journal.trace_id)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(recovered.since(0)["head"], 1)
        self.assertEqual(recovered.since(0)["events"][0]["event"]["text"], "first")
        self.assertEqual(recovered.metadata["recovery"][0]["reason"], "invalid_json_line")
        self.assertTrue(recovered.metadata["recovery"][0]["preserved"])

    def test_valid_final_line_without_newline_is_recovered_not_lost(self):
        journal = self.store.start({})
        journal.record({"type": "text", "text": "complete"})
        path = self.root / journal.trace_id / "events.jsonl"
        path.write_bytes(path.read_bytes().rstrip(b"\n"))
        original = path.read_bytes()
        recovered = TraceStore(self.root).get(journal.trace_id)
        self.assertEqual(recovered.sequence, 1)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(recovered.metadata["recovery"][0]["reason"], "missing_final_newline")

    def test_finished_status_is_durable_and_finish_is_idempotent(self):
        journal = self.store.start({})
        journal.record({"type": "test"})
        final = journal.finish("failed", "Provider disconnected")
        self.assertEqual(journal.finish("ended"), final)
        reopened = TraceStore(self.root).get(journal.trace_id)
        self.assertEqual(reopened.metadata["status"], "failed")
        self.assertEqual(reopened.metadata["reason"], "Provider disconnected")
        with self.assertRaises(RuntimeError):
            reopened.record({"type": "late"})

    def test_manifest_atomic_updates_and_metadata_copies(self):
        journal = self.store.start({"model": "luna"})
        journal.record({"type": "test"})
        manifest = json.loads((self.root / journal.trace_id / "manifest.json").read_text())
        self.assertEqual(manifest["event_count"], 1)
        metadata = journal.metadata
        metadata["config"]["model"] = "changed"
        self.assertEqual(journal.metadata["config"]["model"], "luna")
        self.assertEqual(list((self.root / journal.trace_id).glob("*.tmp")), [])

    def test_sources_and_client_clock_are_preserved_separately(self):
        journal = self.store.start({})
        journal.record({"type": "playback_started", "t_ms": 9876, "clock_id": "phone"}, source="client")
        row = journal.since(0)["events"][0]
        self.assertEqual(row["source"], "client")
        self.assertEqual(row["event"]["t_ms"], 9876)
        self.assertEqual(row["event"]["clock_id"], "phone")
        self.assertNotEqual(row["clock_id"], "phone")
        self.assertEqual(row["timestamp_basis"], "server_receipt")

    def test_threads_do_not_duplicate_ids_or_corrupt_lines(self):
        journal = self.store.start({})
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers:
            list(workers.map(lambda index: journal.record({"type": "concurrent", "index": index}), range(80)))
        events = journal.export()["events"]
        self.assertEqual([row["id"] for row in events], list(range(1, 81)))
        self.assertEqual(sorted(row["event"]["index"] for row in events), list(range(80)))

    def test_logging_handler_accepts_observable_json_only(self):
        journal = self.store.start({})
        journal.emit(logging.LogRecord("provider", logging.INFO, "", 0, '{"type":"tool","result":"ok"}', (), None))
        journal.emit(logging.LogRecord("provider", logging.INFO, "", 0, "not json", (), None))
        self.assertEqual(journal.sequence, 1)
        self.assertEqual(journal.since(0)["events"][0]["source"], "provider")

    def test_list_newest_first_after_restart(self):
        first = self.store.start({"name": "first"})
        first.finish()
        second = self.store.start({"name": "second"})
        second.finish()
        sessions = TraceStore(self.root).list_sessions()
        self.assertEqual([item["trace_id"] for item in sessions], [second.trace_id, first.trace_id])

    def test_invalid_cursor_limit_and_status(self):
        journal = self.store.start({})
        for cursor in (-1, True, "0", None):
            with self.assertRaises(ValueError):
                journal.since(cursor)
        for limit in (0, -1, True, "400"):
            with self.assertRaises(ValueError):
                journal.since(0, limit)
        with self.assertRaises(ValueError):
            journal.finish("active")


class BufferedTraceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = TraceStore(self.root, secrets=["provider-secret-for-test"])
        self.journal = self.store.start({"model": "luna"})
        self.buffer = BufferedJournal(self.journal)

    def tearDown(self):
        try:
            self.buffer.finish()
        except TraceWriteError:
            pass
        self.temp.cleanup()

    def test_finish_drains_and_joins_before_final_manifest(self):
        for index in range(137):
            self.buffer.record({"type": "text", "index": index})
        final = self.buffer.finish("ended", "Done")
        self.assertFalse(self.buffer._writer.is_alive())
        self.assertEqual(final["buffer"]["pending_events"], 0)
        reopened = TraceStore(self.root).get(self.buffer.trace_id)
        self.assertEqual(reopened.metadata["status"], "ended")
        self.assertEqual([row["event"]["index"] for row in reopened.export()["events"]], list(range(137)))

    def test_batches_keep_order_and_amortize_disk_calls(self):
        with mock.patch.object(self.journal, "_append_prepared", wraps=self.journal._append_prepared) as append:
            for index in range(223):
                self.buffer.record({"type": "token", "index": index})
            self.buffer.finish()
            sizes = [len(call.args[0]) for call in append.call_args_list]
        self.assertEqual(sum(sizes), 223)
        self.assertLess(len(sizes), 10)
        self.assertLessEqual(max(sizes), 50)
        self.assertEqual([row["event"]["index"] for row in self.journal.export()["events"]], list(range(223)))

    def test_receipt_timestamps_are_captured_before_background_write(self):
        self.journal._started = 50
        with mock.patch("duplex.trial_traces.time.time", return_value=123456), mock.patch("duplex.trial_traces.time.perf_counter", return_value=50.012):
            self.buffer.record({"type": "client", "t_ms": 9999}, source="client")
        self.buffer.finish()
        row = self.journal.since(0)["events"][0]
        self.assertEqual(row["at"], 123456)
        self.assertEqual(row["elapsed_ms"], 12)
        self.assertEqual(row["event"]["t_ms"], 9999)

    def test_slow_disk_does_not_block_producers_and_queue_is_sanitized_copy(self):
        entered, release = threading.Event(), threading.Event()
        original = self.journal._append_prepared
        def delayed(batch):
            entered.set()
            release.wait(5)
            original(batch)
        self.journal._append_prepared = delayed
        self.buffer.record({"type": "first"})
        self.assertTrue(entered.wait(2))
        event = {"type": "audio", "pcm": "PRIVATE-AUDIO", "api_key": "provider-secret-for-test",
                 "mouth_cues": [{"viseme": "AA"}], "note": "provider-secret-for-test"}
        start = time.perf_counter()
        self.buffer.record(event)
        elapsed = time.perf_counter()-start
        event["mouth_cues"][0]["viseme"] = "CHANGED"
        with self.buffer._condition:
            queued = json.dumps(list(self.buffer._queue))
        self.assertNotIn("PRIVATE-AUDIO", queued)
        self.assertNotIn("provider-secret-for-test", queued)
        self.assertNotIn('"pcm"', queued)
        self.assertLess(elapsed, .2)
        release.set()
        self.buffer.finish()
        self.assertEqual(self.journal.export()["events"][1]["event"]["mouth_cues"][0]["viseme"], "AA")

    def test_writer_error_propagates_to_flush_finish_and_future_records(self):
        with mock.patch.object(self.journal, "_append_prepared", side_effect=OSError("disk failed provider-secret-for-test")):
            self.buffer.record({"type": "event"})
            with self.assertRaises(TraceWriteError):
                self.buffer.flush(timeout=2)
            with self.assertRaises(TraceWriteError):
                self.buffer.finish()
            with self.assertRaises(TraceWriteError):
                self.buffer.record({"type": "later"})
        self.assertIn("disk failed", self.buffer.error)
        self.assertNotIn("provider-secret-for-test", self.buffer.error)
        self.assertEqual(self.buffer.metadata["buffer"]["pending_events"], 1)
        self.assertEqual(self.journal.metadata["status"], "active")

    def test_late_records_are_ignored_without_raising(self):
        self.buffer.record({"type": "first"})
        self.buffer.finish()
        for _ in range(20):
            self.buffer.record({"type": "late"})
        self.assertEqual(self.buffer.metadata["buffer"]["late_records_ignored"], 20)
        self.assertEqual(self.journal.sequence, 1)

    def test_flush_and_export_include_every_previously_accepted_event(self):
        self.buffer.record({"type": "first"})
        self.buffer.flush(timeout=2)
        self.assertEqual(self.store.get(self.buffer.trace_id).sequence, 1)
        self.buffer.record({"type": "second"})
        exported = self.buffer.export()
        self.assertEqual(len(exported["events"]), 2)
        self.assertEqual(exported["session"]["buffer"]["pending_events"], 0)
        self.assertEqual(self.buffer.since(0)["head"], 2)

    def test_finished_journal_cannot_be_rewrapped(self):
        self.buffer.finish()
        with self.assertRaises(ValueError):
            BufferedJournal(self.journal)


if __name__ == "__main__":
    unittest.main()
