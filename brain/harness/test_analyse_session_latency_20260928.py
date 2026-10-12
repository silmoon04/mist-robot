import json
import tempfile
import unittest
from pathlib import Path

from brain.harness.analyse_session_latency_20260928 import analyze_file


def row(event_id, elapsed, source, event, basis="server_receipt"):
    return {"id": event_id, "elapsed_ms": elapsed, "source": source,
            "timestamp_basis": basis, "clock_id": "trace_server:fixture", "event": event}


class LatencyTraceTest(unittest.TestCase):
    def analyze(self, events):
        doc = {"session":{"trace_id":"fixture","config":{"id":"fixture-arch","floor":"selective"},"status":"active"},
               "events":events}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"fixture.json"
            path.write_text(json.dumps(doc),encoding="utf-8")
            return analyze_file(path)

    def test_correlates_exact_model_turn_and_audio_sequence_and_filters_browser_clock(self):
        events = [
            row(1,100,"server",{"type":"transcript_done","role":"user","text":"hello"}),
            row(2,120,"server",{"type":"debug_model","phase":"thinking_started","turn_id":"a1","input_text":"hello"}),
            row(3,140,"model_protocol",{"type":"turn.created","turn":{"id":"a1","role":"assistant"}}),
            row(3,150,"browser_command",{"type":"turn.delta","turn_id":"a1","delta":"wrong source duplicate"}),
            row(3,160,"browser_command",{"type":"speech_style","turn_id":"wrong-source-style"}),
            row(4,200,"model_protocol",{"type":"turn.delta","turn_id":"a1","delta":"hi"}),
            row(5,210,"server",{"type":"speech_style","turn_id":"a1"}),
            row(6,300,"server",{"type":"audio_delivery","epoch":0,"seq":0,"encoded_bytes":4800}),
            row(7,600,"browser",{"type":"playback_started","epoch":0,"sequence":0,"clock_source":"output_timestamp"}),
            row(8,650,"server",{"type":"latency","tts":{"epoch":0,"sequence":0,"first_byte_s":0.4}}),
            row(9,800,"model_protocol",{"type":"turn.created","turn":{"id":"u2","role":"user"}}),
            row(10,1000,"server",{"type":"transcript_done","role":"user","text":"missing"}),
            row(11,1100,"browser",{"type":"playback_started","epoch":0,"sequence":1,"client_ms":999999},basis="browser_client"),
        ]
        result=self.analyze(events)
        first, second = result["turns"]
        self.assertEqual(first["model_turn_id"],"a1")
        self.assertEqual(first["user_final_to_first_text_ms"],100)
        self.assertEqual(first["user_final_to_first_audio_packet_ms"],200)
        self.assertEqual(first["user_final_to_playback_started_ms"],500)
        self.assertTrue(first["playback_sequence_paired"])
        self.assertIsNone(second["user_final_to_first_text_ms"])
        self.assertEqual(result["latency_stats"]["user_final_to_first_text_ms"]["n"],1)

    def test_does_not_assign_text_after_a_new_user_turn_started(self):
        events = [
            row(1,100,"server",{"type":"transcript_done","role":"user","text":"hello"}),
            row(2,120,"server",{"type":"debug_model","phase":"thinking_started","turn_id":"a1","input_text":"hello"}),
            row(3,140,"model_protocol",{"type":"turn.created","turn":{"id":"a1","role":"assistant"}}),
            row(4,150,"model_protocol",{"type":"turn.created","turn":{"id":"u2","role":"user"}}),
            row(5,200,"model_protocol",{"type":"turn.delta","turn_id":"a1","delta":"stale output"}),
        ]
        result=self.analyze(events)
        first=result["turns"][0]
        self.assertIsNone(first["user_final_to_first_text_ms"])
        self.assertEqual(first["exclusion_reason"],"new_user_turn_before_first_text")

    def test_reset_between_audio_packet_and_playback_excludes_playback_only(self):
        events = [
            row(1,100,"server",{"type":"transcript_done","role":"user","text":"hello"}),
            row(2,120,"server",{"type":"debug_model","phase":"thinking_started","turn_id":"a1","input_text":"hello"}),
            row(3,140,"model_protocol",{"type":"turn.created","turn":{"id":"a1","role":"assistant"}}),
            row(4,200,"model_protocol",{"type":"turn.delta","turn_id":"a1","delta":"hi"}),
            row(5,210,"server",{"type":"speech_style","turn_id":"a1"}),
            row(6,300,"server",{"type":"audio_delivery","epoch":0,"seq":0,"encoded_bytes":4800}),
            row(7,500,"server",{"type":"audio_reset","epoch":1}),
            row(8,600,"browser",{"type":"playback_started","epoch":0,"sequence":0,"clock_source":"output_timestamp"}),
        ]
        result=self.analyze(events)
        turn=result["turns"][0]
        self.assertEqual(turn["user_final_to_first_audio_packet_ms"],200)
        self.assertIsNone(turn["user_final_to_playback_started_ms"])
        self.assertEqual(turn["playback_missing_reason"],"audio_reset_between_packet_and_playback")


if __name__ == "__main__":
    unittest.main()
